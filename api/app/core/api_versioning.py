"""API Versioning Strategy Implementation.

This module provides a comprehensive API versioning system supporting:
- URL path versioning (/v1/, /v2/)
- Header-based versioning
- Query parameter versioning
- Content negotiation
"""

from typing import Optional, Dict, Any, Callable, List
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class VersioningStrategy(Enum):
    """API versioning strategies."""
    URL_PATH = "url_path"
    HEADER = "header"
    QUERY_PARAM = "query_param"
    CONTENT_TYPE = "content_type"


@dataclass
class APIVersion:
    """API version configuration."""
    version: str
    deprecated: bool = False
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    changes: List[str] = None
    
    def __post_init__(self):
        if self.changes is None:
            self.changes = []
    
    def is_active(self) -> bool:
        """Check if version is still active."""
        if self.sunset_date:
            return datetime.now() < self.sunset_date
        return True
    
    def is_deprecated(self) -> bool:
        """Check if version is deprecated."""
        return self.deprecated
    
    def get_deprecation_headers(self) -> Dict[str, str]:
        """Get deprecation headers for response."""
        headers = {}
        if self.deprecated:
            headers["Sunset"] = self.sunset_date.isoformat() if self.sunset_date else ""
            headers["Deprecation"] = "true"
            if self.deprecation_date:
                headers["Deprecation-Date"] = self.deprecation_date.isoformat()
        return headers


class VersionManager:
    """Manage API versions and routing."""
    
    def __init__(self, default_version: str = "1.0"):
        self.versions: Dict[str, APIVersion] = {}
        self.default_version = default_version
        self.routers: Dict[str, APIRouter] = {}
        
    def register_version(self, version: APIVersion) -> None:
        """Register a new API version."""
        self.versions[version.version] = version
        self.routers[version.version] = APIRouter(prefix=f"/v{version.version.split('.')[0]}")
    
    def get_version(self, version_str: str) -> Optional[APIVersion]:
        """Get version configuration."""
        return self.versions.get(version_str)
    
    def get_router(self, version_str: str) -> Optional[APIRouter]:
        """Get router for a specific version."""
        return self.routers.get(version_str)
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all available versions."""
        return [
            {
                "version": v.version,
                "deprecated": v.deprecated,
                "active": v.is_active(),
                "sunset_date": v.sunset_date.isoformat() if v.sunset_date else None,
                "changes": v.changes
            }
            for v in self.versions.values()
        ]


# Global version manager
version_manager = VersionManager()

# Register versions
version_manager.register_version(
    APIVersion(
        version="1.0",
        deprecated=False,
        changes=["Initial API release"]
    )
)

version_manager.register_version(
    APIVersion(
        version="2.0",
        deprecated=False,
        changes=[
            "Improved render response format",
            "Added batch processing support",
            "Enhanced error responses"
        ]
    )
)

version_manager.register_version(
    APIVersion(
        version="1.1",
        deprecated=True,
        deprecation_date=datetime.now() - timedelta(days=30),
        sunset_date=datetime.now() + timedelta(days=60),
        changes=["Transitional version between v1 and v2"]
    )
)


def versioned_route(
    version: str,
    deprecated: bool = False,
    alternate_versions: Optional[Dict[str, Callable]] = None
):
    """Decorator for versioned routes.
    
    Args:
        version: API version this route belongs to
        deprecated: Whether this specific route is deprecated
        alternate_versions: Alternative implementations for other versions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get('request') or args[0]
            
            # Get requested version
            requested_version = extract_version(request)
            
            # Check if version is valid
            api_version = version_manager.get_version(requested_version)
            if not api_version:
                raise HTTPException(
                    status_code=400,
                    detail=f"API version {requested_version} not supported"
                )
            
            if not api_version.is_active():
                raise HTTPException(
                    status_code=410,
                    detail=f"API version {requested_version} has been sunset"
                )
            
            # Use alternate implementation if available
            if alternate_versions and requested_version in alternate_versions:
                return await alternate_versions[requested_version](*args, **kwargs)
            
            # Call original function
            response = await func(*args, **kwargs)
            
            # Add version headers
            if isinstance(response, JSONResponse):
                response.headers["API-Version"] = requested_version
                if api_version.is_deprecated():
                    for key, value in api_version.get_deprecation_headers().items():
                        response.headers[key] = value
            
            return response
        
        return wrapper
    return decorator


def extract_version(request: Request) -> str:
    """Extract API version from request.
    
    Priority order:
    1. URL path (/v1/, /v2/)
    2. Header (API-Version or Accept)
    3. Query parameter (?version=1.0)
    4. Default version
    """
    # Check URL path
    path_parts = request.url.path.split("/")
    for part in path_parts:
        if part.startswith("v") and part[1:].replace(".", "").isdigit():
            return part[1:]
    
    # Check headers
    if "API-Version" in request.headers:
        return request.headers["API-Version"]
    
    if "Accept" in request.headers:
        accept = request.headers["Accept"]
        if "version=" in accept:
            version = accept.split("version=")[1].split(";")[0].split(",")[0]
            return version.strip()
    
    # Check query parameters
    if "version" in request.query_params:
        return request.query_params["version"]
    
    # Return default
    return version_manager.default_version


