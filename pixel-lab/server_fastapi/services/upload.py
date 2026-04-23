"""Helpers pour l'upload d'images (sanitize name, suggest unused)."""
from __future__ import annotations

import re
from pathlib import Path

_SAFE_BASENAME_RE = re.compile(r"[^A-Za-z0-9._\- ]+")


def sanitize_basename(name: str) -> str:
    name = (name or "").strip().strip(".")
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    else:
        ext = ext.lower()
    stem = _SAFE_BASENAME_RE.sub("_", stem).strip("_ ")
    if not stem:
        stem = "image"
    return f"{stem}.{ext}" if ext else stem


def suggest_unused_name(basename: str, inputs_dir: Path) -> str:
    stem, dot, ext = basename.rpartition(".")
    if not dot:
        stem, ext = basename, ""
    else:
        ext = "." + ext
    for i in range(2, 1000):
        if not (inputs_dir / f"{stem}-{i}{ext}").exists():
            return f"{stem}-{i}{ext}"
    return f"{stem}-1000{ext}"
