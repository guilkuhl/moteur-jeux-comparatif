"""Store de jobs in-memory : verrou single-active + pont thread → event loop pour SSE."""
from __future__ import annotations

import asyncio
import contextlib
import threading
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

# Cap de la queue par subscriber. Évite qu'un client SSE mort ne fasse croître
# la mémoire indéfiniment : on drop silencieusement les nouveaux events au-delà.
SUBSCRIBER_QUEUE_MAX = 1000


@dataclass
class Job:
    job_id: str
    state: str = "running"  # "running" | "done"
    events: list[dict[str, Any]] = field(default_factory=list)
    # subscribers : queues asyncio alimentées depuis le thread worker via
    # call_soon_threadsafe — jamais put direct depuis un thread non-loop.
    subscribers: list[asyncio.Queue[dict[str, Any]]] = field(default_factory=list)


class JobStore:
    """Stocke les jobs en mémoire process, sérialise via `threading.Lock`.

    ⚠️ Mémoire process : gunicorn `-w > 1` casserait la garantie « un seul
    job actif à la fois » — voir `serve.py`.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: str | None = None
        self._jobs: dict[str, Job] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Lie le store à la boucle asyncio principale (appelé depuis le lifespan FastAPI)."""
        self._loop = loop

    def try_start(self) -> Job | None:
        """Retourne un nouveau `Job` s'il n'y a aucun job actif, sinon None (→ 409)."""
        with self._lock:
            if self._active is not None:
                return None
            job_id = str(uuid.uuid4())
            job = Job(job_id=job_id)
            self._jobs[job_id] = job
            self._active = job_id
            return job

    def finish(self, job_id: str) -> None:
        """Marque le job comme `done` et libère le slot actif."""
        with self._lock:
            if self._active == job_id:
                self._active = None
            job = self._jobs.get(job_id)
            if job is not None:
                job.state = "done"

    def push(self, job_id: str, event: dict[str, Any]) -> None:
        """Dispatch thread-safe : persiste l'event puis notifie les subscribers via l'event loop."""
        job = self._jobs.get(job_id)
        if job is None:
            return
        job.events.append(event)
        loop = self._loop
        if loop is None:
            return
        for q in list(job.subscribers):
            # call_soon_threadsafe est l'API pont thread → event loop ; on
            # supprime les RuntimeError possibles si le loop est en shutdown.
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(q.put_nowait, event)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def subscribe(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """Async generator qui yield chaque événement jusqu'au `done` (ou disparition du job).

        Les événements déjà présents dans `job.events` sont rejoués en tête —
        un client qui se connecte après le début du job ne rate aucun event.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_MAX)
        for evt in list(job.events):
            q.put_nowait(evt)
        job.subscribers.append(q)
        try:
            while True:
                evt = await q.get()
                yield evt
                if evt.get("type") == "done":
                    return
        finally:
            if q in job.subscribers:
                job.subscribers.remove(q)


job_store = JobStore()
