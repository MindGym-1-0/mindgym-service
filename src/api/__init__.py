"""API routes and endpoints"""
from fastapi import APIRouter
from .onboarding import router as onboarding_router
from .auth import router as auth_router

# Combine all routers
router = APIRouter()
router.include_router(onboarding_router)
router.include_router(auth_router)

__all__ = ["router"]
