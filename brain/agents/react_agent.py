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

    def _build_prompt(self, question: str, steps: List[AgentStep], tools: str) -> str:
        """
        Build the prompt for the next step.
        Can be overridden by subclasses (e.g. RecursiveAgent).
        """
        prompt = (
            f"You are a helpful AI assistant with access to the following tools:\n\n{tools}\n\n"
            "Use the following format:\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action: the action to take, should be one of the tool names\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n\n"
            f"Question: {question}\n"
        )
        
        for step in steps:
            prompt += f"\nThought: {step.thought}"
            if step.action:
                prompt += f"\nAction: {step.action}"
            if step.action_input:
                prompt += f"\nAction Input: {step.action_input}"
            if step.observation:
                prompt += f"\nObservation: {step.observation}"

        prompt += "\nThought:"
        return prompt

    async def solve_native(self, question: str) -> AgentResult:
        """
        Solve using the native ReAct loop (bypassing OctoTools).
        Used by subclasses like RecursiveAgent that need custom prompts/handling.
        """
        import sys
        if '/app' not in sys.path:
            sys.path.append('/app')
            
        try:
            from services.llm import llm
        except ImportError as e:
            return AgentResult(
                answer="",
                steps=[],
                total_steps=0,
                success=False,
                error=f"Import Error: {e}"
            )
        
        steps = []
        tools_desc = self.tool_registry.list_tools()
        
        for i in range(self.MAX_STEPS):
            # 1. Build prompt
            prompt = self._build_prompt(question, steps, tools_desc)
            
            # 2. Call LLM
            try:
                response = await llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    stop=["Observation:"]
                )
                content = response["content"]
            except Exception as e:
                return AgentResult(
                    answer="", steps=steps, total_steps=i, success=False,
                    error=f"LLM Error: {str(e)}"
                )

            # 3. Parse output
            thought = ""
            action = ""
            action_input = ""
            final_answer = ""
            
            # Extract Thought
            # The prompt ends with "Thought:", so the model output usually starts with the thought text.
            # However, sometimes it might repeat "Thought:" or start with a newline.
            
            clean_content = content.strip()
            logger.info(f"DEBUG: Raw LLM Output:\n{clean_content}\n-------------------")
            
            # Helper to extract text before a keyword
            def get_text_before(text, keyword):
                if keyword in text:
                    return text.split(keyword)[0].strip()
                return text
            
            if "Final Answer:" in clean_content:
                # If Final Answer is present, it might be the only thing or after Thought
                if "Thought:" in clean_content:
                    thought_part = clean_content.split("Thought:")[-1]
                    thought = thought_part.split("Final Answer:")[0].strip()
                else:
                    # no "Thought:" tag, assume everything before Final Answer is thought (or empty if it starts with FA)
                    thought = clean_content.split("Final Answer:")[0].strip()
                
                final_answer = clean_content.split("Final Answer:")[-1].strip()
                steps.append(AgentStep(thought=thought, step_number=i+1))
                return AgentResult(
                    answer=final_answer,
                    steps=steps,
                    total_steps=len(steps),
                    success=True
                )

            if "Action:" in clean_content:
                if "Thought:" in clean_content:
                    thought = clean_content.split("Thought:")[-1].split("Action:")[0].strip()
                else:
                    # Assume everything before Action is thought
                    thought = clean_content.split("Action:")[0].strip()
                
                if "Action Input:" in clean_content:
                    action_part = clean_content.split("Action:")[-1]
                    action = action_part.split("Action Input:")[0].strip()
                    action_input = action_part.split("Action Input:")[-1].strip()
            else:
                # No Action, maybe just thought?
                if "Thought:" in clean_content:
                    thought = clean_content.split("Thought:")[-1].strip()
                else:
                    thought = clean_content.strip()
            
            # 4. Execute Action
            if action and action_input:
                tool = self.tool_registry.get_tool(action)
                if tool:
                    try:
                        if asyncio.iscoroutinefunction(tool):
                            observation = await tool(action_input)
                        else:
                            observation = await asyncio.to_thread(tool, action_input)
                    except Exception as e:
                        observation = f"Tool Error: {str(e)}"
                else:
                    observation = f"Error: Tool '{action}' not found. Available tools: {', '.join(self.tool_registry.tools.keys())}"
                
                steps.append(AgentStep(
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=str(observation),
                    step_number=i+1
                ))
            else:
                # Model didn't produce an action - maybe just thinking or confused
                if not final_answer:
                    steps.append(AgentStep(thought=thought, step_number=i+1, observation="Error: No Action or Final Answer provided."))
            
        return AgentResult(
            answer="Max steps reached without final answer.",
            steps=steps,
            total_steps=self.MAX_STEPS,
            success=False
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