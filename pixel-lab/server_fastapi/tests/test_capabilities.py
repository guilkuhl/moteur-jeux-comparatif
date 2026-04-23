"""Tests pour /api/capabilities — sonde GPU."""
from __future__ import annotations

from server_fastapi.services import gpu_util


def test_capabilities_shape(client):
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    body = res.json()
    assert "gpu" in body
    assert set(body["gpu"].keys()) == {"available", "device_count", "device_name"}
    assert isinstance(body["gpu"]["available"], bool)
    assert isinstance(body["gpu"]["device_count"], int)


def test_is_cuda_available_returns_bool():
    # On ne peut pas forcer la présence de CUDA dans la sandbox ; on vérifie
    # seulement la signature et que le cache lru ne propage pas d'exception.
    gpu_util.is_cuda_available.cache_clear()
    assert isinstance(gpu_util.is_cuda_available(), bool)


def test_preview_accepts_use_gpu_flag(client, test_input_image, reset_preview_cache):
    body = {
        "image": test_input_image,
        "pipeline": [
            {"algo": "denoise", "method": "bilateral", "params": {"d": 5}},
        ],
        "use_gpu": True,
    }
    res = client.post("/api/preview", json=body)
    # Avec ou sans GPU réel, la requête doit aboutir (fallback CPU transparent).
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/png")
