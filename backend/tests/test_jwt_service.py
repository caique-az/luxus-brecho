"""
Testes da Fase 1 do plano de correções do backend (jwt_service).

Cobrem as correções dos itens 5, 6 e 7 do code review:
  - #5 convenção única de tipo do `sub` (int) → owner_or_admin_required deixa
    de negar o próprio dono ('5' != 5).
  - #6 refresh_access_token normaliza o `sub` para int antes do find_one.
  - #7 JWT_SECRET_KEY sem fallback: RuntimeError no import se ausente.
"""
import importlib.util
import os

import pytest
from flask import Flask, g, jsonify

from app.services.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_payload,
    jwt_required,
    admin_required,
    owner_or_admin_required,
    refresh_access_token,
)


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def jwt_app():
    """App Flask mínima com rotas protegidas por cada decorator, para exercitá-los
    de forma isolada via test_client (request context real, g, jsonify)."""
    app = Flask(__name__)

    @app.route("/me")
    @jwt_required
    def me():
        return jsonify({"user_id": g.user_id, "type": type(g.user_id).__name__})

    @app.route("/admin")
    @admin_required
    def admin_only():
        return jsonify({"user_id": g.user_id})

    @app.route("/user/<int:user_id>/resource")
    @owner_or_admin_required("user_id")
    def owned(user_id):
        return jsonify({"caller": g.user_id, "resource": user_id})

    return app


@pytest.fixture
def jwt_client(jwt_app):
    return jwt_app.test_client()


# --------------------------------------------------------------------------- #
# #5 — get_user_id_from_payload: convenção única de tipo (int)
# --------------------------------------------------------------------------- #
class TestGetUserIdFromPayload:
    def test_sub_string_vira_int(self):
        assert get_user_id_from_payload({"sub": "5"}) == 5

    def test_sub_int_permanece_int(self):
        assert get_user_id_from_payload({"sub": 5}) == 5

    def test_retorno_e_sempre_int(self):
        assert isinstance(get_user_id_from_payload({"sub": "42"}), int)

    def test_sub_ausente_retorna_none(self):
        assert get_user_id_from_payload({}) is None

    def test_sub_nao_numerico_retorna_none(self):
        assert get_user_id_from_payload({"sub": "abc"}) is None

    def test_sub_none_retorna_none(self):
        assert get_user_id_from_payload({"sub": None}) is None

    def test_sub_vazio_retorna_none(self):
        assert get_user_id_from_payload({"sub": ""}) is None


# --------------------------------------------------------------------------- #
# Round-trip de token: sub gravado como str, lido como int
# --------------------------------------------------------------------------- #
class TestTokenRoundTrip:
    def test_access_token_sub_e_str_mas_lido_como_int(self):
        token = create_access_token(5, "Cliente", "a@b.com")
        ok, payload, err = decode_token(token)
        assert ok and err is None
        assert payload["sub"] == "5"  # gravado como string
        uid = get_user_id_from_payload(payload)
        assert uid == 5 and isinstance(uid, int)  # lido como int

    def test_refresh_token_sub_lido_como_int(self):
        token = create_refresh_token(5)
        ok, payload, _ = decode_token(token)
        assert ok
        assert get_user_id_from_payload(payload) == 5


