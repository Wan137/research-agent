"""Executor node: runs whichever tool tool_router selected for the current
plan step (or, once all steps are done, the final synthesis pass) and
records the result.

Failure handling is deliberately asymmetric:
  - A tool failing on a *non-final* step doesn't abort the run — it's logged
    as a failed note in state["tool_notes"] and the plan moves on to the
    next step. One sub-task failing (e.g. a search API being down) shouldn't
    throw away research that already succeeded on other steps.
  - A failure during the *final synthesis* pass sets state["error"], since
    at that point there's no draft answer to fall back on — finish_node
    reports it as a graceful failure instead of the graph crashing.
"""
from app.agent.nodes._util import make_trace_event
from app.agent.state import AgentState
from app.agent.tools import TOOL_REGISTRY
from app.logging_config import get_agent_logger

logger = get_agent_logger("executor")


async def executor_node(state: AgentState) -> dict:
    tool_name = state["next_tool"]
    assert tool_name is not None, "executor_node reached without a selected tool"

    plan = state.get("plan") or []
    step_index = state.get("step_index", 0)
    is_final = step_index >= len(plan)
    query = state["question"] if is_final else plan[step_index]

    tool_fn = TOOL_REGISTRY.get(tool_name)
    if tool_fn is None:
        success, output, sources = False, f"Tool '{tool_name}' is not registered.", []
    else:
        try:
            result = await tool_fn(query, state)
            success, output, sources = True, result["output"], result.get("sources", [])
        except Exception as exc:  # noqa: BLE001 - any tool failure is handled uniformly here
            logger.exception("Tool '%s' failed", tool_name)
            success, output, sources = False, str(exc), []

    tool_call_record = {"tool": tool_name, "input": query, "output": output, "success": success}

    if is_final:
        if success:
            content_trace = [
                make_trace_event("tool_call", "executor", f"Synthesizing final answer via '{tool_name}'."),
                make_trace_event("tool_result", "executor", output),
            ]
            logger.info("Final synthesis via '%s' succeeded.", tool_name)
            return {
                "draft_answer": output,
                "sources": sources,
                "tool_calls": [tool_call_record],
                "trace": content_trace,
            }

        content = f"Final synthesis via '{tool_name}' failed: {output}"
        logger.error(content)
        return {
            "tool_calls": [tool_call_record],
            "trace": [make_trace_event("error", "executor", content)],
            "error": output,
        }

    # Non-final step: record the note (success or failure) and move on.
    if success:
        note = f"[{tool_name}] {output}"
        content = f"Tool '{tool_name}' completed step {step_index + 1}/{len(plan)}."
        trace_step = "tool_result"
    else:
        note = f"[{tool_name}] failed: {output}"
        content = f"Tool '{tool_name}' failed on step {step_index + 1}/{len(plan)}: {output}"
        trace_step = "error"

    logger.info(content)
    return {
        "tool_notes": [note],
        "sources": sources,
        "step_index": step_index + 1,
        "tool_calls": [tool_call_record],
        "trace": [
            make_trace_event("tool_call", "executor", f"Called '{tool_name}' for step {step_index + 1}."),
            make_trace_event(trace_step, "executor", content),
        ],
    }
