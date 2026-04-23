"""POST /api/convert, GET /api/jobs/{id}/stream, GET /api/algos."""
from __future__ import annotations

import asyncio
import json
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import ALGO_MODULES
from ..schemas.pipeline import ConvertRequest
from ..schemas.responses import JobCreatedResponse
from ..services.job_store import job_store
from ..services.pipeline_runner import run_job

router = APIRouter(prefix="/api", tags=["convert"])


@router.post("/convert", status_code=202, response_model=JobCreatedResponse)
def api_convert(payload: ConvertRequest) -> JobCreatedResponse:
    job = job_store.try_start()
    if job is None:
        raise HTTPException(status_code=409, detail="Un job est déjà actif")
    # Exécution dans un thread : les algos sont CPU-bound (NumPy/Pillow relâchent le GIL).
    threading.Thread(
        target=run_job,
        args=(job.job_id, payload.model_dump()),
        daemon=True,
    ).start()
    return JobCreatedResponse(job_id=job.job_id)


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job introuvable")

    async def event_gen():
        asyncio.get_event_loop().time()
        async for evt in job_store.subscribe(job_id):
            yield f"data: {json.dumps(evt)}\n\n"
            asyncio.get_event_loop().time()
        # après un `done`, on sort du générateur

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/algos")
def api_algos() -> dict:
    result: dict = {}
    for algo_name, mod in ALGO_MODULES.items():
        methods: dict = {}
        params = getattr(mod, "PARAMS", {})
        for method_name in mod.METHODS:
            methods[method_name] = {"params": params.get(method_name, [])}
        result[algo_name] = {"methods": methods}
    return result
