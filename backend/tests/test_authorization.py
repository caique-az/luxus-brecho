"""
Testes de autorização da Fase 2 (fechar rotas abertas / IDOR).

Não validam o caminho feliz (isso está nos testes de cada recurso), mas sim que
as rotas agora NEGAM acesso indevido:
  - anônimo (sem token) -> 401;
  - usuário logado tentando acessar recurso de outro -> 403;
  - operação de admin feita por cliente comum -> 403.
"""
import json

import pytest


def _json_post(client, url, body, headers=None):
    return client.post(
        url, data=json.dumps(body), content_type="application/json", headers=headers
    )


# --------------------------------------------------------------------------- #
# Carrinho — @owner_or_admin_required('user_id')  [#2]
# --------------------------------------------------------------------------- #
class TestCartAuthorization:
    def test_sem_token_retorna_401(self, client, mock_db):
        assert client.get("/api/cart/1").status_code == 401

    def test_outro_usuario_retorna_403(self, client, mock_db, auth_headers):
        outro = auth_headers(user_id=2)
        assert client.get("/api/cart/1", headers=outro).status_code == 403

    def test_mutacao_de_outro_usuario_retorna_403(self, client, mock_db, auth_headers):
        outro = auth_headers(user_id=2)
        resp = _json_post(client, "/api/cart/1/add", {"product_id": 1}, outro)
        assert resp.status_code == 403

    def test_dono_acessa(self, client, mock_db, user_headers):
        assert client.get("/api/cart/1", headers=user_headers).status_code == 200

    def test_admin_acessa(self, client, mock_db, admin_headers):
        assert client.get("/api/cart/1", headers=admin_headers).status_code == 200


# --------------------------------------------------------------------------- #
# Pedidos — posse nas rotas de usuário, admin no status  [#3]
# --------------------------------------------------------------------------- #
class TestOrdersAuthorization:
    def test_lista_sem_token_retorna_401(self, client, mock_db):
        assert client.get("/api/orders/user/1").status_code == 401

    def test_lista_de_outro_usuario_retorna_403(self, client, mock_db, auth_headers):
        outro = auth_headers(user_id=2)
        assert client.get("/api/orders/user/1", headers=outro).status_code == 403

    def test_criar_para_outro_usuario_retorna_403(self, client, mock_db, auth_headers):
        outro = auth_headers(user_id=2)
        resp = _json_post(client, "/api/orders/user/1", {"items": []}, outro)
        assert resp.status_code == 403

    def test_obter_pedido_alheio_retorna_403(self, client, mock_db, sample_order, auth_headers):
        mock_db["orders"].insert_one(sample_order)  # user_id=1
        outro = auth_headers(user_id=2)
        resp = client.get(f"/api/orders/{sample_order['id']}", headers=outro)
        assert resp.status_code == 403

    def test_obter_proprio_pedido_ok(self, client, mock_db, sample_order, user_headers):
        mock_db["orders"].insert_one(sample_order)
        resp = client.get(f"/api/orders/{sample_order['id']}", headers=user_headers)
        assert resp.status_code == 200

    def test_cancelar_pedido_alheio_retorna_403(self, client, mock_db, sample_order, sample_product, auth_headers):
        mock_db["orders"].insert_one(sample_order)
        mock_db["products"].insert_one(sample_product)
        outro = auth_headers(user_id=2)
        resp = client.post(f"/api/orders/{sample_order['id']}/cancel", headers=outro)
        assert resp.status_code == 403

    def test_status_exige_auth(self, client, mock_db, sample_order):
        r = client.put(
            f"/api/orders/{sample_order['id']}/status",
            data=json.dumps({"status": "enviado"}),
            content_type="application/json",
        )
        assert r.status_code == 401

    def test_status_por_cliente_retorna_403(self, client, mock_db, sample_order, user_headers):
        mock_db["orders"].insert_one(sample_order)
        r = client.put(
            f"/api/orders/{sample_order['id']}/status",
            data=json.dumps({"status": "enviado"}),
            content_type="application/json",
            headers=user_headers,  # dono, mas não admin
        )
        assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Categorias — @admin_required nas mutações, leitura pública  [#9]
# --------------------------------------------------------------------------- #
class TestCategoriesAuthorization:
    def test_criar_sem_token_retorna_401(self, client, mock_db):
        resp = _json_post(client, "/api/categories", {"name": "X"})
        assert resp.status_code == 401

    def test_criar_por_cliente_retorna_403(self, client, mock_db, user_headers):
        resp = _json_post(client, "/api/categories", {"name": "X"}, user_headers)
        assert resp.status_code == 403

    def test_excluir_por_cliente_retorna_403(self, client, mock_db, user_headers):
        assert client.delete("/api/categories/1", headers=user_headers).status_code == 403

    def test_listar_e_publico(self, client, mock_db):
        assert client.get("/api/categories").status_code == 200


# --------------------------------------------------------------------------- #
# Imagens — @admin_required nas mutações, leitura pública  [#10]
# --------------------------------------------------------------------------- #
class TestImagesAuthorization:
    def test_upload_sem_token_retorna_401(self, client, mock_db):
        assert client.post("/api/images/upload").status_code == 401

    def test_upload_por_cliente_retorna_403(self, client, mock_db, user_headers):
        assert client.post("/api/images/upload", headers=user_headers).status_code == 403

    def test_delete_por_cliente_retorna_403(self, client, mock_db, user_headers):
        assert client.delete("/api/images/delete", headers=user_headers).status_code == 403


# --------------------------------------------------------------------------- #
# Favoritos — @jwt_required (sem X-User-Id falsificável)  [#4]
# --------------------------------------------------------------------------- #
class TestFavoritesAuthorization:
    def test_listar_sem_token_retorna_401(self, client, mock_db):
        assert client.get("/api/favorites").status_code == 401

    def test_toggle_sem_token_retorna_401(self, client, mock_db):
        resp = _json_post(client, "/api/favorites/toggle", {"product_id": 1})
        assert resp.status_code == 401

    def test_x_user_id_nao_autentica_mais(self, client, mock_db):
        # o header falsificável antigo não deve mais conceder acesso
        resp = client.get("/api/favorites", headers={"X-User-Id": "1"})
        assert resp.status_code == 401
