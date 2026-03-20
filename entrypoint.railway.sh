#!/bin/bash
set -e

export PORT="${PORT:-8000}"
# Must be set in Railway to the Ollama service private URL
# e.g. http://ollama.railway.internal:11434
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"
# Single volume mounted at /app/storage on Railway
export STORAGE_DIR="/app/storage"

LLM_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"

echo "=== Promtior RAG Chatbot (Railway) ==="
echo "  PORT            : $PORT"
echo "  OLLAMA_BASE_URL : $OLLAMA_BASE_URL"
echo "  STORAGE_DIR     : $STORAGE_DIR"

# Create storage subdirs inside the mounted volume
mkdir -p "${STORAGE_DIR}/data" "${STORAGE_DIR}/vectorstore"

# ── 1. Wait for Ollama service to be ready ─────────────────────────────────
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 40); do
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" -o /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    sleep 5
    if [ "$i" -eq 40 ]; then
        echo "ERROR: Ollama not reachable at ${OLLAMA_BASE_URL}. Set OLLAMA_BASE_URL in Railway env vars."
        exit 1
    fi
done

# ── 2. Pull required models if not already cached in Ollama service ────────
for PULL_MODEL in "${LLM_MODEL}" "${EMBEDDING_MODEL}"; do
    echo "Checking model '${PULL_MODEL}'..."
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" | grep -q "\"${PULL_MODEL}"; then
        echo "  Already downloaded."
    else
        echo "  Pulling '${PULL_MODEL}' — this may take several minutes..."
        curl -s "${OLLAMA_BASE_URL}/api/pull" \
            -d "{\"name\": \"${PULL_MODEL}\"}" \
            -H "Content-Type: application/json" | tail -1
        # Verify the model is actually registered after pull
        echo "  Verifying '${PULL_MODEL}' is available..."
        for j in $(seq 1 10); do
            if curl -sf "${OLLAMA_BASE_URL}/api/tags" | grep -q "\"${PULL_MODEL}"; then
                echo "  Done."
                break
            fi
            echo "  Model not yet visible, waiting 3s... ($j/10)"
            sleep 3
            if [ "$j" -eq 10 ]; then
                echo "ERROR: Model '${PULL_MODEL}' not available after pull. Exiting."
                exit 1
            fi
        done
    fi
done

# ── 3. Scrape website if needed ────────────────────────────────────────────
if [ ! -f "${STORAGE_DIR}/data/scraped_content.json" ]; then
    echo "Scraping Promtior website..."
    python scraper.py
else
    echo "Scraped data already exists, skipping scraper."
fi

# ── 4. Build vector store if needed ───────────────────────────────────────
if [ ! -d "${STORAGE_DIR}/vectorstore" ] || [ -z "$(ls -A ${STORAGE_DIR}/vectorstore 2>/dev/null)" ]; then
    echo "Building vector store..."
    python ingest.py
else
    echo "Vector store already exists, skipping ingestion."
fi

# ── 5. Start LangServe server ──────────────────────────────────────────────
echo "Starting server on port ${PORT}..."
exec python server.py
