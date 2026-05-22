"""FastAPI application factory and main entry point"""
from __future__ import annotations

import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.api.auth import router as auth_router
from src.api.auth import v1_router as auth_v1_router
from src.api.onboarding import router as onboarding_router
from src.api.jobs import router as jobs_router
from src.api.jobs_id import router as jobs_id_router
from src.lib import config
from src.lib.config import get_settings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    try:
        settings = get_settings()
    except ValidationError:
        settings = None

    app = FastAPI(
        title="MindGym Service",
        description="Backend API for MindGym - AI-powered job search companion",
        version="0.1.0",
    )

    # Combine both CORS origins requirements
    cors_origins = config.cors_origin_list()
    allow_origins = ["http://localhost:3000", "http://localhost:3001"]
    if settings and settings.frontend_url:
        allow_origins.insert(0, settings.frontend_url)
    
    # Merge both origin lists cleanly removing duplicates
    final_origins = list(dict.fromkeys(allow_origins + cors_origins))
    allow_all = "*" in final_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else final_origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include their onboarding and authentication routers
    app.include_router(onboarding_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(auth_v1_router, prefix="/api/v1")

    # Include your Job Tracker features under the required specification
    app.include_router(jobs_router, prefix="/api/applications", tags=["jobs"])
    app.include_router(jobs_id_router, prefix="/api/applications", tags=["jobs"])

    @app.on_event("startup")
    async def validate_configuration() -> None:
        try:
            startup_settings = get_settings()
        except ValidationError:
            logger.warning("Missing environment configuration for Supabase-backed auth features")
            return

        if not startup_settings.supabase_service_role_key:
            logger.warning("SUPABASE_SERVICE_ROLE_KEY is not configured")
        if not startup_settings.resolved_supabase_jwt_secret:
            logger.warning("SUPABASE_JWT_SECRET is not configured")

    @app.get("/")
    async def root():
        return {"status": "MindGym API is running"}

    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    try:
        settings = get_settings()
        host = settings.api_host
        port = settings.api_port
        reload = settings.debug
    except ValidationError:
        logger.warning("Running with default host/port because configuration is incomplete")
        host = "0.0.0.0"
        port = 8000
        reload = False

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
    )