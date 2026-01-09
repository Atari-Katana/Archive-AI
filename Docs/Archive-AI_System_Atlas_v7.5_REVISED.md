# Archive-AI: Unified System Atlas (v7.5 - REVISED)

**Architecture:** Hybrid Inference / Titans Memory / Redis-Native / LangGraph
**Status:** **Final Production Specification**
**Date:** December 2025
**Hardware Target:** Single NVIDIA RTX 5060 Ti (16GB VRAM) + 64GB System RAM

---

## I. Executive Summary

Archive-AI is a local-first cognitive framework designed for permanent memory retention and autonomous reasoning. It operates entirely on consumer hardware by leveraging a specialized **Hybrid Inference** stack.

**The v7.5 "Production" Architecture:**
We have optimized the system for stability on a single GPU:
1.  **One Database:** **Redis Stack** handles everything (Streams, Vectors, Library).
2.  **One Logic Graph:** **ReAct Agents** handle Reasoning and Tool Use.
3.  **Async Memory:** "Surprise Scoring" happens in the background to ensure zero latency.
4.  **Safety First:** Strict VRAM caps and a dedicated Docker Sandbox for code execution.

---

## II. The Dual-Engine Inference Layer

To prevent Out-Of-Memory (OOM) crashes on 16GB VRAM, we enforce strict partitioning.

### 1. Engine A: "Vorpal" (Speed & Perception)
* **Backend:** Custom `vLLM` fork.
* **Role:** Chat, Routing, and Perplexity Calculation.
* **VRAM Cap:** **3.5 GB** (Hard Limit).
* **Format:** **EXL2** (4.0bpw).
* **Status:** Always Resident in VRAM.
* **Performance:** ~60-80 tokens/second for chat.

### 2. Engine B: "Goblin" (Deep Thought)
* **Backend:** `llama.cpp` (Server Mode).
* **Role:** Reasoning, Coding, Entity Extraction.
* **VRAM Cap:** **10.0 GB** (Hard Limit).
* **Format:** **GGUF** (Q4_K_M).
* **Offloading:** Majority of layers fit in 10GB; minimal System RAM spillover.
* **Status:** llama.cpp server remains running; loads different model files on demand (30-60s swap time).
* **Performance:** ~15-30 tokens/second for complex reasoning.

**The Math:** 3.5GB (Vorpal) + 10.0GB (Goblin) = **13.5GB**.
* *Remaining 2.5GB is reserved for OS Desktop Manager and CUDA Context overhead.*

---

## III. The Redis-Native Memory System (Titans Architecture)

### 1. Hot Tier (Async Stream)
* **Structure:** `Redis Stream` (Key: `session:input_stream`).
* **The Fix:** We do **not** block the chat on memory processing.
    * *User Turn:* Input is immediately sent to Vorpal for a reply.
    * *Background Worker:* Simultaneously pulls input from Redis Stream to calculate Surprise Score.

### 2. The Titans "Surprise Metric"
A memory is stored only if it is "Surprising" (High Error Signal).

* **Step 1: Prediction Error (Perplexity)**
    * Vorpal (Llama-8B) calculates the log-probability of the user's text.
* **Step 2: Vector Distance (RedisVL)**
    * Query Redis for similar past memories.
* **Step 3: The Hybrid Score**
    * $$Score = (0.6 \times Perplexity) + (0.4 \times VectorDistance)$$
    * **Threshold:** $> 0.7$ moves to Warm Tier.
    * **Note:** These weights are initial estimates and should be tuned empirically during Phase 3.

### 3. Warm & Cold Tiers (Unified Vector Store)
* **Structure:** `RedisJSON` + `RediSearch`.
* **Safety:** Redis is configured with `maxmemory 20gb` and `allkeys-lru` eviction to prevent System RAM exhaustion during massive library ingestion.

---

## IV. The Library Engine (Redis-Powered)

