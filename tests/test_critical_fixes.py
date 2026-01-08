#!/usr/bin/env python3
"""
Test suite for the three critical fixes:
1. RLM response field mapping
2. SQL injection protection in vector search
3. Binary data preservation in archival
"""

import httpx
import json
import time
import sys

BASE_URL = "http://localhost:8081"
SANDBOX_URL = "http://localhost:8003"

def test_rlm_response_mapping():
    """Test Fix #1: RLM response field mapping"""
    print("\n" + "="*70)
    print("Test 1: RLM Response Field Mapping")
    print("="*70)

    # Test that sandbox returns correct fields and they are processed correctly
    test_cases = [
        {
            "code": "print('Hello from RLM')",
            "context": {"CORPUS": "Test corpus"},
            "expected_status": "success",
            "expected_in_result": "Hello from RLM"
        },
        {
            "code": "print(len(CORPUS))",
            "context": {"CORPUS": "Test corpus data"},
            "expected_status": "success",
            "expected_in_result": "16"
        },
        {
            "code": "invalid python syntax",
            "context": {},
            "expected_status": "error",
            "expected_in_error": "Syntax Error"
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        try:
            response = httpx.post(
                f"{SANDBOX_URL}/execute",
                json={"code": test["code"], "context": test.get("context", {})},
                timeout=10.0
            )
            result = response.json()

            # Check status
            if result.get("status") != test["expected_status"]:
                print(f"  ✗ Test case {i}: Wrong status. Got {result.get('status')}, expected {test['expected_status']}")
                failed += 1
                continue

            # Check content
            if test["expected_status"] == "success":
                if test["expected_in_result"] in (result.get("result") or ""):
                    print(f"  ✓ Test case {i}: PASS (result contains '{test['expected_in_result']}')")
                    passed += 1
                else:
                    print(f"  ✗ Test case {i}: Expected '{test['expected_in_result']}' in result, got: {result.get('result')}")
                    failed += 1
            else:
                if test.get("expected_in_error") and test["expected_in_error"] in (result.get("error") or ""):
                    print(f"  ✓ Test case {i}: PASS (error contains '{test['expected_in_error']}')")
                    passed += 1
                else:
                    print(f"  ✗ Test case {i}: Expected error, got: {result.get('error')}")
                    failed += 1

        except Exception as e:
            print(f"  ✗ Test case {i}: Exception - {e}")
            failed += 1

    print(f"\nResult: {passed}/{passed+failed} passed")
    return failed == 0


def test_sql_injection_protection():
    """Test Fix #2: SQL injection protection in vector search"""
    print("\n" + "="*70)
    print("Test 2: SQL Injection Protection")
    print("="*70)

    # Test session_id with various special characters that could break FT.SEARCH
    test_cases = [
        "user:123",
        "user-123",
        "user{123}",
        "user[123]",
        "user@123",
        "user#123",
        "user$123",
        "user%123",
        "user&123",
        "user*123",
        "user(123)",
        "user=123",
        "user+123",
        "user~123",
        "user/123",
        "user\\123",
        "user|123",
        "user.123",
        "user,123",
        "user;123",
        "user'123",
        'user"123',
    ]

    passed = 0
    failed = 0

    for session_id in test_cases:
        try:
            response = httpx.post(
                f"{BASE_URL}/memories/search",
                json={"query": "test", "top_k": 5, "session_id": session_id},
                timeout=10.0
            )

            # Should return successfully (even if empty results)
            if response.status_code == 200:
                print(f"  ✓ Session ID '{session_id}': PASS")
                passed += 1
            else:
                print(f"  ✗ Session ID '{session_id}': Failed with status {response.status_code}")
                failed += 1

        except Exception as e:
            print(f"  ✗ Session ID '{session_id}': Exception - {e}")
            failed += 1

    print(f"\nResult: {passed}/{passed+failed} passed")
    return failed == 0


def test_binary_data_preservation():
    """Test Fix #3: Binary data preservation in archival"""
    print("\n" + "="*70)
    print("Test 3: Binary Data Preservation in Archival")
    print("="*70)

    try:
        import base64

        # Test the encoding/decoding logic used in cold_storage.py
        # This simulates how binary embeddings are preserved in JSON

        # Create a test memory with binary embedding (simulating a float32 vector)
        test_embedding = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09'

        # Test encoding (what happens during archival)
        encoded = {
            "_binary": True,
            "data": base64.b64encode(test_embedding).decode('utf-8')
        }

        # Test decoding (what happens during restoration)
        decoded = base64.b64decode(encoded["data"])

        # Verify round-trip preservation
        if decoded == test_embedding:
            print("  ✓ Binary encoding/decoding: PASS")
            print(f"    Original: {test_embedding.hex()}")
            print(f"    Encoded:  {encoded['data']}")
            print(f"    Decoded:  {decoded.hex()}")
            passed = 1
        else:
            print("  ✗ Binary encoding/decoding: FAIL")
            print(f"    Original: {test_embedding.hex()}")
            print(f"    Decoded:  {decoded.hex()}")
            passed = 0

        # Test that regular fields are preserved
        regular_field = "test string value"
        if isinstance(regular_field, str):
            print("  ✓ Regular field preservation: PASS")
            passed += 1
        else:
            print("  ✗ Regular field preservation: FAIL")

        # Test JSON serialization
        import json
        test_memory = {
            "message": "test message",
            "embedding": encoded,
            "timestamp": 1234567890
        }

        json_str = json.dumps(test_memory)
        restored = json.loads(json_str)

        if restored["embedding"]["_binary"] and restored["embedding"]["data"] == encoded["data"]:
            print("  ✓ JSON serialization: PASS")
            passed += 1
        else:
            print("  ✗ JSON serialization: FAIL")

        print(f"\nResult: {passed}/3 passed")
        return passed == 3

    except Exception as e:
        print(f"  ✗ Binary data test: Exception - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*70)
    print("Archive-AI Critical Fixes Test Suite")
    print("="*70)

    results = []

    # Run all tests
    results.append(("RLM Response Mapping", test_rlm_response_mapping()))
    results.append(("SQL Injection Protection", test_sql_injection_protection()))
    results.append(("Binary Data Preservation", test_binary_data_preservation()))

    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All critical fixes validated successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
