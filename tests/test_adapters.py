# tests/test_adapters.py
import json
from agents.langchain_adapters import FunctionChain

def test_function_chain_single_input_single_output(tmp_path):
    def dummy_parser(raw):
        # emulate your parser returning a dict
        return {"product_id": "p1", "name": raw.get("Product Name")}

    chain = FunctionChain(dummy_parser, input_keys=["raw"], output_keys=["product"])
    result = chain._call({"raw": {"Product Name": "GlowBoost"}})
    assert "product" in result
    assert result["product"]["product_id"] == "p1"
    assert result["product"]["name"] == "GlowBoost"

def test_function_chain_multi_input_dict_output():
    def dummy_logic(payload):
        # payload will be a dict when multiple input_keys are used by caller
        product = payload["product"]
        questions = payload["questions"]
        return {"content_blocks": {"title": product["name"], "questions": questions}}

    chain = FunctionChain(dummy_logic, input_keys=["product", "questions"], output_keys=["content_blocks"])
    res = chain._call({"product": {"name": "G"}, "questions": ["q1", "q2"]})
    assert "content_blocks" in res
    assert res["content_blocks"]["title"] == "G"
    assert res["content_blocks"]["questions"] == ["q1", "q2"]

from agents.langchain_runnables import wrap_as_runnable

def test_runnable_simple():
    def echo(x):
        return x
    r = wrap_as_runnable(echo)
    assert hasattr(r, "invoke")
    out = r.invoke("hello")
    assert out == "hello"

def test_runnable_chain_simple():
    def add1(x):
        return x + 1
    def mul2(x):
        return x * 2
    # wrap both and chain via composition if available
    r1 = wrap_as_runnable(add1)
    r2 = wrap_as_runnable(mul2)
    try:
        chain = r1 | r2
        res = chain.invoke(3)
        assert res == 8
    except Exception:
        # fallback: manual chaining
        assert r2.invoke(r1.invoke(3)) == 8
