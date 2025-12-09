"""
OrchestratorAgent stub - simple synchronous DAG runner for the assignment.
"""
import json
import os
from pathlib import Path

from agents.llm_adapter import paraphrase_faq_items, OPENAI_AVAILABLE
from .data_parser import DataParserAgent
from .question_generator import QuestionGeneratorAgent
from .logic_engine import LogicBlockEngineAgent
from .template_engine import TemplateEngineAgent

class OrchestratorAgent:
    def __init__(self, config: dict = None):
        self.config = config or {}

    def run(self, input_path: str, outputs_dir: str = "outputs"):
        p = Path(input_path)
        raw = json.loads(p.read_text())
        parser = DataParserAgent()
        product_model = parser.run(raw)

        qgen = QuestionGeneratorAgent()
        questions = qgen.run(product_model)

        llm_adapter = None
        # prefer Ollama if configured or running locally
        use_ollama = os.getenv("USE_OLLAMA", "1")  # default to 1 if you intend to use local Ollama
        if use_ollama and os.getenv("OLLAMA_BASE", None) is None:
            # keep default base but ensure server is reachable
            os.environ.setdefault("OLLAMA_BASE", "http://localhost:11434")

        if os.getenv("OLLAMA_BASE"):
            try:
                from agents.ollama_adapter import paraphrase_faq_items as ollama_paraphrase
                # Quick health check (optional): try a small GET; if fails, adapter will still attempt calls and fallback
                llm_adapter = ollama_paraphrase
                print("[orchestrator] Using Ollama adapter for FAQ paraphrasing.")
            except Exception as e:
                print("[orchestrator] Ollama adapter import failed:", e)
                llm_adapter = None

        # If Ollama not present, you can still fall back to OpenAI adapter if desired (previous logic)
        if not llm_adapter:
            # existing OpenAI adapter wiring (if you kept agents/llm_adapter.py)
            try:
                from agents.llm_adapter import paraphrase_faq_items as openai_paraphrase
                if os.getenv("OPENAI_API_KEY"):
                    llm_adapter = openai_paraphrase
                    print("[orchestrator] Using OpenAI adapter for FAQ paraphrasing.")
            except Exception:
                llm_adapter = None

        logic = LogicBlockEngineAgent(llm_adapter=llm_adapter)
        blocks = logic.run(product_model, questions).get("blocks", {})

        templater = TemplateEngineAgent()
        pages = templater.run(product_model, blocks, questions)

        outdir = Path(outputs_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "product_page.json").write_text(json.dumps(pages["product_page"], indent=2, ensure_ascii=False))
        (outdir / "faq.json").write_text(json.dumps(pages["faq"], indent=2, ensure_ascii=False))
        (outdir / "comparison_page.json").write_text(json.dumps(pages["comparison"], indent=2, ensure_ascii=False))

        return {"product_page": str(outdir / "product_page.json")}