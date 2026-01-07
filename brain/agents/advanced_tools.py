"""
Advanced Tools for ReAct Agents (Phase 3.5)
Tools that integrate with Archive-AI infrastructure.
"""

import httpx
import json
from datetime import datetime
from typing import Dict, Tuple, Callable, Any, Optional

from config import config
from memory.vector_store import vector_store
from agents.code_validator import validate_code


async def memory_search(query: str) -> str:
    """
    Search the vector store for relevant memories.

    This tool searches the Archive-AI memory system for similar
    messages based on semantic similarity.

    Args:
        query: Text to search for in memories

    Returns:
        Formatted list of similar memories with scores
    """
    try:
        # Validate input
        if not query or not query.strip():
            return "Error: Search query cannot be empty"

        query = query.strip()

        # Limit query length (prevent abuse)
        if len(query) > 500:
            return f"Error: Query too long ({len(query)} chars). Maximum 500 characters."

        # Ensure vector store is connected
        if not vector_store.client:
            vector_store.connect()

        # Search for similar memories
        results = vector_store.search_similar(
            query_text=query,
            top_k=3  # Return top 3 most relevant
        )

        if not results:
            return "No relevant memories found."

        # Format results
        output = f"Found {len(results)} relevant memories:\n\n"
        for i, memory in enumerate(results, 1):
            # Convert similarity score (lower is better in cosine distance)
            # to percentage (higher is better)
            similarity_pct = max(0, (1.0 - float(memory['similarity_score'])) * 100)

            output += f"{i}. [{similarity_pct:.1f}% match] {memory['message']}\n"
            output += f"   (Surprise: {memory['surprise_score']:.3f}, "
            output += f"Timestamp: {datetime.fromtimestamp(memory['timestamp']).strftime('%Y-%m-%d %H:%M:%S')})\n\n"

        return output.strip()

    except Exception as e:
        return f"Error searching memories: {str(e)}"


async def code_execution(code: str) -> str:
    """
    Execute Python code in a secure sandbox environment.

    This tool runs Python code in an isolated Docker container
    with limited permissions and no network access.

    Args:
        code: Python code to execute

    Returns:
        Output from code execution (stdout/stderr)

    Security: Code runs in isolated sandbox with:
    - No network access
    - Limited filesystem access
    - Resource limits (CPU, memory, time)
    - No dangerous modules (os, subprocess, etc.)
    """
    try:
        # Validate input
        if not code or not code.strip():
            return "Error: Code cannot be empty"

        # Aggressively strip surrounding quotes and whitespace
        code = code.strip()
        while (code.startswith("'") and code.endswith("'")) or (code.startswith('"') and code.endswith('"')):
            code = code[1:-1].strip()
        
        # Handle escaped newlines (if LLM sends literal \n)
        if "\\n" in code:
            try:
                # Use unicode_escape to convert literal \n to actual newline
                # but be careful not to break other characters
                code = bytes(code, "utf-8").decode("unicode_escape")
            except Exception:
                # Fallback to simple replace if decode fails
                code = code.replace("\\n", "\n")
        
        # Remove markdown code blocks
        if code.startswith("```"):
            # Remove first line (e.g. ```python)
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)
        
        code = code.strip()

        # Validate code before execution
        is_valid, validation_msg = validate_code(code)

        # If validation failed (critical issues), return error
        if not is_valid:
            return f"Validation Error:\n{validation_msg}"

        # If validation passed but has warnings, prepend warning to output
        warning_prefix = ""
        if validation_msg:
            warning_prefix = f"{validation_msg}\n\n"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{config.SANDBOX_URL}/execute",
                json={"code": code}
            )
            response.raise_for_status()
            result = response.json()

            # Format output
            if result.get("error"):
                return f"{warning_prefix}Execution Error:\n{result['error']}"

            stdout = result.get("stdout", "").strip()
            stderr = result.get("stderr", "").strip()

            output = ""
            if stdout:
                output += f"Output:\n{stdout}"
            if stderr:
                if output:
                    output += "\n\n"
                output += f"Warnings/Errors:\n{stderr}"

            # If no output, the validator already warned about this
            if not output:
                return f"{warning_prefix}Code executed successfully (no output)."

            # Return output with any warnings prepended
            return f"{warning_prefix}{output}" if warning_prefix else output

    except httpx.HTTPError as e:
        return f"Sandbox service error: {str(e)}"
    except Exception as e:
        return f"Error executing code: {str(e)}"


