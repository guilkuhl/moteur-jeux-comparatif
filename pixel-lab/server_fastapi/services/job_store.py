"""Store de jobs in-memory : verrou single-active + pont thread → event loop pour SSE."""
from __future__ import annotations

import asyncio
import contextlib
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    job_id: str
    state: str = "running"  # running | done
    events: list[dict[str, Any]] = field(default_factory=list)
    # subscribers : queues asyncio alimentées depuis le thread worker via call_soon_threadsafe
    subscribers: list[asyncio.Queue] = field(default_factory=list)


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: str | None = None
        self._jobs: dict[str, Job] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Lier le store à la boucle asyncio principale (appelé au startup FastAPI)."""
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
        with self._lock:
            if self._active == job_id:
                self._active = None
            if job_id in self._jobs:
                self._jobs[job_id].state = "done"

    def push(self, job_id: str, event: dict[str, Any]) -> None:
        """Thread-safe : dispatch l'événement vers tous les subscribers via l'event loop."""
        job = self._jobs.get(job_id)
        if job is None:
            return
        job.events.append(event)
        loop = self._loop
        if loop is None:
            return
        for q in list(job.subscribers):
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(q.put_nowait, event)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def subscribe(self, job_id: str):
        """Async generator qui yield chaque événement jusqu'à réception du `done`."""
        job = self._jobs.get(job_id)
        if job is None:
            return
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        # Rejouer les événements déjà reçus (client qui se connecte après le début du job)
        for evt in list(job.events):
            q.put_nowait(evt)
        job.subscribers.append(q)
        try:
            while True:
                evt = await q.get()
                yield evt
                if evt.get("type") == "done":
                    return
                if job.state == "done" and job.events[-1:] != [evt]:
                    # sécurité : si le job est marqué done mais on n'a pas reçu l'event
                    return
        finally:
            if q in job.subscribers:
                job.subscribers.remove(q)


job_store = JobStore()
