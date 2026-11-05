import argparse
import socket
import threading
import webbrowser

from app import create_app
from app.db import reset_demo_data


app = create_app()
# La porta 5000 su macOS è occupata dal servizio AirPlay: il prototipo parte dalla 5050.
DEFAULT_PORT = 5050


def free_port(preferred):
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avvia il prototipo del Centro Culturale Aurora.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="porta locale (predefinita: 5050)")
    parser.add_argument("--reset-demo", action="store_true",
                        help="cancella i dati e ricarica quelli dimostrativi con date aggiornate")
    parser.add_argument("--no-browser", action="store_true", help="non aprire il browser all'avvio")
    arguments = parser.parse_args()

    if arguments.reset_demo:
        with app.app_context():
            reset_demo_data()
        print("Dati dimostrativi ripristinati.")

    port = free_port(arguments.port)
    address = f"http://127.0.0.1:{port}"
    print(f"\nCentro Culturale Aurora in esecuzione su {address}")
    print("Per fermare il prototipo premi CTRL+C oppure chiudi questa finestra.\n")
    if not arguments.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(address,)).start()
    app.run(port=port)
