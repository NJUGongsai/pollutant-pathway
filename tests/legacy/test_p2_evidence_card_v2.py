"""P2 证据卡 v2 离线实施测试（2026-10-21）。

任务书：docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md
冻结设计：docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md（SHA-256
37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4）。

覆盖：
- v1 off 路径身份零漂移（prompt 哈希/schema/descriptor/载荷字节/identity 键）；
- v2 字段面裁剪（删 Gasteiger/分子式/元素组成/冗余来源/数组/coefficient_status）；
- 参与物保真（已知系数保留、unknown 不伪造、行数不隐藏）；
- SMARTS 质子化容忍与完整内部匹配；
- 主产物级 FG 类集合 delta、分子式/碳氧化态 delta 与 unknown 边界；
- 两臂共享 v2 prompt、仅证据字段不同；
- 确定性/输入只读/池顺序不变。

环境纪律：零模型零网络（scripted 桩同载荷路径）；零金标零题面
（合成分子与真实 298 集合零重叠）。
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.candidate_evidence import (  # noqa: E402
    CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION,
    CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2,
    CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2,
    candidate_evidence_payload_v2,
    substrate_evidence_payload,
    substrate_evidence_payload_v2,
    substrate_facts_v2,
)
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.production import prepare_hypothesis  # noqa: E402
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    PROPOSALS_PROMPT_VERSION_V2,
    ScriptedRealModelAdapter,
    _PROMPT_EVIDENCE_NOTES_V1,
    _PROMPT_STATIC_4,
    _PROPOSALS_SYSTEM_PROMPT,
    build_proposals_user_payload,
    proposals_prompt_version,
    proposals_system_prompt,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    PPV1RunError,
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_DEFAULT_PROFILE_POLICY,
)

V1_PROMPT_SHA256 = (
    "fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e")


def _recorded_spec() -> dict:
    """合成池条目（recorded 形态；与真实 298 记录零重叠）。"""
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
    substrate = build_chemical_state("CCO", "raw_input",
                                     [{"record": "synth-p2-v2"}])
    return prepare_hypothesis(
        spec, parent_path_id="path-synth-p2-v2",
        substrate_state=substrate,
        transformation_ref=str(spec.get("transformation_ref") or ""))


def _v2_evidence(spec: dict, substrate: str = "CCO", *,
                 prepared: dict | None = None) -> dict:
    return candidate_evidence_payload_v2(
        spec=spec, prepared=prepared,
        substrate_facts=substrate_facts_v2(substrate))


# ---------------------------------------------------------------- 身份


def test_v1_prompt_identity_unchanged_and_v2_differs() -> None:
    assert PROPOSALS_PROMPT_VERSION == V1_PROMPT_SHA256
    assert PROPOSALS_PROMPT_VERSION == hashlib.sha256(
        _PROPOSALS_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    assert PROPOSALS_PROMPT_VERSION_V2 != PROPOSALS_PROMPT_VERSION
    assert PROPOSALS_PROMPT_VERSION_V2 == hashlib.sha256(
        proposals_system_prompt("v2").encode("utf-8")).hexdigest()
    # v2 只改证据段：其它段逐字沿用
    assert proposals_system_prompt("v2") != _PROPOSALS_SYSTEM_PROMPT
    assert "functional-group class delta" in proposals_system_prompt("v2")
    assert "partial charges" not in proposals_system_prompt("v2")
    assert "partial charges" in _PROPOSALS_SYSTEM_PROMPT
    # v1 static4 仍等于 prefix+v1 notes（证明 v2 没改 Rule/Example 段）
    assert _PROMPT_STATIC_4 == (
        _PROMPT_STATIC_4.split("Candidate evidence notes", 1)[0]
        + _PROMPT_EVIDENCE_NOTES_V1)
    assert proposals_prompt_version(None) == PROPOSALS_PROMPT_VERSION
    assert proposals_prompt_version("v1") == PROPOSALS_PROMPT_VERSION
    assert proposals_prompt_version("v2") == PROPOSALS_PROMPT_VERSION_V2
    with pytest.raises(ValueError):
        proposals_system_prompt("v3")


def test_v2_schema_and_descriptor_versions() -> None:
    assert CANDIDATE_EVIDENCE_SCHEMA_VERSION == "candidate-evidence-2"
    assert CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION == "candidate-evidence-descr-2"
    assert CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2 == "candidate-evidence-3"
    assert CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2 == \
        "candidate-evidence-descr-3"


# ---------------------------------------------------------------- 字段面


def test_v2_candidate_fields_exact() -> None:
    spec = _recorded_spec()
    evidence = _v2_evidence(spec, prepared=_prepared_for(spec))
    assert set(evidence) == {
        "edit_summary", "participants", "alignment_quality",
        "conditions_and_scope", "functional_group_delta", "product_delta",
    }
    assert "source" not in evidence
    # edit_summary 只留三项
    assert set(evidence["edit_summary"]) == {
        "n_edits", "op_counts", "bond_order_changes"}
    assert evidence["edit_summary"]["n_edits"] == 2
    assert evidence["edit_summary"]["op_counts"] == {
        "add_atom": 1, "change_bond_order": 1}
    # participants 保真紧凑
    rows = evidence["participants"]
    assert [r["role"] for r in rows] == [
        "primary_substrate", "principal_product"]
    assert set(rows[0]) == {"side", "role", "coefficient", "smiles"}
    assert rows[0]["coefficient"] == "1" and rows[1]["coefficient"] == "1"
    assert "coefficient_status" not in json.dumps(evidence)
    # alignment 只留 status
    assert evidence["alignment_quality"] == {"status": "resolved"}
    # conditions/scope 三键
    assert set(evidence["conditions_and_scope"]) == {
        "requirements", "participant_list_status", "step_scope"}
    # 新 delta
    assert evidence["functional_group_delta"] == {
        "scope": "principal_product",
        "gained": ["aldehyde"], "lost": ["hydroxyl_oh"]}
    assert evidence["product_delta"] == {
        "scope": "principal_product", "formula": {"H": -2},
        "carbon_oxidation_state": 1.0}


def test_v2_participants_preserve_known_and_unknown_coefficients() -> None:
    spec = _recorded_spec()
    spec["coproducts"] = ["CO"]
    prepared = _prepared_for(spec)
    evidence = _v2_evidence(spec, prepared=prepared)
    by_role = {r["role"]: r for r in evidence["participants"]}
    assert by_role["primary_substrate"]["coefficient"] == "1"
    assert by_role["principal_product"]["coefficient"] == "1"
    assert by_role["coproduct"]["coefficient"] == "unknown"
    assert by_role["coproduct"]["smiles"] == "CO"
    assert all(set(r) == {"side", "role", "coefficient", "smiles"}
               for r in evidence["participants"])
    # prepared 缺席 ⇒ participants=unknown，但图级 delta 仍可算
    no_prepared = _v2_evidence(spec, prepared=None)
    assert no_prepared["participants"] == "unknown"
    assert no_prepared["functional_group_delta"]["gained"] == ["aldehyde"]


def test_v2_payload_keeps_top_level_ref_and_omits_card_source() -> None:
    spec = _recorded_spec()
    evidence = _v2_evidence(spec, prepared=_prepared_for(spec))
    raw = build_proposals_user_payload(
        substrate_smiles="CCO", atom_id_map={"S_C_1": "C"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "SYNTH_REC_0001@L3",
                       "coproducts": [], "evidence": evidence}],
        substrate_evidence=substrate_evidence_payload_v2("CCO"),
        schema_version=CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2)
    payload = json.loads(raw)
    entry = payload["pool_hypotheses"][0]
    assert entry["transformation_ref"] == "SYNTH_REC_0001@L3"
    assert "source" not in entry["evidence"]
    assert payload["candidate_evidence_schema_version"] == \
        "candidate-evidence-3"


def test_v2_payload_compact_separators_only_on_arm_b() -> None:
    """P2 格式级压缩：v2 B 臂用紧凑分隔符；字段/取值零变化，A 臂不变。"""
    spec = _recorded_spec()
    evidence = _v2_evidence(spec, prepared=_prepared_for(spec))
    raw_b = build_proposals_user_payload(
        substrate_smiles="CCO", atom_id_map={"S_C_1": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "SYNTH_REC_0001@L3",
                       "coproducts": [], "evidence": evidence}],
        substrate_evidence=substrate_evidence_payload_v2("CCO"),
        schema_version=CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2)
    # 紧凑渲染 == 同值对象按最小分隔符重排（无字段增删、无取值改动）
    assert raw_b == json.dumps(
        json.loads(raw_b), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"))
    assert ", " not in raw_b and ": " not in raw_b
    assert json.loads(raw_b)["pool_hypotheses"][0]["evidence"] == evidence
    # A 臂（带 v2 schema 但无底物证据）仍默认分隔符 ⇒ v1 字节兼容
    raw_a = build_proposals_user_payload(
        substrate_smiles="CCO",
        atom_id_map={"S_C_1": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "t1", "coproducts": []}],
        schema_version=CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2)
    assert raw_a == _expected_v1_payload_without_evidence()
    assert ", " in raw_a and ": " in raw_a


def test_v2_substrate_evidence_compact() -> None:
    evidence = substrate_evidence_payload_v2("CCO")
    assert set(evidence) == {
        "descriptor_version", "substrate_render_ok", "functional_groups",
        "representation_fidelity", "condition_keys_known"}
    assert evidence["descriptor_version"] == "candidate-evidence-descr-3"
    assert evidence["substrate_render_ok"] is True
    assert evidence["functional_groups"] == [
        {"class": "hydroxyl_oh", "n_hits": 1}]
    text = json.dumps(evidence, sort_keys=True)
    for forbidden in ("gasteiger", "molecular_formula", "element_counts",
                      "smarts", "matches"):
        assert forbidden not in text


def test_v2_protonation_tolerance_only_on_v2_path() -> None:
    # v2 同时容忍中性/带电表示
    assert substrate_facts_v2("CC(=O)O")["class_hits"].get(
        "carboxylic_acid") == 1
    assert substrate_facts_v2("CC(=O)[O-]")["class_hits"].get(
        "carboxylic_acid") == 1
    assert substrate_facts_v2("CCN")["class_hits"].get(
        "amine_primary") == 1
    assert substrate_facts_v2("CC[NH3+]")["class_hits"].get(
        "amine_primary") == 1
    assert substrate_facts_v2("CCNCC")["class_hits"].get(
        "amine_secondary") == 1
    assert substrate_facts_v2("CC[NH2+]CC")["class_hits"].get(
        "amine_secondary") == 1
    assert substrate_facts_v2("CCN(C)CC")["class_hits"].get(
        "amine_tertiary") == 1
    assert substrate_facts_v2("CC[NH+](C)CC")["class_hits"].get(
        "amine_tertiary") == 1
    # 酰胺排除仍有效
    assert "amine_primary" not in substrate_facts_v2(
        "CC(=O)N")["class_hits"]
    assert "amine_secondary" not in substrate_facts_v2(
        "CC(=O)NCC")["class_hits"]
    # v1（off 路径）保持原行为：羧酸根不被识别为 carboxylic_acid
    v1_classes = {r["class"] for r in substrate_evidence_payload(
        "CC(=O)[O-]")["functional_groups"]}
    assert "carboxylic_acid" not in v1_classes


# ---------------------------------------------------------------- delta 锚


def _delta(spec: dict, substrate: str) -> dict:
    return _v2_evidence(spec, substrate=substrate)


def test_v2_fg_delta_no_change_single_gain_loss_multi_hit_overlap() -> None:
    # 无变化
    same = _delta({"product_smiles": "CCO"}, "CCO")[
        "functional_group_delta"]
    assert same == {"scope": "principal_product",
                    "gained": [], "lost": []}
    # 单得失（乙醇→乙醛）
    step = _delta({"product_smiles": "CC=O"}, "CCO")[
        "functional_group_delta"]
    assert step["gained"] == ["aldehyde"] and step["lost"] == [
        "hydroxyl_oh"]
    # 多命中（甘油三个羟基；类集合仍是单类）
    glycerol = substrate_facts_v2("CC(O)C(O)CO")
    assert glycerol["class_hits"]["hydroxyl_oh"] == 3
    # 跨类重叠（乙酰乙酸：ketone + carboxylic_acid 独立保留）
    overlap = substrate_facts_v2("CC(=O)CC(=O)O")
    assert overlap["class_hits"].get("ketone") == 1
    assert overlap["class_hits"].get("carboxylic_acid") == 1
    # 主产物 scope：副产物次序不改变 delta
    a = _v2_evidence({"product_smiles": "CC=O",
                      "coproducts": ["CO", "O"]}, "CCO")
    b = _v2_evidence({"product_smiles": "CC=O",
                      "coproducts": ["O", "CO"]}, "CCO")
    assert a["functional_group_delta"] == b["functional_group_delta"]
    assert a["product_delta"] == b["product_delta"]


def test_v2_product_delta_formula_and_carbon_oxidation() -> None:
    # 乙醇→乙醛：H -2，碳平均氧化态 +1
    aldehyde = _delta({"product_smiles": "CC=O"}, "CCO")["product_delta"]
    assert aldehyde["formula"] == {"H": -2}
    assert aldehyde["carbon_oxidation_state"] == 1.0
    # 乙醇→乙酸：H -2，O +1，碳平均氧化态 +2
    acid = _delta({"product_smiles": "CC(=O)O"}, "CCO")["product_delta"]
    assert acid["formula"] == {"H": -2, "O": 1}
    assert acid["carbon_oxidation_state"] == 2.0
    # 乙酸根→乙酸根：无变化；电荷入式后仍为 0
    acetate = _delta({"product_smiles": "CC(=O)[O-]"},
                     "CC(=O)[O-]")["product_delta"]
    assert acetate["formula"] == {}
    assert acetate["carbon_oxidation_state"] == 0.0
    # 含 N：氧化态 unknown（不猜），但公式差仍在
    amine = _delta({"product_smiles": "CC=O"}, "CCN")["product_delta"]
    # CCN -> CC=O：H -3、N -1、O +1（N 参与 ⇒ 氧化态不猜）
    assert amine["formula"] == {"H": -3, "N": -1, "O": 1}
    assert amine["carbon_oxidation_state"] == "unknown"


def test_v2_delta_unknown_boundaries() -> None:
    # 产物非法/多组分 ⇒ 整个 delta unknown
    for product in ("not_a_smiles", "CCO.CC", ""):
        ev = _v2_evidence({"product_smiles": product}, "CCO")
        assert ev["functional_group_delta"] == "unknown"
        assert ev["product_delta"] == "unknown"
    # 底物解析失败 ⇒ 整个 delta unknown（与真实零命中区分）
    bad = _v2_evidence({"product_smiles": "CCO"}, "not_a_smiles")
    assert bad["functional_group_delta"] == "unknown"
    assert bad["product_delta"] == "unknown"
    # 真实零命中：甲烷无注册 FG，delta 为空集合而非 unknown
    methane = _v2_evidence({"product_smiles": "C"}, "C")
    assert methane["functional_group_delta"] == {
        "scope": "principal_product", "gained": [], "lost": []}
    assert methane["product_delta"]["formula"] == {}
    # 真实零命中但底物 render 失败的空表读法不同
    broken = substrate_evidence_payload_v2("not_a_smiles")
    assert broken["substrate_render_ok"] is False
    assert broken["functional_groups"] == []


def test_v2_full_internal_matches_not_render_capped() -> None:
    # 10 个乙醇片段：完整内部匹配 n_hits=10；v2 不渲染 matches/smarts
    evidence = substrate_evidence_payload_v2(".".join(["CCO"] * 10))
    rows = {r["class"]: r["n_hits"] for r in evidence["functional_groups"]}
    assert rows["hydroxyl_oh"] == 10
    assert "matches" not in json.dumps(evidence)
    assert "smarts" not in json.dumps(evidence)


def test_v2_determinism_and_input_readonly() -> None:
    spec = _recorded_spec()
    prepared = _prepared_for(spec)
    snapshot = copy.deepcopy(spec)
    facts = substrate_facts_v2("CCO")
    a = json.dumps(_v2_evidence(spec, prepared=prepared),
                   sort_keys=True, ensure_ascii=False)
    b = json.dumps(_v2_evidence(spec, prepared=prepared),
                   sort_keys=True, ensure_ascii=False)
    assert a == b
    assert spec == snapshot
    assert json.dumps(facts, sort_keys=True) == json.dumps(
        substrate_facts_v2("CCO"), sort_keys=True)


def test_v2_forbidden_content_absent() -> None:
    spec = _recorded_spec()
    evidence = _v2_evidence(spec, prepared=_prepared_for(spec))
    text = json.dumps(evidence, sort_keys=True)
    for forbidden in (
            '"source"', "source_kind", "origin_group_key", "alignment_ref",
            "coefficient_status", "gasteiger", "molecular_formula",
            "element_counts", "smarts", "matches", "compile_diagnostics",
            "mapping_origin", "n_alignments_total",
            "enumeration_truncated"):
        assert forbidden not in text, forbidden
    # 顶层引用不在卡内，但载荷条目仍保留（由 real_model 构建）
    assert "SYNTH_REC_0001@L3" not in text


# ---------------------------------------------------------------- 载荷/运行


def _expected_v1_payload_without_evidence() -> str:
    return json.dumps({
        "substrate_smiles": "CCO",
        "substrate_atom_id_map": {"S_C_1": "C", "S_O_1": "O"},
        "pool_hypotheses": [{
            "hypothesis_id": "B", "product_smiles": "CC=O",
            "transformation_ref": "t1", "coproducts": []}],
        "protocol_version": "s5b-real-model-1",
    }, ensure_ascii=False, sort_keys=True)


def test_v2_arm_a_user_json_byte_compatible_with_v1() -> None:
    # A 臂：v2 prompt 下不渲染任何证据键 ⇒ 用户 JSON 与 v1 无证据路径同字节
    assert build_proposals_user_payload(
        substrate_smiles="CCO",
        atom_id_map={"S_C_1": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "t1", "coproducts": []}],
        schema_version=CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2) == \
        _expected_v1_payload_without_evidence()
    # 不传 schema_version 的旧调用仍逐字节同
    assert build_proposals_user_payload(
        substrate_smiles="CCO",
        atom_id_map={"S_C_1": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "B", "product_smiles": "CC=O",
                       "transformation_ref": "t1", "coproducts": []}]) == \
        _expected_v1_payload_without_evidence()


def _run_plan(spec: dict) -> dict:
    return {"pools": {"CCO": [spec]},
            "model": {"provider_kind": "scripted"}}


def test_v2_both_arms_share_prompt_and_identity(tmp_path) -> None:
    spec = _recorded_spec()
    runs_root = tmp_path / "runs"
    # B 臂（证据 on）
    model_b = ScriptedRealModelAdapter(strategy="first_pool",
                                       model_id="p2-v2-b")
    out_b = start_ppv1_run(
        config=resolve_config(), runs_root=runs_root, run_id="p2-v2-b",
        smiles="CCO", plan=_run_plan(spec), model=model_b,
        profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        evidence_card_enabled=True, evidence_card_version="v2")
    assert out_b["evidence_card_enabled"] is True
    assert out_b["evidence_card_version"] == "v2"
    assert model_b.seen_system_prompts == [proposals_system_prompt("v2")]
    payload_b = json.loads(model_b.seen_user_payloads[0])
    assert payload_b["candidate_evidence_schema_version"] == \
        "candidate-evidence-3"
    assert "substrate_evidence" in payload_b
    entry_b = payload_b["pool_hypotheses"][0]
    assert "source" not in entry_b["evidence"]
    assert entry_b["evidence"]["functional_group_delta"]["scope"] == \
        "principal_product"
    identity_b = json.loads(
        (runs_root / "p2-v2-b" / "run_identity.json").read_text())
    assert identity_b["strategy"]["evidence_card_version"] == "v2"
    assert identity_b["strategy"]["candidate_evidence_schema_version"] == \
        "candidate-evidence-3"
    assert identity_b["strategy"]["candidate_evidence_descriptor_version"] \
        == "candidate-evidence-descr-3"
    assert identity_b["strategy"]["rdkit_version"]
    assert identity_b["prediction"]["prompt_versions"]["proposals"] == \
        PROPOSALS_PROMPT_VERSION_V2
    # A 臂（证据 off，仍用 v2 prompt）
    model_a = ScriptedRealModelAdapter(strategy="first_pool",
                                       model_id="p2-v2-a")
    out_a = start_ppv1_run(
        config=resolve_config(), runs_root=runs_root, run_id="p2-v2-a",
        smiles="CCO", plan=_run_plan(spec), model=model_a,
        profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        evidence_card_enabled=False, evidence_card_version="v2")
    assert out_a["evidence_card_enabled"] is False
    assert out_a["evidence_card_version"] == "v2"
    assert model_a.seen_system_prompts == [proposals_system_prompt("v2")]
    payload_a = json.loads(model_a.seen_user_payloads[0])
    assert "substrate_evidence" not in payload_a
    assert "candidate_evidence_schema_version" not in payload_a
    assert "evidence" not in payload_a["pool_hypotheses"][0]
    # A 臂用户 JSON 与 v1 无证据路径同形（跨 run 的 hypothesis_id 含
    # parent_path_id，不能跨 run 比字节；字节等价由上面的
    # build_proposals_user_payload 单测与 off_path 证据脚本覆盖）。
    model_v1 = ScriptedRealModelAdapter(strategy="first_pool",
                                        model_id="p2-v1-a")
    start_ppv1_run(
        config=resolve_config(), runs_root=runs_root, run_id="p2-v1-a",
        smiles="CCO", plan=_run_plan(spec), model=model_v1,
        profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        evidence_card_enabled=False)
    payload_v1 = json.loads(model_v1.seen_user_payloads[0])
    assert set(payload_a) == set(payload_v1)
    assert "evidence" not in payload_a["pool_hypotheses"][0]
    assert "evidence" not in payload_v1["pool_hypotheses"][0]
    assert model_v1.seen_system_prompts == [_PROPOSALS_SYSTEM_PROMPT]
    identity_v1 = json.loads(
        (runs_root / "p2-v1-a" / "run_identity.json").read_text())
    assert "evidence_card_version" not in identity_v1["strategy"]
    assert "candidate_evidence_schema_version" not in \
        identity_v1["strategy"]
    assert "candidate_evidence_descriptor_version" not in \
        identity_v1["strategy"]
    assert "rdkit_version" not in identity_v1["strategy"]
    assert identity_v1["prediction"]["prompt_versions"]["proposals"] == \
        PROPOSALS_PROMPT_VERSION


def test_v1_default_summary_has_no_v2_keys(tmp_path) -> None:
    spec = _recorded_spec()
    model = ScriptedRealModelAdapter(strategy="first_pool",
                                     model_id="p2-v1-summary")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="p2-v1-summary", smiles="CCO", plan=_run_plan(spec),
        model=model, profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        evidence_card_enabled=False)
    assert "evidence_card_version" not in out
    assert out["evidence_card_enabled"] is False


def test_v2_resume_rejects_version_switch(tmp_path) -> None:
    spec = _recorded_spec()
    runs_root = tmp_path / "runs"
    model = ScriptedRealModelAdapter(strategy="first_pool",
                                     model_id="p2-v2-resume")
    start_ppv1_run(
        config=resolve_config(), runs_root=runs_root,
        run_id="p2-v2-resume", smiles="CCO", plan=_run_plan(spec),
        model=model, profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        evidence_card_enabled=True, evidence_card_version="v2")
    with pytest.raises(PPV1RunError) as excinfo:
        resume_ppv1_run(
            config=resolve_config(), runs_root=runs_root,
            run_id="p2-v2-resume", model=model,
            evidence_card_enabled=True)
    assert excinfo.value.detail.get("kind") == \
        "evidence_card_version_mismatch"
    # 带 v2 版本可正常 resume（身份一致）
    out = resume_ppv1_run(
        config=resolve_config(), runs_root=runs_root,
        run_id="p2-v2-resume", model=model,
        evidence_card_enabled=True, evidence_card_version="v2")
    assert out["evidence_card_version"] == "v2"
