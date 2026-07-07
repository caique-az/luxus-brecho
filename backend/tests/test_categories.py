"""
Testes para rotas de categorias.
"""
import pytest
import json
from datetime import datetime


class TestCategoriesList:
    """Testes para listagem de categorias."""
    
    def test_list_categories_empty(self, client, mock_db):
        """Testa listagem quando não há categorias."""
        response = client.get("/api/categories")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # API retorna {items: [], pagination: {...}}
        assert "items" in data
        assert "pagination" in data
    
    def test_list_categories_with_data(self, client, mock_db, sample_category):
        """Testa listagem com categorias cadastradas."""
        mock_db["categories"].insert_one(sample_category)
        
        response = client.get("/api/categories")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert "items" in data
        assert len(data["items"]) >= 1


class TestCategoryCreate:
    """Testes para criação de categorias."""
    
    def test_create_category_success(self, client, mock_db, admin_headers):
        """Testa criação de categoria com sucesso."""
        mock_db["counters"].insert_one({"name": "categories", "seq": 0})

        category_data = {
            "name": "Nova Categoria",
            "description": "Descrição da categoria",
        }

        response = client.post(
            "/api/categories",
            data=json.dumps(category_data),
            content_type="application/json",
            headers=admin_headers
        )

        assert response.status_code in [200, 201]

    def test_create_category_missing_name(self, client, mock_db, admin_headers):
        """Testa criação sem nome."""
        category_data = {
            "description": "Descrição sem nome",
        }

        response = client.post(
            "/api/categories",
            data=json.dumps(category_data),
            content_type="application/json",
            headers=admin_headers
        )

        assert response.status_code == 400

    def test_create_category_duplicate_name(self, client, mock_db, sample_category, admin_headers):
        """Testa criação com nome duplicado."""
        mock_db["categories"].insert_one(sample_category)
        mock_db["counters"].insert_one({"name": "categories", "seq": 1})

        category_data = {
            "name": sample_category["name"],
            "description": "Outra descrição",
        }

        response = client.post(
            "/api/categories",
            data=json.dumps(category_data),
            content_type="application/json",
            headers=admin_headers
        )

        # Deve retornar erro de duplicado
        assert response.status_code == 409


class TestCategoryGet:
    """Testes para obter categoria específica."""
    
    def test_get_category_by_id(self, client, mock_db, sample_category):
        """Testa obter categoria por ID."""
        mock_db["categories"].insert_one(sample_category)
        
        response = client.get(f"/api/categories/{sample_category['id']}")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["id"] == sample_category["id"]
        assert data["name"] == sample_category["name"]
    
    def test_get_category_not_found(self, client, mock_db):
        """Testa obter categoria inexistente."""
        response = client.get("/api/categories/99999")
        
        assert response.status_code == 404


class TestCategoryUpdate:
    """Testes para atualização de categorias."""
    
    def test_update_category_success(self, client, mock_db, sample_category, admin_headers):
        """Testa atualização de categoria com sucesso."""
        mock_db["categories"].insert_one(sample_category)

        update_data = {
            "name": "Categoria Atualizada",
            "description": "Nova descrição",
        }

        response = client.put(
            f"/api/categories/{sample_category['id']}",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=admin_headers
        )

        assert response.status_code == 200

    def test_update_category_not_found(self, client, mock_db, admin_headers):
        """Testa atualização de categoria inexistente."""
        update_data = {
            "name": "Categoria Atualizada",
        }

        response = client.put(
            "/api/categories/99999",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=admin_headers
        )

        assert response.status_code == 404


class TestCategoryDelete:
    """Testes para exclusão de categorias."""
    
    def test_delete_category_success(self, client, mock_db, sample_category, admin_headers):
        """Testa exclusão de categoria."""
        mock_db["categories"].insert_one(sample_category)

        response = client.delete(
            f"/api/categories/{sample_category['id']}",
            headers=admin_headers
        )

        assert response.status_code == 200

    def test_delete_category_not_found(self, client, mock_db, admin_headers):
        """Testa exclusão de categoria inexistente."""
        response = client.delete(
            "/api/categories/99999",
            headers=admin_headers
        )

        assert response.status_code == 404
