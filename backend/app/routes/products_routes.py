from __future__ import annotations
from flask import Blueprint, request, current_app
from app.utils.db import require_db
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import Any, Dict
from marshmallow import Schema, fields, ValidationError
import time
from functools import wraps

from ..services.jwt_service import admin_required
from ..utils.responses import ok, err
from ..utils.pagination import parse_pagination

class ProductQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=lambda x: 1 <= x <= 1000)
    page_size = fields.Integer(load_default=20, validate=lambda x: 1 <= x <= 100)
    categoria = fields.String(load_default=None, allow_none=True, validate=lambda x: len(x) <= 50 if x else True)
    q = fields.String(load_default=None, allow_none=True, validate=lambda x: len(x) <= 100 if x else True)

from ..models.product_model import (
    get_collection,
    prepare_new_product,
    validate_product,
    normalize_product,
)
from ..services.supabase_storage import storage_service
from ..utils.serialization import serialize_doc as _serialize

# Create the Blueprint
products_bp = Blueprint('products', __name__)

@products_bp.route('/', methods=['GET'])
@require_db
def list_products():
    """List all products with optional filtering and pagination"""
    schema = ProductQuerySchema()
    try:
        args = schema.load(request.args)
    except ValidationError as exc:
        return err('Parâmetros inválidos', 400, errors=exc.messages)

    db = current_app.db

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

    if q:
        cursor = cursor.sort([("score", {"$meta": "textScore"})])
    else:
        cursor = cursor.sort("titulo", 1)

    total = coll.count_documents(query)

    items = [
        _serialize(doc) for doc in cursor.skip((page - 1) * page_size).limit(page_size)
    ]

    return ok({
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    })

@products_bp.route('/<int:id>', methods=['GET'])
@require_db
def get_product(id: int):
    """Get a single product by ID"""
    db = current_app.db

    coll = get_collection(db)
    doc = coll.find_one({"id": int(id)})

    if not doc:
        return err("produto não encontrado", 404)

    return ok(_serialize(doc))

@products_bp.route('/', methods=['POST'])
@admin_required
@require_db
def create_product():
    """Create a new product - Admin only"""
    db = current_app.db

    coll = get_collection(db)
    payload = request.get_json(silent=True) or {}

    valid, errors, doc = prepare_new_product(db, payload)
    if not valid:
        return err("erro de validação", 400, errors=errors)

    try:
        coll.insert_one(doc)
    except DuplicateKeyError:
        return err("ID já existente", 409)

    return ok(_serialize(doc), status=201)

@products_bp.route('/<int:id>', methods=['PUT'])
@admin_required
@require_db
def update_product(id: int):
    """Update an existing product - Admin only"""
    db = current_app.db

    coll = get_collection(db)
    current = coll.find_one({"id": int(id)})

    if not current:
        return err("produto não encontrado", 404)

    payload = request.get_json(silent=True) or {}

    # Merge parcial
    merged = dict(current)
    merged.pop("_id", None)
    merged.update(payload)
    merged = normalize_product(merged)

    valid, errors = validate_product(merged, db)
    if not valid:
        return err("erro de validação", 400, errors=errors)

    # Não permitir troca de id
    merged["id"] = current["id"]

    coll.update_one({"id": int(id)}, {"$set": merged})
    updated = coll.find_one({"id": int(id)})

    return ok(_serialize(updated))

@products_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
@require_db
def delete_product(id: int):
    """Delete a product - Admin only"""
    db = current_app.db

    coll = get_collection(db)

    # Check if product exists first
    current = coll.find_one({"id": int(id)})
    if not current:
        return err("produto não encontrado", 404)

    # Delete associated image if exists
    if current.get('imagem') and current['imagem'].startswith('http'):
        try:
            storage_service.delete_image(current['imagem'])
        except Exception as e:
            current_app.logger.warning(f"Erro ao deletar imagem: {e}")

    # Delete product from database
    res = coll.delete_one({"id": int(id)})
    if res.deleted_count == 0:
        return err("erro ao excluir produto", 500)

    return ok(message="produto excluído")

