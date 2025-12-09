
# Problem Statement

Kasparro requires a robust, auditable automation pipeline that converts a small, structured product record into three machine-readable JSON artifacts: a product description page, a deterministic comparison page, and an FAQ page containing at least fifteen grounded questions and answers. The system must be designed and implemented as a multi-agent architecture that emphasises clarity of responsibility, reproducibility, and safety. Key constraints are:

* All generated content must be derived strictly from the provided product data; the system must not introduce facts, medical claims, or other external knowledge.
* Agents must be modular, stateless with respect to one another, and composable into a directed acyclic orchestration graph (DAG).
* The pipeline must produce deterministic outputs for identical inputs to support testing and verification.
* Optional natural-language polishing using a local LLM (Ollama) is acceptable only if the adapter enforces strict validation and deterministic fallback behavior.
* Outputs must be UTF-8 JSON files suitable for downstream consumption by UI or other automation.

This problem emphasizes software architecture, agent boundaries, validation and safety around optional LLM usage, and the ability to produce repeatable, testable outputs that would be acceptable in a production or hiring-review context.

# Solution Overview

The implemented solution is a deterministic, agent-driven pipeline that transforms a canonical `product_input.json` into three deliverables: `product_page.json`, `comparison_page.json`, and `faq.json`. The system is organized around a small set of focused agents and deterministic logic blocks. The core design decisions are:

1. **Clear agent responsibilities**

   * *DataParserAgent*: validates and normalizes raw input into a canonical `product_model`.
   * *QuestionGeneratorAgent*: deterministically synthesizes a set of categorized questions covering the product attributes.
   * *LogicBlockEngineAgent*: invokes independent, pure logic blocks (product, benefits, usage, ingredients, safety, purchase, compare) to produce structured intermediate outputs.
   * *TemplateEngineAgent*: composes final JSON pages using templates that map block outputs to schema fields.
   * *LLM Adapter (optional)*: performs conservative paraphrasing of FAQ answers only; its output is validated and rejected if it violates constraints.

2. **Directed acyclic orchestration (DAG)**

   * The OrchestratorAgent runs each stage in a fixed order: parse → question generation → logic engine → templater → write outputs.
   * No agent modifies another’s state; all data flows explicitly through return values and function parameters, preserving reproducibility and testability.

3. **Determinism and testability**

   * All logic blocks are deterministic pure functions for a fixed input; Product B generation in the compare block uses deterministic variation rules so CI and tests remain stable.
   * Unit tests cover parsing, FAQ construction, comparison scoring, and recommendation rules to ensure stable behavior and guardrails against regressions.

4. **LLM safety and validation**

   * The LLM adapter is strictly an editor: prompts include the compact product JSON and an explicit instruction not to add facts.
   * Paraphrases undergo conservative validation: blacklist checks for claim words, numeric and percentage preservation, and length heuristics. Invalid outputs are rejected in favor of deterministic rewrites.

5. **Template-driven outputs**

   * Final pages are template-driven, ensuring consistent schema and straightforward extensibility. Templates specify required fields and fallback behavior when data is missing.

6. **Operational considerations**

   * All output files are written using UTF-8 with `ensure_ascii=False` to preserve currency symbols and locale-sensitive characters.
   * The pipeline runs end-to-end without an LLM present; LLM behavior is opt-in and non-blocking.

The result is a production-oriented, auditable system that meets the assignment constraints and is suitable for a portfolio demonstration: it highlights architecture, safe LLM usage patterns, test-driven development, and clear, maintainable code structure.

# Scopes and Assumptions

## Scope of the System

This project implements a deterministic, multi-agent content generation system designed to transform a structured product JSON input into three output JSON artifacts: a product page, a comparison page, and an FAQ page. The system is constrained to operate strictly within the limits of the provided dataset and the deterministic logic defined in the agents and logic blocks.

### In-Scope Functionality

