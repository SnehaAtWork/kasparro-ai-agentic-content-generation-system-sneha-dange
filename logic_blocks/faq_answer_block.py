# logic_blocks/faq_answer_block.py
"""
Deterministic FAQ Answer Block (Final Version)
- Purely rule-based.
- No LLM logic here.
- LLM paraphrasing is handled ONLY by LogicEngine if llm_adapter is enabled.
"""

import logging

logger = logging.getLogger(__name__)


def _normalize(text):
    if not text:
        return ""
    return text.strip()


def _answer_or_fallback(value, fallback):
    """
    Returns the product field if present,
    otherwise returns a clean fallback string.
    """
    if value is None:
        return fallback
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return fallback
        return ", ".join([str(v) for v in value])
    if isinstance(value, str) and value.strip() == "":
        return fallback
    return str(value)


def run_block(product_model, questions):
    """
    Produce deterministic FAQ answers with zero hallucination.
    LLM paraphrasing is *not* done here — LogicEngine handles that separately.
    """

    logger.info(
        "[faq_block] Generating deterministic FAQ for product=%s, questions=%d",
        product_model.get("id"),
        len(questions),
    )

    pm = product_model
    safe = lambda field, fallback: _answer_or_fallback(pm.get(field), fallback)

    faqs = []

    for q in questions:
        text = q.get("text", "").lower().strip()

        # 1. Usage
        if "use" in text or "apply" in text or "how to" in text:
            raw_usage = safe("usage", "Usage information was not provided.")
            ans = f"You can use it as follows: {raw_usage}"
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 2. Ingredients
        if "ingredient" in text:
            ans = safe("ingredients", "Key ingredients were not provided.")
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 3. Benefits
        if "benefit" in text or "good for" in text:
            ans = safe("benefits", "Benefits were not provided.")
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 4. Side effects / safety
        if "side effect" in text or "safe" in text or "sensitive" in text:
            ans = safe("side_effects", "No safety information was provided.")
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 5. Skin type / suitability
        if "skin" in text or "suitable" in text:
            ans = safe("skin_type", "Skin suitability information was not provided.")
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 6. Price
        if "price" in text or "cost" in text:
            price = pm.get("price_inr")
            if price:
                ans = f"The price is ₹{price}."
            else:
                ans = "Price information was not provided."
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 7. Comparison
        if "compare" in text or "difference" in text:
            ans = "Comparison information is available in the comparison section."
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 8. Purchase
        if "where to buy" in text or "purchase" in text:
            ans = "Purchase information was not provided."
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 9. Storage
        if "store" in text or "storage" in text:
            ans = "Storage instructions were not provided."
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 10. Shelf life
        if "shelf" in text or "expire" in text or "expiry" in text:
            ans = "Shelf-life information was not provided."
            faqs.append({"question": q["text"], "answer": ans})
            continue

        # 11. DEFAULT fallback — safe, flat, non-hallucinatory
        ans = "This information was not provided in the product details."
        faqs.append({"question": q["text"], "answer": ans})

    logger.info(
        "[faq_block] Deterministic FAQ generation complete. count=%d", len(faqs)
    )

    return {"faq_items": faqs}
