"""Sequel Backend - Main Application"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

from app.core.config import get_settings
from app.core.exceptions import SequelException
from app.services.nlp.keybert_service import keybert_service
from app.api.v1.nlp.keybert import router as keybert_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sequel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")

    if settings.enable_nlp_services and settings.keybert_enabled:
        logger.info("🔤 Initializing KeyBERT service...")
        await keybert_service.initialize()
        logger.info("✅ KeyBERT service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    if keybert_service.is_initialized():
        await keybert_service.cleanup()
    logger.info("👋 Shutdown complete")


def create_application() -> FastAPI:
    """Create FastAPI application"""

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
        request.state.request_id = request_id

        start = time.time()
        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round((time.time() - start) * 1000, 2))

        return response

    # Exception handlers
    @app.exception_handler(SequelException)
    async def sequel_exception_handler(request: Request, exc: SequelException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "error_code": exc.error_code,
                "status_code": exc.status_code
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "details": exc.errors()
            }
        )

    # Routes
    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "services": {
                "keybert": {
                    "initialized": keybert_service.is_initialized()
                }
            }
        }

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "api_docs": "/docs" if settings.debug else "disabled",
            "health": "/health"
        }

    # Include API routers
    if settings.enable_nlp_services:
        app.include_router(
            keybert_router,
            prefix=f"{settings.api_v1_prefix}/nlp"
        )

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