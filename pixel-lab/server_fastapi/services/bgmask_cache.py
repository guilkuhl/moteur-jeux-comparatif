"""Cache mémoire des masques de fond (/api/bgmask)."""
from __future__ import annotations

import threading
from collections import OrderedDict


class BgmaskCache:
    def __init__(self, max_size: int = 16) -> None:
        self._store: OrderedDict[tuple, tuple[bytes, tuple | None]] = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_size

    def get(self, key: tuple) -> tuple[bytes, tuple | None] | None:
        with self._lock:
            val = self._store.get(key)
            if val is not None:
                self._store.move_to_end(key)
            return val

    def put(self, key: tuple, val: tuple[bytes, tuple | None]) -> None:
        with self._lock:
            self._store[key] = val
            self._store.move_to_end(key)
            while len(self._store) > self._max:
                self._store.popitem(last=False)


bgmask_cache = BgmaskCache(max_size=16)