async def datetime_tool(query: str = "now") -> str:
    """
    Get current date/time information.

    Args:
        query: What time information to get:
            - "now" or "current": Current date and time
            - "date": Current date only
            - "time": Current time only
            - "timestamp": Unix timestamp
            - "iso": ISO 8601 format

    Returns:
        Requested date/time information
    """
    # Validate input
    if not isinstance(query, str):
        query = "now"

    # Strip quotes (LLM often adds them)
    query_cleaned = query.strip()
    if query_cleaned.startswith("'") and query_cleaned.endswith("'"):
        query_cleaned = query_cleaned[1:-1].strip()
    if query_cleaned.startswith('"') and query_cleaned.endswith('"'):
        query_cleaned = query_cleaned[1:-1].strip()

    query_lower = query_cleaned.lower().strip()

    # Validate mode
    valid_modes = ["now", "current", "date", "time", "timestamp", "iso", ""]
    if query_lower not in valid_modes:
        return f"Invalid mode '{query_cleaned}'. Valid modes: now, date, time, timestamp, iso"

    now = datetime.now()

    if query_lower in ["now", "current", ""]:
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    elif query_lower == "date":
        return f"Current date: {now.strftime('%Y-%m-%d')}"
    elif query_lower == "time":
        return f"Current time: {now.strftime('%H:%M:%S')}"
    elif query_lower == "timestamp":
        return f"Unix timestamp: {int(now.timestamp())}"
    elif query_lower == "iso":
        return f"ISO 8601: {now.isoformat()}"
    else:
        # Default to full datetime
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


async def json_tool(json_input: str) -> str:
    """
    Parse and query JSON data.

    This tool can:
    - Validate JSON syntax
    - Pretty-print JSON
    - Extract specific fields

    Args:
        json_input: JSON string to parse, or "key:value" to extract

    Returns:
        Parsed/formatted JSON or extracted value

    Examples:
        - '{"name": "Alice", "age": 30}' → Pretty-printed JSON
        - 'name:{"name": "Alice"}' → Extracts "name" field
    """
    try:
        # Strip common LLM-added quotes (single quotes around entire input)
        cleaned_input = json_input.strip()

        # Remove wrapping single quotes if present
        if cleaned_input.startswith("'") and cleaned_input.endswith("'"):
            cleaned_input = cleaned_input[1:-1]

        # Remove wrapping backticks (markdown code blocks)
        if cleaned_input.startswith("`") and cleaned_input.endswith("`"):
            cleaned_input = cleaned_input.strip("`")

        # Check if this is a key extraction request (key:json_string)
        if ":" in cleaned_input:
            # Try to detect key:json pattern
            # Look for first colon that's followed by { or [
            parts = cleaned_input.split(":", 1)
            if len(parts) == 2:
                potential_key = parts[0].strip()
                potential_json = parts[1].strip()

                # Check if the second part looks like JSON
                if potential_json.startswith(("{", "[")):
                    try:
                        data = json.loads(potential_json)

                        # Extract the key if it exists
                        if isinstance(data, dict) and potential_key in data:
                            value = data[potential_key]
                            return f"Extracted '{potential_key}': {json.dumps(value, indent=2)}"
                        else:
                            # Key not found, return parsed JSON
                            formatted = json.dumps(data, indent=2)
                            return f"Parsed JSON (key '{potential_key}' not found):\n{formatted}"
                    except json.JSONDecodeError:
                        # Not valid JSON after the colon, treat whole thing as JSON
                        pass

        # Regular JSON parsing (no key extraction)
        data = json.loads(cleaned_input)

        # Pretty-print
        formatted = json.dumps(data, indent=2)

        # Add summary
        if isinstance(data, dict):
            return f"Valid JSON object with {len(data)} keys:\n{formatted}"
        elif isinstance(data, list):
            return f"Valid JSON array with {len(data)} items:\n{formatted}"
        else:
            return f"Valid JSON value:\n{formatted}"

    except json.JSONDecodeError as e:
        return f"Invalid JSON: {str(e)}\nInput received: {json_input[:100]}..."
    except Exception as e:
        return f"Error processing JSON: {str(e)}"


