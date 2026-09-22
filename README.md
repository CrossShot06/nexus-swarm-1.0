# Nexus Swarm 1.0 🚀

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/Django-ASGI-green.svg)
![Docker](https://img.shields.io/badge/Docker-Sandboxed-2496ED.svg)
![Ollama](https://img.shields.io/badge/AI-Llama_3.1_%7C_Qwen_2.5-orange.svg)
![Celery](https://img.shields.io/badge/Celery-Redis-yellow.svg)

**Nexus Swarm** is an intelligent, fault-tolerant, and self-healing automated C++ code generation, compilation, and execution framework. 

Built with enterprise-grade system architecture, it leverages a **Dual-AI Agent** system orchestrated within an asynchronous Django backend. Generated code is securely compiled and executed in a highly restricted, headless Alpine Docker sandbox, ensuring an isolated environment protected against runaway processes and malicious code.

## 🌟 Key Features

### 1. Dual-AI Brain Architecture
- **The Architect (Llama 3.1)**: Acts as the Senior Software Architect. It processes the user's prompt, establishes system constraints, and drafts a strict, step-by-step technical blueprint without writing syntax.
- **The Developer (Qwen 2.5 Coder 7B)**: Acts as the execution layer. It ingests the architectural blueprint and outputs syntactically correct, highly optimized C++ code. This separation of concerns prevents context degradation and hallucination.

### 2. Enterprise Task Orchestration
- **Asynchronous Processing**: Utilizes **Celery** and **Redis** as a message broker to decouple the web layer from the compute-heavy AI execution layer. 
- **Concurrency Control**: A strictly bounded worker pool mathematically guarantees the host machine's memory budget is never exceeded, regardless of traffic spikes.

### 3. Hardened Docker Sandbox Orchestration
- **Secure Execution**: The framework dynamically spins up an isolated Alpine Linux Docker container (`nexus-swarm:latest`) to compile and run untrusted AI-generated code.
- **Zero-Trust Resource Constraints**: 
  - Hard limit of 512MB RAM.
  - Complete network isolation (air-gapped).
  - `--pids-limit` enforced to instantly neutralize C++ fork bombs.
  - 3-second `SIGKILL` timeout to prevent infinite loops.

### 4. AI Self-Healing & Telemetry Interceptor
- **LangGraph State Machine**: Orchestrates the autonomous debugging loop.
- **Compiler/Runtime Error Catching**: If compilation fails or the binary crashes (e.g., segmentation faults), the Python orchestrator intercepts `stderr`, hashes the error signature, and feeds it back to the AI for a targeted rewrite.
- **Auto-Retries**: The swarm is granted up to 5 self-healing iterations to resolve logic or syntax errors autonomously before returning a final state.

### 5. Interactive Orbital Command UI
- **Live Telemetry via SSE**: The Django ASGI (Daphne) backend maintains long-lived Server-Sent Event (SSE) connections to stream live execution logs, compilation status, and stdout directly to a sci-fi themed tactical dashboard.
- **Mission Archive (PostgreSQL)**: Persistently stores execution logs, generated blueprints, and C++ source code using ACID-compliant transactions and MVCC to handle concurrent workflow completions.

---

## 🏗️ System Architecture Workflow

1. **Uplink Directive**: User submits a prompt via the UI. Django instantly pushes the task to the **Redis** broker and returns an SSE connection endpoint.
2. **Task Ingestion**: A **Celery** worker picks up the task and triggers the LangGraph state machine.
3. **Blueprint & Code Generation**: Llama 3.1 drafts the architecture; Qwen 2.5 writes the C++.
4. **Sandboxed Compilation**: Code is mounted into the Alpine Docker container and compiled via `g++`.
5. **Self-Healing Loop**: If `stderr` is detected, the error is parsed and sent back to Qwen 2.5 for an automatic rewrite.
6. **Execution & Archiving**: Upon success, the binary output is streamed back to the client via Redis Pub/Sub -> Daphne SSE, and the final state is committed to **PostgreSQL**.

---

## 🛠️ Local Setup & Installation

### Prerequisites
- **Docker** & **Docker Compose**
- **Ollama** (with models pulled locally)
- **Python 3.10+**
- **Redis** server running locally or via Docker.

### 1. Pull AI Models
Ensure Ollama is running, then pull the required models:
```bash
ollama run llama3.1
ollama run qwen2.5-coder:7b
```

### 2. Build the Sandbox Environment
Build the custom Alpine C++ compiler image used for untrusted execution:
```bash
python build_image.py
# Or manually: docker build -t nexus-swarm:latest .
```

### 3. Install Backend Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Start the Infrastructure
You will need three terminal windows to run the full stack locally:

**Terminal 1: Start Redis**
```bash
redis-server
```

**Terminal 2: Start the Celery Worker**
```bash
celery -A nexus_core worker -l info
```

**Terminal 3: Start the ASGI Web Server**
```bash
daphne -p 8000 nexus_core.asgi:application
```

### 5. Launch
Navigate to `http://localhost:8000` in your browser to access the Orbital Command dashboard.

---

## 🛡️ License & Security Disclaimer
This project handles the autonomous execution of untrusted C++ code. While strict containerization and OS-level limits are in place, deploying this on a public-facing production server requires additional infrastructure hardening (e.g., Kubernetes gVisor, firecracker microVMs). Use at your own risk.