@products_bp.route('/with-image', methods=['POST'])
@admin_required
@require_db
def create_product_with_image():
    """
    Create product with image upload
    POST /api/products/with-image

    Form Data:
    - titulo, descricao, preco, categoria: product data
    - image: image file
    """
    db = current_app.db

    try:
        # Detailed image validation
        if 'image' not in request.files:
            return err("Imagem é obrigatória", 400, errors={"image": "Nenhum arquivo de imagem enviado"})

        file = request.files['image']
        if file.filename == '':
            return err("Nenhuma imagem selecionada", 400, errors={"image": "Arquivo de imagem vazio"})

        # Validate file extension
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return err(
                "Formato de arquivo inválido",
                400,
                errors={"image": f"Apenas os formatos {', '.join(allowed_extensions)} são permitidos"},
            )

        # Validate file size (max 5MB)
        file_content = file.read()
        if len(file_content) > 5 * 1024 * 1024:  # 5MB in bytes
            return err("Arquivo muito grande", 400, errors={"image": "O tamanho máximo permitido é 5MB"})

        file.seek(0)  # Reset file pointer after reading

        # Get product data from form
        form_data = {
            "titulo": request.form.get('titulo'),
            "descricao": request.form.get('descricao'),
            "preco": request.form.get('preco'),
            "categoria": request.form.get('categoria')
        }

        # Detailed validation of required fields
        errors = {}
        for field in ['titulo', 'descricao', 'categoria']:
            if not form_data.get(field):
                errors[field] = f'O campo {field} é obrigatório'
            elif isinstance(form_data[field], str) and len(form_data[field].strip()) == 0:
                errors[field] = f'O campo {field} não pode estar vazio'

        if not form_data.get('preco'):
            errors['preco'] = 'O campo preço é obrigatório'

        if errors:
            return err("Campos obrigatórios não preenchidos", 400, errors=errors)

        # Price validation and conversion
        try:
            preco = float(form_data['preco'])
            if preco <= 0:
                return err("O preço deve ser maior que zero")
            form_data['preco'] = preco
        except (ValueError, TypeError):
            return err("Preço deve ser um número válido")

        # First upload image to get URL
        # Use temporary ID for upload
        temp_id = int(time.time() * 1000)  # Timestamp as temporary ID
        success, result = storage_service.upload_image(file, temp_id)

        if not success:
            return err(f"Erro no upload da imagem: {result}")

        # Add image URL to product data
        form_data['imagem'] = result

        # Now prepare product with all data (including image)
        coll = get_collection(db)
        valid, errors, product_doc = prepare_new_product(db, form_data)
        if not valid:
            # If validation fails, remove already uploaded image
            storage_service.delete_image(result)
            return err("erro de validação", 400, errors=errors)

        # Rename file to use real product ID
        product_id = product_doc['id']
        if temp_id != product_id:
            # Upload again with correct ID
            file.stream.seek(0)  # Reset file stream
            success_final, final_url = storage_service.upload_image(file, product_id)
            if success_final:
                # Remove temporary file and use new URL
                storage_service.delete_image(result)
                product_doc['imagem'] = final_url
            # If re-upload fails, keep temporary but it still works

        # Insert product into database
        try:
            coll.insert_one(product_doc)
        except DuplicateKeyError:
            # If it fails, try to delete uploaded image
            storage_service.delete_image(result)
            return err("ID já existente", 409)

        return ok(message="Produto criado com sucesso", status=201, product=_serialize(product_doc))

    except Exception as e:
        current_app.logger.error(f"Erro ao criar produto com imagem: {e}")
        return err("Erro interno no servidor", 500)

@products_bp.route('/<int:id>/image', methods=['PUT'])
@admin_required
@require_db
def update_product_image(id: int):
    """
    Update only the image of a product - Admin only
    PUT /api/products/<id>/image

    Form Data:
    - image: new image file
    """
    db = current_app.db

    coll = get_collection(db)

    # Check if product exists
    current_product = coll.find_one({"id": int(id)})
    if not current_product:
        return err("produto não encontrado", 404)

    # Validate if there's a new image
    if 'image' not in request.files:
        return err("Nova imagem é obrigatória")

    file = request.files['image']
    if file.filename == '':
        return err("Nenhuma imagem selecionada")

    try:
        # Upload new image
        success, result = storage_service.upload_image(file, id)

        if not success:
            return err(f"Erro no upload: {result}")

        # Delete old image if it exists
        old_image_url = current_product.get('imagem')
        if old_image_url and old_image_url.startswith('http'):
            storage_service.delete_image(old_image_url)

        # Update product with new URL
        coll.update_one(
            {"id": int(id)},
            {"$set": {"imagem": result}}
        )

        # Return updated product
        updated_product = coll.find_one({"id": int(id)})
        return ok(message="Imagem atualizada com sucesso", product=_serialize(updated_product))

    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar imagem: {e}")
        return err("Erro interno no servidor", 500)

@products_bp.route('/category/<string:categoria>', methods=['GET'])
@require_db
def get_products_by_category(categoria: str):
    """Get products by specific category"""
    db = current_app.db

    coll = get_collection(db)

    page, page_size, skip = parse_pagination(default_page_size=20)

    query = {"categoria": categoria}
    cursor = coll.find(query).sort("titulo", 1)
    total = coll.count_documents(query)

    items = [
        _serialize(doc) for doc in cursor.skip(skip).limit(page_size)
    ]

    if not items:
        return err("nenhum produto encontrado para essa categoria", 404)

    return ok({
        "items": items,
        "categoria": categoria,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    })
