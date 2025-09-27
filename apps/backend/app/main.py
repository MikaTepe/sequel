# apps/backend/app/main.py

import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

# Handle both relative and absolute imports
try:
    # Try relative imports first (when run as module)
    from .core.config import get_settings, settings
    from .core.exceptions import (
        SequelException,
        format_exception_details,
        KeywordExtractionException,
        ModelNotLoadedException
    )
    from .services.nlp.keybert_service import keybert_service
    from .api.v1.nlp.keybert import router as keybert_router
except ImportError:
    # Fall back to absolute imports (when run directly)
    import os
    import sys

    # Add the parent directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from app.core.config import get_settings, settings
    from app.core.exceptions import (
        SequelException,
        format_exception_details,
        KeywordExtractionException,
        ModelNotLoadedException
    )
    from app.services.nlp.keybert_service import keybert_service
    from app.api.v1.nlp.keybert import router as keybert_router


# Setup logging
def setup_logging():
    """Configure application logging"""

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

    # Configure specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    # Application logger
    app_logger = logging.getLogger("sequel")
    app_logger.setLevel(getattr(logging, settings.log_level.upper()))

    return app_logger


# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management

    Handles startup and shutdown events for the entire application
    """
    logger = logging.getLogger("sequel.main")

    # === STARTUP ===
    startup_start = time.time()

    logger.info("🚀 Starting Sequel Backend Application")
    logger.info(f"📊 Environment: {settings.environment}")
    logger.info(f"🏷️  Version: {settings.app_version}")
    logger.info(f"🐛 Debug Mode: {settings.debug}")
    logger.info(f"🌐 API Prefix: {settings.api_v1_prefix}")

    try:
        # Initialize NLP services
        if settings.enable_nlp_services:
            logger.info("🧠 Initializing NLP services...")

            # Initialize KeyBERT service
            if settings.keybert_enabled:
                logger.info("🔤 Initializing KeyBERT service...")
                await keybert_service.initialize()
                logger.info("✅ KeyBERT service initialized successfully")
            else:
                logger.info("⚠️ KeyBERT service disabled in configuration")
        else:
            logger.info("⚠️ NLP services disabled in configuration")

        startup_time = time.time() - startup_start
        logger.info(f"🎊 Application startup completed in {startup_time:.2f} seconds")

    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise e

    yield

    # === SHUTDOWN ===
    logger.info("🛑 Shutting down Sequel Backend Application")

    try:
        # Cleanup NLP services
        if settings.keybert_enabled and keybert_service.is_initialized():
            logger.info("🧹 Cleaning up KeyBERT service...")
            await keybert_service.cleanup()

        logger.info("👋 Application shutdown completed successfully")

    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application

    Returns:
        Configured FastAPI application instance
    """

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if settings.debug else None,
    )

    # Setup middleware
    setup_middleware(app)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Setup routers
    setup_routers(app)

    return app


def setup_middleware(app: FastAPI):
    """Configure application middleware"""

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Trusted Host Middleware (production security)
    if settings.is_production and settings.allowed_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )

    # Add request ID and timing middleware
    @app.middleware("http")
    async def add_request_id_and_timing(request: Request, call_next):
        """Add request ID and processing time to response headers"""

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
        request.state.request_id = request_id

        # Time the request
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Add headers
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

        return response


def setup_exception_handlers(app: FastAPI):
    """Configure global exception handlers"""

    logger = logging.getLogger("sequel.exceptions")

    @app.exception_handler(SequelException)
    async def sequel_exception_handler(request: Request, exc: SequelException):
        """Handle custom Sequel exceptions"""

        logger.warning(
            f"Sequel exception: {exc.message} "
            f"(code: {exc.error_code}, status: {exc.status_code})",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )

        error_details = format_exception_details(exc)

        return JSONResponse(
            status_code=exc.status_code,
            content=error_details
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""

        logger.warning(
            f"Validation error: {exc}",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "error_code": "VALIDATION_ERROR",
                "details": exc.errors(),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""

        logger.warning(
            f"HTTP exception: {exc.detail} (status: {exc.status_code})",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc):
        """Handle internal server errors"""

        logger.error(
            f"Internal server error: {exc}",
            extra={"request_id": getattr(request.state, "request_id", None)},
            exc_info=True
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred" if settings.is_production else str(exc),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


def setup_routers(app: FastAPI):
    """Configure API routers"""

    # === HEALTH ENDPOINTS ===

    @app.get("/health")
    async def global_health_check():
        """Global application health check"""

        # Check service health
        services_health = {}

        if settings.keybert_enabled:
            services_health["keybert"] = {
                "status": "healthy" if keybert_service.is_initialized() else "initializing",
                "initialized": keybert_service.is_initialized()
            }

        # Overall status
        all_healthy = all(
            service["status"] == "healthy"
            for service in services_health.values()
        )

        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "environment": settings.environment,
            "services": services_health,
            "uptime_seconds": time.time() - getattr(app.state, "start_time", time.time())
        }

    @app.get("/")
    async def root():
        """Root endpoint with API information"""

        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "description": settings.app_description,
            "environment": settings.environment,
            "api_docs": "/docs" if settings.debug else "disabled",
            "health_check": "/health",
            "api_v1": settings.api_v1_prefix,
            "timestamp": datetime.utcnow().isoformat()
        }

    # === API ROUTERS ===

    # NLP Services
    if settings.enable_nlp_services:
        app.include_router(
            keybert_router,
            prefix=f"{settings.api_v1_prefix}/nlp",
            tags=["nlp"]
        )


# Initialize logging
setup_logging()

# Create application instance
app = create_application()

# Store startup time for uptime calculation
app.state.start_time = time.time()

# Development server entry point
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else 4,
        access_log=settings.debug
    )