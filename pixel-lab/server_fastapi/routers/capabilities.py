"""GET /api/capabilities — sonde les fonctionnalités backend optionnelles (GPU)."""
from __future__ import annotations

from fastapi import APIRouter

from ..services.gpu_util import capabilities

router = APIRouter(prefix="/api", tags=["capabilities"])


@router.get("/capabilities")
def get_capabilities() -> dict:
    return capabilities()
