"""FastAPI application factory and main entry point"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.jobs import router as jobs_router
from src.api.jobs_id import router as jobs_id_router
from src.lib import config
from src.lib.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="MindGym Service",
        description="Backend API for MindGym - AI-powered job search companion",
        version="0.1.0",
    )

    cors_origins = config.cors_origin_list()
    allow_all = cors_origins == ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}

    # Registering endpoints under the agreed frontend spec (/api/applications)
    app.include_router(jobs_router, prefix="/api/applications", tags=["jobs"])
    app.include_router(jobs_id_router, prefix="/api/applications", tags=["jobs"])
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )