from logic_blocks.faq_answer_block import run_block

def test_faq_answer_basic():
    product = {
        "name": "GlowBoost Vitamin C Serum",
        "usage": "Apply 2–3 drops daily",
        "benefits": ["Brightening", "Fades dark spots"],
        "ingredients": ["Vitamin C", "Hyaluronic Acid"],
        "side_effects": "Mild tingling",
        "skin_type": ["Oily", "Combination"],
        "price_inr": 699
    }

    questions = [
        {"text": "How do I use this product?"},
        {"text": "What are the key ingredients?"},
        {"text": "Are there any side effects?"},
    ]

    out = run_block(product, questions)
    faq_items = out.get("faq_items", [])

    assert len(faq_items) == 3
    assert "use" in faq_items[0]["answer"].lower()
    assert "ingredients" in faq_items[1]["answer"].lower() or "vitamin c" in faq_items[1]["answer"].lower()
    assert "tingling" in faq_items[2]["answer"].lower()