async def web_search_tool(query: str) -> str:
    """
    Search the web using DuckDuckGo with fallback to Wikipedia.

    Args:
        query: Search query

    Returns:
        Formatted search results from best available source
    """
    try:
        from duckduckgo_search import DDGS
        
        # Validate input
        if not query or not query.strip():
            return "Error: Search query cannot be empty"
            
        # Strip surrounding quotes from LLM
        query = query.strip()
        while (query.startswith("'") and query.endswith("'")) or (query.startswith('"') and query.endswith('"')):
            query = query[1:-1].strip()
        
        results = []
        source = "DuckDuckGo"
        
        # Stage 1: Try DDG Text
        try:
            with DDGS() as ddgs:
                search_gen = ddgs.text(query, max_results=5)
                for r in search_gen:
                    results.append(r)
        except Exception:
            pass # Fall through to next stage
            
        # Stage 2: Try DDG News (if text failed)
        if not results:
            try:
                with DDGS() as ddgs:
                    search_gen = ddgs.news(query, max_results=5)
                    for r in search_gen:
                        # Normalize keys to match text results
                        results.append({
                            'title': r.get('title'),
                            'href': r.get('url'),
                            'body': r.get('body')
                        })
                if results:
                    source = "DuckDuckGo News"
            except Exception:
                pass
                
        # Stage 3: Try Wikipedia (if DDG failed)
        if not results:
            try:
                import httpx
                headers = {"User-Agent": "Archive-AI/1.0 (Cognitive Framework; Local-First)"}
                wiki_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={query}&limit=3&format=json"
                
                async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
                    resp = await client.get(wiki_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Wikipedia opensearch format: [query, [titles], [descriptions], [links]]
                        titles = data[1]
                        bodies = data[2]
                        links = data[3]
                        
                        for i in range(len(titles)):
                            results.append({
                                'title': titles[i],
                                'href': links[i],
                                'body': bodies[i]
                            })
                        if results:
                            source = "Wikipedia"
            except Exception:
                pass
                
        if not results:
            return f"No results found for '{query}' across multiple sources (DDG, News, Wikipedia)."
            
        # Format results
        output = f"Web Search Results ({source}) for '{query}':\n\n"
        for i, res in enumerate(results, 1):
            title = res.get('title', 'No Title')
            link = res.get('href', '#')
            body = res.get('body', 'No description available.')
            
            output += f"{i}. {title}\n"
            output += f"   Link: {link}\n"
            output += f"   Snippet: {body}\n\n"
            
        return output.strip()
        
    except ImportError:
        return "Error: duckduckgo-search library not installed."
    except Exception as e:
        return f"Error performing web search: {str(e)}"


async def rlm_read_tool(corpus: str) -> str:
    """
    Specialized tool for processing large documents using the Recursive Language Model (RLM) pattern.
    It decomposes the text and analyzes it iteratively.
    """
    from .recursive_agent import RecursiveAgent
    try:
        # We give it a generic 'summarize and analyze' instruction
        # since tools typically take one input string.
        async with RecursiveAgent(corpus=corpus) as agent:
            result = await agent.solve(
                "Perform a comprehensive analysis of this corpus. "
                "Identify key themes, significant facts, and provide a detailed summary."
            )
            return result.answer
    except Exception as e:
        return f"Error in RLM_Read: {str(e)}"


# Tool registry for advanced tools
ADVANCED_TOOLS = {
    "MemorySearch": (
        "Search past conversations for relevant information using semantic similarity. "
        "Use this when you need to recall previous discussions or find related context. "
        "Input format: plain text query describing what you're looking for. "
        "Example: 'conversations about quantum physics'",
        memory_search
    ),
    "CodeExecution": (
        "Execute Python code in a secure sandbox to perform calculations or data processing. "
        "Use this for complex math, data transformations, or algorithmic problems. "
        "IMPORTANT: Your code MUST print() the final result to see output. "
        "Input format: valid Python code as a single string. "
        "Good example: 'result = 7*6*5*4*3*2*1\\nprint(result)' "
        "Bad example: 'result = 7*6*5*4*3*2*1' (no print, no output!) "
        "WARNING: Code runs in isolation with 10-second timeout.",
        code_execution
    ),
    "DateTime": (
        "Get current date and time information in various formats. "
        "Use this when you need to know the current date, time, or timestamp. "
        "Input format: 'date' (for date only), 'time' (for time only), 'now' (for both), "
        "'timestamp' (Unix time), or 'iso' (ISO 8601 format). "
        "Example: 'date' returns '2025-12-28'",
        datetime_tool
    ),
    "JSON": (
        "Parse, validate, and extract data from JSON strings. "
        "Use this to work with JSON data or extract specific fields. "
        "Input format: Just the JSON string itself (do NOT add extra quotes). "
        "For extraction: 'fieldname:{json_here}' "
        "Examples: '{\"name\":\"Alice\"}' or 'name:{\"name\":\"Alice\",\"age\":30}'",
        json_tool
    ),
    "WebSearch": (
        "Search the web for current information, news, or technical documentation. "
        "Powered by DuckDuckGo (privacy-focused). "
        "Input format: search query as plain text. "
        "Example: 'latest python version' or 'who won the 2024 super bowl'",
        web_search_tool
    ),
    "RLM_Read": (
        "Recursively read and analyze a large text document or corpus. "
        "Use this for infinite-context tasks like summarizing books, searching huge logs, "
        "or deep-reading complex papers. "
        "Input format: The entire text content to be analyzed.",
        rlm_read_tool
    ),
}


def get_advanced_tools() -> Dict[str, Tuple[str, Callable]]:
    """Get the advanced tools dictionary for use with ReAct agent"""
    return ADVANCED_TOOLS
