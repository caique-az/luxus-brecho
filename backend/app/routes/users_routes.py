from flask import Blueprint, current_app
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


def _get_limiter():
    """Obtém o limiter da aplicação se disponível."""
    return getattr(current_app, 'limiter', None)


def _apply_rate_limit(limit_string):
    """Decorator factory para aplicar rate limit se disponível."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            limiter = _get_limiter()
            if limiter:
                # Aplica limite dinamicamente
                return limiter.limit(limit_string)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


# Rotas CRUD básicas (protegidas por JWT)
@users_bp.route("/", methods=["GET"])
@admin_required
def list_users_endpoint():
    """Lista usuários - apenas admin."""
    return list_users()

@users_bp.route("/<int:id>", methods=["GET"])
@owner_or_admin_required('id')
def get_user_endpoint(id):
    """Busca usuário - dono ou admin."""
    return get_user(id)

@users_bp.route("/", methods=["POST"])
def create_user_endpoint():
    """Registro de usuário com rate limiting."""
    limiter = _get_limiter()
    if limiter:
        @limiter.limit("3 per minute;10 per hour")
        def limited_create():
            return create_user()
        return limited_create()
    return create_user()

@users_bp.route("/<int:id>", methods=["PUT"])
@owner_or_admin_required('id')
def update_user_endpoint(id):
    """Atualiza usuário - dono ou admin."""
    return update_user(id)

@users_bp.route("/<int:id>", methods=["DELETE"])
@admin_required
def delete_user_endpoint(id):
    """Exclui usuário - apenas admin."""
    return delete_user(id)

# Rotas de autenticação (com rate limiting)
@users_bp.route("/auth", methods=["POST"])
def auth_endpoint():
    """Endpoint de autenticação com rate limiting."""
    limiter = _get_limiter()
    if limiter:
        # 10 tentativas por minuto, 50 por hora
        @limiter.limit("10 per minute;50 per hour")
        def limited_auth():
            return authenticate_user()
        return limited_auth()
    return authenticate_user()

@users_bp.route("/<int:id>/change-password", methods=["PUT"])
@owner_or_admin_required('id')
def change_password_endpoint(id):
    """Altera senha - dono ou admin, com rate limiting."""
    limiter = _get_limiter()
    if limiter:
        @limiter.limit("3 per hour")
        def limited_change():
            return change_password(id)
        return limited_change()
    return change_password(id)

# Rota de refresh token
@users_bp.route("/refresh-token", methods=["POST"])
def refresh_token_route():
    """Renova access token usando refresh token."""
    return refresh_token_endpoint()

# Rotas de recuperação de senha (com rate limiting)
@users_bp.route("/forgot-password", methods=["POST"])
def forgot_password_endpoint():
    """Endpoint de recuperação de senha com rate limiting."""
    limiter = _get_limiter()
    if limiter:
        # 5 tentativas por hora
        @limiter.limit("5 per hour")
        def limited_forgot():
            return forgot_password()
        return limited_forgot()
    return forgot_password()

@users_bp.route("/reset-password", methods=["POST"])
def reset_password_endpoint():
    """Endpoint de reset de senha com rate limiting."""
    limiter = _get_limiter()
    if limiter:
        # 10 tentativas por hora
        @limiter.limit("10 per hour")
        def limited_reset():
            return reset_password()
        return limited_reset()
    return reset_password()

# Rotas de confirmação de email
users_bp.route("/confirm-email/<string:token>", methods=["GET"])(confirm_email)

@users_bp.route("/resend-confirmation", methods=["POST"])
def resend_confirmation_endpoint():
    """Endpoint de reenvio de confirmação com rate limiting."""
    limiter = _get_limiter()
    if limiter:
        # 3 tentativas por hora
        @limiter.limit("3 per hour")
        def limited_resend():
            return resend_confirmation_email()
        return limited_resend()
    return resend_confirmation_email()

# Rotas de informações
users_bp.route("/types", methods=["GET"])(get_user_types)
users_bp.route("/summary", methods=["GET"])(get_users_summary)

# Rotas de exclusão de conta
users_bp.route("/request-deletion", methods=["POST"])(request_account_deletion)
users_bp.route("/confirm-deletion", methods=["POST"])(confirm_account_deletion)
