"""Proxy routes for forwarding requests to microservices"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
import httpx

from app.services.service_registry import service_registry

router = APIRouter()
logger = logging.getLogger("gateway.proxy")


@router.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy_request(request: Request, full_path: str):
    """Proxy requests to appropriate microservice"""

    # Find target service
    service_info = service_registry.find_service_by_path(f"/{full_path}")

    if not service_info:
        raise HTTPException(
            status_code=404,
            detail=f"No service found for path: /{full_path}"
        )

    service_url, service_path = service_info
    target_url = f"{service_url}{service_path}"

    # Forward request
    try:
        async with httpx.AsyncClient() as client:
            # Prepare headers
            headers = dict(request.headers)
            headers.pop("host", None)  # Remove host header

            # Get request body
            body = await request.body()

            # Forward request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=request.query_params,
                content=body,
                timeout=30.0
            )

            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )

    except httpx.RequestError as e:
        logger.error(f"Error proxying request to {target_url}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )