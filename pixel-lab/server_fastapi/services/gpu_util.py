"""Détection des capacités GPU (OpenCV CUDA) et helpers.

La plupart des distributions `opencv-contrib-python-headless` publient le module
`cv2.cuda` comme namespace mais sans backend CUDA actif (comptage = 0). La sonde
retourne alors `False` et l'utilisateur voit un toggle désactivé.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import cv2

logger = logging.getLogger("pixel_lab.gpu")


@lru_cache(maxsize=1)
def is_cuda_available() -> bool:
    """Vrai si OpenCV a été buildé avec CUDA et au moins un device est visible."""
    cuda = getattr(cv2, "cuda", None)
    if cuda is None:
        return False
    try:
        return cuda.getCudaEnabledDeviceCount() > 0
    except Exception:  # noqa: BLE001
        # Certains builds exposent le namespace mais plantent à l'appel.
        logger.debug("cv2.cuda probe raised", exc_info=True)
        return False


def capabilities() -> dict:
    """Retourne un payload stable pour `/api/capabilities`."""
    available = is_cuda_available()
    device_name: str | None = None
    device_count = 0
    if available:
        cuda = cv2.cuda
        try:
            device_count = cuda.getCudaEnabledDeviceCount()
            info = cuda.DeviceInfo(0)
            device_name = info.name()
        except Exception:  # noqa: BLE001
            logger.debug("cv2.cuda device introspection failed", exc_info=True)
    return {
        "gpu": {
            "available": available,
            "device_count": device_count,
            "device_name": device_name,
        }
    }
