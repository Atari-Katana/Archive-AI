from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import time
import psutil
import httpx
import json

from config import config
from memory.vector_store import vector_store
from schemas.metrics import MetricsSnapshot

class MetricsCollector:
    """
    Collects performance metrics and stores in Redis.
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
        
        # Engine stats state
        self.last_vorpal_tokens = 0.0
        self.last_vorpal_time = time.time()

    async def collect_snapshot(self) -> MetricsSnapshot:
        """Collect a single metrics snapshot"""

        # System metrics
        cpu = self.process.cpu_percent(interval=1.0)
        mem_info = self.process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024
        mem_percent = self.process.memory_percent()

        # Engine metrics
        vorpal_url = config.VORPAL_URL
        goblin_url = config.GOBLIN_URL
        
        vorpal_metrics = await self._get_engine_metrics(vorpal_url, "vllm")
        # Goblin (llama.cpp) metrics logic can be added here if needed
        goblin_metrics = {"healthy": False, "tps": 0.0} 

        # Aggregate GPU stats (simple sum/avg for now)
        gpu_used = vorpal_metrics.get("gpu_used_mb")
        gpu_total = vorpal_metrics.get("gpu_total_mb")
        
        gpu_percent = None
        if gpu_used and gpu_total and gpu_total > 0:
            gpu_percent = (gpu_used / gpu_total) * 100

        # Calculate rates
        avg_latency = (self.total_latency / self.request_count) if self.request_count > 0 else 0.0
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0.0

        # Service health checks
        vorpal_status = "healthy" if vorpal_metrics.get("healthy") else "unhealthy"
        bolt_xl_status = await self._check_service(config.BOLT_XL_URL)
        goblin_status = await self._check_service(goblin_url)
        redis_status = "healthy" if self._check_redis() else "unhealthy"
        sandbox_status = await self._check_service(config.SANDBOX_URL)
        voice_status = await self._check_service(config.VOICE_URL)

        # Get Bolt-XL TPS and Device info from Redis
        bolt_xl_tps = 0.0
        bolt_xl_device = "Unknown"
        bolt_xl_loading = "Ready"

        if vector_store and vector_store.client:
            try:
                tps_val = vector_store.client.get("metrics:bolt_xl:tps")
                if tps_val:
                    bolt_xl_tps = float(tps_val)

                device_val = vector_store.client.get("bolt_xl:device")
                if device_val:
                    bolt_xl_device = device_val.decode('utf-8') if isinstance(device_val, bytes) else str(device_val)

                loading_val = vector_store.client.get("bolt_xl:loading_status")
                if loading_val:
                    bolt_xl_loading = loading_val.decode('utf-8') if isinstance(loading_val, bytes) else str(loading_val)
            except:
                pass

        return MetricsSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu,
            memory_mb=mem_mb,
            memory_percent=mem_percent,
            gpu_memory_used_mb=gpu_used,
            gpu_memory_total_mb=gpu_total,
            gpu_memory_percent=gpu_percent,
            request_count=self.request_count,
            avg_latency=avg_latency,
            error_rate=error_rate,
            vorpal_status=vorpal_status,
            bolt_xl_status=bolt_xl_status,
            goblin_status=goblin_status,
            redis_status=redis_status,
            sandbox_status=sandbox_status,
            voice_status=voice_status,
            vorpal_tps=vorpal_metrics.get("tps"),
            bolt_xl_tps=bolt_xl_tps,
            goblin_tps=goblin_metrics.get("tps"),
            bolt_xl_device=bolt_xl_device,
            bolt_xl_loading=bolt_xl_loading
        )

    async def _get_engine_metrics(self, url: str, engine_type: str) -> Dict[str, Any]:
        """Fetch metrics from engine"""
        result = {"healthy": False, "tps": 0.0, "gpu_used_mb": None, "gpu_total_mb": None}
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                # check health
                try:
                    health = await client.get(f"{url}/health")
                    if health.status_code == 200:
                        result["healthy"] = True
                except:
                    pass
                
                if not result["healthy"]:
                    try:
                        models = await client.get(f"{url}/v1/models")
                        if models.status_code == 200:
                            result["healthy"] = True
                    except:
                        pass
                
                # Fetch metrics
                try:
                    metrics_resp = await client.get(f"{url}/metrics")
                    if metrics_resp.status_code == 200:
                        data = metrics_resp.text
                        
                        if engine_type == "vllm":
                            current_tokens = 0.0
                            found_tokens = False
                            
                            for line in data.split('\n'):
                                if line.startswith('vllm:kv_cache_usage_perc'):
                                    try:
                                        percent = float(line.split()[-1])
                                        # Estimate VRAM (Assume 16GB total)
                                        result["gpu_total_mb"] = 16384.0
                                        # Base usage (model weights ~6GB) + Cache usage (active ctx)
                                        # This is a rough heuristic for the meter
                                        result["gpu_used_mb"] = 6144.0 + (10240.0 * percent)
                                    except:
                                        pass
                                elif line.startswith('vllm:generation_tokens_total'):
                                    try:
                                        current_tokens = float(line.split()[-1])
                                        found_tokens = True
                                    except:
                                        pass
                            
                            # Calculate TPS delta
                            if found_tokens:
                                now = time.time()
                                time_diff = now - self.last_vorpal_time
                                token_diff = current_tokens - self.last_vorpal_tokens
                                
                                if time_diff > 0 and token_diff >= 0:
                                    # If tokens haven't changed, decay the speed to 0 slowly or just show 0
                                    # Real-time monitoring usually wants instantaneous speed
                                    result["tps"] = token_diff / time_diff
                                
                                # Update state
                                self.last_vorpal_tokens = current_tokens
                                self.last_vorpal_time = now

                except:
                    pass
        except:
            pass
        return result

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
metrics_collector_service = MetricsCollector()
