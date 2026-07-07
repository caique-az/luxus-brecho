from __future__ import annotations
from flask import request, current_app, g
from app.utils.db import require_db
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import Any, Dict
import re
import time
import secrets
from datetime import datetime, timedelta

from ..utils.pagination import parse_pagination
from ..utils.responses import ok, err
from ..models.user_model import (
    get_collection,
    prepare_new_user,
    prepare_user_update,
    validate_user_payload,
    normalize_user,
    verify_password,
    hash_password,
    validate_password,
    USER_TYPES,
)
from ..services.email_service import send_confirmation_email, send_welcome_email, send_password_reset_email, send_account_deletion_code
from ..services.jwt_service import create_access_token, create_refresh_token, refresh_access_token, JWT_ACCESS_TOKEN_EXPIRES
import random

# Nº máximo de tentativas do código de exclusão antes de invalidá-lo (anti-brute-force)
MAX_DELETION_ATTEMPTS = 5

# Campos removidos ao invalidar um código de exclusão (expirado ou tentativas esgotadas)
_DELETION_UNSET = {"deletion_code": "", "deletion_code_expiration": "", "deletion_attempts": ""}


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serializa documento removendo campos internos."""
    if not doc:
        return {}
    return normalize_user(doc)


@require_db
def list_users():
    """Lista usuários com paginação e filtros."""
    db = current_app.db

    coll = get_collection(db)

    try:
        # Paginação com clamp (page_size limitado; evita .limit() ilimitado)
        page, page_size, skip = parse_pagination(default_page_size=20)

        # Parâmetros de filtro
        tipo = request.args.get("tipo")
        ativo = request.args.get("ativo")
        search = request.args.get("search")

        # Constrói filtro
        filter_query = {}

        if tipo and tipo in USER_TYPES:
            filter_query["tipo"] = tipo

        if ativo is not None:
            filter_query["ativo"] = ativo.lower() == "true"

        if search:
            # Escapa o termo: sem isso, um input como "(a+)+$" vira regex e
            # abre ReDoS (mesmo restrito a admin autenticado).
            safe_search = re.escape(search)
            filter_query["$or"] = [
                {"nome": {"$regex": safe_search, "$options": "i"}},
                {"email": {"$regex": safe_search, "$options": "i"}}
            ]

        # Contagem total
        total = coll.count_documents(filter_query)

        # Busca com paginação
        cursor = coll.find(filter_query).sort("data_criacao", -1).skip(skip).limit(page_size)

        users = [_serialize(doc) for doc in cursor]

        return ok({
            "items": users,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total
            }
        })

    except ValueError as e:
        return err(f"Parâmetros inválidos: {e}")
    except Exception as e:
        current_app.logger.error(f"Erro ao listar usuários: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def get_user(id: int):
    """Busca usuário por ID."""
    db = current_app.db

    coll = get_collection(db)

    try:
        user = coll.find_one({"id": id})
        if not user:
            return err("Usuário não encontrado", 404)

        return ok(_serialize(user))

    except Exception as e:
        current_app.logger.error(f"Erro ao buscar usuário {id}: {e}")
        return err("Erro interno do servidor", 500)


def create_user():
    """Registro público de usuário.

    Sempre cria um Cliente: o `tipo` do payload é ignorado para impedir o
    auto-registro como administrador (escalada de privilégio). A criação de
    administradores tem um caminho próprio, protegido por @admin_required
    (ver create_admin / rota POST /api/users/admin).
    """
    return _create_user_with_tipo("Cliente")


def create_admin():
    """Cria um administrador. A rota é protegida por @admin_required: só um
    admin autenticado consegue criar outro admin."""
    return _create_user_with_tipo("Administrador")


@require_db
def _create_user_with_tipo(tipo: str):
    """Núcleo de criação de usuário. O `tipo` é imposto pelo chamador (nunca vem
    do corpo da requisição), o que garante que o privilégio seja definido pela
    rota — não pelo cliente."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        # O privilégio nunca é decidido pelo payload: o tipo é imposto pela rota.
        payload["tipo"] = tipo

        # Valida payload
        is_valid, error_msg = validate_user_payload(payload)
        if not is_valid:
            return err(error_msg)

        coll = get_collection(db)

        # Verifica se email já existe
        existing_user = coll.find_one({"email": payload["email"].strip().lower()})
        if existing_user:
            return err("Email já está em uso", 409)

        # Prepara dados do usuário
        user_data = prepare_new_user(payload, db)

        # Insere no banco
        result = coll.insert_one(user_data)

        # Busca usuário criado
        created_user = coll.find_one({"_id": result.inserted_id})

        # Envia email de confirmação
        if user_data["token_confirmacao"]:
            is_admin = user_data["tipo"] == "Administrador"
            send_confirmation_email(
                user_data["email"],
                user_data["nome"],
                user_data["token_confirmacao"],
                is_admin=is_admin
            )
            if is_admin:
                message = "Administrador criado com sucesso. Email de confirmação enviado."
            else:
                message = "Usuário criado com sucesso. Verifique seu email para confirmar a conta."
        else:
            message = "Usuário criado com sucesso"

        return ok(
            message=message,
            status=201,
            user=_serialize(created_user),
            email_confirmation_required=user_data["tipo"] == "Cliente"
        )

    except DuplicateKeyError as e:
        if "email" in str(e):
            return err("Email já está em uso", 409)
        return err("Dados duplicados", 409)
    except Exception as e:
        current_app.logger.error(f"Erro ao criar usuário: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def update_user(id: int):
    """Atualiza usuário existente."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        # Valida payload para atualização
        is_valid, error_msg = validate_user_payload(payload, is_update=True)
        if not is_valid:
            return err(error_msg)

        coll = get_collection(db)

        # Verifica se usuário existe
        existing_user = coll.find_one({"id": id})
        if not existing_user:
            return err("Usuário não encontrado", 404)

        # Verifica se email já está em uso por outro usuário
        if "email" in payload:
            email_check = coll.find_one({
                "email": payload["email"].strip().lower(),
                "id": {"$ne": id}
            })
            if email_check:
                return err("Email já está em uso", 409)

        # Prepara dados para atualização
        update_data = prepare_user_update(payload)

        # Atualiza no banco
        result = coll.update_one(
            {"id": id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return err("Usuário não encontrado", 404)

        # Busca usuário atualizado
        updated_user = coll.find_one({"id": id})

        return ok(
            message="Usuário atualizado com sucesso",
            user=_serialize(updated_user)
        )

    except DuplicateKeyError as e:
        if "email" in str(e):
            return err("Email já está em uso", 409)
        return err("Dados duplicados", 409)
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar usuário {id}: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def delete_user(id: int):
    """Exclui usuário (soft delete - marca como inativo)."""
    db = current_app.db

    try:
        coll = get_collection(db)

        # Verifica se usuário existe
        existing_user = coll.find_one({"id": id})
        if not existing_user:
            return err("Usuário não encontrado", 404)

        # Verifica se é o último administrador
        if existing_user.get("tipo") == "Administrador":
            admin_count = coll.count_documents({
                "tipo": "Administrador",
                "ativo": True,
                "id": {"$ne": id}
            })
            if admin_count == 0:
                return err("Não é possível excluir o último administrador")

        # Soft delete - marca como inativo
        result = coll.update_one(
            {"id": id},
            {"$set": {"ativo": False, "data_atualizacao": datetime.utcnow()}}
        )

        if result.matched_count == 0:
            return err("Usuário não encontrado", 404)

        return ok(message="Usuário desativado com sucesso")

    except Exception as e:
        current_app.logger.error(f"Erro ao excluir usuário {id}: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def authenticate_user():
    """Autentica usuário com email e senha."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        email = payload.get("email")
        senha = payload.get("senha")

        if not email or not senha:
            return err("Email e senha são obrigatórios")

        coll = get_collection(db)

        # Busca usuário por email
        user = coll.find_one({"email": email.strip().lower()})

        if not user:
            return err("Credenciais inválidas", 401)

        # Verifica senha
        if not verify_password(senha, user["senha_hash"]):
            return err("Credenciais inválidas", 401)

        # Verifica se o email foi confirmado
        if not user.get("email_confirmado", False):
            return err(
                "Email não confirmado. Verifique sua caixa de entrada.",
                403,
                email_not_confirmed=True
            )

        # Verifica se o usuário está ativo
        if not user.get("ativo", False):
            return err("Conta desativada. Entre em contato com o suporte.", 403)

        # Gera tokens JWT
        access_token = create_access_token(
            user_id=user['id'],
            user_type=user['tipo'],
            email=user['email']
        )
        refresh_token = create_refresh_token(user_id=user['id'])

        return ok(
            message="Autenticação realizada com sucesso",
            user=_serialize(user),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=int(JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
        )

    except Exception as e:
        current_app.logger.error(f"Erro na autenticação: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def refresh_token_endpoint():
    """Renova o access token usando um refresh token válido."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        token = payload.get("refresh_token")
        if not token:
            return err("Refresh token é obrigatório")

        success, tokens, error = refresh_access_token(token, db)

        if not success:
            return err(error, 401)

        return ok(tokens)

    except Exception as e:
        current_app.logger.error(f"Erro ao renovar token: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def change_password(id: int):
    """Altera senha do usuário."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        senha_atual = payload.get("senha_atual")
        senha_nova = payload.get("senha_nova")

        if not senha_atual or not senha_nova:
            return err("Senha atual e nova senha são obrigatórias")

        coll = get_collection(db)

        # Busca usuário
        user = coll.find_one({"id": id, "ativo": True})
        if not user:
            return err("Usuário não encontrado", 404)

        # Verifica senha atual
        if not verify_password(senha_atual, user["senha_hash"]):
            return err("Senha atual incorreta")

        # Valida nova senha
        from ..models.user_model import validate_password, hash_password
        is_valid, error_msg = validate_password(senha_nova)
        if not is_valid:
            return err(error_msg)

        # Atualiza senha
        result = coll.update_one(
            {"id": id},
            {"$set": {
                "senha_hash": hash_password(senha_nova),
                "data_atualizacao": datetime.utcnow()
            }}
        )

        if result.matched_count == 0:
            return err("Usuário não encontrado", 404)

        return ok(message="Senha alterada com sucesso")

    except Exception as e:
        current_app.logger.error(f"Erro ao alterar senha do usuário {id}: {e}")
        return err("Erro interno do servidor", 500)


def get_user_types():
    """Retorna tipos de usuário disponíveis."""
    return ok(
        message="Tipos de usuário disponíveis",
        types=USER_TYPES
    )


@require_db
def get_users_summary():
    """Retorna resumo de usuários por tipo."""
    db = current_app.db

    try:
        coll = get_collection(db)

        # Contagem por tipo
        pipeline = [
            {"$match": {"ativo": True}},
            {"$group": {
                "_id": "$tipo",
                "count": {"$sum": 1}
            }}
        ]

        result = list(coll.aggregate(pipeline))

        summary = {}
        for item in result:
            summary[item["_id"]] = item["count"]

        # Garante que todos os tipos apareçam
        for user_type in USER_TYPES:
            if user_type not in summary:
                summary[user_type] = 0

        total_users = sum(summary.values())

        return ok(
            message="Resumo de usuários obtido com sucesso",
            summary=summary,
            total=total_users
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao obter resumo de usuários: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def confirm_email(token: str):
    """Confirma email do usuário através do token."""
    db = current_app.db

    try:
        coll = get_collection(db)

        # Busca usuário pelo token
        user = coll.find_one({
            "token_confirmacao": token,
            "email_confirmado": False
        })

        if not user:
            return err("Token inválido ou já utilizado", 404)

        # Verifica se o token expirou
        if user.get("token_expiracao") and user["token_expiracao"] < datetime.utcnow():
            return err("Token expirado. Solicite um novo email de confirmação.", 410)

        # Atualiza usuário: confirma email, ativa conta e remove token
        result = coll.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "email_confirmado": True,
                    "ativo": True,
                    "token_confirmacao": None,
                    "token_expiracao": None,
                    "data_atualizacao": datetime.utcnow()
                }
            }
        )

        if result.matched_count == 0:
            return err("Erro ao confirmar email", 500)

        # Envia email de boas-vindas
        send_welcome_email(user["email"], user["nome"])

        return ok(message="Email confirmado com sucesso! Sua conta está ativa.")

    except Exception as e:
        current_app.logger.error(f"Erro ao confirmar email: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def resend_confirmation_email():
    """Reenvia email de confirmação."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        email = payload.get("email")
        if not email:
            return err("Email é obrigatório")

        coll = get_collection(db)

        # Busca usuário por email
        user = coll.find_one({"email": email.strip().lower()})

        if not user:
            # Não revela se o email existe ou não por segurança
            return ok(message="Se o email existir, um novo link será enviado")

        # Verifica se já está confirmado
        if user.get("email_confirmado", False):
            return err("Email já confirmado")

        # Gera novo token
        from ..models.user_model import generate_confirmation_token, get_token_expiration

        new_token = generate_confirmation_token()
        new_expiration = get_token_expiration()

        # Atualiza token
        coll.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "token_confirmacao": new_token,
                    "token_expiracao": new_expiration,
                    "data_atualizacao": datetime.utcnow()
                }
            }
        )

        # Envia novo email
        send_confirmation_email(user["email"], user["nome"], new_token)

        return ok(message="Email de confirmação reenviado com sucesso")

    except Exception as e:
        current_app.logger.error(f"Erro ao reenviar email de confirmação: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def forgot_password():
    """Envia email para recuperação de senha."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        email = payload.get("email", "").strip().lower()

        if not email:
            return err("Email é obrigatório")

        coll = get_collection(db)

        # Busca usuário pelo email
        user = coll.find_one({"email": email, "ativo": True})

        # Por segurança, sempre retorna sucesso mesmo se email não existir
        if user:
            # Gera token único de recuperação
            reset_token = secrets.token_urlsafe(32)
            reset_expiration = datetime.utcnow() + timedelta(hours=1)  # Expira em 1 hora

            # Salva token no banco
            coll.update_one(
                {"id": user["id"]},
                {"$set": {
                    "reset_token": reset_token,
                    "reset_token_expiracao": reset_expiration,
                    "data_atualizacao": datetime.utcnow()
                }}
            )

            # Envia email com link de recuperação
            send_password_reset_email(user["email"], user["nome"], reset_token)

            current_app.logger.info(f"Email de recuperação enviado para {email}")
        else:
            current_app.logger.warning(f"Email {email} não encontrado, mas retornando sucesso por segurança")

        # Sempre retorna sucesso para não revelar se email existe
        return ok(message="Se o email estiver cadastrado, você receberá um link para redefinir sua senha")

    except Exception as e:
        current_app.logger.error(f"Erro ao processar recuperação de senha: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def reset_password():
    """Redefine senha usando token de recuperação."""
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        token = payload.get("token")
        nova_senha = payload.get("nova_senha")

        if not token or not nova_senha:
            return err("Token e nova senha são obrigatórios")

        coll = get_collection(db)

        # Busca usuário pelo token
        user = coll.find_one({
            "reset_token": token,
            "ativo": True
        })

        if not user:
            return err("Token inválido ou expirado")

        # Verifica se token expirou
        if user.get("reset_token_expiracao") and user["reset_token_expiracao"] < datetime.utcnow():
            return err("Token expirado. Solicite um novo link de recuperação.")

        # Valida nova senha
        is_valid, error_msg = validate_password(nova_senha)
        if not is_valid:
            return err(error_msg)

        # Atualiza senha e remove token
        result = coll.update_one(
            {"id": user["id"]},
            {"$set": {
                "senha_hash": hash_password(nova_senha),
                "data_atualizacao": datetime.utcnow()
            },
            "$unset": {
                "reset_token": "",
                "reset_token_expiracao": ""
            }}
        )

        if result.matched_count == 0:
            return err("Erro ao redefinir senha", 500)

        current_app.logger.info(f"Senha redefinida com sucesso para usuário ID {user['id']}")

        return ok(message="Senha redefinida com sucesso")

    except Exception as e:
        current_app.logger.error(f"Erro ao redefinir senha: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def request_account_deletion():
    """Solicita exclusão de conta - envia código de 6 dígitos por email.

    Requer autenticação (@jwt_required na rota): o alvo é sempre o próprio
    usuário logado (g.user_id), nunca um id vindo do corpo da requisição.
    """
    db = current_app.db

    try:
        # Identidade vem do token (int garantido por jwt_required), não do corpo.
        user_id = g.user_id

        coll = get_collection(db)

        # Busca usuário
        user = coll.find_one({"id": user_id, "ativo": True})
        if not user:
            return err("Usuário não encontrado", 404)

        # Gera código de 6 dígitos
        deletion_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Define expiração (30 minutos)
        code_expiration = datetime.utcnow() + timedelta(minutes=30)

        # Salva código no banco (zera o contador de tentativas de uma solicitação anterior)
        coll.update_one(
            {"id": user_id},
            {"$set": {
                "deletion_code": deletion_code,
                "deletion_code_expiration": code_expiration,
                "deletion_attempts": 0,
                "data_atualizacao": datetime.utcnow()
            }}
        )

        # Envia email com código
        email_sent = send_account_deletion_code(user["email"], user["nome"], deletion_code)

        if not email_sent:
            return err("Erro ao enviar email. Tente novamente.", 500)

        current_app.logger.info(f"Código de exclusão enviado para {user['email']}")

        return ok(
            message="Código de verificação enviado para seu email",
            email_sent=True
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao solicitar exclusão de conta: {e}")
        return err("Erro interno do servidor", 500)


@require_db
def confirm_account_deletion():
    """Confirma exclusão de conta com código de 6 dígitos.

    Requer autenticação (@jwt_required na rota): o alvo é sempre o próprio
    usuário logado (g.user_id). O código é comparado em tempo constante e é
    invalidado após MAX_DELETION_ATTEMPTS tentativas erradas, para impedir
    força bruta sobre os 6 dígitos.
    """
    db = current_app.db

    try:
        payload = request.get_json()
        if not payload:
            return err("Payload JSON é obrigatório")

        # Identidade vem do token (int garantido por jwt_required), não do corpo.
        user_id = g.user_id
        code = payload.get("code")

        if not code:
            return err("Código é obrigatório")

        coll = get_collection(db)

        # Busca usuário
        user = coll.find_one({"id": user_id, "ativo": True})
        if not user:
            return err("Usuário não encontrado", 404)

        # Verifica se há código de exclusão
        if not user.get("deletion_code"):
            return err("Nenhuma solicitação de exclusão encontrada")

        # Verifica se o código expirou
        if user.get("deletion_code_expiration") and user["deletion_code_expiration"] < datetime.utcnow():
            # Limpa código expirado
            coll.update_one(
                {"id": user_id},
                {"$unset": _DELETION_UNSET}
            )
            return err("Código expirado. Solicite um novo código.", 410)

        # Verifica o código em tempo constante (evita side-channel por timing)
        if not secrets.compare_digest(str(user["deletion_code"]), str(code)):
            attempts = int(user.get("deletion_attempts", 0)) + 1
            if attempts >= MAX_DELETION_ATTEMPTS:
                # Excedeu o limite: invalida o código, forçando nova solicitação
                coll.update_one(
                    {"id": user_id},
                    {"$unset": _DELETION_UNSET}
                )
                return err("Muitas tentativas inválidas. Solicite um novo código.", 429)
            coll.update_one(
                {"id": user_id},
                {"$set": {"deletion_attempts": attempts}}
            )
            return err("Código inválido")

        # Exclui a conta permanentemente
        result = coll.delete_one({"id": user_id})

        if result.deleted_count == 0:
            return err("Erro ao excluir conta", 500)

        current_app.logger.info(f"Conta do usuário ID {user_id} excluída permanentemente")

        return ok(
            message="Conta excluída com sucesso",
            deleted=True
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao confirmar exclusão de conta: {e}")
        return err("Erro interno do servidor", 500)
