"""Schémas Pydantic pour /api/presets — stocke des pipelines nommés."""
from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .pipeline import PipelineStep

_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,40}$")


class PresetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    pipeline: list[PipelineStep] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError(
                "nom invalide : 1-40 caractères, alphanumériques, '-' ou '_' uniquement"
            )
        return v


class PresetOut(BaseModel):
    name: str
    pipeline: list[dict]  # renvoyé tel que stocké, non-revalidé
    updated_at: str
