"""
Code Assistant Agent (Chunk 5.5)
Specialized agent for code generation, testing, and debugging.
"""

import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass

from config import config
from services.llm import llm


@dataclass
class CodeResult:
    """Result from code assistant"""
    task: str
    code: str
    explanation: str
    test_output: Optional[str]
    success: bool
    attempts: int
    error: Optional[str] = None


async def execute_code(code: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Execute code in sandbox environment.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds

    Returns:
        Dictionary with status, result, and error (if any)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout + 5.0) as client:
            response = await client.post(
                f"{config.SANDBOX_URL}/execute",
                json={"code": code, "timeout": timeout}
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "error": f"Sandbox returned HTTP {response.status_code}"
                }

    except httpx.TimeoutException:
        return {
            "status": "error",
            "error": f"Code execution timeout ({timeout}s)"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Sandbox communication error: {str(e)}"
        }


async def generate_code(task: str, previous_error: Optional[str] = None) -> Dict[str, str]:
    """
    Generate code using LLM based on task description.

    Args:
        task: Natural language description of coding task
        previous_error: Error from previous attempt (for debugging)

    Returns:
        Dictionary with 'code' and 'explanation' keys
    """
    # Build prompt based on whether this is initial generation or debugging
    if previous_error:
        system_prompt = (
            "You are a Python code debugging assistant. The user provided code that failed. "
            "Analyze the error and provide a corrected version. "
            "Return ONLY the corrected Python code, followed by a brief explanation."
        )
        user_prompt = f"Task: {task}\n\nPrevious Error:\n{previous_error}\n\nProvide corrected code:"
    else:
        system_prompt = (
            "You are a Python code generation assistant. Generate clean, working Python code "
            "based on the user's task description. Include test/demonstration code that shows "
            "the function working. Return ONLY Python code followed by a brief explanation."
        )
        user_prompt = f"Task: {task}\n\nGenerate Python code:"

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = await llm.chat(
            messages=messages,
            max_tokens=1000,
            temperature=0.2
        )
        
        full_response = result["content"]

        # Try to extract code and explanation
        # Look for code blocks (```python ... ```)
        if "```python" in full_response:
            parts = full_response.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0].strip()
                # Everything after the code block is explanation
                explanation = full_response.split("```")[-1].strip()
                if not explanation:
                    explanation = "Code generated successfully"
                return {"code": code_part, "explanation": explanation}

        # If no code blocks, try to split by common patterns
        if "\n\nExplanation:" in full_response:
            code, explanation = full_response.split("\n\nExplanation:", 1)
            return {"code": code.strip(), "explanation": explanation.strip()}

        # Fallback: treat everything as code
        return {
            "code": full_response,
            "explanation": "Code generated (no explicit explanation provided)"
        }

    except Exception as e:
        return {
            "code": "",
            "explanation": f"Code generation error: {str(e)}"
        }


async def code_assist(
    task: str,
    max_attempts: int = 3,
    timeout: int = 10
) -> CodeResult:
    """
    Complete code assistance workflow with generation, testing, and debugging.

    Args:
        task: Natural language description of coding task
        max_attempts: Maximum number of retry attempts for debugging
        timeout: Execution timeout per attempt (seconds)

    Returns:
        CodeResult with final code, explanation, and test output
    """
    attempt = 0
    last_error = None

    while attempt < max_attempts:
        attempt += 1

        # Generate code (or regenerate with error feedback)
        gen_result = await generate_code(task, previous_error=last_error)

        if not gen_result["code"]:
            return CodeResult(
                task=task,
                code="",
                explanation=gen_result["explanation"],
                test_output=None,
                success=False,
                attempts=attempt,
                error=gen_result["explanation"]
            )

        code = gen_result["code"]
        explanation = gen_result["explanation"]

        # Execute code in sandbox
        exec_result = await execute_code(code, timeout=timeout)

        if exec_result["status"] == "success":
            # Success!
            return CodeResult(
                task=task,
                code=code,
                explanation=explanation,
                test_output=exec_result.get("result"),
                success=True,
                attempts=attempt
            )
        else:
            # Execution failed - prepare for retry
            last_error = exec_result.get("error", "Unknown error")

            if attempt >= max_attempts:
                # Out of attempts
                return CodeResult(
                    task=task,
                    code=code,
                    explanation=explanation,
                    test_output=None,
                    success=False,
                    attempts=attempt,
                    error=last_error
                )

            # Loop will retry with error feedback

    # Should never reach here, but just in case
    return CodeResult(
        task=task,
        code="",
        explanation=gen_result["explanation"], # Fixed ref
        test_output=None,
        success=False,
        attempts=max_attempts,
        error="Code generation failed after maximum attempts"
    )