1. **Structured Input Parsing**
   The system parses and normalizes input product data, converting fields such as benefits, ingredients, skin type, and pricing into standardized formats suitable for downstream processing.

2. **Deterministic Question Generation**
   A set of 15+ FAQ questions is generated based solely on the product attributes. This includes categories such as informational, usage, safety, ingredients, storage, comparison, suitability, purchase, and effectiveness.

3. **Execution of Logic Blocks**
   The LogicBlockEngine executes independent, pure logic functions that derive structured features such as:

   * Product highlights
   * Benefit explanations
   * Usage steps
   * Safety notes
   * Ingredient summaries
   * Purchase descriptors
   * Deterministic comparison with a generated Product B (ingredient overlap, benefit overlap, pricing difference, pros/cons, and recommendation)

4. **Template-Based Output Rendering**
   Templates define field structure and assembly logic for the final JSON pages, ensuring output consistency and schema stability.

5. **Optional LLM Paraphrasing Layer**
   FAQ answers may be paraphrased via a local LLM (Ollama) under strict constraints. The system includes:

   * A safety-focused prompt
   * Validation to prevent added facts or claims
   * Deterministic fallback behavior when validation fails

6. **UTF-8 JSON Output Generation**
   The system writes `product_page.json`, `comparison_page.json`, and `faq.json` using UTF-8 encoding and `ensure_ascii=False` to preserve locale-sensitive characters (e.g., ₹).

7. **End-to-End Deterministic Execution**
   In the absence of an LLM or when LLM validation fails, the system maintains full functionality and determinism.

---

## Out of Scope

The system intentionally avoids or excludes the following:

1. **External Knowledge Integration**
   No ingredient roles, safety claims, or domain knowledge outside the provided product data may be introduced.

2. **Creative or Marketing-Focused Content Generation**
   The system does not produce persuasive, subjective, or marketing-driven descriptions.

3. **Web Rendering or UI Layer**
   HTML/CSS rendering, UI-based product pages, and front-end components are not part of the scope.

4. **Real Product Comparison or Data Retrieval**
   Product B is synthetic and deterministic. The system does not fetch real competitor data.

5. **Stochastic LLM Behavior as a Dependency**
   LLMs do not control the logic pipeline. Any LLM result must be validated and can be discarded.

6. **Multi-product Processing or Batch Pipelines**
   The system operates on one product input per run.

7. **SKUs, inventory data, or catalog management**
   Extendable, but not included in this challenge.

---

## Assumptions

1. **Input Data Follows the Provided Schema**
   The product input includes fields such as name, ingredients, benefits, skin type, usage, side effects, concentration, and price (or price equivalent). Any missing optional fields are handled gracefully.

2. **All Numeric and Percentage Values in Input Are Authoritative**
   The system preserves numbers exactly and prohibits modification during paraphrasing.

3. **No External Calls Beyond Optional LLM Endpoint**
   The system does not call any non-local API.

4. **LLM Presence Is Optional**
   The system must succeed even if the LLM is unavailable or responding incorrectly.

5. **The System Runner Provides Correct File Paths**
   The pipeline expects valid input paths and will raise `FileNotFoundError` otherwise.

6. **JSON Outputs Are Consumed by Upstream Systems**
   Output formatting remains stable to allow integration into larger automation pipelines.

---

This section defines what the system does and does not do. It establishes boundaries for evaluation, testing, and future extension while ensuring alignment with the constraints of the Kasparro Applied AI Engineer Challenge.

# System Design

This document describes the system-level design for the Multi-Agent Content Generation System developed for the Kasparro Applied AI Engineer Challenge. It covers architecture, agent responsibilities, data flow (DAG), logic block design, template schema, validation rules (especially for LLM integration), testing strategy, deployment considerations, and extension points. Diagrams and sequence charts are included to make the design actionable and review-ready.

---

# **1. Goals and Design Constraints**

