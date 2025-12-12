# logic_blocks/compare_block.py
"""
Compare Block - deterministic, auditable comparison between product_a and a generated or provided product_b.

Goals:
 - Deterministic variant generator for product_b when not provided (but marked clearly as generated).
 - Computes ingredient/benefit overlap and price deltas.
 - Produces human-readable summary, pros/cons, recommendation structure.
 - Avoids exposing a "real" SKU for product_b (product_b is explicitly labelled/generated).
 - No external calls; fully reproducible.

Based on your original implementation (deterministic generator + scoring). See original for provenance. :contentReference[oaicite:2]{index=2}
"""
from typing import Dict, Any, List
import hashlib
import math

def _normalize_list(lst):
    if not lst:
        return []
    return [str(x).strip().lower() for x in lst if x]

def _title_case_list(lst):
    return [s.title() for s in lst]

def _unique(a: List[str], b: List[str]):
    aset = set(a)
    bset = set(b)
    return sorted(list(aset - bset))

def _shared(a: List[str], b: List[str]):
    aset = set(a)
    bset = set(b)
    return sorted(list(aset & bset))

def _safe_price(p):
    try:
        if p is None:
            return None
        return float(p)
    except Exception:
        return None

def _ensure_field(dst: Dict, key: str, src: Dict):
    if key not in dst or dst.get(key) is None:
        if key in src and src.get(key) is not None:
            dst[key] = src.get(key)

# Deterministic variant generator (keeps it safe & labelled)
def _deterministic_variant(product_a: Dict[str, Any]) -> Dict[str, Any]:
    base_id = product_a.get("id", "product_a")
    digest = hashlib.md5(base_id.encode("utf8")).hexdigest()
    num = int(digest[:8], 16)

    ingredient_swaps = [
        ["glycerin", "niacinamide"],
        ["squalane", "glycerin"],
        ["panthenol", "glycerin"],
        ["betaine", "urea"]
    ]
    benefit_variants = [
        ["hydration", "soothing"],
        ["anti-aging", "firming"],
        ["brightening", "even-tone"],
        ["hydration", "barrier-repair"]
    ]
    concentration_options = ["5% Vitamin C", "10% Vitamin C", "15% Vitamin C"]
    skin_type_variants = [
        ["dry", "sensitive"],
        ["normal", "dry"],
        ["oily", "combination"],
        ["all skin types"]
    ]
    price_mults = [0.8, 1.1, 1.25, 1.5]

    idx1 = num % len(ingredient_swaps)
    idx2 = (num >> 3) % len(benefit_variants)
    idx3 = (num >> 6) % len(concentration_options)
    idx4 = (num >> 9) % len(skin_type_variants)
    idx5 = (num >> 12) % len(price_mults)

    base_ings = [s for s in (product_a.get("ingredients") or [])]
    base_bens = [s for s in (product_a.get("benefits") or [])]

    shared_seed = base_ings[:1] if base_ings else []
    swap_choice = ingredient_swaps[idx1]
    # normalize case
    shared_seed_lower = [s.lower() for s in shared_seed]
    new_ings = shared_seed + [x for x in swap_choice if x.lower() not in shared_seed_lower]

    shared_ben_seed = base_bens[:1] if base_bens else []
    shared_ben_lower = [s.lower() for s in shared_ben_seed]
    new_bens = shared_ben_seed + [b for b in benefit_variants[idx2] if b.lower() not in shared_ben_lower]

    new_conc = concentration_options[idx3]
    new_skin = skin_type_variants[idx4]
    price_a = product_a.get("price_inr") or 0
    mult = price_mults[idx5]
    new_price = None if price_a == 0 else int(round(price_a * mult))

    variant = {
        # keep id clearly generated and not a real SKU
        "id": f"generated_variant_{idx1}{idx2}",
        "name": f"{product_a.get('name','Product A')} (Generated Comparator)",
        "ingredients": new_ings,
        "benefits": new_bens,
        "concentration": new_conc,
        "skin_type": new_skin,
        "usage": product_a.get("usage"),
        "side_effects": product_a.get("side_effects"),
        "price_inr": new_price,
        "metadata": {
            "generated": True,
            "variant_reason": f"swap_idx={idx1},ben_idx={idx2},conc_idx={idx3},skin_idx={idx4},price_idx={idx5}"
        }
    }
    return variant

