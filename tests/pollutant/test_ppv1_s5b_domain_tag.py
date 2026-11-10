"""PPV1 S5b —— 题域标签通道(biosysmodb121 第三题域;零网络、零金标、合成夹具)。

背景(2026-10-29 CC 拍板):BIOSYSMOdb121 是第三个题域,对外数字不得借用
``298`` 标签。此前 ``build_reference_graph`` 的 ``domain`` 写死默认 ``"298"``
且 CLI ``build`` 没有透出口,任何新题域的参考图都会被标成 298 —— 正是红线
禁止的张冠李戴。本测试锁住四条:

- 298 缺省逐字节不变(历史批可复现,零漂移);
- ``domain="biosysmodb121"`` 落到参考图 ``domain`` 字段且图 ID 前缀换域;
- ``dev`` 保持历史 ``rg298-`` 前缀(历史口径不因新增题域而变);
- 取值域外的 domain fail-closed 拒绝(不静默接受)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    DOMAINS,
    ReferenceGraphContractError,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    build_question_batch,
    s5b_graph_id,
)

_SUB = "CCO"
_PROD = "CC=O"


def _questions(tmp_path: Path) -> Path:
    path = tmp_path / "questions.jsonl"
    path.write_text(json.dumps({
        "qid": "DOM-Q001", "substrate_smiles": _SUB,
        "products_smiles": [_PROD]}) + "\n", encoding="utf-8")
    return path


def _build(tmp_path: Path, name: str, **kwargs) -> dict:
    questions = _questions(tmp_path)
    manifest = build_question_batch(
        questions, tmp_path / name, batch_tag=name,
        pool_provider=lambda _s: [], provider_kind="scripted",
        synthetic_review=True, **kwargs)
    graph_path = next(
        (tmp_path / name / "reference_graphs").glob("*.json"))
    return {"manifest": manifest,
            "graph": json.loads(graph_path.read_text(encoding="utf-8")),
            "graph_id": graph_path.stem}


def test_domains_enum_contains_third_domain() -> None:
    assert DOMAINS == frozenset({"dev", "298", "biosysmodb121"})


def test_default_domain_is_298_with_legacy_prefix(tmp_path: Path) -> None:
    out = _build(tmp_path, "b298")
    assert out["graph"]["domain"] == "298"
    assert out["graph_id"].startswith("rg298-")
    assert out["graph_id"] == s5b_graph_id("DOM-Q001")


def test_biosysmodb121_domain_propagates_and_changes_prefix(
        tmp_path: Path) -> None:
    out = _build(tmp_path, "bb121", domain="biosysmodb121")
    assert out["graph"]["domain"] == "biosysmodb121"
    assert out["graph_id"].startswith("rgbiosysmodb121-")
    # 同一 qid 在两个题域下得到不同的图 ID,不会互相覆盖
    assert out["graph_id"] != s5b_graph_id("DOM-Q001")


def test_dev_domain_keeps_legacy_prefix(tmp_path: Path) -> None:
    out = _build(tmp_path, "bdev", domain="dev")
    assert out["graph"]["domain"] == "dev"
    assert out["graph_id"].startswith("rg298-")


def test_unknown_domain_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ReferenceGraphContractError):
        _build(tmp_path, "bbad", domain="not_a_domain")