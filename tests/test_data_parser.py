# tests/test_data_parser.py
from agents.data_parser import parse_raw_product, ProductModel

def test_parse_basic_input():
    raw = {
        "product_name": "GlowBoost Vitamin C Serum",
        "concentration": "10% Vitamin C",
        "skin_type": "Oily, Combination",
        "key_ingredients": "Vitamin C, Hyaluronic Acid",
        "benefits": "Brightening, Fades dark spots",
        "how_to_use": "Apply 2–3 drops in the morning before sunscreen",
        "side_effects": "Mild tingling for sensitive skin",
        "price": "₹699"
    }
    pm = parse_raw_product(raw)
    assert isinstance(pm, ProductModel)
    assert pm.name == "GlowBoost Vitamin C Serum"
    assert pm.concentration == "10% Vitamin C"
    assert pm.skin_type == ["Oily", "Combination"]
    assert pm.ingredients == ["Vitamin C", "Hyaluronic Acid"]
    assert pm.benefits == ["Brightening", "Fades dark spots"]
    assert pm.usage.startswith("Apply 2–3 drops")
    assert pm.side_effects.startswith("Mild tingling")
    assert pm.price_inr == 699

def test_parse_price_variations():
    raw = {"product_name": "X","price":"1,299"}
    pm = parse_raw_product(raw)
    assert pm.price_inr == 1299

    raw2 = {"product_name":"Y","price":"Rs. 2,499"}
    pm2 = parse_raw_product(raw2)
    assert pm2.price_inr == 2499

def test_parse_missing_fields():
    raw = {"product_name":"Z"}
    pm = parse_raw_product(raw)
    assert pm.name == "Z"
    assert pm.price_inr is None
    assert pm.ingredients == []
    assert pm.benefits == []
