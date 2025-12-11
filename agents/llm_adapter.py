# agents/llm_adapter.py
"""
LLM adapter for paraphrasing FAQ answers.

This module is compatible with both older (pre-1.0) openai python clients and newer (>=1.0).
- If openai (old) exposes ChatCompletion, uses openai.ChatCompletion.create(...)
- Otherwise, tries the new SDK usage via from openai import OpenAI; client = OpenAI(); client.chat.completions.create(...)

Adapter rules:
- Only paraphrases the 'answer' field (no new facts).
- Performs lightweight validation to avoid introducing blacklisted terms or conflicting numeric claims.
- If any failure occurs, returns original items unmodified.
"""

import os
import json
import re
from typing import List, Dict
from logging import getLogger

logger = getLogger(__name__)

OPENAI_AVAILABLE = False
try:
    import openai  # type: ignore
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# Basic blacklist to reduce hallucination risk
BLACKLIST_PATTERNS = [
    r"\bclinical\b", r"\bstudy\b", r"\bproven\b", r"\bFDA\b", r"\bdermatologist\b",
    r"\bguarantee\b", r"\bguaranteed\b"
]

def _contains_blacklisted(text: str) -> bool:
    t = text.lower()
    for pat in BLACKLIST_PATTERNS:
        if re.search(pat, t):
            return True
    return False

def _validate_paraphrase(original: str, paraphrase: str, product_fields: Dict) -> bool:
    """
    Basic validation:
    1) Paraphrase must not contain blacklisted words.
    2) Paraphrase must not assert contradictory numeric claims (price / % concentration).
    3) If paraphrase contains a number and the original didn't, be conservative and reject.
    This is intentionally conservative — on doubt, return False.
    """
    if not paraphrase or not isinstance(paraphrase, str):
        return False

    if _contains_blacklisted(paraphrase):
        return False

    # Price checks
    orig_price = product_fields.get("price_inr")
    if orig_price:
        # if paraphrase mentions any numeric price, ensure it includes the original price
        parap_nums = re.findall(r"\d{2,}", paraphrase.replace(",", ""))
        if parap_nums:
            if str(orig_price) not in paraphrase:
                return False

    # concentration checks (percent)
    concentration = str(product_fields.get("concentration") or "")
    orig_pct = re.search(r"(\d+%)", concentration)
    p_pct = re.search(r"(\d+%)", paraphrase)
    if p_pct and orig_pct:
        if p_pct.group(1) != orig_pct.group(1):
            return False
    if p_pct and not orig_pct:
        # paraphrase introduced a percent while original product had none -> suspect
        return False

    # Basic sanity: paraphrase should not be drastically longer than original (heuristic)
    if len(paraphrase) > max(400, len(original) * 3):
        return False

    return True

def _call_openai_old(messages: List[Dict], model: str, max_tokens: int):
    """
    Calls older openai.ChatCompletion.create API (pre-1.0)
    """
    resp = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return resp["choices"][0]["message"]["content"]

def _call_openai_new(messages: List[Dict], model: str, max_tokens: int):
    """
    Calls the new OpenAI client (>=1.0).
    Uses: from openai import OpenAI; client = OpenAI(); client.chat.completions.create(...)
    """
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError(f"new OpenAI client not available: {e}")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.2,
    )
    # resp may be a dict-like; extract assistant message content
    # new SDK returns choices[0].message.content (string)
    try:
        return resp["choices"][0]["message"]["content"]
    except Exception:
        # last-resort: try attribute access
        try:
            return resp.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"unexpected response shape from OpenAI client: {e}")

def _call_openai(messages: List[Dict], model: str, max_tokens: int):
    """
    Wrapper that tries old API first, then new API.
    """
    # prefer using the new client if available
    # detect old API presence:
    try:
        if hasattr(openai, "ChatCompletion"):
            # older API style
            return _call_openai_old(messages, model, max_tokens)
    except Exception:
        pass

    # try new API client
    return _call_openai_new(messages, model, max_tokens)

def paraphrase_faq_items(faq_items: List[Dict], product_fields: Dict, max_tokens: int = 512) -> List[Dict]:
    """
    Paraphrase the answer field for each FAQ item.

    Input faq_items: list of {question, category, answer}
    Returns: paraphrased items with same keys; on failure, returns original faq_items
    """
    if not OPENAI_AVAILABLE or not os.getenv("OPENAI_API_KEY"):
        # no adapter available — return original
        return faq_items

    # build payload for the model (we'll ask a single paraphrase call)
    payload_list = []
    for it in faq_items:
        payload_list.append({
            "question": it.get("question"),
            "category": it.get("category", ""),
            "answer": it.get("answer", "")
        })

    system_msg = (
        "You are a careful paraphraser. Rephrase the provided answers for clarity and tone "
        "without adding any new factual claims, numeric values, references to studies, or guarantees. "
        "If you cannot paraphrase without adding new facts, return the original answer."
    )
    user_msg = (
        "Input (JSON):\n" + json.dumps(payload_list, ensure_ascii=False) + "\n\n"
        "Return a JSON array of objects with keys: question, category, answer_paraphrase. "
        "Example: [{\"question\":\"...\",\"category\":\"...\",\"answer_paraphrase\":\"...\"}, ...]. "
        "Do not include any surrounding explanation."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        raw_text = _call_openai(messages, model=model, max_tokens=max_tokens)
    except Exception as e:
        logger.info("[llm_adapter] paraphrase failed (API):", str(e))
        return faq_items

    # parse JSON from model output (robust)
    parsed = None
    try:
        parsed = json.loads(raw_text)
    except Exception:
        m = re.search(r"(\[.*\])", raw_text, flags=re.S)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except Exception:
                parsed = None

    if not parsed or not isinstance(parsed, list) or len(parsed) != len(faq_items):
        # Model didn't return expected JSON; don't change items
        logger.info("[llm_adapter] paraphrase: unexpected response shape; returning original items.")
        return faq_items

    result = []
    for orig, p in zip(faq_items, parsed):
        para = p.get("answer_paraphrase") or p.get("answer") or orig.get("answer", "")
        # conservative validation
        if _validate_paraphrase(orig.get("answer",""), para, product_fields):
            new_item = orig.copy()
            new_item["answer"] = para
            result.append(new_item)
        else:
            # fallback to original answer
            result.append(orig)

    return result
