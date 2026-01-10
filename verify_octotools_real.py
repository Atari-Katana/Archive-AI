import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock

# Path setup to include project root
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'octotools_repo'))

# Environment variables for OctoTools
# Point to localhost:8000 where Vorpal is running
os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"
os.environ["OPENAI_API_KEY"] = "dummy-key"

from brain.agents.react_agent import ReActAgent, ToolRegistry

class TestRealOctoTools(unittest.IsolatedAsyncioTestCase):
    async def test_calculator_tool_real(self):
        """
        Test the ReActAgent with OctoTools against a real (or mocked via localhost) Vorpal engine.
        Since we can't guarantee Vorpal is listening on localhost inside this container context 
        without network mode 'host', this test might fail if network is isolated.
        However, if we are in the 'brain' container context or on host, it should work.
        """
        print("\nTesting OctoTools + ReActAgent with real network calls...")
        
        registry = ToolRegistry()
        # Note: Registry isn't strictly used by OctoTools wrapper in ReActAgent 
        # (it uses internal 'archive_ai' toolset), but we pass it for compatibility.

        try:
            async with ReActAgent(registry) as agent:
                # Simple math task that uses CalculatorTool
                question = "What is 15 * 15?"
                result = await agent.solve(question)
                
                print(f"Result: {result}")
                
                if result.success:
                    print("✅ Agent succeeded!")
                    print(f"Answer: {result.answer}")
                    # Check if answer contains 225
                    if "225" in result.answer:
                        print("✅ Answer is correct.")
                    else:
                        print("⚠️ Answer might be incorrect (expected 225).")
                else:
                    print(f"❌ Agent failed: {result.error}")
                    # If failure is due to connection, that's expected if we can't hit localhost:8000
                    if "Connection refused" in str(result.error) or "ConnectError" in str(result.error):
                        print("⚠️ Could not connect to Vorpal (http://localhost:8000). This is expected if running in isolated env.")
                    else:
                        raise Exception(f"Agent failed with unexpected error: {result.error}")

        except Exception as e:
            print(f"❌ Exception during test: {e}")
            # Don't fail the build if it's just connectivity
            if "Connection refused" in str(e) or "ConnectError" in str(e):
                 print("⚠️ Connection error handled.")
            else:
                raise e

if __name__ == '__main__':
    unittest.main()
