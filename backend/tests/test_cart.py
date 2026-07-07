"""
Testes para rotas de carrinho.
"""
import pytest
import json
from datetime import datetime


class TestCartGet:
    """Testes para obter carrinho."""
    
    def test_get_cart_empty(self, client, mock_db, user_headers):
        """Testa obter carrinho vazio."""
        response = client.get("/api/cart/1", headers=user_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert "items" in data
        assert data["items"] == [] or len(data["items"]) == 0
    
    def test_get_cart_with_items(self, client, mock_db, sample_product, user_headers):
        """Testa obter carrinho com itens."""
        mock_db["products"].insert_one(sample_product)
        mock_db["carts"].insert_one({
            "user_id": 1,
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                    "added_at": datetime.utcnow(),
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        response = client.get("/api/cart/1", headers=user_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert "items" in data
        assert len(data["items"]) == 1


class TestCartAdd:
    """Testes para adicionar ao carrinho."""
    
    def test_add_to_cart_success(self, client, mock_db, sample_product, user_headers):
        """Testa adicionar produto ao carrinho."""
        mock_db["products"].insert_one(sample_product)

        cart_data = {
            "product_id": sample_product["id"],
            "quantity": 1,
        }

        response = client.post(
            "/api/cart/1/add",
            data=json.dumps(cart_data),
            content_type="application/json",
            headers=user_headers
        )

        assert response.status_code in [200, 201]
    
    def test_add_to_cart_product_not_found(self, client, mock_db, user_headers):
        """Testa adicionar produto inexistente."""
        cart_data = {
            "product_id": 99999,
            "quantity": 1,
        }

        response = client.post(
            "/api/cart/1/add",
            data=json.dumps(cart_data),
            content_type="application/json",
            headers=user_headers
        )

        assert response.status_code == 404
    
    def test_add_to_cart_unavailable_product(self, client, mock_db, sample_product, user_headers):
        """Testa adicionar produto indisponível."""
        sample_product["status"] = "vendido"
        mock_db["products"].insert_one(sample_product)

        cart_data = {
            "product_id": sample_product["id"],
            "quantity": 1,
        }

        response = client.post(
            "/api/cart/1/add",
            data=json.dumps(cart_data),
            content_type="application/json",
            headers=user_headers
        )

        assert response.status_code == 400
    
    def test_add_to_cart_missing_product_id(self, client, mock_db, user_headers):
        """Testa adicionar sem product_id."""
        cart_data = {
            "quantity": 1,
        }

        response = client.post(
            "/api/cart/1/add",
            data=json.dumps(cart_data),
            content_type="application/json",
            headers=user_headers
        )

        assert response.status_code == 400


class TestCartRemove:
    """Testes para remover do carrinho."""
    
    def test_remove_from_cart_success(self, client, mock_db, sample_product, user_headers):
        """Testa remover produto do carrinho."""
        mock_db["products"].insert_one(sample_product)
        mock_db["carts"].insert_one({
            "user_id": 1,
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                    "added_at": datetime.utcnow(),
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        remove_data = {
            "product_id": sample_product["id"],
        }

        response = client.post(
            "/api/cart/1/remove",
            data=json.dumps(remove_data),
            content_type="application/json",
            headers=user_headers
        )

        assert response.status_code == 200
    
    def test_remove_from_cart_not_found(self, client, mock_db, user_headers):
        """Testa remover produto que não está no carrinho."""
        mock_db["carts"].insert_one({
            "user_id": 1,
            "items": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        remove_data = {
            "product_id": 99999,
        }

        response = client.post(
            "/api/cart/1/remove",
            data=json.dumps(remove_data),
            content_type="application/json",
            headers=user_headers
        )

        # API pode retornar 200 mesmo se item não existir (idempotente)
        assert response.status_code in [200, 404]


class TestCartSinglePiece:
    """Testes da regra de peça única (sem quantidade; re-adicionar é idempotente)."""

    def test_readd_e_idempotente(self, client, mock_db, sample_product, user_headers):
        """Re-adicionar o mesmo produto não duplica nem cria quantidade."""
        mock_db["products"].insert_one(sample_product)
        mock_db["carts"].insert_one({
            "user_id": 1,
            "items": [{"product_id": sample_product["id"], "added_at": datetime.utcnow()}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        add_data = {"product_id": sample_product["id"]}
        response = client.post(
            "/api/cart/1/add",
            data=json.dumps(add_data),
            content_type="application/json",
            headers=user_headers,
        )

        assert response.status_code == 200  # idempotente: já estava no carrinho
        cart = mock_db["carts"].find_one({"user_id": 1})
        assert len(cart["items"]) == 1  # não duplicou
        assert "quantity" not in cart["items"][0]  # sem quantidade

    def test_update_route_nao_existe_mais(self, client, mock_db, user_headers):
        """A rota de atualizar quantidade foi removida (peça única)."""
        response = client.put(
            "/api/cart/1/update",
            data=json.dumps({"product_id": 1, "quantity": 3}),
            content_type="application/json",
            headers=user_headers,
        )
        assert response.status_code == 404


class TestCartClear:
    """Testes para limpar carrinho."""
    
    def test_clear_cart_success(self, client, mock_db, sample_product, user_headers):
        """Testa limpar carrinho."""
        mock_db["products"].insert_one(sample_product)
        mock_db["carts"].insert_one({
            "user_id": 1,
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                    "added_at": datetime.utcnow(),
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        response = client.delete("/api/cart/1/clear", headers=user_headers)

        assert response.status_code == 200

    def test_clear_empty_cart(self, client, mock_db, user_headers):
        """Testa limpar carrinho já vazio."""
        response = client.delete("/api/cart/1/clear", headers=user_headers)

        assert response.status_code == 200


class TestCartSync:
    """Testes para sincronização de carrinho."""
    
    def test_sync_cart_success(self, client, mock_db, sample_product, user_headers):
        """Testa sincronizar carrinho."""
        mock_db["products"].insert_one(sample_product)

        sync_data = {
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                }
            ]
        }

        response = client.post(
            "/api/cart/1/sync",
            data=json.dumps(sync_data),
            content_type="application/json",
            headers=user_headers
        )

        assert response.status_code == 200
    
    def test_sync_cart_filters_unavailable(self, client, mock_db, sample_product, user_headers):
        """Testa que sync filtra produtos indisponíveis."""
        sample_product["status"] = "vendido"
        mock_db["products"].insert_one(sample_product)

        sync_data = {
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                }
            ]
        }

        response = client.post(
            "/api/cart/1/sync",
            data=json.dumps(sync_data),
            content_type="application/json",
            headers=user_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        
        # Deve ter filtrado o produto indisponível
        assert data.get("items_count", 0) == 0
