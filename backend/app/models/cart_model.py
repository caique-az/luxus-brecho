"""
Modelo para gerenciamento de carrinhos de compras.
Cada usuário pode ter um carrinho com múltiplos itens.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId
from pymongo import ASCENDING

COLLECTION_NAME = "carts"


def get_collection(db):
    """Retorna a coleção de carrinhos."""
    return db[COLLECTION_NAME]


def ensure_indexes(db) -> None:
    """Garante que os índices necessários existam na coleção de carrinhos."""
    if db is None:
        return
    
    collection = db[COLLECTION_NAME]
    
    # Índice único por usuário (cada usuário tem apenas um carrinho)
    collection.create_index(
        [("user_id", ASCENDING)],
        unique=True,
        name="user_id_unique"
    )


def normalize_cart(cart: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza documento do carrinho para resposta da API."""
    if not cart:
        return {}
    
    normalized = {
        "id": str(cart.get("_id", "")),
        "user_id": cart.get("user_id"),
        "items": cart.get("items", []),
        "created_at": cart.get("created_at", datetime.utcnow()).isoformat() if cart.get("created_at") else None,
        "updated_at": cart.get("updated_at", datetime.utcnow()).isoformat() if cart.get("updated_at") else None,
    }
    
    return normalized


def normalize_cart_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza item do carrinho (peça única: sem quantidade)."""
    return {
        "product_id": item.get("product_id"),
        "added_at": item.get("added_at", datetime.utcnow()).isoformat() if item.get("added_at") else None,
    }


def coerce_product_id(value: Any) -> Optional[int]:
    """Converte `product_id` para int de forma segura.

    Retorna None quando o valor não é conversível — em especial um dict como
    ``{"$gt": 0}`` (operador NoSQL): sendo truthy, ele passaria por checagens do
    tipo ``if not product_id`` e iria direto ao filtro do Mongo, casando um
    produto arbitrário e sendo gravado como product_id. Rejeitar o não-int aqui
    barra essa injeção. `bool` é excluído de propósito (é subclasse de int).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def validate_cart_item(item: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Valida item do carrinho (peça única: sem quantidade).

    Exige um `product_id` inteiro válido (ver `coerce_product_id`).
    """
    if coerce_product_id(item.get("product_id")) is None:
        return False, "product_id deve ser um inteiro válido"

    return True, None
