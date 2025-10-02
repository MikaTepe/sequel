"""API Gateway - Central entry point for all microservices"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import get_settings
from app.core.middleware import RequestIdMiddleware, LoggingMiddleware
from app.services.service_registry import service_registry
from app.routes.proxy import router as proxy_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s [%(levelname)s] [gateway] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting API Gateway")

    # Initialize service registry
    await service_registry.initialize()
    logger.info("✅ Service registry initialized")

    yield

    # Cleanup
    logger.info("🛑 Shutting down API Gateway")
    await service_registry.cleanup()


def create_application() -> FastAPI:
    """Create FastAPI application"""

    app = FastAPI(
        title="Sequel API Gateway",
        description="Central API Gateway for Sequel microservices",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Routes
    @app.get("/health")
    async def health():
        """Gateway health check"""
        services_health = await service_registry.check_all_services()

        return {
            "status": "healthy",
            "service": "gateway",
            "version": "1.0.0",
            "services": services_health
        }

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "Sequel API Gateway",
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else "disabled",
            "services": await service_registry.list_services()
        }

    # Include proxy router
    app.include_router(proxy_router, prefix="/api")

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
