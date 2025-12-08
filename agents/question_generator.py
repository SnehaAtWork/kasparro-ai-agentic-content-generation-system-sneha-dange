"""
QuestionGeneratorAgent stub
Generates categorized questions given a ProductModel.
"""
from typing import Dict, List

class QuestionGeneratorAgent:
    def __init__(self, config: Dict = None):
        self.config = config or {}

    def run(self, product_model: Dict) -> Dict:
        # simple heuristic-based questions (expand later)
        name = product_model.get("name", "the product")
        qs = [
            {"id":"q1","category":"Informational","text":f"What is {name} used for?"},
            {"id":"q2","category":"Usage","text":"How do I use this product?"},
            {"id":"q3","category":"Safety","text":"Are there any side effects?"},
            {"id":"q4","category":"Purchase","text":"What is the price and value for money?"},
            {"id":"q5","category":"Comparison","text":"How does it compare to other Vitamin C serums?"},
        ]
        # later expand to 15+; for now return a base object
        return {"questions": qs}