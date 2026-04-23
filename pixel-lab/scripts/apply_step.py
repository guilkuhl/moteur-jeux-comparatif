"""
apply_step.py — Module partagé d'exécution d'une étape de pipeline.

Expose `run_step`, utilisée par :
  - `scripts/process.py`   (CLI, via subprocess depuis `workflow.py`/`batch.py`),
  - `server/app.py::_run_job` (orchestrateur `/api/convert`, in-process).

Source unique de vérité pour :
  - le cast des paramètres (int/float/bool) selon PARAMS,
  - le nommage `iter_NNN_<algo>_<method>.png`,
  - la construction de l'entrée d'historique.
"""

from __future__ import annotations

import inspect
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

# Permet `from algorithms import ...` que l'on soit importé depuis scripts/ ou server/
_THIS_DIR = Path(__file__).parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from algorithms import bgdetect, denoise, pixelsnap, scale2x, sharpen  # noqa: F401

ALGO_MODULES = {
    "sharpen":   sharpen,
    "scale2x":   scale2x,
    "denoise":   denoise,
    "pixelsnap": pixelsnap,
}


def _cast_params(algo: str, method: str, params: dict) -> dict:
    """Cast les valeurs selon la spec PARAMS du module d'algo.

    Les paramètres reçus peuvent venir du front (JSON, floats) ou de la CLI
    (strings). On respecte le type déclaré dans PARAMS (int/float/bool) et on
    laisse passer tel quel les paramètres non déclarés (rares).
    """
    mod = ALGO_MODULES[algo]
    meta_list = getattr(mod, "PARAMS", {}).get(method, [])
    meta = {p["name"]: p for p in meta_list}
    out: dict[str, Any] = {}
    for k, v in params.items():
        if k not in meta:
            out[k] = v
            continue
        t = meta[k].get("type")
        if t == "int":
            out[k] = int(v)
        elif t == "bool":
            if isinstance(v, bool):
                out[k] = v
            elif isinstance(v, str):
                out[k] = v.strip().lower() in ("1", "true", "yes", "on")
            else:
                out[k] = bool(v)
        elif t == "float":
            out[k] = float(v)
        else:
            # Type non déclaré : tenter un cast numérique safe
            if isinstance(v, (int, float)):
                out[k] = float(v)
            else:
                out[k] = v
    return out


def _next_iter_index(dst_dir: Path) -> int:
    """Prochain index `iter_NNN` dans `dst_dir` en se basant sur les fichiers
    existants `iter_*.png`. Retourne 1 si le dossier est vide/inexistant.

    On dérive l'index des fichiers sur disque (et pas d'un compteur externe)
    pour rester aligné sur `history.json` même en cas d'écriture concurrente.
    """
    if not dst_dir.exists():
        return 1
    max_idx = 0
    for f in dst_dir.iterdir():
        name = f.name
        if not name.startswith("iter_"):
            continue
        # iter_NNN_<algo>_<method>.png
        try:
            n = int(name.split("_", 2)[1])
            if n > max_idx:
                max_idx = n
        except (IndexError, ValueError):
            continue
    return max_idx + 1


def _supports_kwarg(fn: Any, kwarg: str) -> bool:
    try:
        return kwarg in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def run_step(
    src_path: Path,
    algo: str,
    method: str,
    params: dict,
    dst_dir: Path,
    *,
    name_override: str | None = None,
    use_gpu: bool = False,
) -> tuple[Path, dict]:
    """Charge `src_path`, applique `algo/method(**params)`, écrit
    `iter_NNN_<algo>_<method>.png` dans `dst_dir`, renvoie `(chemin, entry)`.

    `entry` est une entrée prête à être ajoutée dans `history.json[<stem>]["runs"]`,
    sans le champ `source` (laissé au caller, qui connaît le contexte CLI/serveur).

    `use_gpu` est injecté dans `params` uniquement pour les fonctions d'algo qui
    déclarent ce kwarg dans leur signature (opt-in, pas de propagation aveugle).
    """
    if algo not in ALGO_MODULES:
        raise ValueError(
            f"Algo inconnu : {algo}. Disponibles : {list(ALGO_MODULES.keys())}"
        )
    mod = ALGO_MODULES[algo]
    if method not in mod.METHODS:
        raise ValueError(
            f"Méthode inconnue '{method}' pour algo '{algo}'. "
            f"Disponibles : {list(mod.METHODS.keys())}"
        )

    typed_params = _cast_params(algo, method, params)
    fn = mod.METHODS[method]

    if use_gpu and _supports_kwarg(fn, "use_gpu") and "use_gpu" not in typed_params:
        typed_params["use_gpu"] = True

    src_path = Path(src_path)
    img = Image.open(src_path).copy()
    result = fn(img, **typed_params)

    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    iter_idx = _next_iter_index(dst_dir)
    out_name = f"iter_{iter_idx:03d}_{algo}_{method}.png"
    out_path = dst_dir / out_name
    result.save(out_path)

    entry = {
        "index":     iter_idx,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "algo":      algo,
        "method":    method,
        "params":    typed_params,
        "output":    out_name,
    }
    return out_path, entry
