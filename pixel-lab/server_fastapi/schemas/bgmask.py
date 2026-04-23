"""Query params pour GET /api/bgmask."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..deps import resolve_input, safe_name


class BgmaskQuery(BaseModel):
    image: str
    tolerance: int = Field(default=8, ge=0, le=50)
    feather: int = Field(default=0, ge=0, le=5)
    mode: Literal["highlight", "raw"] = "highlight"

    @field_validator("image")
    @classmethod
    def _check_image(cls, v: str) -> str:
        if not safe_name(v):
            raise ValueError(f"nom d'image invalide '{v}'")
        if resolve_input(v) is None:
            raise ValueError(f"fichier introuvable '{v}'")
        return v
