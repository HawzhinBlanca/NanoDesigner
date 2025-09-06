# Smart Graphic Designer API - Development Guide

## Table of Contents
1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Code Standards](#code-standards)
4. [Testing Strategy](#testing-strategy)
5. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
6. [Performance Optimization](#performance-optimization)
7. [Deployment Guide](#deployment-guide)
8. [Contributing](#contributing)

## Development Setup

### Prerequisites

- **Python**: 3.11 or higher
- **Poetry**: For dependency management
- **Docker**: For running dependencies
- **Git**: For version control
- **IDE**: VS Code, PyCharm, or similar with Python support

### Local Development Environment

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd NanoDesigner
   ```

2. **Set Up Python Environment**
   ```bash
   cd api
   poetry install
   poetry shell
   ```

3. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start Dependencies**
   ```bash
   docker compose up -d redis qdrant postgres langfuse minio
   ```

5. **Run Database Migrations**
   ```bash
   # If migrations exist
   poetry run alembic upgrade head
   ```

6. **Start the Development Server**
   ```bash
   poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Development Dependencies

The project uses Poetry for dependency management. Key development dependencies include:

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-mock = "^3.12.0"
black = "^24.0.0"
isort = "^5.13.0"
mypy = "^1.8.0"
ruff = "^0.1.0"
pre-commit = "^3.6.0"
```

### IDE Configuration

#### VS Code Settings (.vscode/settings.json)
```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestArgs": [
        "app/tests"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true
}
```

### Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
poetry run pre-commit install
```

This will run code formatting, linting, and basic tests before each commit.

## Project Structure

```
NanoDesigner/
├── api/                          # FastAPI application
│   ├── app/
│   │   ├── core/                 # Core configuration and utilities
│   │   │   ├── config.py         # Configuration management
│   │   │   ├── logging.py        # Logging setup
│   │   │   └── security.py       # Security utilities
│   │   ├── models/               # Data models and schemas
│   │   │   ├── schemas.py        # Pydantic request/response models
│   │   │   └── exceptions.py     # Custom exception classes
│   │   ├── routers/              # API route handlers
│   │   │   ├── render.py         # Main render endpoint
│   │   │   ├── ingest.py         # Document ingestion
│   │   │   ├── canon.py          # Brand canon management
│   │   │   ├── critique.py       # Design critique
│   │   │   ├── health.py         # Health checks
│   │   │   ├── websocket.py      # WebSocket endpoints
│   │   │   └── admin.py          # Admin endpoints
│   │   ├── services/             # Business logic services
│   │   │   ├── openrouter.py     # OpenRouter API client
│   │   │   ├── gemini_image.py   # Image generation service
│   │   │   ├── guardrails.py     # Validation service
│   │   │   ├── redis.py          # Caching service
│   │   │   ├── qdrant.py         # Vector database service
│   │   │   ├── storage_adapter.py # Storage abstraction
│   │   │   ├── langfuse.py       # Observability service
│   │   │   └── ...
│   │   ├── tests/                # Test suites
│   │   │   ├── unit/             # Unit tests
│   │   │   ├── integration/      # Integration tests
│   │   │   ├── contracts/        # Contract tests
│   │   │   └── fixtures/         # Test fixtures
│   │   └── main.py               # FastAPI application entry
│   ├── pyproject.toml            # Python dependencies
│   ├── Dockerfile                # Container definition
│   └── openapi.yaml              # API specification
├── docs/                         # Documentation
│   ├── API_DOCUMENTATION.md      # API usage guide
│   ├── DEVELOPMENT_GUIDE.md      # This file
│   └── ARCHITECTURE.md           # System architecture
├── tests/                        # System-level tests
│   ├── load/                     # Load testing
│   └── e2e/                      # End-to-end tests
├── guardrails/                   # Validation schemas
│   ├── render_plan.json
│   ├── canon.json
│   └── critique.json
├── policies/                     # Configuration policies
│   └── openrouter_policy.json
├── infra/                        # Infrastructure configs
│   ├── kong/                     # API gateway config
│   ├── k8s/                      # Kubernetes manifests
│   └── migrations/               # Database migrations
├── scripts/                      # Utility scripts
├── docker-compose.yml            # Local development stack
├── .env.example                  # Environment template
└── README.md                     # Project overview
```

### Key Components

#### Services Layer
The services layer contains the core business logic:

- **OpenRouter Service**: Handles AI model communication
- **Guardrails Service**: Validates AI outputs against schemas
- **Redis Service**: Provides caching and session management
- **Storage Service**: Abstracts file storage (local/S3)
- **Langfuse Service**: Observability and tracing

#### Routers Layer
API endpoints organized by domain:

- **Render Router**: Main design generation endpoint
- **Ingest Router**: Document processing and analysis
- **Canon Router**: Brand guideline management
- **Health Router**: System health and monitoring

#### Models Layer
Data models and validation:

- **Schemas**: Pydantic models for API requests/responses
- **Exceptions**: Custom exception hierarchy for error handling

## Code Standards

### Python Style Guide

We follow PEP 8 with some modifications:

```python
# Good: Type hints for all function parameters and returns
def generate_image(prompt: str, size: str = "1024x1024") -> Dict[str, Any]:
    """Generate an image using AI model.
    
    Args:
        prompt: Text description of the image.
        size: Image dimensions in WIDTHxHEIGHT format.
        
    Returns:
        Dictionary containing image data and metadata.
        
    Raises:
        ImageGenerationException: If generation fails.
    """
    pass

# Good: Descriptive variable names
user_request = parse_request(raw_data)
validation_errors = validate_schema(user_request)

# Bad: Abbreviated or unclear names
req = parse_request(data)
errs = validate(req)
```

### Error Handling Patterns

Use custom exceptions with proper error context:

```python
# Good: Specific exception with context
try:
    response = call_openrouter(model, messages)
except httpx.HTTPStatusError as e:
    raise OpenRouterException(
        message=f"API call failed: {e.response.status_code}",
        status_code=e.response.status_code,
        model=model,
        details={"response_body": e.response.text[:500]}
    )

# Bad: Generic exception handling
try:
    response = call_openrouter(model, messages)
except Exception as e:
    raise Exception(f"Something went wrong: {e}")
```

### Async/Await Guidelines

Prefer async functions for I/O operations:

```python
# Good: Async for I/O operations
async def process_render_request(request: RenderRequest) -> RenderResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
    return process_response(response)

# Good: Sync for CPU-bound operations
def validate_color_palette(colors: List[str]) -> List[str]:
    validated = []
    for color in colors:
        if re.match(r'^#[0-9A-Fa-f]{6}$', color):
            validated.append(color)
    return validated
```

### Logging Standards

Use structured logging with appropriate levels:

```python
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Good: Structured logging with context
def process_request(request_id: str, user_id: str) -> None:
    logger.info(
        "Processing render request",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "component": "render_service"
        }
    )
    
    try:
        result = expensive_operation()
        logger.info(
            "Request processed successfully",
            extra={"request_id": request_id, "duration_ms": result.duration}
        )
    except Exception as e:
        logger.error(
            "Request processing failed",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise
```

### Documentation Standards

All public functions must have comprehensive docstrings:

```python
def cache_get_set(
    client: redis.Redis,
    key: str,
    factory: Callable[[], Any],
    ttl: int = 86400
) -> Any:
    """Get value from cache or compute and store if missing.
    
    This function implements the cache-aside pattern, checking for
    an existing cached value first, and if not found, computing
    the value using the factory function and storing it in the cache.
    
    Args:
        client: Redis client instance.
        key: Cache key to retrieve/store value.
        factory: Function to compute value if cache miss.
        ttl: Time to live in seconds. Defaults to 86400 (24 hours).
        
    Returns:
        The cached or computed value.
        
    Raises:
        redis.RedisError: If Redis operations fail.
        
    Example:
        ```python
        def expensive_computation():
            return sum(range(1000000))
            
        result = cache_get_set(
            redis_client,
            "expensive_result",
            expensive_computation,
            ttl=3600
        )
        ```
    """
    pass
```

## Testing Strategy

### Test Pyramid

We follow the test pyramid approach:

```
    /\
   /  \     E2E Tests (Few)
  /____\    - Full system integration
 /      \   - Browser automation
/________\  - Production-like environment

/        \  Integration Tests (Some)
/__________\ - API endpoint testing
             - Database integration
             - External service mocking

/            \ Unit Tests (Many)
/______________\ - Function-level testing
                 - Service class testing
                 - Isolated component testing
```

### Unit Tests

Located in `api/app/tests/unit/`, these test individual functions and classes:

```python
# tests/unit/test_openrouter.py
import pytest
from unittest.mock import Mock, patch
from app.services.openrouter import call_task, OpenRouterException

class TestOpenRouterService:
    @patch('app.services.openrouter.call_openrouter')
    def test_call_task_success(self, mock_call):
        # Arrange
        mock_call.return_value = {"choices": [{"message": {"content": "Success"}}]}
        
        # Act
        result = call_task("planner", [{"role": "user", "content": "test"}])
        
        # Assert
        assert result["choices"][0]["message"]["content"] == "Success"
        mock_call.assert_called_once()
        
    @patch('app.services.openrouter.call_openrouter')
    def test_call_task_with_fallback(self, mock_call):
        # Test fallback behavior when primary model fails
        mock_call.side_effect = [
            Exception("Primary failed"),
            {"choices": [{"message": {"content": "Fallback success"}}]}
        ]
        
        result = call_task("planner", [{"role": "user", "content": "test"}])
        assert "Fallback success" in str(result)
```

### Integration Tests

Located in `api/app/tests/integration/`, these test component interactions:

```python
# tests/integration/test_render_endpoint.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_render_request():
    return {
        "project_id": "test-project",
        "prompts": {
            "task": "create",
            "instruction": "Create a simple banner"
        },
        "outputs": {
            "count": 1,
            "format": "png", 
            "dimensions": "800x400"
        }
    }

def test_render_endpoint_success(client, sample_render_request):
    """Test successful render request."""
    response = client.post("/render", json=sample_render_request)
    
    assert response.status_code == 200
    data = response.json()
    assert "assets" in data
    assert len(data["assets"]) == 1
    assert "audit" in data
    assert data["audit"]["guardrails_ok"] is True

def test_render_endpoint_validation_error(client):
    """Test render request with validation errors."""
    invalid_request = {
        "project_id": "",  # Invalid: empty string
        "prompts": {
            "task": "invalid_task",  # Invalid enum
            "instruction": "Hi"  # Invalid: too short
        }
    }
    
    response = client.post("/render", json=invalid_request)
    assert response.status_code == 422
    
    data = response.json()
    assert "validation_errors" in data or "detail" in data
```

### Contract Tests

Located in `api/app/tests/contracts/`, these validate API contracts:

```python
# tests/contracts/test_guardrails_contracts.py
import json
import pytest
from pathlib import Path
from app.services.guardrails import validate_contract

class TestGuardrailsContracts:
    def test_render_plan_contract(self):
        """Test render plan contract validation."""
        valid_plan = {
            "goal": "Create a professional banner",
            "ops": ["text_overlay", "style_transfer"],
            "safety": {
                "respect_logo_safe_zone": True,
                "palette_only": False
            }
        }
        
        # Should not raise exception
        validate_contract("render_plan.json", valid_plan)
        
    def test_render_plan_contract_invalid(self):
        """Test render plan contract with invalid data."""
        invalid_plan = {
            "goal": "X",  # Too short
            "ops": ["invalid_operation"],  # Invalid enum
            "safety": {}  # Missing required fields
        }
        
        with pytest.raises(HTTPException) as exc_info:
            validate_contract("render_plan.json", invalid_plan)
            
        assert exc_info.value.status_code == 422
        assert "guardrails" in exc_info.value.detail
```

### Load Tests

Located in `tests/load/`, these validate performance characteristics:

```bash
# Run load tests
cd tests/load
./run-load-tests.sh --type load --url http://localhost:8000
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test category
poetry run pytest app/tests/unit/
poetry run pytest app/tests/integration/
poetry run pytest app/tests/contracts/

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test
poetry run pytest app/tests/unit/test_openrouter.py::TestOpenRouterService::test_call_task_success

# Run tests in parallel
poetry run pytest -n auto
```

## Debugging and Troubleshooting

### Debug Configuration

#### FastAPI Debug Mode
```python
# main.py
import logging
from fastapi import FastAPI

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    title="SGD API",
    debug=True,  # Enable debug mode
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc"  # ReDoc at /redoc
)
```

#### VS Code Debug Configuration (.vscode/launch.json)
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "cwd": "${workspaceFolder}/api",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/api"
            }
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "app/tests/unit/test_openrouter.py::TestOpenRouterService::test_call_task_success",
                "-v",
                "-s"
            ],
            "cwd": "${workspaceFolder}/api"
        }
    ]
}
```

### Common Debug Scenarios

#### 1. OpenRouter API Issues
```python
# Add debug logging to openrouter.py
import logging

