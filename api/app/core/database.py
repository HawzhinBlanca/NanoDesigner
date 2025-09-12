"""Database health check functionality."""

import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def get_db_health() -> bool:
    """Check database connectivity and health by executing SELECT 1.

    Uses SQLAlchemy engine from services.db to perform a lightweight query.
    """
    try:
        from sqlalchemy import text
        from ..services.db import engine

        def _check() -> bool:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True

        # Run blocking DB call in a thread to avoid blocking event loop
        return await asyncio.to_thread(_check)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

async def get_prometheus_metrics() -> Dict[str, Any]:
    """Get metrics from Prometheus."""
    try:
        import httpx
        import os
        
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{prometheus_url}/api/v1/query", params={
                "query": "up"
            })
            
            if response.status_code == 200:
                data = response.json()
                # Process Prometheus metrics
                metrics = {}
                
                # Extract relevant metrics
                if data.get("data", {}).get("result"):
                    for result in data["data"]["result"]:
                        metric_name = result["metric"].get("__name__", "unknown")
                        value = float(result["value"][1]) if result.get("value") else 0.0
                        metrics[metric_name] = value
                
                return metrics
            else:
                logger.warning(f"Prometheus query failed: {response.status_code}")
                return {}
                
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        return {}
