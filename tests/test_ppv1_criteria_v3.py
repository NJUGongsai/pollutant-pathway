"""ppv1-criteria-v3 判分侧 T-D-A/B 披露轴回归(2026-10-19;E1b)。

生效口径:docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md
(§4.2 A-1..A-8 / §4.3 B-1..B-7 / §6 / §8 / §10)。全部夹具为合成
规则级:零金标、零真实 qid、零结构外带(规则常量 SMILES 为判据已
列名的合成对象);不外推 dev/298,不构成科学性能声明。

覆盖(E1b 验收矩阵 §3.2):
- 版本承载:常量/白名单/resolve/非法值三门同拒;v3 引擎不可用
  fail-closed 结构化拒;
- 指纹:四臂 param_sha256(实测默认值 + transforms 替代登记)与
  前置 1 登记逐臂一致;
- A 轴:默认臂/立体保留臂布尔独立、分开报数;档 A 只披露
  (match_status 不变、不进 strict);N1 型配对两臂全不相等;
  fail-closed 机读原因;
- B 轴:Uncharger 默认启用 + ChargeParent 并列敏感性;B-6 碳酸
  体系闭集机读排除(非"所有含碳对");净电荷差不得扩面;
- B-5:双轴布尔 + A→B 单归属 + 双满足计数;单归属断言;
- N4:S5A-01 封顶节点不适用(applicable=false,机读原因);
- 批级:分臂计数 + tautomer_promoted_nodes 恒空 + 参数指纹块;
- 正交:N3/N7 —— v3 与 v2 同 payload 的 V2 tier 计数/豁免披露
  逐位一致;v1/v2 输出字节不变(开工前冻结读数),v3 仅增量键;
- 判分透传:s5b_scoring 聚合附 criteria_v3 块。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    CRITERIA_V3_CARBONATE_EXCLUSION_REASON,
    CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT,
    CRITERIA_V3_PROTONATION_ARM_UNCHARGER,
    CRITERIA_V3_TAUTOMER_ARM_DEFAULT,
    CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING,
    EvaluationContractError,
    PPV1_CRITERIA_V1,
    PPV1_CRITERIA_V2,
    PPV1_CRITERIA_V3,
    PPV1_CRITERIA_VERSIONS,
    _criteria_v3_arm_registry,
    criteria_v3_aggregate_pair_blocks,
    criteria_v3_normalized_identity_pair,
    evaluate_scientific,
    match_reference_edges,
    match_reference_nodes,
    resolve_criteria_version,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_REFERENCE_GRAPH_VERSION,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    reference_graph_sha256,
    validate_reference_graph,
)

from test_ppv1_s5a_schema import (  # noqa: E402
    synth_evaluation_input,
    synth_split_manifest,
)

# ---- 合成规则常量(判据已列名的对象;零金标零真实 qid)----
L_ALA = "C[C@@H](N)C(=O)O"
D_ALA = "C[C@H](N)C(=O)O"
R_BUTANOL = "CC[C@@H](C)O"
S_BUTANOL = "CC[C@H](C)O"
ACID = "CC(=O)O"
ANION = "CC(=O)[O-]"
L_LACTIC = "C[C@@H](O)C(=O)O"
D_LACTATE = "C[C@H](O)C(=O)[O-]"
CARBONATE = "O=C([O-])[O-]"
BICARBONATE = "O=C(O)[O-]"
PRODUCT = "CC=O"
QID = "q-syn-v3"

# 开工前(HEAD 26ad119 源码树 ;2026-10-19)冻结的 v1/v2 读数(本文件
# 合成夹具逐字节;捕获脚本 e1b_pre_baseline_testfixture.py,产物
# reports/ppv1_s5b/t_de_e1_2026-10-19/e1_td_impl/
# e1b_pre_baseline_testfixture.json)
BASELINE_NODES_SHA256 = (
    "85337bc60de696a36e2069c247ec922b447fd8fafc48e094a0dba5ba023140bb")
BASELINE_EDGES_V1_SHA256 = (
    "58ff0ff8f82ccd2e9a640643002fde88d26f9ac84e0dff4beff40335cb4febec")
BASELINE_EDGES_V2_SHA256 = (
    "a467481322ff9a52a3b9c2c44c96f824dc9b8987f92ee3e406accecc76dcecc2")
BASELINE_EVAL_V1_SHA256 = (
    "8916afa8c8d2eb15ee2511963979484530eb68466813027dc51c6e7fa990b55f")
BASELINE_EVAL_V2_SHA256 = (
    "d1eb4aecc489215046deb8b2e893e619f2357c5e9545a3d5496a328838fcbeab")

_BASE = {
    "reference_graph_id": "rg-e1b",
    "schema_version": PPV1_REFERENCE_GRAPH_VERSION,
    "domain": "298",
    "track": "known_evidence_reconstruction",
    "edges": [
        {"edge_id": "e-1", "edge_status": "reference_only",
         "from_node_ids": ["n-root"], "to_node_ids": ["n-p1"],
         "participants": [
             {"node_id": "n-root", "role": "substrate", "side": "reactant",
              "coefficient": None, "coefficient_status": "unknown"},
             {"node_id": "n-p1", "role": "principal_product",
              "side": "product", "coefficient": None,
              "coefficient_status": "unknown"}],
         "step_scope": "net_reaction", "condition_requirements": [],
         "provenance_refs": ["pv-1"], "source_group_refs": ["sg-a"],
         "evidence_basis": "database_recorded_reaction",
         "scenario_scope": "rhea_generic_enzymology_no_scenario",
         "coefficient_status": "unknown",
         "participant_list_status": "partial",
         "transformation_ref": "rhea:1",
         "transformation_signature_status": "unknown"},
        {"edge_id": "e-2", "edge_status": "reference_only",
         "from_node_ids": ["n-root"], "to_node_ids": ["n-b1"],
         "participants": [
             {"node_id": "n-root", "role": "substrate", "side": "reactant",
              "coefficient": None, "coefficient_status": "unknown"},
             {"node_id": "n-b1", "role": "intermediate", "side": "product",
              "coefficient": None, "coefficient_status": "unknown"}],
         "step_scope": "net_reaction", "condition_requirements": [],
         "provenance_refs": ["pv-1"], "source_group_refs": ["sg-a"],
         "evidence_basis": "database_recorded_reaction",
         "scenario_scope": "rhea_generic_enzymology_no_scenario",
         "coefficient_status": "unknown",
         "participant_list_status": "partial",
         "transformation_ref": "rhea:2",
         "transformation_signature_status": "unknown"},
    ],
    "provenance_manifest": [{
        "provenance_id": "pv-1", "citation_ref": "cite-1",
        "evidence_basis": "database_recorded_reaction",
        "independent_status": "unknown",
        "observation_scope": "recorded_only",
        "source_conditions": [], "source_group_id": "sg-a",
        "source_origin": "database",
        "structure_match_scope": "strict_structure"}],
    "source_groups": [{
        "source_group_id": "sg-a", "member_records": ["rec-1"],
        "independence_status": "unknown",
        "note": "synthetic rule-level fixture"}],
    "split_assignment": {"split": "development",
                         "route_group_keys": ["rg-e1b"],
                         "split_rule_version": "split-rule-1"},
    "coverage_statement": {"covered_axes": ["exact_edges"], "known_gaps": [],
                           "not_evaluable_edge_ids": [],
                           "not_evaluable_node_ids": []},
    "endpoint_annotations": [],
    "creation_review": {"review_status": "pending_user_teacher_review",
                        "reviewer": "synthetic-fixture",
                        "note": "synthetic rule-level fixture"},
}

# (node_id, structure_smiles, structure_identity_scope, role)
_NODES = (
    ("n-root", L_ALA, "strict_structure", "root"),
    ("n-p1", PRODUCT, "strict_structure", "principal_product"),
    ("n-b1", ACID, "strict_structure", "intermediate"),
    # S5A-01 封顶节点(N4):cn_only 内容状态在场
    ("n-cap", L_ALA, "cn_only", "intermediate"),
    # N1 型配对:两臂全不相等(远程 sp3 手性,互变算子不触及)
    ("n-iso", R_BUTANOL, "strict_structure", "intermediate"),
    # B-6 碳酸体系闭集配对(单一配对排除)
    ("n-carb", CARBONATE, "strict_structure", "intermediate"),
)

# (state_id, smiles)
_STATES = (
    ("cs-sub", D_ALA),          # A 轴:仅默认臂相等(P1 型)
    ("cs-prod", PRODUCT),       # strict 命中
    ("cs-b", ANION),            # B 轴:Uncharger 相等(P2 型)
    ("cs-cap", D_ALA),          # 封顶节点 cn_only
    ("cs-iso", S_BUTANOL),      # N1 型:两臂均不相等
    ("cs-carb", BICARBONATE),   # B-6 闭集排除
    ("cs-chg", D_LACTATE),      # B-3 负控:净电荷差异 + 立体差,不授
)


def _build_graph() -> dict:
    graph = json.loads(json.dumps(_BASE))
    nodes = []
    for node_id, smi, scope, role in _NODES:
        nodes.append({
            "node_id": node_id, "state_identity": f"strict:{smi}",
            "structure_smiles": smi, "structure_identity_scope": scope,
            "role": role, "occurrence_id": f"occ-{node_id}",
            "source_group_refs": ["sg-a"], "condition_scope": [],
            "provenance_refs": ["pv-1"], "node_status": "observed"})
    graph["nodes"] = nodes
    edge = graph["edges"][0]
    for node_id, _smi, _scope, _role in _NODES[2:]:
        edge["to_node_ids"].append(node_id)
        edge["participants"].append({
            "node_id": node_id, "role": "coproduct", "side": "product",
            "coefficient": None, "coefficient_status": "unknown"})
    graph["root_entity"] = {
        "entity_id": "ent-1", "structure_smiles_raw": L_ALA,
        "strict_structure_identity": L_ALA, "source_refs": [QID],
        "formal_charge": 0, "isotope_information_status": "unknown",
        "stereo_information_status": "unknown"}
    validate_reference_graph(graph)
    return graph


def _participant(state_id: str, side: str, role: str, seq: int) -> dict:
    return {"state_ref": state_id, "side": side, "role": role,
            "coefficient": None, "coefficient_status": "unknown",
            "entry_id": f"pe-{seq}", "merged_from": [],
            "parallel_contribution": False}


def _build_payload() -> dict:
    participants = [
        _participant("cs-sub", "reactant", "primary_substrate", 1),
        _participant("cs-prod", "product", "principal_product", 2),
    ]
    for seq, (state_id, _smi) in enumerate(_STATES[2:], start=3):
        participants.append(_participant(state_id, "reactant",
                                         "cosubstrate", seq))
    return {
        "run_id": "r-e1b",
        "states": [{"state_id": state_id,
                    "payload": {"smiles_isomeric": smi,
                                "cn_identity": cn_identity(smi)}}
                   for state_id, smi in _STATES],
        "events": [{"event_id": "ppev-1", "hypothesis_id": "hyp-1",
                    "payload": json.dumps({
                        "schema_version": "ppv1-event-8",
                        "participants": participants,
                        "participant_state_refs": [
                            p["state_ref"] for p in participants]})}],
        "hypotheses": [{"hypothesis_id": "hyp-1", "payload": json.dumps({
            "schema_version": "ppv1-hypothesis-8",
            "step_scope": "net_reaction", "provenance_refs": []})}],
        "provenance_records": [],
    }


def _node_block(nodes: list[dict], node_id: str) -> dict:
    for entry in nodes:
        if entry["node_id"] == node_id:
            return entry.get("criteria_v3_normalized_identity") or {}
    raise AssertionError(f"node not found: {node_id}")


def _pair_of(node_block: dict, state_id: str) -> dict:
    for pair in node_block.get("axis_pairs") or []:
        if pair.get("state_id") == state_id:
            return pair
    raise AssertionError(f"pair not found: {state_id}")


def _evaluation_input(graph: dict) -> dict:
    inp = synth_evaluation_input(
        domain="298", graphs=[graph],
        split_manifest=synth_split_manifest(
            graph_id=graph["reference_graph_id"], group_ids=["sg-a"]),
        exports=[{"run_id": "r-e1b", "export_digest": "d" * 32,
                  "qid": QID, "lossy_projection": False}])
    inp["run_identity"]["run_id"] = "r-e1b"
    inp["reference_graph_manifest"] = [{
        "reference_graph_id": graph["reference_graph_id"],
        "sha256": reference_graph_sha256(graph), "domain": "298",
        "track": "known_evidence_reconstruction", "qid": QID}]
    return inp


def _fake_reader_factory(payload: dict):
    blob = json.dumps(payload)

    def reader(entry):  # noqa: ARG001 —— 合成读取通道
        return {"payload": json.loads(blob)}

    return reader


def _canonical_json_sha256(obj) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(
        obj, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 版本承载

def test_criteria_v3_constants_and_resolve() -> None:
    """常量/白名单/resolve:v3 显式启用;非法值结构化拒。"""
    assert PPV1_CRITERIA_V3 == "ppv1-criteria-v3"
    assert PPV1_CRITERIA_VERSIONS == {PPV1_CRITERIA_V1, PPV1_CRITERIA_V2,
                                      PPV1_CRITERIA_V3}
    for version in sorted(PPV1_CRITERIA_VERSIONS):
        assert resolve_criteria_version(version) == version
    with pytest.raises(EvaluationContractError) as excinfo:
        resolve_criteria_version("ppv1-criteria-v9")
    assert excinfo.value.detail["kind"] == "criteria_version_invalid"
    assert excinfo.value.detail["allowed"] == sorted(PPV1_CRITERIA_VERSIONS)


def test_criteria_v3_engine_unavailable_fail_closed(monkeypatch) -> None:
    """v3 请求而 RDKit 引擎/指纹不可得 ⇒ 结构化拒(不降级、不留空指纹)。"""
    import pathway_v43.pollutant.evaluation as ev

    monkeypatch.setattr(
        ev, "_criteria_v3_arm_registry",
        lambda: {"available": False,
                 "unavailable_reason": "synthetic_unavailable"})
    with pytest.raises(EvaluationContractError) as excinfo:
        ev.resolve_criteria_version(PPV1_CRITERIA_V3)
    assert excinfo.value.detail["kind"] == "criteria_v3_engine_unavailable"
    assert excinfo.value.detail["unavailable_reason"] == \
        "synthetic_unavailable"


def test_criteria_v3_arm_fingerprints_and_registered_defaults() -> None:
    """四臂 param_sha256 + 实测默认值 + transforms 替代登记(与前置 1
    逐臂一致;参数拼写按 RDKit CleanupParameters 官方名)。"""
    registry = _criteria_v3_arm_registry()
    assert registry["available"] is True
    arms = registry["arms"]
    expected = {
        CRITERIA_V3_TAUTOMER_ARM_DEFAULT:
            "fa4c6a42650e8b9cd39e669293b1697cfc0425f92ba2492080ca454e80f38f1f",
        CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING:
            "56e413406f62ef3af960a8b8cf1a3a17367530383344ce02acc16ac7e87f5ce7",
        CRITERIA_V3_PROTONATION_ARM_UNCHARGER:
            "b059fe221c28ae8ecf4390d0f10f60907b062440b840713733871977c106ac20",
        CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT:
            "7e88e6136bfd158e6ff34db3553c6cb624e9ac899208eb92a1f16987fb4720bf",
    }
    for arm, sha in expected.items():
        assert arms[arm]["param_sha256"] == sha, arm
    default_params = arms[CRITERIA_V3_TAUTOMER_ARM_DEFAULT]["params"]
    # 实测默认值(未显式设置项不得遗漏)
    assert default_params["maxTransforms"] == 1000
    assert default_params["maxTautomers"] == 1000
    assert default_params["tautomerRemoveSp3Stereo_effective"] is True
    assert default_params["tautomerRemoveBondStereo_effective"] is True
    assert default_params["tautomerRemoveIsotopicHs_effective"] is True
    assert default_params["tautomerReassignStereo_effective"] is True
    assert default_params["maxRestarts_effective"] == 200
    keep_params = arms[CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING]["params"]
    assert keep_params["tautomerRemoveSp3Stereo_effective"] is False
    assert keep_params["tautomerRemoveBondStereo_effective"] is True
    # 双臂差异逐项 diff(单列登记)
    assert registry["dual_arm_diff"]["tautomerRemoveSp3Stereo_effective"] == {
        "default": True, "stereo_preserving": False}
    # transforms 替代登记:本构建无 tautomerTransforms.in ⇒ 原子库 sha256
    env = registry["environment"]
    assert "absent" in env["tautomerTransforms_file"]
    assert env["libRDKitMolStandardize_sha256"]
    assert env["rdMolStandardize_so_sha256"]
    # 碳酸体系闭集:三物种经同算子落回两规范形;指纹入册
    carbonate = registry["carbonate_system"]
    assert carbonate["normalized_forms_sorted"] == ["O=C(O)O", "O=C=O"]
    assert carbonate["sha256"]


def test_criteria_v3_rejected_at_node_and_edge_gates() -> None:
    """机器挡板:非法值在节点/边匹配入口同样结构化拒(同一 resolve)。"""
    graph = _build_graph()
    payload = _build_payload()
    with pytest.raises(EvaluationContractError) as exc1:
        match_reference_nodes(graph, payload,
                              criteria_version="ppv1-criteria-v9")
    assert exc1.value.detail["kind"] == "criteria_version_invalid"
    nodes = match_reference_nodes(graph, payload)
    with pytest.raises(EvaluationContractError) as exc2:
        match_reference_edges(graph, payload, nodes,
                              criteria_version="ppv1-criteria-v9")
    assert exc2.value.detail["kind"] == "criteria_version_invalid"


# ---------------------------------------------------------------- A 轴

def test_v3_a_axis_two_arms_separate_and_disclosure_only() -> None:
    """A 轴(P1 型:仅默认臂相等):双臂布尔独立保存、分开报数;档 A
    只披露 —— match_status 不变(cn_only)、不产 strict 提升。"""
    graph = _build_graph()
    payload = _build_payload()
    nodes_v3 = match_reference_nodes(graph, payload,
                                     criteria_version=PPV1_CRITERIA_V3)
    root = next(e for e in nodes_v3 if e["node_id"] == "n-root")
    assert root["match_status"] == "cn_only"  # 判分侧互变归一禁改
    assert "identity_scope_cap" not in root
    block = root["criteria_v3_normalized_identity"]
    assert block["tier"] == "disclosure_only"
    assert block["applicable"] is True
    assert block["strict_promotion"] is False
    assert block["tautomer_promoted_nodes"] == []
    pair = _pair_of(block, "cs-sub")
    tautomer = pair["tautomer"]
    assert tautomer["normalized_identity_axis_default"] is True
    assert tautomer["normalized_identity_axis_stereo_preserving"] is False
    assert tautomer["any_arm_granted"] is True
    assert tautomer["strict_promotion"] is False
    default_arm = tautomer["arms"][CRITERIA_V3_TAUTOMER_ARM_DEFAULT]
    keep_arm = tautomer["arms"][
        CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING]
    assert default_arm["tautomer_arm"] == "default"
    assert default_arm["normalization_source"] == \
        "tautomer_enumerator_default_v1"
    assert default_arm["strict_eligible"] is False  # 敏感性披露臂
    assert keep_arm["tautomer_arm"] == "stereo_preserving"
    assert keep_arm["normalization_source"] == \
        "tautomer_enumerator_stereo_preserving_v1"
    assert keep_arm["tier_b_status"] == "locked_not_unlocked_this_round"
    assert default_arm["tautomer_param_sha256"] != \
        keep_arm["tautomer_param_sha256"]
    assert pair["single_attribution"] == "tautomer"
    assert pair["original_match_status"] == "cn_only"
    assert pair["strict_promotion"] is False
    counts = block["axis_pair_counts"]
    # n-root 的 cn_only 配对 = {cs-sub, cs-cap}(两者均为同一手性变体
    # 结构)⇒ 默认臂相等计数 2;n-cap 为封顶节点(不适用)
    assert counts["tautomer_normalized_pairs_default"] == 2
    assert counts["tautomer_normalized_pairs_stereo_preserving"] == 0
    assert counts["strict_promoted_pairs"] == 0


def test_v3_n1_isomer_pair_not_granted_both_arms() -> None:
    """N1 型负控(远程 sp3 手性):两臂均不授 ⇒ 单归属 none;
    防"立体擦除冒充互变救回"。"""
    pair = criteria_v3_normalized_identity_pair(R_BUTANOL, S_BUTANOL)
    assert pair["tautomer"]["normalized_identity_axis_default"] is False
    assert pair["tautomer"][
        "normalized_identity_axis_stereo_preserving"] is False
    assert pair["tautomer"]["any_arm_granted"] is False
    assert pair["protonation"]["any_arm_granted"] is False
    assert pair["single_attribution"] == "none"
    assert pair["double_satisfied"] is False


def test_v3_fail_closed_unparseable_reasons() -> None:
    """fail-closed:不可解析 ⇒ 不授归一相等 + 逐臂机读原因(无第三态)。"""
    pair = criteria_v3_normalized_identity_pair(
        L_ALA, "not-a-smiles[")
    assert pair["tautomer"]["any_arm_granted"] is False
    assert pair["protonation"]["any_arm_granted"] is False
    for arm_row in pair["tautomer"]["arms"].values():
        assert arm_row["normalized_identity_axis"] is False
    reason = pair["tautomer"]["arms"][
        CRITERIA_V3_TAUTOMER_ARM_DEFAULT]["reason"]
    assert reason == "structure_unparseable"
    assert pair["single_attribution"] == "none"


def test_v3_n4_s5a01_cap_not_crossed() -> None:
    """N4:S5A-01 封顶节点(scope=cn_only)即使有 cn_only 配对也
    applicable=false(机读原因)且封顶披露保持。"""
    graph = _build_graph()
    payload = _build_payload()
    nodes_v3 = match_reference_nodes(graph, payload,
                                     criteria_version=PPV1_CRITERIA_V3)
    capped = next(e for e in nodes_v3 if e["node_id"] == "n-cap")
    assert capped["match_status"] == "cn_only"
    assert capped["reference_identity_scope"] == "cn_only"
    block = capped["criteria_v3_normalized_identity"]
    assert block["applicable"] is False
    assert block["not_applicable_reason"] == "identity_scope_cap"
    assert block["axis_pairs"] == []
    assert block["strict_promotion"] is False
    # 合法 strict 节点(v3 同 payload)不受影响;封顶节点不进严格档
    strict_nodes = match_reference_nodes(
        graph, payload, criteria_version=PPV1_CRITERIA_V3)
    assert all(e["match_status"] != "strict_structure"
               or e["node_id"] == "n-p1" for e in strict_nodes)
    root = next(e for e in strict_nodes if e["node_id"] == "n-root")
    assert root["match_status"] == "cn_only"


# ---------------------------------------------------------------- B 轴

def test_v3_b_axis_uncharger_default_charge_parent_sensitivity() -> None:
    """B 轴(P2 型 酸/盐):Uncharger 默认启用臂 + ChargeParent 并列
    敏感性臂分开报数;单归属 protonation。"""
    pair = criteria_v3_normalized_identity_pair(ACID, ANION)
    protonation = pair["protonation"]
    assert protonation["enabled_arm"] == "uncharger"
    uncharger = protonation["arms"][CRITERIA_V3_PROTONATION_ARM_UNCHARGER]
    charge_parent = protonation["arms"][
        CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT]
    assert uncharger["enabled"] is True
    assert uncharger["sensitivity_only"] is False
    assert uncharger["normalized_identity_axis_uncharger"] is True
    assert uncharger["normalization_source"] == "uncharger_default_v1"
    assert charge_parent["enabled"] is False
    assert charge_parent["sensitivity_only"] is True
    assert charge_parent["normalization_source"] == "charge_parent_v1"
    assert pair["tautomer"]["any_arm_granted"] is False  # 质子化不冒充互变
    assert pair["single_attribution"] == "protonation"
    assert pair["protonation"]["strict_promotion"] is False


def test_v3_b3_net_charge_difference_not_granted() -> None:
    """B-3:归一后仍不相等且净电荷不同(0 vs -1)⇒ 不授质子化轴;
    禁"净电荷对齐"扩面(不得引入电荷对齐策略来扩面)。"""
    pair = criteria_v3_normalized_identity_pair(L_LACTIC, D_LACTATE)
    protonation = pair["protonation"]
    assert protonation["any_arm_granted"] is False
    assert not any(
        row["normalized_identity_axis"] for row in
        protonation["arms"].values())
    assert protonation["carbonate_system_exclusion"] is False
    assert pair["single_attribution"] == "none"
    assert pair["double_satisfied"] is False


def test_v3_b6_carbonate_closed_set_exclusion() -> None:
    """B-6:碳酸体系闭集两侧命中 ⇒ 逐对象排除 + 机读原因;闭集外
    含碳对(乙酸/乙酸根)不受排除(防"所有含碳对"误读)。"""
    pair = criteria_v3_normalized_identity_pair(CARBONATE, BICARBONATE)
    protonation = pair["protonation"]
    assert protonation["carbonate_system_exclusion"] is True
    assert protonation["exclusion_reason"] == \
        CRITERIA_V3_CARBONATE_EXCLUSION_REASON
    for row in protonation["arms"].values():
        assert row["normalized_identity_axis"] is False
        assert row["reason"] == CRITERIA_V3_CARBONATE_EXCLUSION_REASON
    assert protonation["any_arm_granted"] is False
    assert pair["single_attribution"] == "none"
    # 闭集外含碳对正控:不得被排除
    control = criteria_v3_normalized_identity_pair(ACID, ANION)
    assert control["protonation"]["carbonate_system_exclusion"] is False
    assert control["protonation"]["exclusion_reason"] is None


# ---------------------------------------------------------------- B-5 单归属

def test_v3_b5_single_attribution_and_double_satisfied_counting() -> None:
    """B-5:双轴布尔 + A→B 单归属 + 双满足计数(披露,不静默吞);
    单归属断言(标签和 == 配对数,无第三态)。"""
    a_only = criteria_v3_normalized_identity_pair(L_ALA, D_ALA)
    b_only = criteria_v3_normalized_identity_pair(ACID, ANION)
    none_pair = criteria_v3_normalized_identity_pair(R_BUTANOL, S_BUTANOL)
    # 双满足(合成披露块:直接构造,证明计数非恒零死码)
    double = json.loads(json.dumps(a_only))
    double["protonation"]["any_arm_granted"] = True
    double["protonation"]["arms"][
        CRITERIA_V3_PROTONATION_ARM_UNCHARGER][
        "normalized_identity_axis"] = True
    double["protonation"]["arms"][
        CRITERIA_V3_PROTONATION_ARM_UNCHARGER][
        "normalized_identity_axis_uncharger"] = True
    double["double_satisfied"] = True
    double["single_attribution"] = "tautomer"
    counts = criteria_v3_aggregate_pair_blocks(
        [a_only, b_only, none_pair, double])
    assert counts["pairs_total"] == 4
    assert counts["single_attribution_counts"] == {
        "tautomer": 2, "protonation": 1, "none": 1}
    assert counts["double_satisfied_pairs"] == 1
    assert counts["strict_promoted_pairs"] == 0
    assert sum(counts["single_attribution_counts"].values()) == \
        counts["pairs_total"]
    # 单归属断言:非法标签 ⇒ 立即失败(不静默)
    bad = json.loads(json.dumps(a_only))
    bad["single_attribution"] = "aromatic"
    with pytest.raises(AssertionError):
        criteria_v3_aggregate_pair_blocks([bad])


# ---------------------------------------------------------------- 正交/不变

def test_v1_v2_byte_invariance_and_v3_increment_only() -> None:
    """缺省 v1 字节不变 / 显式 v2 行为不变(开工前冻结读数);v3 只在
    节点条目增量新键(criteria_v3_normalized_identity)。"""
    graph = _build_graph()
    payload = _build_payload()
    nodes_v1 = match_reference_nodes(graph, payload)
    nodes_v2 = match_reference_nodes(graph, payload,
                                     criteria_version=PPV1_CRITERIA_V2)
    nodes_v3 = match_reference_nodes(graph, payload,
                                     criteria_version=PPV1_CRITERIA_V3)
    assert _canonical_json_sha256(nodes_v1) == BASELINE_NODES_SHA256
    assert _canonical_json_sha256(nodes_v2) == BASELINE_NODES_SHA256
    assert "criteria_v3" not in json.dumps(nodes_v1)
    # v3 = v1 投影(去掉 v3 新键后逐字节相等)
    stripped = json.loads(json.dumps(nodes_v3))
    for entry in stripped:
        entry.pop("criteria_v3_normalized_identity", None)
    assert _canonical_json_sha256(stripped) == BASELINE_NODES_SHA256

    edges_v1 = match_reference_edges(graph, payload, nodes_v1,
                                     criteria_version=PPV1_CRITERIA_V1)
    edges_v2 = match_reference_edges(graph, payload, nodes_v1,
                                     criteria_version=PPV1_CRITERIA_V2)
    assert _canonical_json_sha256(edges_v1) == BASELINE_EDGES_V1_SHA256
    assert _canonical_json_sha256(edges_v2) == BASELINE_EDGES_V2_SHA256

    reader = _fake_reader_factory(payload)
    eval_input = _evaluation_input(graph)
    out_v1 = evaluate_scientific(
        json.loads(json.dumps(eval_input)),
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader, criteria_version=PPV1_CRITERIA_V1)
    out_v2 = evaluate_scientific(
        json.loads(json.dumps(eval_input)),
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader, criteria_version=PPV1_CRITERIA_V2)
    assert out_v1["output_sha256"] == BASELINE_EVAL_V1_SHA256
    assert out_v2["output_sha256"] == BASELINE_EVAL_V2_SHA256
    assert "criteria_v3" not in out_v1 and "criteria_v2" not in out_v1
    assert "criteria_v3" not in out_v2


def test_v3_orthogonality_v2_tier_counts_identical_same_payload() -> None:
    """N3/N7 正交性:v3 承载 v2 判分语义 —— 同 payload 下 v2 与 v3 的
    逐边 tier 计数/豁免披露与批级 criteria_v2 块逐位一致。"""
    graph = _build_graph()
    payload = _build_payload()
    nodes = match_reference_nodes(graph, payload)
    edges_v2 = match_reference_edges(graph, payload, nodes,
                                     criteria_version=PPV1_CRITERIA_V2)
    edges_v3 = match_reference_edges(graph, payload, nodes,
                                     criteria_version=PPV1_CRITERIA_V3)
    assert _canonical_json_sha256(edges_v2) == \
        _canonical_json_sha256(edges_v3)
    assert [e["criteria_v2_tier_counts"] for e in edges_v2] == \
        [e["criteria_v2_tier_counts"] for e in edges_v3]
    assert json.dumps(edges_v3).count("criteria_v3_normalized_identity") == 0

    reader = _fake_reader_factory(payload)
    eval_input = _evaluation_input(graph)
    out_v2 = evaluate_scientific(
        json.loads(json.dumps(eval_input)),
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader, criteria_version=PPV1_CRITERIA_V2)
    out_v3 = evaluate_scientific(
        json.loads(json.dumps(eval_input)),
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader, criteria_version=PPV1_CRITERIA_V3)
    assert out_v3["criteria_v2"] == out_v2["criteria_v2"]


# ---------------------------------------------------------------- 批级

def test_v3_batch_block_counts_and_empty_promoted_nodes() -> None:
    """批级 criteria_v3:分臂分列计数 + 单归属 + 恒空
    tautomer_promoted_nodes + 参数指纹登记 + 档 A 措辞。"""
    graph = _build_graph()
    payload = _build_payload()
    out = evaluate_scientific(
        _evaluation_input(graph),
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_fake_reader_factory(payload),
        criteria_version=PPV1_CRITERIA_V3)
    block = out["criteria_v3"]
    assert block["criteria_version"] == PPV1_CRITERIA_V3
    assert block["tier"] == "disclosure_only"
    assert block["strict_promotion"] is False
    assert block["hit_at_1_effect"] == "none"
    assert block["tautomer_promoted_nodes"] == []
    assert block["tautomer_normalized_pairs_default"] == 2
    # (n-root 的两个 cn_only 状态:cs-sub/cs-cap 均为同构手性变体)
    assert block["tautomer_normalized_pairs_stereo_preserving"] == 0
    assert block["protonation_normalized_pairs_uncharger"] == 1
    assert block["protonation_normalized_pairs_charge_parent"] == 1
    assert block["carbonate_system_excluded_pairs"] == 1
    assert block["carbonate_system_exclusion_reason"] == \
        CRITERIA_V3_CARBONATE_EXCLUSION_REASON
    assert sum(block["single_attribution_counts"].values()) == \
        block["axis_pairs_total"]
    assert "strict_promoted_pairs" not in block  # 批级不另立第三态键
    assert block["strict_promotion"] is False
    assert block["axis_nodes_not_applicable"] >= 1
    registry = block["param_registry"]
    assert set(registry["arms"]) == {
        CRITERIA_V3_TAUTOMER_ARM_DEFAULT,
        CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING,
        CRITERIA_V3_PROTONATION_ARM_UNCHARGER,
        CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT}
    assert registry["environment"]["rdkit_version"]
    assert "AROMATIC-REPR=0" in block["aromatic_repr_note"]
    assert "单批不宣称稳定" in block["single_batch_note"]
    # 判分侧 strict 指标零改动:样本 match_status 与 v1 全等
    out_v1 = evaluate_scientific(
        _evaluation_input(graph),
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_fake_reader_factory(payload),
        criteria_version=PPV1_CRITERIA_V1)
    for sample_v3, sample_v1 in zip(out["sample_results"],
                                    out_v1["sample_results"]):
        statuses_v3 = [(e["node_id"], e["match_status"])
                       for e in sample_v3["predicted_node_matches"]]
        statuses_v1 = [(e["node_id"], e["match_status"])
                       for e in sample_v1["predicted_node_matches"]]
        assert statuses_v3 == statuses_v1
        edges_v3 = [(e["edge_id"], e["match_status"])
                    for e in sample_v3["predicted_edge_matches"]]
        edges_v1 = [(e["edge_id"], e["match_status"])
                    for e in sample_v1["predicted_edge_matches"]]
        assert edges_v3 == edges_v1


# ---------------------------------------------------------------- 判分透传

def test_scoring_aggregate_carries_criteria_v3(tmp_path) -> None:
    """s5b_scoring 聚合透传 criteria_v3 块(v1/v2 缺省零新键)。"""
    from pathway_v43.pollutant.s5b_scoring import score_s5b_batch
    import pathway_v43.pollutant.s5b_scoring as scoring
    from test_ppv1_s5b_hit50_v3_wv6 import (  # noqa: E402
        GRAPH_ID,
        _APPROVED,
        _minimal_batch_root,
    )

    batch_root = _minimal_batch_root(tmp_path)

    def _fake_output(extra_block: bool) -> dict:
        out = {"status": "pending_user_teacher_decision",
               "sample_results": [],
               "coverage_report": {"pairing": {
                   "bases_by_graph": {GRAPH_ID: "qid_strict"}}}}
        if extra_block:
            out["criteria_v3"] = {"criteria_version": PPV1_CRITERIA_V3,
                                  "tautomer_promoted_nodes": []}
            out["criteria_v2"] = {"criteria_version": PPV1_CRITERIA_V2,
                                  "tier_counts": {}}
        return out

    real_evaluate = scoring.evaluate_scientific
    try:
        scoring.evaluate_scientific = \
            lambda evaluation_input, **kwargs: _fake_output(True)
        agg_v3 = score_s5b_batch(
            batch_root, runs_root=tmp_path / "runs",
            data_scope="synthetic_rule_level",
            preregistration=dict(_APPROVED),
            criteria_version=PPV1_CRITERIA_V3)
        metrics_v3 = json.loads(
            (batch_root / "metrics.json").read_text(encoding="utf-8"))
        scoring.evaluate_scientific = \
            lambda evaluation_input, **kwargs: _fake_output(False)
        agg_v1 = score_s5b_batch(
            batch_root, runs_root=tmp_path / "runs",
            data_scope="synthetic_rule_level",
            preregistration=dict(_APPROVED),
            criteria_version=PPV1_CRITERIA_V1)
    finally:
        scoring.evaluate_scientific = real_evaluate
    assert agg_v3["criteria_v3"]["criteria_version"] == PPV1_CRITERIA_V3
    assert agg_v3["criteria_v2"]["criteria_version"] == PPV1_CRITERIA_V2
    assert metrics_v3["criteria_v3"]["criteria_version"] == PPV1_CRITERIA_V3
    assert "criteria_v3" not in agg_v1
    assert "criteria_v2" not in agg_v1


def test_scoring_rejects_invalid_criteria_version(tmp_path) -> None:
    """判分入口同一 resolve 判据:非法值结构化拒(先于批装载)。"""
    from pathway_v43.pollutant.s5b_scoring import score_s5b_batch
    with pytest.raises(RuntimeError) as excinfo:
        score_s5b_batch("/nonexistent-batch-root",
                        runs_root="/nonexistent-runs",
                        criteria_version="ppv1-criteria-v9")
    assert "criteria_version 非法" in str(excinfo.value)