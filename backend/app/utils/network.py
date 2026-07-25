"""
Descoberta do endereço em que o backend fica acessível na rede local.

O IP é detectado em tempo de execução, sem depender de nenhum arquivo gerado
previamente: basta subir o servidor. O network-config.json da raiz continua
sendo respeitado como override opcional de host/porta.
"""
import json
import os
import socket
from pathlib import Path
from typing import Optional

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 5000

# backend/app/utils/network.py -> raiz do projeto
_CONFIG_PATH = Path(__file__).resolve().parents[3] / 'network-config.json'


def detect_lan_ip() -> Optional[str]:
    """
    IP da interface que a máquina usa para sair para a rede.

    O socket UDP é apenas "conectado" para consultar a tabela de rotas do SO —
    nenhum pacote é enviado e não há necessidade de internet.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('8.8.8.8', 53))
        return sock.getsockname()[0]
    except OSError:
        pass
    finally:
        sock.close()

    # Máquina sem rota default: tenta o hostname e descarta loopback
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        return None

    return None if ip.startswith('127.') else ip


def load_network_config() -> dict:
    """Lê a seção `backend` do network-config.json, se o arquivo existir."""
    if not _CONFIG_PATH.exists():
        return {}

    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️  Ignorando network-config.json inválido: {e}")
        return {}

    backend = config.get('backend')
    return backend if isinstance(backend, dict) else {}


def resolve_server_config() -> dict:
    """
    Host, porta e IP de rede do servidor.

    Precedência de host/porta: variáveis de ambiente > network-config.json >
    padrão. O IP é sempre detectado em tempo de execução; o valor gravado no
    network-config.json só entra se a detecção falhar, porque ele pode ter
    ficado obsoleto após uma troca de rede.
    """
    override = load_network_config()

    host = os.getenv('FLASK_HOST') or override.get('host') or DEFAULT_HOST
    port = int(os.getenv('FLASK_PORT') or override.get('port') or DEFAULT_PORT)
    lan_ip = detect_lan_ip() or override.get('current_ip')

    return {'host': host, 'port': port, 'lan_ip': lan_ip}


def get_base_url() -> str:
    """URL base (http://host:porta) para montar links fora do contexto HTTP."""
    config = resolve_server_config()
    return f"http://{config['lan_ip'] or '127.0.0.1'}:{config['port']}"
