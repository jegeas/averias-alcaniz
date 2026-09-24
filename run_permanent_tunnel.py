import os
import sys
import time
import socket
import threading
import webbrowser
import uvicorn
import ngrok

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
from services.config_service import ConfigService

AUTH_TOKEN = "3IfVQ7uXazSBuz7jbID5YGYc9oq_72QgKLNiqdpvd9NbJgoAZ"
PERMANENT_DOMAIN = "astute-dice-carbon.ngrok-free.dev"
PORT = 8000


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_local_server():
    if not is_port_in_use(PORT):
        print("[1/2] Iniciando servidor web de la aplicacion en puerto 8000...", flush=True)
        t = threading.Thread(
            target=lambda: uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning"),
            daemon=True
        )
        t.start()
        time.sleep(2)
    else:
        print("[1/2] Servidor web local ya activo en puerto 8000.", flush=True)


def run_tunnel_loop():
    print("\n" + "=" * 62, flush=True)
    print("   APLICACION CONECTADA PARA ACCESO DESDE RED MOVIL (4G/5G)", flush=True)
    print("=" * 62 + "\n", flush=True)

    start_local_server()

    print(f"[2/2] Conectando dominio permanente https://{PERMANENT_DOMAIN}...", flush=True)

    while True:
        try:
            listener = ngrok.forward(
                PORT,
                authtoken=AUTH_TOKEN,
                domain=PERMANENT_DOMAIN
            )
            url = listener.url()

            print("\n" + "=" * 62, flush=True)
            print("  TU APLICACION ESTA ACTIVA PARA CUALQUIER RED MOVIL!", flush=True)
            print("=" * 62, flush=True)
            print(f"\n  Direccion permanente para tu movil (4G / 5G / Wi-Fi):", flush=True)
            print(f"  >> {url}\n", flush=True)
            print("  * Funciona con datos moviles desde cualquier lugar.", flush=True)
            print("  * Guardala en favoritos o anadela a la pantalla de inicio.", flush=True)
            print("=" * 62 + "\n", flush=True)
            print("Servicio activo con autoreconexion automatica.", flush=True)
            print("Presione CTRL+C para detener.\n", flush=True)

            while True:
                time.sleep(5)
                # Check if server is healthy
                if not is_port_in_use(PORT):
                    print("Servidor web local no responde, reiniciando...", flush=True)
                    start_local_server()

        except KeyboardInterrupt:
            print("\nCerrando servicio...", flush=True)
            try:
                ngrok.disconnect(f"https://{PERMANENT_DOMAIN}")
            except Exception:
                pass
            print("Servicio detenido.", flush=True)
            break
        except Exception as e:
            print(f"[AVISO] Conexion interrumpida: {e}. Reconectando en 5 segundos...", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    run_tunnel_loop()
