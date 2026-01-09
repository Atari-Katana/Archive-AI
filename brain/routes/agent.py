from fastapi import APIRouter, HTTPException, Request
from schemas.agent import (
    AgentRequest, AgentResponse, AgentStepResponse,
    RecursiveAgentRequest, CodeAssistRequest, CodeAssistResponse
)
from agents import (
    ReActAgent, ToolRegistry, get_basic_tools, get_advanced_tools
)
from agents.recursive_agent import RecursiveAgent
from agents.code_agent import code_assist
from stream_handler import stream_handler
from config import config
import httpx

router = APIRouter(prefix="/agent", tags=["agents"])

@router.post("/", response_model=AgentResponse)
async def agent_solve(request: AgentRequest):
    """
    Basic ReAct agent (6 tools)
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Capture input to Redis Stream (non-blocking)
    await stream_handler.capture_input(request.question)

    try:
        # Build tool registry (basic tools only)
        registry = ToolRegistry()
        basic_tools = get_basic_tools()

        for tool_name, (description, func) in basic_tools.items():
            registry.register(tool_name, description, func)

        # Run ReAct agent
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            async with ReActAgent(registry, http_client=client) as agent:
                # Override max steps if specified
                if request.max_steps:
                    agent.MAX_STEPS = request.max_steps

                result = await agent.solve(request.question)

        # Convert steps to response model
        steps_response = [
            AgentStepResponse(
                step_number=step.step_number,
                thought=step.thought,
                action=step.action,
                action_input=step.action_input,
                observation=step.observation
            )
            for step in result.steps
        ]

        return AgentResponse(
            answer=result.answer,
            steps=steps_response,
            total_steps=result.total_steps,
            success=result.success,
            engine=f"vorpal/{config.VORPAL_MODEL}",
            error=result.error
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vorpal engine error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@router.post("/advanced", response_model=AgentResponse)
async def agent_solve_advanced(request: AgentRequest):
    """
    Advanced ReAct agent (11 tools)
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Capture input to Redis Stream (non-blocking)
    await stream_handler.capture_input(request.question)

    try:
        # Build tool registry (basic + advanced tools)
        registry = ToolRegistry()

        # Register basic tools
        basic_tools = get_basic_tools()
        for tool_name, (description, func) in basic_tools.items():
            registry.register(tool_name, description, func)

        # Register advanced tools
        advanced_tools = get_advanced_tools()
        for tool_name, (description, func) in advanced_tools.items():
            registry.register(tool_name, description, func)

        # Run ReAct agent
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            async with ReActAgent(registry, http_client=client) as agent:
                # Override max steps if specified
                if request.max_steps:
                    agent.MAX_STEPS = request.max_steps

                result = await agent.solve(request.question)

        # Convert steps to response model
        steps_response = [
            AgentStepResponse(
                step_number=step.step_number,
                thought=step.thought,
                action=step.action,
                action_input=step.action_input,
                observation=step.observation
            )
            for step in result.steps
        ]

        return AgentResponse(
            answer=result.answer,
            steps=steps_response,
            total_steps=result.total_steps,
            success=result.success,
            engine=f"vorpal/{config.VORPAL_MODEL}",
            error=result.error
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vorpal engine error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@router.post("/recursive", response_model=AgentResponse)
async def run_recursive_agent(request: RecursiveAgentRequest):
    """
    Run the Recursive Language Model (RLM) Agent.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if not request.corpus:
        raise HTTPException(status_code=400, detail="Corpus cannot be empty")

    try:
        # Initialize RLM agent
        async with RecursiveAgent(corpus=request.corpus) as agent:
            # Execute
            result = await agent.solve(request.question)

        # Format steps
        formatted_steps = []
        for step in result.steps:
            formatted_steps.append({
                "step_number": step.step_number,
                "thought": step.thought,
                "action": step.action,
                "action_input": step.action_input,
                "observation": step.observation
            })

        return AgentResponse(
            answer=result.answer,
            steps=formatted_steps,
            total_steps=result.total_steps,
            success=result.success,
            engine=f"vorpal/{config.VORPAL_MODEL}",
            error=result.error
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Note: /code_assist was in main.py, but not under /agent prefix necessarily. 
# main.py had @app.post("/code_assist", ...). 
# If I put it here, it becomes /agent/code_assist.
# If I want to keep /code_assist, I should put it in a separate router or adjust prefix.
# However, grouping it under agents seems logical.
# Wait, main.py had: @app.post("/code_assist", ..., tags=["agents"])
# It was at root /code_assist.
# If I put it in this router with prefix /agent, it breaks API compatibility.
# I will create a separate router or just add it to this file but attach it to a router with no prefix? 
# Or I can have multiple routers in this file.

router_root = APIRouter(tags=["agents"])

@router_root.post("/code_assist", response_model=CodeAssistResponse)
async def assist_with_code(request: CodeAssistRequest):
    """
    Code assistance with automated testing and debugging.
    """
    if not request.task or not request.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    # Validate parameters
    if request.max_attempts < 1 or request.max_attempts > 5:
        raise HTTPException(
            status_code=400,
            detail="max_attempts must be between 1 and 5"
        )

    if request.timeout < 1 or request.timeout > 30:
        raise HTTPException(
            status_code=400,
            detail="timeout must be between 1 and 30 seconds"
        )

    try:
        result = await code_assist(
            task=request.task,
            max_attempts=request.max_attempts,
            timeout=request.timeout
        )

        return CodeAssistResponse(
            task=result.task,
            code=result.code,
            explanation=result.explanation,
            test_output=result.test_output,
            success=result.success,
            attempts=result.attempts,
            engine=f"vorpal/{config.VORPAL_MODEL}",
            error=result.error
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Code assistance error: {str(e)}"
        )
