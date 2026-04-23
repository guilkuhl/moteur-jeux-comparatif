"""
bgdetect — détection automatique du fond d'un sprite pixel-art.

Stratégie en 3 étapes, arrêt dès qu'une réponse est trouvée :
  1. Bypass RGBA : si l'image a déjà des pixels alpha=0, ceux-ci sont le fond.
  2. Échantillonnage des 4 coins : si ≥3 sont égaux (L∞ ≤ tolerance),
     cette couleur est la bg_color.
  3. Flood-fill depuis les bords en connectivité-4 : marque tous les pixels
     connectés aux bords qui matchent bg_color.

Le masque retourné est booléen H×W avec True = foreground, False = background.
Expose aussi METHODS et PARAMS pour intégration CLI/API standard.
"""
from __future__ import annotations

from collections import deque

import numpy as np
from PIL import Image, ImageFilter

RGB = tuple[int, int, int]


def _to_rgb_array(img: Image.Image) -> np.ndarray:
    """Retourne un ndarray (H, W, 3) uint8 en RGB."""
    if img.mode == "RGBA":
        return np.asarray(img.convert("RGB"), dtype=np.uint8)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.asarray(img, dtype=np.uint8)


def _color_match(a: np.ndarray, b: np.ndarray, tol: int) -> np.ndarray:
    """Retourne un masque booléen H×W où a est égal à b à tol près (L∞)."""
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    return (diff.max(axis=-1) <= tol)


def detect_bg_color(img: Image.Image, tolerance: int = 8) -> RGB | None:
    """Lit les 4 pixels de coin, retourne la couleur de fond si ≥3 coins sont égaux
    (distance L∞ ≤ tolerance), sinon None."""
    arr = _to_rgb_array(img)
    h, w = arr.shape[:2]
    if h < 2 or w < 2:
        return None
    corners = np.stack([
        arr[0, 0],
        arr[0, w - 1],
        arr[h - 1, 0],
        arr[h - 1, w - 1],
    ])  # (4, 3)

    # Pour chaque coin, compte combien d'autres coins sont dans la tolerance
    best_center = None
    best_count = 0
    for i in range(4):
        ref = corners[i]
        matches = np.abs(corners.astype(np.int16) - ref.astype(np.int16)).max(axis=-1) <= tolerance
        count = int(matches.sum())
        if count > best_count:
            best_count = count
            best_center = corners[matches].mean(axis=0).astype(np.uint8)
    if best_count >= 3 and best_center is not None:
        return (int(best_center[0]), int(best_center[1]), int(best_center[2]))
    return None


def _flood_fill_from_edges(arr: np.ndarray, bg_color: RGB, tolerance: int) -> np.ndarray:
    """BFS connectivity-4 depuis chaque pixel de bord matchant bg_color.
    Retourne un masque bool H×W, True = fond atteint par flood-fill."""
    h, w = arr.shape[:2]
    ref = np.array(bg_color, dtype=np.uint8)
    candidate = _color_match(arr, ref, tolerance)  # True = peut être fond
    bg = np.zeros((h, w), dtype=bool)

    dq: deque = deque()
    # Seed : bords (top, bottom, left, right)
    for x in range(w):
        if candidate[0, x] and not bg[0, x]:
            bg[0, x] = True; dq.append((0, x))
        if candidate[h - 1, x] and not bg[h - 1, x]:
            bg[h - 1, x] = True; dq.append((h - 1, x))
    for y in range(1, h - 1):
        if candidate[y, 0] and not bg[y, 0]:
            bg[y, 0] = True; dq.append((y, 0))
        if candidate[y, w - 1] and not bg[y, w - 1]:
            bg[y, w - 1] = True; dq.append((y, w - 1))

    while dq:
        y, x = dq.popleft()
        if y > 0 and candidate[y - 1, x] and not bg[y - 1, x]:
            bg[y - 1, x] = True; dq.append((y - 1, x))
        if y + 1 < h and candidate[y + 1, x] and not bg[y + 1, x]:
            bg[y + 1, x] = True; dq.append((y + 1, x))
        if x > 0 and candidate[y, x - 1] and not bg[y, x - 1]:
            bg[y, x - 1] = True; dq.append((y, x - 1))
        if x + 1 < w and candidate[y, x + 1] and not bg[y, x + 1]:
            bg[y, x + 1] = True; dq.append((y, x + 1))
    return bg


