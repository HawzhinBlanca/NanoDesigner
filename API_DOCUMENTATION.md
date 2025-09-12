# Smart Graphic Designer API Documentation

## Overview

The Smart Graphic Designer API provides AI-powered graphic design capabilities with brand consistency enforcement. Built with FastAPI and powered by OpenRouter, it offers comprehensive endpoints for design generation, brand canon management, and quality assurance.

## Base URL

```
Production: https://api.yourdomain.com
Development: http://localhost:8000
```

## Authentication

All API endpoints (except health checks) require JWT authentication. Include the bearer token in the Authorization header:

```http
Authorization: Bearer YOUR_JWT_TOKEN
```

## Rate Limiting

- **Default:** 100 requests per minute per API key
- **Burst:** 30 requests
- **Headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Request Headers

| Header | Description | Required |
|--------|-------------|----------|
| `Authorization` | Bearer token for authentication | Yes |
| `X-Request-ID` | Unique request identifier for tracing | No (auto-generated) |
| `X-Idempotency-Key` | Prevent duplicate processing | No (recommended for POST) |

## Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Request identifier for tracking |
| `X-Process-Time` | Processing time in milliseconds |
| `X-RateLimit-*` | Rate limiting information |

## Endpoints

### 1. Health Checks

#### GET /health
Basic health check for load balancers.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "service": "sgd-api",
  "environment": "production",
  "version": "1.0.0"
}
```

#### GET /health/detailed
Comprehensive health check with all dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "uptime_seconds": 3600,
  "dependencies": {
    "redis": {
      "status": "healthy",
      "latency_ms": 1.5
    },
    "postgres": {
      "status": "healthy",
      "latency_ms": 2.3
    },
    "qdrant": {
      "status": "healthy",
      "collections": 3
    },
    "openrouter": {
      "status": "healthy",
      "available_models": 50
    }
  },
  "system": {
    "cpu_percent": 45.2,
    "memory": {
      "used_percent": 62.5,
      "available_gb": 8.2
    }
  }
}
```

### 2. Design Generation

#### POST /render
Generate designs based on prompts and brand constraints.

**Request Body:**
```json
{
  "project_id": "project-123",
  "prompts": {
    "task": "create",
    "instruction": "Professional banner for tech conference",
    "references": ["s3://bucket/reference1.png"]
  },
  "outputs": {
    "count": 3,
    "format": "png",
    "dimensions": "1920x1080"
  },
  "constraints": {
    "palette_hex": ["#4770A3", "#F7B500"],
    "fonts": ["Verdana", "Inter"],
    "logo_safe_zone_pct": 10
  }
}
```

**Response:**
```json
{
  "assets": [
    {
      "url": "https://cdn.example.com/signed-url",
      "r2_key": "assets/project-123/render-456.png",
      "synthid": {
        "present": true,
        "payload": "watermark-data"
      }
    }
  ],
  "audit": {
    "trace_id": "trace-789",
    "model_route": "google/gemini-2.0-flash",
    "cost_usd": 0.05,
    "guardrails_ok": true,
    "verified_by": "synthid"
  }
}
```

### 3. Asset Ingestion

#### POST /ingest/file
Upload and process brand assets (multipart/form-data).

**Form Data:**
- `file`: Binary file data
- `project_id`: Project identifier

**Response:**
```json
{
  "document_id": "doc-123",
  "processed": true,
  "extracted": {
    "colors": 5,
    "fonts": 2,
    "logos": 1
  }
}
```

#### POST /ingest
Process assets from URLs.

**Request Body:**
```json
{
  "project_id": "project-123",
  "assets": [
    "https://example.com/brand-guide.pdf",
    "https://example.com/logo.svg"
  ]
}
```

**Response:**
```json
{
  "processed": 2,
  "qdrant_ids": ["vec-123", "vec-456"]
}
```

### 4. Brand Canon Management

#### POST /canon/derive
Derive brand canon from ingested assets.

