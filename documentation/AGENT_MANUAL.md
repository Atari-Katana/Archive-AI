# Archive-AI Agent Manual

**Version:** 7.5
**Last Updated:** 2025-12-30
**For:** Developers Building Custom Agents

---

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding the ReAct Pattern](#understanding-the-react-pattern)
3. [Architecture Overview](#architecture-overview)
4. [Building Custom Tools](#building-custom-tools)
5. [Tool Registry System](#tool-registry-system)
6. [Specialized Agents](#specialized-agents)
7. [Agent Prompting Best Practices](#agent-prompting-best-practices)
8. [Debugging Agent Reasoning](#debugging-agent-reasoning)
9. [Tool Composition Strategies](#tool-composition-strategies)
10. [Integration with Brain API](#integration-with-brain-api)
11. [Performance Optimization](#performance-optimization)
12. [Advanced Patterns](#advanced-patterns)

---

## Introduction

Archive-AI's agent system is built on the **ReAct (Reasoning + Acting)** pattern, which enables autonomous problem-solving through iterative reasoning and tool use. This manual will guide you through building custom agents, creating tools, and integrating them into the Archive-AI ecosystem.

### What You'll Learn

- How the ReAct loop works internally
- Creating custom tools from scratch
- Building specialized agents for specific domains
- Debugging and optimizing agent performance
- Best practices for prompt engineering
- Integration patterns with the Brain API

### Prerequisites

- Python 3.11+ knowledge
- Understanding of async/await patterns
- Basic familiarity with LLMs
- Access to a running Archive-AI instance

---

## Understanding the ReAct Pattern

### The ReAct Loop

The ReAct pattern combines reasoning (thinking about what to do) with acting (using tools to accomplish tasks). Each iteration follows this cycle:

```
1. Thought:      "I need to calculate the factorial of 7"
2. Action:       CodeExecution
3. Action Input: "result = 7*6*5*4*3*2*1\nprint(result)"
4. Observation:  "Output: 5040"
5. Thought:      "I have the answer"
6. Action:       Final Answer
7. Action Input: "The factorial of 7 is 5040"
```

### Implementation in Archive-AI

**Location:** `/home/user/Archive-AI/brain/agents/react_agent.py`

The core ReAct agent consists of:

1. **Agent State** - Tracks execution phase (thinking, acting, observing, finished, error)
2. **Agent Step** - Represents one iteration (thought, action, observation)
3. **Tool Registry** - Available tools the agent can call
4. **Agent Result** - Final output with full reasoning trace

### Step-by-Step Execution

```python
async def solve(self, question: str) -> AgentResult:
    """Main ReAct loop"""
    steps = []

    for step_num in range(self.MAX_STEPS):
        # 1. Build prompt with history
        prompt = self._build_prompt(question, steps, tools_description)

        # 2. Generate next reasoning step (LLM call)
        response = await self._generate_step(prompt)

        # 3. Parse response into thought/action/action_input
        parsed = self._parse_step(response)

        # 4. Execute action using appropriate tool
        if parsed["action"] == "Final Answer":
            return AgentResult(answer=parsed["action_input"], ...)

        observation = await self._execute_action(
            parsed["action"],
            parsed["action_input"]
        )

        # 5. Store step and continue
        steps.append(AgentStep(
            thought=parsed["thought"],
            action=parsed["action"],
            observation=observation
        ))
```

### Why ReAct Works

- **Transparency**: Every reasoning step is visible
- **Debuggability**: Can trace exactly where agent went wrong
- **Flexibility**: New tools = new capabilities
- **Self-correction**: Agent can see tool outputs and adjust strategy

---

## Architecture Overview

### Component Hierarchy

```
Archive-AI Agent System
│
├── Brain API (FastAPI)
│   ├── /chat/agent/basic      → Basic Agent (6 tools)
│   ├── /chat/agent/advanced   → Advanced Agent (11 tools)
│   ├── /research              → Research Agent
│   └── /code/assist           → Code Agent
│
├── ReAct Agent Framework
│   ├── react_agent.py         → Core ReAct loop
│   ├── ToolRegistry          → Tool management
│   └── AgentResult           → Output structure
│
├── Tools
│   ├── basic_tools.py        → Calculator, String ops
│   ├── advanced_tools.py     → Memory, Code exec, JSON
│   └── library_search.py     → Document search
│
└── Specialized Agents
    ├── research_agent.py     → Multi-source research
    └── code_agent.py         → Code generation + testing
```

### Data Flow

```
User Request
    ↓
Brain API Endpoint
    ↓
Agent Initialization (select tools)
    ↓
ReAct Loop (max 10 iterations)
    ↓
    ├─→ LLM (Vorpal) generates thought/action
    ├─→ Tool execution (via registry)
    ├─→ Observation stored
    └─→ Loop continues until "Final Answer"
    ↓
AgentResult (answer + reasoning trace)
    ↓
Return to user
```

---

## Building Custom Tools

### Tool Requirements

Every tool must:
1. Be an async function
2. Accept a string input parameter
3. Return a string result
4. Handle errors gracefully
5. Be registered in a ToolRegistry

### Basic Tool Template

```python
async def my_custom_tool(input_text: str) -> str:
    """
    One-line description of what the tool does.

    Args:
        input_text: Description of expected input

    Returns:
        Description of output format
    """
    try:
        # 1. Validate input
        if not input_text or not input_text.strip():
            return "Error: Input cannot be empty"

        # 2. Process input
        result = process_data(input_text)

        # 3. Return formatted result
        return f"Result: {result}"

    except Exception as e:
        return f"Error: {str(e)}"
```

### Example: Weather Tool (Mock)

```python
import json
from datetime import datetime

async def weather_lookup(location: str) -> str:
    """
    Get current weather for a location (mock data).

    Args:
        location: City name or "lat,lon" coordinates

    Returns:
        Weather summary with temperature and conditions
    """
    try:
        # Clean input
        location = location.strip().lower()

        if not location:
            return "Error: Please provide a location"

        # Mock weather data (in real tool, call API)
        mock_weather = {
            "temperature": 72,
            "conditions": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 8
        }

        return (
            f"Weather in {location.title()}:\n"
            f"  Temperature: {mock_weather['temperature']}°F\n"
            f"  Conditions: {mock_weather['conditions']}\n"
            f"  Humidity: {mock_weather['humidity']}%\n"
            f"  Wind: {mock_weather['wind_speed']} mph"
        )

    except Exception as e:
        return f"Error looking up weather: {str(e)}"
```

### Example: Database Query Tool

```python
import redis.asyncio as redis
import json

async def database_query(query: str) -> str:
    """
    Query the Redis database for keys or values.

    Args:
        query: Command like "GET key" or "SCAN pattern"

    Returns:
        Query results formatted as string
    """
    try:
        # Parse query
        parts = query.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "Error: Query format is 'COMMAND key/pattern'"

        command = parts[0].upper()
        argument = parts[1]

        # Connect to Redis
        r = await redis.from_url("redis://redis:6379")

        try:
            if command == "GET":
                value = await r.get(argument)
                if value:
                    return f"Value for '{argument}': {value.decode()}"
                else:
                    return f"Key '{argument}' not found"

            elif command == "KEYS":
                keys = await r.keys(argument)
                if keys:
                    key_list = [k.decode() for k in keys[:20]]
                    return f"Found {len(keys)} keys:\n" + "\n".join(key_list)
                else:
                    return f"No keys matching '{argument}'"

            else:
                return f"Error: Unsupported command '{command}'"

        finally:
            await r.close()

    except Exception as e:
        return f"Database error: {str(e)}"
```

### Example: File System Tool

```python
import os
from pathlib import Path

async def file_operations(operation: str) -> str:
    """
    Perform safe file operations in allowed directories.

    Args:
        operation: Format is "ACTION:path" like "LIST:/data" or "READ:/data/file.txt"

    Returns:
        Operation result or error message

    Security: Only operates within /data directory
    """
    try:
        # Parse operation
        if ":" not in operation:
            return "Error: Format is 'ACTION:path' (e.g., 'LIST:/data')"

        action, path = operation.split(":", 1)
        action = action.strip().upper()
        path = path.strip()

        # Security: restrict to /data directory
        safe_base = Path("/data")
        target = (safe_base / path).resolve()

        if not str(target).startswith(str(safe_base)):
            return "Error: Access denied - path outside allowed directory"

        # Execute action
        if action == "LIST":
            if not target.exists():
                return f"Error: Directory {path} does not exist"

            if not target.is_dir():
                return f"Error: {path} is not a directory"

            files = sorted(target.iterdir(), key=lambda x: x.name)
            file_list = []
            for f in files[:50]:  # Limit to 50 files
                size = f.stat().st_size if f.is_file() else "-"
                file_type = "DIR" if f.is_dir() else "FILE"
                file_list.append(f"  [{file_type}] {f.name} ({size} bytes)")

            return f"Contents of {path}:\n" + "\n".join(file_list)

        elif action == "READ":
            if not target.exists():
                return f"Error: File {path} does not exist"

            if not target.is_file():
                return f"Error: {path} is not a file"

            # Read file (limit size)
            file_size = target.stat().st_size
            if file_size > 100_000:  # 100KB limit
                return f"Error: File too large ({file_size} bytes). Max 100KB"

            content = target.read_text()
            return f"Contents of {path}:\n\n{content}"

        elif action == "INFO":
            if not target.exists():
                return f"Error: Path {path} does not exist"

            stat = target.stat()
            is_dir = target.is_dir()

            return (
                f"Info for {path}:\n"
                f"  Type: {'Directory' if is_dir else 'File'}\n"
                f"  Size: {stat.st_size} bytes\n"
                f"  Modified: {datetime.fromtimestamp(stat.st_mtime)}\n"
            )

        else:
            return f"Error: Unknown action '{action}'. Supported: LIST, READ, INFO"

    except Exception as e:
        return f"File operation error: {str(e)}"
```

### Tool Design Best Practices

**Input Validation:**
```python
# Always validate and clean inputs
input_text = input_text.strip()

# Check for empty input
if not input_text:
    return "Error: Input cannot be empty"

# Limit input length to prevent abuse
if len(input_text) > MAX_LENGTH:
    return f"Error: Input too long (max {MAX_LENGTH} chars)"

# Remove LLM-added quotes (common issue)
if input_text.startswith('"') and input_text.endswith('"'):
    input_text = input_text[1:-1]
```

**Error Handling:**
```python
try:
    # Main tool logic
    result = perform_operation(input_text)
    return f"Success: {result}"

except SpecificError as e:
    # Handle specific errors with helpful messages
    return f"Error: {str(e)}\nTry using format: 'example input'"

except Exception as e:
    # Catch-all for unexpected errors
    return f"Unexpected error: {str(e)}"
```

**Output Formatting:**
```python
# Good: Clear, structured output
return (
    f"Found 3 results:\n"
    f"1. Item A (score: 0.95)\n"
    f"2. Item B (score: 0.87)\n"
    f"3. Item C (score: 0.72)"
)

# Bad: Ambiguous output
return "results: A, B, C"
```

**Performance Considerations:**
```python
# Set timeouts for external calls
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.get(url)

# Limit result sizes
results = results[:MAX_RESULTS]  # Don't return thousands of items

# Cache expensive operations when possible
@lru_cache(maxsize=100)
def expensive_computation(input_data):
    # ...
```

---

## Tool Registry System

### Creating a Tool Registry

The `ToolRegistry` manages all available tools:

```python
from brain.agents.react_agent import ToolRegistry

# Create registry
registry = ToolRegistry()

# Register tools
registry.register(
    name="WeatherLookup",
    description=(
        "Get current weather for any city. "
        "Input format: city name (e.g., 'Seattle', 'New York'). "
        "Returns temperature, conditions, humidity, wind speed."
    ),
    func=weather_lookup
)

registry.register(
    name="DatabaseQuery",
    description=(
        "Query the Redis database. "
        "Input format: 'COMMAND argument' (e.g., 'GET mykey', 'KEYS pattern*'). "
        "Supported commands: GET, KEYS. "
        "Returns query results or error message."
    ),
    func=database_query
)
```

### Tool Description Guidelines

Good tool descriptions are critical for agent success:

```python
# GOOD: Specific, with examples
description = (
    "Calculate factorial of a number using code execution. "
    "Input format: just the number (e.g., '7' for factorial of 7). "
    "Returns: The calculated factorial. "
    "Example: input '5' returns '120'"
)

# BAD: Vague, no examples
description = "Does math calculations"
```

**Description Template:**
```
1. What the tool does (one sentence)
2. Input format (be specific)
3. What it returns
4. Example usage (optional but helpful)
5. Special notes/warnings (optional)
```

### Organizing Tools into Sets

```python
# basic_tools.py
BASIC_TOOLS = {
    "Calculator": (description, calculator_func),
    "StringLength": (description, string_length_func),
    # ...
}

def get_basic_tools():
    return BASIC_TOOLS

# advanced_tools.py
ADVANCED_TOOLS = {
    "MemorySearch": (description, memory_search_func),
    "CodeExecution": (description, code_execution_func),
    # ...
}

def get_advanced_tools():
    return ADVANCED_TOOLS

# Combine tool sets
def get_all_tools():
    tools = {}
    tools.update(get_basic_tools())
    tools.update(get_advanced_tools())
    return tools
```

### Dynamic Tool Loading

```python
def build_agent_registry(tool_set: str = "basic") -> ToolRegistry:
    """Build a tool registry based on desired tool set"""
    registry = ToolRegistry()

    if tool_set == "basic":
        from brain.agents.basic_tools import get_basic_tools
        tools = get_basic_tools()
    elif tool_set == "advanced":
        from brain.agents.basic_tools import get_basic_tools
        from brain.agents.advanced_tools import get_advanced_tools
        tools = {**get_basic_tools(), **get_advanced_tools()}
    elif tool_set == "custom":
        # Load custom tools
        tools = load_custom_tools()
    else:
        raise ValueError(f"Unknown tool set: {tool_set}")

    # Register all tools
    for name, (description, func) in tools.items():
        registry.register(name, description, func)

    return registry
```

---

## Specialized Agents

### Research Agent

**Purpose:** Multi-source research combining library documents and conversation memories.

**Location:** `/home/user/Archive-AI/brain/agents/research_agent.py`

**Key Features:**
- Searches library documents (PDFs, text files)
- Searches conversation memories
- Synthesizes findings from multiple sources
- Provides cited answers

**Usage Example:**

```python
from brain.agents.research_agent import research_query

# Single query
result = await research_query(
    question="What is the surprise score algorithm?",
    use_library=True,
    use_memory=True,
    top_k=5
)

print(f"Answer: {result.answer}")
print(f"Sources: {result.total_sources}")
print(f"Library chunks: {result.library_chunks_consulted}")
print(f"Memories: {result.memories_consulted}")
```

**Multi-Query Research:**

```python
from brain.agents.research_agent import multi_query_research

# Research multiple related questions
questions = [
    "What is the Titans architecture?",
    "How does surprise score work?",
    "What is the memory retention algorithm?"
]

result = await multi_query_research(
    questions=questions,
    synthesize=True
)

# Get synthesis of all findings
print(result["synthesis"])
```

**Creating a Custom Research Agent:**

```python
async def domain_specific_research(topic: str) -> dict:
    """
    Research agent specialized for a specific domain.

    Example: Legal research that combines case law library
    with previous research notes.
    """
    # Step 1: Search library with domain-specific filters
    library_results = await library_search_tool(
        query=topic,
        filter_file_type="pdf"  # Only search PDFs
    )

    # Step 2: Search memories for related discussions
    memory_results = await memory_search(topic)

    # Step 3: Extract key entities
    entities = await extract_entities(topic)

    # Step 4: Secondary searches for each entity
    entity_results = []
    for entity in entities:
        result = await library_search_tool(entity)
        entity_results.append(result)

    # Step 5: Synthesize all findings
    synthesis = await synthesize_research(
        primary_results=library_results,
        memory_context=memory_results,
        entity_expansions=entity_results
    )

    return {
        "topic": topic,
        "synthesis": synthesis,
        "sources": {
            "library": library_results,
            "memories": memory_results,
            "entities": entity_results
        }
    }
```

### Code Agent

**Purpose:** Autonomous code generation, testing, and debugging.

**Location:** `/home/user/Archive-AI/brain/agents/code_agent.py`

**Key Features:**
- Generates Python code from natural language
- Automatically tests code in sandbox
- Debugs and fixes errors (up to 3 attempts)
- Returns working code with explanation

**Usage Example:**

```python
from brain.agents.code_agent import code_assist

# Generate and test code
result = await code_assist(
    task="Create a function that checks if a string is a palindrome",
    max_attempts=3,
    timeout=10
)

if result.success:
    print(f"Code:\n{result.code}")
    print(f"\nTest Output:\n{result.test_output}")
    print(f"\nExplanation:\n{result.explanation}")
    print(f"Completed in {result.attempts} attempt(s)")
else:
    print(f"Failed after {result.attempts} attempts")
    print(f"Error: {result.error}")
```

**The Code Generation Loop:**

```python
# Simplified version of code_assist workflow
async def code_workflow(task: str):
    attempt = 0
    last_error = None

    while attempt < MAX_ATTEMPTS:
        attempt += 1

        # Generate code (with error feedback if retry)
        gen_result = await generate_code(task, previous_error=last_error)
        code = gen_result["code"]

        # Test code in sandbox
        exec_result = await execute_code(code, timeout=10)

        if exec_result["status"] == "success":
            # Success!
            return {
                "code": code,
                "output": exec_result["result"],
                "attempts": attempt
            }
        else:
            # Failed - prepare error feedback for next attempt
            last_error = exec_result["error"]

    # Max attempts reached
    return {"error": "Failed after maximum attempts"}
```

**Creating a Custom Code Agent:**

```python
async def test_driven_code_agent(
    requirements: str,
    test_cases: list
) -> dict:
    """
    Code agent that uses test-driven development.

    Args:
        requirements: Natural language requirements
        test_cases: List of (input, expected_output) tuples
    """
    # Step 1: Generate initial code
    code = await generate_code(requirements)

    # Step 2: Run all test cases
    passed_tests = []
    failed_tests = []

    for test_input, expected_output in test_cases:
        # Wrap code with test harness
        test_code = f"""
{code}

# Test case
test_input = {repr(test_input)}
result = main_function(test_input)
print(f"Result: {{result}}")
        """

        # Execute
        exec_result = await execute_code(test_code)

        if exec_result["status"] == "success":
            actual_output = extract_result(exec_result["result"])
            if actual_output == expected_output:
                passed_tests.append(test_input)
            else:
                failed_tests.append({
                    "input": test_input,
                    "expected": expected_output,
                    "actual": actual_output
                })

    # Step 3: If any tests failed, regenerate with feedback
    if failed_tests:
        error_feedback = format_test_failures(failed_tests)
        code = await generate_code(
            requirements,
            previous_error=error_feedback
        )
        # Could iterate here...

    return {
        "code": code,
        "passed": len(passed_tests),
        "failed": len(failed_tests),
        "test_results": {
            "passed": passed_tests,
            "failed": failed_tests
        }
    }
```

### Custom Agent Template

```python
from brain.agents.react_agent import ReActAgent, ToolRegistry
from typing import Dict, Any
import httpx

class CustomAgent:
    """Template for building custom specialized agents"""

    def __init__(self):
        self.registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self):
        """Register tools specific to this agent"""
        # Add domain-specific tools
        self.registry.register(
            "DomainTool1",
            "Description of what this tool does",
            self.domain_tool_1
        )
        self.registry.register(
            "DomainTool2",
            "Description of what this tool does",
            self.domain_tool_2
        )

    async def domain_tool_1(self, input_text: str) -> str:
        """First domain-specific tool"""
        # Implementation
        return f"Result from tool 1: {input_text}"

    async def domain_tool_2(self, input_text: str) -> str:
        """Second domain-specific tool"""
        # Implementation
        return f"Result from tool 2: {input_text}"

    async def solve(self, problem: str) -> Dict[str, Any]:
        """
        Main entry point for the agent.

        Args:
            problem: Problem statement or query

        Returns:
            Dictionary with answer and metadata
        """
        async with ReActAgent(self.registry) as agent:
            result = await agent.solve(problem)

            return {
                "answer": result.answer,
                "success": result.success,
                "steps": result.total_steps,
                "reasoning_trace": [
                    {
                        "thought": step.thought,
                        "action": step.action,
                        "observation": step.observation
                    }
                    for step in result.steps
                ]
            }

# Usage
async def main():
    agent = CustomAgent()
    result = await agent.solve("Your domain-specific problem here")
    print(result["answer"])
```

---

## Agent Prompting Best Practices

### System Prompt Design

The ReAct agent uses a carefully designed system prompt:

```python
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
```

**Key Elements:**

1. **Clear role definition** - "You are a helpful AI assistant..."
2. **Tool awareness** - List all available tools with descriptions
3. **Format specification** - Exact structure to follow
4. **Stop conditions** - When to use "Final Answer"

### Improving Agent Performance with Prompts

**Add Examples (Few-Shot Learning):**

```python
prompt += """
Example:

Thought: I need to find information about quantum computing
Action: LibrarySearch
Action Input: quantum computing basics
Observation: Found 3 documents about quantum computing...

Thought: Now I have enough information to answer
Action: Final Answer
Action Input: Quantum computing is a type of computation that...
"""
```

**Add Constraints:**

```python
prompt += """
Important Rules:
1. Always use tools when available rather than guessing
2. If a tool returns an error, try a different approach
3. Be concise in your thoughts - focus on what to do next
4. When you have enough information, provide a Final Answer
5. Don't use the same failing action more than twice
"""
```

**Domain-Specific Guidance:**

```python
# For research agent
prompt += """
Research Strategy:
1. Start with broad LibrarySearch
2. Search memories for related context
3. Combine sources in your final answer
4. Always cite sources using [Source N] notation
"""

# For code agent
prompt += """
Coding Strategy:
1. Break complex tasks into smaller functions
2. Always include test/demonstration code
3. Use print() statements to show output
4. Handle edge cases and errors
"""
```

### Handling Common Agent Failures

**Problem: Agent loops without making progress**

Solution: Add progress tracking to prompt

```python
Thought: [State what you learned from previous steps and what's still needed]
```

**Problem: Agent gives up too easily**

Solution: Encourage persistence

```python
prompt += """
If a tool returns an error:
1. Read the error message carefully
2. Try a different approach or tool
3. Adjust your input format based on the error
Don't give up after one failed attempt!
"""
```

**Problem: Agent provides answers without using tools**

Solution: Enforce tool usage

```python
prompt += """
CRITICAL: You MUST use available tools to gather information.
Never make up answers or rely on your training data.
If no tool can help, say "I cannot answer this with available tools."
"""
```

---

## Debugging Agent Reasoning

### Accessing Reasoning Traces

Every agent execution returns complete reasoning trace:

```python
result = await agent.solve("What is 7 factorial?")

# Inspect each step
for i, step in enumerate(result.steps, 1):
    print(f"\n--- Step {i} ---")
    print(f"Thought: {step.thought}")
    print(f"Action: {step.action}")
    print(f"Action Input: {step.action_input}")
    print(f"Observation: {step.observation}")

# Final answer
print(f"\nFinal Answer: {result.answer}")
print(f"Success: {result.success}")
print(f"Total Steps: {result.total_steps}")
```

### Common Debugging Patterns

**Check if tools are being called:**

```python
tools_used = [step.action for step in result.steps if step.action]
print(f"Tools used: {tools_used}")

if not tools_used:
    print("WARNING: Agent didn't use any tools!")
```

**Check for loops:**

```python
actions = [step.action for step in result.steps]
if len(actions) != len(set(actions)):
    print("WARNING: Agent repeated the same action")
    print(f"Action sequence: {actions}")
```

**Check tool error rates:**

```python
errors = [
    step.observation
    for step in result.steps
    if "Error" in step.observation
]
if errors:
    print(f"Found {len(errors)} tool errors:")
    for error in errors:
        print(f"  - {error}")
```

### Logging and Monitoring

**Add logging to tools:**

```python
import logging

logger = logging.getLogger(__name__)

async def my_tool(input_text: str) -> str:
    logger.info(f"Tool called with input: {input_text[:100]}")

    try:
        result = process(input_text)
        logger.info(f"Tool succeeded: {len(result)} chars returned")
        return result
    except Exception as e:
        logger.error(f"Tool failed: {str(e)}")
        return f"Error: {str(e)}"
```

**Track agent metrics:**

```python
class AgentMetrics:
    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.avg_steps = 0
        self.tool_usage = defaultdict(int)

    def record(self, result: AgentResult):
        self.total_calls += 1
        if result.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

        self.avg_steps = (
            (self.avg_steps * (self.total_calls - 1) + result.total_steps)
            / self.total_calls
        )

        for step in result.steps:
            if step.action:
                self.tool_usage[step.action] += 1

    def report(self):
        return {
            "total_calls": self.total_calls,
            "success_rate": self.successful_calls / self.total_calls,
            "avg_steps": self.avg_steps,
            "tool_usage": dict(self.tool_usage)
        }
```

---

## Tool Composition Strategies

### Sequential Composition

Chain tools together for complex workflows:

```python
async def multi_step_research(topic: str) -> str:
    """
    Research workflow:
    1. Search library for topic
    2. Extract key terms from results
    3. Search for each key term
    4. Synthesize all findings
    """
    # Step 1: Initial search
    initial_results = await library_search_tool(topic)

    # Step 2: Extract key terms (could be another tool)
    key_terms = extract_key_terms(initial_results)

    # Step 3: Expand search
    expanded_results = []
    for term in key_terms:
        result = await library_search_tool(term)
        expanded_results.append(result)

    # Step 4: Synthesize
    all_results = [initial_results] + expanded_results
    synthesis = synthesize(all_results)

    return synthesis
```

### Parallel Composition

Run multiple tools concurrently:

```python
import async

async def parallel_search(query: str) -> dict:
    """
    Search multiple sources simultaneously
    """
    # Launch all searches in parallel
    library_task = asyncio.create_task(
        library_search_tool(query)
    )
    memory_task = asyncio.create_task(
        memory_search(query)
    )
    code_task = asyncio.create_task(
        code_search(query)
    )

    # Wait for all to complete
    library_results, memory_results, code_results = await asyncio.gather(
        library_task,
        memory_task,
        code_task
    )

    return {
        "library": library_results,
        "memories": memory_results,
        "code": code_results
    }
```

### Conditional Composition

Choose tools based on input type:

```python
async def smart_dispatcher(user_input: str) -> str:
    """
    Route to appropriate tool based on input analysis
    """
    # Analyze input type
    if is_math_question(user_input):
        return await calculator(user_input)

    elif is_code_request(user_input):
        result = await code_assist(user_input)
        return result.code

    elif is_research_question(user_input):
        result = await research_query(user_input)
        return result.answer

    elif is_factual_query(user_input):
        return await library_search_tool(user_input)

    else:
        # Default: use ReAct agent
        async with ReActAgent(default_registry) as agent:
            result = await agent.solve(user_input)
            return result.answer
```

### Feedback Loops

Iterative refinement with tool feedback:

```python
async def iterative_improvement(task: str, quality_threshold: float = 0.8):
    """
    Keep refining until quality threshold met
    """
    attempts = 0
    max_attempts = 5

    while attempts < max_attempts:
        attempts += 1

        # Generate solution
        solution = await generate_solution(task)

        # Evaluate quality
        quality_score = await evaluate_solution(solution)

        if quality_score >= quality_threshold:
            return {
                "solution": solution,
                "quality": quality_score,
                "attempts": attempts
            }

        # Refine task with feedback
        task = f"{task}\n\nPrevious attempt scored {quality_score}. Improve by addressing: {get_weaknesses(solution)}"

    return {
        "solution": solution,
        "quality": quality_score,
        "attempts": attempts,
        "warning": "Quality threshold not met"
    }
```

---

## Integration with Brain API

### Adding an Agent Endpoint

**Location:** `/home/user/Archive-AI/brain/main.py`

```python
from brain.agents.react_agent import ReActAgent, ToolRegistry
from brain.agents.basic_tools import get_basic_tools

@app.post("/chat/agent/custom")
async def custom_agent_endpoint(request: ChatRequest):
    """Custom agent with specialized tools"""
    try:
        # Build tool registry
        registry = ToolRegistry()

        # Add your custom tools
        tools = get_custom_tools()
        for name, (description, func) in tools.items():
            registry.register(name, description, func)

        # Run agent
        async with ReActAgent(registry) as agent:
            result = await agent.solve(request.message)

        return {
            "response": result.answer,
            "success": result.success,
            "steps": result.total_steps,
            "reasoning": [
                {
                    "thought": step.thought,
                    "action": step.action,
                    "observation": step.observation
                }
                for step in result.steps
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Streaming Agent Responses

For real-time agent reasoning display:

```python
from sse_starlette.sse import EventSourceResponse

@app.post("/chat/agent/stream")
async def stream_agent(request: ChatRequest):
    """Stream agent reasoning steps in real-time"""

    async def event_generator():
        registry = build_registry()

        async with ReActAgent(registry) as agent:
            # Modify agent to yield steps instead of returning all at once
            async for step in agent.solve_streaming(request.message):
                # Send each step as SSE event
                yield {
                    "event": "step",
                    "data": json.dumps({
                        "thought": step.thought,
                        "action": step.action,
                        "observation": step.observation
                    })
                }

            # Send final answer
            yield {
                "event": "complete",
                "data": json.dumps({
                    "answer": agent.final_answer
                })
            }

    return EventSourceResponse(event_generator())
```

### Agent Middleware

Add logging, metrics, or rate limiting:

```python
from functools import wraps
import time

def agent_middleware(func):
    """Decorator to add monitoring to agent endpoints"""

    @wraps(func)
    async def wrapper(request: ChatRequest):
        start_time = time.time()

        # Log request
        logger.info(f"Agent request: {request.message[:100]}")

        try:
            # Execute agent
            result = await func(request)

            # Log success
            duration = time.time() - start_time
            logger.info(f"Agent completed in {duration:.2f}s")

            # Record metrics
            metrics_collector.record_agent_call(
                endpoint=func.__name__,
                duration=duration,
                success=True
            )

            return result

        except Exception as e:
            # Log failure
            duration = time.time() - start_time
            logger.error(f"Agent failed after {duration:.2f}s: {str(e)}")

            # Record metrics
            metrics_collector.record_agent_call(
                endpoint=func.__name__,
                duration=duration,
                success=False,
                error=str(e)
            )

            raise

    return wrapper

# Use decorator
@app.post("/chat/agent/monitored")
@agent_middleware
async def monitored_agent(request: ChatRequest):
    # Agent implementation
    pass
```

---

## Performance Optimization

### Tool Caching

Cache expensive tool results:

```python
from functools import lru_cache
import hashlib

class CachedTool:
    def __init__(self, tool_func, cache_size=100):
        self.tool_func = tool_func
        self.cache = {}
        self.cache_size = cache_size

    async def __call__(self, input_text: str) -> str:
        # Generate cache key
        cache_key = hashlib.md5(input_text.encode()).hexdigest()

        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self.cache[cache_key]

        # Execute tool
        result = await self.tool_func(input_text)

        # Store in cache
        self.cache[cache_key] = result

        # Evict old entries if cache full
        if len(self.cache) > self.cache_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        return result

# Usage
cached_library_search = CachedTool(library_search_tool, cache_size=50)
registry.register("LibrarySearch", description, cached_library_search)
```

### Reduce MAX_STEPS

For simple tasks, lower iteration limit:

```python
class FastAgent(ReActAgent):
    MAX_STEPS = 5  # Instead of default 10

# Or configure per-call
agent.MAX_STEPS = 3
result = await agent.solve(simple_question)
```

### Parallel Tool Execution

Execute independent tools simultaneously:

```python
async def parallel_execution(tools_to_call: list) -> list:
    """Execute multiple tools in parallel"""
    tasks = [
        execute_tool(tool_name, tool_input)
        for tool_name, tool_input in tools_to_call
    ]

    results = await asyncio.gather(*tasks)
    return results
```

### Use Faster Models

For simple agents, use smaller/faster models:

```python
# In agent._generate_step()
payload = {
    "model": config.VORPAL_MODEL,  # Fast small model
    "prompt": prompt,
    "max_tokens": 128,  # Reduce for faster generation
    "temperature": 0.3,  # Lower for more focused responses
}
```

### Timeout Configuration

Set appropriate timeouts for tools:

```python
async def tool_with_timeout(input_text: str, timeout: int = 5) -> str:
    """Tool with configurable timeout"""
    try:
        async with asyncio.timeout(timeout):
            result = await expensive_operation(input_text)
            return result
    except asyncio.TimeoutError:
        return f"Error: Operation timed out after {timeout}s"
```

---

## Advanced Patterns

### Multi-Agent Collaboration

Multiple agents working together:

```python
async def multi_agent_system(complex_task: str):
    """
    Break complex task across specialized agents:
    1. Research agent gathers information
    2. Code agent implements solution
    3. Verification agent tests result
    """
    # Step 1: Research
    research_agent = ResearchAgent()
    research_results = await research_agent.solve(
        f"Research background information for: {complex_task}"
    )

    # Step 2: Code generation
    code_agent = CodeAgent()
    code_results = await code_agent.solve(
        f"Implement solution for: {complex_task}\n"
        f"Background: {research_results.answer}"
    )

    # Step 3: Verification
    verify_agent = VerificationAgent()
    verification = await verify_agent.solve(
        f"Verify this solution:\n{code_results.code}\n"
        f"Requirements: {complex_task}"
    )

    return {
        "research": research_results.answer,
        "code": code_results.code,
        "verification": verification.answer,
        "confidence": verification.confidence_score
    }
```

### Hierarchical Task Decomposition

Agent that breaks complex tasks into subtasks:

```python
async def hierarchical_agent(complex_task: str):
    """
    Decompose complex task into subtasks and solve each
    """
    # Step 1: Decompose task
    decomposition_prompt = f"""
    Break this complex task into 3-5 smaller subtasks:
    {complex_task}

    Return as numbered list.
    """

    decomposition = await llm_call(decomposition_prompt)
    subtasks = parse_subtasks(decomposition)

    # Step 2: Solve each subtask
    subtask_results = []
    for subtask in subtasks:
        result = await agent.solve(subtask)
        subtask_results.append({
            "subtask": subtask,
            "result": result.answer
        })

    # Step 3: Synthesize results
    synthesis_prompt = f"""
    Original task: {complex_task}

    Subtask results:
    {format_results(subtask_results)}

    Provide final integrated answer:
    """

    final_answer = await llm_call(synthesis_prompt)

    return {
        "answer": final_answer,
        "subtasks": subtask_results
    }
```

### Self-Healing Agents

Agents that detect and recover from errors:

```python
class SelfHealingAgent(ReActAgent):
    """Agent with error recovery capabilities"""

    async def solve(self, question: str) -> AgentResult:
        attempts = 0
        max_retries = 3

        while attempts < max_retries:
            try:
                result = await super().solve(question)

                # Check if result looks valid
                if self.validate_result(result):
                    return result

                # Invalid result - try different approach
                question = self.reformulate_question(question, result)
                attempts += 1

            except Exception as e:
                attempts += 1
                if attempts >= max_retries:
                    raise

                # Modify approach based on error
                question = self.handle_error(question, e)

        raise Exception("Failed after all retry attempts")

    def validate_result(self, result: AgentResult) -> bool:
        """Check if result meets quality criteria"""
        if not result.success:
            return False
        if len(result.answer) < 10:
            return False
        if "error" in result.answer.lower():
            return False
        return True

    def reformulate_question(self, original: str, failed_result: AgentResult) -> str:
        """Reformulate question after failure"""
        return f"{original}\n\nPrevious attempt failed. Try a different approach."
```

### Agent Ensembles

Run multiple agents and combine results:

```python
async def ensemble_agent(question: str) -> str:
    """
    Run multiple agents with different configurations
    and aggregate results
    """
    # Create agents with different tool sets
    agent1 = ReActAgent(basic_tools_registry)
    agent2 = ReActAgent(advanced_tools_registry)
    agent3 = ReActAgent(research_tools_registry)

    # Run all in parallel
    results = await asyncio.gather(
        agent1.solve(question),
        agent2.solve(question),
        agent3.solve(question),
        return_exceptions=True
    )

    # Filter successful results
    successful = [r for r in results if isinstance(r, AgentResult) and r.success]

    if not successful:
        return "All agents failed to answer"

    # Aggregate answers (majority vote, averaging, etc.)
    if len(successful) == 1:
        return successful[0].answer

    # Use LLM to synthesize multiple answers
    synthesis_prompt = f"""
    Question: {question}

    Multiple answers from different agents:
    {chr(10).join(f"Agent {i+1}: {r.answer}" for i, r in enumerate(successful))}

    Provide the best synthesized answer:
    """

    final_answer = await llm_call(synthesis_prompt)
    return final_answer
```

---

## Conclusion

You now have a comprehensive understanding of Archive-AI's agent system. Key takeaways:

1. **ReAct Pattern** - Transparent reasoning + tool execution
2. **Tool Design** - Simple async functions with good error handling
3. **Tool Registry** - Central management of available tools
4. **Specialized Agents** - Research and Code agents for specific domains
5. **Debugging** - Full reasoning traces for transparency
6. **Integration** - Easy to add new endpoints to Brain API
7. **Optimization** - Caching, timeouts, and parallel execution
8. **Advanced Patterns** - Multi-agent collaboration and ensembles

### Next Steps

1. Study the existing agents in `/home/user/Archive-AI/brain/agents/`
2. Create a simple custom tool and test it
3. Build a specialized agent for your domain
4. Add monitoring and logging to track performance
5. Experiment with advanced patterns like ensembles

### Resources

- **ReAct Paper:** https://arxiv.org/abs/2210.03629
- **Code Location:** `/home/user/Archive-AI/brain/agents/`
- **API Docs:** http://localhost:8080/docs
- **Test Scripts:** `/home/user/Archive-AI/scripts/test-*.sh`

### Getting Help

- Check reasoning traces for debugging
- Review tool descriptions carefully
- Start simple and add complexity gradually
- Test tools independently before adding to agents
- Monitor agent metrics to identify bottlenecks

Happy agent building!
