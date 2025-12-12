# agents/langchain_adapters.py
"""
Diagnostic + tolerant LangChain adapter wrapper.

This module:
- Attempts multiple import paths to find a Chain base class in installed LangChain.
- Prints/import-tracebacks (to stdout) so you can see what succeeded/failed.
- Falls back to object if nothing is found so tests can still run.
"""

from typing import Any, Callable, Dict, List, Optional
import traceback, sys

LangChainBase = None
_import_attempts = []

# List of (module_path, attr_name) to try. Add/remove as needed.
candidates = [
    ("langchain.chains.base", "Chain"),
    ("langchain.chains", "Chain"),
    ("langchain.chain", "Chain"),
    ("langchain.llms.base", "Chain"),
    ("langchain.schema", "Chain"),
]

for mod_path, attr in candidates:
    try:
        module = __import__(mod_path, fromlist=[attr])
        LangChainBase = getattr(module, attr, None)
        _import_attempts.append((mod_path, attr, True, getattr(module, '__file__', None)))
        if LangChainBase is not None:
            print(f"[langchain-adapter] Found Chain at {mod_path}.{attr} (module file: {getattr(module, '__file__', None)})")
            break
    except Exception as e:
        _import_attempts.append((mod_path, attr, False, repr(e)))

if LangChainBase is None:
    print("[langchain-adapter] Could not locate a Chain class in tried paths. Import attempts:")
    for p, a, ok, info in _import_attempts:
        print(f" - {p}.{a} -> success={ok}, info={info}")
    print("[langchain-adapter] Falling back to plain `object` as Chain base. Tests will still run.")

# Final fallback
if LangChainBase is None:
    LangChainBase = object

class FunctionChain(LangChainBase):
    def __init__(
        self,
        fn: Callable[[Dict[str, Any]], Any],
        input_keys: Optional[List[str]] = None,
        output_keys: Optional[List[str]] = None,
        name: Optional[str] = None,
    ):
        try:
            super().__init__()
        except Exception:
            # Some Chain implementations may require different init signature
            pass

        self.fn = fn
        self._input_keys = input_keys or ["input"]
        self._output_keys = output_keys or ["output"]
        self._name = name or getattr(fn, "__name__", "function_chain")

    @property
    def input_keys(self) -> List[str]:
        return self._input_keys

    @input_keys.setter
    def input_keys(self, v: List[str]):
        self._input_keys = v

    @property
    def output_keys(self) -> List[str]:
        return self._output_keys

    @output_keys.setter
    def output_keys(self, v: List[str]):
        self._output_keys = v

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

    @property
    def verbose(self) -> bool:
        return False