logger = logging.getLogger(__name__)

def call_openrouter(model: str, messages: List[dict], **kw) -> dict:
    logger.debug(f"Calling OpenRouter with model: {model}")
    logger.debug(f"Messages: {messages}")
    logger.debug(f"Additional params: {kw}")
    
    with httpx.Client() as client:
        try:
            response = client.post(url, json=payload)
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"API error: {response.text}")
                
            return response.json()
        except Exception as e:
            logger.error(f"Request failed: {e}", exc_info=True)
            raise
```

#### 2. Database Connection Issues
```python
# Debug Redis connection
def debug_redis_connection():
    import redis
    from app.core.config import settings
    
    try:
        client = redis.from_url(settings.redis_url)
        client.ping()
        print("✅ Redis connection successful")
        
        # Test basic operations
        client.set("test_key", "test_value", ex=10)
        value = client.get("test_key")
        print(f"✅ Redis read/write test: {value}")
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

# Debug Qdrant connection  
def debug_qdrant_connection():
    from qdrant_client import QdrantClient
    from app.core.config import settings
    
    try:
        client = QdrantClient(url=settings.qdrant_url)
        collections = client.get_collections()
        print(f"✅ Qdrant connection successful. Collections: {collections}")
        
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
```

#### 3. Performance Profiling
```python
# Add performance monitoring
import time
import functools
from typing import Callable, Any

