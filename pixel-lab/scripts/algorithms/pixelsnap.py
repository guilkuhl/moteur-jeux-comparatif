"""
pixelsnap.py — Nettoyage des pixels flous dans un sprite pixel-art upscalé
===========================================================================
Problème : un sprite upscalé avec interpolation bilinéaire/bicubique a des
pixels "fondus" — chaque bloc N×N de pixels devrait être une couleur unie
mais contient des dégradés aux bords.

Solution : détecter la taille de bloc N, puis pour chaque bloc N×N remplacer
tous ses pixels par la couleur représentative (médiane, moyenne ou mode).

Méthodes disponibles :
    median  — médiane canal par canal (robuste au bruit, default)
    mean    — moyenne (lissage doux, préserve les transitions)
    mode    — couleur la plus fréquente (pixels les plus nets)

Usage via process.py :
    python scripts/process.py inputs/sprite.png pixelsnap
    python scripts/process.py inputs/sprite.png pixelsnap method=mode block=4
"""

import numpy as np
from PIL import Image
from math import gcd
from functools import reduce


# ─── Détection automatique de la taille de bloc ───────────────────────────────

def detect_block_size(arr: np.ndarray) -> int:
    """
    Estime la taille N des pixels agrandis via GCD des runs de pixels identiques.
    Analyse plusieurs lignes et colonnes pour robustesse.
    """
    h, w = arr.shape[:2]
    all_runs = []

    # Échantillonne plusieurs lignes et colonnes
    for frac in (0.25, 0.5, 0.75):
        for axis in (0, 1):
            if axis == 0:
                line = arr[int(h * frac)]       # ligne horizontale
            else:
                line = arr[:, int(w * frac)]    # colonne verticale

            runs = []
            count = 1
            for i in range(1, len(line)):
                if np.array_equal(line[i], line[i - 1]):
                    count += 1
                else:
                    runs.append(count)
                    count = 1
            runs.append(count)
            all_runs.extend(r for r in runs if r > 0)

    if not all_runs:
        return 1

    g = reduce(gcd, all_runs)
    return max(1, min(g, 16))   # cap à 16px de bloc


# ─── Algorithme principal ────────────────────────────────────────────────────

def snap(img: Image.Image, block: int = 0, method: str = "median") -> Image.Image:
    """
    Uniformise chaque bloc N×N de pixels avec sa couleur représentative.

    Args:
        img    : image PIL (RGB ou RGBA)
        block  : taille du bloc en pixels (0 = auto-détection)
        method : 'median' | 'mean' | 'mode'

    Returns:
        Image PIL nettoyée.
    """
    has_alpha = img.mode == "RGBA"
    arr = np.array(img.convert("RGBA" if has_alpha else "RGB"), dtype=np.uint8)
    h, w = arr.shape[:2]
    channels = arr.shape[2]

    # Auto-détection de la taille de bloc si non fournie
    N = block if block > 1 else detect_block_size(arr[:, :, :3])
    if N <= 1:
        # Rien à faire — pixels natifs
        return img.copy()

    result = arr.copy()

    for y in range(0, h, N):
        for x in range(0, w, N):
            patch = arr[y:y + N, x:x + N]          # peut être plus petit aux bords
            pixels = patch.reshape(-1, channels)    # (k, C)

            if method == "mean":
                color = np.mean(pixels, axis=0).astype(np.uint8)

            elif method == "mode":
                # Couleur la plus fréquente canal par canal serait inexacte ;
                # on cherche le pixel le plus fréquent comme tuple.
                px_tuples = [tuple(p) for p in pixels.tolist()]
                from collections import Counter
                color = np.array(Counter(px_tuples).most_common(1)[0][0], dtype=np.uint8)

            else:  # median (default)
                color = np.median(pixels, axis=0).astype(np.uint8)

            result[y:y + N, x:x + N] = color

    mode = "RGBA" if has_alpha else "RGB"
    return Image.fromarray(result, mode)


# ─── Dict METHODS exposé pour workflow.py ────────────────────────────────────

METHODS = {
    "median": lambda img, **kw: snap(img, block=int(kw.get("block", 0)), method="median"),
    "mean":   lambda img, **kw: snap(img, block=int(kw.get("block", 0)), method="mean"),
    "mode":   lambda img, **kw: snap(img, block=int(kw.get("block", 0)), method="mode"),
}
