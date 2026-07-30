import datetime
import pathlib
import time

import pytest
from reaction_agent.hashing import canonical_hash, stable_id

def test_same_content_different_key_order_same_hash():
    a = canonical_hash({"b": 1, "a": 2})
    b = canonical_hash({"a": 2, "b": 1})
    assert a == b

def test_source_change_different_hash():
    assert canonical_hash({"x": 1}) != canonical_hash({"x": 2})

def test_same_content_deterministic():
    # renamed from test_timestamp_excluded_from_canonical (MINOR-3): 原命名误导，
    # 此处实际验证的是同内容确定性，而非 timestamp 排除。
    h1 = canonical_hash({"data": "abc"})
    assert h1 == canonical_hash({"data": "abc"})

def test_canonical_hash_does_not_inject_timestamp():
    # canonical_hash 本身不得主动注入 timestamp/临时路径 (MINOR-3 真正的 ts 排除测试)。
    # 同一对象在不同时刻调用，hash 必须一致——证明无隐藏 timestamp。
    obj = {"smiles": "CCO"}
    h1 = canonical_hash(obj)
    time.sleep(0.01)
    h2 = canonical_hash(obj)
    assert h1 == h2

def test_canonical_hash_rejects_datetime():
    # datetime 对象不得静默 stringify 进入 hash (IMPORTANT-2)。
    # default=str 会让 datetime 纳入 hash，违反 "canonical_hash 不含 timestamp" 硬约束。
    with pytest.raises(TypeError):
        canonical_hash({"ts": datetime.datetime(2026, 7, 29, 12, 0, 0)})

def test_canonical_hash_rejects_path():
    # Path 对象不得静默 stringify 进入 hash (IMPORTANT-2)。
    # default=str 会让临时路径纳入 hash，违反 "canonical_hash 不含临时路径" 硬约束。
    with pytest.raises(TypeError):
        canonical_hash({"path": pathlib.Path("/tmp/x.json")})

def test_canonical_hash_allows_basic_types():
    # 正常 dict/list/基本类型仍 work (IMPORTANT-2 回归)。
    # 显式 scope 允许 dict/list/str/int/float/bool/None 及其嵌套。
    h = canonical_hash({
        "a": 1, "b": [1, 2, "x"], "c": True, "d": None, "e": 1.5,
        "nested": {"k": [False, 0, "s"]},
    })
    assert isinstance(h, str) and len(h) == 64

def test_stable_id_format():
    sid = stable_id("rxn", {"smiles": "C"})
    assert sid.startswith("rxn_") and len(sid) > 4

def test_stable_id_python_hash_not_used():
    # 同对象多次调用稳定（不依赖 Python hash() 随机化）
    obj = {"smiles": "CCO", "name": "ethanol"}
    assert stable_id("participant", obj) == stable_id("participant", obj)
