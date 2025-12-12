# agents/langchain_runnables.py
"""
Runnable adapter for LangChain v1.x — robust and tolerant.

Provides:
  - wrap_as_runnable(fn, name=None) -> object with .invoke(...) and optional composition support
  - Uses langchain_core.runnables.RunnableLambda when available (LangChain v1.x)
  - Falls back to a shim that exposes .invoke(...) and chaining when RunnableLambda is not available
"""

from typing import Any, Callable, Dict, List, Optional
import traceback

# Detect Runnable support (langchain_core.runnables.RunnableLambda)
_USE_RUNNABLE = False
try:
    # v1.x exposes runnables in langchain_core.runnables
    from langchain_core.runnables import RunnableLambda, Runnable  # type: ignore
    _USE_RUNNABLE = True
except Exception:
    RunnableLambda = None
    Runnable = None

# If Runnable isn't available, try to import the tolerant FunctionChain if present
if not _USE_RUNNABLE:
    try:
        from agents.langchain_adapters import FunctionChain  # type: ignore
    except Exception:
        # Minimal fallback FunctionChain-like implementation
        class FunctionChain:
            def __init__(self, fn: Callable, input_keys: Optional[List[str]] = None, output_keys: Optional[List[str]] = None, name: Optional[str] = None):
                self.fn = fn
                self._input_keys = input_keys or ["input"]
                self._output_keys = output_keys or ["output"]
                self._name = name or getattr(fn, "__name__", "function_chain")

            def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
                if len(self._input_keys) == 1:
                    payload = inputs.get(self._input_keys[0])
                else:
                    payload = {k: inputs.get(k) for k in self._input_keys}
                result = self.fn(payload)
                if isinstance(result, dict):
                    out = {k: result.get(k) for k in self._output_keys if k in result}
                    if out:
                        return out
                    return {self._output_keys[0]: result}
                else:
                    return {self._output_keys[0]: result}


def wrap_as_runnable(fn: Callable[[Any], Any], name: Optional[str] = None):
    """
    Wrap a pure python callable `fn` into:
      - a RunnableLambda (if available), or
      - a shim object with .invoke(payload) that calls fn and returns its value.

    The callable `fn` is expected to accept a single argument (payload) and return a value.
    """
    if _USE_RUNNABLE and RunnableLambda is not None:
        # Create a RunnableLambda that simply calls fn(payload)
        r = RunnableLambda(fn)
        try:
            setattr(r, "__name__", name or getattr(fn, "__name__", "runnable_lambda"))
        except Exception:
            pass
        return r

    # Fallback shim: create a shim that exposes .invoke() and chaining via | if possible.
    # It wraps a FunctionChain if available for parity.
    try:
        fc = FunctionChain(fn, input_keys=["input"], output_keys=["output"], name=name)
    except Exception:
        # If even FunctionChain isn't available, create a minimal wrapper.
        class _MinimalFC:
            def __init__(self, fn):
                self.fn = fn
            def _call(self, inputs):
                return {"output": self.fn(inputs)}
        fc = _MinimalFC(fn)

    class Shim:
        def __init__(self, fc):
            self._fc = fc

        def invoke(self, payload):
            # Best-effort: if underlying adapter supports .invoke, use it; else use _call
            if hasattr(self._fc, "invoke"):
                try:
                    return self._fc.invoke(payload)
                except Exception:
                    pass
            if hasattr(self._fc, "_call"):
                try:
                    # _call expects dict keyed by input key; we used "input"
                    return self._fc._call({"input": payload}).get("output")
                except Exception:
                    # last resort, call fn directly
                    if hasattr(self._fc, "fn"):
                        return self._fc.fn(payload)
                    raise
            # final fallback: try call
            if callable(self._fc):
                return self._fc(payload)
            raise RuntimeError("Unable to invoke wrapped function")

        def __or__(self, other):
            # composition: return a new runnable that calls self then other
            def chained(x):
                a = self.invoke(x)
                # other may be Runnable-like with invoke
                if hasattr(other, "invoke"):
                    return other.invoke(a)
                if callable(other):
                    return other(a)
                raise RuntimeError("Cannot chain to other")
            return wrap_as_runnable(chained)

        # allow callable behavior as well
        def __call__(self, payload):
            return self.invoke(payload)

    return Shim(fc)
