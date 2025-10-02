"""API routes"""
from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter(prefix="/keybert", tags=["extraction"])
router.include_router(endpoints_router)

__all__ = ["router"]