* **Ingestion:** `archive-librarian` service watches `~/ArchiveAI/Library-Drop`.
* **Process:** OCR $\rightarrow$ Text Chunking $\rightarrow$ RedisJSON.
* **Chunking Strategy:**
    * **Chunk Size:** 250 tokens (down from 500 for better retrieval precision).
    * **Overlap:** 50 tokens (ensures context continuity across chunks).
* **Schema:** tagged with `type: library_book`.
* **Retrieval:** The Reasoning Engine uses hybrid search to query both `type: memory` and `type: library_book` in a single pass.

---

## V. Autonomy Layer (The API Sandbox)

We implement a "Microservice Sandbox" to ensure the container actually listens for code.

* **Service:** `archive-sandbox` (Docker).
* **Base Image:** `python:3.10-slim`.
* **Internal Server:**
    * The container runs a `FastAPI` wrapper on port 8000.
    * Endpoint: `POST /execute { "code": "print('hello')" }`.
* **Dockerfile Spec:**
    ```dockerfile
    FROM python:3.10-slim
    RUN pip install fastapi uvicorn requests pandas numpy
    COPY server.py /app/server.py
    # No root access, separate user
    RUN useradd -m sandboxuser
    USER sandboxuser
    CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
    ```
* **Security:** 
    * No external network access (isolated on `archive-net` bridge).
    * No volume mounts.
    * Only `archive-brain` service has network access to sandbox.

---

## VI. Orchestration (Unified ReAct)

### 1. Semantic Router (RedisVL)
* **Mechanism:** Intent patterns stored as vector embeddings in Redis vector index.
* **Library:** RedisVL provides both vector storage and semantic routing capabilities.
* **Flow:** 
    * User input is embedded and compared against stored route vectors.
    * Routing decision happens asynchronously in background worker.
    * Context updated for next turn, OR blocks on explicit "Help me" / tool-use requests.
* **Route Creation:**
    * Initial routes: Hand-crafted intent patterns (e.g., "memory query", "code execution", "library search").
    * Future: Routes can be expanded/refined based on usage patterns.

### 2. Agent Planning System (ReAct)
* **Architecture:** Multi-step reasoning with tool execution
* **Planning Loop:**
    1. **Task Decomposition:** DeepSeek-R1-Distill breaks complex queries into subtasks
    2. **Tool Selection:** Router identifies required tools (code execution, library search, web search, memory queries)
    3. **Execution:** ReAct agent orchestrates sequential or parallel tool calls
    4. **Observation:** Results fed back to reasoning model
    5. **Iteration:** Agent continues until task complete or max iterations (default: 10)

* **Available Tools:**
    * `execute_code` - Run Python in sandbox
    * `search_library` - Query document chunks via RedisVL
    * `search_memory` - Query past conversations
    * `search_web` - External knowledge retrieval (optional, requires network)
    * `store_artifact` - Save generated files to persistent storage

* **Safety Mechanisms:**
    * Max iterations cap prevents infinite loops
    * Tool execution timeout (30s per call)
    * Sandbox isolation for code execution
    * Human-in-the-loop for destructive operations (file deletion, external API calls)

### 3. Chain of Verification (CoV)
1.  **Draft:** DeepSeek-R1-Distill (Goblin) generates answer with chain-of-thought.
2.  **Critique:** Llama-3-8B (Vorpal) extracts factual claims from draft.
3.  **Verify:** Tool Node searches Redis Library/Web for supporting evidence.
4.  **Revise:** DeepSeek-R1-Distill rewrites if evidence contradicts draft.

---

## VII. Voice Integration Layer

### 1. Speech-to-Text (FastWhisper)
* **Backend:** `faster-whisper` (CPU-optimized)
* **Model:** `large-v3` or `medium.en` (user selectable)
* **Processing:** Real-time streaming with VAD (Voice Activity Detection)
* **Performance:** ~0.5-2 seconds latency depending on model size
* **Resource:** Runs on CPU, no GPU required

