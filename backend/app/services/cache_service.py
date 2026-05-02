"""
Sistema de cache para melhorar performance.
"""
import json
import hashlib
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Cache simples em memória (substituir por Redis em produção)
_cache_store = {}
_cache_expiry = {}


def _generate_key(*args, **kwargs) -> str:
    """Gera chave única baseada nos argumentos."""
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cache(key: str) -> Optional[Any]:
    """
    Obtém valor do cache.
    
    Args:
        key: Chave do cache
        
    Returns:
        Valor do cache ou None se não existir/expirado
    """
    # Verifica se existe e não expirou
    if key in _cache_store:
        expiry = _cache_expiry.get(key)
        if expiry and datetime.now() < expiry:
            logger.debug(f"Cache hit: {key}")
            return _cache_store[key]
        else:
            # Remove cache expirado
            del _cache_store[key]
            if key in _cache_expiry:
                del _cache_expiry[key]
            logger.debug(f"Cache expired: {key}")
    
    logger.debug(f"Cache miss: {key}")
    return None


def set_cache(key: str, value: Any, ttl: int = 300):
    """
    Define valor no cache.
    
    Args:
        key: Chave do cache
        value: Valor a ser armazenado
        ttl: Tempo de vida em segundos (default: 5 minutos)
    """
    _cache_store[key] = value
    _cache_expiry[key] = datetime.now() + timedelta(seconds=ttl)
    logger.debug(f"Cache set: {key} (TTL: {ttl}s)")


def delete_cache(key: str):
    """
    Remove item do cache.
    
    Args:
        key: Chave do cache
    """
    if key in _cache_store:
        del _cache_store[key]
    if key in _cache_expiry:
        del _cache_expiry[key]
    logger.debug(f"Cache deleted: {key}")


def clear_cache():
    """Limpa todo o cache."""
    _cache_store.clear()
    _cache_expiry.clear()
    logger.info("Cache cleared")


def cache_result(ttl: int = 300, key_prefix: str = None):
    """
    Decorator para cachear resultado de funções.
    
    Args:
        ttl: Tempo de vida do cache em segundos
        key_prefix: Prefixo opcional para a chave
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gera chave baseada na função e argumentos
            cache_key_parts = [key_prefix or func.__name__]
            
            # Adiciona argumentos à chave
            if args:
                cache_key_parts.append(_generate_key(*args))
            if kwargs:
                cache_key_parts.append(_generate_key(**kwargs))
            
            cache_key = ':'.join(cache_key_parts)
            
            # Tenta obter do cache
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Executa função e cacheia resultado
            result = func(*args, **kwargs)
            set_cache(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_pattern(pattern: str):
    """
    Invalida cache baseado em padrão.
    
    Args:
        pattern: Padrão de chave para invalidar
    """
    keys_to_delete = [
        key for key in _cache_store.keys()
        if pattern in key
    ]
    
    for key in keys_to_delete:
        delete_cache(key)
    
    logger.info(f"Invalidated {len(keys_to_delete)} cache entries with pattern: {pattern}")


# Cache específico para produtos
def cache_product(product_id: int, product_data: dict, ttl: int = 600):
    """Cacheia dados de um produto."""
    key = f"product:{product_id}"
    set_cache(key, product_data, ttl)


def get_cached_product(product_id: int) -> Optional[dict]:
    """Obtém produto do cache."""
    key = f"product:{product_id}"
    return get_cache(key)


def invalidate_product_cache(product_id: int = None):
    """
    Invalida cache de produtos.
    Se product_id for None, invalida todos os produtos.
    """
    if product_id:
        delete_cache(f"product:{product_id}")
        invalidate_pattern("products:")  # Invalida listagens
    else:
        invalidate_pattern("product")


# Cache específico para categorias
def cache_categories(categories_data: list, ttl: int = 3600):
    """Cacheia lista de categorias."""
    set_cache("categories:all", categories_data, ttl)


def get_cached_categories() -> Optional[list]:
    """Obtém categorias do cache."""
    return get_cache("categories:all")


def invalidate_categories_cache():
    """Invalida cache de categorias."""
    invalidate_pattern("categories:")


# Cache específico para carrinho
def cache_cart(user_id: int, cart_data: dict, ttl: int = 1800):
    """Cacheia dados do carrinho."""
    key = f"cart:{user_id}"
    set_cache(key, cart_data, ttl)


def get_cached_cart(user_id: int) -> Optional[dict]:
    """Obtém carrinho do cache."""
    key = f"cart:{user_id}"
    return get_cache(key)


def invalidate_cart_cache(user_id: int):
    """Invalida cache do carrinho."""
    delete_cache(f"cart:{user_id}")


# Cache específico para usuários
def cache_user(user_id: int, user_data: dict, ttl: int = 900):
    """Cacheia dados do usuário."""
    key = f"user:{user_id}"
    # Remove senha do cache por segurança
    safe_user_data = {k: v for k, v in user_data.items() if k != 'senha_hash'}
    set_cache(key, safe_user_data, ttl)


def get_cached_user(user_id: int) -> Optional[dict]:
    """Obtém usuário do cache."""
    key = f"user:{user_id}"
    return get_cache(key)


def invalidate_user_cache(user_id: int):
    """Invalida cache do usuário."""
    delete_cache(f"user:{user_id}")


# Estatísticas do cache
def get_cache_stats() -> dict:
    """Retorna estatísticas do cache."""
    total_items = len(_cache_store)
    expired_items = sum(
        1 for key, expiry in _cache_expiry.items()
        if datetime.now() >= expiry
    )
    
    return {
        'total_items': total_items,
        'active_items': total_items - expired_items,
        'expired_items': expired_items,
        'cache_keys': list(_cache_store.keys())[:10]  # Primeiras 10 chaves
    }
