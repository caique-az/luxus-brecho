from flask import request, jsonify, current_app
from pymongo.errors import DuplicateKeyError
from typing import Any, Dict

from ..models.category_model import (
    get_collection,
    prepare_new_category,
    validate_category,
    normalize_category,
)
from ..utils.serialization import serialize_doc
from ..utils.pagination import get_pagination_params
from ..utils.decorators import require_db


def _invalidate_categories_cache():
    """Invalida o cache de categorias após modificações."""
    try:
        from ..utils.cache import invalidate_categories_cache
        invalidate_categories_cache()
    except ImportError:
        pass  # Cache não disponível


@require_db
def list_categories():
    """Lista todas as categorias com filtros opcionais."""
    db = current_app.db
    coll = get_collection(db)

    # Filtro por status ativo
    active_only = request.args.get("active_only", "false").lower() == "true"
    page, page_size = get_pagination_params(default_size=10)

    query: Dict[str, Any] = {}
    if active_only:
        query["active"] = True

    cursor = coll.find(query).sort("name", 1)
    total = coll.count_documents(query)

    items = [
        serialize_doc(doc) for doc in cursor.skip((page - 1) * page_size).limit(page_size)
    ]

    return jsonify(
        items=items,
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    )


@require_db
def get_category(id: int):
    """Busca uma categoria específica por ID."""
    db = current_app.db
    coll = get_collection(db)

    doc = coll.find_one({"id": int(id)})
    if not doc:
        return jsonify(message="category not found"), 404
    return jsonify(serialize_doc(doc))


@require_db
def create_category():
    """Cria uma nova categoria."""
    db = current_app.db
    coll = get_collection(db)

    payload = request.get_json(silent=True) or {}
    ok, errors, doc = prepare_new_category(db, payload)
    if not ok:
        return jsonify(message="validation error", errors=errors), 400

    try:
        # Verificar se nome já existe
        existing = coll.find_one({"name": doc["name"]})
        if existing:
            return jsonify(message="category name already exists"), 409

        coll.insert_one(doc)
        _invalidate_categories_cache()  # Invalida cache após criar
    except DuplicateKeyError:
        return jsonify(message="category id already exists"), 409

    return jsonify(serialize_doc(doc)), 201


@require_db
def update_category(id: int):
    """Atualiza uma categoria existente."""
    db = current_app.db
    coll = get_collection(db)

    current = coll.find_one({"id": int(id)})
    if not current:
        return jsonify(message="category not found"), 404

    payload = request.get_json(silent=True) or {}
    # Merge parcial
    merged = serialize_doc(current)
    merged.update(payload)
    merged = normalize_category(merged)

    ok, errors = validate_category(merged)
    if not ok:
        return jsonify(message="validation error", errors=errors), 400

    # Não permitir troca de id
    merged["id"] = current["id"]

    # Verificar se nome já existe (em outra categoria)
    if "name" in payload and payload["name"] != current["name"]:
        existing = coll.find_one({"name": merged["name"], "id": {"$ne": int(id)}})
        if existing:
            return jsonify(message="category name already exists"), 409

    coll.update_one({"id": int(id)}, {"$set": merged})
    _invalidate_categories_cache()  # Invalida cache após atualizar
    updated = coll.find_one({"id": int(id)})
    return jsonify(serialize_doc(updated))


@require_db
def delete_category(id: int):
    """Deleta permanentemente uma categoria se não houver produtos associados."""
    db = current_app.db
    coll = get_collection(db)

    category = coll.find_one({"id": int(id)})
    if not category:
        return jsonify(message="categoria não encontrada"), 404

    # Verifica se há produtos usando a categoria
    category_name = category.get("name", category.get("nome", "")).strip()
    products_using_category = current_app.db.products.count_documents(
        {"categoria": category_name}
    )

    # Se não encontrou com o nome exato, tenta com capitalização padrão
    if products_using_category == 0:
        products_using_category = current_app.db.products.count_documents(
            {"categoria": category_name.title()}
        )
    if products_using_category > 0:
        return jsonify(
            message="não é possível deletar categoria com produtos associados",
            products_count=products_using_category
        ), 400

    # Delete permanente
    result = coll.delete_one({"id": int(id)})
    if result.deleted_count > 0:
        _invalidate_categories_cache()  # Invalida cache após deletar
        return jsonify(message="categoria deletada com sucesso"), 200
    return jsonify(message="erro ao deletar categoria"), 500


@require_db
def activate_category(id: int):
    """Reativa uma categoria inativa."""
    db = current_app.db
    coll = get_collection(db)

    category = coll.find_one({"id": int(id)})
    if not category:
        return jsonify(message="category not found"), 404

    coll.update_one({"id": int(id)}, {"$set": {"active": True}})
    _invalidate_categories_cache()  # Invalida cache após ativar
    updated = coll.find_one({"id": int(id)})
    return jsonify(serialize_doc(updated))


@require_db
def get_categories_summary():
    """Retorna resumo das categorias para uso em outros endpoints."""
    db = current_app.db
    coll = get_collection(db)

    # Busca apenas categorias ativas
    active_categories = list(coll.find(
        {"active": True},
        {"_id": 0, "id": 1, "name": 1, "description": 1}
    ).sort("name", 1))

    return jsonify(active_categories)
