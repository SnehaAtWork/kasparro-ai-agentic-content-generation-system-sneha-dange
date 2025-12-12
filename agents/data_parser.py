# agents/data_parser.py
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, validator, Field
import re

PRICE_RE = re.compile(r"[\d,]+")

class ProductModel(BaseModel):
    id: str = Field(default="product_001")
    name: str
    concentration: Optional[str] = None
    skin_type: List[str] = []
    ingredients: List[str] = []
    benefits: List[str] = []
    usage: Optional[str] = None
    side_effects: Optional[str] = None
    price_inr: Optional[int] = None
    raw: Dict[str, Any] = {}

    @validator("skin_type", pre=True)
    def normalize_skin_type(cls, v):
        # Accept comma-separated string or list
        if v is None:
            return []
        if isinstance(v, list):
            return [s.strip() for s in v if s and isinstance(s, str)]
        if isinstance(v, str):
            return [s.strip() for s in re.split(r"[;,]", v) if s.strip()]
        raise ValueError("skin_type must be a list or string")

    @validator("ingredients", pre=True)
    def normalize_ingredients(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [i.strip() for i in v if i and isinstance(i, str)]
        if isinstance(v, str):
            return [s.strip() for s in re.split(r"[;,]", v) if s.strip()]
        raise ValueError("ingredients must be a list or string")

    @validator("benefits", pre=True)
    def normalize_benefits(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [s.strip() for s in v if s and isinstance(s, str)]
        if isinstance(v, str):
            return [s.strip() for s in re.split(r"[;,]", v) if s.strip()]
        raise ValueError("benefits must be a list or string")

    @validator("price_inr", pre=True, always=True)
    def parse_price(cls, v, values):
        # If price already integer, return it; otherwise try to parse from raw input
        if isinstance(v, int):
            return v
        # attempt to find a price in the raw input if present
        raw = values.get("raw") or {}
        price_field = v if v is not None else raw.get("price") or raw.get("price_inr") or raw.get("Price")
        if price_field is None:
            return None
        # price_field could be string like "₹699" or "699" or "699.00"
        if isinstance(price_field, (int, float)):
            return int(price_field)
        if isinstance(price_field, str):
            match = PRICE_RE.search(price_field.replace("₹", "").replace("Rs.", "").replace("INR", ""))
            if match:
                try:
                    return int(match.group(0).replace(",", ""))
                except Exception:
                    return None
        return None

def parse_raw_product(raw: Dict[str, Any]) -> ProductModel:
    """
    Parse the raw input dict into a validated ProductModel.
    Keeps the raw input attached in the model for traceability.
    """
    # normalize keys (allow different casing/underscores)
    # map expected keys to raw fields
    mapping = {
        # accept all common variants
        "name": (
            raw.get("product_name")
            or raw.get("Product Name")
            or raw.get("name")
            or raw.get("product")
        ),

        "concentration": (
            raw.get("concentration")
            or raw.get("Concentration")
        ),

        "skin_type": (
            raw.get("skin_type")
            or raw.get("Skin Type")
        ),

        "ingredients": (
            raw.get("key_ingredients")
            or raw.get("Key Ingredients")
            or raw.get("ingredients")
        ),

        "benefits": (
            raw.get("benefits")
            or raw.get("Benefits")
        ),

        "usage": (
            raw.get("how_to_use")
            or raw.get("How to Use")
            or raw.get("usage")
        ),

        "side_effects": (
            raw.get("side_effects")
            or raw.get("Side Effects")
        ),
    }

    pm_input = {
        "id": raw.get("id", "product_001"),
        "raw": raw,
        **mapping,
    }
    # Include price field raw if present - price_inr validator will parse it
    if "price" in raw:
        pm_input["price_inr"] = raw.get("price")
    if "price_inr" in raw:
        pm_input["price_inr"] = raw.get("price_inr")

    model = ProductModel(**pm_input)
    return model

class DataParserAgent:
    def __init__(self, config: Dict = None):
        self.config = config or {}

    def run(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a canonical dict representation (ProductModel.dict()).
        """
        product = parse_raw_product(raw_input)
        return product.dict()
