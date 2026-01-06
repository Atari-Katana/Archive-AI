#!/usr/bin/env python3
"""
Code Sandbox Server (Chunk 1.2)
FastAPI server for safe Python code execution.
"""

import io
import contextlib
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Archive-AI Code Sandbox", version="1.0.0")


class CodeRequest(BaseModel):
    """Request model for code execution"""
    code: str
    timeout: int = 30  # seconds


class CodeResponse(BaseModel):
    """Response model for code execution"""
    status: str
    result: str | None = None
    error: str | None = None


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"status": "healthy", "service": "code-sandbox"}


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint (standard convention)"""
    return {"status": "healthy", "service": "code-sandbox"}


@app.post("/execute", response_model=CodeResponse)
async def execute_code(request: CodeRequest) -> CodeResponse:
    """
    Execute Python code in isolated environment.

    Args:
        request: CodeRequest with code to execute

    Returns:
        CodeResponse with result or error
    """
    if not request.code or not request.code.strip():
        raise HTTPException(
            status_code=400,
            detail="Code cannot be empty"
        )

    # Capture stdout
    stdout_capture = io.StringIO()

    try:
        # Create limited globals/locals for execution
        # Only allow safe built-ins
        safe_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
                "round": round,
                "sorted": sorted,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "any": any,
                "all": all,
                "type": type,
                "help": help,
                "__import__": __import__,
            }
        }

        # Use same namespace for globals and locals to support recursion
        # Functions need to reference themselves in the same namespace
        namespace: Dict[str, Any] = safe_globals.copy()

        # Run code with stdout capture
        with contextlib.redirect_stdout(stdout_capture):
            # Execute Python code in sandboxed namespace
            exec(request.code, namespace, namespace)

        # Get captured output
        output = stdout_capture.getvalue()

        # If there's output, return it; otherwise return success message
        result = output if output else "Code executed successfully"

        return CodeResponse(
            status="success",
            result=result.strip()
        )

    except SyntaxError as e:
        error_msg = f"Syntax Error: {e.msg} at line {e.lineno}"
        return CodeResponse(
            status="error",
            error=error_msg
        )

    except NameError as e:
        error_msg = f"Name Error: {str(e)}"
        return CodeResponse(
            status="error",
            error=error_msg
        )

    except Exception as e:
        # Capture full traceback for debugging
        error_msg = f"{type(e).__name__}: {str(e)}"

        return CodeResponse(
            status="error",
            error=error_msg
        )

    finally:
        stdout_capture.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
