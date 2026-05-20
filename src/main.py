import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.api.auth import router as auth_router
from src.api.auth import v1_router as auth_v1_router
from src.lib.config import get_settings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api")
app.include_router(auth_v1_router, prefix="/api/v1")


@app.on_event("startup")
async def validate_configuration() -> None:
    try:
        settings = get_settings()
    except ValidationError:
        logger.exception("Missing required environment configuration for backend startup")
        raise

    if not settings.supabase_service_role_key:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY is not configured")
    if not settings.resolved_supabase_jwt_secret:
        logger.warning("SUPABASE_JWT_SECRET is not configured")


@app.get("/")
def root():
    return {"status": "MindGym API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
