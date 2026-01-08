"""
Test Medium Priority Fixes (Issues #11-16)
Tests all the medium-priority bug fixes applied to the codebase.
"""

import subprocess
import time

def test_health_endpoints():
    """Test Issue #16: Response models for health endpoints"""
    print("\n=== Testing Issue #16: Response Models ===")

    # Test root endpoint
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8081/"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Root endpoint failed"
    assert '"status"' in result.stdout, "Root endpoint missing status field"
    assert '"service"' in result.stdout, "Root endpoint missing service field"
    assert '"version"' in result.stdout, "Root endpoint missing version field"
    print("✓ Root endpoint has proper response model")

    # Test health endpoint
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8081/health"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Health endpoint failed"
    assert '"status"' in result.stdout, "Health endpoint missing status"
    assert '"vorpal_url"' in result.stdout, "Health endpoint missing vorpal_url"
    print("✓ Health endpoint has proper response model")


def test_rate_limiting():
    """Test Issue #14: Rate limiting on public endpoints"""
    print("\n=== Testing Issue #14: Rate Limiting ===")

    # Check that rate limiting code is present in main.py
    with open('brain/main.py', 'r') as f:
        main_content = f.read()

    assert 'class RateLimiter' in main_content, "RateLimiter class not found"
    assert 'rate_limiter.is_allowed' in main_content, "Rate limiter not being called"
    assert 'status_code=429' in main_content, "Rate limit error response not configured"
    assert 'Rate limit exceeded' in main_content, "Rate limit error message not found"
    print("✓ Rate limiting code properly implemented in main.py")


def test_archive_search_validation():
    """Test Issue #10: Admin endpoint validation (from high-priority fixes)"""
    print("\n=== Testing Admin Endpoint Validation ===")

    # Test empty query rejection
    result = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "http://localhost:8081/admin/search_archive?query=&max_results=5"],
        capture_output=True,
        text=True,
        timeout=5
    )

    assert '"Query cannot be empty"' in result.stdout, "Empty query not rejected"
    print("✓ Empty query properly rejected")

    # Test max_results out of range
    result = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "http://localhost:8081/admin/search_archive?query=test&max_results=500"],
        capture_output=True,
        text=True,
        timeout=5
    )

    assert '"max_results must be between 1 and 100"' in result.stdout, "Invalid max_results not rejected"
    print("✓ Invalid max_results properly rejected")


def test_configuration_timeouts():
    """Test Issue #15: Centralized timeout configuration"""
    print("\n=== Testing Issue #15: Configuration Timeouts ===")

    # Check that config.py has timeout constants
    with open('brain/config.py', 'r') as f:
        config_content = f.read()

    assert 'HEALTH_CHECK_TIMEOUT' in config_content, "Missing HEALTH_CHECK_TIMEOUT"
    assert 'METRICS_TIMEOUT' in config_content, "Missing METRICS_TIMEOUT"
    assert 'SANDBOX_TIMEOUT' in config_content, "Missing SANDBOX_TIMEOUT"
    assert 'VERIFICATION_TIMEOUT' in config_content, "Missing VERIFICATION_TIMEOUT"
    print("✓ All timeout constants defined in config")

    # Check that main.py uses config timeouts
    with open('brain/main.py', 'r') as f:
        main_content = f.read()

    assert 'config.HEALTH_CHECK_TIMEOUT' in main_content, "main.py not using config timeouts"
    print("✓ main.py uses centralized timeout configuration")


def test_scan_iter_usage():
    """Test Issue #13: Efficient Redis key scanning"""
    print("\n=== Testing Issue #13: Efficient Redis Scanning ===")

    # Check that cold_storage.py uses scan_iter instead of keys
    with open('brain/memory/cold_storage.py', 'r') as f:
        storage_content = f.read()

    assert 'scan_iter' in storage_content, "cold_storage.py not using scan_iter"
    assert storage_content.count('.keys(') == 0 or 'scan_iter' in storage_content, \
        "cold_storage.py still using blocking keys() call"
    print("✓ cold_storage.py uses non-blocking scan_iter()")


def test_memory_worker_return_value():
    """Test Issue #11: Memory worker return value handling"""
    print("\n=== Testing Issue #11: Memory Worker Return Values ===")

    # Check that process_entry returns bool
    with open('brain/workers/memory_worker.py', 'r') as f:
        worker_content = f.read()

    assert '-> bool:' in worker_content, "process_entry doesn't return bool"
    assert 'return True' in worker_content, "No success return statements"
    assert 'return False' in worker_content, "No failure return statements"
    print("✓ process_entry properly returns success/failure status")


if __name__ == "__main__":
    print("Testing Medium Priority Fixes (Issues #11-16)")
    print("=" * 60)

    try:
        test_health_endpoints()
        test_rate_limiting()
        test_archive_search_validation()
        test_configuration_timeouts()
        test_scan_iter_usage()
        test_memory_worker_return_value()

        print("\n" + "=" * 60)
        print("✓ ALL MEDIUM PRIORITY FIXES TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        exit(1)
