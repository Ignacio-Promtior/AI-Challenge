"""
server.py — Step 3
Starts the LangServe API server.
Usage: python server.py
Playground UI: http://localhost:8000/chat/playground
"""

from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langserve import add_routes

from chain import create_rag_chain

app = FastAPI(
    title="Promtior RAG Chatbot",
    description=(
        "A Retrieval-Augmented Generation chatbot that answers questions "
        "about Promtior using content scraped from the official website."
    ),
    version="1.0.0",
)

# Allow all origins — no credentials needed for a public chatbot API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
        "ui": "/ui",
    }


# Serve the static frontend — must be mounted AFTER all API routes
if os.path.isdir("frontend"):
    app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Promtior RAG Chatbot server on port {port}...")
    print(f"  Playground → http://localhost:{port}/chat/playground")
    print(f"  API docs   → http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
