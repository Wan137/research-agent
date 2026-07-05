"""Planner node: the entry point of the graph. Breaks the user's question
into an ordered list of sub-tasks that later nodes will work through.

Design note: the plan is currently advisory rather than binding — tool_router
doesn't yet parse it to pick tools (that's the next milestone, once
web_search/calculator/vector_search exist). Producing it now still matters
because 1) it's the first thing streamed to the frontend so the user sees
the agent "think" before anything else happens, and 2) the executor's
answer_directly fallback uses it to structure its reasoning.
"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import LLMError, ainvoke_llm
from app.agent.nodes._util import make_trace_event
from app.agent.state import AgentState
from app.logging_config import get_agent_logger

logger = get_agent_logger("planner")

SYSTEM_PROMPT = (
    "You are the planning component of a research agent. Given a user's "
    "question, break it down into a short ordered list of concrete sub-tasks "
    "needed to answer it well (usually 2-5 steps). "
    'Respond with ONLY a JSON object of the form {"steps": ["step 1", "step 2", ...]}. '
    "No prose, no markdown fences."
)


def _parse_plan(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
        steps = data.get("steps", [])
        if isinstance(steps, list) and steps:
            return [str(s) for s in steps]
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: the model ignored the JSON instruction. Salvage a numbered
    # or bulleted list from plain text rather than failing the whole run.
    lines = [line.strip(" -*") for line in raw.splitlines() if line.strip()]
    lines = [re.sub(r"^\d+[.)]\s*", "", line) for line in lines]
    return lines[:5] if lines else ["Answer the question directly."]


async def planner_node(state: AgentState) -> dict:
    question = state["question"]
    logger.info("Planning for question: %s", question)

    try:
        raw = await ainvoke_llm(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)],
            temperature=0.1,
        )
        plan = _parse_plan(raw)
        content = "Plan:\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(plan))
        return {
            "plan": plan,
            "trace": [make_trace_event("planning", "planner", content)],
        }
    except LLMError as exc:
        logger.error("Planning failed: %s", exc)
        return {
            "error": str(exc),
            "trace": [make_trace_event("error", "planner", f"Planning failed: {exc}")],
        }
