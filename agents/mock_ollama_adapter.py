def paraphrase_faq_items(faq_items, product_fields, model=None):
    out = []
    for it in faq_items:
        new = it.copy()
        new["answer"] = it["answer"] + " (paraphrased-mock)"
        out.append(new)
    return out
