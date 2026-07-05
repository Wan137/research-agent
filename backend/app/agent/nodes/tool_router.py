"""Tool-router node: walks the plan one step at a time, picking a tool for
each step via the LLM's native function-calling, then routes to a final
synthesis pass once every step is done.

Step loop shape:
  - state["step_index"] < len(plan): pick a tool for plan[step_index].
    executor runs it, appends the result to state["tool_notes"], and
    increments step_index (see executor.py).
  - state["step_index"] >= len(plan): every step has been researched; route
    to answer_directly one more time to synthesize state["tool_notes"] into
    a single final answer (executor recognizes this case and writes
    draft_answer instead of appending another note).
  - state["draft_answer"] is not None: synthesis already produced an answer
    (or critique re-approved a previous one) — done, go to critique.

Routing itself failing (LLM error, malformed response) doesn't abort the
run — it falls back to answer_directly for that step, same as an
unmatched/ambiguous step would, so a routing hiccup degrades to "reason
about it directly" rather than crashing the graph.
"""
from typing import Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agent.llm import get_llm
from app.agent.nodes._util import make_trace_event
from app.agent.state import AgentState
from app.logging_config import get_agent_logger

logger = get_agent_logger("tool_router")


class ToolSelection(BaseModel):
    """Select exactly one tool to execute the given research-plan step."""

    tool: Literal["calculator", "web_search", "vector_search", "answer_directly"] = Field(
        description=(
            "'calculator': the step is pure arithmetic (e.g. 'calculate 15% of 240'). "
            "'web_search': the step needs current, recent, or time-sensitive information "
            "from the live web. "
            "'vector_search': the step asks about something in this project's own local "
            "knowledge base, which currently covers: LangGraph, Groq, Tavily, Server-Sent "
            "Events, and ChromaDB. "
            "'answer_directly': default fallback — use general knowledge reasoning when no "
            "other tool clearly applies."
        )
    )


async def _pick_tool_for_step(step_text: str) -> str:
    try:
        llm = get_llm(temperature=0.0).bind_tools([ToolSelection], tool_choice="required")
        response = await llm.ainvoke(
            [HumanMessage(content=f"Which tool should handle this research-plan step?\n\n{step_text}")]
        )
        return response.tool_calls[0]["args"]["tool"]
    except Exception as exc:  # noqa: BLE001 - a routing failure degrades to a safe default
        logger.warning("Tool selection failed for step '%s', defaulting to answer_directly: %s", step_text, exc)
        return "answer_directly"


async def tool_router_node(state: AgentState) -> dict:
    if state.get("error"):
        return {"next_tool": None}

    if state.get("draft_answer") is not None:
        content = "Draft answer ready. Routing to self-critique."
        logger.info(content)
        return {"next_tool": None, "trace": [make_trace_event("routing", "tool_router", content)]}

    plan = state.get("plan") or []
    step_index = state.get("step_index", 0)

    if step_index >= len(plan):
        next_tool = "answer_directly"
        content = "All plan steps researched. Synthesizing final answer."
    else:
        step_text = plan[step_index]
        next_tool = await _pick_tool_for_step(step_text)
        content = f"Step {step_index + 1}/{len(plan)}: '{step_text}' -> routing to '{next_tool}'."

    logger.info(content)
    return {
        "next_tool": next_tool,
        "trace": [make_trace_event("routing", "tool_router", content)],
    }


def route_after_tool_router(state: AgentState) -> str:
    if state.get("error"):
        return "finish"
    return "executor" if state.get("next_tool") else "critique"
