"""
Serviço de autenticação JWT.
Gerencia criação, validação e refresh de tokens.
"""
import os
import jwt
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import request, jsonify, g, current_app
import logging

logger = logging.getLogger(__name__)

def _get_config():
    """Obtém configuração JWT do app ou usa defaults seguros."""
    try:
        from config import get_config
        cfg = get_config()
        return {
            'secret_key': cfg.JWT_SECRET_KEY,
            'algorithm': cfg.JWT_ALGORITHM,
            'access_expires': cfg.JWT_ACCESS_TOKEN_EXPIRES,
            'refresh_expires': cfg.JWT_REFRESH_TOKEN_EXPIRES
        }
    except:
        # Fallback apenas para desenvolvimento
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            return {
                'secret_key': os.environ.get('JWT_SECRET_KEY', 'dev-secret-key'),
                'algorithm': 'HS256',
                'access_expires': timedelta(hours=24),
                'refresh_expires': timedelta(days=30)
            }
        else:
            raise RuntimeError("JWT configuration not available in production")


def create_access_token(user_id: int, user_type: str, email: str) -> str:
    """
    Cria um token de acesso JWT.
    
    Args:
        user_id: ID do usuário
        user_type: Tipo do usuário (Cliente/Administrador)
        email: Email do usuário
        
    Returns:
        Token JWT codificado
    """
    config = _get_config()
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,  # Subject (ID do usuário)
        'type': user_type,
        'email': email,
        'iat': now,  # Issued at
        'exp': now + config['access_expires'],  # Expiration
        'token_type': 'access',
        'jti': hashlib.sha256(f"{user_id}{now.timestamp()}".encode()).hexdigest()[:16]  # JWT ID único
    }
    return jwt.encode(payload, config['secret_key'], algorithm=config['algorithm'])


def create_refresh_token(user_id: int) -> str:
    """
    Cria um token de refresh JWT.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Token JWT de refresh codificado
    """
    config = _get_config()
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'iat': now,
        'exp': now + config['refresh_expires'],
        'token_type': 'refresh',
        'jti': hashlib.sha256(f"{user_id}{now.timestamp()}refresh".encode()).hexdigest()[:16]
    }
    return jwt.encode(payload, config['secret_key'], algorithm=config['algorithm'])


def decode_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Decodifica e valida um token JWT.
    
    Args:
        token: Token JWT a ser decodificado
        
    Returns:
        Tupla (sucesso, payload, mensagem_erro)
    """
    config = _get_config()
    try:
        payload = jwt.decode(token, config['secret_key'], algorithms=[config['algorithm']])
        return True, payload, None
    except jwt.ExpiredSignatureError:
        return False, None, 'Token expirado'
    except jwt.InvalidTokenError as e:
        return False, None, f'Token inválido: {str(e)}'


def get_token_from_header() -> Optional[str]:
    """
    Extrai o token do header Authorization.
    
    Returns:
        Token JWT ou None se não encontrado
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer '
    return None


def jwt_required(f):
    """
    Decorator que exige autenticação JWT válida.
    Adiciona user_id, user_type e user_email ao objeto g do Flask.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        
        if not token:
            return jsonify({'error': 'Token de autenticação não fornecido'}), 401
        
        success, payload, error = decode_token(token)
        
        if not success:
            return jsonify({'error': error}), 401
        
        if payload.get('token_type') != 'access':
            return jsonify({'error': 'Tipo de token inválido'}), 401
        
        # Adiciona informações do usuário ao contexto da requisição
        g.user_id = payload.get('sub')
        g.user_type = payload.get('type')
        g.user_email = payload.get('email')
        
        return f(*args, **kwargs)
    
    return decorated


def jwt_optional(f):
    """
    Decorator que aceita autenticação JWT opcional.
    Se o token for válido, adiciona informações ao objeto g.
    Se não houver token ou for inválido, continua sem autenticação.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        
        if token:
            success, payload, _ = decode_token(token)
            if success and payload.get('token_type') == 'access':
                g.user_id = payload.get('sub')
                g.user_type = payload.get('type')
                g.user_email = payload.get('email')
            else:
                g.user_id = None
                g.user_type = None
                g.user_email = None
        else:
            g.user_id = None
            g.user_type = None
            g.user_email = None
        
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f):
    """
    Decorator que exige que o usuário seja administrador.
    Deve ser usado APÓS jwt_required.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        
        if not token:
            return jsonify({'error': 'Token de autenticação não fornecido'}), 401
        
        success, payload, error = decode_token(token)
        
        if not success:
            return jsonify({'error': error}), 401
        
        if payload.get('token_type') != 'access':
            return jsonify({'error': 'Tipo de token inválido'}), 401
        
        if payload.get('type') != 'Administrador':
            return jsonify({'error': 'Acesso negado. Requer privilégios de administrador'}), 403
        
        g.user_id = payload.get('sub')
        g.user_type = payload.get('type')
        g.user_email = payload.get('email')
        
        return f(*args, **kwargs)
    
    return decorated


def owner_or_admin_required(user_id_param: str = 'user_id'):
    """
    Decorator que exige que o usuário seja o dono do recurso ou administrador.
    
    Args:
        user_id_param: Nome do parâmetro da URL que contém o user_id
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_header()
            
            if not token:
                return jsonify({'error': 'Token de autenticação não fornecido'}), 401
            
            success, payload, error = decode_token(token)
            
            if not success:
                return jsonify({'error': error}), 401
            
            if payload.get('token_type') != 'access':
                return jsonify({'error': 'Tipo de token inválido'}), 401
            
            g.user_id = payload.get('sub')
            g.user_type = payload.get('type')
            g.user_email = payload.get('email')
            
            # Verifica se é admin ou dono do recurso
            resource_user_id = kwargs.get(user_id_param)
            if resource_user_id is not None:
                try:
                    resource_user_id = int(resource_user_id)
                except (ValueError, TypeError):
                    pass
            
            if g.user_type != 'Administrador' and g.user_id != resource_user_id:
                return jsonify({'error': 'Acesso negado. Você não tem permissão para este recurso'}), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def refresh_access_token(refresh_token: str, db) -> Tuple[bool, Optional[Dict[str, str]], Optional[str]]:
    """
    Gera um novo access token usando um refresh token válido.
    
    Args:
        refresh_token: Token de refresh
        db: Conexão com o banco de dados
        
    Returns:
        Tupla (sucesso, tokens, mensagem_erro)
    """
    success, payload, error = decode_token(refresh_token)
    
    if not success:
        return False, None, error
    
    if payload.get('token_type') != 'refresh':
        return False, None, 'Token de refresh inválido'
    
    user_id = payload.get('sub')
    
    # Busca usuário no banco para obter dados atualizados
    from app.models.user_model import get_collection
    users = get_collection(db)
    user = users.find_one({'id': user_id})
    
    if not user:
        return False, None, 'Usuário não encontrado'
    
    if not user.get('ativo', True):
        return False, None, 'Conta desativada'
    
    # Gera novos tokens
    new_access_token = create_access_token(
        user_id=user['id'],
        user_type=user['tipo'],
        email=user['email']
    )
    new_refresh_token = create_refresh_token(user_id=user['id'])
    
    return True, {
        'access_token': new_access_token,
        'refresh_token': new_refresh_token,
        'token_type': 'Bearer',
        'expires_in': int(JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
    }, None
