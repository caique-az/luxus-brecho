from flask import jsonify, request, current_app
from datetime import datetime
from typing import Dict, Any
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import time

from ..models.product_model import (
    get_collection,
    normalize_product,
    validate_product,
    prepare_new_product,
)

from ..services import storage as storage_service
from ..services.cache_service import (
    cache_product,
    get_cached_product,
    invalidate_product_cache,
)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    d = dict(doc)
    d.pop("_id", None)
    return d


def list_products():
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    coll = get_collection(db)

    categoria = request.args.get("categoria")
    q = request.args.get("q")
    
    # Tratamento seguro dos parâmetros de paginação
    try:
        page = max(int(request.args.get("page", 1) or 1), 1)
    except (ValueError, TypeError):
        page = 1
    
    try:
        page_size = min(max(int(request.args.get("page_size", 10) or 10), 1), 100)
    except (ValueError, TypeError):
        page_size = 10

    query: Dict[str, Any] = {}
    if categoria:
        query["categoria"] = categoria
    if q:
        query["$text"] = {"$search": q}

    # Projeção para retornar apenas campos necessários
    projection = {
        "_id": 0,
        "id": 1,
        "titulo": 1,
        "preco": 1,
        "descricao": 1,
        "categoria": 1,
        "imagem": 1,
        "status": 1,
    }

    # Usa aggregation com $facet para obter items e total em uma única query
    skip = (page - 1) * page_size
    
    pipeline = [
        {"$match": query},
    ]
    
    # Adiciona sort por score se for busca textual
    if q:
        pipeline.append({"$sort": {"score": {"$meta": "textScore"}}})
    
    pipeline.append({
        "$facet": {
            "items": [
                {"$skip": skip},
                {"$limit": page_size},
                {"$project": projection}
            ],
            "total": [{"$count": "count"}]
        }
    })

    result = list(coll.aggregate(pipeline))
    
    if result:
        items = result[0].get("items", [])
        total_arr = result[0].get("total", [])
        total = total_arr[0]["count"] if total_arr else 0
    else:
        items = []
        total = 0

    return jsonify(
        items=items,
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    )


def get_product(id: int):
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503
    
    # Tenta obter do cache primeiro
    cached = get_cached_product(int(id))
    if cached:
        return jsonify(cached)
    
    coll = get_collection(db)
    doc = coll.find_one({"id": int(id)})
    if not doc:
        return jsonify(message="produto não encontrado"), 404
    
    # Serializa e cacheia o produto
    product_data = _serialize(doc)
    cache_product(int(id), product_data, ttl=600)  # Cache por 10 minutos
    
    return jsonify(product_data)


def create_product():
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503
    coll = get_collection(db)

    payload = request.get_json(silent=True) or {}
    ok, errors, doc = prepare_new_product(db, payload)
    if not ok:
        return jsonify(message="erro de validação", errors=errors), 400

    try:
        coll.insert_one(doc)
    except DuplicateKeyError:
        return jsonify(message="ID já existente"), 409

    return jsonify(_serialize(doc)), 201


def update_product(id: int):
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503
    coll = get_collection(db)

    current = coll.find_one({"id": int(id)})
    if not current:
        return jsonify(message="produto não encontrado"), 404

    payload = request.get_json(silent=True) or {}
    # Merge parcial
    merged = dict(current)
    merged.pop("_id", None)
    merged.update(payload)
    merged = normalize_product(merged)

    ok, errors = validate_product(merged, db)  # Passa db para validação dinâmica
    if not ok:
        return jsonify(message="erro de validação", errors=errors), 400

    # Não permitir troca de id
    merged["id"] = current["id"]

    coll.update_one({"id": int(id)}, {"$set": merged})
    updated = coll.find_one({"id": int(id)})
    
    # Invalida cache do produto atualizado
    invalidate_product_cache(int(id))
    
    return jsonify(_serialize(updated))


def delete_product(id: int):
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503
    coll = get_collection(db)

    res = coll.delete_one({"id": int(id)})
    if res.deleted_count == 0:
        return jsonify(message="produto não encontrado"), 404
    
    # Invalida cache do produto deletado
    invalidate_product_cache(int(id))
    
    return jsonify(message="produto excluído"), 200


