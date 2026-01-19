# Archive-AI v7.5 Implementation Plan
## Bite-Sized Chunks with Checkpoints

**Philosophy:** Each chunk is 1-3 files, independently testable, with clear pass/fail criteria.

---

## PHASE 1: INFRASTRUCTURE (Week 1)

### Chunk 1.1: Redis Stack Setup
**Files:** `docker-compose.yml` (partial), `scripts/test-redis.py`

**Task:**
- Create base `docker-compose.yml` with Redis Stack service only
- Configure memory limits and persistence
- Write test script to verify Redis Stack is running and RedisJSON/RediSearch modules loaded

**Test:**
```bash
docker-compose up -d redis
python scripts/test-redis.py
```

**Pass Criteria:**
- Redis responds to ping
- RedisJSON commands work (`JSON.SET`, `JSON.GET`)
- RediSearch index creation works
- Memory limit enforced (check with `INFO memory`)

**CHECKPOINT:** `checkpoints/checkpoint-1.1-redis.md`

---

### Chunk 1.2: Code Sandbox Container
**Files:** `sandbox/server.py`, `sandbox/Dockerfile`, `sandbox/requirements.txt`

**Task:**
- Create FastAPI server with single `/execute` endpoint
- Implement basic Python code execution
- Create Dockerfile with non-root user
- Test code execution isolation

**Test:**
```bash
docker build -t archive-ai/sandbox:test ./sandbox
docker run -p 8000:8000 archive-ai/sandbox:test
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(2+2)"}'
```

**Pass Criteria:**
- Server responds with `{"result": "4", "status": "success"}`
- Invalid code returns error without crashing
- Container runs as non-root user (check with `docker exec`)

**CHECKPOINT:** `checkpoints/checkpoint-1.2-sandbox.md`

---

### Chunk 1.3: Vorpal Engine Setup
**Files:** `vorpal/Dockerfile`, `vorpal/config.yaml`, `docker-compose.yml` (update)

**Task:**
- Create Vorpal container using vLLM
- Configure GPU memory utilization to 0.22 (3.5GB cap)
- Add placeholder model config (will use actual model in testing)
- Add Vorpal service to docker-compose

**Test:**
```bash
# Place test model in ./models/vorpal/
docker-compose up -d vorpal
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "test", "prompt": "Hello", "max_tokens": 10}'
```

**Pass Criteria:**
- Container starts without OOM
- VRAM usage ~3-3.5GB (check with `nvidia-smi`)
- API responds to completion requests

**CHECKPOINT:** `checkpoints/checkpoint-1.3-vorpal.md`

---

### Chunk 1.4: Goblin Engine Setup
**Files:** `goblin/start.sh`, `docker-compose.yml` (update)

**Task:**
- Configure llama.cpp server in docker-compose
- Set `n_gpu_layers=38` for 14B models
- Add volume mount for model directory
- Test with placeholder GGUF model

**Test:**
```bash
# Place test GGUF in ./models/goblin/
docker-compose up -d goblin
curl http://localhost:8081/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test", "n_predict": 10}'
```

**Pass Criteria:**
- Container starts without OOM
- VRAM usage ~8-10GB (check with `nvidia-smi`)
- API responds to completion requests
- Total VRAM (Vorpal + Goblin) < 14GB

**CHECKPOINT:** `checkpoints/checkpoint-1.4-goblin.md`

---

### Chunk 1.5: VRAM Stress Test
**Files:** `scripts/vram-stress-test.py`

**Task:**
- Write script that hammers both engines simultaneously
- Monitor VRAM usage over 10-minute period
- Log any OOM warnings or crashes

**Test:**
```bash
docker-compose up -d redis vorpal goblin
python scripts/vram-stress-test.py --duration 600
```

**Pass Criteria:**
- No OOM crashes
- VRAM stays between 13-14.5GB
- Both engines respond throughout test
- No memory leaks (usage stable over time)

**CHECKPOINT:** `checkpoints/checkpoint-1.5-vram-test.md`

---

## PHASE 2: LOGIC LAYER + VOICE (Week 2)

### Chunk 2.1: Archive-Brain Core (Minimal)
**Files:** `brain/main.py`, `brain/config.py`, `brain/requirements.txt`, `brain/Dockerfile`

**Task:**
- Create minimal FastAPI server for brain orchestrator
- Single endpoint: `POST /chat` that proxies to Vorpal
- No memory, no routing, just pass-through
- Add to docker-compose