## 1.1 Primary Goals

The system is architected to transform a structured product dataset into three deterministic JSON outputs:

* **Product Page JSON**
* **Comparison Page JSON**
* **FAQ JSON** containing 15+ grounded question–answer pairs

The solution emphasizes:

* **Determinism**: identical inputs must always produce identical outputs.
* **Agentic Modularity**: each agent performs a single responsibility with no hidden global state.
* **Safety and Grounding**: all generated content must come strictly from the provided product data—no added facts.
* **Extensibility**: logic blocks, templates, and agents can be extended without architectural changes.
* **Optional LLM Augmentation**: paraphrasing is allowed but strictly validated and isolated.

## 1.2 Key Design Constraints

* No external data sources or domain knowledge may be introduced.
* LLM use must remain optional; pipeline must run fully without it.
* Outputs must be stable, structured, and UTF‑8 encoded.
* The system must use a **DAG-style orchestration**, preventing cycles and side effects.
* Logic blocks must be **pure deterministic functions**.

## 1.3 Non‑Goals

These are intentionally excluded:

* Marketing copy generation or subjective descriptions
* Front‑end or rendering logic
* Fetching real competitor product data

---

# **2. High‑Level Architecture and DAG**

The system is organized as a **Directed Acyclic Graph (DAG)** executed by a single orchestrator component.

### 2.1 Architectural Overview

```
Raw Product JSON
       │
       ▼
DataParserAgent
       │ product_model
       ▼
QuestionGeneratorAgent
       │ questions
       ▼
LogicBlockEngineAgent
       │ blocks
       ▼
TemplateEngineAgent
       │
       ▼
Final Output JSON Pages
```

### 2.2 Rationale for DAG Architecture

* Ensures clear ordering and prevents backward dependencies.
* Enables deterministic reproducibility.
* Promotes testability—each node can be unit tested independently.
* Supports modular extension by inserting new blocks or agents.

### 2.3 Agent Boundary Rules

* No agent may modify another agent’s internal state.
* Inputs and outputs must be explicit, serializable dictionaries.
* No shared mutable global variables.

### 2.4 Execution Contract

The **OrchestratorAgent** supervises all steps:

* Loads input
* Passes data forward only
* Handles selection of optional LLM adapter
* Writes outputs atomically

---

# **3. Agents: Responsibilities, Inputs, Outputs**

Each agent performs exactly one domain responsibility.

---

## **3.1 DataParserAgent**

**Purpose:** Converts raw input into a validated, normalized `product_model`.

### Inputs

* Raw product JSON from file.

### Outputs

A canonical dictionary containing:

* `id`
* `name`
* `ingredients` (list)
* `benefits` (list)
* `usage`
* `usage_steps` (optional, later computed)
* `side_effects`
* `skin_type` (list)
* `concentration`
* `price_inr`
* `raw` (unchanged copy of original data)

### Key Design Notes

* Parsing must be strict yet fault‑tolerant.
* Normalization removes formatting inconsistencies.
* No additional knowledge may be inferred.

---

## **3.2 QuestionGeneratorAgent**

**Purpose:** Produce at least 15 deterministic questions covering all aspects of the product.

### Inputs

* `product_model`

### Outputs

* A list of objects: `{ "question": ..., "category": ... }`

### Categories

* Informational
* Usage
* Safety
* Benefits
* Ingredients
* Suitability
* Storage
* Purchase
* Effectiveness
* Comparison

### Design Notes

* Question generation is fully deterministic.
* No LLM is used to generate questions.
* Questions must be grounded in fields present in `product_model`.

---

## **3.3 LogicBlockEngineAgent**

**Purpose:** Execute a predefined sequence of pure logic blocks.

### Inputs

* `product_model`
* `questions`

### Outputs

* `blocks` dictionary, keyed by block name

### Characteristics

* Every block is a pure function.
* No external requests, no mutations, no randomness.
* All intermediate fields must be structured and predictable.

