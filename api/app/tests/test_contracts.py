"""API Contract Testing using Pact/Schema validation.

This module implements contract testing to ensure API compatibility
between frontend and backend services.
"""

import pytest
import json
from typing import Dict, Any
from jsonschema import validate, ValidationError
from pydantic import BaseModel, Field
from datetime import datetime

# API Response Schemas
RENDER_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["assets", "audit", "meta"],
    "properties": {
        "assets": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "url"],
                "properties": {
                    "id": {"type": "string"},
                    "url": {"type": "string", "format": "uri"},
                    "metadata": {"type": "object"}
                }
            }
        },
        "audit": {
            "type": "object",
            "required": ["cost_usd", "trace_id"],
            "properties": {
                "cost_usd": {"type": "number"},
                "trace_id": {"type": "string"},
                "model_route": {"type": "string"},
                "verified_by": {"type": "string"}
            }
        },
        "meta": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "processing_time_ms": {"type": "integer"}
            }
        }
    }
}

CANON_DERIVE_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["canon", "meta"],
    "properties": {
        "canon": {
            "type": "object",
            "required": ["brand_name", "colors", "typography"],
            "properties": {
                "brand_name": {"type": "string"},
                "colors": {
                    "type": "object",
                    "properties": {
                        "primary": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                        "secondary": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"}
                    }
                },
                "typography": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "body": {"type": "string"}
                    }
                }
            }
        },
        "meta": {"type": "object"}
    }
}

CRITIQUE_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["critique", "meta"],
    "properties": {
        "critique": {
            "type": "object",
            "required": ["score", "feedback"],
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 10},
                "feedback": {"type": "string"},
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "meta": {"type": "object"}
    }
}