def create_product_with_image():
    """
    Cria produto com upload de imagem
    POST /api/products/with-image
    
    Form Data:
    - titulo, descricao, preco, categoria: dados do produto
    - image: arquivo de imagem
    """
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503
    
    try:
        # Validação detalhada da imagem
        if 'image' not in request.files:
            return jsonify(message="Imagem é obrigatória", errors={"image": "Nenhum arquivo de imagem enviado"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify(message="Nenhuma imagem selecionada", errors={"image": "Arquivo de imagem vazio"}), 400
            
        # Valida extensão do arquivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify(
                message="Formato de arquivo inválido",
                errors={"image": f"Apenas os formatos {', '.join(allowed_extensions)} são permitidos"}
            ), 400
            
        # Valida tamanho do arquivo (máx 5MB)
        if len(file.read()) > 5 * 1024 * 1024:  # 5MB em bytes
            file.seek(0)  # Reset do ponteiro do arquivo
            return jsonify(
                message="Arquivo muito grande",
                errors={"image": "O tamanho máximo permitido é 5MB"}
            ), 400
            
        file.seek(0)  # Reset do ponteiro do arquivo após leitura
        
        # Obtém dados do produto do form
        form_data = {
            "titulo": request.form.get('titulo'),
            "descricao": request.form.get('descricao'),
            "preco": request.form.get('preco'),
            "categoria": request.form.get('categoria')
        }
        
        # Validação detalhada de campos obrigatórios
        errors = {}
        for field in ['titulo', 'descricao', 'categoria']:
            if not form_data.get(field):
                errors[field] = f'O campo {field} é obrigatório'
            elif isinstance(form_data[field], str) and len(form_data[field].strip()) == 0:
                errors[field] = f'O campo {field} não pode estar vazio'

        if not form_data.get('preco'):
            errors['preco'] = 'O campo preço é obrigatório'
        
        if errors:
            return jsonify(message="Campos obrigatórios não preenchidos", errors=errors), 400
        
        # Validação e conversão do preço
        try:
            preco = float(form_data['preco'])
            if preco <= 0:
                return jsonify(message="O preço deve ser maior que zero"), 400
            form_data['preco'] = preco
        except (ValueError, TypeError):
            return jsonify(message="Preço deve ser um número válido"), 400
        
        # Primeiro faz upload da imagem para obter URL
        # Usa um ID temporário para o upload
        temp_id = int(time.time() * 1000)  # Timestamp como ID temporário
        success, result = storage_service.upload_image(file, temp_id)
        
        if not success:
            return jsonify(message=f"Erro no upload da imagem: {result}"), 400
        
        # Adiciona URL da imagem aos dados do produto
        form_data['imagem'] = result
        
        # Agora prepara produto com todos os dados (incluindo imagem)
        coll = get_collection(db)
        ok, errors, product_doc = prepare_new_product(db, form_data)
        if not ok:
            # Se falhar na validação, remove a imagem já enviada
            storage_service.delete_image(result)
            return jsonify(message="erro de validação", errors=errors), 400
        
        # Renomeia arquivo para usar o ID real do produto
        product_id = product_doc['id']
        if temp_id != product_id:
            # Upload novamente com ID correto
            file.stream.seek(0)  # Reset do stream do arquivo
            success_final, final_url = storage_service.upload_image(file, product_id)
            if success_final:
                # Remove arquivo temporário e usa novo URL
                storage_service.delete_image(result)
                product_doc['imagem'] = final_url
            # Se falhar o re-upload, mantém o temporário mas funciona
        
        # Insere produto no banco
        try:
            coll.insert_one(product_doc)
        except DuplicateKeyError:
            # Se falhar, tenta deletar a imagem que foi enviada
            storage_service.delete_image(result)
            return jsonify(message="ID já existente"), 409
        
        return jsonify({
            "message": "Produto criado com sucesso",
            "product": _serialize(product_doc)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Erro ao criar produto com imagem: {e}")
        return jsonify(message="Erro interno no servidor"), 500


def update_product_image(id: int):
    """
    Atualiza apenas a imagem de um produto
    PUT /api/products/<id>/image
    
    Form Data:
    - image: novo arquivo de imagem
    """
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503
    
    coll = get_collection(db)
    
    # Verifica se produto existe
    current_product = coll.find_one({"id": int(id)})
    if not current_product:
        return jsonify(message="produto não encontrado"), 404
    
    # Valida se há nova imagem
    if 'image' not in request.files:
        return jsonify(message="Nova imagem é obrigatória"), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify(message="Nenhuma imagem selecionada"), 400
    
    try:
        # Faz upload da nova imagem
        success, result = storage_service.upload_image(file, id)
        
        if not success:
            return jsonify(message=f"Erro no upload: {result}"), 400
        
        # Deleta imagem antiga se existir
        old_image_url = current_product.get('imagem')
        if old_image_url and old_image_url.startswith('http'):
            storage_service.delete_image(old_image_url)
        
        # Atualiza produto com nova URL
        coll.update_one(
            {"id": int(id)}, 
            {"$set": {"imagem": result}}
        )
        
        # Retorna produto atualizado
        updated_product = coll.find_one({"id": int(id)})
        return jsonify({
            "message": "Imagem atualizada com sucesso",
            "product": _serialize(updated_product)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar imagem: {e}")
        return jsonify(message="Erro interno no servidor"), 500
