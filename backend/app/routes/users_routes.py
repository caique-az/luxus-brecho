from flask import Blueprint
from app.controllers.users_controller import (
    list_users,
    get_user,
    create_user,
    update_user,
    delete_user,
    authenticate_user,
    change_password,
    forgot_password,
    reset_password,
    get_user_types,
    get_users_summary,
    confirm_email,
    resend_confirmation_email,
    request_account_deletion,
    confirm_account_deletion,
    refresh_token_endpoint,
)
from app.services.jwt_service import jwt_required, admin_required, owner_or_admin_required

users_bp = Blueprint("users", __name__)


# Rotas CRUD básicas (protegidas por JWT)
@users_bp.route("/", methods=["GET"])
@admin_required
def list_users_endpoint():
    return list_users()

@users_bp.route("/<int:id>", methods=["GET"])
@owner_or_admin_required('id')
def get_user_endpoint(id):
    return get_user(id)

@users_bp.route("/", methods=["POST"])
def create_user_endpoint():
    return create_user()

@users_bp.route("/<int:id>", methods=["PUT"])
@owner_or_admin_required('id')
def update_user_endpoint(id):
    return update_user(id)

@users_bp.route("/<int:id>", methods=["DELETE"])
@admin_required
def delete_user_endpoint(id):
    return delete_user(id)

# Rotas de autenticação
@users_bp.route("/auth", methods=["POST"])
def auth_endpoint():
    return authenticate_user()

@users_bp.route("/<int:id>/change-password", methods=["PUT"])
@owner_or_admin_required('id')
def change_password_endpoint(id):
    return change_password(id)

# Rota de refresh token
@users_bp.route("/refresh-token", methods=["POST"])
def refresh_token_route():
    return refresh_token_endpoint()

# Rotas de recuperação de senha
@users_bp.route("/forgot-password", methods=["POST"])
def forgot_password_endpoint():
    return forgot_password()

@users_bp.route("/reset-password", methods=["POST"])
def reset_password_endpoint():
    return reset_password()

# Rotas de confirmação de email
users_bp.route("/confirm-email/<string:token>", methods=["GET"])(confirm_email)

@users_bp.route("/resend-confirmation", methods=["POST"])
def resend_confirmation_endpoint():
    return resend_confirmation_email()

# Rotas de informações
users_bp.route("/types", methods=["GET"])(get_user_types)

@users_bp.route("/summary", methods=["GET"])
@admin_required
def get_users_summary_endpoint():
    return get_users_summary()

# Rotas de exclusão de conta (requerem autenticação)
@users_bp.route("/request-deletion", methods=["POST"])
@jwt_required
def request_deletion_endpoint():
    return request_account_deletion()

@users_bp.route("/confirm-deletion", methods=["POST"])
@jwt_required
def confirm_deletion_endpoint():
    return confirm_account_deletion()


def _register_rate_limits(state):
    """Aplica rate limits nos endpoints sensíveis após o registro do blueprint."""
    limiter = getattr(state.app, 'limiter', None)
    if not limiter:
        return
    vf = state.app.view_functions
    limiter.limit("10 per minute;50 per hour")(vf['users.auth_endpoint'])
    limiter.limit("3 per minute;10 per hour")(vf['users.create_user_endpoint'])
    limiter.limit("3 per hour")(vf['users.change_password_endpoint'])
    limiter.limit("5 per hour")(vf['users.forgot_password_endpoint'])
    limiter.limit("10 per hour")(vf['users.reset_password_endpoint'])
    limiter.limit("3 per hour")(vf['users.resend_confirmation_endpoint'])


users_bp.record_once(_register_rate_limits)
