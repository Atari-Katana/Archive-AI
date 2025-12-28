#!/usr/bin/env python3
"""
VRAM Stress Test (Chunk 1.5)
Hammers both Vorpal and Goblin engines simultaneously to verify VRAM stability.
"""

import argparse
import time
import subprocess
import threading
import sys
from datetime import datetime
import requests


class VRAMMonitor:
    """Monitor GPU VRAM usage"""

    def __init__(self):
        self.readings = []
        self.monitoring = False

    def get_vram_usage(self):
        """Get current VRAM usage in MB"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used',
                 '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                check=True
            )
            return int(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def monitor_loop(self, interval=2):
        """Monitor VRAM usage at regular intervals"""
        while self.monitoring:
            usage = self.get_vram_usage()
            if usage is not None:
                timestamp = datetime.now().isoformat()
                self.readings.append((timestamp, usage))
                print(f"[{timestamp}] VRAM: {usage / 1024:.2f} GB")
            time.sleep(interval)

    def start(self, interval=2):
        """Start monitoring in background thread"""
        self.monitoring = True
        self.thread = threading.Thread(
            target=self.monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.thread.start()

    def stop(self):
        """Stop monitoring"""
        self.monitoring = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=5)

    def get_stats(self):
        """Get VRAM usage statistics"""
        if not self.readings:
            return None

        usages = [r[1] for r in self.readings]
        return {
            'min_mb': min(usages),
            'max_mb': max(usages),
            'avg_mb': sum(usages) / len(usages),
            'readings': len(usages)
        }


def stress_vorpal(duration, results):
    """Stress test Vorpal engine"""
    url = "http://localhost:8000/v1/completions"

    start_time = time.time()
    requests_made = 0
    errors = 0

    while time.time() - start_time < duration:
        try:
            payload = {
                "model": "vorpal",
                "prompt": f"Test prompt {requests_made}",
                "max_tokens": 50
            }
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                requests_made += 1
            else:
                errors += 1
        except requests.exceptions.RequestException as e:
            errors += 1
            print(f"Vorpal error: {e}")

        time.sleep(0.5)  # Small delay between requests

    results['vorpal'] = {
        'requests': requests_made,
        'errors': errors
    }


def stress_goblin(duration, results):
    """Stress test Goblin engine"""
    url = "http://localhost:8080/completion"

    start_time = time.time()
    requests_made = 0
    errors = 0

    while time.time() - start_time < duration:
        try:
            payload = {
                "prompt": f"Test prompt {requests_made}",
                "n_predict": 50
            }
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                requests_made += 1
            else:
                errors += 1
        except requests.exceptions.RequestException as e:
            errors += 1
            print(f"Goblin error: {e}")

        time.sleep(1.0)  # Goblin is slower, longer delay

    results['goblin'] = {
        'requests': requests_made,
        'errors': errors
    }


def main():
    parser = argparse.ArgumentParser(
        description='VRAM stress test for Vorpal + Goblin'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=600,
        help='Test duration in seconds (default: 600)'
    )
    parser.add_argument(
        '--monitor-interval',
        type=int,
        default=2,
        help='VRAM monitoring interval in seconds (default: 2)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("VRAM Stress Test - Chunk 1.5")
    print("=" * 60)
    print(f"Duration: {args.duration} seconds")
    print(f"Monitor interval: {args.monitor_interval} seconds")
    print()

    # Check GPU availability
    print("[1/5] Checking GPU availability...")
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total',
             '--format=csv,noheader'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"GPU: {result.stdout.strip()}")
        print("✅ PASS: GPU detected")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FAIL: nvidia-smi not found or GPU not available")
        return 1

    # Check if services are running
    print("\n[2/5] Checking if services are running...")
    services_ok = True

    try:
        requests.get("http://localhost:8000/health", timeout=5)
        print("✅ Vorpal: Running")
    except requests.exceptions.RequestException:
        print("❌ Vorpal: Not responding")
        services_ok = False

    try:
        requests.get("http://localhost:8080/health", timeout=5)
        print("✅ Goblin: Running")
    except requests.exceptions.RequestException:
        print("❌ Goblin: Not responding")
        services_ok = False

    if not services_ok:
        msg = "\n❌ FAIL: Start services with: "
        msg += "docker-compose up -d vorpal goblin"
        print(msg)
        return 1

    # Start VRAM monitoring
    print("\n[3/5] Starting VRAM monitoring...")
    monitor = VRAMMonitor()
    monitor.start(interval=args.monitor_interval)

    # Get baseline VRAM
    time.sleep(2)
    baseline = monitor.get_vram_usage()
    print(f"Baseline VRAM: {baseline / 1024:.2f} GB")

    # Run stress test
    print(f"\n[4/5] Running stress test ({args.duration}s)...")
    print("Hammering both engines simultaneously...")
    print()

    results = {}
    threads = [
        threading.Thread(target=stress_vorpal, args=(args.duration, results)),
        threading.Thread(target=stress_goblin, args=(args.duration, results))
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Stop monitoring
    monitor.stop()

    # Analyze results
    print("\n[5/5] Analyzing results...")
    stats = monitor.get_stats()

    if stats is None:
        print("❌ FAIL: No VRAM readings collected")
        return 1

    print("\nVRAM Statistics:")
    print(f"  Min: {stats['min_mb'] / 1024:.2f} GB")
    print(f"  Max: {stats['max_mb'] / 1024:.2f} GB")
    print(f"  Avg: {stats['avg_mb'] / 1024:.2f} GB")
    print(f"  Readings: {stats['readings']}")

    print("\nEngine Performance:")
    if 'vorpal' in results:
        print(f"  Vorpal: {results['vorpal']['requests']} requests, "
              f"{results['vorpal']['errors']} errors")
    if 'goblin' in results:
        print(f"  Goblin: {results['goblin']['requests']} requests, "
              f"{results['goblin']['errors']} errors")

    # Check pass criteria
    print("\n" + "=" * 60)
    print("Pass Criteria Check:")
    print("=" * 60)

    all_pass = True

    # 1. No OOM crashes (engines still responding)
    if results.get('vorpal', {}).get('requests', 0) > 0 and \
       results.get('goblin', {}).get('requests', 0) > 0:
        print("✅ PASS: No OOM crashes (both engines responding)")
    else:
        print("❌ FAIL: One or both engines stopped responding")
        all_pass = False

    # 2. VRAM stays between 13-14.5GB
    max_gb = stats['max_mb'] / 1024
    if 13.0 <= max_gb <= 14.5:
        print(f"✅ PASS: VRAM within range ({max_gb:.2f}GB)")
    else:
        print(f"❌ FAIL: VRAM out of range ({max_gb:.2f}GB, "
              f"expected 13-14.5GB)")
        all_pass = False

    # 3. No memory leaks (usage stable)
    first_half = [r[1] for r in monitor.readings[:len(monitor.readings)//2]]
    second_half = [r[1] for r in monitor.readings[len(monitor.readings)//2:]]

    if first_half and second_half:
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        growth = ((avg_second - avg_first) / avg_first) * 100

        if abs(growth) < 5:  # Less than 5% growth
            print(f"✅ PASS: Memory stable (growth: {growth:.1f}%)")
        else:
            print(f"⚠️  WARNING: Possible memory leak (growth: {growth:.1f}%)")

    print()
    if all_pass:
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nChunk 1.5 pass criteria met.")
        return 0
    else:
        print("=" * 60)
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
