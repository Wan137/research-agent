"""Builds the LangGraph StateGraph that drives the research agent.

Shape of the graph:

    START -> planner -> tool_router --(tool selected)--> executor -\
                            ^                                       |
                            |------------------(loop)---------------
                            |
                            '--(no tool needed)--> critique --(rejected, retries left)--> tool_router
                                                        |
                                                        '--(approved / retries exhausted)--> finish -> END

Any node can short-circuit straight to `finish` by setting state["error"];
the conditional edges below check for that first so a failure always
produces a (graceful) response instead of the graph hanging or crashing.

Why a graph instead of a linear chain: the tool_router <-> executor loop
lets the agent call multiple tools in sequence for one question (once real
tools are registered), and the critique <-> tool_router loop lets it redo
work based on its own self-review — neither is expressible as a straight
line of steps.
"""
from langgraph.graph import END, START, StateGraph

from app.agent.nodes.critique import critique_node, route_after_critique
from app.agent.nodes.executor import executor_node
from app.agent.nodes.finish import finish_node
from app.agent.nodes.planner import planner_node
from app.agent.nodes.tool_router import route_after_tool_router, tool_router_node
from app.agent.state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("tool_router", tool_router_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critique", critique_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "tool_router")

    graph.add_conditional_edges(
        "tool_router",
        route_after_tool_router,
        {"executor": "executor", "critique": "critique", "finish": "finish"},
    )

    graph.add_edge("executor", "tool_router")

    graph.add_conditional_edges(
        "critique",
        route_after_critique,
        {"tool_router": "tool_router", "finish": "finish"},
    )

    graph.add_edge("finish", END)

    return graph.compile()


# Compiled once at import time and reused across requests — compilation just
# builds the graph structure, it holds no per-request state.
research_agent_graph = build_graph()
