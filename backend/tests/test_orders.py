"""
Testes para rotas de pedidos.
Exigem JWT: listar/criar/ver/cancelar como dono (id=1); atualizar status é admin.
"""
import pytest
import json
from datetime import datetime


class TestOrdersList:
    """Testes para listagem de pedidos."""

    def test_list_orders_empty(self, client, mock_db, auth_headers):
        """Testa listagem quando não há pedidos."""
        response = client.get("/api/orders/user/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert "orders" in data
        assert data["orders"] == []

    def test_list_orders_with_data(self, client, mock_db, sample_order, auth_headers):
        """Testa listagem com pedidos cadastrados."""
        mock_db["orders"].insert_one(sample_order)

        response = client.get(f"/api/orders/user/{sample_order['user_id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert "orders" in data
        assert len(data["orders"]) >= 1

    def test_list_orders_requires_auth(self, client, mock_db):
        """Sem token, GET /orders/user/<id> retorna 401."""
        response = client.get("/api/orders/user/1")
        assert response.status_code == 401

    def test_list_orders_other_user_forbidden(self, client, mock_db, auth_headers):
        """Cliente id=1 não pode listar pedidos de outro usuário."""
        response = client.get("/api/orders/user/2", headers=auth_headers)
        assert response.status_code == 403


class TestOrderCreate:
    """Testes para criação de pedidos."""

    def test_create_order_success(self, client, mock_db, sample_product, auth_headers):
        """Testa criação de pedido com sucesso."""
        mock_db["products"].insert_one(sample_product)
        mock_db["counters"].insert_one({"_id": "orders", "seq": 0})
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

        order_data = {
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                }
            ],
            "endereco": {
                "rua": "Rua Teste",
                "numero": "123",
                "complemento": "Apto 1",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "01234-567",
            }
        }

        response = client.post(
            "/api/orders/user/1",
            data=json.dumps(order_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]
        data = response.get_json()

        assert "order" in data or "id" in data

    def test_create_order_missing_items(self, client, mock_db, auth_headers):
        """Testa criação sem itens."""
        order_data = {
            "items": [],
            "endereco": {
                "rua": "Rua Teste",
                "numero": "123",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "01234-567",
            }
        }

        response = client.post(
            "/api/orders/user/1",
            data=json.dumps(order_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_create_order_missing_address(self, client, mock_db, sample_product, auth_headers):
        """Testa criação sem endereço."""
        mock_db["products"].insert_one(sample_product)

        order_data = {
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                }
            ],
        }

        response = client.post(
            "/api/orders/user/1",
            data=json.dumps(order_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_create_order_incomplete_address(self, client, mock_db, sample_product, auth_headers):
        """Testa criação com endereço incompleto."""
        mock_db["products"].insert_one(sample_product)

        order_data = {
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                }
            ],
            "endereco": {
                "rua": "Rua Teste",
                # Faltam campos obrigatórios
            }
        }

        response = client.post(
            "/api/orders/user/1",
            data=json.dumps(order_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestOrderGet:
    """Testes para obter pedido específico."""

    def test_get_order_by_id(self, client, mock_db, sample_order, auth_headers):
        """Testa obter pedido por ID (dono)."""
        mock_db["orders"].insert_one(sample_order)

        response = client.get(f"/api/orders/{sample_order['id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data["id"] == sample_order["id"]

    def test_get_order_not_found(self, client, mock_db, auth_headers):
        """Testa obter pedido inexistente."""
        response = client.get("/api/orders/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_get_order_other_user_forbidden(self, client, mock_db, sample_order, auth_headers):
        """Cliente id=1 não pode ver pedido de outro usuário."""
        sample_order["user_id"] = 2
        mock_db["orders"].insert_one(sample_order)

        response = client.get(f"/api/orders/{sample_order['id']}", headers=auth_headers)

        assert response.status_code == 403


class TestOrderStatusUpdate:
    """Testes para atualização de status (admin)."""

    def test_update_status_success(self, client, mock_db, sample_order, admin_headers):
        """Testa atualização de status com sucesso."""
        mock_db["orders"].insert_one(sample_order)

        status_data = {
            "status": "em_preparacao",
        }

        response = client.put(
            f"/api/orders/{sample_order['id']}/status",
            data=json.dumps(status_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 200

    def test_update_status_invalid(self, client, mock_db, sample_order, admin_headers):
        """Testa atualização com status inválido."""
        mock_db["orders"].insert_one(sample_order)

        status_data = {
            "status": "status_invalido",
        }

        response = client.put(
            f"/api/orders/{sample_order['id']}/status",
            data=json.dumps(status_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 400

    def test_update_status_not_found(self, client, mock_db, admin_headers):
        """Testa atualização de pedido inexistente."""
        status_data = {
            "status": "em_preparacao",
        }

        response = client.put(
            "/api/orders/99999/status",
            data=json.dumps(status_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 404

    def test_update_status_forbidden_for_client(self, client, mock_db, sample_order, auth_headers):
        """Cliente não pode atualizar status (só admin)."""
        mock_db["orders"].insert_one(sample_order)

        response = client.put(
            f"/api/orders/{sample_order['id']}/status",
            data=json.dumps({"status": "em_preparacao"}),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestOrderCancel:
    """Testes para cancelamento de pedidos."""

    def test_cancel_order_success(self, client, mock_db, sample_order, sample_product, auth_headers):
        """Testa cancelamento de pedido com sucesso (dono)."""
        mock_db["orders"].insert_one(sample_order)
        mock_db["products"].insert_one(sample_product)

        response = client.post(f"/api/orders/{sample_order['id']}/cancel", headers=auth_headers)

        assert response.status_code == 200

    def test_cancel_order_not_found(self, client, mock_db, auth_headers):
        """Testa cancelamento de pedido inexistente."""
        response = client.post("/api/orders/99999/cancel", headers=auth_headers)

        assert response.status_code == 404

    def test_cancel_order_already_cancelled(self, client, mock_db, sample_order, auth_headers):
        """Testa cancelamento de pedido já cancelado."""
        sample_order["status"] = "cancelado"
        mock_db["orders"].insert_one(sample_order)

        response = client.post(f"/api/orders/{sample_order['id']}/cancel", headers=auth_headers)

        assert response.status_code == 400

    def test_cancel_order_already_shipped(self, client, mock_db, sample_order, auth_headers):
        """Testa cancelamento de pedido já enviado."""
        sample_order["status"] = "enviado"
        mock_db["orders"].insert_one(sample_order)

        response = client.post(f"/api/orders/{sample_order['id']}/cancel", headers=auth_headers)

        assert response.status_code == 400


class TestOrderFlow:
    """Testes de fluxo completo de pedido."""

    def test_complete_order_flow(self, client, mock_db, sample_product, auth_headers, admin_headers):
        """Testa fluxo completo: cliente cria -> admin atualiza status -> entregar."""
        mock_db["products"].insert_one(sample_product)
        mock_db["counters"].insert_one({"_id": "orders", "seq": 0})
        mock_db["carts"].insert_one({
            "user_id": 1,
            "items": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        # 1. Criar pedido (cliente dono)
        order_data = {
            "items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 1,
                }
            ],
            "endereco": {
                "rua": "Rua Teste",
                "numero": "123",
                "complemento": "",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "01234-567",
            }
        }

        response = client.post(
            "/api/orders/user/1",
            data=json.dumps(order_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]
        data = response.get_json()
        order_id = data.get("order", {}).get("id") or data.get("id")

        if order_id:
            # 2. Atualizar para em preparação (admin)
            response = client.put(
                f"/api/orders/{order_id}/status",
                data=json.dumps({"status": "em_preparacao"}),
                content_type="application/json",
                headers=admin_headers,
            )
            assert response.status_code == 200

            # 3. Atualizar para enviado (admin)
            response = client.put(
                f"/api/orders/{order_id}/status",
                data=json.dumps({"status": "enviado"}),
                content_type="application/json",
                headers=admin_headers,
            )
            assert response.status_code == 200

            # 4. Atualizar para entregue (admin)
            response = client.put(
                f"/api/orders/{order_id}/status",
                data=json.dumps({"status": "entregue"}),
                content_type="application/json",
                headers=admin_headers,
            )
            assert response.status_code == 200
