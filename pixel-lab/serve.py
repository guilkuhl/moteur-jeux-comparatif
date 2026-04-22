"""
serve.py — Entrée unique du Pixel Lab (Flask + dashboard)
==========================================================

Modes :
  - dev  (défaut)             : `app.run(threaded=True)` — Flask reload manuel.
  - prod (PIXEL_LAB_PROD=1)    : lance gunicorn `-w 1` sur 127.0.0.1:5500.

Usage :
    python pixel-lab/serve.py
    PIXEL_LAB_PROD=1 python pixel-lab/serve.py         # si gunicorn installé

Installation (prod) :
    pip install -r pixel-lab/requirements-prod.txt

⚠️  Garder `-w 1` : le verrou `_active_job` et le cache preview de `server/app.py`
    sont des globaux mémoire du process. Passer à `-w > 1` sans porter le lock
    vers un mécanisme inter-process (fichier lock / Redis) casserait la garantie
    « un seul job actif à la fois ».
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent

# Permet `from server.app import app` peu importe le cwd au moment du lancement.
sys.path.insert(0, str(ROOT))


def _run_gunicorn(bind: str = "127.0.0.1:5500") -> None:
    """Démarre gunicorn en process courant (fallback si indisponible)."""
    try:
        from gunicorn.app.wsgiapp import run  # type: ignore
    except ImportError:
        print("[serve] gunicorn introuvable — fallback sur app.run().")
        print("        Installe-le avec : pip install -r pixel-lab/requirements-prod.txt")
        _run_flask_dev(bind)
        return

    # Injection des args gunicorn via sys.argv (son CLI lit ce tableau).
    # -w 1 : un seul worker, voir caveat en tête de fichier.
    sys.argv = [
        "gunicorn",
        "-w", "1",
        "-b", bind,
        "--threads", "4",
        "server.app:app",
    ]
    print(f"[serve] gunicorn → http://{bind}/dashboard/index.html")
    run()


def _run_flask_dev(bind: str = "127.0.0.1:5500") -> None:
    """Fallback développement : app.run, identique à `python server/app.py`."""
    from server.app import app
    host, _, port_s = bind.partition(":")
    port = int(port_s or "5500")
    url = f"http://{host}:{port}/dashboard/index.html"
    print(f"[serve] Flask dev → {url}")
    if os.environ.get("PIXEL_LAB_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass
    app.run(host=host, port=port, debug=False, threaded=True)


def main() -> None:
    bind = os.environ.get("PIXEL_LAB_BIND", "127.0.0.1:5500")
    if os.environ.get("PIXEL_LAB_PROD", "0") == "1":
        _run_gunicorn(bind)
    else:
        _run_flask_dev(bind)


if __name__ == "__main__":
    main()
