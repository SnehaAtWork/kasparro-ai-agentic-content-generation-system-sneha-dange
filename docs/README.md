# Multi‑Agent Content Generation System

## Branches
- `main` — original submission
- `langchain-rewrite` — LangChain migration (work in progress)

This project implements a deterministic, testable, multi‑agent pipeline that converts a raw e‑commerce product JSON into three structured outputs:

* `product_page.json`
* `comparison_page.json`
* `faq.json`

The system is designed according to the requirements of the **Applied AI Engineer Challenge**, with strict constraints:

* No model hallucinations
* No domain knowledge or external assumptions
* Pure, deterministic logic blocks
* No hidden global state
* Optional LLM use only for paraphrasing, never for generating facts

---

## 1. Project Structure

```
├── agents/
│   ├── data_parser.py
│   ├── question_generator.py
│   ├── logic_engine.py
│   ├── orchestrator.py
│   ├── template_engine.py
│   ├── ollama_adapter.py (optional LLM paraphrasing)
├── logic_blocks/
├── templates/
├── tests/
├── inputs/product_input.json
├── outputs/
├── run_pipeline.py
└── README.md
```

---

## 2. Pipeline Overview

1. **DataParserAgent** – Normalises raw product JSON into a typed product model.
2. **QuestionGeneratorAgent** – Generates structured FAQ questions based on available fields.
3. **LogicBlockEngineAgent** – Executes deterministic logic blocks:

   * product, benefits, usage, safety, ingredients
   * synthetic product B generation
   * deep comparison, scoring, recommendation
4. **TemplateEngineAgent** – Renders structured JSON outputs.
5. **Optional LLM Adapter** – Paraphrases FAQ answers without adding facts.
6. Outputs written atomically to `outputs/`.

---

## 3. Running the Pipeline

Activate your environment, then run:

```bash
python run_pipeline.py --input inputs/product_input.json
```

Outputs are created in `./outputs/`.

---

## 4. Design Principles

* **Deterministic by default** – all core transformations are rule‑based.
* **Clear agent boundaries** – each agent performs exactly one responsibility.
* **No side effects** – no API calls inside logic blocks.
* **Replaceable adapters** – paraphrasing can be toggled via environment variables.
* **Strict validation** – paraphraser outputs are validated to prevent hallucinations.

---

## 5. Extensibility

* Add new logic blocks by extending `logic_blocks/` and registering them.
* Add new templates by modifying `templates/` and updating `TemplateEngineAgent`.
* Swap LLM providers by implementing the same paraphrase adapter contract.

---

## 6. Testing

Run all tests:

```bash
pytest -q
```

Tests cover parsing, FAQ generation, comparison logic, and recommendation rules.

---

## 7. Outputs

Each output is guaranteed to be:

* JSON‑serializable
* UTF‑8 encoded
* Deterministic (except optional paraphrasing)

---

## 8. License

This repository is for evaluation and demonstration purposes.

---

For full architecture, execution flow diagrams, and system design documents, refer to the project documentation files in this repository.
