#!/usr/bin/env python3
"""
Vorpal Engine Direct Performance Test
Tests the Vorpal (vLLM) service directly.
"""

import asyncio
import httpx
import json
import time
import sys

VORPAL_URL = "http://localhost:8000"

# Fetch model name first
async def get_model_name():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{VORPAL_URL}/v1/models")
            resp.raise_for_status()
            data = resp.json()
            return data['data'][0]['id']
        except Exception as e:
            print(f"Error fetching model name: {e}")
            return "test"

async def test_completion(model_name, prompt, max_tokens, test_name):
    print(f"--- Running Test: {test_name} ---")
    start_time = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        try:
            resp = await client.post(f"{VORPAL_URL}/v1/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data['choices'][0]['text']
            duration = (time.perf_counter() - start_time) * 1000
            
            tokens = data['usage']['completion_tokens']
            tps = tokens / (duration / 1000)
            
            print(f"✅ Success ({duration:.2f}ms)")
            print(f"Output: {text[:100]}...")
            print(f"Speed: {tps:.2f} tokens/sec")
            return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            if 'resp' in locals():
                print(f"Response: {resp.text}")
            return False

async def test_streaming(model_name):
    print(f"--- Running Test: Streaming ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "model": model_name,
            "prompt": "Count from 1 to 10.",
            "max_tokens": 50,
            "stream": True
        }
        try:
            async with client.stream("POST", f"{VORPAL_URL}/v1/completions", json=payload) as resp:
                resp.raise_for_status()
                first_token = True
                print("Stream output:", end=" ", flush=True)
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            text = data['choices'][0]['text']
                            print(text, end="", flush=True)
                        except:
                            pass
                print("\n✅ Stream finished")
                return True
        except Exception as e:
            print(f"\n❌ Streaming Failed: {e}")
            return False

async def main():
    print(f"Connecting to Vorpal at {VORPAL_URL}...")
    model_name = await get_model_name()
    print(f"Target Model: {model_name}")

    # 1. Short Test
    if not await test_completion(model_name, "Hello, how are you?", 20, "Short Prompt"):
        sys.exit(1)

    # 2. Medium Test
    if not await test_completion(model_name, "Write a short poem about coding.", 100, "Medium Prompt"):
        sys.exit(1)

    # 3. Context Test (Simulate large context)
    # 3000 chars ~ 750 tokens
    large_prompt = "This is a test of the context window. " * 200 
    if not await test_completion(model_name, large_prompt + "\nSummarize this.", 50, "Large Context"):
        sys.exit(1)

    # 4. Streaming Test
    if not await test_streaming(model_name):
        sys.exit(1)

    print("\n🎉 ALL THOROUGH TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(main())
