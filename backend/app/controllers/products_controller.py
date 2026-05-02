import time
from typing import Any, Dict

from flask import request, jsonify, current_app
from marshmallow import Schema, fields, ValidationError
from pymongo.errors import DuplicateKeyError

from ..models.product_model import (
    get_collection,
    prepare_new_product,
    validate_product,
    normalize_product,
)
from ..services.supabase_storage import storage_service
from ..services.cache_service import get_cached_product, cache_product, invalidate_product_cache


class ProductQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=lambda x: 1 <= x <= 1000)
    page_size = fields.Integer(load_default=20, validate=lambda x: 1 <= x <= 100)
    categoria = fields.String(load_default=None, allow_none=True, validate=lambda x: len(x) <= 50 if x else True)
    q = fields.String(load_default=None, allow_none=True, validate=lambda x: len(x) <= 100 if x else True)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    d = dict(doc)
    d.pop("_id", None)
    return d


def list_products():
    schema = ProductQuerySchema()
    try:
        args = schema.load(request.args)
    except ValidationError as err:
        return jsonify({'success': False, 'message': 'Parâmetros inválidos', 'errors': err.messages}), 400

    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    coll = get_collection(db)
    categoria = args.get("categoria")
    q = args.get("q")
    page = args['page']
    page_size = args['page_size']

    query: Dict[str, Any] = {}
    if categoria:
        query["categoria"] = categoria
    if q:
        query["$text"] = {"$search": q}

    cursor = coll.find(query)
    cursor = cursor.sort([("score", {"$meta": "textScore"})]) if q else cursor.sort("titulo", 1)
    total = coll.count_documents(query)
    items = [_serialize(doc) for doc in cursor.skip((page - 1) * page_size).limit(page_size)]

    return jsonify(items=items, pagination={"page": page, "page_size": page_size, "total": total})


def get_product(id: int):
    cached = get_cached_product(id)
    if cached is not None:
        return jsonify(cached)

    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    coll = get_collection(db)
    doc = coll.find_one({"id": int(id)})
    if not doc:
        return jsonify(message="produto não encontrado"), 404

    serialized = _serialize(doc)
    cache_product(id, serialized)
    return jsonify(serialized)


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

    merged = dict(current)
    merged.pop("_id", None)
    merged.update(payload)
    merged = normalize_product(merged)

    ok, errors = validate_product(merged, db)
    if not ok:
        return jsonify(message="erro de validação", errors=errors), 400

    merged["id"] = current["id"]
    coll.update_one({"id": int(id)}, {"$set": merged})
    invalidate_product_cache(id)
    updated = coll.find_one({"id": int(id)})

    return jsonify(_serialize(updated))


def delete_product(id: int):
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    coll = get_collection(db)
    current = coll.find_one({"id": int(id)})
    if not current:
        return jsonify(message="produto não encontrado"), 404

    if current.get('imagem') and current['imagem'].startswith('http'):
        try:
            storage_service.delete_image(current['imagem'])
        except Exception as e:
            current_app.logger.warning(f"Erro ao deletar imagem: {e}")

    res = coll.delete_one({"id": int(id)})
    if res.deleted_count == 0:
        return jsonify(message="erro ao excluir produto"), 500

    invalidate_product_cache(id)
    return jsonify(message="produto excluído"), 200


def create_product_with_image():
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    try:
        if 'image' not in request.files:
            return jsonify(message="Imagem é obrigatória", errors={"image": "Nenhum arquivo de imagem enviado"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify(message="Nenhuma imagem selecionada", errors={"image": "Arquivo de imagem vazio"}), 400

        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify(
                message="Formato de arquivo inválido",
                errors={"image": f"Apenas os formatos {', '.join(allowed_extensions)} são permitidos"}
            ), 400

        file_content = file.read()
        if len(file_content) > 5 * 1024 * 1024:
            return jsonify(message="Arquivo muito grande", errors={"image": "O tamanho máximo permitido é 5MB"}), 400

        file.seek(0)

        form_data = {
            "titulo": request.form.get('titulo'),
            "descricao": request.form.get('descricao'),
            "preco": request.form.get('preco'),
            "categoria": request.form.get('categoria')
        }

        errors = {}
        for field in ['titulo', 'descricao', 'categoria']:
            if not form_data.get(field) or not str(form_data[field]).strip():
                errors[field] = f'O campo {field} é obrigatório'

        if not form_data.get('preco'):
            errors['preco'] = 'O campo preço é obrigatório'

        if errors:
            return jsonify(message="Campos obrigatórios não preenchidos", errors=errors), 400

        try:
            preco = float(form_data['preco'])
            if preco <= 0:
                return jsonify(message="O preço deve ser maior que zero"), 400
            form_data['preco'] = preco
        except (ValueError, TypeError):
            return jsonify(message="Preço deve ser um número válido"), 400

        temp_id = int(time.time() * 1000)
        success, result = storage_service.upload_image(file, temp_id)
        if not success:
            return jsonify(message=f"Erro no upload da imagem: {result}"), 400

        form_data['imagem'] = result

        coll = get_collection(db)
        ok, errors, product_doc = prepare_new_product(db, form_data)
        if not ok:
            storage_service.delete_image(result)
            return jsonify(message="erro de validação", errors=errors), 400

        product_id = product_doc['id']
        if temp_id != product_id:
            file.stream.seek(0)
            success_final, final_url = storage_service.upload_image(file, product_id)
            if success_final:
                storage_service.delete_image(result)
                product_doc['imagem'] = final_url

        try:
            coll.insert_one(product_doc)
        except DuplicateKeyError:
            storage_service.delete_image(result)
            return jsonify(message="ID já existente"), 409

        return jsonify({"message": "Produto criado com sucesso", "product": _serialize(product_doc)}), 201

    except Exception as e:
        current_app.logger.error(f"Erro ao criar produto com imagem: {e}")
        return jsonify(message="Erro interno no servidor"), 500


def update_product_image(id: int):
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    coll = get_collection(db)
    current_product = coll.find_one({"id": int(id)})
    if not current_product:
        return jsonify(message="produto não encontrado"), 404

    if 'image' not in request.files:
        return jsonify(message="Nova imagem é obrigatória"), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify(message="Nenhuma imagem selecionada"), 400

    try:
        success, result = storage_service.upload_image(file, id)
        if not success:
            return jsonify(message=f"Erro no upload: {result}"), 400

        old_image_url = current_product.get('imagem')
        if old_image_url and old_image_url.startswith('http'):
            storage_service.delete_image(old_image_url)

        coll.update_one({"id": int(id)}, {"$set": {"imagem": result}})
        invalidate_product_cache(id)
        updated_product = coll.find_one({"id": int(id)})

        return jsonify({"message": "Imagem atualizada com sucesso", "product": _serialize(updated_product)}), 200

    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar imagem: {e}")
        return jsonify(message="Erro interno no servidor"), 500


def get_products_by_category(categoria: str):
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    coll = get_collection(db)

    page = max(int(request.args.get("page", 1) or 1), 1)
    page_size = min(max(int(request.args.get("page_size", 20) or 20), 1), 100)

    query = {"categoria": categoria}
    total = coll.count_documents(query)
    items = [
        _serialize(doc)
        for doc in coll.find(query).sort("titulo", 1).skip((page - 1) * page_size).limit(page_size)
    ]

    if not items:
        return jsonify(message="nenhum produto encontrado para essa categoria"), 404

    return jsonify(items=items, categoria=categoria, pagination={"page": page, "page_size": page_size, "total": total})
