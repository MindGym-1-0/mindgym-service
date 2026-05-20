import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.core.config import get_settings
from app.routes.router import api_router

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='MindGym Backend Authentication Service', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://localhost:3001'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(api_router)


@app.on_event('startup')
async def validate_configuration() -> None:
    try:
        settings = get_settings()
    except ValidationError:
        logger.exception('Missing required environment configuration for backend startup')
        raise

    if not settings.supabase_service_role_key:
        logger.warning('SUPABASE_SERVICE_ROLE_KEY is not configured')
    if not settings.resolved_supabase_jwt_secret:
        logger.warning('SUPABASE_JWT_SECRET is not configured')


@app.get('/health')
async def health_check() -> dict[str, str]:
    return {'status': 'ok'}
