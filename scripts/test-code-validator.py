#!/usr/bin/env python3
"""
Test script for code validator integration.
Verifies that code validation catches common issues before execution.
"""

import sys
import os
import importlib.util

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import code_validator directly without triggering __init__.py
validator_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'brain', 'agents', 'code_validator.py'
)
spec = importlib.util.spec_from_file_location("code_validator", validator_path)
code_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(code_validator)
validate_code = code_validator.validate_code


def test_validation():
    """Run comprehensive validation tests"""

    print("=" * 70)
    print("Code Validator Test Suite")
    print("=" * 70)
    print()

    tests_passed = 0
    tests_failed = 0

    # Test 1: Valid code with print
    print("Test 1: Valid code with print() statement")
    code = "result = 2 + 2\nprint(result)"
    is_valid, msg = validate_code(code)
    if is_valid and msg is None:
        print("✓ PASS: Code accepted")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected valid, got: {msg}")
        tests_failed += 1
    print()

    # Test 2: Code without print (should warn but allow)
    print("Test 2: Code without print() statement")
    code = "result = 2 + 2"
    is_valid, msg = validate_code(code)
    if is_valid and msg and "WARNING" in msg:
        print(f"✓ PASS: Code accepted with warning")
        print(f"  Warning: {msg[:60]}...")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected warning, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 3: Syntax error
    print("Test 3: Syntax error detection")
    code = "print(2 +)"
    is_valid, msg = validate_code(code)
    if not is_valid and "Syntax error" in msg:
        print(f"✓ PASS: Syntax error caught")
        print(f"  Error: {msg[:60]}...")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected syntax error, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 4: Dangerous import (os)
    print("Test 4: Dangerous import detection (os)")
    code = "import os\nprint(os.getcwd())"
    is_valid, msg = validate_code(code)
    if not is_valid and "Blocked imports" in msg:
        print(f"✓ PASS: Dangerous import blocked")
        print(f"  Error: {msg[:60]}...")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected import block, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 5: Dangerous import (subprocess)
    print("Test 5: Dangerous import detection (subprocess)")
    code = "import subprocess\nsubprocess.run(['ls'])"
    is_valid, msg = validate_code(code)
    if not is_valid and "Blocked imports" in msg:
        print(f"✓ PASS: Dangerous import blocked")
        print(f"  Error: {msg[:60]}...")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected import block, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 6: Function definition without call
    print("Test 6: Function definition without call")
    code = "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"
    is_valid, msg = validate_code(code)
    if is_valid and msg and "function but doesn't call it" in msg:
        print(f"✓ PASS: Function warning generated")
        print(f"  Warning: {msg[:60]}...")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected function warning, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 7: Class definition without usage
    print("Test 7: Class definition without usage")
    code = "class MyClass:\n    def __init__(self):\n        self.value = 42"
    is_valid, msg = validate_code(code)
    if is_valid and msg and "class but doesn't use it" in msg:
        print(f"✓ PASS: Class warning generated")
        print(f"  Warning: {msg[:60]}...")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected class warning, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 8: Empty code
    print("Test 8: Empty code detection")
    code = "   "
    is_valid, msg = validate_code(code)
    if not is_valid and "empty" in msg.lower():
        print(f"✓ PASS: Empty code rejected")
        print(f"  Error: {msg}")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected empty error, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 9: Code too long
    print("Test 9: Code length limit")
    code = "print('x')\n" * 1000  # >5000 chars
    is_valid, msg = validate_code(code)
    if not is_valid and "too long" in msg:
        print(f"✓ PASS: Long code rejected")
        print(f"  Error: {msg[:60]}...")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Expected length error, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 10: Safe imports allowed
    print("Test 10: Safe imports allowed (math, json)")
    code = "import math\nimport json\nprint(math.pi)"
    is_valid, msg = validate_code(code)
    if is_valid:
        print(f"✓ PASS: Safe imports allowed")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Safe imports should be allowed, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Test 11: Complex valid code
    print("Test 11: Complex valid code")
    code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(f"Fibonacci(10) = {result}")
"""
    is_valid, msg = validate_code(code)
    if is_valid:
        print(f"✓ PASS: Complex code validated")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Complex code should be valid, got: is_valid={is_valid}, msg={msg}")
        tests_failed += 1
    print()

    # Summary
    print("=" * 70)
    print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70)

    if tests_failed == 0:
        print("\n✓ All tests passed!\n")
        return 0
    else:
        print(f"\n✗ {tests_failed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    sys.exit(test_validation())
