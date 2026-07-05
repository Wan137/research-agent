"""Web search tool via the Tavily API (search purpose-built for AI agents —
returns concise, LLM-ready snippets instead of raw HTML). Tavily's client is
synchronous, so the call is offloaded to a thread to avoid blocking the
event loop that's also serving the SSE stream."""
import asyncio

from app.agent.errors import ToolError
from app.agent.state import AgentState, ToolResult
from app.config import get_settings


def _sync_search(api_key: str, query: str) -> dict:
    from tavily import TavilyClient  # imported lazily so a missing package only breaks this tool

    client = TavilyClient(api_key=api_key)
    return client.search(query=query, max_results=4)


async def web_search(query: str, state: AgentState) -> ToolResult:
    settings = get_settings()
    if not settings.tavily_api_key:
        raise ToolError(
            "TAVILY_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add a free key from https://tavily.com"
        )

    try:
        response = await asyncio.to_thread(_sync_search, settings.tavily_api_key, query)
    except ImportError as exc:
        raise ToolError("tavily-python is not installed. Run: pip install tavily-python") from exc
    except Exception as exc:
        raise ToolError(f"Tavily search failed: {exc}") from exc

    results = response.get("results", [])
    if not results:
        return {"output": "No web search results found.", "sources": []}

    lines = []
    sources = []
    for result in results:
        title = result.get("title") or "Untitled"
        snippet = (result.get("content") or "").strip()[:300]
        lines.append(f"- {title}: {snippet}")
        sources.append({"title": title, "url": result.get("url", "")})

    return {"output": "\n".join(lines), "sources": sources}
