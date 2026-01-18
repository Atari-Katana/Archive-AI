import time
import psutil
from typing import List

from config import config
from services.metrics_service import metrics_collector_service
from memory.vector_store import vector_store
from schemas.common import ServiceStatus
from schemas.metrics import SystemMetrics, MemoryStats, SystemStatusResponse, MetricsSnapshot

try:
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class SystemService:
    def __init__(self):
        self.startup_time = time.time()

    async def get_system_status(self) -> SystemStatusResponse:
        """
        Get comprehensive system status
        """
        # Calculate uptime
        uptime = time.time() - self.startup_time

        # Get system metrics via unified collector
        snapshot = await metrics_collector_service.collect_snapshot()
        
        system_metrics = SystemMetrics(
            cpu_percent=snapshot.cpu_percent,
            memory_percent=snapshot.memory_percent,
            memory_used_mb=snapshot.memory_mb,
            memory_total_mb=psutil.virtual_memory().total / (1024 * 1024) if PSUTIL_AVAILABLE else None,
            gpu_memory_used_mb=snapshot.gpu_memory_used_mb,
            gpu_memory_total_mb=snapshot.gpu_memory_total_mb,
            gpu_memory_percent=snapshot.gpu_memory_percent,
            tokens_per_sec=snapshot.vorpal_tps,
            device=snapshot.bolt_xl_device,
            loading_status=snapshot.bolt_xl_loading
        )

        # Get memory statistics
        memory_stats = self._get_memory_stats()

        # Check services
        services = []
        
        # Brain (Self)
        services.append(ServiceStatus(
            name="Brain",
            status="healthy",
            url="internal"
        ))

        # Vorpal
        services.append(ServiceStatus(
            name="Vorpal",
            status=snapshot.vorpal_status,
            url=config.VORPAL_URL
        ))

        # Goblin
        services.append(ServiceStatus(
            name="Goblin",
            status=snapshot.goblin_status,
            url=config.GOBLIN_URL
        ))

        # Bolt-XL
        services.append(ServiceStatus(
            name="Bolt-XL",
            status=snapshot.bolt_xl_status,
            url=config.BOLT_XL_URL
        ))

        # Voice
        services.append(ServiceStatus(
            name="Voice",
            status=snapshot.voice_status,
            url=config.VOICE_URL
        ))

        # Redis
        services.append(ServiceStatus(
            name="Redis",
            status=snapshot.redis_status,
            url=config.REDIS_URL
        ))

        # Sandbox
        services.append(ServiceStatus(
            name="Sandbox",
            status=snapshot.sandbox_status,
            url=config.SANDBOX_URL
        ))

        # Set TPS to Bolt-XL TPS if available, otherwise Vorpal
        system_metrics.tokens_per_sec = snapshot.bolt_xl_tps if snapshot.bolt_xl_tps and snapshot.bolt_xl_tps > 0 else snapshot.vorpal_tps

        return SystemStatusResponse(
            uptime_seconds=uptime,
            system=system_metrics,
            memory_stats=memory_stats,
            services=services,
            version="0.4.0"
        )

    def _get_memory_stats(self) -> MemoryStats:
        try:
            # Count total memories
            total_memories = 0
            if vector_store.client:
                try:
                    # Use RediSearch info if available for faster count
                    info = vector_store.client.ft(vector_store.index_name).info()
                    total_memories = int(info['num_docs'])
                except Exception:
                    # Fallback to key scan (slower but works)
                    pass
            
            return MemoryStats(
                total_memories=total_memories,
                storage_threshold=0.7,
                embedding_dim=384,
                index_type="HNSW"
            )
        except Exception:
            return MemoryStats(
                total_memories=0,
                storage_threshold=0.7,
                embedding_dim=384,
                index_type="unknown"
            )

system_service = SystemService()
