"""Tests de dédup en vol sur /api/bgmask (concurrent identical requests → 1 calcul)."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_concurrent_identical_bgmask_share_one_compute(test_input_image):
    """Spec pixel-art-conversion-api § "deux bgmask identiques concurrents".

    Deux GET /api/bgmask identiques lancés en parallèle avec cache vide
    SHALL invoquer bgdetect.detect_bg_color exactement une fois.
    """
    from server_fastapi.deps import bgdetect
    from server_fastapi.main import app
    from server_fastapi.services.bgmask_cache import bgmask_cache

    # Cache vide pour forcer le chemin calcul
    bgmask_cache._store.clear()  # noqa: SLF001

    calls = 0
    real_detect = bgdetect.detect_bg_color

    def counting_detect(*args, **kwargs):
        nonlocal calls
        calls += 1
        # Retenir l'exécution pour laisser le 2ᵉ appel attraper l'inflight
        import time as _t
        _t.sleep(0.05)
        return real_detect(*args, **kwargs)

    try:
        with patch.object(bgdetect, "detect_bg_color", side_effect=counting_detect):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                url = (
                    f"/api/bgmask?image={test_input_image}"
                    "&tolerance=10&feather=0&mode=highlight"
                )
                r1_task = asyncio.create_task(ac.get(url))
                r2_task = asyncio.create_task(ac.get(url))
                r1, r2 = await asyncio.gather(r1_task, r2_task)

        assert r1.status_code == 200
        assert r2.status_code == 200
        # Les deux PNG doivent être identiques octet-à-octet
        assert r1.content == r2.content
        # UN SEUL detect_bg_color partagé
        assert calls == 1, f"bgdetect.detect_bg_color appelé {calls} fois, attendu 1"
    finally:
        bgmask_cache._store.clear()  # noqa: SLF001
