"""
Réduction de bruit pour images pixel-art compressées (JPEG artifacts, etc.)
"""

from PIL import Image
import numpy as np
import cv2


def median_filter(img: Image.Image, size: int = 3) -> Image.Image:
    """Filtre médian — efficace contre les artefacts de compression JPEG."""
    arr = np.array(img)
    if arr.ndim == 3:
        denoised = np.stack([cv2.medianBlur(arr[:, :, c], size) for c in range(arr.shape[2])], axis=2)
    else:
        denoised = cv2.medianBlur(arr, size)
    return Image.fromarray(denoised.astype(np.uint8))


def bilateral_filter(img: Image.Image, d: int = 9, sigma_color: float = 75, sigma_space: float = 75) -> Image.Image:
    """
    Filtre bilatéral : lisse le bruit tout en préservant les bords nets.
    Très adapté au pixel-art.
    """
    arr = np.array(img.convert("RGB"))
    denoised = cv2.bilateralFilter(arr, d, sigma_color, sigma_space)
    result = Image.fromarray(denoised)
    if img.mode != "RGB":
        result = result.convert(img.mode)
    return result


def nlm_denoise(img: Image.Image, h: float = 10, template_size: int = 7, search_size: int = 21) -> Image.Image:
    """
    Non-Local Means (NLM) via OpenCV — le plus puissant pour la réduction de bruit.
    h : force du débruitage (plus grand = plus lisse, mais perd des détails).
    """
    arr = np.array(img.convert("RGB"))
    denoised = cv2.fastNlMeansDenoisingColored(arr, None, h, h, template_size, search_size)
    result = Image.fromarray(denoised)
    if img.mode != "RGB":
        result = result.convert(img.mode)
    return result


METHODS = {
    "median": median_filter,
    "bilateral": bilateral_filter,
    "nlm": nlm_denoise,
}
