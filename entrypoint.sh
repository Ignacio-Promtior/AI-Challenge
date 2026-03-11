#!/bin/bash
set -e

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama.railway.internal:11434}"
MODEL="llama2"
EMBEDDING_MODEL="nomic-embed-text"

echo "=== Promtior RAG Chatbot entrypoint ==="
echo "Ollama URL: $OLLAMA_BASE_URL"

# ── 1. Wait for Ollama to be ready ──────────────────────────────────────────
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 60); do
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" -o /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    echo "  Attempt $i/60 — not ready yet, retrying in 5 s..."
    sleep 5
    if [ "$i" -eq 60 ]; then
        echo "ERROR: Ollama did not become available in time."
        exit 1
    fi
done

# ── 2. Pull required models if not already present ──────────────────────────
for PULL_MODEL in "${MODEL}" "${EMBEDDING_MODEL}"; do
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" | grep -q "\"${PULL_MODEL}\""; then
        echo "Model '${PULL_MODEL}' already present."
    else
        echo "Pulling model '${PULL_MODEL}' — this may take several minutes..."
        curl -s "${OLLAMA_BASE_URL}/api/pull" \
            -d "{\"name\": \"${PULL_MODEL}\"}" \
            -H "Content-Type: application/json" | tail -1
        echo "Model '${PULL_MODEL}' pull complete."
    fi
done

# ── 3. Scrape website if data not yet collected ──────────────────────────────
if [ ! -f "/app/data/scraped_content.json" ] || [ "$(cat /app/data/scraped_content.json)" = "[]" ]; then
    echo "No scraped data found. Running scraper..."
    python scraper.py
    echo "Rebuilding vector store with fresh data..."
    rm -rf /app/vectorstore
    python ingest.py
elif [ ! -d "/app/vectorstore" ] || [ -z "$(ls -A /app/vectorstore 2>/dev/null)" ]; then
    echo "Vector store missing. Running ingest..."
    python ingest.py
else
    echo "Data and vector store already exist, skipping setup."
fi

echo "Setup complete. Starting API server..."
exec python server.py
