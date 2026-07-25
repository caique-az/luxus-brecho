"""Serialização canônica de documentos Mongo para JSON."""
from typing import Any, Dict


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serializa um documento Mongo removendo o ``_id`` interno.

    Forma única que substitui as cópias divergentes de ``_serialize`` espalhadas
    pelos controllers. Em especial, corrige a de favoritos, que **vazava** o
    ``_id`` (convertia o ObjectId para str e o mantinha no output). Não remove
    campos sensíveis específicos de usuário — para isso use ``normalize_user``
    no model, que também tira ``senha_hash``/tokens.
    """
    if not doc:
        return {}
    result = dict(doc)
    result.pop("_id", None)
    return result
