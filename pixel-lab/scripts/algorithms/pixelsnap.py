"""
pixelsnap.py — Nettoyage des pixels flous dans un sprite pixel-art upscalé
===========================================================================
Problème : un sprite upscalé avec interpolation bilinéaire/bicubique a des
pixels "fondus" — chaque bloc N×N de pixels devrait être une couleur unie
mais contient des dégradés aux bords.

Solution : détecter la taille de bloc N + la phase (offset_x, offset_y) du
grid, puis pour chaque bloc N×N remplacer tous ses pixels par la couleur
représentative (médiane, moyenne ou mode).

En mode sprite-sheet (cells=1), l'image est segmentée en cellules via
bgdetect (composants connexes du foreground) et chaque cellule reçoit sa
propre (N, offset_x, offset_y) — utile quand le sheet est mal aligné et
que chaque sprite dérive légèrement en ligne/colonne.

Méthodes disponibles :
    median  — médiane canal par canal (robuste au bruit, default)
    mean    — moyenne (lissage doux, préserve les transitions)
    mode    — couleur la plus fréquente (pixels les plus nets)

Usage via process.py :
    python scripts/process.py inputs/sprite.png pixelsnap
    python scripts/process.py inputs/sprite.png pixelsnap method=mode block=4
    python scripts/process.py inputs/sprite.png pixelsnap cells=1
"""

from collections import Counter, deque

import numpy as np
from PIL import Image

from . import bgdetect

# ─── Détection automatique de la taille de bloc ───────────────────────────────

def _gray(arr: np.ndarray) -> np.ndarray:
    """Luminance perceptuelle (float32) à partir d'un tableau RGB(A)."""
    return (0.299 * arr[:, :, 0].astype(np.float32)
            + 0.587 * arr[:, :, 1]
            + 0.114 * arr[:, :, 2])


