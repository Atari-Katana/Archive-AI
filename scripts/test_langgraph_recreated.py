
import asyncio
import sys
import os
from unittest.mock import MagicMock

# Mock dependencies that might be missing or fail to import
sys.modules['redis'] = MagicMock()
sys.modules['redis.asyncio'] = MagicMock()
sys.modules['stream_handler'] = MagicMock()
sys.modules['services'] = MagicMock()
sys.modules['services.llm'] = MagicMock()

# Mock config
mock_config = MagicMock()
mock_config.VORPAL_URL = "http://mock-vorpal"
sys.modules['config'] = MagicMock()
sys.modules['config'].config = mock_config

# Mock LLM
mock_llm = MagicMock()
async def mock_chat(*args, **kwargs):
    return {"content": "Mocked LLM Response"}
mock_llm.chat = mock_chat
sys.modules['services.llm'].llm = mock_llm

# Add project root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'brain'))

from brain.agents.langgraph_agent import SimpleLangGraphAgent, MultiStepWorkflowAgent

async def test_simple_agent():

    print("\n--- Testing SimpleLangGraphAgent ---")
    agent = SimpleLangGraphAgent()
    result = await agent.run_workflow("What is the capital of France?")
    print(f"Steps: {result['steps']}")
    print(f"Output: {result['output']}")
    print(f"Error: {result['error']}")
    assert result['error'] is None
    assert "interpret" in result['steps']
    assert "generate" in result['steps']

async def test_complex_agent():
    print("\n--- Testing MultiStepWorkflowAgent ---")
    agent = MultiStepWorkflowAgent()
    
    # Test High Confidence Path
    print("Testing 'simple' query (should skip verify)...")
    res1 = await agent.run_workflow("simple question")
    print(f"Steps: {res1['steps']}")
    assert "verify" not in res1['steps']
    
    # Test Low Confidence Path
    print("Testing 'hard' query (should verify)...")
    res2 = await agent.run_workflow("hard question")
    print(f"Steps: {res2['steps']}")
    assert "verify" in res2['steps']

async def main():
    try:
        await test_simple_agent()
        await test_complex_agent()
        print("\n✅ All LangGraph tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
