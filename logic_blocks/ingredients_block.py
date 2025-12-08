def run_block(product_model: dict):
    ingr = product_model.get("ingredients",[])
    return {"ingredients": ingr, "count": len(ingr)}