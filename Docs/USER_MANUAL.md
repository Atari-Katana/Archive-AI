# Archive-AI v7.5 - User Manual
## Your Personal AI Assistant with Perfect Memory

**Welcome to Archive-AI!**  
This manual will teach you everything you need to know to get the most out of your AI companion.

---

## Table of Contents

1. [What is Archive-AI?](#what-is-archive-ai)
2. [Getting Started](#getting-started)
3. [The Web Interface](#the-web-interface)
4. [Chat Modes](#chat-modes)
5. [The Memory System](#the-memory-system)
6. [Using Agents](#using-agents)
7. [Available Tools](#available-tools)
8. [Advanced Features](#advanced-features)
9. [Tips & Tricks](#tips--tricks)
10. [Common Questions](#common-questions)

---

## What is Archive-AI?

Archive-AI is your **personal AI assistant that never forgets**. Unlike cloud-based AI services, everything runs on your computer, so your conversations stay completely private.

### What Makes Archive-AI Special?

**🧠 Perfect Memory**
- Automatically remembers important conversations
- Finds old discussions instantly with semantic search
- Never loses context from past interactions

**🔒 100% Private**
- No data sent to the cloud
- All processing happens on your machine
- Your conversations belong to you

**🛠️ Tool Use**
- Performs calculations
- Executes code
- Searches your memories
- Works with dates, JSON, and more

**🎯 Smart Routing**
- Detects what you need automatically
- Searches memories when you ask about the past
- Provides help when you need guidance

**✅ Verification Mode**
- Double-checks facts to reduce errors
- Shows its reasoning process
- More reliable for important questions

---

## Getting Started

### First Time Setup

1. **Start Archive-AI**:
   ```bash
   cd ~/Archive-AI
   docker-compose up -d
   ```

2. **Wait for Services** (first time takes ~2 minutes):
   ```bash
   # Check if ready
   curl http://localhost:8080/health
   ```

3. **Open the Interface**:
   - Navigate to: `http://localhost:8888`
   - You should see the Archive-AI chat interface

### Your First Conversation

Try these to get started:

1. **Simple Chat**:
   ```
   You: Hello! What can you do?
   AI: [Returns help information]
   ```

2. **Math Question**:
   ```
   You: What is 15 multiplied by 23?
   AI: [Uses Calculator tool] 345
   ```

3. **Memory Test**:
   ```
   You: Remember that my favorite color is blue
   AI: [Responds and stores if surprising]
   
   [Later...]
   You: What did I say about my favorite color?
   AI: [Searches memories and finds it]
   ```

---

## The Web Interface

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Archive-AI                                    [System Info]  │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌────────────────────────────────┐  ┌────────────────────┐  │
│  │                                │  │  System Status     │  │
│  │                                │  │  • Brain: Online   │  │
│  │      Chat Messages             │  │  • Model: Qwen-7B  │  │
│  │                                │  │  • Tools: 11       │  │
│  │                                │  │                    │  │
│  │  [Mode Buttons]                │  │  System Health     │  │
│  │  Chat | Verified | Agent       │  │  • CPU: 12%        │  │
│  │                                │  │  • Memory: 45%     │  │
│  │  User: Hello!                  │  │  • VRAM: 84%       │  │
│  │                                │  │  • Tokens/s: 95    │  │
│  │  AI: Hello! How can I help?    │  │                    │  │
│  │                                │  │  Memory Browser    │  │
│  │                                │  │  127 memories      │  │
│  │                                │  │  [Search...]       │  │
│  └────────────────────────────────┘  └────────────────────┘  │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [Type your message...]                          [Send] │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Interface Elements

**Chat Area** (Left):
- Where conversations happen
- Messages appear with typewriter effect
- Scroll to see history

**Mode Buttons**:
- **Chat**: Fast, normal conversation
- **Verified**: Double-checks facts
- **Basic Agent**: Uses simple tools (calculator, text)
- **Advanced**: Uses all tools (code, memory search)

**System Status Panel** (Right):
- Shows if services are running
- Displays current model
- Lists available tools

**System Health Panel**:
- **Uptime**: How long the system has been running
- **Memories**: Total conversations stored
- **CPU**: Processor usage
- **Memory**: RAM usage  
- **VRAM**: GPU memory usage
- **Tokens/sec**: AI response speed

**Memory Browser**:
- Browse all stored conversations
- Search for specific topics
- Click to view details

---

## Chat Modes

Archive-AI has four conversation modes, each optimized for different tasks.

### 1. Chat Mode (Default) ⚡

**Best for**: Quick questions, casual conversation

**How it works**:
- Fast GPU-powered responses (~1 second)
- Automatically detects if you need help or memory search
- Uses Vorpal engine (7B model)

**When to use**:
- General conversation
- Quick facts
- When speed matters

**Example**:
```
You: What's the weather like today?
AI: I don't have access to real-time weather data...

You: Tell me a joke
AI: Why did the scarecrow win an award? ...
```

**Routing Features**:
Chat mode automatically routes special queries:

- **Help Queries** ("help", "what can you do?"):
  ```
  You: what can you do?
  AI: I'm Archive-AI, your local AI companion...
      [Shows capabilities]
  ```

- **Memory Searches** ("what did I say about...", "remember when..."):
  ```
  You: What did I say about Python?
  AI: I found these relevant memories:
      1. "Can you help me learn Python?" (95% match)
      2. "What's the best Python IDE?" (87% match)
  ```

### 2. Verified Mode ✅

**Best for**: Important facts, research, when accuracy matters

**How it works**:
1. Generates initial answer
2. Creates verification questions
3. Answers verification questions independently
4. Compares for consistency
5. Revises if contradictions found

**When to use**:
- Fact-checking
- Important decisions
- When you need confidence

**Example**:
```
You: What is the largest planet in our solar system?

AI Response:
Initial: "Jupiter is the largest planet..."

Verification Questions:
1. Is Jupiter actually the largest planet?
2. What are the sizes of other planets?

Verification Answers:
1. Yes, Jupiter is 142,984 km in diameter...
2. Saturn is second at 120,536 km...

Final (Verified): "Jupiter is the largest planet at 142,984 km diameter,
followed by Saturn at 120,536 km."

Status: ✅ Verified (no revisions needed)
```

**Trade-offs**:
- ✅ More accurate
- ❌ 3-4x slower (multiple LLM calls)
- ✅ Shows reasoning process

### 3. Basic Agent Mode 🔧

**Best for**: Calculations, text processing, simple tasks

**How it works**:
- Uses ReAct (Reasoning + Acting) loop
- Can use 6 basic tools
- Shows thought process step-by-step

**When to use**:
- Math problems
- Text manipulation
- When you want to see the reasoning

**Available Tools**:
1. Calculator
2. StringLength
3. WordCount
4. ReverseString
5. ToUppercase
6. ExtractNumbers

**Example**:
```
You: What is 15 multiplied by 23?

AI Response:
Step 1:
  Thought: I need to calculate 15 * 23
  Action: Calculator
  Input: "15 * 23"
  Result: Result: 345

Step 2:
  Thought: I have the answer
  Action: FINISH
  Answer: 345

Final Answer: 345
```

**Example with Multiple Steps**:
```
You: How many words are in "Hello world, this is a test"?

Step 1:
  Thought: I need to count the words
  Action: WordCount
  Input: "Hello world, this is a test"
  Result: The text has 6 words

Step 2:
  Thought: I have the count
  Action: FINISH
  Answer: The text has 6 words
```

### 4. Advanced Agent Mode 🚀

**Best for**: Complex tasks, code execution, memory searches

**How it works**:
- Same as Basic Agent but with 11 total tools
- Can execute Python code
- Can search your memories
- Can work with JSON and dates

**When to use**:
- Complex calculations (factorial, etc.)
- Data processing
- When you need code execution
- Searching past conversations

**Available Tools** (all 11):
- All 6 basic tools PLUS:
- Memory Search
- Code Execution
- DateTime
- JSON Parser
- Web Search (placeholder)

**Example - Code Execution**:
```
You: What is the factorial of 7?

Step 1:
  Thought: Factorial requires multiplication, I'll use code
  Action: CodeExecution
  Input: "result = 1\nfor i in range(1, 8):\n    result *= i\nprint(result)"
  Result: Output: 5040

Step 2:
  Thought: I have the factorial
  Action: FINISH
  Answer: The factorial of 7 is 5040
```

**Example - Memory Search**:
```
You: Find my conversations about machine learning

Step 1:
  Thought: I need to search memories
  Action: MemorySearch
  Input: "machine learning"
  Result: Found 3 relevant memories:
          1. [92% match] "Tell me about machine learning"
          2. [85% match] "What is supervised learning?"
          3. [78% match] "Explain neural networks"

Step 2:
  Thought: I found relevant conversations
  Action: FINISH
  Answer: I found 3 conversations about machine learning...
```

---

## The Memory System

### How Memory Works

Archive-AI doesn't remember everything - it remembers **surprising** things.

**"Surprise Score" Explained**:

Every message gets scored on two factors:

1. **Perplexity** (60%): How unexpected is this to the AI?
   - "Hello" = Low surprise (predictable greeting)
   - "My favorite quantum physicist is Feynman" = High surprise (specific, unusual)

2. **Novelty** (40%): Is this different from existing memories?
   - First time mentioning Python = High novelty
   - 10th mention of Python = Low novelty

**Threshold**: Only messages scoring **≥ 0.7** are stored.

### What Gets Remembered?

**Usually Stored** ✅:
- Specific facts about you
- Unusual questions
- Technical discussions
- Detailed preferences
- Complex topics

**Usually NOT Stored** ❌:
- Generic greetings ("Hi", "Hello")
- Common questions ("What's 2+2?")
- Repetitive topics
- Simple chitchat

### Viewing Your Memories

**Option 1: Memory Browser** (Sidebar)

1. See total count at top
2. Scroll through all memories
3. Use search box to filter
4. Click any memory to see details

**Option 2: Ask the AI** (Chat mode):
```
You: What did I say about Python?
AI: I found these relevant memories:
    1. "Can you help me learn Python?" (95% match)
    2. "What's the best Python framework?" (88% match)
```

**Option 3: Advanced Agent**:
```
You: Search my memories for conversations about cooking

[Agent uses MemorySearch tool and returns results]
```

### Memory Details

Each stored memory includes:
- **Message**: The original text
- **Timestamp**: When it was said
- **Perplexity**: How surprising (higher = more surprising)
- **Surprise Score**: Final score (0.0-1.0)
- **Similarity**: How related to your search (when searching)

**Example Memory**:
```json
{
  "message": "I prefer React over Vue for frontend development",
  "timestamp": "2025-12-29 14:30:22",
  "perplexity": 95.66,
  "surprise_score": 0.949,
  "session": "default"
}
```

---

## Using Agents

### What Are Agents?

Agents are AI assistants that can:
1. **Think** about problems step-by-step
2. **Use tools** to get information or perform actions
3. **Reason** through complex tasks

### When to Use Agents

**Use Basic Agent** when you need:
- Math calculations
- Text analysis
- Simple problem-solving

**Use Advanced Agent** when you need:
- Code execution
- Complex calculations
- Memory searches
- Data processing

### Agent Workflow

Every agent follows this pattern:

```
1. THOUGHT: "What do I need to do?"
2. ACTION: [Choose a tool]
3. INPUT: [Provide input to tool]
4. OBSERVATION: [See tool result]
5. [Repeat 1-4 if needed]
6. THOUGHT: "I have the answer"
7. ACTION: FINISH
8. ANSWER: [Final response]
```

### Reading Agent Responses

**Compact View** (in chat):
```
Step 1: Used Calculator with input "15 * 23"
        Result: 345

Answer: 345
```

**Expanded View** (click to see details):
```
Step 1:
  💭 Thought: I need to multiply 15 by 23
  🔧 Action: Calculator
  📝 Input: "15 * 23"
  👁️ Observation: Result: 345

Step 2:
  💭 Thought: I have the answer
  ✅ Action: FINISH
  📝 Answer: 345
```

---

## Available Tools

### Basic Tools (6 tools)

#### 1. Calculator 🧮

**What it does**: Performs math calculations

**Supports**:
- Basic operations: `+`, `-`, `*`, `/`, `%`, `**`
- Functions: `sqrt(n)`, `abs(n)`
- Multi-operand: `100 + 200 + 50`

**Examples**:
```
You: Calculate 50 times 8
AI: Uses Calculator → Result: 400

You: What's the square root of 144?
AI: Uses Calculator → Result: 12.0

You: Add 150, 200, and 175
AI: Uses Calculator → Result: 525
```

#### 2. StringLength 📏

**What it does**: Counts characters in text

**Example**:
```
You: How many characters in "Hello World"?
AI: Uses StringLength → The text has 11 characters
```

#### 3. WordCount 📊

**What it does**: Counts words in text

**Example**:
```
You: How many words in "The quick brown fox"?
AI: Uses WordCount → The text has 4 words
```

#### 4. ReverseString ↩️

**What it does**: Reverses text

**Example**:
```
You: Reverse "Hello"
AI: Uses ReverseString → Reversed: olleH
```

#### 5. ToUppercase 🔤

**What it does**: Converts text to UPPERCASE

**Example**:
```
You: Make "hello world" uppercase
AI: Uses ToUppercase → Uppercase: HELLO WORLD
```

#### 6. ExtractNumbers 🔢

**What it does**: Finds all numbers in text

**Example**:
```
You: Find numbers in "I have 3 cats and 2 dogs"
AI: Uses ExtractNumbers → Found numbers: 3, 2
```

---

### Advanced Tools (5 additional tools)

#### 7. MemorySearch 🔍

**What it does**: Searches your conversation history

**When to use**:
- Finding past discussions
- Recalling specific information
- Connecting related topics

**Example**:
```
You: Find my conversations about programming

Agent:
  Step 1: Uses MemorySearch
          Query: "programming"
          Found 3 memories:
            1. [93% match] "Tell me about Python"
            2. [87% match] "How do I learn JavaScript?"
            3. [82% match] "Best coding practices"
```

**Tips**:
- Be specific in your query
- Use keywords from original conversation
- Results ranked by relevance

#### 8. CodeExecution 💻

**What it does**: Runs Python code in a secure sandbox

**Security**:
- No network access
- No file system access
- 10-second timeout
- Blocked dangerous modules

**What's Allowed**:
- Math operations
- Data structures (list, dict, set)
- Limited libraries: `math`, `random`, `datetime`, `json`

**Example - Factorial**:
```
You: Calculate factorial of 7

Agent:
  Step 1: Uses CodeExecution
          Code: result = 1
                for i in range(1, 8):
                    result *= i
                print(result)
          Output: 5040
          
  Answer: The factorial of 7 is 5040
```

**Example - Data Processing**:
```
You: Find the average of 10, 20, 30, 40, 50

Agent:
  Uses CodeExecution
  Code: numbers = [10, 20, 30, 40, 50]
        average = sum(numbers) / len(numbers)
        print(average)
  Output: 30.0
```

**Important**: Code MUST print() output!
```python
# ✅ GOOD - Prints result
result = 5 + 5
print(result)

# ❌ BAD - No output
result = 5 + 5
```

#### 9. DateTime ⏰

**What it does**: Gets current date/time

**Modes**:
- `now` - Full date and time
- `date` - Just the date
- `time` - Just the time
- `timestamp` - Unix timestamp
- `iso` - ISO 8601 format

**Examples**:
```
You: What's today's date?
AI: Uses DateTime("date") → 2025-12-29

You: What time is it?
AI: Uses DateTime("time") → 14:30:22

You: Get current timestamp
AI: Uses DateTime("timestamp") → 1735481422
```

#### 10. JSON 📋

**What it does**: Parses and validates JSON data

**Features**:
- Validates JSON syntax
- Pretty-prints JSON
- Extracts specific fields

**Example - Validation**:
```
You: Is this valid JSON? {"name": "Alice", "age": 30}

AI: Uses JSON
    Valid JSON object with 2 keys:
    {
      "name": "Alice",
      "age": 30
    }
```

**Example - Field Extraction**:
```
You: Extract "name" from {"name": "Bob", "age": 25}

AI: Uses JSON
    Input: name:{"name": "Bob", "age": 25}
    Extracted 'name': "Bob"
```

#### 11. WebSearch 🌐

**Status**: ⚠️ Not yet implemented (placeholder)

**Future capability**: Search the web for current information

---

## Advanced Features

### Chain of Verification

**What it is**: A 4-step process to reduce hallucinations

**The Process**:
1. **Generate**: Create initial answer
2. **Plan**: List verification questions
3. **Execute**: Answer verification questions independently
4. **Revise**: Check for contradictions, correct if needed

**When to use**:
- Fact-checking
- Important information
- When accuracy is critical

**Example**:
```
Question: "What is the boiling point of water?"

1. Initial Response:
   "Water boils at 100°C or 212°F at sea level"

2. Verification Questions:
   - Is 100°C the correct boiling point at sea level?
   - Does altitude affect boiling point?
   - Is 212°F equivalent to 100°C?

3. Verification Answers:
   - Yes, 100°C at standard pressure
   - Yes, lower pressure = lower boiling point
   - Yes, 212°F = 100°C

4. Final Response:
   "Verified: Water boils at 100°C (212°F) at sea level.
    At higher altitudes, it boils at lower temperatures."
   
   Status: ✅ No contradictions found
```

### Semantic Routing

**What it is**: Automatic detection of what you need

**Routes**:

1. **Help Route**:
   - Triggers: "help", "what can you do?", "?"
   - Response: Shows capability guide
   - Speed: Instant (no LLM call)

2. **Memory Search Route**:
   - Triggers: "remember", "what did I say", "find my conversation"
   - Action: Searches vector store
   - Returns: Relevant past messages

3. **Chat Route** (Default):
   - Everything else
   - Uses Vorpal for fast responses

**Examples**:
```
You: help
→ Routes to Help (instant response)

You: What did I say about Python?
→ Routes to MemorySearch (finds relevant memories)

You: Tell me a joke
→ Routes to Chat (normal conversation)
```

### Voice I/O (Optional)

**Not covered in this manual** - Voice features available but require audio setup.

See technical documentation for voice configuration.

---

## Tips & Tricks

### Getting Better Responses

**Be Specific**:
```
❌ "Tell me about science"
✅ "Explain how photosynthesis works"
```

**Use the Right Mode**:
- Quick facts → Chat mode
- Important facts → Verified mode
- Calculations → Basic Agent
- Complex tasks → Advanced Agent

**For Agents: Be Clear**:
```
❌ "Do some math"
✅ "Calculate the factorial of 7"
```

### Memory Management

**Make Things Memorable**:
- Be specific and detailed
- Share personal preferences
- Discuss unusual topics
- Use precise language

**Search Effectively**:
```
❌ "food"  (too vague)
✅ "Italian restaurants"  (specific)

❌ "coding"  (too broad)
✅ "Python web frameworks"  (focused)
```

### Agent Usage

**For Math**:
- Simple: Use Chat mode (may use calculator automatically)
- Complex: Use Advanced Agent with code execution

**For Text**:
- Simple: Ask in Chat mode
- Analysis: Use Basic Agent

**For Research**:
- Use Verified mode for fact-checking
- Use Advanced Agent for memory searches

### Performance

**Fast Responses**:
- Use Chat mode (Vorpal engine, GPU)
- Avoid complex multi-step tasks
- Keep messages concise

**Quality Over Speed**:
- Use Verified mode (thorough but slower)
- Use Advanced Agent (access to all tools)
- Enable code execution for complex math

---

## Common Questions

### Q: Why isn't my message being remembered?

**A**: Your message needs a surprise score ≥ 0.7

**What to do**:
- Make messages more specific
- Share unique information
- Discuss detailed topics

**Check**:
```bash
# View surprise scores in logs
docker-compose logs brain | grep "surprise"
```

### Q: How do I see what the AI is thinking?

**A**: Use Agent modes (Basic or Advanced)

Agent modes show:
- Thoughts
- Actions taken
- Tool inputs/outputs
- Reasoning process

### Q: Can I delete memories?

**A**: Yes, but requires manual database access

**How** (advanced):
```bash
# Connect to Redis
redis-cli

# List all memories
SCAN 0 MATCH memory:*

# Delete specific memory
DEL memory:1234567890
```

### Q: How do I change the AI model?

**A**: Edit `.env` file (see Owner's Manual)

### Q: Can I export my memories?

**A**: Yes, memories are in Redis

**How**:
```bash
# Backup all data
tar -czf memories-backup.tar.gz data/redis/

# Or use Redis dump
redis-cli SAVE
```

### Q: Why is Verified mode so slow?

**A**: It makes 4+ LLM calls (initial + verification questions + final)

**Trade-off**:
- Chat mode: Fast but may hallucinate
- Verified mode: Slow but more accurate

### Q: How many tools can agents use at once?

**A**: One tool per step, but unlimited steps (up to max_steps)

**Example**:
```
Step 1: Use Calculator
Step 2: Use CodeExecution
Step 3: Use MemorySearch
...
```

### Q: What happens if code execution fails?

**A**: The agent sees the error and can try again

**Example**:
```
Step 1:
  Action: CodeExecution
  Code: print(1/0)
  Result: Error: division by zero

Step 2:
  Thought: I need to fix the error
  Action: CodeExecution
  Code: print(1/2)
  Result: 0.5
```

### Q: Can I add custom tools?

**A**: Yes! See the Agent Tutorial in `/Docs/tutorials/AGENT_TUTORIAL.md`

### Q: How private is my data?

**A**: 100% private

- No cloud connection
- All processing local
- Data stored in `./data/redis/`
- You own everything

### Q: Can multiple people use it?

**A**: Yes, but:
- Memories shared across all users
- Use `session_id` to separate (advanced feature)
- No built-in authentication

---

## Appendix: Quick Reference

### Keyboard Shortcuts

- `Enter` - Send message
- `Shift + Enter` - New line (in text input)

### Chat Mode Examples

```
"Hello"                    → Normal chat
"help"                     → Shows help guide
"What did I say about X?"  → Searches memories
"What is 2+2?"             → Normal chat (may use tools)
```

### Agent Mode Examples

**Basic Agent**:
```
"Calculate 50 * 8"         → Uses Calculator
"Count words in [text]"    → Uses WordCount
"Reverse [text]"           → Uses ReverseString
```

**Advanced Agent**:
```
"What is factorial of 7?"         → Uses CodeExecution
"Find my Python conversations"    → Uses MemorySearch
"What's today's date?"            → Uses DateTime
"Validate this JSON: {...}"       → Uses JSON
```

### Status Indicators

**System Status**:
- 🟢 Green badge = Healthy
- 🟡 Yellow badge = Degraded  
- 🔴 Red badge = Unhealthy

**System Health**:
- CPU: Should be <20% when idle
- Memory: Depends on usage (<80% good)
- VRAM: Typically 75-85% (Vorpal model loaded)
- Tokens/sec: ~80-100 (varies by model)

---

## Getting Help

**In-App Help**:
```
Type: help
```

**Documentation**:
- User Manual: This document
- Owner's Manual: `OWNERS_MANUAL.md` (technical)
- Agent Tutorial: `/Docs/tutorials/AGENT_TUTORIAL.md`

**Logs** (for troubleshooting):
```bash
# View all logs
docker-compose logs -f

# View errors only
docker-compose logs brain | grep -i error
```

**API Documentation**:
```
http://localhost:8080/docs
```

---

**Enjoy using Archive-AI!** 🚀

Your AI assistant that never forgets, always stays private, and keeps getting smarter.