**Test:**
```bash
docker-compose up -d brain
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

**Pass Criteria:**
- Brain receives message
- Forwards to Vorpal
- Returns Vorpal response
- No errors in logs

**CHECKPOINT:** `checkpoints/checkpoint-2.1-brain-minimal.md`

---

### Chunk 2.2: Redis Stream Input Capture
**Files:** `brain/stream_handler.py`, `brain/main.py` (update)

**Task:**
- Add Redis Stream writer to capture all inputs
- Store in `session:input_stream`
- Non-blocking (fire and forget)
- Test with manual Redis inspection

**Test:**
```bash
curl -X POST http://localhost:8081/chat -d '{"message": "Test"}'
redis-cli XREAD COUNT 1 STREAMS session:input_stream 0
```

**Pass Criteria:**
- Input appears in Redis Stream
- Chat response still immediate (not blocked)
- Stream entries have timestamp and message

**CHECKPOINT:** `checkpoints/checkpoint-2.2-stream-capture.md`

---

### Chunk 2.3: Async Memory Worker (Perplexity Only)
**Files:** `brain/workers/memory_worker.py`, `brain/main.py` (update)

**Task:**
- Create background worker that reads from Redis Stream
- Calculate perplexity using Vorpal API
- Log perplexity scores (don't store yet)
- Run as separate thread/process

**Test:**
```bash
# Send messages, watch logs for perplexity scores
curl -X POST http://localhost:8081/chat -d '{"message": "The sky is blue"}'
curl -X POST http://localhost:8081/chat -d '{"message": "Flibbertigibbet zamboni"}'
# Check logs for different perplexity values
```

**Pass Criteria:**
- Worker processes stream entries
- Perplexity calculated for each input
- Common phrases = lower perplexity
- Nonsense = higher perplexity
- Chat still responsive

**CHECKPOINT:** `checkpoints/checkpoint-2.3-perplexity-worker.md`

---

### Chunk 2.4: RedisVL Vector Storage
**Files:** `brain/memory/vector_store.py`, `brain/memory/schema.yaml`

**Task:**
- Set up RedisVL schema for memory embeddings
- Create functions: `store_memory()`, `search_similar()`
- Use sentence-transformers for embeddings (CPU)
- Test with manual memory insertion

**Test:**
```python
from brain.memory.vector_store import store_memory, search_similar

store_memory("I love pizza", embedding_vector, {"type": "memory"})
store_memory("Pizza is delicious", embedding_vector, {"type": "memory"})
results = search_similar("What food do I like?")
# Should return pizza-related memories
```

**Pass Criteria:**
- Memories stored in Redis with vectors
- Similarity search returns relevant results
- RedisVL index created correctly
- No memory leaks from embedding model

**CHECKPOINT:** `checkpoints/checkpoint-2.4-vector-store.md`

---

### Chunk 2.5: Complete Surprise Scoring
**Files:** `brain/workers/memory_worker.py` (update)

**Task:**
- Add vector similarity check to memory worker
- Compute hybrid score: `0.6*perplexity + 0.4*vector_distance`
- Store memories with score > 0.7 in vector store
- Log decisions (stored vs. discarded)

**Test:**
```bash
# Send repeated messages, check if second is ignored
curl -X POST http://localhost:8081/chat -d '{"message": "I like coffee"}'
curl -X POST http://localhost:8081/chat -d '{"message": "I like coffee"}'
# Second should have low surprise score, not stored

# Send novel message
curl -X POST http://localhost:8081/chat -d '{"message": "I hate sardines"}'
# Should have high surprise score, stored
```

**Pass Criteria:**
- Repeated inputs score low (< 0.7)
- Novel inputs score high (> 0.7)
- Only high-surprise memories stored
- Chat latency unaffected

**CHECKPOINT:** `checkpoints/checkpoint-2.5-surprise-scoring.md`

---

### Chunk 2.6: Semantic Router (Basic)
**Files:** `brain/router/semantic_router.py`, `brain/router/routes.yaml`

**Task:**
- Create initial route patterns (chat, memory_query, code_execution)
- Store routes as vectors in Redis
- Implement route matching function
- Add to brain endpoint (classify intent, log result)

**Test:**
```bash
curl -X POST http://localhost:8081/chat -d '{"message": "Hello how are you"}'
# Logs: route=chat

