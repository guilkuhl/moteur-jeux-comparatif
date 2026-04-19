"""
diagnose.py — Analyse d'image avant traitement
===============================================
Mesure plusieurs indicateurs de qualité et recommande les traitements adaptés.

Usage :
    python scripts/diagnose.py inputs/sprite.png
    python scripts/diagnose.py inputs/sprite.png --json    # sortie JSON brute
    python scripts/diagnose.py inputs/sprite.png --save    # sauvegarde dans history.json

Indicateurs mesurés :
    • Flou (Laplacian variance)
    • Artefacts JPEG (énergie sur les bords 8×8)
    • Interpolation / bords doux (détection de gradients lissés)
    • Niveau de bruit (variance locale)
    • Taille de palette (nombre de couleurs uniques)
    • Résolution effective (ratio pixels identiques entre voisins)
"""

import sys
import json
import argparse
import numpy as np
import cv2
from PIL import Image
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent


# ─── Métriques ────────────────────────────────────────────────────────────────

def measure_blur(gray: np.ndarray) -> dict:
    """
    Variance du Laplacien — mesure la netteté.
    Valeur élevée = image nette. Faible = floue.
    """
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    score = float(lap.var())

    if score < 20:
        level, verdict = "très flou", "critical"
    elif score < 100:
        level, verdict = "flou modéré", "warning"
    elif score < 500:
        level, verdict = "acceptable", "ok"
    else:
        level, verdict = "net", "good"

    return {
        "score": round(score, 2),
        "level": level,
        "verdict": verdict,
        "needed": verdict in ("critical", "warning"),
    }


def measure_jpeg_artifacts(gray: np.ndarray) -> dict:
    """
    Détecte les artefacts de compression JPEG : blocs 8×8 visibles.
    Compare la variation aux frontières des blocs vs intérieur.
    """
    h, w = gray.shape
    h8, w8 = (h // 8) * 8, (w // 8) * 8
    g = gray[:h8, :w8].astype(float)

    # Variation aux frontières horizontales des blocs
    border_h = np.abs(g[8::8, :] - g[7:-1:8, :]).mean() if h8 >= 16 else 0.0
    # Variation à l'intérieur des blocs
    inner_h  = np.abs(np.diff(g, axis=0)).mean()

    ratio = border_h / (inner_h + 1e-6)
    score = float(ratio)

    if score > 1.6:
        level, verdict = "artefacts prononcés", "critical"
    elif score > 1.2:
        level, verdict = "artefacts légers", "warning"
    else:
        level, verdict = "pas d'artefacts", "good"

    return {
        "score": round(score, 3),
        "level": level,
        "verdict": verdict,
        "needed": verdict in ("critical", "warning"),
    }


def measure_interpolation(gray: np.ndarray) -> dict:
    """
    Détecte si l'image a été agrandie avec interpolation bilinéaire/bicubique.
    Une image pixel-art upscalée par interpolation a des transitions trop douces.
    On cherche le ratio de gradients faibles (<threshold) sur les bords détectés.
    """
    edges = cv2.Canny(gray, 50, 150)
    if edges.sum() == 0:
        return {"score": 0.0, "level": "indéterminé", "verdict": "ok", "needed": False}

    # Gradient magnitude de Sobel
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx**2 + gy**2)

    # Aux endroits où il y a un bord Canny, quel est le gradient Sobel ?
    edge_mask = edges > 0
    edge_grads = mag[edge_mask]

    # Ratio de bords "doux" (gradient < 15) — typique de l'interpolation
    soft_ratio = float((edge_grads < 15).mean())
    score = round(soft_ratio * 100, 1)

    if soft_ratio > 0.6:
        level, verdict = "interpolation forte", "critical"
    elif soft_ratio > 0.35:
        level, verdict = "interpolation modérée", "warning"
    else:
        level, verdict = "bords nets", "good"

    return {
        "score": score,          # % de bords doux
        "level": level,
        "verdict": verdict,
        "needed": verdict in ("critical", "warning"),
    }


def measure_noise(gray: np.ndarray) -> dict:
    """
    Estime le niveau de bruit par écart-type de la différence
    entre l'image et une version légèrement floutée.
    """
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    noise = gray.astype(float) - blurred.astype(float)
    score = float(noise.std())

    if score > 12:
        level, verdict = "bruit élevé", "critical"
    elif score > 5:
        level, verdict = "bruit modéré", "warning"
    else:
        level, verdict = "propre", "good"

    return {
        "score": round(score, 2),
        "level": level,
        "verdict": verdict,
        "needed": verdict in ("critical", "warning"),
    }


