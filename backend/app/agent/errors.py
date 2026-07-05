class ToolError(Exception):
    """Base class for tool failures. The executor catches this (and any other
    exception a tool raises) uniformly, so individual tools don't need their
    own try/except/logging boilerplate around the executor's call site.

    Lives outside app.agent.tools (rather than as tools/errors.py) so that
    llm.py can import it without triggering app/agent/tools/__init__.py,
    which itself imports answer_directly -> llm.py — that would be a
    circular import if this lived inside the tools package.
    """
