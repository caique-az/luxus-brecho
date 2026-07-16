"""
Controller para gerenciar favoritos dos usuários.
Endpoints:
- GET /favorites - Lista favoritos do usuário autenticado
- POST /favorites - Adiciona produto aos favoritos
- DELETE /favorites/<product_id> - Remove produto dos favoritos
- GET /favorites/check/<product_id> - Verifica se produto está favoritado
"""
from flask import request, current_app
from app.utils.db import require_db
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
from ..utils.responses import ok, err


@require_db
def list_user_favorites(user_id: int):
    """
    Lista todos os favoritos do usuário com detalhes dos produtos.
    
    GET /favorites
    Autenticação: Authorization: Bearer <token> (identidade em g.user_id)
    
    Response:
    {
        "favorites": [
            {
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
    
    # Buscar favoritos
    success, error, favorites = get_user_favorites(db, user_id)
    
    if not success:
        return err(error, 500)

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
    
    return ok({"favorites": result, "total": len(result)})


@require_db
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
    
    # Validar payload
    payload = request.get_json()
    if not payload:
        return err("Payload inválido")

    valid, error = validate_favorite_payload(payload)
    if not valid:
        return err(error)

    product_id = payload['product_id']

    # Verificar se produto existe
    products_coll = get_products_collection(db)
    product = products_coll.find_one({"id": product_id})

    if not product:
        return err("Produto não encontrado", 404)

    # Adicionar favorito
    success, error, favorite = add_favorite(db, user_id, product_id)

    if not success:
        if "já está nos favoritos" in error:
            return err(error, 409)  # Conflict
        return err(error, 500)

    return ok(
        message="Produto adicionado aos favoritos",
        status=201,
        favorite=_serialize(favorite)
    )


@require_db
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
    
    # Remover favorito
    success, error = remove_favorite(db, user_id, product_id)
    
    if not success:
        if "não encontrado" in error:
            return err(error, 404)
        return err(error, 500)

    return ok(message="Produto removido dos favoritos")


@require_db
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
    
    # Verificar se está favoritado
    favorited = is_favorited(db, user_id, product_id)

    return ok(is_favorited=favorited)


@require_db
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
    
    # Validar payload
    payload = request.get_json()
    if not payload:
        return err("Payload inválido")

    valid, error = validate_favorite_payload(payload)
    if not valid:
        return err(error)

    product_id = payload['product_id']

    # Verificar se produto existe
    products_coll = get_products_collection(db)
    product = products_coll.find_one({"id": product_id})

    if not product:
        return err("Produto não encontrado", 404)

    # Verificar se já está favoritado
    favorited = is_favorited(db, user_id, product_id)

    if favorited:
        # Remover
        success, error = remove_favorite(db, user_id, product_id)
        if not success:
            return err(error, 500)

        return ok(
            message="Produto removido dos favoritos",
            is_favorited=False
        )
    else:
        # Adicionar
        success, error, favorite = add_favorite(db, user_id, product_id)
        if not success:
            return err(error, 500)

        return ok(
            message="Produto adicionado aos favoritos",
            status=201,
            is_favorited=True,
            favorite=_serialize(favorite)
        )
