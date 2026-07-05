"""
Serialização de documentos do MongoDB para resposta da API.

Centraliza a remoção do campo interno ``_id``, que nunca deve vazar na
resposta (ver `docs/convencoes.md`). Antes desta função a lógica
``d = dict(doc); d.pop("_id")`` estava copiada em vários controllers.
"""
from typing import Any, Dict


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Copia o documento removendo o campo interno ``_id`` do MongoDB."""
    if not doc:
        return {}
    d = dict(doc)
    d.pop("_id", None)
    return d
