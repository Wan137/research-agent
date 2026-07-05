"""Finish node: the graph's single exit point. Formats whatever the run
produced (a real answer, or a graceful failure message) into the final
shape the API returns."""
from app.agent.nodes._util import make_trace_event
from app.agent.state import AgentState
from app.logging_config import get_agent_logger

logger = get_agent_logger("finish")


async def finish_node(state: AgentState) -> dict:
    if state.get("error") and not state.get("draft_answer"):
        final_answer = (
            "I wasn't able to complete this research request due to an internal "
            f"error: {state['error']}. Please check the server configuration "
            "(e.g. GROQ_API_KEY) and try again."
        )
    else:
        final_answer = state.get("draft_answer") or "No answer was produced."

    logger.info("Finishing run.")
    return {
        "final_answer": final_answer,
        "trace": [make_trace_event("final", "finish", final_answer)],
    }
