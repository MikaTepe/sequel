"""Base schemas used across all services"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BaseRequest(BaseModel):
    """Base request schema"""
    request_id: Optional[str] = Field(None, description="Optional request tracking ID")


class BaseResponse(BaseModel):
    """Base response schema"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime_seconds: Optional[float] = None
    dependencies: Optional[Dict[str, str]] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceInfo(BaseModel):
    """Service information"""
    name: str
    version: str
    status: str
    url: str
    health_endpoint: str