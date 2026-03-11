#!/bin/bash
set -e

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
MODEL="llama2"
EMBEDDING_MODEL="nomic-embed-text"

echo "=== Promtior RAG Chatbot entrypoint ==="
echo "Ollama URL: $OLLAMA_BASE_URL"

# ── 1. Start the API server immediately so Railway healthcheck passes ────────
echo "Starting API server in background..."
python server.py &
SERVER_PID=$!

# ── 2. Wait for Ollama to be ready ──────────────────────────────────────────
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 60); do
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" -o /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    echo "  Attempt $i/60 — Ollama not ready yet, retrying in 5 s..."
    sleep 5
    if [ "$i" -eq 60 ]; then
        echo "ERROR: Ollama did not become available in time. Exiting."
        exit 1
    fi
done

# ── 3. Pull required models if not already present ──────────────────────────
for PULL_MODEL in "${MODEL}" "${EMBEDDING_MODEL}"; do
    echo "Checking if model '${PULL_MODEL}' is available..."
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" | grep -q "\"${PULL_MODEL}\""; then
        echo "Model '${PULL_MODEL}' already downloaded."
    else
        echo "Pulling model '${PULL_MODEL}' — this may take several minutes..."
        curl -s "${OLLAMA_BASE_URL}/api/pull" \
            -d "{\"name\": \"${PULL_MODEL}\"}" \
            -H "Content-Type: application/json" | tail -1
        echo "Model '${PULL_MODEL}' pull complete."
    fi
done

# ── 4. Scrape website if data not yet collected ──────────────────────────────
NEED_INGEST=false
# Re-scrape if file missing, empty array, or contains binary/corrupt content
SCRAPE_FILE="/app/data/scraped_content.json"
if [ ! -f "$SCRAPE_FILE" ] || [ "$(cat "$SCRAPE_FILE")" = "[]" ] || ! python3 -c "
import json, sys
data = json.load(open('$SCRAPE_FILE'))
if not data: sys.exit(1)
content = data[0].get('content','')
# Fail if more than 5% of characters are non-printable (binary garbage)
non_print = sum(1 for c in content if ord(c) < 32 and c not in '\n\r\t')
if non_print / max(len(content),1) > 0.05: sys.exit(1)
" 2>/dev/null; then
    echo "No scraped data found. Running scraper..."
    python scraper.py
    NEED_INGEST=true  # fresh scrape → must rebuild vectorstore
else
    echo "Scraped data already exists, skipping scraper."
fi

# ── 5. Build vector store if it does not exist or data was just scraped ──────
if [ "$NEED_INGEST" = "true" ] || [ ! -d "/app/vectorstore" ] || [ -z "$(ls -A /app/vectorstore 2>/dev/null)" ]; then
    echo "Building vector store..."
    rm -rf /app/vectorstore  # ensure clean rebuild
    python ingest.py
else
    echo "Vector store already exists, skipping ingestion."
fi

echo "Setup complete. Restarting server with populated vector store..."

# ── 6. Kill background server, then restart in foreground with data ready ────
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true

echo "Starting API server in foreground..."
exec python server.py