### Examples of Logic Blocks

* **product_block** – hero blurb, highlights
* **benefits_block** – benefit structure
* **usage_block** – split usage into ordered usage steps
* **ingredients_block** – ingredient lists and counts
* **safety_block** – safety and side‑effects
* **purchase_block** – pricing descriptors
* **compare_block** – deterministic synthetic Product B, scoring, recommendation

---

## **3.4 TemplateEngineAgent**

**Purpose:** Construct final structured JSON outputs using templates.

### Inputs

* `product_model`
* `blocks`
* `questions`

### Outputs

* `product_page.json`
* `comparison_page.json`
* `faq.json`

### Design Notes

* Templates map block output → final schema.
* Missing values must result in fallback text, not errors.
* Ensures uniform formatting across all outputs.

---

## **3.5 Optional LLM Adapter (Ollama)**

**Purpose:** Paraphrase generated FAQ answers **without adding information**.

### Inputs

* Draft FAQ answers
* Compact `product_model` context

### Outputs

* Validated paraphrases OR original deterministic answers

### Constraints

* Must not introduce new claims, benefits, or numerical values.
* Must not alter price or concentration.
* Must not add ingredient roles.
* Validation ensures grounding.

LLM use is **non‑critical**; the system remains fully deterministic if disabled.

---

# **4. Logic Block Design and Examples**

Logic blocks implement the domain logic. They operate independently and deterministically.

---

## **4.1 product_block**

Constructs top‑level product information.

### Responsibilities

* Derive product title
* Compose hero blurb summarizing benefits
* Create 2–5 highlight bullet points
* Produce price statements

### Example Output

```json
{
  "title": "GlowBoost Vitamin C Serum",
  "hero_blurb": "GlowBoost Vitamin C Serum — Brightening and dark‑spot reduction.",
  "price_statement": "Priced at ₹699.",
  "highlights": ["Brightening", "Fades dark spots"]
}
```

---

## **4.2 benefits_block**

Transforms benefit list into structured objects.

### Example Output

```json
{
  "benefits": [
    {"title": "Brightening", "explanation": "Brightening"},
    {"title": "Fades dark spots", "explanation": "Fades dark spots"}
  ]
}
```

---

## **4.3 usage_block**

Splits usage into steps.

### Algorithm

* Split on punctuation: `.`, `;`
* Normalize whitespace
* Exclude empty tokens

### Example Output

```json
{
  "usage": "Apply 2–3 drops in the morning before sunscreen",
  "usage_steps": ["Apply 2–3 drops in the morning", "Apply sunscreen afterwards"]
}
```

---

## **4.4 ingredients_block**

Provides normalized ingredient list and count.

### Example Output

```json
{
  "ingredients": ["Vitamin C", "Hyaluronic Acid"],
  "ingredients_count": 2
}
```

---

## **4.5 safety_block**

Extracts and reformats safety data.

### Example Output

```json
{
  "safety": "Mild tingling for sensitive skin"
}
```

---

## **4.6 purchase_block**

Formats purchase‑related fields.

### Example Output

```json
{
  "price_inr": 699,
  "price_statement": "Priced at ₹699."
}
```

---

## **4.7 compare_block**

One of the most complex blocks.

### Responsibilities

* Construct a **deterministic synthetic Product B** using rule‑driven variations.
* Compute shared and unique features.
* Compute overlap score.
* Compute absolute and percent price difference.
* Generate pros/cons lists.
* Generate recommendation rules:

  * Prefer A if products are very similar and A is cheaper.
  * Prefer B if B offers substantially more features at a modest price difference.
  * Otherwise generate a contextual recommendation.

---

# **5. Template Engine and Output Schemas**

Templates define how logic blocks populate final JSON structures.

---

## **5.1 Product Page Template**

Fields include:

