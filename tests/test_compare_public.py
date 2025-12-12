# tests/test_compare_public.py
from agents.data_parser import DataParserAgent
from logic_blocks.compare_block import run_block
import pytest

def test_compare_block_public_api():
    raw = {
        "Product Name": "GlowBoost",
        "Price": "₹699",
        "Key Ingredients": ["Vitamin C", "Hyaluronic Acid"],
        "Benefits": ["Brightening"],
        "How to Use": "Apply nightly",
        "Side Effects": ""
    }
    # Use public DataParserAgent to produce the product model as production code would
    parser = DataParserAgent()
    product_model = parser.run(raw)

    out = run_block(product_model)
    assert isinstance(out, dict)
    assert "product_b" in out
    assert "summary" in out
    assert "score" in out
    assert isinstance(out["score"], dict)