# --------------------------------------------------------------------------- #
# jwt_required
# --------------------------------------------------------------------------- #
class TestJwtRequired:
    def test_sem_token_retorna_401(self, jwt_client):
        assert jwt_client.get("/me").status_code == 401

    def test_token_invalido_retorna_401(self, jwt_client):
        resp = jwt_client.get("/me", headers=auth_header("token-lixo"))
        assert resp.status_code == 401

    def test_token_valido_expoe_user_id_int(self, jwt_client):
        token = create_access_token(7, "Cliente", "a@b.com")
        resp = jwt_client.get("/me", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json() == {"user_id": 7, "type": "int"}

    def test_refresh_token_rejeitado_no_access(self, jwt_client):
        # um refresh token não pode acessar rota que exige access token
        token = create_refresh_token(7)
        resp = jwt_client.get("/me", headers=auth_header(token))
        assert resp.status_code == 401


# --------------------------------------------------------------------------- #
# #5 — owner_or_admin_required: o bug central (str vs int) negava o dono
# --------------------------------------------------------------------------- #
class TestOwnerOrAdminRequired:
    def test_dono_acessa_o_proprio_recurso(self, jwt_client):
        # Regressão do item #5: antes '5' != 5 → 403 para o próprio dono.
        token = create_access_token(5, "Cliente", "a@b.com")
        resp = jwt_client.get("/user/5/resource", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json() == {"caller": 5, "resource": 5}

    def test_terceiro_nao_acessa_recurso_alheio(self, jwt_client):
        token = create_access_token(5, "Cliente", "a@b.com")
        resp = jwt_client.get("/user/9/resource", headers=auth_header(token))
        assert resp.status_code == 403

    def test_admin_acessa_qualquer_recurso(self, jwt_client):
        token = create_access_token(2, "Administrador", "admin@b.com")
        resp = jwt_client.get("/user/9/resource", headers=auth_header(token))
        assert resp.status_code == 200

    def test_sem_token_retorna_401(self, jwt_client):
        assert jwt_client.get("/user/5/resource").status_code == 401


# --------------------------------------------------------------------------- #
# admin_required
# --------------------------------------------------------------------------- #
class TestAdminRequired:
    def test_admin_passa(self, jwt_client):
        token = create_access_token(2, "Administrador", "admin@b.com")
        assert jwt_client.get("/admin", headers=auth_header(token)).status_code == 200

    def test_cliente_recebe_403(self, jwt_client):
        token = create_access_token(2, "Cliente", "a@b.com")
        assert jwt_client.get("/admin", headers=auth_header(token)).status_code == 403

    def test_sem_token_retorna_401(self, jwt_client):
        assert jwt_client.get("/admin").status_code == 401


# --------------------------------------------------------------------------- #
# #6 — refresh_access_token: find_one precisa buscar por id int
# --------------------------------------------------------------------------- #
class _RecordingCollection:
    """Coleção fake que registra a última query e casa 'id' de forma estrita
    (5 == 5, mas 5 != '5') — evidenciando que o sub chega como int."""

    def __init__(self, user):
        self.user = user
        self.last_query = None

    def find_one(self, query):
        self.last_query = query
        if self.user is not None and self.user.get("id") == query.get("id"):
            return self.user
        return None


class TestRefreshAccessToken:
    def _patch_collection(self, monkeypatch, user):
        coll = _RecordingCollection(user)
        monkeypatch.setattr(
            "app.models.user_model.get_collection", lambda db: coll
        )
        return coll

    def test_refresh_valido_busca_por_id_int_e_emite_tokens(self, monkeypatch):
        user = {"id": 5, "tipo": "Cliente", "email": "a@b.com", "ativo": True}
        coll = self._patch_collection(monkeypatch, user)

        rtok = create_refresh_token(5)
        ok, tokens, err = refresh_access_token(rtok, db=None)

        assert ok is True, err
        assert tokens is not None
        assert "access_token" in tokens and "refresh_token" in tokens
        # o cerne da correção #6: a busca usou int, não a string do sub
        assert coll.last_query == {"id": 5}
        assert isinstance(coll.last_query["id"], int)

    def test_access_token_nao_serve_como_refresh(self, monkeypatch):
        self._patch_collection(monkeypatch, {"id": 5, "ativo": True})
        atok = create_access_token(5, "Cliente", "a@b.com")
        ok, tokens, err = refresh_access_token(atok, db=None)
        assert ok is False
        assert tokens is None

    def test_usuario_inexistente_falha(self, monkeypatch):
        self._patch_collection(monkeypatch, None)
        rtok = create_refresh_token(5)
        ok, tokens, err = refresh_access_token(rtok, db=None)
        assert ok is False
        assert tokens is None

    def test_conta_desativada_falha(self, monkeypatch):
        user = {"id": 5, "tipo": "Cliente", "email": "a@b.com", "ativo": False}
        self._patch_collection(monkeypatch, user)
        rtok = create_refresh_token(5)
        ok, tokens, err = refresh_access_token(rtok, db=None)
        assert ok is False
        assert "desativada" in (err or "").lower()


# --------------------------------------------------------------------------- #
# #7 — JWT_SECRET_KEY sem fallback (fail-fast no import)
# --------------------------------------------------------------------------- #
class TestSecretKeyFailFast:
    def _reimport_isolado(self):
        """Recarrega jwt_service num módulo isolado, relendo o ambiente atual,
        sem afetar o módulo já importado pela suíte."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "services", "jwt_service.py",
        )
        spec = importlib.util.spec_from_file_location("jwt_service_reimport_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_import_sem_secret_levanta_runtime_error(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(RuntimeError):
            self._reimport_isolado()

    def test_import_com_secret_funciona(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "chave-de-teste-suficientemente-longa")
        module = self._reimport_isolado()
        assert module.JWT_SECRET_KEY == "chave-de-teste-suficientemente-longa"
