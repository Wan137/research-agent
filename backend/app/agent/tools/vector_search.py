"""Vector search over a small local knowledge base (in-memory ChromaDB).

Seeded with a handful of placeholder documents about this project's own
tech stack, so the tool is demonstrably functional before real documents are
added (swap `_SEED_DOCS` for a real ingestion pipeline later — see README).

ChromaDB's client is synchronous and its default embedding function loads a
local model on first use, so both collection setup and queries are offloaded
to a thread to avoid blocking the event loop.
"""
import asyncio

from app.agent.errors import ToolError
from app.agent.state import AgentState, ToolResult

_SEED_DOCS = [
    {
        "id": "langgraph",
        "title": "LangGraph",
        "url": "https://langchain-ai.github.io/langgraph/",
        "text": (
            "LangGraph is a library for building stateful, multi-actor applications with "
            "LLMs. It models an agent as a graph of nodes and edges over a shared state "
            "object, supporting cycles, conditional branching, and streaming of "
            "intermediate steps — unlike a linear LangChain chain."
        ),
    },
    {
        "id": "groq",
        "title": "Groq LPU Inference",
        "url": "https://groq.com/",
        "text": (
            "Groq provides an API for very fast LLM inference on its custom LPU hardware, "
            "with a free tier suitable for prototyping. It hosts open models such as "
            "Llama 3.3 70B."
        ),
    },
    {
        "id": "tavily",
        "title": "Tavily Search API",
        "url": "https://tavily.com/",
        "text": (
            "Tavily is a search API purpose-built for AI agents. It returns concise, "
            "LLM-ready results rather than raw HTML, and has a free tier for developers."
        ),
    },
    {
        "id": "sse",
        "title": "Server-Sent Events",
        "url": "https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events",
        "text": (
            "Server-Sent Events (SSE) let a server push a stream of text/event-stream "
            "frames to a client over a single long-lived HTTP response. It's a good fit "
            "for streaming an agent's incremental reasoning steps to a frontend."
        ),
    },
    {
        "id": "chromadb",
        "title": "ChromaDB",
        "url": "https://www.trychroma.com/",
        "text": (
            "Chroma is an open-source embedding database. It stores documents alongside "
            "vector embeddings and supports similarity search, making it a common choice "
            "for retrieval-augmented generation (RAG) knowledge bases."
        ),
    },
]

_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    import chromadb

    client = chromadb.Client()  # in-memory; reseeded each process start
    collection = client.get_or_create_collection("research_agent_kb")
    if collection.count() == 0:
        collection.add(
            ids=[doc["id"] for doc in _SEED_DOCS],
            documents=[doc["text"] for doc in _SEED_DOCS],
            metadatas=[{"title": doc["title"], "url": doc["url"]} for doc in _SEED_DOCS],
        )
    _collection = collection
    return collection


def _sync_query(query: str) -> dict:
    collection = _get_collection()
    return collection.query(query_texts=[query], n_results=2)


async def vector_search(query: str, state: AgentState) -> ToolResult:
    try:
        results = await asyncio.to_thread(_sync_query, query)
    except ImportError as exc:
        raise ToolError("chromadb is not installed. Run: pip install chromadb") from exc
    except Exception as exc:
        raise ToolError(f"Vector search failed: {exc}") from exc

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]

    if not documents:
        return {"output": "No relevant documents found in the local knowledge base.", "sources": []}

    lines = []
    sources = []
    for text, meta in zip(documents, metadatas):
        lines.append(f"- ({meta['title']}) {text}")
        sources.append({"title": meta["title"], "url": meta["url"]})

    return {"output": "\n".join(lines), "sources": sources}
