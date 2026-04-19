"""
Sharpening / dé-flou pour images pixel-art.
Plusieurs modes disponibles : unsharp_mask, laplacian, custom_kernel.
"""

from PIL import Image, ImageFilter
import numpy as np
import cv2


def unsharp_mask(img: Image.Image, radius: float = 1.0, percent: int = 150, threshold: int = 3) -> Image.Image:
    """Unsharp mask — le classique. Fonctionne bien pour dé-flouter sans artefacts."""
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def laplacian_sharpen(img: Image.Image, strength: float = 1.0) -> Image.Image:
    """Sharpen via laplacien OpenCV. Agressif, bon pour récupérer les bords pixel."""
    has_alpha = img.mode == "RGBA"
    arr = np.array(img.convert("RGB"))   # cv2 Laplacian fonctionne sur 3 canaux
    lap = cv2.Laplacian(arr, cv2.CV_64F)
    sharpened = np.clip(arr - strength * lap, 0, 255).astype(np.uint8)
    result = Image.fromarray(sharpened, "RGB")
    if has_alpha:
        result = result.convert("RGBA")
        result.putalpha(img.split()[3])
    return result


def kernel_sharpen(img: Image.Image, amount: float = 1.5) -> Image.Image:
    """Sharpen par convolution avec un kernel paramétrable."""
    center = 1 + 4 * amount
    side = -amount
    kernel = ImageFilter.Kernel(
        size=(3, 3),       # PIL 9+ exige un tuple, pas un int
        kernel=[0, side, 0, side, center, side, 0, side, 0],
        scale=1,
        offset=0
    )
    # ImageFilter.Kernel ne supporte pas RGBA — traiter sur RGB puis restaurer alpha
    if img.mode == "RGBA":
        rgb = img.convert("RGB").filter(kernel)
        result = rgb.convert("RGBA")
        result.putalpha(img.split()[3])  # restaurer canal alpha original
        return result
    return img.filter(kernel)


METHODS = {
    "unsharp_mask": unsharp_mask,
    "laplacian": laplacian_sharpen,
    "kernel": kernel_sharpen,
}

PARAMS = {
    "unsharp_mask": [
        {"name": "radius",    "type": "float", "default": 1.0, "min": 0.1, "max": 10.0},
        {"name": "percent",   "type": "int",   "default": 150, "min": 0,   "max": 500},
        {"name": "threshold", "type": "int",   "default": 3,   "min": 0,   "max": 255},
    ],
    "laplacian": [
        {"name": "strength", "type": "float", "default": 1.0, "min": 0.1, "max": 5.0},
    ],
    "kernel": [
        {"name": "amount", "type": "float", "default": 1.5, "min": 0.1, "max": 5.0},
    ],
}