def compute_bg_mask(
    img: Image.Image,
    bg_color: RGB | None = None,
    tolerance: int = 8,
    feather: int = 0,
) -> np.ndarray:
    """Retourne un masque booléen H×W (True = foreground, False = background).

    - Si img est RGBA avec alpha=0 présent → masque = (alpha > 0), bypass.
    - Sinon, détecte bg_color si None, puis flood-fill depuis les bords.
    - Si aucun fond détecté → masque True partout (rien à préserver).
    - feather > 0 : dilatation binaire + flou gaussien pour adoucir les bords.
    """
    # 1. Bypass RGBA
    if img.mode == "RGBA":
        alpha = np.asarray(img.split()[-1], dtype=np.uint8)
        if (alpha == 0).any():
            mask = alpha > 0
            return _apply_feather(mask, feather) if feather > 0 else mask

    arr = _to_rgb_array(img)

    # 2. Détection bg_color si pas fournie
    if bg_color is None:
        bg_color = detect_bg_color(img, tolerance=tolerance)
    if bg_color is None:
        # Aucun fond détecté → tout est foreground
        return np.ones(arr.shape[:2], dtype=bool)

    # 3. Flood-fill depuis les bords
    bg_mask = _flood_fill_from_edges(arr, bg_color, tolerance)
    foreground = ~bg_mask

    # 4. Feather optionnel
    if feather > 0:
        foreground = _apply_feather(foreground, feather)
    return foreground


def _apply_feather(mask: np.ndarray, radius: int) -> np.ndarray:
    """Dilate le masque foreground de `radius` pixels et le reconvertit en booléen.
    Simple mais suffisant pour V1 ; V2 pourra exposer un masque float32 soft."""
    # Conversion en image PIL en niveaux de gris pour réutiliser ImageFilter
    img = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    img = img.filter(ImageFilter.MaxFilter(size=max(3, 2 * radius + 1)))
    img = img.filter(ImageFilter.GaussianBlur(radius=max(1, radius // 2)))
    arr = np.asarray(img)
    return arr >= 128


def composite_preserve_bg(src: Image.Image, out: Image.Image) -> Image.Image:
    """Compose : conserve les pixels foreground de `out` et réinjecte les pixels
    de fond de `src`. Si aucun fond n'est détecté, retourne `out` inchangé."""
    mask = compute_bg_mask(src)
    if mask.all():
        # Pas de fond détecté → pas de composition
        return out

    src_arr = np.asarray(src.convert(out.mode), dtype=np.uint8)
    out_arr = np.asarray(out, dtype=np.uint8).copy()

    # mask True = foreground → garder out. False = fond → restaurer src.
    bg_pixels = ~mask
    out_arr[bg_pixels] = src_arr[bg_pixels]
    return Image.fromarray(out_arr, mode=out.mode)


def _auto(img: Image.Image, tolerance: int = 8, feather: int = 0) -> Image.Image:
    """Wrapper "algo" standard : retourne une image PIL de visualisation
    (alpha=0 pour fond, alpha=255 pour foreground ; RGB = bg_color ou noir).
    Utile pour le bouton 🎯 Détecter fond dans le dashboard."""
    mask = compute_bg_mask(img, tolerance=tolerance, feather=feather)
    bg = detect_bg_color(img, tolerance=tolerance) or (0, 0, 0)
    h, w = mask.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., 0] = bg[0]
    out[..., 1] = bg[1]
    out[..., 2] = bg[2]
    out[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


METHODS = {"auto": _auto}
PARAMS = {
    "auto": [
        {"name": "tolerance", "type": "int", "default": 8, "min": 0, "max": 50},
        {"name": "feather",   "type": "int", "default": 0, "min": 0, "max": 5},
    ],
}


if __name__ == "__main__":
    # Test manuel rapide : charger une image, afficher la couleur détectée
    import sys
    from pathlib import Path
    if len(sys.argv) < 2:
        print("Usage : python -m algorithms.bgdetect <image.png>")
        sys.exit(1)
    p = Path(sys.argv[1])
    img = Image.open(p)
    color = detect_bg_color(img)
    mask = compute_bg_mask(img)
    fg_ratio = float(mask.mean())
    print(f"Image     : {p.name} ({img.size[0]}×{img.size[1]}, mode={img.mode})")
    print(f"bg_color  : {color}")
    print(f"foreground: {fg_ratio:.1%} des pixels")
