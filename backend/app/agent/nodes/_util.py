"""Small shared helper so every node builds trace events the same way."""
from datetime import datetime, timezone

from app.agent.state import TraceEvent


def make_trace_event(step: str, node: str, content: str) -> TraceEvent:
    return TraceEvent(
        step=step,
        node=node,
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
