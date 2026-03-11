"""
server.py — Step 3
Starts the LangServe API server.
Usage: python server.py
Playground UI: http://localhost:8000/chat/playground
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
import os

from chain import create_rag_chain

app = FastAPI(
    title="Promtior RAG Chatbot",
    description=(
        "A Retrieval-Augmented Generation chatbot that answers questions "
        "about Promtior using content scraped from the official website."
    ),
    version="1.0.0",
)

# Allow all origins for local development — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build RAG chain and expose it via LangServe
rag_chain = create_rag_chain()

add_routes(
    app,
    rag_chain,
    path="/chat",
)


@app.get("/")
async def root():
    return {
        "message": "Promtior RAG Chatbot is running.",
        "docs": "/docs",
        "chat_endpoint": "/chat/invoke",
        "playground": "/chat/playground",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print("Starting Promtior RAG Chatbot server...")
    print(f"  Playground → http://localhost:{port}/chat/playground")
    print(f"  API docs   → http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
