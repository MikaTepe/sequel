"""API routes"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router, tags=["extraction"])

__all__ = ["router"]