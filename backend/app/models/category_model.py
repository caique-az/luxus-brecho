"""
Modelo e utilidades para a coleção de categorias.
- Define categorias permitidas para o brechó
- Valida payloads de categoria
- Garante validator e índices no MongoDB
"""
from typing import Dict, Any, Tuple, List
from pymongo import ASCENDING

from ..utils.counters import next_sequence

COLLECTION_NAME = "categories"
COUNTERS_COLLECTION = "counters"
COUNTER_KEY_CATEGORIES = "categories"

# Validador JSON Schema para MongoDB
MONGO_JSON_SCHEMA: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["id", "name", "description", "active"],
        "properties": {
            "id": {
                "description": "Identificador numérico único da categoria",
                "bsonType": ["int", "long"],
            },
            "name": {
                "bsonType": "string",
                "minLength": 1,
                "description": "Nome da categoria"
            },
            "description": {
                "bsonType": "string",
                "minLength": 1,
                "description": "Descrição da categoria"
            },
            "active": {
                "bsonType": "bool",
                "description": "Se a categoria está ativa"
            }
        },
        "additionalProperties": True,
    }
}


def normalize_category(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza campos da categoria (strings, boolean)."""
    data = dict(payload or {})

    # Normalização de campos
    if "nome" in data:
        data["name"] = data.pop("nome").strip()

    # Trim de strings principais
    for key in ("name", "description"):
        if key in data and isinstance(data[key], str):
            data[key] = data[key].strip()

    # Garantir que active é boolean
    if "active" in data:
        data["active"] = bool(data["active"])

    return data


def validate_category(payload: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """Valida o payload da categoria. Retorna (ok, erros)."""
    errors: Dict[str, str] = {}
    data = normalize_category(payload)

    # id é opcional neste momento (poderemos auto-gerar depois)
    if "id" in data and not isinstance(data["id"], (int,)):
        errors["id"] = "deve ser inteiro"

    # Campos obrigatórios
    required = ["name", "description"]
    for k in required:
        if data.get(k) in (None, ""):
            errors[k] = "obrigatório"

    # Validação específica do nome
    if "name" in data:
        name = data["name"]
        if len(name) < 2:
            errors["name"] = "deve ter pelo menos 2 caracteres"
        elif len(name) > 50:
            errors["name"] = "deve ter no máximo 50 caracteres"

    # Validação da descrição
    if "description" in data:
        desc = data["description"]
        if len(desc) < 5:
            errors["description"] = "deve ter pelo menos 5 caracteres"
        elif len(desc) > 200:
            errors["description"] = "deve ter no máximo 200 caracteres"

    return (len(errors) == 0), errors


def get_collection(db):
    """Retorna a coleção de categorias."""
    return db[COLLECTION_NAME]


def ensure_categories_collection(db):
    """Garante que a coleção exista com validator e índices úteis."""
    if db is None:
        return None

    try:
        if COLLECTION_NAME not in db.list_collection_names():
            db.create_collection(
                COLLECTION_NAME,
                validator=MONGO_JSON_SCHEMA,
                validationLevel="moderate",
            )
        else:
            # Atualiza validator se a coleção já existir
            db.command(
                "collMod",
                COLLECTION_NAME,
                validator=MONGO_JSON_SCHEMA,
                validationLevel="moderate",
            )
    except Exception as e:
        print(f"Aviso: não foi possível aplicar validator na coleção '{COLLECTION_NAME}': {e}")

    # Garante a coleção de counters
    try:
        ensure_counters_collection(db)
    except Exception as e:
        print(f"Aviso: não foi possível preparar counters: {e}")

    coll = db[COLLECTION_NAME]

    # Índices (create_index é idempotente: no-op quando já existe)
    try:
        coll.create_index([("id", ASCENDING)], unique=True, name="uniq_id")
    except Exception as e:
        print(f"Aviso: não foi possível criar índice único em 'id': {e}")

    try:
        coll.create_index(
            [("name", ASCENDING)], 
            unique=True, 
            name="uniq_name",
            partialFilterExpression={"name": {"$exists": True}}
        )
    except Exception as e:
        print(f"Aviso: não foi possível criar índice único em 'name': {e}")

    try:
        coll.create_index([("active", ASCENDING)], name="idx_active")
    except Exception as e:
        print(f"Aviso: não foi possível criar índice em 'active': {e}")

    return coll


def ensure_counters_collection(db):
    """Garante a coleção de contadores para categorias."""
    if db is None:
        return None
    coll = db[COUNTERS_COLLECTION]
    try:
        coll.create_index([("name", ASCENDING)], unique=True, name="uniq_name")
    except Exception as e:
        print(f"Aviso: não foi possível criar índice em counters.name: {e}")
    
    # Garante documento para categories
    try:
        coll.update_one(
            {"name": COUNTER_KEY_CATEGORIES},
            {"$setOnInsert": {"seq": 0}},
            upsert=True,
        )
    except Exception as e:
        print(f"Aviso: não foi possível inicializar contador de categorias: {e}")
    return coll


def get_next_sequence(db, name: str) -> int:
    """Obtém o próximo número sequencial para um contador nomeado."""
    return next_sequence(db, name)


def prepare_new_category(db, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
    """Normaliza, valida e atribui id sequencial se necessário.
    Retorna (ok, erros, documento_pronto).
    """
    data = normalize_category(payload)
    ok, errors = validate_category(data)
    if not ok:
        return False, errors, {}

    # Gera id se não informado (get_next_sequence faz upsert do contador)
    if "id" not in data:
        try:
            data["id"] = get_next_sequence(db, COUNTER_KEY_CATEGORIES)
        except Exception as e:
            errors["id"] = f"falha ao gerar id: {e}"
            return False, errors, {}

    # Garantir campo active
    if "active" not in data:
        data["active"] = True

    return True, {}, data


def get_active_categories_list(db) -> List[str]:
    """Retorna lista de nomes das categorias ativas."""
    if db is None:
        return []
    
    try:
        coll = get_collection(db)
        categories = coll.find({"active": True}, {"name": 1, "_id": 0})
        return [cat["name"] for cat in categories]
    except Exception as e:
        print(f"Erro ao buscar categorias ativas: {e}")
        return []

