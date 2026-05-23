"""FastAPI application factory and main entry point"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager  # Added for modern lifespan handling
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.auth import v1_router as auth_v1_router
from src.api.onboarding import router as onboarding_router
from src.api.jobs import router as jobs_router
from src.api.jobs_id import router as jobs_id_router
# 1. IMPORT YOUR NEW STREAKS ROUTER HERE
from src.api.streaks import router as streaks_router
from src.lib import config
from src.lib.config import settings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup validation routines cleanly via modern lifespan architecture"""
    # 🚀 Everything here runs on application STARTUP
    if not getattr(settings, "supabase_service_role_key", None):
        logger.warning("SUPABASE_SERVICE_ROLE_KEY is not configured")
    if not getattr(settings, "resolved_supabase_jwt_secret", None):
        logger.warning("SUPABASE_JWT_SECRET is not configured")
        
    yield  # ⏸️ Application serves traffic while paused here
    
    # 🛑 Everything here runs on application SHUTDOWN (Optional)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="MindGym Service",
        description="Backend API for MindGym - AI-powered job search companion",
        version="0.1.0",
        lifespan=lifespan,  # Hooking up the clean, warning-free lifespan manager
    )

    # Combine both CORS origins requirements
    cors_origins = config.cors_origin_list()
    allow_origins = ["http://localhost:3000", "http://localhost:3001"]
    if settings and getattr(settings, "frontend_url", None):
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

    # 2. MOUNT THE STREAKS ROUTER WITH THE REQUIRED PREFIX AND TAGS
    app.include_router(streaks_router, prefix="/api/streaks", tags=["streaks"])

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

    host = getattr(settings, "api_host", "0.0.0.0")
    port = getattr(settings, "api_port", 8000)
    reload = getattr(settings, "debug", False)

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
    )