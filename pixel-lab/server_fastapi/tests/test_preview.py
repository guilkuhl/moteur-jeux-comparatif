"""POST /api/preview — scenarios canonique pixel-art-conversion-api."""
from __future__ import annotations


def test_preview_returns_binary_png_with_metadata_headers(
    client, test_input_image, reset_preview_cache,
):
    """Spec: pixel-art-conversion-api § "Réponse réussie au format binaire"."""
    payload = {
        "image": test_input_image,
        "pipeline": [
            {"algo": "sharpen", "method": "unsharp_mask", "params": {"radius": 1.0, "percent": 150}}
        ],
        "downscale": 64,
    }
    r = client.post("/api/preview", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    # PNG magic number
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    # Headers métadonnées présents et entiers. L'image source est 32×32 donc
    # le thumbnail borné par 64 la laisse telle quelle (max dim ≤ bound).
    assert int(r.headers["x-width"]) == 32
    assert int(r.headers["x-height"]) == 32
    assert int(r.headers["x-elapsed-ms"]) >= 0
    assert int(r.headers["x-cache-hit-depth"]) == 0  # premier appel, cache vide


def test_preview_cache_hit_depth_bumps_on_shared_prefix(
    client, test_input_image, reset_preview_cache,
):
    """Spec: pixel-art-conversion-api § "Header de cache hit"."""
    payload1 = {
        "image": test_input_image,
        "pipeline": [
            {"algo": "sharpen", "method": "unsharp_mask", "params": {"radius": 1.0, "percent": 150}}
        ],
        "downscale": 64,
    }
    r1 = client.post("/api/preview", json=payload1)
    assert r1.status_code == 200
    assert int(r1.headers["x-cache-hit-depth"]) == 0

    # Même 1ère étape → la seconde doit partir du cache (depth=1)
    payload2 = {
        **payload1,
        "pipeline": payload1["pipeline"] + [
            {"algo": "denoise", "method": "median", "params": {"size": 3}}
        ],
    }
    r2 = client.post("/api/preview", json=payload2)
    assert r2.status_code == 200
    assert int(r2.headers["x-cache-hit-depth"]) == 1


def test_preview_bad_method_returns_422_json(client):
    """Spec: pixel-art-conversion-api § "Erreur de validation reste en JSON"."""
    r = client.post(
        "/api/preview",
        json={
            "image": "irrelevant.png",
            "pipeline": [{"algo": "sharpen", "method": "inexistant"}],
            "downscale": 256,
        },
    )
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/json")
    assert "errors" in r.json()
