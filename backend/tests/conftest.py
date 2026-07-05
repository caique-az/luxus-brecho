"""
Configuração de fixtures para testes do backend.
"""
import pytest
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


class MockCollection:
    """Mock para coleções do MongoDB."""
    
    def __init__(self):
        self.data = []
        self.counter = 0
    
    def find(self, query=None, projection=None):
        if query is None:
            return MockCursor(self.data.copy())
        
        results = []
        for doc in self.data:
            match = True
            for key, value in query.items():
                if key == "$or":
                    or_match = False
                    for condition in value:
                        if all(doc.get(k) == v for k, v in condition.items()):
                            or_match = True
                            break
                    if not or_match:
                        match = False
                elif key == "$text":
                    # Busca textual simplificada
                    search_term = value.get("$search", "").lower()
                    titulo = str(doc.get("titulo", "")).lower()
                    descricao = str(doc.get("descricao", "")).lower()
                    if search_term not in titulo and search_term not in descricao:
                        match = False
                elif isinstance(value, dict):
                    # Suporte a operadores como $in, $ne, etc.
                    if "$in" in value:
                        if doc.get(key) not in value["$in"]:
                            match = False
                    elif "$ne" in value:
                        if doc.get(key) == value["$ne"]:
                            match = False
                    elif "$gt" in value:
                        if not (doc.get(key) is not None and doc.get(key) > value["$gt"]):
                            match = False
                    elif "$gte" in value:
                        if not (doc.get(key) is not None and doc.get(key) >= value["$gte"]):
                            match = False
                    elif "$lt" in value:
                        if not (doc.get(key) is not None and doc.get(key) < value["$lt"]):
                            match = False
                    elif "$lte" in value:
                        if not (doc.get(key) is not None and doc.get(key) <= value["$lte"]):
                            match = False
                    elif "$regex" in value:
                        import re
                        pattern = value["$regex"]
                        options = value.get("$options", "")
                        flags = re.IGNORECASE if "i" in options else 0
                        if not re.search(pattern, str(doc.get(key, "")), flags):
                            match = False
                    else:
                        if doc.get(key) != value:
                            match = False
                elif doc.get(key) != value:
                    match = False
                    break
            if match:
                results.append(doc)
        
        return MockCursor(results)
    
    def find_one(self, query=None):
        if query is None and self.data:
            return self.data[0]
        
        for doc in self.data:
            match = True
            for key, value in query.items():
                if doc.get(key) != value:
                    match = False
                    break
            if match:
                return doc
        return None
    
    def insert_one(self, document):
        doc_copy = document.copy()
        if "_id" not in doc_copy:
            doc_copy["_id"] = f"mock_id_{len(self.data)}"
        self.data.append(doc_copy)
        
        result = MagicMock()
        result.inserted_id = doc_copy["_id"]
        return result
    
    def update_one(self, query, update, upsert=False):
        doc = self.find_one(query)
        result = MagicMock()
        
        if doc:
            if "$set" in update:
                doc.update(update["$set"])
            if "$inc" in update:
                for key, value in update["$inc"].items():
                    doc[key] = doc.get(key, 0) + value
            if "$push" in update:
                for key, value in update["$push"].items():
                    if key not in doc:
                        doc[key] = []
                    doc[key].append(value)
            if "$pull" in update:
                for key, value in update["$pull"].items():
                    if key in doc:
                        doc[key] = [item for item in doc[key] if not all(
                            item.get(k) == v for k, v in value.items()
                        )]
            result.matched_count = 1
            result.modified_count = 1
        elif upsert:
            new_doc = query.copy()
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$inc" in update:
                for key, value in update["$inc"].items():
                    new_doc[key] = value
            self.data.append(new_doc)
            result.matched_count = 0
            result.modified_count = 0
            result.upserted_id = new_doc.get("_id", f"mock_id_{len(self.data)}")
        else:
            result.matched_count = 0
            result.modified_count = 0

        return result

    def update_many(self, query, update, upsert=False):
        matched = list(self.find(query))
        result = MagicMock()
        for doc in matched:
            if "$set" in update:
                doc.update(update["$set"])
            if "$inc" in update:
                for key, value in update["$inc"].items():
                    doc[key] = doc.get(key, 0) + value
            if "$push" in update:
                for key, value in update["$push"].items():
                    doc.setdefault(key, []).append(value)
            if "$pull" in update:
                for key, value in update["$pull"].items():
                    if key in doc:
                        doc[key] = [item for item in doc[key] if not all(
                            item.get(k) == v for k, v in value.items()
                        )]
        result.matched_count = len(matched)
        result.modified_count = len(matched)
        return result

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        doc = self.find_one(query)
        
        if doc:
            if "$inc" in update:
                for key, value in update["$inc"].items():
                    doc[key] = doc.get(key, 0) + value
            if "$set" in update:
                doc.update(update["$set"])
            return doc
        elif upsert:
            new_doc = query.copy()
            if "$inc" in update:
                for key, value in update["$inc"].items():
                    new_doc[key] = value
            if "$set" in update:
                new_doc.update(update["$set"])
            self.data.append(new_doc)
            return new_doc
        
        return None
    
    def delete_one(self, query):
        result = MagicMock()
        for i, doc in enumerate(self.data):
            match = True
            for key, value in query.items():
                if doc.get(key) != value:
                    match = False
                    break
            if match:
                self.data.pop(i)
                result.deleted_count = 1
                return result
        
        result.deleted_count = 0
        return result
    
    def delete_many(self, query):
        result = MagicMock()
        deleted = 0
        self.data = [doc for doc in self.data if not all(
            doc.get(k) == v for k, v in query.items()
        )]
        result.deleted_count = deleted
        return result
    
    def count_documents(self, query=None):
        if query is None:
            return len(self.data)
        return len(list(self.find(query)))
    
    def create_index(self, *args, **kwargs):
        pass


