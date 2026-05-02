"""
Decorators customizados para a aplicação.
"""
from functools import wraps
from flask import request, jsonify, g, current_app
import logging

logger = logging.getLogger(__name__)


def validate_json(*required_fields):
    """
    Decorator para validar campos JSON obrigatórios.
    
    Args:
        required_fields: Lista de campos obrigatórios
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            json_data = request.get_json(silent=True)
            
            if not json_data:
                return jsonify({'error': 'JSON é obrigatório'}), 400
            
            missing_fields = []
            for field in required_fields:
                if field not in json_data:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'error': 'Campos obrigatórios ausentes',
                    'missing_fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator que exige que o usuário seja administrador.
    Deve ser usado APÓS jwt_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_type = getattr(g, 'user_type', None)
        
        if not user_type:
            return jsonify({'error': 'Autenticação necessária'}), 401
        
        if user_type != 'Administrador':
            return jsonify({
                'error': 'Acesso negado',
                'message': 'Apenas administradores podem acessar este recurso'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def log_request(action):
    """
    Decorator para logar requisições importantes.
    
    Args:
        action: Descrição da ação
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = getattr(g, 'user_id', 'anonymous')
            ip = request.remote_addr
            
            logger.info(f"[{action}] User: {user_id}, IP: {ip}, Path: {request.path}")
            
            result = f(*args, **kwargs)
            
            # Log resultado
            if hasattr(result, 'status_code'):
                logger.info(f"[{action}] Completed with status: {result.status_code}")
            
            return result
        return decorated_function
    return decorator



def handle_errors(f):
    """
    Decorator para tratar erros de forma consistente.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Erro de validação em {request.path}: {e}")
            return jsonify({'error': str(e)}), 400
        except KeyError as e:
            logger.warning(f"Campo ausente em {request.path}: {e}")
            return jsonify({'error': f'Campo obrigatório ausente: {e}'}), 400
        except Exception as e:
            logger.error(f"Erro não tratado em {request.path}: {e}", exc_info=True)
            
            # Em produção, não expor detalhes do erro
            if current_app.config.get('DEBUG'):
                return jsonify({
                    'error': 'Erro interno do servidor',
                    'details': str(e)
                }), 500
            else:
                return jsonify({'error': 'Erro interno do servidor'}), 500
    
    return decorated_function


def cache_response(timeout=300, key_prefix='view'):
    """
    Decorator para cachear respostas.
    
    Args:
        timeout: Tempo de cache em segundos
        key_prefix: Prefixo para a chave de cache
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Por enquanto, apenas retorna a função original
            # TODO: Implementar cache com Redis quando disponível
            return f(*args, **kwargs)
        return decorated_function
    return decorator
