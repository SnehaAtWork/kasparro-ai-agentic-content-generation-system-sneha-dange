# agents/orchestrator.py
"""
OrchestratorAgent - orchestrates parser -> question generator -> logic blocks -> templater.
Writes JSON outputs using UTF-8 encoding to avoid encoding errors on Windows (e.g. ₹).
"""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from logging import getLogger

logger = getLogger(__name__)

# lazy import helper to avoid import-time side effects
def _lazy_import(name: str):
    module = __import__(name, fromlist=["dummy"])
    return module

class OrchestratorAgent:
    """
    OrchestratorAgent accepts an explicit `config` dict at construction time.
    DO NOT read or set environment variables inside this module to avoid global side effects.
    Expected config keys:
      - "ollama_base": str (optional)  e.g. "http://localhost:11434"
      - "use_ollama": str or bool (optional, default "1")
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    def _choose_llm_adapter(self) -> Optional[callable]:
        """
        Prefer local Ollama adapter if the config provides an ollama_base and use_ollama is enabled.
        Returns a callable(llm_items, product_model) or None.
        """
        # prefer config values (no os.environ mutation here)
        ollama_base = self.config.get("ollama_base")
        use_ollama_raw = self.config.get("use_ollama", "1")
        use_ollama = str(use_ollama_raw) == "1" or bool(use_ollama_raw) is True

        # try Ollama first if configured
        if use_ollama and ollama_base:
            try:
                # lazy import the adapter (adapter is responsible for using the base URL)
                from agents.ollama_adapter import paraphrase_faq_items as ollama_paraphrase  # type: ignore
                logger.info("[orchestrator] Using Ollama adapter for FAQ paraphrasing (base=%s).", ollama_base)
                # If your ollama_adapter needs the base URL, it should accept it via arguments or be constructed here.
                # For example: return functools.partial(ollama_paraphrase, base_url=ollama_base)
                return ollama_paraphrase
            except Exception as e:
                logger.info("[orchestrator] Ollama adapter not available: %s", e)

        # fallback to OpenAI adapter if available and key present in env (OpenAI key is inherently an env secret)
        try:
            from agents.llm_adapter import paraphrase_faq_items as openai_paraphrase  # type: ignore
            import os
            if os.getenv("OPENAI_API_KEY"):
                logger.info("[orchestrator] Using OpenAI adapter for FAQ paraphrasing.")
                return openai_paraphrase
        except Exception as e:
            logger.info("[orchestrator] OpenAI adapter not available: %s", e)

        # no adapter available
        logger.info("[orchestrator] No LLM paraphrase adapter will be used (deterministic fallback).")
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
        logger.info("[orchestrator] Loaded input: %s", input_path)

        # 1) parse
        parser = DataParserAgent()
        product_model = parser.run(raw)
        logger.info("[orchestrator] Parsed product: %s", product_model.get("name", product_model.get("id")))

        # 2) questions
        qgen = QuestionGeneratorAgent()
        questions = qgen.run(product_model)
        logger.info("[orchestrator] Generated %d questions", len(questions.get("questions", [])))

        # 3) choose adapter then run logic blocks
        llm_adapter = self._choose_llm_adapter()
        logic = LogicBlockEngineAgent(llm_adapter=llm_adapter)
        blocks = logic.run(product_model, questions).get("blocks", {})
        logger.info("[orchestrator] Logic blocks executed. Blocks: %s", list(blocks.keys()))

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

        logger.info("[orchestrator] Wrote outputs to: %s", outdir)
        return {
            "product_page": product_path,
            "faq": faq_path,
            "comparison_page": comparison_path
        }