### 2. Text-to-Speech (XTTS-v5)
* **Backend:** Coqui XTTS v2 (XTTS-v5 if referring to a fork/variant)
* **Voice:** Sir Ian McKellen voice clone (custom trained)
* **Processing:** Async generation, streams audio back to client
* **Performance:** ~1-3 seconds to first audio chunk
* **Resource:** CPU inference (can use GPU if VRAM available, but not required)

### 3. Voice Service Architecture
* **Service:** `archive-voice` (Docker container)
* **Endpoints:**
    * `POST /transcribe` - Audio → Text
    * `POST /synthesize` - Text → Audio
* **Integration:** Archive-brain routes voice I/O through this service
* **Storage:** Temporary audio buffers in Redis (auto-expire after 60s)

---

## VIII. Presentation Layer (UI)

### 1. The "Engine Room" (Hardware Dashboard)
* **Visualizer:** Real-time VRAM chart showing the 13.5GB split (3.5GB Vorpal + 10GB Goblin).
* **Controls:**
    * **GGUF Layer Slider:** Manually tune `n_gpu_layers` for Goblin (if needed).
    * **Context Gauge:** Alert at 80% context usage.
    * **Model Swap:** Button to switch Goblin between Reasoning and Coding models.
    * **Voice Toggle:** Enable/disable voice mode.

### 2. The Model Hub
* **Features:**
    * **Compatibility Guard:** Blocks download of models > 12GB GGUF file size (safety buffer for Goblin).
    * **Format Sorter:** Auto-sorts `.gguf` to Goblin and `.safetensors` to Vorpal.
    * **VRAM Estimator:** Shows approximate VRAM usage for each model before loading.

---

## IX. Model Catalog (Verified List)

| Role | Model | Engine | Format | VRAM | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Scout** | `Llama-3-8B-Instruct-EXL2` (4.0bpw) | Vorpal | EXL2 | ~3.0GB | Chat, Routing, Perplexity |
| **Thinker** | `DeepSeek-R1-Distill-Qwen-14B` (Q4_K_M) | Goblin | GGUF | ~8.5GB | Reasoning, CoT, Agent Planning |
| **Coder** | `Qwen-2.5-Coder-14B-Instruct` (Q4_K_M) | Goblin | GGUF | ~8.0GB | Python, System Engineering |
| **Librarian** | `bge-reranker-v2-m3` | CPU | ONNX | N/A | Memory Retrieval Reranking |
| **Listener** | `faster-whisper-large-v3` | CPU | ONNX | N/A | Speech-to-Text |
| **Speaker** | `xtts-v2` (custom voice) | CPU | PyTorch | N/A | Text-to-Speech (Ian McKellen voice) |

**Model Swapping:**
* Goblin can swap between Thinker and Coder models on demand.
* Swap time: 30-60 seconds from NVMe SSD.
* Default: Thinker model loaded at startup.

---

## X. Infrastructure (Final Docker Stack)

