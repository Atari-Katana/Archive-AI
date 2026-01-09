from fastapi import APIRouter
from services.metrics_service import metrics_collector_service
from services.system_service import system_service
from schemas.metrics import SystemStatusResponse, HistoricalMetricsResponse, MetricsSnapshot

router = APIRouter(tags=["metrics"])

@router.get("/metrics", response_model=SystemStatusResponse, tags=["health"])
async def get_system_status_dashboard():
    """
    System metrics and statistics (Dashboard)
    """
    return await system_service.get_system_status()

@router.get("/metrics/", response_model=HistoricalMetricsResponse, tags=["metrics"])
async def get_historical_metrics(hours: int = 1):
    """
    Get performance metrics for last N hours.
    """
    if hours < 1:
        hours = 1
    if hours > 24:
        hours = 24

    metrics = await metrics_collector_service.get_metrics(hours)

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

    return HistoricalMetricsResponse(
        metrics=metrics,
        time_range=f"{hours}h",
        summary=summary
    )

@router.get("/metrics/current")
async def get_current_metrics():
    """Get current metrics snapshot"""
    snapshot = await metrics_collector_service.collect_snapshot()
    return snapshot

@router.post("/metrics/record")
async def record_request(latency: float, success: bool = True):
    """
    Record a request for metrics tracking.
    """
    metrics_collector_service.record_request(latency, success)
    return {"status": "recorded"}

@router.delete("/metrics/")
async def clear_metrics():
    """Clear all stored metrics"""
    from memory.vector_store import vector_store # Import here to avoid circular dep if any
    
    if vector_store and vector_store.client:
        try:
            vector_store.client.delete(metrics_collector_service.metrics_key)
            return {"status": "cleared"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return {"status": "redis unavailable"}
