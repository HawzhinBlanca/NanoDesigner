
"""User journey optimization service.

This module provides intelligent optimization of user journeys based on
historical data, performance metrics, and user behavior patterns.
"""

from __future__ import annotations
import json


import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from .e2e_monitoring import (
    monitoring_service, 
    JourneyStage, 
    UserJourney,
    MetricType
)
from .redis import get_client as get_redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)

class OptimizationStrategy(str, Enum):
    """Available optimization strategies."""
    PERFORMANCE_FIRST = "performance_first"
    RELIABILITY_FIRST = "reliability_first"
    COST_EFFICIENT = "cost_efficient"
    USER_EXPERIENCE = "user_experience"
    BALANCED = "balanced"

class CacheStrategy(str, Enum):
    """Caching strategies for optimization."""
    AGGRESSIVE = "aggressive"  # Cache everything possible
    CONSERVATIVE = "conservative"  # Cache only safe items
    ADAPTIVE = "adaptive"  # Adapt based on usage patterns
    DISABLED = "disabled"  # No optimization caching

@dataclass
class OptimizationRule:
    """Individual optimization rule."""
    name: str
    condition: str  # JSON-serializable condition
    action: str  # Action to take
    priority: int  # Higher number = higher priority
    enabled: bool = True
    metadata: Dict[str, Any] = None

@dataclass
class JourneyOptimization:
    """Optimization recommendations for a user journey."""
    journey_id: str
    user_id: str
    project_id: str
    strategy: OptimizationStrategy
    optimizations: List[Dict[str, Any]]
    estimated_improvement: Dict[str, float]  # time_saved_ms, success_rate_increase, etc.
    confidence_score: float  # 0-1 confidence in recommendations
    metadata: Dict[str, Any] = None

