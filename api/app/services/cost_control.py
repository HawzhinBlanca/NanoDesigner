from __future__ import annotations

import logging
from typing import Dict
from datetime import date
from sqlalchemy import text
from .db import db_session
import os

logger = logging.getLogger(__name__)


def check_budget_status(org_id: str) -> Dict[str, object]:
    """Best-effort budget check placeholder.

    In absence of a real budget store, always return not exceeded.
    """
    with db_session() as s:
        # Read today's spend and budget
        today = date.today()
        usage = s.execute(
            text("SELECT spend_usd FROM org_usage_daily WHERE org_id=:org AND usage_date=:d"),
            {"org": org_id, "d": today},
        ).scalar() or 0.0
        budget = s.execute(
            text("SELECT daily_budget_usd FROM org_budgets WHERE org_id=:org"),
            {"org": org_id},
        ).scalar() or 0.0
        return {
            "is_exceeded": bool(budget and usage >= budget),
            "current_spend_usd": float(usage),
            "retry_after_seconds": 3600,
        }


def enforce_budget(org_id: str, cost_usd: float, model: str, task: str) -> Dict[str, object]:
    """Best-effort budget tracking placeholder.

    Returns a minimal structure describing usage; no side effects yet.
    """
    with db_session() as s:
        today = date.today()
        # Upsert usage
        s.execute(
            text(
                """
                INSERT INTO org_usage_daily (org_id, usage_date, spend_usd)
                VALUES (:org, :d, :c)
                ON CONFLICT (org_id, usage_date) DO UPDATE
                SET spend_usd = org_usage_daily.spend_usd + EXCLUDED.spend_usd
                """
            ),
            {"org": org_id, "d": today, "c": float(cost_usd)},
        )
        # Read updated usage and budget
        usage = s.execute(
            text("SELECT spend_usd FROM org_usage_daily WHERE org_id=:org AND usage_date=:d"),
            {"org": org_id, "d": today},
        ).scalar() or 0.0
        budget = s.execute(
            text("SELECT daily_budget_usd FROM org_budgets WHERE org_id=:org"),
            {"org": org_id},
        ).scalar() or 0.0
        pct = float(usage / budget) if budget else 0.0
        # Simple alerting via webhook if configured
        webhook = os.getenv("BUDGET_ALERT_WEBHOOK")
        if webhook and budget:
            # Determine threshold crossings
            thresholds = [0.5, 0.8, 1.0]
            for t in thresholds:
                if pct >= t:
                    try:
                        import json, httpx
                        payload = {
                            "org_id": org_id,
                            "threshold": int(t * 100),
                            "usage_usd": float(usage),
                            "budget_usd": float(budget),
                        }
                        with httpx.Client(timeout=5.0) as client:
                            client.post(webhook, json=payload)
                    except Exception:
                        pass
        return {"org_id": org_id, "added_cost_usd": float(cost_usd), "percentage_used": pct}

"""Real-time cost control and budget enforcement service.

This module implements per-organization budget caps with:
- Real-time cost tracking from OpenRouter API responses
- Daily budget enforcement with 429 responses
- Alert thresholds at 50%, 80%, 100% of budget
- Retry-After header calculation
"""


import time
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import httpx
from fastapi import HTTPException

