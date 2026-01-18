# Archive-AI v7.5 - Claude Code Handoff Document

**Date:** December 27, 2025
**From:** Claude (claude.ai) + David
**To:** Claude Code
**Project:** Archive-AI v7.5 Production Implementation

---

## I. Executive Summary

You are being handed a **complete, battle-tested architecture** for Archive-AI v7.5, a local-first AI cognitive framework. The design has been thoroughly vetted, the implementation plan is chunked into 43 small, testable pieces, and your job is to **execute autonomously** while David is on holiday break.

**Your Mission:**
Build Archive-AI v7.5 one chunk at a time, following the implementation plan exactly, creating checkpoints after each chunk, and only escalating to David when you hit genuine architectural questions or blockers.

---

## II. Project Context

### What is Archive-AI?

Archive-AI is a **local-first AI companion system** with:
- **Permanent memory** using a "Surprise Score" metric (Titans architecture)
- **Dual inference engines** (Vorpal + Goblin) optimized for single 16GB GPU
- **Voice I/O** using FastWhisper + XTTS (Ian McKellen voice)
- **Agentic capabilities** using LangGraph with ReAct loops
- **Library ingestion** for document knowledge base
- **Chain of Verification** for hallucination mitigation

### Hardware Target
- **Single NVIDIA RTX 5060 Ti** (16GB VRAM)
- **64GB System RAM**
- **NVMe SSD** for model storage
- **CPU:** Any modern CPU (8+ cores recommended)

### The Problem We're Solving
David has been struggling with **chunks that are too large**, leading to:
- Integration failures
- Uncaught bugs propagating through multiple components
- Context window exhaustion requiring restarts
- Frustration and project delays

**The Solution:** Small, independently testable chunks with rigorous checkpoints.

---

## III. Critical Design Documents

You have been provided with two essential documents:

### 1. `Archive-AI_System_Atlas_v7.5_REVISED.md`
This is the **architectural specification**. It defines:
- VRAM allocation (3.5GB Vorpal, 10GB Goblin, 2.5GB buffer)
- Model choices (Llama-3-8B, DeepSeek-R1-Distill-14B, Qwen-2.5-Coder-14B)
- Redis memory architecture
- Docker stack composition
- Performance targets

**TREAT THIS AS GOSPEL.** Do not deviate from the spec without David's explicit approval.

### 2. `Archive-AI_Implementation_Plan_v7.5.md`
This is your **work order**. It contains:
- 43 chunks across 4 phases
- Specific files to create for each chunk
- Test criteria for each chunk
- Hygiene checklist to run between chunks

**FOLLOW THIS SEQUENTIALLY.** Do not skip chunks, do not combine chunks, do not reorder chunks without good reason.

---

## IV. Autonomy Guidelines

### What You Should Do Autonomously

✅ **Implementation Decisions:**
- Variable names, function organization, code structure
- Library choices within reason (if spec says "FastAPI," use FastAPI, but picking request validation lib is your call)
- Error messages and logging formats
- Test implementation details
- Minor optimizations that don't change architecture

✅ **Bug Fixes:**
- Syntax errors
- Import errors
- Type mismatches
- Logic bugs discovered during testing
- Performance issues within spec limits

✅ **Chunk Execution:**
- Write all code for the chunk
- Run all tests
- Execute hygiene checklist
- Write CHECKPOINT.md
- Move to next chunk if tests pass

### What You Should Escalate to David

🚫 **Architecture Changes:**
- Deviating from VRAM allocation
- Changing model choices
- Altering Redis schema
- Modifying Docker stack composition
- Adding/removing major components

🚫 **Spec Conflicts:**
- When implementation plan contradicts system atlas
- When test criteria seem impossible to meet
- When dependencies have breaking changes

🚫 **Major Blockers:**
- Can't proceed without hardware access (GPU testing)
- Can't proceed without external resources (model downloads)
- Can't proceed without architectural decision

🚫 **Judgment Calls:**
- Security implications
- Data loss risk
- Performance degradation beyond spec

### The Decision Tree

```
Question arises
    ↓
Is it explicitly defined in spec/plan?
    YES → Follow spec/plan
    NO ↓
Does it affect architecture or performance targets?
    YES → Escalate to David
    NO ↓
Is it a reasonable implementation choice?
    YES → Decide and document in CHECKPOINT
    NO → Escalate to David
```

