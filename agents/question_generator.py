# agents/question_generator.py
"""
QuestionGeneratorAgent

Produces a deterministic, config-driven set of questions for a product model.
The agent exposes a simple public API:
    qagent = QuestionGeneratorAgent()
    questions = qagent.run(product_model)

Questions are returned as a list of dicts with keys:
    - id: unique string
    - category: category name
    - text: question text

This implementation avoids imperative construction and instead uses a template list
for transparency and easy extension.
"""

from typing import Dict, List, Any
import itertools
import re


def _mk(qid: int, category: str, text: str) -> Dict[str, Any]:
    return {"id": f"q{qid:03d}", "category": category, "text": text}


def _normalize_name(product: Dict) -> str:
    name = product.get("name") or product.get("Product Name") or product.get("title") or "the product"
    # collapse whitespace
    return re.sub(r"\s+", " ", str(name)).strip()


class QuestionGeneratorAgent:
    """
    Config-driven question generator.
    The templates list can be adjusted or loaded from an external YAML/JSON config if desired.
    """

    # Default templates (category, template)
    _TEMPLATES = [
        ("Informational", "What is {name} and who is it for?"),
        ("Informational", "What does the concentration {concentration} mean for users?"),
        ("Usage", "How do I use {name} (steps and frequency)?"),
        ("Usage", "Can I use {name} with other skincare actives like retinol or acids?"),
        ("Safety", "Are there any side effects when using {name}?"),
        ("Safety", "Is {name} safe for sensitive skin?"),
        ("Purchase", "What is the price of {name} and is it value for money?"),
        ("Purchase", "Where can I buy {name} and are there discounts available?"),
        ("Comparison", "How does {name} compare to other Vitamin C serums?"),
        ("Comparison", "What are the advantages of {name} over similar products?"),
        ("Ingredients", "What are the key ingredients in {name} and what do they do?"),
        ("Ingredients", "Is Hyaluronic Acid in {name} safe to use with Vitamin C?"),
        ("Storage", "How should I store {name} to preserve potency?"),
        ("Storage", "What is the typical shelf life of {name} after opening?"),
        ("Suitability", "Is {name} suitable for oily and combination skin?"),
        ("Effectiveness", "How long before I see results with regular use of {name}?"),
        ("Safety", "Should I do a patch test before using {name}?"),
    ]

    def __init__(self, templates: List[tuple] = None, minimum_questions: int = 12):
        # Allow overriding templates for tests or customization
        self.templates = templates if templates is not None else list(self._TEMPLATES)
        self.minimum_questions = int(minimum_questions)

    def _render_templates(self, product: Dict) -> List[Dict[str, str]]:
        name = _normalize_name(product)
        concentration = product.get("concentration") or product.get("Concentration") or ""
        # Attempt to normalize ingredients & price for template niceties
        ingredients = product.get("ingredients") or product.get("Key Ingredients") or []
        try:
            ing_sample = ", ".join(ingredients[:2]) if isinstance(ingredients, (list, tuple)) and ingredients else ""
        except Exception:
            ing_sample = ""

        rendered = []
        for cat, tpl in self.templates:
            text = tpl.format(name=name, concentration=concentration, ingredients=ing_sample)
            rendered.append({"category": cat, "text": text})
        return rendered

    def run(self, product_model: Dict) -> List[Dict]:
        """
        Generate questions for the provided product_model.

        Returns:
            List[Dict]: list of question dicts with keys id, category, text
        """
        # Defensive: accept either raw product dict or structured model
        if product_model is None:
            product_model = {}

        # Render templates into concrete text
        rendered = self._render_templates(product_model)

        # If templates produce fewer than minimum_questions, auto-generate extras
        questions = []
        qid = 1
        for item in rendered:
            questions.append(_mk(qid, item["category"], item["text"]))
            qid += 1

        # Add filler questions if below minimum
        base_name = _normalize_name(product_model)
        while len(questions) < self.minimum_questions:
            questions.append(_mk(qid, "Informational", f"Additional question about {base_name} #{qid}"))
            qid += 1

        return questions


# Simple manual test when run as script
if __name__ == "__main__":
    sample = {
        "name": "GlowBoost Vitamin C Serum",
        "concentration": "10% Vitamin C",
        "ingredients": ["Vitamin C", "Hyaluronic Acid"]
    }
    agent = QuestionGeneratorAgent()
    qs = agent.run(sample)
    for q in qs:
        print(q)
