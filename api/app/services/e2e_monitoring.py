from __future__ import annotations

"""End-to-End monitoring and observability service.

This module provides comprehensive monitoring, tracing, and observability
for the complete user journey across all system components.
"""


import time
import json
import asyncio
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from ..core.config import settings
from .langfuse import Trace
from .redis import get_client as get_redis_client

logger = logging.getLogger(__name__)

class JourneyStage(str, Enum):
    """Stages in the user journey."""
    AUTHENTICATION = "authentication"
    PROJECT_CREATION = "project_creation" 
    BRAND_INGEST = "brand_ingest"
    CANON_DERIVATION = "canon_derivation"
    DESIGN_GENERATION = "design_generation"
    ASSET_DELIVERY = "asset_delivery"
    QUALITY_CRITIQUE = "quality_critique"
    USER_FEEDBACK = "user_feedback"

class MetricType(str, Enum):
    """Types of metrics to track."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class JourneyStep:
    """Individual step in a user journey."""
    stage: JourneyStage
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    duration_ms: Optional[int] = None
    
    def complete(self, success: bool = True, error_message: Optional[str] = None):
        """Mark step as completed."""
        self.end_time = datetime.utcnow()
        self.success = success
        self.error_message = error_message
        if self.start_time:
            self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)

@dataclass
class UserJourney:
    """Complete user journey tracking."""
    journey_id: str
    user_id: str
    project_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    steps: List[JourneyStep] = None
    success: bool = True
    total_duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.metadata is None:
            self.metadata = {}
    
    def add_step(self, stage: JourneyStage, metadata: Dict[str, Any] = None) -> JourneyStep:
        """Add a new step to the journey."""
        step = JourneyStep(
            stage=stage,
            start_time=datetime.utcnow(),
            metadata=metadata or {}
        )
        self.steps.append(step)
        return step
    
    def complete(self, success: bool = True):
        """Complete the journey."""
        self.end_time = datetime.utcnow()
        self.success = success
        if self.start_time:
            self.total_duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)

@dataclass  
class SystemMetric:
    """System performance metric."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

