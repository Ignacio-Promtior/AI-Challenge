# AI-Challenge — Promtior RAG Chatbot

A **Retrieval-Augmented Generation (RAG)** chatbot that answers questions about the [Promtior](https://www.promtior.ai) website, built with **LangChain + LangServe + Ollama (LLaMA 3.1 8B)**.

---

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   scraper.py    │───▶│   ingest.py      │───▶│   server.py     │
│                 │    │                  │    │                 │
│ Crawls Promtior │    │ Chunks text,     │    │ LangServe API   │
│ website pages   │    │ creates embeddings    │ /chat/invoke    │
│ → JSON file     │    │ → ChromaDB       │    │ /chat/playground│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               ▲                        │
                       OllamaEmbeddings          Ollama LLaMA 3.1 8B
                       (nomic-embed-text)         generative LLM
```

### Deployment architecture

**Local (Docker Compose):** two containers on the same Docker network — `promtior_app` + `promtior_ollama`.

**Production (Railway):** two independent Railway services communicating over the private network — one running the official `ollama/ollama` image, the other built from `Dockerfile.railway`.

> **Live demo:** [https://ai-challenge-production-b6b2.up.railway.app/ui/](https://ai-challenge-production-b6b2.up.railway.app/ui/)

## Files

| File | Purpose |
|------|---------|
| `scraper.py` | Crawls the Promtior website and saves content to `data/scraped_content.json` |
| `ingest.py` | Loads scraped content (+ optional PDF), chunks it, and builds the ChromaDB vector store |
| `chain.py` | Defines the LangChain RAG chain (retriever → prompt → LLM) |
| `server.py` | Starts the LangServe FastAPI server |
| `Dockerfile` | Builds the chatbot application image (local Docker) |
| `docker-compose.yml` | Orchestrates the app + Ollama containers locally |
| `entrypoint.sh` | Local container startup script (waits for Ollama, pulls models, scrapes, ingests, serves) |
| `Dockerfile.railway` | Builds the app image for Railway (no Ollama binary) |
| `entrypoint.railway.sh` | Railway startup script (connects to external Ollama service) |
| `railway.toml` | Railway build & deploy configuration |
| `requirements.txt` | Python dependencies |
| `frontend/index.html` | Standalone chat UI served by FastAPI at `/ui` |

---

## Running with Docker (recommended)

The easiest way to run the full stack. **Docker + Docker Compose** are the only prerequisites — no Python installation needed locally.

```bash
docker compose up --build
```

That single command will:
1. Build the chatbot image
2. Start the Ollama service
3. Wait for Ollama to be ready
4. Pull the LLaMA 3.1 8B model (first run only — ~4.7 GB)
5. Scrape the Promtior website (first run only)
6. Build the ChromaDB vector store (first run only)
7. Start the LangServe API at **http://localhost:8000**

> **GPU acceleration (NVIDIA):** Uncomment the `deploy` block in `docker-compose.yml` to enable GPU support (requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)).

> **Optional PDF:** Place the Promtior presentation at `data/presentation.pdf` before the first run.

> **PDF on Railway:** The `data/presentation.pdf` is not baked into the Railway image. To include it in a Railway deployment, upload the file manually to the persistent volume at `/app/storage/data/presentation.pdf` before the first startup.

### Stopping the stack

```bash
docker compose down
```

Data is persisted in `./data/`, `./vectorstore/`, and the `ollama_data` Docker volume — so subsequent starts skip the expensive first-time steps.

---

## Running locally (without Docker)

### Prerequisites

### 1. Python 3.10+

### 2. Ollama with LLaMA 3.1 8B

Install [Ollama](https://ollama.com) and pull the model:

```bash
ollama pull llama3.1:8b
```

Confirm it runs:

```bash
ollama run llama3.1:8b
```

---

## Setup

```bash
# 1. Clone / open the project
cd AI-Challenge

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the chatbot (3 steps)

### Step 1 — Scrape the Promtior website

```bash
python scraper.py
```

This creates `data/scraped_content.json` with the text from all crawled pages.

> **Optional (extra points):** Download the Promtior presentation PDF and save it as `data/presentation.pdf`. The ingestion script will automatically include it.

### Step 2 — Build the vector store

```bash
python ingest.py
```

This chunks all documents, generates embeddings with Ollama, and persists a ChromaDB vector store in `./vectorstore/`.

> *This step can take several minutes the first time.*

### Step 3 — Start the server

```bash
python server.py
```

The API is now live at **http://localhost:8000**.

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `POST /chat/invoke` | Ask a question (JSON) |
| `GET /ui` | Chat web UI (browser) |
| `GET /chat/playground` | Interactive LangServe UI |
| `GET /docs` | Swagger / OpenAPI docs |

---

## Usage examples

### Chat UI (recommended)

Open your browser at:  
**http://localhost:8000/ui**

### cURL

```bash
curl -X POST http://localhost:8000/chat/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "What services does Promtior offer?"}'
```

```bash
curl -X POST http://localhost:8000/chat/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "When was Promtior founded?"}'
```

### Python client

```python
import requests

response = requests.post(
    "http://localhost:8000/chat/invoke",
    json={"input": "What services does Promtior offer?"},
)
print(response.json()["output"])
```

---

## Design decisions

- **Embeddings:** `nomic-embed-text` via Ollama — specialized for plain text, ~15x faster than using the generative LLM for embeddings (~2s vs ~30s per chunk).
- **LLM:** LLaMA 3.1 8B via Ollama (local, no API key required). Configured in `chain.py` via `OLLAMA_MODEL`.
- **Vector store:** ChromaDB (persistent on disk — vectorstore is not rebuilt on restarts if the directory already exists).
- **Chunking:** `RecursiveCharacterTextSplitter` with 1 000-character chunks and 150-character overlap to preserve context across chunk boundaries.
- **Retrieval:** Top-5 most similar chunks are injected into the prompt.
- **Sources:** Each retrieved chunk carries its origin URL in the metadata, making answers traceable.
