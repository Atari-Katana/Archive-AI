import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Path setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'brain'))

from brain.agents.react_agent import ReActAgent, ToolRegistry, AgentResult
from brain.agents.code_agent import code_assist

class TestAgentsWithOctoTools(unittest.IsolatedAsyncioTestCase):
    @patch('brain.agents.react_agent.construct_solver')
    async def test_react_agent_octotools_flow(self, mock_construct_solver):
        # Mock Solver
        mock_solver = MagicMock()
        mock_construct_solver.return_value = mock_solver
        
        # Mock Solve Result
        mock_solver.solve.return_value = {
            "final_output": "The answer is 4.",
            "memory": [
                {"step": 1, "sub_goal": "Calculate 2+2", "tool": "CalculatorTool", "command": "2+2", "result": "4"},
                {"step": 2, "sub_goal": "Final Answer", "tool": "Final Answer", "command": "The answer is 4.", "result": ""}
            ]
        }

        # Mock Registry (unused but required)
        registry = ToolRegistry()

        # Run Agent
        async with ReActAgent(registry) as agent:
            result = await agent.solve("What is 2 + 2?")

        # Assertions
        self.assertTrue(result.success)
        self.assertEqual(result.answer, "The answer is 4.")
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.steps[0].action, "CalculatorTool")
        mock_construct_solver.assert_called_once()
        mock_solver.solve.assert_called_once_with("What is 2 + 2?")

    @patch('brain.agents.code_agent.llm')
    @patch('brain.agents.code_agent.execute_code')
    async def test_code_agent_flow(self, mock_execute, mock_llm_global):
        # Mock LLM Chat
        mock_llm_global.chat = AsyncMock(return_value={
            "content": "```python\nprint('Hello')\n```\nExplanation: Prints hello."
        })

        # Mock Sandbox execution
        mock_execute.return_value = {"status": "success", "result": "Hello"}

        # Run Code Assistant
        result = await code_assist("Print hello")

        # Assertions
        self.assertTrue(result.success)
        self.assertEqual(result.code, "print('Hello')")
        mock_llm_global.chat.assert_called_once()
        mock_execute.assert_called_once()

if __name__ == '__main__':
    unittest.main()