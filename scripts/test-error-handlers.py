#!/usr/bin/env python3
"""
Test script for error handling system.
Verifies error formatting, message templates, and model checking.
"""

import sys
import os
import importlib.util

# Import error_handlers directly without triggering __init__.py
handlers_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'brain', 'error_handlers.py'
)
spec = importlib.util.spec_from_file_location("error_handlers", handlers_path)
error_handlers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(error_handlers)

# Import classes and functions
ErrorFormatter = error_handlers.ErrorFormatter
ErrorCategory = error_handlers.ErrorCategory
ArchiveAIError = error_handlers.ArchiveAIError
ModelUnavailableError = error_handlers.ModelUnavailableError
RedisUnavailableError = error_handlers.RedisUnavailableError
ValidationError = error_handlers.ValidationError
VRAMExceededError = error_handlers.VRAMExceededError
create_error_message = error_handlers.create_error_message


def test_error_formatting():
    """Test error message formatting"""

    print("=" * 70)
    print("Error Handler Test Suite")
    print("=" * 70)
    print()

    tests_passed = 0
    tests_failed = 0

    # Test 1: ASCII Box Formatting
    print("Test 1: ASCII Box Formatting")
    box_msg = ErrorFormatter.format_box(
        "Model Not Available",
        "Vorpal engine is not responding at http://localhost:8000",
        [
            "Check if Docker container is running: docker ps",
            "Check service logs: docker logs vorpal",
            "Restart services: bash scripts/start.sh"
        ]
    )
    if "╔" in box_msg and "╗" in box_msg and "Model Not Available" in box_msg:
        print("✓ PASS: Box formatting works")
        print("\nExample output:")
        print(box_msg)
        tests_passed += 1
    else:
        print("✗ FAIL: Box formatting failed")
        tests_failed += 1
    print()

    # Test 2: Simple Formatting
    print("Test 2: Simple Error Formatting")
    simple_msg = ErrorFormatter.format_simple("Validation Error", "Input is empty")
    if "⚠" in simple_msg and "Validation Error" in simple_msg and "Input is empty" in simple_msg:
        print("✓ PASS: Simple formatting works")
        print(f"  Output: {simple_msg}")
        tests_passed += 1
    else:
        print("✗ FAIL: Simple formatting failed")
        tests_failed += 1
    print()

    # Test 3: Model Unavailable Error
    print("Test 3: ModelUnavailableError")
    try:
        error = ModelUnavailableError("Vorpal", "Connection refused")
        formatted = error.format(use_box=False)
        if "Model Error" in formatted and "Vorpal" in formatted and "Connection refused" in formatted:
            print("✓ PASS: ModelUnavailableError created")
            print(f"  Message: {formatted}")
            tests_passed += 1
        else:
            print("✗ FAIL: ModelUnavailableError formatting failed")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAIL: ModelUnavailableError raised exception: {e}")
        tests_failed += 1
    print()

    # Test 4: Redis Unavailable Error
    print("Test 4: RedisUnavailableError")
    try:
        error = RedisUnavailableError("Connection timeout")
        formatted = error.format(use_box=False)
        if "Resource Error" in formatted and "Redis" in formatted:
            print("✓ PASS: RedisUnavailableError created")
            print(f"  Message: {formatted}")
            tests_passed += 1
        else:
            print("✗ FAIL: RedisUnavailableError formatting failed")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAIL: RedisUnavailableError raised exception: {e}")
        tests_failed += 1
    print()

    # Test 5: Validation Error
    print("Test 5: ValidationError")
    try:
        error = ValidationError("message", "cannot be empty")
        formatted = error.format(use_box=False)
        if "Validation Error" in formatted and "message" in formatted:
            print("✓ PASS: ValidationError created")
            print(f"  Message: {formatted}")
            tests_passed += 1
        else:
            print("✗ FAIL: ValidationError formatting failed")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAIL: ValidationError raised exception: {e}")
        tests_failed += 1
    print()

    # Test 6: VRAM Exceeded Error
    print("Test 6: VRAMExceededError")
    try:
        error = VRAMExceededError(15500.0, 13500.0)
        formatted = error.format(use_box=False)
        if "Resource Error" in formatted and "15500" in formatted and "13500" in formatted:
            print("✓ PASS: VRAMExceededError created")
            print(f"  Message: {formatted}")
            tests_passed += 1
        else:
            print("✗ FAIL: VRAMExceededError formatting failed")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAIL: VRAMExceededError raised exception: {e}")
        tests_failed += 1
    print()

    # Test 7: Error Message Templates
    print("Test 7: Error Message Templates")
    test_cases = [
        ("empty_input", {"field_name": "message"}, "Input cannot be empty"),
        ("too_long", {"field_name": "code", "current": 6000, "maximum": 5000}, "6000"),
        ("out_of_range", {"field_name": "timeout", "current": 50, "minimum": 1, "maximum": 30}, "out of range"),
        ("not_found", {"resource": "Memory", "identifier": "mem:12345"}, "not found"),
    ]

    template_passed = 0
    for template_key, kwargs, expected_substring in test_cases:
        msg = create_error_message(template_key, **kwargs)
        if expected_substring in msg:
            template_passed += 1
        else:
            print(f"  ✗ Template '{template_key}' failed: {msg}")

    if template_passed == len(test_cases):
        print(f"✓ PASS: All {len(test_cases)} error templates work")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Only {template_passed}/{len(test_cases)} templates passed")
        tests_failed += 1
    print()

    # Test 8: Recovery Steps
    print("Test 8: Recovery Steps in Box Format")
    error = ModelUnavailableError("Goblin", "Port 8001 unreachable")
    formatted_box = error.format(use_box=True)
    if "Recovery Steps:" in formatted_box and "docker ps" in formatted_box:
        print("✓ PASS: Recovery steps included in box format")
        tests_passed += 1
    else:
        print("✗ FAIL: Recovery steps missing or malformed")
        tests_failed += 1
    print()

    # Test 9: Error Categories
    print("Test 9: Error Categories")
    categories = [
        (ErrorCategory.MODEL, "model"),
        (ErrorCategory.NETWORK, "network"),
        (ErrorCategory.VALIDATION, "validation"),
        (ErrorCategory.RESOURCE, "resource"),
    ]

    category_passed = 0
    for category, expected_value in categories:
        if category.value == expected_value:
            category_passed += 1

    if category_passed == len(categories):
        print(f"✓ PASS: All {len(categories)} error categories defined correctly")
        tests_passed += 1
    else:
        print(f"✗ FAIL: Only {category_passed}/{len(categories)} categories valid")
        tests_failed += 1
    print()

    # Test 10: Custom Error with Context
    print("Test 10: Custom Error with Context")
    try:
        error = ArchiveAIError(
            "Custom error for testing",
            category=ErrorCategory.VALIDATION,
            context={"request_id": "req-12345", "user": "test"},
            recovery_steps=["Step 1", "Step 2"]
        )
        if error.context["request_id"] == "req-12345" and len(error.recovery_steps) == 2:
            print("✓ PASS: Custom error with context works")
            tests_passed += 1
        else:
            print("✗ FAIL: Context or recovery steps not stored correctly")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAIL: Custom error raised exception: {e}")
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
    sys.exit(test_error_formatting())