---

## V. David's Preferences (Important)

From David's user preferences and our working history:

### Communication Style
- **Medium verbosity** - Not terse, not verbose
- **Heavy dash of humor** - Keep it light when appropriate
- **No empty ego boosts** - Be honest, even if truth is harsh
- **Profanity welcome** - Natural language, not corporate-speak
- **Don't stampede with choices** - Present options clearly, don't overwhelm

### Technical Approach
- **Tell the truth** regardless of how he might feel
- **Avoid filling in blanks** without sufficient support
- **Avoid creating facts** unless asked to
- **Historical authenticity** when applicable (but this is a modern project, so less relevant)

### What David Hates
- Sycophantic responses ("That's a great idea!" without substance)
- Over-explaining obvious things
- Beating around the bush when delivering bad news
- Asking permission for things that are clearly in scope

### What David Appreciates
- Getting shit done
- Honest technical feedback
- Direct communication
- Working code that actually runs

---

## VI. The Chunked Approach (Why It Matters)

### Previous Failures
David has tried building this system multiple times with **large, monolithic chunks**:
- "Build the entire memory system"
- "Implement the agent framework"
- "Set up all the Docker services"

**Result:** Integration nightmares, hidden bugs, context exhaustion.

### The New Way
Each chunk is **1-3 files** and **1-3 hours of work**:
- Small enough to hold in working memory
- Independently testable
- Clear pass/fail criteria
- Checkpoint creates hard context save

### Your Responsibility
**DO NOT COMBINE CHUNKS.** Even if you think "I could do chunks 2.1 and 2.2 together," **DON'T.**

The point is to have many small, verified steps, not fewer large ones.

---

## VII. Checkpoint Format (Critical)

After **every single chunk**, you must create a `checkpoints/checkpoint-X.Y-name.md` file.

### Template

```markdown
# Checkpoint X.Y - [Feature Name]

**Date:** [ISO timestamp]
**Status:** [PASS / FAIL / PARTIAL]
**Chunk Duration:** [time spent]

---

## Files Created/Modified

- `path/to/file1.py` (Created)
- `path/to/file2.py` (Modified)
- `path/to/file3.yaml` (Created)

---

## Implementation Summary

[2-3 sentences describing what was built]

---

## Tests Executed

### Test 1: [Name]
**Command:** `docker-compose up -d redis`
**Expected:** Redis starts without errors
**Result:** ✅ PASS
**Evidence:** [paste relevant output or screenshot if needed]

### Test 2: [Name]
**Command:** `python scripts/test-redis.py`
**Expected:** All RedisJSON/RediSearch commands succeed
**Result:** ✅ PASS
**Evidence:** [paste output]

---

## Hygiene Checklist

- [x] Syntax & Linting: `flake8 brain/` → No errors
- [x] Function Call Audit: All function signatures verified
- [x] Import Trace: All imports in requirements.txt
- [x] Logic Walk: Code reviewed, no obvious bugs
- [x] Manual Test: All chunk tests pass
- [x] Integration Check: Previous chunks still work

---

## Pass Criteria Met

- [x] Redis responds to ping
- [x] RedisJSON commands work
- [x] RediSearch index creation works
- [x] Memory limit enforced

**OVERALL STATUS:** ✅ PASS

---

## Known Issues / Tech Debt

[List any issues found that aren't blockers, e.g.:]
- Redis persistence not fully tested (will test in long-running test)
- Logging format could be more structured (future enhancement)

---

## Next Chunk

**Chunk 1.2 - Code Sandbox Container**
- Create FastAPI server with `/execute` endpoint
- Implement basic Python code execution
- Create Dockerfile with non-root user

---

## Notes for David

[Any decisions made, questions that arose, or context he should know]

Example:
- Chose `redis-py` over `aioredis` because redis-py now includes async support
- Test script uses pytest instead of unittest (more modern, better fixtures)

---

## Autonomous Decisions Made

[Log any choices you made that weren't explicitly in the spec]

Example:
- Used Python 3.11 instead of 3.10 (better performance, still compatible)
- Added retry logic to Redis connection (3 retries with exponential backoff)

These decisions are within autonomy guidelines but logged for transparency.
```

