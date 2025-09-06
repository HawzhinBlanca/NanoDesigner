"""OpenRouter API client for AI model integration.

This module provides a robust client for interacting with the OpenRouter API,
which serves as a unified gateway to multiple AI models including GPT, Claude,
Gemini, and others. It includes retry logic, error handling, and observability.

Key Features:
- Unified API for multiple AI providers
- Automatic retry with exponential backoff
- Policy-based model routing and fallbacks
- Comprehensive error handling and logging
- Cost tracking and usage monitoring
- Langfuse integration for observability

Example:
    ```python
    from app.services.openrouter import call_task
    from app.services.langfuse import Trace
    
    trace = Trace("design_generation")
    response = call_task(
        task="planner",
        messages=[
            {"role": "system", "content": "You are a design expert"},
            {"role": "user", "content": "Create a banner design"}
        ],
        trace=trace
    )
    ```

Configuration:
    Set the OPENROUTER_API_KEY environment variable with your API key.
    Model routing policies are defined in policies/openrouter_policy.json.

See Also:
    - OpenRouter API documentation: https://openrouter.ai/docs
    - policies/openrouter_policy.json: Model routing configuration
    - services/langfuse.py: Observability and tracing
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from ..core.config import settings
from .langfuse import Trace
from .openrouter_policy import load_policy


def _headers() -> Dict[str, str]:
    """Generate HTTP headers for OpenRouter API requests.
    
    Creates the necessary headers including authentication, referer,
    and service identification for OpenRouter API calls.
    
    Returns:
        Dict[str, str]: Dictionary of HTTP headers for API requests.
        
    Note:
        The OPENROUTER_API_KEY environment variable must be set.
        The HTTP-Referer and X-Title headers are required by OpenRouter
        for request attribution and monitoring.
    """
    return {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}",
        "HTTP-Referer": "https://yourapp",
        "X-Title": settings.service_name,
        "Content-Type": "application/json",
    }


def call_openrouter(model: str, messages: List[dict], timeout: float = 30.0, **kw) -> dict:
    """Make a direct call to the OpenRouter chat completions API.
    
    This function provides a low-level interface to the OpenRouter API for
    chat completions. For most use cases, prefer call_task() which includes
    policy routing, retries, and fallbacks.
    
    Args:
        model (str): The model identifier (e.g., "openrouter/gpt-4").
        messages (List[dict]): List of message objects with 'role' and 'content'.
        timeout (float, optional): Request timeout in seconds. Defaults to 30.0.
        **kw: Additional parameters to pass to the API (temperature, max_tokens, etc.).
        
    Returns:
        dict: The API response containing choices, usage, and metadata.
        
    Raises:
        RuntimeError: If the API request fails with HTTP error details.
        
    Example:
        ```python
        response = call_openrouter(
            model="openrouter/gpt-4",
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello!"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        ```
        
    Note:
        This function does not include retry logic or fallbacks.
        Use call_task() for production code with error handling.
    """
    with httpx.Client(timeout=timeout) as client:
        try:
            r = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=_headers(),
                json={"model": model, "messages": messages, **kw},
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:  # type: ignore[name-defined]
            status = e.response.status_code if e.response is not None else "?"
            body = e.response.text[:800] if e.response is not None else ""
            raise RuntimeError(f"OpenRouter error {status}: {body}")


def call_openrouter_images(model: str, prompt: str, n: int = 1, size: str = "1024x1024", timeout: float = 60.0, **kw) -> dict:
    """Generate images using OpenRouter's image generation API.
    
    This function calls the OpenRouter Images API which provides access to
    various image generation models including DALL-E, Midjourney, Stable
    Diffusion, and Gemini Image.
    
    Args:
        model (str): Image generation model (e.g., "openrouter/gemini-2.5-flash-image").
        prompt (str): Text description of the image to generate.
        n (int, optional): Number of images to generate (1-6). Defaults to 1.
        size (str, optional): Image dimensions (e.g., "1024x1024"). Defaults to "1024x1024".
        timeout (float, optional): Request timeout in seconds. Defaults to 60.0.
        **kw: Additional model-specific parameters.
        
    Returns:
        dict: API response with generated image data in base64 format.
        
    Raises:
        httpx.HTTPStatusError: If the API request fails.
        
    Example:
        ```python
        response = call_openrouter_images(
            model="openrouter/gemini-2.5-flash-image",
            prompt="A modern tech startup banner with blue colors",
            n=2,
            size="1200x630"
        )
        
        # Extract image data
        for img_data in response["data"]:
            b64_image = img_data["b64_json"]
            # Process base64 image data...
        ```
        
    Note:
        - Image generation typically takes 10-60 seconds depending on complexity
        - Generated images are returned as base64-encoded data
        - Different models support different sizes and parameters
        - Check model documentation for supported sizes and features
    """
    """Call OpenRouter Images API, which many providers (including Gemini image) support via a unified endpoint.

    Returns provider-specific JSON; typical shape aligns with OpenAI Images API: { "data": [ { "b64_json": "..." } ] }
    """
    payload = {"model": model, "prompt": prompt, "n": n, "size": size}
    payload.update(kw)
    with httpx.Client(timeout=timeout) as client:
        r = client.post(
            "https://openrouter.ai/api/v1/images",
            headers=_headers(),
            json=payload,
        )
        r.raise_for_status()
        return r.json()


def _retry_conf():
    pol = load_policy()
    conf = pol.retry_conf()
    return stop_after_attempt(conf.get("max_attempts", 2)), wait_fixed(conf.get("backoff_ms", 400) / 1000.0)


def _extract_message_text(resp: dict) -> str:
    """Extract text content from OpenRouter API response.
    
    Handles different response formats from various AI models, including
    simple string content and complex structured responses with multiple
    content types (text, images, etc.).
    
    Args:
        resp (dict): The raw API response from OpenRouter.
        
    Returns:
        str: Extracted text content, or empty string if no text found.
        
    Example:
        ```python
        # Simple text response
        response = {
            "choices": [{
                "message": {"content": "Hello world!"}
            }]
        }
        text = _extract_message_text(response)  # "Hello world!"
        
        # Structured response with multiple content types
        response = {
            "choices": [{
                "message": {
                    "content": [
                        {"text": "First part"},
                        {"text": "Second part"},
                        {"type": "image", "url": "..."}
                    ]
                }
            }]
        }
        text = _extract_message_text(response)  # "First part\nSecond part"
        ```
        
    Note:
        This function is used internally to normalize responses from different
        AI models that may return content in various formats.
    """
    choices = resp.get("choices", [])
    if not choices:
        return ""
    msg = choices[0].get("message", {})
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Concatenate text parts
        texts = [p.get("text", "") for p in content if isinstance(p, dict)]
        return "\n".join([t for t in texts if t])
    return ""


def call_task(task: str, messages: List[dict], trace: Optional[Trace] = None, **kw) -> dict:
    """Execute an AI task using policy-based model routing and fallbacks.
    
    This is the primary function for making AI model calls in the application.
    It uses the policy configuration to determine the best model for each task,
    implements automatic retries and fallbacks, and provides comprehensive
    error handling and observability.
    
    Args:
        task (str): The task type (e.g., "planner", "critic", "draft", "image").
        messages (List[dict]): List of chat messages with 'role' and 'content'.
        trace (Optional[Trace]): Langfuse trace for observability. Defaults to None.
        **kw: Additional parameters passed to the underlying API call.
        
    Returns:
        dict: The successful API response from the primary or fallback model.
        
    Raises:
        Exception: If all models (primary + fallbacks) fail to complete the request.
        
    Example:
        ```python
        from app.services.langfuse import Trace
        
        trace = Trace("content_planning")
        
        response = call_task(
            task="planner",
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": user_request}
            ],
            trace=trace,
            temperature=0.3,
            max_tokens=1000
        )
        
        plan_content = response["choices"][0]["message"]["content"]
        ```
        
    Policy Configuration:
        Task routing is configured in policies/openrouter_policy.json:
        ```json
        {
            "tasks": {
                "planner": {
                    "primary": "openrouter/gpt-4",
                    "fallbacks": ["openrouter/claude-3-sonnet"],
                    "max_cost_usd": 0.02
                },
                "image": {
                    "primary": "openrouter/gemini-2.5-flash-image",
                    "max_cost_usd": 0.10
                }
            }
        }
        ```
        
    Error Handling:
        - Automatic retry with exponential backoff for transient failures
        - Fallback to alternative models if primary model fails
        - Comprehensive error logging with model and task context
        - Cost tracking and budget enforcement
        
    Observability:
        - Request/response timing and token usage tracking
        - Model performance metrics via Langfuse
        - Error categorization and alerting
        - Cost attribution by task and model
    """
    pol = load_policy()
    model = pol.model_for(task)
    fallbacks = pol.fallbacks_for(task)
    stop, wait = _retry_conf()
    timeout_ms = pol.timeout_ms_for("image" if task == "image" else "default")

    @retry(stop=stop, wait=wait)
    def _do(model_name: str) -> dict:
        with (trace.span(f"openrouter:{task}", {"model": model_name}) if trace else _null_span()):
            resp = call_openrouter(model_name, messages, timeout=timeout_ms / 1000.0, **kw)
            return resp

    try:
        return _do(model)
    except Exception:
        for fb in fallbacks:
            try:
                return _do(fb)
            except Exception:
                continue
        raise


class _null_span:
    """Null object pattern for tracing spans.
    
    Provides a no-op context manager that can be used when no
    Langfuse trace is available, avoiding conditional logic in
    the calling code.
    
    Example:
        ```python
        # With this null span, this code works whether trace is None or not
        with (trace.span("operation") if trace else _null_span()):
            # Perform operation
            pass
        ```
    """
    
    def __enter__(self):
        """Enter the context manager (no-op)."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Exit the context manager (no-op)."""
        return False
