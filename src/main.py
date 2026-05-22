from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.jobs import router as jobs_router
from src.api.jobs_id import router as jobs_id_router
from src.lib import config


def create_app() -> FastAPI:
    app = FastAPI(title="MindGym Service")

    cors_origins = config.cors_origin_list()
    allow_all = cors_origins == ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"ok": True}

    # Swapped routing prefixes to match frontend contracts (/api/applications)
    app.include_router(jobs_router, prefix="/api/applications", tags=["jobs"])
    app.include_router(jobs_id_router, prefix="/api/applications", tags=["jobs"])
    return app


app = create_app()