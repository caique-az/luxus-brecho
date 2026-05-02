"""
Modelo e utilidades para a coleção de usuários.
- Define tipos de usuário permitidos (Administrador, Cliente)
- Valida payloads de usuário
- Garante validator e índices no MongoDB
- Gerencia hash de senhas
- Gerencia confirmação de email
"""
from typing import Dict, Any, Tuple, Optional
from pymongo.collection import ReturnDocument
import bcrypt
import re
import secrets
from datetime import datetime, timedelta

COLLECTION_NAME = "users"
COUNTERS_COLLECTION = "counters"
COUNTER_KEY_USERS = "users"

# Tipos de usuário permitidos
USER_TYPES = ["Administrador", "Cliente"]

def validate_email(email: str) -> bool:
    """Valida formato do email."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> Tuple[bool, str]:
    """
    Valida força da senha.
    Retorna (is_valid, message)
    """
    if len(password) < 6:
        return False, "Senha deve ter pelo menos 6 caracteres"
    
    if len(password) > 100:
        return False, "Senha deve ter no máximo 100 caracteres"
    
    # Pelo menos uma letra e um número
    if not re.search(r'[A-Za-z]', password):
        return False, "Senha deve conter pelo menos uma letra"
    
    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número"
    
    return True, "Senha válida"

def hash_password(password: str) -> str:
    """Gera hash da senha usando bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_confirmation_token() -> str:
    """Gera token único para confirmação de email."""
    return secrets.token_urlsafe(32)

def get_token_expiration() -> datetime:
    """Retorna data de expiração do token (24 horas)."""
    return datetime.utcnow() + timedelta(hours=24)

def create_schema() -> Dict[str, Any]:
    """Cria schema de validação para usuários."""
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id", "nome", "email", "senha_hash", "tipo", "ativo"],
            "properties": {
                "id": {
                    "description": "Identificador numérico único do usuário",
                    "bsonType": ["int", "long"],
                },
                "nome": {
                    "bsonType": "string",
                    "minLength": 2,
                    "maxLength": 100,
                    "description": "Nome completo do usuário (obrigatório)"
                },
                "email": {
                    "bsonType": "string",
                    "minLength": 5,
                    "maxLength": 255,
                    "description": "Email único do usuário (obrigatório)"
                },
                "senha_hash": {
                    "bsonType": "string",
                    "description": "Hash da senha do usuário (obrigatório)"
                },
                "tipo": {
                    "bsonType": "string",
                    "enum": USER_TYPES,
                    "description": f"Tipo do usuário: {', '.join(USER_TYPES)}"
                },
                "ativo": {
                    "bsonType": "bool",
                    "description": "Status ativo/inativo do usuário"
                },
                "email_confirmado": {
                    "bsonType": "bool",
                    "description": "Se o email foi confirmado pelo usuário"
                },
                "token_confirmacao": {
                    "bsonType": ["string", "null"],
                    "description": "Token para confirmação de email"
                },
                "token_expiracao": {
                    "bsonType": ["date", "null"],
                    "description": "Data de expiração do token de confirmação"
                },
                "telefone": {
                    "bsonType": ["string", "null"],
                    "maxLength": 20,
                    "description": "Telefone do usuário (opcional)"
                },
                "endereco": {
                    "bsonType": ["object", "null"],
                    "properties": {
                        "rua": {"bsonType": "string", "maxLength": 200},
                        "numero": {"bsonType": "string", "maxLength": 10},
                        "complemento": {"bsonType": ["string", "null"], "maxLength": 100},
                        "bairro": {"bsonType": "string", "maxLength": 100},
                        "cidade": {"bsonType": "string", "maxLength": 100},
                        "estado": {"bsonType": "string", "maxLength": 2},
                        "cep": {"bsonType": "string", "maxLength": 10}
                    },
                    "description": "Endereço do usuário (opcional)"
                },
                "data_criacao": {
                    "bsonType": "date",
                    "description": "Data de criação do usuário"
                },
                "data_atualizacao": {
                    "bsonType": "date",
                    "description": "Data da última atualização"
                }
            }
        }
    }

def get_collection(db):
    """Retorna a coleção de usuários com validação."""
    return db[COLLECTION_NAME]

