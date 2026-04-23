"""
Sharpening / dé-flou pour images pixel-art.
Plusieurs modes disponibles : unsharp_mask, laplacian, custom_kernel.

Chaque méthode accepte un paramètre optionnel `preserve_bg` (défaut False) :
quand True, les pixels classés comme fond (via bgdetect.compute_bg_mask)
sont réinjectés à l'original après traitement.
"""

import cv2
import numpy as np
from PIL import Image, ImageFilter

from . import bgdetect


def _maybe_preserve_bg(src: Image.Image, out: Image.Image, preserve_bg: bool) -> Image.Image:
    if not preserve_bg:
        return out
    return bgdetect.composite_preserve_bg(src, out)


def unsharp_mask(img: Image.Image, radius: float = 1.0, percent: int = 150, threshold: int = 3, preserve_bg: bool = False) -> Image.Image:
    """Unsharp mask — le classique. Fonctionne bien pour dé-flouter sans artefacts."""
    out = img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))
    return _maybe_preserve_bg(img, out, preserve_bg)


def laplacian_sharpen(img: Image.Image, strength: float = 1.0, preserve_bg: bool = False) -> Image.Image:
    """Sharpen via laplacien OpenCV. Agressif, bon pour récupérer les bords pixel."""
    has_alpha = img.mode == "RGBA"
    arr = np.array(img.convert("RGB"))
    lap = cv2.Laplacian(arr, cv2.CV_64F)
    sharpened = np.clip(arr - strength * lap, 0, 255).astype(np.uint8)
    result = Image.fromarray(sharpened, "RGB")
    if has_alpha:
        result = result.convert("RGBA")
        result.putalpha(img.split()[3])
    return _maybe_preserve_bg(img, result, preserve_bg)


def kernel_sharpen(img: Image.Image, amount: float = 1.5, preserve_bg: bool = False) -> Image.Image:
    """Sharpen par convolution avec un kernel paramétrable."""
    center = 1 + 4 * amount
    side = -amount
    kernel = ImageFilter.Kernel(
        size=(3, 3),
        kernel=[0, side, 0, side, center, side, 0, side, 0],
        scale=1,
        offset=0
    )
    if img.mode == "RGBA":
        rgb = img.convert("RGB").filter(kernel)
        result = rgb.convert("RGBA")
        result.putalpha(img.split()[3])
    else:
        result = img.filter(kernel)
    return _maybe_preserve_bg(img, result, preserve_bg)


METHODS = {
    "unsharp_mask": unsharp_mask,
    "laplacian": laplacian_sharpen,
    "kernel": kernel_sharpen,
}

PARAMS = {
    "unsharp_mask": [
        {"name": "radius",      "type": "float", "default": 1.0, "min": 0.1, "max": 10.0},
        {"name": "percent",     "type": "int",   "default": 150, "min": 0,   "max": 500},
        {"name": "threshold",   "type": "int",   "default": 3,   "min": 0,   "max": 255},
        {"name": "preserve_bg", "type": "bool",  "default": False},
    ],
    "laplacian": [
        {"name": "strength",    "type": "float", "default": 1.0, "min": 0.1, "max": 5.0},
        {"name": "preserve_bg", "type": "bool",  "default": False},
    ],
    "kernel": [
        {"name": "amount",      "type": "float", "default": 1.5, "min": 0.1, "max": 5.0},
        {"name": "preserve_bg", "type": "bool",  "default": False},
    ],
}
