"""
Controller para gerenciar favoritos dos usuários.
A identidade vem do JWT (``g.user_id``, int); as rotas aplicam ``@jwt_required``
e repassam ``g.user_id`` como ``user_id``.
Endpoints:
- GET /favorites - Lista favoritos do usuário autenticado
- POST /favorites - Adiciona produto aos favoritos
- DELETE /favorites/<product_id> - Remove produto dos favoritos
- GET /favorites/check/<product_id> - Verifica se produto está favoritado
- POST /favorites/toggle - Alterna favorito
"""
from flask import request, current_app
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
from ..utils.decorators import require_db
from ..utils.serialization import serialize_doc
from ..utils.responses import ok, err


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serializa favorito convertendo _id em string (favoritos mantêm o _id)."""
    if not doc:
        return {}
    d = dict(doc)
    if '_id' in d:
        d['_id'] = str(d['_id'])
    return d


@require_db
def list_user_favorites(user_id: int):
    """Lista todos os favoritos do usuário autenticado com detalhes dos produtos."""
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
            fav_data['product'] = serialize_doc(product)
        else:
            # Produto não existe mais, mas mantém o favorito
            fav_data['product'] = None

        result.append(fav_data)

    return ok({"favorites": result, "total": len(result)})


@require_db
def add_to_favorites(user_id: int):
    """Adiciona um produto aos favoritos do usuário autenticado.

    POST /favorites
    Body: { "product_id": 123 }
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
        favorite=_serialize(favorite),
    )


@require_db
def remove_from_favorites(user_id: int, product_id: int):
    """Remove um produto dos favoritos do usuário autenticado.

    DELETE /favorites/<product_id>
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
    """Verifica se um produto está nos favoritos do usuário autenticado.

    GET /favorites/check/<product_id>
    """
    db = current_app.db

    # Verificar se está favoritado
    favorited = is_favorited(db, user_id, product_id)

    return ok(is_favorited=favorited)


@require_db
def toggle_favorite(user_id: int):
    """Alterna o estado de favorito (adiciona se não existe, remove se existe).

    POST /favorites/toggle
    Body: { "product_id": 123 }
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

        return ok(message="Produto removido dos favoritos", is_favorited=False)
    else:
        # Adicionar
        success, error, favorite = add_favorite(db, user_id, product_id)
        if not success:
            return err(error, 500)

        return ok(
            message="Produto adicionado aos favoritos",
            status=201,
            is_favorited=True,
            favorite=_serialize(favorite),
        )
