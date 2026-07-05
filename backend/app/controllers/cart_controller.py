"""
Controller para gerenciamento de carrinhos de compras.
"""
from flask import jsonify, request, current_app
from datetime import datetime
from typing import Dict, Any
from bson import ObjectId

from ..models.cart_model import get_collection


def get_user_cart(user_id: int):
    """Obtém o carrinho do usuário."""
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    try:
        coll = get_collection(db)
        cart = coll.find_one({"user_id": user_id})
        
        if not cart:
            # Retorna carrinho vazio se não existir
            return jsonify({
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
        
        return jsonify({
            "id": str(cart.get("_id", "")),
            "user_id": user_id,
            "items": items_with_details,
            "created_at": cart.get("created_at").isoformat() if cart.get("created_at") else None,
            "updated_at": cart.get("updated_at").isoformat() if cart.get("updated_at") else None,
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao obter carrinho: {e}")
        return jsonify(message="Erro interno do servidor"), 500


def add_to_cart(user_id: int):
    """Adiciona item ao carrinho do usuário."""
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    try:
        payload = request.get_json()
        if not payload:
            return jsonify(message="Payload JSON é obrigatório"), 400

        product_id = payload.get("product_id")
        quantity = payload.get("quantity", 1)

        if not product_id:
            return jsonify(message="ID do produto é obrigatório"), 400

        # Verifica se o produto existe e está disponível
        products_coll = db["products"]
        product = products_coll.find_one({"id": product_id})
        
        if not product:
            return jsonify(message="Produto não encontrado"), 404
        
        if product.get("status") != "disponivel":
            return jsonify(message="Produto não está disponível"), 400

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

        return jsonify({
            "message": "Produto adicionado ao carrinho",
            "product_id": product_id,
            "quantity": quantity,
        }), 201

    except Exception as e:
        current_app.logger.error(f"Erro ao adicionar ao carrinho: {e}")
        return jsonify(message="Erro interno do servidor"), 500


def remove_from_cart(user_id: int):
    """Remove item do carrinho do usuário."""
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    try:
        payload = request.get_json()
        if not payload:
            return jsonify(message="Payload JSON é obrigatório"), 400

        product_id = payload.get("product_id")

        if not product_id:
            return jsonify(message="ID do produto é obrigatório"), 400

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
            return jsonify(message="Produto não encontrado no carrinho"), 404

        return jsonify({
            "message": "Produto removido do carrinho",
            "product_id": product_id,
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao remover do carrinho: {e}")
        return jsonify(message="Erro interno do servidor"), 500


def update_cart_item(user_id: int):
    """Atualiza quantidade de item no carrinho."""
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    try:
        payload = request.get_json()
        if not payload:
            return jsonify(message="Payload JSON é obrigatório"), 400

        product_id = payload.get("product_id")
        quantity = payload.get("quantity")

        if not product_id:
            return jsonify(message="ID do produto é obrigatório"), 400

        if not isinstance(quantity, int) or quantity < 1:
            return jsonify(message="Quantidade deve ser um número inteiro positivo"), 400

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
            return jsonify(message="Produto não encontrado no carrinho"), 404

        return jsonify({
            "message": "Quantidade atualizada",
            "product_id": product_id,
            "quantity": quantity,
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar carrinho: {e}")
        return jsonify(message="Erro interno do servidor"), 500


def clear_cart(user_id: int):
    """Limpa o carrinho do usuário."""
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    try:
        coll = get_collection(db)
        now = datetime.utcnow()

        result = coll.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "items": [],
                    "updated_at": now,
                }
            }
        )

        return jsonify({"message": "Carrinho limpo com sucesso"})

    except Exception as e:
        current_app.logger.error(f"Erro ao limpar carrinho: {e}")
        return jsonify(message="Erro interno do servidor"), 500


def sync_cart(user_id: int):
    """Sincroniza carrinho local com o servidor."""
    db = current_app.db
    if db is None:
        return jsonify(message="banco de dados indisponível"), 503

    try:
        payload = request.get_json()
        if not payload:
            return jsonify(message="Payload JSON é obrigatório"), 400

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

        return jsonify({
            "message": "Carrinho sincronizado",
            "items_count": len(valid_items),
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao sincronizar carrinho: {e}")
        return jsonify(message="Erro interno do servidor"), 500
