"""Cache LRU en mémoire pour les préfixes de pipeline /api/preview."""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from PIL import Image


class PreviewCache:
    def __init__(self, max_size: int = 32) -> None:
        self._store: OrderedDict[tuple, Image.Image] = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_size

    @staticmethod
    def step_key(step: dict[str, Any]) -> tuple:
        algo = step["algo"]
        method = step["method"]
        params = step.get("params") or {}
        return (algo, method, tuple(sorted(params.items())))

    @classmethod
    def pipeline_key(
        cls,
        basename: str,
        mtime_ns: int,
        downscale: int | None,
        steps_prefix: list[dict[str, Any]],
    ) -> tuple:
        return (basename, mtime_ns, downscale, tuple(cls.step_key(s) for s in steps_prefix))

    def get(self, key: tuple) -> Image.Image | None:
        with self._lock:
            img = self._store.get(key)
            if img is None:
                return None
            self._store.move_to_end(key)
            return img.copy()

    def put(self, key: tuple, img: Image.Image) -> None:
        with self._lock:
            self._store[key] = img.copy()
            self._store.move_to_end(key)
            while len(self._store) > self._max:
                self._store.popitem(last=False)


preview_cache = PreviewCache(max_size=128)