* `id`, `title`, `hero_blurb`
* `highlights`
* `ingredients`, `ingredients_count`
* `benefits`
* `usage`, `usage_steps`
* `safety`
* `metadata` (concentration, skin type, etc.)

---

## **5.2 Comparison Page Template**

Contains:

* Full representation of Product A
* Generated Product B
* Computed comparison fields:

  * shared ingredients
  * unique ingredients
  * shared benefits
  * price delta
  * scores
  * pros and cons
  * recommendation summary

---

## **5.3 FAQ Template**

Includes for each item:

* `question`
* `category`
* `answer` (optionally paraphrased)
* timestamp metadata

Templates enforce:

* Stable structure
* No fields omitted
* No hallucinated values added

# **6. LLM Adapter: Prompt Design and Validation**

The LLM Adapter (Ollama-based) is *optional* and serves as a controlled paraphrasing layer for FAQ answers. It must not introduce external knowledge, modify numeric values, or produce content inconsistent with the product data.

---

## **6.1 Design Principles**

1. **LLM as Editor, Not Generator**
   The adapter rewrites *only* the DRAFT answer created by deterministic logic blocks. It is not allowed to generate new content from scratch.

2. **Grounding**
   The prompt includes a compact version of `product_model`, so the LLM understands what information it *may* reference.

3. **Strict Constraints**
   The prompt instructs the model to:

   * Not add new facts.
   * Not create new ingredient roles or descriptions.
   * Preserve all numbers, especially price and concentration.
   * Return only a short, human-readable reformulation.

4. **Validation of LLM Output**

After the LLM returns a paraphrase, the adapter runs a deterministic validation:

| Rule                     | Example Behavior                                                |
| ------------------------ | --------------------------------------------------------------- |
| Blacklisted words        | Rejects paraphrase containing “clinical”, “dermatologist”, etc. |
| Numeric preservation     | Ensures ₹699 or “10%” remain unchanged                          |
| No new percentages       | Rejects output containing “5%” if not in input                  |
| Length constraints       | Rejects paraphrases 4× longer than DRAFT                        |
| No hallucinated entities | Rejects mentions of new chemicals or benefits                   |

If validation fails → revert to deterministic fallback.

---

## **6.2 Prompt Architecture**

```
You are an e-commerce FAQ assistant. Rewrite the DRAFT ANSWER into a clear, human-friendly answer.
STRICT RULES:
1. Use ONLY PRODUCT_DATA and DRAFT.
2. Do NOT add facts, claims, new ingredients, new numbers, or assumptions.
3. Keep answers short (1–3 sentences).
4. If information is missing, reply exactly: "Not specified in the product data."

PRODUCT_DATA:
{product_json}
QUESTION:
{question_text}
DRAFT ANSWER:
{draft}
REWRITTEN ANSWER:
```

This structure ensures transparency, safety, and deterministic fallback behavior.

---

# **7. Data Flow — Sequence Diagrams & Flowcharts**

Below are enriched diagrams describing the internal architecture.

---

## **7.1 Full Pipeline Sequence Diagram**

```
User
 │
 │  run_pipeline.py
 ▼
OrchestratorAgent
 │
 │───▶ DataParserAgent
 │       parse(raw_json)
 │       return product_model
 │
 │───▶ QuestionGeneratorAgent
 │       generate(product_model)
 │       return questions
 │
 │───▶ LogicBlockEngineAgent
 │       run(product_model, questions)
 │       execute blocks in order
 │       return blocks
 │
 │───▶ TemplateEngineAgent
 │       render(product_model, blocks, questions)
 │       ├─ build product_page
 │       ├─ build comparison_page
 │       └─ build faq
 │
 │───▶ (Optional) LLM Adapter
 │       paraphrase(draft_answers)
 │       validate → accept or fallback
 │       return finalized FAQ
 │
 ▼
Outputs written to /outputs/
```

---

## **7.2 Logic Block Engine Internal Flow**

