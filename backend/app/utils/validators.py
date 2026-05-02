"""
Validadores e sanitizadores para entrada de dados.
"""
import re
from typing import Any, Dict, Tuple


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
