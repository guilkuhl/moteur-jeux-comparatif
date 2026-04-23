"""Tests de dédup en vol sur /api/preview (concurrent identical requests → 1 calcul)."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_concurrent_identical_previews_share_one_render(
    test_input_image, reset_preview_cache,
):
    """Spec pixel-art-conversion-api § "deux previews identiques concurrents".

    Deux POST /api/preview identiques lancés en parallèle avec cache vide
    SHALL invoquer preview_runner.render exactement une fois.
    """
    from server_fastapi.main import app
    from server_fastapi.services import preview_runner

    calls = 0
    real_render = preview_runner.render
    render_gate = asyncio.Event()

    def counting_render(*args, **kwargs):
        nonlocal calls
        calls += 1
        # Cède la main pour que le second appel puisse trouver l'entrée inflight
        # avant que la factory ne finisse.
        import time as _t
        _t.sleep(0.05)
        return real_render(*args, **kwargs)

    payload = {
        "image": test_input_image,
        "pipeline": [
            {"algo": "sharpen", "method": "unsharp_mask",
             "params": {"radius": 1.0, "percent": 150}}
        ],
        "downscale": 64,
    }

    with patch.object(preview_runner, "render", side_effect=counting_render):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            render_gate.set()
            r1_task = asyncio.create_task(ac.post("/api/preview", json=payload))
            r2_task = asyncio.create_task(ac.post("/api/preview", json=payload))
            r1, r2 = await asyncio.gather(r1_task, r2_task)

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Même PNG octet-à-octet
    assert r1.content == r2.content
    # UN SEUL calcul partagé par les deux
    assert calls == 1, f"preview_runner.render appelé {calls} fois, attendu 1"


@pytest.mark.asyncio
async def test_isolated_preview_still_works(test_input_image, reset_preview_cache):
    """Sanity : un appel isolé reste 200 avec PNG valide (pas de régression)."""
    from server_fastapi.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/preview",
            json={
                "image": test_input_image,
                "pipeline": [
                    {"algo": "sharpen", "method": "unsharp_mask",
                     "params": {"radius": 1.0, "percent": 150}}
                ],
                "downscale": 64,
            },
        )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
