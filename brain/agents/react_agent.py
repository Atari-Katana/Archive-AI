"""
ReAct Agent Framework (Chunk 3.2)
Implements Reasoning + Acting pattern for multi-step problem solving.

ReAct Loop:
1. Thought: Reason about what to do next
2. Action: Select and execute a tool
3. Observation: See the result
4. Repeat until task complete
5. Final Answer: Return the solution

Based on: "ReAct: Synergizing Reasoning and Acting in Language Models"
https://arxiv.org/abs/2210.03629
"""

import httpx
import re
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from config import config


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
    Tools are functions the agent can call to perform actions.
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_descriptions: Dict[str, str] = {}

    def register(self, name: str, description: str, func: Callable):
        """
        Register a new tool.

        Args:
            name: Tool name (used in Action)
            description: What the tool does
            func: Callable that executes the tool
        """
        self.tools[name] = func
        self.tool_descriptions[name] = description

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> str:
        """Get formatted list of available tools"""
        if not self.tools:
            return "No tools available."

        tool_list = []
        for name, desc in self.tool_descriptions.items():
            tool_list.append(f"- {name}: {desc}")

        return "\n".join(tool_list)


class ReActAgent:
    """
    ReAct agent that can reason and act to solve complex problems.

    The agent follows the ReAct pattern:
    - Thought: Reasoning about the next step
    - Action: Tool to use
    - Action Input: Input for the tool
    - Observation: Result from the tool

    This continues until the agent reaches a final answer.
    """

    # Maximum steps to prevent infinite loops
    MAX_STEPS = 10

    def __init__(
        self,
        tool_registry: ToolRegistry,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        """
        Initialize ReAct agent.

        Args:
            tool_registry: Registry of available tools
            http_client: Optional httpx client for LLM calls
        """
        self.tool_registry = tool_registry
        self.http_client = http_client
        self.own_client = http_client is None

    async def __aenter__(self):
        """Async context manager entry"""
        if self.own_client:
            self.http_client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.own_client and self.http_client:
            await self.http_client.aclose()

    def _build_prompt(
        self,
        question: str,
        steps: List[AgentStep],
        tools: str
    ) -> str:
        """
        Build the ReAct prompt for the LLM.

        Args:
            question: Original user question
            steps: Previous agent steps
            tools: Available tools description

        Returns:
            Formatted prompt for the LLM
        """
        prompt = f"""You are a helpful AI assistant that can reason and use tools to answer questions.

Available Tools:
{tools}

Use the following format:

Thought: [your reasoning about what to do next]
Action: [tool name from available tools, or "Final Answer"]
Action Input: [input for the tool, or your final answer if Action is "Final Answer"]
Observation: [result from the tool - this will be provided by the system]

Question: {question}
"""

        # Add previous steps to the prompt
        for step in steps:
            prompt += f"\nThought: {step.thought}"
            if step.action:
                prompt += f"\nAction: {step.action}"
            if step.action_input:
                prompt += f"\nAction Input: {step.action_input}"
            if step.observation:
                prompt += f"\nObservation: {step.observation}"

        # Prompt for next thought
        prompt += "\nThought:"

        return prompt

    async def _generate_step(self, prompt: str) -> str:
        """
        Generate the next reasoning step using Vorpal.

        Args:
            prompt: The ReAct prompt

        Returns:
            LLM response with Thought/Action/Action Input
        """
        payload = {
            "model": "Qwen/Qwen2.5-3B-Instruct",
            "prompt": prompt,
            "max_tokens": 256,
            "temperature": 0.7,
            "stop": ["Observation:"]  # Stop before observation
        }

        response = await self.http_client.post(
            f"{config.VORPAL_URL}/v1/completions",
            json=payload
        )
        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["text"].strip()

    def _parse_step(self, response: str) -> Dict[str, str]:
        """
        Parse the LLM response into thought, action, and action input.

        Args:
            response: Raw LLM response

        Returns:
            Dict with 'thought', 'action', 'action_input'
        """
        parsed = {
            "thought": "",
            "action": "",
            "action_input": ""
        }

        # Extract thought
        thought_match = re.search(
            r"^(.+?)(?=Action:|$)",
            response,
            re.DOTALL | re.MULTILINE
        )
        if thought_match:
            parsed["thought"] = thought_match.group(1).strip()

        # Extract action
        action_match = re.search(r"Action:\s*(.+?)(?=\n|Action Input:|$)", response)
        if action_match:
            parsed["action"] = action_match.group(1).strip()

        # Extract action input
        action_input_match = re.search(
            r"Action Input:\s*(.+?)(?=\n\n|$)",
            response,
            re.DOTALL
        )
        if action_input_match:
            parsed["action_input"] = action_input_match.group(1).strip()

        return parsed

    async def _execute_action(
        self,
        action: str,
        action_input: str
    ) -> str:
        """
        Execute an action using the appropriate tool.

        Args:
            action: Tool name
            action_input: Input for the tool

        Returns:
            Observation from the tool
        """
        if action == "Final Answer":
            return action_input

        tool = self.tool_registry.get_tool(action)
        if not tool:
            return f"Error: Tool '{action}' not found. Available tools: {', '.join(self.tool_registry.tools.keys())}"

        try:
            # Execute the tool
            result = await tool(action_input)
            return str(result)
        except Exception as e:
            return f"Error executing {action}: {str(e)}"

    async def solve(self, question: str) -> AgentResult:
        """
        Solve a question using the ReAct pattern.

        Args:
            question: The question to solve

        Returns:
            AgentResult with answer and reasoning trace
        """
        steps: List[AgentStep] = []
        tools_description = self.tool_registry.list_tools()

        for step_num in range(self.MAX_STEPS):
            try:
                # Build prompt with history
                prompt = self._build_prompt(question, steps, tools_description)

                # Generate next step
                response = await self._generate_step(prompt)

                # Parse response
                parsed = self._parse_step(response)

                # Create step object
                current_step = AgentStep(
                    thought=parsed["thought"],
                    action=parsed["action"],
                    action_input=parsed["action_input"],
                    step_number=step_num + 1
                )

                # Check if we're done
                if parsed["action"] == "Final Answer":
                    current_step.observation = "Task complete"
                    steps.append(current_step)

                    return AgentResult(
                        answer=parsed["action_input"],
                        steps=steps,
                        total_steps=len(steps),
                        success=True
                    )

                # Execute action
                if parsed["action"]:
                    observation = await self._execute_action(
                        parsed["action"],
                        parsed["action_input"]
                    )
                    current_step.observation = observation

                steps.append(current_step)

            except Exception as e:
                return AgentResult(
                    answer="",
                    steps=steps,
                    total_steps=len(steps),
                    success=False,
                    error=f"Error at step {step_num + 1}: {str(e)}"
                )

        # Max steps reached
        return AgentResult(
            answer="Unable to complete task within step limit",
            steps=steps,
            total_steps=len(steps),
            success=False,
            error=f"Maximum steps ({self.MAX_STEPS}) reached"
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
    # Build tool registry
    registry = ToolRegistry()
    for name, (desc, func) in tools.items():
        registry.register(name, desc, func)

    # Run agent
    async with ReActAgent(registry) as agent:
        return await agent.solve(question)
