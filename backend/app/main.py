"""FastAPI app exposing the research agent over a streaming HTTP endpoint.

Streaming design: LangGraph's `astream(state, stream_mode="updates")` yields
one dict per node execution, containing *only the fields that node
returned* (not the full accumulated state) — see the reducer note in
state.py for why that's true for the list fields. That maps directly onto
SSE: each node's trace entries get forwarded to the client the moment that
node finishes, so the frontend can render "Step 1: Planning..." etc. in real
time instead of waiting for the whole run to complete.

We use a hand-rolled `text/event-stream` response (not a library like
sse-starlette) because the framing is simple enough (`event: ...\ndata:
...\n\n`) that a dependency isn't worth it, and it keeps the request body a
POST (needed to send the question) — the browser's native EventSource only
supports GET, so the frontend consumes this with fetch + a ReadableStream
reader instead.
"""
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.graph import research_agent_graph
from app.agent.state import new_initial_state
from app.config import get_settings
from app.logging_config import configure_logging, get_agent_logger

configure_logging()
logger = get_agent_logger("api")

app = FastAPI(title="Research Agent API")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    question: str


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_research(question: str):
    initial_state = new_initial_state(question)
    accumulated_sources: list[dict] = []

    try:
        async for update in research_agent_graph.astream(initial_state, stream_mode="updates"):
            for node_name, partial in update.items():
                for source in partial.get("sources", []):
                    # The same tool (e.g. vector_search) can be picked for more than
                    # one plan step and return the same source each time; keep only
                    # the first occurrence so the frontend doesn't show duplicates.
                    if source not in accumulated_sources:
                        accumulated_sources.append(source)

                for trace_event in partial.get("trace", []):
                    yield _sse("trace", trace_event)

                if node_name == "finish":
                    yield _sse(
                        "done",
                        {
                            "final_answer": partial.get("final_answer"),
                            "sources": accumulated_sources,
                        },
                    )
    except Exception as exc:  # last-resort guard so the stream always ends cleanly
        logger.exception("Unhandled error while streaming research run")
        yield _sse("error", {"message": str(exc)})


@app.post("/api/research")
async def research(request: ResearchRequest):
    return StreamingResponse(
        _stream_research(request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx/proxy buffering when deployed
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
