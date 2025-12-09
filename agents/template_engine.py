# agents/template_engine.py
"""
TemplateEngineAgent: assemble pages from template specs and block outputs.

Resilient: when a required template field is missing, construct conservative fallback
derived only from product_model and other blocks. Ensures no nulls for list/object fields.
"""
import json
from typing import Dict, Any
from pathlib import Path
import re
from datetime import datetime

def _safe_join(items):
    return ", ".join(items) if items else ""

def _split_usage_to_steps(usage_text: str):
    """
    Deterministic, conservative splitter for usage instructions.
    Splits on punctuation, 'and', 'then', or newlines but preserves short phrases.
    Returns list of steps (empty list if no usage).
    """
    if not usage_text or not isinstance(usage_text, str):
        return []
    parts = re.split(r"[.;\n]\s*|\sand\s|\sthen\s", usage_text)
    steps = [p.strip() for p in parts if p and p.strip()]
    return steps or [usage_text.strip()]

class TemplateEngineAgent:
    def __init__(self, templates_dir: str = "templates", config: Dict = None):
        self.templates_dir = Path(templates_dir)
        self.config = config or {}

    def _load_template(self, name: str) -> Dict[str, Any]:
        path = self.templates_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        return json.loads(path.read_text(encoding="utf8"))

    def _resolve_source(self, source: str, product: Dict, blocks: Dict) -> Any:
        if not source:
            return None
        parts = source.split(".")
        val = None
        if parts[0] == "product":
            val = product
            for p in parts[1:]:
                val = val.get(p) if isinstance(val, dict) else None
        elif parts[0] == "blocks":
            val = blocks
            for p in parts[1:]:
                val = val.get(p) if isinstance(val, dict) else None
        else:
            val = None
        return val

    def _build_hero_fallback(self, product: Dict, blocks: Dict, max_len: int = 160) -> str:
        name = product.get("name", "Product")
        # 1) benefits_block summary
        b_summary = blocks.get("benefits_block", {}).get("summary")
        if b_summary:
            candidate = f"{name} - {b_summary}"
        else:
            benefits = product.get("benefits") or []
            if benefits:
                candidate = f"{name} - Benefits: {', '.join(benefits[:2])}"
            else:
                concentration = product.get("concentration")
                if concentration:
                    candidate = f"{name} - {concentration}"
                else:
                    candidate = name
        # sanitize unusual characters
        candidate = "".join(ch for ch in candidate if ord(ch) >= 32)
        if max_len and len(candidate) > max_len:
            candidate = candidate[: max_len - 3].rstrip() + "..."
        return candidate


    def run(self, product_model: Dict, blocks: Dict, questions: Dict) -> Dict:
        result = {}

        # PRODUCT PAGE
        tpl = self._load_template("product_template")
        page = {}
        fields = tpl.get("fields", {})
        for fname, fmeta in fields.items():
            src = fmeta.get("source")
            val = self._resolve_source(src, product_model, blocks)
            # enforce max_len if present
            max_len = fmeta.get("max_len")
            if isinstance(val, str) and max_len:
                if len(val) > max_len:
                    val = val[: max_len - 3].rstrip() + "..."
            page[fname] = val

        # HERO BLURB fallback
        hero_meta = fields.get("hero_blurb", {})
        hero_max_len = hero_meta.get("max_len", 160)
        if not page.get("hero_blurb"):
            page["hero_blurb"] = self._build_hero_fallback(product_model, blocks, max_len=hero_max_len)

        # Ensure price_statement fallback
        if not page.get("price_statement"):
            price = product_model.get("price_inr")
            page["price_statement"] = f"Priced at ₹{price}." if price else "Price not specified."

        # Ensure highlights fallback
        if not page.get("highlights"):
            # try blocks.product_block.highlights first, then derive
            highlights = blocks.get("product_block", {}).get("highlights") or []
            if not highlights:
                benefits = product_model.get("benefits") or []
                ingredients = product_model.get("ingredients") or []
                concentration = product_model.get("concentration")
                if benefits:
                    highlights.append(f"Primary benefits: {_safe_join(benefits[:2])}")
                if ingredients:
                    highlights.append(f"Key ingredients: {_safe_join(ingredients[:2])}")
                if concentration:
                    highlights.append(f"Concentration: {concentration}")
            page["highlights"] = highlights[:3]

        # Ensure benefits: prefer block items, else convert product.benefits -> items
        if not page.get("benefits"):
            b_items = blocks.get("benefits_block", {}).get("items")
            if b_items:
                page["benefits"] = b_items
            else:
                pb = product_model.get("benefits") or []
                page["benefits"] = [{"title": b, "explanation": b} for b in pb]

        # Ensure metadata present
        if not page.get("metadata"):
            page["metadata"] = {
                "concentration": product_model.get("concentration") or None,
                "skin_type": product_model.get("skin_type") or []
            }

        # Ensure list-like fields are non-null
        if page.get("highlights") is None:
            page["highlights"] = []
        if page.get("benefits") is None:
            page["benefits"] = []
        if page.get("ingredients") is None:
            page["ingredients"] = []

        # Convert usage string into structured steps
        usage_text = page.get("usage")
        page["usage_steps"] = _split_usage_to_steps(usage_text)


        # Validate required
        missing = [r for r in tpl.get("required", []) if page.get(r) is None]
        if missing:
            raise ValueError(f"Missing required fields for product_template: {missing}")

        result["product_page"] = page

        # FAQ + comparison as before
        faq_block = blocks.get("faq_answer_block", {}).get("faq_items", [])
        result["faq"] = {"product_id": product_model.get("id"), "items": faq_block[:5]}

        comparison = {
            "product_a": product_model,
            "product_b": (blocks.get("compare_block") or {}).get("product_b", {"id": "product_b_001", "name": "Product B"}),
            "comparison": blocks.get("compare_block", {})
        }
        result["comparison"] = comparison

        # --- Provenance injection (clean, minimal, consistent) ---
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Product page provenance
        result["product_page"]["last_updated"] = timestamp
        result["product_page"]["source"] = "input_product_model"

        # FAQ provenance
        result["faq"]["last_updated"] = timestamp
        result["faq"]["source"] = "generated_faq"

        # Comparison page provenance
        result["comparison"]["last_updated"] = timestamp
        result["comparison"]["source"] = "comparison_block"

        return result
