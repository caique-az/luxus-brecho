"""
Decorators de infraestrutura compartilhados entre controllers.
"""
from functools import wraps
from flask import current_app, jsonify


def require_db(f):
    """Curto-circuita a requisição com um 503 padronizado quando o banco não
    está disponível (``current_app.db is None``).

    Substitui o bloco ``db = current_app.db; if db is None: return ..., 503``
    que estava repetido — com mensagens divergentes — em dezenas de funções.
    O corpo decorado segue lendo ``current_app.db``, agora com a garantia de
    que não é ``None``.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_app.db is None:
            return jsonify(success=False, message="Banco de dados indisponível"), 503
        return f(*args, **kwargs)

    return decorated
