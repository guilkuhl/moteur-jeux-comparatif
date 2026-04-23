"""DELETE /api/outputs/<stem>[/<filename>]."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..deps import OUTPUTS_DIR, safe_name
from ..services import history_store

router = APIRouter(prefix="/api", tags=["outputs"])


@router.delete("/outputs/{stem}/{filename}")
def delete_one(stem: str, filename: str) -> dict:
    if not (safe_name(stem) and safe_name(filename)):
        raise HTTPException(status_code=400, detail="nom invalide")
    filepath = OUTPUTS_DIR / stem / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="fichier introuvable")
    filepath.unlink()

    def _mut(h: dict) -> None:
        if stem in h:
            h[stem]["runs"] = [
                r for r in h[stem]["runs"] if not r.get("output", "").endswith(filename)
            ]

    history_store.update(_mut)
    return {"deleted": filename}


@router.delete("/outputs/{stem}")
def delete_all(stem: str) -> dict:
    if not safe_name(stem):
        raise HTTPException(status_code=400, detail="nom invalide")
    out_dir = OUTPUTS_DIR / stem
    deleted: list[str] = []
    if out_dir.exists():
        for f in out_dir.iterdir():
            if f.name.startswith("iter_"):
                f.unlink()
                deleted.append(f.name)

    def _mut(h: dict) -> None:
        if stem in h:
            h[stem]["runs"] = []

    history_store.update(_mut)
    return {"deleted": deleted}
