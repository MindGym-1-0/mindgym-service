from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.auth import v1_router as auth_v1_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix='/api')
api_router.include_router(auth_v1_router, prefix='/api/v1')