def profile_time(func: Callable) -> Callable:
    """Decorator to profile function execution time."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            print(f"⏱️  {func.__name__} took {duration:.2f} seconds")
            
            # Log slow functions
            if duration > 1.0:
                logger.warning(f"Slow function detected: {func.__name__} ({duration:.2f}s)")
    
    return wrapper

# Usage
@profile_time
def expensive_operation():
    # Your code here
    pass
```

### Debugging Tools

#### 1. Request/Response Logging
```python
# middleware/logging.py
import logging
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("request_logger")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        logger.debug(f"Headers: {dict(request.headers)}")
        
        # Get request body for debugging (be careful with large payloads)
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if len(body) < 1000:  # Only log small bodies
                logger.debug(f"Body: {body.decode()}")
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        logger.info(f"Response: {response.status_code} ({duration:.2f}s)")
        
        return response
```

#### 2. Health Check Diagnostics
```python
# Enhanced health check for debugging
from app.routers.health import router

@router.get("/debug")
async def debug_health():
    """Detailed health information for debugging."""
    diagnostics = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": {
            "python_version": sys.version,
            "fastapi_version": fastapi.__version__,
            "env_vars": {
                key: "***" if "key" in key.lower() or "secret" in key.lower() else value
                for key, value in os.environ.items()
                if key.startswith(("SGD_", "OPENROUTER_", "REDIS_", "QDRANT_"))
            }
        },
        "dependencies": {},
        "performance": {}
    }
    
    # Test Redis
    try:
        start = time.time()
        redis_client = get_redis_client()
        redis_client.ping()
        diagnostics["dependencies"]["redis"] = {
            "status": "connected",
            "response_time_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        diagnostics["dependencies"]["redis"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test Qdrant
    try:
        start = time.time()
        qdrant_client = get_qdrant_client()
        collections = qdrant_client.get_collections()
        diagnostics["dependencies"]["qdrant"] = {
            "status": "connected",
            "collections_count": len(collections.collections),
            "response_time_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        diagnostics["dependencies"]["qdrant"] = {
            "status": "error",
            "error": str(e)
        }
    
    return diagnostics
```

## Performance Optimization

### Database Optimization

#### Redis Configuration
```python
# Optimize Redis connection pooling
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

# Create connection pool
pool = ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    retry_on_timeout=True,
    socket_connect_timeout=5,
    socket_timeout=5
)

redis_client = redis.Redis(connection_pool=pool, decode_responses=True)
```

#### Qdrant Optimization
```python
# Optimize vector search performance
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Configure client with performance settings
qdrant_client = QdrantClient(
    url=settings.qdrant_url,
    grpc_port=6334,  # Use gRPC for better performance
    prefer_grpc=True,
    timeout=30
)

# Optimize collection creation
def create_optimized_collection(collection_name: str, vector_size: int):
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
            # Performance optimizations
            on_disk_payload=True,  # Store payload on disk
            hnsw_config={
                "m": 16,  # Number of bi-directional links
                "ef_construct": 100,  # Size of dynamic candidate list
            }
        ),
        # Sharding configuration for large datasets
        shard_number=2,
        replication_factor=1
    )
```

### Caching Strategies

#### Multi-level Caching
```python
from functools import lru_cache
from typing import Optional, Dict, Any
import asyncio

class CacheManager:
    """Multi-level cache with memory and Redis tiers."""
    
    def __init__(self, redis_client, memory_size: int = 1000):
        self.redis = redis_client
        self.memory_cache = {}
        self.memory_size = memory_size
        
    @lru_cache(maxsize=1000)
    def _memory_get(self, key: str) -> Optional[Any]:
        """Memory cache tier (fastest)."""
        return self.memory_cache.get(key)
        
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache with fallback tiers."""
        # Try memory cache first
        value = self._memory_get(key)
        if value is not None:
            return value
            
        # Try Redis cache
        value = await self.redis.get(key)
        if value is not None:
            # Promote to memory cache
            self.memory_cache[key] = value
            return value
            
        return None
        
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in both cache tiers."""
        # Set in Redis with TTL
        await self.redis.setex(key, ttl, value)
        
        # Set in memory cache
        self.memory_cache[key] = value
        
        # Maintain memory cache size
        if len(self.memory_cache) > self.memory_size:
            # Remove oldest entries (simple LRU)
            oldest_keys = list(self.memory_cache.keys())[:len(self.memory_cache) - self.memory_size]
            for old_key in oldest_keys:
                del self.memory_cache[old_key]
```

#### Smart Cache Keys
```python
import hashlib
from typing import Any, Dict

def generate_cache_key(operation: str, **params) -> str:
    """Generate deterministic cache keys from parameters."""
    
    # Sort parameters for consistent keys
    sorted_params = sorted(params.items())
    
    # Create string representation
    param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
    
    # Generate hash for long keys
    if len(param_str) > 100:
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"{operation}:{param_hash}"
    
    return f"{operation}:{param_str}"

# Usage
cache_key = generate_cache_key(
    "render_plan",
    project_id="proj_123",
    instruction="Create banner",
    constraints={"palette": ["#FF0000", "#00FF00"]}
)
```

### Async Optimization

#### Connection Pooling
```python
import asyncio
import aiohttp
from typing import AsyncGenerator

class HTTPClientManager:
    """Manage HTTP connection pools for external APIs."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with connection pooling."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection limit
                limit_per_host=20,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=60,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=30,  # Total request timeout
                connect=10,  # Connection timeout
                sock_read=10  # Socket read timeout
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "SGD-API/1.0"}
            )
            
        return self.session
        
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

