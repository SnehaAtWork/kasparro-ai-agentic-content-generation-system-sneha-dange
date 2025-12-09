# logic_blocks/faq_answer_block.py
# (use the improved derive_answer from earlier, but include category in outputs)

from typing import Dict, List
import re

def _safe_join(items):
    return ", ".join(items) if items else ""

def _has_word(q: str, word: str):
    return re.search(rf"\b{re.escape(word)}\b", q, flags=re.I) is not None

def derive_answer(question: str, product: Dict) -> str:
    q = (question or "").strip()
    name = product.get("name", "the product")
    usage = product.get("usage") or product.get("how_to_use") or ""
    benefits = _safe_join(product.get("benefits", []))
    ingredients = _safe_join(product.get("ingredients", []))
    side_effects = product.get("side_effects") or ""
    skin_types = _safe_join(product.get("skin_type", []))
    price = product.get("price_inr")
    concentration = product.get("concentration") or ""

    # (same rules as we used earlier — kept concise here)
    if _has_word(q, "what is") or _has_word(q, "who is it for"):
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

    if _has_word(q, "concentration") or re.search(r"\b\d+%|\bpercent\b", q, flags=re.I):
        if concentration:
            return f"The listed concentration is {concentration} (as provided in the product data)."
        return "No concentration information is provided."

    if _has_word(q, "how do i use") or _has_word(q, "how to use") or _has_word(q, "use this product"):
        if usage:
            return f"Usage: {usage}"
        return "Usage instructions are not specified."

    if _has_word(q, "retinol") or _has_word(q, "acids") or _has_word(q, "combine") or _has_word(q, "with other"):
        return ("No explicit compatibility information with other actives is provided in the product data. "
                "Refer to product guidance or the product label for compatibility recommendations.")

    if _has_word(q, "side effect") or _has_word(q, "sensitive skin") or _has_word(q, "safety"):
        if side_effects:
            return f"Reported side effects: {side_effects}"
        return "No side effects are listed in the provided product data."

    if _has_word(q, "ingredient"):
        if ingredients:
            return f"Key ingredients: {ingredients}."
        return "No ingredients are listed."

    if _has_word(q, "price") or _has_word(q, "buy"):
        if price:
            return f"The listed price is ₹{price}."
        return "Price is not specified in the provided data."

    if _has_word(q, "suitable") or _has_word(q, "skin type") or _has_word(q, "oily") or _has_word(q, "combination"):
        if skin_types:
            return f"Listed skin types: {skin_types}."
        return "No skin type suitability is provided."

    if _has_word(q, "store") or _has_word(q, "shelf") or _has_word(q, "expiry"):
        return "No storage or shelf-life information is provided in the product data."

    if _has_word(q, "how long") or _has_word(q, "results") or _has_word(q, "see results"):
        if benefits:
            return f"The product lists benefits such as: {benefits}. Results are dependent on consistent use."
        return "No effectiveness information is provided."

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
    """
    items = []
    for q in questions:
        q_text = q.get("text", "")
        q_cat = q.get("category", "")
        ans = derive_answer(q_text, product_model)
        items.append({"question": q_text, "category": q_cat, "answer": ans})
    return {"faq_items": items}
