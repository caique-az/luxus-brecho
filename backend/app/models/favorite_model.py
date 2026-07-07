"""
Modelo e utilidades para a coleção de favoritos.
- Gerencia favoritos dos usuários
- Garante índices no MongoDB
- Valida payloads de favoritos
"""
from typing import Dict, Any, List, Optional, Tuple
from pymongo import ASCENDING
from bson import ObjectId
from datetime import datetime

COLLECTION_NAME = "favorites"


def ensure_indexes(db) -> None:
    """Garante que os índices necessários existam na coleção de favoritos."""
    if db is None:
        return
    
    collection = db[COLLECTION_NAME]
    
    # Índice composto único: um usuário não pode favoritar o mesmo produto duas vezes
    collection.create_index(
        [("user_id", ASCENDING), ("product_id", ASCENDING)],
        unique=True,
        name="user_product_unique"
    )
    
    # Índice para buscar favoritos por usuário
    collection.create_index(
        [("user_id", ASCENDING), ("created_at", ASCENDING)],
        name="user_created"
    )
    
    # Índice para buscar por produto (útil para estatísticas)
    collection.create_index(
        [("product_id", ASCENDING)],
        name="product_idx"
    )


def validate_favorite_payload(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Valida o payload de um favorito.
    
    Args:
        payload: Dicionário com os dados do favorito
        
    Returns:
        Tupla (válido, mensagem_erro)
    """
    if not isinstance(payload, dict):
        return False, "Payload deve ser um objeto"
    
    # Validar product_id
    product_id = payload.get('product_id')
    if not product_id:
        return False, "product_id é obrigatório"
    
    if not isinstance(product_id, int):
        return False, "product_id deve ser um número inteiro"
    
    return True, None


def create_favorite_document(user_id: str, product_id: int) -> Dict[str, Any]:
    """
    Cria um documento de favorito.
    
    Args:
        user_id: ID do usuário (ObjectId como string)
        product_id: ID do produto (int)
        
    Returns:
        Documento do favorito
    """
    return {
        "user_id": user_id,
        "product_id": product_id,
        "created_at": datetime.utcnow()
    }


def add_favorite(db, user_id: str, product_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Adiciona um produto aos favoritos do usuário.
    
    Args:
        db: Instância do banco de dados
        user_id: ID do usuário
        product_id: ID do produto
        
    Returns:
        Tupla (sucesso, mensagem_erro, documento)
    """
    if db is None:
        return False, "Banco de dados não disponível", None
    
    try:
        collection = db[COLLECTION_NAME]
        
        # Verificar se já existe
        existing = collection.find_one({
            "user_id": user_id,
            "product_id": product_id
        })
        
        if existing:
            return False, "Produto já está nos favoritos", None
        
        # Criar documento
        favorite_doc = create_favorite_document(user_id, product_id)
        
        # Inserir
        result = collection.insert_one(favorite_doc)
        favorite_doc['_id'] = result.inserted_id
        
        return True, None, favorite_doc
        
    except Exception as e:
        return False, f"Erro ao adicionar favorito: {str(e)}", None


def remove_favorite(db, user_id: str, product_id: int) -> Tuple[bool, Optional[str]]:
    """
    Remove um produto dos favoritos do usuário.
    
    Args:
        db: Instância do banco de dados
        user_id: ID do usuário
        product_id: ID do produto
        
    Returns:
        Tupla (sucesso, mensagem_erro)
    """
    if db is None:
        return False, "Banco de dados não disponível"
    
    try:
        collection = db[COLLECTION_NAME]
        
        result = collection.delete_one({
            "user_id": user_id,
            "product_id": product_id
        })
        
        if result.deleted_count == 0:
            return False, "Favorito não encontrado"
        
        return True, None
        
    except Exception as e:
        return False, f"Erro ao remover favorito: {str(e)}"


def get_user_favorites(db, user_id: str) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Busca todos os favoritos de um usuário.
    
    Args:
        db: Instância do banco de dados
        user_id: ID do usuário
        
    Returns:
        Tupla (sucesso, mensagem_erro, lista_favoritos)
    """
    if db is None:
        return False, "Banco de dados não disponível", []
    
    try:
        collection = db[COLLECTION_NAME]
        
        favorites = list(collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1))  # Mais recentes primeiro
        
        # Remove o _id interno do Mongo (não deve vazar na resposta da API)
        for fav in favorites:
            fav.pop('_id', None)

        return True, None, favorites
        
    except Exception as e:
        return False, f"Erro ao buscar favoritos: {str(e)}", []


def is_favorited(db, user_id: str, product_id: int) -> bool:
    """
    Verifica se um produto está nos favoritos do usuário.
    
    Args:
        db: Instância do banco de dados
        user_id: ID do usuário
        product_id: ID do produto
        
    Returns:
        True se está favoritado, False caso contrário
    """
    if db is None:
        return False
    
    try:
        collection = db[COLLECTION_NAME]
        
        favorite = collection.find_one({
            "user_id": user_id,
            "product_id": product_id
        })
        
        return favorite is not None
        
    except Exception:
        return False


def get_favorite_count_by_product(db, product_id: int) -> int:
    """
    Conta quantos usuários favoritaram um produto.
    
    Args:
        db: Instância do banco de dados
        product_id: ID do produto
        
    Returns:
        Número de favoritos
    """
    if db is None:
        return 0
    
    try:
        collection = db[COLLECTION_NAME]
        return collection.count_documents({"product_id": product_id})
    except Exception:
        return 0


def clear_user_favorites(db, user_id: str) -> Tuple[bool, Optional[str], int]:
    """
    Remove todos os favoritos de um usuário.
    
    Args:
        db: Instância do banco de dados
        user_id: ID do usuário
        
    Returns:
        Tupla (sucesso, mensagem_erro, quantidade_removida)
    """
    if db is None:
        return False, "Banco de dados não disponível", 0
    
    try:
        collection = db[COLLECTION_NAME]
        
        result = collection.delete_many({"user_id": user_id})
        
        return True, None, result.deleted_count
        
    except Exception as e:
        return False, f"Erro ao limpar favoritos: {str(e)}", 0
