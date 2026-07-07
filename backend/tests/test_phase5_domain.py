"""
Testes da Fase 5 do plano (regras de domínio / correção):

  - #11 peça única: o pedido não multiplica por `quantity` e deduplica o produto;
  - #12 pedido com item inválido / total zero é rejeitado (não persiste 201);
  - #13 injeção de operador NoSQL: `product_id` não-int é rejeitado com 400.
"""
import json

import pytest


ADDRESS = {
    "rua": "Rua Teste",
    "numero": "123",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "cep": "01234-567",
}


def _post(client, url, body, headers=None):
    return client.post(
        url, data=json.dumps(body), content_type="application/json", headers=headers
    )


# --------------------------------------------------------------------------- #
# #13 — Injeção de operador NoSQL no carrinho
# --------------------------------------------------------------------------- #
class TestCartNoSQLInjection:
    def test_add_rejeita_operador_mongo(self, client, mock_db, sample_product, user_headers):
        mock_db["products"].insert_one(sample_product)
        # {"$gt": 0} é truthy e casaria um produto arbitrário no filtro do Mongo.
        resp = _post(client, "/api/cart/1/add", {"product_id": {"$gt": 0}}, user_headers)
        assert resp.status_code == 400

    def test_add_rejeita_product_id_nao_numerico(self, client, mock_db, user_headers):
        resp = _post(client, "/api/cart/1/add", {"product_id": "abc"}, user_headers)
        assert resp.status_code == 400

    def test_sync_ignora_operador_mongo(self, client, mock_db, sample_product, user_headers):
        mock_db["products"].insert_one(sample_product)
        resp = _post(
            client, "/api/cart/1/sync",
            {"items": [{"product_id": {"$gt": 0}}, {"product_id": sample_product["id"]}]},
            user_headers,
        )
        assert resp.status_code == 200
        # o operador foi descartado; só o produto válido entrou
        assert resp.get_json().get("items_count") == 1


# --------------------------------------------------------------------------- #
# #11 — Peça única: sem multiplicação por quantity, com dedupe
# --------------------------------------------------------------------------- #
class TestOrderSinglePiece:
    def test_quantity_no_payload_e_ignorada(self, client, mock_db, sample_product, user_headers):
        mock_db["products"].insert_one(sample_product)
        body = {"items": [{"product_id": sample_product["id"], "quantity": 3}], "endereco": ADDRESS}

        resp = _post(client, "/api/orders/user/1", body, user_headers)
        assert resp.status_code == 201

        order = resp.get_json()["order"]
        # total é o preço unitário, não preço × 3
        assert order["total"] == sample_product["preco"]
        assert len(order["items"]) == 1
        assert "quantity" not in order["items"][0]

    def test_produto_repetido_e_deduplicado(self, client, mock_db, sample_product, user_headers):
        mock_db["products"].insert_one(sample_product)
        body = {
            "items": [
                {"product_id": sample_product["id"]},
                {"product_id": sample_product["id"]},
            ],
            "endereco": ADDRESS,
        }

        resp = _post(client, "/api/orders/user/1", body, user_headers)
        assert resp.status_code == 201

        order = resp.get_json()["order"]
        assert len(order["items"]) == 1
        assert order["total"] == sample_product["preco"]


# --------------------------------------------------------------------------- #
# #12 — Pedido com itens inválidos / total zero é rejeitado
# --------------------------------------------------------------------------- #
class TestOrderRejectsInvalid:
    def test_todos_ids_inexistentes_nao_cria_pedido(self, client, mock_db, user_headers):
        body = {"items": [{"product_id": 999999}], "endereco": ADDRESS}
        resp = _post(client, "/api/orders/user/1", body, user_headers)

        assert resp.status_code == 404
        # nenhum pedido total 0 foi persistido
        assert mock_db["orders"].count_documents({}) == 0

    def test_id_inexistente_misturado_rejeita_tudo(self, client, mock_db, sample_product, user_headers):
        mock_db["products"].insert_one(sample_product)
        body = {
            "items": [
                {"product_id": sample_product["id"]},
                {"product_id": 999999},
            ],
            "endereco": ADDRESS,
        }
        resp = _post(client, "/api/orders/user/1", body, user_headers)

        assert resp.status_code == 404
        assert mock_db["orders"].count_documents({}) == 0

    def test_operador_mongo_no_pedido_retorna_400(self, client, mock_db, sample_product, user_headers):
        mock_db["products"].insert_one(sample_product)
        body = {"items": [{"product_id": {"$gt": 0}}], "endereco": ADDRESS}
        resp = _post(client, "/api/orders/user/1", body, user_headers)

        assert resp.status_code == 400
        assert mock_db["orders"].count_documents({}) == 0
