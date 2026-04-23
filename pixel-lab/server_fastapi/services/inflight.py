"""InflightDedup : partage le résultat d'un calcul CPU-bound en vol entre appelants concurrents.

Le premier appelant pour une clé donnée exécute la factory dans un thread via
`asyncio.to_thread`. Les appelants concurrents sur la même clé attendent le
même Future et reçoivent le même résultat (ou la même exception).

L'entrée dédup est purgée à la résolution (succès ou erreur), donc une relance
après exception repart sur un calcul frais.
"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class InflightDedup(Generic[T]):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inflight: dict[tuple, asyncio.Future[T]] = {}

    async def run(self, key: tuple, factory: Callable[[], T]) -> T:
        loop = asyncio.get_running_loop()
        with self._lock:
            fut = self._inflight.get(key)
            if fut is None:
                fut = loop.create_future()
                self._inflight[key] = fut
                owner = True
            else:
                owner = False

        if owner:
            try:
                result = await asyncio.to_thread(factory)
            except BaseException as exc:  # noqa: BLE001
                fut.set_exception(exc)
                with self._lock:
                    self._inflight.pop(key, None)
                raise
            else:
                fut.set_result(result)
                with self._lock:
                    self._inflight.pop(key, None)
                return result

        return await fut
