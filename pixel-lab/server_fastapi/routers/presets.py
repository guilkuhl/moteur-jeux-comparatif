"""CRUD /api/presets — pipelines nommés réutilisables."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.presets import PresetIn, PresetOut
from ..services import presets_store

router = APIRouter(prefix="/api/presets", tags=["presets"])


@router.get("", response_model=list[PresetOut])
def list_presets() -> list[dict]:
    return presets_store.list_all()


@router.post("", response_model=PresetOut, status_code=201)
def create_or_update_preset(body: PresetIn) -> dict:
    # `pipeline` est déjà validé par PipelineStep ; on le resérialise en dicts
    # plats pour que presets.json reste JSON-friendly et réimportable.
    serialized = [step.model_dump() for step in body.pipeline]
    return presets_store.upsert(body.name, serialized)


@router.delete("/{name}", status_code=204)
def delete_preset(name: str) -> None:
    if not presets_store.remove(name):
        raise HTTPException(status_code=404, detail="preset_not_found")
