#!/usr/bin/env python3
"""
Test script for Surprise Scoring (Chunk 2.5)
Tests surprise score calculation logic.
"""

import sys
from pathlib import Path

# Add brain to path
sys.path.insert(0, str(Path(__file__).parent.parent / "brain"))

from workers.memory_worker import MemoryWorker


def test_surprise_calculation():
    """Test surprise score calculation logic"""
    print("=" * 70)
    print("Surprise Score Calculation Test")
    print("=" * 70)

    worker = MemoryWorker()

    # Test 1: Low perplexity, low vector distance (common phrase, similar to previous)
    print("\n[Test 1] Low perplexity + Low vector distance")
    perplexity1 = 5.0  # Common phrase
    vector_distance1 = 0.1  # Very similar to existing
    surprise1 = worker.calculate_surprise_score(perplexity1, vector_distance1)
    print(f"  Perplexity: {perplexity1}")
    print(f"  Vector Distance: {vector_distance1}")
    print(f"  Surprise Score: {surprise1:.3f}")
    print(f"  Expected: LOW (< 0.3)")
    assert surprise1 < 0.3, f"Expected low surprise, got {surprise1}"
    print("  ✅ PASS")

    # Test 2: High perplexity, high vector distance (rare phrase, novel content)
    print("\n[Test 2] High perplexity + High vector distance")
    perplexity2 = 50.0  # Rare/unusual phrase
    vector_distance2 = 0.9  # Very different from existing
    surprise2 = worker.calculate_surprise_score(perplexity2, vector_distance2)
    print(f"  Perplexity: {perplexity2}")
    print(f"  Vector Distance: {vector_distance2}")
    print(f"  Surprise Score: {surprise2:.3f}")
    print(f"  Expected: HIGH (> 0.7)")
    assert surprise2 > 0.7, f"Expected high surprise, got {surprise2}"
    print("  ✅ PASS")

    # Test 3: Medium perplexity, medium vector distance
    print("\n[Test 3] Medium perplexity + Medium vector distance")
    perplexity3 = 15.0  # Moderate complexity
    vector_distance3 = 0.5  # Somewhat novel
    surprise3 = worker.calculate_surprise_score(perplexity3, vector_distance3)
    print(f"  Perplexity: {perplexity3}")
    print(f"  Vector Distance: {vector_distance3}")
    print(f"  Surprise Score: {surprise3:.3f}")
    print(f"  Expected: MEDIUM (0.4-0.7)")
    assert 0.4 <= surprise3 <= 0.7, f"Expected medium surprise, got {surprise3}"
    print("  ✅ PASS")

    # Test 4: Perplexity dominates (high perplexity, low vector distance)
    print("\n[Test 4] High perplexity + Low vector distance")
    perplexity4 = 40.0  # High perplexity
    vector_distance4 = 0.2  # Similar to existing
    surprise4 = worker.calculate_surprise_score(perplexity4, vector_distance4)
    print(f"  Perplexity: {perplexity4}")
    print(f"  Vector Distance: {vector_distance4}")
    print(f"  Surprise Score: {surprise4:.3f}")
    print(f"  Expected: MEDIUM-HIGH (perplexity weight = 60%)")
    # With 60% weight on perplexity, should still be moderately high
    assert surprise4 > 0.5, f"Expected medium-high surprise, got {surprise4}"
    print("  ✅ PASS")

    # Test 5: Vector distance dominates (low perplexity, high vector distance)
    print("\n[Test 5] Low perplexity + High vector distance")
    perplexity5 = 5.0  # Low perplexity
    vector_distance5 = 0.9  # Very novel
    surprise5 = worker.calculate_surprise_score(perplexity5, vector_distance5)
    print(f"  Perplexity: {perplexity5}")
    print(f"  Vector Distance: {vector_distance5}")
    print(f"  Surprise Score: {surprise5:.3f}")
    print(f"  Expected: MEDIUM (vector weight = 40%)")
    # With 40% weight on vector distance, should be moderate
    assert 0.3 <= surprise5 <= 0.6, f"Expected medium surprise, got {surprise5}"
    print("  ✅ PASS")

    # Test 6: Threshold check
    print("\n[Test 6] Threshold verification")
    print(f"  Threshold: {worker.SURPRISE_THRESHOLD}")
    print(f"  Perplexity weight: {worker.PERPLEXITY_WEIGHT}")
    print(f"  Vector distance weight: {worker.VECTOR_DISTANCE_WEIGHT}")
    assert worker.SURPRISE_THRESHOLD == 0.7, "Threshold should be 0.7"
    assert worker.PERPLEXITY_WEIGHT == 0.6, "Perplexity weight should be 0.6"
    assert worker.VECTOR_DISTANCE_WEIGHT == 0.4, "Vector weight should be 0.4"
    print("  ✅ PASS")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print("\nNote: This tests the surprise calculation logic.")
    print("Full integration test with Vorpal requires GPU.")
    return True


if __name__ == "__main__":
    try:
        success = test_surprise_calculation()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
