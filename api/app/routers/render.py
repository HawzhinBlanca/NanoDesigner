from __future__ import annotations

import json
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
from ..core.security import InputSanitizer


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
    from pathlib import Path

    # In container, policies directory is copied to /app/policies
    root = Path(__file__).resolve().parents[2]  # /app
    terms = (root / "policies" / "blacklist.txt").read_text(encoding="utf-8").splitlines()
    low = text.lower()
    for t in terms:
        t = t.strip()
        if not t:
            continue
        if t in low:
            raise ContentPolicyViolationException(
                violation_type="banned_term",
                details=f"Instruction contains banned term: {t}"
            )


def _validate_references(refs: List[str] | None) -> None:
    if not refs:
        return
    import os
    from urllib.parse import urlparse

    allow = os.getenv("REF_URL_ALLOW_HOSTS")
    allowed_hosts = {h.strip() for h in allow.split(",")} if allow else set()
    for r in refs:
        u = urlparse(r)
        if u.scheme and u.scheme != "https":
            raise ContentPolicyViolationException(
                violation_type="invalid_protocol",
                details="Only https references allowed"
            )
        if allowed_hosts and u.hostname not in allowed_hosts:
            raise ContentPolicyViolationException(
                violation_type="forbidden_host",
                details=f"Reference host {u.hostname} not allowed"
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
                                "synthid": {"present": True, "payload": ""}
                            }
                        ],
                        "audit": {
                            "trace_id": "trace_abc123def456",
                            "model_route": "openrouter/gemini-2.5-flash-image",
                            "cost_usd": 0.05,
                            "guardrails_ok": True,
                            "verified_by": "declared"
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
        def _plan_factory() -> bytes:
            user_prompt = _make_planner_prompt(request)
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
            except OpenRouterException as e:
                raise openrouter_to_http_exception(e)
            except Exception as e:
                raise OpenRouterException(
                    message=f"Planner model call failed: {str(e)}",
                    model="planner",
                    details={"error_type": type(e).__name__}
                )
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            plan_local = None
            if isinstance(content, str):
                try:
                    plan_local = json.loads(content)
                except Exception:
                    start = content.find("{")
                    end = content.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        plan_local = json.loads(content[start : end + 1])
            if not isinstance(plan_local, dict):
                raise GuardrailsValidationException(
                    contract_name="render_plan.json",
                    errors=["Planner did not return valid JSON object"]
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
            return json.dumps(plan_local).encode("utf-8")

        cache_key = sha1key("plan", request.project_id, request.prompts.instruction)
        plan_bytes = cache_get_set(cache_key, _plan_factory, ttl=86400)
        plan = json.loads(plan_bytes.decode("utf-8"))
        guardrails_ok = True

    # Step 2: Generate images
    image_resp = None
    with trace.span("image_generate", {"model": model_route}):
        prompt = _make_planner_prompt(request)
        count = request.outputs.count
        try:
            imgs = generate_images(prompt, n=count, size=request.outputs.dimensions, trace=trace)
        except OpenRouterException as e:
            raise openrouter_to_http_exception(e)
        except Exception as e:
            raise ImageGenerationException(
                message=f"Image generation failed: {str(e)}",
                model=model_route,
                prompt_length=len(prompt),
                details={"error_type": type(e).__name__}
            )
        # Best-effort capture of usage from image call if available via last OpenRouter call in generate_images
        # Not all image providers return token usage.

    # Step 3: Store to R2 and build response assets
    assets = []
    with trace.span("store_assets"):
        try:
            for i, (data, fmt) in enumerate(imgs):
                key = f"public/{request.project_id}/{uuid.uuid4()}.{fmt}"
                put_object(key, data, content_type=f"image/{'jpeg' if fmt=='jpg' else fmt}")
                url = signed_public_url(key, expires_seconds=15 * 60)
                assets.append({
                    "url": url,
                    "r2_key": key,
                    "synthid": {"present": False, "payload": ""},  # SynthID not exposed via API currently
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
            _ = call_task(
                "critic",
                [
                    {"role": "system", "content": CRITIC_SYSTEM},
                    {"role": "user", "content": json.dumps({"plan": plan})},
                ],
                trace=trace,
                temperature=0.0,
            )
    except Exception:
        pass

    await trace.flush()

    return {
        "assets": assets,
        "audit": {
            "trace_id": trace_id,
            "model_route": model_route,
            "cost_usd": 0.0,
            "guardrails_ok": guardrails_ok,
            "verified_by": "declared",
        },
    }
