"""
Testes da Fase 4 do plano (item #14): admin inicial seguro.

Garantem que:
  - sem ADMIN_EMAIL/ADMIN_PASSWORD nenhum admin é semeado (não há senha padrão);
  - com as env vars, o admin usa exatamente essas credenciais;
  - a antiga credencial hardcoded (contatojmfr@gmail.com / senha123) nunca é criada;
  - um admin já existente não é sobrescrito;
  - uma senha fraca não gera admin.
"""
import pytest

from app.models.user_model import create_default_admin, get_collection, verify_password


class TestDefaultAdminSeed:
    def test_sem_env_vars_nao_cria_admin(self, mock_db, monkeypatch):
        monkeypatch.delenv("ADMIN_EMAIL", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

        create_default_admin(mock_db)

        assert get_collection(mock_db).find_one({"tipo": "Administrador"}) is None

    def test_com_env_vars_usa_credenciais_do_ambiente(self, mock_db, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAIL", "chefe@luxus.com")
        monkeypatch.setenv("ADMIN_PASSWORD", "Forte123")
        monkeypatch.setenv("ADMIN_NAME", "Chefe")

        create_default_admin(mock_db)

        admin = get_collection(mock_db).find_one({"tipo": "Administrador"})
        assert admin is not None
        assert admin["email"] == "chefe@luxus.com"
        assert admin["nome"] == "Chefe"
        # A senha vem do ambiente — não do antigo hardcode.
        assert verify_password("Forte123", admin["senha_hash"]) is True
        assert verify_password("senha123", admin["senha_hash"]) is False

    def test_nao_semeia_credencial_hardcoded_antiga(self, mock_db, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAIL", "chefe@luxus.com")
        monkeypatch.setenv("ADMIN_PASSWORD", "Forte123")

        create_default_admin(mock_db)

        assert get_collection(mock_db).find_one({"email": "contatojmfr@gmail.com"}) is None

    def test_nao_sobrescreve_admin_existente(self, mock_db, monkeypatch):
        get_collection(mock_db).insert_one({
            "id": 1, "nome": "Existente", "email": "ja@existe.com",
            "tipo": "Administrador", "ativo": True,
        })
        monkeypatch.setenv("ADMIN_EMAIL", "novo@luxus.com")
        monkeypatch.setenv("ADMIN_PASSWORD", "Forte123")

        create_default_admin(mock_db)

        admins = list(get_collection(mock_db).find({"tipo": "Administrador"}))
        assert len(admins) == 1
        assert admins[0]["email"] == "ja@existe.com"

    def test_senha_fraca_nao_cria_admin(self, mock_db, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAIL", "chefe@luxus.com")
        monkeypatch.setenv("ADMIN_PASSWORD", "123")  # sem letra e curta demais

        create_default_admin(mock_db)

        assert get_collection(mock_db).find_one({"tipo": "Administrador"}) is None
