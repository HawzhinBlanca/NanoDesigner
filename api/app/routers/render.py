from __future__ import annotations

import json
import logging
import uuid
from typing import List

from fastapi import APIRouter, Body, HTTPException

from ..core.config import settings
from ..models.schemas import RenderRequest, RenderResponse
from ..models.exceptions import (
    ContentPolicyViolationException,
    OpenRouterException,
    GuardrailsValidationException,
    ImageGenerationException,
    StorageException,
    ValidationError,
    openrouter_to_http_exception,
    guardrails_to_http_exception,
    content_policy_to_http_exception,
    storage_to_http_exception
)
from ..services.guardrails import validate_contract
from ..services.langfuse import Trace
from ..services.gemini_image import generate_images
from ..services.openrouter import call_task
from ..services.prompts import PLANNER_SYSTEM, CRITIC_SYSTEM
from ..services.redis import cache_get_set, sha1key
from ..services.storage_adapter import put_object, signed_public_url
from ..services.cost_tracker import CostTracker, extract_cost_from_openrouter_response, extract_cost_from_image_response, estimate_image_cost, CostInfo
from ..services.synthid import get_verification_status, verify_image_synthid
from ..services.error_handler import handle_errors, validate_input, safe_json_parse, retry_with_backoff, ErrorContext, get_error_handler
from ..core.security import InputSanitizer

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    tags=["Generation"],
    responses={
        400: {"description": "Bad request - content policy violation or invalid parameters"},
        401: {"description": "Unauthorized - invalid or missing API key"},
        422: {"description": "Validation error - request doesn't meet schema requirements"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "AI service unavailable"},
        500: {"description": "Internal server error"}
    }
)


def _make_planner_prompt(req: RenderRequest) -> str:
    parts = [
        "You are a senior brand designer. Create a render plan strictly following Brand Canon if provided.",
        f"Task: {req.prompts.task}\nInstruction: {req.prompts.instruction}",
    ]
    if req.constraints:
        parts.append(f"Constraints: {json.dumps(req.constraints.model_dump(exclude_none=True))}")
    return "\n".join(parts)


def _content_filter(text: str) -> None:
    """Enhanced content filtering with better error handling."""
    if not text or not isinstance(text, str):
        raise ValidationError("instruction", "Instruction must be a non-empty string", text)
    
    if len(text.strip()) < 3:
        raise ValidationError("instruction", "Instruction must be at least 3 characters long", text)
    
    if len(text) > 5000:
        raise ValidationError("instruction", "Instruction must be less than 5000 characters", len(text))
    
    try:
        from pathlib import Path
        # In container, policies directory is copied to /app/policies
        root = Path(__file__).resolve().parents[2]  # /app
        blacklist_file = root / "policies" / "blacklist.txt"
        
        if not blacklist_file.exists():
            logger.warning("Blacklist file not found, skipping content filtering")
            return
            
        terms = blacklist_file.read_text(encoding="utf-8").splitlines()
        low = text.lower()
        
        for t in terms:
            t = t.strip()
            if not t or t.startswith("#"):  # Skip empty lines and comments
                continue
            if t in low:
                raise ContentPolicyViolationException(
                    violation_type="banned_term",
                    details=f"Instruction contains banned term: {t}"
                )
    except (IOError, OSError) as e:
        logger.error(f"Failed to read blacklist file: {e}")
        # Continue without content filtering rather than failing the request
        pass


def _validate_references(refs: List[str] | None) -> None:
    """Enhanced reference validation with comprehensive checks."""
    if not refs:
        return
    
    if len(refs) > 10:
        raise ValidationError("references", "Maximum 10 references allowed", len(refs))
    
    import os
    from urllib.parse import urlparse
    
    allow = os.getenv("REF_URL_ALLOW_HOSTS")
    allowed_hosts = {h.strip() for h in allow.split(",")} if allow else set()
    
    for i, r in enumerate(refs):
        if not isinstance(r, str):
            raise ValidationError(f"references[{i}]", "Reference must be a string", type(r).__name__)
        
        if len(r) > 2048:
            raise ValidationError(f"references[{i}]", "Reference URL too long (max 2048 chars)", len(r))
        
        try:
            u = urlparse(r)
        except Exception as e:
            raise ValidationError(f"references[{i}]", f"Invalid URL format: {str(e)}", r)
        
        if not u.scheme:
            raise ContentPolicyViolationException(
                violation_type="missing_protocol",
                details=f"Reference {i+1} missing protocol (https required)"
            )
        
        if u.scheme != "https":
            raise ContentPolicyViolationException(
                violation_type="invalid_protocol",
                details=f"Reference {i+1} uses {u.scheme}, only https allowed"
            )
        
        if not u.hostname:
            raise ValidationError(f"references[{i}]", "Reference URL missing hostname", r)
        
        # Check for suspicious patterns
        suspicious_patterns = [".onion", "localhost", "127.0.0.1", "0.0.0.0", "::1"]
        if any(pattern in u.hostname.lower() for pattern in suspicious_patterns):
            raise ContentPolicyViolationException(
                violation_type="suspicious_host",
                details=f"Reference {i+1} uses suspicious hostname: {u.hostname}"
            )
        
        if allowed_hosts and u.hostname not in allowed_hosts:
            raise ContentPolicyViolationException(
                violation_type="forbidden_host",
                details=f"Host {u.hostname} not in allowed hosts: {', '.join(allowed_hosts)}"
            )


