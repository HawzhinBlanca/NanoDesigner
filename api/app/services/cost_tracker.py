from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# Remove duplicate CostInfo class definition - keeping the enhanced one below



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
        # Gemini 2.5 Flash Image Preview - the only model we use
        "google/gemini-2.5-flash-image-preview": {"prompt": 0.075, "completion": 0.3},  # Image generation
        "gemini-2.5-flash-image-preview": {"prompt": 0.075, "completion": 0.3},  # Alternate name
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
    try:
        n_images = max(1, int(n_images))
    except (ValueError, TypeError):
        n_images = 1
    
    # Image generation pricing (per image) - only gemini-2.5-flash-image-preview
    image_pricing = {
        "google/gemini-2.5-flash-image-preview": 0.04,
        "gemini-2.5-flash-image-preview": 0.04,  # Support both with and without prefix
    }
    
    # Clean model name - remove openrouter prefix if present
    clean_model = model.replace("openrouter/", "").lower()
    per_image_cost = image_pricing.get(clean_model, 0.05)  # Default fallback
    total_cost = per_image_cost * n_images
    
    logger.debug(f"Estimated image cost for {model}: ${total_cost:.4f} ({n_images} images)")
    
    return total_cost
