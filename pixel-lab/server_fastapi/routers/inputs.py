"""GET/POST/DELETE /api/inputs."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..deps import (
    ALLOWED_UPLOAD_EXTS,
    HISTORY_FILE,
    INPUT_EXTS,
    INPUTS_DIR,
    INPUTS_TRASH,
    MAX_UPLOAD_BYTES,
    OUTPUTS_DIR,
    OUTPUTS_TRASH,
    safe_name,
)
from ..services import history_store
from ..services.trash import move_to_trash
from ..services.upload import sanitize_basename, suggest_unused_name

router = APIRouter(prefix="/api", tags=["inputs"])


@router.get("/inputs")
def list_inputs() -> list[dict]:
    history: dict = {}
    if HISTORY_FILE.exists():
        history = json.loads(HISTORY_FILE.read_text("utf-8"))
    files = []
    if INPUTS_DIR.exists():
        for f in sorted(INPUTS_DIR.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() in INPUT_EXTS:
                files.append({"name": f.name, "processed": f.stem in history})
    return files


@router.post("/inputs")
async def upload_input(file: UploadFile) -> dict:
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="missing_file")

    basename = sanitize_basename(file.filename)
    ext = Path(basename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=415,
            detail=f"Extension {ext or '?'} non supportée (autorisé: png, webp, jpg, jpeg).",
        )

    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = INPUTS_DIR / basename
    if dest.exists():
        # Réponse 409 avec suggestion d'un nom libre
        return JSONResponse(
            status_code=409,
            content={
                "error": "exists",
                "message": f"{basename} existe déjà.",
                "suggestion": suggest_unused_name(basename, INPUTS_DIR),
            },
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop gros (> 20 MB).")
    dest.write_bytes(data)
    return {"basename": basename, "size": dest.stat().st_size}


@router.delete("/inputs/{basename:path}")
def delete_input(basename: str) -> dict:
    if not safe_name(basename):
        raise HTTPException(status_code=400, detail="bad_name")
    src = INPUTS_DIR / basename
    if not src.exists():
        raise HTTPException(status_code=404, detail="not_found")

    archived_src = move_to_trash(src, INPUTS_TRASH)

    stem = Path(basename).stem
    archived_out = None
    out_dir = OUTPUTS_DIR / stem
    if out_dir.exists():
        archived_out = move_to_trash(out_dir, OUTPUTS_TRASH)

    def _mut(h: dict) -> None:
        h.pop(stem, None)

    history_store.update(_mut)

    from ..deps import ROOT
    return {
        "archivedSource": str(archived_src.relative_to(ROOT)),
        "archivedOutputs": str(archived_out.relative_to(ROOT)) if archived_out else None,
    }
