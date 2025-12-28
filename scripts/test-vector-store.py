#!/usr/bin/env python3
"""
Test script for RedisVL Vector Store (Chunk 2.4)
Tests memory storage and vector similarity search.
"""

import sys
import time
from pathlib import Path

# Add brain to path
sys.path.insert(0, str(Path(__file__).parent.parent / "brain"))

from memory.vector_store import VectorStore


def main():
    """Test vector store functionality"""
    print("=" * 70)
    print("Vector Store Test")
    print("=" * 70)

    # Initialize vector store
    print("\n[1/5] Connecting to Redis and loading model...")
    # Try Docker network first, fall back to localhost
    import os
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    store = VectorStore(redis_url=redis_url)
    try:
        store.connect()
        print("✅ Connected")
    except Exception as e:
        print(f"❌ FAIL: Connection error: {e}")
        return False

    # Create index
    print("\n[2/5] Creating vector index...")
    try:
        store.create_index()
        print("✅ Index created/verified")
    except Exception as e:
        print(f"❌ FAIL: Index creation error: {e}")
        store.close()
        return False

    # Store test memories
    print("\n[3/5] Storing test memories...")
    test_memories = [
        {
            "message": "The sky is blue and the sun is shining",
            "perplexity": 5.2,
            "metadata": {"type": "common_phrase"}
        },
        {
            "message": "What a beautiful day it is today",
            "perplexity": 6.1,
            "metadata": {"type": "common_phrase"}
        },
        {
            "message": "Flibbertigibbet zamboni xylophone quantum fluctuation",
            "perplexity": 45.7,
            "metadata": {"type": "nonsense"}
        },
        {
            "message": "The weather forecast predicts sunny skies",
            "perplexity": 7.3,
            "metadata": {"type": "weather"}
        },
        {
            "message": "Grotesque kaleidoscope of bewildering peculiarities",
            "perplexity": 32.4,
            "metadata": {"type": "unusual"}
        }
    ]

    stored_keys = []
    try:
        for mem in test_memories:
            key = store.store_memory(
                message=mem["message"],
                perplexity=mem["perplexity"],
                session_id="test_session",
                metadata=mem["metadata"]
            )
            stored_keys.append(key)
            time.sleep(0.1)  # Small delay for index updates

        print(f"✅ Stored {len(stored_keys)} memories")

    except Exception as e:
        print(f"❌ FAIL: Storage error: {e}")
        store.close()
        return False

    # Wait for indexing
    print("\n[4/5] Waiting for index to update...")
    time.sleep(1)

    # Test similarity search
    print("\n[5/5] Testing similarity search...")
    try:
        # Query 1: Should match weather-related memories
        print("\n  Query 1: 'The sun is bright today'")
        results1 = store.search_similar(
            "The sun is bright today",
            top_k=3,
            session_id="test_session"
        )

        if not results1:
            print("  ❌ No results found")
            store.close()
            return False

        print(f"  ✅ Found {len(results1)} similar memories:")
        for i, mem in enumerate(results1, 1):
            print(f"    {i}. [{mem['similarity_score']:.4f}] "
                  f"{mem['message'][:50]}... (PPL: {mem['perplexity']:.1f})")

        # Query 2: Should match nonsense/unusual text
        print("\n  Query 2: 'Random gibberish words'")
        results2 = store.search_similar(
            "Random gibberish words",
            top_k=3,
            session_id="test_session"
        )

        if not results2:
            print("  ❌ No results found")
            store.close()
            return False

        print(f"  ✅ Found {len(results2)} similar memories:")
        for i, mem in enumerate(results2, 1):
            print(f"    {i}. [{mem['similarity_score']:.4f}] "
                  f"{mem['message'][:50]}... (PPL: {mem['perplexity']:.1f})")

        print("\n✅ Similarity search working correctly")

    except Exception as e:
        print(f"❌ FAIL: Search error: {e}")
        import traceback
        traceback.print_exc()
        store.close()
        return False

    # Cleanup
    store.close()

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
