"""
Configuração de índices do MongoDB para otimização de performance.
"""
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import OperationFailure
import logging

logger = logging.getLogger(__name__)


def create_indexes(db):
    """
    Cria todos os índices necessários para otimização.
    
    Args:
        db: Instância do banco MongoDB
    """
    try:
        # Índices para produtos
        create_product_indexes(db)
        
        # Índices para usuários
        create_user_indexes(db)
        
        # Índices para categorias
        create_category_indexes(db)
        
        # Índices para carrinho
        create_cart_indexes(db)
        
        # Índices para favoritos
        create_favorite_indexes(db)
        
        # Índices para pedidos
        create_order_indexes(db)
        
        logger.info("✅ Todos os índices foram criados com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar índices: {e}")
        raise


def create_product_indexes(db):
    """Cria índices para a coleção de produtos."""
    coll = db["products"]
    
    # Índice único para ID
    coll.create_index([("id", ASCENDING)], unique=True, name="idx_product_id")
    
    # Índice para categoria (queries frequentes por categoria)
    coll.create_index([("categoria", ASCENDING)], name="idx_product_category")
    
    # Índice para status (filtrar disponíveis)
    coll.create_index([("status", ASCENDING)], name="idx_product_status")
    
    # Índice composto para categoria + status (queries combinadas)
    coll.create_index(
        [("categoria", ASCENDING), ("status", ASCENDING)], 
        name="idx_product_category_status"
    )
    
    # Índice para produtos em destaque
    coll.create_index([("destaque", DESCENDING)], name="idx_product_featured")
    
    # Índice de texto para busca full-text
    coll.create_index(
        [("titulo", TEXT), ("descricao", TEXT)], 
        name="idx_product_text",
        default_language="portuguese"
    )
    
    # Índice para ordenação por preço
    coll.create_index([("preco", ASCENDING)], name="idx_product_price_asc")
    coll.create_index([("preco", DESCENDING)], name="idx_product_price_desc")
    
    # Índice para data de criação (ordenação por novidades)
    coll.create_index([("data_criacao", DESCENDING)], name="idx_product_created")
    
    logger.info("✅ Índices de produtos criados")


def create_user_indexes(db):
    """Cria índices para a coleção de usuários."""
    coll = db["users"]
    
    # Índice único para ID
    coll.create_index([("id", ASCENDING)], unique=True, name="idx_user_id")
    
    # Índice único para email
    coll.create_index([("email", ASCENDING)], unique=True, name="idx_user_email")
    
    # Índice para tipo de usuário
    coll.create_index([("tipo", ASCENDING)], name="idx_user_type")
    
    # Índice para status ativo
    coll.create_index([("ativo", ASCENDING)], name="idx_user_active")
    
    # Índice composto para tipo + ativo (admins ativos)
    coll.create_index(
        [("tipo", ASCENDING), ("ativo", ASCENDING)], 
        name="idx_user_type_active"
    )
    
    # Índice para email confirmado
    coll.create_index([("email_confirmado", ASCENDING)], name="idx_user_email_confirmed")
    
    # Índice para token de confirmação
    coll.create_index([("token_confirmacao", ASCENDING)], sparse=True, name="idx_user_confirm_token")
    
    # Índice para token de reset de senha
    coll.create_index([("reset_token", ASCENDING)], sparse=True, name="idx_user_reset_token")
    
    # Índice de texto para busca por nome
    coll.create_index([("nome", TEXT)], name="idx_user_text")
    
    logger.info("✅ Índices de usuários criados")


def create_category_indexes(db):
    """Cria índices para a coleção de categorias."""
    coll = db["categories"]
    
    # Índice único para ID
    coll.create_index([("id", ASCENDING)], unique=True, name="idx_category_id")
    
    # Índice único para nome
    coll.create_index([("nome", ASCENDING)], unique=True, name="idx_category_name")
    
    # Índice para ordenação
    coll.create_index([("ordem", ASCENDING)], name="idx_category_order")
    
    # Índice para status ativo
    coll.create_index([("ativo", ASCENDING)], name="idx_category_active")
    
    logger.info("✅ Índices de categorias criados")


def create_cart_indexes(db):
    """Cria índices para a coleção de carrinhos."""
    coll = db["carts"]
    
    # Índice único para user_id (um carrinho por usuário)
    coll.create_index([("user_id", ASCENDING)], unique=True, name="idx_cart_user")
    
    # Índice para items.product_id (busca rápida de produtos no carrinho)
    coll.create_index([("items.product_id", ASCENDING)], name="idx_cart_products")
    
    # TTL index para remover carrinhos abandonados após 30 dias (serve também para ordenação)
    coll.create_index(
        [("updated_at", ASCENDING)], 
        expireAfterSeconds=2592000,  # 30 dias
        name="idx_cart_ttl"
    )
    
    logger.info("✅ Índices de carrinho criados")


def create_favorite_indexes(db):
    """Cria índices para a coleção de favoritos."""
    coll = db["favorites"]
    
    # Índice composto único (um usuário não pode favoritar o mesmo produto duas vezes)
    coll.create_index(
        [("user_id", ASCENDING), ("product_id", ASCENDING)], 
        unique=True, 
        name="idx_favorite_user_product"
    )
    
    # Índice para buscar favoritos de um usuário
    coll.create_index([("user_id", ASCENDING)], name="idx_favorite_user")
    
    # Índice para buscar quantos favoritaram um produto
    coll.create_index([("product_id", ASCENDING)], name="idx_favorite_product")
    
    # Índice para data de criação
    coll.create_index([("created_at", DESCENDING)], name="idx_favorite_created")
    
    logger.info("✅ Índices de favoritos criados")


def create_order_indexes(db):
    """Cria índices para a coleção de pedidos."""
    coll = db["orders"]
    
    # Índice único para ID do pedido
    coll.create_index([("id", ASCENDING)], unique=True, name="idx_order_id")
    
    # Índice para buscar pedidos de um usuário
    coll.create_index([("user_id", ASCENDING)], name="idx_order_user")
    
    # Índice para status do pedido
    coll.create_index([("status", ASCENDING)], name="idx_order_status")
    
    # Índice composto para usuário + status
    coll.create_index(
        [("user_id", ASCENDING), ("status", ASCENDING)], 
        name="idx_order_user_status"
    )
    
    # Índice para data de criação (ordenação)
    coll.create_index([("created_at", DESCENDING)], name="idx_order_created")
    
    # Índice para produtos nos pedidos
    coll.create_index([("items.product_id", ASCENDING)], name="idx_order_products")
    
    # Índice para valor total (relatórios)
    coll.create_index([("total", DESCENDING)], name="idx_order_total")
    
    # Índice composto para relatórios por período
    coll.create_index(
        [("created_at", DESCENDING), ("status", ASCENDING), ("total", DESCENDING)], 
        name="idx_order_reports"
    )
    
    logger.info("✅ Índices de pedidos criados")