curl -X POST http://localhost:8081/chat -d '{"message": "What did I say about pizza?"}'
# Logs: route=memory_query

curl -X POST http://localhost:8081/chat -d '{"message": "Run this code: print(hello)"}'
# Logs: route=code_execution
```

**Pass Criteria:**
- Routing patterns loaded into Redis
- Intent classification works
- High accuracy on test set (>80%)
- No routing for ambiguous queries (falls back to chat)

**CHECKPOINT:** `checkpoints/checkpoint-2.6-semantic-router.md`

---

### Chunk 2.7: Voice Service - FastWhisper
**Files:** `voice/server.py`, `voice/transcribe.py`, `voice/Dockerfile`, `voice/requirements.txt`

**Task:**
- Create FastAPI server with `/transcribe` endpoint
- Implement FastWhisper integration (large-v3 model)
- Accept audio bytes, return text
- Add to docker-compose

**Test:**
```bash
docker-compose up -d voice
curl -X POST http://localhost:8001/transcribe \
  -F "audio=@test_audio.wav"
# Returns: {"text": "This is a test"}
```

**Pass Criteria:**
- Whisper model loads on CPU
- Audio transcription accurate (test with known samples)
- Latency < 2 seconds for 5-second clips
- Memory usage < 4GB

**CHECKPOINT:** `checkpoints/checkpoint-2.7-voice-whisper.md`

---

### Chunk 2.8: Voice Service - XTTS
**Files:** `voice/synthesize.py`, `voice/server.py` (update)

**Task:**
- Add XTTS-v2 integration
- Create `/synthesize` endpoint (text → audio)
- Load custom Ian McKellen voice
- Return audio bytes

**Test:**
```bash
curl -X POST http://localhost:8001/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "You shall not pass", "voice": "ian_mckellen"}' \
  --output test_output.wav
# Play audio, verify quality
```

**Pass Criteria:**
- Voice clone loaded
- Audio quality acceptable (no artifacts)
- Latency < 3 seconds for 20-word sentence
- Memory usage stable

**CHECKPOINT:** `checkpoints/checkpoint-2.8-voice-xtts.md`

---

### Chunk 2.9: Voice Round-Trip Integration
**Files:** `brain/main.py` (update), `brain/voice_handler.py`

**Task:**
- Add `/voice_chat` endpoint to brain
- Pipeline: transcribe → chat → synthesize
- Return audio response
- Measure total latency

**Test:**
```bash
curl -X POST http://localhost:8081/voice_chat \
  -F "audio=@question.wav" \
  --output response.wav
# Play response, verify it answers the question
```

**Pass Criteria:**
- Full pipeline works
- Total latency < 5 seconds
- Audio quality preserved
- No race conditions or deadlocks

**CHECKPOINT:** `checkpoints/checkpoint-2.9-voice-roundtrip.md`

---

## PHASE 3: INTEGRATION, AGENTS & TUNING (Week 3)

### Chunk 3.1: Library Ingestion - File Watcher
**Files:** `librarian/watcher.py`, `librarian/Dockerfile`, `librarian/requirements.txt`

**Task:**
- Watch `~/ArchiveAI/Library-Drop` for new files
- Trigger processing on file creation
- Support PDF, TXT, MD files
- Add to docker-compose

**Test:**
```bash
docker-compose up -d librarian
echo "Test document" > ~/ArchiveAI/Library-Drop/test.txt
# Check logs for processing trigger
```

**Pass Criteria:**
- File changes detected
- Processing triggered automatically
- Handles multiple simultaneous files
- No crashes on invalid files

**CHECKPOINT:** `checkpoints/checkpoint-3.1-library-watcher.md`

---

### Chunk 3.2: Library Ingestion - OCR & Chunking
**Files:** `librarian/processor.py`, `librarian/chunker.py`

**Task:**
- OCR for PDFs (using Tesseract)
- Text extraction for TXT/MD
- Chunk into 250-token pieces with 50-token overlap
- Add metadata (filename, chunk index, type)

**Test:**
```python
from librarian.processor import process_document

