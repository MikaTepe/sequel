"""Keyword Extraction Microservice - KeyBERT Service"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import get_settings
from app.services.keybert_service import keybert_service
from app.api.v1 import router as api_router

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s [%(levelname)s] [keyword-extraction] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("keyword-extraction")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Service lifespan management"""
    logger.info("🚀 Starting Keyword Extraction Service")

    # Initialize KeyBERT
    await keybert_service.initialize()
    logger.info("✅ KeyBERT initialized")

    yield

    # Cleanup
    logger.info("🛑 Shutting down")
    await keybert_service.cleanup()


def create_application() -> FastAPI:
    """Create FastAPI application"""

    app = FastAPI(
        title="Keyword Extraction Service",
        description="Microservice for keyword extraction using KeyBERT",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy" if keybert_service.is_initialized() else "starting",
            "service": "keyword-extraction",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "keybert_initialized": keybert_service.is_initialized()
        }

    # Include API routes
    app.include_router(api_router)

    return app


app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )