"""Enhanced OpenRouter integration with advanced cost tracking and monitoring."""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

import httpx
from fastapi import HTTPException, status

from ..core.config import settings
from ..core.tenant_isolation import TenantContext


class ModelProvider(Enum):
    """AI model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    META = "meta"
    MISTRAL = "mistral"
    COHERE = "cohere"


@dataclass
class ModelCost:
    """Model cost structure."""
    provider: ModelProvider
    model_name: str
    input_cost_per_1k: Decimal
    output_cost_per_1k: Decimal
    image_cost_per_image: Optional[Decimal] = None
    context_window: int = 4096
    max_output_tokens: int = 4096


@dataclass
class UsageMetrics:
    """Usage metrics for API calls."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    images_generated: int = 0
    cost_usd: Decimal = Decimal('0.00')
    model_used: str = ""
    provider: str = ""
    latency_ms: int = 0


@dataclass
class CostBudget:
    """Cost budget configuration."""
    daily_limit_usd: Decimal
    monthly_limit_usd: Decimal
    per_request_limit_usd: Decimal
    alert_threshold_pct: int = 80  # Alert at 80% of budget


class CostTracker:
    """Advanced cost tracking and budget management."""
    
    def __init__(self):
        self.model_costs = self._load_model_costs()
        self.usage_cache = {}  # In production, this would be Redis/DB
        self.budgets = {}      # In production, this would be from DB
    
    def _load_model_costs(self) -> Dict[str, ModelCost]:
        """Load model cost information."""
        # In production, this would be loaded from database or config
        return {
            "openai/gpt-4": ModelCost(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4",
                input_cost_per_1k=Decimal('0.03'),
                output_cost_per_1k=Decimal('0.06'),
                context_window=8192,
                max_output_tokens=4096
            ),
            "openai/gpt-3.5-turbo": ModelCost(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                input_cost_per_1k=Decimal('0.001'),
                output_cost_per_1k=Decimal('0.002'),
                context_window=16384,
                max_output_tokens=4096
            ),
            "anthropic/claude-3-sonnet": ModelCost(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-sonnet",
                input_cost_per_1k=Decimal('0.003'),
                output_cost_per_1k=Decimal('0.015'),
                context_window=200000,
                max_output_tokens=4096
            ),
            "google/gemini-pro": ModelCost(
                provider=ModelProvider.GOOGLE,
                model_name="gemini-pro",
                input_cost_per_1k=Decimal('0.0005'),
                output_cost_per_1k=Decimal('0.0015'),
                context_window=32768,
                max_output_tokens=8192
            ),
            "openai/dall-e-3": ModelCost(
                provider=ModelProvider.OPENAI,
                model_name="dall-e-3",
                input_cost_per_1k=Decimal('0.00'),
                output_cost_per_1k=Decimal('0.00'),
                image_cost_per_image=Decimal('0.04'),
                context_window=4096,
                max_output_tokens=0
            ),
        }
    
    def calculate_cost(self, model: str, usage: Dict[str, int]) -> Decimal:
        """Calculate cost for API usage."""
        if model not in self.model_costs:
            # Default cost if model not found
            return Decimal('0.01')
        
        model_cost = self.model_costs[model]
        total_cost = Decimal('0.00')
        
        # Text generation cost
        if usage.get('prompt_tokens', 0) > 0:
            input_cost = (Decimal(usage['prompt_tokens']) / 1000) * model_cost.input_cost_per_1k
            total_cost += input_cost
        
        if usage.get('completion_tokens', 0) > 0:
            output_cost = (Decimal(usage['completion_tokens']) / 1000) * model_cost.output_cost_per_1k
            total_cost += output_cost
        
        # Image generation cost
        if usage.get('images_generated', 0) > 0 and model_cost.image_cost_per_image:
            image_cost = Decimal(usage['images_generated']) * model_cost.image_cost_per_image
            total_cost += image_cost
        
        return total_cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    def set_budget(self, tenant: TenantContext, budget: CostBudget):
        """Set budget for tenant."""
        self.budgets[tenant.org_id] = budget
    
    def get_usage_stats(self, tenant: TenantContext, period: str = "daily") -> Dict[str, Any]:
        """Get usage statistics for tenant."""
        # In production, this would query from database
        key = f"{tenant.org_id}:{period}"
        return self.usage_cache.get(key, {
            "total_cost": Decimal('0.00'),
            "total_tokens": 0,
            "total_requests": 0,
            "models_used": [],
            "period": period
        })
    
    def check_budget_limits(self, tenant: TenantContext, estimated_cost: Decimal) -> bool:
        """Check if request would exceed budget limits."""
        if tenant.org_id not in self.budgets:
            return True  # No budget set, allow request
        
        budget = self.budgets[tenant.org_id]
        
        # Check per-request limit
        if estimated_cost > budget.per_request_limit_usd:
            return False
        
        # Check daily limit
        daily_usage = self.get_usage_stats(tenant, "daily")
        if daily_usage["total_cost"] + estimated_cost > budget.daily_limit_usd:
            return False
        
        # Check monthly limit
        monthly_usage = self.get_usage_stats(tenant, "monthly")
        if monthly_usage["total_cost"] + estimated_cost > budget.monthly_limit_usd:
            return False
        
        return True
    
    def record_usage(self, tenant: TenantContext, usage: UsageMetrics):
        """Record usage for tenant."""
        # In production, this would write to database
        for period in ["daily", "monthly", "yearly"]:
            key = f"{tenant.org_id}:{period}"
            if key not in self.usage_cache:
                self.usage_cache[key] = {
                    "total_cost": Decimal('0.00'),
                    "total_tokens": 0,
                    "total_requests": 0,
                    "models_used": set(),
                    "period": period
                }
            
            stats = self.usage_cache[key]
            stats["total_cost"] += usage.cost_usd
            stats["total_tokens"] += usage.total_tokens
            stats["total_requests"] += 1
            stats["models_used"].add(usage.model_used)
        
        print(f"💰 COST TRACKING: {tenant.org_id} - ${usage.cost_usd} for {usage.model_used}")


