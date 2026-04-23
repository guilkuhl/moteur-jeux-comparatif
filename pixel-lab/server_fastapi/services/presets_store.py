"""Lecture/écriture atomique de `presets.json` avec lock thread-safe.

Schéma : `{"<name>": {"pipeline": [...], "updated_at": "<iso>"}}`. Le nom fait
office de clé primaire ; pas de versioning, l'écriture écrase l'entrée existante.
"""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import Any

from ..deps import PRESETS_FILE

_lock = threading.Lock()


def load() -> dict[str, dict[str, Any]]:
    if not PRESETS_FILE.exists():
        return {}
    try:
        data = json.loads(PRESETS_FILE.read_text("utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save(data: dict[str, dict[str, Any]]) -> None:
    PRESETS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")


def list_all() -> list[dict[str, Any]]:
    data = load()
    return [{"name": n, **entry} for n, entry in sorted(data.items())]


def upsert(name: str, pipeline: list[dict[str, Any]]) -> dict[str, Any]:
    with _lock:
        data = load()
        entry = {
            "pipeline": pipeline,
            "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        data[name] = entry
        save(data)
        return {"name": name, **entry}


def remove(name: str) -> bool:
    with _lock:
        data = load()
        if name not in data:
            return False
        del data[name]
        save(data)
        return True