class JourneyOptimizer:
    """Optimizes user journeys based on data and patterns."""
    
    def __init__(self):
        self.optimization_rules: List[OptimizationRule] = []
        self.cache_strategies: Dict[str, CacheStrategy] = {}
        self.performance_baselines: Dict[str, float] = {}
        self.load_default_rules()
    
    def load_default_rules(self):
        """Load default optimization rules."""
        
        self.optimization_rules = [
            OptimizationRule(
                name="cache_brand_canon",
                condition=json.dumps({
                    "stage": "canon_derivation",
                    "repeat_project": True,
                    "processing_time_ms": {"gt": 5000}
                }),
                action="enable_aggressive_caching",
                priority=8,
                metadata={"cache_duration": 3600, "cache_scope": "project"}
            ),
            
            OptimizationRule(
                name="preload_models",
                condition=json.dumps({
                    "stage": "design_generation",
                    "user_pattern": "frequent",
                    "time_of_day": {"in": ["09:00-12:00", "14:00-17:00"]}
                }),
                action="preload_ai_models",
                priority=7,
                metadata={"models": ["planner", "generator"], "warmup_time": 30}
            ),
            
            OptimizationRule(
                name="batch_processing",
                condition=json.dumps({
                    "stage": "design_generation",
                    "output_count": {"gt": 3},
                    "queue_size": {"lt": 5}
                }),
                action="enable_batch_processing",
                priority=6,
                metadata={"batch_size": 4, "max_wait_time": 10000}
            ),
            
            OptimizationRule(
                name="cdn_optimization",
                condition=json.dumps({
                    "stage": "asset_delivery",
                    "user_location": {"not_in": ["same_region"]},
                    "asset_size": {"gt": 1048576}  # > 1MB
                }),
                action="enable_cdn_optimization",
                priority=5,
                metadata={"compression": True, "format_conversion": True}
            ),
            
            OptimizationRule(
                name="skip_critique_for_simple",
                condition=json.dumps({
                    "stage": "quality_critique",
                    "design_complexity": "simple",
                    "user_experience": "expert",
                    "previous_success_rate": {"gt": 0.95}
                }),
                action="skip_optional_step",
                priority=4,
                metadata={"skip_stage": "quality_critique", "auto_approve": True}
            ),
            
            OptimizationRule(
                name="parallel_processing",
                condition=json.dumps({
                    "multiple_outputs": True,
                    "system_load": {"lt": 0.7},
                    "output_count": {"gt": 2}
                }),
                action="enable_parallel_processing",
                priority=6,
                metadata={"max_parallel": 3, "resource_limit": 0.8}
            )
        ]
        
        logger.info(f"Loaded {len(self.optimization_rules)} default optimization rules")
    
    async def optimize_journey(
        self,
        journey_id: str,
        user_id: str,
        project_id: str,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> JourneyOptimization:
        """Generate optimization recommendations for a journey."""
        
        # Get user history and patterns
        user_patterns = await self._analyze_user_patterns(user_id)
        project_history = await self._analyze_project_history(project_id)
        system_metrics = await self._get_current_system_metrics()
        
        # Apply optimization rules
        applicable_rules = await self._filter_applicable_rules(
            user_patterns, project_history, system_metrics, strategy
        )
        
        # Generate specific optimizations
        optimizations = []
        estimated_improvement = {
            "time_saved_ms": 0,
            "success_rate_increase": 0.0,
            "cost_reduction": 0.0,
            "resource_savings": 0.0
        }
        
        for rule in applicable_rules:
            optimization = await self._apply_optimization_rule(
                rule, user_patterns, project_history, system_metrics
            )
            
            if optimization:
                optimizations.append(optimization)
                
                # Accumulate estimated improvements
                if "estimated_time_saved" in optimization:
                    estimated_improvement["time_saved_ms"] += optimization["estimated_time_saved"]
                if "success_rate_boost" in optimization:
                    estimated_improvement["success_rate_increase"] += optimization["success_rate_boost"]
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            optimizations, user_patterns, len(applicable_rules)
        )
        
        journey_optimization = JourneyOptimization(
            journey_id=journey_id,
            user_id=user_id,
            project_id=project_id,
            strategy=strategy,
            optimizations=optimizations,
            estimated_improvement=estimated_improvement,
            confidence_score=confidence_score,
            metadata={
                "analysis_time": datetime.utcnow().isoformat(),
                "rules_evaluated": len(self.optimization_rules),
                "rules_applied": len(applicable_rules)
            }
        )
        
        # Store optimization plan
        await self._store_optimization_plan(journey_optimization)
        
        logger.info(
            f"Generated {len(optimizations)} optimizations for journey {journey_id}",
            extra={
                "journey_id": journey_id,
                "user_id": user_id,
                "strategy": strategy.value,
                "confidence_score": confidence_score
            }
        )
        
        return journey_optimization
    
    async def apply_optimizations(
        self,
        journey_id: str,
        optimization: JourneyOptimization
    ) -> Dict[str, Any]:
        """Apply optimizations to a journey in progress."""
        
        applied_optimizations = []
        failed_optimizations = []
        
        for opt in optimization.optimizations:
            try:
                result = await self._execute_optimization(journey_id, opt)
                if result.get("success"):
                    applied_optimizations.append({
                        "optimization": opt["name"],
                        "result": result
                    })
                else:
                    failed_optimizations.append({
                        "optimization": opt["name"],
                        "error": result.get("error", "Unknown error")
                    })
                    
            except Exception as e:
                failed_optimizations.append({
                    "optimization": opt["name"],
                    "error": str(e)
                })
                logger.error(f"Failed to apply optimization {opt['name']}: {e}")
        
        # Record optimization effectiveness
        await monitoring_service.record_metric(
            "optimization.applied",
            len(applied_optimizations),
            MetricType.COUNTER,
            {"journey_id": journey_id, "strategy": optimization.strategy.value}
        )
        
        return {
            "applied": applied_optimizations,
            "failed": failed_optimizations,
            "success_rate": len(applied_optimizations) / len(optimization.optimizations) if optimization.optimizations else 1.0
        }
    
    async def _analyze_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze historical user patterns."""
        
        redis_client = get_redis_client()
        
        # Get user's recent journeys (last 30 days)
        user_journeys_key = f"user_journeys:{user_id}"
        journey_ids = await redis_client.lrange(user_journeys_key, 0, -1)
        
        patterns = {
            "total_journeys": len(journey_ids),
            "frequent_stages": {},
            "average_durations": {},
            "common_failures": [],
            "peak_usage_times": [],
            "preferred_outputs": {},
            "experience_level": "beginner"  # beginner, intermediate, expert
        }
        
        if not journey_ids:
            return patterns
        
        # Analyze journey patterns
        stage_counts = {}
        stage_durations = {}
        failure_patterns = []
        
        for journey_id in journey_ids[-20:]:  # Last 20 journeys
            journey = await monitoring_service.get_journey(journey_id)
            if not journey:
                continue
                
            for step in journey.steps:
                stage = step.stage.value
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
                
                if step.duration_ms:
                    if stage not in stage_durations:
                        stage_durations[stage] = []
                    stage_durations[stage].append(step.duration_ms)
                
                if not step.success and step.error_message:
                    failure_patterns.append({
                        "stage": stage,
                        "error": step.error_message,
                        "timestamp": step.end_time.isoformat() if step.end_time else None
                    })
        
        # Calculate averages
        patterns["frequent_stages"] = dict(sorted(stage_counts.items(), key=lambda x: x[1], reverse=True))
        patterns["average_durations"] = {
            stage: sum(durations) / len(durations)
            for stage, durations in stage_durations.items()
        }
        patterns["common_failures"] = failure_patterns[-5:]  # Last 5 failures
        
        # Determine experience level
        if patterns["total_journeys"] > 50:
            patterns["experience_level"] = "expert"
        elif patterns["total_journeys"] > 10:
            patterns["experience_level"] = "intermediate"
        
        return patterns
    
    async def _analyze_project_history(self, project_id: str) -> Dict[str, Any]:
        """Analyze project-specific patterns."""
        
        redis_client = get_redis_client()
        
        # Get project's journey history
        project_journeys_key = f"project_journeys:{project_id}"
        journey_ids = await redis_client.lrange(project_journeys_key, 0, -1)
        
        history = {
            "total_renders": len(journey_ids),
            "success_rate": 1.0,
            "common_patterns": {},
            "performance_trends": {},
            "cached_assets": [],
            "brand_canon_stable": False
        }
        
        if not journey_ids:
            return history
        
        successful_journeys = 0
        total_duration = 0
        
        for journey_id in journey_ids[-10:]:  # Last 10 journeys
            journey = await monitoring_service.get_journey(journey_id)
            if not journey:
                continue
                
            if journey.success:
                successful_journeys += 1
            
            if journey.total_duration_ms:
                total_duration += journey.total_duration_ms
        
        history["success_rate"] = successful_journeys / len(journey_ids)
        history["average_duration_ms"] = total_duration / len(journey_ids) if journey_ids else 0
        
        # Check if brand canon is stable (hasn't changed in recent journeys)
        history["brand_canon_stable"] = len(journey_ids) > 3  # Simplified check
        
        return history
    
    async def _get_current_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics."""
        
        metrics = await monitoring_service.get_real_time_metrics()
        
        return {
            "active_journeys": metrics.get("active_journeys", 0),
            "system_load": 0.5,  # TODO: Get from actual system monitoring
            "redis_healthy": metrics.get("redis_healthy", True),
            "ai_model_latency": 2000,  # TODO: Get from OpenRouter metrics
            "storage_latency": 50,  # TODO: Get from storage metrics
            "cache_hit_rate": 0.7  # TODO: Get from cache metrics
        }
    
    async def _filter_applicable_rules(
        self,
        user_patterns: Dict[str, Any],
        project_history: Dict[str, Any],
        system_metrics: Dict[str, Any],
        strategy: OptimizationStrategy
    ) -> List[OptimizationRule]:
        """Filter optimization rules that apply to current context."""
        
        applicable_rules = []
        
        for rule in self.optimization_rules:
            if not rule.enabled:
                continue
            
            # Parse condition
            try:
                condition = json.loads(rule.condition)
                
                if await self._evaluate_condition(condition, user_patterns, project_history, system_metrics):
                    # Adjust priority based on strategy
                    adjusted_priority = self._adjust_priority_for_strategy(rule, strategy)
                    rule.priority = adjusted_priority
                    applicable_rules.append(rule)
                    
            except Exception as e:
                logger.warning(f"Failed to evaluate rule {rule.name}: {e}")
        
        # Sort by priority (highest first)
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        return applicable_rules
    
    async def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        user_patterns: Dict[str, Any],
        project_history: Dict[str, Any],
        system_metrics: Dict[str, Any]
    ) -> bool:
        """Evaluate if a condition matches current context."""
        
        context = {
            **user_patterns,
            **project_history,
            **system_metrics,
            "current_time": datetime.utcnow().hour
        }
        
        # Simple condition evaluation (can be expanded)
        for key, expected in condition.items():
            if key not in context:
                continue
            
            actual = context[key]
            
            if isinstance(expected, dict):
                # Handle operators like {"gt": 5000}
                for op, value in expected.items():
                    if op == "gt" and actual <= value:
                        return False
                    elif op == "lt" and actual >= value:
                        return False
                    elif op == "gte" and actual < value:
                        return False
                    elif op == "lte" and actual > value:
                        return False
                    elif op == "eq" and actual != value:
                        return False
                    elif op == "in" and actual not in value:
                        return False
                    elif op == "not_in" and actual in value:
                        return False
            else:
                # Direct comparison
                if actual != expected:
                    return False
        
        return True
    
    def _adjust_priority_for_strategy(
        self, 
        rule: OptimizationRule, 
        strategy: OptimizationStrategy
    ) -> int:
        """Adjust rule priority based on optimization strategy."""
        
        base_priority = rule.priority
        
        if strategy == OptimizationStrategy.PERFORMANCE_FIRST:
            if "cache" in rule.action or "preload" in rule.action:
                return base_priority + 2
        elif strategy == OptimizationStrategy.RELIABILITY_FIRST:
            if "skip" in rule.action:
                return base_priority - 3  # Less likely to skip steps
        elif strategy == OptimizationStrategy.COST_EFFICIENT:
            if "batch" in rule.action or "skip" in rule.action:
                return base_priority + 1
        elif strategy == OptimizationStrategy.USER_EXPERIENCE:
            if "preload" in rule.action or "parallel" in rule.action:
                return base_priority + 2
        
        return base_priority
    
    async def _apply_optimization_rule(
        self,
        rule: OptimizationRule,
        user_patterns: Dict[str, Any],
        project_history: Dict[str, Any],
        system_metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply a specific optimization rule."""
        
        optimization = {
            "name": rule.name,
            "action": rule.action,
            "priority": rule.priority,
            "metadata": rule.metadata or {}
        }
        
        # Add specific recommendations based on action type
        if rule.action == "enable_aggressive_caching":
            optimization["parameters"] = {
                "cache_duration": rule.metadata.get("cache_duration", 3600),
                "cache_scope": rule.metadata.get("cache_scope", "project"),
                "cache_strategy": "aggressive"
            }
            optimization["estimated_time_saved"] = min(5000, user_patterns.get("average_durations", {}).get("canon_derivation", 0) * 0.8)
            
        elif rule.action == "preload_ai_models":
            optimization["parameters"] = {
                "models": rule.metadata.get("models", ["planner"]),
                "warmup_time": rule.metadata.get("warmup_time", 30)
            }
            optimization["estimated_time_saved"] = 2000  # Typical model loading time
            
        elif rule.action == "enable_batch_processing":
            optimization["parameters"] = {
                "batch_size": rule.metadata.get("batch_size", 4),
                "max_wait_time": rule.metadata.get("max_wait_time", 10000)
            }
            optimization["estimated_time_saved"] = 3000  # Batch efficiency savings
            
        elif rule.action == "skip_optional_step":
            skip_stage = rule.metadata.get("skip_stage")
            if skip_stage and skip_stage in user_patterns.get("average_durations", {}):
                optimization["estimated_time_saved"] = user_patterns["average_durations"][skip_stage]
            optimization["parameters"] = {
                "skip_stage": skip_stage,
                "auto_approve": rule.metadata.get("auto_approve", False)
            }
            
        elif rule.action == "enable_parallel_processing":
            optimization["parameters"] = {
                "max_parallel": rule.metadata.get("max_parallel", 2),
                "resource_limit": rule.metadata.get("resource_limit", 0.7)
            }
            optimization["estimated_time_saved"] = 4000  # Parallel processing savings
        
        return optimization
    
    async def _execute_optimization(
        self,
        journey_id: str,
        optimization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific optimization."""
        
        action = optimization.get("action")
        parameters = optimization.get("parameters", {})
        
        try:
            if action == "enable_aggressive_caching":
                # Set cache strategy for this journey
                redis_client = get_redis_client()
                await redis_client.setex(
                    f"cache_strategy:{journey_id}",
                    parameters.get("cache_duration", 3600),
                    json.dumps(parameters)
                )
                return {"success": True, "message": "Aggressive caching enabled"}
                
            elif action == "preload_ai_models":
                # Signal model preloading (implementation depends on AI service)
                await monitoring_service.record_metric(
                    "optimization.model_preload",
                    1,
                    MetricType.COUNTER,
                    {"models": str(parameters.get("models", []))}
                )
                return {"success": True, "message": "AI models preloading initiated"}
                
            elif action == "enable_batch_processing":
                # Set batch processing flag
                redis_client = get_redis_client()
                await redis_client.setex(
                    f"batch_config:{journey_id}",
                    300,  # 5 minutes
                    json.dumps(parameters)
                )
                return {"success": True, "message": "Batch processing enabled"}
                
            elif action == "skip_optional_step":
                # Set skip flag for specific stage
                redis_client = get_redis_client()
                await redis_client.setex(
                    f"skip_stage:{journey_id}",
                    1800,  # 30 minutes
                    parameters.get("skip_stage", "")
                )
                return {"success": True, "message": f"Stage {parameters.get('skip_stage')} will be skipped"}
                
            elif action == "enable_parallel_processing":
                # Set parallel processing configuration
                redis_client = get_redis_client()
                await redis_client.setex(
                    f"parallel_config:{journey_id}",
                    300,  # 5 minutes
                    json.dumps(parameters)
                )
                return {"success": True, "message": "Parallel processing enabled"}
                
            else:
                return {"success": False, "error": f"Unknown optimization action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_confidence_score(
        self,
        optimizations: List[Dict[str, Any]],
        user_patterns: Dict[str, Any],
        rules_applied: int
    ) -> float:
        """Calculate confidence score for optimization recommendations."""
        
        base_confidence = 0.5
        
        # Increase confidence based on user experience
        experience_level = user_patterns.get("experience_level", "beginner")
        if experience_level == "expert":
            base_confidence += 0.2
        elif experience_level == "intermediate":
            base_confidence += 0.1
        
        # Increase confidence based on data availability
        total_journeys = user_patterns.get("total_journeys", 0)
        if total_journeys > 20:
            base_confidence += 0.2
        elif total_journeys > 5:
            base_confidence += 0.1
        
        # Adjust based on number of applicable optimizations
        if rules_applied > 3:
            base_confidence += 0.1
        elif rules_applied == 0:
            base_confidence -= 0.2
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, base_confidence))
    
    async def _store_optimization_plan(self, optimization: JourneyOptimization):
        """Store optimization plan for later analysis."""
        
        redis_client = get_redis_client()
        
        optimization_data = {
            "journey_id": optimization.journey_id,
            "user_id": optimization.user_id,
            "project_id": optimization.project_id,
            "strategy": optimization.strategy.value,
            "optimizations": optimization.optimizations,
            "estimated_improvement": optimization.estimated_improvement,
            "confidence_score": optimization.confidence_score,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": optimization.metadata
        }
        
        await redis_client.setex(
            f"optimization_plan:{optimization.journey_id}",
            86400,  # 24 hours
            json.dumps(optimization_data)
        )

# Global optimizer instance
journey_optimizer = JourneyOptimizer()

# Convenience functions
async def optimize_user_journey(
    journey_id: str,
    user_id: str,
    project_id: str,
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
) -> JourneyOptimization:
    """Optimize a user journey with the given strategy."""
    return await journey_optimizer.optimize_journey(journey_id, user_id, project_id, strategy)

async def apply_journey_optimizations(
    journey_id: str,
    optimization: JourneyOptimization
) -> Dict[str, Any]:
    """Apply optimizations to a journey."""
    return await journey_optimizer.apply_optimizations(journey_id, optimization)