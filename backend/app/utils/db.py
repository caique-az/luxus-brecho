"""Decorator de disponibilidade do banco para as views."""
from functools import wraps

from flask import current_app, jsonify


def require_db(f):
    """Aborta com 503 se o banco não estiver disponível.

    Centraliza o guard ``db = current_app.db; if db is None: return 503`` que
    estava copiado ~46× nos controllers/rotas, com três mensagens divergentes
    (``banco de dados indisponível`` / ``Banco de dados indisponível`` /
    ``database unavailable``). Agora há uma única resposta canônica. As views
    continuam lendo ``current_app.db`` normalmente — o decorator só garante que
    ele não é ``None``.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if getattr(current_app, "db", None) is None:
            return jsonify(message="Banco de dados indisponível"), 503
        return f(*args, **kwargs)

    return wrapper
