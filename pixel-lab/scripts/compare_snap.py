"""
compare_snap.py — Génère TOUTES les variantes algo/méthode pour comparaison
============================================================================
En mode exhaustif (défaut), applique chaque algo × méthode disponible
à l'image originale et génère une itération par combinaison.
Parfait pour choisir le meilleur traitement dans le dashboard.

Variantes générées :
    • sharpen  : unsharp_mask, laplacian, kernel
    • denoise  : median, bilateral, nlm
    • pixelsnap: median, mode, mean
    • combos   : pixelsnap/median → sharpen/unsharp_mask
                 denoise/median  → pixelsnap/median → sharpen
    • scale2x  (si --scale 2 passé)

Usage :
    py scripts/compare_snap.py inputs/fireball.png
    py scripts/compare_snap.py inputs/fireball.png --block 4
    py scripts/compare_snap.py inputs/fireball.png --scale 2
    py scripts/compare_snap.py inputs/fireball.png --only pixelsnap
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image
import traceback

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from algorithms import sharpen   as sharpen_mod
from algorithms import denoise   as denoise_mod
from algorithms import scale2x   as scale2x_mod
from algorithms import pixelsnap as pixelsnap_mod
from diagnose import diagnose, build_recommendations

HISTORY_FILE = ROOT / "history.json"
OUTPUTS_DIR  = ROOT / "outputs"

R, G, Y, C, BOLD, DIM, RESET = (
    "\033[91m", "\033[92m", "\033[93m", "\033[96m",
    "\033[1m",  "\033[2m",  "\033[0m"
)

def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}

def save_history(h):
    HISTORY_FILE.write_text(json.dumps(h, indent=2, ensure_ascii=False), encoding="utf-8")

def next_iter(name, history):
    return len(history.get(name, {}).get("runs", [])) + 1


def normalize_img(img: Image.Image) -> Image.Image:
    """
    Normalise le mode de l'image pour garantir RGB ou RGBA 8-bit.
    Gère les modes palette (P, PA), niveaux de gris (L, LA), 16-bit, CMYK, etc.
    """
    if img.mode == "RGBA":
        return img
    if img.mode in ("P", "PA"):
        # Palette indexée → détecter si transparence
        img = img.convert("RGBA" if img.info.get("transparency") is not None else "RGB")
    elif img.mode == "LA":
        img = img.convert("RGBA")
    elif img.mode == "L":
        img = img.convert("RGB")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    # Downgrade 16-bit → 8-bit si nécessaire
    import numpy as np
    arr = np.array(img)
    if arr.dtype != np.uint8:
        arr = (arr / 256).astype(np.uint8)
        img = Image.fromarray(arr, img.mode)
    return img


def apply_and_save(img, name, algo, method, params, history):
    """Applique algo/méthode, sauvegarde, ajoute à history. Retourne l'image résultante."""
    ALGO_MAP = {
        "sharpen":   sharpen_mod.METHODS,
        "denoise":   denoise_mod.METHODS,
        "scale2x":   scale2x_mod.METHODS,
        "pixelsnap": pixelsnap_mod.METHODS,
    }
    fn = ALGO_MAP[algo][method]
    # Normaliser le mode avant traitement (évite les erreurs avec P, L, 16-bit, etc.)
    img = normalize_img(img)
    out_img = fn(img.copy(), **params)

    out_dir = OUTPUTS_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)

    idx = next_iter(name, history)
    path = out_dir / f"iter_{idx:03d}_{algo}_{method}.png"
    out_img.save(path)

    history.setdefault(name, {"source": f"inputs/{name}.png", "runs": []})["runs"].append({
        "index":     idx,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "algo":      algo,
        "method":    method,
        "params":    params,
        "output":    str(path.relative_to(ROOT)),
        "source":    f"inputs/{name}.png",
        "workflow":  True,
    })

    size_str = f"{out_img.width}×{out_img.height}"
    print(f"  {C}[{idx:03d}]{RESET} {BOLD}{algo}/{method}{RESET}  {DIM}({size_str}){RESET}  → {path.name}")
    return out_img, path


EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tga"}