# Version-specific response models
class RenderResponseV1(BaseModel):
    """Render response for API v1."""
    assets: List[Dict[str, Any]]
    audit: Dict[str, Any]


class RenderResponseV2(BaseModel):
    """Render response for API v2 with enhanced fields."""
    assets: List[Dict[str, Any]]
    audit: Dict[str, Any]
    metadata: Dict[str, Any]
    processing_stats: Dict[str, Any]


def transform_response_for_version(
    data: Dict[str, Any],
    from_version: str,
    to_version: str
) -> Dict[str, Any]:
    """Transform response data between API versions."""
    
    if from_version == "2.0" and to_version == "1.0":
        # Downgrade from v2 to v1
        transformed = {
            "assets": data.get("assets", []),
            "audit": data.get("audit", {})
        }
        # Remove v2-specific fields
        return transformed
    
    elif from_version == "1.0" and to_version == "2.0":
        # Upgrade from v1 to v2
        transformed = data.copy()
        transformed["metadata"] = {}
        transformed["processing_stats"] = {}
        return transformed
    
    return data


# Middleware for version handling
class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware for API version handling."""
    
    def __init__(self, app: ASGIApp, version_manager: VersionManager):
        super().__init__(app)
        self.version_manager = version_manager
    
    async def dispatch(self, request: Request, call_next):
        """Process request with version handling."""
        # Extract version
        version = extract_version(request)
        
        # Store in request state
        request.state.api_version = version
        
        # Check if version exists
        api_version = self.version_manager.get_version(version)
        if not api_version:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid API version",
                    "supported_versions": [v.version for v in self.version_manager.versions.values()]
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add version headers
        response.headers["API-Version"] = version
        response.headers["X-API-Version-Status"] = "deprecated" if api_version.is_deprecated() else "stable"
        
        # Add deprecation headers if needed
        if api_version.is_deprecated():
            for key, value in api_version.get_deprecation_headers().items():
                response.headers[key] = str(value)
        
        return response


# Version discovery endpoint
async def get_api_versions(request: Request) -> JSONResponse:
    """Get available API versions."""
    return JSONResponse(
        content={
            "versions": version_manager.list_versions(),
            "default": version_manager.default_version,
            "current": extract_version(request)
        }
    )


# Backwards compatibility layer
class BackwardsCompatibilityHandler:
    """Handle backwards compatibility between versions."""
    
    @staticmethod
    def handle_deprecated_field(
        field_name: str,
        old_value: Any,
        new_field_name: str,
        transformer: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Handle deprecated field mapping."""
        new_value = transformer(old_value) if transformer else old_value
        return {
            new_field_name: new_value,
            "_deprecated_mapping": {
                field_name: new_field_name
            }
        }
    
    @staticmethod
    def add_compatibility_layer(
        response: Dict[str, Any],
        version: str
    ) -> Dict[str, Any]:
        """Add compatibility layer to response."""
        response["_api_version"] = version
        response["_compatibility"] = {
            "warnings": [],
            "deprecated_fields": [],
            "new_fields": []
        }
        return response


# Example versioned endpoint implementations
async def render_v1(request: Request, prompt: str) -> Dict[str, Any]:
    """Render endpoint for API v1."""
    return {
        "assets": [{"url": "https://example.com/v1/image.png"}],
        "audit": {"cost": 0.01}
    }


async def render_v2(request: Request, prompt: str) -> Dict[str, Any]:
    """Render endpoint for API v2."""
    return {
        "assets": [{"url": "https://example.com/v2/image.png", "id": "asset-123"}],
        "audit": {"cost": 0.01, "model": "dall-e-3"},
        "metadata": {"version": "2.0"},
        "processing_stats": {"duration_ms": 1500}
    }


# Usage example
if __name__ == "__main__":
    from fastapi import FastAPI
    
    app = FastAPI(title="Versioned API Example")
    
    # Add version middleware
    app.add_middleware(APIVersionMiddleware, version_manager=version_manager)
    
    # Add version discovery endpoint
    app.get("/versions")(get_api_versions)
    
    # Add versioned routes
    v1_router = version_manager.get_router("1.0")
    v2_router = version_manager.get_router("2.0")
    
    if v1_router:
        v1_router.post("/render")(render_v1)
        app.include_router(v1_router)
    
    if v2_router:
        v2_router.post("/render")(render_v2)
        app.include_router(v2_router)