from ..services.redis import get_redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Budget alert levels."""
    FIFTY_PERCENT = 50
    EIGHTY_PERCENT = 80
    HUNDRED_PERCENT = 100


@dataclass
class BudgetStatus:
    """Current budget status for an organization."""
    org_id: str
    daily_budget_usd: float
    current_spend_usd: float
    percentage_used: float
    is_exceeded: bool
    retry_after_seconds: Optional[int]
    alert_level: Optional[AlertLevel]
    reset_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "org_id": self.org_id,
            "daily_budget_usd": self.daily_budget_usd,
            "current_spend_usd": round(self.current_spend_usd, 4),
            "percentage_used": round(self.percentage_used, 2),
            "is_exceeded": self.is_exceeded,
            "retry_after_seconds": self.retry_after_seconds,
            "alert_level": self.alert_level.value if self.alert_level else None,
            "reset_time": self.reset_time.isoformat()
        }


class CostControlService:
    """Service for real-time cost control and budget enforcement."""
    
    def __init__(self):
        """Initialize cost control service."""
        self.redis = get_redis_client()
        self.daily_budget_usd = float(os.getenv("DAILY_BUDGET_USD", "10.0"))
        self.alert_thresholds = [0.5, 0.8, 1.0]  # 50%, 80%, 100%
        self.webhook_url = os.getenv("BUDGET_ALERT_WEBHOOK")
        
        # Cost rates per model (example rates - should be loaded from config)
        self.model_costs = {
            "openrouter/gpt-5": {"prompt": 0.01, "completion": 0.03},  # per 1K tokens
            "openrouter/claude-4.1": {"prompt": 0.008, "completion": 0.024},
            "openrouter/deepseek-v3.1": {"prompt": 0.0002, "completion": 0.0002},
            "openrouter/gpt-5-mini": {"prompt": 0.0003, "completion": 0.0006},
            "openrouter/gemini-2.5-flash-image": {"flat": 0.075}  # per image
        }
        
        logger.info(f"Cost control initialized with daily budget: ${self.daily_budget_usd}")
    
    def track_cost(
        self,
        org_id: str,
        cost_usd: float,
        model: str,
        task: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BudgetStatus:
        """Track API cost and enforce budget.
        
        Args:
            org_id: Organization identifier
            cost_usd: Cost in USD for this API call
            model: Model used
            task: Task type
            metadata: Additional metadata
            
        Returns:
            Current budget status
            
        Raises:
            HTTPException: If budget is exceeded (429)
        """
        # Get current daily spend
        today_key = self._get_daily_key(org_id)
        
        # Increment spend atomically
        new_spend = self.redis.incrbyfloat(today_key, cost_usd)
        
        # Set expiry to end of day if new key
        if self.redis.ttl(today_key) == -1:
            seconds_until_midnight = self._seconds_until_midnight()
            self.redis.expire(today_key, seconds_until_midnight)
        
        # Log the cost
        self._log_cost_entry(org_id, cost_usd, model, task, metadata)
        
        # Calculate budget status
        percentage_used = (new_spend / self.daily_budget_usd) * 100
        is_exceeded = new_spend >= self.daily_budget_usd
        
        # Determine alert level
        alert_level = None
        if percentage_used >= 100:
            alert_level = AlertLevel.HUNDRED_PERCENT
        elif percentage_used >= 80:
            alert_level = AlertLevel.EIGHTY_PERCENT
        elif percentage_used >= 50:
            alert_level = AlertLevel.FIFTY_PERCENT
        
        # Send alerts if threshold crossed
        if alert_level:
            self._send_alert_if_needed(org_id, new_spend, percentage_used, alert_level)
        
        # Calculate retry-after if exceeded
        retry_after = None
        if is_exceeded:
            retry_after = self._seconds_until_midnight()
        
        status = BudgetStatus(
            org_id=org_id,
            daily_budget_usd=self.daily_budget_usd,
            current_spend_usd=new_spend,
            percentage_used=percentage_used,
            is_exceeded=is_exceeded,
            retry_after_seconds=retry_after,
            alert_level=alert_level,
            reset_time=self._get_reset_time()
        )
        
        # Enforce budget cap
        if is_exceeded:
            logger.warning(f"Budget exceeded for org {org_id}: ${new_spend:.4f}/${self.daily_budget_usd}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "BudgetExceeded",
                    "message": f"Daily budget of ${self.daily_budget_usd} exceeded",
                    "current_spend": round(new_spend, 4),
                    "retry_after_seconds": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.daily_budget_usd),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(self._get_reset_time().timestamp()))
                }
            )
        
        return status
    
    def check_budget(self, org_id: str) -> BudgetStatus:
        """Check current budget status without incrementing.
        
        Args:
            org_id: Organization identifier
            
        Returns:
            Current budget status
        """
        today_key = self._get_daily_key(org_id)
        current_spend = float(self.redis.get(today_key) or 0)
        
        percentage_used = (current_spend / self.daily_budget_usd) * 100
        is_exceeded = current_spend >= self.daily_budget_usd
        
        # Determine alert level
        alert_level = None
        if percentage_used >= 100:
            alert_level = AlertLevel.HUNDRED_PERCENT
        elif percentage_used >= 80:
            alert_level = AlertLevel.EIGHTY_PERCENT
        elif percentage_used >= 50:
            alert_level = AlertLevel.FIFTY_PERCENT
        
        retry_after = None
        if is_exceeded:
            retry_after = self._seconds_until_midnight()
        
        return BudgetStatus(
            org_id=org_id,
            daily_budget_usd=self.daily_budget_usd,
            current_spend_usd=current_spend,
            percentage_used=percentage_used,
            is_exceeded=is_exceeded,
            retry_after_seconds=retry_after,
            alert_level=alert_level,
            reset_time=self._get_reset_time()
        )
    
    def calculate_cost_from_response(
        self,
        response: Dict[str, Any],
        model: str
    ) -> float:
        """Calculate actual cost from OpenRouter API response.
        
        Args:
            response: OpenRouter API response
            model: Model identifier
            
        Returns:
            Cost in USD
        """
        # Check if cost is directly provided
        if "cost_usd" in response:
            return response["cost_usd"]
        
        # Calculate from usage
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Get model costs
        costs = self.model_costs.get(model, {"prompt": 0.01, "completion": 0.03})
        
        if "flat" in costs:
            # Flat rate per request (e.g., image generation)
            return costs["flat"]
        else:
            # Token-based pricing
            prompt_cost = (prompt_tokens / 1000) * costs["prompt"]
            completion_cost = (completion_tokens / 1000) * costs["completion"]
            return prompt_cost + completion_cost
    
    def _get_daily_key(self, org_id: str) -> str:
        """Get Redis key for daily budget tracking."""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"budget:daily:{org_id}:{today}"
    
    def _get_alert_key(self, org_id: str, level: AlertLevel) -> str:
        """Get Redis key for alert tracking."""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"budget:alert:{org_id}:{today}:{level.value}"
    
    def _log_cost_entry(
        self,
        org_id: str,
        cost_usd: float,
        model: str,
        task: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log individual cost entry for auditing."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "org_id": org_id,
            "cost_usd": cost_usd,
            "model": model,
            "task": task,
            "metadata": metadata or {}
        }
        
        # Store in Redis list for audit trail (keep last 1000 entries)
        audit_key = f"budget:audit:{org_id}"
        self.redis.lpush(audit_key, json.dumps(entry))
        self.redis.ltrim(audit_key, 0, 999)
        self.redis.expire(audit_key, 86400 * 7)  # Keep for 7 days
        
        logger.info(f"Cost tracked: org={org_id}, model={model}, task={task}, cost=${cost_usd:.4f}")
    
    def _send_alert_if_needed(
        self,
        org_id: str,
        current_spend: float,
        percentage: float,
        level: AlertLevel
    ):
        """Send alert if this threshold hasn't been alerted today."""
        alert_key = self._get_alert_key(org_id, level)
        
        # Check if we've already sent this alert today
        if self.redis.exists(alert_key):
            return
        
        # Mark alert as sent
        self.redis.setex(alert_key, self._seconds_until_midnight(), "1")
        
        # Send alert
        alert_message = (
            f"Budget Alert for {org_id}: "
            f"{level.value}% of daily budget used. "
            f"Current spend: ${current_spend:.2f}/${self.daily_budget_usd}"
        )
        
        logger.warning(alert_message)
        
        # Send webhook if configured
        if self.webhook_url:
            self._send_webhook_alert(org_id, current_spend, percentage, level)
    
    def _send_webhook_alert(
        self,
        org_id: str,
        current_spend: float,
        percentage: float,
        level: AlertLevel
    ):
        """Send alert via webhook."""
        try:
            payload = {
                "type": "budget_alert",
                "org_id": org_id,
                "alert_level": level.value,
                "current_spend_usd": round(current_spend, 4),
                "daily_budget_usd": self.daily_budget_usd,
                "percentage_used": round(percentage, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            with httpx.Client(timeout=5.0) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _seconds_until_midnight(self) -> int:
        """Calculate seconds until midnight UTC."""
        now = datetime.utcnow()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int((midnight - now).total_seconds())
    
    def _get_reset_time(self) -> datetime:
        """Get the next budget reset time (midnight UTC)."""
        now = datetime.utcnow()
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    def get_spending_report(self, org_id: str, days: int = 7) -> Dict[str, Any]:
        """Get spending report for an organization.
        
        Args:
            org_id: Organization identifier
            days: Number of days to include
            
        Returns:
            Spending report with daily breakdowns
        """
        report = {
            "org_id": org_id,
            "period_days": days,
            "daily_budget_usd": self.daily_budget_usd,
            "daily_spending": [],
            "total_spend_usd": 0.0
        }
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            key = f"budget:daily:{org_id}:{date}"
            spend = float(self.redis.get(key) or 0)
            
            report["daily_spending"].append({
                "date": date,
                "spend_usd": round(spend, 4),
                "percentage_of_budget": round((spend / self.daily_budget_usd) * 100, 2)
            })
            
            report["total_spend_usd"] += spend
        
        report["total_spend_usd"] = round(report["total_spend_usd"], 4)
        report["average_daily_spend"] = round(report["total_spend_usd"] / days, 4)
        
        return report


# Global service instance
import os
_service: Optional[CostControlService] = None


def get_cost_control_service() -> CostControlService:
    """Get the global cost control service instance."""
    global _service
    if _service is None:
        _service = CostControlService()
    return _service


def enforce_budget(
    org_id: str,
    cost_usd: float,
    model: str,
    task: str
) -> Dict[str, Any]:
    """Enforce budget for an API call.
    
    Args:
        org_id: Organization identifier
        cost_usd: Cost of the API call
        model: Model used
        task: Task type
        
    Returns:
        Budget status dictionary
        
    Raises:
        HTTPException: If budget exceeded (429)
    """
    service = get_cost_control_service()
    status = service.track_cost(org_id, cost_usd, model, task)
    return status.to_dict()


def check_budget_status(org_id: str) -> Dict[str, Any]:
    """Check current budget status.
    
    Args:
        org_id: Organization identifier
        
    Returns:
        Budget status dictionary
    """
    service = get_cost_control_service()
    status = service.check_budget(org_id)
    return status.to_dict()