def run_one(src: Path, scale: int = 1, block: int = 0, only: set = None):
    """Traite une seule image — toutes les variantes."""
    name = src.stem
    img_orig = Image.open(src)
    if img_orig.mode not in ("RGB", "RGBA"):
        img_orig = img_orig.convert("RGBA")

    bar = "═" * 64
    print(f"\n{BOLD}{C}{bar}{RESET}")
    print(f"  {BOLD}⚡ COMPARE ALL — {src.name}{RESET}")
    print(f"{BOLD}{C}{bar}{RESET}\n")

    # ── Diagnostic pour info bloc ────────────────────────────────────────────────
    result  = diagnose(src)
    result.pop("_img")
    metrics = result["metrics"]
    psize   = metrics["pixel_block"]["pixel_size"]
    block   = block if block > 1 else psize
    print(f"  Taille bloc détectée : ×{psize}  →  utilisée pour pixelsnap : ×{block}\n")

    if only is None:
        only = {"sharpen", "denoise", "pixelsnap", "combos"}
    if scale > 1:
        only.add("scale2x")

    history = load_history()
    total   = 0

    # ── Sauvegarder source une fois ──────────────────────────────────────────────
    src_copy = OUTPUTS_DIR / name / "source.png"
    src_copy.parent.mkdir(parents=True, exist_ok=True)
    if not src_copy.exists():
        img_orig.save(src_copy)

    # ── Sharpen ──────────────────────────────────────────────────────────────────
    if "sharpen" in only:
        print(f"{BOLD}① SHARPEN{RESET}\n")
        variants = [
            ("unsharp_mask", {"radius": 1.2, "percent": 180, "threshold": 2}),
            ("unsharp_mask", {"radius": 0.8, "percent": 120, "threshold": 1}),
            ("laplacian",    {"strength": 0.5}),
            ("laplacian",    {"strength": 1.0}),
            ("kernel",       {"amount": 1.2}),
        ]
        for method, params in variants:
            apply_and_save(img_orig, name, "sharpen", method, params, history)
            total += 1

    # ── Denoise ──────────────────────────────────────────────────────────────────
    if "denoise" in only:
        print(f"\n{BOLD}② DENOISE{RESET}\n")
        variants = [
            ("median",    {"size": 3}),
            ("bilateral", {"sigma_color": 40, "sigma_space": 40}),
            ("bilateral", {"sigma_color": 75, "sigma_space": 75}),
            ("nlm",       {"h": 6}),
            ("nlm",       {"h": 10}),
        ]
        for method, params in variants:
            apply_and_save(img_orig, name, "denoise", method, params, history)
            total += 1

    # ── PixelSnap ────────────────────────────────────────────────────────────────
    if "pixelsnap" in only:
        print(f"\n{BOLD}③ PIXELSNAP{RESET}\n")
        blocks_to_try = sorted({block, max(1, block - 1), block + 1, block * 2} - {0})
        for b in blocks_to_try:
            for method in ("median", "mode", "mean"):
                apply_and_save(img_orig, name, "pixelsnap", method, {"block": b}, history)
                total += 1

    # ── Combos ───────────────────────────────────────────────────────────────────
    if "combos" in only:
        print(f"\n{BOLD}④ COMBOS (enchainements){RESET}\n")

        # pixelsnap → sharpen
        for snap_m in ("median", "mode"):
            snapped, _ = apply_and_save(img_orig, name, "pixelsnap", snap_m, {"block": block}, history)
            apply_and_save(snapped, name, "sharpen", "unsharp_mask",
                           {"radius": 1.0, "percent": 150, "threshold": 1}, history)
            total += 2

        # denoise → pixelsnap → sharpen
        denoised, _ = apply_and_save(img_orig, name, "denoise", "median", {"size": 3}, history)
        snapped,  _ = apply_and_save(denoised, name, "pixelsnap", "median", {"block": block}, history)
        apply_and_save(snapped, name, "sharpen", "unsharp_mask",
                       {"radius": 0.8, "percent": 120, "threshold": 1}, history)
        total += 3

    # ── Scale2x ──────────────────────────────────────────────────────────────────
    if "scale2x" in only and scale > 1:
        print(f"\n{BOLD}⑤ SCALE ×{scale}{RESET}\n")
        # nearest sur original
        s = scale
        resized = img_orig.resize((img_orig.width * s, img_orig.height * s), Image.NEAREST)
        apply_and_save(resized, name, "scale2x", "nearest", {"scale": s}, history)
        # pixelsnap puis scale nearest
        snapped, _ = apply_and_save(img_orig, name, "pixelsnap", "median", {"block": block}, history)
        resized2 = snapped.resize((snapped.width * s, snapped.height * s), Image.NEAREST)
        apply_and_save(resized2, name, "scale2x", f"snap_nearest_x{s}", {"block": block, "scale": s}, history)
        total += 2

    # ── Enregistrer history ──────────────────────────────────────────────────────
    history[name]["last_diagnosis"] = {
        "timestamp": result["timestamp"],
        "metrics": {
            k: {kk: vv for kk, vv in v.items() if kk != "needed"}
            for k, v in metrics.items()
            if isinstance(v, dict)
        },
        "recommendations": [r["algo"] for r in build_recommendations(metrics) if r.get("algo")],
    }
    save_history(history)

    print(f"\n{BOLD}{C}{bar}{RESET}")
    print(f"  {G}✓{RESET} {total} variante(s) générée(s) dans outputs/{name}/")
    print(f"{BOLD}{C}{bar}{RESET}\n")
    return total


