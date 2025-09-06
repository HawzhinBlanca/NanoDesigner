"""Cost tracking service for OpenRouter API calls.

This module provides utilities to track and calculate costs from OpenRouter API responses.
It handles both chat completions and image generation costs.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CostInfo:
    """Cost information for an API call."""
    total_cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    
    def __add__(self, other: 'CostInfo') -> 'CostInfo':
        """Add two CostInfo objects together."""
        return CostInfo(
            total_cost_usd=self.total_cost_usd + other.total_cost_usd,
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            model=f"{self.model}+{other.model}"
        )


class CostTracker:
    """Tracks costs across multiple API calls."""
    
    def __init__(self):
        self.total_cost = 0.0
        self.calls: List[CostInfo] = []
    
    def add_call(self, cost_info: CostInfo) -> None:
        """Add a cost info to the tracker."""
        self.calls.append(cost_info)
        self.total_cost += cost_info.total_cost_usd
    
    def get_total_cost(self) -> float:
        """Get the total cost across all calls."""
        return self.total_cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all costs."""
        return {
            "total_cost_usd": self.total_cost,
            "total_calls": len(self.calls),
            "total_tokens": sum(call.total_tokens for call in self.calls),
            "models_used": list(set(call.model for call in self.calls))
        }


def extract_cost_from_openrouter_response(response: Dict[str, Any], model: str) -> CostInfo:
    """Extract cost information from an OpenRouter API response.
    
    Args:
        response: The OpenRouter API response
        model: The model that was called
        
    Returns:
        CostInfo: Cost information extracted from the response
    """
    usage = response.get("usage", {})
    
    # Extract token counts
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
    
    # Try to get cost from OpenRouter's cost field (if available)
    total_cost = 0.0
    
    # OpenRouter sometimes provides cost directly
    if "cost" in response:
        total_cost = float(response["cost"])
    elif "usage" in response and "cost" in response["usage"]:
        total_cost = float(response["usage"]["cost"])
    else:
        # Fallback: estimate cost based on model and tokens
        total_cost = estimate_cost_from_tokens(model, prompt_tokens, completion_tokens)
    
    return CostInfo(
        total_cost_usd=total_cost,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model
    )


def estimate_cost_from_tokens(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost based on model and token counts.
    
    This is a fallback when OpenRouter doesn't provide direct cost information.
    Prices are approximate and based on OpenRouter's pricing as of 2025.
    """
    # Simplified pricing model - in production, this should be more comprehensive
    # and regularly updated
    pricing = {
        # GPT models (per 1K tokens)
        "openrouter/gpt-4": {"prompt": 0.03, "completion": 0.06},
        "openrouter/gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "openrouter/gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        
        # Claude models
        "openrouter/claude-3-opus": {"prompt": 0.015, "completion": 0.075},
        "openrouter/claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
        "openrouter/claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
        
        # Gemini models
        "openrouter/gemini-pro": {"prompt": 0.0005, "completion": 0.0015},
        "openrouter/gemini-2.5-flash-image": {"prompt": 0.075, "completion": 0.3},  # Image generation
        
        # DeepSeek models
        "openrouter/deepseek-v3": {"prompt": 0.00014, "completion": 0.00028},
        "openrouter/deepseek-v3.1": {"prompt": 0.00014, "completion": 0.00028},
    }
    
    # Get pricing for the model
    model_pricing = pricing.get(model, {"prompt": 0.001, "completion": 0.002})  # Default fallback
    
    # Calculate cost
    prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
    completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
    
    total_cost = prompt_cost + completion_cost
    
    logger.debug(f"Estimated cost for {model}: ${total_cost:.6f} "
                f"({prompt_tokens} prompt + {completion_tokens} completion tokens)")
    
    return total_cost


def extract_cost_from_image_response(response: Dict[str, Any], model: str, n_images: int = 1) -> CostInfo:
    """Extract cost information from an OpenRouter image generation response.
    
    Args:
        response: The OpenRouter Images API response
        model: The model that was called
        n_images: Number of images generated
        
    Returns:
        CostInfo: Cost information for the image generation
    """
    # Try to get cost from response
    total_cost = 0.0
    
    if "cost" in response:
        total_cost = float(response["cost"])
    elif "usage" in response and "cost" in response["usage"]:
        total_cost = float(response["usage"]["cost"])
    else:
        # Estimate based on model and number of images
        total_cost = estimate_image_cost(model, n_images)
    
    return CostInfo(
        total_cost_usd=total_cost,
        prompt_tokens=0,  # Image generation doesn't use traditional tokens
        completion_tokens=0,
        total_tokens=0,
        model=model
    )


def estimate_image_cost(model: str, n_images: int) -> float:
    """Estimate cost for image generation.
    
    Args:
        model: The image generation model
        n_images: Number of images generated
        
    Returns:
        float: Estimated cost in USD
    """
    # Image generation pricing (per image)
    image_pricing = {
        "openrouter/gemini-2.5-flash-image": 0.04,  # Approximate
        "openrouter/dall-e-3": 0.08,
        "openrouter/dall-e-2": 0.02,
        "openrouter/stable-diffusion-xl": 0.01,
    }
    
    per_image_cost = image_pricing.get(model, 0.05)  # Default fallback
    total_cost = per_image_cost * n_images
    
    logger.debug(f"Estimated image cost for {model}: ${total_cost:.4f} ({n_images} images)")
    
    return total_cost
