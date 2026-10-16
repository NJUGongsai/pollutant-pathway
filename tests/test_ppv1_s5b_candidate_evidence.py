"""候选证据卡测试(Plan v1 §2.1 落地;任务书 TASK_EVIDENCE_CARD_IMPL_
2026-10-15 §四;设计书 EVIDENCE_CARD_DESIGN_NOTE_2026-10-15)。

三组验收(任务书 §四):
- **正控**:合成池条目(含 spec 事实+prepared 单一装配源)→ 载荷含全部
  证据字段且值正确;同输入双跑字节全等(确定性);提示词版本哈希变化被
  断言(显式升版 = 新批身份);格式反馈轮载荷同样携带证据(一致性);
- **负控**:事实缺失 → 字面 "unknown"(不许空串/null 冒充);描述符
  字段不得含「确定位点」措辞(gasteiger 字段名自带 _reference + 提示词
  规则段声明);禁词扫描(EC 编号/编造条件键在证据面零出现);
- **不变量**:证据函数不修改 spec(只读);未接线载荷逐字节向后兼容;
  run_inputs 零证据键(证据只在 decide 调用期现算);端到端池条目集合
  与顺序不变。

环境纪律:零模型零网络(scripted 桩同载荷路径);零金标零题面
(合成分子与真实 298 集合零重叠)。
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.candidate_evidence import (  # noqa: E402
    CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    candidate_evidence_payload,
    substrate_evidence_payload,
)
from pathway_v43.pollutant.production import prepare_hypothesis  # noqa: E402
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    ScriptedRealModelAdapter,
    _PROPOSALS_SYSTEM_PROMPT,
    build_proposals_user_payload,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.s5b_builder import build_question_batch  # noqa: E402
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_DEFAULT_PROFILE_POLICY,
)

# 8da11cb7 基线(候选证据卡轮之前的提示词哈希;升版断言锚点)
LEGACY_PROMPT_SHA256_8DA11CB7 = (
    "e28b5342b0036a6af0893ca310045bed9d0e9d8bfc85f3d21c880e9a7917b962")

_EC_NUMBER_RE = re.compile(r"\b\d+\.\d{1,2}\.\d{1,2}\.\d+\b")
_FORBIDDEN_EVIDENCE_KEYS = frozenset({
    "ec", "ec_number", "ec_numbers", "record_status", "recorded_status",
    "condition_recommended", "recommended_conditions", "temperature_c",
    "ph_value", "reaction_site_assignment", "assigned_sites",
})


def _recorded_spec() -> dict:
    """合成池条目(recorded 形态;key/ref 前缀沿 s5b_compiler/recorded_
    source 既有契约;合成 record id 与真实 298 记录零重叠)。"""
    return {
        "key": "rec-SYNTH_REC_0001@L3", "product_smiles": "CC=O",
        "coefficient": 1,
        "transformation_ref": "SYNTH_REC_0001@L3",
        "origin_group_key": "rec-source:SYNTH_REC_0001@L3",
        "edits": [
            {"op": "change_bond_order", "atom1": "S_C_2",
             "atom2": "S_O_1", "from_order": "single",
             "to_order": "double"},
            {"op": "add_atom", "element": "O",
             "new_atom_id": "SN_O_1", "atom1": "S_C_2"},
        ],
        "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
        "alignment": {
            "status": "resolved",
            "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"},
            "equivalence_classes": [],
            "ref": "recorded-inferred:SYNTH_REC_0001@L3"},
        "expectation": {"target_smiles": "CC=O"},
        "compile": {
            "compiler_version": "synthetic", "mapping_origin": "inferred",
            "n_alignments_total": 2, "n_equivalent_alignments": 2,
            "truncated": False, "template_center_maps": [1, 2]},
        "requirements": [
            {"key": "oxygen_regime", "level": "preference",
             "value": "aerobic", "basis": "observed_condition_reference"}],
    }


def _prepared_for(spec: dict) -> dict:
    """真实单一构建源(prepare_hypothesis)的 prepared 产物。"""
    substrate = build_chemical_state("CCO", "raw_input",
                                     [{"record": "synth-evcard"}])
    return prepare_hypothesis(
        spec, parent_path_id="path-synth-evcard",
        substrate_state=substrate,
        transformation_ref=str(spec.get("transformation_ref") or ""))


# ---------------------------------------------------------------- 正控


def test_candidate_evidence_recorded_spec_full_fields() -> None:
    """正控:recorded 形态 spec+prepared → 全部证据字段值正确。"""
    spec = _recorded_spec()
    prepared = _prepared_for(spec)
    evidence = candidate_evidence_payload(spec=spec, prepared=prepared)
    # 编辑变化摘要(逐 op 确定性渲染)
    summary = evidence["edit_summary"]
    assert summary["n_edits"] == 2
    assert summary["op_counts"] == {"add_atom": 1, "change_bond_order": 1}
    assert summary["bond_order_changes"] == [
        {"atom1": "S_C_2", "atom2": "S_O_1",
         "from_order": "single", "to_order": "double"}]
    assert summary["added_atoms"] == [
        {"new_atom_id": "SN_O_1", "element": "O"}]
    assert summary["bonds_broken"] == 0 and summary["bonds_formed"] == 0
    # 参与物角色与来源(prepared 单一装配源;缺省装配两行)
    rows = evidence["participants"]
    assert [r["role"] for r in rows] == ["primary_substrate",
                                         "principal_product"]
    assert rows[0]["side"] == "reactant" and rows[1]["side"] == "product"
    assert rows[0]["smiles"] == "CCO" and rows[1]["smiles"] == "CC=O"
    assert all(r["coefficient_status"] == "known" for r in rows)
    # 来源(在线字段派生)
    assert evidence["source"]["source_kind"] == "recorded_inferred"
    assert evidence["source"]["transformation_ref"] == \
        "SYNTH_REC_0001@L3"
    assert evidence["source"]["alignment_ref"] == \
        "recorded-inferred:SYNTH_REC_0001@L3"
    # 对齐状态/质量/检索信号(spec.compile 在线诊断块)
    quality = evidence["alignment_quality"]
    assert quality["status"] == "resolved"
    assert quality["mapping_origin"] == "inferred"
    assert quality["n_alignments_total"] == 2
    assert quality["n_equivalent_alignments"] == 2
    assert quality["enumeration_truncated"] is False
    assert quality["stereo_dissolution_applied"] == "unknown"
    assert quality["n_donor_atoms_mapped"] == 2
    # 条件与证明范围(键在位=真值;键缺=unknown)
    scope = evidence["conditions_and_scope"]
    assert scope["requirements"] == spec["requirements"]
    assert scope["participant_list_status"] == "partial"
    assert scope["step_scope"] == "net_reaction"


def test_candidate_evidence_analog_spec_source_kind() -> None:
    """正控:analog 形态(tpl- 前缀)→ source_kind=analog_template。"""
    spec = _recorded_spec()
    spec["key"] = "tpl-SYNTH_TPL_0002"
    spec["origin_group_key"] = "analog-template:SYNTH_TPL_0002"
    spec["alignment"] = {
        "status": "resolved", "donor_to_current": {"S_C_2": "S_C_2"},
        "ref": "tpl:SYNTH_TPL_0002"}
    evidence = candidate_evidence_payload(spec=spec, prepared=None)
    assert evidence["source"]["source_kind"] == "analog_template"
    assert evidence["participants"] == "unknown"  # 无 prepared 不重派生


def test_substrate_evidence_cco_fields() -> None:
    """正控:底物档案卡(官能团命中+参考描述符+组成)值正确。"""
    evidence = substrate_evidence_payload("CCO")
    assert evidence["substrate_render_ok"] is True
    classes = {f["class"] for f in evidence["functional_groups"]}
    assert "hydroxyl_oh" in classes and "arene_ring" not in classes
    hydroxyl = next(f for f in evidence["functional_groups"]
                    if f["class"] == "hydroxyl_oh")
    assert hydroxyl["n_hits"] == 1
    assert hydroxyl["matches"] == [["S_O_1", "S_C_2"]]  # 同一 S ID 空间
    charges = evidence["gasteiger_charges_reference"]
    assert charges["min"] <= charges["mean"] <= charges["max"]
    assert charges["min"] < 0 and charges["max"] > 0  # 乙醇三原子极性
    ids = [e["atom_id"] for e in charges["lowest"] + charges["highest"]]
    assert len(set(ids)) == 3 and set(ids) == {"S_C_1", "S_C_2", "S_O_1"}
    assert evidence["element_counts"] == {"C": 2, "H": 6, "O": 1}
    assert evidence["molecular_formula"] == "C2H6O"
    assert evidence["condition_keys_known"] == "unknown"  # 未传档案


def test_substrate_evidence_with_profile_online_values() -> None:
    """正控:substrate_profile 在线值直读(fidelity/条件键)。"""
    from pathway_v43.pollutant.substrate_profile import (
        build_substrate_profile,
    )

    state = build_chemical_state("CCO", "raw_input",
                                 [{"record": "synth-evcard"}])
    profile = build_substrate_profile(state, None)
    evidence = substrate_evidence_payload("CCO",
                                          substrate_profile=profile)
    assert evidence["representation_fidelity"] == \
        dict(profile.representation_fidelity)
    assert evidence["condition_keys_known"] == []


def test_payload_carries_evidence_and_schema_version() -> None:
    """正控:载荷携带 evidence 子对象+顶层 substrate_evidence+schema。"""
    spec = _recorded_spec()
    evidence = candidate_evidence_payload(spec=spec, prepared=None)
    substrate = substrate_evidence_payload("CCO")
    payload = json.loads(build_proposals_user_payload(
        substrate_smiles="CCO", atom_id_map={"S_C_1": "C"},
        pool_entries=[
            {"hypothesis_id": "B", "product_smiles": "CC=O",
             "transformation_ref": "t1", "coproducts": [],
             "evidence": evidence}],
        substrate_evidence=substrate))
    entry = payload["pool_hypotheses"][0]
    assert entry["evidence"] == evidence
    assert payload["substrate_evidence"] == substrate
    assert payload["candidate_evidence_schema_version"] == \
        CANDIDATE_EVIDENCE_SCHEMA_VERSION == "candidate-evidence-2"
    # 既有四键不受影响
    assert entry["hypothesis_id"] == "B" and entry["coproducts"] == []


def test_determinism_double_run_byte_equality() -> None:
    """正控:同输入双跑 ⇒ 证据与载荷字节全等(纯函数;零随机零时序)。"""
    spec = _recorded_spec()
    prepared = _prepared_for(spec)
    a = json.dumps(candidate_evidence_payload(spec=spec,
                                              prepared=prepared),
                   sort_keys=True, ensure_ascii=False)
    b = json.dumps(candidate_evidence_payload(spec=spec,
                                              prepared=prepared),
                   sort_keys=True, ensure_ascii=False)
    assert a == b
    for smiles in ("CCO", "c1ccccc1CC(=O)N", "CC(=O)Nc1ccc(O)cc1"):
        sa = json.dumps(substrate_evidence_payload(smiles),
                        sort_keys=True)
        sb = json.dumps(substrate_evidence_payload(smiles),
                        sort_keys=True)
        assert sa == sb
    kwargs = dict(
        substrate_smiles="CCO", atom_id_map={"S_C_1": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "t1", "coproducts": [],
                       "evidence": candidate_evidence_payload(
                           spec=spec, prepared=prepared)}],
        substrate_evidence=substrate_evidence_payload("CCO"))
    assert build_proposals_user_payload(**kwargs) == \
        build_proposals_user_payload(**kwargs)


def test_prompt_version_hash_moved_and_evidence_rules_present() -> None:
    """正控:提示词版本哈希变化被断言(显式升版 = 新批身份)。"""
    assert PROPOSALS_PROMPT_VERSION != LEGACY_PROMPT_SHA256_8DA11CB7
    assert PROPOSALS_PROMPT_VERSION == hashlib.sha256(
        _PROPOSALS_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    # 证据规则段在位(语义:字段来源/unknown 处理/描述符纪律)
    assert "Candidate evidence notes" in _PROPOSALS_SYSTEM_PROMPT
    assert '"evidence"' in _PROPOSALS_SYSTEM_PROMPT
    assert '"substrate_evidence"' in _PROPOSALS_SYSTEM_PROMPT
    assert "never guess or invent a value for it" in \
        _PROPOSALS_SYSTEM_PROMPT
    # 描述符纪律:参考字段措辞在位,「确定位点」否定语义在位
    assert "not assigned reaction sites" in _PROPOSALS_SYSTEM_PROMPT


def _feedback_profile() -> dict:
    return dict(S5B_DEFAULT_PROFILE_POLICY,
                format_feedback_policy={"max_format_feedback_rounds": 1})


def test_format_feedback_round_carries_evidence(tmp_path) -> None:
    """正控/一致性:格式反馈轮载荷同样携带证据(同入口共用)。"""
    spec = _recorded_spec()
    hyp_id = _prepared_for(spec)["hypothesis"].hypothesis_id
    model = ScriptedRealModelAdapter(
        strategy="responses",
        responses=[
            # 可解析但缺 "proposals" 键 ⇒ json_field_error(可进反馈轮;
            # 非 JSON 文本是 structure_unparseable,不进反馈)
            json.dumps({"proposal": []}),
            json.dumps({"proposals": [{"hypothesis_id": hyp_id}],
                        "rank_hypotheses": [hyp_id]}),
        ],
        model_id="evcard-fb")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="evcard-fb", smiles="CCO",
        plan={"pools": {"CCO": [spec]},
              "model": {"provider_kind": "scripted"}},
        model=model, profile_policy=_feedback_profile())
    assert out["native_export"]["export_digest"]
    assert len(model.seen_user_payloads) == 2  # 首发+反馈轮
    for raw in model.seen_user_payloads:
        payload = json.loads(raw)
        entry = payload["pool_hypotheses"][0]
        assert entry["evidence"]["edit_summary"]["n_edits"] == 2
        assert entry["evidence"]["source"]["source_kind"] == \
            "recorded_inferred"
        assert payload["candidate_evidence_schema_version"] == \
            CANDIDATE_EVIDENCE_SCHEMA_VERSION
        assert payload["substrate_evidence"]["molecular_formula"] == \
            "C2H6O"
    # 反馈轮格式反馈块照旧
    assert json.loads(
        model.seen_user_payloads[1])["format_feedback"]["error_kind"]


# ---------------------------------------------------------------- 负控


def test_missing_facts_render_unknown_not_empty_or_none() -> None:
    """负控:事实缺失 → 字面 unknown(不许空串/null 冒充)。"""
    evidence = candidate_evidence_payload(spec={}, prepared=None)
    assert evidence["edit_summary"] == "unknown"
    assert evidence["participants"] == "unknown"
    assert evidence["source"] == {
        "source_kind": "unknown", "transformation_ref": "unknown",
        "origin_group_key": "unknown", "alignment_ref": "unknown"}
    quality = evidence["alignment_quality"]
    assert quality["status"] == "unknown"
    assert quality["mapping_origin"] == "unknown"
    assert quality["n_alignments_total"] == "unknown"
    assert quality["enumeration_truncated"] == "unknown"
    assert quality["n_donor_atoms_mapped"] == "unknown"
    assert evidence["conditions_and_scope"]["requirements"] == "unknown"
    _assert_no_empty_or_none(evidence)
    # 渲染失败底物 ⇒ 各字段如实 unknown(不伪造)
    broken = substrate_evidence_payload("not-a-smiles")
    assert broken["substrate_render_ok"] is False
    assert broken["functional_groups"] == []
    assert broken["gasteiger_charges_reference"] == "unknown"
    assert broken["element_counts"] == "unknown"
    assert broken["molecular_formula"] == "unknown"
    _assert_no_empty_or_none(broken)


def _assert_no_empty_or_none(node) -> None:
    """递归:证据面零空串零 None(缺失一律 unknown 字面)。"""
    if isinstance(node, dict):
        for key, value in node.items():
            assert value is not None, f"{key} 为 None(冒充事实)"
            if isinstance(value, str):
                assert value != "", f"{key} 为空串(冒充事实)"
            _assert_no_empty_or_none(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_empty_or_none(item)


def test_forbidden_content_scan_on_evidence() -> None:
    """负控:EC 编号/编造条件/记录状态/指派位点在证据面零出现。"""
    spec = _recorded_spec()
    prepared = _prepared_for(spec)
    blobs = [
        candidate_evidence_payload(spec=spec, prepared=prepared),
        candidate_evidence_payload(spec={}, prepared=None),
        substrate_evidence_payload("CCO"),
        substrate_evidence_payload("c1ccccc1N(=O)=O"),
    ]
    for blob in blobs:
        text = json.dumps(blob, sort_keys=True, ensure_ascii=False)
        assert not _EC_NUMBER_RE.search(text), "证据面出现 EC 编号形态"
        assert "SYNTH_REC" not in text or "transformation_ref" in text
        for key in _FORBIDDEN_EVIDENCE_KEYS:
            assert f'"{key}"' not in text, f"证据面出现禁用键 {key}"
    # 描述符纪律:参考字段命名(提示词措辞断言见正控)
    assert "gasteiger_charges_reference" in blobs[2]


# ---------------------------------------------------------------- 不变量


def test_evidence_function_does_not_mutate_spec() -> None:
    """不变量:证据函数只读 spec(deepcopy 前后逐字节同)。"""
    spec = _recorded_spec()
    snapshot = copy.deepcopy(spec)
    candidate_evidence_payload(spec=spec, prepared=None)
    assert spec == snapshot
    assert json.dumps(spec, sort_keys=True) == json.dumps(
        snapshot, sort_keys=True)


def test_payload_without_evidence_backward_compatible_bytes() -> None:
    """不变量:未接线调用方载荷与既有路径逐字节同(向后兼容)。"""
    payload = build_proposals_user_payload(
        substrate_smiles="CCO",
        atom_id_map={"S_C_1": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "t1", "coproducts": []}])
    expected = json.dumps({
        "substrate_smiles": "CCO",
        "substrate_atom_id_map": {"S_C_1": "C", "S_O_1": "O"},
        "pool_hypotheses": [{
            "hypothesis_id": "B", "product_smiles": "CC=O",
            "transformation_ref": "t1", "coproducts": []}],
        "protocol_version": "s5b-real-model-1",
    }, ensure_ascii=False, sort_keys=True)
    assert payload == expected
    # evidence 非法形状(非 dict)不渲染,同字节
    assert build_proposals_user_payload(
        substrate_smiles="CCO", atom_id_map={"S_C_1": "C"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "t1", "coproducts": [],
                       "evidence": "junk"}]) == json.dumps({
        "substrate_smiles": "CCO",
        "substrate_atom_id_map": {"S_C_1": "C"},
        "pool_hypotheses": [{
            "hypothesis_id": "B", "product_smiles": "CC=O",
            "transformation_ref": "t1", "coproducts": []}],
        "protocol_version": "s5b-real-model-1",
    }, ensure_ascii=False, sort_keys=True)


def test_run_inputs_zero_evidence_keys(tmp_path) -> None:
    """不变量:run_inputs 零证据键(证据只在 decide 调用期现算)。"""
    questions_path = tmp_path / "q.jsonl"
    questions_path.write_text(
        json.dumps({"qid": "SYNTH-EV1", "substrate_smiles": "CCO",
                    "products_smiles": ["CC=O"],
                    "raw_reaction": "CCO>>CC=O"}) + "\n",
        encoding="utf-8")
    build_question_batch(
        questions_path, tmp_path / "batch", batch_tag="evcard",
        pool_provider=lambda s: [_recorded_spec()],
        provider_kind="scripted", synthetic_review=True)
    run_input = (tmp_path / "batch/run_inputs/SYNTH-EV1.json").read_text(
        encoding="utf-8")
    assert '"evidence"' not in run_input
    assert '"substrate_evidence"' not in run_input
    assert "candidate_evidence_schema_version" not in run_input
    # 池条目集合与顺序:证据注入不改变冻结池形态(spec 原样入池)
    plan = json.loads(run_input)["plan"]
    assert plan["pools"]["CCO"][0]["key"] == "rec-SYNTH_REC_0001@L3"
    assert "evidence" not in plan["pools"]["CCO"][0]


def test_end_to_end_pool_order_unchanged_in_payload(tmp_path) -> None:
    """不变量:端到端 decide 载荷池条目集合与顺序不变(证据只增不扰)。"""
    specs = [_recorded_spec(),
             dict(_recorded_spec(), key="tpl-SYNTH_TPL_0002",
                  origin_group_key="analog-template:SYNTH_TPL_0002")]
    model = ScriptedRealModelAdapter(strategy="first_pool",
                                     model_id="evcard-order")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="evcard-order", smiles="CCO",
        plan={"pools": {"CCO": specs},
              "model": {"provider_kind": "scripted"}},
        model=model, profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY))
    assert out["native_export"]["export_digest"]
    payload = json.loads(model.seen_user_payloads[0])
    entries = payload["pool_hypotheses"]
    # 集合与顺序不变:池条目数 == 冻结池数;证据与 spec 逐位对应
    # (载荷 hypothesis_id 是内容派生假设 ID,顺序即冻结池序)
    assert len(entries) == len(specs) == 2
    assert entries[0]["hypothesis_id"] != entries[1]["hypothesis_id"]
    assert [e["evidence"]["source"]["source_kind"] for e in entries] == [
        "recorded_inferred", "analog_template"]
    # 池候选四键+evidence,零多余键
    for entry in entries:
        assert set(entry.keys()) == {
            "hypothesis_id", "product_smiles", "transformation_ref",
            "coproducts", "evidence"}


# ------------------------------------------------- P1 修复轮(2026-10-15)
# Codex 复审 docs/EVIDENCE_CARD_CODEX_REVIEW_2026-10-15.md §阻塞项回修
# 负控;复核判据(评审 §五收口):未知系数不得变数值、已知系数维持原值;
# 不可用电荷不残留 NaN/Infinity、分子式/元素组成等其它底物事实仍输出。


def _assert_strict_json_payload(raw: str) -> None:
    """最终用户载荷双面核验:解析后对象零 NaN/Infinity(allow_nan=False
    重序列化触发 ValueError),原文零 NaN/Infinity/null 字面。"""
    payload = json.loads(raw)
    json.dumps(payload, allow_nan=False)
    assert "NaN" not in raw and "Infinity" not in raw
    assert "null" not in raw  # 缺失事实一律字面 unknown,零 null 冒充


def test_full_chain_recorded_compiled_unknown_coefficient_payload(
        tmp_path) -> None:
    """负控(P1-1):真实 recorded 编译形状(库记录无配平系数 ⇒ spec
    合法无 coefficient 键)走公开 start_ppv1_run(scripted=True,零
    monkeypatch),断言最终用户载荷参与物 coefficient 为字面 unknown
    而非 null;coefficient_status 原语义保留。"""
    from pathway_v43.pollutant.recorded_source import (
        compile_recorded_reaction,
    )

    compiled = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO", products=["CC=O"],
        record_id="SYNTH_COD_P1FIX")  # 合成 record id,与真实 298 零重叠
    assert compiled["status"] == "compiled"
    spec = compiled["spec"]
    assert "coefficient" not in spec  # 库记录无配平系数 ⇒ 合法删除
    model = ScriptedRealModelAdapter(strategy="first_pool",
                                     model_id="evcard-p1fix-unk")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="evcard-p1fix-unk", smiles="CCO",
        plan={"pools": {"CCO": [spec]},
              "model": {"provider_kind": "scripted"}},
        model=model, profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        scripted=True)
    assert out["native_export"]["export_digest"]
    raw = model.seen_user_payloads[0]
    rows = json.loads(raw)["pool_hypotheses"][0]["evidence"]["participants"]
    assert len(rows) == 2  # 底物+主产物缺省装配两行
    for row in rows:
        # 修复前实测 null(评审探针);修复后字面 unknown,状态原语义
        assert row["coefficient"] == "unknown"
        assert row["coefficient_status"] == "unknown"
    _assert_strict_json_payload(raw)


def test_full_chain_default_coproduct_unknown_coefficient_payload(
        tmp_path) -> None:
    """负控(P1-1):主系数已知+默认副产物(production.py 缺省装配
    coproduct coefficient=None/unknown)⇒ 载荷副产物 coefficient 为
    字面 unknown;已知系数维持原值不变(复核判据二)。"""
    spec = _recorded_spec()  # 主系数已知:coefficient=1
    spec["coproducts"] = ["CO"]  # 合成副产物,与真实 298 零重叠
    model = ScriptedRealModelAdapter(strategy="first_pool",
                                     model_id="evcard-p1fix-coprod")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="evcard-p1fix-coprod", smiles="CCO",
        plan={"pools": {"CCO": [spec]},
              "model": {"provider_kind": "scripted"}},
        model=model, profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        scripted=True)
    assert out["native_export"]["export_digest"]
    raw = model.seen_user_payloads[0]
    rows = json.loads(raw)["pool_hypotheses"][0]["evidence"]["participants"]
    by_role = {r["role"]: r for r in rows}
    # 已知系数维持原值(不因修复变成 unknown,也不得伪造数值)
    assert by_role["primary_substrate"]["coefficient"] == "1"
    assert by_role["principal_product"]["coefficient"] == "1"
    assert by_role["primary_substrate"]["coefficient_status"] == "known"
    assert by_role["principal_product"]["coefficient_status"] == "known"
    # 默认副产物未知系数:字面 unknown 而非 null
    assert by_role["coproduct"]["coefficient"] == "unknown"
    assert by_role["coproduct"]["coefficient_status"] == "unknown"
    assert by_role["coproduct"]["smiles"] == "CO"
    _assert_strict_json_payload(raw)


def test_substrate_evidence_nonfinite_gasteiger_degrades_unknown() -> None:
    """负控(P1-2):Gasteiger 对 Se 底物合法解析但不抛异常返回非有限
    值 ⇒ 整个电荷描述符降字面 unknown,零 NaN/Infinity 残留;分子式/
    元素组成照常输出(不全面拒绝合法底物,不许 NaN 冒充事实)。"""
    for smiles, formula, counts in (
            ("C[SeH]", "CH4Se", {"C": 1, "H": 4, "Se": 1}),
            ("C[Se]C", "C2H6Se", {"C": 2, "H": 6, "Se": 1})):
        evidence = substrate_evidence_payload(smiles)
        assert evidence["substrate_render_ok"] is True
        assert evidence["gasteiger_charges_reference"] == "unknown"
        # 其它底物事实保留(评审复核判据)
        assert evidence["molecular_formula"] == formula
        assert evidence["element_counts"] == counts
        assert isinstance(evidence["functional_groups"], list)
        text = json.dumps(evidence, sort_keys=True)
        assert "NaN" not in text and "Infinity" not in text
        _assert_no_empty_or_none(evidence)


def test_full_chain_gasteiger_nonfinite_negative_and_finite_positive(
        tmp_path) -> None:
    """负控+正控(P1-2,全链):Se 底物最终用户载荷零 NaN/Infinity、
    电荷字段=unknown、分子式/元素组成仍在;同链 CCO 有限参考电荷数值
    保留(合法能力不丢,同链正控)。"""
    runs_root = tmp_path / "runs"
    for smiles, run_id in (("C[SeH]", "evcard-p1fix-se"),
                           ("CCO", "evcard-p1fix-cco")):
        model = ScriptedRealModelAdapter(
            strategy="responses",
            responses=[json.dumps({"proposals": [], "rank_hypotheses": []})],
            model_id=run_id)
        out = start_ppv1_run(
            config=resolve_config(), runs_root=runs_root, run_id=run_id,
            smiles=smiles,
            plan={"pools": {smiles: []},
                  "model": {"provider_kind": "scripted"}},
            model=model, profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
            scripted=True)
        assert out["native_export"]["export_digest"]
        raw = model.seen_user_payloads[0]
        _assert_strict_json_payload(raw)
        substrate = json.loads(raw)["substrate_evidence"]
        assert substrate["substrate_render_ok"] is True
        if smiles == "C[SeH]":
            assert substrate["gasteiger_charges_reference"] == "unknown"
            assert substrate["molecular_formula"] == "CH4Se"
            assert substrate["element_counts"]["Se"] == 1
        else:
            charges = substrate["gasteiger_charges_reference"]
            assert isinstance(charges, dict)
            assert charges["min"] <= charges["mean"] <= charges["max"]
            assert charges["min"] < 0 and charges["max"] > 0
            assert isinstance(charges["min"], float)


def test_functional_group_smarts_caliber_amide_vs_amine() -> None:
    """mimo 修正案(2026-10-16):amine_primary/secondary 补酰胺排除(同 tertiary
    先例口径)——酰胺 N 不再误标 amine;普通一级/二级胺(含苯胺)不受影响。"""
    from pathway_v43.pollutant.candidate_evidence import (
        substrate_evidence_payload,
    )
    def _classes(smi):
        return {r["class"] for r in
                substrate_evidence_payload(smi)["functional_groups"]}
    assert "amine_primary" not in _classes("CC(=O)N")
    assert "amine_secondary" not in _classes("CC(=O)NC")
    assert "amine_primary" in _classes("CCN")
    assert "amine_primary" in _classes("Nc1ccccc1")


def test_functional_group_smarts_caliber_carboxyl_oh_excluded() -> None:
    """mimo 修正案(2026-10-16):hydroxyl_oh 排除羧酸自身 -OH(酸+醇双标签
    最贵误导面);醇羟基不受影响(乙醇/乳酸醇臂)。"""
    from pathway_v43.pollutant.candidate_evidence import (
        substrate_evidence_payload,
    )
    def _rows(smi):
        return {r["class"]: r["n_hits"] for r in
                substrate_evidence_payload(smi)["functional_groups"]}
    assert "hydroxyl_oh" not in _rows("CC(=O)O")
    assert _rows("CCO").get("hydroxyl_oh") == 1
    assert _rows("CC(O)C(=O)O").get("hydroxyl_oh") == 1  # 乳酸:仅醇 OH
    assert _rows("CC(O)C(=O)O").get("carboxylic_acid") == 1
