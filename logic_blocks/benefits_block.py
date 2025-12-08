def run_block(product_model: dict):
    benefits = product_model.get("benefits", [])
    summary = " and ".join(benefits) if benefits else ""
    items = [{"title": b, "explanation": f"{b} effect."} for b in benefits]
    return {"summary": summary, "items": items}