```
                 LogicBlockEngineAgent
                          │
  ┌────────────────────────┼────────────────────────┐
  ▼                        ▼                        ▼
product_block      benefits_block            usage_block
  │                        │                        │
  ▼                        ▼                        ▼
ingredients_block   safety_block            purchase_block
                          │
                          ▼
                    compare_block
                          │
                          ▼
                blocks = { key: output_dict }
```

Blocks do not depend on one another unless semantically required. For example, `compare_block` requires the parsed product model but not the previous blocks.

---

## **7.3 FAQ Generation & Paraphrasing Flow**

```
QuestionGeneratorAgent
        │
        ▼
 Draft FAQ Items
        │
        ▼
 LogicBlockEngine (faq_answer_block)
        │
        ▼
 Optional LLM Adapter (paraphrase_faq_items)
        │        │
        │        ├── valid paraphrase → accept
        │        └── invalid paraphrase → deterministic fallback
        ▼
 Final FAQ Items
```

---

# **8. Testing Strategy and CI Considerations**

Testing is critical because the system must be deterministic, explainable, and safe. The testing strategy covers units, integration, and validation against hallucination.

---

## **8.1 Unit Tests**

### DataParserAgent Tests

* Validate handling of comma-separated strings.
* Validate price parsing behavior.
* Validate normalization of missing or malformed fields.

### QuestionGeneratorAgent Tests

* Ensure 15+ questions are produced.
* Ensure categories are covered consistently.

### Logic Blocks Tests

Examples:

* `usage_block` splits usage correctly.
* `benefits_block` produces structured objects.
* `compare_block` produces correct score when two products are identical.
* Recommendation rules behave as expected.

### LLM Adapter Tests

* Use mocking (or `mock_ollama_adapter.py`) to simulate paraphrasing.
* Ensure validation correctly rejects invalid outputs.
* Ensure fallback behavior is triggered.

---

## **8.2 Integration Tests**

Integration tests run the entire pipeline:

```
python run_pipeline.py inputs/sample.json
```

And verify that:

* All three output files are created.
* Outputs match expected canonical output for known input.
* No nondeterministic behavior appears.

---

## **8.3 Continuous Integration Considerations**

* LLM functionality should be **off** in CI to avoid nondeterminism.
* Use a mock adapter for paraphrasing during CI.
* Validate schema using JSON schema tests.
* All tests must run in <1s for responsiveness.

---

# **9. Security, Privacy, and Safety Considerations**

Even though the system operates on non-sensitive product data, security and safety principles were applied.

---

## **9.1 Data Security**

* No external network calls except optional LLM endpoint.
* Local LLM endpoint (Ollama) avoids cloud exposure.
* Inputs/outputs remain within local filesystem.

---

## **9.2 Privacy**

* System assumes no PII exists in input.
* If PII were accidentally provided, system does not transmit it externally.

---

## **9.3 Safety Constraints Against Hallucination**

The LLM adapter includes:

* Strict prompt constraints
* Hard validation rules
* Blacklisted medical/clinical claim terminology
* Numeric consistency checks

This guarantees the system never outputs unsafe, misleading, or fabricated facts.

---

# **10. Performance and Operational Considerations**

## **10.1 Performance Characteristics**

* Deterministic logic is lightweight.
* Typical runtime is <1 second without LLM.
* With LLM paraphrasing, runtime depends on model size (Llama3 8B yields ~1–3 seconds per FAQ set).

---

## **10.2 Resource Usage**

* <100MB RAM for deterministic path.
* Additional RAM depending on local LLM configuration.

---

## **10.3 Deployment Considerations**

* Works in any Python 3.10+ environment.
* Ideal for local, containerized, or CI execution.
* Does not require GPUs unless LLM acceleration is desired.

---

## **10.4 Reliability & Resilience**

* LLM failures are gracefully handled.
* Missing fields in product data result in controlled fallback text.
* Logic blocks are independently testable.

