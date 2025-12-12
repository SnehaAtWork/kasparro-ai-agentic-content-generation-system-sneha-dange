# agents/logic_engine.py
"""
LogicBlockEngineAgent - runs registered logic blocks.
Supports an optional llm_adapter callable which can be used to paraphrase/augment
FAQ answers after deterministic generation.

Each block module in logic_blocks/ must expose a run_block(...) function.
"""
from typing import Dict, Optional, Callable, List
import importlib
import logging
import inspect
logger = logging.getLogger(__name__)

REGISTERED_BLOCKS = [
    "product_block",
    "benefits_block",
    "usage_block",
    "safety_block",
    "ingredients_block",
    "compare_block",
    "purchase_block",
    "faq_answer_block",
]

class LogicBlockEngineAgent:
    def __init__(self, config: Dict = None, llm_adapter: Optional[Callable] = None):
        """
        llm_adapter signature: Callable[[List[Dict], Dict], List[Dict]]
          - receives (faq_items, product_model) and returns new faq_items
        """
        self.config = config or {}
        self.llm_adapter = llm_adapter

    @staticmethod
    def _call_block_fn(fn, product_model, questions, blocks):
        """
        Call block function `fn` in a tolerant way:
        - supports signatures:
            run_block(product_model)
            run_block(product_model, questions)
            run_block(product_model, questions, blocks)
            run_block(product_model, blocks)   (older variants)
        - accepts product_model possibly being a list and normalizes it to a dict where possible.
        Returns the block result (dict) or {'error': '<msg>'} on exception.
        """
        try:
            sig = inspect.signature(fn)
            params = list(sig.parameters.keys())
            # Normalize product_model if it's a single-element list
            pm = product_model
            if isinstance(pm, list):
                # choose first dict-like element if present, else keep as-is
                first_dict = None
                for el in pm:
                    if isinstance(el, dict):
                        first_dict = el
                        break
                if first_dict is not None:
                    pm = first_dict
                else:
                    # leave pm as list (fn may accept list)
                    pm = product_model

            # Build ordered args by name if possible
            # Try common parameter names
            try:
                # prefer direct positional call depending on arity
                if len(params) == 0:
                    return fn()
                elif len(params) == 1:
                    return fn(pm)
                elif len(params) == 2:
                    # if second param name contains 'questions' assume (product, questions)
                    if 'questions' in params[1].lower():
                        return fn(pm, questions)
                    # else assume (product, blocks)
                    return fn(pm, blocks)
                else:
                    # 3+ params: try (product, questions, blocks)
                    return fn(pm, questions, blocks)
            except TypeError:
                # as fallback, try calling by position with best guess
                try:
                    return fn(pm, questions, blocks)
                except Exception as e:
                    # final fallback: try minimal call
                    return fn(pm)
        except Exception as e:
            logger.exception("Block invocation failed: %s", e)
            return {"error": str(e)}

    def run(self, product_model: Dict, questions: Dict = None) -> Dict:
        """
        Runs each registered block. For faq_answer_block, the block receives both
        product_model and questions and returns {'faq_items': [...] }.
        If llm_adapter is provided, it will be applied to faq_items with product_model
        as context. Any adapter failure falls back to deterministic faq_items.
        """
        blocks = {}
        for blk in REGISTERED_BLOCKS:
            try:
                mod = importlib.import_module(f"logic_blocks.{blk}")
            except Exception as e:
                blocks[blk] = {"error": f"import error: {e}"}
                continue

            # module loaded; ensure run_block exists
            if not hasattr(mod, "run_block"):
                blocks[blk] = {"error": "no run_block() in block module"}
                continue

            try:
                # Use the tolerant invoker for all blocks
                res = self._call_block_fn(mod.run_block, product_model, questions, blocks)

                # If the block returned an error dict, pass it through
                if isinstance(res, dict) and "error" in res:
                    blocks[blk] = res
                    continue

                # Special handling for FAQ block to apply llm_adapter (if configured)
                if blk == "faq_answer_block":
                    # res should be dict with 'faq_items' or be list itself
                    if isinstance(res, dict) and "faq_items" in res:
                        faq_items = res.get("faq_items", [])
                    elif isinstance(res, list):
                        faq_items = res
                    else:
                        # unknown shape - normalize to empty list
                        faq_items = []

                    # apply optional llm adapter for paraphrasing (best-effort)
                    if self.llm_adapter:
                        try:
                            paraphrased = self.llm_adapter(faq_items, product_model)
                            if isinstance(paraphrased, list):
                                blocks[blk] = {"faq_items": paraphrased}
                            else:
                                blocks[blk] = {"faq_items": faq_items, "adapter_error": "adapter returned non-list"}
                        except Exception as e:
                            blocks[blk] = {"faq_items": faq_items, "adapter_error": str(e)}
                    else:
                        blocks[blk] = {"faq_items": faq_items}
                else:
                    # For non-FAQ blocks, accept whatever the block returned (dict/list/primitive)
                    blocks[blk] = res

            except Exception as e:
                # Defensive: catch any error and record it rather than crash
                logger.exception("Block %s execution failed: %s", blk, e)
                blocks[blk] = {"error": str(e)}


        logger.info("DEBUG blocks keys: %s", list(blocks.keys()))
        # and optionally dump blocks to artifacts:
        from utils.checkpoints import save; save("after_logic_blocks", blocks)
        return {"blocks": blocks}