```yaml
services:
  # 1. The State Engine (Redis Stack)
  redis:
    image: redis/redis-stack:latest
    command: redis-server --maxmemory 20gb --maxmemory-policy allkeys-lru --appendonly yes
    ports: ["6379:6379", "8002:8001"]
    volumes:
      - ./data/redis:/data
    deploy:
      resources:
        limits:
          memory: 24G  # Docker limit slightly higher than Redis config

  # 2. The Brain (Orchestrator)
  archive-brain:
    image: archive-ai/brain:v7.5
    depends_on: [redis, vorpal, goblin, sandbox, voice]
    environment:
      - REDIS_URL=redis://redis:6379
      - SANDBOX_URL=http://sandbox:8000
      - VOICE_URL=http://voice:8001
      - ASYNC_MEMORY=true
      - VORPAL_URL=http://vorpal:8000
      - GOBLIN_URL=http://goblin:8080
    networks:
      - archive-net

  # 3. The Code Sandbox (API Mode)
  sandbox:
    build: ./sandbox
    networks:
      - archive-net
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
    # No volumes! No external network! Safe execution only.

  # 4. Voice Services (Speech I/O)
  voice:
    image: archive-ai/voice:v7.5
    environment:
      - WHISPER_MODEL=large-v3
      - XTTS_VOICE=ian_mckellen
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./models/voice:/models
    networks:
      - archive-net
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'

  # 5. Engine A: Speed (Vorpal)
  vorpal:
    image: archive-ai/vorpal:latest
    environment:
      - GPU_MEMORY_UTILIZATION=0.22  # ~3.5GB of 16GB
      - MODEL_PATH=/models/Llama-3-8B-Instruct-EXL2-4.0bpw
    volumes:
      - ./models/vorpal:/models
    networks:
      - archive-net
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  # 6. Engine B: Capacity (Goblin)
  goblin:
    image: ghcr.io/ggerganov/llama.cpp:server-cuda
    environment:
      - LLAMA_ARG_N_GPU_LAYERS=38  # Tuned for 10GB limit on 14B models
      - LLAMA_ARG_CTX_SIZE=8192
    volumes:
      - ./models/goblin:/models
    networks:
      - archive-net
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  # 7. Library Ingestion Worker
  archive-librarian:
    image: archive-ai/librarian:v7.5
    depends_on: [redis]
    environment:
      - REDIS_URL=redis://redis:6379
      - WATCH_DIR=/library-drop
      - CHUNK_SIZE=250
      - CHUNK_OVERLAP=50
    volumes:
      - ~/ArchiveAI/Library-Drop:/library-drop
    networks:
      - archive-net

networks:
  archive-net:
    driver: bridge
    internal: true  # Sandbox isolation
```

---

## XI. Implementation Roadmap

### Phase 1: Infrastructure (Week 1)
1. **Build the Sandbox Container**
   - Implement FastAPI server with `/execute` endpoint.
   - Test basic code execution (print, simple math).
   - Verify no external network access.

2. **Launch Core Services**
   - Start `redis`, `vorpal`, `goblin`.
   - Verify Redis persistence and memory limits.

3. **VRAM Stress Test**
   - Load both models simultaneously.
   - Run sustained chat + reasoning workload.
   - Confirm total VRAM stays under 14GB.
   - Monitor for OOM errors.

**Success Criteria:**
- [ ] All containers running without crashes.
- [ ] VRAM usage stable at 13.5GB ± 0.5GB.
- [ ] Sandbox executes basic Python code.

### Phase 2: Logic Layer + Voice (Week 2)
1. **Implement Archive-Brain Core**
   - Set up ReAct agent with basic chat flow.
   - Connect to Vorpal for chat responses.
   - Implement Goblin model swapping logic.

2. **Build Async Memory Worker**
   - Redis Stream listener for input capture.
   - Perplexity calculation via Vorpal.
   - Vector similarity via RedisVL.
   - Surprise score computation and storage.

3. **Semantic Router Setup**
   - Create initial intent vector patterns in Redis.
   - Implement routing logic using RedisVL.
   - Test basic intent classification (chat vs. tool use).

4. **Voice Integration**
   - Build `archive-voice` container with FastWhisper + XTTS.
   - Implement `/transcribe` and `/synthesize` endpoints.
   - Test voice round-trip (speak → transcribe → respond → synthesize).
   - Verify latency acceptable (< 3 seconds total).

**Success Criteria:**
- [ ] Chat responses working via Vorpal.
- [ ] Memory scoring happens asynchronously.
- [ ] High-surprise inputs stored in Warm tier.
- [ ] Voice mode functional with acceptable latency.

### Phase 3: Integration, Agents & Tuning (Week 3)
1. **Library Ingestion**
   - Implement `archive-librarian` service.
   - Test OCR → chunking → Redis pipeline.
   - Perform "Library Drop" stress test (50+ documents).
   - Verify Redis memory cap holds.

2. **Agent Planning System**
   - Implement ReAct loop.
   - Connect all tools (code execution, library search, memory, web).
   - Test multi-step reasoning tasks:
     * "Analyze this dataset and create a visualization"
     * "Search the library for X, summarize findings, then generate a report"
     * "Debug this code by running it and fixing errors iteratively"
   - Verify max iteration caps and timeouts work.

