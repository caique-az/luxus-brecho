"""
Script principal para executar o servidor Flask
"""

import os
from app import create_app
from app.utils.network import resolve_server_config

def main():
    # Carrega variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv()

    # Cria a aplicação Flask
    app = create_app()

    # Host/porta vêm de env vars ou do network-config.json; o IP da rede é
    # detectado automaticamente, sem exigir nenhum passo prévio na raiz
    server_config = resolve_server_config()
    host = server_config['host']
    port = server_config['port']
    current_ip = server_config['lan_ip']

    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("🚀 " + "="*50)
    print(f"🚀 Iniciando servidor Flask...")
    print(f"📍 Host: {host}")
    print(f"🔌 Porta: {port}")
    print(f"🐛 Debug: {debug}")
    
    print(f"🔗 API Local: http://127.0.0.1:{port}/api")

    if current_ip:
        print(f"🌐 IP da Rede: {current_ip}")
        print(f"🔗 API Rede: http://{current_ip}:{port}/api")
        print(f"❤️  Health: http://{current_ip}:{port}/api/health")
    else:
        print("⚠️  IP da rede não detectado — apenas acesso local disponível")
        print(f"❤️  Health: http://127.0.0.1:{port}/api/health")

    print("🚀 " + "="*50)
    
    # Inicia o servidor
    # Nota: use_reloader=False evita o erro WinError 10038 no Windows
    # O reloader pode causar conflitos de socket no Windows com Python 3.13
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,  # Desabilitado para evitar WinError 10038 no Windows
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
    except OSError as e:
        if "10038" in str(e) or "10048" in str(e):
            print(f"❌ Erro de socket: A porta {port} pode estar em uso.")
            print("💡 Tente: taskkill /F /IM python.exe ou mude a porta")
        else:
            print(f"❌ Erro de rede: {e}")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")

if __name__ == '__main__':
    main()