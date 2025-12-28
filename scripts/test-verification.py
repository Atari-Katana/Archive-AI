#!/usr/bin/env python3
"""
Test Chain of Verification (Chunk 3.1)
Tests the verification pipeline to ensure it catches hallucinations.
"""

import asyncio
import sys
sys.path.insert(0, '/app')  # For running inside Brain container

from verification import ChainOfVerification


async def test_verification():
    """Test the complete verification chain"""

    print("=" * 70)
    print("Chain of Verification Test")
    print("=" * 70)
    print()

    # Test cases: questions that might lead to hallucinations
    test_cases = [
        {
            "name": "Factual Question",
            "prompt": "What is the capital of France?",
            "expect_revision": False
        },
        {
            "name": "Math Question",
            "prompt": "What is 15 * 23?",
            "expect_revision": False
        },
        {
            "name": "Potentially Ambiguous",
            "prompt": "Who was the first person to walk on Mars?",
            "expect_revision": True  # Should catch that no one has walked on Mars yet
        }
    ]

    async with ChainOfVerification() as cov:
        for i, test_case in enumerate(test_cases, 1):
            print(f"Test {i}/{len(test_cases)}: {test_case['name']}")
            print(f"Question: {test_case['prompt']}")
            print()

            try:
                result = await cov.verify(test_case['prompt'])

                print(f"Initial Response:")
                print(f"  {result['initial_response']}")
                print()

                print(f"Verification Questions ({len(result['verification_questions'])}):")
                for j, q in enumerate(result['verification_questions'], 1):
                    print(f"  {j}. {q}")
                print()

                print(f"Verification Answers:")
                for qa in result['verification_qa']:
                    print(f"  Q: {qa['question']}")
                    print(f"  A: {qa['answer']}")
                    print()

                print(f"Final Response:")
                print(f"  {result['final_response']}")
                print()

                revised_symbol = "✅ REVISED" if result['revised'] else "➡️  NO CHANGE"
                print(f"Status: {revised_symbol}")

                if result['revised']:
                    print(f"  Revision detected - verification caught potential issues")
                else:
                    print(f"  No revision needed - initial response validated")

            except Exception as e:
                print(f"❌ ERROR: {e}")

            print()
            print("-" * 70)
            print()

    print("=" * 70)
    print("Verification Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_verification())
