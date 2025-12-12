# logic_blocks/purchase_block.py
"""
Safe Purchase Block.
Minimal deterministic implementation that extracts price info and seller info if present.
Returns a stable dict for templates.
"""
from typing import Dict, Any

def run_block(product_model: Dict[str,Any]) -> Dict[str,Any]:
    try:
        price = product_model.get("price_inr") or product_model.get("price") or None
        purchase = {
            "price_inr": price,
            "available": True if price else False,
            "notes": "Generated purchase information (conservative)"
        }
        return purchase
    except Exception as e:
        return {"error": str(e)}
