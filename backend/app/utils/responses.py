"""
Helpers de resposta JSON no envelope padrão da API.

Envelope canônico (plano), definido em ``docs/convencoes.md``:

- sucesso: ``{"success": true, "message"?: str, <chaves de domínio...>}``
- erro:    ``{"success": false, "message": str, "errors"?: {campo: motivo}}``

Antes destes helpers cada controller montava o corpo à mão: uns incluíam
``success``, outros não; ``images`` e os decorators JWT usavam a chave ``error``.
Centralizar aqui garante que ``success`` sirva sempre de discriminador e que a
mensagem de erro tenha sempre a mesma chave (``message``).

O envelope é **plano**: os dados de domínio ficam no topo do corpo, ao lado de
``success`` (não aninhados sob ``data``), acompanhando o formato já usado pelos
controllers (``items``, ``favorites``, ``user`` ...). Endpoints que devolvem uma
lista pura (ex.: ``/categories/summary``) são a exceção documentada e não passam
por estes helpers.
"""
from typing import Any, Dict, Optional, Tuple
from flask import jsonify


def ok(
    data: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    status: int = 200,
    **extra: Any,
) -> Tuple[Any, int]:
    """Monta uma resposta de sucesso no envelope padrão.

    ``data`` é mesclado no topo do corpo, de modo que documentos de domínio que
    já tenham campos como ``status`` (produtos, pedidos) não colidam com o código
    HTTP. ``extra`` acrescenta chaves simples sem precisar montar um dict à parte.
    """
    body: Dict[str, Any] = {"success": True}
    if message is not None:
        body["message"] = message
    if data:
        body.update(data)
    if extra:
        body.update(extra)
    return jsonify(body), status


def err(
    message: str,
    status: int = 400,
    errors: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> Tuple[Any, int]:
    """Monta uma resposta de erro no envelope padrão.

    ``errors`` carrega o mapa ``{campo: motivo}`` de erros de validação; ``extra``
    acrescenta sinalizadores pontuais (ex.: ``email_not_confirmed=True``).
    """
    body: Dict[str, Any] = {"success": False, "message": message}
    if errors is not None:
        body["errors"] = errors
    if extra:
        body.update(extra)
    return jsonify(body), status
