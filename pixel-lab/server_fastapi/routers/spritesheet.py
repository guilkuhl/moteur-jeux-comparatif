"""Routes spritesheet : slicing, constraints, export."""
from __future__ import annotations

import datetime
import io
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from PIL import Image

from ..deps import INPUTS_DIR, OUTPUTS_DIR, safe_name
from ..services import history_store

router = APIRouter(prefix="/api", tags=["spritesheet"])


# ──────────────────────────────── Slicing ────────────────────────────────────

def _validate_slicing_config(base: dict | None, overrides: list) -> list[str]:
    errors: list[str] = []
    if base is None:
        return errors
    cols = base.get("cols")
    rows = base.get("rows")
    if not isinstance(cols, int) or cols < 1 or cols > 256:
        errors.append("cols must be int in [1,256]")
    if not isinstance(rows, int) or rows < 1 or rows > 256:
        errors.append("rows must be int in [1,256]")
    for fld in ("cellW", "cellH", "gapX", "gapY", "marginX", "marginY"):
        v = base.get(fld, 0)
        if not isinstance(v, int) or v < 0 or v > 1024:
            errors.append(f"{fld} must be int in [0,1024]")
    if not isinstance(overrides, list):
        errors.append("overrides must be a list")
        return errors
    occupied: dict[tuple, str] = {}
    for ov in overrides:
        if not isinstance(ov, dict):
            errors.append("override must be dict")
            continue
        cx, cy = ov.get("cellX"), ov.get("cellY")
        otype = ov.get("type")
        if not isinstance(cx, int) or not isinstance(cy, int):
            errors.append("override.cellX/cellY must be int")
            continue
        if cols and rows and (cx < 0 or cx >= cols or cy < 0 or cy >= rows):
            errors.append(f"override at ({cx},{cy}) is out of grid {cols}x{rows}")
            continue
        if otype not in ("resize", "merge", "ignore", "name", "pivot", "order"):
            errors.append(f"unknown override type {otype!r}")
            continue
        if otype == "merge":
            mw = ov.get("w", 1)
            mh = ov.get("h", 1)
            if not isinstance(mw, int) or not isinstance(mh, int) or mw < 1 or mh < 1:
                errors.append(f"merge at ({cx},{cy}) needs positive w,h")
                continue
            for dx in range(mw):
                for dy in range(mh):
                    key = (cx + dx, cy + dy)
                    if key in occupied and occupied[key] != "merge_owner":
                        errors.append(f"merge at ({cx},{cy}) overlaps with cell {key}")
                    occupied[key] = "merge_member"
            occupied[(cx, cy)] = "merge_owner"
    return errors


@router.get("/slicing/{basename:path}")
def slicing_get(basename: str) -> dict:
    if not safe_name(basename):
        raise HTTPException(status_code=400, detail="bad_name")
    stem = Path(basename).stem
    h = history_store.load()
    entry = h.get(stem) or {}
    sl = entry.get("slicing")
    if not sl:
        return {"base": None, "overrides": []}
    return sl


@router.put("/slicing/{basename:path}")
async def slicing_put(basename: str, request: Request) -> dict:
    if not safe_name(basename):
        raise HTTPException(status_code=400, detail="bad_name")
    payload = await request.json() if await request.body() else {}
    base = payload.get("base")
    overrides = payload.get("overrides", [])
    errors = _validate_slicing_config(base, overrides if isinstance(overrides, list) else [])
    if errors:
        raise HTTPException(status_code=400, detail={"error": "invalid_config", "details": errors})

    stem = Path(basename).stem

    def _mut(h: dict) -> None:
        if stem not in h:
            h[stem] = {"source": f"inputs/{basename}", "runs": []}
        if base is None:
            h[stem].pop("slicing", None)
        else:
            h[stem]["slicing"] = {"base": base, "overrides": overrides}

    new_state = history_store.update(_mut)
    return new_state.get(stem, {}).get("slicing") or {"base": None, "overrides": []}


# ────────────────────────── Constraints validate ──────────────────────────────

