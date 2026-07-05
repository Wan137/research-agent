# Research Agent

An AI agent that answers complex questions by autonomously planning, calling tools, and
self-verifying its own answer before responding — with the full reasoning process streamed
live to the frontend.

## Architecture

The agent is a [LangGraph](https://langchain-ai.github.io/langgraph/) state graph, not a linear
chain. Each node reads/writes a shared `AgentState` and control flow between them is decided by
the state at runtime, which is what lets the agent loop (call more than one tool, or redo work
after failing its own review) instead of always executing the same fixed sequence of steps.

```
START -> planner -> tool_router --(step remaining)--> executor -\
                        ^                                        |
                        |------------------(loop)------------------
                        |
                        '--(draft answer ready)--> critique --(rejected, retries left)--> tool_router
                                                        |
                                                        '--(approved / retries exhausted)--> finish -> END
```

- **planner** — breaks the question into an ordered list of sub-tasks (`state["plan"]`).
- **tool_router** — walks the plan one step at a time and picks a tool for each step
  (`calculator`, `web_search`, `vector_search`, or `answer_directly` as the fallback) using the
  LLM's native function-calling (`bind_tools([ToolSelection], tool_choice="required")`), not
  regex/keyword matching. If tool selection itself fails, it degrades to `answer_directly` for
  that step rather than aborting the run. Once every step has a result, it routes to one more
  `answer_directly` pass to synthesize `state["tool_notes"]` into a final answer.
- **executor** — runs whichever tool was selected. A tool failing on a non-final step is logged
  as a failed note and the plan moves on (one sub-task failing shouldn't throw away research
  that already succeeded elsewhere); a failure during the *final synthesis* pass sets
  `state["error"]` since there's no draft answer to fall back on at that point.
- **critique** — reviews the draft answer against the original question; can send the run back
  through `tool_router` for another synthesis attempt with feedback (bounded by
  `MAX_CRITIQUE_RETRIES`).
- **finish** — the graph's single exit point; formats the final answer (or a graceful failure
  message) for the API to return.

Any node can set `state["error"]` to short-circuit straight to `finish` — failures produce a
clean explanatory response instead of crashing the process or hanging the request.

### Tools

| Tool | What it does | Notes |
|---|---|---|
| `calculator` | Arithmetic via an `ast`-walking safe evaluator | No `eval()`/`exec()` — only whitelisted numeric operators are reachable |
| `web_search` | Tavily API, purpose-built search for AI agents | Requires `TAVILY_API_KEY`; degrades to a clear `ToolError` if missing |
| `vector_search` | In-memory ChromaDB over a small seeded knowledge base | Seeded with placeholder docs about this project's own stack (LangGraph, Groq, Tavily, SSE, ChromaDB) — swap in real documents later |
| `answer_directly` | LLM reasoning with no external tool | Fallback for unmatched plan steps, and reused for the final synthesis pass over gathered notes |

### Streaming design

The FastAPI endpoint (`POST /api/research`) streams Server-Sent Events by consuming
`graph.astream(state, stream_mode="updates")`. LangGraph emits one dict per node execution
containing *only the fields that node returned*. The list-valued fields in `AgentState` (`trace`,
`tool_calls`, `sources`) use an `operator.add` reducer, so a node only needs to return the new
items it produced — LangGraph merges them into the accumulated state internally, while the
streamed "update" for that node still shows just the new items. That maps directly onto SSE
frames: each node's trace entries are forwarded to the client the instant that node finishes, so
the frontend can render "Step 1: Planning…" etc. as the agent works, not after it's done.

### Current status

The graph, streaming, error-handling, all four tools, and LLM-based tool routing are wired
end-to-end and verified working against the real Groq API and in the browser. **Not yet done:**
swapping the seeded `vector_search` knowledge base for real documents. Not yet deployed (backend
to Railway/Render, frontend to Vercel) or pushed to GitHub.

## Project structure

```
backend/            FastAPI + LangGraph agent
  app/
    agent/
      state.py       AgentState schema (the single source of truth flowing through the graph)
      graph.py        StateGraph wiring
      llm.py          Groq/Llama 3.3 70B client wrapper
      nodes/          planner, tool_router, executor, critique, finish
      tools/          calculator, web_search (Tavily), vector_search (ChromaDB), answer_directly
    main.py           FastAPI app, SSE endpoint
    config.py         env-based settings
    logging_config.py
  requirements.txt
  .env.example

frontend/            React + Tailwind chat UI
  src/
    hooks/useResearchStream.ts   drives the SSE request, one "run" per question
    lib/sse.ts                   hand-rolled SSE frame parser (fetch doesn't support
                                  EventSource for POST requests)
    components/                  ReasoningTrace, RunCard
  .env.example
```

## Running locally

**Backend**

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash; use venv\Scripts\activate.bat for cmd.exe
pip install -r requirements.txt
cp .env.example .env            # then add your GROQ_API_KEY (https://console.groq.com/keys)
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Then open http://localhost:5173.

## Deployment

Not deployed yet — structured to be deploy-ready: backend as a standard FastAPI/Uvicorn app
(Railway/Render), frontend as a static Vite build (Vercel). CORS origins are read from the
`CORS_ORIGINS` env var on the backend so the production frontend URL can be added without a
code change.
