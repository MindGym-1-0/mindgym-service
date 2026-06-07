"""FastAPI application factory and main entry point"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.auth import v1_router as auth_v1_router
from src.api.coach import router as coach_router
from src.api.daily_focus import router as daily_focus_router
from src.api.insights import router as insights_router
from src.api.interviews import router as interviews_router
from src.api.jobs import router as jobs_router
from src.api.jobs_id import router as jobs_id_router
from src.api.mood_logs import router as mood_logs_router
from src.api.onboarding import router as onboarding_router
from src.api.progress import router as progress_router
from src.api.sessions import router as sessions_router
from src.api.sessions import users_router as users_router
from src.api.streaks import router as streaks_router
from src.api.weekly_mission import router as weekly_mission_router
from src.lib import config
from src.lib.config import settings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup validation routines via modern lifespan architecture.

    🚀 Everything here runs on application STARTUP.
    """
    if not getattr(settings, "supabase_service_role_key", None):
        logger.warning("SUPABASE_SERVICE_ROLE_KEY is not configured")
    if not getattr(settings, "resolved_supabase_jwt_secret", None):
        logger.warning("SUPABASE_JWT_SECRET is not configured")

    yield  # ⏸️ Application serves traffic while paused here


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="MindGym Service",
        description="Backend API for MindGym - AI job search companion",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Combine both CORS origins requirements
    cors_origins = config.cors_origin_list()
    allow_origins = ["http://localhost:3000", "http://localhost:3001"]
    if settings and getattr(settings, "frontend_url", None):
        allow_origins.insert(0, settings.frontend_url)

    # Merge both origin lists cleanly removing duplicates
    final_origins = list(dict.fromkeys(allow_origins + cors_origins))
    # Credentials-based auth cannot be used with wildcard CORS origins.
    final_origins = [origin for origin in final_origins if origin != "*"]
    if not final_origins:
        raise RuntimeError(
            "CORS_ORIGINS only contained '*' which is incompatible with "
            "allow_credentials=True. Add at least one explicit origin."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=final_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include onboarding and authentication routers
    app.include_router(onboarding_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(auth_v1_router, prefix="/api/v1")

    # Include Job Tracker features under the required specification
    app.include_router(
        jobs_router, prefix="/api/applications", tags=["jobs"]
    )
    app.include_router(
        jobs_id_router, prefix="/api/applications", tags=["jobs"]
    )

    # Session and user profile routes
    app.include_router(sessions_router)
    app.include_router(users_router)

    # Progress, Analytics, and AI Insights routes
    app.include_router(progress_router, prefix="/api", tags=["progress"])
    app.include_router(insights_router, tags=["insights"])

    # Streaks and Core Platform routers
    app.include_router(
        streaks_router, prefix="/api/streaks", tags=["streaks"]
    )
    app.include_router(coach_router, prefix="/api/coach", tags=["coach"])
    app.include_router(
        interviews_router, prefix="/api/interviews", tags=["interviews"]
    )

    # Core user optimization routers
    app.include_router(
        mood_logs_router, prefix="/api/mood-logs", tags=["mood-logs"]
    )
    app.include_router(
        daily_focus_router, prefix="/api/daily-focus", tags=["Daily Focus"]
    )
    app.include_router(
        weekly_mission_router,
        prefix="/api/weekly-mission",
        tags=["Weekly Mission"],
    )

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
