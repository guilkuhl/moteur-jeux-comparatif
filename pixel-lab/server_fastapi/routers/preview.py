"""POST /api/preview — renvoie un PNG binaire + headers X-*."""
from __future__ import annotations

import time

from fastapi import APIRouter, Response

from ..schemas.pipeline import PreviewRequest
from ..services import preview_runner
from ..services.inflight import InflightDedup

router = APIRouter(prefix="/api", tags=["preview"])

_preview_dedup: InflightDedup[tuple[bytes, int, int, int]] = InflightDedup()


def _dedup_key(payload: PreviewRequest) -> tuple:
    steps = tuple(
        (s.algo, s.method, tuple(sorted((s.params or {}).items())))
        for s in payload.pipeline
    )
    return (payload.image, payload.downscale, steps, payload.use_gpu)


@router.post(
    "/preview",
    responses={200: {"content": {"image/png": {}}}},
)
async def api_preview(payload: PreviewRequest) -> Response:
    t0 = time.perf_counter()
    key = _dedup_key(payload)
    steps_dump = [s.model_dump() for s in payload.pipeline]
    png_bytes, width, height, hit_depth = await _preview_dedup.run(
        key,
        lambda: preview_runner.render(
            payload.image,
            steps_dump,
            payload.downscale,
            use_gpu=payload.use_gpu,
        ),
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "X-Width": str(width),
            "X-Height": str(height),
            "X-Elapsed-Ms": str(elapsed_ms),
            "X-Cache-Hit-Depth": str(hit_depth),
        },
    )
