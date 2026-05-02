"""
Modelo e utilidades para a coleção de produtos.
- Define categorias permitidas dinamicamente
- Valida payloads de produto
- Garante validator e índices no MongoDB
"""
from typing import Dict, Any, Tuple
from pymongo import ASCENDING
from pymongo.collection import ReturnDocument

COLLECTION_NAME = "products"
COUNTERS_COLLECTION = "counters"
COUNTER_KEY_PRODUCTS = "products"

def get_allowed_categories(db) -> set:
    """Busca categorias ativas do cache ou banco de dados."""
    if db is None:
        return set()
    
    try:
        from ..utils.cache import get_cached_categories
        return get_cached_categories(db)
    except ImportError:
        # Fallback se cache não estiver disponível
        try:
            from .category_model import get_active_categories_list
            active_cats = get_active_categories_list(db)
            return set(active_cats)
        except Exception as e:
            print(f"Erro ao buscar categorias ativas: {e}")
            return set()


def create_dynamic_schema(db) -> Dict[str, Any]:
    """Cria schema dinâmico baseado nas categorias ativas."""
    allowed_categories = list(get_allowed_categories(db))
    
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id", "titulo", "preco", "descricao", "categoria", "imagem"],
            "properties": {
                "id": {
                    "description": "Identificador numérico único do produto",
                    "bsonType": ["int", "long"],
                },
                "titulo": {
                    "bsonType": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Título do produto (obrigatório)"
                },
                "preco": {
                    "bsonType": ["double", "int", "long"],
                    "minimum": 0,
                    "description": "Preço do produto (obrigatório)"
                },
                "descricao": {
                    "bsonType": "string",
                    "minLength": 1,
                    "maxLength": 500,
                    "description": "Descrição do produto (obrigatório)"
                },
                "categoria": {
                    "bsonType": "string",
                    "enum": allowed_categories,
                    "description": "Categoria do produto (obrigatório)"
                },
                "imagem": {
                    "bsonType": "string",
                    "minLength": 1,
                    "description": "URL da imagem do produto (obrigatório)"
                },
                "status": {
                    "bsonType": "string",
                    "enum": ["disponivel", "indisponivel", "vendido"],
                    "description": "Status do produto (obrigatório)"
                },
            },
            "additionalProperties": True,
        }
    }


