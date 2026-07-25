"""
Serviço de autenticação JWT.
Gerencia criação, validação e refresh de tokens.
"""
from __future__ import annotations
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import request, g, current_app

# Import absoluto (não relativo): este módulo é reimportado isoladamente em
# tests/test_jwt_service.py via spec_from_file_location, contexto em que um
# ``from ..utils...`` não tem pacote pai e falharia.
from app.utils.responses import err


# Configurações JWT
# Sem fallback: um segredo hardcoded no repositório tornaria os tokens de admin
# forjáveis. Falha rápido no startup se a variável de ambiente não estiver definida.
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    raise RuntimeError(
        'JWT_SECRET_KEY não está definida. Defina a variável de ambiente '
        '(veja .env.example) antes de iniciar a aplicação.'
    )
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # Token de acesso expira em 24h
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # Token de refresh expira em 30 dias


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
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),  # Subject (ID do usuário)
        'type': user_type,
        'email': email,
        'iat': now,  # Issued at
        'exp': now + JWT_ACCESS_TOKEN_EXPIRES,  # Expiration
        'token_type': 'access'
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Cria um token de refresh JWT.

    Args:
        user_id: ID do usuário

    Returns:
        Token JWT de refresh codificado
    """
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'iat': now,
        'exp': now + JWT_REFRESH_TOKEN_EXPIRES,
        'token_type': 'refresh'
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Decodifica e valida um token JWT.

    Args:
        token: Token JWT a ser decodificado

    Returns:
        Tupla (sucesso, payload, mensagem_erro)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
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


def get_user_id_from_payload(payload: Dict[str, Any]) -> Optional[int]:
    """
    Lê a claim 'sub' e normaliza para int (convenção única do serviço).

    O token grava 'sub' como str, mas o banco guarda 'id' como int. Toda leitura
    da identidade passa por aqui para que comparações de posse e buscas no banco
    usem sempre int. Retorna None se a claim estiver ausente ou não for numérica.
    """
    try:
        return int(payload['sub'])
    except (KeyError, ValueError, TypeError):
        return None


def _load_fresh_user(user_id: int):
    """Recarrega `tipo`/`ativo` do banco para checar o frescor do privilégio.

    O access token vale por até 24h; sem esta releitura, um admin rebaixado ou
    uma conta desativada manteriam acesso até o token expirar. Relemos o usuário
    do banco (1 query) e o tratamos como fonte da verdade. O token nunca ELEVA
    privilégio (apenas o banco concede admin); o banco só pode REVOGÁ-lo.

    Retorna uma tupla (user, deny):
      - (user, None): usuário ativo encontrado — use `user` como fonte da verdade;
      - (None, None): não há banco acessível, degrada para as claims do token
        (só ocorre em testes isolados de decorator ou com o Mongo fora, situação
        em que as rotas sensíveis já respondem 503 ao tocar o banco);
      - (None, (resposta, status)): negue a requisição com essa resposta.
    """
    db = getattr(current_app, 'db', None)
    if db is None:
        return None, None
    from app.models.user_model import get_collection
    user = get_collection(db).find_one({'id': user_id})
    if not user:
        return None, err('Usuário não encontrado', 401)
    if not user.get('ativo', True):
        return None, err('Conta desativada', 403)
    return user, None


def _set_identity(user_id, user, payload):
    """Popula g.user_id/user_type/user_email para a requisição.

    Usa o `user` do banco (fonte da verdade) quando disponível e degrada para as
    claims do token quando não há banco (ver `_load_fresh_user`). Centraliza o
    fallback que antes era copiado nos três decorators.
    """
    g.user_id = user_id
    g.user_type = user.get('tipo') if user else payload.get('type')
    g.user_email = user.get('email') if user else payload.get('email')


def jwt_required(f):
    """
    Decorator que exige autenticação JWT válida.
    Adiciona user_id, user_type e user_email ao objeto g do Flask.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()

        if not token:
            return err('Token de autenticação não fornecido', 401)

        success, payload, error = decode_token(token)

        if not success:
            return err(error, 401)

        if payload.get('token_type') != 'access':
            return err('Tipo de token inválido', 401)

        # Adiciona informações do usuário ao contexto da requisição
        user_id = get_user_id_from_payload(payload)
        if user_id is None:
            return err('Token inválido: identificação de usuário ausente', 401)

        # Frescor: rejeita conta inexistente/desativada e usa o banco como fonte
        # da verdade para tipo/email (degrada para as claims se não houver banco).
        user, deny = _load_fresh_user(user_id)
        if deny:
            return deny

        _set_identity(user_id, user, payload)

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
                g.user_id = get_user_id_from_payload(payload)
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
            return err('Token de autenticação não fornecido', 401)

        success, payload, error = decode_token(token)

        if not success:
            return err(error, 401)

        if payload.get('token_type') != 'access':
            return err('Tipo de token inválido', 401)

        # 1º gate (barato): o token precisa reivindicar admin. Um token nunca
        # eleva privilégio, então quem não reivindica admin já é barrado aqui.
        if payload.get('type') != 'Administrador':
            return err('Acesso negado. Requer privilégios de administrador', 403)

        user_id = get_user_id_from_payload(payload)
        if user_id is None:
            return err('Token inválido: identificação de usuário ausente', 401)

        # 2º gate (frescor): o banco confirma que ainda é admin e está ativo.
        # Um admin rebaixado ou desativado perde o acesso na próxima requisição.
        user, deny = _load_fresh_user(user_id)
        if deny:
            return deny
        if user is not None and user.get('tipo') != 'Administrador':
            return err('Acesso negado. Requer privilégios de administrador', 403)

        _set_identity(user_id, user, payload)

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
                return err('Token de autenticação não fornecido', 401)

            success, payload, error = decode_token(token)

            if not success:
                return err(error, 401)

            if payload.get('token_type') != 'access':
                return err('Tipo de token inválido', 401)

            user_id = get_user_id_from_payload(payload)
            if user_id is None:
                return err('Token inválido: identificação de usuário ausente', 401)

            # Frescor: rejeita conta desativada e usa o tipo do banco (fonte da
            # verdade) para o bypass de admin — admin rebaixado perde o bypass.
            user, deny = _load_fresh_user(user_id)
            if deny:
                return deny

            _set_identity(user_id, user, payload)

            # Verifica se é admin ou dono do recurso (comparação int vs int)
            resource_user_id = kwargs.get(user_id_param)
            if resource_user_id is not None:
                try:
                    resource_user_id = int(resource_user_id)
                except (ValueError, TypeError):
                    resource_user_id = None

            if g.user_type != 'Administrador' and g.user_id != resource_user_id:
                return err('Acesso negado. Você não tem permissão para este recurso', 403)

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

    user_id = get_user_id_from_payload(payload)
    if user_id is None:
        return False, None, 'Token de refresh inválido'

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
