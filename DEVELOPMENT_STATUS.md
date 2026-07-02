# 📍 Web Scout ADK: Development Status & Next Steps

This file serves as a live handoff document detailing the architecture, current codebase state, and how to resume work.

---

## 🛠️ Codebase Architecture & File Sitemap

1.  **SQLite Registry (`app/signatures.db`):** 
    *   Saves web scripts and technologies to avoid redundant LLM queries.
    *   Connector implemented in [app/repository.py](file:///Users/marcocardoso/DEV/web-scout-adk/app/repository.py).
    *   Query/inspect programmatically via [inspect_signatures.py](file:///Users/marcocardoso/DEV/web-scout-adk/inspect_signatures.py).
2.  **Gemini Core Agent (`app/agent.py`):**
    *   Main Google ADK reasoning agent structure (`root_agent`).
    *   Configured to use **`gemini-2.5-pro`** (to bypass 20-request daily limit of `2.5-flash`).
3.  **Groq Standalone Pipeline (`app/groq_agent.py`):**
    *   A zero-rate-limit alternative script that runs entirely on **Llama 3.3** via Groq.
    *   Uses SQLite signature caching, Llama self-healing, and compiles the canvas.
4.  **Local Web Dashboard (`app/web_server.py` & `app/static/`):**
    *   FastAPI backend routing searches and serving index.html.
    *   Serves the canvas HTML at `/sandbox` to bypass browser iframe local file security blocks.
5.  **Groq Evaluation Harness (`app/groq_eval.py`):**
    *   Local test runner executing our cases and grading via Llama-3.3-70b as the judge.

---

## 🚀 How to Run the Project Locally

### 1. Requirements Setup
Verify your `.env` contains:
```bash
GEMINI_API_KEY=your-api-key
GROQ_API_KEY=your-groq-key
```

### 2. Launching the Web UI Control Center
Start the local FastAPI server:
```bash
uv run python app/web_server.py
```
👉 Open **http://localhost:8080** in your browser.

### 3. Running a CLI Scan
To run a direct command-line scan using Groq:
```bash
uv run python app/groq_agent.py <target-url>
```

### 4. Running the Evaluations (Test Suite)
To run the local LLM-judge grading scorecard:
```bash
uv run python app/groq_eval.py
```

---

## 📋 Outstanding Next Steps (Where to Pick Up Next)

When you return to this project, you can choose to work on:
*   **Next Step 1: Upgrade to Google Cloud Run:**
    Enhance the repository configurations to prepare it for deployment:
    ```bash
    agents-cli scaffold enhance . --deployment-target cloud_run
    ```
    This will generate Dockerfiles and Terraform configs so you can put your FastAPI dashboard online.
*   **Next Step 2: Implement dynamic logs streaming in the Web UI:**
    Refactor the API in `/api/scan` to stream stdout logs using FastAPI `StreamingResponse` to show real-time progress on the dashboard terminal widget.
*   **Next Step 3: Expand the SQLite signatures database:**
    Add more seeded regex patterns in `app/repository.py` for common frontend frameworks (like React, Svelte, Vue) to prevent unnecessary LLM self-healing calls on those libraries.