def normalize_product(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza campos (categoria, strings básicas). Não altera tipos numéricos.
    """
    data = dict(payload or {})

    # Normaliza categoria para capitalização padrão
    if "categoria" in data and data["categoria"]:
        data["categoria"] = str(data["categoria"]).strip()

    # Trim de strings principais
    for key in ("titulo", "descricao", "imagem"):
        if key in data and isinstance(data[key], str):
            data[key] = data[key].strip()

    return data


def validate_product(payload: Dict[str, Any], db=None) -> Tuple[bool, Dict[str, str]]:
    """Valida o payload do produto (validação em app). Retorna (ok, erros).
    Observação: a coleção também terá validator no MongoDB.
    """
    errors: Dict[str, str] = {}
    data = normalize_product(payload)

    # id é opcional neste momento (poderemos auto-gerar depois). Se enviado, deve ser int/long.
    if "id" in data and not isinstance(data["id"], (int,)):
        errors["id"] = "deve ser um número inteiro"

    # Campos obrigatórios (status é opcional - será definido como 'disponivel' por padrão)
    required = ["titulo", "preco", "descricao", "categoria", "imagem"]
    for k in required:
        if data.get(k) in (None, ""):
            errors[k] = "campo obrigatório"

    # Validações específicas de tamanho e formato
    if "titulo" in data and data["titulo"]:
        titulo = data["titulo"]
        if len(titulo) < 2:
            errors["titulo"] = "deve ter pelo menos 2 caracteres"
        elif len(titulo) > 100:
            errors["titulo"] = "deve ter no máximo 100 caracteres"

    if "descricao" in data and data["descricao"]:
        desc = data["descricao"]
        if len(desc) < 10:
            errors["descricao"] = "deve ter pelo menos 10 caracteres"
        elif len(desc) > 500:
            errors["descricao"] = "deve ter no máximo 500 caracteres"

    # Validação da imagem obrigatória
    if "imagem" in data and data["imagem"]:
        imagem = data["imagem"]
        if len(imagem) < 5:
            errors["imagem"] = "URL da imagem deve ter pelo menos 5 caracteres"
        # Validação básica de URL
        if not (imagem.startswith("http://") or imagem.startswith("https://") or imagem.startswith("/")):
            errors["imagem"] = "deve ser uma URL válida"

    # Tipos
    if "preco" in data and not isinstance(data.get("preco"), (int, float)):
        errors["preco"] = "deve ser um número"
    elif "preco" in data and data["preco"] < 0:
        errors["preco"] = "deve ser um número positivo"

    # Categoria permitida - busca dinamicamente do banco
    cat = data.get("categoria")
    if cat:
        allowed_categories = get_allowed_categories(db)
        if cat not in allowed_categories:
            errors["categoria"] = f"deve ser uma das seguintes categorias: {', '.join(sorted(allowed_categories))}"

    # Status permitido
    status = data.get("status")
    if status:
        allowed_status = ["disponivel", "indisponivel", "vendido"]
        if status not in allowed_status:
            errors["status"] = f"deve ser um dos seguintes: {', '.join(allowed_status)}"

    return (len(errors) == 0), errors


def get_collection(db):
    return db[COLLECTION_NAME]


def ensure_products_collection(db):
    """Garante que a coleção exista com validator e índices úteis.
    - Cria coleção com validator se não existir
    - Aplica collMod para atualizar validator se já existir
    - Cria índices: uniq_id em id, idx_categoria, e índice de texto para título+descrição
    """
    if db is None:
        return None

    # Cria schema dinâmico baseado nas categorias ativas
    dynamic_schema = create_dynamic_schema(db)

    try:
        if COLLECTION_NAME not in db.list_collection_names():
            db.create_collection(
                COLLECTION_NAME,
                validator=dynamic_schema,
                validationLevel="moderate",
            )
        else:
            # Atualiza validator se a coleção já existir
            db.command(
                "collMod",
                COLLECTION_NAME,
                validator=dynamic_schema,
                validationLevel="moderate",
            )
    except Exception as e:
        print(f"Erro ao aplicar validator na coleção '{COLLECTION_NAME}': {e}")

    # Garante a coleção de counters e documento inicial para produtos
    try:
        ensure_counters_collection(db)
    except Exception as e:
        print(f"Erro ao preparar counters: {e}")

    return db[COLLECTION_NAME]


def ensure_counters_collection(db):
    """Garante a coleção de contadores e documento base para produtos."""
    if db is None:
        return None
    coll = db[COUNTERS_COLLECTION]
    try:
        coll.create_index([("name", ASCENDING)], unique=True, name="uniq_name")
    except Exception as e:
        print(f"Erro ao criar índice em counters.name: {e}")
    # Garante documento para products
    try:
        coll.update_one(
            {"name": COUNTER_KEY_PRODUCTS},
            {"$setOnInsert": {"seq": 0}},
            upsert=True,
        )
    except Exception as e:
        print(f"Erro ao inicializar contador de produtos: {e}")
    return coll


def get_next_sequence(db, name: str) -> int:
    """Obtém o próximo número sequencial para um contador nomeado."""
    doc = db[COUNTERS_COLLECTION].find_one_and_update(
        {"name": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"]) if doc and "seq" in doc else 1


def prepare_new_product(db, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
    """Normaliza, valida e atribui id sequencial se necessário.
    Retorna (ok, erros, documento_pronto).
    """
    data = normalize_product(payload)
    ok, errors = validate_product(data, db)  # Passa db para validação dinâmica
    if not ok:
        return False, errors, {}

    # Gera id se não informado
    if "id" not in data:
        try:
            ensure_counters_collection(db)
            data["id"] = get_next_sequence(db, COUNTER_KEY_PRODUCTS)
        except Exception as e:
            errors["id"] = f"falha ao gerar id: {e}"
            return False, errors, {}

    # Define status padrão se não informado
    if "status" not in data or not data["status"]:
        data["status"] = "disponivel"

    # Coerção de tipos: preço como float
    if isinstance(data.get("preco"), int):
        data["preco"] = float(data["preco"])

    return True, {}, data
