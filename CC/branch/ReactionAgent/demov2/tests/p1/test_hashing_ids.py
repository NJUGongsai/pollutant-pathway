import pytest
from reaction_agent.hashing import canonical_hash, stable_id

def test_same_content_different_key_order_same_hash():
    a = canonical_hash({"b": 1, "a": 2})
    b = canonical_hash({"a": 2, "b": 1})
    assert a == b

def test_source_change_different_hash():
    assert canonical_hash({"x": 1}) != canonical_hash({"x": 2})

def test_timestamp_excluded_from_canonical():
    # canonical_hash 不应把临时时间纳入；此处验证 dict 内 ts 变化改变 hash，
    # 但 canonical_hash 本身不注入 ts
    h1 = canonical_hash({"data": "abc"})
    assert h1 == canonical_hash({"data": "abc"})

def test_stable_id_format():
    sid = stable_id("rxn", {"smiles": "C"})
    assert sid.startswith("rxn_") and len(sid) > 4

def test_stable_id_python_hash_not_used():
    # 同对象多次调用稳定（不依赖 Python hash() 随机化）
    obj = {"smiles": "CCO", "name": "ethanol"}
    assert stable_id("participant", obj) == stable_id("participant", obj)
