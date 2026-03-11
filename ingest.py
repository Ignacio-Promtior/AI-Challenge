"""
ingest.py — Step 2
Loads scraped JSON + optional PDF, chunks the text, generates embeddings
with Ollama, and persists the Chroma vector store.
Usage: python ingest.py
"""

import json
import os
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

# When running inside Docker, Ollama is a separate service on the same network.
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
# Use a dedicated embedding model — much faster than llama2 for this task.
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

SCRAPED_FILE = "data/scraped_content.json"
PDF_FILE = "data/presentation.pdf"   # optional – place the Promtior PDF here
VECTORSTORE_DIR = "./vectorstore"
OLLAMA_MODEL = "llama2"  # used for embeddings; switch to nomic-embed-text if available


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_scraped_json(path: str) -> list[Document]:
    with open(path, "r", encoding="utf-8") as f:
        pages = json.load(f)
    return [
        Document(page_content=p["content"], metadata={"source": p["url"]})
        for p in pages
        if p.get("content", "").strip()
    ]


def load_pdf(path: str) -> list[Document]:
    from langchain_community.document_loaders import PyPDFLoader
    loader = PyPDFLoader(path)
    return loader.load()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ingest():
    documents: list[Document] = []

    # --- Web-scraped content ---
    if not os.path.exists(SCRAPED_FILE):
        raise FileNotFoundError(
            f"{SCRAPED_FILE} not found. Run 'python scraper.py' first."
        )
    print(f"Loading scraped content from {SCRAPED_FILE}...")
    docs = load_scraped_json(SCRAPED_FILE)
    print(f"  Loaded {len(docs)} web pages.")
    documents.extend(docs)

    # --- Optional PDF presentation ---
    if os.path.exists(PDF_FILE):
        print(f"Loading PDF from {PDF_FILE}...")
        pdf_docs = load_pdf(PDF_FILE)
        print(f"  Loaded {len(pdf_docs)} PDF pages.")
        documents.extend(pdf_docs)
    else:
        print(
            f"[INFO] No PDF found at {PDF_FILE}. "
            "Place the Promtior presentation there for extra context."
        )

    # --- Chunking ---
    print("Splitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"  Created {len(chunks)} chunks.")

    # --- Embeddings + Vector store ---
    print(f"Building vector store with Ollama embeddings (model={EMBEDDING_MODEL})...")
    print(f"  Ollama URL: {OLLAMA_BASE_URL}")
    print("  (This may take a few minutes the first time.)")
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTORSTORE_DIR,
    )
    print(f"\nVector store saved to '{VECTORSTORE_DIR}'. Ingestion complete.")


if __name__ == "__main__":
    ingest()
