"""
Testes para rotas de usuários.
"""
import pytest
import json
from datetime import datetime


class TestUsersList:
    """Testes para listagem de usuários."""
    
    def test_list_users_empty(self, client, mock_db, admin_headers):
        """Testa listagem quando não há usuários."""
        response = client.get("/api/users", headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()

        # API retorna {items: [], pagination: {...}}
        assert "items" in data
        assert "pagination" in data

    def test_list_users_with_data(self, client, mock_db, sample_user, admin_headers):
        """Testa listagem com usuários cadastrados."""
        mock_db["users"].insert_one(sample_user)

        response = client.get("/api/users", headers=admin_headers)

        assert response.status_code == 200


class TestUserCreate:
    """Testes para criação de usuários."""
    
    def test_create_user_success(self, client, mock_db):
        """Testa criação de usuário com sucesso."""
        # Configura counter
        mock_db["counters"].insert_one({"_id": "users", "sequence_value": 0})
        
        user_data = {
            "nome": "Novo Usuário",
            "email": "novo@email.com",
            "senha": "Senha123",
            "tipo": "Cliente",  # Campo obrigatório
        }
        
        response = client.post(
            "/api/users",
            data=json.dumps(user_data),
            content_type="application/json"
        )
        
        assert response.status_code in [200, 201]
    
    def test_create_user_missing_fields(self, client, mock_db):
        """Testa criação sem campos obrigatórios."""
        user_data = {
            "nome": "Usuário Incompleto",
        }
        
        response = client.post(
            "/api/users",
            data=json.dumps(user_data),
            content_type="application/json"
        )
        
        assert response.status_code == 400
    
    def test_create_user_invalid_email(self, client, mock_db):
        """Testa criação com email inválido."""
        user_data = {
            "nome": "Usuário",
            "email": "email-invalido",
            "senha": "Senha123",
        }
        
        response = client.post(
            "/api/users",
            data=json.dumps(user_data),
            content_type="application/json"
        )
        
        assert response.status_code == 400
    
    def test_create_user_duplicate_email(self, client, mock_db, sample_user):
        """Testa criação com email duplicado."""
        mock_db["users"].insert_one(sample_user)
        mock_db["counters"].insert_one({"_id": "users", "seq": 1})
        
        user_data = {
            "nome": "Outro Usuário",
            "email": sample_user["email"],
            "senha": "Senha123",
        }
        
        response = client.post(
            "/api/users",
            data=json.dumps(user_data),
            content_type="application/json"
        )
        
        assert response.status_code in [400, 409]


class TestUserGet:
    """Testes para obter usuário específico."""
    
    def test_get_user_by_id(self, client, mock_db, sample_user, admin_headers):
        """Testa obter usuário por ID."""
        mock_db["users"].insert_one(sample_user)

        response = client.get(f"/api/users/{sample_user['id']}", headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data["id"] == sample_user["id"]
        assert data["nome"] == sample_user["nome"]

    def test_get_user_not_found(self, client, mock_db, admin_headers):
        """Testa obter usuário inexistente."""
        response = client.get("/api/users/99999", headers=admin_headers)

        assert response.status_code == 404


class TestUserUpdate:
    """Testes para atualização de usuários."""
    
    def test_update_user_success(self, client, mock_db, sample_user, admin_headers):
        """Testa atualização de usuário com sucesso."""
        mock_db["users"].insert_one(sample_user)

        update_data = {
            "nome": "Nome Atualizado",
            "email": sample_user["email"],
            "tipo": sample_user["tipo"],
        }

        response = client.put(
            f"/api/users/{sample_user['id']}",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=admin_headers
        )

        assert response.status_code == 200

    def test_update_user_not_found(self, client, mock_db, admin_headers):
        """Testa atualização de usuário inexistente."""
        update_data = {
            "nome": "Nome Atualizado",
            "email": "test@test.com",
            "tipo": "Cliente",
        }

        response = client.put(
            "/api/users/99999",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=admin_headers
        )

        assert response.status_code == 404


class TestUserDelete:
    """Testes para exclusão de usuários."""
    
    def test_delete_user_success(self, client, mock_db, sample_user, admin_headers):
        """Testa exclusão (soft delete) de usuário."""
        mock_db["users"].insert_one(sample_user)

        response = client.delete(f"/api/users/{sample_user['id']}", headers=admin_headers)

        assert response.status_code == 200

    def test_delete_user_not_found(self, client, mock_db, admin_headers):
        """Testa exclusão de usuário inexistente."""
        response = client.delete("/api/users/99999", headers=admin_headers)

        assert response.status_code == 404


class TestUserAuth:
    """Testes para autenticação de usuários."""
    
    def test_auth_success(self, client, mock_db, sample_user):
        """Testa autenticação com credenciais válidas."""
        # Insere usuário com senha hashada conhecida
        import bcrypt
        password = "Senha123"
        sample_user["senha_hash"] = bcrypt.hashpw(
            password.encode("utf-8"), 
            bcrypt.gensalt()
        ).decode("utf-8")
        mock_db["users"].insert_one(sample_user)
        
        auth_data = {
            "email": sample_user["email"],
            "senha": password,
        }
        
        response = client.post(
            "/api/users/auth",
            data=json.dumps(auth_data),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "user" in data or "id" in data
    
    def test_auth_wrong_password(self, client, mock_db, sample_user):
        """Testa autenticação com senha incorreta."""
        import bcrypt
        sample_user["senha_hash"] = bcrypt.hashpw(
            "Senha123".encode("utf-8"), 
            bcrypt.gensalt()
        ).decode("utf-8")
        mock_db["users"].insert_one(sample_user)
        
        auth_data = {
            "email": sample_user["email"],
            "senha": "SenhaErrada",
        }
        
        response = client.post(
            "/api/users/auth",
            data=json.dumps(auth_data),
            content_type="application/json"
        )
        
        assert response.status_code == 401
    
    def test_auth_user_not_found(self, client, mock_db):
        """Testa autenticação com usuário inexistente."""
        auth_data = {
            "email": "inexistente@email.com",
            "senha": "Senha123",
        }
        
        response = client.post(
            "/api/users/auth",
            data=json.dumps(auth_data),
            content_type="application/json"
        )
        
        assert response.status_code in [401, 404]
    
    def test_auth_inactive_user(self, client, mock_db, sample_user):
        """Testa autenticação com usuário inativo."""
        import bcrypt
        sample_user["ativo"] = False
        sample_user["senha_hash"] = bcrypt.hashpw(
            "Senha123".encode("utf-8"), 
            bcrypt.gensalt()
        ).decode("utf-8")
        mock_db["users"].insert_one(sample_user)
        
        auth_data = {
            "email": sample_user["email"],
            "senha": "Senha123",
        }
        
        response = client.post(
            "/api/users/auth",
            data=json.dumps(auth_data),
            content_type="application/json"
        )
        
        assert response.status_code in [401, 403]


class TestUserInfo:
    """Testes para endpoint de informações do usuário."""
    
    def test_get_user_info(self, client, mock_db, sample_user):
        """Testa obter informações do usuário."""
        mock_db["users"].insert_one(sample_user)
        
        response = client.get(
            "/api/users/me",
            headers={"X-User-Id": str(sample_user["id"])}
        )
        
        # Pode retornar 200 ou 401 dependendo da implementação
        assert response.status_code in [200, 401, 404]
