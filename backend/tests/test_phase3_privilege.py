"""
Testes da Fase 3 do plano de correções do backend (bloquear escalada de privilégio).

Cobrem:
  - #1  registro público sempre cria Cliente; admin só por outro admin (/admin);
  - #8  exclusão de conta endurecida (auth + posse, contador de tentativas,
        comparação em tempo constante, alvo vindo do token e não do corpo);
  - #15 frescor de privilégio: os decorators releem tipo/ativo do banco, então
        conta desativada e admin rebaixado perdem acesso na próxima requisição.
"""
import json

import pytest


def _json_post(client, url, body, headers=None):
    return client.post(
        url, data=json.dumps(body), content_type="application/json", headers=headers
    )


# --------------------------------------------------------------------------- #
# #1 — Auto-registro como administrador
# --------------------------------------------------------------------------- #
class TestPublicRegistrationForcesCliente:
    def test_registro_publico_ignora_tipo_administrador(self, client, mock_db):
        # Mesmo pedindo tipo="Administrador", o registro público cria um Cliente.
        body = {
            "nome": "Fulano",
            "email": "fulano@x.com",
            "senha": "Senha123",
            "tipo": "Administrador",
        }
        resp = _json_post(client, "/api/users/", body)
        assert resp.status_code in (200, 201)

        created = mock_db["users"].find_one({"email": "fulano@x.com"})
        assert created is not None
        assert created["tipo"] == "Cliente"
        # Cliente não é ativado na hora (precisa confirmar email) — nunca vira admin ativo
        assert created["ativo"] is False

    def test_criar_admin_sem_token_retorna_401(self, client, mock_db):
        body = {"nome": "A", "email": "a@x.com", "senha": "Senha123"}
        assert _json_post(client, "/api/users/admin", body).status_code == 401

    def test_criar_admin_por_cliente_retorna_403(self, client, mock_db, user_headers):
        body = {"nome": "A", "email": "a@x.com", "senha": "Senha123"}
        assert _json_post(client, "/api/users/admin", body, user_headers).status_code == 403

    def test_criar_admin_por_admin_cria_administrador(self, client, mock_db, admin_headers):
        body = {"nome": "Novo Admin", "email": "novoadmin@x.com", "senha": "Senha123"}
        resp = _json_post(client, "/api/users/admin", body, admin_headers)
        assert resp.status_code in (200, 201)

        created = mock_db["users"].find_one({"email": "novoadmin@x.com"})
        assert created is not None
        assert created["tipo"] == "Administrador"
        assert created["ativo"] is True  # admin é ativado imediatamente


# --------------------------------------------------------------------------- #
# #8 — Exclusão de conta endurecida
# --------------------------------------------------------------------------- #
class TestAccountDeletionHardened:
    def test_request_sem_token_retorna_401(self, client, mock_db):
        resp = _json_post(client, "/api/users/request-deletion", {"user_id": 1})
        assert resp.status_code == 401

    def test_confirm_sem_token_retorna_401(self, client, mock_db):
        resp = _json_post(client, "/api/users/confirm-deletion", {"user_id": 1, "code": "123456"})
        assert resp.status_code == 401

    def test_request_usa_usuario_do_token_nao_do_corpo(self, client, mock_db, user_headers, monkeypatch):
        # Um segundo usuário existe; o corpo tenta mirá-lo, mas o alvo é o do token (1).
        mock_db["users"].insert_one({
            "id": 2, "nome": "Outro", "email": "outro@x.com", "tipo": "Cliente", "ativo": True,
        })
        import app.controllers.users_controller as uc
        monkeypatch.setattr(uc, "send_account_deletion_code", lambda *a, **k: True)

        resp = _json_post(client, "/api/users/request-deletion", {"user_id": 2}, user_headers)
        assert resp.status_code == 200

        # O código foi gravado no usuário do token (1), nunca no usuário 2 do corpo.
        assert mock_db["users"].find_one({"id": 1}).get("deletion_code")
        assert mock_db["users"].find_one({"id": 2}).get("deletion_code") is None

    def test_codigo_correto_exclui_a_conta(self, client, mock_db, user_headers):
        mock_db["users"].update_one(
            {"id": 1}, {"$set": {"deletion_code": "654321", "deletion_attempts": 0}}
        )
        resp = _json_post(client, "/api/users/confirm-deletion", {"code": "654321"}, user_headers)
        assert resp.status_code == 200
        assert mock_db["users"].find_one({"id": 1}) is None

    def test_tentativas_erradas_invalidam_o_codigo(self, client, mock_db, user_headers):
        mock_db["users"].update_one(
            {"id": 1}, {"$set": {"deletion_code": "111111", "deletion_attempts": 0}}
        )
        # 5 tentativas erradas: a última atinge o limite e invalida o código.
        resp = None
        for _ in range(5):
            resp = _json_post(client, "/api/users/confirm-deletion", {"code": "000000"}, user_headers)
        assert resp.status_code == 429

        user = mock_db["users"].find_one({"id": 1})
        assert user is not None  # a conta NÃO foi excluída por código errado
        assert "deletion_code" not in user  # código invalidado

        # Com o código invalidado, até o valor correto não exclui mais nada.
        resp = _json_post(client, "/api/users/confirm-deletion", {"code": "111111"}, user_headers)
        assert resp.status_code == 400
        assert mock_db["users"].find_one({"id": 1}) is not None


# --------------------------------------------------------------------------- #
# #15 — Frescor de privilégio nos decorators
# --------------------------------------------------------------------------- #
class TestPrivilegeFreshness:
    def test_conta_desativada_perde_acesso_jwt_required(self, client, mock_db, user_headers):
        # Rota jwt_required (favoritos): desativar no banco nega na próxima requisição.
        mock_db["users"].update_one({"id": 1}, {"$set": {"ativo": False}})
        assert client.get("/api/favorites", headers=user_headers).status_code == 403

    def test_conta_desativada_perde_acesso_owner(self, client, mock_db, user_headers):
        # Rota owner_or_admin_required: dono desativado não acessa nem o próprio recurso.
        mock_db["users"].update_one({"id": 1}, {"$set": {"ativo": False}})
        assert client.get("/api/cart/1", headers=user_headers).status_code == 403

    def test_admin_rebaixado_perde_privilegio(self, client, mock_db, admin_headers):
        # admin_required: rebaixar o admin no banco nega, mesmo o token dizendo Administrador.
        mock_db["users"].update_one({"id": 99}, {"$set": {"tipo": "Cliente"}})
        resp = _json_post(client, "/api/categories", {"name": "X"}, admin_headers)
        assert resp.status_code == 403

    def test_admin_rebaixado_perde_bypass_owner(self, client, mock_db, admin_headers):
        # O bypass de admin em owner_or_admin usa o tipo do BANCO, não o do token.
        mock_db["users"].update_one({"id": 99}, {"$set": {"tipo": "Cliente"}})
        # 99 não é dono do carrinho 1 e não é mais admin -> 403
        assert client.get("/api/cart/1", headers=admin_headers).status_code == 403

    def test_token_de_usuario_inexistente_retorna_401(self, client, mock_db):
        # Token válido para um id ausente do banco (sem a factory que semeia).
        from app.services.jwt_service import create_access_token
        token = create_access_token(777, "Cliente", "ghost@x.com")
        resp = client.get("/api/favorites", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