### Checkpoint Discipline

**YOU MUST:**
- Create a checkpoint after every chunk
- Mark it PASS only if all test criteria met
- Mark it FAIL if any test criteria not met
- Mark it PARTIAL if tests pass but concerns exist

**DO NOT:**
- Move to next chunk if status is FAIL
- Skip checkpoints because "it's small"
- Combine multiple chunks into one checkpoint

---

## VIII. The Hygiene Checklist (Between Every Chunk)

Before writing CHECKPOINT.md, run through this:

### 1. Syntax & Linting
```bash
flake8 <files_created_or_modified>
# OR
pylint <files_created_or_modified>
```
- Fix all errors
- Document any warnings being ignored (and why)

### 2. Function Call Audit
- List all new functions defined
- Grep for all calls to those functions
- Verify signatures match (args, kwargs, return types)
- Check return value handling

### 3. Import Trace
- List all new imports
- Verify packages in `requirements.txt`
- Test imports in Python REPL: `python -c "import X"`
- Check for circular imports

### 4. Logic Walk
- Read code start-to-finish
- Check for obvious bugs:
  - Off-by-one errors
  - Null/None checks
  - Exception handling
  - Race conditions (async code)
  - Resource leaks (files, connections)

### 5. Manual Test
- Run the specific test for this chunk
- Verify ALL pass criteria met
- Test error cases (not just happy path)
- Check logs for warnings

### 6. Integration Check
- Run quick smoke test of overall system
- Verify doesn't break previous chunks
- Check resource usage (VRAM, RAM, CPU)

**THIS IS NON-NEGOTIABLE.** Every chunk, every time.

---

## IX. Handling Blockers

### Hardware Blockers (GPU Access)

Some chunks (especially Phase 1 VRAM testing) require actual GPU access. You have two options:

**Option 1: Write code, defer testing**
- Implement the chunk fully
- Write the test script
- Mark checkpoint as `PARTIAL - Needs GPU Testing`
- Document what needs to be tested
- David runs the GPU tests when back

**Option 2: Mock/Simulate**
- Create mock GPU responses for testing
- Note in checkpoint that real GPU testing needed
- Still mark as `PARTIAL`

**DO NOT** mark as PASS without testing. PARTIAL is fine for GPU-dependent chunks.

### Dependency Blockers (Missing Resources)

If you need a resource that's not available (model download, API key, etc.):

1. Document the requirement in checkpoint
2. Create placeholder/mock if possible
3. Mark as `PARTIAL - Needs [Resource]`
4. Move to next chunk if it doesn't depend on this one

### Conceptual Blockers (Unclear Spec)

If the spec is unclear or contradictory:

1. **STOP**
2. Create checkpoint with status `BLOCKED`
3. Document the specific question
4. Wait for David's clarification
5. **DO NOT GUESS** - unclear specs lead to rework

---

## X. Special Considerations

### VRAM is Sacred

The **entire architecture** is built around staying under 16GB VRAM. Any code that could affect VRAM usage should be **triple-checked**:

- Vorpal: 3.5GB cap (GPU_MEMORY_UTILIZATION=0.22)
- Goblin: 10GB cap (n_gpu_layers tuned for this)
- Total: Must stay under 13.5GB to leave 2.5GB buffer

**If you're unsure if something affects VRAM, ask David.**

### Redis Memory is Also Sacred

Redis is configured with `maxmemory 20gb` and `allkeys-lru` eviction. Any code that stores data in Redis should consider:

- Will this fit in 20GB?
- Is LRU eviction acceptable for this data?
- Should this be persisted differently?

### Security Matters (Sandbox)

The code sandbox is designed to be **secure by default**:
- No root access
- No external network
- Separate user
- Limited resources

**DO NOT** weaken these constraints without David's approval.

---

## XI. Git Workflow

### Branching Strategy

```
main
  └─ dev
      └─ phase-1
      └─ phase-2
      └─ phase-3
      └─ phase-4
```

- Work in phase branches
- Merge to `dev` at end of each phase
- Merge to `main` only at final release

### Commit Messages

