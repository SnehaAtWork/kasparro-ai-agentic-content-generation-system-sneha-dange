# agents/question_generator.py
"""
Deterministic QuestionGeneratorAgent.

Generates 15+ categorized questions based on ProductModel input.
Optional: an LLM adapter hook (not used by default).
"""
from typing import Dict, List, Callable, Optional


DEFAULT_CATEGORIES = [
    "Informational",
    "Usage",
    "Safety",
    "Purchase",
    "Comparison",
    "Ingredients",
    "Storage",
    "Suitability",
    "Effectiveness",
]


def _normalize_name(product_model: Dict) -> str:
    return product_model.get("name") or "this product"


def _mk(qid: int, category: str, text: str) -> Dict:
    return {"id": f"q{qid}", "category": category, "text": text}


class QuestionGeneratorAgent:
    def __init__(self, config: Dict = None, llm_adapter: Optional[Callable] = None):
        """
        config: optional config dict
        llm_adapter: optional callable(fn: List[Dict]) -> List[Dict] that can augment/paraphrase questions.
        """
        self.config = config or {}
        self.llm_adapter = llm_adapter

    def _generate_seed_questions(self, product_model: Dict) -> List[Dict]:
        name = _normalize_name(product_model)
        concentration = product_model.get("concentration")
        ingredients = product_model.get("ingredients", [])
        price = product_model.get("price_inr")

        qs = []
        qid = 1

        # Informational
        qs.append(_mk(qid, "Informational", f"What is {name} and who is it for?")); qid += 1
        qs.append(_mk(qid, "Informational", f"What does the concentration {concentration or 'N/A'} mean?")); qid += 1

        # Usage
        qs.append(_mk(qid, "Usage", f"How do I use {name} (steps and frequency)?")); qid += 1
        qs.append(_mk(qid, "Usage", f"Can I use {name} with other skincare products like retinol or acids?")); qid += 1

        # Safety
        qs.append(_mk(qid, "Safety", f"Are there any side effects when using {name}?")); qid += 1
        qs.append(_mk(qid, "Safety", f"Can people with sensitive skin use {name}?")); qid += 1

        # Purchase
        qs.append(_mk(qid, "Purchase", f"What is the price of {name} and is it value for money?")); qid += 1
        qs.append(_mk(qid, "Purchase", f"Where can I buy {name} and are there discounts available?")); qid += 1

        # Comparison
        qs.append(_mk(qid, "Comparison", f"How does {name} compare to other Vitamin C serums?")); qid += 1
        qs.append(_mk(qid, "Comparison", f"What are the advantages of {name} over similar products?")); qid += 1

        # Ingredients
        qs.append(_mk(qid, "Ingredients", f"What are the key ingredients in {name} and their roles?")); qid += 1
        qs.append(_mk(qid, "Ingredients", f"Is Hyaluronic Acid in {name} safe to use with Vitamin C?")); qid += 1

        # Storage & Expiry
        qs.append(_mk(qid, "Storage", f"How should I store {name} to preserve potency?")); qid += 1
        qs.append(_mk(qid, "Storage", f"What is the typical shelf life of {name} after opening?")); qid += 1

        # Suitability & Effectiveness
        qs.append(_mk(qid, "Suitability", f"Is {name} suitable for oily and combination skin?")); qid += 1
        qs.append(_mk(qid, "Effectiveness", f"How long before I see results with regular use of {name}?")); qid += 1

        # Safety extra: patch tests
        qs.append(_mk(qid, "Safety", f"Should I do a patch test before using {name}?")); qid += 1

        # Trim or expand logic can go here
        return qs

    def run(self, product_model: Dict) -> Dict:
        """
        Returns: { "questions": [ {id, category, text}, ... ] }
        Guarantees: >= 15 questions (if seed < 15, repeats are avoided by generating fallback generic questions)
        """
        seed = self._generate_seed_questions(product_model)

        # Ensure at least 15 unique questions
        if len(seed) < 15:
            extra_needed = 15 - len(seed)
            base = product_model.get("name", "the product")
            for i in range(extra_needed):
                seed.append(_mk(len(seed) + 1, "Informational", f"Additional question about {base} #{i+1}"))

        # Optional: call llm_adapter to paraphrase / expand (must return validated structure)
        if self.llm_adapter:
            try:
                augmented = self.llm_adapter(seed)
                # basic validation: list of dicts with id, category, text
                if isinstance(augmented, list) and all(isinstance(q, dict) for q in augmented):
                    return {"questions": augmented}
            except Exception:
                # fallback to deterministic seed if adapter fails
                pass

        return {"questions": seed}
