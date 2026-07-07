"""
Controller para gerenciamento de carrinhos de compras.
"""
from flask import request, current_app
from datetime import datetime

from ..models.cart_model import get_collection
from ..utils.decorators import require_db
from ..utils.responses import ok, err


@require_db
def get_user_cart(user_id: int):
    """Obtém o carrinho do usuário."""
    db = current_app.db

    coll = get_collection(db)
    cart = coll.find_one({"user_id": user_id})

    if not cart:
        # Retorna carrinho vazio se não existir
        return ok({
            "user_id": user_id,
            "items": [],
            "created_at": None,
            "updated_at": None,
        })

    # Busca informações dos produtos em uma única query (evita N+1)
    products_coll = db["products"]
    product_ids = [item.get("product_id") for item in cart.get("items", [])]

    # Uma única query para todos os produtos
    products = list(products_coll.find(
        {"id": {"$in": product_ids}},
        {"_id": 0, "id": 1, "titulo": 1, "preco": 1, "imagem": 1, "status": 1, "categoria": 1}
    ))
    products_dict = {p["id"]: p for p in products}

    items_with_details = []
    for item in cart.get("items", []):
        product = products_dict.get(item.get("product_id"))
        if product:
            items_with_details.append({
                "product_id": item.get("product_id"),
                "quantity": item.get("quantity", 1),
                "added_at": item.get("added_at").isoformat() if item.get("added_at") else None,
                "product": {
                    "id": product.get("id"),
                    "titulo": product.get("titulo"),
                    "preco": product.get("preco"),
                    "imagem": product.get("imagem"),
                    "status": product.get("status"),
                    "categoria": product.get("categoria"),
                }
            })

    return ok({
        "id": str(cart.get("_id", "")),
        "user_id": user_id,
        "items": items_with_details,
        "created_at": cart.get("created_at").isoformat() if cart.get("created_at") else None,
        "updated_at": cart.get("updated_at").isoformat() if cart.get("updated_at") else None,
    })


@require_db
def add_to_cart(user_id: int):
    """Adiciona item ao carrinho do usuário."""
    db = current_app.db

    payload = request.get_json()
    if not payload:
        return err("Payload JSON é obrigatório")

    product_id = payload.get("product_id")
    quantity = payload.get("quantity", 1)

    if not product_id:
        return err("ID do produto é obrigatório")

    # Verifica se o produto existe e está disponível
    products_coll = db["products"]
    product = products_coll.find_one({"id": product_id})

    if not product:
        return err("Produto não encontrado", 404)

    if product.get("status") != "disponivel":
        return err("Produto não está disponível")

    coll = get_collection(db)
    now = datetime.utcnow()

    # Verifica se o carrinho já existe
    cart = coll.find_one({"user_id": user_id})

    if cart:
        # Verifica se o produto já está no carrinho
        existing_item = None
        for item in cart.get("items", []):
            if item.get("product_id") == product_id:
                existing_item = item
                break

        if existing_item:
            # Atualiza quantidade
            coll.update_one(
                {"user_id": user_id, "items.product_id": product_id},
                {
                    "$set": {
                        "items.$.quantity": existing_item.get("quantity", 1) + quantity,
                        "updated_at": now,
                    }
                }
            )
        else:
            # Adiciona novo item
            coll.update_one(
                {"user_id": user_id},
                {
                    "$push": {
                        "items": {
                            "product_id": product_id,
                            "quantity": quantity,
                            "added_at": now,
                        }
                    },
                    "$set": {"updated_at": now}
                }
            )
    else:
        # Cria novo carrinho
        coll.insert_one({
            "user_id": user_id,
            "items": [{
                "product_id": product_id,
                "quantity": quantity,
                "added_at": now,
            }],
            "created_at": now,
            "updated_at": now,
        })

    return ok(
        message="Produto adicionado ao carrinho",
        status=201,
        product_id=product_id,
        quantity=quantity,
    )


@require_db
def remove_from_cart(user_id: int):
    """Remove item do carrinho do usuário."""
    db = current_app.db

    payload = request.get_json()
    if not payload:
        return err("Payload JSON é obrigatório")

    product_id = payload.get("product_id")

    if not product_id:
        return err("ID do produto é obrigatório")

    coll = get_collection(db)
    now = datetime.utcnow()

    result = coll.update_one(
        {"user_id": user_id},
        {
            "$pull": {"items": {"product_id": product_id}},
            "$set": {"updated_at": now}
        }
    )

    if result.modified_count == 0:
        return err("Produto não encontrado no carrinho", 404)

    return ok(message="Produto removido do carrinho", product_id=product_id)


@require_db
def update_cart_item(user_id: int):
    """Atualiza quantidade de item no carrinho."""
    db = current_app.db

    payload = request.get_json()
    if not payload:
        return err("Payload JSON é obrigatório")

    product_id = payload.get("product_id")
    quantity = payload.get("quantity")

    if not product_id:
        return err("ID do produto é obrigatório")

    if not isinstance(quantity, int) or quantity < 1:
        return err("Quantidade deve ser um número inteiro positivo")

    coll = get_collection(db)
    now = datetime.utcnow()

    result = coll.update_one(
        {"user_id": user_id, "items.product_id": product_id},
        {
            "$set": {
                "items.$.quantity": quantity,
                "updated_at": now,
            }
        }
    )

    if result.modified_count == 0:
        return err("Produto não encontrado no carrinho", 404)

    return ok(message="Quantidade atualizada", product_id=product_id, quantity=quantity)


@require_db
def clear_cart(user_id: int):
    """Limpa o carrinho do usuário."""
    db = current_app.db

    coll = get_collection(db)
    now = datetime.utcnow()

    coll.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "items": [],
                "updated_at": now,
            }
        }
    )

    return ok(message="Carrinho limpo com sucesso")


@require_db
def sync_cart(user_id: int):
    """Sincroniza carrinho local com o servidor."""
    db = current_app.db

    payload = request.get_json()
    if not payload:
        return err("Payload JSON é obrigatório")

    items = payload.get("items", [])

    coll = get_collection(db)
    products_coll = db["products"]
    now = datetime.utcnow()

    # Busca todos os produtos de uma vez (evita N+1)
    product_ids = [item.get("product_id") for item in items if item.get("product_id")]
    products = list(products_coll.find(
        {"id": {"$in": product_ids}, "status": "disponivel"},
        {"_id": 0, "id": 1}
    ))
    available_product_ids = {p["id"] for p in products}

    # Filtra apenas itens com produtos disponíveis
    valid_items = [
        {
            "product_id": item.get("product_id"),
            "quantity": item.get("quantity", 1),
            "added_at": now,
        }
        for item in items
        if item.get("product_id") in available_product_ids
    ]

    # Atualiza ou cria carrinho
    coll.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "items": valid_items,
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            }
        },
        upsert=True
    )

    return ok(message="Carrinho sincronizado", items_count=len(valid_items))
