"""
QuantLab Sandbox — executes user-submitted strategy code safely.

ISO 25010 — Functional Suitability: strategies receive live market events.
ISO 27001 A.14 — Secure Development: code executed in a restricted namespace;
    dangerous builtins (open, exec, eval, __import__) are blocked.

The sandbox pattern:
  1. User submits Python source code via POST /api/v1/lab/strategies
  2. Code is compiled and executed in a restricted globals dict
  3. Any class that inherits BaseStrategy and calls register() is captured
  4. Strategy is live-wired to market events via StrategyRunner
"""
from __future__ import annotations

import ast
import concurrent.futures
import textwrap
import traceback
from typing import Any

from app.quantlab import sdk

_EXEC_TIMEOUT_SECONDS = 5   # module-level exec must complete within 5 s
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="sandbox")


# ── AST safety check ─────────────────────────────────────────────────────────

_BANNED_NODES = {
    ast.Import,
    ast.ImportFrom,
}

_BANNED_NAMES = {
    "open", "eval", "exec", "__import__", "compile",
    "globals", "locals", "vars", "dir",
    "breakpoint", "input",
    "__builtins__", "__loader__", "__spec__",
}


def _check_ast(source: str) -> list[str]:
    """Return list of safety violations (empty = safe)."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]

    violations: list[str] = []

    for node in ast.walk(tree):
        if type(node) in _BANNED_NODES:
            violations.append(
                f"Line {node.lineno}: import statements are not allowed — "
                "use the SDK classes already available in scope."
            )
        if isinstance(node, ast.Name) and node.id in _BANNED_NAMES:
            violations.append(f"Line {node.lineno}: '{node.id}' is not allowed.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.append(
                f"Line {node.lineno}: dunder attribute access '{node.attr}' is not allowed."
            )

    return violations


# ── Safe builtins ─────────────────────────────────────────────────────────────

_SAFE_BUILTINS = {
    "abs", "all", "any", "bool", "dict", "enumerate", "filter",
    "float", "frozenset", "int", "isinstance", "issubclass", "len",
    "list", "map", "max", "min", "print", "range", "reversed",
    "round", "set", "slice", "sorted", "str", "sum", "tuple", "type",
    "zip", "None", "True", "False",
}


def _make_globals() -> dict[str, Any]:
    import builtins
    safe_builtins = {k: getattr(builtins, k) for k in _SAFE_BUILTINS if hasattr(builtins, k)}

    import math
    return {
        "__builtins__": safe_builtins,
        # SDK classes
        "BaseStrategy":    sdk.BaseStrategy,
        "BaseIndicator":   sdk.BaseIndicator,
        "TradeEvent":      sdk.TradeEvent,
        "QuoteEvent":      sdk.QuoteEvent,
        "Signal":          sdk.Signal,
        "SMA":             sdk.SMA,
        "EMA":             sdk.EMA,
        "RSI":             sdk.RSI,
        "BollingerBands":  sdk.BollingerBands,
        "SessionVWAP":     sdk.SessionVWAP,
        "OrderFlowDelta":  sdk.OrderFlowDelta,
        "VolumeProfile":   sdk.VolumeProfile,
        "Indicator":       sdk.Indicator,
        "ta":              sdk.ta,
        "register":        sdk.register,
        # Safe math
        "math":            math,
    }


# ── Sandbox ───────────────────────────────────────────────────────────────────

class SandboxError(Exception):
    pass


class QuantLabSandbox:
    """Compiles and executes a strategy script, returns registered class."""

    def run(self, source: str) -> tuple[type[sdk.BaseStrategy] | None, list[str]]:
        """
        Returns (strategy_class, errors).
        strategy_class is None if compilation or safety check failed.

        Execution is dispatched to a thread pool with a hard timeout to prevent
        infinite loops at module level from blocking the event loop.
        """
        source = textwrap.dedent(source)
        violations = _check_ast(source)
        if violations:
            return None, violations

        future = _executor.submit(self._exec, source)
        try:
            return future.result(timeout=_EXEC_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            future.cancel()
            return None, [f"Execution timed out after {_EXEC_TIMEOUT_SECONDS}s — check for infinite loops."]
        except Exception:
            return None, [traceback.format_exc()]

    @staticmethod
    def _exec(source: str) -> tuple[type[sdk.BaseStrategy] | None, list[str]]:
        registered: list[type[sdk.BaseStrategy]] = []

        original_hook = sdk._registry_hook
        sdk._registry_hook = lambda cls: registered.append(cls)

        try:
            code = compile(source, "<quantlab>", "exec")
            exec(code, _make_globals())  # noqa: S102
        except Exception:
            return None, [traceback.format_exc()]
        finally:
            sdk._registry_hook = original_hook

        if not registered:
            return None, ["No strategy registered. Call register(YourStrategyClass) at module level."]

        return registered[-1], []
