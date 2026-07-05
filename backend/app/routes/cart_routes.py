"""
Rotas para gerenciamento de carrinhos de compras.
Todas exigem JWT: o dono do token deve ser o ``user_id`` da URL (ou admin).
"""
from flask import Blueprint
from app.controllers.cart_controller import (
    get_user_cart,
    add_to_cart,
    remove_from_cart,
    update_cart_item,
    clear_cart,
    sync_cart,
)
from app.services.jwt_service import owner_or_admin_required

cart_bp = Blueprint("cart", __name__)


# Rotas do carrinho
@cart_bp.route("/<int:user_id>", methods=["GET"])
@owner_or_admin_required('user_id')
def get_cart(user_id):
    """Obtém o carrinho do usuário."""
    return get_user_cart(user_id)


@cart_bp.route("/<int:user_id>/add", methods=["POST"])
@owner_or_admin_required('user_id')
def add_item(user_id):
    """Adiciona item ao carrinho."""
    return add_to_cart(user_id)


@cart_bp.route("/<int:user_id>/remove", methods=["POST"])
@owner_or_admin_required('user_id')
def remove_item(user_id):
    """Remove item do carrinho."""
    return remove_from_cart(user_id)


@cart_bp.route("/<int:user_id>/update", methods=["PUT"])
@owner_or_admin_required('user_id')
def update_item(user_id):
    """Atualiza quantidade de item no carrinho."""
    return update_cart_item(user_id)


@cart_bp.route("/<int:user_id>/clear", methods=["DELETE"])
@owner_or_admin_required('user_id')
def clear(user_id):
    """Limpa o carrinho do usuário."""
    return clear_cart(user_id)


@cart_bp.route("/<int:user_id>/sync", methods=["POST"])
@owner_or_admin_required('user_id')
def sync(user_id):
    """Sincroniza carrinho local com o servidor."""
    return sync_cart(user_id)
