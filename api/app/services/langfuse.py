from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional, List

import httpx
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class Trace:
    """Enhanced Langfuse trace with comprehensive LLM call tracking."""
    
    def __init__(self, name: str):
        self.name = name
        self.id = str(uuid.uuid4())
        self.spans: list[dict] = []
        self.logs: list[dict] = []
        self.llm_calls: list[dict] = []
        self.total_cost_usd = 0.0
        self.total_tokens = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Add a log entry to the trace"""
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message
        })
    
    def log_llm_call(
        self,
        model: str,
        prompt: str,
        completion: str,
        latency_ms: int,
        cost_usd: float,
        prompt_tokens: int,
        completion_tokens: int,
        task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a complete LLM call with all required metrics."""
        # Hash prompt/completion to avoid logging raw PII
        import hashlib
        prompt_hash = hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()
        completion_hash = hashlib.sha256((completion or "").encode("utf-8")).hexdigest()
        llm_call = {
            "timestamp": time.time(),
            "model": model,
            "task": task,
            "prompt_hash": prompt_hash,
            "completion_hash": completion_hash,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "metadata": metadata or {}
        }
        
        self.llm_calls.append(llm_call)
        self.total_cost_usd += cost_usd
        self.total_tokens += llm_call["total_tokens"]
        
        logger.info(
            f"LLM call tracked: model={model}, task={task}, "
            f"cost=${cost_usd:.4f}, tokens={llm_call['total_tokens']}, "
            f"latency={latency_ms}ms"
        )

    @contextmanager
    def span(self, name: str, meta: Optional[Dict[str, Any]] = None):
        """Create a span for tracking operation timing and metadata."""
        start = time.time()
        span = {
            "name": name,
            "start": start,
            "meta": meta or {},
            "llm_calls": []  # Track LLM calls within this span
        }
        
        # Store reference to current span for LLM tracking
        current_span_index = len(self.spans)
        
        try:
            yield span
            span["status"] = "OK"
        except Exception as e:  # noqa: BLE001
            span["status"] = "ERROR"
            span["error"] = str(e)
            raise
        finally:
            span["end"] = time.time()
            span["duration_ms"] = int((span["end"] - start) * 1000)
            
            # Associate LLM calls made during this span
            if self.llm_calls:
                # Find calls made during this span's timeframe
                span_llm_calls = [
                    call for call in self.llm_calls
                    if start <= call["timestamp"] <= span["end"]
                ]
                span["llm_calls"] = span_llm_calls
                span["llm_cost_usd"] = sum(call["cost_usd"] for call in span_llm_calls)
                span["llm_tokens"] = sum(call["total_tokens"] for call in span_llm_calls)
            
            self.spans.append(span)
            
            # Log span completion with metrics
            if span.get("llm_calls"):
                logger.info(
                    f"Span '{name}' completed: {span['duration_ms']}ms, "
                    f"LLM calls: {len(span['llm_calls'])}, "
                    f"cost: ${span.get('llm_cost_usd', 0):.4f}"
                )

    async def flush(self):
        """Send trace data to Langfuse cloud."""
        if not (settings.langfuse_public_key and settings.langfuse_secret_key):
            logger.debug("Langfuse credentials not configured, skipping trace flush")
            return
            
        payload = {
            "traceId": self.id,
            "name": self.name,
            "spans": self.spans,
            "logs": self.logs,
            "llmCalls": self.llm_calls,  # Include LLM call details
            "metrics": {
                "totalCostUsd": self.total_cost_usd,
                "totalTokens": self.total_tokens,
                "llmCallCount": len(self.llm_calls)
            },
            "service": settings.service_name,
            "env": settings.service_env,
            "region": settings.service_region,
            "timestamp": time.time()
        }
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{settings.langfuse_host}/api/public/ingestion",
                    headers={
                        "X-Langfuse-Public-Key": settings.langfuse_public_key,
                        "X-Langfuse-Secret-Key": settings.langfuse_secret_key,
                        "Content-Type": "application/json",
                    },
                    content=json.dumps(payload),
                )
                response.raise_for_status()
                logger.debug(f"Trace {self.id} flushed to Langfuse successfully")
        except Exception as e:
            logger.error(f"Failed to flush trace to Langfuse: {e}")
            # Don't raise - tracing failures shouldn't break the application
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trace for logging or response."""
        return {
            "trace_id": self.id,
            "name": self.name,
            "span_count": len(self.spans),
            "llm_call_count": len(self.llm_calls),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_tokens": self.total_tokens,
            "duration_ms": sum(span.get("duration_ms", 0) for span in self.spans)
        }


def extract_messages_text(messages: List[Dict[str, Any]]) -> str:
    """Extract text from message list for logging."""
    texts = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            texts.append(f"{role}: {content}")
        elif isinstance(content, list):
            # Handle structured content
            text_parts = [
                part.get("text", "") for part in content
                if isinstance(part, dict) and "text" in part
            ]
            if text_parts:
                texts.append(f"{role}: {' '.join(text_parts)}")
    return "\n".join(texts)


def track_openrouter_call(
    trace: Optional[Trace],
    task: str,
    model: str,
    messages: List[Dict[str, Any]],
    response: Dict[str, Any],
    latency_ms: int
):
    """Track an OpenRouter API call in the trace."""
    if not trace:
        return
    
    # Extract prompt and completion
    prompt = extract_messages_text(messages)
    
    choices = response.get("choices", [])
    completion = ""
    if choices:
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str):
            completion = content
        elif isinstance(content, list):
            texts = [p.get("text", "") for p in content if isinstance(p, dict)]
            completion = "\n".join(texts)
    
    # Extract token usage and cost
    usage = response.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    
    # Calculate cost (this should come from the response or be calculated based on model)
    cost_usd = response.get("cost_usd", 0.0)
    if cost_usd == 0.0 and "usage" in response:
        # Estimate cost based on tokens if not provided
        # These are example rates - should be loaded from pricing config
        cost_per_1k_prompt = 0.01  # $0.01 per 1K prompt tokens
        cost_per_1k_completion = 0.03  # $0.03 per 1K completion tokens
        cost_usd = (
            (prompt_tokens / 1000) * cost_per_1k_prompt +
            (completion_tokens / 1000) * cost_per_1k_completion
        )
    
    trace.log_llm_call(
        model=model,
        prompt=prompt,
        completion=completion,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        task=task,
        metadata={
            "response_id": response.get("id"),
            "created": response.get("created")
        }
    )