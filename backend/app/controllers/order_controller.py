"""
Controller para gerenciamento de pedidos.
"""
from flask import jsonify, request, current_app
from datetime import datetime
from typing import Dict, Any

from ..models.order_model import (
    get_collection,
    get_next_id,
    normalize_order,
    validate_order,
    ORDER_STATUS,
)
from ..models.cart_model import get_collection as get_cart_collection
from ..utils.pagination import get_pagination_params
from ..utils.decorators import require_db


@require_db
def get_user_orders(user_id: int):
    """Obtém todos os pedidos do usuário com paginação."""
    db = current_app.db

    # Parâmetros de paginação
    page, page_size = get_pagination_params()

    coll = get_collection(db)

    # Query com filtro por usuário
    query = {"user_id": user_id}

    # Contagem total
    total = coll.count_documents(query)

    # Busca com paginação
    skip = (page - 1) * page_size
    orders = list(coll.find(query).sort("created_at", -1).skip(skip).limit(page_size))

    return jsonify({
        "orders": [normalize_order(order) for order in orders],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
        }
    })


@require_db
def get_order_by_id(order_id: int):
    """Obtém um pedido específico pelo ID."""
    db = current_app.db

    coll = get_collection(db)
    order = coll.find_one({"id": order_id})

    if not order:
        return jsonify(message="Pedido não encontrado"), 404

    return jsonify(normalize_order(order))


@require_db
def create_order(user_id: int):
    """Cria um novo pedido com transação para garantir consistência."""
    db = current_app.db

    payload = request.get_json()
    if not payload:
        return jsonify(message="Payload JSON é obrigatório"), 400

    payload["user_id"] = user_id

    # Valida dados do pedido
    is_valid, error_msg = validate_order(payload)
    if not is_valid:
        return jsonify(message=error_msg), 400

    # Busca informações dos produtos numa única query
    products_coll = db["products"]
    items = payload.get("items", [])
    products_by_id = {
        p["id"]: p
        for p in products_coll.find(
            {"id": {"$in": [item.get("product_id") for item in items]}},
            {"_id": 0, "id": 1, "status": 1, "preco": 1, "titulo": 1, "imagem": 1},
        )
    }

    items_with_details = []
    total = 0
    product_ids_to_update = []

    for item in items:
        product = products_by_id.get(item.get("product_id"))
        if product:
            if product.get("status") != "disponivel":
                return jsonify(message=f"Produto '{product.get('titulo')}' não está disponível"), 400

            item_total = (product.get("preco", 0)) * item.get("quantity", 1)
            items_with_details.append({
                "product_id": item.get("product_id"),
                "quantity": item.get("quantity", 1),
                "preco_unitario": product.get("preco", 0),
                "preco_total": item_total,
                "titulo": product.get("titulo"),
                "imagem": product.get("imagem"),
            })
            total += item_total
            product_ids_to_update.append(item.get("product_id"))

    coll = get_collection(db)
    cart_coll = get_cart_collection(db)
    now = datetime.utcnow()

    order_id = get_next_id(db)

    order = {
        "id": order_id,
        "user_id": user_id,
        "items": items_with_details,
        "total": total,
        "status": "confirmado",
        "endereco": payload.get("endereco"),
        "created_at": now,
        "updated_at": now,
    }

    # Tenta usar transação se disponível (MongoDB 4.0+)
    mongo_client = current_app.mongo
    if mongo_client and hasattr(mongo_client, 'start_session'):
        try:
            with mongo_client.start_session() as session:
                with session.start_transaction():
                    # Insere pedido
                    coll.insert_one(order, session=session)

                    # Atualiza status dos produtos para vendido
                    if product_ids_to_update:
                        products_coll.update_many(
                            {"id": {"$in": product_ids_to_update}},
                            {"$set": {"status": "vendido"}},
                            session=session
                        )

                    # Limpa o carrinho do usuário
                    cart_coll.update_one(
                        {"user_id": user_id},
                        {"$set": {"items": [], "updated_at": now}},
                        session=session
                    )

            current_app.logger.info(f"Pedido {order_id} criado com transação")
        except Exception as tx_error:
            current_app.logger.warning(f"Transação não suportada, usando operações sequenciais: {tx_error}")
            # Fallback para operações sem transação
            _create_order_without_transaction(coll, products_coll, cart_coll, order, product_ids_to_update, user_id, now)
    else:
        # Sem suporte a transações
        _create_order_without_transaction(coll, products_coll, cart_coll, order, product_ids_to_update, user_id, now)

    return jsonify({
        "message": "Pedido criado com sucesso",
        "order": normalize_order(order),
    }), 201


def _create_order_without_transaction(coll, products_coll, cart_coll, order, product_ids, user_id, now):
    """Cria pedido sem transação (fallback)."""
    coll.insert_one(order)

    if product_ids:
        products_coll.update_many(
            {"id": {"$in": product_ids}},
            {"$set": {"status": "vendido"}}
        )

    cart_coll.update_one(
        {"user_id": user_id},
        {"$set": {"items": [], "updated_at": now}}
    )


@require_db
def update_order_status(order_id: int):
    """Atualiza o status de um pedido."""
    db = current_app.db

    payload = request.get_json()
    if not payload:
        return jsonify(message="Payload JSON é obrigatório"), 400

    new_status = payload.get("status")
    if not new_status or new_status not in ORDER_STATUS:
        return jsonify(message=f"Status inválido. Valores permitidos: {', '.join(ORDER_STATUS)}"), 400

    coll = get_collection(db)
    now = datetime.utcnow()

    result = coll.update_one(
        {"id": order_id},
        {"$set": {"status": new_status, "updated_at": now}}
    )

    if result.matched_count == 0:
        return jsonify(message="Pedido não encontrado"), 404

    return jsonify({
        "message": "Status atualizado com sucesso",
        "order_id": order_id,
        "status": new_status,
    })


@require_db
def cancel_order(order_id: int):
    """Cancela um pedido."""
    db = current_app.db

    coll = get_collection(db)
    products_coll = db["products"]
    now = datetime.utcnow()

    # Busca o pedido
    order = coll.find_one({"id": order_id})
    if not order:
        return jsonify(message="Pedido não encontrado"), 404

    if order.get("status") == "cancelado":
        return jsonify(message="Pedido já está cancelado"), 400

    if order.get("status") in ["enviado", "entregue"]:
        return jsonify(message="Não é possível cancelar pedido já enviado ou entregue"), 400

    # Restaura status dos produtos para disponível
    product_ids = [item.get("product_id") for item in order.get("items", [])]
    if product_ids:
        products_coll.update_many(
            {"id": {"$in": product_ids}},
            {"$set": {"status": "disponivel"}}
        )

    # Atualiza status do pedido
    coll.update_one(
        {"id": order_id},
        {"$set": {"status": "cancelado", "updated_at": now}}
    )

    return jsonify({
        "message": "Pedido cancelado com sucesso",
        "order_id": order_id,
    })