**Request Body:**
```json
{
  "project_id": "project-123",
  "evidence_ids": ["doc-123", "doc-456"],
  "merge_strategy": "overlay"
}
```

**Response:**
```json
{
  "palette_hex": ["#4770A3", "#F7B500"],
  "fonts": ["Verdana", "Noto Sans"],
  "voice": {
    "tone": "professional, authoritative",
    "dos": ["Use clear language"],
    "donts": ["Avoid jargon"]
  }
}
```

#### GET /canon/{project_id}
Retrieve brand canon for a project.

**Response:**
```json
{
  "project_id": "project-123",
  "canon": {
    "palette_hex": ["#4770A3", "#F7B500"],
    "fonts": ["Verdana"],
    "logo_elements": {
      "minimum_sizes": {
        "print": "20mm",
        "digital": "80px"
      }
    }
  },
  "last_updated": "2024-01-01T00:00:00Z"
}
```

### 5. Quality Assurance

#### POST /critique
Evaluate designs against brand guidelines.

**Request Body:**
```json
{
  "project_id": "project-123",
  "asset_ids": ["asset-123", "asset-456"]
}
```

**Response:**
```json
{
  "score": 0.85,
  "violations": [
    "Font size below minimum",
    "Logo clear space violated"
  ],
  "repair_suggestions": [
    "Increase header font to 24px",
    "Add 20px padding around logo"
  ]
}
```

### 6. Metrics

#### GET /metrics/json
Get application metrics in JSON format.

**Response:**
```json
{
  "uptime_seconds": 3600,
  "total_requests": 1000,
  "error_rate": 0.02,
  "average_response_time_ms": 250,
  "active_connections": 15
}
```

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "dimensions",
      "issue": "Must be in format WIDTHxHEIGHT"
    },
    "request_id": "req-123",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Invalid request parameters |
| `AUTHENTICATION_ERROR` | 401 | Missing or invalid token |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_ERROR` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## WebSocket Endpoint

### WS /ws/render/{project_id}
Real-time design generation with progress updates.

**Connection:**
```javascript
const ws = new WebSocket('wss://api.yourdomain.com/ws/render/project-123');
```

**Messages:**
```json
// Client -> Server
{
  "type": "render_request",
  "data": { /* same as /render request */ }
}

// Server -> Client
{
  "type": "progress",
  "data": {
    "stage": "planning",
    "progress": 0.25,
    "message": "Creating design plan..."
  }
}

// Server -> Client (final)
{
  "type": "complete",
  "data": { /* same as /render response */ }
}
```

## SDKs and Examples

### cURL
```bash
curl -X POST https://api.yourdomain.com/render \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test",
    "prompts": {
      "task": "create",
      "instruction": "Modern logo"
    },
    "outputs": {
      "count": 1,
      "format": "png",
      "dimensions": "512x512"
    }
  }'
```

### Python
```python
import requests

response = requests.post(
    "https://api.yourdomain.com/render",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "project_id": "test",
        "prompts": {"task": "create", "instruction": "Modern logo"},
        "outputs": {"count": 1, "format": "png", "dimensions": "512x512"}
    }
)
```

### JavaScript
```javascript
const response = await fetch('https://api.yourdomain.com/render', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    project_id: 'test',
    prompts: { task: 'create', instruction: 'Modern logo' },
    outputs: { count: 1, format: 'png', dimensions: '512x512' }
  })
});
```

## Best Practices

1. **Idempotency:** Use `X-Idempotency-Key` for critical operations
2. **Pagination:** Use `limit` and `offset` parameters for list endpoints
3. **Caching:** Respect `Cache-Control` headers
4. **Retries:** Implement exponential backoff for 5xx errors
5. **Monitoring:** Track `X-Request-ID` for debugging

## Support

- **Documentation:** https://docs.yourdomain.com
- **Status Page:** https://status.yourdomain.com
- **Support Email:** support@yourdomain.com
- **API Keys:** https://dashboard.yourdomain.com/api-keys