"""
Rotas para gerenciar favoritos dos usuários.
Autenticação via JWT (`Authorization: Bearer`); a identidade do usuário vem de
``g.user_id`` (int) — não mais de um header ``X-User-Id`` falsificável.
"""
from flask import Blueprint, g
from app.controllers.favorites_controller import (
    list_user_favorites,
    add_to_favorites,
    remove_from_favorites,
    check_favorite,
    toggle_favorite,
)
from app.services.jwt_service import jwt_required

favorites_bp = Blueprint("favorites", __name__)


# Listar favoritos do usuário autenticado
@favorites_bp.route("/", methods=["GET"])
@jwt_required
def list_favorites_route():
    return list_user_favorites(g.user_id)


# Adicionar produto aos favoritos
@favorites_bp.route("/", methods=["POST"])
@jwt_required
def add_favorite_route():
    return add_to_favorites(g.user_id)


# Remover produto dos favoritos
@favorites_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required
def remove_favorite_route(product_id):
    return remove_from_favorites(g.user_id, product_id)


# Verificar se produto está favoritado
@favorites_bp.route("/check/<int:product_id>", methods=["GET"])
@jwt_required
def check_favorite_route(product_id):
    return check_favorite(g.user_id, product_id)


# Alternar favorito (toggle)
@favorites_bp.route("/toggle", methods=["POST"])
@jwt_required
def toggle_favorite_route():
    return toggle_favorite(g.user_id)
