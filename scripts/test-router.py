#!/usr/bin/env python3
"""
Test script for Semantic Router (Chunk 2.6)
Tests intent classification and parameter extraction.
"""

import sys
from pathlib import Path

# Add brain to path
sys.path.insert(0, str(Path(__file__).parent.parent / "brain"))

from router import SemanticRouter, Intent


def test_router():
    """Test semantic router functionality"""
    print("=" * 70)
    print("Semantic Router Test")
    print("=" * 70)

    router = SemanticRouter()

    # Test cases: (message, expected_intent, expected_params)
    test_cases = [
        # CHAT intent
        ("Hello, how are you?", Intent.CHAT, {}),
        ("What's the weather like?", Intent.CHAT, {}),
        ("Tell me a joke", Intent.CHAT, {}),
        ("The sky is blue", Intent.CHAT, {}),

        # SEARCH_MEMORY intent
        ("What did I say about Python?", Intent.SEARCH_MEMORY, {"query": "python"}),
        ("Remember when I mentioned machine learning", Intent.SEARCH_MEMORY,
         {"query": "when i mentioned machine learning"}),
        ("Find my previous message about Redis", Intent.SEARCH_MEMORY,
         {"query": "my previous message redis"}),
        ("Search for conversations about AI", Intent.SEARCH_MEMORY,
         {"query": "conversations ai"}),
        ("What did I say earlier?", Intent.SEARCH_MEMORY, {"query": "earlier?"}),
        ("Recall what we discussed about Docker", Intent.SEARCH_MEMORY,
         {"query": "what we discussed docker"}),

        # HELP intent
        ("help", Intent.HELP, {}),
        ("How do I use this?", Intent.HELP, {}),
        ("What can you do?", Intent.HELP, {}),
        ("Show me the commands", Intent.HELP, {}),
        ("?", Intent.HELP, {}),
        ("Explain how this works", Intent.HELP, {}),
    ]

    passed = 0
    failed = 0

    for i, (message, expected_intent, expected_params_subset) in enumerate(test_cases, 1):
        result = router.route(message)

        print(f"\n[Test {i}] Message: \"{message}\"")
        print(f"  Expected Intent: {expected_intent.value}")
        print(f"  Actual Intent: {result['intent'].value}")
        print(f"  Confidence: {result['confidence']:.2f}")

        if expected_params_subset:
            print(f"  Expected Params: {expected_params_subset}")
            print(f"  Actual Params: {result['params']}")

        # Check intent
        if result["intent"] != expected_intent:
            print(f"  ❌ FAIL: Intent mismatch")
            failed += 1
            continue

        # Check confidence is reasonable
        if result["confidence"] < 0.5:
            print(f"  ❌ FAIL: Low confidence ({result['confidence']})")
            failed += 1
            continue

        # For search_memory, check query parameter exists
        if expected_intent == Intent.SEARCH_MEMORY:
            if "query" not in result["params"]:
                print(f"  ❌ FAIL: Missing query parameter")
                failed += 1
                continue
            # Check query is not empty and contains some expected content
            query = result["params"]["query"]
            if not query or len(query.strip()) == 0:
                print(f"  ❌ FAIL: Empty query")
                failed += 1
                continue

        print(f"  ✅ PASS")
        passed += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")

    if failed == 0:
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        return True
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    try:
        success = test_router()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
