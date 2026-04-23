"""Routes /api/cleanup/* — duplicates, subpixel, normalize, report."""
from __future__ import annotations

import datetime
import json
from collections import Counter
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from PIL import Image

from ..deps import OUTPUTS_DIR, safe_name
from ..services import history_store
from .spritesheet import iter_cells

router = APIRouter(prefix="/api/cleanup", tags=["cleanup"])


def _phash(img: Image.Image, size: int = 8) -> int:
    small = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.float32)
    mean = arr.mean()
    bits = (arr > mean).astype(np.uint8).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(b)
    return h


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _phase_correlate(a: Image.Image, b: Image.Image) -> tuple[float, float]:
    A = np.asarray(a.convert("L"), dtype=np.float32)
    B = np.asarray(b.convert("L"), dtype=np.float32)
    if A.shape != B.shape:
        b2 = b.convert("L").resize(a.size, Image.Resampling.NEAREST)
        B = np.asarray(b2, dtype=np.float32)
    Fa = np.fft.fft2(A)
    Fb = np.fft.fft2(B)
    R = Fa * np.conj(Fb)
    R /= np.abs(R) + 1e-10
    r = np.fft.ifft2(R).real
    peak = np.unravel_index(np.argmax(r), r.shape)
    dy, dx = peak
    h, w = r.shape
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w

    def parab(y0: float, y1: float, y2: float) -> float:
        denom = y0 - 2 * y1 + y2
        return 0.5 * (y0 - y2) / denom if abs(denom) > 1e-9 else 0.0

    py, px = peak
    sx = sy = 0.0
    if 1 <= py < h - 1:
        sy = parab(r[py - 1, px], r[py, px], r[py + 1, px])
    if 1 <= px < w - 1:
        sx = parab(r[py, px - 1], r[py, px], r[py, px + 1])
    return (float(dx) + sx, float(dy) + sy)


@router.post("/detect-duplicates")
async def detect_duplicates(request: Request) -> dict:
    payload = await request.json()
    image_name = payload.get("image")
    threshold = int(payload.get("similarity_threshold", 5))
    if not image_name or not safe_name(image_name):
        raise HTTPException(status_code=400, detail="bad_image")
    img, frames, _ = iter_cells(image_name)
    if img is None:
        raise HTTPException(status_code=400, detail="no_slicing")
    hashes = [
        (f, _phash(img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))))
        for f in frames
    ]
    pairs = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = _hamming(hashes[i][1], hashes[j][1])
            if d <= threshold:
                pairs.append({
                    "a": {"cellX": hashes[i][0]["cellX"], "cellY": hashes[i][0]["cellY"], "name": hashes[i][0]["name"]},
                    "b": {"cellX": hashes[j][0]["cellX"], "cellY": hashes[j][0]["cellY"], "name": hashes[j][0]["name"]},
                    "hamming": d,
                })
    return {"pairs": pairs, "threshold": threshold}


@router.post("/detect-subpixel")
async def detect_subpixel(request: Request) -> dict:
    payload = await request.json()
    image_name = payload.get("image")
    if not image_name or not safe_name(image_name):
        raise HTTPException(status_code=400, detail="bad_image")
    img, frames, _ = iter_cells(image_name)
    if img is None:
        raise HTTPException(status_code=400, detail="no_slicing")
    shifts = []
    for i in range(1, len(frames)):
        a = img.crop((frames[i-1]["x"], frames[i-1]["y"], frames[i-1]["x"] + frames[i-1]["w"], frames[i-1]["y"] + frames[i-1]["h"]))
        b = img.crop((frames[i]["x"], frames[i]["y"], frames[i]["x"] + frames[i]["w"], frames[i]["y"] + frames[i]["h"]))
        try:
            dx, dy = _phase_correlate(a, b)
        except Exception:  # noqa: BLE001
            continue
        mag = (dx * dx + dy * dy) ** 0.5
        if 0.2 < mag < 2.5:
            shifts.append({
                "cell": {"cellX": frames[i]["cellX"], "cellY": frames[i]["cellY"], "name": frames[i]["name"]},
                "delta": {"x": round(dx, 3), "y": round(dy, 3)},
                "magnitude": round(mag, 3),
            })
    return {"shifts": shifts}


