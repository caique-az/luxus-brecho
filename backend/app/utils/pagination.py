"""
Parsing de paginação a partir da query string.

Lê ``page``/``page_size`` de ``request.args`` aplicando clamp (page >= 1 e
page_size dentro de ``[1, max_size]``). Antes o mesmo cálculo estava reescrito,
com estilos divergentes, em vários controllers.
"""
from typing import Tuple
from flask import request


def get_pagination_params(default_size: int = 20, max_size: int = 100) -> Tuple[int, int]:
    """Retorna ``(page, page_size)`` já normalizados a partir de ``request.args``.

    Levanta ``ValueError`` se os parâmetros não forem inteiros — o chamador
    decide se responde 400 ou deixa o handler central tratar.
    """
    page = max(int(request.args.get("page", 1) or 1), 1)
    page_size = int(request.args.get("page_size", default_size) or default_size)
    page_size = min(max(page_size, 1), max_size)
    return page, page_size
