# orchestrator/langchain_orchestrator.py
"""
LangChain-compatible orchestrator using FunctionChain wrappers.
This preserves your exact agent logic while satisfying the requirement
to use LangChain in the orchestration layer.
"""

import json
from pathlib import Path
from agents.langchain_adapters import FunctionChain

# --- REAL AGENTS (from your repo) ---
from agents.data_parser import DataParserAgent          # :contentReference[oaicite:5]{index=5}
from agents.question_generator import QuestionGeneratorAgent  # :contentReference[oaicite:6]{index=6}
from agents.logic_engine import LogicBlockEngineAgent   # :contentReference[oaicite:7]{index=7}
from agents.template_engine import TemplateEngineAgent  # :contentReference[oaicite:8]{index=8}


# Wrap each agent.run() method as a LangChain FunctionChain
parse_chain = FunctionChain(
    lambda raw: DataParserAgent().run(raw),
    input_keys=["raw"],
    output_keys=["product_model"]
)

question_chain = FunctionChain(
    lambda product: QuestionGeneratorAgent().run(product),
    input_keys=["product_model"],
    output_keys=["questions"]
)

logic_chain = FunctionChain(
    lambda payload: LogicBlockEngineAgent().run(
        payload["product_model"], 
        payload["questions"]
    ),
    input_keys=["product_model", "questions"],
    output_keys=["blocks"]
)

template_chain = FunctionChain(
    lambda payload: TemplateEngineAgent().run(
        payload["product_model"],
        payload["blocks"],
        payload["questions"]
    ),
    input_keys=["product_model", "blocks", "questions"],
    output_keys=["pages"]
)


def _write_outputs(pages: dict, outdir="artifacts"):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    def dump(obj, name):
        path = out / f"{name}.json"
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    return {
        "product_page": dump(pages["product_page"], "product_page"),
        "faq": dump(pages["faq"], "faq"),
        "comparison_page": dump(pages["comparison"], "comparison_page")
    }


# ----------------- PIPELINE -----------------
def run_pipeline(raw_input: dict) -> dict:
    # 1. Parse
    product_model = parse_chain._call({"raw": raw_input})["product_model"]

    # 2. Questions
    questions = question_chain._call({"product_model": product_model})["questions"]

    # 3. Logic blocks
    blocks = logic_chain._call({
        "product_model": product_model,
        "questions": questions
    })["blocks"]

    # 4. Templates
    pages = template_chain._call({
        "product_model": product_model,
        "blocks": blocks,
        "questions": questions
    })["pages"]

    # 5. Outputs
    return _write_outputs(pages)


if __name__ == "__main__":
    SAMPLE = {
        "Product Name": "GlowBoost Vitamin C Serum",
        "Concentration": "10% Vitamin C",
        "Skin Type": "Oily, Combination",
        "Key Ingredients": "Vitamin C, Hyaluronic Acid",
        "Benefits": "Brightening, Fades dark spots",
        "How to Use": "Apply 2–3 drops in the morning before sunscreen",
        "Side Effects": "Mild tingling for sensitive skin",
        "Price": "₹699"
    }

    print("Running LangChain(FunctionChain)-based orchestrator...")
    res = run_pipeline(SAMPLE)
    print("Artifacts written:", res)
