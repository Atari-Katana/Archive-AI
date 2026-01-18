
I have reorganized the Docker containers and standardized the configuration across the codebase.

### **Changes Implemented**

**1. Standardized Port Architecture**
All internal services now follow a consistent convention: **Internal Port 8000** (where possible) mapped to unique Host Ports.

| Service | Internal Port | Host Port | Internal Docker URL |
| :--- | :--- | :--- | :--- |
| **Brain** (Orchestrator) | **8000** | **8080** | `http://brain:8000` |
| **Bifrost** (Gateway) | 8080 | **8081** | `http://bifrost:8080` |
| **Vorpal** (Engine A) | 8000 | **8002** | `http://vorpal:8000` |
| **Goblin** (Engine B) | 8080 | **8003** | `http://goblin:8080` |
| **Sandbox** (Code Exec) | 8000 | **8004** | `http://sandbox:8000` |
| **Voice** (Audio I/O) | **8000** | **8005** | `http://voice:8000` |
| **Redis** | 6379 | 6379 | `redis:6379` |

**2. Updated Configuration Files**
*   **`docker-compose.yml`**: Rewritten with new port mappings and container names.
*   **`.env.example`**: Updated with the new standard ports.
*   **`brain/config.py`**: Default service URLs now point to the correct internal ports (e.g., `http://brain:8000`, `http://voice:8000`).
*   **`brain/main.py`**: Updated to listen on port 8000.
*   **`voice/server.py`**: Updated to listen on port 8000.
*   **`scripts/start`**: Updated health check and UI links to use port 8080.

**3. Rebuilt Containers**
*   Updated `Dockerfile` for `brain` and `voice` to expose port 8000.
*   Successfully rebuilt all images (`docker-compose build`).

### **Next Steps**
Run the start script to launch the standardized stack:
```bash
./start
```
The Brain API will now be available at **http://localhost:8080**.
