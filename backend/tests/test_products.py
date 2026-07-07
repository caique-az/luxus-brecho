"""
Testes para rotas de produtos.
"""
import pytest
import json
from datetime import datetime


class TestProductsList:
    """Testes para listagem de produtos."""
    
    def test_list_products_empty(self, client, mock_db):
        """Testa listagem quando não há produtos."""
        response = client.get("/api/products")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # API retorna {items: [], pagination: {...}}
        assert "items" in data
        assert "pagination" in data
    
    def test_list_products_with_data(self, client, mock_db, sample_product):
        """Testa listagem com produtos cadastrados."""
        mock_db["products"].insert_one(sample_product)
        
        response = client.get("/api/products")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert "items" in data
        assert len(data["items"]) >= 1
    
    def test_list_products_with_pagination(self, client, mock_db, sample_product):
        """Testa listagem com paginação."""
        # Insere múltiplos produtos
        for i in range(15):
            product = sample_product.copy()
            product["id"] = i + 1
            product["titulo"] = f"Produto {i + 1}"
            mock_db["products"].insert_one(product)
        
        # API usa page_size, não limit
        response = client.get("/api/products?page=1&page_size=10")
        
        assert response.status_code == 200
    
    def test_list_products_filter_by_category(self, client, mock_db, sample_product):
        """Testa filtro por categoria."""
        mock_db["products"].insert_one(sample_product)
        
        response = client.get(f"/api/products?categoria={sample_product['categoria']}")
        
        assert response.status_code == 200
    
    def test_list_products_search(self, client, mock_db, sample_product):
        """Testa busca por termo."""
        mock_db["products"].insert_one(sample_product)
        
        response = client.get(f"/api/products?q={sample_product['titulo'][:5]}")
        
        assert response.status_code == 200


class TestProductCreate:
    """Testes para criação de produtos."""
    
    def test_create_product_success(self, client, mock_db, sample_category, admin_headers):
        """Testa criação de produto com sucesso (rota exige admin)."""
        # Configura counter e categoria
        mock_db["counters"].insert_one({"name": "products", "seq": 0})
        mock_db["categories"].insert_one(sample_category)

        product_data = {
            "titulo": "Novo Produto",
            "descricao": "Descrição do produto com mais de 10 caracteres",
            "preco": 150.00,
            "categoria": "Roupas",
            "imagem": "https://example.com/image.jpg",  # Campo obrigatório
        }

        response = client.post(
            "/api/products",
            data=json.dumps(product_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code in [200, 201]
    
    def test_create_product_missing_fields(self, client, mock_db, admin_headers):
        """Testa criação sem campos obrigatórios (rota exige admin)."""
        product_data = {
            "titulo": "Produto Incompleto",
        }

        response = client.post(
            "/api/products",
            data=json.dumps(product_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 400
    
    def test_create_product_invalid_price(self, client, mock_db, admin_headers):
        """Testa criação com preço inválido (rota exige admin)."""
        mock_db["counters"].insert_one({"_id": "products", "seq": 0})

        product_data = {
            "titulo": "Produto",
            "descricao": "Descrição",
            "preco": -10.00,  # Preço negativo
            "categoria": "Roupas",
        }

        response = client.post(
            "/api/products",
            data=json.dumps(product_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 400


class TestProductGet:
    """Testes para obter produto específico."""
    
    def test_get_product_by_id(self, client, mock_db, sample_product):
        """Testa obter produto por ID."""
        mock_db["products"].insert_one(sample_product)
        
        response = client.get(f"/api/products/{sample_product['id']}")
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["id"] == sample_product["id"]
        assert data["titulo"] == sample_product["titulo"]
    
    def test_get_product_not_found(self, client, mock_db):
        """Testa obter produto inexistente."""
        response = client.get("/api/products/99999")
        
        assert response.status_code == 404


class TestProductUpdate:
    """Testes para atualização de produtos."""
    
    def test_update_product_success(self, client, mock_db, sample_product, sample_category, admin_headers):
        """Testa atualização de produto com sucesso (rota exige admin)."""
        mock_db["products"].insert_one(sample_product)
        mock_db["categories"].insert_one(sample_category)

        update_data = {
            "titulo": "Título Atualizado",
            "preco": 199.90,
        }

        response = client.put(
            f"/api/products/{sample_product['id']}",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 200
    
    def test_update_product_not_found(self, client, mock_db, admin_headers):
        """Testa atualização de produto inexistente (rota exige admin)."""
        update_data = {
            "titulo": "Título Atualizado",
        }

        response = client.put(
            "/api/products/99999",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 404
    
    def test_update_product_status(self, client, mock_db, sample_product, sample_category, admin_headers):
        """Testa atualização de status do produto (rota exige admin)."""
        mock_db["products"].insert_one(sample_product)
        mock_db["categories"].insert_one(sample_category)

        update_data = {
            "status": "vendido",
        }

        response = client.put(
            f"/api/products/{sample_product['id']}",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=admin_headers,
        )

        assert response.status_code == 200


class TestProductDelete:
    """Testes para exclusão de produtos."""
    
    def test_delete_product_success(self, client, mock_db, sample_product, admin_headers):
        """Testa exclusão de produto (rota exige admin)."""
        mock_db["products"].insert_one(sample_product)

        response = client.delete(
            f"/api/products/{sample_product['id']}", headers=admin_headers
        )

        assert response.status_code == 200
    
    def test_delete_product_not_found(self, client, mock_db, admin_headers):
        """Testa exclusão de produto inexistente (rota exige admin)."""
        response = client.delete("/api/products/99999", headers=admin_headers)

        assert response.status_code == 404


class TestProductsByCategory:
    """Testes para produtos por categoria."""
    
    def test_get_products_by_category(self, client, mock_db, sample_product):
        """Testa obter produtos por categoria."""
        mock_db["products"].insert_one(sample_product)
        
        response = client.get(f"/api/products/category/{sample_product['categoria']}")
        
        assert response.status_code == 200
    
    def test_get_products_by_category_not_found(self, client, mock_db):
        """Testa categoria sem produtos."""
        response = client.get("/api/products/category/CategoriaInexistente")
        
        # Retorna 404 quando não há produtos
        assert response.status_code == 404
