"""Modèles de réponse — utilisés pour `response_model=` et OpenAPI."""
from __future__ import annotations

from pydantic import BaseModel


class InputFile(BaseModel):
    name: str
    processed: bool


class JobCreatedResponse(BaseModel):
    job_id: str


class HealthzResponse(BaseModel):
    status: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    message: str | None = None
