# tests/test_end_to_end.py
import json
import tempfile
from pathlib import Path
import shutil
import os
import pytest

# Try to import build_and_run from run_pipeline (preferred). Fall back to subprocess if not importable.
try:
    from run_pipeline import build_and_run
    _HAS_BUILD = True
except Exception:
    _HAS_BUILD = False
    import subprocess, sys

SAMPLE = {
    "Product Name": "GlowBoost Vitamin C Serum",
    "Concentration": "10% Vitamin C",
    "Skin Type": "Oily, Combination",
    "Key Ingredients": ["Vitamin C", "Hyaluronic Acid"],
    "Benefits": ["Brightening", "Fades dark spots"],
    "How to Use": "Apply 2–3 drops in the morning before sunscreen",
    "Side Effects": "Mild tingling for sensitive skin",
    "Price": "₹699"
}

def _read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def test_end_to_end_creates_outputs(tmp_path):
    outdir = tmp_path / "outputs"
    outdir.mkdir()

    if _HAS_BUILD:
        artifacts = build_and_run(SAMPLE, str(outdir))
    else:
        # write SAMPLE to a temp file and call CLI
        inp = tmp_path / "input.json"
        inp.write_text(json.dumps(SAMPLE, indent=2, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run([sys.executable, "run_pipeline.py", "-i", str(inp), "-o", str(outdir)], capture_output=True, text=True)
        assert proc.returncode == 0, f"run_pipeline failed: {proc.stderr}"
        # heuristic: list output files
        artifacts = {p.name: str(p) for p in outdir.iterdir()}

    # Assert the three artifact JSONs exist
    expected = {"product_page.json", "faq.json", "comparison_page.json"}
    found = set([p.name for p in outdir.iterdir()])
    assert expected.issubset(found), f"Missing expected outputs: {expected - found}"

    # Basic content sanity check
    product = _read_json(outdir / "product_page.json")
    assert isinstance(product, dict)
    assert product.get("title") or product.get("name")

    faq = _read_json(outdir / "faq.json")
    assert "qna" in faq or "faq_items" in faq or isinstance(faq, dict)

    comparison = _read_json(outdir / "comparison_page.json")
    # should contain summary and product_b
    assert "summary" in comparison or "product_b" in comparison or isinstance(comparison, dict)