@router.post("/normalize")
async def normalize(request: Request) -> dict:
    payload = await request.json()
    image_name = payload.get("image")
    alignment = payload.get("alignment", "center")
    if not image_name or not safe_name(image_name):
        raise HTTPException(status_code=400, detail="bad_image")
    img, frames, grid = iter_cells(image_name)
    if img is None:
        raise HTTPException(status_code=400, detail="no_slicing")
    maxW = max(f["w"] for f in frames)
    maxH = max(f["h"] for f in frames)
    base = grid["base"]
    cols, rows = base["cols"], base["rows"]
    out_w = cols * maxW
    out_h = rows * maxH
    out = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    frame_map = {(f["cellX"], f["cellY"]): f for f in frames}
    for cy in range(rows):
        for cx in range(cols):
            f = frame_map.get((cx, cy))
            if not f:
                continue
            crop = img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
            dx = {"center": (maxW - f["w"]) // 2, "topleft": 0, "bottomleft": 0}.get(alignment, 0)
            dy = {"center": (maxH - f["h"]) // 2, "topleft": 0, "bottomleft": maxH - f["h"]}.get(alignment, 0)
            out.paste(crop, (cx * maxW + dx, cy * maxH + dy), crop)
    stem = Path(image_name).stem
    outputs_stem = OUTPUTS_DIR / stem
    outputs_stem.mkdir(parents=True, exist_ok=True)
    existing = [p for p in outputs_stem.iterdir() if p.name.startswith("iter_")]
    idx = len(existing) + 1
    fname = f"iter_{idx:03d}_normalize.png"
    out.save(outputs_stem / fname, format="PNG")

    def _mut(h: dict) -> None:
        h.setdefault(stem, {"source": f"inputs/{image_name}", "runs": []})
        h[stem]["runs"].append({
            "algo": "cleanup", "method": "normalize",
            "params": {"alignment": alignment, "target": [maxW, maxH]},
            "output": f"outputs/{stem}/{fname}",
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        })
    history_store.update(_mut)
    return {
        "iter": f"outputs/{stem}/{fname}",
        "dimensions": [out_w, out_h],
        "cellSize": [maxW, maxH],
    }


@router.get("/report")
def report(image: str = "") -> Response:
    if not image or not safe_name(image):
        raise HTTPException(status_code=400, detail="bad_image")
    img, frames, _ = iter_cells(image)
    if img is None:
        raise HTTPException(status_code=400, detail="no_slicing")
    hashes = [
        (f, _phash(img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))))
        for f in frames
    ]
    duplicates = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = _hamming(hashes[i][1], hashes[j][1])
            if d <= 5:
                duplicates.append({
                    "pair": [
                        (hashes[i][0]["cellX"], hashes[i][0]["cellY"]),
                        (hashes[j][0]["cellX"], hashes[j][0]["cellY"]),
                    ],
                    "hamming": d,
                })
    sizes = sorted({(f["w"], f["h"]) for f in frames})
    c = Counter((f["w"], f["h"]) for f in frames)
    dominant = c.most_common(1)[0][0] if c else None
    empty = []
    for f in frames:
        crop = img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        arr = np.asarray(crop)
        if arr.shape[-1] == 4:
            nonzero = int((arr[..., 3] > 0).sum())
            if nonzero < (f["w"] * f["h"] * 0.01):
                empty.append((f["cellX"], f["cellY"]))
    body = {
        "duplicates": duplicates,
        "size_variants": {
            "unique_sizes": [list(s) for s in sizes],
            "dominant": list(dominant) if dominant else None,
        },
        "empty_cells": [list(e) for e in empty],
        "frame_count": len(frames),
    }
    return Response(
        json.dumps(body, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{Path(image).stem}_report.json"'},
    )
