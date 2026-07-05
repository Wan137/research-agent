"""Single point of contact for talking to the LLM (Groq/Llama 3.3 70B).

Kept separate from the graph nodes so that:
- swapping providers later (e.g. adding an OpenAI fallback) touches one file
- nodes don't each need their own try/except/logging boilerplate for LLM calls
"""
from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq

from app.agent.errors import ToolError
from app.config import get_settings


class LLMError(ToolError):
    """Raised when the LLM call fails after the provider's own retries.
    Subclasses ToolError so answer_directly (which is itself just a tool that
    happens to call the LLM) surfaces failures the same way every other tool
    does, and the executor only needs one except clause."""


_llm: ChatGroq | None = None


def get_llm(temperature: float = 0.2) -> ChatGroq:
    """Lazily construct the ChatGroq client. Lazy so the app can still boot
    (e.g. for a health check) even if GROQ_API_KEY is missing; the failure is
    deferred to the first actual call, where it's caught and surfaced as a
    trace event instead of crashing the process."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise LLMError(
            "GROQ_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add your key from https://console.groq.com/keys"
        )

    global _llm
    if _llm is None or _llm.temperature != temperature:
        _llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temperature,
        )
    return _llm


async def ainvoke_llm(messages: list[BaseMessage], temperature: float = 0.2) -> str:
    """Invoke the LLM and return plain text, wrapping any failure in LLMError
    so callers only need to handle one exception type."""
    try:
        llm = get_llm(temperature=temperature)
        response = await llm.ainvoke(messages)
        return str(response.content)
    except LLMError:
        raise
    except Exception as exc:  # network errors, rate limits, bad responses, etc.
        raise LLMError(f"Groq API call failed: {exc}") from exc