def _build_recommendation(a: Dict[str, Any], product_b: Dict[str, Any],
                          shared_benefits: List[str], unique_benefits_a: List[str], unique_benefits_b: List[str],
                          overall: float, price_a: float, price_b: float) -> Dict[str, Any]:
    rules = []
    # benefit-driven rules
    for ben in unique_benefits_b:
        rules.append({
            "if": f"you want {ben.title()}",
            "choose": "Product B",
            "reason": f"Product B lists {ben.title()} while Product A does not."
        })
    for ben in unique_benefits_a:
        rules.append({
            "if": f"you want {ben.title()}",
            "choose": "Product A",
            "reason": f"Product A lists {ben.title()} while Product B does not."
        })

    # skin-type rules
    a_skin = [s.title() for s in (a.get("skin_type") or [])]
    b_skin = [s.title() for s in (product_b.get("skin_type") or [])]

    for st in sorted(set(b_skin) - set(a_skin)):
        rules.append({
            "if": f"your skin is {st}",
            "choose": "Product B",
            "reason": f"Product B lists {st} as suitable."
        })
    for st in sorted(set(a_skin) - set(b_skin)):
        rules.append({
            "if": f"your skin is {st}",
            "choose": "Product A",
            "reason": f"Product A lists {st} as suitable."
        })

    # price-driven rule when similar
    if overall >= 0.6 and price_a is not None and price_b is not None:
        cheaper = "Product A" if price_a <= price_b else "Product B"
        rules.append({
            "if": "you prioritize price and products are similar",
            "choose": cheaper,
            "reason": f"Products are similar (overall={overall}). {cheaper} is cheaper."
        })

    default_choice = "Consider Product A"
    default_reasons = ["No strong preference matched; defaulting to Product A."]
    if len(unique_benefits_b) > 0 and overall < 0.5:
        default_choice = "Consider Product B"
        default_reasons = ["Product B offers distinct benefits not present in Product A."]

    if overall >= 0.6:
        rationale = [f"Products are fairly similar (overall={overall}). Consider price and specific preferences."]
    else:
        rationale = [f"Products differ (overall={overall}). Follow contextual rules above."]

    return {
        "decision": "Contextual",
        "default": default_choice,
        "default_reasons": default_reasons,
        "rules": rules,
        "decision_rationale": rationale
    }

