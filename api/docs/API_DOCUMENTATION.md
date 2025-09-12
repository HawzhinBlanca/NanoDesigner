# NanoDesigner API Documentation

## Overview

NanoDesigner is a production-ready AI-powered design generation platform built with FastAPI, featuring comprehensive monitoring, error handling, and observability.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.nanodesigner.com`

## Authentication

All API requests require authentication via JWT tokens in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Rate Limiting

- **Default**: 100 requests per minute per API key
- **Burst**: 30 requests per 10 seconds
- Rate limit headers are included in responses:
  - `X-RateLimit-Limit`: Request limit per window
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Time when window resets

## Core Endpoints

### Generate Images

**POST** `/render`

Generate AI-powered design images based on prompts and constraints.

#### Request Body

```json
{
  "project_id": "string",
  "prompts": {
    "task": "create | edit | variations",
    "instruction": "Design description (min 5 chars)",
    "references": ["url1", "url2"]  // Optional, max 8
  },
  "outputs": {
    "count": 1,  // 1-6 images
    "dimensions": "1024x1024",  // Format: WIDTHxHEIGHT
    "format": "png | jpg | webp"
  },
  "constraints": {  // Optional
    "palette_hex": ["#FF0000", "#00FF00"],  // Max 12 colors
    "fonts": ["Arial", "Helvetica"],  // Max 6 fonts
    "logo_safe_zone_pct": 10  // 0-40%
  }
}
```

#### Response

```json
{
  "assets": [
    {
      "url": "https://cdn.example.com/signed-url",
      "r2_key": "project/renders/uuid.png",
      "synthid": {
        "present": false,
        "payload": null
      }
    }
  ],
  "audit": {
    "trace_id": "trace_abc123",
    "model_route": "openrouter/gemini-2.5-flash-image",
    "cost_usd": 0.05,
    "guardrails_ok": true,
    "plan": {
      "goal": "Create professional logo design",
      "steps": ["analysis", "generation", "refinement"],
      "safety_checks": ["content_policy", "brand_canon"]
    }
  }
}
```

#### Error Codes

- **422**: Validation error (invalid request format)
- **429**: Rate limit exceeded
- **502**: External service error (OpenRouter/Gemini)
- **503**: Service unavailable

### Async Rendering

**POST** `/render/async`

Submit render job for asynchronous processing (for large batches).

Returns immediately with job ID. Use WebSocket or polling to get results.

### Health Monitoring

**GET** `/monitoring/health`

Comprehensive system health check.

#### Response

```json
{
  "status": "healthy | degraded | unhealthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "redis": {
      "status": "healthy",
      "checked_at": "2024-01-01T00:00:00Z"
    },
    "database": {
      "status": "healthy", 
      "checked_at": "2024-01-01T00:00:00Z"
    },
    "openrouter": {
      "status": "healthy",
      "checked_at": "2024-01-01T00:00:00Z"
    },
    "storage": {
      "status": "healthy",
      "checked_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

### System Metrics

**GET** `/monitoring/metrics`

Get system performance and business metrics.

#### Query Parameters

- `hours` (integer): Hours of metrics to return (1-24, default: 1)

#### Response

```json
{
  "performance": {
    "request_count": 1000,
    "avg_response_time": 0.850,
    "p95_response_time": 1.200,
    "error_rate": 0.5,
    "status_codes": {
      "200": 950,
      "422": 30,
      "500": 20
    }
  },
  "business": {
    "renders_total": 1000,
    "renders_success": 980,
    "renders_failure": 20,
    "revenue_total": 500.00,
    "users_signup": 50
  },
  "system": {
    "uptime_hours": 720,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 25.5,
    "disk_usage_percent": 45.2
  }
}
```

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Human readable error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "trace_id": "trace_abc123",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Invalid request format |
| `CONTENT_POLICY_VIOLATION` | 422 | Content violates policies |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `BUDGET_EXCEEDED` | 422 | Organization budget limit hit |
| `EXTERNAL_SERVICE_ERROR` | 502 | OpenRouter/AI service error |
| `STORAGE_ERROR` | 503 | File storage service error |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

## WebSocket API

**WebSocket** `/ws/render/{project_id}`

Real-time updates for render jobs.

### Message Types

#### Job Status Updates
```json
{
  "type": "job_status",
  "job_id": "job_abc123",
  "status": "queued | processing | completed | failed",
  "progress": 75,
  "eta_seconds": 30
}
```

#### Render Completed
```json
{
  "type": "render_completed",
  "job_id": "job_abc123", 
  "assets": [...],  // Same format as /render response
  "audit": {...}
}
```

## SDK Examples

### Python

```python
import httpx

class NanoDesignerClient:
    def __init__(self, api_key: str, base_url: str = "https://api.nanodesigner.com"):
        self.session = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    def render(self, project_id: str, instruction: str, **kwargs):
        response = self.session.post("/render", json={
            "project_id": project_id,
            "prompts": {
                "task": "create",
                "instruction": instruction
            },
            "outputs": {
                "count": 1,
                "dimensions": "1024x1024", 
                "format": "png"
            },
            **kwargs
        })
        response.raise_for_status()
        return response.json()

# Usage
client = NanoDesignerClient("your-api-key")
result = client.render("project-1", "Create a modern logo design")
```

### JavaScript/TypeScript

```typescript
interface RenderRequest {
  project_id: string;
  prompts: {
    task: 'create' | 'edit' | 'variations';
    instruction: string;
    references?: string[];
  };
  outputs: {
    count: number;
    dimensions: string;
    format: 'png' | 'jpg' | 'webp';
  };
  constraints?: {
    palette_hex?: string[];
    fonts?: string[];
    logo_safe_zone_pct?: number;
  };
}

class NanoDesignerClient {
  constructor(private apiKey: string, private baseUrl = 'https://api.nanodesigner.com') {}
  
  async render(request: RenderRequest) {
    const response = await fetch(`${this.baseUrl}/render`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      throw new Error(`Render failed: ${response.statusText}`);
    }
    
    return response.json();
  }
}

// Usage
const client = new NanoDesignerClient('your-api-key');
const result = await client.render({
  project_id: 'project-1',
  prompts: {
    task: 'create',
    instruction: 'Create a modern logo design'
  },
  outputs: {
    count: 1,
    dimensions: '1024x1024',
    format: 'png'
  }
});
```

## Production Considerations

### Performance

- **Response Times**: 
  - p95 < 2 seconds (excluding AI generation time)
  - p99 < 5 seconds
- **Throughput**: Up to 1000 concurrent requests
- **Caching**: Redis-based caching for plans and embeddings

### Reliability

- **Uptime SLA**: 99.9%
- **Error Budget**: < 0.1% error rate
- **Failover**: Automatic fallback to secondary AI models
- **Retries**: Automatic retry with exponential backoff

### Monitoring

- **Real User Monitoring (RUM)**: Frontend performance tracking
- **APM**: Application performance monitoring 
- **Alerting**: Proactive alerts for degraded performance
- **Dashboards**: Real-time system health and business metrics

### Security

- **Content Filtering**: NSFW and policy violation detection
- **Rate Limiting**: Per-user and per-organization limits
- **Input Validation**: Comprehensive request sanitization
- **Audit Logging**: Full audit trail for compliance

## Support

- **Documentation**: https://docs.nanodesigner.com
- **Status Page**: https://status.nanodesigner.com  
- **API Support**: api-support@nanodesigner.com
- **Emergency**: For production issues, contact support with "URGENT" in subject