def _period_from_autocorr(signal: np.ndarray, max_period: int = 64) -> int:
    n = len(signal)
    if n < 6:
        return 0
    sig = signal - signal.mean()
    fft_vals = np.fft.rfft(sig, n=2 * n)
    ac = np.fft.irfft(fft_vals * np.conj(fft_vals))[:n]
    if ac[0] < 1e-8:
        return 0
    ac = ac / ac[0]
    limit = min(max_period + 1, n // 2)
    for lag in range(2, limit):
        if (ac[lag] > ac[lag - 1]
                and ac[lag] > ac[min(lag + 1, n - 1)]
                and ac[lag] > 0.10):
            return lag
    return 0


def detect_block_size(arr: np.ndarray) -> int:
    """
    Détecte la taille N des blocs pixel via autocorrélation du gradient.

    Robuste aux pixels interpolés des images AI : même si les pixels ne sont
    pas identiques en bord de bloc, le gradient présente une périodicité N
    révélée par l'autocorrélation FFT.
    """
    gray = _gray(arr)
    col_profile = np.abs(np.diff(gray, axis=1)).mean(axis=0)   # (w-1,)
    row_profile = np.abs(np.diff(gray, axis=0)).mean(axis=1)   # (h-1,)

    p_col = _period_from_autocorr(col_profile)
    p_row = _period_from_autocorr(row_profile)

    periods = [p for p in [p_col, p_row] if p >= 2]
    if not periods:
        return 1

    period = Counter(periods).most_common(1)[0][0]
    return max(2, min(period, 64))


# ─── Détection de phase (offset du grid) ─────────────────────────────────────

def _detect_phase_1d(profile: np.ndarray, N: int) -> int:
    """
    Retourne l'offset ox ∈ [0, N) où le grid N commence, en maximisant
    l'énergie de gradient aux frontières de bloc présumées.

    Principe : profile[i] = gradient entre pixel i et i+1. Si le grid démarre
    à l'offset ox (les blocs couvrent [ox, ox+N-1], [ox+N, ox+2N-1], …), les
    frontières tombent aux indices (ox-1) + k*N. On replie le profil modulo
    N et l'argmax donne (ox-1) mod N.
    """
    m = len(profile) // N
    if m < 2 or N < 2:
        return 0
    folded = profile[:m * N].reshape(m, N)        # (m, N)
    energy = folded.sum(axis=0)                    # (N,)
    best_boundary = int(np.argmax(energy))         # position (ox-1) mod N
    return (best_boundary + 1) % N


def detect_phase(arr: np.ndarray, N: int) -> tuple:
    """Retourne (offset_x, offset_y) ∈ [0,N)² du grid N×N."""
    if N < 2:
        return (0, 0)
    gray = _gray(arr)
    col_profile = np.abs(np.diff(gray, axis=1)).mean(axis=0)   # (w-1,)
    row_profile = np.abs(np.diff(gray, axis=0)).mean(axis=1)   # (h-1,)
    ox = _detect_phase_1d(col_profile, N)
    oy = _detect_phase_1d(row_profile, N)
    return (ox, oy)


# ─── Segmentation en cellules (sprite sheet) ─────────────────────────────────

def _label_components(mask: np.ndarray, min_area: int = 16) -> list:
    """
    BFS 4-connexe sur `mask` (True = foreground). Retourne une liste de
    bounding boxes (y0, x0, y1, x1) avec y1/x1 exclusifs, filtrées par
    min_area pour éliminer le bruit isolé.
    """
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    boxes = []
    for start_y in range(h):
        for start_x in range(w):
            if not mask[start_y, start_x] or visited[start_y, start_x]:
                continue
            dq = deque([(start_y, start_x)])
            visited[start_y, start_x] = True
            y0 = y1 = start_y
            x0 = x1 = start_x
            area = 0
            while dq:
                y, x = dq.popleft()
                area += 1
                if y < y0: y0 = y
                if y > y1: y1 = y
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y > 0 and mask[y - 1, x] and not visited[y - 1, x]:
                    visited[y - 1, x] = True; dq.append((y - 1, x))
                if y + 1 < h and mask[y + 1, x] and not visited[y + 1, x]:
                    visited[y + 1, x] = True; dq.append((y + 1, x))
                if x > 0 and mask[y, x - 1] and not visited[y, x - 1]:
                    visited[y, x - 1] = True; dq.append((y, x - 1))
                if x + 1 < w and mask[y, x + 1] and not visited[y, x + 1]:
                    visited[y, x + 1] = True; dq.append((y, x + 1))
            if area >= min_area:
                boxes.append((y0, x0, y1 + 1, x1 + 1))
    return boxes


# ─── Remplacement bloc par bloc aligné sur (ox, oy) ─────────────────────────

def _block_ranges(low: int, high: int, offset: int, N: int) -> list:
    """Liste (start, end) des blocs alignés sur offset dans [low, high)."""
    ranges = []
    if offset > 0 and low < high:
        ranges.append((low, min(low + offset, high)))
    y = low + offset
    while y < high:
        ranges.append((y, min(y + N, high)))
        y += N
    return ranges


def _replace_patch(patch: np.ndarray, method: str) -> np.ndarray:
    """Retourne la couleur représentative d'un patch (k, C)."""
    pixels = patch.reshape(-1, patch.shape[-1])
    if method == "mean":
        return np.mean(pixels, axis=0).astype(np.uint8)
    if method == "mode":
        px_tuples = [tuple(p) for p in pixels.tolist()]
        return np.array(Counter(px_tuples).most_common(1)[0][0], dtype=np.uint8)
    return np.median(pixels, axis=0).astype(np.uint8)


def _snap_region(result: np.ndarray, src: np.ndarray,
                 y0: int, x0: int, y1: int, x1: int,
                 N: int, ox: int, oy: int, method: str) -> None:
    """Applique le snap bloc-par-bloc sur result[y0:y1, x0:x1] ← src, aligné sur (ox, oy)."""
    for ys, ye in _block_ranges(y0, y1, oy, N):
        for xs, xe in _block_ranges(x0, x1, ox, N):
            color = _replace_patch(src[ys:ye, xs:xe], method)
            result[ys:ye, xs:xe] = color


# ─── Algorithme principal ────────────────────────────────────────────────────

def snap(img: Image.Image, block: int = 0, method: str = "median",
         cells: int = 0, offset_x: int = -1, offset_y: int = -1,
         min_cell_area: int = 64) -> Image.Image:
    """
    Uniformise chaque bloc N×N de pixels avec sa couleur représentative.

    Args:
        img        : image PIL (RGB ou RGBA)
        block      : taille du bloc en pixels (0 = auto-détection)
        method     : 'median' | 'mean' | 'mode'
        cells      : 0 = global, 1 = segmentation auto en cellules (sprite sheet),
                     (N, ox, oy) re-détectés indépendamment par cellule
        offset_x   : phase horizontale ∈ [0, N) ; -1 = auto-détection
        offset_y   : phase verticale ∈ [0, N) ; -1 = auto-détection
        min_cell_area : aire minimale (en pixels) d'un composant connexe pour
                     être traité comme cellule

    Returns:
        Image PIL nettoyée.
    """
    has_alpha = img.mode == "RGBA"
    arr = np.array(img.convert("RGBA" if has_alpha else "RGB"), dtype=np.uint8)
    h, w = arr.shape[:2]
    rgb = arr[:, :, :3]
    result = arr.copy()

    def _apply_region(y0: int, x0: int, y1: int, x1: int) -> None:
        sub_rgb = rgb[y0:y1, x0:x1]
        if sub_rgb.shape[0] < 4 or sub_rgb.shape[1] < 4:
            return
        N = block if block > 1 else detect_block_size(sub_rgb)
        if N <= 1:
            return
        if offset_x >= 0 or offset_y >= 0:
            ox = offset_x % N if offset_x >= 0 else _detect_phase_1d(
                np.abs(np.diff(_gray(sub_rgb), axis=1)).mean(axis=0), N)
            oy = offset_y % N if offset_y >= 0 else _detect_phase_1d(
                np.abs(np.diff(_gray(sub_rgb), axis=0)).mean(axis=1), N)
        else:
            ox, oy = detect_phase(sub_rgb, N)
        _snap_region(result, arr, y0, x0, y1, x1, N, ox, oy, method)

    if cells:
        fg_mask = bgdetect.compute_bg_mask(img)
        if fg_mask.all():
            # Pas de fond détecté → fallback mode global
            _apply_region(0, 0, h, w)
        else:
            boxes = _label_components(fg_mask, min_area=max(4, int(min_cell_area)))
            if not boxes:
                _apply_region(0, 0, h, w)
            for (y0, x0, y1, x1) in boxes:
                _apply_region(y0, x0, y1, x1)
    else:
        _apply_region(0, 0, h, w)

    mode = "RGBA" if has_alpha else "RGB"
    return Image.fromarray(result, mode)


# ─── Dict METHODS exposé pour workflow.py ────────────────────────────────────

def _kw(kw: dict, name: str, default: int) -> int:
    try:
        return int(kw.get(name, default))
    except (TypeError, ValueError):
        return default


def _make(method: str):
    def _fn(img, **kw):
        return snap(img,
                    block=_kw(kw, "block", 0),
                    method=method,
                    cells=_kw(kw, "cells", 0),
                    offset_x=_kw(kw, "offset_x", -1),
                    offset_y=_kw(kw, "offset_y", -1))
    return _fn


METHODS = {
    "median": _make("median"),
    "mean":   _make("mean"),
    "mode":   _make("mode"),
}

_COMMON_PARAMS = [
    {"name": "block",    "type": "int", "default": 0,  "min": 0,  "max": 64},
    {"name": "cells",    "type": "int", "default": 0,  "min": 0,  "max": 1},
    {"name": "offset_x", "type": "int", "default": -1, "min": -1, "max": 63},
    {"name": "offset_y", "type": "int", "default": -1, "min": -1, "max": 63},
]

PARAMS = {
    "median": list(_COMMON_PARAMS),
    "mean":   list(_COMMON_PARAMS),
    "mode":   list(_COMMON_PARAMS),
}