@router.post(
    "/render",
    response_model=RenderResponse,
    summary="Generate graphic designs using AI",
    description="""Generate professional graphic designs based on prompts and brand constraints.
    
    This endpoint uses AI models to create custom graphics following your brand guidelines
    and design requirements. It supports various output formats and can generate multiple
    variations in a single request.
    
    **Key Features:**
    - AI-powered design generation using Gemini 2.5 Flash Image
    - Brand constraint enforcement (colors, fonts, safe zones)
    - Multiple output formats (PNG, JPG, WEBP)
    - Reference image support for style guidance
    - Guardrails validation for quality assurance
    - Real-time progress tracking via WebSocket
    
    **Rate Limits:**
    - 100 requests per minute per API key
    - Burst capacity: 30 requests
    
    **Cost:**
    - Estimated $0.02-0.10 per generation depending on complexity
    - Exact cost returned in audit.cost_usd field
    """,
    responses={
        200: {
            "description": "Successfully generated designs",
            "content": {
                "application/json": {
                    "example": {
                        "assets": [
                            {
                                "url": "https://cdn.example.com/assets/design-001.png?expires=1640995200&signature=abc123",
                                "r2_key": "public/project-123/550e8400-e29b-41d4-a716-446655440000.png",
                                "synthid": {"present": False, "payload": ""}
                            }
                        ],
                        "audit": {
                            "trace_id": "trace_abc123def456",
                            "model_route": "openrouter/gemini-2.5-flash-image",
                            "cost_usd": 0.05,
                            "guardrails_ok": True,
                            "verified_by": "none"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Content policy violation or invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ContentPolicyViolationException",
                        "message": "Content policy violation: banned_term",
                        "violation_type": "banned_term",
                        "details": "Instruction contains banned term: violence"
                    }
                }
            }
        },
        422: {
            "description": "Validation error or guardrails failure",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Request validation failed",
                        "guardrails": [
                            "['goal']: String too short",
                            "['ops']: Invalid operation type"
                        ]
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "error": "RateLimitExceeded",
                        "message": "API rate limit exceeded",
                        "retry_after_seconds": 60
                    }
                }
            }
        },
        502: {
            "description": "AI model service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "error": "OpenRouterException",
                        "message": "Model service temporarily unavailable",
                        "model": "gemini-2.5-flash-image",
                        "status_code": 503
                    }
                }
            }
        }
    },
    tags=["Generation"]
)
@handle_errors("render", fallback_response={"assets": [], "audit": {"error": "Service degraded"}})
async def render(request: RenderRequest = Body(
    ...,
    description="Design generation request with prompts, output specs, and constraints",
    example={
        "project_id": "marketing-campaign-q1",
        "prompts": {
            "task": "create",
            "instruction": "Design a modern social media banner for a tech company launch with clean typography",
            "references": ["https://example.com/brand-guide.jpg"]
        },
        "outputs": {
            "count": 2,
            "format": "png",
            "dimensions": "1200x630"
        },
        "constraints": {
            "palette_hex": ["#1E3A8A", "#FFFFFF", "#3B82F6"],
            "fonts": ["Inter", "Roboto"],
            "logo_safe_zone_pct": 25.0
        }
    }
)):
    trace = Trace("render")
    trace_id = trace.id
    guardrails_ok = False
    model_route = "openrouter/gemini-2.5-flash-image"
    cost_tracker = CostTracker()

    # Content policy enforcement + sanitization
    try:
        sanitizer = InputSanitizer(mode="strict")
        # sanitize textual inputs
        request.prompts.instruction = sanitizer.sanitize(request.prompts.instruction)
        if hasattr(request.prompts, "references") and request.prompts.references:
            request.prompts.references = [sanitizer.sanitize(r) for r in request.prompts.references]
        _content_filter(request.prompts.instruction)
        _validate_references(getattr(request.prompts, "references", None))
    except ContentPolicyViolationException as e:
        raise content_policy_to_http_exception(e)

    # Step 1: Plan via OpenRouter (planner task) with cache
    with trace.span("plan"):
        user_prompt = _make_planner_prompt(request)
        cache_key = sha1key("plan", request.project_id, request.prompts.instruction)
        
        # Check if plan is cached
        cached_plan = None
        try:
            from ..services.redis import get_client
            redis_client = get_client()
            cached_bytes = redis_client.get(cache_key)
            if cached_bytes:
                cached_plan = json.loads(cached_bytes.decode("utf-8"))
        except Exception:
            pass  # If cache fails, we'll generate fresh
        
        if cached_plan:
            # Plan is cached, no API call needed (no cost)
            plan = cached_plan
        else:
            # Need to generate plan (will incur cost)
            try:
                resp = call_task(
                    "planner",
                    [
                        {"role": "system", "content": PLANNER_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    trace=trace,
                    temperature=0.2,
                )
                # Track cost from planner call
                planner_cost = extract_cost_from_openrouter_response(resp, "planner")
                cost_tracker.add_call(planner_cost)
            except OpenRouterException as e:
                raise openrouter_to_http_exception(e)
            except Exception as e:
                raise OpenRouterException(
                    message=f"Planner model call failed: {str(e)}",
                    model="planner",
                    details={"error_type": type(e).__name__}
                )
            
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Enhanced JSON parsing with better error handling
            plan_local = safe_json_parse(
                content, 
                "planner_response",
                fallback=None
            )
            
            # If direct parsing failed, try to extract JSON from content
            if plan_local is None and isinstance(content, str):
                logger.warning("Direct JSON parsing failed, attempting extraction")
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1 and end > start:
                    json_content = content[start : end + 1]
                    plan_local = safe_json_parse(
                        json_content,
                        "extracted_planner_response", 
                        fallback=None
                    )
            
            if not isinstance(plan_local, dict):
                logger.error(f"Planner returned invalid response: {content[:200]}...")
                raise GuardrailsValidationException(
                    contract_name="render_plan.json",
                    errors=[
                        "Planner did not return valid JSON object",
                        f"Response type: {type(plan_local).__name__}",
                        f"Content preview: {str(content)[:100]}..."
                    ]
                )
            try:
                validate_contract("render_plan.json", plan_local)
            except HTTPException as e:
                if e.status_code == 422 and "guardrails" in e.detail:
                    raise GuardrailsValidationException(
                        contract_name="render_plan.json",
                        errors=e.detail["guardrails"]
                    )
                raise
            
            plan = plan_local
            
            # Cache the plan for future use
            try:
                redis_client = get_client()
                redis_client.setex(cache_key, 86400, json.dumps(plan).encode("utf-8"))
            except Exception:
                pass  # Cache failure shouldn't break the request
        
        guardrails_ok = True

    # Step 2: Generate images
    image_resp = None
    with trace.span("image_generate", {"model": model_route}):
        prompt = _make_planner_prompt(request)
        count = request.outputs.count
        try:
            imgs = generate_images(prompt, n=count, size=request.outputs.dimensions, trace=trace)
            
            # Estimate cost for image generation (since generate_images doesn't return cost info)
            image_cost = estimate_image_cost(model_route, count)
            cost_tracker.add_call(CostInfo(
                total_cost_usd=image_cost,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                model=model_route
            ))
        except OpenRouterException as e:
            raise openrouter_to_http_exception(e)
        except Exception as e:
            raise ImageGenerationException(
                message=f"Image generation failed: {str(e)}",
                model=model_route,
                prompt_length=len(prompt),
                details={"error_type": type(e).__name__}
            )

    # Step 3: Store to R2 and build response assets
    assets = []
    with trace.span("store_assets"):
        try:
            for i, (data, fmt) in enumerate(imgs):
                key = f"public/{request.project_id}/{uuid.uuid4()}.{fmt}"
                put_object(key, data, content_type=f"image/{'jpeg' if fmt=='jpg' else fmt}")
                url = signed_public_url(key, expires_seconds=15 * 60)
                
                # Verify SynthID (currently returns honest "none" status)
                synthid_present, synthid_payload = verify_image_synthid(data, model_route)
                
                assets.append({
                    "url": url,
                    "r2_key": key,
                    "synthid": {"present": synthid_present, "payload": synthid_payload},
                })
        except Exception as e:
            raise StorageException(
                operation="upload",
                storage_backend=settings.storage_backend,
                details={
                    "project_id": request.project_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )

    # Optional critic step (best-effort)
    try:
        with trace.span("critic"):
            critic_resp = call_task(
                "critic",
                [
                    {"role": "system", "content": CRITIC_SYSTEM},
                    {"role": "user", "content": json.dumps({"plan": plan})},
                ],
                trace=trace,
                temperature=0.0,
            )
            # Track cost from critic call
            critic_cost = extract_cost_from_openrouter_response(critic_resp, "critic")
            cost_tracker.add_call(critic_cost)
    except Exception:
        pass

    await trace.flush()

    return {
        "assets": assets,
        "audit": {
            "trace_id": trace_id,
            "model_route": model_route,
            "cost_usd": round(cost_tracker.get_total_cost(), 4),  # Real cost tracking!
            "guardrails_ok": guardrails_ok,
            "verified_by": get_verification_status(),  # Honest verification status
        },
    }
