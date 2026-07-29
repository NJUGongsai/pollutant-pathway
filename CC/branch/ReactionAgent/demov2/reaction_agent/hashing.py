"""Canonical content hashing + stable IDs (chatgpt_p1_train.md §8.3/§8.4)."""
from __future__ import annotations
import hashlib, json

def _canonicalize(obj) -> object:
    if isinstance(obj, dict):
        return {k: _canonicalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):
        # list 顺序语义由调用方负责；这里保持原序但元素规范化
        return [_canonicalize(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_canonicalize(x) for x in obj)  # 非语义集合排序
    return obj

def canonical_hash(obj) -> str:
    payload = json.dumps(_canonicalize(obj), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def stable_id(prefix: str, obj) -> str:
    return f"{prefix}_{canonical_hash(obj)[:12]}"
