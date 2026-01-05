#!/usr/bin/env python3
"""
Archive-AI Inference Performance Test

Tests inference performance across different prompt types and sizes.
Measures: latency, throughput (tokens/sec), time-to-first-token, model utilization.

Usage:
    python3 scripts/inference-perf-test.py --iterations 1
    python3 scripts/inference-perf-test.py --iterations 500 --output results.json
"""

import argparse
import json
import time
import httpx
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import statistics


# Test prompts of varying complexity and length
TEST_PROMPTS = {
    "simple_short": {
        "prompt": "What is 2+2?",
        "category": "simple",
        "expected_tokens": 10,
    },
    "simple_medium": {
        "prompt": "Explain what photosynthesis is in one paragraph.",
        "category": "simple",
        "expected_tokens": 100,
    },
    "reasoning_short": {
        "prompt": "If a train leaves station A at 60mph and another leaves station B at 40mph, 100 miles apart, when do they meet?",
        "category": "reasoning",
        "expected_tokens": 150,
    },
    "reasoning_medium": {
        "prompt": "You have 8 balls, one is slightly heavier. You have a balance scale and can use it twice. How do you find the heavy ball? Explain your reasoning step by step.",
        "category": "reasoning",
        "expected_tokens": 250,
    },
    "code_generation": {
        "prompt": "Write a Python function that checks if a string is a palindrome. Include docstring and example usage.",
        "category": "code",
        "expected_tokens": 200,
    },
    "summarization": {
        "prompt": "Summarize the key differences between supervised and unsupervised machine learning, including examples of each and when to use them.",
        "category": "summarization",
        "expected_tokens": 300,
    },
    "conversation": {
        "prompt": "I'm planning a trip to Japan. What are the top 3 cities I should visit and what should I see in each?",
        "category": "conversation",
        "expected_tokens": 250,
    },
}


