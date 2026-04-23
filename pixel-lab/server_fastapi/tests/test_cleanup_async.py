"""Tests de non-blocage de la boucle asyncio pendant les calculs cleanup."""
from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def grid_2x2(test_input_image) -> Iterator[str]:
    from server_fastapi.services import history_store

    stem = "test_small"

    def _install(h: dict) -> None:
        h.setdefault(stem, {"source": f"inputs/{test_input_image}", "runs": []})
        h[stem]["slicing"] = {
            "base": {"cols": 2, "rows": 2, "cellW": 16, "cellH": 16,
                     "gapX": 0, "gapY": 0, "marginX": 0, "marginY": 0},
            "overrides": [],
        }

    history_store.update(_install)
    yield test_input_image


@pytest.mark.asyncio
async def test_detect_duplicates_does_not_block_event_loop(grid_2x2):
    """Un cleanup lent SHALL laisser un autre endpoint répondre en parallèle.

    Spec pixel-art-conversion-api § "detect-duplicates n'interfère pas avec
    un autre endpoint".
    """
    from server_fastapi.main import app
    from server_fastapi.routers import cleanup

    # Injecte une latence dans le calcul pour simuler un gros spritesheet.
    # Si le handler bloque la boucle, /api/capabilities ne pourra pas répondre
    # avant la fin de cette latence.
    real_compute = cleanup._compute_duplicates

    def slow_compute(*args, **kwargs):
        time.sleep(0.5)  # 500 ms CPU dans un thread
        return real_compute(*args, **kwargs)

    transport = ASGITransport(app=app)
    with patch.object(cleanup, "_compute_duplicates", side_effect=slow_compute):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Lance le cleanup lent en arrière-plan
            cleanup_task = asyncio.create_task(
                ac.post(
                    "/api/cleanup/detect-duplicates",
                    json={"image": grid_2x2, "similarity_threshold": 5},
                )
            )
            # Laisse 50 ms pour que le handler démarre et prenne un thread
            await asyncio.sleep(0.05)

            # Un endpoint léger DOIT répondre sans attendre la fin du cleanup
            t0 = time.perf_counter()
            r_caps = await ac.get("/api/capabilities")
            elapsed_light = (time.perf_counter() - t0) * 1000

            r_cleanup = await cleanup_task

    assert r_caps.status_code == 200
    assert r_cleanup.status_code == 200
    # Le handler léger SHALL répondre en < 100 ms (bien avant la fin des 500 ms
    # du cleanup). Sans offload, il attendrait que la boucle soit libre.
    assert elapsed_light < 250, (
        f"/api/capabilities a pris {elapsed_light:.0f} ms — la boucle asyncio "
        f"semble bloquée par detect_duplicates"
    )
