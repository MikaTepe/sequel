"""FastAPI Dependencies"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
import uuid

from .config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)

# === AUTHENTICATION ===

async def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Basic authentication dependency"""

    # Development mode - allow without auth
    if settings.debug and credentials is None:
        return {
            "user_id": "dev_user",
            "username": "development",
            "roles": ["user", "admin"],
            "is_authenticated": True
        }

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: Implement JWT validation
    return {
        "user_id": "authenticated_user",
        "username": "user",
        "roles": ["user"],
        "is_authenticated": True,
        "token": credentials.credentials
    }


async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Admin-only access"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# === REQUEST TRACKING ===

async def get_request_id(request: Request) -> str:
    """Get or generate request ID"""
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id
    return request_id


# === PAGINATION ===

class PaginationParams:
    """Pagination parameters"""

    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), 1000)


def get_pagination_params(skip: int = 0, limit: int = 100) -> PaginationParams:
    """Get pagination parameters"""

    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip must be >= 0"
        )

    if limit <= 0 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 1000"
        )

    return PaginationParams(skip=skip, limit=limit)


# === RATE LIMITING ===

class RateLimiter:
    """Simple rate limiter"""

    def __init__(self):
        self._requests = {}

    def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        current_time = time.time()

        if identifier not in self._requests:
            self._requests[identifier] = []

        # Clean old requests
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier]
            if current_time - req_time < window
        ]

        # Check limit
        if len(self._requests[identifier]) < limit:
            self._requests[identifier].append(current_time)
            return True

        return False


rate_limiter = RateLimiter()


async def check_rate_limit(
        request: Request,
        current_user: Optional[dict] = Depends(get_current_user)
):
    """Rate limiting dependency"""

    if not settings.rate_limit_enabled:
        return

    identifier = (
        current_user.get("user_id") if current_user and current_user.get("is_authenticated")
        else request.client.host
    )

    if not rate_limiter.is_allowed(
            identifier=identifier,
            limit=settings.rate_limit_requests,
            window=settings.rate_limit_window
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {settings.rate_limit_requests} requests per {settings.rate_limit_window} seconds"
        )


# === SERVICE VALIDATION ===

async def validate_nlp_services():
    """Check if NLP services are available"""

    if not settings.enable_nlp_services:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NLP services are disabled"
        )

    if settings.keybert_enabled:
        from ..services.nlp.keybert_service import keybert_service
        if not keybert_service.is_initialized():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="KeyBERT service not initialized"
            )


# === TYPE ANNOTATIONS ===

RequestIdDep = Annotated[str, Depends(get_request_id)]
PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]
CurrentUserDep = Annotated[dict, Depends(get_current_user)]
AdminUserDep = Annotated[dict, Depends(get_admin_user)]