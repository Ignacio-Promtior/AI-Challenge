FROM python:3.11-slim

# System dependencies needed by chromadb and other native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY scraper.py ingest.py chain.py server.py entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Persistent volumes will be mounted here at runtime
VOLUME ["/app/data", "/app/vectorstore"]

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
