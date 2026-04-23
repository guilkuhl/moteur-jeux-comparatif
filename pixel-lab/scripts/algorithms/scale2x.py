"""
Algorithmes de pixel-art upscaling sans flou.
- nearest  : plus proche voisin (le classique pixel-art)
- scale2x  : Scale2X (AdvMAME2x) — lisse les diagonales sans interpoler
- xbr2x    : xBR simplifié via cv2 + post-traitement
- eagle    : Eagle2x
"""

import numpy as np
from PIL import Image


def nearest(img: Image.Image, scale: int = 2) -> Image.Image:
    """Agrandissement au plus proche voisin — bords parfaitement nets."""
    w, h = img.size
    return img.resize((w * scale, h * scale), Image.NEAREST)


def scale2x(img: Image.Image) -> Image.Image:
    """
    Scale2X (AdvMAME2x) pur Python/NumPy.
    Lisse les diagonales en analysant les pixels voisins.
    """
    src = np.array(img.convert("RGBA"))
    h, w = src.shape[:2]
    dst = np.zeros((h * 2, w * 2, 4), dtype=np.uint8)

    # Pad pour éviter les bords
    p = np.pad(src, ((1, 1), (1, 1), (0, 0)), mode='edge')

    for y in range(h):
        for x in range(w):
            B = p[y,     x + 1]  # haut
            D = p[y + 1, x]      # gauche
            E = p[y + 1, x + 1]  # centre
            F = p[y + 1, x + 2]  # droite
            H = p[y + 2, x + 1]  # bas

            def eq(a, b): return np.array_equal(a, b)

            E0 = D if (eq(D, B) and not eq(D, H) and not eq(B, F)) else E
            E1 = F if (eq(B, F) and not eq(B, D) and not eq(F, H)) else E
            E2 = D if (eq(H, D) and not eq(H, F) and not eq(D, B)) else E
            E3 = F if (eq(F, H) and not eq(F, B) and not eq(H, D)) else E

            dst[y * 2,     x * 2]     = E0
            dst[y * 2,     x * 2 + 1] = E1
            dst[y * 2 + 1, x * 2]     = E2
            dst[y * 2 + 1, x * 2 + 1] = E3

    result = Image.fromarray(dst, "RGBA")
    if img.mode != "RGBA":
        result = result.convert(img.mode)
    return result


def eagle2x(img: Image.Image) -> Image.Image:
    """
    Eagle2x : chaque pixel devient 2x2 en fonction de ses 4 voisins diagonaux.
    """
    src = np.array(img.convert("RGBA"))
    h, w = src.shape[:2]
    dst = np.zeros((h * 2, w * 2, 4), dtype=np.uint8)

    p = np.pad(src, ((1, 1), (1, 1), (0, 0)), mode='edge')

    for y in range(h):
        for x in range(w):
            S = p[y,     x]      # haut-gauche
            T = p[y,     x + 1]  # haut
            U = p[y,     x + 2]  # haut-droite
            V = p[y + 1, x]      # gauche
            E = p[y + 1, x + 1]  # centre
            W = p[y + 1, x + 2]  # droite
            X = p[y + 2, x]      # bas-gauche
            Y = p[y + 2, x + 1]  # bas
            Z = p[y + 2, x + 2]  # bas-droite

            def eq(a, b): return np.array_equal(a, b)

            E0 = S if (eq(S, T) and eq(S, V)) else E
            E1 = U if (eq(T, U) and eq(U, W)) else E
            E2 = X if (eq(V, X) and eq(X, Y)) else E
            E3 = Z if (eq(W, Z) and eq(Y, Z)) else E

            dst[y * 2,     x * 2]     = E0
            dst[y * 2,     x * 2 + 1] = E1
            dst[y * 2 + 1, x * 2]     = E2
            dst[y * 2 + 1, x * 2 + 1] = E3

    result = Image.fromarray(dst, "RGBA")
    if img.mode != "RGBA":
        result = result.convert(img.mode)
    return result


METHODS = {
    "nearest": nearest,
    "scale2x": scale2x,
    "eagle2x": eagle2x,
}

PARAMS = {
    "nearest": [
        {"name": "scale", "type": "int", "default": 2, "min": 1, "max": 8},
    ],
    "scale2x": [],
    "eagle2x": [],
}
