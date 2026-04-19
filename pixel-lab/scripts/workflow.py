"""
workflow.py — Pipeline complet automatique du Pixel Lab
=======================================================
Lance en une seule commande :
  1. Diagnostic de l'image (blur, JPEG, interpolation, bruit, palette)
  2. Génération des traitements recommandés dans l'ordre optimal
  3. Application de chaque traitement (chaque étape = une itération tracée)
  4. Mise à jour de history.json
  5. Résumé final avec les chemins de sortie

Usage :
    python scripts/workflow.py inputs/sprite.png
    python scripts/workflow.py inputs/sprite.png --dry-run      # voir le plan sans exécuter
    python scripts/workflow.py inputs/sprite.png --force        # forcer même si l'image semble OK
    python scripts/workflow.py inputs/sprite.png --scale 2      # upscale final ×2 (défaut: 1, pas d'upscale)
    python scripts/workflow.py inputs/sprite.png --only sharpen denoise   # limiter à certains algos

⚠️  Pixel Art Snap (skill Claude) n'est pas inclus — c'est un outil externe à lancer séparément.
"""

import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime
from PIL import Image
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from diagnose import diagnose, print_report, build_recommendations
from algorithms import sharpen     as sharpen_mod
from algorithms import scale2x     as scale2x_mod
from algorithms import denoise     as denoise_mod
from algorithms import pixelsnap   as pixelsnap_mod

HISTORY_FILE = ROOT / "history.json"
OUTPUTS_DIR  = ROOT / "outputs"
INPUTS_DIR   = ROOT / "inputs"

ALGO_MAP = {
    "sharpen":    sharpen_mod.METHODS,
    "scale2x":    scale2x_mod.METHODS,
    "denoise":    denoise_mod.METHODS,
    "pixelsnap":  pixelsnap_mod.METHODS,
}

# ─── Couleurs terminal ────────────────────────────────────────────────────────
R, G, Y, C, B, DIM, BOLD, RESET = (
    "\033[91m", "\033[92m", "\033[93m", "\033[96m",
    "\033[94m", "\033[2m",  "\033[1m",  "\033[0m"
)
def ok(s):    return f"{G}{s}{RESET}"
def warn(s):  return f"{Y}{s}{RESET}"
def err(s):   return f"{R}{s}{RESET}"
def info(s):  return f"{C}{s}{RESET}"
def bold(s):  return f"{BOLD}{s}{RESET}"
def dim(s):   return f"{DIM}{s}{RESET}"

# ─── Historique ───────────────────────────────────────────────────────────────

def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}

def save_history(h: dict):
    HISTORY_FILE.write_text(json.dumps(h, indent=2, ensure_ascii=False), encoding="utf-8")

def next_iter(image_name: str, history: dict) -> int:
    return len(history.get(image_name, {}).get("runs", [])) + 1

# ─── Plan de traitement ───────────────────────────────────────────────────────

# Paramètres par défaut par algo/méthode
DEFAULT_PARAMS = {
    ("sharpen",    "unsharp_mask"): {"radius": 1.2, "percent": 180, "threshold": 2},
    ("sharpen",    "laplacian"):    {"strength": 0.8},
    ("sharpen",    "kernel"):       {"amount": 1.2},
    ("scale2x",    "nearest"):      {"scale": 2},
    ("scale2x",    "scale2x"):      {},
    ("scale2x",    "eagle2x"):      {},
    ("denoise",    "median"):       {"size": 3},
    ("denoise",    "bilateral"):    {"sigma_color": 60, "sigma_space": 60},
    ("denoise",    "nlm"):          {"h": 8},
    ("pixelsnap",  "median"):       {"block": 0},   # 0 = auto-détection
    ("pixelsnap",  "mode"):         {"block": 0},
    ("pixelsnap",  "mean"):         {"block": 0},
}

