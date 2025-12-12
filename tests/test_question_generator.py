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

    # out must be a list
    assert isinstance(out, list)

    # Should generate >= minimum_questions
    assert len(out) >= agent.minimum_questions

    # Each item in list must have required keys
    for q in out:
        assert "id" in q
        assert "category" in q
        assert "text" in q
        assert isinstance(q["id"], str)
        assert isinstance(q["category"], str)
        assert isinstance(q["text"], str)
