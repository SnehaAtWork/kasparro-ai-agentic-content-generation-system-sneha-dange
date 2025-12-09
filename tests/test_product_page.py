from pathlib import Path
from agents.template_engine import TemplateEngineAgent

def test_product_page_assembly():
    # minimal fixture using parse output + blocks stub
    product = {
        "id":"product_001",
        "name":"GlowBoost Vitamin C Serum",
        "concentration":"10% Vitamin C",
        "skin_type":["Oily","Combination"],
        "ingredients":["Vitamin C","Hyaluronic Acid"],
        "benefits":["Brightening","Fades dark spots"],
        "usage":"Apply 2–3 drops in the morning before sunscreen",
        "side_effects":"Mild tingling for sensitive skin",
        "price_inr":699,
        "metadata":{"concentration":"10% Vitamin C"}
    }

    blocks = {
        "product_block": {
            "hero_blurb":"GlowBoost Vitamin C Serum — Benefits: Brightening • Fades dark spots • 10% Vitamin C",
            "highlights":["Primary benefits: Brightening, Fades dark spots","Key ingredients: Vitamin C, Hyaluronic Acid","Concentration: 10% Vitamin C"],
            "price_statement":"Priced at ₹699."
        },
        "ingredients_block": {"ingredients":["Vitamin C","Hyaluronic Acid"], "count":2},
        "benefits_block": {"summary":"Brightens skin", "items":[{"title":"Brightening","explanation":"..."}]},
        "usage_block": {"text":"Apply 2–3 drops...","steps":["Apply 2-3 drops","Use sunscreen"]},
        "safety_block": {"text":"Mild tingling for sensitive skin"}
    }

    t = TemplateEngineAgent()
    out = t.run(product, blocks, {"questions":[]})
    page = out["product_page"]

    assert page["id"] == "product_001"
    assert "hero_blurb" in page and isinstance(page["hero_blurb"], str)
    assert page["price_inr"] == 699
    assert isinstance(page["highlights"], list)
