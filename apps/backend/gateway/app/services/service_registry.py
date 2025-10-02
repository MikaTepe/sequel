"""Service registry for managing microservices"""

import logging
from typing import Dict, List, Optional
import httpx

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("gateway.registry")


class ServiceRegistry:
    """Registry for managing microservice endpoints"""

    def __init__(self):
        self.services: Dict[str, dict] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Initialize service registry"""
        self._http_client = httpx.AsyncClient(timeout=10.0)

        # Register services
        self.services = {
            "keyword-extraction": {
                "name": "Keyword Extraction Service",
                "url": settings.keyword_extraction_url,
                "health": f"{settings.keyword_extraction_url}/health",
                "prefix": "/keybert",
            }
        }

        logger.info(f"Registered {len(self.services)} services")

    async def cleanup(self):
        """Cleanup resources"""
        if self._http_client:
            await self._http_client.aclose()

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get service URL by name"""
        service = self.services.get(service_name)
        return service["url"] if service else None

    def find_service_by_path(self, path: str) -> Optional[tuple[str, str]]:
        """Find service by request path"""
        for service_id, service in self.services.items():
            if path.startswith(service["prefix"]):
                # Remove prefix from path
                service_path = path[len(service["prefix"]):]
                return service["url"], service_path
        return None

    async def check_service_health(self, service_id: str) -> dict:
        """Check health of a specific service"""
        service = self.services.get(service_id)
        if not service or not self._http_client:
            return {"status": "unknown"}

        try:
            response = await self._http_client.get(service["health"])
            if response.status_code == 200:
                return {"status": "healthy", **response.json()}
            return {"status": "unhealthy", "code": response.status_code}
        except Exception as e:
            logger.error(f"Health check failed for {service_id}: {e}")
            return {"status": "unreachable", "error": str(e)}

    async def check_all_services(self) -> Dict[str, dict]:
        """Check health of all services"""
        results = {}
        for service_id in self.services:
            results[service_id] = await self.check_service_health(service_id)
        return results

    async def list_services(self) -> List[dict]:
        """List all registered services"""
        return [
            {
                "id": service_id,
                "name": service["name"],
                "prefix": service["prefix"],
            }
            for service_id, service in self.services.items()
        ]


service_registry = ServiceRegistry()