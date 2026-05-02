"""
Validadores e sanitizadores para entrada de dados.
"""
import re
from typing import Any, Dict, List, Tuple
from bson import ObjectId
from pymongo.collection import Collection


def sanitize_string(value: Any, max_length: int = 500) -> str:
    """
    Sanitiza string removendo caracteres perigosos.
    
    Args:
        value: Valor a ser sanitizado
        max_length: Tamanho máximo permitido
        
    Returns:
        String sanitizada
    """
    if not value:
        return ""
    
    # Converte para string
    value = str(value).strip()
    
    # Remove caracteres de controle e nulls
    value = ''.join(char for char in value if ord(char) >= 32)
    
    # Limita tamanho
    value = value[:max_length]
    
    # Remove operadores MongoDB perigosos
    dangerous_patterns = [
        r'\$where',
        r'\$regex', 
        r'\$ne',
        r'\$gt',
        r'\$lt',
        r'\$gte',
        r'\$lte',
        r'\$in',
        r'\$nin',
        r'\$or',
        r'\$and',
        r'\$not',
        r'\$nor',
        r'\$exists',
        r'\$type',
        r'\$expr',
        r'\$jsonSchema',
        r'\$mod',
        r'\$text',
        r'\$where'
    ]
    
    for pattern in dangerous_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    return value


def sanitize_email(email: str) -> str:
    """
    Sanitiza e valida email.
    
    Args:
        email: Email a ser sanitizado
        
    Returns:
        Email sanitizado e em lowercase
        
    Raises:
        ValueError: Se email for inválido
    """
    if not email:
        raise ValueError("Email é obrigatório")
    
    email = email.strip().lower()
    
    # Regex básico para email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValueError("Formato de email inválido")
    
    # Limita tamanho
    if len(email) > 254:  # RFC 5321
        raise ValueError("Email muito longo")
    
    return email


def sanitize_integer(value: Any, min_val: int = None, max_val: int = None) -> int:
    """
    Sanitiza e valida inteiro.
    
    Args:
        value: Valor a ser convertido
        min_val: Valor mínimo permitido
        max_val: Valor máximo permitido
        
    Returns:
        Inteiro validado
        
    Raises:
        ValueError: Se valor for inválido
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("Valor deve ser um número inteiro")
    
    if min_val is not None and value < min_val:
        raise ValueError(f"Valor deve ser maior ou igual a {min_val}")
    
    if max_val is not None and value > max_val:
        raise ValueError(f"Valor deve ser menor ou igual a {max_val}")
    
    return value


def sanitize_float(value: Any, min_val: float = None, max_val: float = None) -> float:
    """
    Sanitiza e valida float.
    
    Args:
        value: Valor a ser convertido
        min_val: Valor mínimo permitido
        max_val: Valor máximo permitido
        
    Returns:
        Float validado
        
    Raises:
        ValueError: Se valor for inválido
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("Valor deve ser um número")
    
    if min_val is not None and value < min_val:
        raise ValueError(f"Valor deve ser maior ou igual a {min_val}")
    
    if max_val is not None and value > max_val:
        raise ValueError(f"Valor deve ser menor ou igual a {max_val}")
    
    return value


def sanitize_pagination(page: Any, page_size: Any) -> Tuple[int, int]:
    """
    Sanitiza parâmetros de paginação.
    
    Args:
        page: Número da página
        page_size: Tamanho da página
        
    Returns:
        Tupla (page, page_size) sanitizados
    """
    try:
        page = sanitize_integer(page, min_val=1)
    except (TypeError, ValueError):
        page = 1
    
    try:
        page_size = sanitize_integer(page_size, min_val=1, max_val=100)
    except (TypeError, ValueError):
        page_size = 10
    
    return page, page_size


def sanitize_object_id(value: Any) -> str:
    """
    Sanitiza e valida ObjectId do MongoDB.
    
    Args:
        value: Valor a ser validado
        
    Returns:
        String do ObjectId válido
        
    Raises:
        ValueError: Se ObjectId for inválido
    """
    if isinstance(value, ObjectId):
        return str(value)
    
    try:
        # Tenta criar ObjectId para validar
        obj_id = ObjectId(value)
        return str(obj_id)
    except Exception:
        raise ValueError("ID inválido")


def sanitize_query_params(params: Dict[str, Any], allowed_fields: List[str]) -> Dict[str, Any]:
    """
    Sanitiza parâmetros de query removendo campos não permitidos.
    
    Args:
        params: Dicionário de parâmetros
        allowed_fields: Lista de campos permitidos
        
    Returns:
        Dicionário sanitizado
    """
    sanitized = {}
    
    for field in allowed_fields:
        if field in params:
            value = params[field]
            
            # Sanitiza baseado no tipo
            if isinstance(value, str):
                sanitized[field] = sanitize_string(value)
            elif isinstance(value, (int, float)):
                sanitized[field] = value
            elif isinstance(value, bool):
                sanitized[field] = value
            elif isinstance(value, list):
                # Sanitiza cada item da lista
                sanitized[field] = [
                    sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            elif value is not None:
                sanitized[field] = sanitize_string(str(value))
    
    return sanitized


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Valida força da senha.
    
    Args:
        password: Senha a ser validada
        
    Returns:
        Tupla (válida, mensagem_erro)
    """
    if not password:
        return False, "Senha é obrigatória"
    
    if len(password) < 8:
        return False, "Senha deve ter no mínimo 8 caracteres"
    
    if len(password) > 128:
        return False, "Senha deve ter no máximo 128 caracteres"
    
    # Verifica complexidade
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
    
    complexity_score = sum([has_upper, has_lower, has_digit, has_special])
    
    if complexity_score < 3:
        return False, "Senha deve conter pelo menos 3 dos seguintes: letra maiúscula, letra minúscula, número, caractere especial"
    
    # Verifica senhas comuns
    common_passwords = [
        'password', '12345678', 'qwerty', 'abc123', 'password123',
        'admin', 'letmein', 'welcome', 'monkey', '1234567890'
    ]
    
    if password.lower() in common_passwords:
        return False, "Senha muito comum, escolha outra"
    
    return True, ""


def validate_cep(cep: str) -> Tuple[bool, str]:
    """
    Valida CEP brasileiro.
    
    Args:
        cep: CEP a ser validado
        
    Returns:
        Tupla (válido, cep_formatado)
    """
    if not cep:
        return False, ""
    
    # Remove caracteres não numéricos
    cep = re.sub(r'\D', '', cep)
    
    # Verifica tamanho
    if len(cep) != 8:
        return False, ""
    
    # Formata CEP
    formatted = f"{cep[:5]}-{cep[5:]}"
    
    return True, formatted


def validate_cpf(cpf: str) -> bool:
    """
    Valida CPF brasileiro.
    
    Args:
        cpf: CPF a ser validado
        
    Returns:
        True se válido, False caso contrário
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'\D', '', cpf)
    
    # Verifica tamanho
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula primeiro dígito verificador
    sum_digit = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digit1 = (sum_digit * 10 % 11) % 10
    
    if digit1 != int(cpf[9]):
        return False
    
    # Calcula segundo dígito verificador
    sum_digit = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digit2 = (sum_digit * 10 % 11) % 10
    
    return digit2 == int(cpf[10])


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    Valida telefone brasileiro.
    
    Args:
        phone: Telefone a ser validado
        
    Returns:
        Tupla (válido, telefone_formatado)
    """
    if not phone:
        return False, ""
    
    # Remove caracteres não numéricos
    phone = re.sub(r'\D', '', phone)
    
    # Verifica tamanho (com ou sem DDD)
    if len(phone) < 10 or len(phone) > 11:
        return False, ""
    
    # Formata telefone
    if len(phone) == 11:
        formatted = f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
    else:
        formatted = f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
    
    return True, formatted


def prevent_nosql_injection(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Previne injeção NoSQL removendo operadores perigosos.
    
    Args:
        query: Query MongoDB
        
    Returns:
        Query sanitizada
    """
    if not query:
        return {}
    
    dangerous_keys = [
        '$where', '$regex', '$options', '$expr', '$jsonSchema',
        '$text', '$search', '$language', '$caseSensitive',
        '$diacriticSensitive', '$near', '$nearSphere',
        '$geometry', '$maxDistance', '$minDistance'
    ]
    
    def clean_dict(d):
        cleaned = {}
        for key, value in d.items():
            # Remove chaves perigosas
            if key in dangerous_keys:
                continue
            
            # Remove chaves que começam com $
            if key.startswith('$') and key not in ['$in', '$nin', '$eq', '$ne', '$gt', '$lt', '$gte', '$lte']:
                continue
            
            # Recursivamente limpa dicionários aninhados
            if isinstance(value, dict):
                cleaned[key] = clean_dict(value)
            elif isinstance(value, list):
                # Limpa cada item da lista
                cleaned[key] = [
                    clean_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        
        return cleaned
    
    return clean_dict(query)
