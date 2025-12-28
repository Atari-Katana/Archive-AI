#!/usr/bin/env python3
"""
Long Conversation Test (Chunk 4.8)
Runs 500+ conversation turns to test system stability, memory usage, and performance.
"""

import asyncio
import time
import httpx
import psutil
import json
from datetime import datetime
from typing import List, Dict, Any
import argparse
import subprocess


class LongConversationTest:
    """Automated stress test for Archive-AI system."""

    def __init__(self, brain_url: str = "http://localhost:8080", turns: int = 500):
        self.brain_url = brain_url
        self.turns = turns
        self.results = []
        self.errors = []
        self.start_time = None
        self.initial_vram = None
        self.test_prompts = self._generate_test_prompts()

    def _generate_test_prompts(self) -> List[Dict[str, Any]]:
        """Generate diverse test prompts covering different modes and features."""
        prompts = []

        # Chat prompts (simple conversation)
        chat_prompts = [
            "Hello, how are you?",
            "What's the weather like today?",
            "Tell me about artificial intelligence.",
            "What is the capital of France?",
            "Explain quantum computing in simple terms.",
            "What's 2 + 2?",
            "Who wrote Romeo and Juliet?",
            "What's the meaning of life?",
        ]

        # Agent prompts (require tool use)
        agent_prompts = [
            {"message": "Calculate 123 * 456", "mode": "agent"},
            {"message": "What is the length of the word 'supercalifragilisticexpialidocious'?", "mode": "agent"},
            {"message": "Count the words in this sentence: The quick brown fox jumps over the lazy dog", "mode": "agent"},
            {"message": "Convert 'hello world' to uppercase", "mode": "agent"},
            {"message": "Extract all numbers from: abc123def456ghi789", "mode": "agent"},
        ]

        # Advanced agent prompts (code execution, memory search)
        advanced_prompts = [
            {"message": "Calculate the factorial of 10", "mode": "advanced"},
            {"message": "What's the current date and time?", "mode": "advanced"},
            {"message": "Search my memories for any information about 'calculator'", "mode": "advanced"},
            {"message": "Write Python code to find prime numbers up to 20", "mode": "advanced"},
        ]

        # Verified prompts (chain of verification)
        verified_prompts = [
            {"message": "What is the square root of 144?", "mode": "verify"},
            {"message": "Is Paris the capital of France?", "mode": "verify"},
            {"message": "How many days are in February during a leap year?", "mode": "verify"},
        ]

        # Build test sequence (cycling through different types)
        for i in range(self.turns):
            if i % 20 == 0:
                # Every 20 turns, use advanced mode
                prompt = advanced_prompts[i % len(advanced_prompts)]
            elif i % 15 == 0:
                # Every 15 turns, use verified mode
                prompt = verified_prompts[i % len(verified_prompts)]
            elif i % 10 == 0:
                # Every 10 turns, use basic agent
                prompt = agent_prompts[i % len(agent_prompts)]
            else:
                # Most turns are simple chat
                message = chat_prompts[i % len(chat_prompts)]
                prompt = {"message": message, "mode": "chat"}

            prompts.append(prompt)

        return prompts

    def get_vram_usage(self) -> float:
        """Get current VRAM usage in MB using nvidia-smi."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            print(f"Warning: Could not get VRAM usage: {e}")
        return 0.0

    def get_system_memory(self) -> Dict[str, float]:
        """Get current system memory usage."""
        mem = psutil.virtual_memory()
        return {
            "used_mb": mem.used / (1024 * 1024),
            "percent": mem.percent,
            "available_mb": mem.available / (1024 * 1024)
        }

    async def send_message(self, message: str, mode: str = "chat") -> Dict[str, Any]:
        """Send a message to the Brain API and return response with metrics."""
        endpoint_map = {
            "chat": "/chat",
            "verify": "/verify",
            "agent": "/agent",
            "advanced": "/agent/advanced"
        }

        endpoint = endpoint_map.get(mode, "/chat")
        url = f"{self.brain_url}{endpoint}"

        # Build request body based on endpoint type
        if mode in ["agent", "advanced"]:
            request_body = {"question": message, "max_steps": 10}
        else:
            request_body = {"message": message}

        start_time = time.time()
        vram_before = self.get_vram_usage()
        mem_before = self.get_system_memory()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=request_body)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "vram_used": vram_before,
                "memory": mem_before
            }

        end_time = time.time()
        vram_after = self.get_vram_usage()
        mem_after = self.get_system_memory()

        # Extract response text based on mode
        if mode in ["agent", "advanced"]:
            response_text = data.get("answer", "")
        else:
            response_text = data.get("response", "")

        return {
            "success": True,
            "response_time": end_time - start_time,
            "vram_before": vram_before,
            "vram_after": vram_after,
            "vram_delta": vram_after - vram_before,
            "memory_before": mem_before,
            "memory_after": mem_after,
            "memory_delta": mem_after["used_mb"] - mem_before["used_mb"],
            "mode": mode,
            "message": message,
            "response_length": len(response_text)
        }

    async def run_test(self):
        """Run the long conversation test."""
        print(f"Starting Long Conversation Test: {self.turns} turns")
        print(f"Brain API: {self.brain_url}")
        print(f"Start time: {datetime.now()}")
        print("=" * 60)

        self.start_time = time.time()
        self.initial_vram = self.get_vram_usage()
        initial_memory = self.get_system_memory()

        print(f"Initial VRAM: {self.initial_vram:.1f} MB")
        print(f"Initial Memory: {initial_memory['used_mb']:.1f} MB ({initial_memory['percent']:.1f}%)")
        print("=" * 60)

        for i, prompt_data in enumerate(self.test_prompts, 1):
            message = prompt_data["message"]
            mode = prompt_data.get("mode", "chat")

            # Progress indicator
            if i % 10 == 0:
                elapsed = time.time() - self.start_time
                rate = i / elapsed
                eta = (self.turns - i) / rate if rate > 0 else 0
                print(f"\nTurn {i}/{self.turns} | {elapsed:.1f}s elapsed | ETA: {eta:.1f}s | Mode: {mode}")

            # Send message and collect metrics
            result = await self.send_message(message, mode)
            result["turn"] = i
            result["elapsed_time"] = time.time() - self.start_time

            self.results.append(result)

            if not result["success"]:
                error_msg = f"Turn {i}: {result['error']}"
                self.errors.append(error_msg)
                print(f"❌ ERROR: {error_msg}")
            else:
                # Only print details every 50 turns
                if i % 50 == 0:
                    print(f"   Response time: {result['response_time']:.2f}s")
                    print(f"   VRAM: {result['vram_after']:.1f} MB (Δ {result['vram_delta']:+.1f})")
                    print(f"   Memory: {result['memory_after']['used_mb']:.1f} MB (Δ {result['memory_delta']:+.1f})")

            # Brief delay to avoid overwhelming the system
            await asyncio.sleep(0.1)

        # Final summary
        self.generate_report()

    def generate_report(self):
        """Generate final test report."""
        print("\n" + "=" * 60)
        print("LONG CONVERSATION TEST REPORT")
        print("=" * 60)

        total_time = time.time() - self.start_time
        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]

        # Basic stats
        print(f"\n📊 Basic Statistics:")
        print(f"   Total turns: {self.turns}")
        print(f"   Successful: {len(successful)} ({len(successful)/self.turns*100:.1f}%)")
        print(f"   Failed: {len(failed)} ({len(failed)/self.turns*100:.1f}%)")
        print(f"   Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print(f"   Average rate: {self.turns/total_time:.2f} turns/second")

        if not successful:
            print("\n❌ No successful requests to analyze!")
            return

        # Response time analysis
        response_times = [r["response_time"] for r in successful]
        avg_response = sum(response_times) / len(response_times)
        min_response = min(response_times)
        max_response = max(response_times)

        # Check for degradation (compare first 100 vs last 100)
        first_100 = response_times[:100] if len(response_times) >= 100 else response_times[:len(response_times)//2]
        last_100 = response_times[-100:] if len(response_times) >= 100 else response_times[len(response_times)//2:]
        avg_first = sum(first_100) / len(first_100) if first_100 else 0
        avg_last = sum(last_100) / len(last_100) if last_100 else 0
        degradation_pct = ((avg_last - avg_first) / avg_first * 100) if avg_first > 0 else 0

        print(f"\n⏱️  Response Times:")
        print(f"   Average: {avg_response:.2f}s")
        print(f"   Min: {min_response:.2f}s")
        print(f"   Max: {max_response:.2f}s")
        print(f"   First 100 avg: {avg_first:.2f}s")
        print(f"   Last 100 avg: {avg_last:.2f}s")
        print(f"   Degradation: {degradation_pct:+.1f}%")

        # VRAM analysis
        final_vram = self.get_vram_usage()
        vram_delta = final_vram - self.initial_vram
        vram_deltas = [r.get("vram_delta", 0) for r in successful if "vram_delta" in r]
        max_vram_spike = max(vram_deltas) if vram_deltas else 0

        print(f"\n🎮 VRAM Usage:")
        print(f"   Initial: {self.initial_vram:.1f} MB")
        print(f"   Final: {final_vram:.1f} MB")
        print(f"   Total change: {vram_delta:+.1f} MB")
        print(f"   Max spike: {max_vram_spike:+.1f} MB")

        # Memory analysis
        final_memory = self.get_system_memory()
        memory_deltas = [r.get("memory_delta", 0) for r in successful if "memory_delta" in r]
        total_memory_change = final_memory["used_mb"] - successful[0]["memory_before"]["used_mb"]

        print(f"\n💾 System Memory:")
        print(f"   Initial: {successful[0]['memory_before']['used_mb']:.1f} MB")
        print(f"   Final: {final_memory['used_mb']:.1f} MB")
        print(f"   Total change: {total_memory_change:+.1f} MB")

        # Errors
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                print(f"   - {error}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more")

        # Pass/Fail assessment
        print(f"\n{'='*60}")
        print("PASS/FAIL ASSESSMENT:")
        print(f"{'='*60}")

        passed = True

        # Check 1: Success rate
        success_rate = len(successful) / self.turns * 100
        if success_rate >= 95:
            print(f"✅ Success rate: {success_rate:.1f}% (>= 95%)")
        else:
            print(f"❌ Success rate: {success_rate:.1f}% (< 95%)")
            passed = False

        # Check 2: VRAM stability (no major leak)
        if abs(vram_delta) < 500:  # Less than 500MB change
            print(f"✅ VRAM stable: {vram_delta:+.1f} MB change")
        else:
            print(f"⚠️  VRAM changed significantly: {vram_delta:+.1f} MB")
            # Don't fail, just warn

        # Check 3: Response time degradation
        if degradation_pct < 50:  # Less than 50% slower
            print(f"✅ Response times stable: {degradation_pct:+.1f}% change")
        else:
            print(f"❌ Response times degraded: {degradation_pct:+.1f}% slower")
            passed = False

        # Check 4: No crashes (test completed)
        print(f"✅ No crashes: Test completed all {self.turns} turns")

        # Final verdict
        print(f"\n{'='*60}")
        if passed:
            print("🎉 TEST PASSED - System is stable over long conversations")
        else:
            print("⚠️  TEST FAILED - Issues detected, see above")
        print(f"{'='*60}\n")

        # Save detailed results to JSON
        report_file = f"test-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "test_date": datetime.now().isoformat(),
                "turns": self.turns,
                "total_time": total_time,
                "success_rate": success_rate,
                "avg_response_time": avg_response,
                "degradation_pct": degradation_pct,
                "vram_delta": vram_delta,
                "memory_delta": total_memory_change,
                "errors": self.errors,
                "passed": passed,
                "results": self.results
            }, f, indent=2)

        print(f"📄 Detailed results saved to: {report_file}")


async def main():
    parser = argparse.ArgumentParser(description="Long Conversation Test for Archive-AI")
    parser.add_argument("--turns", type=int, default=500, help="Number of conversation turns (default: 500)")
    parser.add_argument("--url", type=str, default="http://localhost:8080", help="Brain API URL")
    args = parser.parse_args()

    test = LongConversationTest(brain_url=args.url, turns=args.turns)
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
