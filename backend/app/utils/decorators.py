"""
Decorators de infraestrutura compartilhados entre controllers.
"""
from functools import wraps
from flask import current_app, jsonify, g


def require_db(f):
    """Curto-circuita a requisição com um 503 padronizado quando o banco não
    está disponível (``current_app.db is None``).

    Substitui o bloco ``db = current_app.db; if db is None: return ..., 503``
    que estava repetido — com mensagens divergentes — em dezenas de funções.
    Injeta ``g.db`` para quem preferir usá-lo; o padrão ``db = current_app.db``
    continua válido, pois o decorator garante que não é ``None``.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_app.db is None:
            return jsonify(success=False, message="Banco de dados indisponível"), 503
        g.db = current_app.db
        return f(*args, **kwargs)

    return decorated
