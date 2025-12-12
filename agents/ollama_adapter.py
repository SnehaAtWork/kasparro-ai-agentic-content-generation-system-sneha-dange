# agents/ollama_adapter.py
"""
SAFE OLLAMA PARAPHRASER
-----------------------

This adapter performs STRICT, hallucination-safe paraphrasing:

- LLM is allowed to change ONLY phrasing, nothing else.
- No new facts, benefits, claims, warnings, ingredients, or usage details.
- If factual drift is detected, original answer is kept.
- Includes detailed logs to help trace behavior.
"""

import requests
import logging
from typing import List, Dict
from config import OLLAMA_BASE, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# ---------------- SAFE PARAPHRASING PROMPT -----------------

PARAPHRASE_PROMPT = """
You must rewrite the following answer ONLY to improve clarity and readability.

CRITICAL RULES (DO NOT BREAK THESE):
- Do NOT add any new facts.
- Do NOT remove any facts.
- Do NOT exaggerate, soften, or reinterpret meaning.
- Do NOT add marketing language or persuasive tone.
- Do NOT add safety claims not present in the text.
- Do NOT omit warnings / side effects.
- Do NOT add commentary like "rewritten answer:".
- Preserve ALL factual content exactly as stated.
- You are allowed ONLY to rephrase sentences in a neutral, factual tone.

Rewrite this answer factually, clearly, and concisely:

"{text}"

Return ONLY the rewritten answer. No explanations, no prefixes, no quotes.
"""

# ------------------ FACTUAL INTEGRITY CHECK ------------------

def _facts_present(original: str, rewritten: str, required_tokens: List[str]) -> bool:
    """
    Ensures all critical factual tokens (ingredients, warnings, numeric instructions)
    remain present in rewritten text.
    """
    rewritten_lower = rewritten.lower()
    for token in required_tokens:
        if token and token.lower() not in rewritten_lower:
            return False
    return True


def _extract_required_tokens(answer: str, product: Dict) -> List[str]:
    """
    Extract tokens that MUST appear in rewritten version.
    This prevents hallucinations or omissions.
    """
    tokens = []

    # Basic product attributes
    if "usage" in product and isinstance(product["usage"], str):
        # Split usage into meaningful words/tokens (no small stopwords)
        tokens.extend([w for w in product["usage"].split() if len(w) > 3])

    if "benefits" in product and isinstance(product["benefits"], list):
        tokens.extend(product["benefits"])

    if "ingredients" in product and isinstance(product["ingredients"], list):
        tokens.extend(product["ingredients"])

    if "side_effects" in product and isinstance(product["side_effects"], str):
        tokens.extend([product["side_effects"]])

    # Basic tokens from original answer
    for w in answer.split():
        if len(w) > 4:  # only meaningful words
            tokens.append(w)

    # Deduplicate
    return list({t.lower(): t for t in tokens}.values())


# ------------------ OLLAMA PARAPHRASING ------------------

def paraphrase_faq_items(faq_items: List[Dict], product_model: Dict) -> List[Dict]:
    """Safely paraphrase FAQ items using Ollama, with fallback on factual drift."""

    improved_items = []

    for idx, item in enumerate(faq_items):

        original = item.get("answer", "").strip()
        logger.info(f"[ollama_adapter] Paraphrasing FAQ item {idx+1}/{len(faq_items)}")

        # If empty answer, skip
        if not original:
            improved_items.append(item)
            continue

        # Extract required factual tokens for safety check
        required_tokens = _extract_required_tokens(original, product_model)

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": PARAPHRASE_PROMPT.format(text=original),
            "stream": False,
        }

        try:
            logger.debug(f"[ollama_adapter] Sending request to {OLLAMA_BASE}/api/generate")
            r = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=60)
            r.raise_for_status()

            response = r.json()
            rewritten = response.get("response", "").strip()

            if not rewritten:
                logger.warning("[ollama_adapter] Empty rewrite received. Keeping original.")
                improved_items.append(item)
                continue

            # ------------ Factual Drift Check -------------
            if not _facts_present(original, rewritten, required_tokens):
                logger.error(
                    "[ollama_adapter] FACTUAL DRIFT DETECTED. "
                    f"Original='{original[:60]}...' | Rewritten='{rewritten[:60]}...'"
                )
                improved_items.append(item)
                continue

            # ------------ Accept Safe Rewrite -------------
            logger.info(
                f"[ollama_adapter] Safe paraphrase succeeded for item {idx+1}. "
                f"Original='{original[:40]}…' → New='{rewritten[:40]}…'"
            )

            improved_items.append({**item, "answer": rewritten})

        except Exception as e:
            logger.error(f"[ollama_adapter] Paraphrasing failed for item {idx+1}: {e}")
            improved_items.append(item)

    return improved_items
