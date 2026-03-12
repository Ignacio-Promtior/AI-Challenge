# AI-Challenge — Promtior RAG Chatbot

A **Retrieval-Augmented Generation (RAG)** chatbot that answers questions about the [Promtior](https://www.promtior.ai) website, built with **LangChain + LangServe + Ollama (LLaMA 2)**.

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
                       OllamaEmbeddings          Ollama LLaMA 2
                       (LLaMA 2)                 retriever + LLM
```

## Files

| File | Purpose |
|------|---------|
| `scraper.py` | Crawls the Promtior website and saves content to `data/scraped_content.json` |
| `ingest.py` | Loads scraped content (+ optional PDF), chunks it, and builds the ChromaDB vector store |
| `chain.py` | Defines the LangChain RAG chain (retriever → prompt → LLM) |
| `server.py` | Starts the LangServe FastAPI server |
| `Dockerfile` | Builds the chatbot application image |
| `docker-compose.yml` | Orchestrates the app + Ollama containers |
| `entrypoint.sh` | Container startup script (waits for Ollama, pulls model, scrapes, ingests, serves) |
| `requirements.txt` | Python dependencies |

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
4. Pull the LLaMA 2 model (first run only — ~4 GB)
5. Scrape the Promtior website (first run only)
6. Build the ChromaDB vector store (first run only)
7. Start the LangServe API at **http://localhost:8000**

> **GPU acceleration (NVIDIA):** Uncomment the `deploy` block in `docker-compose.yml` to enable GPU support (requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)).

> **Optional PDF:** Place the Promtior presentation at `data/presentation.pdf` before the first run.

### Stopping the stack

```bash
docker compose down
```

Data is persisted in `./data/`, `./vectorstore/`, and the `ollama_data` Docker volume — so subsequent starts skip the expensive first-time steps.

---

## Running locally (without Docker)

### Prerequisites

### 1. Python 3.10+

### 2. Ollama with LLaMA 2

Install [Ollama](https://ollama.com) and pull the model:

```bash
ollama pull llama2
```

Confirm it runs:

```bash
ollama run llama2
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
| `GET /chat/playground` | Interactive browser UI |
| `GET /docs` | Swagger / OpenAPI docs |

---

## Usage examples

### Interactive playground (recommended)

Open your browser at:  
**http://localhost:8000/chat/playground**

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

- **LLM & Embeddings:** Ollama + LLaMA 2 (local, no API key required). Swap `OLLAMA_MODEL` in `chain.py` and `ingest.py` to `nomic-embed-text` for better embedding quality.
- **Vector store:** ChromaDB (persistent, no external service needed).
- **Chunking:** `RecursiveCharacterTextSplitter` with 1 000-token chunks and 150-token overlap to preserve context across chunk boundaries.
- **Retrieval:** Top-5 most similar chunks are injected into the prompt.
- **Sources:** The model cites the URL of each retrieved chunk so answers are traceable.
