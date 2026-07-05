"""
Testes para rotas de favoritos.
Exigem JWT (Authorization: Bearer); a identidade vem do token (id=1).
Favoritos guardam user_id como string ("1"), casando com str(g.user_id).
"""
import pytest
import json
from datetime import datetime


class TestFavoritesList:
    """Testes para listagem de favoritos."""

    def test_list_favorites_empty(self, client, mock_db, auth_headers):
        """Testa listagem quando não há favoritos."""
        response = client.get("/api/favorites", headers=auth_headers)

        assert response.status_code == 200

    def test_list_favorites_with_data(self, client, mock_db, sample_product, auth_headers):
        """Testa listagem com favoritos cadastrados."""
        mock_db["products"].insert_one(sample_product)
        mock_db["favorites"].insert_one({
            "user_id": "1",
            "product_id": sample_product["id"],
            "created_at": datetime.utcnow(),
        })

        response = client.get("/api/favorites", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] >= 1


class TestFavoriteAdd:
    """Testes para adicionar favorito."""

    def test_add_favorite_success(self, client, mock_db, sample_product, auth_headers):
        """Testa adicionar produto aos favoritos."""
        mock_db["products"].insert_one(sample_product)

        favorite_data = {
            "product_id": sample_product["id"],
        }

        response = client.post(
            "/api/favorites",
            data=json.dumps(favorite_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]

    def test_add_favorite_duplicate(self, client, mock_db, sample_product, auth_headers):
        """Testa adicionar favorito duplicado."""
        mock_db["products"].insert_one(sample_product)
        mock_db["favorites"].insert_one({
            "user_id": "1",
            "product_id": sample_product["id"],
            "created_at": datetime.utcnow(),
        })

        favorite_data = {
            "product_id": sample_product["id"],
        }

        response = client.post(
            "/api/favorites",
            data=json.dumps(favorite_data),
            content_type="application/json",
            headers=auth_headers,
        )

        # Produto já favoritado deve retornar 409
        assert response.status_code == 409

    def test_add_favorite_requires_auth(self, client, mock_db, sample_product):
        """Testa adicionar sem token -> 401."""
        mock_db["products"].insert_one(sample_product)

        favorite_data = {
            "product_id": sample_product["id"],
        }

        response = client.post(
            "/api/favorites",
            data=json.dumps(favorite_data),
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_add_favorite_missing_product_id(self, client, mock_db, auth_headers):
        """Testa adicionar sem product_id."""
        favorite_data = {}

        response = client.post(
            "/api/favorites",
            data=json.dumps(favorite_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestFavoriteRemove:
    """Testes para remover favorito."""

    def test_remove_favorite_success(self, client, mock_db, sample_product, auth_headers):
        """Testa remover produto dos favoritos."""
        mock_db["products"].insert_one(sample_product)
        mock_db["favorites"].insert_one({
            "user_id": "1",
            "product_id": sample_product["id"],
            "created_at": datetime.utcnow(),
        })

        response = client.delete(
            f"/api/favorites/{sample_product['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_remove_favorite_not_found(self, client, mock_db, auth_headers):
        """Testa remover favorito inexistente."""
        response = client.delete("/api/favorites/99999", headers=auth_headers)

        assert response.status_code == 404


class TestFavoriteToggle:
    """Testes para alternar favorito."""

    def test_toggle_favorite_add(self, client, mock_db, sample_product, auth_headers):
        """Testa toggle quando produto não é favorito."""
        mock_db["products"].insert_one(sample_product)

        toggle_data = {
            "product_id": sample_product["id"],
        }

        response = client.post(
            "/api/favorites/toggle",
            data=json.dumps(toggle_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]
        data = response.get_json()
        assert data["is_favorited"] is True

    def test_toggle_favorite_remove(self, client, mock_db, sample_product, auth_headers):
        """Testa toggle quando produto já é favorito."""
        mock_db["products"].insert_one(sample_product)
        mock_db["favorites"].insert_one({
            "user_id": "1",
            "product_id": sample_product["id"],
            "created_at": datetime.utcnow(),
        })

        toggle_data = {
            "product_id": sample_product["id"],
        }

        response = client.post(
            "/api/favorites/toggle",
            data=json.dumps(toggle_data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["is_favorited"] is False


class TestFavoriteCheck:
    """Testes para verificar se é favorito."""

    def test_check_is_favorite_true(self, client, mock_db, sample_product, auth_headers):
        """Testa verificação quando é favorito."""
        mock_db["products"].insert_one(sample_product)
        mock_db["favorites"].insert_one({
            "user_id": "1",
            "product_id": sample_product["id"],
            "created_at": datetime.utcnow(),
        })

        response = client.get(
            f"/api/favorites/check/{sample_product['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["is_favorited"] is True

    def test_check_is_favorite_false(self, client, mock_db, sample_product, auth_headers):
        """Testa verificação quando não é favorito."""
        mock_db["products"].insert_one(sample_product)

        response = client.get(
            f"/api/favorites/check/{sample_product['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["is_favorited"] is False