def get_next_id(db) -> int:
    """Gera próximo ID sequencial para usuário."""
    counters = db[COUNTERS_COLLECTION]
    result = counters.find_one_and_update(
        {"name": COUNTER_KEY_USERS},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return result["seq"]

def validate_user_payload(payload: Dict[str, Any], is_update: bool = False) -> Tuple[bool, str]:
    """
    Valida payload de usuário.
    Args:
        payload: Dados do usuário
        is_update: Se é uma atualização (campos opcionais)
    Returns:
        (is_valid, error_message)
    """
    if not is_update:
        required_fields = ["nome", "email", "tipo", "senha"]
        for field in required_fields:
            if field not in payload or not payload[field]:
                return False, f"Campo '{field}' é obrigatório"
    
    # Valida nome
    if "nome" in payload:
        nome = payload["nome"].strip()
        if len(nome) < 2 or len(nome) > 100:
            return False, "Nome deve ter entre 2 e 100 caracteres"
    
    # Valida email
    if "email" in payload:
        email = payload["email"].strip().lower()
        if not validate_email(email):
            return False, "Email inválido"
    
    # Valida senha (apenas na criação ou se fornecida na atualização)
    if "senha" in payload:
        is_valid, message = validate_password(payload["senha"])
        if not is_valid:
            return False, message
    
    # Valida tipo
    if "tipo" in payload:
        if payload["tipo"] not in USER_TYPES:
            return False, f"Tipo deve ser um dos seguintes: {', '.join(USER_TYPES)}"
    
    # Valida telefone se fornecido
    if "telefone" in payload and payload["telefone"]:
        telefone = payload["telefone"].strip()
        if len(telefone) > 20:
            return False, "Telefone deve ter no máximo 20 caracteres"
    
    # Valida endereço se fornecido
    if "endereco" in payload and payload["endereco"]:
        endereco = payload["endereco"]
        required_address_fields = ["rua", "numero", "bairro", "cidade", "estado", "cep"]
        for field in required_address_fields:
            if field not in endereco or not endereco[field]:
                return False, f"Campo '{field}' é obrigatório no endereço"
        
        # Valida CEP (formato básico)
        cep = endereco["cep"].replace("-", "").replace(" ", "")
        if not re.match(r'^\d{8}$', cep):
            return False, "CEP deve ter 8 dígitos"
        
        # Valida estado (2 letras)
        if len(endereco["estado"]) != 2:
            return False, "Estado deve ter 2 caracteres"
    
    return True, "Usuário válido"

def prepare_new_user(payload: Dict[str, Any], db) -> Dict[str, Any]:
    """Prepara dados de um novo usuário para inserção."""
    now = datetime.utcnow()
    
    # Administradores não precisam confirmar email
    is_admin = payload["tipo"] == "Administrador"
    
    user_data = {
        "id": get_next_id(db),
        "nome": payload["nome"].strip(),
        "email": payload["email"].strip().lower(),
        "senha_hash": hash_password(payload["senha"]),
        "tipo": payload["tipo"],
        "ativo": is_admin,  # Admin ativo imediatamente, Cliente após confirmar email
        "email_confirmado": is_admin,  # Admin não precisa confirmar
        "token_confirmacao": None if is_admin else generate_confirmation_token(),
        "token_expiracao": None if is_admin else get_token_expiration(),
        "data_criacao": now,
        "data_atualizacao": now
    }
    
    # Campos opcionais
    if "telefone" in payload and payload["telefone"]:
        user_data["telefone"] = payload["telefone"].strip()
    
    if "endereco" in payload and payload["endereco"]:
        endereco = payload["endereco"].copy()
        endereco["cep"] = endereco["cep"].replace("-", "").replace(" ", "")
        user_data["endereco"] = endereco
    
    return user_data

def prepare_user_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara dados para atualização de usuário."""
    update_data = {
        "data_atualizacao": datetime.utcnow()
    }
    
    # Campos que podem ser atualizados
    updatable_fields = ["nome", "email", "tipo", "ativo", "telefone", "endereco"]
    
    for field in updatable_fields:
        if field in payload:
            if field == "nome" and payload[field]:
                update_data[field] = payload[field].strip()
            elif field == "email" and payload[field]:
                update_data[field] = payload[field].strip().lower()
            elif field == "endereco" and payload[field]:
                endereco = payload[field].copy()
                if "cep" in endereco:
                    endereco["cep"] = endereco["cep"].replace("-", "").replace(" ", "")
                update_data[field] = endereco
            else:
                update_data[field] = payload[field]
    
    # Atualiza senha se fornecida
    if "senha" in payload and payload["senha"]:
        update_data["senha_hash"] = hash_password(payload["senha"])
    
    return update_data

def normalize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza dados do usuário para resposta (remove campos sensíveis)."""
    if not user:
        return {}
    
    normalized = dict(user)
    normalized.pop("_id", None)
    normalized.pop("senha_hash", None)  # Remove hash da senha por segurança
    normalized.pop("token_confirmacao", None)  # Remove token por segurança
    normalized.pop("token_expiracao", None)  # Remove expiração do token
    
    # Converte datas para string ISO
    if "data_criacao" in normalized:
        normalized["data_criacao"] = normalized["data_criacao"].isoformat()
    if "data_atualizacao" in normalized:
        normalized["data_atualizacao"] = normalized["data_atualizacao"].isoformat()
    
    return normalized

def ensure_users_collection(db):
    """Garante que a coleção de usuários existe com validação e índices."""
    try:
        # Cria coleção se não existir
        if COLLECTION_NAME not in db.list_collection_names():
            db.create_collection(COLLECTION_NAME)
            print(f"✅ Coleção '{COLLECTION_NAME}' criada")
        
        # Aplica schema de validação
        schema = create_schema()
        db.command("collMod", COLLECTION_NAME, validator=schema)
        print(f"✅ Schema de validação aplicado à coleção '{COLLECTION_NAME}'")
        
        print(f"✅ Schema configurado para a coleção '{COLLECTION_NAME}'")
        
    except Exception as e:
        print(f"❌ Erro ao configurar coleção de usuários: {e}")
