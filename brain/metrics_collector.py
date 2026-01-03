"""
Performance Metrics Collection Service
Collects and stores historical performance metrics for monitoring.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import time
import psutil
import httpx

try:
    from config import config
    from memory.vector_store import vector_store
except ImportError:
    # For testing without full environment
    config = None
    vector_store = None


class MetricsSnapshot(BaseModel):
    """Single metrics snapshot"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    request_count: int = 0
    avg_latency: float = 0.0
    error_rate: float = 0.0
    vorpal_status: str = "unknown"
    goblin_status: str = "unknown"
    redis_status: str = "unknown"


class MetricsResponse(BaseModel):
    """Metrics response with multiple snapshots"""
    metrics: List[MetricsSnapshot]
    time_range: str
    summary: Dict[str, float]


router = APIRouter(prefix="/metrics", tags=["Metrics"])


class MetricsCollector:
    """
    Collects performance metrics and stores in Redis.

    Metrics collected:
    - CPU usage
    - Memory usage
    - Request counts
    - Latency
    - Error rates
    - Service health status
    """

    def __init__(self):
        self.process = psutil.Process()
        self.metrics_key = "metrics:history"
        self.max_metrics = 1000  # Keep last 1000 snapshots
        self.collection_interval = 30  # Collect every 30 seconds
        self.running = False

        # Runtime stats
        self.request_count = 0
        self.total_latency = 0.0
        self.error_count = 0

    async def collect_snapshot(self) -> MetricsSnapshot:
        """Collect a single metrics snapshot"""

        # System metrics
        cpu = self.process.cpu_percent(interval=1.0)
        mem_info = self.process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024
        mem_percent = self.process.memory_percent()

        # Calculate rates
        avg_latency = (self.total_latency / self.request_count) if self.request_count > 0 else 0.0
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0.0

        # Service health checks
        vorpal_status = await self._check_service(config.VORPAL_URL if config else "http://localhost:8000")
        goblin_status = await self._check_service(config.GOBLIN_URL if config else "http://localhost:8080")
        redis_status = "healthy" if self._check_redis() else "unhealthy"

        return MetricsSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu,
            memory_mb=mem_mb,
            memory_percent=mem_percent,
            request_count=self.request_count,
            avg_latency=avg_latency,
            error_rate=error_rate,
            vorpal_status=vorpal_status,
            goblin_status=goblin_status,
            redis_status=redis_status
        )

    async def _check_service(self, url: str) -> str:
        """Check if service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{url}/health")
                return "healthy" if response.status_code == 200 else "degraded"
        except:
            return "unhealthy"

    def _check_redis(self) -> bool:
        """Check if Redis is available"""
        try:
            if vector_store and vector_store.client:
                vector_store.client.ping()
                return True
        except:
            pass
        return False

    async def store_snapshot(self, snapshot: MetricsSnapshot):
        """Store snapshot in Redis"""
        if not vector_store or not vector_store.client:
            return

        try:
            # Store as JSON in sorted set (timestamp as score)
            import json
            snapshot_json = json.dumps(snapshot.dict())
            vector_store.client.zadd(
                self.metrics_key,
                {snapshot_json: snapshot.timestamp}
            )

            # Trim to max size
            vector_store.client.zremrangebyrank(self.metrics_key, 0, -(self.max_metrics + 1))

        except Exception as e:
            print(f"Error storing metrics: {e}")

    async def get_metrics(self, hours: int = 1) -> List[MetricsSnapshot]:
        """
        Get metrics from last N hours.

        Args:
            hours: Number of hours to retrieve

        Returns:
            List of metrics snapshots
        """
        if not vector_store or not vector_store.client:
            return []

        try:
            import json

            # Calculate timestamp range
            now = time.time()
            start_time = now - (hours * 3600)

            # Get snapshots from sorted set
            snapshots_json = vector_store.client.zrangebyscore(
                self.metrics_key,
                start_time,
                now
            )

            # Parse JSON
            snapshots = []
            for snapshot_json in snapshots_json:
                data = json.loads(snapshot_json)
                snapshots.append(MetricsSnapshot(**data))

            return snapshots

        except Exception as e:
            print(f"Error retrieving metrics: {e}")
            return []

    async def start_collection(self):
        """Start background metrics collection"""
        self.running = True

        while self.running:
            try:
                snapshot = await self.collect_snapshot()
                await self.store_snapshot(snapshot)
            except Exception as e:
                print(f"Metrics collection error: {e}")

            await asyncio.sleep(self.collection_interval)

    def stop_collection(self):
        """Stop background metrics collection"""
        self.running = False

    def record_request(self, latency: float, success: bool = True):
        """
        Record a request for metrics.

        Args:
            latency: Request latency in seconds
            success: Whether request succeeded
        """
        self.request_count += 1
        self.total_latency += latency

        if not success:
            self.error_count += 1


# Global collector instance
collector = MetricsCollector()


@router.get("/", response_model=MetricsResponse)
async def get_metrics(hours: int = 1):
    """
    Get performance metrics for last N hours.

    Args:
        hours: Number of hours (default 1, max 24)

    Returns:
        Metrics snapshots with summary statistics
    """
    if hours < 1:
        hours = 1
    if hours > 24:
        hours = 24

    metrics = await collector.get_metrics(hours)

    # Calculate summary
    summary = {}
    if metrics:
        summary = {
            "avg_cpu": sum(m.cpu_percent for m in metrics) / len(metrics),
            "max_cpu": max(m.cpu_percent for m in metrics),
            "avg_memory": sum(m.memory_mb for m in metrics) / len(metrics),
            "max_memory": max(m.memory_mb for m in metrics),
            "total_requests": metrics[-1].request_count if metrics else 0,
            "avg_latency": metrics[-1].avg_latency if metrics else 0.0,
            "error_rate": metrics[-1].error_rate if metrics else 0.0,
        }

    return MetricsResponse(
        metrics=metrics,
        time_range=f"{hours}h",
        summary=summary
    )


@router.get("/current")
async def get_current_metrics():
    """Get current metrics snapshot"""
    snapshot = await collector.collect_snapshot()
    return snapshot


@router.post("/record")
async def record_request(latency: float, success: bool = True):
    """
    Record a request for metrics tracking.

    Args:
        latency: Request latency in seconds
        success: Whether request succeeded
    """
    collector.record_request(latency, success)
    return {"status": "recorded"}


@router.delete("/")
async def clear_metrics():
    """Clear all stored metrics"""
    if vector_store and vector_store.client:
        try:
            vector_store.client.delete(collector.metrics_key)
            return {"status": "cleared"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return {"status": "redis unavailable"}


# Add router to main app in brain/main.py:
# app.include_router(metrics_collector.router)

# Start collection on startup:
# @app.on_event("startup")
# async def startup():
#     asyncio.create_task(metrics_collector.collector.start_collection())
