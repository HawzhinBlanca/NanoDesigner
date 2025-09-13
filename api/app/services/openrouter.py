"""OpenRouter API integration with health checks."""

import httpx
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _headers() -> Dict[str, str]:
    """Build standard OpenRouter headers (test-friendly)."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    referer = os.getenv("SERVICE_BASE_URL", "http://localhost:8000")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": referer,
        "X-Title": "NanoDesigner",
    }

def _extract_message_text(response: Dict[str, Any]) -> str:
    """Extract text content from an OpenRouter-style response."""
    try:
        choices = response.get("choices", [])
        if not choices:
            return ""
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
            return "\n".join([p for p in parts if p])
        return ""
    except Exception:
        return ""

async def health_check() -> bool:
    """Check OpenRouter API health."""
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("OpenRouter API key not configured")
            return False
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://nanodesigner.app",
                    "X-Title": "NanoDesigner"
                },
                timeout=10.0
            )
            
            return response.status_code == 200
            
    except Exception as e:
        logger.error(f"OpenRouter health check failed: {e}")
        return False

def call_openrouter(messages: list, model: str | None = None, **kwargs) -> Dict[str, Any]:
    """Sync OpenRouter call (unit-test friendly: uses httpx.Client)."""
    import httpx
    from ..core.config import settings
    
    headers = _headers()
    payload = {
        "model": model or kwargs.get("model") or "openai/gpt-4o",
        "messages": messages,
        "max_tokens": kwargs.get("max_tokens", 1000),
        "temperature": kwargs.get("temperature", 0.7),
    }
    
    # Use configured timeout with proper minimum
    timeout = max(settings.openrouter_timeout, settings.min_timeout_seconds, 30.0)
    
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"OpenRouter error {e.response.status_code}")

def call_openrouter_images(prompt: str, **kwargs) -> Dict[str, Any]:
    """Sync OpenRouter images call (unit-test friendly)."""
    import httpx
    headers = _headers()
    model = kwargs.get("model", "google/gemini-2.5-flash-image-preview")
    payload = {
        "model": model,
        "prompt": prompt,
        "n": kwargs.get("n", 1),
        "size": kwargs.get("size", "1024x1024"),
    }
    try:
        with httpx.Client(timeout=30.0) as client:  # Increased timeout for image generation
            resp = client.post(
                "https://openrouter.ai/api/v1/images",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            
            # Check if response has content
            content = resp.text
            if not content or content.strip() == "":
                raise RuntimeError(f"Empty response from OpenRouter Images API")
            
            try:
                return resp.json()
            except ValueError as e:
                # Log the actual response content for debugging
                raise RuntimeError(f"Invalid JSON response from OpenRouter Images API: {e}. Content: {content[:500]}")
                
    except httpx.HTTPStatusError as e:
        error_text = e.response.text if hasattr(e.response, 'text') else str(e)
        raise RuntimeError(f"OpenRouter Images API HTTP error {e.response.status_code}: {error_text}")
    except httpx.TimeoutException:
        raise RuntimeError("OpenRouter Images API request timed out")
    except Exception as e:
        raise RuntimeError(f"OpenRouter Images API request failed: {str(e)}")

def load_policy():  # minimal policy used by tests (can be patched)
    class _P:
        def model_for(self, task):
            return "openai/gpt-4o"
        def fallbacks_for(self, task):
            return []
        def timeout_ms_for(self, task):
            return 20000
        def retry_conf(self):
            return {"max_attempts": 2, "backoff_ms": 400}
    return _P()

def call_task(task: str | None = None, messages: list | None = None, trace=None, **kwargs) -> Dict[str, Any]:
    """Sync task call for unit tests using call_openrouter and policy.

    Accepts `task` (preferred) or `task_type` (legacy) as the task name.
    If `trace` is provided, creates a span 'openrouter:{task}'.
    """
    task_name = task or kwargs.pop("task_type", None) or "planner"
    if messages is None:
        messages = []
    policy = load_policy()
    model = policy.model_for(task_name)
    def _do_call(selected_model: str) -> Dict[str, Any]:
        if trace is not None and hasattr(trace, "span"):
            with trace.span(f"openrouter:{task_name}", {"model": selected_model}):
                return call_openrouter(messages, model=selected_model, **kwargs)
        return call_openrouter(messages, model=selected_model, **kwargs)
    try:
        return _do_call(model)
    except Exception:
        fallbacks = policy.fallbacks_for(task_name) or []
        if fallbacks:
            return _do_call(fallbacks[0])
        raise

async def async_call_task(task_type: str, messages: list, **kwargs) -> Dict[str, Any]:
    """Async call for runtime - uses httpx.AsyncClient and raises OpenRouterException."""
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    # Resolve model via policy file
    import json
    from pathlib import Path
    # Resolve policy path relative to repo root or from env override
    policy_env = os.getenv("OPENROUTER_POLICY_PATH")
    if policy_env:
        policy_path = Path(policy_env)
    else:
        # This file lives at repo_root/api/app/services/openrouter.py
        # repo_root is parents[2]
        policy_path = Path(__file__).resolve().parents[2] / "policies" / "openrouter_policy.json"
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            policy = json.load(f)
    except Exception:
        # Fallback minimal policy if file missing or unreadable
        policy = {
            "tasks": {
                "planner": {"primary": "openrouter/gpt-5", "fallbacks": ["openrouter/claude-4.1"]},
                "critic": {"primary": "openrouter/claude-4.1", "fallbacks": ["openrouter/gpt-5"]},
                "image": {"primary": "google/gemini-2.5-flash-image-preview", "fallbacks": []},
            },
            "timeouts_ms": {"default": 30000, "image": 45000},
            "retry": {"max_attempts": 2, "backoff_ms": 400},
        }
    task_cfg = (policy.get("tasks", {}) or {}).get(task_type) or {}
    primary_model = task_cfg.get("primary")
    fallbacks = task_cfg.get("fallbacks", [])
    timeouts_ms = policy.get("timeouts_ms", {})
    retry_conf = policy.get("retry", {"max_attempts": 2, "backoff_ms": 400})
    max_attempts = int(retry_conf.get("max_attempts", 2))
    backoff_ms = int(retry_conf.get("backoff_ms", 400))
    # Determine timeout per task
    from ..core.config import settings
    default_timeout_ms = settings.openrouter_timeout * 1000
    
    # Use task-specific or default timeout
    task_timeout_ms = int(timeouts_ms.get(task_type, timeouts_ms.get("default", default_timeout_ms)))
    
    # Special handling for image tasks which typically take longer
    if task_type == "image":
        task_timeout_ms = max(task_timeout_ms, settings.openrouter_timeout_long * 1000)
    # Use configured minimum timeout for production safety
    timeout_seconds = max(settings.min_timeout_seconds, task_timeout_ms / 1000.0)
    
    # Final model (explicit override wins)
    # Only remove "openrouter/" prefix if present - OpenRouter doesn't expect it
    # But keep other prefixes like "google/" or "openai/"
    model = kwargs.get("model", primary_model or "openai/gpt-4o")
    logger.info(f"async_call_task: task_type={task_type}, model from kwargs/policy={model}")
    if model and model.startswith("openrouter/"):
        model = model.replace("openrouter/", "")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://nanodesigner.app",
        "X-Title": "NanoDesigner"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": kwargs.get("max_tokens", 1000),
        "temperature": kwargs.get("temperature", 0.7),
        **{k: v for k, v in kwargs.items() if k not in ["model", "max_tokens", "temperature", "trace"]}
    }
    
    from ..core.circuit_breaker import get_openrouter_breaker
    from ..models.exceptions import OpenRouterException
    from ..services.cost_tracker import extract_cost_from_openrouter_response as _extract_cost

    # Clean up model names - remove "openrouter/" prefix from all models
    models_to_try = [model] + [m.replace("openrouter/", "") if m and m.startswith("openrouter/") else m for m in fallbacks if m]
    last_err: Exception | None = None
    # Optional OpenTelemetry tracer
    tracer = None
    try:
        from opentelemetry import trace as _trace  # type: ignore
        tracer = _trace.get_tracer("app.services.openrouter")
    except Exception:
        tracer = None

    for candidate in models_to_try:
        attempt = 0
        while attempt < max_attempts:
            try:
                async def _do_request():
                    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                        request_payload = {**payload, "model": candidate}
                        # Log minimal info without prompt contents unless explicitly enabled
                        import json, os
                        if os.getenv("OPENROUTER_DEBUG") == "1":
                            safe_payload = {**request_payload, "messages": "[redacted]"}
                            logger.debug(f"OpenRouter request payload: {json.dumps(safe_payload, default=str)[:500]}")
                        else:
                            logger.debug(f"OpenRouter request: task={task_type}, model={candidate}")
                        return await client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers=headers,
                            json=request_payload
                        )
                breaker = get_openrouter_breaker()
                if tracer is not None:
                    with tracer.start_as_current_span(
                        f"openrouter.{task_type}",
                        attributes={
                            "ai.model": candidate,
                            "ai.provider": "openrouter",
                            "ai.task": task_type,
                            "retry.attempt": attempt + 1,
                        },
                    ):
                        response = await breaker.call(_do_request)
                else:
                    response = await breaker.call(_do_request)
                if response.status_code != 200:
                    raise OpenRouterException(message=f"OpenRouter API request failed: {response.status_code}", model=candidate, details={"task": task_type})
                result = response.json()
                # Enforce max cost if provided
                max_cost = float(task_cfg.get("max_cost_usd")) if task_cfg.get("max_cost_usd") is not None else None
                if max_cost is not None:
                    try:
                        cost_info = _extract_cost(result, candidate)
                        if cost_info.total_cost_usd and cost_info.total_cost_usd > max_cost:
                            raise OpenRouterException(message=f"Cost {cost_info.total_cost_usd} exceeds max {max_cost}", model=candidate, details={"task": task_type})
                    except Exception:
                        # If cost cannot be extracted, proceed (policy best-effort)
                        pass
                logger.info(f"OpenRouter API call successful for {task_type} using {candidate}")
                return result
            except httpx.TimeoutException as te:
                last_err = te
                attempt += 1
                # backoff
                await _async_sleep(backoff_ms * attempt)
            except Exception as e:
                last_err = e
                attempt += 1
                await _async_sleep(backoff_ms * attempt)
        # try next fallback
    # Exhausted all models/attempts
    msg = str(last_err) if last_err else "OpenRouter request failed"
    raise OpenRouterException(message=msg, model=model, details={"task": task_type})


async def _async_sleep(ms: int) -> None:
    import asyncio
    await asyncio.sleep(max(0.0, ms / 1000.0))
