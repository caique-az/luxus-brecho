"""
Superfície única de configuração por variáveis de ambiente.

Cada variável tem **uma** função aqui, que concentra seu nome, seu default e seu
parsing. A tabela para humanos vive em `docs/setup-e-deploy.md`; este módulo é a
fonte no código — os dois precisam concordar.

Duas decisões que valem explicação:

**São funções, não constantes.** Ler no import congelaria o valor antes de os
testes ajustarem o ambiente (`tests/test_phase4_admin_seed.py` usa
``monkeypatch.setenv("ADMIN_EMAIL", ...)`` e espera que o seed enxergue o valor
novo). Funções leem no momento do uso.

**Valor inválido cai no default em vez de estourar.** Um `int()` cru sobre a
query string já derrubava rotas com 500 (BE-08); o mesmo padrão nos tunings do
Mongo era pior: ``MONGO_MAX_POOL_SIZE=abc`` levantava ValueError dentro do bloco
de conexão, que engolia a exceção e deixava o app **subir sem banco** — todas as
rotas em 503, com a mensagem "Erro inesperado na conexão MongoDB" apontando para
a rede em vez do typo. Aqui o valor inválido avisa e usa o default.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple


def _raw(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _str(name: str, default: str = "") -> str:
    value = _raw(name)
    return value if value is not None else default


def _flag(name: str, default: bool = False) -> bool:
    value = _raw(name)
    if value is None:
        return default
    return value.lower() == "true"


def _int(name: str, default: int) -> int:
    """Inteiro tolerante: valor não numérico avisa e cai no default."""
    value = _raw(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        print(f"⚠️  {name}={value!r} não é um inteiro — usando o default {default}.")
        return default


# ========== Flask ==========

def secret_key() -> str:
    """Assina a sessão do Flask (não os JWTs — esse é o jwt_secret_key)."""
    return _str("SECRET_KEY", "dev-secret-key")


def debug_mode() -> bool:
    return _flag("FLASK_DEBUG")


def env_name() -> str:
    """Rótulo informativo devolvido por GET /api/health."""
    return _str("FLASK_ENV", "production")


def max_content_length() -> int:
    return _int("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)


def flask_host() -> str:
    return _str("FLASK_HOST", "0.0.0.0")


def flask_port() -> int:
    return _int("FLASK_PORT", 5000)


def frontend_origin() -> Optional[str]:
    """Lista CSV de origens permitidas no CORS. None → lista embutida."""
    return _raw("FRONTEND_ORIGIN")


def ratelimit_storage_uri() -> str:
    return _str("RATELIMIT_STORAGE_URI", "memory://")


# ========== MongoDB ==========

def mongodb_uri() -> Optional[str]:
    """None → o app sobe sem banco e as rotas com @require_db respondem 503."""
    return _raw("MONGODB_URI")


def mongodb_database() -> Optional[str]:
    """None → usa o database embutido na URI."""
    return _raw("MONGODB_DATABASE")


def mongo_client_options() -> dict:
    """Tunings do driver. Chaves prontas para ``MongoClient(uri, **options)``."""
    return {
        "serverSelectionTimeoutMS": _int("MONGO_SERVER_SELECTION_MS", 15000),
        "connectTimeoutMS": _int("MONGO_CONNECT_TIMEOUT_MS", 20000),
        "socketTimeoutMS": _int("MONGO_SOCKET_TIMEOUT_MS", 20000),
        "maxPoolSize": _int("MONGO_MAX_POOL_SIZE", 50),
        "appname": _str("MONGO_APPNAME", "Luxus-Brecho-Backend"),
    }


# ========== JWT ==========

def require_jwt_secret_key() -> str:
    """Segredo dos tokens. Sem ele o app **não sobe**.

    Um default embutido tornaria os tokens de admin forjáveis por qualquer um
    com acesso ao repositório, então aqui é fail-fast em vez de fallback.
    """
    value = _raw("JWT_SECRET_KEY")
    if not value:
        raise RuntimeError(
            "JWT_SECRET_KEY não está definida. Defina a variável de ambiente "
            "(veja .env.example) antes de iniciar a aplicação."
        )
    return value


# ========== Admin inicial ==========

def admin_seed() -> Tuple[Optional[str], Optional[str], str]:
    """(email, senha, nome) do admin semeado no boot.

    Sem email/senha nenhum admin é criado — não existe credencial padrão.
    """
    return _raw("ADMIN_EMAIL"), _raw("ADMIN_PASSWORD"), _str("ADMIN_NAME", "Administrador")


# ========== Supabase Storage ==========

def supabase_url() -> Optional[str]:
    return _raw("SUPABASE_URL")


def supabase_key() -> Optional[str]:
    return _raw("SUPABASE_KEY")


def supabase_bucket() -> str:
    return _str("SUPABASE_BUCKET", "product-images")


def supabase_service_role() -> Tuple[Optional[str], Optional[str]]:
    """(email, senha) usados só para repetir upload barrado pela RLS do bucket."""
    return _raw("SUPABASE_SERVICE_ROLE_EMAIL"), _raw("SUPABASE_SERVICE_ROLE_KEY")


# ========== E-mail ==========

def smtp_host() -> str:
    return _str("SMTP_HOST", "smtp.gmail.com")


def smtp_port() -> int:
    return _int("SMTP_PORT", 587)


def smtp_user() -> str:
    return _str("SMTP_USER", "")


def smtp_password() -> str:
    return _str("SMTP_PASSWORD", "")


def from_email() -> str:
    return _str("FROM_EMAIL", smtp_user())


def from_name() -> str:
    return _str("FROM_NAME", "Luxus Brechó")


def production_url() -> str:
    """Primeiro da cadeia de bases de link de e-mail (ver email_service)."""
    return _str("PRODUCTION_URL", "")


def app_url() -> str:
    return _str("APP_URL", "")


def frontend_url() -> str:
    """Base dos links que apontam para o site (ex.: /redefinir-senha/<token>)."""
    return _str("FRONTEND_URL", "http://localhost:5173")
