#!/usr/bin/env python3
"""
Parse performance test log and generate comprehensive report
"""

import re
import json
import statistics
from typing import List, Dict
from pathlib import Path


def parse_test_result(line: str, iteration: int) -> Dict:
    """Parse a single test result line"""
    # Pattern: [N] Running test_name... ✓ 123.4ms, 56.7 tok/s
    # or: [N] Running test_name... ✗ error

    match_success = re.search(r'\[(\d+)\] Running (\w+)\.\.\. ✓ ([\d.]+)ms, ([\d.]+) tok/s', line)
    match_failure = re.search(r'\[(\d+)\] Running (\w+)\.\.\. ✗ (.+)$', line)

    if match_success:
        return {
            "iteration": int(match_success.group(1)),
            "test_name": match_success.group(2),
            "success": True,
            "latency_ms": float(match_success.group(3)),
            "tokens_per_sec": float(match_success.group(4)),
        }
    elif match_failure:
        return {
            "iteration": int(match_failure.group(1)),
            "test_name": match_failure.group(2),
            "success": False,
            "error": match_failure.group(3),
        }

    return None


def categorize_test(test_name: str) -> str:
    """Categorize test by name"""
    if test_name.startswith("simple"):
        return "simple"
    elif test_name.startswith("reasoning"):
        return "reasoning"
    elif test_name.startswith("code"):
        return "code"
    elif test_name.startswith("summarization"):
        return "summarization"
    elif test_name.startswith("conversation"):
        return "conversation"
    return "unknown"


def calc_percentiles(data: List[float]) -> Dict:
    """Calculate percentile statistics"""
    if not data:
        return {}
    sorted_data = sorted(data)
    return {
        "min": min(data),
        "max": max(data),
        "mean": statistics.mean(data),
        "median": statistics.median(data),
        "p50": statistics.median(data),
        "p90": sorted_data[int(len(sorted_data) * 0.90)] if len(sorted_data) > 10 else sorted_data[-1],
        "p95": sorted_data[int(len(sorted_data) * 0.95)] if len(sorted_data) > 20 else sorted_data[-1],
        "p99": sorted_data[int(len(sorted_data) * 0.99)] if len(sorted_data) > 100 else sorted_data[-1],
        "stdev": statistics.stdev(data) if len(data) > 1 else 0,
    }


def generate_report(log_file: str) -> Dict:
    """Generate comprehensive report from log file"""

    results = []

    # Parse log file
    with open(log_file, 'r') as f:
        for line in f:
            result = parse_test_result(line.strip(), 0)
            if result:
                result["category"] = categorize_test(result["test_name"])
                results.append(result)

    # Filter successful results
    successful = [r for r in results if r.get("success", False)]
    failed = [r for r in results if not r.get("success", False)]

    if not successful:
        return {
            "error": "No successful tests to analyze",
            "total_tests": len(results),
            "failed_tests": len(failed),
        }

    # Overall statistics
    latencies = [r["latency_ms"] for r in successful]
    throughputs = [r["tokens_per_sec"] for r in successful]

    # Per-category statistics
    categories = {}
    for result in successful:
        cat = result["category"]
        if cat not in categories:
            categories[cat] = {
                "latencies": [],
                "throughputs": [],
                "count": 0,
            }
        categories[cat]["latencies"].append(result["latency_ms"])
        categories[cat]["throughputs"].append(result["tokens_per_sec"])
        categories[cat]["count"] += 1

    # Per-test statistics
    tests = {}
    for result in successful:
        test_name = result["test_name"]
        if test_name not in tests:
            tests[test_name] = {
                "latencies": [],
                "throughputs": [],
                "count": 0,
                "category": result["category"],
            }
        tests[test_name]["latencies"].append(result["latency_ms"])
        tests[test_name]["throughputs"].append(result["tokens_per_sec"])
        tests[test_name]["count"] += 1

    # Determine number of iterations
    max_iteration = max([r.get("iteration", 0) for r in results])

    # Calculate statistics
    report = {
        "summary": {
            "total_tests": len(results),
            "successful_tests": len(successful),
            "failed_tests": len(failed),
            "success_rate": len(successful) / len(results) * 100 if results else 0,
            "iterations_completed": max_iteration,
            "tests_per_iteration": 7,
        },
        "overall": {
            "latency_ms": calc_percentiles(latencies),
            "throughput_tokens_per_sec": calc_percentiles(throughputs),
        },
        "by_category": {},
        "by_test": {},
        "failures": {},
    }

    # Per-category stats
    for cat, data in categories.items():
        report["by_category"][cat] = {
            "count": data["count"],
            "latency_ms": calc_percentiles(data["latencies"]),
            "throughput_tokens_per_sec": calc_percentiles(data["throughputs"]),
        }

    # Per-test stats
    for test_name, data in tests.items():
        report["by_test"][test_name] = {
            "count": data["count"],
            "category": data["category"],
            "latency_ms": calc_percentiles(data["latencies"]),
            "throughput_tokens_per_sec": calc_percentiles(data["throughputs"]),
        }

    # Failure analysis
    if failed:
        failure_reasons = {}
        for fail in failed:
            reason = fail.get("error", "unknown")
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        report["failures"] = {
            "count": len(failed),
            "reasons": failure_reasons,
        }

    return report


