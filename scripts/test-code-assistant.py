#!/usr/bin/env python3
"""
Test script for Code Assistant Agent (Chunk 5.5)
Tests code generation, execution, and debugging capabilities
"""

import requests
import json


BRAIN_URL = "http://localhost:8080"


def test_simple_function():
    """Test simple function generation"""
    print("\n=== Test 1: Simple Function (Factorial) ===")

    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={
            "task": "Write a function to calculate factorial of a number, then test it with n=5"
        }
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Task: {data['task'][:60]}...")
    print(f"Success: {data['success']}")
    print(f"Attempts: {data['attempts']}")
    print(f"Test Output: {data['test_output']}")
    print(f"Code Preview: {data['code'][:100]}...")

    assert response.status_code == 200
    assert data['success'] is True
    assert data['test_output'] is not None
    assert len(data['code']) > 0
    print("✅ PASS")


def test_string_manipulation():
    """Test string manipulation function"""
    print("\n=== Test 2: String Manipulation (Palindrome) ===")

    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={
            "task": "Write a function to check if a string is a palindrome, test with 'racecar' and 'hello'"
        }
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Success: {data['success']}")
    print(f"Attempts: {data['attempts']}")
    print(f"Test Output: {data['test_output']}")

    assert response.status_code == 200
    assert data['success'] is True
    assert "True" in data['test_output']  # racecar is palindrome
    assert "False" in data['test_output']  # hello is not
    print("✅ PASS")


def test_list_operations():
    """Test list manipulation"""
    print("\n=== Test 3: List Operations (Find Max) ===")

    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={
            "task": "Write a function to find the maximum value in a list, test with [3, 1, 4, 1, 5, 9, 2, 6]"
        }
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Success: {data['success']}")
    print(f"Attempts: {data['attempts']}")
    print(f"Test Output: {data['test_output']}")

    assert response.status_code == 200
    assert data['success'] is True
    # Maximum value should be 9
    assert "9" in data['test_output']
    print("✅ PASS")


def test_error_handling():
    """Test error handling for invalid requests"""
    print("\n=== Test 4: Error Handling ===")

    # Empty task
    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={"task": ""}
    )
    print(f"Empty task status: {response.status_code}")
    assert response.status_code == 400
    print("✅ Empty task rejected")

    # Invalid max_attempts
    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={"task": "test", "max_attempts": 10}
    )
    print(f"Invalid max_attempts status: {response.status_code}")
    assert response.status_code == 400
    print("✅ Invalid max_attempts rejected")

    # Invalid timeout
    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={"task": "test", "timeout": 100}
    )
    print(f"Invalid timeout status: {response.status_code}")
    assert response.status_code == 400
    print("✅ Invalid timeout rejected")

    print("✅ PASS")


def test_code_quality():
    """Test code quality and explanation"""
    print("\n=== Test 5: Code Quality (FizzBuzz) ===")

    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={
            "task": "Write a FizzBuzz function that prints numbers 1-15, replacing multiples of 3 with Fizz, multiples of 5 with Buzz, and multiples of both with FizzBuzz"
        }
    )

    data = response.json()

    print(f"Success: {data['success']}")
    print(f"Attempts: {data['attempts']}")
    print(f"Has explanation: {len(data['explanation']) > 0}")
    print(f"Test Output Preview: {data['test_output'][:100] if data['test_output'] else 'None'}...")

    assert response.status_code == 200
    assert data['success'] is True
    assert len(data['explanation']) > 0
    assert data['test_output'] is not None

    # Check for FizzBuzz in output
    if data['test_output']:
        output = data['test_output']
        assert "Fizz" in output or "fizz" in output.lower()
        print("✅ FizzBuzz logic present")

    print("✅ PASS")


def test_timeout_handling():
    """Test timeout parameter"""
    print("\n=== Test 6: Timeout Handling ===")

    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={
            "task": "Write a simple function that adds two numbers and test it with 5 and 3",
            "timeout": 5  # Short timeout
        }
    )

    data = response.json()

    print(f"Success: {data['success']}")
    print(f"Attempts: {data['attempts']}")
    print(f"Completed within timeout: {data['success']}")

    assert response.status_code == 200
    # Simple addition should complete quickly
    assert data['success'] is True
    print("✅ PASS")


def test_multiple_test_cases():
    """Test function with multiple test cases"""
    print("\n=== Test 7: Multiple Test Cases (Even/Odd) ===")

    response = requests.post(
        f"{BRAIN_URL}/code_assist",
        json={
            "task": "Write a function to check if a number is even, test with numbers 2, 3, 10, 7"
        }
    )

    data = response.json()

    print(f"Success: {data['success']}")
    print(f"Test Output: {data['test_output']}")

    assert response.status_code == 200
    assert data['success'] is True
    assert data['test_output'] is not None
    print("✅ PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Code Assistant Agent Test Suite (Chunk 5.5)")
    print("=" * 60)

    try:
        test_simple_function()
        test_string_manipulation()
        test_list_operations()
        test_error_handling()
        test_code_quality()
        test_timeout_handling()
        test_multiple_test_cases()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
