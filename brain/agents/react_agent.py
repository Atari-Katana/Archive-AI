"""
ReAct Agent Framework (Chunk 3.2) - OctoTools Integration
Replaces native ReAct implementation with OctoTools framework.
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

# Add OctoTools to path
current_dir = os.path.dirname(os.path.abspath(__file__))
octotools_root = os.path.abspath(os.path.join(current_dir, '../../octotools_repo'))
if octotools_root not in sys.path:
    sys.path.append(octotools_root)

# Set OpenAI Base URL for OctoTools to use Vorpal
from config import config
os.environ["OPENAI_BASE_URL"] = f"{config.VORPAL_URL}/v1"
# Ensure API Key is set (even if dummy)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "dummy-key"

try:
    from octotools.solver import construct_solver
except ImportError:
    # Fallback/Mock for when octotools is not installed properly in dev environment
    construct_solver = None

from stream_handler import stream_handler

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Agent execution states"""
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    FINISHED = "finished"
    ERROR = "error"

@dataclass
class AgentStep:
    """Single step in the agent's reasoning process"""
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None
    step_number: int = 0

@dataclass
class AgentResult:
    """Final result from agent execution"""
    answer: str
    steps: List[AgentStep]
    total_steps: int
    success: bool
    error: Optional[str] = None

class ToolRegistry:
    """
    Registry of tools available to the agent.
    Maintained for compatibility, but OctoTools uses its own discovery.
    """
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_descriptions: Dict[str, str] = {}

    def register(self, name: str, description: str, func: Callable):
        self.tools[name] = func
        self.tool_descriptions[name] = description

    def get_tool(self, name: str) -> Optional[Callable]:
        return self.tools.get(name)

    def list_tools(self) -> str:
        if not self.tools:
            return "No tools available."
        tool_list = []
        for name, desc in self.tool_descriptions.items():
            tool_list.append(f"- {name}: {desc}")
        return "\n".join(tool_list)

class ReActAgent:
    """
    ReAct agent wrapper around OctoTools.
    """
    MAX_STEPS = 10

    def __init__(
        self,
        tool_registry: ToolRegistry, 
        llm_client: Optional[Any] = None 
    ):
        self.tool_registry = tool_registry
        
        if construct_solver is None:
            logger.error("OctoTools not found or failed to import.")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def _save_procedural_memory(self, question: str, result: AgentResult):
        if not result.success:
            return
        try:
            summary = (
                f"Procedural Memory: To solve the task '{question}', "
                f"I performed {result.total_steps} steps using OctoTools. "
                f"The final outcome was: {result.answer}"
            )
            await stream_handler.capture_input(summary)
        except Exception as e:
            logger.warning(f"Failed to save procedural memory: {e}")

    async def solve(self, question: str) -> AgentResult:
        """
        Solve a question using OctoTools.
        """
        if construct_solver is None:
            return AgentResult(
                answer="",
                steps=[],
                total_steps=0,
                success=False,
                error="OctoTools framework not available."
            )

        try:
            # Run OctoTools in a thread since it is synchronous
            def run_octotools():
                solver = construct_solver(
                    llm_engine_name="gpt-4o", # Triggers OpenAI engine (redirected to Vorpal)
                    enabled_tools=["archive_ai"],
                    max_steps=self.MAX_STEPS,
                    verbose=True
                )
                return solver.solve(question)

            json_data = await asyncio.to_thread(run_octotools)
            
            final_answer = json_data.get("final_output") or json_data.get("direct_output") or json_data.get("base_response") or "No answer generated."
            memory = json_data.get("memory", [])
            
            steps = []
            for i, action in enumerate(memory):
                # OctoTools Memory Action structure check needed.
                # Assuming it has dict-like access or object attributes
                # In solver.py: self.memory.add_action(...)
                # In memory.py (which I haven't seen but inferred):
                
                # Check if action is dict or object
                if isinstance(action, dict):
                    thought = action.get('sub_goal') or action.get('thought', '')
                    tool = action.get('tool', '')
                    command = action.get('command', '')
                    result = str(action.get('result', ''))
                else:
                    # Try attribute access
                    thought = getattr(action, 'sub_goal', '')
                    tool = getattr(action, 'tool', '')
                    command = getattr(action, 'command', '')
                    result = str(getattr(action, 'result', ''))

                step = AgentStep(
                    step_number=i+1,
                    thought=thought,
                    action=tool,
                    action_input=command,
                    observation=result
                )
                steps.append(step)
            
            result = AgentResult(
                answer=final_answer,
                steps=steps,
                total_steps=len(steps),
                success=True
            )
            
            await self._save_procedural_memory(question, result)
            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return AgentResult(
                answer="",
                steps=[],
                total_steps=0,
                success=False,
                error=f"OctoTools Error: {str(e)}"
            )

# Convenience function for one-off agent tasks
async def solve_with_react(
    question: str,
    tools: Dict[str, tuple[str, Callable]]
) -> AgentResult:
    """
    Convenience function to solve a question with ReAct.

    Args:
        question: Question to solve
        tools: Dict of {name: (description, function)}

    Returns:
        AgentResult
    """
    # Build dummy registry
    registry = ToolRegistry()
    for name, (desc, func) in tools.items():
        registry.register(name, desc, func)

    async with ReActAgent(registry) as agent:
        return await agent.solve(question)