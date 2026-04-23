"""Factory FastAPI : middlewares, healthcheck, montage des routers + dist statique."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .deps import FRONTEND_DIST, ROOT
from .routers import (
    autotile,
    bgmask,
    capabilities,
    cleanup,
    convert,
    history,
    inputs,
    outputs,
    presets,
    preview,
    spritesheet,
)
from .schemas.responses import HealthzResponse
from .services.job_store import job_store

__version__ = "1.0.0"

logger = logging.getLogger("pixel_lab")
logger.setLevel(os.environ.get("PIXEL_LAB_LOG_LEVEL", "INFO"))


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    job_store.bind_loop(asyncio.get_running_loop())
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pixel Lab API",
        version=__version__,
        description="Atelier pixel-art — conversion, preview live, bgmask, spritesheet, autotile.",
        lifespan=_lifespan,
    )

    # CORS : dev front sur :5173, prod sur :5500 même origine. Jamais allow_origins=["*"].
    cors_origins = os.environ.get(
        "PIXEL_LAB_CORS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5500,http://localhost:5500",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins if o.strip()],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Width", "X-Height", "X-Elapsed-Ms", "X-Cache-Hit-Depth",
                        "X-Cache", "X-Bgmask-Color", "X-Frames-Count", "X-Request-Id"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None)
        logger.exception("Unhandled exception (request_id=%s)", rid)
        return JSONResponse(
            status_code=500,
            content={"error": "internal", "request_id": rid},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        rid = getattr(request.state, "request_id", None)
        # `jsonable_encoder` convertit les `ValueError` imbriqués dans `ctx`
        # en strings — sans ça, `json.dumps` échoue sur les erreurs custom.
        return JSONResponse(
            status_code=422,
            content={"errors": jsonable_encoder(exc.errors()), "request_id": rid},
        )

    @app.get("/healthz", response_model=HealthzResponse, tags=["meta"])
    def healthz() -> HealthzResponse:
        return HealthzResponse(status="ok", version=__version__)

    # Dossiers statiques utilisateur : `inputs/` et `outputs/` (lecture seule via
    # StaticFiles). Le front référence `/inputs/<nom>` pour afficher la source et
    # `/outputs/<stem>/<iter>.png` pour les itérations produites.
    app.mount("/inputs", StaticFiles(directory=str(ROOT / "inputs"), check_dir=False), name="inputs")
    app.mount("/outputs", StaticFiles(directory=str(ROOT / "outputs"), check_dir=False), name="outputs")

    # Routers API
    app.include_router(convert.router)
    app.include_router(preview.router)
    app.include_router(bgmask.router)
    app.include_router(inputs.router)
    app.include_router(outputs.router)
    app.include_router(spritesheet.router)
    app.include_router(cleanup.router)
    app.include_router(autotile.router)
    app.include_router(history.router)
    app.include_router(presets.router)
    app.include_router(capabilities.router)

    # SPA Vue buildée : montée en dernier (routes `/api/*` et `/inputs/*` matchent avant).
    # En dev, le front tourne séparément via `npm run dev` sur :5173 avec proxy /api → :5500.
    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
    else:
        @app.get("/", include_in_schema=False)
        def _no_spa() -> dict:
            return {
                "message": (
                    "frontend-dist/ introuvable. Build le front : "
                    "`cd pixel-lab/frontend && npm ci && npm run build && cp -r dist ../frontend-dist`."
                ),
            }

    return app


app = create_app()
