# Quick Start Guide: Archive-AI User Interfaces (UI)

This guide provides instructions for accessing and running the user interfaces of the Archive-AI system. It assumes that the core backend services (Brain, LLMs, Redis, etc.) are already running.

---

## Prerequisites: Backend Services

Before proceeding, ensure that your Archive-AI backend services are up and running.
Please refer to the main **[QUICKSTART.md](QUICKSTART.md)** for detailed instructions on setting up and launching the backend.

Once the backend is confirmed to be running (e.g., via `bash scripts/health-check.sh`), you can proceed with the UI.

---

## 1. Web UI (Modern Chat Client)

The primary web-based chat client provides a clean, modern interface to interact with Archive-AI.

### Accessing the Web UI

1.  **Start with the master script:** Run `./start --web` to launch the backend and serve the UI on port 8888.
2.  **Open in Browser:** Navigate to:
    `http://localhost:8888`
    (Or directly via Brain at `http://localhost:8081/ui/index.html`)

### Features

*   **Chat:** Send messages to Archive-AI and receive responses.
*   **Mode Selection:** Switch between `Chat`, `Verified`, `Basic Agent`, and `Advanced Agent` modes.
*   **Quick Actions:** Use pre-defined buttons for time or calculations.
*   **API Connection:** Communicates with the Brain API at `http://localhost:8081`.

---

## 2. Flutter UI (Desktop Client)

A Flutter desktop application is available for a native experience. Unlike the web UI, this client is a standalone desktop app.

### Running the Flutter UI

1.  **Launch via Master Script:** Run `./start --gui` from the project root. This will start the backend and launch the Flutter app automatically.
2.  **Manual Start:**
    ```bash
    cd ui/flutter_ui
    flutter run -d linux
    ```

### Features

*   **Native Desktop Experience:** Runs as a standalone application on Linux (can be compiled for Windows/macOS).
*   **Live API Connection:** Connected to the Brain API at `http://localhost:8081`.
*   **Basic Chat:** Core conversation functionality.

This provides a basic visual representation of a desktop client for the system.

---

### Need Help?

For any issues with the backend services, refer to the troubleshooting section in the main **[QUICKSTART.md](QUICKSTART.md)** or consult the comprehensive **[USER_MANUAL.md](Docs/USER_MANUAL.md)**.