result = process_document("test.pdf")
# Returns list of chunks with metadata
assert all(chunk['tokens'] <= 250 for chunk in result)
assert result[0]['chunk_index'] == 0
```

**Pass Criteria:**
- PDFs correctly OCR'd
- Text files processed
- Chunk sizes within spec
- Overlap preserved
- Metadata complete

**CHECKPOINT:** `checkpoints/checkpoint-3.2-library-processing.md`

---

### Chunk 3.3: Library Ingestion - Redis Storage
**Files:** `librarian/storage.py`, `librarian/watcher.py` (update)

**Task:**
- Store chunks in RedisVL with embeddings
- Tag with `type: library_book`
- Create search index for library content
- Complete end-to-end pipeline

**Test:**
```bash
cp sample_doc.pdf ~/ArchiveAI/Library-Drop/
# Wait for processing
redis-cli FT.SEARCH library_index "*" LIMIT 0 5
# Should return chunks from sample_doc.pdf
```

**Pass Criteria:**
- Documents automatically processed and stored
- Chunks searchable via RedisVL
- Embeddings generated
- Redis memory stays under cap

**CHECKPOINT:** `checkpoints/checkpoint-3.3-library-storage.md`

---

### Chunk 3.4: Library Search Integration
**Files:** `brain/tools/library_search.py`, `brain/main.py` (update)

**Task:**
- Create library search tool
- Query both `type:memory` and `type:library_book`
- Return top-k results with reranking
- Add to brain endpoints

**Test:**
```python
# After loading library with known content
result = search_library("Victorian railways")
# Should return relevant chunks from library
```

**Pass Criteria:**
- Hybrid search works (memory + library)
- Relevant results returned
- Reranker improves accuracy
- Fast enough (< 500ms)

**CHECKPOINT:** `checkpoints/checkpoint-3.4-library-search.md`

---

### Chunk 3.5: LangGraph Setup (Basic Flow)
**Files:** `brain/graph/basic_flow.py`, `brain/graph/nodes.py`, `brain/requirements.txt` (update)

**Task:**
- Install LangGraph
- Create basic graph: Input → Route → Chat/Memory/Code
- Single-step execution (no loops yet)
- Replace direct endpoint logic

**Test:**
```bash
curl -X POST http://localhost:8081/chat -d '{"message": "Hello"}'
# Should route through LangGraph to chat node

curl -X POST http://localhost:8081/chat -d '{"message": "What did I say earlier?"}'
# Should route to memory query node
```

**Pass Criteria:**
- LangGraph orchestrates requests
- Routing decisions correct
- Tools called appropriately
- Response format unchanged

**CHECKPOINT:** `checkpoints/checkpoint-3.5-langgraph-basic.md`

---

### Chunk 3.6: Code Execution Tool
**Files:** `brain/tools/code_executor.py`, `brain/graph/nodes.py` (update)

**Task:**
- Create code execution node
- Call sandbox `/execute` endpoint
- Handle success/error responses
- Add to LangGraph tool set

**Test:**
```bash
curl -X POST http://localhost:8081/chat \
  -d '{"message": "Run this: print(2+2)"}'
# Should execute code and return "4"
```

**Pass Criteria:**
- Code sent to sandbox
- Results returned in response
- Errors handled gracefully
- Timeout enforced (30s)

**CHECKPOINT:** `checkpoints/checkpoint-3.6-code-execution-tool.md`

---

### Chunk 3.7: ReAct Agent Loop (No CoV)
**Files:** `brain/graph/agent_flow.py`, `brain/graph/nodes.py` (update)

**Task:**
- Implement ReAct reasoning loop
- Max 10 iterations
- Tool selection via Goblin (DeepSeek-R1-Distill)
- Observation → Thought → Action cycle

**Test:**
```bash
curl -X POST http://localhost:8081/chat \
  -d '{"message": "Calculate fibonacci(10) and tell me the result"}'
# Should: write code, execute it, observe result, respond
```

**Pass Criteria:**
- Multi-step tasks complete
- Tool calls in correct order
- Iteration limit enforced
- Agent stops when task done

**CHECKPOINT:** `checkpoints/checkpoint-3.7-react-agent.md`

---

### Chunk 3.8: Chain of Verification (Draft → Critique)
**Files:** `brain/graph/cov_flow.py`, `brain/graph/nodes.py` (update)

**Task:**
- Create CoV graph: Draft (Goblin) → Critique (Vorpal)
- Extract factual claims from draft
- Store claims for verification
- No verification yet (just extraction)

**Test:**
```python
draft = "The Eiffel Tower is 500 meters tall and was built in 1900."
claims = extract_claims(draft)
# Should return: ["Eiffel Tower is 500 meters tall", "Built in 1900"]
```

**Pass Criteria:**
- Claims correctly extracted
- No hallucinations in extraction
- Format parseable for next step

**CHECKPOINT:** `checkpoints/checkpoint-3.8-cov-draft-critique.md`

---

### Chunk 3.9: Chain of Verification (Verify → Revise)
**Files:** `brain/graph/cov_flow.py` (update)

**Task:**
- Add verification step: search library/web for evidence
- Compare evidence to claims
- Revise draft if contradictions found
- Complete CoV pipeline

**Test:**
```bash
# With library containing correct info
curl -X POST http://localhost:8081/chat \
  -d '{"message": "Tell me about the Eiffel Tower", "use_cov": true}'
