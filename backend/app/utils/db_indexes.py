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


def drop_all_indexes(db):
    """
    Remove todos os índices personalizados (mantém apenas _id).
    Use com cuidado!
    
    Args:
        db: Instância do banco MongoDB
    """
    collections = ["products", "users", "categories", "carts", "favorites", "orders"]
    
    for collection_name in collections:
        try:
            coll = db[collection_name]
            # Lista todos os índices
            indexes = coll.list_indexes()
            
            for index in indexes:
                index_name = index["name"]
                # Não remove o índice padrão _id
                if index_name != "_id_":
                    coll.drop_index(index_name)
                    logger.info(f"Removido índice: {index_name} da coleção {collection_name}")
                    
        except Exception as e:
            logger.warning(f"Erro ao remover índices de {collection_name}: {e}")
    
    logger.info("✅ Todos os índices personalizados foram removidos")


def get_index_stats(db):
    """
    Retorna estatísticas sobre os índices.
    
    Args:
        db: Instância do banco MongoDB
        
    Returns:
        Dict com estatísticas dos índices
    """
    stats = {}
    collections = ["products", "users", "categories", "carts", "favorites", "orders"]
    
    for collection_name in collections:
        try:
            coll = db[collection_name]
            indexes = list(coll.list_indexes())
            
            stats[collection_name] = {
                "total_indexes": len(indexes),
                "indexes": [
                    {
                        "name": idx["name"],
                        "keys": idx["key"],
                        "unique": idx.get("unique", False),
                        "sparse": idx.get("sparse", False),
                        "ttl": idx.get("expireAfterSeconds")
                    }
                    for idx in indexes
                ]
            }
            
        except Exception as e:
            stats[collection_name] = {"error": str(e)}
    
    return stats


def analyze_query_performance(db, collection_name: str, query: dict):
    """
    Analisa a performance de uma query usando explain().
    
    Args:
        db: Instância do banco MongoDB
        collection_name: Nome da coleção
        query: Query a ser analisada
        
    Returns:
        Dict com análise de performance
    """
    try:
        coll = db[collection_name]
        explanation = coll.find(query).explain()
        
        # Extrai métricas importantes
        execution_stats = explanation.get("executionStats", {})
        
        return {
            "query": query,
            "execution_time_ms": execution_stats.get("executionTimeMillis", 0),
            "total_docs_examined": execution_stats.get("totalDocsExamined", 0),
            "total_keys_examined": execution_stats.get("totalKeysExamined", 0),
            "docs_returned": execution_stats.get("nReturned", 0),
            "index_used": execution_stats.get("executionStages", {}).get("indexName"),
            "is_index_scan": execution_stats.get("executionStages", {}).get("stage") == "IXSCAN",
            "is_collection_scan": execution_stats.get("executionStages", {}).get("stage") == "COLLSCAN",
            "performance_rating": _rate_query_performance(execution_stats)
        }
        
    except Exception as e:
        return {"error": str(e)}


def _rate_query_performance(stats):
    """
    Avalia a performance da query.
    
    Args:
        stats: Estatísticas de execução
        
    Returns:
        String com avaliação da performance
    """
    docs_examined = stats.get("totalDocsExamined", 0)
    docs_returned = stats.get("nReturned", 0)
    execution_time = stats.get("executionTimeMillis", 0)
    
    # Se examinou muitos documentos para retornar poucos
    if docs_examined > 0 and docs_returned > 0:
        efficiency = docs_returned / docs_examined
        if efficiency < 0.1:
            return "POOR - Query examinou muitos documentos desnecessários"
        elif efficiency < 0.5:
            return "FAIR - Query pode ser otimizada"
        else:
            return "GOOD - Query eficiente"
    
    # Baseado no tempo de execução
    if execution_time > 100:
        return "SLOW - Query demorou mais de 100ms"
    elif execution_time > 50:
        return "MODERATE - Query demorou entre 50-100ms"
    else:
        return "FAST - Query executou em menos de 50ms"