def print_report(report: Dict):
    """Print formatted report to console"""

    print("\n" + "="*80)
    print("INFERENCE PERFORMANCE TEST REPORT - 250 ITERATIONS")
    print("="*80)

    # Summary
    summary = report["summary"]
    print(f"\n📊 SUMMARY")
    print(f"   Iterations:       {summary['iterations_completed']}")
    print(f"   Total Tests:      {summary['total_tests']}")
    print(f"   Successful:       {summary['successful_tests']} ({summary['success_rate']:.2f}%)")
    print(f"   Failed:           {summary['failed_tests']}")

    # Overall performance
    overall = report["overall"]
    lat = overall["latency_ms"]
    thr = overall["throughput_tokens_per_sec"]

    print(f"\n⚡ OVERALL PERFORMANCE")
    print(f"   Latency (ms):")
    print(f"      Mean:    {lat['mean']:.2f} ms")
    print(f"      Median:  {lat['median']:.2f} ms (p50)")
    print(f"      P90:     {lat['p90']:.2f} ms")
    print(f"      P95:     {lat['p95']:.2f} ms")
    print(f"      P99:     {lat['p99']:.2f} ms")
    print(f"      Min:     {lat['min']:.2f} ms")
    print(f"      Max:     {lat['max']:.2f} ms")
    print(f"      StdDev:  {lat['stdev']:.2f} ms")

    print(f"\n   Throughput (tokens/sec):")
    print(f"      Mean:    {thr['mean']:.2f} tok/s")
    print(f"      Median:  {thr['median']:.2f} tok/s (p50)")
    print(f"      P90:     {thr['p90']:.2f} tok/s")
    print(f"      P95:     {thr['p95']:.2f} tok/s")
    print(f"      P99:     {thr['p99']:.2f} tok/s")
    print(f"      Min:     {thr['min']:.2f} tok/s")
    print(f"      Max:     {thr['max']:.2f} tok/s")
    print(f"      StdDev:  {thr['stdev']:.2f} tok/s")

    # By category
    print(f"\n📁 PERFORMANCE BY CATEGORY")
    for cat, data in sorted(report["by_category"].items()):
        cat_lat = data["latency_ms"]
        cat_thr = data["throughput_tokens_per_sec"]
        print(f"\n   {cat.upper()} ({data['count']} tests)")
        print(f"      Latency:    {cat_lat['mean']:.2f} ± {cat_lat['stdev']:.2f} ms")
        print(f"                  p50: {cat_lat['p50']:.2f} ms, p95: {cat_lat['p95']:.2f} ms, p99: {cat_lat['p99']:.2f} ms")
        print(f"      Throughput: {cat_thr['mean']:.2f} ± {cat_thr['stdev']:.2f} tok/s")
        print(f"                  p50: {cat_thr['p50']:.2f} tok/s, p95: {cat_thr['p95']:.2f} tok/s")

    # By test
    print(f"\n🧪 PERFORMANCE BY TEST")
    for test_name, data in sorted(report["by_test"].items()):
        test_lat = data["latency_ms"]
        test_thr = data["throughput_tokens_per_sec"]
        print(f"\n   {test_name} ({data['count']} runs)")
        print(f"      Category:   {data['category']}")
        print(f"      Latency:    {test_lat['mean']:.2f} ± {test_lat['stdev']:.2f} ms")
        print(f"                  p50: {test_lat['p50']:.2f}, p95: {test_lat['p95']:.2f}, p99: {test_lat['p99']:.2f} ms")
        print(f"      Throughput: {test_thr['mean']:.2f} ± {test_thr['stdev']:.2f} tok/s")
        print(f"                  p50: {test_thr['p50']:.2f}, p95: {test_thr['p95']:.2f} tok/s")

    # Failures
    if report.get("failures") and report["failures"].get("count", 0) > 0:
        print(f"\n❌ FAILURES")
        print(f"   Total: {report['failures']['count']}")
        for reason, count in report["failures"]["reasons"].items():
            print(f"      {reason}: {count}")
    else:
        print(f"\n✅ NO FAILURES - 100% Success Rate!")

    print("\n" + "="*80)


if __name__ == "__main__":
    import sys

    log_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude/-home-davidjackson-Archive-AI/tasks/b44dfe3.output"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "data/perf-test-report-250.json"

    print(f"Parsing log file: {log_file}")
    report = generate_report(log_file)

    # Print report
    print_report(report)

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Full report saved to: {output_file}")
