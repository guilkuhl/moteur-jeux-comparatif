"""
serve.py — Lance le dashboard Pixel Lab dans le navigateur
==========================================================
Démarre un serveur HTTP local et ouvre automatiquement le dashboard.

Usage :
    py serve.py
    py serve.py --port 8080
"""

import http.server
import socketserver
import webbrowser
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).parent

def main():
    parser = argparse.ArgumentParser(description="Pixel Lab — serveur dashboard")
    parser.add_argument("--port", type=int, default=5500, help="Port (défaut: 5500)")
    parser.add_argument("--no-browser", action="store_true", help="Ne pas ouvrir le navigateur")
    args = parser.parse_args()

    os.chdir(ROOT)

    url = f"http://localhost:{args.port}/dashboard/index.html"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *a):
            pass  # Silencieux

    print(f"\n  ⚡ Pixel Lab Dashboard")
    print(f"  ─────────────────────────────")
    print(f"  URL     : {url}")
    print(f"  Dossier : {ROOT}")
    print(f"\n  Ctrl+C pour arrêter\n")

    if not args.no_browser:
        webbrowser.open(url)

    with socketserver.TCPServer(("", args.port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Serveur arrêté.\n")

if __name__ == "__main__":
    main()