---

# **11. Extensibility and Integration Points**

The system is intentionally designed to be modular, allowing new features, behaviors, or agents to be added without rewriting existing components. Extensibility is achieved through clear boundaries, template-driven composition, deterministic logic functions, and optional adapters.

---

## **11.1 Extending Logic Blocks**

Logic blocks are housed in their own module directory (e.g., `logic_blocks/`). Adding a new block involves:

1. Creating a new Python file, e.g., `promotion_block.py`.
2. Implementing a pure function such as:

   ```python
   def run(product_model, questions=None):
       return { "promotion_message": ... }
   ```
3. Registering the block inside `LogicBlockEngineAgent` in the execution order.

### Example: Adding a Sustainability Block

```python
{
  "sustainability": {
      "certifications": [...],
      "packaging_recyclable": true
  }
}
```

### Best Practices

* Keep logic blocks deterministic.
* Avoid referencing external APIs.
* Validate input fields before computing outputs.

---

## **11.2 Extending Templates**

Templates can be extended by adding new JSON fields and mapping them to existing or new block outputs.

For example, extending the product page template:

```json
{
  "environmental_impact": "${sustainability_block.impact_score}"
}
```

A template extension does **not** require changes to upstream logic blocks unless new data is required.

---

## **11.3 Adding New Output Pages**

To add a new page type (e.g., merchant-summary page):

1. Create a new template file in `templates/`.
2. Add rendering logic in `TemplateEngineAgent`.
3. Optionally add a new logic block for data shaping.

---

## **11.4 Integrating Additional LLMs**

The LLM adapter is architected as replaceable. To integrate a different model:

* Create a new adapter module (e.g., `adapters/deepseek_adapter.py`).
* Implement a function following the contract:

  ```python
  def paraphrase_faq_items(faq_items, product_model):
      return faq_items
  ```
* Modify Orchestrator to choose the correct adapter based on environment variables.

### Integration Principles

* Never use the LLM to *generate* new content; restrict usage to paraphrasing.
* Apply the same validation rules (numeric preservation, no new claims, blacklist terms).

---

## **11.5 Plug-in Architecture Opportunities**

The system can evolve into a plug‑in architecture where:

* Agents register themselves through decorators.
* Logic blocks auto-discover via directory scanning.
* Templates load dynamically based on output type.

This pattern enables new teams to add features without modifying core pipeline code.

---

## **11.6 Batch Processing and Multi-Product Pipelines**

To process multiple product inputs:

* Create a batch orchestrator that iterates through a folder of JSON files.
* Enable parallel runs with independent subprocesses while preserving determinism.

---

# **12. Appendix: Example Data Shapes and Sample Flows**

This section provides canonical examples of each major data structure in the system, along with a full execution walkthrough.

---

## **12.1 Example Raw Input JSON**

```json
{
  "product_name": "GlowBoost Vitamin C Serum",
  "concentration": "10% Vitamin C",
  "skin_type": "Oily, Combination",
  "key_ingredients": "Vitamin C, Hyaluronic Acid",
  "benefits": "Brightening, Fades dark spots",
  "how_to_use": "Apply 2–3 drops in the morning before sunscreen",
  "side_effects": "Mild tingling for sensitive skin",
  "price": "₹699"
}
```

---

## **12.2 Parsed Product Model (After DataParserAgent)**

```json
{
  "id": "product_001",
  "name": "GlowBoost Vitamin C Serum",
  "concentration": "10% Vitamin C",
  "skin_type": ["Oily", "Combination"],
  "ingredients": ["Vitamin C", "Hyaluronic Acid"],
  "benefits": ["Brightening", "Fades dark spots"],
  "usage": "Apply 2–3 drops in the morning before sunscreen",
  "side_effects": "Mild tingling for sensitive skin",
  "price_inr": 699,
  "raw": { ... }
}
```

---