# Should catch wrong height/date and correct them
```

**Pass Criteria:**
- False claims caught
- Draft revised with correct info
- Evidence cited in response
- Accuracy > 90% on test set

**CHECKPOINT:** `checkpoints/checkpoint-3.9-cov-complete.md`

---

### Chunk 3.10: Empirical Tuning - Surprise Weights
**Files:** `scripts/tune-surprise-weights.py`, `brain/config.py` (update)

**Task:**
- Create test dataset (high/low surprise examples)
- Test weight combinations: 0.5/0.5, 0.6/0.4, 0.7/0.3
- Measure precision/recall
- Update config with best weights

**Test:**
```bash
python scripts/tune-surprise-weights.py
# Outputs best weights based on test set
```

**Pass Criteria:**
- Best weights identified
- Precision > 80%
- Recall > 70%
- Config updated

**CHECKPOINT:** `checkpoints/checkpoint-3.10-tuning-surprise.md`

---

### Chunk 3.11: Empirical Tuning - VRAM Optimization
**Files:** `scripts/tune-gpu-layers.py`, `docker-compose.yml` (update if needed)

**Task:**
- Test different `n_gpu_layers` for Goblin
- Measure throughput vs VRAM usage
- Find optimal balance
- Update docker-compose

**Test:**
```bash
python scripts/tune-gpu-layers.py --test-layers 30,35,38,40
# Outputs performance metrics for each
```

**Pass Criteria:**
- Optimal layers identified
- No OOM errors
- Throughput acceptable (>15 tok/s)
- Config updated

**CHECKPOINT:** `checkpoints/checkpoint-3.11-tuning-vram.md`

---

## PHASE 4: UI & POLISH (Week 4)

### Chunk 4.1: Engine Room Dashboard - Base UI
**Files:** `ui/dashboard.html`, `ui/static/css/dashboard.css`, `ui/app.py`

**Task:**
- Create simple Flask/FastAPI UI server
- Basic HTML dashboard
- No real-time data yet (static placeholders)
- Serve on port 8081

**Test:**
```bash
python ui/app.py
# Open http://localhost:8081 in browser
# Should see dashboard layout
```

**Pass Criteria:**
- UI loads without errors
- Layout looks reasonable
- Responsive design
- No console errors

**CHECKPOINT:** `checkpoints/checkpoint-4.1-ui-base.md`

---

### Chunk 4.2: Engine Room - VRAM Visualization
**Files:** `ui/dashboard.html` (update), `ui/static/js/vram-chart.js`, `brain/main.py` (add `/metrics` endpoint)

**Task:**
- Add `/metrics` endpoint to brain (reports VRAM usage)
- Create real-time chart using Chart.js
- Update every 2 seconds
- Show Vorpal/Goblin split

**Test:**
```bash
# Open dashboard
# Should see live VRAM chart updating
# Load models, watch chart reflect changes
```

**Pass Criteria:**
- Chart updates in real-time
- VRAM values accurate (compare to `nvidia-smi`)
- Visual clear (colors, labels)
- No memory leaks in browser

**CHECKPOINT:** `checkpoints/checkpoint-4.2-ui-vram-chart.md`

---

### Chunk 4.3: Engine Room - Context Gauge
**Files:** `ui/dashboard.html` (update), `ui/static/js/context-gauge.js`

**Task:**
- Add context usage to `/metrics` endpoint
- Create gauge widget
- Alert (red) when > 80%
- Show current/max tokens

**Test:**
```bash
# Long conversation to fill context
# Watch gauge increase
# Verify alert triggers at 80%
```

**Pass Criteria:**
- Gauge accurate
- Alert triggers correctly
- Updates smoothly
- Mobile-friendly

**CHECKPOINT:** `checkpoints/checkpoint-4.3-ui-context-gauge.md`

---

### Chunk 4.4: Engine Room - Model Swap Controls
**Files:** `ui/dashboard.html` (update), `brain/main.py` (add `/swap_model` endpoint)

**Task:**
- Add model swap endpoint (switch Goblin between Thinker/Coder)
- Create swap button in UI
- Show progress during 30-60s load
- Update display when complete

**Test:**
```bash
# Click swap button
# Should see progress indicator
# After 30-60s, model switches
# Verify with test query
```

**Pass Criteria:**
- Swap works reliably
- Progress feedback clear
- No crashes during swap
- Chat disabled during swap

**CHECKPOINT:** `checkpoints/checkpoint-4.4-ui-model-swap.md`

---

### Chunk 4.5: Model Hub - VRAM Estimator
**Files:** `ui/model-hub.html`, `ui/static/js/model-estimator.js`, `brain/models/estimator.py`

**Task:**
- Create VRAM estimation function (based on model size/quant)
- Model hub page listing available models
- Show estimated VRAM for each
- Highlight compatible models (green) vs too large (red)

**Test:**
```bash
# Open model hub page
# Should see list of models with VRAM estimates
# Verify estimates roughly match actual (±15%)
```

**Pass Criteria:**
- Estimates reasonably accurate
- Compatible models clearly marked
- UI intuitive
- Updates when models added

**CHECKPOINT:** `checkpoints/checkpoint-4.5-ui-model-hub.md`

---

### Chunk 4.6: Model Hub - One-Click Loading
**Files:** `ui/model-hub.html` (update), `brain/models/loader.py`, `brain/main.py` (add `/load_model` endpoint)

**Task:**
- Add model loading endpoint
- Download model if not present (progress bar)
- Load into appropriate engine
- Update dashboard when done

**Test:**
```bash
# Click "Load" on a model
# Should download (if needed) and load
# Verify model responds to queries
# VRAM chart updates
```

**Pass Criteria:**
- Download works (with progress)
- Loading reliable
- Errors handled (disk space, network)
- UI updates correctly

**CHECKPOINT:** `checkpoints/checkpoint-4.6-ui-model-loading.md`

---

### Chunk 4.7: Voice Mode UI Toggle
**Files:** `ui/chat.html`, `ui/static/js/voice-mode.js`

**Task:**
- Add voice mode toggle to chat UI
- Enable microphone input when on
- Show recording indicator
- Play synthesized responses

**Test:**
```bash
# Enable voice mode
# Click to record
# Speak question
# Should see transcription, then hear response
```

**Pass Criteria:**
- Recording works (permission requested)
- Transcription accurate
- Audio playback smooth
- Toggle persistent (remembers state)

**CHECKPOINT:** `checkpoints/checkpoint-4.7-ui-voice-mode.md`

---

### Chunk 4.8: Long Conversation Test
**Files:** `tests/long-conversation-test.py`

**Task:**
- Automated test: 500+ turns
- Mix of chat, memory queries, code execution
- Monitor VRAM, memory usage, response times
- Log any errors or degradation

**Test:**
```bash
python tests/long-conversation-test.py --turns 500
# Let it run for ~2 hours
# Check final report
```

**Pass Criteria:**
- No crashes
- VRAM stable
- Response times don't degrade
- Memory system works throughout

**CHECKPOINT:** `checkpoints/checkpoint-4.8-long-conversation-test.md`

---

### Chunk 4.9: Multi-Modal Stress Test
**Files:** `tests/multi-modal-stress-test.py`

**Task:**
- Concurrent workload: chat + library queries + code execution + voice
- Simulate realistic usage patterns
- Monitor resource usage
- Test for race conditions

**Test:**
```bash
python tests/multi-modal-stress-test.py --duration 3600
# 1 hour of mixed workload
```

**Pass Criteria:**
- All features work concurrently
- No deadlocks
- VRAM within limits
- No data corruption

**CHECKPOINT:** `checkpoints/checkpoint-4.9-multi-modal-stress-test.md`

---

### Chunk 4.10: Agent Stress Test
**Files:** `tests/agent-stress-test.py`, `tests/agent-test-cases.yaml`

**Task:**
- 20+ complex multi-step tasks
- Test agent planning, tool use, error recovery
- Measure success rate
- Identify failure patterns

**Test:**
```bash
python tests/agent-stress-test.py
# Runs all test cases
# Outputs success rate and failure analysis
```

**Pass Criteria:**
- Success rate > 80%
- No infinite loops
- Timeout handling works
- Failures logged for improvement

**CHECKPOINT:** `checkpoints/checkpoint-4.10-agent-stress-test.md`

---

### Chunk 4.11: Edge Case Testing
**Files:** `tests/edge-cases.py`

**Task:**
- Test edge cases:
  - OOM triggers (load huge model)
  - Invalid code execution
  - Missing models
  - Redis connection loss
  - Disk full during library ingestion
- Verify graceful degradation

**Test:**
```bash
python tests/edge-cases.py --test-all
# Each test should fail gracefully, not crash
```

**Pass Criteria:**
- All edge cases handled
- Error messages clear
- System recoverable
- No data loss

**CHECKPOINT:** `checkpoints/checkpoint-4.11-edge-case-testing.md`

---

### Chunk 4.12: Final Documentation & Polish
**Files:** `README.md`, `docs/installation.md`, `docs/usage.md`, `docs/troubleshooting.md`

**Task:**
- Complete installation guide
- Usage examples for all features
- Troubleshooting common issues
- Architecture diagram
- API documentation

**Test:**
```bash
# Have someone else follow installation guide
# Should be able to install and run without help
```

**Pass Criteria:**
- Docs complete and accurate
- Clear and concise
- Examples work
- Troubleshooting covers common issues

**CHECKPOINT:** `checkpoints/checkpoint-4.12-documentation.md`

---

## FINAL CHECKPOINT: `checkpoints/RELEASE-v7.5.md`

**Includes:**
- All features working
- All tests passing
- Documentation complete
- Known issues documented
- Performance metrics recorded
- Ready for deployment

---

## CHUNK HYGIENE CHECKLIST (Use Between Every Chunk)

```markdown
## Pre-CHECKPOINT Review

