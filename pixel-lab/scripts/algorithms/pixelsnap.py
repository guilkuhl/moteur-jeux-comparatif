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
from collections import Counter


# ─── Détection automatique de la taille de bloc ───────────────────────────────

def detect_block_size(arr: np.ndarray) -> int:
    """
    Détecte la taille N des blocs pixel via autocorrélation du gradient.

    Robuste aux pixels interpolés des images AI : même si les pixels ne sont
    pas identiques en bord de bloc, le gradient présente une périodicité N
    révélée par l'autocorrélation FFT.
    """
    h, w = arr.shape[:2]

    # Luminance perceptuelle
    gray = (0.299 * arr[:, :, 0].astype(np.float32)
            + 0.587 * arr[:, :, 1]
            + 0.114 * arr[:, :, 2])

    # Profils 1D : énergie de gradient moyennée sur l'axe perpendiculaire
    col_profile = np.abs(np.diff(gray, axis=1)).mean(axis=0)   # (w-1,)
    row_profile = np.abs(np.diff(gray, axis=0)).mean(axis=1)   # (h-1,)

    def period_from_autocorr(signal: np.ndarray, max_period: int = 64) -> int:
        n = len(signal)
        if n < 6:
            return 0
        sig = signal - signal.mean()
        # Autocorrélation circulaire via FFT (zero-padding pour éviter l'aliasing)
        fft_vals = np.fft.rfft(sig, n=2 * n)
        ac = np.fft.irfft(fft_vals * np.conj(fft_vals))[:n]
        if ac[0] < 1e-8:
            return 0
        ac = ac / ac[0]
        # Premier pic local dans [2, max_period] dépassant le seuil 0.10
        limit = min(max_period + 1, n // 2)
        for lag in range(2, limit):
            if (ac[lag] > ac[lag - 1]
                    and ac[lag] > ac[min(lag + 1, n - 1)]
                    and ac[lag] > 0.10):
                return lag
        return 0

    p_col = period_from_autocorr(col_profile)
    p_row = period_from_autocorr(row_profile)

    periods = [p for p in [p_col, p_row] if p >= 2]
    if not periods:
        return 1

    # Mode des deux estimations (ou unique valeur disponible)
    period = Counter(periods).most_common(1)[0][0]
    return max(2, min(period, 64))


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

PARAMS = {
    "median": [{"name": "block", "type": "int", "default": 0, "min": 0, "max": 64}],
    "mean":   [{"name": "block", "type": "int", "default": 0, "min": 0, "max": 64}],
    "mode":   [{"name": "block", "type": "int", "default": 0, "min": 0, "max": 64}],
}
