"""POST /api/preview — renvoie un PNG binaire + headers X-*."""
from __future__ import annotations

import time

from fastapi import APIRouter, Response

from ..schemas.pipeline import PreviewRequest
from ..services import preview_runner

router = APIRouter(prefix="/api", tags=["preview"])


@router.post(
    "/preview",
    responses={200: {"content": {"image/png": {}}}},
)
def api_preview(payload: PreviewRequest) -> Response:
    t0 = time.perf_counter()
    png_bytes, width, height, hit_depth = preview_runner.render(
        payload.image,
        [s.model_dump() for s in payload.pipeline],
        payload.downscale,
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
