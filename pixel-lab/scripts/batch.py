"""
batch.py — Traitement automatique de toutes les images dans inputs/
===================================================================
Lance le workflow complet sur chaque image trouvée dans inputs/.
Ignore les images déjà traitées sauf si --redo est passé.

Usage :
    py scripts/batch.py
    py scripts/batch.py --scale 2
    py scripts/batch.py --dry-run
    py scripts/batch.py --redo              # retraite même les images déjà faites
    py scripts/batch.py --only sharpen      # limite les algos
"""

import sys
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

INPUTS_DIR   = ROOT / "inputs"
HISTORY_FILE = ROOT / "history.json"
EXTENSIONS   = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tga"}

R, G, Y, C, BOLD, DIM, RESET = (
    "\033[91m", "\033[92m", "\033[93m", "\033[96m",
    "\033[1m",  "\033[2m",  "\033[0m"
)


def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def already_processed(name: str, history: dict) -> bool:
    return bool(history.get(name, {}).get("runs"))


def main():
    parser = argparse.ArgumentParser(description="Pixel Lab — batch sur tout inputs/")
    parser.add_argument("--dry-run", action="store_true", help="Plan sans exécuter")
    parser.add_argument("--redo",    action="store_true", help="Retraiter même les images déjà faites")
    parser.add_argument("--force",   action="store_true", help="Forcer même si image jugée OK")
    parser.add_argument("--scale",   type=int, default=1, help="Upscale final (ex: 2)")
    parser.add_argument("--only",    nargs="+", choices=["sharpen", "scale2x", "denoise", "pixelsnap"],
                        help="Limiter aux algos spécifiés")
    args = parser.parse_args()

    # Trouver toutes les images
    images = sorted([
        p for p in INPUTS_DIR.iterdir()
        if p.suffix.lower() in EXTENSIONS
    ])

    if not images:
        print(f"{Y}Aucune image trouvée dans inputs/{RESET}")
        print(f"Formats acceptés : {', '.join(sorted(EXTENSIONS))}")
        sys.exit(0)

    history = load_history()

    # Séparer à traiter / déjà faites
    to_process = []
    skipped    = []
    for img in images:
        if not args.redo and already_processed(img.stem, history):
            skipped.append(img)
        else:
            to_process.append(img)

    # Résumé
    bar = "═" * 56
    print(f"\n{BOLD}{C}{bar}{RESET}")
    print(f"  {BOLD}⚡ PIXEL LAB — BATCH{RESET}")
    print(f"{BOLD}{C}{bar}{RESET}")
    print(f"\n  {BOLD}{len(images)}{RESET} image(s) dans inputs/")
    print(f"  {G}→ à traiter   : {len(to_process)}{RESET}")
    if skipped:
        print(f"  {DIM}→ déjà faites : {len(skipped)} (utilise --redo pour les relancer){RESET}")
    print()

    if not to_process:
        print(f"{G}✓ Tout est déjà traité.{RESET}\n")
        return

    # Import workflow ici pour ne pas payer le coût si rien à faire
    from workflow import run_workflow

    ok_count  = 0
    err_count = 0

    for i, img_path in enumerate(to_process, 1):
        print(f"{BOLD}{C}── [{i}/{len(to_process)}] {img_path.name} {RESET}\n")
        try:
            run_workflow(
                src     = img_path,
                dry_run = args.dry_run,
                force   = args.force,
                scale   = args.scale,
                only    = args.only,
            )
            ok_count += 1
        except Exception as e:
            print(f"\n{R}[erreur] {img_path.name} : {e}{RESET}\n")
            err_count += 1

    # Bilan final
    print(f"\n{BOLD}{C}{bar}{RESET}")
    print(f"  {BOLD}BILAN{RESET}  {G}{ok_count} réussi(s){RESET}", end="")
    if err_count:
        print(f"  {R}{err_count} erreur(s){RESET}", end="")
    print(f"\n  Dashboard : ouvre {BOLD}dashboard/index.html{RESET}")
    print(f"{BOLD}{C}{bar}{RESET}\n")


if __name__ == "__main__":
    main()