class E2EMonitoringService:
    """End-to-End monitoring and observability service."""
    
    def __init__(self):
        self.redis_client = None
        self.active_journeys: Dict[str, UserJourney] = {}
        self.metrics_buffer: List[SystemMetric] = []
        self.flush_interval = 60  # seconds
        self.last_flush = time.time()
        
    async def get_redis(self):
        """Get Redis client instance."""
        if not self.redis_client:
            self.redis_client = get_redis_client()
        return self.redis_client
    
    async def start_journey(
        self, 
        journey_id: str, 
        user_id: str, 
        project_id: str,
        metadata: Dict[str, Any] = None
    ) -> UserJourney:
        """Start tracking a new user journey."""
        
        journey = UserJourney(
            journey_id=journey_id,
            user_id=user_id,
            project_id=project_id,
            start_time=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.active_journeys[journey_id] = journey
        
        # Store in Redis for persistence
        redis_client = await self.get_redis()
        await redis_client.setex(
            f"journey:{journey_id}",
            3600,  # 1 hour TTL
            json.dumps(asdict(journey), default=str)
        )
        
        logger.info(
            "Started user journey",
            extra={
                "journey_id": journey_id,
                "user_id": user_id,
                "project_id": project_id,
                "metadata": metadata
            }
        )
        
        return journey

    async def initialize(self) -> None:
        """Initialize service (stub for tests)."""
        return None

    async def get_journey_details(self, journey_id: str) -> Optional[Dict[str, Any]]:
        """Return journey details (stub for tests)."""
        journey = await self.get_journey(journey_id)
        return asdict(journey) if journey else None

    async def get_status(self) -> Dict[str, Any]:
        """Basic status info (stub)."""
        return {"ok": True, "active_journeys": len(self.active_journeys)}
    
    async def add_journey_step(
        self, 
        journey_id: str, 
        stage: JourneyStage,
        metadata: Dict[str, Any] = None
    ) -> Optional[JourneyStep]:
        """Add a step to an existing journey."""
        
        journey = await self.get_journey(journey_id)
        if not journey:
            logger.warning(f"Journey not found: {journey_id}")
            return None
        
        step = journey.add_step(stage, metadata)
        
        # Update in Redis
        await self._update_journey_in_redis(journey_id, journey)
        
        logger.info(
            "Added journey step",
            extra={
                "journey_id": journey_id,
                "stage": stage.value,
                "metadata": metadata
            }
        )
        
        return step
    
    async def complete_journey_step(
        self,
        journey_id: str,
        stage: JourneyStage,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """Complete a journey step."""
        
        journey = await self.get_journey(journey_id)
        if not journey:
            logger.warning(f"Journey not found: {journey_id}")
            return
        
        # Find the most recent step for this stage
        step = None
        for s in reversed(journey.steps):
            if s.stage == stage and s.end_time is None:
                step = s
                break
        
        if not step:
            logger.warning(f"Active step not found for stage {stage.value} in journey {journey_id}")
            return
        
        step.complete(success, error_message)
        
        # Update metadata if provided
        if metadata:
            step.metadata.update(metadata)
        
        # Update in Redis
        await self._update_journey_in_redis(journey_id, journey)
        
        # Record metrics
        await self._record_step_metrics(journey_id, step)
        
        logger.info(
            "Completed journey step",
            extra={
                "journey_id": journey_id,
                "stage": stage.value,
                "success": success,
                "duration_ms": step.duration_ms,
                "error_message": error_message
            }
        )
    
    async def complete_journey(
        self,
        journey_id: str,
        success: bool = True,
        metadata: Dict[str, Any] = None
    ):
        """Complete a user journey."""
        
        journey = await self.get_journey(journey_id)
        if not journey:
            logger.warning(f"Journey not found: {journey_id}")
            return
        
        journey.complete(success)
        
        # Update metadata if provided
        if metadata:
            journey.metadata.update(metadata)
        
        # Update in Redis with longer TTL for completed journeys
        redis_client = await self.get_redis()
        await redis_client.setex(
            f"journey:{journey_id}",
            86400,  # 24 hours for completed journeys
            json.dumps(asdict(journey), default=str)
        )
        
        # Record final metrics
        await self._record_journey_metrics(journey)
        
        # Remove from active journeys
        self.active_journeys.pop(journey_id, None)
        
        logger.info(
            "Completed user journey",
            extra={
                "journey_id": journey_id,
                "success": success,
                "total_duration_ms": journey.total_duration_ms,
                "total_steps": len(journey.steps),
                "successful_steps": len([s for s in journey.steps if s.success])
            }
        )
    
    async def get_journey(self, journey_id: str) -> Optional[UserJourney]:
        """Get journey by ID."""
        
        # Try active journeys first
        if journey_id in self.active_journeys:
            return self.active_journeys[journey_id]
        
        # Try Redis
        redis_client = await self.get_redis()
        journey_data = await redis_client.get(f"journey:{journey_id}")
        
        if journey_data:
            try:
                data = json.loads(journey_data)
                
                # Convert string timestamps back to datetime
                data['start_time'] = datetime.fromisoformat(data['start_time'])
                if data.get('end_time'):
                    data['end_time'] = datetime.fromisoformat(data['end_time'])
                
                # Convert steps
                steps = []
                for step_data in data.get('steps', []):
                    step_data['start_time'] = datetime.fromisoformat(step_data['start_time'])
                    if step_data.get('end_time'):
                        step_data['end_time'] = datetime.fromisoformat(step_data['end_time'])
                    step_data['stage'] = JourneyStage(step_data['stage'])
                    steps.append(JourneyStep(**step_data))
                
                data['steps'] = steps
                return UserJourney(**data)
                
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.error(f"Failed to deserialize journey {journey_id}: {e}")
        
        return None
    
    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        tags: Dict[str, str] = None
    ):
        """Record a system metric."""
        
        metric = SystemMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        
        self.metrics_buffer.append(metric)
        
        # Flush if buffer is full or time interval passed
        if (len(self.metrics_buffer) >= 100 or 
            time.time() - self.last_flush > self.flush_interval):
            await self._flush_metrics()
    
    async def get_journey_analytics(
        self, 
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get analytics for completed journeys."""
        
        redis_client = await self.get_redis()
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Get all journey keys
        journey_keys = await redis_client.keys("journey:*")
        
        completed_journeys = []
        for key in journey_keys:
            journey_data = await redis_client.get(key)
            if journey_data:
                try:
                    data = json.loads(journey_data)
                    if data.get('end_time'):
                        end_time = datetime.fromisoformat(data['end_time'])
                        if end_time >= cutoff_time:
                            completed_journeys.append(data)
                except (json.JSONDecodeError, ValueError):
                    continue
        
        if not completed_journeys:
            return {
                "total_journeys": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "stage_success_rates": {},
                "common_failures": []
            }
        
        # Calculate analytics
        total_journeys = len(completed_journeys)
        successful_journeys = len([j for j in completed_journeys if j.get('success')])
        success_rate = successful_journeys / total_journeys
        
        # Average duration
        durations = [j.get('total_duration_ms', 0) for j in completed_journeys if j.get('total_duration_ms')]
        avg_duration_ms = sum(durations) / len(durations) if durations else 0
        
        # Stage success rates
        stage_stats = {}
        failure_reasons = []
        
        for journey in completed_journeys:
            for step in journey.get('steps', []):
                stage = step.get('stage')
                if stage not in stage_stats:
                    stage_stats[stage] = {'total': 0, 'successful': 0}
                
                stage_stats[stage]['total'] += 1
                if step.get('success'):
                    stage_stats[stage]['successful'] += 1
                else:
                    error_msg = step.get('error_message')
                    if error_msg:
                        failure_reasons.append({
                            'stage': stage,
                            'error': error_msg,
                            'timestamp': step.get('end_time')
                        })
        
        stage_success_rates = {
            stage: stats['successful'] / stats['total']
            for stage, stats in stage_stats.items()
        }
        
        # Most common failures (last 10)
        common_failures = sorted(
            failure_reasons,
            key=lambda x: x['timestamp'] if x['timestamp'] else '',
            reverse=True
        )[:10]
        
        return {
            "total_journeys": total_journeys,
            "success_rate": success_rate,
            "avg_duration_ms": int(avg_duration_ms),
            "stage_success_rates": stage_success_rates,
            "common_failures": common_failures,
            "time_window_hours": time_window_hours
        }
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time system metrics."""
        
        redis_client = await self.get_redis()
        
        # Get active journeys count
        active_journeys_count = len(self.active_journeys)
        
        # Get metrics from last flush
        recent_metrics = {}
        if self.metrics_buffer:
            for metric in self.metrics_buffer[-10:]:  # Last 10 metrics
                recent_metrics[metric.name] = {
                    'value': metric.value,
                    'type': metric.metric_type.value,
                    'timestamp': metric.timestamp.isoformat()
                }
        
        # System health indicators
        try:
            # Redis health
            await redis_client.ping()
            redis_healthy = True
        except Exception:
            redis_healthy = False
        
        return {
            "active_journeys": active_journeys_count,
            "redis_healthy": redis_healthy,
            "metrics_buffer_size": len(self.metrics_buffer),
            "recent_metrics": recent_metrics,
            "last_flush_time": datetime.fromtimestamp(self.last_flush).isoformat()
        }
    
    async def _update_journey_in_redis(self, journey_id: str, journey: UserJourney):
        """Update journey data in Redis."""
        
        redis_client = await self.get_redis()
        await redis_client.setex(
            f"journey:{journey_id}",
            3600,  # 1 hour TTL for active journeys
            json.dumps(asdict(journey), default=str)
        )
    
    async def _record_step_metrics(self, journey_id: str, step: JourneyStep):
        """Record metrics for a completed step."""
        
        # Duration metric
        if step.duration_ms is not None:
            await self.record_metric(
                f"journey.step.duration",
                step.duration_ms,
                MetricType.HISTOGRAM,
                {"stage": step.stage.value, "success": str(step.success)}
            )
        
        # Success/failure counter
        await self.record_metric(
            f"journey.step.completion",
            1,
            MetricType.COUNTER,
            {"stage": step.stage.value, "success": str(step.success)}
        )
    
    async def _record_journey_metrics(self, journey: UserJourney):
        """Record metrics for a completed journey."""
        
        # Total duration
        if journey.total_duration_ms is not None:
            await self.record_metric(
                "journey.total.duration",
                journey.total_duration_ms,
                MetricType.HISTOGRAM,
                {"success": str(journey.success)}
            )
        
        # Journey completion counter
        await self.record_metric(
            "journey.completion",
            1,
            MetricType.COUNTER,
            {"success": str(journey.success)}
        )
        
        # Steps count
        await self.record_metric(
            "journey.steps.count",
            len(journey.steps),
            MetricType.GAUGE,
            {"success": str(journey.success)}
        )
        
        # Success rate per journey
        successful_steps = len([s for s in journey.steps if s.success])
        if journey.steps:
            step_success_rate = successful_steps / len(journey.steps)
            await self.record_metric(
                "journey.steps.success_rate",
                step_success_rate,
                MetricType.GAUGE,
                {"journey_success": str(journey.success)}
            )
    
    async def _flush_metrics(self):
        """Flush metrics buffer to storage/monitoring system."""
        
        if not self.metrics_buffer:
            return
        
        try:
            redis_client = await self.get_redis()
            
            # Store metrics in Redis for retrieval
            metrics_data = [asdict(metric) for metric in self.metrics_buffer]
            await redis_client.setex(
                f"metrics:{int(time.time())}",
                3600,  # 1 hour TTL
                json.dumps(metrics_data, default=str)
            )
            
            # Note: External monitoring integration can be added here (Prometheus, DataDog, etc.)
            logger.info(f"Flushed {len(self.metrics_buffer)} metrics to storage")
            
            self.metrics_buffer.clear()
            self.last_flush = time.time()
            
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")

# Global monitoring service instance
monitoring_service = E2EMonitoringService()

# Convenience functions for easier usage
async def start_user_journey(
    journey_id: str,
    user_id: str, 
    project_id: str,
    metadata: Dict[str, Any] = None
) -> UserJourney:
    """Start tracking a user journey."""
    return await monitoring_service.start_journey(journey_id, user_id, project_id, metadata)

async def add_journey_step(
    journey_id: str,
    stage: JourneyStage,
    metadata: Dict[str, Any] = None
) -> Optional[JourneyStep]:
    """Add a step to a journey."""
    return await monitoring_service.add_journey_step(journey_id, stage, metadata)

async def complete_journey_step(
    journey_id: str,
    stage: JourneyStage,
    success: bool = True,
    error_message: Optional[str] = None,
    metadata: Dict[str, Any] = None
):
    """Complete a journey step."""
    return await monitoring_service.complete_journey_step(
        journey_id, stage, success, error_message, metadata
    )

async def complete_user_journey(
    journey_id: str,
    success: bool = True,
    metadata: Dict[str, Any] = None
):
    """Complete a user journey."""
    return await monitoring_service.complete_journey(journey_id, success, metadata)

async def record_system_metric(
    name: str,
    value: float,
    metric_type: MetricType,
    tags: Dict[str, str] = None
):
    """Record a system metric."""
    return await monitoring_service.record_metric(name, value, metric_type, tags)

# Context manager for automatic step tracking
class JourneyStepTracker:
    """Context manager for tracking journey steps."""
    
    def __init__(
        self,
        journey_id: str,
        stage: JourneyStage,
        metadata: Dict[str, Any] = None
    ):
        self.journey_id = journey_id
        self.stage = stage
        self.metadata = metadata
        self.step = None
    
    async def __aenter__(self):
        """Start the step."""
        self.step = await add_journey_step(self.journey_id, self.stage, self.metadata)
        return self.step
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Complete the step."""
        success = exc_type is None
        error_message = str(exc_val) if exc_val else None
        
        await complete_journey_step(
            self.journey_id,
            self.stage,
            success,
            error_message
        )
        
        return False  # Don't suppress exceptions