"""Déplacement de fichiers/dossiers vers un dossier trash avec timestamp."""
from __future__ import annotations

import datetime
import shutil
from pathlib import Path


def move_to_trash(src: Path, trash_root: Path) -> Path:
    """Déplace `src` dans `trash_root` avec un timestamp unique. Retourne le chemin destination."""
    trash_root.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if src.is_file():
        dest = trash_root / f"{src.stem}_{ts}{src.suffix}"
        n = 1
        while dest.exists():
            n += 1
            dest = trash_root / f"{src.stem}_{ts}_{n}{src.suffix}"
    else:
        dest = trash_root / f"{src.name}_{ts}"
        n = 1
        while dest.exists():
            n += 1
            dest = trash_root / f"{src.name}_{ts}_{n}"
    shutil.move(str(src), str(dest))
    return dest
