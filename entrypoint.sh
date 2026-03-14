#!/bin/bash
set -e

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
MODEL="llama3.2:1b"
EMBEDDING_MODEL="nomic-embed-text"

echo "=== Promtior RAG Chatbot entrypoint ==="
echo "Ollama URL: $OLLAMA_BASE_URL"

# ── 1. Wait for Ollama to be ready ─────────────────────────────────────────
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" -o /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    echo "  Attempt $i/30 — Ollama not ready yet, retrying in 5 s..."
    sleep 5
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Ollama did not become available in time. Exiting."
        exit 1
    fi
done

# ── 2. Pull required models if not already present ─────────────────────────
for PULL_MODEL in "${MODEL}" "${EMBEDDING_MODEL}"; do
    echo "Checking if model '${PULL_MODEL}' is available..."
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" | grep -q "\"${PULL_MODEL}"; then
        echo "Model '${PULL_MODEL}' already downloaded."
    else
        echo "Pulling model '${PULL_MODEL}' — this may take several minutes..."
        curl -s "${OLLAMA_BASE_URL}/api/pull" \
            -d "{\"name\": \"${PULL_MODEL}\"}" \
            -H "Content-Type: application/json" | tail -1
        echo "Model '${PULL_MODEL}' pull complete."
    fi
done

# ── 3. Scrape website if data not yet collected ─────────────────────────────
if [ ! -f "/app/data/scraped_content.json" ]; then
    echo "No scraped data found. Running scraper..."
    python scraper.py
else
    echo "Scraped data already exists, skipping scraper."
fi

# ── 4. Build vector store if it does not exist ─────────────────────────────
if [ ! -d "/app/vectorstore" ] || [ -z "$(ls -A /app/vectorstore 2>/dev/null)" ]; then
    echo "Vector store not found. Running ingest..."
    python ingest.py
else
    echo "Vector store already exists, skipping ingestion."
fi

# ── 5. Start the LangServe API server ──────────────────────────────────────
echo "Starting LangServe server on port 8000..."
exec python server.py
