from flask import Blueprint, jsonify
from flask_cors import cross_origin

from app import config
import psutil
import datetime

# Cria o blueprint das rotas de health
health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'], strict_slashes=False)
@cross_origin()
def health_check():
    """Endpoint de verificação de saúde da API"""
    try:
        # Informações básicas do sistema
        memory = psutil.virtual_memory()
        
        health_data = {
            'status': 'OK',
            'timestamp': datetime.datetime.now().isoformat(),
            'uptime_seconds': psutil.boot_time(),
            'memory_usage': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent
            },
            'environment': config.env_name(),
            'debug': config.debug_mode(),
            'version': '1.0.0'
        }
        
        return jsonify({
            'success': True,
            'data': health_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'ERROR',
            'message': 'Erro no health check',
            'detail': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

@health_bp.route('/health', methods=['OPTIONS'], strict_slashes=False)
@cross_origin()
def health_options():
    """Lida com requisições OPTIONS para CORS preflight no health"""
    return jsonify({'success': True, 'message': 'OK'}), 200