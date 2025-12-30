# Archive-AI User's Manual

**Version:** 7.5
**Last Updated:** 2025-12-29
**For:** End Users

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is Archive-AI?](#what-is-archive-ai)
3. [Getting Started](#getting-started)
4. [Using the Web Interface](#using-the-web-interface)
5. [Using the API](#using-the-api)
6. [Chat Modes](#chat-modes)
7. [Memory System](#memory-system)
8. [Library System](#library-system)
9. [Agents](#agents)
10. [Voice Features](#voice-features)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Introduction

Welcome to Archive-AI! This manual will help you understand and use Archive-AI effectively, whether you're having conversations, conducting research, generating code, or exploring your conversation history.

---

## What is Archive-AI?

Archive-AI is a **local-first AI companion** that runs entirely on your own hardware. Unlike cloud-based AI services, all your conversations and data stay on your machine.

### Key Features

- **Permanent Memory** - Remembers important conversations using "Surprise Score" filtering
- **Multiple Chat Modes** - Choose from standard chat, verified responses, or agent-based problem solving
- **Research Assistant** - Search through your documents and conversation history
- **Code Assistant** - Generate, test, and debug Python code automatically
- **Voice Interaction** - Speak to Archive-AI and hear responses (optional)
- **Document Library** - Index and search your PDF, text, and markdown files
- **Privacy First** - All processing happens locally, nothing sent to external servers

### System Requirements

Archive-AI requires the following to run:
- Access to a system where Archive-AI is installed
- Web browser (Chrome, Firefox, Safari, or Edge)
- Network access to the Archive-AI server (http://localhost:8080 for local installations)

---

## Getting Started

### Accessing Archive-AI

**Web Interface:**
1. Open your web browser
2. Navigate to http://localhost:8888
3. The Archive-AI dashboard will load

**API Access:**
- Base URL: http://localhost:8080
- API Documentation: http://localhost:8080/docs (interactive Swagger UI)
- Alternative Docs: http://localhost:8080/redoc (ReDoc format)

### First Steps

1. **Test the system** - Try a simple chat message like "Hello, how are you?"
2. **Check system health** - Look at the dashboard to see service status
3. **Browse your memories** - Open the Memory Browser to see what's been stored
4. **Try an agent** - Ask a math question in Agent mode

---

## Using the Web Interface

The web interface has four main sections:

### 1. Mode Selection

Choose your interaction mode with the buttons at the top:

- **Chat** - Standard conversation with Vorpal (fast responses)
- **Verified** - Chain of Verification mode (reduces hallucinations)
- **Basic Agent** - ReAct agent with 6 basic tools
- **Advanced Agent** - ReAct agent with all 11 tools

### 2. Input Area

- Type your message or question in the text box
- Click "Send" or press Enter to submit
- Clear button erases your input

### 3. Response Display

Responses appear in the chat area with:
- **Your message** displayed first
- **AI response** below it
- **Agent reasoning** (in agent modes) showing thought process
- **Tool usage** statistics for agent interactions

### 4. Sidebar Panels

**System Status:**
- Service health indicators (green = healthy)
- CPU and memory usage
- Uptime counter
- Total memories stored

**Memory Browser:**
- Search your stored memories
- Click memories to see details
- View surprise scores and timestamps

**Health Dashboard:**
- Real-time system metrics
- Service connectivity status
- Auto-refreshes every 5 seconds

---

## Using the API

Archive-AI provides a comprehensive REST API for programmatic access.

### API Documentation

Visit http://localhost:8080/docs for interactive documentation where you can:
- See all available endpoints
- Test endpoints directly in your browser
- View request/response schemas
- Copy curl commands

### Quick API Examples

**Chat Request:**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is quantum computing?"}'
```

**Memory Search:**
```bash
curl -X POST http://localhost:8080/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 5}'
```

**Research Question:**
```bash
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Explain transformer architecture",
    "use_library": true,
    "use_memory": true,
    "top_k": 5
  }'
```

**Code Generation:**
```bash
curl -X POST http://localhost:8080/code_assist \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a function to check if a number is prime",
    "max_attempts": 3
  }'
```

---

## Chat Modes

### Standard Chat Mode

**What it does:** Direct conversation with Vorpal, the fast inference engine.

**When to use:**
- Quick questions
- General conversation
- Brainstorming
- Creative writing

**How it works:**
1. Your message is sent to Vorpal (Qwen 2.5-3B or 7B model)
2. Response is generated and returned
3. Interaction is captured in the memory system
4. High-surprise conversations are automatically remembered

**Example interactions:**
- "Tell me a story about a space explorer"
- "What's the difference between Java and JavaScript?"
- "Help me brainstorm business names"

---

### Verified Chat Mode

**What it does:** Uses Chain of Verification to reduce hallucinations and improve accuracy.

**When to use:**
- Fact-checking required
- Important decisions
- Technical explanations
- Historical or scientific questions

**How it works (4 stages):**
1. **Generate** - Create initial response
2. **Plan** - Develop verification questions
3. **Execute** - Answer verification questions independently
4. **Revise** - Update response if inconsistencies found

**What you get:**
- Initial response
- List of verification questions
- Verification answers
- Final (potentially revised) response
- Boolean flag indicating if revision occurred

**Example interactions:**
- "When was the Eiffel Tower completed?" (dates are verified)
- "What are the side effects of ibuprofen?" (medical facts verified)
- "How does HTTPS encryption work?" (technical details verified)

---

### Basic Agent Mode

**What it does:** Uses ReAct pattern (Reasoning + Acting) with 6 basic tools.

**Available Tools:**
1. **Calculator** - Performs math operations (+, -, *, /, sqrt, abs)
2. **StringLength** - Counts characters in text
3. **WordCount** - Counts words in text
4. **ReverseString** - Reverses text
5. **ToUppercase** - Converts text to uppercase
6. **ExtractNumbers** - Finds numbers in text

**When to use:**
- Math problems
- Text analysis
- Multi-step calculations
- Simple data processing

**How it works:**
1. Agent receives your question
2. Thinks about what to do (Thought)
3. Chooses a tool (Action)
4. Executes the tool (Observation)
5. Repeats until answer found (max 10 steps)

**Example interactions:**
- "Calculate 15 * 27 + 89"
- "How many words are in 'The quick brown fox jumps over the lazy dog'?"
- "Extract all numbers from 'Order #12345 costs $67.89'"

**Viewing agent reasoning:**
- Click "Show Steps" to see the agent's thought process
- Each step shows: thought → action → observation
- Success indicator shows if the task completed

---

### Advanced Agent Mode

**What it does:** All basic tools PLUS 5 advanced capabilities.

**Additional Tools:**
7. **MemorySearch** - Search stored conversation memories
8. **CodeExecution** - Run Python code in a secure sandbox
9. **DateTime** - Get current date and time in various formats
10. **JSON** - Parse and validate JSON data
11. **WebSearch** - (Placeholder for future web search capability)

**When to use:**
- Complex computational problems
- Problems requiring memory recall
- Time-sensitive questions
- Data structure work
- Custom calculations beyond basic math

**Example interactions:**
- "Search my memories for discussions about machine learning, then tell me the current time"
- "Write Python code to calculate fibonacci(10) and run it"
- "Parse this JSON and tell me the value of 'name': {\"name\": \"Alice\", \"age\": 30}"

**Important notes:**
- Code execution runs in a **secure sandbox** (no file system or network access)
- Code must include `print()` statements to show results
- Maximum execution time: 10 seconds (configurable 1-30s)
- Memory search returns top 3 most relevant memories

---

## Memory System

Archive-AI automatically remembers important conversations using a "Surprise Score" metric.

### How Memory Works

**Automatic Storage:**
- Every message you send is analyzed
- System calculates:
  - **Perplexity** - How unexpected the text is (60% weight)
  - **Novelty** - How different from existing memories (40% weight)
- **Surprise Score** = 0.6 × perplexity + 0.4 × novelty
- Messages scoring ≥ 0.7 are permanently stored

**What gets remembered:**
- Novel questions you haven't asked before
- Complex or unusual requests
- Unexpected conversation topics
- Technical or specialized queries

**What doesn't get remembered:**
- Common greetings ("hello", "thanks")
- Repetitive questions
- Very short messages
- Predictable responses

### Browsing Your Memories

**Via Web Interface:**
1. Open the Memory Browser in the sidebar
2. See all stored memories (newest first)
3. Click any memory to view details:
   - Full message text
   - Surprise score
   - Timestamp
   - Perplexity value

**Via API:**
```bash
# List all memories
curl http://localhost:8080/memories?limit=50

# Search memories semantically
curl -X POST http://localhost:8080/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python", "top_k": 10}'
```

### Memory Search

**Semantic search** finds memories by meaning, not just keywords:
- "coding help" finds memories about programming, development, debugging
- "math problems" finds memories about calculations, algebra, equations
- Uses 384-dimensional vector embeddings
- Returns similarity scores (0.0 = identical, 1.0 = completely different)

**Search tips:**
- Use descriptive phrases, not single words
- Ask questions similar to your original queries
- Similarity scores < 0.3 are highly relevant
- Similarity scores > 0.7 may not be useful

### Memory Archival

**Automatic archival** keeps the system performant:
- Memories older than 30 days are archived to disk
- Archives stored in: `data/archive/YYYY-MM/memories-YYYYMMDD.json`
- 1,000 most recent memories kept in fast storage (Redis)
- Runs daily at 3:00 AM
- Archived memories searchable via admin API

**Manual archival trigger:**
```bash
curl -X POST http://localhost:8080/admin/archive_old_memories
```

---

## Library System

The Library feature lets you upload documents and search them later.

### Adding Documents

**Drop files in the watch folder:**
```bash
~/ArchiveAI/Library-Drop/
```

**Supported formats:**
- PDF files (.pdf) - Text extraction with OCR fallback
- Plain text (.txt)
- Markdown (.md)

**Processing:**
- Files are automatically detected and processed
- Text is chunked into 250-token segments (50-token overlap)
- Each chunk is embedded and indexed
- Original files are not modified

### Searching Your Library

**Via API:**
```bash
curl -X POST http://localhost:8080/library/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "top_k": 5
  }'
```

**Response includes:**
- Matching text chunks
- Source filename
- Chunk position (e.g., "chunk 3 of 10")
- Similarity score and percentage
- Token count

**Get library statistics:**
```bash
curl http://localhost:8080/library/stats
```

Returns:
- Total chunks indexed
- Number of unique files
- List of all filenames

---

## Agents

Archive-AI includes specialized agents for different tasks.

### Research Assistant

**What it does:** Combines library search and memory search to answer questions with citations.

**Endpoint:** `POST /research`

**Features:**
- Searches your document library
- Searches conversation memories
- Synthesizes information from multiple sources
- Provides citations for each claim

**Example:**
```bash
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is HNSW indexing?",
    "use_library": true,
    "use_memory": true,
    "top_k": 5
  }'
```

**Response includes:**
- Synthesized answer
- List of sources (library chunks + memories)
- Number of library chunks consulted
- Number of memories consulted
- Citations in [Source N] format

**Multi-question research:**
```bash
curl -X POST http://localhost:8080/research/multi \
  -H "Content-Type: application/json" \
  -d '{
    "questions": [
      "What is HNSW?",
      "How does cosine similarity work?",
      "What are vector embeddings?"
    ],
    "synthesize": true
  }'
```

Answers each question separately, then provides a synthesis combining all findings.

### Code Assistant

**What it does:** Generates Python code, tests it automatically, and debugs if needed.

**Endpoint:** `POST /code_assist`

**Features:**
- Generates code from natural language descriptions
- Executes code in secure sandbox
- Auto-detects errors
- Debugs and retries up to 3 times
- Returns working code with explanations

**Example:**
```bash
curl -X POST http://localhost:8080/code_assist \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a function to calculate fibonacci numbers recursively, then test it with n=10",
    "max_attempts": 3,
    "timeout": 10
  }'
```

**Response includes:**
- Generated Python code
- Code explanation
- Test output (if code ran successfully)
- Success status
- Number of attempts needed
- Error message (if failed)

**Supported tasks:**
- Function definitions
- Algorithm implementations
- Data structure operations
- Mathematical calculations
- Text processing

**Limitations:**
- Python only
- No file system access
- No network access
- No external libraries (only built-ins: math, random, etc.)
- 10-second default timeout (configurable 1-30s)

---

## Voice Features

Archive-AI supports voice input and output (when enabled).

### Speech-to-Text (STT)

**Engine:** Faster-Whisper

**Supported audio formats:**
- WAV, MP3, M4A, FLAC, OGG, Opus

**Usage:**
```bash
curl -X POST http://localhost:8001/transcribe \
  -F "audio=@recording.wav"
```

**Features:**
- Automatic language detection
- Voice activity detection
- Optimized for CPU inference
- Multiple model sizes (tiny, base, small, medium, large)

### Text-to-Speech (TTS)

**Engine:** F5-TTS (neural text-to-speech)

**Usage:**
```bash
curl -X POST http://localhost:8001/synthesize \
  -F 'text=Hello, this is Archive-AI speaking.'
```

**Output:** WAV audio file

**Features:**
- Natural voice synthesis
- Voice cloning capability (with reference audio)
- CPU or GPU acceleration

---

## Best Practices

### Getting Accurate Responses

1. **Be specific** - "Calculate the area of a circle with radius 5" vs "circle area"
2. **Use Verified mode** for facts - Dates, scientific claims, technical specs
3. **Break down complex questions** - Multi-part questions work better as separate queries
4. **Use agents for computation** - Don't ask the LLM to do math, use the Calculator tool

### Working with Memory

1. **Unique phrasing** helps storage - Novel questions are more likely to be remembered
2. **Search semantically** - Use natural language, not keywords
3. **Check memory browser** before asking - Your question might already be answered
4. **Important info gets remembered** - Don't worry about saving everything manually

### Using Agents Effectively

1. **Basic vs Advanced** - Use basic agent for simple tasks (faster, more reliable)
2. **Check reasoning steps** - If agent fails, review the step-by-step trace
3. **Code execution tips**:
   - Always include `print()` to see output
   - Keep code simple and focused
   - Test complex logic manually first

### Library Management

1. **Organize before uploading** - Name files descriptively
2. **One topic per document** - Easier to search later
3. **Use markdown headers** - Helps chunking find logical sections
4. **PDF quality matters** - Clear text extracts better than scans

---

## Troubleshooting

### Common Issues

**"Service unavailable" errors:**
- Check that Archive-AI is running: `docker compose ps`
- Verify services are healthy: http://localhost:8080/health
- Wait 30 seconds after startup for models to load

**No response from chat:**
- Check browser console for errors (F12)
- Try the API directly: `curl http://localhost:8080/health`
- Restart the brain service: `docker compose restart brain`

**Memory not being stored:**
- Check surprise scores in memory browser
- Most messages score < 0.7 (this is normal)
- Try more unique or complex questions
- View memory worker logs: `docker compose logs brain | grep MemoryWorker`

**Agent gets stuck or fails:**
- Review reasoning steps to see where it failed
- Try rephrasing your question
- Use fewer steps in complex tasks
- Check agent mode (basic vs advanced) matches your needs

**Library search returns nothing:**
- Confirm files were processed: `curl http://localhost:8080/library/stats`
- Check Librarian logs: `docker compose logs librarian`
- Verify files are in watch folder: `ls ~/ArchiveAI/Library-Drop/`
- Try different search terms (semantic search, not keyword matching)

**Slow responses:**
- GPU mode is significantly faster than CPU
- Vorpal (chat) is faster than Goblin (reasoning)
- Reduce agent max_steps for faster (but less thorough) results
- Check system resources: http://localhost:8080/metrics

### Getting Help

**System health check:**
```bash
curl http://localhost:8080/health
curl http://localhost:8080/metrics
```

**View service logs:**
```bash
docker compose logs brain
docker compose logs vorpal
docker compose logs librarian
```

**Check VRAM usage:**
```bash
nvidia-smi
```

**Test individual services:**
```bash
# Vorpal
curl http://localhost:8000/health

# Redis
docker exec archive-ai-redis-1 redis-cli PING

# Sandbox
curl http://localhost:8003/health
```

---

## Appendix: Quick Reference

### Web Interface URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Web UI | http://localhost:8888 | Main user interface |
| API Docs | http://localhost:8080/docs | Interactive API documentation |
| ReDoc | http://localhost:8080/redoc | Alternative API docs |
| Health Check | http://localhost:8080/health | System status |
| Metrics | http://localhost:8080/metrics | Resource usage |
| Redis Insight | http://localhost:8002 | Database viewer |

### API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Standard conversation |
| `/verify` | POST | Verified conversation (Chain of Verification) |
| `/agent` | POST | Basic ReAct agent (6 tools) |
| `/agent/advanced` | POST | Advanced ReAct agent (11 tools) |
| `/memories` | GET | List stored memories |
| `/memories/search` | POST | Semantic memory search |
| `/library/search` | POST | Search document library |
| `/library/stats` | GET | Library statistics |
| `/research` | POST | Research assistant (single question) |
| `/research/multi` | POST | Multi-question research |
| `/code_assist` | POST | Code generation and testing |

### Configuration Defaults

| Setting | Default | Purpose |
|---------|---------|---------|
| Surprise threshold | 0.7 | Minimum score for memory storage |
| Memory keep count | 1,000 | Recent memories in hot storage |
| Archive age | 30 days | Age threshold for cold storage |
| Agent max steps | 10 | Maximum reasoning iterations |
| Code timeout | 10s | Sandbox execution limit |
| Library chunk size | 250 tokens | Document chunking size |
| Chunk overlap | 50 tokens | Overlap between chunks |
| Memory search top-k | 10 | Default search results |
| Library search top-k | 5 | Default library results |

---

**End of User's Manual**

For technical details and system administration, see the **Owner's Manual**.
For building custom agents, see the **Agent Manual**.
For installation and operations, see the **Go Manual**.