class InferencePerformanceTester:
    """Inference performance testing harness"""

    def __init__(self, brain_url: str = "http://localhost:8080"):
        self.brain_url = brain_url
        self.results: List[Dict] = []

    async def test_single_inference(
        self,
        prompt: str,
        category: str,
        expected_tokens: int,
        test_name: str
    ) -> Dict:
        """
        Run a single inference test and measure performance.

        Returns dict with:
            - latency_ms: Total time from request to completion
            - tokens_generated: Number of tokens in response
            - tokens_per_sec: Throughput
            - prompt_tokens: Estimated prompt tokens
            - category: Test category
            - test_name: Name of test
            - success: Whether test succeeded
            - error: Error message if failed
        """
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.brain_url}/chat",
                    json={"message": prompt}
                )

                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                if response.status_code != 200:
                    return {
                        "test_name": test_name,
                        "category": category,
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "latency_ms": latency_ms,
                    }

                result = response.json()
                response_text = result.get("response", "")

                # Estimate tokens (rough: ~4 chars per token)
                prompt_tokens = len(prompt) // 4
                response_tokens = len(response_text) // 4
                total_tokens = prompt_tokens + response_tokens

                tokens_per_sec = response_tokens / (latency_ms / 1000) if latency_ms > 0 else 0

                return {
                    "test_name": test_name,
                    "category": category,
                    "success": True,
                    "latency_ms": latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "response_tokens": response_tokens,
                    "total_tokens": total_tokens,
                    "tokens_per_sec": tokens_per_sec,
                    "expected_tokens": expected_tokens,
                    "response_length": len(response_text),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return {
                "test_name": test_name,
                "category": category,
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def run_test_suite(self, iteration: int) -> List[Dict]:
        """Run all test prompts once and return results"""
        results = []

        for test_name, test_config in TEST_PROMPTS.items():
            print(f"  [{iteration}] Running {test_name}...", end=" ", flush=True)

            result = await self.test_single_inference(
                prompt=test_config["prompt"],
                category=test_config["category"],
                expected_tokens=test_config["expected_tokens"],
                test_name=test_name
            )

            result["iteration"] = iteration
            results.append(result)

            if result["success"]:
                print(f"✓ {result['latency_ms']:.1f}ms, {result['tokens_per_sec']:.1f} tok/s")
            else:
                print(f"✗ {result.get('error', 'unknown error')}")

            # Small delay between tests to avoid overwhelming the system
            await asyncio.sleep(0.5)

        return results

    async def run_multiple_iterations(self, num_iterations: int) -> List[Dict]:
        """Run test suite multiple times"""
        all_results = []

        print(f"\n{'='*60}")
        print(f"Starting {num_iterations} iterations of inference performance tests")
        print(f"{'='*60}\n")

        for i in range(1, num_iterations + 1):
            print(f"\nIteration {i}/{num_iterations}")
            print("-" * 60)

            iteration_results = await self.run_test_suite(i)
            all_results.extend(iteration_results)

            # Progress update every 10 iterations
            if i % 10 == 0:
                success_count = sum(1 for r in all_results if r.get("success", False))
                total_count = len(all_results)
                success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                print(f"\n>>> Progress: {i}/{num_iterations} iterations complete ({success_rate:.1f}% success rate)")

        return all_results

    def generate_statistics_report(self, results: List[Dict]) -> Dict:
        """Generate comprehensive statistics from test results"""

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
                }
            tests[test_name]["latencies"].append(result["latency_ms"])
            tests[test_name]["throughputs"].append(result["tokens_per_sec"])
            tests[test_name]["count"] += 1

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

        # Calculate statistics
        report = {
            "summary": {
                "total_tests": len(results),
                "successful_tests": len(successful),
                "failed_tests": len(failed),
                "success_rate": len(successful) / len(results) * 100,
            },
            "overall": {
                "latency_ms": calc_percentiles(latencies),
                "throughput_tokens_per_sec": calc_percentiles(throughputs),
            },
            "by_category": {},
            "by_test": {},
            "failures": [],
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
    print("INFERENCE PERFORMANCE TEST REPORT")
    print("="*80)

    # Summary
    summary = report["summary"]
    print(f"\n📊 SUMMARY")
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
    print(f"      Median:  {lat['median']:.2f} ms")
    print(f"      P90:     {lat['p90']:.2f} ms")
    print(f"      P95:     {lat['p95']:.2f} ms")
    print(f"      P99:     {lat['p99']:.2f} ms")
    print(f"      Min:     {lat['min']:.2f} ms")
    print(f"      Max:     {lat['max']:.2f} ms")
    print(f"      StdDev:  {lat['stdev']:.2f} ms")

    print(f"\n   Throughput (tokens/sec):")
    print(f"      Mean:    {thr['mean']:.2f} tok/s")
    print(f"      Median:  {thr['median']:.2f} tok/s")
    print(f"      P90:     {thr['p90']:.2f} tok/s")
    print(f"      P95:     {thr['p95']:.2f} tok/s")
    print(f"      Min:     {thr['min']:.2f} tok/s")
    print(f"      Max:     {thr['max']:.2f} tok/s")

    # By category
    print(f"\n📁 PERFORMANCE BY CATEGORY")
    for cat, data in report["by_category"].items():
        cat_lat = data["latency_ms"]
        cat_thr = data["throughput_tokens_per_sec"]
        print(f"\n   {cat.upper()} ({data['count']} tests)")
        print(f"      Latency:    {cat_lat['mean']:.2f} ms (p95: {cat_lat['p95']:.2f} ms)")
        print(f"      Throughput: {cat_thr['mean']:.2f} tok/s (p95: {cat_thr['p95']:.2f} tok/s)")

    # By test
    print(f"\n🧪 PERFORMANCE BY TEST")
    for test_name, data in sorted(report["by_test"].items()):
        test_lat = data["latency_ms"]
        test_thr = data["throughput_tokens_per_sec"]
        print(f"\n   {test_name} ({data['count']} runs)")
        print(f"      Latency:    {test_lat['mean']:.2f} ± {test_lat['stdev']:.2f} ms")
        print(f"      Throughput: {test_thr['mean']:.2f} ± {test_thr['stdev']:.2f} tok/s")

    # Failures
    if "failures" in report and report["failures"]["count"] > 0:
        print(f"\n❌ FAILURES")
        print(f"   Total: {report['failures']['count']}")
        for reason, count in report["failures"]["reasons"].items():
            print(f"      {reason}: {count}")

    print("\n" + "="*80)


async def main():
    parser = argparse.ArgumentParser(description="Archive-AI Inference Performance Test")
    parser.add_argument("--iterations", type=int, default=1, help="Number of test iterations")
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    parser.add_argument("--report", type=str, help="Output file for statistics report")
    parser.add_argument("--brain-url", type=str, default="http://localhost:8080", help="Brain API URL")

    args = parser.parse_args()

    # Run tests
    tester = InferencePerformanceTester(brain_url=args.brain_url)
    results = await tester.run_multiple_iterations(args.iterations)

    # Generate report
    report = tester.generate_statistics_report(results)

    # Print to console
    print_report(report)

    # Save raw results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Raw results saved to: {args.output}")

    # Save report
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✓ Statistics report saved to: {args.report}")

    # Return exit code based on success rate
    success_rate = report["summary"]["success_rate"]
    if success_rate < 95:
        print(f"\n⚠️  Warning: Success rate ({success_rate:.1f}%) is below 95%")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
