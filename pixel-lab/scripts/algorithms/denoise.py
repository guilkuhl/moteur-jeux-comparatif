"""
Réduction de bruit pour images pixel-art compressées (JPEG artifacts, etc.)

Chaque méthode accepte un paramètre optionnel `preserve_bg` (défaut False) :
quand True, les pixels classés comme fond (via bgdetect.compute_bg_mask)
sont réinjectés à l'original après traitement.
"""

import logging

import cv2
import numpy as np
from PIL import Image

from . import bgdetect

_logger = logging.getLogger("pixel_lab.denoise")


def _try_gpu_bilateral(
    arr: np.ndarray, d: int, sigma_color: float, sigma_space: float
) -> np.ndarray | None:
    """Essaye d'exécuter le filtre bilatéral sur GPU. Retourne None si échec."""
    cuda = getattr(cv2, "cuda", None)
    if cuda is None:
        return None
    try:
        if cuda.getCudaEnabledDeviceCount() == 0:
            return None
    except Exception:  # noqa: BLE001
        return None
    try:
        gpu_mat = cv2.cuda_GpuMat()
        gpu_mat.upload(arr)
        gpu_out = cv2.cuda.bilateralFilter(gpu_mat, d, sigma_color, sigma_space)
        return gpu_out.download()
    except Exception:  # noqa: BLE001
        _logger.info("cv2.cuda.bilateralFilter indisponible, fallback CPU", exc_info=True)
        return None


def _maybe_preserve_bg(src: Image.Image, out: Image.Image, preserve_bg: bool) -> Image.Image:
    if not preserve_bg:
        return out
    return bgdetect.composite_preserve_bg(src, out)


def median_filter(img: Image.Image, size: int = 3, preserve_bg: bool = False) -> Image.Image:
    """Filtre médian — efficace contre les artefacts de compression JPEG."""
    arr = np.array(img)
    if arr.ndim == 3:
        denoised = np.stack([cv2.medianBlur(arr[:, :, c], size) for c in range(arr.shape[2])], axis=2)
    else:
        denoised = cv2.medianBlur(arr, size)
    out = Image.fromarray(denoised.astype(np.uint8))
    return _maybe_preserve_bg(img, out, preserve_bg)


def bilateral_filter(
    img: Image.Image,
    d: int = 9,
    sigma_color: float = 75,
    sigma_space: float = 75,
    preserve_bg: bool = False,
    use_gpu: bool = False,
) -> Image.Image:
    """Filtre bilatéral : lisse le bruit tout en préservant les bords nets.

    Si `use_gpu=True` et qu'OpenCV a été buildé avec CUDA, tente le chemin
    `cv2.cuda.bilateralFilter` — sinon fallback CPU silencieux.
    """
    arr = np.array(img.convert("RGB"))
    denoised: np.ndarray | None = None
    if use_gpu:
        denoised = _try_gpu_bilateral(arr, d, sigma_color, sigma_space)
    if denoised is None:
        denoised = cv2.bilateralFilter(arr, d, sigma_color, sigma_space)
    result = Image.fromarray(denoised)
    if img.mode != "RGB":
        result = result.convert(img.mode)
    return _maybe_preserve_bg(img, result, preserve_bg)


def nlm_denoise(img: Image.Image, h: float = 10, template_size: int = 7, search_size: int = 21, preserve_bg: bool = False) -> Image.Image:
    """Non-Local Means via OpenCV — le plus puissant pour la réduction de bruit."""
    arr = np.array(img.convert("RGB"))
    denoised = cv2.fastNlMeansDenoisingColored(arr, None, h, h, template_size, search_size)
    result = Image.fromarray(denoised)
    if img.mode != "RGB":
        result = result.convert(img.mode)
    return _maybe_preserve_bg(img, result, preserve_bg)


METHODS = {
    "median": median_filter,
    "bilateral": bilateral_filter,
    "nlm": nlm_denoise,
}

PARAMS = {
    "median": [
        {"name": "size",        "type": "int",  "default": 3, "min": 1, "max": 15},
        {"name": "preserve_bg", "type": "bool", "default": False},
    ],
    "bilateral": [
        {"name": "d",           "type": "int",   "default": 9,  "min": 1, "max": 25},
        {"name": "sigma_color", "type": "float", "default": 75, "min": 1, "max": 200},
        {"name": "sigma_space", "type": "float", "default": 75, "min": 1, "max": 200},
        {"name": "preserve_bg", "type": "bool",  "default": False},
    ],
    "nlm": [
        {"name": "h",             "type": "float", "default": 10, "min": 1,  "max": 50},
        {"name": "template_size", "type": "int",   "default": 7,  "min": 3,  "max": 21},
        {"name": "search_size",   "type": "int",   "default": 21, "min": 7,  "max": 63},
        {"name": "preserve_bg",   "type": "bool",  "default": False},
    ],
}
