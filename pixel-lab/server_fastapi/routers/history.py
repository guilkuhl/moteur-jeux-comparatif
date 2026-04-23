"""POST /api/history/prune."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..deps import INPUTS_DIR, OUTPUTS_DIR, OUTPUTS_TRASH, safe_name
from ..services import history_store
from ..services.trash import move_to_trash

router = APIRouter(prefix="/api", tags=["history"])


@router.post("/history/prune")
async def prune(request: Request) -> dict:
    payload = await request.json()
    basenames = payload.get("basenames") or []
    if not isinstance(basenames, list):
        raise HTTPException(status_code=400, detail="basenames_must_be_list")

    existing_sources: set[str] = set()
    if INPUTS_DIR.exists():
        for f in INPUTS_DIR.iterdir():
            if f.is_file():
                existing_sources.add(f.stem)

    pruned: list[str] = []
    skipped: list[dict] = []

    def _mut(h: dict) -> None:
        for name in basenames:
            if not isinstance(name, str) or not safe_name(name):
                skipped.append({"name": str(name), "reason": "bad_name"})
                continue
            stem = Path(name).stem if "." in name else name
            if stem in existing_sources:
                skipped.append({"name": name, "reason": "source file still present"})
                continue
            if stem not in h:
                skipped.append({"name": name, "reason": "not_in_history"})
                continue
            out_dir = OUTPUTS_DIR / stem
            if out_dir.exists():
                move_to_trash(out_dir, OUTPUTS_TRASH)
            del h[stem]
            pruned.append(stem)

    history_store.update(_mut)
    return {"pruned": pruned, "skipped": skipped}
