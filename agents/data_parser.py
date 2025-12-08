"""
DataParserAgent stub
Parses the raw product input into canonical ProductModel.
"""
from typing import Dict

class DataParserAgent:
    def __init__(self, config: Dict = None):
        self.config = config or {}

    def run(self, raw_input: Dict) -> Dict:
        # minimal normalization (expand later)
        pm = {
            "id": "product_001",
            "name": raw_input.get("product_name"),
            "concentration": raw_input.get("concentration"),
            "skin_type": [s.strip() for s in raw_input.get("skin_type","").split(",") if s.strip()],
            "ingredients": [i.strip() for i in raw_input.get("key_ingredients","").split(",") if i.strip()],
            "benefits": [b.strip() for b in raw_input.get("benefits","").split(",") if b.strip()],
            "usage": raw_input.get("how_to_use"),
            "side_effects": raw_input.get("side_effects"),
            "price_inr": None
        }
        # simple price extraction
        price = raw_input.get("price","").replace("₹","").replace(",","").strip()
        try:
            pm["price_inr"] = int(price)
        except Exception:
            pm["price_inr"] = None
        return pm