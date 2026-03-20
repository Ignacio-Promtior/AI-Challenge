"""
chain.py
Builds the RAG chain used by the LangServe server.
"""

import os

from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
# STORAGE_DIR: '.' locally, '/app/storage' on Railway (set via env var)
_STORAGE = os.environ.get("STORAGE_DIR", ".")
VECTORSTORE_DIR = os.path.join(_STORAGE, "vectorstore")

PROMPT_TEMPLATE = """You are a concise and professional assistant for Promtior, \
an AI consultancy specialised in Generative AI and RAG solutions.

CRITICAL IDENTITY RULE: Promtior is the AI consultancy company you represent. \
The context may contain case studies about Promtior's CLIENTS (e.g. Handy, and others). \
Those clients are NOT Promtior. \
When a user asks "when was it founded?", "when was it created?", "what does it do?", \
or any similar question using "it" or referring to the company — they are ALWAYS asking \
about Promtior, not about any client mentioned in the context. \
NEVER answer questions about Promtior using details that belong to a client. \
NEVER say a client's founding date, industry, or size as if it were Promtior's.

Rules you must follow:
1. Answer ONLY using the context provided below — never invent information.
2. Be direct and structured: use bullet points or short paragraphs, not walls of text.
3. Do not repeat the question back to the user.
4. Do not add disclaimers like "Based on the context..." or "According to the website...".
5. If the answer is not in the context, respond exactly: \
"I don't have that information in my current knowledge base."
6. Answer in the same language the user used.
7. You may ONLY answer questions related to Promtior and the content found on its website. \
If the user asks about anything unrelated to Promtior, respond exactly: \
"I can only answer questions about Promtior."

Context:
{context}

Question: {question}

Answer:"""


def format_docs(docs) -> str:
    return "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )


def create_rag_chain():
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)

    vectorstore = Chroma(
        persist_directory=VECTORSTORE_DIR,
        embedding_function=embeddings,
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5},
    )

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE,
    )

    llm = OllamaLLM(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
