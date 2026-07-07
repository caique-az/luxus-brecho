"""Parsing de paginação com limites seguros para as views."""
from typing import Tuple

from flask import request


def parse_pagination(default_page_size: int = 20, max_page_size: int = 100) -> Tuple[int, int, int]:
    """Lê ``page``/``page_size`` da query string com clamp.

    Retorna ``(page, page_size, skip)``. ``page`` é no mínimo 1; ``page_size``
    fica limitado a ``[1, max_page_size]`` para evitar um ``.limit()`` ilimitado
    (um ``page_size`` gigante varreria a coleção inteira — vetor de DoS). Valores
    ausentes ou não numéricos caem no default.
    """
    def _read_int(name: str, default: int) -> int:
        try:
            return int(request.args.get(name, default))
        except (TypeError, ValueError):
            return default

    page = max(_read_int("page", 1), 1)
    page_size = min(max(_read_int("page_size", default_page_size), 1), max_page_size)
    skip = (page - 1) * page_size
    return page, page_size, skip
