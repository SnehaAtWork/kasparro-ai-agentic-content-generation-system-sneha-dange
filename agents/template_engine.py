# agents/template_engine.py
"""
Robust TemplateEngineAgent.

- Loads templates from templates/<name>.json when present.
- If template file missing, uses a safe built-in default product_template.
- Resolves sources like "product.name", "blocks.benefits_block.items[0]" (simple list indexing supported).
- Uses conservative fallbacks for missing fields rather than raising, and logs missing required fields.
- Produces stable JSON artifacts with provenance.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def _safe_join(items):
    return ", ".join(items) if items else ""

def _split_usage_to_steps(usage_text: Optional[str]):
    if not usage_text or not isinstance(usage_text, str):
        return []
    parts = re.split(r"[.;\n]\s*|\sand\s|\sthen\s", usage_text)
    steps = [p.strip() for p in parts if p and p.strip()]
    return steps or [usage_text.strip()]

# Built-in default product_template used when templates/product_template.json is absent.
_DEFAULT_PRODUCT_TEMPLATE = {
    "name": "product_template",
    "required": ["price_inr"],
    "fields": {
        "name": {"source": "product.name", "max_len": 120},
        "hero_blurb": {"source": "product.short_description", "max_len": 160},
        "price_inr": {"source": "product.price_inr"},
        "price_statement": {"source": None},
        "highlights": {"source": "blocks.product_block.highlights"},
        "benefits": {"source": "blocks.benefits_block.items"},
        "ingredients": {"source": "product.ingredients"},
        "usage": {"source": "product.usage"},
        "metadata": {"source": None}
    }
}

class TemplateEngineAgent:
    def __init__(self, templates_dir: str = "templates", config: Dict = None):
        self.templates_dir = Path(templates_dir)
        self.config = config or {}

    def _load_template(self, name: str) -> Dict[str, Any]:
        path = self.templates_dir / f"{name}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf8"))
                logger.info("[templater] Loaded template from %s", path)
                return data
            except Exception as e:
                logger.warning("[templater] Failed to parse template %s: %s. Falling back to built-in.", path, e)
        else:
            logger.info("[templater] Template file %s not found; using built-in default.", path)
        # fallback default
        return _DEFAULT_PRODUCT_TEMPLATE

    def _traverse(self, root: Any, path: str):
        """
        Resolve dotted path with optional simple list indexing e.g. "ingredients[0]" on a root.
        Returns None when not resolvable.
        """
        if not path:
            return None
        cur = root
        # split by dots but keep bracket parts together
        parts = re.split(r"\.(?![^\[]*\])", path)
        for p in parts:
            if cur is None:
                return None
            # list index?
            m = re.match(r"^([^\[]+)\[(\d+)\]$", p)
            if m:
                key, idx = m.group(1), int(m.group(2))
                if isinstance(cur, dict):
                    cur = cur.get(key)
                else:
                    return None
                if isinstance(cur, list):
                    if 0 <= idx < len(cur):
                        cur = cur[idx]
                    else:
                        return None
                else:
                    return None
            else:
                if isinstance(cur, dict):
                    cur = cur.get(p)
                else:
                    return None
        return cur

    def _resolve_source(self, source: Optional[str], product: Dict, blocks: Dict):
        if not source:
            return None
        if source.startswith("product."):
            return self._traverse(product, source[len("product."):])
        if source.startswith("blocks."):
            return self._traverse(blocks, source[len("blocks."):])
        # allow top-level keys 'product' and 'blocks'
        if source == "product":
            return product
        if source == "blocks":
            return blocks
        # literal fallback: if source is a constant string in quotes
        lit = re.match(r"^\"(.+)\"$|^'(.+)'$", source)
        if lit:
            return lit.group(1) or lit.group(2)
        return None

    def _build_hero_fallback(self, product: Dict, blocks: Dict, max_len: int = 160) -> str:
        name = product.get("name") or "Product"
        b_summary = None
        try:
            b_summary = (blocks.get("benefits_block") or {}).get("summary")
        except Exception:
            b_summary = None
        if b_summary:
            candidate = f"{name} - {b_summary}"
        else:
            benefits = product.get("benefits") or []
            if benefits:
                candidate = f"{name} - Benefits: {_safe_join(benefits[:2])}"
            else:
                concentration = product.get("concentration")
                candidate = f"{name} - {concentration}" if concentration else name
        # sanitize
        candidate = "".join(ch for ch in candidate if ord(ch) >= 32)
        if max_len and len(candidate) > max_len:
            candidate = candidate[: max_len - 3].rstrip() + "..."
        return candidate

    def run(self, product_model: Dict, blocks: Dict, questions: Dict) -> Dict:
        tpl = self._load_template("product_template")
        page: Dict[str, Any] = {}
        fields = tpl.get("fields", {}) or {}
        # Resolve fields
        for fname, fmeta in fields.items():
            src = fmeta.get("source") if isinstance(fmeta, dict) else None
            val = self._resolve_source(src, product_model, blocks) if src else None
            # apply max length trimming for strings
            max_len = fmeta.get("max_len") if isinstance(fmeta, dict) else None
            if isinstance(val, str) and max_len:
                if len(val) > max_len:
                    val = val[: max_len - 3].rstrip() + "..."
            page[fname] = val

        # HERO BLURB fallback
        hero_meta = fields.get("hero_blurb", {}) or {}
        hero_max_len = hero_meta.get("max_len", 160)
        if not page.get("hero_blurb"):
            page["hero_blurb"] = self._build_hero_fallback(product_model, blocks, max_len=hero_max_len)

        # Price fallbacks: try product.price_inr, product.price, blocks.purchase_block.price_inr
        if page.get("price_inr") is None:
            page["price_inr"] = product_model.get("price_inr") or product_model.get("price") or \
                                (blocks.get("purchase_block") or {}).get("price_inr")

        # Price statement fallback
        if not page.get("price_statement"):
            price = page.get("price_inr")
            page["price_statement"] = f"Priced at ₹{price}." if price else "Price not specified."

        # Highlights fallback: prefer blocks.product_block.highlights else derive
        if not page.get("highlights"):
            highlights = (blocks.get("product_block") or {}).get("highlights") or []
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

        # Benefits: prefer block items, else model -> items
        if not page.get("benefits"):
            b_items = (blocks.get("benefits_block") or {}).get("items")
            if b_items:
                page["benefits"] = b_items
            else:
                pb = product_model.get("benefits") or []
                page["benefits"] = [{"title": b, "explanation": b} for b in pb]

        # Ingredients fallback: keep list
        if page.get("ingredients") is None:
            page["ingredients"] = product_model.get("ingredients") or []

        # usage steps
        usage_text = page.get("usage") or product_model.get("usage")
        page["usage_steps"] = _split_usage_to_steps(usage_text)

        # metadata
        if not page.get("metadata"):
            page["metadata"] = {
                "concentration": product_model.get("concentration") or None,
                "skin_type": product_model.get("skin_type") or []
            }

        # Enforce list types and non-null lists
        for k in ("highlights", "benefits", "ingredients", "usage_steps"):
            if page.get(k) is None:
                page[k] = []

        # Validate required fields (log missing but do not raise)
        missing = [r for r in tpl.get("required", []) if page.get(r) is None]
        if missing:
            logger.warning("[templater] Missing required fields in product_template: %s. Filling conservative defaults.", missing)
            # Fill conservative defaults for common required keys
            for r in missing:
                if r == "price_inr":
                    page["price_inr"] = page.get("price_inr") or None
                elif r == "name":
                    page["name"] = product_model.get("name") or product_model.get("id") or "Product"
                else:
                    page[r] = page.get(r) or None

        # Build outputs: product_page, faq, comparison
        result: Dict[str, Any] = {}
        result["product_page"] = page

        # FAQ: take faq_items from blocks
        faq_items = (blocks.get("faq_answer_block") or {}).get("faq_items", [])
        result["faq"] = {"product_id": product_model.get("id"), "items": faq_items}

        # Comparison assembly
        compare_block = blocks.get("compare_block") or {}
        comp_product_b = compare_block.get("product_b")
        comparison_payload = {k: v for k, v in compare_block.items() if k != "product_b"}
        result["comparison"] = {
            "product_a": product_model,
            "product_b": comp_product_b,
            "comparison": comparison_payload
        }

        # Provenance
        timestamp = datetime.utcnow().isoformat() + "Z"
        result["product_page"]["last_updated"] = timestamp
        result["product_page"]["source"] = "input_product_model"
        result["faq"]["last_updated"] = timestamp
        result["faq"]["source"] = "generated_faq"
        result["comparison"]["last_updated"] = timestamp
        result["comparison"]["source"] = "comparison_block"

        return result
