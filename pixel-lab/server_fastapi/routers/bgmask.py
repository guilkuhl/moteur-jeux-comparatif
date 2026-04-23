"""GET /api/bgmask — masque de fond détecté, PNG RGBA + headers cache."""
from __future__ import annotations

import io

import numpy as np
from fastapi import APIRouter, Depends, Response
from PIL import Image

from ..deps import bgdetect, resolve_input
from ..schemas.bgmask import BgmaskQuery
from ..services.bgmask_cache import bgmask_cache

router = APIRouter(prefix="/api", tags=["bgmask"])


@router.get("/bgmask", responses={200: {"content": {"image/png": {}}}})
def api_bgmask(query: BgmaskQuery = Depends()) -> Response:
    path = resolve_input(query.image)
    mtime_ns = path.stat().st_mtime_ns
    key = (query.image, mtime_ns, query.tolerance, query.feather, query.mode)

    cached = bgmask_cache.get(key)
    if cached is not None:
        png_bytes, bg_color = cached
        return Response(
            png_bytes,
            media_type="image/png",
            headers={
                "X-Cache": "HIT",
                "X-Bgmask-Color": (
                    "#{:02x}{:02x}{:02x}".format(*bg_color) if bg_color else "none"
                ),
            },
        )

    img = Image.open(path)
    bg_color = bgdetect.detect_bg_color(img, tolerance=query.tolerance)
    mask = bgdetect.compute_bg_mask(
        img, bg_color=bg_color, tolerance=query.tolerance, feather=query.feather
    )
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    if query.mode == "raw":
        c = bg_color or (0, 0, 0)
        rgba[..., 0], rgba[..., 1], rgba[..., 2] = c[0], c[1], c[2]
        rgba[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    else:
        rgba[..., 0], rgba[..., 1], rgba[..., 2] = 0, 255, 100
        rgba[..., 3] = np.where(mask, 200, 0).astype(np.uint8)

    out_img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    out_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    bgmask_cache.put(key, (png_bytes, bg_color))

    return Response(
        png_bytes,
        media_type="image/png",
        headers={
            "X-Cache": "MISS",
            "X-Bgmask-Color": (
                "#{:02x}{:02x}{:02x}".format(*bg_color) if bg_color else "none"
            ),
        },
    )
