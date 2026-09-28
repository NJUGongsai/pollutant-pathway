"""R1-a 产物指纹稳定性审计(任务书 §2;无凭证无网络)。

哈希事故回归:r1 四臂 50 条路线的 ``ArtifactIntegrityError`` 根因是
``assess_alignment`` 的 alignment 是 int 键 dict({2:0, 11:8}),写入时
``sort_keys`` 按数值序、JSON 往返后键变字符串按字典序("11"<"2"),
写入哈希 ≠ 读回哈希。本套件整链验收 str 键修补:

- 多位映射号(2、11、13)逐分支:成功/失败/歧义/预算外各对齐结果;
- 真实故障结构(含失败明细的 decision)写入→重读→再读,哈希稳定;
- 同键幂等写;单字段/单字节篡改仍被拒绝(fail-closed 不静默)。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pathway_v43.domain.models import canonical_json, content_hash
from pathway_v43.storage.artifact_store import (
    ArtifactConflict,
    ArtifactIntegrityError,
    ArtifactStore,
)


def _assert_str_keys(o, path="$"):
    if isinstance(o, dict):
        for k in o:
            assert isinstance(k, str), f"int/非str键 {path}.{k!r}"
            _assert_str_keys(o[k], f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _assert_str_keys(v, f"{path}[{i}]")


def _assert_roundtrip(obj, label):
    s1 = canonical_json(obj)
    r1 = json.loads(s1)
    s2 = canonical_json(r1)
    assert s1 == s2, f"{label}: canonical round-trip 不稳定"
    r2 = json.loads(s2)
    s3 = canonical_json(r2)
    assert s2 == s3, f"{label}: 二次往返不稳定"
    return r1


# ------------------------------------------------ 生产端全分支


@pytest.mark.parametrize("fixture_id", [
    "F1_full_donor_exact",       # 成功:full donor 对齐
    "F2_center_match_first_shell_conflict",  # 失败明细:首壳冲突
    "F3_bond_order_mismatch",    # 失败:键级不匹配
    "F3v_valence_h_conflict",    # 失败:价态/氢冲突
    "F4_formal_charge_conflict",  # 失败:形式电荷冲突
    "F5_symmetric_equivalent",   # 等价对齐
    "F6_competing_sites",        # 歧义:竞争位点
])
def test_alignment_all_branches_str_key_and_stable(fixture_id):
    """七个夹具覆盖 success/失败明细/歧义分支:整块无 int 键 + 双往返稳定。"""
    from tests.test_reactant_similar import _fx, _similar_ref
    from pathway_v43.services.donor_applicability import (
        ApplicabilityPolicy, build_eligibility,
    )

    fx = _fx(fixture_id)
    # 不带相似通道(既有路径)与带相似通道(D1 新路径)都审计
    for similar in (None, _similar_ref(fx["donor"])):
        block = build_eligibility(
            [], fx["substrate_smiles"],
            ApplicabilityPolicy(max_donor_candidates=3),
            similar_refs=[similar] if similar else None)
        _assert_str_keys(block, fixture_id)
        _assert_roundtrip(block, f"{fixture_id}(similar={bool(similar)})")
        for card in block["cards"]:
            for ev in card.get("donor_evals", []):
                for r in ev.get("results", []):
                    for k in (r.get("alignment") or {}):
                        assert isinstance(k, str)


def test_multi_digit_mapping_numbers_specific():
    """事故现场的映射号形状:2、11、13(字典序 "11"<"2" 恰是事故雷)。

    用真实事故同源形状(payload 含 int 键 alignment 的 decision 结构)
    + 多位映射号键值,断言生产端输出的键全为字符串且双往返稳定。
    直接调 assess_alignment 需要分子对象,这里在存储层钉"int 键必炸"
    机理(见 regression 用例)并在生产端夹具上核对真实 map 号形状。
    """
    # r1 事故真实键形:alignment {2:0, 11:8}(数值序 vs 字典序分歧源)
    ints = {2: 0, 11: 8, 13: 1}
    strs = {str(k): v for k, v in ints.items()}
    # 数值序键序 != 字符串字典序键序 —— 这就是写入/读回哈希分歧机理
    assert sorted(ints) == [2, 11, 13] and sorted(strs) == ["11", "13", "2"]
    # 生产端转换后的 canonical 序对同一 dict 稳定
    s1 = canonical_json(strs)
    assert s1 == canonical_json(json.loads(s1))
    # 真实夹具的 alignment 键位:results 明细与 selected 两处全为 str
    from tests.test_reactant_similar import _fx, _similar_ref
    from pathway_v43.services.donor_applicability import (
        ApplicabilityPolicy, build_eligibility,
    )

    for fid in ("F1_full_donor_exact",
                "F2_center_match_first_shell_conflict",
                "F6_competing_sites"):
        fx = _fx(fid)
        block = build_eligibility(
            [], fx["substrate_smiles"],
            ApplicabilityPolicy(max_donor_candidates=3),
            similar_refs=[_similar_ref(fx["donor"])])
        keys: set[str] = set()
        for card in block["cards"]:
            for ev in card.get("donor_evals", []):
                for r in ev.get("results", []):
                    keys.update((r.get("alignment") or {}).keys())
                sel = (ev.get("selected_result") or {})
                if sel:
                    keys.update((sel.get("alignment") or {}).keys())
        sel_block = block.get("selected") or {}
        keys.update((sel_block.get("alignment") or {}).get(
            "alignment", {}).keys())
        assert keys and all(isinstance(k, str) for k in keys), \
            f"{fid}: {sorted(keys)}"


def test_assess_donor_payload_has_no_int_keys_all_statuses():
    """assess_donor 全部返回分支(含提前返回)无 int 键 dict。"""
    from pathway_v43.services.donor_applicability import assess_donor

    donor = {"record_id": "r1", "index": "corpus", "asset_file": "f",
             "asset_sha256": "a" * 64, "line_no": 3,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "OCCO", "mapped_rhs": "OCC=O"}
    # donor == substrate(提前返回分支)
    ev = assess_donor(donor, "OCCO")
    _assert_str_keys(ev, "same-substrate")
    _assert_roundtrip(ev, "same-substrate")
    # 正常路径分支(成功或失败由化学决定,两态都审计)
    ev2 = assess_donor(donor, "CCCO")
    _assert_str_keys(ev2, "normal")
    _assert_roundtrip(ev2, "normal")
    # 不可解析供体(提前返回)
    ev3 = assess_donor({**donor, "mapped_lhs": "NOT_A_SMILES"},
                       "CCCO")
    _assert_str_keys(ev3, "unparseable")
    _assert_roundtrip(ev3, "unparseable")


# ------------------------------------------------ 存储端写读哈希


def _decision_like_payload() -> dict:
    """r1 事故同款 decision 形状:资格块含失败明细 results。"""
    from tests.test_reactant_similar import _fx, _similar_ref
    from pathway_v43.services.donor_applicability import (
        ApplicabilityPolicy, build_eligibility,
    )

    fx = _fx("F2_center_match_first_shell_conflict")
    block = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[_similar_ref(fx["donor"])])
    return {
        "outcome": "awaiting_prediction", "path_id": "p1",
        "prediction_mode": "analogy_edit",
        "prediction_reason": "applicable_donor:gated:x",
        "accepted_evidence_id": None, "considered": 26,
        "analogy_eligibility": block, "reason": "r",
        "run_id": "audit-r1", "strategy_version": "v43-policy-5",
        "created_at": "2026-09-28T00:00:00+0000",
    }


def test_decision_write_read_reread_hash_stable(tmp_path):
    """真实故障结构:写 → 读 → 再读,每次哈希校验都通过。"""
    store = ArtifactStore(tmp_path / "runs", "audit-r1")
    payload = _decision_like_payload()
    env = store.write("T_audit", "decision", payload)
    assert env.get("created") is True
    e1 = store.read("T_audit", "decision")
    assert e1["payload_hash"] == env["payload_hash"]
    e2 = store.read("T_audit", "decision")
    assert e2["payload_hash"] == env["payload_hash"]
    assert canonical_json(e1["payload"]) == canonical_json(e2["payload"])
    # payload 哈希与内容自洽(整树往返)
    assert content_hash(json.loads(canonical_json(payload))) == \
        env["payload_hash"]


def test_same_key_same_content_idempotent(tmp_path):
    """同键同内容幂等;同键不同内容冲突(不可变产物)。"""
    store = ArtifactStore(tmp_path / "runs", "audit-r1")
    payload = _decision_like_payload()
    env1 = store.write("T_audit", "decision", payload)
    env2 = store.write("T_audit", "decision", payload)
    assert env2.get("created") is False  # 幂等返回,不覆盖
    with pytest.raises(ArtifactConflict):
        store.write("T_audit", "decision", {**payload, "reason": "tamper"})


def _tamper(path: Path, mode: str) -> None:
    text = path.read_text(encoding="utf-8")
    if mode == "field":
        env = json.loads(text)
        env["payload"]["reason"] = "tampered"
        path.write_text(canonical_json(env) + "\n", encoding="utf-8")
    elif mode == "byte":
        data = bytearray(path.read_bytes())
        # 翻转 payload 中一个字节(非结构位,保持 JSON 可读)
        idx = text.index('"reason"') + 12
        data[idx] = (data[idx] + 1) if data[idx] < 127 else data[idx] - 1
        path.write_bytes(bytes(data))


@pytest.mark.parametrize("mode", ["field", "byte"])
def test_tampered_artifact_rejected(tmp_path, mode):
    """单字段/单字节篡改必须被读端拒绝(fail-closed,不静默当缺失)。

    byte 模式可能破坏 JSON 结构 → 读取抛 JSONDecodeError,同为
    fail-closed(不吞错、不静默返回)。
    """
    store = ArtifactStore(tmp_path / "runs", "audit-r1")
    store.write("T_audit", "decision", _decision_like_payload())
    _tamper(tmp_path / "runs" / "audit-r1" / "results" / "T_audit"
            / "decision.json", mode)
    with pytest.raises((ArtifactIntegrityError, json.JSONDecodeError)):
        store.read("T_audit", "decision")


def test_regression_int_key_payload_reproduces_original_bug(tmp_path):
    """机理钉:int 键 payload 写入后重读必然哈希不一致(修复前的事故)。

    用 int 键构造同形状 payload,证明存储层的守卫确实拦截该类漂移
    (生产端已不产 int 键,这里验证读取端不吞错)。
    """
    store = ArtifactStore(tmp_path / "runs", "audit-r1")
    payload = {"results": [{"alignment": {2: 0, 11: 8, 13: 1}}]}
    env = store.write("T_intkey", "decision", payload)
    path = tmp_path / "runs" / "audit-r1" / "results" / "T_intkey" \
        / "decision.json"
    # 写入后的文件键已是字符串(JSON 规则);重算哈希与信封不一致
    with pytest.raises(ArtifactIntegrityError):
        store.read("T_intkey", "decision")
    # 信封哈希是按内存 int 键算的;重读按文件 str 键算,两者不同
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert content_hash(disk["payload"]) != env["payload_hash"]
