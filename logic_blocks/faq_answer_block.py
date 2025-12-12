# logic_blocks/faq_answer_block.py
"""
FINAL REFINED FAQ ANSWER LOGIC (v2)
-----------------------------------
Clean, deterministic, context-aware answer generation with:
- Correct intent classification
- Proper use of product fields
- Thoughtful fallback answers
- Neutral, safe "value" heuristic
- Expanded compatibility handling
- Concentration explanation
- Perfect integration with optional safe paraphraser
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


# =============================================================
# Helpers
# =============================================================

def _lower(s: str) -> str:
    return (s or "").lower()

def _safe_join(values):
    if isinstance(values, list):
        return ", ".join(values)
    return str(values) if values else ""


# =============================================================
# 1. QUESTION CLASSIFIER (v2 refined ordering + rules)
# =============================================================

def classify_question(q: str) -> str:
    ql = _lower(q)

    # 1. USAGE (strict patterns)
    if any(p in ql for p in [
        "how do i use", "how to use", "how should i use",
        "usage", "apply", "apply it", "steps", "frequency"
    ]):
        return "usage"

    # 2. OTHER (storage, shelf life, comparison FIRST to prevent overview fallback)
    if any(p in ql for p in [
        "store", "storage", "shelf life", "expire",
        "compare", "comparison", "difference"
    ]):
        return "other"

    # 3. VALUE (price + purchase)
    if any(p in ql for p in [
        "price", "cost", "buy", "purchase", "discount",
        "value for money", "where can i get", "where can i buy"
    ]):
        return "value"

    # 4. INGREDIENTS + COMPATIBILITY
    if any(p in ql for p in [
        "ingredient", "ingredients", "what is in",
        "retinol", "acid", "aha", "bha",
        "compatible", "use with", "hyaluronic"
    ]):
        return "ingredients"

    # 5. SAFETY + SKIN SUITABILITY
    if any(p in ql for p in [
        "side effect", "sensitive skin", "irritation",
        "skin type", "suitable for",
        "oily skin", "dry skin", "combination skin",
        "patch test"
    ]):
        return "safety"

    # 6. OVERVIEW (meaning, product definition, purpose)
    if any(p in ql for p in [
        "what is", "who is it for",
        "concentration", "mean"
    ]):
        return "overview"

    return "other"


# =============================================================
# 2. ANSWER LOGIC (v2)
# =============================================================

def generate_answer(category: str, q: str, product: Dict[str, Any]) -> str:
    ql = _lower(q)

    # ------------------------------ OVERVIEW ------------------------------
    if category == "overview":
        name = product.get("name", "this product")
        conc = product.get("concentration")
        benefits = product.get("benefits") or []

        # Special handling for concentration meaning questions
        if "concentration" in ql or "mean" in ql:
            if conc:
                return (
                    f"{conc} refers to the strength of the active ingredient in the formula. "
                    f"It indicates how potent the Vitamin C content is compared to lower percentages."
                )
            return "The concentration meaning is not provided in the product details."

        # Standard overview answer
        out = f"{name}."
        if benefits:
            out += f" Key benefits include {_safe_join(benefits)}."
        if conc:
            out += f" It contains {conc}."
        return out

    # ------------------------------ USAGE ------------------------------
    if category == "usage":
        usage = product.get("usage")
        return usage or "Usage instructions were not provided."

    # ------------------------------ INGREDIENTS / COMPATIBILITY ------------------------------
    if category == "ingredients":
        ingredients = product.get("ingredients")

        # Compatibility questions detection
        if any(p in ql for p in ["retinol", "acid", "aha", "bha", "hyaluronic", "compatible", "use with"]):
            return (
                "Compatibility with other active ingredients such as Vitamin C, retinol, hyaluronic acid, "
                "AHAs, or BHAs is not specified in the product details."
            )

        if ingredients:
            return f"The key ingredients include {_safe_join(ingredients)}."

        return "Ingredient information was not provided."

    # ------------------------------ SAFETY (side effects + suitability) ------------------------------
    if category == "safety":

        # Skin suitability
        if any(p in ql for p in ["skin type", "suitable for", "oily", "dry", "combination"]):
            st = product.get("skin_type")
            if st:
                return f"Suitable for {_safe_join(st)} skin types."
            return "Skin-type suitability information was not provided."

        # Side effects
        se = product.get("side_effects")
        return se or "Side-effect information was not provided."

    # ------------------------------ VALUE (price + value-for-money) ------------------------------
    if category == "value":
        price = product.get("price_inr")
        benefits = product.get("benefits") or []

        # Price-only question
        if "price" in ql or "cost" in ql:
            return f"The price is ₹{price}." if price else "Price information was not provided."

        # Value-for-money question
        if "value" in ql:
            if price and benefits:
                return (
                    f"The product offers benefits such as {_safe_join(benefits)}. "
                    f"At ₹{price}, its value depends on individual skincare needs and expectations "
                    f"but is consistent with typical Vitamin C serums."
                )
            elif price:
                return f"At ₹{price}, the value depends on your personal skincare goals."
            return "Value assessment is not possible because the price was not provided."

        # Purchase information
        return "Purchase information was not provided."

    # ------------------------------ OTHER (shelf life, storage, comparison, misc) ------------------------------

    # Storage
    if "store" in ql or "storage" in ql:
        return "Storage instructions were not provided."

    # Shelf life
    if "shelf life" in ql or "expire" in ql:
        return "Shelf-life information was not provided."

    # Comparison
    if "compare" in ql or "difference" in ql:
        return "Comparison information was not provided."

    return "This information was not provided in the product details."


# =============================================================
# 3. EXECUTION BLOCK WITH OPTIONAL SAFE PARAPHRASING
# =============================================================

def run_block(product_model: Dict[str, Any], questions: List[Dict[str, Any]], llm_adapter=None) -> Dict[str, Any]:
    """
    Deterministic → LLM-safe FAQ generation pipeline.
    """
    faq_items = []
    pid = product_model.get("id", "unknown")

    logger.info(f"[faq_block] Generating refined FAQ for product={pid}, questions={len(questions)}")

    # Deterministic answers first
    for q in questions:
        q_text = q.get("text") or q.get("question") or ""
        if not q_text:
            continue

        category = classify_question(q_text)
        answer = generate_answer(category, q_text, product_model)

        faq_items.append({
            "question": q_text,
            "answer": answer,
            "category": category
        })

    logger.info(f"[faq_block] Produced {len(faq_items)} deterministic answers.")

    # Apply safe paraphrasing only if enabled
    if llm_adapter is not None:
        logger.info("[faq_block] Applying safe paraphraser (LLM mode enabled)...")
        try:
            improved = llm_adapter(faq_items, product_model)
            return {"faq_items": improved, "llm_used": True}
        except Exception as e:
            logger.error(f"[faq_block] LLM paraphraser failed: {e}")
            return {"faq_items": faq_items, "llm_used": False}

    # Deterministic mode: no paraphrasing
    return {"faq_items": faq_items, "llm_used": False}

