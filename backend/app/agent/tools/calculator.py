"""Sandboxed calculator. Evaluates arithmetic by walking a parsed `ast` tree
and dispatching only whitelisted node/operator types — never eval()/exec()
on the raw string — so nothing beyond numeric arithmetic is reachable no
matter what text the plan or the LLM passes in here.

Exponentiation uses Python syntax (`2 ** 10`), not `^`.
"""
import ast
import operator as _op
import re

from app.agent.errors import ToolError
from app.agent.state import AgentState, ToolResult

_BIN_OPS = {
    ast.Add: _op.add,
    ast.Sub: _op.sub,
    ast.Mult: _op.mul,
    ast.Div: _op.truediv,
    ast.FloorDiv: _op.floordiv,
    ast.Mod: _op.mod,
    ast.Pow: _op.pow,
}
_UNARY_OPS = {ast.USub: _op.neg, ast.UAdd: _op.pos}

# Plan steps and questions are natural language ("Calculate 12% of 250"), so
# we pull out the arithmetic-looking substring rather than requiring the
# caller to pass a bare expression.
_EXPR_RE = re.compile(r"[-+*/().\d\s]{3,}")


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        try:
            return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        except ZeroDivisionError as exc:
            raise ToolError("Division by zero.") from exc
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    raise ToolError(f"Unsupported expression element: {ast.dump(node)}")


def safe_eval(expression: str) -> float:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError(f"'{expression}' is not a valid arithmetic expression: {exc}") from exc
    return _eval(tree)


async def calculator(query: str, state: AgentState) -> ToolResult:
    match = _EXPR_RE.search(query)
    if not match:
        raise ToolError(f"Could not find an arithmetic expression in: '{query}'")

    expression = match.group().strip()
    result = safe_eval(expression)
    return {"output": f"{expression} = {result}", "sources": []}