# Global client manager
http_manager = HTTPClientManager()

# Use in services
async def call_external_api(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    session = await http_manager.get_session()
    async with session.post(url, json=data) as response:
        return await response.json()
```

#### Background Tasks
```python
import asyncio
from typing import Callable, Any
from concurrent.futures import ThreadPoolExecutor

class BackgroundTaskManager:
    """Manage background tasks and thread pools."""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: set = set()
        
    async def run_in_background(self, func: Callable, *args, **kwargs) -> asyncio.Task:
        """Run function in background task."""
        task = asyncio.create_task(func(*args, **kwargs))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task
        
    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """Run CPU-intensive function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
        
    async def shutdown(self):
        """Gracefully shutdown background tasks."""
        # Cancel pending tasks
        for task in self.tasks:
            task.cancel()
            
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        # Shutdown thread pool
        self.executor.shutdown(wait=True)

# Usage
background_manager = BackgroundTaskManager()

async def process_render_async(request: RenderRequest):
    # Quick validation and response
    validation_result = await validate_request(request)
    
    # Process heavy work in background
    task = await background_manager.run_in_background(
        generate_and_store_assets,
        request,
        validation_result
    )
    
    return {"job_id": task.get_name(), "status": "processing"}
```

## Deployment Guide

### Docker Configuration

#### Multi-stage Dockerfile
```dockerfile
# api/Dockerfile
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only=main --no-dev

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r sgd && useradd -r -g sgd sgd

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
WORKDIR /app
COPY app/ app/
COPY policies/ policies/
COPY guardrails/ guardrails/

# Set ownership
RUN chown -R sgd:sgd /app

# Switch to non-root user
USER sgd

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Production Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
      target: production
    ports:
      - "8000:8000"
    environment:
      - SERVICE_ENV=production
      - LOG_LEVEL=INFO
    env_file:
      - .env.production
    depends_on:
      - redis
      - qdrant
      - postgres
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./infra/nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  qdrant:
    image: qdrant/qdrant:v1.11.0
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  qdrant_data:
  postgres_data:
```

### Kubernetes Deployment

#### API Deployment
```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sgd-api
  labels:
    app: sgd-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sgd-api
  template:
    metadata:
      labels:
        app: sgd-api
    spec:
      containers:
      - name: api
        image: sgd-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: SERVICE_ENV
          value: "production"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: QDRANT_URL
          value: "http://qdrant:6333"
        envFrom:
        - secretRef:
            name: sgd-api-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
      imagePullSecrets:
      - name: registry-credentials
---
apiVersion: v1
kind: Service
metadata:
  name: sgd-api-service
spec:
  selector:
    app: sgd-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Horizontal Pod Autoscaler
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sgd-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sgd-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### CI/CD Pipeline

#### GitHub Actions
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
          
      qdrant:
        image: qdrant/qdrant:v1.11.0
        ports:
          - 6333:6333
        options: >-
          --health-cmd "curl -f http://localhost:6333/health"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: latest
        virtualenvs-create: true
        virtualenvs-in-project: true
        
    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v3
      with:
        path: api/.venv
        key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
        
    - name: Install dependencies
      if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
      working-directory: ./api
      run: poetry install --no-interaction --no-root
      
    - name: Install project
      working-directory: ./api
      run: poetry install --no-interaction
      
    - name: Lint with ruff
      working-directory: ./api
      run: poetry run ruff check .
      
    - name: Format check with black
      working-directory: ./api
      run: poetry run black --check .
      
    - name: Type check with mypy
      working-directory: ./api
      run: poetry run mypy app/
      
    - name: Run unit tests
      working-directory: ./api
      run: poetry run pytest app/tests/unit/ -v --cov=app --cov-report=xml
      
    - name: Run integration tests
      working-directory: ./api
      run: poetry run pytest app/tests/integration/ -v
      env:
        REDIS_URL: redis://localhost:6379/0
        QDRANT_URL: http://localhost:6333
        
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./api/coverage.xml
        
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
        
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  build-and-deploy:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
      
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
        
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
          
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./api/Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        
    - name: Deploy to staging
      if: github.ref == 'refs/heads/develop'
      run: |
        echo "Deploy to staging environment"
        # Add staging deployment commands
        
    - name: Deploy to production
      if: github.ref == 'refs/heads/main'
      run: |
        echo "Deploy to production environment"
        # Add production deployment commands
```

## Contributing

### Development Workflow

1. **Fork the Repository**
   ```bash
   git clone https://github.com/your-username/NanoDesigner.git
   cd NanoDesigner
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes**
   - Follow code standards and guidelines
   - Add tests for new functionality
   - Update documentation as needed

4. **Test Changes**
   ```bash
   # Run all tests
   cd api
   poetry run pytest
   
   # Run linting
   poetry run ruff check .
   poetry run black --check .
   poetry run mypy app/
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat`: New features
- `fix`: Bug fixes  
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Code Review Process

1. **Automated Checks**
   - All tests must pass
   - Code coverage must be maintained
   - Linting and formatting checks must pass
   - Security scans must pass

2. **Manual Review**
   - At least one approval from a maintainer
   - Architecture decisions reviewed for complex changes
   - Documentation updates verified
   - Performance impact assessed

3. **Merge Requirements**
   - All conversations resolved
   - Up-to-date with main branch
   - No merge conflicts

### Release Process

1. **Version Bump**
   ```bash
   # Update version in pyproject.toml
   poetry version minor  # or major, patch
   ```

2. **Update Changelog**
   - Add release notes to CHANGELOG.md
   - Include breaking changes, new features, bug fixes

3. **Create Release**
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0"
   git push origin v1.2.0
   ```

4. **Deploy**
   - Automated deployment triggers from tag
   - Monitor deployment health
   - Update documentation if needed

---

This development guide provides comprehensive information for contributing to the Smart Graphic Designer API project. For additional questions, please reach out to the development team or create an issue on GitHub.