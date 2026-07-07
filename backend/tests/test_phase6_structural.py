"""
Testes da Fase 6 do plano (dívida estrutural), nos itens com comportamento
observável:

  - #7  helpers extraídos para utils: `serialize_doc` (canônico, sem vazar `_id`)
        e `parse_pagination` (com clamp de page_size);
  - leak de `_id` em favoritos corrigido (resposta não expõe o ObjectId interno);
  - #8  `list_users` escapa o termo de busca (regex) e não estoura 500.

Os itens de bootstrap (factory única, fail-fast de blueprints, rate limit
configurável) não têm superfície HTTP fácil de exercitar e ficam cobertos pela
própria inicialização da app no conftest.
"""
from datetime import datetime

import pytest

from app.utils.serialization import serialize_doc
from app.utils.pagination import parse_pagination


# --------------------------------------------------------------------------- #
# #7 — serialize_doc (forma canônica: remove _id, nunca o vaza)
# --------------------------------------------------------------------------- #
class TestSerializeDoc:
    def test_remove_id(self):
        out = serialize_doc({"_id": "abc123", "nome": "X"})
        assert "_id" not in out
        assert out["nome"] == "X"

    def test_nao_vaza_id_como_string(self):
        # Regressão do bug de favoritos: antes convertia _id para str e o mantinha.
        out = serialize_doc({"_id": "652f...", "product_id": 1})
        assert "_id" not in out

    def test_doc_vazio_vira_dict_vazio(self):
        assert serialize_doc({}) == {}
        assert serialize_doc(None) == {}

    def test_nao_muta_o_original(self):
        original = {"_id": "x", "a": 1}
        serialize_doc(original)
        assert "_id" in original  # a cópia é que perde o _id


# --------------------------------------------------------------------------- #
# #7 — parse_pagination (clamp de page_size; page >= 1)
# --------------------------------------------------------------------------- #
class TestParsePagination:
    def test_default(self, app):
        with app.test_request_context("/"):
            assert parse_pagination(default_page_size=20) == (1, 20, 0)

    def test_clamp_page_size_ao_maximo(self, app):
        with app.test_request_context("/?page_size=100000"):
            page, page_size, skip = parse_pagination(default_page_size=20)
            assert page_size == 100  # teto, não 100000

    def test_page_minimo_um_e_skip(self, app):
        with app.test_request_context("/?page=0&page_size=10"):
            page, page_size, skip = parse_pagination()
            assert page == 1
            assert skip == 0

    def test_skip_calculado(self, app):
        with app.test_request_context("/?page=3&page_size=10"):
            page, page_size, skip = parse_pagination()
            assert (page, page_size, skip) == (3, 10, 20)

    def test_valores_nao_numericos_caem_no_default(self, app):
        with app.test_request_context("/?page=abc&page_size=xyz"):
            assert parse_pagination(default_page_size=20) == (1, 20, 0)


# --------------------------------------------------------------------------- #
# Favoritos: a resposta não expõe o _id interno do Mongo
# --------------------------------------------------------------------------- #
class TestFavoritesNoIdLeak:
    def test_lista_favoritos_sem_id(self, client, mock_db, sample_product, user_headers):
        mock_db["products"].insert_one(sample_product)
        # insert_one do mock atribui um _id; se vazasse, apareceria na resposta.
        mock_db["favorites"].insert_one({
            "user_id": 1,
            "product_id": sample_product["id"],
            "created_at": datetime.utcnow(),
        })

        resp = client.get("/api/favorites", headers=user_headers)
        assert resp.status_code == 200

        favorites = resp.get_json()["favorites"]
        assert len(favorites) == 1
        assert "_id" not in favorites[0]


# --------------------------------------------------------------------------- #
# #8 + #7 — list_users: busca com metacaracteres de regex e clamp de page_size
# --------------------------------------------------------------------------- #
class TestListUsersHardening:
    def test_page_size_e_limitado_na_resposta(self, client, mock_db, admin_headers):
        resp = client.get("/api/users/?page_size=100000", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.get_json()["pagination"]["page_size"] == 100

    def test_busca_com_regex_nao_estoura_500(self, client, mock_db, admin_headers):
        # Termo com metacaracteres de ReDoS; escapado, é tratado como literal.
        resp = client.get("/api/users/?search=(a%2B)%2B%24", headers=admin_headers)
        assert resp.status_code == 200


# --------------------------------------------------------------------------- #
# #3 — require_db: guard de banco centralizado, com 503 canônico
# --------------------------------------------------------------------------- #
class TestRequireDb:
    def test_banco_indisponivel_retorna_503_canonico(self, client, app, admin_headers, monkeypatch):
        # admin_headers já semeou o admin; derrubar o banco depois força o 503
        # pela camada require_db (a auth degrada para as claims sem banco).
        monkeypatch.setattr(app, "db", None)
        resp = client.get("/api/users/", headers=admin_headers)
        assert resp.status_code == 503
        assert resp.get_json()["message"] == "Banco de dados indisponível"


# --------------------------------------------------------------------------- #
# #5 — create_order marca os produtos como vendido (via update_many, 1 query)
# --------------------------------------------------------------------------- #
class TestOrderMarksProductsSold:
    def test_create_order_marca_produto_vendido(self, client, mock_db, sample_product, user_headers):
        import json

        mock_db["products"].insert_one(sample_product)
        body = {
            "items": [{"product_id": sample_product["id"]}],
            "endereco": {
                "rua": "Rua Teste", "numero": "1", "bairro": "Centro",
                "cidade": "São Paulo", "estado": "SP", "cep": "01234-567",
            },
        }
        resp = client.post(
            "/api/orders/user/1", data=json.dumps(body),
            content_type="application/json", headers=user_headers,
        )
        assert resp.status_code == 201

        produto = mock_db["products"].find_one({"id": sample_product["id"]})
        assert produto["status"] == "vendido"
