"""Lecture/écriture atomique de `history.json` avec lock thread-safe."""
from __future__ import annotations

import json
import threading

from ..deps import HISTORY_FILE

_lock = threading.Lock()


def load() -> dict:
    """Retourne le contenu de history.json, ou {} si absent."""
    if not HISTORY_FILE.exists():
        return {}
    return json.loads(HISTORY_FILE.read_text("utf-8"))


def save(data: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")


def update(mutator) -> dict:
    """Applique `mutator(data)` sous le lock et persiste. Retourne le nouvel état."""
    with _lock:
        data = load()
        mutator(data)
        save(data)
        return data