Format:
```
[Chunk X.Y] Brief description

- Detail 1
- Detail 2

Checkpoint: checkpoints/checkpoint-X.Y-name.md
```

Example:
```
[Chunk 1.1] Redis Stack setup with memory limits

- Configure Redis Stack in docker-compose.yml
- Add maxmemory 20gb and allkeys-lru eviction
- Create test script for RedisJSON/RediSearch

Checkpoint: checkpoints/checkpoint-1.1-redis.md
```

### When to Commit

- After each chunk's checkpoint is written
- Commit includes: code changes + checkpoint file
- Use meaningful branch names: `chunk-1.1-redis-setup`

---

## XII. Testing Philosophy

### Unit Tests vs Integration Tests vs Manual Tests

For this project, we're using **manual tests** for chunks because:

1. Fast to write
2. Easy to verify
3. Tests real integration
4. No test framework overhead

**However**, you should still think about:
- Edge cases
- Error conditions
- Performance
- Resource usage

### Test-Driven Development (Sort Of)

For each chunk:
1. Read the test criteria first
2. Write code to meet those criteria
3. Run the test
4. Fix until test passes
5. Run hygiene checklist
6. Write checkpoint

**The test criteria are your specification.**

---

## XIII. Performance Expectations

From the design doc, here are the targets:

**Latency:**
- Chat (Vorpal): < 2s to first token
- Reasoning (Goblin): < 10s to first token
- Voice round-trip: < 3s total

**Throughput:**
- Vorpal: ~60-80 tokens/second
- Goblin: ~15-30 tokens/second

**Memory:**
- VRAM: 13.5GB ± 1GB
- System RAM: < 24GB (excluding Redis)
- Redis: < 20GB

**If your implementation doesn't meet these, investigate before moving on.**

---

## XIV. Common Pitfalls to Avoid

Based on David's previous attempts:

### 1. Scope Creep
**Bad:** "While implementing the sandbox, I also added a job queue system."
**Good:** Implement exactly what the chunk specifies, nothing more.

### 2. Premature Optimization
**Bad:** "I rewrote the memory worker to use Cython for speed."
**Good:** Get it working first, optimize later if needed.

### 3. Skipping Tests
**Bad:** "The code looks good, I'm sure it works."
**Good:** Run every test, verify every criterion.

### 4. Combining Chunks
**Bad:** "Chunks 2.1 and 2.2 are related, I'll do them together."
**Good:** Do 2.1, checkpoint, then do 2.2, checkpoint.

### 5. Inventing Requirements
**Bad:** "I added user authentication because it seems important."
**Good:** Only implement what's in the spec.

### 6. Ignoring Hygiene
**Bad:** "I'll fix the linting errors later."
**Good:** Fix them now, before the checkpoint.

---

## XV. Starting Point

You should begin with:

**Chunk 1.1: Redis Stack Setup**

Location: `Archive-AI_Implementation_Plan_v7.5.md` → Phase 1 → Chunk 1.1

### Your First Tasks:
1. Create project directory structure
2. Initialize git repository
3. Create `docker-compose.yml` with Redis Stack service
4. Create `scripts/test-redis.py`
5. Run tests
6. Run hygiene checklist
7. Write `checkpoints/checkpoint-1.1-redis.md`

### Expected Time:
1-2 hours

### When You're Done:
Move to Chunk 1.2 (Code Sandbox Container)

---

## XVI. Communication Protocol

### Checkpoints are Your Communication

David will review checkpoints when he has time. Each checkpoint should be **self-contained** - he should be able to read it and understand:
- What was built
- What works
- What doesn't work
- What's next

### When to Ping David

Use **BLOCKED** status in checkpoint when you need input:

```markdown
**Status:** BLOCKED - Need Architectural Decision

## Blocker

The spec says to use FastAPI for the sandbox, but the chunk test 
requires WebSocket support which FastAPI handles differently than 
the plan describes. 

Options:
1. Use FastAPI with WebSocket plugin (adds dependency)
2. Use aiohttp instead (different framework)
3. Modify test to not require WebSocket

Waiting for David's decision on which approach to take.
```

David will see this and respond when he can.

### No News is Good News

If checkpoints are marked **PASS**, keep going. David will speak up if he sees something wrong.

---

## XVII. Project Structure

