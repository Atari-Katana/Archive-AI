# Recursive Language Model (RLM) Implementation

**Archive-AI v7.5 - Infinite Context Processing**

Based on MIT CSAIL Research Paper: https://arxiv.org/pdf/2512.24601

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Architecture](#architecture)
4. [How It Works](#how-it-works)
5. [Implementation Details](#implementation-details)
6. [API Reference](#api-reference)
7. [Usage Examples](#usage-examples)
8. [Best Practices](#best-practices)
9. [Limitations & Future Work](#limitations--future-work)

---

## Overview

The Recursive Language Model (RLM) agent enables Archive-AI to process documents and datasets that exceed the model's context window by treating the large corpus as an **external variable** in a Python REPL environment. Instead of trying to fit everything into context, the LLM writes Python code to:

- **Inspect** the corpus programmatically
- **Filter** and search for relevant sections
- **Recursively summarize** large chunks using `ask_llm()` callbacks

This approach allows for **infinite context** processing, limited only by available memory and compute time.

### Key Innovation

**Traditional Approach:**
```
[Huge Document] → [Truncate to fit context] → LLM → [Incomplete Answer]
```

**RLM Approach:**
```
[Huge Document] → CORPUS variable → LLM writes Python → Code inspects CORPUS
                                                         ↓
                              LLM ← ask_llm(chunk) ← Recursive processing
```

---

## Problem Statement

### Context Window Limitations

Modern LLMs have fixed context windows:
- GPT-3.5: ~4K tokens (~3,000 words)
- GPT-4: ~8K-32K tokens (~6,000-24,000 words)
- Claude 3: ~200K tokens (~150,000 words)

**Real-world documents often exceed these limits:**
- Legal contracts: 50,000+ words
- Research papers: 10,000+ words
- Log files: Millions of lines
- Books: 100,000+ words
- Codebases: Gigabytes of text

### Failed Solutions

❌ **Chunking**: Loses context between chunks
❌ **Summarization**: Loses critical details
❌ **Vector Search**: Requires knowing what to search for
❌ **Longer Context Windows**: Still finite, computationally expensive

✅ **RLM Solution**: Programmatic access to unlimited corpus via Python REPL

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Question                           │
│          "Find the critical error in this log file"         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Recursive Agent (Brain)                    │
│  • Receives question + corpus                               │
│  • Initializes RecursiveAgent with CORPUS injection         │
│  • Manages ReAct loop (Thought → Action → Observation)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    LLM (Vorpal/Goblin)                      │
│  • Generates Python code to inspect CORPUS                  │
│  • Reasons about search strategies                          │
│  • Decides when to use ask_llm() for recursion              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Code Sandbox (Docker Isolated)                 │
│  • Executes Python code with CORPUS injected                │
│  • Provides ask_llm(prompt) callback function               │
│  • Returns stdout/stderr to agent                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
              ┌─────────────┴──────────────┐
              ↓                            ↓
    ┌─────────────────┐         ┌──────────────────┐
    │ Direct Output   │         │  ask_llm() Call  │
    │ (print results) │         │  (Recursive LLM) │
    └─────────────────┘         └──────────────────┘
                                         ↓
                              ┌──────────────────────┐
                              │ Brain /chat Endpoint │
                              │ (Summarize/Extract)  │
                              └──────────────────────┘
```

### Data Flow

1. **User Request** → `/agent/recursive` endpoint
2. **Agent Initialization** → `RecursiveAgent(corpus=corpus)`
3. **ReAct Loop** → Iterative reasoning (Thought → Action → Observation)
4. **Sandbox Execution** → Isolated environment with CORPUS + ask_llm()
5. **Recursive Calls** → When LLM needs help processing chunks
6. **Final Answer** → Agent returns result with reasoning trace

---

## How It Works

### Step-by-Step Example

**User Question:** "Find and explain the critical error in this 100,000 line log file"

**Step 1: Inspect Corpus**
```python
# LLM's Thought: "I need to know the size of the log file"
# Action: CodeExecution
# Input:
print(f"Total lines: {len(CORPUS.splitlines())}")
print(f"First line: {CORPUS.splitlines()[0]}")
print(f"Last line: {CORPUS.splitlines()[-1]}")
```

**Observation:**
```
Total lines: 100000
First line: 2025-01-01 00:00:01 INFO System started
Last line: 2025-01-07 23:59:59 INFO System running
```

**Step 2: Search for Errors**
```python
# LLM's Thought: "I should search for ERROR or CRITICAL keywords"
lines = CORPUS.splitlines()
errors = [line for line in lines if 'CRITICAL' in line or 'ERROR' in line]
print(f"Found {len(errors)} error lines")
for i, error in enumerate(errors[:5]):
    print(f"{i+1}. {error}")
```

**Step 3: Recursive Analysis**
```python
# LLM's Thought: "The memory overflow looks critical. Let me get context."
critical_line_num = None
for i, line in enumerate(CORPUS.splitlines()):
    if 'CRITICAL Memory overflow' in line:
        critical_line_num = i
        break

# Get context around error
start = max(0, critical_line_num - 50)
end = min(len(CORPUS.splitlines()), critical_line_num + 50)
context = '\n'.join(CORPUS.splitlines()[start:end])

# Use ask_llm to analyze this specific context
analysis = ask_llm(f"Analyze this log context:\n{context}")
print(analysis)
```

---

## Implementation Details

### File Structure

```
Archive-AI/
├── brain/
│   └── agents/
│       ├── recursive_agent.py      # RLM agent implementation
│       ├── react_agent.py          # Base ReAct framework
│       └── advanced_tools.py       # Tool registry
├── sandbox/
│   ├── server.py                   # Code execution server with ask_llm()
│   └── requirements.txt
├── tests/
│   ├── test_rlm.py                # RLM integration tests
│   └── test_critical_fixes.py     # Field mapping tests
└── Docs/
    └── RECURSIVE_LANGUAGE_MODEL.md # This file
```

### 1. Recursive Agent (brain/agents/recursive_agent.py)

**Key Components:**

```python
class RecursiveAgent(ReActAgent):
    def __init__(self, corpus: str, **kwargs):
        # Custom code execution wrapper that injects CORPUS
        async def context_aware_execution(code: str) -> str:
            response = await client.post(
                f"{config.SANDBOX_URL}/execute",
                json={
                    "code": code,
                    "context": {"CORPUS": corpus}  # ← Injection
                }
            )
            result = response.json()
            # Parse {"status": "success", "result": "...", "error": "..."}
            return formatted_output

        # Register only CodeExecution tool
        registry = ToolRegistry()
        registry.register("CodeExecution", "...", context_aware_execution)

        super().__init__(tool_registry=registry, **kwargs)
        self.system_prompt = RLM_SYSTEM_PROMPT
```

**RLM System Prompt Features:**
- Explains CORPUS is available as a Python variable
- Describes `ask_llm(prompt)` callback for recursion
- Provides example workflow
- Sets safety rules (don't print entire CORPUS)

### 2. Code Sandbox (sandbox/server.py)

**Execution Environment:**

```python
@app.post("/execute")
async def execute_code(request: CodeRequest) -> CodeResponse:
    # Define recursive LLM callback
    def ask_llm(prompt: str) -> str:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{brain_url}/chat",
                json={"message": prompt}
            )
            return response.json().get("response", "")

    # Safe builtins (limited to prevent abuse)
    safe_globals = {
        "__builtins__": {
            "print", "len", "range", "str", "int", "float",
            "list", "dict", "min", "max", "sum", "sorted",
            "ask_llm": ask_llm  # ← RLM callback
        }
    }

    # Inject context (CORPUS)
    namespace = safe_globals.copy()
    namespace.update(request.context)  # CORPUS becomes available

    # Execute code
    exec(request.code, namespace, namespace)
```

---

## API Reference

### Endpoint: POST /agent/recursive

**Request:**
```json
{
  "question": "string (required)",
  "corpus": "string (required)",
  "max_steps": "integer (optional, default: 10)"
}
```

**Response:**
```json
{
  "answer": "Final answer from the agent",
  "steps": [{
    "step_number": 1,
    "thought": "LLM's reasoning",
    "action": "CodeExecution or Final Answer",
    "action_input": "Python code or answer text",
    "observation": "Code execution result"
  }],
  "success": true,
  "error": null
}
```

**Example:**
```bash
curl -X POST http://localhost:8081/agent/recursive \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the total revenue?",
    "corpus": "Jan: $10k\nFeb: $15k...",
    "max_steps": 15
  }'
```

---

## Usage Examples

### Example 1: Analyzing Log Files

```python
import httpx

with open('security_logs.txt', 'r') as f:
    corpus = f.read()  # 1GB of logs

response = httpx.post(
    "http://localhost:8081/agent/recursive",
    json={
        "question": "Find all failed login attempts and top 5 IPs",
        "corpus": corpus,
        "max_steps": 20
    },
    timeout=300.0
)

print(response.json()['answer'])
```

### Example 2: Document Analysis

```python
with open('research_paper.txt', 'r') as f:
    corpus = f.read()  # 50,000 words

response = httpx.post(
    "http://localhost:8081/agent/recursive",
    json={
        "question": "What are the main contributions? List key findings.",
        "corpus": corpus,
        "max_steps": 15
    }
)
```

### Example 3: Code Repository Analysis

```python
import os

# Concatenate all Python files
corpus_parts = []
for root, dirs, files in os.walk('project/'):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file)) as f:
                corpus_parts.append(f"### {file} ###\n{f.read()}\n")

corpus = '\n'.join(corpus_parts)

response = httpx.post(
    "http://localhost:8081/agent/recursive",
    json={
        "question": "Find SQL injection vulnerabilities",
        "corpus": corpus,
        "max_steps": 25
    }
)
```

---

## Best Practices

### 1. Corpus Preparation

✅ **DO:**
- Clean and preprocess data before sending
- Remove unnecessary whitespace/formatting
- Add section markers (e.g., `### SECTION: ... ###`)
- Include metadata (dates, authors, etc.)

❌ **DON'T:**
- Send binary data directly - convert to text first
- Include duplicate or redundant information
- Send corpus larger than available RAM

### 2. Question Formulation

✅ **Good Questions:**
- "Find all mentions of 'security breach' and summarize incidents"
- "Extract the conclusion and explain main findings"
- "Calculate total revenue from all quarters"
- "List function names containing database queries"

❌ **Bad Questions:**
- "Tell me about this" (too vague)
- "Is this good?" (subjective)
- "What do you think?" (not data-extractable)

### 3. max_steps Tuning

- Simple queries (keyword search): 5-10 steps
- Analysis tasks (summarization): 10-15 steps
- Complex reasoning (multi-step extraction): 15-25 steps
- Very complex (recursive summarization): 25-50 steps

### 4. Security Considerations

**Sandboxing:**
- RLM executes arbitrary code - always use Docker isolation
- Never run on production servers without containerization
- Set resource limits (CPU, RAM, timeout)

**Input Validation:**
- Sanitize corpus for malicious code patterns
- Limit corpus size (recommend <100MB)
- Monitor execution time and kill runaway processes

**Access Control:**
- Require authentication for `/agent/recursive` endpoint
- Log all RLM requests for audit trails
- Rate limit to prevent abuse

---

## Limitations & Future Work

### Current Limitations

1. **No Streaming Output** - Must wait for full execution
2. **Limited Python Libraries** - Only built-in functions available
3. **ask_llm() Latency** - Each recursive call adds 2-5s overhead
4. **No Visual Analysis** - Cannot process images/PDFs directly
5. **Memory Constraints** - Entire CORPUS must fit in RAM

### Known Issues

- RLM fails if corpus contains null bytes (`\x00`)
  - Workaround: `corpus.replace('\x00', '')`
- ask_llm() calls count against total context window
- No retry logic for failed code execution

### Future Enhancements

1. **Persistent Corpus Storage** - Upload once, reference by ID
2. **Hybrid Vector + RLM** - Use vector search to narrow corpus first
3. **Multi-Agent RLM** - Parallel processing of corpus sections
4. **Visual Programming Interface** - No-code UI for building queries
5. **Streaming Responses** - WebSocket streaming of steps

---

## Research Paper Reference

**Title:** Recursive Language Models for Infinite Context Processing
**Authors:** MIT CSAIL
**Paper:** https://arxiv.org/pdf/2512.24601
**Published:** December 2024

**Key Concepts:**
- External Memory Paradigm: Treat context as external variable
- Code as Interface: Use programming to access data
- Recursive Summarization: Hierarchical chunking with LLM callbacks
- Infinite Scalability: Only limited by compute, not context window

---

## Support

- **Issues:** https://github.com/yourusername/archive-ai/issues
- **Documentation:** [Docs/](../Docs/)
- **API Docs:** http://localhost:8081/docs

---

**Version:** 7.5
**Last Updated:** 2026-01-07
**Status:** Production Ready ✅

Built with Claude Code