def _is_pot(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _next_pot(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


@router.post("/constraints/validate")
async def constraints_validate(request: Request) -> dict:
    payload = await request.json()
    image_name = payload.get("image")
    constraints = payload.get("constraints") or {}
    grid = payload.get("grid") or {}
    if not image_name or not safe_name(image_name):
        raise HTTPException(status_code=400, detail="bad_image")
    base = grid.get("base") if isinstance(grid, dict) else None
    if not base:
        return {"violations": [], "warning": "no_grid"}
    overrides = grid.get("overrides", []) if isinstance(grid, dict) else []
    cols, rows = base.get("cols", 0), base.get("rows", 0)
    cellW, cellH = base.get("cellW", 0), base.get("cellH", 0)
    mul_n = constraints.get("mulN")
    use_pot = constraints.get("pot")
    violations: list[dict] = []
    ignore_set = {(o.get("cellX"), o.get("cellY")) for o in overrides if o.get("type") == "ignore"}

    def cell_dims(cx: int, cy: int) -> tuple[int, int]:
        w, h = cellW, cellH
        for o in overrides:
            if o.get("cellX") == cx and o.get("cellY") == cy:
                if o.get("type") == "resize":
                    w = o.get("w", w); h = o.get("h", h)
                elif o.get("type") == "merge":
                    w = cellW * o.get("w", 1); h = cellH * o.get("h", 1)
        return w, h

    for cy in range(rows):
        for cx in range(cols):
            if (cx, cy) in ignore_set:
                continue
            w, h = cell_dims(cx, cy)
            if mul_n and isinstance(mul_n, int) and mul_n > 0:
                if w % mul_n != 0 or h % mul_n != 0:
                    sugg_w = ((w + mul_n - 1) // mul_n) * mul_n
                    sugg_h = ((h + mul_n - 1) // mul_n) * mul_n
                    violations.append({
                        "cellX": cx, "cellY": cy,
                        "issue": f"{w}x{h} non multiple de {mul_n}",
                        "suggestion": f"padder à {sugg_w}x{sugg_h} ou rogner à {w - w % mul_n}x{h - h % mul_n}",
                        "type": "mulN",
                    })
            if use_pot and (not _is_pot(w) or not _is_pot(h)):
                violations.append({
                    "cellX": cx, "cellY": cy,
                    "issue": f"{w}x{h} non POT",
                    "suggestion": f"padder à {_next_pot(w)}x{_next_pot(h)}",
                    "type": "pot",
                })
    return {"violations": violations}


# ────────────────────────────── Export ZIP ────────────────────────────────────

def _build_frames(grid: dict, template: str, options: dict) -> list[dict]:
    base = grid.get("base") or {}
    overrides = grid.get("overrides", [])
    cols, rows = base.get("cols", 0), base.get("rows", 0)
    cellW, cellH = base.get("cellW", 0), base.get("cellH", 0)
    gapX, gapY = base.get("gapX", 0), base.get("gapY", 0)
    marginX, marginY = base.get("marginX", 0), base.get("marginY", 0)

    ov_by_cell: dict = {}
    for o in overrides:
        ov_by_cell.setdefault((o.get("cellX"), o.get("cellY")), []).append(o)

    def find(cx: int, cy: int, type_: str):
        return next((o for o in ov_by_cell.get((cx, cy), []) if o.get("type") == type_), None)

    def is_member(cx: int, cy: int) -> bool:
        for o in overrides:
            if o.get("type") != "merge":
                continue
            ox, oy = o.get("cellX"), o.get("cellY")
            mw, mh = o.get("w", 1), o.get("h", 1)
            dx, dy = cx - ox, cy - oy
            if 0 <= dx < mw and 0 <= dy < mh and (dx > 0 or dy > 0):
                return True
        return False

    frames: list[dict] = []
    used_names: set[str] = set()
    idx = 0
    order_map = {(o["cellX"], o["cellY"]): o.get("value", 0) for o in overrides if o.get("type") == "order"}
    cells: list[tuple[int, int]] = []
    for cy in range(rows):
        for cx in range(cols):
            if find(cx, cy, "ignore") or is_member(cx, cy):
                continue
            cells.append((cx, cy))
    if order_map:
        cells.sort(key=lambda p: (order_map.get(p, 1e9), p[1], p[0]))

    for cx, cy in cells:
        merge = find(cx, cy, "merge")
        resize = find(cx, cy, "resize")
        w = cellW * (merge["w"] if merge else 1) + gapX * ((merge["w"] if merge else 1) - 1)
        h = cellH * (merge["h"] if merge else 1) + gapY * ((merge["h"] if merge else 1) - 1)
        if resize:
            w, h = resize.get("w", w), resize.get("h", h)
        x = marginX + cx * (cellW + gapX)
        y = marginY + cy * (cellH + gapY)
        nameOv = find(cx, cy, "name")
        custom_name = nameOv.get("name") if nameOv else f"{cx}_{cy}"
        name = template.format(
            basename=options.get("basename", "img"), col=cx, row=cy, index=idx, name=custom_name
        )
        base_name = name
        suffix = 1
        while name in used_names:
            suffix += 1
            name = f"{base_name}_{suffix}"
        used_names.add(name)
        frame: dict = {
            "name": name, "x": x, "y": y, "w": w, "h": h,
            "index": idx, "cellX": cx, "cellY": cy,
        }
        pivot = find(cx, cy, "pivot")
        if pivot and options.get("pivot"):
            frame["pivot"] = {"x": pivot.get("x", 0.5), "y": pivot.get("y", 0.5)}
        frames.append(frame)
        idx += 1
    return frames


def _emit_json_phaser(frames: list[dict], image_name: str, atlas_size: tuple) -> str:
    out = {
        "frames": {
            f["name"]: {
                "frame": {"x": f["x"], "y": f["y"], "w": f["w"], "h": f["h"]},
                "rotated": False,
                "trimmed": False,
                "spriteSourceSize": {"x": 0, "y": 0, "w": f["w"], "h": f["h"]},
                "sourceSize": {"w": f["w"], "h": f["h"]},
                **({"pivot": f["pivot"]} if "pivot" in f else {}),
            }
            for f in frames
        },
        "meta": {"image": image_name, "size": {"w": atlas_size[0], "h": atlas_size[1]}, "scale": "1"},
    }
    return json.dumps(out, indent=2, ensure_ascii=False)


def _emit_xml_starling(frames: list[dict], image_name: str) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<TextureAtlas imagePath="{xml_escape(image_name)}">']
    for f in frames:
        parts.append(
            f'  <SubTexture name="{xml_escape(f["name"])}" '
            f'x="{f["x"]}" y="{f["y"]}" width="{f["w"]}" height="{f["h"]}"/>'
        )
    parts.append("</TextureAtlas>")
    return "\n".join(parts)


def _emit_css_sprites(frames: list[dict], image_name: str) -> str:
    parts = [f'.sprite {{ background: url("{image_name}") no-repeat; display: inline-block; }}']
    for f in frames:
        parts.append(
            f'.sprite-{f["name"]} {{ background-position: -{f["x"]}px -{f["y"]}px; '
            f'width: {f["w"]}px; height: {f["h"]}px; }}'
        )
    return "\n".join(parts)


@router.post("/export")
async def api_export(request: Request) -> Response:
    payload = await request.json()
    image_name = payload.get("image")
    fmt = payload.get("format", "json_phaser")
    template = payload.get("template", "{basename}_{col}_{row}")
    options = payload.get("options") or {}
    if not image_name or not safe_name(image_name):
        raise HTTPException(status_code=400, detail="bad_image")
    src_path = INPUTS_DIR / image_name
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="image_not_found")
    h = history_store.load()
    stem = Path(image_name).stem
    grid = (h.get(stem) or {}).get("slicing")
    if not grid or not grid.get("base"):
        raise HTTPException(status_code=400, detail="no_slicing")
    options["basename"] = stem
    frames = _build_frames(grid, template, options)
    if not frames:
        raise HTTPException(status_code=400, detail="no_frames")

    img = Image.open(src_path).convert("RGBA")
    atlas_size = img.size

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if fmt == "individual":
            for f in frames:
                crop = img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
                pb = io.BytesIO()
                crop.save(pb, format="PNG")
                zf.writestr(f["name"] + ".png", pb.getvalue())
        else:
            atlas_buf = io.BytesIO()
            img.save(atlas_buf, format="PNG")
            zf.writestr("atlas.png", atlas_buf.getvalue())
            if fmt == "png_atlas":
                pass
            elif fmt == "json_phaser":
                zf.writestr("atlas.json", _emit_json_phaser(frames, "atlas.png", atlas_size))
            elif fmt == "xml_starling":
                zf.writestr("atlas.xml", _emit_xml_starling(frames, "atlas.png"))
            elif fmt == "css_sprites":
                zf.writestr("atlas.css", _emit_css_sprites(frames, "atlas.png"))
            else:
                raise HTTPException(status_code=400, detail="unknown_format")

    export_dir = OUTPUTS_DIR / stem / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    (export_dir / f"export_{fmt}_{ts}.zip").write_bytes(buf.getvalue())

    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{stem}_{fmt}.zip"',
            "X-Frames-Count": str(len(frames)),
        },
    )


def iter_cells(image_name: str):
    """Yield (img, frames, grid) — utilisé par cleanup aussi."""
    h = history_store.load()
    stem = Path(image_name).stem
    grid = (h.get(stem) or {}).get("slicing")
    if not grid or not grid.get("base"):
        return None, None, None
    src = INPUTS_DIR / image_name
    if not src.exists():
        return None, None, None
    img = Image.open(src).convert("RGBA")
    frames = _build_frames(grid, "{col}_{row}", {"basename": stem})
    return img, frames, grid
