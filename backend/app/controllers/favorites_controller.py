"""
Controller para gerenciar favoritos dos usuários.
Endpoints:
- GET /favorites - Lista favoritos do usuário autenticado
- POST /favorites - Adiciona produto aos favoritos
- DELETE /favorites/<product_id> - Remove produto dos favoritos
- GET /favorites/check/<product_id> - Verifica se produto está favoritado
"""
from flask import request, jsonify, current_app
from typing import Any, Dict

from ..models.favorite_model import (
    add_favorite,
    remove_favorite,
    get_user_favorites,
    is_favorited,
    validate_favorite_payload,
    ensure_indexes
)
from ..models.product_model import get_collection as get_products_collection
from ..utils.serialization import serialize_doc as _serialize


def list_user_favorites(user_id: int):
    """
    Lista todos os favoritos do usuário com detalhes dos produtos.
    
    GET /favorites
    Autenticação: Authorization: Bearer <token> (identidade em g.user_id)
    
    Response:
    {
        "favorites": [
            {
                "_id": "...",
                "user_id": "...",
                "product_id": 1,
                "created_at": "...",
                "product": { ... }  // Detalhes do produto
            }
        ],
        "total": 5
    }
    """
    db = current_app.db
    if db is None:
        return jsonify(message="Banco de dados indisponível"), 503
    
    # Buscar favoritos
    success, error, favorites = get_user_favorites(db, user_id)
    
    if not success:
        return jsonify(message=error), 500
    
    # Buscar detalhes dos produtos
    products_coll = get_products_collection(db)
    product_ids = [fav['product_id'] for fav in favorites]
    
    products = list(products_coll.find({"id": {"$in": product_ids}}))
    products_dict = {p['id']: p for p in products}
    
    # Combinar favoritos com produtos
    result = []
    for fav in favorites:
        fav_data = _serialize(fav)
        product = products_dict.get(fav['product_id'])
        
        if product:
            # Remover _id do produto
            product_data = dict(product)
            product_data.pop('_id', None)
            fav_data['product'] = product_data
        else:
            # Produto não existe mais, mas mantém o favorito
            fav_data['product'] = None
        
        result.append(fav_data)
    
    return jsonify(
        favorites=result,
        total=len(result)
    ), 200


def add_to_favorites(user_id: int):
    """
    Adiciona um produto aos favoritos.
    
    POST /favorites
    Autenticação: Authorization: Bearer <token> (identidade em g.user_id)
    Body: { "product_id": 123 }
    
    Response:
    {
        "message": "Produto adicionado aos favoritos",
        "favorite": { ... }
    }
    """
    db = current_app.db
    if db is None:
        return jsonify(message="Banco de dados indisponível"), 503
    
    # Validar payload
    payload = request.get_json()
    if not payload:
        return jsonify(message="Payload inválido"), 400
    
    valid, error = validate_favorite_payload(payload)
    if not valid:
        return jsonify(message=error), 400
    
    product_id = payload['product_id']
    
    # Verificar se produto existe
    products_coll = get_products_collection(db)
    product = products_coll.find_one({"id": product_id})
    
    if not product:
        return jsonify(message="Produto não encontrado"), 404
    
    # Adicionar favorito
    success, error, favorite = add_favorite(db, user_id, product_id)
    
    if not success:
        if "já está nos favoritos" in error:
            return jsonify(message=error), 409  # Conflict
        return jsonify(message=error), 500
    
    return jsonify(
        message="Produto adicionado aos favoritos",
        favorite=_serialize(favorite)
    ), 201


def remove_from_favorites(user_id: int, product_id: int):
    """
    Remove um produto dos favoritos.
    
    DELETE /favorites/<product_id>
    Autenticação: Authorization: Bearer <token> (identidade em g.user_id)
    
    Response:
    {
        "message": "Produto removido dos favoritos"
    }
    """
    db = current_app.db
    if db is None:
        return jsonify(message="Banco de dados indisponível"), 503
    
    # Remover favorito
    success, error = remove_favorite(db, user_id, product_id)
    
    if not success:
        if "não encontrado" in error:
            return jsonify(message=error), 404
        return jsonify(message=error), 500
    
    return jsonify(message="Produto removido dos favoritos"), 200


def check_favorite(user_id: int, product_id: int):
    """
    Verifica se um produto está nos favoritos.
    
    GET /favorites/check/<product_id>
    Autenticação: Authorization: Bearer <token> (identidade em g.user_id)
    
    Response:
    {
        "is_favorited": true
    }
    """
    db = current_app.db
    if db is None:
        return jsonify(message="Banco de dados indisponível"), 503
    
    # Verificar se está favoritado
    favorited = is_favorited(db, user_id, product_id)
    
    return jsonify(is_favorited=favorited), 200


def toggle_favorite(user_id: int):
    """
    Alterna o estado de favorito (adiciona se não existe, remove se existe).
    
    POST /favorites/toggle
    Autenticação: Authorization: Bearer <token> (identidade em g.user_id)
    Body: { "product_id": 123 }
    
    Response:
    {
        "message": "Produto adicionado aos favoritos" | "Produto removido dos favoritos",
        "is_favorited": true | false
    }
    """
    db = current_app.db
    if db is None:
        return jsonify(message="Banco de dados indisponível"), 503
    
    # Validar payload
    payload = request.get_json()
    if not payload:
        return jsonify(message="Payload inválido"), 400
    
    valid, error = validate_favorite_payload(payload)
    if not valid:
        return jsonify(message=error), 400
    
    product_id = payload['product_id']
    
    # Verificar se produto existe
    products_coll = get_products_collection(db)
    product = products_coll.find_one({"id": product_id})
    
    if not product:
        return jsonify(message="Produto não encontrado"), 404
    
    # Verificar se já está favoritado
    favorited = is_favorited(db, user_id, product_id)
    
    if favorited:
        # Remover
        success, error = remove_favorite(db, user_id, product_id)
        if not success:
            return jsonify(message=error), 500
        
        return jsonify(
            message="Produto removido dos favoritos",
            is_favorited=False
        ), 200
    else:
        # Adicionar
        success, error, favorite = add_favorite(db, user_id, product_id)
        if not success:
            return jsonify(message=error), 500
        
        return jsonify(
            message="Produto adicionado aos favoritos",
            is_favorited=True,
            favorite=_serialize(favorite)
        ), 201
