"""Tests unitaires pour services.inflight.InflightDedup."""
from __future__ import annotations

import asyncio
import threading

import pytest

from server_fastapi.services.inflight import InflightDedup


@pytest.mark.asyncio
async def test_single_call_returns_factory_result():
    dedup: InflightDedup[int] = InflightDedup()
    calls = 0

    def factory() -> int:
        nonlocal calls
        calls += 1
        return 42

    result = await dedup.run(("k",), factory)
    assert result == 42
    assert calls == 1


@pytest.mark.asyncio
async def test_concurrent_calls_share_one_computation():
    """Deux appels concurrents sur la même clé → factory appelée 1 fois."""
    dedup: InflightDedup[int] = InflightDedup()
    calls = 0
    gate = threading.Event()

    def slow_factory() -> int:
        nonlocal calls
        calls += 1
        # Laisse le temps au second appel de trouver l'entrée inflight
        gate.wait(timeout=2.0)
        return 7

    async def concurrent_call() -> int:
        return await dedup.run(("same",), slow_factory)

    task1 = asyncio.create_task(concurrent_call())
    # Cède la main pour que task1 démarre et insère son Future
    await asyncio.sleep(0.05)
    task2 = asyncio.create_task(concurrent_call())
    # Débloque le thread, les deux tasks doivent résoudre
    gate.set()
    r1, r2 = await asyncio.gather(task1, task2)

    assert r1 == 7
    assert r2 == 7
    assert calls == 1


@pytest.mark.asyncio
async def test_exception_propagated_then_key_purged():
    """Une exception est propagée puis la clé est purgée pour permettre un retry propre."""
    dedup: InflightDedup[int] = InflightDedup()
    calls = 0

    def failing() -> int:
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await dedup.run(("err",), failing)

    # Entrée purgée → re-run exécute de nouveau la factory
    with pytest.raises(ValueError, match="boom"):
        await dedup.run(("err",), failing)

    assert calls == 2


@pytest.mark.asyncio
async def test_concurrent_exception_shared():
    """Deux appels concurrents reçoivent la même exception."""
    dedup: InflightDedup[int] = InflightDedup()
    calls = 0
    gate = threading.Event()

    def failing() -> int:
        nonlocal calls
        calls += 1
        gate.wait(timeout=2.0)
        raise RuntimeError("shared-fail")

    async def concurrent_call() -> int:
        return await dedup.run(("shared",), failing)

    task1 = asyncio.create_task(concurrent_call())
    await asyncio.sleep(0.05)
    task2 = asyncio.create_task(concurrent_call())
    gate.set()
    results = await asyncio.gather(task1, task2, return_exceptions=True)

    assert all(isinstance(r, RuntimeError) and "shared-fail" in str(r) for r in results)
    assert calls == 1
