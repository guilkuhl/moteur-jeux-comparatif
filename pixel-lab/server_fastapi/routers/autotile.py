"""POST /api/autotile/generate (Wang 16/47/256)."""
from __future__ import annotations

import base64
import datetime
import io
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from PIL import Image

from ..deps import OUTPUTS_DIR, safe_name
from ..services import history_store

router = APIRouter(prefix="/api/autotile", tags=["autotile"])


def _decode_tile_data_url(data_url: str) -> Image.Image:
    if not data_url or not data_url.startswith("data:"):
        raise ValueError("invalid_data_url")
    _, b64 = data_url.split(",", 1)
    raw = base64.b64decode(b64)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def _quadrant(tile: Image.Image, quad: str) -> Image.Image:
    w, h = tile.size
    hw, hh = w // 2, h // 2
    if quad == "TL": return tile.crop((0, 0, hw, hh))
    if quad == "TR": return tile.crop((hw, 0, w, hh))
    if quad == "BL": return tile.crop((0, hh, hw, h))
    if quad == "BR": return tile.crop((hw, hh, w, h))
    return tile


def _compose_wang16(bits: int, base_tile: Image.Image, edge_tile: Image.Image, tile_size: int) -> Image.Image:
    out = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
    hs = tile_size // 2
    corners = [("TL", 0, 0, 3), ("TR", hs, 0, 2), ("BL", 0, hs, 1), ("BR", hs, hs, 0)]
    for quad, x, y, bit_idx in corners:
        use_base = (bits >> bit_idx) & 1
        src = base_tile if use_base else edge_tile
        q = _quadrant(src, quad)
        if q.size != (hs, hs):
            q = q.resize((hs, hs), Image.Resampling.NEAREST)
        out.paste(q, (x, y), q)
    return out


def _compose_wang256(bits: int, tiles: dict, tile_size: int) -> Image.Image:
    wang16_bits = 0
    for wang_idx, big_idx in [(3, 7), (2, 5), (1, 3), (0, 1)]:
        if (bits >> big_idx) & 1:
            wang16_bits |= (1 << wang_idx)
    return _compose_wang16(wang16_bits, tiles["base"], tiles["edge"], tile_size)


@router.post("/generate")
async def generate(request: Request) -> dict:
    payload = await request.json()
    mode = payload.get("mode", "wang16")
    tile_size = int(payload.get("tile_size", 16))
    tiles_payload = payload.get("tiles") or {}
    image_name = payload.get("image")
    if tile_size not in (8, 16, 32, 64, 128):
        raise HTTPException(status_code=400, detail="bad_tile_size")
    required = {
        "wang16":  ["base", "edge"],
        "wang47":  ["base", "edge", "corner_in", "corner_out"],
        "wang256": ["base", "edge"],
    }.get(mode)
    if not required:
        raise HTTPException(status_code=400, detail="unknown_mode")
    tiles: dict = {}
    for key in required:
        url = tiles_payload.get(key)
        if not url:
            raise HTTPException(status_code=400, detail=f"missing_tile_{key}")
        try:
            t = _decode_tile_data_url(url)
            if t.size != (tile_size, tile_size):
                t = t.resize((tile_size, tile_size), Image.Resampling.NEAREST)
            tiles[key] = t
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"bad_tile_{key}: {e}") from e

    if mode == "wang16":
        cols, rows = 4, 4
        variants = [_compose_wang16(b, tiles["base"], tiles["edge"], tile_size) for b in range(16)]
    elif mode == "wang47":
        cols, rows = 7, 7
        variants = []
        blob47 = [0, 1, 4, 5, 16, 17, 20, 21, 64, 65, 68, 69, 80, 81, 84, 85,
                  68, 69, 84, 85, 80, 81, 84, 85, 4, 5, 20, 21, 80, 81, 84, 85,
                  16, 17, 20, 21, 64, 65, 68, 69, 64, 65, 68, 69, 4, 5, 20]
        for b in blob47:
            c = 0
            if (b >> 6) & 1: c |= (1 << 3)
            if (b >> 4) & 1: c |= (1 << 2)
            if (b >> 2) & 1: c |= (1 << 1)
            if b & 1:        c |= 1
            variants.append(_compose_wang16(c, tiles["base"], tiles["edge"], tile_size))
        while len(variants) < cols * rows:
            variants.append(Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0)))
    else:  # wang256
        cols, rows = 16, 16
        variants = [_compose_wang256(b, tiles, tile_size) for b in range(256)]

    atlas = Image.new("RGBA", (cols * tile_size, rows * tile_size), (0, 0, 0, 0))
    for i, v in enumerate(variants):
        x = (i % cols) * tile_size
        y = (i // cols) * tile_size
        atlas.paste(v, (x, y), v)

    if image_name and safe_name(image_name):
        stem = Path(image_name).stem
    else:
        stem = f"autotile_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = OUTPUTS_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [p for p in out_dir.iterdir() if p.name.startswith("iter_")] if out_dir.exists() else []
    idx = len(existing) + 1
    fname = f"iter_{idx:03d}_autotile_{mode}.png"
    atlas.save(out_dir / fname, format="PNG")

    def _mut(h: dict) -> None:
        h.setdefault(
            stem,
            {"source": f"inputs/{image_name}" if image_name else f"outputs/{stem}/{fname}", "runs": []},
        )
        h[stem]["runs"].append({
            "algo": "autotile", "method": mode,
            "params": {"tile_size": tile_size},
            "output": f"outputs/{stem}/{fname}",
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        })
    history_store.update(_mut)
    return {
        "iter": f"outputs/{stem}/{fname}",
        "gridLayout": {"cols": cols, "rows": rows, "tile_size": tile_size, "mode": mode},
    }
