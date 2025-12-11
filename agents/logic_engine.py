# agents/logic_engine.py
"""
LogicBlockEngineAgent - runs registered logic blocks.
Supports an optional llm_adapter callable which can be used to paraphrase/augment
FAQ answers after deterministic generation.

Each block module in logic_blocks/ must expose a run_block(...) function.
"""
from typing import Dict, Optional, Callable, List
import importlib

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

            try:
                if not hasattr(mod, "run_block"):
                    blocks[blk] = {"error": "no run_block() in block module"}
                    continue

                # FAQ block needs questions passed in
                if blk == "faq_answer_block":
                    q_list = questions.get("questions", []) if questions else []
                    faq_out = mod.run_block(product_model, q_list)
                    faq_items = faq_out.get("faq_items", [])

                    # apply optional llm adapter for paraphrasing (best-effort)
                    if self.llm_adapter:
                        try:
                            paraphrased = self.llm_adapter(faq_items, product_model)
                            # ensure adapter returns a list; else fallback
                            if isinstance(paraphrased, list):
                                blocks[blk] = {"faq_items": paraphrased}
                            else:
                                blocks[blk] = {"faq_items": faq_items, "adapter_error": "adapter returned non-list"}
                        except Exception as e:
                            blocks[blk] = {"faq_items": faq_items, "adapter_error": str(e)}
                    else:
                        blocks[blk] = {"faq_items": faq_items}
                else:
                    # other blocks receive only product_model
                    out = mod.run_block(product_model)
                    blocks[blk] = out
            except Exception as e:
                blocks[blk] = {"error": str(e)}

        return {"blocks": blocks}
