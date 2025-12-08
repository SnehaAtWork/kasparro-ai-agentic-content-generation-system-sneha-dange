def run_block(product_model: dict):
    usage = product_model.get("usage") or product_model.get("how_to_use","")
    # simple split into steps if comma/semicolon
    steps = [s.strip() for s in usage.replace(";",",").split(",") if s.strip()]
    return {"text": usage, "steps": steps}