def build_plan(recs: list[dict], only: list[str] | None, scale: int) -> list[dict]:
    """
    Construit le plan d'exécution à partir des recommandations du diagnostic.
    - Exclut le pipeline (on le décompose step by step)
    - Filtre sur --only si fourni
    - Ajoute un upscale final si scale > 1
    """
    steps = []
    seen = set()

    for rec in recs:
        algo = rec.get("algo")
        if not algo or algo == "pipeline":
            continue
        if algo in seen:
            continue
        if only and algo not in only:
            continue
        seen.add(algo)
        method = rec["method"]
        params = DEFAULT_PARAMS.get((algo, method), {}).copy()
        steps.append({
            "algo":   algo,
            "method": method,
            "params": params,
            "reason": rec["reason"],
        })

    # Upscale final si demandé et pas déjà dans le plan
    if scale > 1 and "scale2x" not in seen:
        method = "nearest" if scale > 2 else "scale2x"
        steps.append({
            "algo":   "scale2x",
            "method": method,
            "params": {"scale": scale} if method == "nearest" else {},
            "reason": f"Upscale final ×{scale} demandé.",
        })

    return steps

# ─── Exécution d'une étape ────────────────────────────────────────────────────

def run_step(img: Image.Image, step: dict) -> Image.Image:
    algo, method, params = step["algo"], step["method"], step["params"]
    fn = ALGO_MAP[algo][method]
    return fn(img.copy(), **params)

def save_iter(img: Image.Image, image_name: str, iter_idx: int, step: dict) -> Path:
    out_dir = OUTPUTS_DIR / image_name
    out_dir.mkdir(parents=True, exist_ok=True)
    label = f"iter_{iter_idx:03d}_{step['algo']}_{step['method']}"
    path = out_dir / f"{label}.png"
    img.save(path)
    return path

# ─── Affichage du plan ────────────────────────────────────────────────────────

def print_plan(steps: list[dict], dry_run: bool):
    tag = " [DRY RUN]" if dry_run else ""
    plan_title = "📋 PLAN D'EXÉCUTION"
    print(f"\n{bold(plan_title)}{tag}\n")
    if not steps:
        print(f"  {ok('✓')} Aucun traitement nécessaire d'après le diagnostic.")
        return
    for i, s in enumerate(steps, 1):
        params_str = ", ".join(f"{k}={v}" for k, v in s["params"].items()) or "—"
        print(f"  {info(f'[{i}]')} {bold(s['algo'].upper())} / {s['method']}")
        print(f"       {dim(s['reason'])}")
        print(f"       params : {dim(params_str)}\n")

# ─── Workflow principal ───────────────────────────────────────────────────────

