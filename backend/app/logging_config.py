"""Central logging setup. Every agent node logs through the 'agent' logger so
that node execution is visible in server logs independent of the SSE trace
that gets sent to the frontend."""
import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        # Avoid duplicate handlers on reload (uvicorn --reload re-imports the module)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)


def get_agent_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"agent.{name}")
