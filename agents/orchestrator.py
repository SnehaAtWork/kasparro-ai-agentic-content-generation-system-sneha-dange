# agents/orchestrator.py
"""
OrchestratorAgent - orchestrates parser -> question generator -> logic blocks -> templater.
Writes JSON outputs using UTF-8 encoding to avoid encoding errors on Windows (e.g. ₹).
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

# lazy import helper to avoid import-time side effects
def _lazy_import(name: str):
    module = __import__(name, fromlist=["dummy"])
    return module

class OrchestratorAgent:
    def __init__(self, config: dict = None):
        self.config = config or {}

    def _choose_llm_adapter(self) -> Optional[callable]:
        """
        Prefer local Ollama adapter if available (OLLAMA_BASE), else try OpenAI adapter.
        Returns a callable(llm_items, product_model) or None.
        """
        # try Ollama first
        try:
            if os.getenv("OLLAMA_BASE") or os.getenv("USE_OLLAMA", "1") == "1":
                # default base if unset
                os.environ.setdefault("OLLAMA_BASE", "http://localhost:11434")
                from agents.ollama_adapter import paraphrase_faq_items as ollama_paraphrase  # type: ignore
                print("[orchestrator] Using Ollama adapter for FAQ paraphrasing.")
                return ollama_paraphrase
        except Exception as e:
            print("[orchestrator] Ollama adapter not available:", e)

        # fallback to OpenAI adapter if available and key present
        try:
            from agents.llm_adapter import paraphrase_faq_items as openai_paraphrase  # type: ignore
            if os.getenv("OPENAI_API_KEY"):
                print("[orchestrator] Using OpenAI adapter for FAQ paraphrasing.")
                return openai_paraphrase
        except Exception as e:
            # not fatal; adapter is optional
            print("[orchestrator] OpenAI adapter not available:", e)

        # no adapter available
        print("[orchestrator] No LLM paraphrase adapter will be used (deterministic fallback).")
        return None

    def run(self, input_path: str, outputs_dir: str = "outputs") -> dict:
        """
        Run end-to-end pipeline and write outputs under `outputs_dir`.
        Returns dict of output file paths.
        """
        p = Path(input_path)
        if not p.exists():
            raise FileNotFoundError(f"Input not found: {p}")

        # IMPORT AGENTS (lazy to avoid import-time issues)
        from agents.data_parser import DataParserAgent
        from agents.question_generator import QuestionGeneratorAgent
        from agents.logic_engine import LogicBlockEngineAgent
        from agents.template_engine import TemplateEngineAgent

        raw = json.loads(p.read_text(encoding="utf-8"))
        print("[orchestrator] Loaded input:", input_path)

        # 1) parse
        parser = DataParserAgent()
        product_model = parser.run(raw)
        print("[orchestrator] Parsed product:", product_model.get("name", product_model.get("id")))

        # 2) questions
        qgen = QuestionGeneratorAgent()
        questions = qgen.run(product_model)
        print(f"[orchestrator] Generated {len(questions.get('questions', []))} questions")

        # 3) choose adapter then run logic blocks
        llm_adapter = self._choose_llm_adapter()
        logic = LogicBlockEngineAgent(llm_adapter=llm_adapter)
        blocks = logic.run(product_model, questions).get("blocks", {})
        print("[orchestrator] Logic blocks executed. Blocks:", list(blocks.keys()))

        # 4) templating
        templater = TemplateEngineAgent()
        pages = templater.run(product_model, blocks, questions)
        outdir = Path(outputs_dir)
        outdir.mkdir(parents=True, exist_ok=True)

        # Write with UTF-8 encoding and ensure_ascii=False to preserve characters like ₹
        def _write_json(obj, filename):
            path = outdir / filename
            content = json.dumps(obj, indent=2, ensure_ascii=False)
            path.write_text(content, encoding="utf-8")
            return str(path)

        product_path = _write_json(pages["product_page"], "product_page.json")
        faq_path = _write_json(pages["faq"], "faq.json")
        comparison_path = _write_json(pages["comparison"], "comparison_page.json")

        print("[orchestrator] Wrote outputs to:", outdir)
        return {
            "product_page": product_path,
            "faq": faq_path,
            "comparison_page": comparison_path
        }