def run_workflow(src: Path, dry_run: bool, force: bool, scale: int, only: list[str] | None):
    bar = "═" * 56

    print(f"\n{bold(C + bar + RESET)}")
    print(f"  {bold('⚡ PIXEL LAB — WORKFLOW AUTOMATIQUE')}")
    print(f"{bold(C + bar + RESET)}\n")

    # ── 1. Diagnostic ──────────────────────────────────────────────────────
    print(f"{bold('① DIAGNOSTIC')}\n")
    t0 = time.time()
    result = diagnose(src)
    img_orig = result.pop("_img")
    metrics  = result["metrics"]
    recs     = result["recommendations"]

    print_report(src, img_orig, metrics, recs)

    # Vérifier si traitement nécessaire
    needs_treatment = any(
        m.get("needed", False)
        for m in metrics.values()
        if isinstance(m, dict)
    )

    if not needs_treatment and not force:
        print(f"\n{ok('✓')} L'image semble en bon état. Utilise {info('--force')} pour traiter quand même.\n")
        return

    # ── 2. Plan ────────────────────────────────────────────────────────────
    print(f"{bold('② PLAN')}")
    steps = build_plan(recs, only, scale)
    print_plan(steps, dry_run)

    if not steps:
        print(f"{ok('✓')} Rien à faire.\n")
        return

    if dry_run:
        print(f"\n{warn('DRY RUN — aucun fichier écrit.')}\n")
        return

    # ── 3. Exécution ───────────────────────────────────────────────────────
    print(f"{bold('③ EXÉCUTION')}\n")

    history     = load_history()
    image_name  = src.stem
    if image_name not in history:
        history[image_name] = {"source": f"inputs/{src.name}", "runs": []}

    # Copier la source si besoin
    src_copy = OUTPUTS_DIR / image_name / "source.png"
    if not src_copy.exists():
        src_copy.parent.mkdir(parents=True, exist_ok=True)
        img_orig.save(src_copy)
        print(f"  {dim('source → outputs/' + image_name + '/source.png')}")

    current_img = img_orig.copy()
    outputs = []

    for step in steps:
        iter_idx = next_iter(image_name, history)
        t1 = time.time()

        print(f"  {info(f'[{iter_idx}]')} {bold(step['algo'])}/{step['method']} ... ", end="", flush=True)
        current_img = run_step(current_img, step)
        out_path = save_iter(current_img, image_name, iter_idx, step)
        elapsed = round(time.time() - t1, 2)
        print(f"{ok('✓')}  {dim(f'{elapsed}s → ' + str(out_path.relative_to(ROOT)))}")

        run_entry = {
            "index":     iter_idx,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "algo":      step["algo"],
            "method":    step["method"],
            "params":    step["params"],
            "output":    str(out_path.relative_to(ROOT)),
            "source":    f"inputs/{src.name}",
            "workflow":  True,
        }
        history[image_name]["runs"].append(run_entry)
        outputs.append(out_path)

    # Sauvegarder le diagnostic dans history
    history[image_name]["last_diagnosis"] = {
        "timestamp": result["timestamp"],
        "metrics": {
            k: {kk: vv for kk, vv in v.items() if kk != "needed"}
            for k, v in metrics.items()
            if isinstance(v, dict)
        },
        "recommendations": [r["algo"] for r in recs if r.get("algo")],
    }
    save_history(history)

    # ── 4. Résumé ──────────────────────────────────────────────────────────
    total = round(time.time() - t0, 2)
    print(f"\n{bold(C + bar + RESET)}")
    print(f"  {ok('✓')} {len(steps)} traitement(s) appliqué(s) en {total}s")
    print(f"  {bold('Résultat final :')} {outputs[-1].relative_to(ROOT)}")
    print(f"  {bold('Dashboard     :')} ouvre dashboard/index.html")
    print(f"\n  {warn('⚠️  Pixel Art Snap')} : skill Claude externe — à lancer séparément")
    print(f"     si tu veux la quantification de palette et l'export SVG.")
    print(f"{bold(C + bar + RESET)}\n")

# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pixel Lab — workflow automatique complet",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("source",
        help="Image source (chemin relatif à inputs/ ou absolu)")
    parser.add_argument("--dry-run", action="store_true",
        help="Affiche le plan sans rien exécuter")
    parser.add_argument("--force", action="store_true",
        help="Forcer le traitement même si l'image semble OK")
    parser.add_argument("--scale", type=int, default=1,
        help="Upscale final (ex: 2 pour ×2). Défaut: 1 (pas d'upscale)")
    parser.add_argument("--only", nargs="+",
        choices=["sharpen", "scale2x", "denoise", "pixelsnap"],
        help="Limiter aux algos spécifiés (ex: --only pixelsnap sharpen)")
    args = parser.parse_args()

    src = Path(args.source)
    if not src.is_absolute():
        src = ROOT / "inputs" / src
    if not src.exists():
        print(f"{err('[erreur]')} Image introuvable : {src}")
        sys.exit(1)

    run_workflow(
        src      = src,
        dry_run  = args.dry_run,
        force    = args.force,
        scale    = args.scale,
        only     = args.only,
    )

if __name__ == "__main__":
    main()
