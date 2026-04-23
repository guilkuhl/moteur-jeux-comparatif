"""Schémas Pydantic pour /api/convert et /api/preview — source unique de vérité."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..deps import ALGO_MODULES, resolve_input, safe_name


class PipelineStep(BaseModel):
    """Une étape de pipeline : algo + méthode + paramètres."""

    model_config = ConfigDict(extra="forbid", strict=False)

    algo: Literal["sharpen", "scale2x", "denoise", "pixelsnap"]
    method: str
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_method_and_params(self) -> PipelineStep:
        mod = ALGO_MODULES[self.algo]
        if self.method not in mod.METHODS:
            raise ValueError(
                f"méthode inconnue '{self.method}' pour algo '{self.algo}' "
                f"(disponibles : {sorted(mod.METHODS.keys())})"
            )
        allowed = {p["name"]: p for p in getattr(mod, "PARAMS", {}).get(self.method, [])}
        typed: dict[str, Any] = {}
        for pname, pval in self.params.items():
            if pname not in allowed:
                raise ValueError(
                    f"paramètre '{pname}' non déclaré pour {self.algo}/{self.method}"
                )
            meta = allowed[pname]
            ptype = meta.get("type")
            if ptype == "bool":
                if not isinstance(pval, bool):
                    raise ValueError(f"{pname}: booléen attendu, reçu {pval!r}")
                typed[pname] = pval
                continue
            try:
                v = float(pval)
            except (TypeError, ValueError) as e:
                raise ValueError(f"{pname}: valeur non numérique {pval!r}") from e
            if v < meta["min"] or v > meta["max"]:
                raise ValueError(
                    f"{pname}: {pval} hors bornes [{meta['min']}, {meta['max']}]"
                )
            typed[pname] = int(v) if ptype == "int" else v
        self.params = typed
        return self


class ConvertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    images: list[str] = Field(min_length=1)
    pipeline: list[PipelineStep] = Field(min_length=1)
    use_gpu: bool = False

    @field_validator("images")
    @classmethod
    def _check_images(cls, v: list[str]) -> list[str]:
        for name in v:
            if not isinstance(name, str) or not safe_name(name):
                raise ValueError(f"nom d'image invalide '{name}'")
            if resolve_input(name) is None:
                raise ValueError(f"fichier introuvable '{name}'")
        return v


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: str
    pipeline: list[PipelineStep] = Field(min_length=1)
    downscale: int | None = 256
    use_gpu: bool = False

    @field_validator("image")
    @classmethod
    def _check_image(cls, v: str) -> str:
        if not safe_name(v):
            raise ValueError(f"nom d'image invalide '{v}'")
        if resolve_input(v) is None:
            raise ValueError(f"fichier introuvable '{v}'")
        return v

    @field_validator("downscale")
    @classmethod
    def _check_downscale(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v < 64 or v > 4096:
            raise ValueError(f"downscale: {v} hors bornes [64, 4096]")
        return v
