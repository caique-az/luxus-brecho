"""
Testes do envelope de resposta padrão (``{success, message, ...}``).

Trava o contrato do item 2 dos débitos técnicos: toda resposta — de sucesso ou
de erro — carrega ``success`` como discriminador e usa ``message`` (nunca
``error``) para a mensagem, inclusive nos erros de autenticação emitidos pelos
decorators JWT.
"""
import pytest


class TestEnvelopeSucesso:
    """Respostas de sucesso trazem ``success: True`` no topo (envelope plano)."""

    def test_root_tem_success(self, client):
        data = client.get("/").get_json()
        assert data["success"] is True

    def test_lista_produtos_tem_success(self, client):
        resp = client.get("/api/products")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        # Dados de domínio ficam ao lado de ``success``, não aninhados em ``data``.
        assert "items" in data
        assert "pagination" in data

    def test_lista_categorias_tem_success(self, client):
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "items" in data

    def test_health_tem_success(self, client):
        data = client.get("/api/health").get_json()
        assert data["success"] is True


class TestEnvelopeErro:
    """Respostas de erro trazem ``success: False`` + ``message`` (nunca ``error``)."""

    def test_404_handler(self, client):
        data = client.get("/api/rota-inexistente").get_json()
        assert data["success"] is False
        assert "message" in data

    def test_produto_inexistente(self, client):
        resp = client.get("/api/products/999999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert "message" in data

    def test_auth_sem_token_usa_envelope(self, client):
        """Sem token, o decorator ``jwt_required`` responde no envelope padrão."""
        resp = client.get("/api/favorites")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["success"] is False
        assert "message" in data
        # A chave antiga e forjável não deve mais aparecer.
        assert "error" not in data

    def test_admin_sem_token_usa_envelope(self, client):
        """Escrita de categoria exige admin; o 401 também segue o envelope."""
        resp = client.post("/api/categories", json={"name": "X"})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["success"] is False
        assert "message" in data
        assert "error" not in data
