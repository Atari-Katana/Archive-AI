# Agent Tutorial: Creating and Deploying Custom Agents

## Overview

Archive-AI uses ReAct (Reasoning + Acting) agents that can think through problems and use tools to accomplish tasks. This tutorial shows you how to create and deploy your own custom agent.

## What You'll Learn

1. How to create a custom tool
2. How to register the tool with the agent system
3. How to test your agent via the API
4. How to use your agent in the UI

---

## Part 1: Creating a Custom Tool

Tools are Python functions that agents can call. Each tool needs:
- A clear docstring describing what it does
- Typed parameters
- A return value

**Example:** Let's create a weather tool

Create `/home/davidjackson/Archive-AI/brain/tools/weather_tool.py`:

```python
def get_weather(location: str) -> str:
    """
    Get current weather for a location.
    
    Args:
        location: City name or zip code
        
    Returns:
        Weather description string
    """
    # In a real implementation, you'd call a weather API
    # For this example, we'll return mock data
    return f"Weather in {location}: Sunny, 72°F"
```

---

## Part 2: Registering Your Tool

Add your tool to the tool registry in `/home/davidjackson/Archive-AI/brain/agents.py`:

```python
# Import your tool
from tools.weather_tool import get_weather

# In the get_basic_tools() function, add your tool:
def get_basic_tools() -> ToolRegistry:
    registry = ToolRegistry()
    
    # Existing tools...
    registry.register_tool("calculator", calculate)
    registry.register_tool("python_exec", execute_python)
    
    # Add your new tool
    registry.register_tool("weather", get_weather)
    
    return registry
```

**That's it!** Your tool is now available to all agents.

---

## Part 3: Testing Your Agent

### Via API (using curl):

```bash
curl -X POST http://localhost:8080/agent \
  -H "Content-Type: application/json" \
  -d '{
    "task": "What'\''s the weather in San Francisco?",
    "max_steps": 5,
    "tools": "basic"
  }'
```

### Via Python:

```python
import requests

response = requests.post('http://localhost:8080/agent', json={
    'task': 'What is the weather in San Francisco?',
    'max_steps': 5,
    'tools': 'basic'
})

print(response.json())
```

### Expected Response:

```json
{
  "answer": "The weather in San Francisco is Sunny, 72°F",
  "steps": [
    {
      "step_number": 1,
      "thought": "I need to get the weather for San Francisco",
      "action": "weather",
      "action_input": "San Francisco",
      "observation": "Weather in San Francisco: Sunny, 72°F"
    },
    {
      "step_number": 2,
      "thought": "I have the weather information",
      "action": "FINISH",
      "action_input": "The weather in San Francisco is Sunny, 72°F"
    }
  ],
  "total_steps": 2,
  "success": true
}
```

---

## Part 4: Using in the UI

1. Open the Archive-AI web interface at `http://localhost:8080/ui`
2. Click the **"Basic Agent"** or **"Advanced"** mode button
3. Type your question: "What's the weather in Boston?"
4. The agent will automatically use your tool!

---

## Advanced: Tool Categories

Archive-AI has two tool levels:

### Basic Tools (Fast, Safe)
- Calculator, time queries, data analysis
- Use for: Quick facts, calculations
- Register in: `get_basic_tools()`

### Advanced Tools (Powerful, Needs Caution)
- Code execution, web search, file operations
- Use for: Complex tasks, research
- Register in: `get_advanced_tools()`

**Example - Adding to Advanced:**

```python
def get_advanced_tools() -> ToolRegistry:
    registry = get_basic_tools()  # Start with basic tools
    
    # Add powerful tools
    registry.register_tool("web_search", web_search)
    registry.register_tool("your_advanced_tool", your_function)
    
    return registry
```

---

## Best Practices

1. **Clear Docstrings**: The agent reads your docstring to understand the tool
   ```python
   def good_tool(city: str) -> str:
       """Get population of a city."""  # ✅ Clear
       
   def bad_tool(x: str) -> str:
       """Does stuff."""  # ❌ Vague
   ```

2. **Type Hints**: Always use type hints for parameters and returns

3. **Error Handling**: Return error messages as strings, don't raise exceptions
   ```python
   try:
       result = api_call()
       return result
   except Exception as e:
       return f"Error: {str(e)}"  # ✅ Agent can handle this
   ```

4. **Testing**: Test tools independently before registering them
   ```bash
   python3 -c "from tools.weather_tool import get_weather; print(get_weather('NYC'))"
   ```

---

## Debugging Tips

### Tool Not Being Called?

1. Check the docstring is clear
2. Verify tool is registered in the right category
3. Check logs: `docker-compose logs brain | grep -i agent`

### Agent Making Wrong Decisions?

- Improve tool docstrings
- Add examples in docstrings
- Reduce `max_steps` to limit exploration

### Want to See Agent Reasoning?

Check the `steps` array in the response - it shows all thoughts and actions.

---

## Quick Reference

**File Locations:**
- Tools: `/brain/tools/`
- Agent code: `/brain/agents.py`
- API docs: `http://localhost:8080/docs`

**Key Endpoints:**
- `/agent` - Run basic agent
- `/agent/advanced` - Run advanced agent
- `/health` - Check if agent system is ready

**Restart After Changes:**
```bash
docker-compose restart brain
```

---

## Example: Complete Custom Tool

```python
# /brain/tools/crypto_tool.py
import requests

def get_crypto_price(symbol: str) -> str:
    """
    Get current price of a cryptocurrency.
    
    Args:
        symbol: Crypto symbol (BTC, ETH, etc.)
        
    Returns:
        Current price in USD
    """
    try:
        # Call a crypto API (example)
        response = requests.get(
            f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot',
            timeout=5
        )
        data = response.json()
        price = data['data']['amount']
        return f"{symbol} is currently ${price} USD"
    except Exception as e:
        return f"Error fetching {symbol} price: {str(e)}"
```

Register it:
```python
# In agents.py
from tools.crypto_tool import get_crypto_price

registry.register_tool("crypto_price", get_crypto_price)
```

Use it:
```bash
curl -X POST http://localhost:8080/agent \
  -H "Content-Type: application/json" \
  -d '{"task": "What is the price of Bitcoin?"}'
```

---

## Next Steps

- Create tools for your specific use case (APIs, databases, etc.)
- Explore the existing tools in `/brain/tools/`
- Read `/brain/agents.py` to understand the ReAct loop
- Check out Advanced mode for more powerful capabilities

**Happy building! 🤖**
