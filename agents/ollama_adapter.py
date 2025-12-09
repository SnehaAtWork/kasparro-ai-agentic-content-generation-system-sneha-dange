# agents/ollama_adapter.py
"""
Ollama adapter for local paraphrasing (llama3:8b or similar).
Function: paraphrase_faq_items(faq_items, product_fields) -> List[Dict]
This adapter calls a local Ollama server (default http://localhost:11434).
It is conservative: it only rewrites the 'answer' text and validates paraphrases.
On any failure or validation problem it returns the original items.
"""

import os
import json
import re
import requests
from typing import List, Dict

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

# conservative blacklist to avoid strong claims
BLACKLIST_PATTERNS = [
    r"\bclinical\b", r"\bstudy\b", r"\bproven\b", r"\bFDA\b", r"\bdermatologist\b",
    r"\bguarantee\b", r"\bguaranteed\b"
]

def _contains_blacklisted(text: str) -> bool:
    t = (text or "").lower()
    for pat in BLACKLIST_PATTERNS:
        if re.search(pat, t):
            return True
    return False

def _validate_paraphrase(original: str, paraphrase: str, product_fields: Dict) -> bool:
    """
    Conservative validation:
    - no blacklisted terms
    - numeric values not contradicted (prices, percentages)
    - paraphrase not excessively longer than original
    """
    if not isinstance(paraphrase, str) or not paraphrase.strip():
        return False

    if _contains_blacklisted(paraphrase):
        return False

    # price check
    orig_price = product_fields.get("price_inr")
    if orig_price:
        # if paraphrase includes numbers ensure orig_price exists in paraphrase
        nums = re.findall(r"\d{2,}", paraphrase.replace(",", ""))
        if nums and str(orig_price) not in paraphrase:
            return False

    # concentration percent check
    concentration = str(product_fields.get("concentration") or "")
    orig_pct = re.search(r"(\d+%)", concentration)
    p_pct = re.search(r"(\d+%)", paraphrase)
    if p_pct and orig_pct:
        if p_pct.group(1) != orig_pct.group(1):
            return False
    if p_pct and not orig_pct:
        # paraphrase introduced a percent when none existed
        return False

    # length heuristic
    if len(paraphrase) > max(600, len(original) * 4):
        return False

    return True

def _extract_text_from_ollama_response(resp_json):
    """
    Robustly extract text from various possible Ollama response shapes.
    Try common keys; fallback to raw JSON string.
    """
    # common Ollama return shapes: {'results': [{'content': '...'}], ...}
    try:
        if isinstance(resp_json, dict):
            # results -> each item may have 'content' or 'output' or 'text'
            if "results" in resp_json and isinstance(resp_json["results"], list):
                parts = []
                for r in resp_json["results"]:
                    # r may contain 'content' (string) or 'message' or 'text'
                    if isinstance(r, dict):
                        for k in ("content", "text", "output", "message"):
                            if k in r and isinstance(r[k], str):
                                parts.append(r[k])
                                break
                    else:
                        parts.append(str(r))
                return "\n".join(parts).strip()
            # fallback keys
            for k in ("output", "content", "text"):
                if k in resp_json and isinstance(resp_json[k], str):
                    return resp_json[k].strip()
        # last resort:
        return json.dumps(resp_json, ensure_ascii=False)
    except Exception:
        return json.dumps(resp_json, ensure_ascii=False)

def paraphrase_faq_items(faq_items: List[Dict], product_fields: Dict, model: str = None) -> List[Dict]:
    """
    Paraphrase the 'answer' field of each faq_item using Ollama local server.
    - faq_items: list of {"question", "category", "answer"}
    - product_fields: product_model dict (for validation)
    Returns paraphrased items or original items on failure.
    """
    model = model or DEFAULT_MODEL
    results = []
    # single-call batching is better, but some Ollama setups are easier per-item; we'll do per-item for clarity
    url = f"{OLLAMA_BASE}/api/generate"

    headers = {"Content-Type": "application/json"}
    for item in faq_items:
        original = item.get("answer", "")
        # build strict prompt that asks only to paraphrase without adding facts
        prompt = (
            "Paraphrase the following answer for clarity and tone WITHOUT adding any new facts, "
            "numbers, references, or claims. If you cannot paraphrase without adding facts, return the original answer.\n\n"
            f"Question: {item.get('question','')}\n"
            f"Category: {item.get('category','')}\n"
            f"Answer: {original}\n\n"
            "Return only the paraphrased answer as plain text."
        )

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": 0.2,
            "max_tokens": 256
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=OLLAMA_TIMEOUT)
            if not resp.ok:
                # fallback to original item
                results.append(item)
                continue
            try:
                resp_json = resp.json()
            except Exception:
                # not JSON? fallback to raw text
                resp_text = resp.text
                paraphrase = resp_text.strip()
            else:
                paraphrase = _extract_text_from_ollama_response(resp_json)

            # validation
            if _validate_paraphrase(original, paraphrase, product_fields):
                new_item = item.copy()
                new_item["answer"] = paraphrase
                results.append(new_item)
            else:
                # conservative fallback
                results.append(item)
        except Exception:
            # network or server issue: fallback
            results.append(item)

    return results
