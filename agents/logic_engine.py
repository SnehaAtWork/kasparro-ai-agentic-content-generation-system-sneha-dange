"""
LogicBlockEngineAgent stub
Runs logic blocks (imported from logic_blocks/) and returns block outputs.
"""
from typing import Dict
import importlib

REGISTERED_BLOCKS = [
    "benefits_block",
    "usage_block",
    "safety_block",
    "ingredients_block",
    "compare_block",
    "purchase_block",
    "faq_answer_block"
]

class LogicBlockEngineAgent:
    def __init__(self, config: Dict = None):
        self.config = config or {}

    def run(self, product_model: Dict, questions: Dict = None) -> Dict:
        blocks = {}
        for blk in REGISTERED_BLOCKS:
            try:
                mod = importlib.import_module(f"logic_blocks.{blk}")
                if hasattr(mod, "run_block"):

                    # FAQ block requires both product + questions
                    if blk == "faq_answer_block":
                        blocks[blk] = mod.run_block(
                            product_model,
                            questions.get("questions", []) if questions else []
                        )
                    else:
                        blocks[blk] = mod.run_block(product_model)
                else:
                    blocks[blk] = {"error": "no run_block() in module"}
            except Exception as e:
                blocks[blk] = {"error": str(e)}
        return {"blocks": blocks}