def measure_palette(img: Image.Image) -> dict:
    """
    Compte le nombre de couleurs uniques.
    Pixel-art authentique = peu de couleurs (<= 64 en général).
    """
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    reshaped = arr.reshape(-1, 3)
    unique = len(np.unique(reshaped, axis=0))
    ratio = unique / (h * w)

    if unique <= 16:
        level, verdict = "vraie palette pixel-art", "good"
    elif unique <= 64:
        level, verdict = "palette pixel-art étendue", "good"
    elif unique <= 512:
        level, verdict = "palette dégradée (possible interpolation)", "warning"
    else:
        level, verdict = "image photo / très dégradée", "warning"

    return {
        "count": unique,
        "ratio": round(ratio * 100, 3),   # % de pixels uniques
        "level": level,
        "verdict": verdict,
    }


def measure_resolution_block(img: Image.Image) -> dict:
    """
    Tente de deviner la taille réelle des pixels pixel-art
    en cherchant le GCD des runs de pixels identiques.
    """
    arr = np.array(img.convert("RGB"))
    # Sur une ligne horizontale, cherche la longueur des séquences de pixels identiques
    row = arr[arr.shape[0] // 2]
    runs = []
    count = 1
    for i in range(1, len(row)):
        if np.array_equal(row[i], row[i-1]):
            count += 1
        else:
            runs.append(count)
            count = 1
    runs.append(count)

    if not runs:
        return {"pixel_size": 1, "level": "indéterminé"}

    from math import gcd
    from functools import reduce
    g = reduce(gcd, runs)
    g = min(g, 8)  # cap raisonnable

    if g == 1:
        level = "pixels 1:1 (natif ou interpolé)"
    else:
        level = f"pixels agrandis ×{g} (pixel-art upscalé)"

    return {"pixel_size": g, "level": level}


# ─── Recommandations ─────────────────────────────────────────────────────────

def build_recommendations(metrics: dict) -> list[dict]:
    recs = []

    blur  = metrics["blur"]
    jpeg  = metrics["jpeg_artifacts"]
    interp = metrics["interpolation"]
    noise = metrics["noise"]
    psize = metrics["pixel_block"]["pixel_size"]

    # 1. Débruitage en premier si bruit + artefacts
    if noise["needed"] and jpeg["needed"]:
        recs.append({
            "priority": 1,
            "algo": "denoise",
            "method": "nlm",
            "reason": "Bruit et artefacts JPEG détectés — NLM les traite ensemble.",
            "command": "python scripts/process.py <image> denoise method=nlm h=10"
        })
    elif jpeg["needed"]:
        recs.append({
            "priority": 1,
            "algo": "denoise",
            "method": "median",
            "reason": f"Artefacts JPEG ({jpeg['level']}) — filtre médian efficace.",
            "command": "python scripts/process.py <image> denoise method=median size=3"
        })
    elif noise["needed"]:
        recs.append({
            "priority": 1,
            "algo": "denoise",
            "method": "bilateral",
            "reason": f"Bruit détecté ({noise['level']}) — bilatéral préserve les bords.",
            "command": "python scripts/process.py <image> denoise method=bilateral sigma_color=50"
        })

    # 2. Sharpen si flou (surtout après dénoise)
    if blur["needed"]:
        method = "laplacian" if blur["verdict"] == "critical" else "unsharp_mask"
        recs.append({
            "priority": 2,
            "algo": "sharpen",
            "method": method,
            "reason": f"Flou détecté ({blur['level']}, score={blur['score']}).",
            "command": f"python scripts/process.py <image> sharpen method={method}"
        })

    # 3. PixelSnap si pixels agrandis (interpolation bilinéaire détectée dans les blocs)
    if psize > 1:
        recs.append({
            "priority": 3,
            "algo": "pixelsnap",
            "method": "median",
            "reason": f"Pixels agrandis ×{psize} — PixelSnap uniformise chaque bloc pour des pixels nets et unicolores.",
            "command": f"python scripts/process.py <image> pixelsnap method=median block={psize}"
        })

    # 4. Upscale si interpolation détectée (en plus ou à la place du pixelsnap)
    if interp["needed"]:
        recs.append({
            "priority": 4,
            "algo": "scale2x",
            "method": "scale2x",
            "reason": f"Interpolation détectée ({interp['level']}) — Scale2X nettoie les bords.",
            "command": "python scripts/process.py <image> scale2x method=scale2x"
        })

    # Pipeline suggéré si plusieurs traitements
    if len(recs) >= 2:
        steps = ",".join(f"{r['algo']}:{r['method']}" for r in sorted(recs, key=lambda x: x["priority"]))
        recs.append({
            "priority": 0,
            "algo": "pipeline",
            "method": steps,
            "reason": "Pipeline complet dans l'ordre optimal.",
            "command": f"python scripts/process.py <image> pipeline steps=\"{steps}\""
        })

    if not recs:
        recs.append({
            "priority": 0,
            "algo": None,
            "method": None,
            "reason": "✓ L'image semble en bon état — traitement probablement non nécessaire.",
            "command": None
        })

    return sorted(recs, key=lambda x: x["priority"])


# ─── Affichage ────────────────────────────────────────────────────────────────

VERDICT_ICON = {"good": "✅", "ok": "✅", "warning": "⚠️ ", "critical": "🔴"}
VERDICT_COLOR = {"good": "\033[92m", "ok": "\033[92m", "warning": "\033[93m", "critical": "\033[91m"}
RESET = "\033[0m"

def c(text, verdict):
    return f"{VERDICT_COLOR.get(verdict,'')}{text}{RESET}"


def print_report(img_path: Path, img: Image.Image, metrics: dict, recs: list):
    w, h = img.size
    print(f"\n{'─'*54}")
    print(f"  🔍 DIAGNOSTIC — {img_path.name}")
    print(f"{'─'*54}")
    print(f"  Taille     : {w}×{h} px  |  Mode : {img.mode}")
    print(f"  Fichier    : {round(img_path.stat().st_size / 1024, 1)} Ko\n")

    b = metrics["blur"]
    j = metrics["jpeg_artifacts"]
    i = metrics["interpolation"]
    n = metrics["noise"]
    p = metrics["palette"]
    bl = metrics["pixel_block"]

    rows = [
        ("Flou (Laplacian)",   f"score={b['score']}",          b['level'],  b['verdict']),
        ("Artefacts JPEG",     f"ratio={j['score']}",           j['level'],  j['verdict']),
        ("Interpolation",      f"{i['score']}% bords doux",    i['level'],  i['verdict']),
        ("Bruit",              f"σ={n['score']}",               n['level'],  n['verdict']),
        ("Palette",            f"{p['count']} couleurs",        p['level'],  p['verdict']),
        ("Taille pixel",       f"×{bl['pixel_size']}",          bl['level'], "ok"),
    ]

    for name, detail, level, verdict in rows:
        icon = VERDICT_ICON.get(verdict, "  ")
        print(f"  {icon} {c(name.ljust(22), verdict)}  {detail.ljust(22)}  {c(level, verdict)}")

    print(f"\n{'─'*54}")
    print(f"  💡 RECOMMANDATIONS\n")
    for r in recs:
        if r["algo"] is None:
            print(f"  {r['reason']}")
        else:
            prio = f"[#{r['priority']}]" if r["priority"] > 0 else "[pipeline]"
            print(f"  {prio} {r['algo'].upper()} / {r['method']}")
            print(f"       {r['reason']}")
            if r["command"]:
                src_name = img_path.name
                cmd = r["command"].replace("<image>", f"inputs/{src_name}")
                print(f"       \033[96m{cmd}\033[0m")
            print()
    print(f"{'─'*54}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def diagnose(img_path: Path) -> dict:
    img = Image.open(img_path)
    gray = np.array(img.convert("L"))

    metrics = {
        "blur":           measure_blur(gray),
        "jpeg_artifacts": measure_jpeg_artifacts(gray),
        "interpolation":  measure_interpolation(gray),
        "noise":          measure_noise(gray),
        "palette":        measure_palette(img),
        "pixel_block":    measure_resolution_block(img),
    }
    recs = build_recommendations(metrics)

    return {
        "image": img_path.name,
        "size": {"w": img.width, "h": img.height, "mode": img.mode},
        "file_kb": round(img_path.stat().st_size / 1024, 1),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "metrics": metrics,
        "recommendations": recs,
        "_img": img,  # interne, pas sérialisé
    }


def main():
    parser = argparse.ArgumentParser(description="Pixel Lab — diagnostic d'image")
    parser.add_argument("source", help="Image à analyser (relative à inputs/ ou absolu)")
    parser.add_argument("--json", action="store_true", help="Affiche uniquement le JSON brut")
    parser.add_argument("--save", action="store_true", help="Sauvegarde le diagnostic dans history.json")
    args = parser.parse_args()

    src = Path(args.source)
    if not src.is_absolute():
        src = ROOT / "inputs" / src
    if not src.exists():
        print(f"[erreur] Image introuvable : {src}")
        sys.exit(1)

    result = diagnose(src)
    img = result.pop("_img")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print_report(src, img, result["metrics"], result["recommendations"])

    if args.save:
        hist_path = ROOT / "history.json"
        history = json.loads(hist_path.read_text()) if hist_path.exists() else {}
        name = src.stem
        if name not in history:
            history[name] = {"source": f"inputs/{src.name}", "runs": []}
        history[name]["last_diagnosis"] = {
            "timestamp": result["timestamp"],
            "metrics": {k: {kk: vv for kk, vv in v.items() if kk != "needed"}
                        for k, v in result["metrics"].items()},
            "recommendations": [r["algo"] for r in result["recommendations"] if r["algo"]],
        }
        hist_path.write_text(json.dumps(history, indent=2, ensure_ascii=False))
        print(f"[saved] Diagnostic enregistré dans history.json")


if __name__ == "__main__":
    main()
