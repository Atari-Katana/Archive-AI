#!/usr/bin/env python3
"""
Agent Stress Test (Chunk 4.10)
Runs comprehensive tests of the ReAct agent system with 20+ scenarios.
Tests tool use, multi-step reasoning, error recovery, and edge cases.
"""

import asyncio
import httpx
import yaml
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import argparse


class AgentStressTest:
    """Comprehensive stress test for ReAct agents."""

    def __init__(self, test_file: str = "tests/agent-test-cases.yaml", brain_url: str = "http://localhost:8080"):
        self.test_file = test_file
        self.brain_url = brain_url
        self.test_cases = []
        self.results = []
        self.config = {}
        self.start_time = None

    def load_tests(self):
        """Load test cases from YAML file."""
        with open(self.test_file, 'r') as f:
            data = yaml.safe_load(f)
            self.test_cases = data.get('test_cases', [])
            self.config = data.get('config', {})
            self.success_criteria = data.get('success_criteria', {})

        print(f"Loaded {len(self.test_cases)} test cases")
        print(f"Success criteria: {self.success_criteria.get('minimum_success_rate', 0.8)*100}% pass rate")

    async def run_agent_test(self, test_case: Dict[str, Any], mode: str = "advanced") -> Dict[str, Any]:
        """Run a single agent test case."""
        test_id = test_case['id']
        question = test_case['question']

        endpoint = "/agent/advanced" if mode == "advanced" else "/agent"
        url = f"{self.brain_url}{endpoint}"

        max_steps = self.config.get('max_steps_per_test', 10)
        timeout = self.config.get('timeout_seconds', 60)

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=float(timeout)) as client:
                response = await client.post(
                    url,
                    json={"question": question, "max_steps": max_steps}
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            return {
                "test_id": test_id,
                "success": False,
                "error": "TIMEOUT",
                "response_time": time.time() - start_time,
                "answer": None,
                "steps": [],
                "tools_used": []
            }
        except Exception as e:
            return {
                "test_id": test_id,
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "answer": None,
                "steps": [],
                "tools_used": []
            }

        response_time = time.time() - start_time

        # Extract agent response
        agent_success = data.get("success", False)
        answer = data.get("answer", "")
        steps = data.get("steps", [])
        total_steps = data.get("total_steps", 0)
        error = data.get("error")

        # Extract tools used
        tools_used = []
        for step in steps:
            if step.get("action"):
                tools_used.append(step["action"])

        return {
            "test_id": test_id,
            "success": agent_success and not error,
            "error": error,
            "response_time": response_time,
            "answer": answer,
            "steps": steps,
            "total_steps": total_steps,
            "tools_used": list(set(tools_used)),  # Unique tools
            "raw_response": data
        }

    def evaluate_result(self, test_case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if the agent result matches expectations."""
        test_id = test_case['id']

        # Check if agent succeeded
        if not result["success"]:
            return {
                "test_id": test_id,
                "passed": False,
                "reason": f"Agent failed: {result.get('error', 'Unknown error')}",
                **result
            }

        # Check for expected error cases
        if test_case.get('expect_error', False):
            # For error cases, we expect the agent to handle it gracefully
            if "error" in result['answer'].lower() or "cannot" in result['answer'].lower():
                return {
                    "test_id": test_id,
                    "passed": True,
                    "reason": "Correctly handled error case",
                    **result
                }
            else:
                return {
                    "test_id": test_id,
                    "passed": False,
                    "reason": "Did not handle error case properly",
                    **result
                }

        # Check expected answer (if provided)
        expected_answer = test_case.get('expected_answer')
        if expected_answer:
            answer_str = str(result['answer']).lower()
            expected_str = str(expected_answer).lower()

            # Flexible matching (contains expected answer)
            if expected_str in answer_str or answer_str in expected_str:
                return {
                    "test_id": test_id,
                    "passed": True,
                    "reason": f"Correct answer: {expected_answer}",
                    **result
                }
            else:
                return {
                    "test_id": test_id,
                    "passed": False,
                    "reason": f"Wrong answer. Expected: {expected_answer}, Got: {result['answer'][:100]}",
                    **result
                }

        # Check expected tools (if provided)
        expected_tools = test_case.get('expected_tools', [])
        if expected_tools:
            tools_used = result.get('tools_used', [])
            if any(tool in tools_used for tool in expected_tools):
                return {
                    "test_id": test_id,
                    "passed": True,
                    "reason": f"Used expected tools: {tools_used}",
                    **result
                }
            else:
                return {
                    "test_id": test_id,
                    "passed": False,
                    "reason": f"Did not use expected tools. Expected: {expected_tools}, Used: {tools_used}",
                    **result
                }

        # If no specific criteria, just check if agent succeeded
        return {
            "test_id": test_id,
            "passed": True,
            "reason": "Agent completed successfully",
            **result
        }

    async def run_all_tests(self):
        """Run all test cases."""
        print(f"\nStarting Agent Stress Test: {len(self.test_cases)} test cases")
        print(f"Brain API: {self.brain_url}")
        print(f"Start time: {datetime.now()}")
        print("=" * 70)

        self.start_time = time.time()

        for i, test_case in enumerate(self.test_cases, 1):
            test_id = test_case['id']
            name = test_case['name']
            difficulty = test_case.get('difficulty', 'medium')
            category = test_case.get('category', 'unknown')

            print(f"\n[{i}/{len(self.test_cases)}] {test_id}: {name}")
            print(f"    Category: {category} | Difficulty: {difficulty}")
            print(f"    Question: {test_case['question'][:80]}...")

            # Determine which agent mode to use
            expected_tools = test_case.get('expected_tools', [])
            advanced_tools = ["MemorySearch", "CodeExecution", "DateTime", "JSON", "WebSearch"]
            mode = "advanced" if any(tool in advanced_tools for tool in expected_tools) else "basic"

            # Run test
            result = await self.run_agent_test(test_case, mode=mode)

            # Evaluate result
            evaluation = self.evaluate_result(test_case, result)
            evaluation['test_case'] = test_case
            self.results.append(evaluation)

            # Print result
            if evaluation['passed']:
                print(f"    ✅ PASS ({evaluation['response_time']:.2f}s, {evaluation['total_steps']} steps)")
                if evaluation.get('tools_used'):
                    print(f"       Tools: {', '.join(evaluation['tools_used'])}")
            else:
                print(f"    ❌ FAIL ({evaluation['response_time']:.2f}s)")
                print(f"       Reason: {evaluation['reason']}")

            # Brief delay between tests
            await asyncio.sleep(0.5)

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 70)
        print("AGENT STRESS TEST REPORT")
        print("=" * 70)

        total_time = time.time() - self.start_time
        total_tests = len(self.results)
        passed_tests = [r for r in self.results if r['passed']]
        failed_tests = [r for r in self.results if not r['passed']]

        # Basic statistics
        print(f"\n📊 Test Statistics:")
        print(f"   Total tests: {total_tests}")
        print(f"   Passed: {len(passed_tests)} ({len(passed_tests)/total_tests*100:.1f}%)")
        print(f"   Failed: {len(failed_tests)} ({len(failed_tests)/total_tests*100:.1f}%)")
        print(f"   Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print(f"   Average time per test: {total_time/total_tests:.2f}s")

        # Performance metrics
        response_times = [r['response_time'] for r in self.results if r.get('response_time')]
        step_counts = [r['total_steps'] for r in self.results if r.get('total_steps')]

        if response_times:
            print(f"\n⏱️  Response Times:")
            print(f"   Average: {sum(response_times)/len(response_times):.2f}s")
            print(f"   Min: {min(response_times):.2f}s")
            print(f"   Max: {max(response_times):.2f}s")

        if step_counts:
            print(f"\n🔢 Step Counts:")
            print(f"   Average: {sum(step_counts)/len(step_counts):.1f} steps")
            print(f"   Min: {min(step_counts)} steps")
            print(f"   Max: {max(step_counts)} steps")

        # Category breakdown
        categories = {}
        for result in self.results:
            cat = result['test_case'].get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if result['passed']:
                categories[cat]['passed'] += 1

        print(f"\n📂 Results by Category:")
        for cat, stats in sorted(categories.items()):
            rate = stats['passed'] / stats['total'] * 100
            status = "✅" if rate >= 80 else "⚠️" if rate >= 60 else "❌"
            print(f"   {status} {cat}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")

        # Tool usage statistics
        all_tools_used = []
        for result in self.results:
            all_tools_used.extend(result.get('tools_used', []))

        if all_tools_used:
            from collections import Counter
            tool_counts = Counter(all_tools_used)
            print(f"\n🔧 Tool Usage:")
            for tool, count in tool_counts.most_common():
                print(f"   {tool}: {count} times")

        # Failure analysis
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for result in failed_tests:
                test_id = result['test_id']
                name = result['test_case']['name']
                reason = result['reason']
                print(f"   • {test_id} - {name}")
                print(f"     Reason: {reason}")

                # Check for patterns
                if result['test_case'].get('known_issue'):
                    print(f"     Note: {result['test_case']['known_issue']}")

        # Identify failure patterns
        error_types = {}
        for result in failed_tests:
            reason = result.get('reason', 'Unknown')
            # Categorize errors
            if 'timeout' in reason.lower():
                error_type = 'TIMEOUT'
            elif 'wrong answer' in reason.lower():
                error_type = 'WRONG_ANSWER'
            elif 'tools' in reason.lower():
                error_type = 'WRONG_TOOLS'
            elif 'error' in reason.lower():
                error_type = 'AGENT_ERROR'
            else:
                error_type = 'OTHER'

            error_types[error_type] = error_types.get(error_type, 0) + 1

        if error_types:
            print(f"\n🔍 Failure Patterns:")
            for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                print(f"   {error_type}: {count}")

        # Pass/Fail assessment
        print(f"\n{'='*70}")
        print("PASS/FAIL ASSESSMENT:")
        print(f"{'='*70}")

        passed_overall = True
        success_rate = len(passed_tests) / total_tests
        min_success_rate = self.success_criteria.get('minimum_success_rate', 0.8)

        # Check 1: Success rate
        if success_rate >= min_success_rate:
            print(f"✅ Success rate: {success_rate*100:.1f}% (>= {min_success_rate*100:.0f}%)")
        else:
            print(f"❌ Success rate: {success_rate*100:.1f}% (< {min_success_rate*100:.0f}%)")
            passed_overall = False

        # Check 2: Average steps
        if step_counts:
            avg_steps = sum(step_counts) / len(step_counts)
            max_avg_steps = self.success_criteria.get('maximum_avg_steps', 5)
            if avg_steps <= max_avg_steps:
                print(f"✅ Average steps: {avg_steps:.1f} (<= {max_avg_steps})")
            else:
                print(f"⚠️  Average steps: {avg_steps:.1f} (> {max_avg_steps})")

        # Check 3: Average time
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_avg_time = self.success_criteria.get('maximum_avg_time', 15)
            if avg_time <= max_avg_time:
                print(f"✅ Average time: {avg_time:.1f}s (<= {max_avg_time}s)")
            else:
                print(f"⚠️  Average time: {avg_time:.1f}s (> {max_avg_time}s)")

        # Check 4: No infinite loops (check for timeouts)
        timeouts = [r for r in failed_tests if 'timeout' in r.get('reason', '').lower()]
        if not timeouts:
            print(f"✅ No infinite loops detected (0 timeouts)")
        else:
            print(f"⚠️  {len(timeouts)} timeout(s) detected - possible infinite loops")

        # Final verdict
        print(f"\n{'='*70}")
        if passed_overall:
            print("🎉 AGENT STRESS TEST PASSED")
            print(f"   The agent system is performing at {success_rate*100:.0f}% success rate")
        else:
            print("⚠️  AGENT STRESS TEST NEEDS IMPROVEMENT")
            print(f"   Current success rate: {success_rate*100:.0f}% (target: {min_success_rate*100:.0f}%)")
            print(f"   Failed tests need investigation and fixes")
        print(f"{'='*70}\n")

        # Save detailed results
        report_file = f"agent-test-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "test_date": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": success_rate,
                "total_time": total_time,
                "avg_response_time": sum(response_times)/len(response_times) if response_times else 0,
                "avg_steps": sum(step_counts)/len(step_counts) if step_counts else 0,
                "passed_overall": passed_overall,
                "results": self.results
            }, f, indent=2)

        print(f"📄 Detailed results saved to: {report_file}")


async def main():
    parser = argparse.ArgumentParser(description="Agent Stress Test for Archive-AI")
    parser.add_argument("--tests", type=str, default="tests/agent-test-cases.yaml", help="Path to test cases YAML file")
    parser.add_argument("--url", type=str, default="http://localhost:8080", help="Brain API URL")
    args = parser.parse_args()

    test = AgentStressTest(test_file=args.tests, brain_url=args.url)
    test.load_tests()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