## **12.3 Generated Questions Example**

```json
[
  {"question": "What is GlowBoost Vitamin C Serum and who is it for?", "category": "Informational"},
  {"question": "How do I use GlowBoost Vitamin C Serum?", "category": "Usage"},
  {"question": "Are there any side effects?", "category": "Safety"},
  ... (15+ total)
]
```

---

## **12.4 Logic Block Outputs (Example)**

### benefits_block

```json
{
  "benefits": [
    {"title": "Brightening", "explanation": "Brightening"},
    {"title": "Fades dark spots", "explanation": "Fades dark spots"}
  ]
}
```

### usage_block

```json
{
  "usage": "Apply 2–3 drops in the morning before sunscreen",
  "usage_steps": ["Apply 2–3 drops in the morning", "Follow with sunscreen"]
}
```

### compare_block (Example Summary)

```json
{
  "shared_ingredients": ["Vitamin C"],
  "unique_to_a": ["Hyaluronic Acid"],
  "unique_to_b": ["Glycerin"],
  "price_difference": {"absolute": 175, "percent": 25.04},
  "score": {"overall": 0.33},
  "recommendation": {"decision": "Consider Product A"}
}
```

---

## **12.5 Final Output Example (FAQ Snippet)**

```json
{
  "product_id": "product_001",
  "items": [
    {
      "question": "How do I use GlowBoost Vitamin C Serum?",
      "category": "Usage",
      "answer": "Apply 2–3 drops in the morning, then follow with sunscreen."
    }
  ],
  "last_updated": "2025-12-09T05:26:01Z",
  "source": "generated_faq"
}
```

---

## **12.6 Complete Execution Flow (Illustrated)**

Below is a Mermaid flowchart representing the complete execution flow of the Multi‑Agent Content Generation System.

```mermaid
flowchart TD
  %% Orchestrator & input
  A[Start: inputs/product_input.json] --> Orchestrator[OrchestratorAgent]
  Orchestrator --> DP[DataParserAgent - (parse -> product_model)]
  DP --> QG[QuestionGeneratorAgent - (generate -> questions)]
  QG --> LBE[LogicBlockEngineAgent - (run blocks)]

  %% Logic blocks as subgraph
  subgraph LOGIC_BLOCKS [Logic Blocks (deterministic, pure)]
    direction TB
    PB[product_block]
    BB[benefits_block]
    UB[usage_block]
    IB[ingredients_block]
    SB[safety_block]
    PurchB[purchase_block]
    CB[compare_block - (generate Product B, scoring)]
  end

  LBE --> PB
  LBE --> BB
  LBE --> UB
  LBE --> IB
  LBE --> SB
  LBE --> PurchB
  LBE --> CB
  PB --> LBE
  BB --> LBE
  UB --> LBE
  IB --> LBE
  SB --> LBE
  PurchB --> LBE
  CB --> LBE

  %% Templating and FAQ path
  LBE --> TE[TemplateEngineAgent - (render templates)]
  TE --> ProdPage[product_page.json]
  TE --> CompPage[comparison_page.json]
  TE --> FAQDraft[faq (draft answers)]

  %% Optional LLM paraphrasing & validation
  FAQDraft --> LLM[Optional LLM Adapter - (paraphrase_faq_items)]
  LLM --> V{Validate paraphrase}
  V -- Pass --> FAQFinal[Accept paraphrases]
  V -- Fail --> Fallback[Deterministic fallback - (use original drafts)]
  Fallback --> FAQFinal
  FAQFinal --> FAQOut[outputs/faq.json]

  %% Final write step (atomic)
  ProdPage --> Write[Write outputs to outputs/ (UTF-8, ensure_ascii=False)]
  CompPage --> Write
  FAQOut --> Write
  Write --> End[End]

  %% Notes
  classDef optional fill:#f9f,stroke:#333,stroke-width:1px;
  class LLM optional;
```





