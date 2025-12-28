#!/usr/bin/env python3
"""
Test script for Research Assistant Agent (Chunk 5.4)
Tests single-query and multi-query research with citations
"""

import requests
import json


BRAIN_URL = "http://localhost:8080"


def test_single_query_library():
    """Test single question with library sources"""
    print("\n=== Test 1: Single Query (Library Only) ===")

    response = requests.post(
        f"{BRAIN_URL}/research",
        json={
            "question": "What is vector search and how does it work?",
            "use_library": True,
            "use_memory": False,
            "top_k": 3
        }
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Question: {data['question']}")
    print(f"Answer: {data['answer'][:200]}...")
    print(f"Library chunks: {data['library_chunks_consulted']}")
    print(f"Memories: {data['memories_consulted']}")
    print(f"Total sources: {data['total_sources']}")
    print(f"Success: {data['success']}")

    assert response.status_code == 200
    assert data['success'] is True
    assert data['library_chunks_consulted'] > 0
    assert len(data['answer']) > 0
    print("✅ PASS")


def test_single_query_both():
    """Test single question with both library and memory sources"""
    print("\n=== Test 2: Single Query (Library + Memory) ===")

    response = requests.post(
        f"{BRAIN_URL}/research",
        json={
            "question": "What are the applications of vector search?",
            "use_library": True,
            "use_memory": True,
            "top_k": 3
        }
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Question: {data['question']}")
    print(f"Answer: {data['answer'][:200]}...")
    print(f"Library chunks: {data['library_chunks_consulted']}")
    print(f"Memories: {data['memories_consulted']}")
    print(f"Total sources: {data['total_sources']}")
    print(f"Success: {data['success']}")

    assert response.status_code == 200
    assert data['success'] is True
    assert len(data['answer']) > 0
    print("✅ PASS")


def test_multi_query_research():
    """Test multi-question research with synthesis"""
    print("\n=== Test 3: Multi-Query Research with Synthesis ===")

    response = requests.post(
        f"{BRAIN_URL}/research/multi",
        json={
            "questions": [
                "What is vector search?",
                "What is HNSW?",
                "What is cosine similarity?"
            ],
            "synthesize": True
        }
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Questions: {data['questions']}")
    print(f"Results: {len(data['results'])}")
    print(f"Synthesis: {data['synthesis'][:200]}...")
    print(f"Total sources: {data['total_sources']}")

    assert response.status_code == 200
    assert data['questions'] == 3
    assert len(data['results']) == 3
    assert 'synthesis' in data
    assert len(data['synthesis']) > 0
    print("✅ PASS")


def test_error_handling():
    """Test error handling for invalid requests"""
    print("\n=== Test 4: Error Handling ===")

    # Empty question
    response = requests.post(
        f"{BRAIN_URL}/research",
        json={"question": "", "use_library": True}
    )
    print(f"Empty question status: {response.status_code}")
    assert response.status_code == 400
    print("✅ Empty question rejected")

    # Too many multi-queries
    response = requests.post(
        f"{BRAIN_URL}/research/multi",
        json={"questions": [f"Question {i}" for i in range(15)]}
    )
    print(f"Too many questions status: {response.status_code}")
    assert response.status_code == 400
    print("✅ Too many questions rejected")

    print("✅ PASS")


def test_citations():
    """Test that answers include proper citations"""
    print("\n=== Test 5: Citation Format ===")

    response = requests.post(
        f"{BRAIN_URL}/research",
        json={
            "question": "Explain vector embeddings",
            "use_library": True,
            "use_memory": False,
            "top_k": 3
        }
    )

    data = response.json()
    answer = data['answer']

    print(f"Answer: {answer[:300]}...")

    # Check for citation markers [Source N]
    has_citations = '[Source' in answer or 'Source' in answer
    print(f"Has citations: {has_citations}")

    if data['total_sources'] > 0:
        assert has_citations, "Answer should include citations when sources are available"

    print("✅ PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Research Assistant Agent Test Suite (Chunk 5.4)")
    print("=" * 60)

    try:
        test_single_query_library()
        test_single_query_both()
        test_multi_query_research()
        test_error_handling()
        test_citations()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
