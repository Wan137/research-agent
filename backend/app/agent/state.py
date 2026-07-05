"""Shared state that flows through every node in the LangGraph graph.

Design note: fields that multiple nodes append to over the course of a run
(trace, tool_calls, sources) use `Annotated[list, operator.add]`. LangGraph
merges a node's returned dict into the overall state using each field's
reducer. For plain fields (the default reducer) a node's return value
*replaces* the prior value, which is what we want for things like
`draft_answer`. For the list fields we want *append* semantics instead, so
each node only has to return the new items it produced, not the whole
history. This also happens to be exactly what we want for streaming: with
stream_mode="updates", LangGraph emits each node's raw return value, so a
node returning trace=[one_new_event] streams just that one event rather than
the accumulated list.
"""
import operator
from typing import Annotated, Any, Optional, TypedDict


class TraceEvent(TypedDict):
    step: str  # "planning" | "routing" | "tool_call" | "critique" | "final" | "error"
    node: str  # which graph node emitted this
    content: str  # human-readable description, shown in the frontend trace panel
    timestamp: str  # ISO 8601


class ToolCallRecord(TypedDict):
    tool: str
    input: str
    output: str
    success: bool


class SourceRecord(TypedDict):
    title: str
    url: str


class ToolResult(TypedDict):
    """What every tool function returns. `sources` is usually empty (e.g.
    calculator, the answer_directly fallback) but web_search and
    vector_search populate it so the frontend can render citations."""

    output: str
    sources: list[SourceRecord]


class AgentState(TypedDict):
    # Input
    question: str

    # Planner output
    plan: Optional[list[str]]

    # Tool routing
    next_tool: Optional[str]  # None means "no more tools needed, ready to critique"
    tool_calls: Annotated[list[ToolCallRecord], operator.add]

    # Plan-execution progress: tool_router walks `plan` one step at a time,
    # picking a tool per step; step_index tracks how far it's gotten, and
    # tool_notes accumulates each step's tool output. Once step_index reaches
    # len(plan), the next executor call is a synthesis pass over tool_notes
    # instead of another per-step tool call (see tool_router.py).
    step_index: int
    tool_notes: Annotated[list[str], operator.add]

    # Executor output
    draft_answer: Optional[str]

    # Self-critique
    critique_feedback: Optional[str]
    is_approved: bool
    retry_count: int

    # Final output
    final_answer: Optional[str]
    sources: Annotated[list[SourceRecord], operator.add]

    # Observability (streamed to the frontend as it's produced)
    trace: Annotated[list[TraceEvent], operator.add]

    # Set when a node hits an unrecoverable error, so finish_node can report
    # a graceful failure instead of the graph just dying.
    error: Optional[str]


def new_initial_state(question: str) -> dict[str, Any]:
    return AgentState(
        question=question,
        plan=None,
        next_tool=None,
        tool_calls=[],
        step_index=0,
        tool_notes=[],
        draft_answer=None,
        critique_feedback=None,
        is_approved=False,
        retry_count=0,
        final_answer=None,
        sources=[],
        trace=[],
        error=None,
    )