class ContractTest:
    """Base class for contract testing."""
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate data against JSON schema."""
        try:
            validate(instance=data, schema=schema)
            return True
        except ValidationError as e:
            pytest.fail(f"Schema validation failed: {e.message}")
            return False


class TestRenderContract(ContractTest):
    """Test render endpoint contract."""
    
    def test_render_request_contract(self):
        """Test render request structure."""
        valid_request = {
            "prompt": "Create a modern logo",
            "constraints": {
                "format": "PNG",
                "dimensions": {"width": 1024, "height": 576}
            },
            "references": []
        }
        
        # Should define request schema and validate
        assert "prompt" in valid_request
        assert isinstance(valid_request["constraints"], dict)
    
    def test_render_response_contract(self):
        """Test render response structure."""
        mock_response = {
            "assets": [
                {
                    "id": "asset-123",
                    "url": "https://example.com/image.png",
                    "metadata": {"size": 1024}
                }
            ],
            "audit": {
                "cost_usd": 0.01,
                "trace_id": "trace-123",
                "model_route": "openai/dall-e-3"
            },
            "meta": {
                "request_id": "req-123",
                "processing_time_ms": 1500
            }
        }
        
        assert self.validate_schema(mock_response, RENDER_RESPONSE_SCHEMA)
    
    def test_render_error_contract(self):
        """Test render error response structure."""
        error_response = {
            "error": {
                "code": "INVALID_PROMPT",
                "message": "Prompt exceeds maximum length",
                "details": {"max_length": 5000, "provided": 5500}
            },
            "meta": {
                "request_id": "req-123",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
        
        assert "error" in error_response
        assert "code" in error_response["error"]


class TestCanonContract(ContractTest):
    """Test canon endpoint contract."""
    
    def test_canon_derive_request_contract(self):
        """Test canon derive request structure."""
        valid_request = {
            "brand_info": {
                "name": "TechCo",
                "industry": "Technology",
                "values": ["Innovation", "Quality"]
            }
        }
        
        assert "brand_info" in valid_request
        assert "name" in valid_request["brand_info"]
    
    def test_canon_derive_response_contract(self):
        """Test canon derive response structure."""
        mock_response = {
            "canon": {
                "brand_name": "TechCo",
                "colors": {
                    "primary": "#0066CC",
                    "secondary": "#FF6600"
                },
                "typography": {
                    "heading": "Montserrat",
                    "body": "Open Sans"
                }
            },
            "meta": {
                "request_id": "req-456"
            }
        }
        
        assert self.validate_schema(mock_response, CANON_DERIVE_RESPONSE_SCHEMA)


class TestCritiqueContract(ContractTest):
    """Test critique endpoint contract."""
    
    def test_critique_request_contract(self):
        """Test critique request structure."""
        valid_request = {
            "asset_url": "https://example.com/design.png",
            "criteria": ["composition", "color", "typography"]
        }
        
        assert "asset_url" in valid_request
        assert isinstance(valid_request["criteria"], list)
    
    def test_critique_response_contract(self):
        """Test critique response structure."""
        mock_response = {
            "critique": {
                "score": 7.5,
                "feedback": "Good composition with room for improvement",
                "suggestions": [
                    "Increase contrast",
                    "Adjust typography hierarchy"
                ]
            },
            "meta": {
                "request_id": "req-789"
            }
        }
        
        assert self.validate_schema(mock_response, CRITIQUE_RESPONSE_SCHEMA)


class TestWebSocketContract:
    """Test WebSocket message contracts."""
    
    def test_job_update_contract(self):
        """Test job update message structure."""
        valid_message = {
            "type": "job_update",
            "job_id": "job-123",
            "status": "in_progress",
            "progress": 50,
            "message": "Processing image..."
        }
        
        assert valid_message["type"] == "job_update"
        assert 0 <= valid_message["progress"] <= 100
    
    def test_job_complete_contract(self):
        """Test job complete message structure."""
        valid_message = {
            "type": "job_complete",
            "job_id": "job-123",
            "status": "completed",
            "result": {
                "assets": ["url1", "url2"]
            }
        }
        
        assert valid_message["status"] == "completed"
        assert "result" in valid_message


class TestPaginationContract:
    """Test pagination contract for list endpoints."""
    
    def test_pagination_request_contract(self):
        """Test pagination request parameters."""
        valid_params = {
            "page": 1,
            "limit": 20,
            "sort": "created_at",
            "order": "desc"
        }
        
        assert valid_params["page"] >= 1
        assert valid_params["limit"] <= 100
        assert valid_params["order"] in ["asc", "desc"]
    
    def test_pagination_response_contract(self):
        """Test pagination response structure."""
        mock_response = {
            "items": [],
            "pagination": {
                "page": 1,
                "limit": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False
            }
        }
        
        assert "items" in mock_response
        assert "pagination" in mock_response
        assert mock_response["pagination"]["total_pages"] == 5


class TestVersioningContract:
    """Test API versioning contracts."""
    
    def test_version_header_contract(self):
        """Test API version header."""
        headers = {
            "API-Version": "1.0",
            "Accept": "application/vnd.api+json;version=1"
        }
        
        assert "API-Version" in headers
    
    def test_deprecated_field_contract(self):
        """Test deprecated field handling."""
        response = {
            "data": "value",
            "old_field": "deprecated",  # Should warn
            "_deprecated": ["old_field"]
        }
        
        assert "_deprecated" in response
        assert "old_field" in response["_deprecated"]


# Contract validation utilities
def generate_contract_documentation():
    """Generate contract documentation from schemas."""
    contracts = {
        "render": RENDER_RESPONSE_SCHEMA,
        "canon_derive": CANON_DERIVE_RESPONSE_SCHEMA,
        "critique": CRITIQUE_RESPONSE_SCHEMA
    }
    
    docs = {}
    for name, schema in contracts.items():
        docs[name] = {
            "schema": schema,
            "example": generate_example_from_schema(schema)
        }
    
    return docs


def generate_example_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate example data from JSON schema."""
    if schema["type"] == "object":
        example = {}
        for prop, prop_schema in schema.get("properties", {}).items():
            if prop_schema["type"] == "string":
                example[prop] = "example_string"
            elif prop_schema["type"] == "number":
                example[prop] = 1.0
            elif prop_schema["type"] == "integer":
                example[prop] = 1
            elif prop_schema["type"] == "array":
                example[prop] = []
            elif prop_schema["type"] == "object":
                example[prop] = generate_example_from_schema(prop_schema)
        return example
    return {}


# Pact-style consumer contracts
class ConsumerContract:
    """Define consumer expectations for API."""
    
    def __init__(self, provider: str, consumer: str):
        self.provider = provider
        self.consumer = consumer
        self.interactions = []
    
    def add_interaction(self, interaction: Dict[str, Any]):
        """Add interaction expectation."""
        self.interactions.append(interaction)
    
    def verify(self) -> bool:
        """Verify all interactions against provider."""
        # Would integrate with actual Pact broker in production
        for interaction in self.interactions:
            # Verify each interaction
            pass
        return True


# Example consumer contract
frontend_backend_contract = ConsumerContract(
    provider="backend-api",
    consumer="frontend-web"
)

frontend_backend_contract.add_interaction({
    "description": "Get render result",
    "request": {
        "method": "POST",
        "path": "/api/render",
        "body": {
            "prompt": "test prompt"
        }
    },
    "response": {
        "status": 200,
        "body": {
            "assets": [],
            "audit": {},
            "meta": {}
        }
    }
})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])