"""
serve.py — Entrée unique Pixel Lab (FastAPI + dashboard)
=========================================================

Modes :
  - dev  (défaut)              : `uvicorn --reload`
  - prod (PIXEL_LAB_PROD=1)    : `gunicorn -k uvicorn.workers.UvicornWorker -w 1`

Usage :
    python pixel-lab/serve.py
    PIXEL_LAB_PROD=1 python pixel-lab/serve.py

Installation prod :
    pip install -r pixel-lab/requirements-prod.txt

⚠️  Garder `-w 1` : le verrou `_active_job` et les caches preview/bgmask de
    `server_fastapi/` sont des globaux mémoire du process. Monter à `-w > 1`
    sans porter ces états vers un mécanisme inter-process (fichier lock, Redis)
    casserait la garantie « un seul job actif à la fois ».
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent

# Permet `from server_fastapi.main import app` peu importe le cwd au moment du lancement.
sys.path.insert(0, str(ROOT))


def _run_gunicorn(bind: str = "127.0.0.1:5500") -> None:
    """Prod : gunicorn + UvicornWorker. Fallback uvicorn dev si gunicorn absent."""
    try:
        from gunicorn.app.wsgiapp import run  # type: ignore
    except ImportError:
        print("[serve] gunicorn introuvable — fallback uvicorn dev.")
        print("        pip install -r pixel-lab/requirements-prod.txt")
        _run_uvicorn(bind, reload=False)
        return

    sys.argv = [
        "gunicorn",
        "-w", "1",
        "-k", "uvicorn.workers.UvicornWorker",
        "-b", bind,
        "--timeout", "120",
        "server_fastapi.main:app",
    ]
    print(f"[serve] gunicorn → http://{bind}/")
    run()


def _run_uvicorn(bind: str = "127.0.0.1:5500", *, reload: bool = True) -> None:
    """Dev : uvicorn avec reload automatique sur modification de fichier .py."""
    import uvicorn

    host, _, port_s = bind.partition(":")
    port = int(port_s or "5500")
    url = f"http://{host}:{port}/"
    print(f"[serve] uvicorn {'(reload)' if reload else ''} → {url}")
    if not reload and os.environ.get("PIXEL_LAB_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass
    uvicorn.run(
        "server_fastapi.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=os.environ.get("PIXEL_LAB_LOG_LEVEL", "info").lower(),
    )


def main() -> None:
    bind = os.environ.get("PIXEL_LAB_BIND", "127.0.0.1:5500")
    if os.environ.get("PIXEL_LAB_PROD", "0") == "1":
        _run_gunicorn(bind)
    else:
        _run_uvicorn(bind, reload=True)


if __name__ == "__main__":
    main()
