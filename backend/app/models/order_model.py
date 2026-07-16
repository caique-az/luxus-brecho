"""
Modelo para gerenciamento de pedidos.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pymongo import ASCENDING, DESCENDING

from ..utils.counters import next_sequence

COLLECTION_NAME = "orders"
COUNTER_KEY = "orders"

# Status possíveis do pedido
ORDER_STATUS = [
    "pendente",
    "confirmado",
    "em_preparacao",
    "enviado",
    "entregue",
    "cancelado"
]


def get_collection(db):
    """Retorna a coleção de pedidos."""
    return db[COLLECTION_NAME]


def ensure_indexes(db) -> None:
    """Garante que os índices necessários existam na coleção de pedidos."""
    if db is None:
        return
    
    collection = db[COLLECTION_NAME]
    
    # Índice único por ID do pedido
    collection.create_index(
        [("id", ASCENDING)],
        unique=True,
        name="order_id_unique"
    )
    
    # Índice composto para listagem de pedidos por usuário (ordenado por data)
    collection.create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)],
        name="user_orders_by_date"
    )
    
    # Índice por status (útil para filtros administrativos)
    collection.create_index(
        [("status", ASCENDING)],
        name="order_status"
    )


def get_next_id(db) -> int:
    """Gera próximo ID sequencial para pedidos."""
    return next_sequence(db, COUNTER_KEY)


def normalize_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza documento do pedido para resposta da API."""
    if not order:
        return {}
    
    return {
        "id": order.get("id"),
        "user_id": order.get("user_id"),
        "items": order.get("items", []),
        "total": order.get("total", 0),
        "status": order.get("status", "pendente"),
        "endereco": order.get("endereco", {}),
        "created_at": order.get("created_at").isoformat() if order.get("created_at") else None,
        "updated_at": order.get("updated_at").isoformat() if order.get("updated_at") else None,
    }


def validate_order(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Valida dados do pedido."""
    if not payload.get("user_id"):
        return False, "ID do usuário é obrigatório"
    
    if not payload.get("items") or len(payload.get("items", [])) == 0:
        return False, "Pedido deve ter pelo menos um item"
    
    if not payload.get("endereco"):
        return False, "Endereço é obrigatório"
    
    endereco = payload.get("endereco", {})
    required_fields = ["rua", "numero", "bairro", "cidade", "estado", "cep"]
    for field in required_fields:
        if not endereco.get(field):
            return False, f"Campo '{field}' do endereço é obrigatório"
    
    return True, None
