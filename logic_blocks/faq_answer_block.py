# logic_blocks/faq_answer_block.py
"""
FAQ Answer Block
Generates deterministic answers for each question based ONLY on product attributes.
No external facts or domain knowledge allowed (per assignment rules).
"""

from typing import Dict, List

def derive_answer(question: str, product: Dict) -> str:
    """
    Strict, rules-based, no external domain knowledge.
    Answers use only product attributes.
    """

    name = product.get("name", "the product")
    usage = product.get("usage", "")
    benefits = ", ".join(product.get("benefits", [])) or "its listed benefits"
    ingredients = ", ".join(product.get("ingredients", [])) or "the listed ingredients"
    side_effects = product.get("side_effects", "No specific side effects listed.")
    price = product.get("price_inr")

    # Rule templates (deterministic)
    if "use" in question.lower():
        return f"You can use {name} as described: {usage}."

    if "side effect" in question.lower():
        return f"The product lists: {side_effects}"

    if "ingredient" in question.lower():
        return f"The key ingredients are: {ingredients}."

    if "benefit" in question.lower():
        return f"The listed benefits are: {benefits}."

    if "price" in question.lower() or "buy" in question.lower():
        if price:
            return f"The listed price is ₹{price}."
        else:
            return "The price is not specified."

    if "compare" in question.lower():
        return (
            f"{name} contains {ingredients} and offers benefits such as {benefits}. "
            "Comparison details depend on the other product’s attributes."
        )

    if "suitable" in question.lower():
        skin_types = ", ".join(product.get("skin_type", []))
        return f"It is listed as suitable for: {skin_types}."

    if "store" in question.lower():
        return f"No specific storage instructions are provided beyond normal product care."

    if "shelf life" in question.lower():
        return f"The shelf life is not specified in the provided data."

    if "result" in question.lower():
        return f"Results depend on consistent use. The listed benefits are: {benefits}."

    # fallback generic answer
    return f"This question relates to the product attributes: name={name}, benefits={benefits}, ingredients={ingredients}."
    

def run_block(product_model: Dict, questions: List[Dict]):
    """
    Returns: { "faq_items": [ {question, answer}, ... ] }
    """
    items = []
    for q in questions:
        q_text = q.get("text")
        ans = derive_answer(q_text, product_model)
        items.append({
            "question": q_text,
            "answer": ans
        })

    return {"faq_items": items}