3. **Chain of Verification**
   - Implement CoV logic.
   - Connect verification to Library search.
   - Test fact-checking on known false statements.

4. **Empirical Tuning**
   - Adjust Surprise Score weights (test 0.5/0.5, 0.7/0.3 variants).
   - Tune `n_gpu_layers` for Goblin if performance issues arise.
   - Optimize chunk overlap if retrieval quality poor.

**Success Criteria:**
- [ ] Library search returns relevant chunks.
- [ ] CoV catches hallucinations.
- [ ] Agent completes multi-step tasks without intervention.
- [ ] Memory system stabilizes over 100+ turns.

### Phase 4: UI & Polish (Week 4)
1. **Engine Room Dashboard**
   - Real-time VRAM visualization.
   - Context usage gauge.
   - Model swap controls.
   - Voice mode toggle.

2. **Model Hub**
   - VRAM estimator.
   - Compatibility checker.
   - One-click model loading.

3. **Final Testing**
   - Long conversation test (500+ turns).
   - Multi-modal workload (chat + library + code execution + voice).
   - Agent stress test (20+ complex multi-step tasks).
   - Edge case testing (OOM triggers, invalid code, missing models).

**Success Criteria:**
- [ ] System runs stable for 24+ hours.
- [ ] UI accurately reflects system state.
- [ ] All major features functional.
- [ ] Agent planning reliable for common tasks.

---

## XII. Known Risks & Mitigation

| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| VRAM overflow during peak usage | System crash | Hard limits in Docker + monitoring alerts |
| Model swap latency | Poor UX during transitions | Preload notification + progress bar |
| Redis memory exhaustion | Data loss | `allkeys-lru` eviction + 20GB hard cap |
| Surprise Score false negatives | Important memories missed | Empirical tuning of weights in Phase 3 |
| Sandbox escape | Security breach | No root, no network, separate user |
| Slow 14B model inference | User impatience | Set expectations: "Thinking..." indicator |
| Voice latency accumulation | Poor conversational flow | Async processing + streaming audio |
| XTTS voice quality | Uncanny valley effect | Custom voice training + quality testing |
| Agent infinite loops | System hangs | Max iteration cap (10) + timeout per tool (30s) |
| Agent destructive actions | Data loss | Human-in-the-loop for file deletion/external calls |

---

## XIII. Success Metrics

**Technical:**
- VRAM usage: 13.5GB ± 1GB under all workloads.
- Chat latency: < 2 seconds to first token (Vorpal).
- Reasoning latency: < 10 seconds to first token (Goblin).
- Voice round-trip: < 3 seconds (transcribe + think + synthesize).
- Memory persistence: 100% retention after Redis restarts.
- Library retrieval: Top-3 chunks relevant > 80% of queries.

**Functional:**
- System runs continuously for 7 days without intervention.
- No OOM crashes during normal usage.
- CoV catches > 90% of obvious hallucinations in test set.
- Agent completes 80% of multi-step tasks without human intervention.
- Voice mode maintains conversational flow (no awkward pauses > 5s).

---

## XIV. Post-Launch Considerations

**Not in Scope for v7.5:**
- Multi-GPU support (single GPU optimization only).
- Distributed deployment (single-machine only).
- Mobile app versions (desktop/web only).
- Real-time collaboration features.

**Future Optimizations (v8.0+):**
- **Speculative decoding for Goblin:** Potential 2x speedup for reasoning tasks. (Note: This has fallen off in past implementations—needs dedicated focus if prioritized.)
- Quantized embeddings for RedisVL (reduce memory footprint).
- Dynamic VRAM reallocation based on workload.
- Advanced agent capabilities: Multi-agent collaboration, long-term planning, hierarchical task decomposition.
- Voice cloning for custom user voices.
- Multilingual support (currently English-only).

---

**END OF SPECIFICATION**
