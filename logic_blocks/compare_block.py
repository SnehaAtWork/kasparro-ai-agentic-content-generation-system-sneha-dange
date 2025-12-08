def run_block(product_model: dict):
    # very simple comparison skeleton (replace with better logic later)
    comparison = {
        "price_diff": None,
        "shared_ingredients": []
    }
    try:
        b = {"ingredients":["Vitamin C","Glycerin"], "price_inr":799}
        a_price = product_model.get("price_inr")
        comparison["price_diff"] = (b["price_inr"] - a_price) if a_price else None
        comparison["shared_ingredients"] = list(set(product_model.get("ingredients",[])) & set(b["ingredients"]))
    except Exception:
        pass
    return comparison