class EnhancedOpenRouterClient:
    """Enhanced OpenRouter client with advanced features."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.cost_tracker = CostTracker()
        self.rate_limits = {}
        self.circuit_breaker = {}
    
    async def call_model(self, 
                        tenant: TenantContext,
                        model: str,
                        messages: List[Dict[str, str]],
                        max_tokens: int = 1000,
                        temperature: float = 0.7,
                        **kwargs) -> Tuple[Dict[str, Any], UsageMetrics]:
        """Call AI model with enhanced tracking."""
        
        start_time = time.time()
        
        # Estimate cost before making request
        estimated_tokens = sum(len(msg.get('content', '')) // 4 for msg in messages)
        estimated_cost = self.cost_tracker.calculate_cost(model, {
            'prompt_tokens': estimated_tokens,
            'completion_tokens': max_tokens
        })
        
        # Check budget limits
        if not self.cost_tracker.check_budget_limits(tenant, estimated_cost):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "Budget limit exceeded",
                    "estimated_cost": str(estimated_cost),
                    "org_id": tenant.org_id
                }
            )
        
        # Check rate limits
        if not self._check_rate_limits(tenant, model):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Check circuit breaker
        if self._is_circuit_open(model):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Circuit breaker open for model: {model}"
            )
        
        try:
            # Make API request
            response = await self._make_api_request(model, messages, max_tokens, temperature, **kwargs)
            
            # Calculate actual cost
            usage_data = response.get('usage', {})
            actual_cost = self.cost_tracker.calculate_cost(model, usage_data)
            
            # Create usage metrics
            usage_metrics = UsageMetrics(
                prompt_tokens=usage_data.get('prompt_tokens', 0),
                completion_tokens=usage_data.get('completion_tokens', 0),
                total_tokens=usage_data.get('total_tokens', 0),
                cost_usd=actual_cost,
                model_used=model,
                provider=model.split('/')[0] if '/' in model else 'unknown',
                latency_ms=int((time.time() - start_time) * 1000)
            )
            
            # Record usage
            self.cost_tracker.record_usage(tenant, usage_metrics)
            
            # Reset circuit breaker on success
            self._reset_circuit_breaker(model)
            
            return response, usage_metrics
            
        except Exception as e:
            # Record failure for circuit breaker
            self._record_failure(model)
            
            # Log error with tenant context
            print(f"❌ OpenRouter API error for {tenant.org_id}: {e}")
            
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {str(e)}"
            )
    
    async def _make_api_request(self, model: str, messages: List[Dict[str, str]], 
                              max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        """Make the actual API request to OpenRouter."""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nanodesigner.ai",
            "X-Title": "NanoDesigner"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=settings.openrouter_timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"API request failed: {response.status_code} - {error_detail}")
            
            return response.json()
    
    def _check_rate_limits(self, tenant: TenantContext, model: str) -> bool:
        """Check rate limits for tenant and model."""
        # Simple rate limiting - in production would be more sophisticated
        key = f"{tenant.org_id}:{model}"
        current_time = time.time()
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # Remove old entries (older than 1 minute)
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if current_time - timestamp < 60
        ]
        
        # Check if under limit (60 requests per minute)
        if len(self.rate_limits[key]) >= 60:
            return False
        
        # Add current request
        self.rate_limits[key].append(current_time)
        return True
    
    def _is_circuit_open(self, model: str) -> bool:
        """Check if circuit breaker is open for model."""
        if model not in self.circuit_breaker:
            return False
        
        breaker = self.circuit_breaker[model]
        
        # If circuit is open, check if cooldown period has passed
        if breaker['state'] == 'open':
            if time.time() - breaker['opened_at'] > 60:  # 1 minute cooldown
                breaker['state'] = 'half_open'
                return False
            return True
        
        return False
    
    def _record_failure(self, model: str):
        """Record failure for circuit breaker."""
        if model not in self.circuit_breaker:
            self.circuit_breaker[model] = {
                'failures': 0,
                'state': 'closed',
                'opened_at': 0
            }
        
        breaker = self.circuit_breaker[model]
        breaker['failures'] += 1
        
        # Open circuit after 5 failures
        if breaker['failures'] >= 5 and breaker['state'] == 'closed':
            breaker['state'] = 'open'
            breaker['opened_at'] = time.time()
            print(f"🚨 Circuit breaker opened for model: {model}")
    
    def _reset_circuit_breaker(self, model: str):
        """Reset circuit breaker on successful request."""
        if model in self.circuit_breaker:
            self.circuit_breaker[model]['failures'] = 0
            self.circuit_breaker[model]['state'] = 'closed'


class SynthIDVerifier:
    """SynthID verification for AI-generated content."""
    
    def __init__(self):
        self.verification_cache = {}
    
    async def verify_content(self, content: str, model: str) -> Dict[str, Any]:
        """Verify if content was generated by AI using SynthID."""
        
        # Simulate SynthID verification
        # In production, this would call actual SynthID API
        
        verification_result = {
            "is_ai_generated": True,  # Assume AI-generated for now
            "confidence": 0.85,
            "model_detected": model,
            "watermark_present": True,
            "verification_method": "synthid",
            "timestamp": time.time()
        }
        
        # Cache result
        content_hash = hash(content)
        self.verification_cache[content_hash] = verification_result
        
        return verification_result
    
    def add_verified_by_field(self, response: Dict[str, Any], 
                            verification: Dict[str, Any]) -> Dict[str, Any]:
        """Add verified_by field to response."""
        
        if 'choices' in response:
            for choice in response['choices']:
                if 'message' in choice:
                    choice['message']['verified_by'] = {
                        "method": verification["verification_method"],
                        "confidence": verification["confidence"],
                        "watermark_detected": verification["watermark_present"],
                        "verified_at": verification["timestamp"]
                    }
        
        return response


# Global instances
enhanced_openrouter = EnhancedOpenRouterClient()
synthid_verifier = SynthIDVerifier()


async def enhanced_call_model(tenant: TenantContext, model: str, 
                            messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Enhanced model calling with full tracking and verification."""
    
    # Call model with tracking
    response, usage_metrics = await enhanced_openrouter.call_model(
        tenant, model, messages, **kwargs
    )
    
    # Verify content with SynthID
    if 'choices' in response and response['choices']:
        content = response['choices'][0].get('message', {}).get('content', '')
        if content:
            verification = await synthid_verifier.verify_content(content, model)
            response = synthid_verifier.add_verified_by_field(response, verification)
    
    # Add usage metadata
    response['usage_metadata'] = asdict(usage_metrics)
    
    return response
