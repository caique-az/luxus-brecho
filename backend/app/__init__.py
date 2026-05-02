import os
import logging
from dotenv import load_dotenv

# Carrega variáveis de ambiente ANTES de qualquer outra coisa
load_dotenv()

# Configuração de logging ANTES de importar bibliotecas que usam logging
_debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
_log_level = logging.DEBUG if _debug_mode else logging.INFO

logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Silenciar logs verbosos de bibliotecas externas ANTES de importá-las
# PyMongo gera MUITOS logs em DEBUG (conexões, comandos, seleção de servidor)
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('pymongo.command').setLevel(logging.WARNING)
logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
logging.getLogger('pymongo.serverSelection').setLevel(logging.WARNING)

# Outras bibliotecas verbosas
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('hpack').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.INFO)

# Agora importa as bibliotecas
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from pymongo.server_api import ServerApi
import certifi

# Importações opcionais para otimização
try:
    from flask_compress import Compress
    HAS_COMPRESS = True
except ImportError:
    HAS_COMPRESS = False

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False

def _should_use_tls(uri: str) -> bool:
    """Define se deve usar TLS/CA (Atlas / SRV / URIs com tls=true)."""
    if not uri:
        return False
    uri_l = uri.lower()
    return (
        uri_l.startswith("mongodb+srv://") or
        "mongodb.net" in uri_l or
        "tls=true" in uri_l or
        "ssl=true" in uri_l
    )

