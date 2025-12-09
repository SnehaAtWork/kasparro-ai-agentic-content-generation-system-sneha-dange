# logic_blocks/product_block.py
"""
Product block: creates hero_blurb, highlights, price_statement and metadata
using only product fields. Returns deterministic, ASCII-safe outputs.
"""
from typing import Dict, List

def _safe_join(items):
    return ", ".join(items) if items else ""

def _sanitize_text(s: str) -> str:
    # Remove control characters and replace non-ASCII bullets with plain separators
    if not isinstance(s, str):
        return ""
    # replace known fancy bullets with colon/space
    s = s.replace("•", " - ").replace("·", " - ")
    # remove other non-printable characters
    return "".join(ch for ch in s if ord(ch) >= 32)

def run_block(product_model: Dict) -> Dict:
    name = product_model.get("name", "the product")
    benefits = product_model.get("benefits") or []
    ingredients = product_model.get("ingredients") or []
    concentration = product_model.get("concentration") or ""
    price = product_model.get("price_inr")

    # Hero blurb: short (<= 160 chars) summary from benefits + concentration
    hero_parts = []
    if benefits:
        hero_parts.append("Benefits: " + _safe_join(benefits))
    if concentration:
        hero_parts.append(concentration)
    if hero_parts:
        hero_blurb = f"{name} - " + " | ".join(hero_parts)
    else:
        hero_blurb = name

    hero_blurb = _sanitize_text(hero_blurb)
    if len(hero_blurb) > 160:
        hero_blurb = hero_blurb[:157].rstrip() + "..."

    # Highlights: up to 3 short bullets derived from product fields
    highlights: List[str] = []
    if benefits:
        highlights.append(f"Primary benefits: {_safe_join(benefits)}")
    if ingredients:
        highlights.append(f"Key ingredients: {_safe_join(ingredients)}")
    if concentration:
        highlights.append(f"Concentration: {concentration}")
    if price and len(highlights) < 3:
        highlights.append(f"Price: ₹{price}")

    highlights = highlights[:3]

    # price statement
    price_statement = f"Priced at ₹{price}." if price else "Price not specified."

    metadata = {
        "concentration": concentration if concentration else None,
        "skin_type": product_model.get("skin_type") or []
    }

    # Ensure shapes are non-null
    return {
        "hero_blurb": hero_blurb,
        "highlights": highlights,
        "price_statement": price_statement,
        "metadata": metadata
    }
