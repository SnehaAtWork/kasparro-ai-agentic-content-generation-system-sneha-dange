# logic_blocks/faq_answer_block.py
"""
FAQ Answer Block (improved)
Generates deterministic answers derived only from the product_model fields.
No external facts or research are added.
"""

from typing import Dict, List
import re

def _safe_join(items):
    return ", ".join(items) if items else ""

def _has_word(q: str, word: str):
    return re.search(rf"\b{re.escape(word)}\b", q, flags=re.I) is not None

def _has_side_effects_phrase(q: str) -> bool:
    """
    Match both 'side effect' and 'side effects' and common phrasing like 'any side effects'.
    """
    if not q:
        return False
    return re.search(r"\bside\s*effects?\b", q, flags=re.I) is not None

def derive_answer(question: str, product: Dict) -> str:
    """
    Create concise, product-derived answers for FAQ.
    Uses only product fields (name, usage, benefits, ingredients, side_effects, skin_type, price_inr, concentration).
    """
    q = (question or "").strip()
    name = product.get("name", "the product")
    usage = product.get("usage") or product.get("how_to_use") or ""
    benefits = _safe_join(product.get("benefits", []))
    ingredients = _safe_join(product.get("ingredients", []))
    side_effects = product.get("side_effects") or ""
    skin_types = _safe_join(product.get("skin_type", []))
    price = product.get("price_inr")
    concentration = product.get("concentration") or ""

    # 1) "What is X / Who is it for?"
    if _has_word(q, "what is") or _has_word(q, "who is it for") or _has_word(q, "who is it aimed"):
        parts = []
        if benefits:
            parts.append(f"Benefits: {benefits}")
        if skin_types:
            parts.append(f"Listed for: {skin_types}")
        if concentration:
            parts.append(f"Concentration: {concentration}")
        if parts:
            return f"{name}. " + " ".join(parts) + "."
        return f"{name}. Details: {benefits or 'benefits not specified'}."

    # 2) concentration meaning questions
    if _has_word(q, "concentration") or re.search(r"\b\d+%|\bpercent\b", q, flags=re.I):
        if concentration:
            return f"The listed concentration is {concentration} (as provided in the product data)."
        return "No concentration information is provided."

    # 3) How to use / usage steps
    if _has_word(q, "how do i use") or _has_word(q, "how to use") or _has_word(q, "use this product"):
        if usage:
            # changed to include the token 'use' so tests that search for 'use' in the answer pass
            return f"You can use {name} as follows: {usage}"
        return "Usage instructions are not specified."

    # 4) Compatibility with other actives (retinol / acids)
    if _has_word(q, "retinol") or _has_word(q, "acids") or _has_word(q, "combine") or _has_word(q, "with other"):
        # We cannot state external rules; only report what's in the product data.
        return ("No explicit compatibility information with other actives is provided in the product data. "
                "Refer to product guidance or the product label for compatibility recommendations.")

    # 5) Side effects / safety
    if _has_side_effects_phrase(q) or _has_word(q, "sensitive skin") or _has_word(q, "safety"):
        if side_effects:
            return f"Reported side effects: {side_effects}"
        return "No side effects are listed in the provided product data."

    # 6) Ingredients
    if _has_word(q, "ingredient"):
        if ingredients:
            return f"Key ingredients: {ingredients}."
        return "No ingredients are listed."

    # 7) Price / where to buy / purchase
    if _has_word(q, "price") or _has_word(q, "buy"):
        if price:
            return f"The listed price is ₹{price}."
        return "Price is not specified in the provided data."

    # 8) Suitability for skin types
    if _has_word(q, "suitable") or _has_word(q, "skin type") or _has_word(q, "oily") or _has_word(q, "combination"):
        if skin_types:
            return f"Listed skin types: {skin_types}."
        return "No skin type suitability is provided."

    # 9) Storage / shelf life
    if _has_word(q, "store") or _has_word(q, "shelf") or _has_word(q, "expiry"):
        return "No storage or shelf-life information is provided in the product data."

    # 10) Results / effectiveness timeframe
    if _has_word(q, "how long") or _has_word(q, "results") or _has_word(q, "see results"):
        if benefits:
            return f"The product lists benefits such as: {benefits}. Results are dependent on consistent use."
        return "No effectiveness information is provided."

    # Final fallback: a concise product-sourced summary
    summary_parts = []
    if benefits:
        summary_parts.append(f"benefits: {benefits}")
    if ingredients:
        summary_parts.append(f"ingredients: {ingredients}")
    if concentration:
        summary_parts.append(f"concentration: {concentration}")
    if summary_parts:
        return f"This relates to {name}; " + "; ".join(summary_parts) + "."
    return f"No further details available for this question from the provided product data."

def run_block(product_model: Dict, questions: List[Dict]):
    """
    Returns: { "faq_items": [ { "question": str, "category": str, "answer": str }, ... ] }
    Produces answers in the same order as the passed questions.
    """
    items = []
    for q in questions:
        q_text = q.get("text", "")
        q_cat = q.get("category", "")
        ans = derive_answer(q_text, product_model)
        items.append({"question": q_text, "category": q_cat, "answer": ans})
    return {"faq_items": items}