def create_app():
    """Factory function para criar a aplicação Flask"""
    
    # Carrega variáveis de ambiente
    load_dotenv()
    
    # Cria a instância Flask
    app = Flask(__name__)
    
    # Configurações básicas
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.config['PROPAGATE_EXCEPTIONS'] = True  # Melhor tratamento de erros
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Reduz tamanho do JSON
    
    # Configura o logger da aplicação (logging já configurado no topo do módulo)
    app.logger.setLevel(_log_level)
    
    # Compressão de resposta (gzip)
    if HAS_COMPRESS:
        Compress(app)
        app.logger.info("✅ Compressão de resposta habilitada")
    
    # Rate Limiting para endpoints sensíveis
    limiter = None
    if HAS_LIMITER:
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://",
        )
        app.limiter = limiter
        app.logger.info("✅ Rate limiting habilitado")
    else:
        app.limiter = None
    
    # Configuração CORS unificada (web + mobile)
    allowed_origins_env = os.getenv("FRONTEND_ORIGIN")
    if allowed_origins_env:
        allowed_origins = [o.strip() for o in allowed_origins_env.split(",")]
    else:
        allowed_origins = [
            'http://localhost:5173',                          # Vite dev server
            'http://127.0.0.1:5173',                          # Vite dev server (IP)
            'http://localhost:19000',                         # Expo DevTools
            'http://localhost:8081',                          # Expo Metro
            'https://luxus-brechofrontend.vercel.app',       # Frontend Vercel
            'https://luxus-brecho-frontend.vercel.app',      # Frontend Vercel (alternativo)
        ]
    
    print(f"🌐 Origens CORS permitidas: {allowed_origins}")
    
    CORS(app, 
         resources={r"/*": {"origins": allowed_origins}},
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         allow_headers=[
             'Content-Type', 
             'Authorization',
             'Accept',
             'Accept-Encoding',
             'X-Client-Version',
             'X-Requested-With',
             'X-User-Id',
             'Origin'
         ],
         expose_headers=['Content-Length', 'Content-Encoding'],
         max_age=3600,
         supports_credentials=True)
    
    # Middleware de segurança
    @app.after_request
    def after_request(response):
        # Headers de segurança
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'  # Permite iframe do mesmo domínio
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Não adicionar headers CORS aqui - já configurado pelo flask-cors
        
        return response
    
    # Inicializa MongoDB
    app.mongo = None
    app.db = None
    
    # Configuração do MongoDB
    uri = os.getenv("MONGODB_URI")
    if uri:
        try:
            db_name_env = os.getenv("MONGODB_DATABASE")
            
            # Configurações de conexão
            client_kwargs = dict(
                serverSelectionTimeoutMS=int(os.getenv("MONGO_SERVER_SELECTION_MS", "15000")),
                connectTimeoutMS=int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "20000")),
                socketTimeoutMS=int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "20000")),
                maxPoolSize=int(os.getenv("MONGO_MAX_POOL_SIZE", "50")),
                retryWrites=True,
                server_api=ServerApi("1"),
                appname=os.getenv("MONGO_APPNAME", "Luxus-Brecho-Backend"),
            )
            
            # Usa CA apenas quando faz sentido (Atlas/SRV/TLS)
            if _should_use_tls(uri):
                client_kwargs["tlsCAFile"] = certifi.where()
            
            client = MongoClient(uri, **client_kwargs)
            
            # Testa conexão
            client.admin.command("ping")
            print("✅ MongoDB conectado com sucesso!")
            app.mongo = client
            
            # Define database
            if db_name_env:
                app.db = client[db_name_env]
            else:
                app.db = client.get_database()
            
            # Garantia de índices/esquemas
            try:
                from .models.category_model import ensure_categories_collection
                from .models.product_model import ensure_products_collection
                from .models.user_model import ensure_users_collection
                from .models.favorite_model import ensure_indexes as ensure_favorites_indexes
                from .models.cart_model import ensure_indexes as ensure_cart_indexes
                from .models.order_model import ensure_indexes as ensure_order_indexes
                
                ensure_categories_collection(app.db)
                ensure_products_collection(app.db)
                ensure_users_collection(app.db)
                ensure_favorites_indexes(app.db)
                ensure_cart_indexes(app.db)
                ensure_order_indexes(app.db)
                
                # Cria índices otimizados
                from .utils.db_indexes import create_indexes
                create_indexes(app.db)
                
                print("✅ Coleções e índices verificados e otimizados")
            except ImportError as e:
                print(f"⚠️  Alguns modelos não foram encontrados: {e}")
                
        except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
            print(f"❌ Erro ao conectar ao MongoDB: {e}")
            print("Verifique MONGODB_URI, rede/IP liberado no Atlas")
        except Exception as e:
            print(f"❌ Erro inesperado na conexão MongoDB: {e}")
    else:
        print("⚠️  MONGODB_URI não configurado - funcionando sem banco")
    
    # Rota raiz
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'message': 'Luxus Brechó API está funcionando!',
            'version': '1.0.0',
            'status': 'online',
            'database': 'connected' if app.db is not None else 'disconnected',

            'endpoints': {
                'health': '/api/health',
                'products': '/api/products',
                'images': '/api/images',
                'users': '/api/users',
                'favorites': '/api/favorites',
                'cart': '/api/cart',
                'orders': '/api/orders'
            }
        })
    
    # Registra os blueprints (rotas) - com tratamento de erro
    blueprints_to_register = [
        ('app.routes.health_routes', 'health_bp', '/api'),
        ('app.routes.products_routes', 'products_bp', '/api/products'),
        ('app.routes.categories_routes', 'categories_bp', '/api/categories'),
        ('app.routes.images_routes', 'images_bp', '/api/images'),
        ('app.routes.users_routes', 'users_bp', '/api/users'),
        ('app.routes.favorites_routes', 'favorites_bp', '/api/favorites'),
        ('app.routes.cart_routes', 'cart_bp', '/api/cart'),
        ('app.routes.order_routes', 'order_bp', '/api/orders')
    ]
    
    # Desabilitar strict slashes globalmente para evitar redirects em preflight
    app.url_map.strict_slashes = False
    
    for module_path, blueprint_name, url_prefix in blueprints_to_register:
        try:
            module = __import__(module_path, fromlist=[blueprint_name])
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            print(f"✅ {blueprint_name} registrado em {url_prefix}")
        except ImportError as e:
            print(f"⚠️  Erro ao importar {module_path}: {e}")
        except AttributeError as e:
            print(f"⚠️  Blueprint {blueprint_name} não encontrado em {module_path}: {e}")
        except Exception as e:
            print(f"❌ Erro inesperado ao registrar {blueprint_name}: {e}")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': 'Endpoint não encontrado',
            'available_endpoints': [
                'GET /',
                'GET /api/health',
                'GET /api/products',
                'POST /api/products',
                'PUT /api/products/<id>',
                'DELETE /api/products/<id>',
                'GET /api/categories',
                'POST /api/categories',
                'GET /api/users',
                'POST /api/users',
                'GET /api/favorites',
                'POST /api/favorites',
                'DELETE /api/favorites/<product_id>',
                'POST /api/favorites/toggle'
            ]
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor',
            'error': str(error) if app.config['DEBUG'] else 'Erro interno'
        }), 500
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'message': 'Método não permitido para este endpoint'
        }), 405
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'success': False,
            'message': 'Arquivo muito grande',
            'max_size': '16MB'
        }), 413
    
    print("🚀 Aplicação Flask criada com sucesso!")
    
    return app