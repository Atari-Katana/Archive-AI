"""
Recursive Language Model (RLM) Agent
Based on MIT CSAIL paper: https://arxiv.org/pdf/2512.24601

This agent handles infinite-context tasks by treating the context as an external
variable ('CORPUS') in a Python REPL environment. The agent writes Python code
to inspect, filter, and recursively summarize the corpus.
"""

from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass

from .react_agent import ReActAgent, ToolRegistry, AgentResult
from config import config

logger = logging.getLogger(__name__)

RLM_SYSTEM_PROMPT = """You are a Recursive Language Model (RLM).
You have been tasked with processing a large text document that is TOO LARGE to fit in your context window.

You cannot see the document directly.
Instead, it is available in your Python environment as a string variable named `CORPUS`.

Your goal is to answer the user's question by writing Python code to inspect `CORPUS`.

### Capabilities
1. **Inspect Data:** You can `print(len(CORPUS))` or `print(CORPUS[:500])` to see the data.
2. **Filter/Search:** You can use regex (`re` module) or string methods to find relevant sections.
3. **Recursive Calls:** You have a special function `ask_llm(prompt)` available.
   - You can pass chunks of `CORPUS` to `ask_llm` to summarize them or extract specific facts.
   - Example: `summary = ask_llm(f"Summarize this text: {chunk}")`

### Rules
- **Do NOT try to print the entire CORPUS.** It will crash the interface.
- **Do NOT guess.** Use the data in `CORPUS`.
- **Iterate:** If a search fails, write new code to try a different strategy.
- **Final Answer:** When you have the answer, output it clearly.

### Example Workflow
Question: "What is the main conclusion of the paper?"
Thought: I check the length of the corpus.
Action: CodeExecution
Action Input: print(len(CORPUS))
Observation: 50000
Thought: It's 50,000 chars. I'll read the last 2000 chars to find the conclusion.
Action: CodeExecution
Action Input: print(CORPUS[-2000:])
Observation: ... In conclusion, the results show...
Thought: I see the conclusion section. I will ask the LLM to summarize it.
Action: CodeExecution
Action Input: print(ask_llm(f"Summarize this conclusion: {CORPUS[-2000:]}"))
Observation: The main conclusion is that...
Final Answer: The conclusion is...
"""

class RecursiveAgent(ReActAgent):
    """
    Specialized agent for RLM tasks.
    Wraps ReActAgent but injects the corpus into the sandbox context.
    """

    def __init__(self, corpus: str, **kwargs):
        # Create a tool registry with only CodeExecution
        # (RLM relies almost entirely on Python)
        from .advanced_tools import code_execution
        
        # We wrap code_execution to inject the corpus context
        async def context_aware_execution(code: str) -> str:
            # Import here to avoid circular imports if any
            import httpx
            from agents.code_validator import validate_code
            
            # Use the existing validation logic from advanced_tools
            # But we call the Sandbox API with the 'context' field
            
            # 1. Validation (re-use logic from advanced_tools/validator)
            # ... (Simplified for brevity, reusing the raw endpoint call)
            
            try:
                async with httpx.AsyncClient(timeout=config.AGENT_TIMEOUT) as client:
                    response = await client.post(
                        f"{config.SANDBOX_URL}/execute",
                        json={
                            "code": code,
                            "context": {"CORPUS": corpus}
                        }
                    )
                    response.raise_for_status()
                    result = response.json()

                    # Sandbox returns: {"status": "success/error", "result": "...", "error": "..."}
                    status = result.get("status", "error")
                    result_output = result.get("result", "").strip()
                    error_output = result.get("error", "").strip()

                    output = ""
                    if result_output:
                        output += f"Output:\n{result_output}"
                    if error_output:
                        output += f"\nErrors:\n{error_output}"

                    return output if output else "Code executed (no output)."

            except httpx.TimeoutException:
                return "Sandbox Error: Request timed out after 60 seconds. Try processing smaller chunks or simplifying the code."
            except httpx.HTTPStatusError as e:
                return f"Sandbox Error: HTTP {e.response.status_code} - {e.response.text}"
            except httpx.ConnectError:
                return f"Sandbox Error: Cannot connect to sandbox at {config.SANDBOX_URL}. Is the service running?"
            except Exception as e:
                logger.exception("Unexpected error in sandbox execution")
                return f"Sandbox Error: Unexpected error - {type(e).__name__}: {str(e)}"

        registry = ToolRegistry()
        registry.register(
            "CodeExecution", 
            "Execute Python code. Variable 'CORPUS' contains the text. Function 'ask_llm(prompt)' is available.",
            context_aware_execution
        )
        
        super().__init__(tool_registry=registry, **kwargs)
        self.system_prompt = RLM_SYSTEM_PROMPT

    def _build_prompt(self, question: str, steps: list, tools: str) -> str:
        """Override prompt builder to use RLM system prompt"""
        prompt = self.system_prompt + f"\n\nQuestion: {question}\n"
        
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

    async def solve(self, question: str) -> AgentResult:
        """Override solve to use native ReAct loop instead of OctoTools"""
        return await self.solve_native(question)
