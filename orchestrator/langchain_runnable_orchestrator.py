# orchestrator/langchain_runnable_orchestrator.py
"""
Runnable-based LangChain orchestrator (v1.x).
This uses RunnableLambda wrappers around your actual agents.
"""

import json
from pathlib import Path

from agents.langchain_runnables import wrap_as_runnable
from agents.data_parser import DataParserAgent               # :contentReference[oaicite:9]{index=9}
from agents.question_generator import QuestionGeneratorAgent # :contentReference[oaicite:10]{index=10}
from agents.logic_engine import LogicBlockEngineAgent        # :contentReference[oaicite:11]{index=11}
from agents.template_engine import TemplateEngineAgent       # :contentReference[oaicite:12]{index=12}

import logging
logger = logging.getLogger(__name__)

# ---- Wrap each agent.run() in a RunnableLambda (or shim fallback) ----

parse_r = wrap_as_runnable(
    lambda raw: DataParserAgent().run(raw),
    name="parse_product"
)

qgen_r = wrap_as_runnable(
    lambda product: QuestionGeneratorAgent().run(product),
    name="generate_questions"
)

logic_r = wrap_as_runnable(
    lambda payload: LogicBlockEngineAgent().run(
        payload["product_model"],
        payload["questions"]
    ),
    name="run_logic_blocks"
)

templ_r = wrap_as_runnable(
    lambda payload: TemplateEngineAgent().run(
        payload["product_model"],
        payload["blocks"],
        payload["questions"]
    ),
    name="render_templates"
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
def run_pipeline_runnable(raw_input: dict) -> dict:
    try:
        # Try full Runnable composition (preferred)
        seq = (
            parse_r
            | (lambda p: {"product_model": p})
            | qgen_r
            | (lambda qs: {"questions": qs})
            | (lambda ctx: {
                "product_model": raw_input,  # Allow full model to propagate
                "questions": ctx["questions"]
            })
        )
        # Actually, our logic needs product_model + questions:
        # So run them manually for guaranteed shape correctness.
        raise Exception("Skip composition; use sequential invoke for predictable shapes.")
    except Exception:
        # 1. Parse
        product_model = parse_r.invoke(raw_input)

        # 2. Questions
        questions = qgen_r.invoke(product_model)

        # 3. Logic blocks
        blocks = logic_r.invoke({
            "product_model": product_model,
            "questions": questions
        })

        # 4. Templates
        pages = templ_r.invoke({
            "product_model": product_model,
            "blocks": blocks,
            "questions": questions
        })

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

    logger.info("Running LangChain Runnable-based orchestrator...")
    res = run_pipeline_runnable(SAMPLE)
    logger.info("Artifacts written:", res)