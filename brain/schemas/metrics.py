from pydantic import BaseModel
from typing import Optional, List, Dict
from .common import ServiceStatus

class SystemMetrics(BaseModel):
    """System resource metrics for status dashboard"""
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None
    gpu_memory_percent: Optional[float] = None
    tokens_per_sec: Optional[float] = None
    device: Optional[str] = None
    loading_status: Optional[str] = None

class MemoryStats(BaseModel):
    """Memory storage statistics"""
    total_memories: int
    storage_threshold: float
    embedding_dim: int
    index_type: str

class SystemStatusResponse(BaseModel):
    """Complete system status response (Dashboard)"""
    uptime_seconds: float
    system: Optional[SystemMetrics] = None
    memory_stats: MemoryStats
    services: List[ServiceStatus]
    version: str

class MetricsSnapshot(BaseModel):
    """Single metrics snapshot for history"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None
    gpu_memory_percent: Optional[float] = None
    request_count: int = 0
    avg_latency: float = 0.0
    error_rate: float = 0.0
    vorpal_status: str = "unknown"
    bolt_xl_status: str = "unknown"
    goblin_status: str = "unknown"
    redis_status: str = "unknown"
    sandbox_status: str = "unknown"
    voice_status: str = "unknown"
    vorpal_tps: Optional[float] = None
    bolt_xl_tps: Optional[float] = None
    goblin_tps: Optional[float] = None
    bolt_xl_device: Optional[str] = "Unknown"
    bolt_xl_loading: Optional[str] = "Ready"

class HistoricalMetricsResponse(BaseModel):
    """Metrics response with multiple snapshots (History)"""
    metrics: List[MetricsSnapshot]
    time_range: str
    summary: Dict[str, float]