def run_block(product_model: Dict[str, Any]) -> Dict[str, Any]:
    a = product_model or {}
    raw = a.get("raw", {}) if isinstance(a.get("raw", {}), dict) else {}
    product_b = raw.get("product_b") or raw.get("productB") or None

    if not product_b:
        product_b = _deterministic_variant(a)
    else:
        product_b = dict(product_b)

    # Ensure fields exist
    for fld in ("concentration", "skin_type", "usage", "side_effects"):
        _ensure_field(product_b, fld, a)

    if "metadata" not in product_b or not isinstance(product_b.get("metadata"), dict):
        product_b["metadata"] = product_b.get("metadata") or {}
    if isinstance(a.get("metadata"), dict):
        for k, v in a["metadata"].items():
            product_b["metadata"].setdefault(k, v)

    # Normalize lists
    a_ingredients = _normalize_list(a.get("ingredients") or [])
    b_ingredients = _normalize_list(product_b.get("ingredients") or [])
    a_benefits = _normalize_list(a.get("benefits") or [])
    b_benefits = _normalize_list(product_b.get("benefits") or [])

    shared_ingredients = _shared(a_ingredients, b_ingredients)
    unique_to_a = _unique(a_ingredients, b_ingredients)
    unique_to_b = _unique(b_ingredients, a_ingredients)

    shared_benefits = _shared(a_benefits, b_benefits)
    unique_benefits_a = _unique(a_benefits, b_benefits)
    unique_benefits_b = _unique(b_benefits, a_benefits)

    # Scores
    try:
        ing_overlap = len(shared_ingredients) / max(1, len(set(a_ingredients + b_ingredients)))
        ben_overlap = len(shared_benefits) / max(1, len(set(a_benefits + b_benefits)))
    except Exception:
        ing_overlap = 0.0
        ben_overlap = 0.0

    overall = round((ing_overlap + ben_overlap) / 2.0, 3)

    price_a = _safe_price(a.get("price_inr"))
    price_b = _safe_price(product_b.get("price_inr"))
    if price_a is not None and price_b is not None and price_a != 0:
        absolute = round(price_b - price_a, 2)
        percent = round((absolute / price_a) * 100, 2)
        price_diff = {"absolute": absolute, "percent": percent}
    else:
        price_diff = {"absolute": None, "percent": None}

    # Summary
    summary_parts = [f"Comparing {a.get('name','Product A')} and {product_b.get('name','Product B')}."]
    if shared_ingredients:
        summary_parts.append(f"Both share ingredients: {', '.join(_title_case_list(shared_ingredients))}.")
    if unique_to_a:
        summary_parts.append(f"Unique to A: {', '.join(_title_case_list(unique_to_a))}.")
    if unique_to_b:
        summary_parts.append(f"Unique to B: {', '.join(_title_case_list(unique_to_b))}.")
    if price_diff and price_diff["absolute"] is not None:
        summary_parts.append(f"Price difference (B - A): ₹{price_diff['absolute']} ({price_diff['percent']}%).")
    summary = " ".join(summary_parts)

    # Pros / Cons
    pros_a: List[str] = []
    pros_b: List[str] = []
    cons_a: List[str] = []
    cons_b: List[str] = []

    if price_a is not None and price_b is not None:
        if price_a < price_b:
            pros_a.append(f"Lower price (₹{int(price_a)})")
            cons_b.append(f"Higher price (₹{int(price_b)})")
        elif price_b < price_a:
            pros_b.append(f"Lower price (₹{int(price_b)})")
            cons_a.append(f"Higher price (₹{int(price_a)})")

    for ing in shared_ingredients:
        label = f"Provides {ing.title()}"
        pros_a.append(label)
        pros_b.append(label)

    for ing in unique_to_a:
        pros_a.append(f"Unique ingredient: {ing.title()}")
        cons_b.append(f"Missing {ing.title()}")
    for ing in unique_to_b:
        pros_b.append(f"Unique ingredient: {ing.title()}")
        cons_a.append(f"Missing {ing.title()}")

    for bnm in shared_benefits:
        pros_a.append(f"Provides {bnm.title()}")
        pros_b.append(f"Provides {bnm.title()}")
    for bnm in unique_benefits_a:
        pros_a.append(f"Offers {bnm.title()}")
    for bnm in unique_benefits_b:
        pros_b.append(f"Offers {bnm.title()}")

    value_indicator = 0.0
    try:
        if price_a and price_b:
            price_ratio = price_b / price_a if price_a != 0 else None
            normalized_price = (price_b - price_a) / max(1, price_a) if price_a != 0 else None
            value_indicator = round((overall) / (1 + abs(normalized_price if normalized_price is not None else 0)), 3)
    except Exception:
        value_indicator = 0.0

    value_label = "Product A offers better value" if value_indicator >= 0.5 else "Product B may offer better value"

    recommendation_obj = _build_recommendation(a, product_b, shared_benefits, unique_benefits_a, unique_benefits_b,
                                              overall, price_a, price_b)

    out = {
        "product_b": product_b,
        "shared_ingredients": _title_case_list(shared_ingredients),
        "unique_to_a": _title_case_list(unique_to_a),
        "unique_to_b": _title_case_list(unique_to_b),
        "shared_benefits": _title_case_list(shared_benefits),
        "unique_benefits_a": _title_case_list(unique_benefits_a),
        "unique_benefits_b": _title_case_list(unique_benefits_b),
        "price_a": price_a,
        "price_b": price_b,
        "price_difference": price_diff,
        "score": {"ingredient_overlap": round(ing_overlap, 3), "benefit_overlap": round(ben_overlap, 3), "overall": overall},
        "summary": summary,
        "value_indicator": value_indicator,
        "value_label": value_label,
        "generated_note": "Product B was deterministically generated for comparison (not a real SKU).",
        "recommendation": recommendation_obj,
        "pros": {"product_a": pros_a, "product_b": pros_b},
        "cons": {"product_a": cons_a, "product_b": cons_b},
        "score_explanation": "Scores range 0–1; higher = more similarity.",
        "decision_rationale": recommendation_obj.get("decision_rationale", [])
    }
    return out
