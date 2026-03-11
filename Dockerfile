FROM python:3.11-slim

# System dependencies needed by chromadb and other native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama using the official install script
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY scraper.py ingest.py chain.py server.py entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Default env vars — work for both Railway (single container) and local override via docker-compose
ENV OLLAMA_BASE_URL=http://localhost:11434
ENV EMBEDDING_MODEL=nomic-embed-text

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
