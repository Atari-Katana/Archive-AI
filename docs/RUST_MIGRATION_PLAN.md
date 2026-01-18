# Archive-AI Rust Migration Plan
**Target:** Conversion of Core Orchestrator and Utilities to Rust
**Status:** DRAFT
**Version:** 1.0

---

## 1. Executive Summary
This document outlines the strategy to migrate the Archive-AI `brain` (orchestrator) and `librarian` (ingestion) services from Python to Rust.

**Why Rust?**
*   **Performance:** Lower latency in request routing and memory processing.
*   **Safety:** Memory safety guarantees and strict type checking eliminate runtime type errors common in dynamic agent systems.
*   **Concurrency:** Tokio's async runtime handles high-concurrency agent workflows more efficiently than Python's `asyncio`.
*   **Resource Efficiency:** Significant reduction in RAM/CPU footprint for the orchestrator layer.

**What stays Python/C++?**
*   **Inference Engines:** `vorpal` (vLLM) and `goblin` (llama.cpp) remain as-is.
*   **Voice:** `voice` container (Faster-Whisper/F5-TTS) remains Python due to deep PyTorch dependencies.
*   **Sandbox:** `sandbox` remains Python to natively execute the user's Python code requests.

---

## 2. Target Architecture

The architecture shifts to a **Hybrid** model:
*   **Rust:** Business logic, API routing, state management, file watching, vector math.
*   **Python:** Deep Learning model inference, dynamic code execution.

### Tech Stack Selection
| Component | Python (Current) | Rust (Target) |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI | **Axum** (Ergonomic, robust, built on Tokio) |
| **Runtime** | asyncio | **Tokio** |
| **Serialization** | Pydantic | **Serde** + **Validator** |
| **Database** | redis-py | **redis-rs** (or `fred` for async) |
| **HTTP Client** | httpx | **Reqwest** |
| **Vector Search** | redisvl | **redis-rs** + custom vector logic or **Qdrant** client |
| **Logging** | logging | **Tracing** + **Tracing-Subscriber** |
| **Error Handling** | Exception Classes | **ThisError** / **Anyhow** |

---

## 3. Phased Implementation Roadmap

### Phase 1: Infrastructure & Scaffolding (Week 1)
**Goal:** Establish the Rust workspace and Docker environment.

1.  **Workspace Setup:**
    *   Initialize Cargo workspace (`archive-ai-rs`).
    *   Create crates: `brain-rs` (binary), `librarian-rs` (binary), `shared` (library for types/config).
2.  **Docker Integration:**
    *   Create `Dockerfile.rust` using multi-stage builds (`chef` or `debian:bookworm-slim`).
    *   Update `docker-compose.yml` to include `brain-rs` (initially alongside `brain`).
3.  **Configuration:**
    *   Port `.env` handling using the `dotenvy` and `config` crates.
    *   Define strongly-typed configuration structs in `shared`.

### Phase 2: The Core Brain (Weeks 2-3)
**Goal:** Replace the FastAPI routing layer.

1.  **Redis Connectivity:**
    *   Implement async Redis connection pool manager.
    *   Port `stream_handler.py` to a Tokio task processing Redis Streams.
2.  **API Routes (Axum):**
    *   Port `/health` and `/config` endpoints.
    *   Port `/chat` endpoint (routing logic only).
    *   Implement "Surprise Score" logic (math-heavy, ideal for Rust).
3.  **Client Layer:**
    *   Implement `EngineClient` struct using `reqwest` to talk to Vorpal/Goblin/Bifrost.
    *   Implement retry logic and timeout handling.

### Phase 3: Agent & Memory Logic (Weeks 4-5)
**Goal:** Port the complex ReAct and Memory logic.

1.  **Memory System:**
    *   Port `vector_store.py`: Implement vector embedding generation (call out to Vorpal) and Redis vector search queries.
    *   Implement the "Titans" memory management (Surprise Score calculation).
2.  **Agent Orchestration:**
    *   **Challenge:** OctoTools is Python.
    *   **Solution:** Rewrite the *orchestrator loop* (ReAct) in Rust. The "Tools" will be implemented as:
        *   *Native Tools:* (Time, Math, String manip) implemented in pure Rust.
        *   *Service Tools:* (Search, Code Exec) calls to `sandbox` or external APIs.
    *   Define `Agent` trait and `Worker` structs.

### Phase 4: The Librarian (Week 6)
**Goal:** High-performance file ingestion.

1.  **File Watcher:**
    *   Use `notify` crate to watch `Library-Drop`.
2.  **Processing:**
    *   Use `pdf-extract` or `lopdf` for PDF text extraction.
    *   Implement chunking algorithms (Rust string slicing is very fast).
    *   Push vectors to Redis.

---

## 4. Migration Strategy (Strangler Pattern)

We will not switch everything at once. We will use the **Strangler Fig Pattern**:

1.  **Proxy:** Configure the existing `brain` (Python) to proxy specific routes to `brain-rs` (Rust) as they are built.
    *   *Alternatively:* Update `docker-compose` to point port `8080` to the Rust container once critical paths (Chat/Health) are ready.
2.  **Parallel Run:** Run `librarian-rs` alongside `librarian` watching a different folder to verify output parity.

---

## 5. Dependency Mapping

| Python Package | Rust Crate Equivalent | Notes |
| :--- | :--- | :--- |
| `fastapi` | `axum` | Best-in-class, robust ecosystem. |
| `pydantic` | `serde` + `validator` | Serde handles JSON, Validator handles constraints. |
| `httpx` | `reqwest` | Async HTTP client. |
| `redis` | `redis` | Low-level, high performance. |
| `psutil` | `sysinfo` | System monitoring. |
| `watchdog` | `notify` | File system events. |
| `numpy` | `ndarray` | If needed for vector math (or plain `Vec<f32>`). |
| `PyPDF2` | `lopdf` | PDF parsing. |

---

## 6. Directory Structure Preview

```text
archive-ai-rs/
├── Cargo.toml              # Workspace definition
├── Dockerfile              # Multi-stage build
├── crates/
│   ├── shared/             # Common types, errors, config
│   │   ├── src/lib.rs
│   │   └── Cargo.toml
│   ├── brain/              # Main Orchestrator
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── routes/
│   │   │   ├── agents/
│   │   │   └── services/
│   │   └── Cargo.toml
│   └── librarian/          # Ingestion Service
│       ├── src/main.rs
│       └── Cargo.toml
```

## 7. Risks & Mitigation

1.  **Complexity of Agent Logic:** Porting dynamic Python agent loops to static Rust types can be tricky.
    *   *Mitigation:* Use `enum` dispatch for Agent States and `Box<dyn Tool>` traits for flexibility.
2.  **Redis Vector Support:** `redis-rs` is low-level.
    *   *Mitigation:* We may need to write raw Redis commands (FT.SEARCH) strings, which is error-prone but performant.
3.  **Learning Curve:** If the team is new to Rust, async ownership (Tokio) can be challenging.
    *   *Mitigation:* Start with `librarian` (simpler) before tackling `brain`.
