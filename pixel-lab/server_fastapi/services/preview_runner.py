"""Exécution in-memory d'un pipeline pour /api/preview (pas d'I/O disque)."""
from __future__ import annotations

import io
from typing import Any

from PIL import Image

from apply_step import _cast_params  # type: ignore[import-not-found]

from ..deps import ALGO_MODULES, resolve_input
from .preview_cache import preview_cache


def _load_source(basename: str) -> Image.Image:
    return Image.open(resolve_input(basename)).copy()


def _apply_downscale(img: Image.Image, downscale: int | None) -> Image.Image:
    if downscale is None:
        return img
    out = img.copy()
    out.thumbnail((downscale, downscale), Image.Resampling.LANCZOS)
    return out


def _apply_step(img: Image.Image, algo: str, method: str, params: dict[str, Any]) -> Image.Image:
    fn = ALGO_MODULES[algo].METHODS[method]
    return fn(img, **_cast_params(algo, method, params))


def render(image_name: str, pipeline: list[dict[str, Any]], downscale: int | None) -> tuple[bytes, int, int, int]:
    """Retourne (png_bytes, width, height, cache_hit_depth)."""
    source_path = resolve_input(image_name)
    mtime_ns = source_path.stat().st_mtime_ns

    cached_img: Image.Image | None = None
    start_idx = 0
    for k in range(len(pipeline), 0, -1):
        key = preview_cache.pipeline_key(image_name, mtime_ns, downscale, pipeline[:k])
        hit = preview_cache.get(key)
        if hit is not None:
            cached_img = hit
            start_idx = k
            break

    if cached_img is None:
        base_key = preview_cache.pipeline_key(image_name, mtime_ns, downscale, [])
        hit = preview_cache.get(base_key)
        if hit is not None:
            cached_img = hit
        else:
            cached_img = _apply_downscale(_load_source(image_name), downscale)
            preview_cache.put(base_key, cached_img)

    current = cached_img
    for i in range(start_idx, len(pipeline)):
        step = pipeline[i]
        current = _apply_step(current, step["algo"], step["method"], step.get("params") or {})
        prefix_key = preview_cache.pipeline_key(image_name, mtime_ns, downscale, pipeline[: i + 1])
        preview_cache.put(prefix_key, current)

    buf = io.BytesIO()
    current.save(buf, format="PNG")
    return buf.getvalue(), current.width, current.height, start_idx
