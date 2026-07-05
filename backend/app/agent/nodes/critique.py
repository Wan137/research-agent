"""Self-critique node: reviews the draft answer against the original question
before it's allowed to reach the user. If the review finds it lacking and
retries remain, it clears draft_answer and loops back through tool_router so
the executor produces a revised answer informed by the feedback.

If the critique call itself fails (LLM error), we don't want to throw away a
perfectly fine draft answer over a review-step outage — so that failure
degrades to "approve as-is" with a note in the trace, rather than surfacing
as a hard error.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import LLMError, ainvoke_llm
from app.agent.nodes._util import make_trace_event
from app.agent.state import AgentState
from app.config import get_settings
from app.logging_config import get_agent_logger

logger = get_agent_logger("critique")

SYSTEM_PROMPT = (
    "You are a strict fact-checking reviewer for a research agent. Given a "
    "question and a draft answer, judge whether the draft actually answers "
    "the question accurately and completely. "
    'Respond with ONLY a JSON object: {"approved": true|false, "feedback": "..."}. '
    "feedback should be empty if approved is true, otherwise a short, actionable "
    "note on what's missing or wrong. No prose, no markdown fences."
)


def _parse_verdict(raw: str) -> tuple[bool, str]:
    try:
        data = json.loads(raw)
        return bool(data.get("approved", True)), str(data.get("feedback", ""))
    except (json.JSONDecodeError, AttributeError):
        # If the reviewer didn't follow the format, don't block the pipeline on it.
        return True, ""


async def critique_node(state: AgentState) -> dict:
    question = state["question"]
    draft = state["draft_answer"] or ""

    try:
        raw = await ainvoke_llm(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"Question: {question}\n\nDraft answer: {draft}"),
            ],
            temperature=0.0,
        )
        approved, feedback = _parse_verdict(raw)
    except LLMError as exc:
        logger.warning("Critique call failed, approving draft as-is: %s", exc)
        approved, feedback = True, ""
        content = f"Self-critique skipped (reviewer unavailable: {exc}); approving draft as-is."
        return {
            "is_approved": True,
            "critique_feedback": "",
            "trace": [make_trace_event("critique", "critique", content)],
        }

    settings = get_settings()
    retry_count = state.get("retry_count", 0)

    if approved:
        content = "Self-critique: draft approved."
    elif retry_count >= settings.max_critique_retries:
        content = (
            f"Self-critique: issues remain ({feedback or 'no detail given'}), "
            f"but max retries ({settings.max_critique_retries}) reached — using best available draft."
        )
        approved = True  # force through so the graph terminates with a real answer
    else:
        content = f"Self-critique: draft needs revision — {feedback}"

    logger.info(content)
    update: dict = {
        "is_approved": approved,
        "critique_feedback": feedback,
        "trace": [make_trace_event("critique", "critique", content)],
    }
    if not approved:
        update["retry_count"] = retry_count + 1
        update["draft_answer"] = None  # forces tool_router back to executor
    return update


def route_after_critique(state: AgentState) -> str:
    if state.get("error"):
        return "finish"
    return "finish" if state.get("is_approved") else "tool_router"
