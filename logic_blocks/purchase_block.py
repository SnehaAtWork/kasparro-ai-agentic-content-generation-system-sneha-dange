def run_block(product_model: dict):
    price = product_model.get("price_inr")
    return {"price_inr": price, "value_statement": f\"Priced at ₹{price}.\" if price else "Price not available."}