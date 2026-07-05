"""Tool registry.

Every tool is an async callable with the signature:

    async def tool(query: str, state: AgentState) -> ToolResult

`query` is whatever tool_router decided to pass it — usually the current
plan step's text. `state` is passed through too, since answer_directly needs
broader context (the full question, notes gathered so far) than a single
query string. Each tool returns a ToolResult ({"output": str, "sources":
list[SourceRecord]}); `sources` is empty for tools that don't produce
citations (calculator, answer_directly).

tool_router_node (see nodes/tool_router.py) picks a tool name per plan step
using simple keyword heuristics — a placeholder for what would be an LLM
function-calling decision in a more sophisticated router.
"""
from typing import Awaitable, Callable

from app.agent.state import AgentState, ToolResult
from app.agent.tools.answer_directly import answer_directly
from app.agent.tools.calculator import calculator
from app.agent.tools.vector_search import vector_search
from app.agent.tools.web_search import web_search

ToolFunc = Callable[[str, AgentState], Awaitable[ToolResult]]

TOOL_REGISTRY: dict[str, ToolFunc] = {
    "answer_directly": answer_directly,
    "calculator": calculator,
    "web_search": web_search,
    "vector_search": vector_search,
}
