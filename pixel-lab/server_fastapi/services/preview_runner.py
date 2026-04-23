"""Exécution in-memory d'un pipeline pour /api/preview (pas d'I/O disque)."""
from __future__ import annotations

import inspect
import io
from pathlib import Path
from typing import Any

from apply_step import _cast_params  # type: ignore[import-not-found]
from PIL import Image

from ..deps import ALGO_MODULES, resolve_input
from .preview_cache import preview_cache


def _require_input(basename: str) -> Path:
    """Rés. le chemin d'une image ; lève si introuvable. La validation Pydantic
    est censée l'avoir fait AVANT qu'on arrive ici — ce `ValueError` est un
    filet de sécurité pour les bugs de caller."""
    path = resolve_input(basename)
    if path is None:
        raise ValueError(f"image introuvable : {basename!r}")
    return path


def _load_source(basename: str) -> Image.Image:
    return Image.open(_require_input(basename)).copy()


def _apply_downscale(img: Image.Image, downscale: int | None) -> Image.Image:
    if downscale is None:
        return img
    out = img.copy()
    out.thumbnail((downscale, downscale), Image.Resampling.LANCZOS)
    return out


def _apply_step(
    img: Image.Image,
    algo: str,
    method: str,
    params: dict[str, Any],
    use_gpu: bool = False,
) -> Image.Image:
    fn = ALGO_MODULES[algo].METHODS[method]
    typed = _cast_params(algo, method, params)
    if use_gpu and "use_gpu" in inspect.signature(fn).parameters and "use_gpu" not in typed:
        typed["use_gpu"] = True
    return fn(img, **typed)


def render(
    image_name: str,
    pipeline: list[dict[str, Any]],
    downscale: int | None,
    use_gpu: bool = False,
) -> tuple[bytes, int, int, int]:
    """Rend le pipeline complet. Retourne (png_bytes, width, height, cache_hit_depth).

    `cache_hit_depth` est le nombre d'étapes en tête de pipeline servies depuis
    le cache (0 = aucun cache, N = toutes les étapes cachées).

    Le flag `use_gpu` fait partie de la clé de cache : le rendu GPU et CPU
    peuvent différer numériquement, donc on les sépare pour éviter tout mix.
    """
    source_path = _require_input(image_name)
    mtime_ns = source_path.stat().st_mtime_ns
    # Injecte use_gpu dans chaque étape pour que la clé de cache en dépende.
    keyed_pipeline = [
        {**step, "_use_gpu": use_gpu} for step in pipeline
    ] if use_gpu else pipeline

    # Recherche du plus long préfixe caché
    cached_img: Image.Image | None = None
    start_idx = 0
    for k in range(len(keyed_pipeline), 0, -1):
        key = preview_cache.pipeline_key(image_name, mtime_ns, downscale, keyed_pipeline[:k])
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
        current = _apply_step(
            current, step["algo"], step["method"], step.get("params") or {}, use_gpu=use_gpu,
        )
        prefix_key = preview_cache.pipeline_key(
            image_name, mtime_ns, downscale, keyed_pipeline[: i + 1],
        )
        preview_cache.put(prefix_key, current)

    buf = io.BytesIO()
    current.save(buf, format="PNG")
    return buf.getvalue(), current.width, current.height, start_idx
