"""
process.py — Script principal du Pixel Lab
==========================================
Applique un ou plusieurs traitements sur une image source,
sauvegarde le résultat dans outputs/{image_name}/iter_XXX_*.png
et met à jour history.json.

Usage :
    python process.py <image_source> <algo> [params...]

Exemples :
    python process.py inputs/sprite.png sharpen method=unsharp_mask radius=1.2 percent=200
    python process.py inputs/sprite.png scale2x method=scale2x
    python process.py inputs/sprite.png denoise method=bilateral sigma_color=50
    python process.py inputs/sprite.png pipeline steps="sharpen:unsharp_mask,scale2x:scale2x"

Algos disponibles :
    sharpen   → methods: unsharp_mask, laplacian, kernel
    scale2x   → methods: nearest, scale2x, eagle2x
    denoise   → methods: median, bilateral, nlm

Après chaque run, ouvrir dashboard/index.html pour comparer les itérations.
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from PIL import Image

# Ajouter le dossier scripts au path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from algorithms import sharpen as sharpen_mod
from algorithms import scale2x as scale2x_mod
from algorithms import denoise as denoise_mod
from algorithms import pixelsnap as pixelsnap_mod
from apply_step import run_step as _run_step_shared

HISTORY_FILE = ROOT / "history.json"
OUTPUTS_DIR  = ROOT / "outputs"
INPUTS_DIR   = ROOT / "inputs"

ALGO_MAP = {
    "sharpen":   sharpen_mod.METHODS,
    "scale2x":   scale2x_mod.METHODS,
    "denoise":   denoise_mod.METHODS,
    "pixelsnap": pixelsnap_mod.METHODS,
}


# ─── Historique ──────────────────────────────────────────────────────────────

def load_history() -> dict:
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(history: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def next_iter_index(image_name: str, history: dict) -> int:
    runs = history.get(image_name, {}).get("runs", [])
    return len(runs) + 1


# ─── Traitement ──────────────────────────────────────────────────────────────

def parse_params(raw: list[str]) -> dict:
    """Convertit ["key=value", ...] en dict avec cast automatique."""
    params = {}
    for item in raw:
        if "=" in item:
            k, v = item.split("=", 1)
            # Auto-cast
            try:
                v = int(v)
            except ValueError:
                try:
                    v = float(v)
                except ValueError:
                    pass
            params[k] = v
    return params


def apply_algo(img: Image.Image, algo: str, params: dict) -> Image.Image:
    """Applique un algorithme avec ses paramètres."""
    if algo not in ALGO_MAP:
        raise ValueError(f"Algo inconnu : {algo}. Disponibles : {list(ALGO_MAP.keys())}")

    method_name = params.pop("method", None)
    methods = ALGO_MAP[algo]

    if method_name is None:
        method_name = list(methods.keys())[0]
        print(f"[info] Pas de method= fourni, utilisation de '{method_name}' par défaut.")

    if method_name not in methods:
        raise ValueError(f"Méthode inconnue '{method_name}' pour algo '{algo}'. Disponibles : {list(methods.keys())}")

    fn = methods[method_name]
    print(f"[process] {algo}/{method_name} avec params={params}")
    return fn(img, **params)


def run_pipeline(img: Image.Image, steps_str: str) -> tuple[Image.Image, list[dict]]:
    """
    Enchaîne plusieurs étapes. Format : "algo:method,algo:method"
    Ex : "sharpen:unsharp_mask,scale2x:scale2x"
    """
    steps_log = []
    for step in steps_str.split(","):
        step = step.strip()
        if ":" in step:
            algo, method = step.split(":", 1)
        else:
            algo, method = step, list(ALGO_MAP[step].keys())[0]
        img = apply_algo(img, algo, {"method": method})
        steps_log.append({"algo": algo, "method": method})
    return img, steps_log


# ─── Sauvegarde ──────────────────────────────────────────────────────────────

def save_result(img: Image.Image, image_name: str, iter_idx: int, algo: str, method: str) -> Path:
    out_dir = OUTPUTS_DIR / image_name
    out_dir.mkdir(parents=True, exist_ok=True)
    label = f"iter_{iter_idx:03d}_{algo}_{method}"
    out_path = out_dir / f"{label}.png"
    img.save(out_path)
    print(f"[saved] {out_path.relative_to(ROOT)}")
    return out_path


# ─── Entrée principale ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pixel Lab — traitement d'images pixel-art")
    parser.add_argument("source",  help="Chemin de l'image source (relative à inputs/ ou absolu)")
    parser.add_argument("algo",    help="Algorithme : sharpen | scale2x | denoise | pipeline")
    parser.add_argument("params",  nargs="*", help="Paramètres key=value (ex: method=scale2x)")
    args = parser.parse_args()

    # Résolution du chemin source
    src_path = Path(args.source)
    if not src_path.is_absolute():
        src_path = INPUTS_DIR / src_path
    if not src_path.exists():
        print(f"[erreur] Image introuvable : {src_path}")
        sys.exit(1)

    image_name = src_path.stem
    img = Image.open(src_path)
    print(f"[open] {src_path.name}  ({img.width}×{img.height}, mode={img.mode})")

    params = parse_params(args.params)
    if 'name' in params:
        image_name = str(params.pop('name'))
    history = load_history()

    # ─ Copier l'image source dans outputs si c'est le 1er run (avant run_step
    #   pour que le dossier cible existe avant toute écriture)
    source_copy = OUTPUTS_DIR / image_name / "source.png"
    source_copy.parent.mkdir(parents=True, exist_ok=True)
    if not source_copy.exists():
        img.save(source_copy)
        print(f"[saved] Source copiée dans outputs/{image_name}/source.png")

    # ─ Pipeline ou algo simple
    if args.algo == "pipeline":
        steps_str = params.get("steps", "")
        if not steps_str:
            print("[erreur] Pipeline : fournis steps='algo:method,algo:method'")
            sys.exit(1)
        result, steps_log = run_pipeline(img.copy(), steps_str)
        method_label = "+".join(s["method"] for s in steps_log)
        algo_label = "pipeline"
        iter_idx = next_iter_index(image_name, history)
        out_path = save_result(result, image_name, iter_idx, algo_label, method_label)
        params_entry = {k: v for k, v in parse_params(args.params).items() if k != "method"}
    else:
        method_name = params.get("method", list(ALGO_MAP.get(args.algo, {}).keys() or ["?"])[0])
        # Les casts (int/float/bool) et l'écriture `iter_NNN_*.png` sont centralisés
        # dans apply_step.run_step — source de vérité partagée avec le serveur.
        step_params = {k: v for k, v in params.items() if k != "method"}
        print(f"[process] {args.algo}/{method_name} avec params={step_params}")
        out_path, entry = _run_step_shared(
            src_path, args.algo, method_name, step_params,
            OUTPUTS_DIR / image_name,
        )
        print(f"[saved] {out_path.relative_to(ROOT)}")
        iter_idx = entry["index"]
        algo_label = entry["algo"]
        method_label = entry["method"]
        params_entry = entry["params"]

    # ─ Mettre à jour l'historique
    run_entry = {
        "index": iter_idx,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "algo": algo_label,
        "method": method_label,
        "params": params_entry,
        "output": str(out_path.relative_to(ROOT)),
        "source": str(src_path.relative_to(ROOT)) if src_path.is_relative_to(ROOT) else str(src_path),
    }

    if image_name not in history:
        history[image_name] = {"source": str(source_copy.relative_to(ROOT)), "runs": []}
    history[image_name]["runs"].append(run_entry)
    save_history(history)
    print(f"[history] Itération #{iter_idx} enregistrée dans history.json")
    print(f"\n✓ Ouvre dashboard/index.html pour comparer les résultats.")


if __name__ == "__main__":
    main()