def main():
    parser = argparse.ArgumentParser(
        description="Pixel Lab — toutes les variantes pour comparaison",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("source", nargs="?",
        help="Image source (dans inputs/ ou chemin absolu). Omis si --all.")
    parser.add_argument("--all",   action="store_true",
        help="Traiter TOUTES les images dans inputs/")
    parser.add_argument("--scale", type=int, default=1,
        help="Ajouter variantes upscale ×N")
    parser.add_argument("--block", type=int, default=0,
        help="Forcer taille bloc pixelsnap (0=auto)")
    parser.add_argument("--only",  nargs="+",
        choices=["sharpen", "denoise", "pixelsnap", "scale2x", "combos"],
        help="Limiter aux groupes spécifiés")
    args = parser.parse_args()

    only = set(args.only) if args.only else None

    if args.all:
        # ── Mode batch : toutes les images de inputs/ ────────────────────────────
        images = sorted([
            p for p in (ROOT / "inputs").iterdir()
            if p.suffix.lower() in EXTENSIONS
        ])
        if not images:
            print(f"{Y}Aucune image dans inputs/{RESET}")
            sys.exit(0)

        bar = "═" * 64
        print(f"\n{BOLD}{C}{bar}{RESET}")
        print(f"  {BOLD}⚡ COMPARE ALL — BATCH ({len(images)} image(s)){RESET}")
        print(f"{BOLD}{C}{bar}{RESET}\n")

        ok = err = 0
        for img_path in images:
            try:
                run_one(img_path, scale=args.scale, block=args.block, only=only)
                ok += 1
            except Exception as e:
                print(f"{R}[erreur]{RESET} {img_path.name} : {e}")
                traceback.print_exc()
                print()
                err += 1

        print(f"\n{BOLD}{C}{bar}{RESET}")
        print(f"  {G}✓ {ok} image(s) traitée(s){RESET}", end="")
        if err:
            print(f"  {R}{err} erreur(s){RESET}", end="")
        print(f"\n  Ouvre le dashboard : {BOLD}py serve.py{RESET}")
        print(f"{BOLD}{C}{bar}{RESET}\n")

    else:
        # ── Mode image unique ────────────────────────────────────────────────────
        if not args.source:
            parser.error("Donne une image source ou utilise --all")
        src = Path(args.source)
        if not src.is_absolute():
            src = ROOT / "inputs" / src
        if not src.exists():
            print(f"{R}[erreur]{RESET} Fichier introuvable : {src}")
            sys.exit(1)
        run_one(src, scale=args.scale, block=args.block, only=only)
        print(f"  Ouvre le dashboard : {BOLD}py serve.py{RESET}\n")


if __name__ == "__main__":
    main()
