# tests/test_question_generator.py
from agents.question_generator import QuestionGeneratorAgent

def test_generate_minimum_questions():
    pm = {
        "name": "GlowBoost Vitamin C Serum",
        "concentration": "10% Vitamin C",
        "ingredients": ["Vitamin C", "Hyaluronic Acid"],
        "price_inr": 699,
    }
    agent = QuestionGeneratorAgent()
    out = agent.run(pm)
    qs = out.get("questions", [])
    # Must produce at least 15
    assert len(qs) >= 15
    # Check categories exist and are non-empty strings
    for q in qs:
        assert "id" in q and q["id"].startswith("q")
        assert "category" in q and isinstance(q["category"], str) and q["category"]
        assert "text" in q and isinstance(q["text"], str) and q["text"]
