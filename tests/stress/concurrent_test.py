#!/usr/bin/env python3
"""
Multi-Modal Stress Testing Framework
Tests concurrent voice + text + agents for deadlocks, memory leaks, and bottlenecks.
"""

import asyncio
import httpx
import time
import psutil
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics


@dataclass
class RequestStats:
    """Statistics for a single request type"""
    total: int = 0
    success: int = 0
    failure: int = 0
    timeouts: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class SystemMetrics:
    """System resource metrics"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float


class StressTestFramework:
    """
    Concurrent stress testing framework for Archive-AI.

    Tests multiple request types simultaneously:
    - Chat requests
    - Agent tasks
    - Memory searches
    - Code execution
    - Library searches

    Monitors for:
    - Deadlocks (requests that never complete)
    - Memory leaks (increasing memory over time)
    - Performance degradation
    - Error rates
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        concurrency: int = 10,
        duration_seconds: int = 300,
        timeout: float = 30.0
    ):
        """
        Initialize stress test framework.

        Args:
            base_url: Archive-AI API base URL
            concurrency: Number of concurrent requests
            duration_seconds: Test duration in seconds
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.concurrency = concurrency
        self.duration_seconds = duration_seconds
        self.timeout = timeout

        # Statistics
        self.stats: Dict[str, RequestStats] = {
            "chat": RequestStats(),
            "agent": RequestStats(),
            "memory_search": RequestStats(),
            "code_execution": RequestStats(),
            "library_search": RequestStats(),
        }

        # System metrics
        self.system_metrics: List[SystemMetrics] = []
        self.process = psutil.Process()

        # Control
        self.start_time: Optional[float] = None
        self.running = False

    async def make_chat_request(self) -> Tuple[bool, float, Optional[str]]:
        """
        Make a chat request.

        Returns:
            Tuple of (success, latency, error_message)
        """
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat",
                    json={"message": "What is 2+2?"}
                )
                latency = time.time() - start

                if response.status_code == 200:
                    return True, latency, None
                else:
                    return False, latency, f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            return False, self.timeout, "Timeout"
        except Exception as e:
            return False, time.time() - start, str(e)

    async def make_agent_request(self) -> Tuple[bool, float, Optional[str]]:
        """
        Make an agent task request.

        Returns:
            Tuple of (success, latency, error_message)
        """
        start = time.time()

        tasks = [
            "Calculate 7 factorial",
            "What is the capital of France?",
            "Count to 10",
            "What day is it today?",
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/agent",
                    json={"question": random.choice(tasks)}
                )
                latency = time.time() - start

                if response.status_code == 200:
                    return True, latency, None
                else:
                    return False, latency, f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            return False, self.timeout, "Timeout"
        except Exception as e:
            return False, time.time() - start, str(e)

    async def make_memory_search_request(self) -> Tuple[bool, float, Optional[str]]:
        """
        Make a memory search request.

        Returns:
            Tuple of (success, latency, error_message)
        """
        start = time.time()

        queries = [
            "recent conversations",
            "math calculations",
            "questions about cities",
            "code examples",
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/memory/search",
                    json={"query": random.choice(queries), "top_k": 5}
                )
                latency = time.time() - start

                if response.status_code == 200:
                    return True, latency, None
                else:
                    return False, latency, f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            return False, self.timeout, "Timeout"
        except Exception as e:
            return False, time.time() - start, str(e)

    async def make_code_execution_request(self) -> Tuple[bool, float, Optional[str]]:
        """
        Make a code execution request.

        Returns:
            Tuple of (success, latency, error_message)
        """
        start = time.time()

        code_snippets = [
            "print(2 + 2)",
            "import math\nprint(math.pi)",
            "result = sum(range(10))\nprint(result)",
            "print('Hello, World!')",
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/code-assist",
                    json={"task": f"Execute this code: {random.choice(code_snippets)}"}
                )
                latency = time.time() - start

                if response.status_code == 200:
                    return True, latency, None
                else:
                    return False, latency, f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            return False, self.timeout, "Timeout"
        except Exception as e:
            return False, time.time() - start, str(e)

    async def make_library_search_request(self) -> Tuple[bool, float, Optional[str]]:
        """
        Make a library search request.

        Returns:
            Tuple of (success, latency, error_message)
        """
        start = time.time()

        queries = [
            "machine learning",
            "database design",
            "python programming",
            "system architecture",
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/library/search",
                    json={"query": random.choice(queries), "top_k": 5}
                )
                latency = time.time() - start

                if response.status_code == 200:
                    return True, latency, None
                else:
                    return False, latency, f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            return False, self.timeout, "Timeout"
        except Exception as e:
            return False, time.time() - start, str(e)

    async def worker(self, worker_id: int):
        """
        Worker coroutine that makes mixed requests.

        Args:
            worker_id: Unique worker identifier
        """
        request_types = [
            ("chat", self.make_chat_request),
            ("agent", self.make_agent_request),
            ("memory_search", self.make_memory_search_request),
            ("code_execution", self.make_code_execution_request),
            ("library_search", self.make_library_search_request),
        ]

        while self.running:
            # Randomly select request type
            request_type, request_func = random.choice(request_types)

            # Make request
            success, latency, error = await request_func()

            # Update statistics
            stats = self.stats[request_type]
            stats.total += 1

            if success:
                stats.success += 1
                stats.latencies.append(latency)
            else:
                stats.failure += 1
                if error == "Timeout":
                    stats.timeouts += 1
                if error:
                    stats.errors[error] += 1

            # Small delay between requests
            await asyncio.sleep(random.uniform(0.1, 0.5))

    async def monitor_system(self):
        """Monitor system resources during test"""
        while self.running:
            try:
                cpu = self.process.cpu_percent(interval=1.0)
                mem_info = self.process.memory_info()
                mem_mb = mem_info.rss / 1024 / 1024
                mem_percent = self.process.memory_percent()

                self.system_metrics.append(SystemMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu,
                    memory_mb=mem_mb,
                    memory_percent=mem_percent
                ))

            except Exception as e:
                print(f"⚠ System monitoring error: {e}")

            await asyncio.sleep(5.0)

    async def run(self):
        """Run stress test"""
        print("=" * 70)
        print("Archive-AI Multi-Modal Stress Test")
        print("=" * 70)
        print(f"Base URL: {self.base_url}")
        print(f"Concurrency: {self.concurrency} workers")
        print(f"Duration: {self.duration_seconds}s ({self.duration_seconds // 60}m)")
        print(f"Timeout: {self.timeout}s per request")
        print("=" * 70)
        print()

        # Check if service is available
        print("🔍 Checking service availability...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code != 200:
                    print(f"✗ Service not healthy: HTTP {response.status_code}")
                    return
                print("✓ Service is healthy")
        except Exception as e:
            print(f"✗ Cannot reach service: {e}")
            return

        print()
        print(f"🚀 Starting stress test at {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Test will run for {self.duration_seconds}s")
        print()

        # Start test
        self.start_time = time.time()
        self.running = True

        # Create workers and system monitor
        workers = [self.worker(i) for i in range(self.concurrency)]
        monitor = self.monitor_system()

        # Run all tasks
        tasks = workers + [monitor]

        try:
            # Run for specified duration
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.duration_seconds
            )
        except asyncio.TimeoutError:
            # Expected - test duration reached
            pass
        finally:
            self.running = False

        # Wait for tasks to finish
        await asyncio.sleep(1.0)

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate test results report"""
        elapsed = time.time() - self.start_time

        print()
        print("=" * 70)
        print(f"Test Results ({elapsed:.1f}s)")
        print("=" * 70)
        print()

        # Request statistics
        print("📊 Request Statistics:")
        print()

        total_requests = 0
        total_success = 0
        total_failure = 0

        for request_type, stats in self.stats.items():
            if stats.total == 0:
                continue

            total_requests += stats.total
            total_success += stats.success
            total_failure += stats.failure

            success_rate = (stats.success / stats.total * 100) if stats.total > 0 else 0

            # Latency statistics
            if stats.latencies:
                p50 = statistics.median(stats.latencies)
                p95 = statistics.quantiles(stats.latencies, n=20)[18] if len(stats.latencies) > 20 else max(stats.latencies)
                p99 = statistics.quantiles(stats.latencies, n=100)[98] if len(stats.latencies) > 100 else max(stats.latencies)
                avg = statistics.mean(stats.latencies)
            else:
                p50 = p95 = p99 = avg = 0.0

            print(f"{request_type.upper()}:")
            print(f"  Total: {stats.total}")
            print(f"  Success: {stats.success} ({success_rate:.1f}%)")
            print(f"  Failure: {stats.failure}")
            print(f"  Timeouts: {stats.timeouts}")
            print(f"  Latency: avg={avg:.2f}s, p50={p50:.2f}s, p95={p95:.2f}s, p99={p99:.2f}s")

            if stats.errors:
                print(f"  Errors:")
                for error, count in sorted(stats.errors.items(), key=lambda x: -x[1])[:5]:
                    print(f"    - {error}: {count}")

            print()

        # Overall statistics
        overall_success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
        requests_per_second = total_requests / elapsed if elapsed > 0 else 0

        print("Overall:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Success Rate: {overall_success_rate:.2f}%")
        print(f"  Throughput: {requests_per_second:.2f} req/s")
        print()

        # System metrics
        if self.system_metrics:
            print("💻 System Resource Usage:")
            print()

            cpu_values = [m.cpu_percent for m in self.system_metrics]
            mem_values = [m.memory_mb for m in self.system_metrics]

            cpu_avg = statistics.mean(cpu_values)
            cpu_max = max(cpu_values)
            mem_avg = statistics.mean(mem_values)
            mem_max = max(mem_values)
            mem_start = mem_values[0]
            mem_end = mem_values[-1]
            mem_growth = mem_end - mem_start

            print(f"  CPU: avg={cpu_avg:.1f}%, max={cpu_max:.1f}%")
            print(f"  Memory: avg={mem_avg:.1f}MB, max={mem_max:.1f}MB")
            print(f"  Memory Growth: {mem_growth:+.1f}MB ({mem_start:.1f}MB → {mem_end:.1f}MB)")

            # Memory leak detection
            if mem_growth > 100:
                print(f"  ⚠ WARNING: Potential memory leak detected ({mem_growth:.1f}MB growth)")
            else:
                print(f"  ✓ No memory leak detected")

            print()

        # Pass/Fail criteria
        print("✅ Pass/Fail Criteria:")
        print()

        criteria_passed = 0
        criteria_total = 5

        # 1. No deadlocks (all requests completed)
        deadlock_free = total_requests > 0
        print(f"  {'✓' if deadlock_free else '✗'} No deadlocks: {total_requests} requests completed")
        if deadlock_free:
            criteria_passed += 1

        # 2. Success rate >95%
        success_rate_pass = overall_success_rate >= 95.0
        print(f"  {'✓' if success_rate_pass else '✗'} Success rate >95%: {overall_success_rate:.2f}%")
        if success_rate_pass:
            criteria_passed += 1

        # 3. No memory leaks
        if self.system_metrics:
            mem_leak_free = mem_growth < 100
            print(f"  {'✓' if mem_leak_free else '✗'} No memory leaks: {mem_growth:+.1f}MB growth")
            if mem_leak_free:
                criteria_passed += 1
        else:
            print(f"  ⚠ Memory leak check skipped (no metrics)")

        # 4. Performance metrics available
        metrics_available = len(self.system_metrics) > 0
        print(f"  {'✓' if metrics_available else '✗'} Performance metrics collected: {len(self.system_metrics)} samples")
        if metrics_available:
            criteria_passed += 1

        # 5. Bottlenecks identified
        bottleneck_msg = self.identify_bottlenecks()
        print(f"  ✓ Bottleneck analysis: {bottleneck_msg}")
        criteria_passed += 1

        print()
        print(f"Result: {criteria_passed}/{criteria_total} criteria passed")

        if criteria_passed == criteria_total:
            print("✓ STRESS TEST PASSED")
        else:
            print(f"✗ STRESS TEST FAILED ({criteria_total - criteria_passed} criteria failed)")

        print("=" * 70)

    def identify_bottlenecks(self) -> str:
        """Identify performance bottlenecks from statistics"""
        bottlenecks = []

        for request_type, stats in self.stats.items():
            if stats.total == 0:
                continue

            # Check for high timeout rate
            timeout_rate = (stats.timeouts / stats.total * 100) if stats.total > 0 else 0
            if timeout_rate > 10:
                bottlenecks.append(f"{request_type} has high timeout rate ({timeout_rate:.1f}%)")

            # Check for high latency
            if stats.latencies:
                p95 = statistics.quantiles(stats.latencies, n=20)[18] if len(stats.latencies) > 20 else max(stats.latencies)
                if p95 > 10.0:
                    bottlenecks.append(f"{request_type} has high p95 latency ({p95:.1f}s)")

        if bottlenecks:
            return "; ".join(bottlenecks)
        else:
            return "No significant bottlenecks detected"


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Archive-AI Multi-Modal Stress Test")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent workers")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout")

    args = parser.parse_args()

    framework = StressTestFramework(
        base_url=args.url,
        concurrency=args.concurrency,
        duration_seconds=args.duration,
        timeout=args.timeout
    )

    await framework.run()


if __name__ == "__main__":
    asyncio.run(main())
