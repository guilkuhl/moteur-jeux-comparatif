"""Dépendances partagées — chemins racine, résolution d'input, stores singleton."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # pixel-lab/
SCRIPTS_DIR = ROOT / "scripts"
INPUTS_DIR = ROOT / "inputs"
OUTPUTS_DIR = ROOT / "outputs"
HISTORY_FILE = ROOT / "history.json"
PRESETS_FILE = ROOT / "presets.json"
FRONTEND_DIST = ROOT / "frontend-dist"

INPUTS_TRASH = INPUTS_DIR / "_trash"
OUTPUTS_TRASH = OUTPUTS_DIR / "_trash"

ALLOWED_UPLOAD_EXTS = {".png", ".webp", ".jpg", ".jpeg"}
INPUT_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tga"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Import après ajout au path : les modules `algorithms` et `apply_step` vivent dans scripts/
from algorithms import bgdetect, denoise, pixelsnap, scale2x, sharpen  # noqa: E402

ALGO_MODULES = {
    "sharpen":   sharpen,
    "scale2x":   scale2x,
    "denoise":   denoise,
    "pixelsnap": pixelsnap,
}
ALGO_NAMES = set(ALGO_MODULES.keys())


def resolve_input(name: str) -> Path | None:
    """Résout un nom d'image (avec/sans extension) vers un fichier réel dans inputs/."""
    exact = INPUTS_DIR / name
    if exact.exists():
        return exact
    for ext in INPUT_EXTS:
        candidate = INPUTS_DIR / f"{name}{ext}"
        if candidate.exists():
            return candidate
    return None


def safe_name(s: str) -> bool:
    """Garde contre le path-traversal pour les noms de fichiers/dossiers."""
    return isinstance(s, str) and "/" not in s and "\\" not in s and ".." not in s


__all__ = [
    "ROOT", "SCRIPTS_DIR", "INPUTS_DIR", "OUTPUTS_DIR", "HISTORY_FILE",
    "PRESETS_FILE", "FRONTEND_DIST", "INPUTS_TRASH", "OUTPUTS_TRASH",
    "ALLOWED_UPLOAD_EXTS", "INPUT_EXTS", "MAX_UPLOAD_BYTES",
    "ALGO_MODULES", "ALGO_NAMES",
    "bgdetect", "resolve_input", "safe_name",
]
