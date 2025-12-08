"""
OrchestratorAgent stub - simple synchronous DAG runner for the assignment.
"""
import json
from pathlib import Path

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

        logic = LogicBlockEngineAgent()
        blocks = logic.run(product_model, questions).get("blocks", {})

        templater = TemplateEngineAgent()
        pages = templater.run(product_model, blocks, questions)

        outdir = Path(outputs_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "product_page.json").write_text(json.dumps(pages["product_page"], indent=2, ensure_ascii=False))
        (outdir / "faq.json").write_text(json.dumps(pages["faq"], indent=2, ensure_ascii=False))
        (outdir / "comparison_page.json").write_text(json.dumps(pages["comparison"], indent=2, ensure_ascii=False))

        return {"product_page": str(outdir / "product_page.json")}