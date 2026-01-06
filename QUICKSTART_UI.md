# Quick Start Guide: Archive-AI User Interfaces (UI)

This guide provides instructions for accessing and running the user interfaces of the Archive-AI system. It assumes that the core backend services (Brain, LLMs, Redis, etc.) are already running.

---

## Prerequisites: Backend Services

Before proceeding, ensure that your Archive-AI backend services are up and running.
Please refer to the main **[QUICKSTART.md](QUICKSTART.md)** for detailed instructions on setting up and launching the backend.

Once the backend is confirmed to be running (e.g., via `bash scripts/health-check.sh`), you can proceed with the UI.

---

## 1. Web UI (Functional Chat Client)

The primary web-based chat client provides a simple and functional interface to interact with the Archive-AI.

### Accessing the Web UI

1.  **Ensure backend is running:** If you've just started with `./go.sh`, the web UI should be accessible automatically.
2.  **Open in Browser:** Navigate to the following URL in your web browser:
    `http://localhost:8080/ui/index.html`

### Features

*   **Chat:** Send messages to the Archive-AI and receive responses.
*   **Mode Selection:** Switch between `Chat`, `Verified`, `Basic Agent`, and `Advanced Agent` modes.
*   **Quick Actions:** Use pre-defined buttons to quickly ask for time or perform calculations.
*   **API Connection:** The UI is pre-configured to communicate with the Brain API at `http://localhost:8080`.

---

## 2. Flutter UI (Basic Desktop Client)

A basic Flutter desktop application is available as a proof-of-concept client. This client offers fundamental chat functionality with simulated responses and is not yet connected to the backend API.

### Running the Flutter UI

1.  **Navigate to the Flutter project directory:**
    ```bash
    cd ui/flutter_ui
    ```
2.  **Ensure Flutter SDK is installed and configured.** If not, follow the official Flutter installation guide for your operating system.
3.  **Run the application (Linux example):**
    ```bash
    flutter run -d linux
    ```
    *   Replace `linux` with `windows` or `macos` if you have configured Flutter for those desktop platforms.
    *   The application will compile and launch in a new desktop window.

### Features

*   **Basic Chat Interface:** Type messages and see them appear in the chat log.
*   **Simulated Responses:** The client will provide a simulated reply to your messages. (Note: This version is NOT connected to the Archive-AI backend).

This provides a basic visual representation of a desktop client for the system.

---

### Need Help?

For any issues with the backend services, refer to the troubleshooting section in the main **[QUICKSTART.md](QUICKSTART.md)** or consult the comprehensive **[USER_MANUAL.md](Docs/USER_MANUAL.md)**.
