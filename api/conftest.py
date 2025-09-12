"""Pytest configuration and fixtures for the Smart Graphic Designer API."""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add the api directory to Python path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

from app.main import app
from app.core.config import settings


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_openrouter():
    """Mock OpenRouter API calls."""
    mock = MagicMock()
    mock.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"goal": "test", "ops": ["text_overlay"], "safety": {"respect_logo_safe_zone": true, "palette_only": false}}'
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        },
        "model": "openrouter/gpt-4"
    }
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.setex.return_value = True
    return mock


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client."""
    mock = MagicMock()
    mock.upsert.return_value = {"status": "ok"}
    mock.search.return_value = []
    return mock


@pytest.fixture
def mock_storage():
    """Mock storage adapter."""
    mock = MagicMock()
    mock.put_object.return_value = True
    mock.signed_public_url.return_value = "https://example.com/test.png"
    return mock


@pytest.fixture
def mock_langfuse():
    """Mock Langfuse tracing."""
    mock = MagicMock()
    mock.id = "test-trace-id"
    mock.span.return_value.__enter__ = MagicMock()
    mock.span.return_value.__exit__ = MagicMock()
    mock.flush = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    test_env = {
        "TESTING": "true",
        "OPENROUTER_API_KEY": "test-key",
        "REDIS_URL": "redis://localhost:6379/1",
        "QDRANT_URL": "http://localhost:6333",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": "/tmp/test-storage",
        "SERVICE_BASE_URL": "http://localhost:8000",
        "LOG_LEVEL": "DEBUG"
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup
    for key in test_env.keys():
        os.environ.pop(key, None)


@pytest.fixture
def sample_render_request():
    """Sample render request for testing."""
    return {
        "project_id": "test-project",
        "prompts": {
            "task": "create",
            "instruction": "Create a modern banner design",
            "references": []
        },
        "outputs": {
            "count": 1,
            "format": "png",
            "dimensions": "1200x630"
        },
        "constraints": {
            "palette_hex": ["#1E3A8A", "#FFFFFF"],
            "fonts": ["Inter"],
            "logo_safe_zone_pct": 25.0
        }
    }


@pytest.fixture
def sample_ingest_request():
    """Sample ingest request for testing."""
    return {
        "project_id": "test-project",
        "assets": ["https://example.com/brand-guide.pdf"]
    }


@pytest.fixture
def sample_canon_derive_request():
    """Sample canon derive request for testing."""
    return {
        "project_id": "test-project",
        "evidence_ids": ["evidence-1", "evidence-2"]
    }


@pytest.fixture
def sample_critique_request():
    """Sample critique request for testing."""
    return {
        "project_id": "test-project",
        "asset_ids": ["asset-1", "asset-2"]
    }
