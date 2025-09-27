from typing import Optional, Generator, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import time
import uuid

from .config import get_settings
from .exceptions import AuthenticationException, AuthorizationException

logger = logging.getLogger(__name__)
settings = get_settings()

# Security
security = HTTPBearer(auto_error=False)


# === AUTHENTICATION & AUTHORIZATION ===

async def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Dependency for user authentication

    TODO: Implement JWT token validation based on your auth requirements

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User information

    Raises:
        HTTPException: If authentication fails
    """
    # In development mode, allow requests without authentication
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

    try:
        # TODO: Implement JWT token validation
        # token = credentials.credentials
        # user = validate_jwt_token(token)
        # return user

        # Placeholder implementation
        return {
            "user_id": "authenticated_user",
            "username": "user",
            "roles": ["user"],
            "is_authenticated": True,
            "token": credentials.credentials
        }

    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(
        current_user: dict = Depends(get_current_user)
):
    """
    Dependency for admin-only access

    Args:
        current_user: Current authenticated user

    Returns:
        User information if admin

    Raises:
        HTTPException: If user is not admin
    """
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# === REQUEST TRACKING ===

async def get_request_id(request: Request) -> str:
    """
    Dependency for request ID tracking

    Generates or extracts request ID for logging and tracing

    Args:
        request: FastAPI request object

    Returns:
        Unique request ID
    """
    # Check if request ID is provided in headers
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        # Generate new request ID
        request_id = str(uuid.uuid4())

    # Store in request state for access in other parts of the application
    request.state.request_id = request_id

    return request_id


class RequestTimer:
    """Request timing context manager"""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


async def get_request_timer() -> RequestTimer:
    """
    Dependency for request timing

    Returns:
        Request timer instance
    """
    return RequestTimer()


# === PAGINATION ===

class PaginationParams:
    """Pagination parameters"""

    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), 1000)  # Max 1000 items per page

    @property
    def offset(self) -> int:
        return self.skip

    @property
    def page_size(self) -> int:
        return self.limit


def get_pagination_params(
        skip: int = 0,
        limit: int = 100
) -> PaginationParams:
    """
    Dependency for pagination parameters

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        Pagination parameters

    Raises:
        HTTPException: If parameters are invalid
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip parameter must be >= 0"
        )

    if limit <= 0 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit parameter must be between 1 and 1000"
        )

    return PaginationParams(skip=skip, limit=limit)


# === SERVICE AVAILABILITY ===

async def validate_nlp_services():
    """
    Dependency to validate that NLP services are available

    Raises:
        HTTPException: If required services are unavailable
    """
    if not settings.enable_nlp_services:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NLP services are disabled"
        )

    # Check individual services
    unavailable_services = []

    # KeyBERT Service
    if settings.keybert_enabled:
        from ..services.nlp.keybert_service import keybert_service
        if not keybert_service.is_initialized():
            unavailable_services.append("KeyBERT")

    # Add other NLP services as they are developed
    # if settings.enable_text_analysis:
    #     from ..services.nlp.analysis_service import analysis_service
    #     if not analysis_service.is_initialized():
    #         unavailable_services.append("TextAnalysis")

    if unavailable_services:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NLP services unavailable: {', '.join(unavailable_services)}"
        )


# === RATE LIMITING ===

class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self._requests = {}

    def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed under rate limit

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit: Maximum requests per window
            window: Time window in seconds

        Returns:
            True if request is allowed
        """
        current_time = time.time()

        if identifier not in self._requests:
            self._requests[identifier] = []

        # Remove old requests outside the window
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier]
            if current_time - req_time < window
        ]

        # Check if under limit
        if len(self._requests[identifier]) < limit:
            self._requests[identifier].append(current_time)
            return True

        return False


rate_limiter = RateLimiter()


async def check_rate_limit(
        request: Request,
        current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Dependency for rate limiting

    Args:
        request: FastAPI request object
        current_user: Current authenticated user (optional)

    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.rate_limit_enabled:
        return

    # Use user ID if authenticated, otherwise use IP
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


# === DATABASE ===

async def get_database_session():
    """
    Dependency for database session

    TODO: Implement database session management

    Yields:
        Database session
    """
    # TODO: Implement with SQLAlchemy
    # async with AsyncSessionLocal() as session:
    #     try:
    #         yield session
    #     finally:
    #         await session.close()

    # Placeholder
    yield None


# === CACHING ===

async def get_cache_client():
    """
    Dependency for cache client (Redis)

    TODO: Implement Redis connection

    Returns:
        Cache client instance
    """
    # TODO: Implement Redis client
    return None


# === LOGGING CONTEXT ===

class LoggingContext:
    """Context for structured logging"""

    def __init__(self, request_id: str, user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.start_time = time.time()

    def get_context(self) -> dict:
        """Get logging context dictionary"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "timestamp": time.time()
        }


async def get_logging_context(
        request_id: str = Depends(get_request_id),
        current_user: Optional[dict] = Depends(get_current_user)
) -> LoggingContext:
    """
    Dependency for logging context

    Args:
        request_id: Request ID
        current_user: Current user (optional)

    Returns:
        Logging context
    """
    user_id = current_user.get("user_id") if current_user else None
    return LoggingContext(request_id=request_id, user_id=user_id)


# === TYPE ANNOTATIONS FOR COMMON DEPENDENCIES ===

# Common dependency type annotations for easier use
RequestIdDep = Annotated[str, Depends(get_request_id)]
PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]
CurrentUserDep = Annotated[dict, Depends(get_current_user)]
AdminUserDep = Annotated[dict, Depends(get_admin_user)]
LoggingContextDep = Annotated[LoggingContext, Depends(get_logging_context)]