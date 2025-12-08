def run_block(product_model: dict):
    se = product_model.get("side_effects","")
    return {"text": se, "warnings": [se] if se else []}