# Smart Graphic Designer API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [Request/Response Examples](#requestresponse-examples)
6. [Error Handling](#error-handling)
7. [Rate Limits](#rate-limits)
8. [Cost Structure](#cost-structure)
9. [WebSocket Support](#websocket-support)
10. [SDK and Client Libraries](#sdk-and-client-libraries)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

## Overview

The Smart Graphic Designer API is a comprehensive AI-powered design generation service that creates professional graphics based on text prompts, brand constraints, and reference materials. Built with FastAPI, it integrates state-of-the-art AI models via OpenRouter to deliver high-quality design assets at scale.

### Key Features

- **🎨 AI-Powered Generation**: Uses Gemini 2.5 Flash Image and other advanced models
- **🎯 Brand Compliance**: Enforces color palettes, typography, and logo safe zones
- **📸 Multiple Formats**: Supports PNG, JPG, and WebP outputs
- **✅ Quality Assurance**: Built-in guardrails and validation systems
- **⚡ Real-time Updates**: WebSocket support for progress tracking
- **📊 Comprehensive Audit**: Full traceability and cost tracking
- **🔒 Enterprise Security**: JWT authentication, rate limiting, content filtering

### Architecture

```
Client Application
        ↓
Kong API Gateway (Auth, Rate Limiting)
        ↓
FastAPI Application
        ↓
┌─────────────┬─────────────┬─────────────┐
│  OpenRouter │    Redis    │   Qdrant    │
│ (AI Models) │  (Caching)  │  (Vectors)  │
└─────────────┴─────────────┴─────────────┘
        ↓
Cloudflare R2 Storage + CDN
```

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenRouter API key
- JWT token (obtained from your authentication provider)

### Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd NanoDesigner
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start Dependencies**
   ```bash
   docker compose up -d redis qdrant postgres langfuse
   ```

3. **Run the API**
   ```bash
   cd api
   poetry install
   poetry run uvicorn app.main:app --reload
   ```

4. **Test the API**
   ```bash
   curl -X POST "http://localhost:8000/render" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
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
     }'
   ```

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API authentication key | - |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse observability public key | - |
| `LANGFUSE_SECRET_KEY` | No | Langfuse observability secret key | - |
| `REDIS_URL` | Yes | Redis connection string | `redis://redis:6379/0` |
| `QDRANT_URL` | Yes | Qdrant vector database URL | `http://qdrant:6333` |
| `R2_ACCESS_KEY_ID` | Yes* | Cloudflare R2 access key | - |
| `R2_SECRET_ACCESS_KEY` | Yes* | Cloudflare R2 secret key | - |
| `R2_BUCKET` | Yes* | Cloudflare R2 bucket name | `assets` |
| `SERVICE_BASE_URL` | No | Base URL for the service | `http://localhost:8000` |

*Required for production; use MinIO for local development

## Authentication

The API uses JWT (JSON Web Tokens) for authentication, validated through Kong API Gateway.

### JWT Token Requirements

Your JWT token must include the following claims:
- `sub`: User ID
- `org_id`: Organization ID
- `roles`: Array of user roles
- `exp`: Expiration timestamp

### Making Authenticated Requests

Include the JWT token in the Authorization header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
     "https://api.example.com/render"
```

### Authentication Errors

- `401 Unauthorized`: Invalid or expired token
- `403 Forbidden`: Valid token but insufficient permissions

## API Endpoints

### Core Endpoints

#### POST /render
Generate graphic designs using AI.

**Request Body:**
```json
{
  "project_id": "string",
  "prompts": {
    "task": "create|edit|variations",
    "instruction": "string (5-2000 chars)",
    "references": ["https://..."] // Optional, max 8 URLs
  },
  "outputs": {
    "count": 1-6,
    "format": "png|jpg|webp",
    "dimensions": "WIDTHxHEIGHT"
  },
  "constraints": { // Optional
    "palette_hex": ["#RRGGBB", ...], // Max 12 colors
    "fonts": ["Font Name", ...], // Max 6 fonts
    "logo_safe_zone_pct": 0-40 // Percentage
  }
}
```

**Response:**
```json
{
  "assets": [
    {
      "url": "https://cdn.example.com/signed-url",
      "r2_key": "storage/path/file.png",
      "synthid": {
        "present": true,
        "payload": ""
      }
    }
  ],
  "audit": {
    "trace_id": "trace_abc123",
    "model_route": "openrouter/gemini-2.5-flash-image",
    "cost_usd": 0.05,
    "guardrails_ok": true
  }
}
```

#### POST /ingest
Upload and process documents for brand canon extraction.

**Request Body:**
```json
{
  "project_id": "string",
  "assets": ["asset_id_1", "asset_id_2"] // Max 50 items
}
```

#### POST /canon/derive
Extract brand guidelines from processed documents.

**Request Body:**
```json
{
  "project_id": "string",
  "evidence_ids": ["evidence_1", "evidence_2"]
}
```

#### POST /critique
Analyze generated designs against brand guidelines.

**Request Body:**
```json
{
  "project_id": "string",
  "asset_ids": ["asset_1", "asset_2"]
}
```

### Utility Endpoints

#### GET /healthz
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "dependencies": {
    "redis": "connected",
    "qdrant": "connected",
    "storage": "available"
  }
}
```

#### GET /metrics
Prometheus metrics for monitoring.

**Response:** Plain text metrics in Prometheus format.

## Request/Response Examples

### Simple Banner Creation

**Request:**
```bash
curl -X POST "https://api.example.com/render" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "social-media-campaign",
    "prompts": {
      "task": "create",
      "instruction": "Create a modern social media banner for tech startup"
    },
    "outputs": {
      "count": 2,
      "format": "png",
      "dimensions": "1200x630"
    }
  }'
```

**Response:**
```json
{
  "assets": [
    {
      "url": "https://cdn.example.com/assets/banner-1.png?expires=1640995200",
      "r2_key": "public/social-media-campaign/banner-1.png",
      "synthid": {"present": true, "payload": ""}
    },
    {
      "url": "https://cdn.example.com/assets/banner-2.png?expires=1640995200", 
      "r2_key": "public/social-media-campaign/banner-2.png",
      "synthid": {"present": true, "payload": ""}
    }
  ],
  "audit": {
    "trace_id": "trace_abc123def456",
    "model_route": "openrouter/gemini-2.5-flash-image",
    "cost_usd": 0.08,
    "guardrails_ok": true
  }
}
```

### Brand-Constrained Design

**Request:**
```bash
curl -X POST "https://api.example.com/render" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "corporate-materials",
    "prompts": {
      "task": "create",
      "instruction": "Design a professional business card",
      "references": ["https://example.com/logo.png"]
    },
    "outputs": {
      "count": 3,
      "format": "png", 
      "dimensions": "1050x600"
    },
    "constraints": {
      "palette_hex": ["#1E3A8A", "#FFFFFF", "#F59E0B"],
      "fonts": ["Helvetica", "Arial"],
      "logo_safe_zone_pct": 25.0
    }
  }'
```

### Design Variations

**Request:**
```json
{
  "project_id": "logo-variations",
  "prompts": {
    "task": "variations",
    "instruction": "Create 4 variations of this logo with different color schemes",
    "references": ["https://example.com/original-logo.svg"]
  },
  "outputs": {
    "count": 4,
    "format": "png",
    "dimensions": "512x512"
  }
}
```

## Error Handling

The API uses structured error responses with specific error types for better client handling.

### Error Response Format

```json
{
  "error": "ErrorType",
  "message": "Human readable message",
  "field": "specific_field", // For validation errors
  "details": {
    // Additional error context
  }
}
```

### Common Error Types

#### 400 Bad Request - Content Policy Violations
```json
{
  "error": "ContentPolicyViolationException",
  "message": "Content policy violation: banned_term",
  "violation_type": "banned_term",
  "details": "Instruction contains banned term: violence"
}
```

#### 422 Unprocessable Entity - Validation Errors
```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "validation_errors": [
    {
      "field": "prompts.instruction",
      "message": "String too short (minimum 5 characters)",
      "value": "Hi"
    }
  ]
}
```

#### 422 - Guardrails Validation Failure
```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "guardrails": [
    "['goal']: String too short",
    "['ops']: Invalid operation type",
    "['safety', 'respect_logo_safe_zone']: Required field missing"
  ]
}
```

#### 429 Too Many Requests
```json
{
  "error": "RateLimitExceeded",
  "message": "API rate limit exceeded",
  "retry_after_seconds": 60,
  "limit": 100,
  "window": "per minute"
}
```

#### 502 Bad Gateway - AI Service Issues
```json
{
  "error": "OpenRouterException", 
  "message": "Model service temporarily unavailable",
  "model": "gemini-2.5-flash-image",
  "status_code": 503,
  "retry_after_seconds": 300
}
```

### Error Handling Best Practices

1. **Always check the error type** for programmatic handling
2. **Implement exponential backoff** for 429 and 5xx errors
3. **Log error details** for debugging and monitoring
4. **Show user-friendly messages** based on error types
5. **Retry transient failures** (5xx errors, timeouts)

## Rate Limits

### Standard Limits

| Endpoint | Rate Limit | Burst Capacity |
|----------|------------|----------------|
| `/render` | 100 req/min | 30 requests |
| `/healthz` | 1000 req/min | 100 requests |
| `/metrics` | 500 req/min | 50 requests |
| All endpoints | 1000 req/min | 150 requests |

### Rate Limit Headers

The API includes rate limit information in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

### Handling Rate Limits

```python
import time
import requests

def make_request_with_backoff(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited, waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

## Cost Structure

### Pricing by Operation Type

| Operation Type | Estimated Cost | Notes |
|----------------|----------------|--------|
| Simple Design (1 image) | $0.02 - $0.05 | Basic layouts, minimal processing |
| Complex Design (1 image) | $0.05 - $0.10 | Advanced features, style transfer |
| Bulk Generation (6 images) | $0.15 - $0.30 | Multiple variations |
| Design Variations (4 images) | $0.10 - $0.20 | Based on existing design |

### Cost Factors

- **Model Selection**: Premium models cost more
- **Image Complexity**: Detailed prompts increase cost
- **Output Resolution**: Higher resolution costs more
- **Generation Count**: Linear cost scaling
- **Processing Time**: Longer operations cost more

### Cost Monitoring

Every response includes actual cost in the audit section:

```json
{
  "audit": {
    "cost_usd": 0.05,
    "model_route": "openrouter/gemini-2.5-flash-image"
  }
}
```

### Budget Controls

Set daily/monthly budget limits via environment variables:
```bash
DAILY_BUDGET_USD=100
MONTHLY_BUDGET_USD=2000
BUDGET_ALERT_THRESHOLD=0.8  # Alert at 80%
```

## WebSocket Support

### Real-time Job Updates

Connect to WebSocket endpoints for real-time progress updates:

```javascript
const ws = new WebSocket(`wss://api.example.com/ws/jobs/${jobId}`);

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Job update:', update);
  
  switch(update.status) {
    case 'queued':
      showStatus('Request queued...');
      break;
    case 'processing':
      showProgress(update.progress || 0);
      break;
    case 'preview_ready':
      showPreview(update.preview_url);
      break;
    case 'completed':
      showResult(update.assets);
      break;
    case 'failed':
      showError(update.error);
      break;
  }
};
```

### WebSocket Endpoints

#### `/ws/jobs/{job_id}`
Real-time updates for specific render jobs.

**Message Format:**
```json
{
  "job_id": "job_123",
  "status": "processing|completed|failed",
  "progress": 0-100,
  "message": "Status description",
  "assets": [...], // Present when completed
  "error": "Error details" // Present when failed
}
```

#### `/ws/health`
Health monitoring WebSocket for system status.

## SDK and Client Libraries

### Official SDKs

- **Python SDK**: `pip install sgd-api-python`
- **JavaScript SDK**: `npm install @sgd/api-client`
- **Go SDK**: `go get github.com/sgd/api-go`

### Python SDK Example

```python
from sgd_api import SGDClient, RenderRequest

client = SGDClient(
    base_url="https://api.example.com",
    jwt_token="your-jwt-token"
)

request = RenderRequest(
    project_id="my-project",
    instruction="Create a banner",
    count=2,
    format="png",
    dimensions="1200x630"
)

# Synchronous call
response = client.render(request)
print(f"Generated {len(response.assets)} assets")

# Async call with progress tracking
async for update in client.render_async(request):
    if update.status == "completed":
        print(f"Assets ready: {update.assets}")
```

### JavaScript SDK Example

```javascript
import { SGDClient } from '@sgd/api-client';

const client = new SGDClient({
  baseUrl: 'https://api.example.com',
  jwtToken: 'your-jwt-token'
});

// Promise-based
const response = await client.render({
  projectId: 'my-project',
  prompts: {
    task: 'create',
    instruction: 'Create a banner'
  },
  outputs: {
    count: 2,
    format: 'png',
    dimensions: '1200x630'
  }
});

// With progress tracking
client.renderWithProgress(request, (update) => {
  console.log(`Progress: ${update.progress}%`);
}).then(result => {
  console.log('Generation complete:', result.assets);
});
```

## Best Practices

### Request Optimization

1. **Use Appropriate Dimensions**
   ```json
   {
     "dimensions": "1200x630" // Good for social media
     // Avoid: "4000x4000" unless necessary (higher cost)
   }
   ```

2. **Optimize Instruction Length**
   ```json
   {
     "instruction": "Modern tech banner with blue theme" // Clear and concise
     // Avoid overly verbose instructions that increase cost
   }
   ```

3. **Leverage Caching**
   - Similar requests are automatically cached for 1 hour
   - Identical prompts + constraints return cached results
   - Use consistent project_id for better cache hits

4. **Batch Related Requests**
   ```json
   {
     "outputs": {"count": 4}, // Better than 4 separate requests
     "instruction": "Create variations with different layouts"
   }
   ```

### Error Handling Patterns

```python
import time
from typing import Optional

def robust_render_request(client, request, max_retries=3) -> Optional[dict]:
    """Make a render request with comprehensive error handling."""
    
    for attempt in range(max_retries):
        try:
            response = client.render(request)
            return response
            
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after or (2 ** attempt)
                time.sleep(wait_time)
                continue
            raise
            
        except ValidationError as e:
            # Don't retry validation errors
            print(f"Request validation failed: {e.details}")
            return None
            
        except ServiceUnavailableError as e:
            if attempt < max_retries - 1:
                # Exponential backoff for service issues
                time.sleep(2 ** attempt)
                continue
            raise
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise
            
    return None
```

### Performance Guidelines

1. **Monitor Response Times**
   - Simple designs: < 15 seconds
   - Complex designs: < 30 seconds
   - Bulk generation: < 60 seconds

2. **Implement Timeouts**
   ```python
   response = client.render(request, timeout=60)
   ```

3. **Use Async Where Possible**
   - Render operations are I/O bound
   - Async clients provide better throughput
   - WebSocket updates prevent polling

4. **Cache Assets Locally**
   - Download and cache generated assets
   - Use CDN URLs efficiently (they expire)
   - Implement local fallback for repeated access

### Security Considerations

1. **Protect JWT Tokens**
   - Store tokens securely (not in client-side code)
   - Implement token refresh logic
   - Use environment variables for tokens

2. **Validate User Input**
   ```python
   # Sanitize prompts before sending
   clean_instruction = sanitize_user_input(user_prompt)
   
   # Validate file references
   if not is_valid_url(reference_url):
       raise ValueError("Invalid reference URL")
   ```

3. **Content Filtering**
   - API includes built-in content filtering
   - Additional client-side validation recommended
   - Monitor for policy violations in responses

4. **Rate Limiting**
   - Implement client-side rate limiting
   - Use exponential backoff for retries
   - Monitor usage patterns

## Troubleshooting

### Common Issues

#### 1. "Authentication Failed" (401)
**Symptoms:** All requests return 401 Unauthorized

**Solutions:**
- Verify JWT token is valid and not expired
- Check token format (should start with "Bearer ")
- Ensure token includes required claims (sub, org_id, roles)
- Test token with `/healthz` endpoint first

#### 2. "Rate Limit Exceeded" (429)
**Symptoms:** Requests fail with 429 after working initially

**Solutions:**
- Implement exponential backoff with retry logic
- Check rate limit headers to understand limits
- Consider request batching to reduce frequency
- Upgrade to higher tier for increased limits

#### 3. "Generation Timeout" (502/503)
**Symptoms:** Requests timeout during AI generation

**Solutions:**
- Reduce complexity in prompts
- Lower image resolution/count
- Implement longer client timeouts (60-120 seconds)
- Use WebSocket for progress updates instead of polling

#### 4. "Validation Error" (422)
**Symptoms:** Request rejected with validation details

**Solutions:**
- Check all required fields are present
- Verify data types (strings, numbers, arrays)
- Ensure dimensions follow "WIDTHxHEIGHT" format
- Validate hex colors have proper format (#RRGGBB)

#### 5. "High Costs"
**Symptoms:** API usage costs higher than expected

**Solutions:**
- Use simpler prompts for basic designs
- Reduce output resolution when possible
- Leverage caching by using consistent inputs
- Monitor cost_usd in responses to understand patterns

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
sgd_logger = logging.getLogger('sgd_api')
sgd_logger.setLevel(logging.DEBUG)

# This will log all requests/responses for debugging
response = client.render(request)
```

### Health Monitoring

Monitor API health programmatically:

```python
def check_api_health():
    try:
        response = requests.get("https://api.example.com/healthz", timeout=10)
        health = response.json()
        
        if health["status"] != "healthy":
            alert("API unhealthy", health)
            
        # Check individual dependencies
        for service, status in health["dependencies"].items():
            if status != "connected" and status != "available":
                alert(f"Service {service} unhealthy", status)
                
    except Exception as e:
        alert("API health check failed", str(e))
```

### Contact Support

For additional help:
- **Documentation**: https://docs.example.com/sgd-api
- **Status Page**: https://status.example.com  
- **Support Email**: support@example.com
- **Community Forum**: https://community.example.com
- **GitHub Issues**: https://github.com/example/sgd-api/issues

---

*Last updated: January 2024*
*API Version: 1.0.0*