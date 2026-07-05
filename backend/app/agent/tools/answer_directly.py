"""Fallback tool that answers using only the LLM's own knowledge. Serves two
roles in the graph, distinguished by the caller (executor_node) rather than
by anything in this file:

1. Per-step fallback — when tool_router can't match a plan step to
   calculator/web_search/vector_search, it defaults here so every step
   produces *something* usable for the final synthesis.
2. Final synthesis — once all plan steps are done, tool_router routes here
   again to combine everything gathered (state["tool_notes"]) into one
   coherent answer.

Both cases go through this same function; it just includes whatever notes
happen to exist yet, which is empty on a first per-step call and populated
by the time synthesis runs.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import ainvoke_llm
from app.agent.state import AgentState, ToolResult

SYSTEM_PROMPT = (
    "You are the reasoning component of a research agent. Answer the user's "
    "question as accurately as you can, using your own knowledge and any "
    "information already gathered below. Be concise but complete. If you are "
    "not confident about a fact, say so explicitly instead of guessing."
)


async def answer_directly(query: str, state: AgentState) -> ToolResult:
    plan = state.get("plan") or []
    plan_text = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    notes = state.get("tool_notes") or []
    feedback = state.get("critique_feedback")

    user_content = f"Question: {state['question']}\n\nPlan:\n{plan_text}"
    if notes:
        user_content += "\n\nInformation gathered so far:\n" + "\n".join(notes)
    user_content += f"\n\nCurrent focus: {query}"
    if feedback:
        user_content += (
            f"\n\nA previous draft answer was reviewed and needs improvement. "
            f"Reviewer feedback: {feedback}\nProduce a revised answer that addresses this."
        )

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]
    output = await ainvoke_llm(messages)
    return {"output": output, "sources": []}
