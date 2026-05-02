"""
Configurações centralizadas da aplicação.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

class Config:
    """Configurações base."""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    PROPAGATE_EXCEPTIONS = True
    JSONIFY_PRETTYPRINT_REGULAR = False
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    
    # MongoDB
    MONGODB_URI = os.environ.get('MONGODB_URI')
    MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'LuxusBrecho')
    MONGO_SERVER_SELECTION_MS = int(os.environ.get('MONGO_SERVER_SELECTION_MS', 15000))
    MONGO_CONNECT_TIMEOUT_MS = int(os.environ.get('MONGO_CONNECT_TIMEOUT_MS', 20000))
    MONGO_SOCKET_TIMEOUT_MS = int(os.environ.get('MONGO_SOCKET_TIMEOUT_MS', 20000))
    MONGO_MAX_POOL_SIZE = int(os.environ.get('MONGO_MAX_POOL_SIZE', 50))
    MONGO_APPNAME = os.environ.get('MONGO_APPNAME', 'Luxus-Brecho-Backend')
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        if DEBUG:
            JWT_SECRET_KEY = 'dev-secret-key-change-in-production'
        else:
            raise ValueError("JWT_SECRET_KEY must be set in production")
    
    JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 86400))  # 24 hours
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days
    )
    
    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_BUCKET = os.environ.get('SUPABASE_BUCKET', 'luxus-brecho')
    
    # Email
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
    FROM_EMAIL = os.environ.get('FROM_EMAIL', SMTP_USER)
    FROM_NAME = os.environ.get('FROM_NAME', 'Luxus Brechó')
    
    # CORS
    FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN')
    if FRONTEND_ORIGIN:
        CORS_ORIGINS = [o.strip() for o in FRONTEND_ORIGIN.split(',')]
    else:
        CORS_ORIGINS = [
            'http://localhost:5173',
            'http://127.0.0.1:5173',
            'https://luxus-brechofrontend.vercel.app',
            'https://luxus-brecho-frontend.vercel.app',
        ]
    
    # Rate Limiting
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '200 per day, 50 per hour')
    RATELIMIT_LOGIN = os.environ.get('RATELIMIT_LOGIN', '5 per minute, 20 per hour')
    RATELIMIT_REGISTER = os.environ.get('RATELIMIT_REGISTER', '3 per minute, 10 per hour')
    RATELIMIT_PASSWORD_RESET = os.environ.get('RATELIMIT_PASSWORD_RESET', '3 per hour')
    
    # Cache (Redis)
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes
    CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', 'luxus_')
    
    # Security
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT', 'luxus-brecho-salt')
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))
    SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class DevelopmentConfig(Config):
    """Configurações de desenvolvimento."""
    DEBUG = True
    TESTING = False
    BCRYPT_LOG_ROUNDS = 4  # Mais rápido para desenvolvimento


class ProductionConfig(Config):
    """Configurações de produção."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    BCRYPT_LOG_ROUNDS = 13  # Mais seguro


class TestingConfig(Config):
    """Configurações de teste."""
    TESTING = True
    DEBUG = True
    BCRYPT_LOG_ROUNDS = 4
    MONGODB_DATABASE = 'luxus_test'
    JWT_SECRET_KEY = 'test-secret-key'
    RATELIMIT_ENABLED = False


# Mapeamento de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Retorna a configuração baseada no ambiente."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
