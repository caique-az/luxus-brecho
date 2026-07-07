"""
Rotas para gerenciamento de pedidos.
- Rotas por usuário (/user/<user_id>): posse (dono ou admin).
- Alteração de status: apenas admin.
- Acesso/cancelamento por order_id: exige JWT; a posse é validada no controller
  (carrega o pedido e compara com g.user_id).
"""
from flask import Blueprint
from app.controllers.order_controller import (
    get_user_orders,
    get_order_by_id,
    create_order,
    update_order_status,
    cancel_order,
)
from app.services.jwt_service import (
    jwt_required,
    admin_required,
    owner_or_admin_required,
)

order_bp = Blueprint("orders", __name__)


@order_bp.route("/user/<int:user_id>", methods=["GET"])
@owner_or_admin_required("user_id")
def get_orders(user_id):
    """Obtém todos os pedidos do usuário."""
    return get_user_orders(user_id)


@order_bp.route("/<int:order_id>", methods=["GET"])
@jwt_required
def get_order(order_id):
    """Obtém um pedido específico (posse validada no controller)."""
    return get_order_by_id(order_id)


@order_bp.route("/user/<int:user_id>", methods=["POST"])
@owner_or_admin_required("user_id")
def create(user_id):
    """Cria um novo pedido."""
    return create_order(user_id)


@order_bp.route("/<int:order_id>/status", methods=["PUT"])
@admin_required
def update_status(order_id):
    """Atualiza o status de um pedido (apenas admin)."""
    return update_order_status(order_id)


@order_bp.route("/<int:order_id>/cancel", methods=["POST"])
@jwt_required
def cancel(order_id):
    """Cancela um pedido (posse validada no controller)."""
    return cancel_order(order_id)
