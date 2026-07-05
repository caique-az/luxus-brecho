"""
Rotas para gerenciar favoritos dos usuários.
Todas exigem JWT (`Authorization: Bearer`); a identidade vem de ``g.user_id``.
"""
from flask import Blueprint
from app.controllers.favorites_controller import (
    list_user_favorites,
    add_to_favorites,
    remove_from_favorites,
    check_favorite,
    toggle_favorite,
)
from app.services.jwt_service import jwt_required

favorites_bp = Blueprint("favorites", __name__)

# Listar favoritos do usuário
favorites_bp.route("/", methods=["GET"])(jwt_required(list_user_favorites))

# Adicionar produto aos favoritos
favorites_bp.route("/", methods=["POST"])(jwt_required(add_to_favorites))


# Remover produto dos favoritos
@favorites_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required
def remove_favorite_route(product_id):
    return remove_from_favorites(product_id)


# Verificar se produto está favoritado
@favorites_bp.route("/check/<int:product_id>", methods=["GET"])
@jwt_required
def check_favorite_route(product_id):
    return check_favorite(product_id)


# Alternar favorito (toggle)
favorites_bp.route("/toggle", methods=["POST"])(jwt_required(toggle_favorite))