Expected directory structure (you'll create this):

```
archive-ai/
├── brain/                  # Archive-Brain orchestrator
│   ├── main.py
│   ├── config.py
│   ├── graph/              # LangGraph flows
│   ├── tools/              # Tool implementations
│   ├── workers/            # Background workers
│   └── memory/             # Memory system
├── vorpal/                 # Vorpal engine
│   ├── Dockerfile
│   └── config.yaml
├── goblin/                 # Goblin engine (llama.cpp)
│   └── start.sh
├── sandbox/                # Code execution sandbox
│   ├── server.py
│   ├── Dockerfile
│   └── requirements.txt
├── voice/                  # Voice services
│   ├── server.py
│   ├── transcribe.py
│   ├── synthesize.py
│   └── requirements.txt
├── librarian/              # Library ingestion
│   ├── watcher.py
│   ├── processor.py
│   └── storage.py
├── ui/                     # Dashboard UI
│   ├── app.py
│   ├── dashboard.html
│   └── static/
├── scripts/                # Test and utility scripts
│   └── test-*.py
├── tests/                  # Test suites
│   └── *.py
├── models/                 # Model storage
│   ├── vorpal/
│   ├── goblin/
│   └── voice/
├── checkpoints/            # Checkpoint files
│   └── checkpoint-*.md
├── docs/                   # Documentation
│   └── *.md
├── data/                   # Persistent data
│   └── redis/
├── docker-compose.yml      # Docker stack
└── README.md
```

---

## XVIII. Success Criteria for This Engagement

You will be considered successful if:

1. **All chunks attempted** - You work through the implementation plan sequentially
2. **All chunks checkpointed** - Every chunk has a corresponding checkpoint file
3. **Most chunks passing** - >80% of chunks marked PASS (some PARTIAL for GPU testing is OK)
4. **No breaking changes** - Architecture stays within spec
5. **Clean code** - Hygiene checklist followed
6. **Good communication** - Checkpoints are clear and complete

You will **NOT** be penalized for:
- Chunks marked PARTIAL due to GPU access
- Chunks marked BLOCKED due to unclear spec
- Taking longer than estimated (as long as you're making progress)
- Finding bugs in the spec (report them!)

---

## XIX. Final Reminders

### The Goal
Build Archive-AI v7.5 one chunk at a time so David can return from holidays to a working system instead of a to-do list.

### The Philosophy
- **Small chunks**: 1-3 hours each
- **Independent testing**: Each chunk proves itself
- **Frequent checkpoints**: Never lose context
- **Autonomous execution**: You decide implementation details
- **Escalate architecture**: David decides structural changes

### The Attitude
- **Get shit done**: Code that works > perfect code that doesn't exist
- **Be honest**: If something's broken, say so
- **Be thorough**: Run all tests, all hygiene checks
- **Be patient**: 43 chunks is a marathon, not a sprint

---

## XX. You've Got This

You have:
- ✅ A complete architecture (System Atlas)
- ✅ A detailed implementation plan (43 chunks)
- ✅ Clear autonomy guidelines
- ✅ Hygiene checklists
- ✅ Checkpoint templates
- ✅ David's trust

**Now go build something awesome.**

Start with Chunk 1.1, take it one chunk at a time, checkpoint after each one, and we'll have Archive-AI v7.5 running by New Year's.

---

**Godspeed, Claude Code.**

---

## Appendix A: Quick Reference

### Key Files
- `Archive-AI_System_Atlas_v7.5_REVISED.md` - Architecture spec
- `Archive-AI_Implementation_Plan_v7.5.md` - Work order
- `CLAUDE_CODE_HANDOFF.md` - This document

### Key Commands
```bash
# Start services
docker-compose up -d [service]

# Check VRAM
nvidia-smi

# Lint code
flake8 <files>

# Test imports
python -c "import X"

# Redis CLI
redis-cli
```

### Key Contacts
- **David** - Product owner, architect (available intermittently during holidays)

### Emergency Stops
If you encounter:
- Data loss risk → STOP, mark BLOCKED
- Security vulnerability → STOP, mark BLOCKED  
- Architectural impossibility → STOP, mark BLOCKED

Do not proceed until David responds.

---

**END OF HANDOFF DOCUMENT**
