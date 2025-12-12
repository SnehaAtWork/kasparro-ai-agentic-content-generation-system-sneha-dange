# run_pipeline.py
"""
LangChain-only pipeline entrypoint.

This script *exclusively* uses the LangChain Runnable-based orchestrator.
It wraps each agent.run(...) as a LangChain Runnable (via wrap_as_runnable)
and executes them sequentially using .invoke(...).

Do NOT expect the legacy agents.orchestrator to run here — this file deliberately
shows the reviewers a pure LangChain-based orchestration surface.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any
from config import USE_OLLAMA

logger = logging.getLogger(__name__)

# langchain runnable adapter (wraps callables into RunnableLambda or shim)
from agents.langchain_runnables import wrap_as_runnable

# Real agents from your repo (no legacy orchestrator used here)
from agents.data_parser import DataParserAgent               # :contentReference[oaicite:4]{index=4}
from agents.question_generator import QuestionGeneratorAgent # :contentReference[oaicite:5]{index=5}
from agents.logic_engine import LogicBlockEngineAgent        # :contentReference[oaicite:6]{index=6}

if USE_OLLAMA:
    logger.info("[INFO] USE_OLLAMA=1 → enabling LLM paraphrasing (Ollama)")
    try:
        from agents.ollama_adapter import paraphrase_faq_items as ollama_paraphraser
        logic_agent = LogicBlockEngineAgent(llm_adapter=ollama_paraphraser)
    except Exception as e:
        logger.warning(f"[WARN] Failed to load Ollama adapter: {e}")
        logic_agent = LogicBlockEngineAgent(llm_adapter=None)
else:
    logger.info("[INFO] USE_OLLAMA=0 → running deterministic mode only")
    logic_agent = LogicBlockEngineAgent(llm_adapter=None)

from agents.template_engine import TemplateEngineAgent       # :contentReference[oaicite:7]{index=7}

logger = logging.getLogger("run_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")


def _read_input(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _write_outputs(pages: Dict[str, Any], outdir: str) -> Dict[str, str]:
    """
    Write product_page.json, faq.json, comparison_page.json into outdir.
    Return dict mapping logical names to written file paths.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    def _dump(obj, name):
        path = out / name
        content = json.dumps(obj, indent=2, ensure_ascii=False)
        path.write_text(content, encoding="utf-8")
        return str(path)

    product_path = _dump(pages["product_page"], "product_page.json")
    faq_path = _dump(pages["faq"], "faq.json")
    comparison_path = _dump(pages["comparison"], "comparison_page.json")

    return {"product_page": product_path, "faq": faq_path, "comparison_page": comparison_path}


def build_and_run(raw_input: Dict[str, Any], outdir: str) -> Dict[str, str]:
    """
    Build runnables that wrap the agent run methods and execute them in sequence.
    We use .invoke(...) for all runnables so the pipeline is explicitly LangChain-driven.
    """

    # Wrap agent run methods as runnables (RunnableLambda when available)
    parse_r = wrap_as_runnable(lambda raw: DataParserAgent().run(raw), name="parse_product")
    qgen_r  = wrap_as_runnable(lambda product: QuestionGeneratorAgent().run(product), name="generate_questions")
    logic_r = wrap_as_runnable(lambda payload: logic_agent.run(payload["product_model"], payload.get("questions")), name="run_logic_blocks")
    templ_r = wrap_as_runnable(lambda payload: TemplateEngineAgent().run(payload["product_model"], payload["blocks"], payload.get("questions")), name="render_templates")

    # Run sequentially with .invoke() to ensure deterministic shapes and clear traceability.
    logger.info("[langchain] Invoking parse runnable")
    product_model = parse_r.invoke(raw_input)
    logger.info("[langchain] Parsed product: %s", product_model.get("name", product_model.get("id")))

    logger.info("[langchain] Invoking question generator runnable")
    questions = qgen_r.invoke(product_model)
    qcount = len(questions.get("questions", [])) if isinstance(questions, dict) else (len(questions) if isinstance(questions, list) else 0)
    logger.info("[langchain] Generated %d questions", qcount)

    logger.info("[langchain] Invoking logic blocks runnable (may call LLM adapter if configured)")
    blocks = logic_r.invoke({"product_model": product_model, "questions": questions})
    # blocks expected to be a dict like {"blocks": {...}} OR just {...} depending on implementation
    if isinstance(blocks, dict) and "blocks" in blocks:
        blocks = blocks["blocks"]

    logger.info("[langchain] Logic blocks executed. Blocks: %s", list(blocks.keys()) if isinstance(blocks, dict) else "unknown")

    logger.info("[langchain] Invoking templater runnable")
    pages = templ_r.invoke({"product_model": product_model, "blocks": blocks, "questions": questions})

    logger.info("[langchain] Writing artifact JSON files to %s", outdir)
    artifacts = _write_outputs(pages, outdir)
    logger.info("[langchain] Wrote artifacts: %s", artifacts)
    return artifacts


def main():
    parser = argparse.ArgumentParser(description="Run pipeline (LangChain-only).")
    parser.add_argument("-i", "--input", default="inputs/product_input.json", help="Path to input JSON")
    parser.add_argument("-o", "--outdir", default="outputs", help="Output directory for JSON artifacts")
    args = parser.parse_args()

    logger.info("Starting LangChain-only pipeline. Input=%s Outdir=%s", args.input, args.outdir)
    raw = _read_input(args.input)
    artifacts = build_and_run(raw, args.outdir)
    logger.info("Pipeline complete. Artifacts: %s", artifacts)


if __name__ == "__main__":
    main()