class MockCursor:
    """Mock para cursor do MongoDB."""
    
    def __init__(self, data):
        self.data = data
        self._skip = 0
        self._limit = None
        self._sort_key = None
        self._sort_order = 1
    
    def skip(self, n):
        self._skip = n
        return self
    
    def limit(self, n):
        self._limit = n
        return self
    
    def sort(self, key, order=1):
        if isinstance(key, str):
            self._sort_key = key
            self._sort_order = order
        return self
    
    def __iter__(self):
        data = self.data[self._skip:]
        if self._limit:
            data = data[:self._limit]
        return iter(data)
    
    def __list__(self):
        return list(self.__iter__())


class MockDatabase:
    """Mock para banco de dados MongoDB."""
    
    def __init__(self):
        self.collections = {}
    
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]
    
    def __getattr__(self, name):
        """Permite acesso via db.products, db.users, etc."""
        if name == 'collections':
            raise AttributeError(name)
        return self[name]
    
    def list_collection_names(self):
        return list(self.collections.keys())
    
    def command(self, *args, **kwargs):
        return {"ok": 1}
    
    def create_collection(self, name, **kwargs):
        """Cria uma coleção."""
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]


@pytest.fixture
def app():
    """Cria instância da aplicação para testes."""
    # Configura variáveis de ambiente para teste
    os.environ["FLASK_DEBUG"] = "False"
    os.environ["SECRET_KEY"] = "test-secret-key"
    
    # Cria app com mock do banco
    with patch.dict(os.environ, {"MONGODB_URI": ""}):
        test_app = create_app()
    
    # Substitui o banco por mock
    test_app.db = MockDatabase()
    test_app.config["TESTING"] = True
    
    yield test_app


@pytest.fixture
def client(app):
    """Cria cliente de teste."""
    return app.test_client()


@pytest.fixture
def mock_db(app):
    """Retorna o banco de dados mockado."""
    return app.db


@pytest.fixture
def admin_headers():
    """Header Authorization com um JWT de administrador válido."""
    from app.services.jwt_service import create_access_token
    token = create_access_token(user_id=999, user_type="Administrador", email="admin@teste.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers():
    """Header Authorization com um JWT de cliente válido (id=1)."""
    from app.services.jwt_service import create_access_token
    token = create_access_token(user_id=1, user_type="Cliente", email="teste@email.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_user():
    """Retorna dados de usuário de exemplo."""
    return {
        "id": 1,
        "nome": "Usuário Teste",
        "email": "teste@email.com",
        "senha_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qNQJqhN8/X4.qN",
        "tipo": "Cliente",
        "ativo": True,
        "email_confirmado": True,
        "data_criacao": datetime.utcnow(),
        "data_atualizacao": datetime.utcnow(),
    }


@pytest.fixture
def sample_admin():
    """Retorna dados de administrador de exemplo."""
    return {
        "id": 2,
        "nome": "Admin Teste",
        "email": "admin@email.com",
        "senha_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qNQJqhN8/X4.qN",
        "tipo": "Administrador",
        "ativo": True,
        "email_confirmado": True,
        "data_criacao": datetime.utcnow(),
        "data_atualizacao": datetime.utcnow(),
    }


@pytest.fixture
def sample_product():
    """Retorna dados de produto de exemplo."""
    return {
        "id": 1,
        "titulo": "Produto Teste",
        "descricao": "Descrição do produto teste com mais de 10 caracteres",
        "preco": 99.90,
        "categoria": "Roupas",
        "tamanho": "M",
        "condicao": "Novo",
        "status": "disponivel",
        "imagem": "https://example.com/image.jpg",
        "destaque": False,
        "data_criacao": datetime.utcnow(),
        "data_atualizacao": datetime.utcnow(),
    }


@pytest.fixture
def sample_category():
    """Retorna dados de categoria de exemplo."""
    return {
        "id": 1,
        "name": "Roupas",
        "description": "Categoria de roupas",
        "active": True,
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_cart_item():
    """Retorna dados de item do carrinho de exemplo."""
    return {
        "product_id": 1,
        "quantity": 1,
    }


@pytest.fixture
def sample_order():
    """Retorna dados de pedido de exemplo."""
    return {
        "id": 1,
        "user_id": 1,
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
                "preco_unitario": 99.90,
                "preco_total": 99.90,
                "titulo": "Produto Teste",
                "imagem_url": "https://example.com/image.jpg",
            }
        ],
        "total": 99.90,
        "status": "confirmado",
        "endereco": {
            "rua": "Rua Teste",
            "numero": "123",
            "complemento": "Apto 1",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "01234-567",
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
