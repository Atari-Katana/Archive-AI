#!/usr/bin/env python3
"""
Test script for Redis Stack setup (Chunk 1.1)
Verifies:
- Redis connection
- RedisJSON module
- RediSearch module
- Memory limit configuration
"""

import redis
import json
import sys


def test_redis():
    """Test Redis Stack functionality"""
    print("=" * 60)
    print("Redis Stack Test - Chunk 1.1")
    print("=" * 60)

    try:
        # Connect to Redis
        print("\n[1/5] Testing Redis connection...")
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Test 1: Ping
        print("    Sending PING...")
        response = r.ping()
        if response:
            print("    ✅ PASS: Redis responds to PING")
        else:
            print("    ❌ FAIL: Redis did not respond to PING")
            return False

        # Test 2: RedisJSON - JSON.SET
        print("\n[2/5] Testing RedisJSON (JSON.SET)...")
        test_data = {
            "name": "Archive-AI",
            "version": "7.5",
            "type": "memory_test"
        }
        r.execute_command('JSON.SET', 'test:json', '$', json.dumps(test_data))
        print("    ✅ PASS: JSON.SET executed successfully")

        # Test 3: RedisJSON - JSON.GET
        print("\n[3/5] Testing RedisJSON (JSON.GET)...")
        result = r.execute_command('JSON.GET', 'test:json')
        retrieved_data = json.loads(result)
        if retrieved_data == test_data:
            print("    ✅ PASS: JSON.GET retrieved correct data")
            print(f"    Retrieved: {retrieved_data}")
        else:
            print("    ❌ FAIL: Data mismatch")
            print(f"    Expected: {test_data}")
            print(f"    Got: {retrieved_data}")
            return False

        # Test 4: RediSearch - Create index
        print("\n[4/5] Testing RediSearch (FT.CREATE)...")
        try:
            # Drop index if it exists
            try:
                r.execute_command('FT.DROPINDEX', 'test_index')
            except redis.exceptions.ResponseError:
                pass

            # Create a simple index
            r.execute_command(
                'FT.CREATE', 'test_index',
                'ON', 'JSON',
                'PREFIX', '1', 'test:',
                'SCHEMA',
                '$.name', 'AS', 'name', 'TEXT',
                '$.version', 'AS', 'version', 'TEXT'
            )
            print("    ✅ PASS: RediSearch index created successfully")

            # Verify index exists
            indexes = r.execute_command('FT._LIST')
            if 'test_index' in indexes:
                print("    ✅ PASS: Index verified in FT._LIST")
            else:
                print("    ❌ FAIL: Index not found in FT._LIST")
                return False

        except redis.exceptions.ResponseError as e:
            print(f"    ❌ FAIL: RediSearch error: {e}")
            return False

        # Test 5: Memory limit check
        print("\n[5/5] Testing memory limit configuration...")
        info = r.info('memory')
        maxmemory = info.get('maxmemory', 0)
        maxmemory_policy = info.get('maxmemory_policy', 'unknown')

        # Convert to GB for readability
        maxmemory_gb = maxmemory / (1024**3) if maxmemory > 0 else 0

        print(f"    Max Memory: {maxmemory_gb:.2f} GB")
        print(f"    Eviction Policy: {maxmemory_policy}")

        # Check if maxmemory is set to 20GB (allowing for small variance)
        expected_bytes = 20 * 1024**3
        if abs(maxmemory - expected_bytes) < 1024**2:  # Within 1MB
            print("    ✅ PASS: Memory limit set to ~20GB")
        else:
            msg = (f"    ❌ FAIL: Memory limit not set correctly "
                   f"(expected ~20GB, got {maxmemory_gb:.2f}GB)")
            print(msg)
            return False

        if maxmemory_policy == 'allkeys-lru':
            print("    ✅ PASS: Eviction policy set to allkeys-lru")
        else:
            msg = (f"    ❌ FAIL: Eviction policy incorrect "
                   f"(expected allkeys-lru, got {maxmemory_policy})")
            print(msg)
            return False

        # Cleanup
        print("\n[Cleanup] Removing test data...")
        r.delete('test:json')
        try:
            r.execute_command('FT.DROPINDEX', 'test_index')
        except redis.exceptions.ResponseError:
            pass
        print("    ✅ Cleanup complete")

        # Final result
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nRedis Stack is configured correctly:")
        print("  - Redis connection: ✅")
        print("  - RedisJSON module: ✅")
        print("  - RediSearch module: ✅")
        print("  - Memory limit (20GB): ✅")
        print("  - Eviction policy (allkeys-lru): ✅")
        print("\nChunk 1.1 pass criteria met.")
        return True

    except redis.exceptions.ConnectionError:
        print("\n❌ FAIL: Could not connect to Redis")
        print("   Make sure Redis is running: docker-compose up -d redis")
        return False
    except Exception as e:
        print(f"\n❌ FAIL: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_redis()
    sys.exit(0 if success else 1)