### 1. Syntax & Linting
- [ ] Run `flake8 <files>` or `pylint <files>`
- [ ] Fix all errors, document warnings to ignore
- [ ] Verify consistent code style

### 2. Function Call Audit
- [ ] List all new functions defined
- [ ] Grep for all calls to those functions
- [ ] Verify signatures match (args, kwargs, types)
- [ ] Check return value handling

### 3. Import Trace
- [ ] List all new imports
- [ ] Verify packages in requirements.txt
- [ ] Test imports in Python REPL
- [ ] Check for circular imports

### 4. Logic Walk
- [ ] Read code flow start-to-finish
- [ ] Check for obvious bugs (off-by-one, null checks, etc.)
- [ ] Verify error handling
- [ ] Look for race conditions (async code)

### 5. Manual Test
- [ ] Run the specific test for this chunk
- [ ] Verify pass criteria met
- [ ] Test error cases (not just happy path)
- [ ] Check logs for warnings

### 6. Integration Check
- [ ] Verify doesn't break previous chunks
- [ ] Run quick smoke test of overall system
- [ ] Check resource usage (VRAM, RAM, CPU)

### 7. CHECKPOINT.md
- [ ] Document what's complete
- [ ] List files created/modified
- [ ] Record test results
- [ ] Note any known issues
- [ ] State next chunk clearly
```

---

**TOTAL CHUNKS:** 43 (across 4 phases)
**ESTIMATED TIME:** 4-5 weeks at 2-3 chunks per day
**CHECKPOINT FREQUENCY:** After every chunk (43 total checkpoints)

---

## Notes for David

**Small Bites:** Each chunk is designed to be completable in 1-3 hours.

**Independent Testing:** Every chunk has its own test that doesn't depend on future work.

**Clear Handoffs:** Each CHECKPOINT.md explicitly states what's done and what's next.

**Flexible Ordering:** Within a phase, some chunks can be reordered if needed (e.g., can do voice before semantic router in Phase 2).

**Parallel Work:** Some chunks can be done in parallel (e.g., Vorpal and Goblin setup), but checkpoints should still be sequential.

**Fail Fast:** If a chunk doesn't pass its criteria, STOP. Don't move to the next chunk. Fix it, checkpoint, then continue.

**Context Resets:** You can clear context after any checkpoint and resume from the CHECKPOINT.md file. No information loss.

This should keep you from choking on oversized bites. One chunk at a time, checkpoints all the way.
