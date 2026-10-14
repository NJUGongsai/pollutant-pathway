"""ppv1-criteria-v2 判分面 T-1 豁免回归(2026-10-13;teacher T-1 裁定
b 档 + mimo r36 九条件 + CS2c 补证 N1''=13)。

预注册:docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md
(状态 preregistration_pending_final_confirmation)。全部夹具为合成
规则级:零金标、零真实 qid、零结构外带(豁免四类 SMILES 为裁定已
列名的规则常量);不外推 dev/298,不构成科学性能声明。

覆盖(任务书 §3.3 六形态 + 单归属 + 计数监控):
- 常量与机器挡板:豁免四类 cn 收敛 + 版本化哈希;豁免身份 ∩
  COMPLETION_LICENSED_IDENTITIES = ∅;含碳禁入(零碳断言);辅因子
  硬拒绝表(NAD/ATP/NH₃/O₂/H₂O₂/CN⁻ 等不入豁免集,负控钉死);
- 正控:已声明水豁免升 strict(逐边 exempted_participants 披露:
  身份哈希/族/侧/角色/tier/谓词三布尔);H⁺ 产物侧豁免(H⁺ 无 O/P
  ⇒ not_applicable 记过);PPi 带 P/O 追溯豁免(r28 A6 半套簿记
  防线正控);
- 负控:无中生水(pred2 拦截:反应物 O=0 而产物豁免水);Pi 反应物
  侧不豁(方向限定,mimo r36 条件 1);NAD 挂名不洗;NH₃/O₂ 机制类
  不豁;未声明多余产物维持 partial(T1′ 未实施 ⇒ 明字);声明链缺席
  /悬空/不可解析 ⇒ unknown = fail-closed;侧别翻转不豁(身份+侧+
  角色绑定);角色不符不豁;
- 单归属:混合 extras 逐实例恰一个 tier(v1_exempt /
  not_exempt_maintains_partial),事件不升 exact;
- H⁺/[H]/[H][H] 三分无合流 + strict(H⁺) ∉ 许可集;
- 字节不变:缺省 v1 输出与显式 v1 输出全等且零新键(豁免关);非法
  criteria_version 结构化拒(评测器/边匹配/判分入口三门);
- 批级:v2 输出 criteria_v2 汇总(豁免计数 + 参考侧 v1 身份监控,
  应为 0;非 0 = 退出条件信号 EXIT_CONDITION_SIGNAL_nonzero);
  v1 输出零 criteria_v2 键;参考图声明豁免身份 ⇒ 退出信号触发。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.pollutant.audit import (  # noqa: E402
    COMPLETION_LICENSED_IDENTITIES,
)
from pathway_v43.pollutant.chemstate import strict_identity_of  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    CRITERIA_TIERS,
    CRITERIA_TIER_NOT_EXEMPT,
    CRITERIA_TIER_V1_EXEMPT,
    CRITERIA_T1P_NOT_IMPLEMENTED_NOTE,
    CRITERIA_V2_NEVER_EXEMPT_FAMILIES,
    EvaluationContractError,
    PPV1_CRITERIA_V1,
    PPV1_CRITERIA_V2,
    PPV1_CRITERIA_VERSIONS,
    evaluate_participant_exemption,
    evaluate_scientific,
    match_reference_edges,
    match_reference_nodes,
    resolve_criteria_version,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_REFERENCE_GRAPH_VERSION,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    validate_reference_graph,
)
from test_ppv1_s5a_schema import (  # noqa: E402
    synth_evaluation_input,
    synth_split_manifest,
)

# ---- 豁免四类代表结构(规则常量,裁定已列名;质子化变体组照抄
# CS2c 补证脚本 V1_VARIANTS) ----
WATER = "O"
H_PLUS = "[H+]"
PI = "OP(=O)(O)O"
PPI = "O=P(O)(O)OP(=O)(O)O"

_SUB_2P = "CCOP(=O)(O)OP(=O)(O)OCC"  # 合成 2P/7O 底物(PPi 追溯正控用)


# ---------------------------------------------------------------- 夹具

_BASE_GRAPH_FIELDS = {
    "reference_graph_id": "rg-crit2",
    "schema_version": PPV1_REFERENCE_GRAPH_VERSION,
    "domain": "298",
    "track": "known_evidence_reconstruction",
    "edges": [{
        "edge_id": "e-1",
        "edge_status": "reference_only",
        "from_node_ids": ["n-root"],
        "to_node_ids": ["n-p1"],
        "participants": [
            {"node_id": "n-root", "role": "substrate", "side": "reactant",
             "coefficient": None, "coefficient_status": "unknown"},
            {"node_id": "n-p1", "role": "principal_product", "side": "product",
             "coefficient": None, "coefficient_status": "unknown"},
        ],
        "step_scope": "net_reaction",
        "condition_requirements": [],
        "provenance_refs": ["pv-1"],
        "source_group_refs": ["sg-a"],
        "evidence_basis": "database_recorded_reaction",
        "scenario_scope": "rhea_generic_enzymology_no_scenario",
        "coefficient_status": "unknown",
        "participant_list_status": "partial",
        "transformation_ref": "rhea:1",
        "transformation_signature_status": "unknown",
    }],
    "provenance_manifest": [{
        "provenance_id": "pv-1",
        "citation_ref": "cite-1",
        "evidence_basis": "database_recorded_reaction",
        "independent_status": "unknown",
        "observation_scope": "recorded_only",
        "source_conditions": [],
        "source_group_id": "sg-a",
        "source_origin": "database",
        "structure_match_scope": "strict_structure",
    }],
    "source_groups": [{
        "source_group_id": "sg-a",
        "member_records": ["rec-1"],
        "independence_status": "unknown",
        "note": "synthetic rule-level fixture(零金标零真实 qid)",
    }],
    "split_assignment": {"split": "development",
                         "route_group_keys": ["rg-crit2"],
                         "split_rule_version": "split-rule-1"},
    "coverage_statement": {"covered_axes": ["exact_edges"],
                           "known_gaps": [],
                           "not_evaluable_edge_ids": [],
                           "not_evaluable_node_ids": []},
    "endpoint_annotations": [],
    "creation_review": {
        "review_status": "pending_user_teacher_review",
        "reviewer": "synthetic-fixture",
        "note": "synthetic rule-level fixture",
    },
}


def _make_graph(root_smi: str, prod_smi: str, *,
                extra_product_nodes: tuple[tuple[str, str], ...] = ()) -> dict:
    """合成参考图(经冻结 schema 校验;extra_product_nodes = (node_id,
    smiles) 附加产物节点并接进边端点 —— 参考侧监控测试用)。"""
    graph = json.loads(json.dumps(_BASE_GRAPH_FIELDS))
    graph["nodes"] = [
        {"node_id": "n-root",
         "state_identity": f"strict:{root_smi}",
         "structure_smiles": root_smi,
         "structure_identity_scope": "strict_structure",
         "role": "root", "occurrence_id": "occ-root",
         "source_group_refs": ["sg-a"], "condition_scope": [],
         "provenance_refs": ["pv-1"], "node_status": "observed"},
        {"node_id": "n-p1",
         "state_identity": f"strict:{prod_smi}",
         "structure_smiles": prod_smi,
         "structure_identity_scope": "strict_structure",
         "role": "principal_product", "occurrence_id": "occ-p1",
         "source_group_refs": ["sg-a"], "condition_scope": [],
         "provenance_refs": ["pv-1"], "node_status": "observed"},
    ]
    edge = graph["edges"][0]
    for node_id, smi in extra_product_nodes:
        graph["nodes"].append({
            "node_id": node_id,
            "state_identity": f"strict:{smi}",
            "structure_smiles": smi,
            "structure_identity_scope": "strict_structure",
            "role": "coproduct", "occurrence_id": f"occ-{node_id}",
            "source_group_refs": ["sg-a"], "condition_scope": [],
            "provenance_refs": ["pv-1"], "node_status": "observed"})
        edge["to_node_ids"].append(node_id)
        edge["participants"].append({
            "node_id": node_id, "role": "coproduct", "side": "product",
            "coefficient": None, "coefficient_status": "unknown"})
    graph["root_entity"] = {
        "entity_id": "ent-1", "structure_smiles_raw": root_smi,
        "strict_structure_identity": root_smi, "source_refs": [],
        "formal_charge": 0, "isotope_information_status": "unknown",
        "stereo_information_status": "unknown"}
    validate_reference_graph(graph)
    return graph


def _participant(state_id: str, side: str, role: str,
                 entry_seq: int) -> dict:
    return {"state_ref": state_id, "side": side, "role": role,
            "coefficient": None, "coefficient_status": "unknown",
            "entry_id": f"pe-{entry_seq}", "merged_from": [],
            "parallel_contribution": False}


def _make_payload(root_smi: str, prod_smi: str, *,
                  extras: tuple[tuple[str, str, str], ...] = (),
                  hyp_refs: tuple[str, ...] = ("prov-1",),
                  declared_equation: dict | None = None,
                  declared_role: str | None = None,
                  provenance_rows: list[dict] | None = None) -> dict:
    """合成导出 payload:事件 = 底物 → 主产物 + extras。

    extras = ((state_id, side, smiles), …);声明链按 v2 消费契约
    (provenance_records 行 payload.record_equation,预注册 §二.1);
    hyp_refs=() 或 provenance_rows=[] 构造缺席/悬空链(负控)。"""
    participants = [
        _participant("cs-sub", "reactant", "primary_substrate", 1),
        _participant("cs-prod", "product", "principal_product", 2),
    ]
    states = [
        {"state_id": "cs-sub", "payload": {
            "smiles_isomeric": root_smi, "cn_identity": None}},
        {"state_id": "cs-prod", "payload": {
            "smiles_isomeric": prod_smi, "cn_identity": None}},
    ]
    for seq, (state_id, side, smi) in enumerate(extras, start=3):
        participants.append(_participant(state_id, side, "coproduct"
                                         if side == "product"
                                         else "cosubstrate", seq))
        states.append({"state_id": state_id, "payload": {
            "smiles_isomeric": smi, "cn_identity": None}})
    prov_rows = list(provenance_rows or [])
    if declared_equation is not None and not prov_rows:
        equation = json.loads(json.dumps(declared_equation))
        if declared_role is not None:
            for entry in equation.get("products", []):
                entry["role"] = declared_role
        prov_rows = [{"record_id": "prov-1", "payload": json.dumps({
            "schema_version": "ppv1-provenance-8",
            "record_equation": equation})}]
    event_body = {
        "schema_version": "ppv1-event-8",
        "participants": participants,
        "participant_state_refs": [p["state_ref"] for p in participants],
    }
    return {
        "states": states,
        "events": [{"event_id": "ppev-1", "hypothesis_id": "hyp-1",
                    "payload": json.dumps(event_body)}],
        "hypotheses": [{"hypothesis_id": "hyp-1", "payload": json.dumps({
            "schema_version": "ppv1-hypothesis-8",
            "step_scope": "net_reaction",
            "provenance_refs": list(hyp_refs)})}],
        "provenance_records": prov_rows,
    }


def _water_declared(root_smi: str, prod_smi: str) -> dict:
    return {"reactants": [{"smiles": root_smi}],
            "products": [{"smiles": prod_smi}, {"smiles": WATER}]}


def _run_match(graph: dict, payload: dict, criteria_version: str):
    nodes = match_reference_nodes(graph, payload)
    return match_reference_edges(graph, payload, nodes,
                                 criteria_version=criteria_version)


def _states_of(payload: dict) -> dict:
    from pathway_v43.pollutant.evaluation import _export_states
    return _export_states(payload)


def _event_body_of(payload: dict) -> dict:
    body = payload["events"][0].get("payload")
    return json.loads(body) if isinstance(body, str) else body


# ---------------------------------------------------------------- 常量与挡板

def test_criteria_constants_and_membership_guards() -> None:
    """判据版本常量 + 豁免四类 cn 收敛 + 版本化哈希 + 三重挡板。"""
    assert PPV1_CRITERIA_V1 == "ppv1-criteria-v1"
    assert PPV1_CRITERIA_V2 == "ppv1-criteria-v2"
    assert PPV1_CRITERIA_VERSIONS == {PPV1_CRITERIA_V1, PPV1_CRITERIA_V2}
    assert resolve_criteria_version(PPV1_CRITERIA_V1) == PPV1_CRITERIA_V1
    assert resolve_criteria_version(PPV1_CRITERIA_V2) == PPV1_CRITERIA_V2
    # 豁免四类变体组各自收敛单一 cn 键(与 CS2c 补证 §5 同结论)
    variants = {
        "v1:H2O": ["O", "[OH-]", "[OH3+]"],
        "v1:H+": ["[H+]"],
        "v1:Pi": ["OP(=O)(O)O", "[O-]P(=O)(O)O", "[O-]P(=O)([O-])O",
                  "[O-]P(=O)([O-])[O-]"],
        "v1:PPi": ["O=P(O)(O)OP(=O)(O)O", "[O-]P(=O)(O)OP(=O)(O)[O-]",
                   "[O-]P(=O)([O-])OP(=O)([O-])[O-]",
                   "O=P([O-])([O-])OP(=O)([O-])([O-])"],
    }
    keys = set()
    for family, group in variants.items():
        cns = {cn_identity(v) for v in group}
        assert len(cns) == 1 and None not in cns, family
        keys |= cns
    # 机器挡板 1:含碳禁入豁免构造(零碳断言)
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
    for key in keys:
        mol = Chem.MolFromSmiles(key)
        assert mol is not None
        assert not any(a.GetSymbol() == "C" for a in mol.GetAtoms()), key
    # 机器挡板 2:豁免身份 ∩ COMPLETION_LICENSED_IDENTITIES = ∅
    assert keys.isdisjoint(COMPLETION_LICENSED_IDENTITIES)
    # 机器挡板 3:辅因子硬拒绝表(常量非空;代表身份不入豁免集)
    assert CRITERIA_V2_NEVER_EXEMPT_FAMILIES
    for rep in ("N", "O=O", "OO", "[C-]#N", "[S-]C#N", "[N]=O"):
        assert cn_identity(rep) not in keys, rep
    # 完备二分恰两 tier + T1′ 未实施明字
    assert CRITERIA_TIERS == {CRITERIA_TIER_V1_EXEMPT,
                              CRITERIA_TIER_NOT_EXEMPT}
    assert "T1'" in CRITERIA_T1P_NOT_IMPLEMENTED_NOTE
    assert "partial" in CRITERIA_T1P_NOT_IMPLEMENTED_NOTE


def test_hplus_atomic_h_h2_three_way_distinct_no_merge() -> None:
    """mimo r36 条件 7:cn([H⁺]) / cn([H]) / cn([H][H]) 三分;
    strict(H⁺) 不进 completion-licensed 集合(无合流)。"""
    assert cn_identity(H_PLUS) != cn_identity("[H]")
    assert cn_identity(H_PLUS) != cn_identity("[H][H]")
    assert cn_identity("[H]") != cn_identity("[H][H]")
    licensed = set(COMPLETION_LICENSED_IDENTITIES)
    assert strict_identity_of(H_PLUS) not in licensed
    assert cn_identity(H_PLUS) not in licensed


# ---------------------------------------------------------------- 正控

def test_declared_water_exemption_unlocks_strict_with_disclosure() -> None:
    """已声明水豁免 strict(任务书 §3.3 形态 1):v2 升 exact ⇒
    matched_strict;逐边披露 exempted_participants(身份哈希/族/侧/
    角色/tier/谓词三布尔);缺省 v1 维持 partial 且零新键。"""
    graph = _make_graph("CCO", "CC=O")
    payload = _make_payload(
        "CCO", "CC=O", extras=(("cs-x", "product", WATER),),
        declared_equation=_water_declared("CCO", "CC=O"))
    v1 = _run_match(graph, payload, PPV1_CRITERIA_V1)
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v1[0]["match_status"] == "matched_participant_coverage_partial"
    assert v2[0]["match_status"] == "matched_strict"
    # 显式 v1 与缺省输出全等(豁免关字节不变;零新键)
    v1_explicit = match_reference_edges(
        graph, payload, match_reference_nodes(graph, payload),
        criteria_version=PPV1_CRITERIA_V1)
    assert v1_explicit == v1
    assert "exempted_participants" not in json.dumps(v1)
    # 披露形态:身份哈希/族/侧/角色/tier/谓词三布尔
    disclosed = v2[0]["matched_events"][0]["exempted_participants"]
    assert len(disclosed) == 1
    row = disclosed[0]
    assert row["state_ref"] == "cs-x"
    assert row["side"] == "product"
    assert row["role"] == "coproduct"
    assert row["tier"] == CRITERIA_TIER_V1_EXEMPT
    assert row["exempt_family"] == "v1:H2O"
    assert row["pred1_record_declared"] == "true"
    assert row["pred2_element_traceable"] == "pass"
    assert row["pred3_cn_identity_member"] is True
    from pathway_v43.pollutant.evaluation import _CRITERIA_V2_IDENTITIES
    assert row["identity_sha256_16"] == \
        _CRITERIA_V2_IDENTITIES["sha256_16_by_cn"][cn_identity(WATER)]


def test_hplus_product_side_exemption_not_applicable_counts_pass() -> None:
    """H⁺ 产物侧豁免正控:H⁺ 无 O/P 涉及 ⇒ pred2 = not_applicable
    记过(预注册 §二.2;判据二 unknown 轴不拦电荷记账)。"""
    graph = _make_graph("CCO", "CC=O")
    payload = _make_payload(
        "CCO", "CC=O", extras=(("cs-h", "product", H_PLUS),),
        declared_equation={"reactants": [{"smiles": "CCO"}],
                           "products": [{"smiles": "CC=O"},
                                        {"smiles": H_PLUS}]})
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v2[0]["match_status"] == "matched_strict"
    row = v2[0]["matched_events"][0]["exempted_participants"][0]
    assert row["exempt_family"] == "v1:H+"
    assert row["pred2_element_traceable"] == "not_applicable"


def test_ppi_product_side_traceable_exemption() -> None:
    """PPi 产物侧带 P/O 追溯豁免正控(r28 A6 半套簿记防线的合法面):
    非豁免反应物侧 P/O 供给 ≥ 豁免需求 ⇒ 三谓词全过 ⇒ strict。"""
    graph = _make_graph(_SUB_2P, "CCO")
    payload = _make_payload(
        _SUB_2P, "CCO", extras=(("cs-ppi", "product", PPI),),
        declared_equation={
            "reactants": [{"smiles": _SUB_2P}],
            "products": [{"smiles": "CCO"}, {"smiles": PPI}]})
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v2[0]["match_status"] == "matched_strict"
    row = v2[0]["matched_events"][0]["exempted_participants"][0]
    assert row["exempt_family"] == "v1:PPi"
    assert row["pred2_element_traceable"] == "pass"


# ---------------------------------------------------------------- 负控

def test_denovo_water_blocked_by_element_account() -> None:
    """无中生水拦截(任务书 §3.3 形态 2;补证 3 题剔除形态):
    反应物侧 O=0 而产物豁免水 ⇒ pred2 fail ⇒ 维持 partial。"""
    graph = _make_graph("CC", "CC=O")  # 乙烷底物:O 供给 0
    payload = _make_payload(
        "CC", "CC=O", extras=(("cs-x", "product", WATER),),
        declared_equation={"reactants": [{"smiles": "CC"}],
                           "products": [{"smiles": "CC=O"},
                                        {"smiles": WATER}]})
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v2[0]["match_status"] == "matched_participant_coverage_partial"
    # 评审细节:pred2 fail(供给 0 < 需求 1)、tier = not_exempt、
    # 元素账 O_product_side = fail(单归属语义与事件级账一致)
    review = evaluate_participant_exemption(
        payload, _event_body_of(payload), _states_of(payload),
        hypothesis_id="hyp-1", from_states={"cs-sub"},
        to_states={"cs-prod"})
    occ = review["occurrences"][0]
    assert occ["tier"] == CRITERIA_TIER_NOT_EXEMPT
    assert occ["pred2_element_traceable"] == "fail"
    assert review["element_accounts"]["O_product_side"] == "fail"
    assert review["all_exempt"] is False


def test_pi_reactant_side_not_exempt() -> None:
    """Pi 反应物侧不豁(任务书 §3.3 形态 3;mimo r36 条件 1 方向限定:
    磷酰化机制判别子保护)⇒ 维持 partial。"""
    graph = _make_graph("CCO", "CC=O")
    payload = _make_payload(
        "CCO", "CC=O", extras=(("cs-pi", "reactant", PI),),
        declared_equation={
            "reactants": [{"smiles": "CCO"}, {"smiles": PI}],
            "products": [{"smiles": "CC=O"}]})
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v2[0]["match_status"] == "matched_participant_coverage_partial"


def test_ppi_without_p_source_half_bookkeeping_blocked() -> None:
    """r28 A6 半套簿记拦截:产物豁免 PPi 而非豁免反应物侧无 P 源
    ⇒ pred2 fail ⇒ 维持 partial(P 追溯是唯一防线的负控)。"""
    graph = _make_graph("CCO", "CC=O")  # 底物无 P
    payload = _make_payload(
        "CCO", "CC=O", extras=(("cs-ppi", "product", PPI),),
        declared_equation={
            "reactants": [{"smiles": "CCO"}],
            "products": [{"smiles": "CC=O"}, {"smiles": PPI}]})
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v2[0]["match_status"] == "matched_participant_coverage_partial"


def test_cofactor_and_mechanism_families_not_washed() -> None:
    """NAD 挂名不洗(任务书 §3.3 形态 4)+ NH₃/O₂ 机制类不豁:
    即使来源记录声明,不在豁免集 ⇒ 维持 partial(辅因子硬拒绝表)。"""
    nad = ("NC1=NC(=O)C=C2N(C[C@H](O)[C@H](O)[C@H](O)"
           "COP(=O)(O)OP(=O)(O)OC3OC(C)C(O)C3O)C1=NC2(N)N")
    graph = _make_graph("CCO", "CC=O")
    for smi in (nad, "N", "O=O"):
        payload = _make_payload(
            "CCO", "CC=O", extras=(("cs-x", "product", smi),),
            declared_equation={
                "reactants": [{"smiles": "CCO"}],
                "products": [{"smiles": "CC=O"}, {"smiles": smi}]})
        v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
        assert v2[0]["match_status"] == \
            "matched_participant_coverage_partial", smi
        review = evaluate_participant_exemption(
            payload, _event_body_of(payload), _states_of(payload),
            hypothesis_id="hyp-1",
            from_states={"cs-sub"}, to_states={"cs-prod"})
        tiers = [o["tier"] for o in review["occurrences"]]
        assert tiers == [CRITERIA_TIER_NOT_EXEMPT]
        assert review["all_exempt"] is False


def test_undeclared_extra_maintains_partial_t1p_note() -> None:
    """未声明多余产物维持 partial(任务书 §3.3 形态 5;T1′ 未实施
    ⇒ 明字,完备二分右侧):声明记录可解析但不含该 cn ⇒ pred1
    false ⇒ not_exempt_maintains_partial。"""
    graph = _make_graph("CCO", "CC=O")
    payload = _make_payload(
        "CCO", "CC=O", extras=(("cs-x", "product", WATER),),
        declared_equation={"reactants": [{"smiles": "CCO"}],
                           "products": [{"smiles": "CC=O"}]})  # 未声明水
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v2[0]["match_status"] == "matched_participant_coverage_partial"
    review = evaluate_participant_exemption(
        payload, _event_body_of(payload), _states_of(payload),
        hypothesis_id="hyp-1", from_states={"cs-sub"},
        to_states={"cs-prod"})
    assert review["declaration_status"] == "resolved"
    occ = review["occurrences"][0]
    assert occ["tier"] == CRITERIA_TIER_NOT_EXEMPT
    assert occ["pred1_record_declared"] == "false"


def test_declaration_chain_missing_dangling_unparseable_fail_closed() -> None:
    """声明链三种不可判形态 ⇒ pred1 unknown = fail-closed(任务书
    排障表行 1:不造数据):
    (a) hypothesis 无 provenance_refs;(b) refs 悬空(无对应
    provenance_records 行);(c) 行存在但 record_equation 缺失/
    含不可解析条目。三种均维持 partial。"""
    graph = _make_graph("CCO", "CC=O")
    common = dict(extras=(("cs-x", "product", WATER),))
    # (a) 链缺席
    payload_a = _make_payload("CCO", "CC=O", hyp_refs=(), **common)
    # (b) 悬空引用
    payload_b = _make_payload("CCO", "CC=O", hyp_refs=("prov-404",),
                              provenance_rows=[], **common)
    # (c) 行在但无 record_equation / 条目不可解析
    payload_c = _make_payload(
        "CCO", "CC=O", hyp_refs=("prov-1",), **common,
        provenance_rows=[{"record_id": "prov-1",
                          "payload": json.dumps({"note": "无方程"})}])
    payload_d = _make_payload(
        "CCO", "CC=O", hyp_refs=("prov-1",), **common,
        provenance_rows=[{"record_id": "prov-1", "payload": json.dumps({
            "record_equation": {"reactants": [{"smiles": "CCO"}],
                                "products": [{"smiles": "not a smiles!!"},
                                             {"smiles": WATER}]}})}])
    for name, payload in (("no_chain", payload_a),
                          ("dangling", payload_b),
                          ("no_equation", payload_c),
                          ("unparseable", payload_d)):
        v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
        assert v2[0]["match_status"] == \
            "matched_participant_coverage_partial", name
        review = evaluate_participant_exemption(
            payload, _event_body_of(payload), _states_of(payload),
            hypothesis_id="hyp-1", from_states={"cs-sub"},
            to_states={"cs-prod"})
        assert review["declaration_status"] != "resolved", name
        assert review["occurrences"][0]["pred1_record_declared"] == \
            "unknown", name
        assert review["all_exempt"] is False, name


def test_side_flip_and_role_mismatch_not_exempt() -> None:
    """声明绑定 = 身份+侧+角色(mimo r36 M3.3):记录只在反应物侧
    声明水而事件写在产物侧 ⇒ pred1 false;记录声明角色与事件角色
    不符 ⇒ pred1 false;两态均维持 partial(侧别翻转不进 v1 也不进
    T1′)。"""
    graph = _make_graph("CCO", "CC=O")
    # (a) 侧别翻转:记录只在反应物侧声明水
    payload_a = _make_payload(
        "CCO", "CC=O", extras=(("cs-x", "product", WATER),),
        declared_equation={"reactants": [{"smiles": "CCO"},
                                         {"smiles": WATER}],
                           "products": [{"smiles": "CC=O"}]})
    v2a = _run_match(graph, payload_a, PPV1_CRITERIA_V2)
    assert v2a[0]["match_status"] == "matched_participant_coverage_partial"
    review_a = evaluate_participant_exemption(
        payload_a, _event_body_of(payload_a), _states_of(payload_a),
        hypothesis_id="hyp-1", from_states={"cs-sub"},
        to_states={"cs-prod"})
    assert review_a["occurrences"][0]["pred1_record_declared"] == "false"
    # (b) 角色不符:记录声明 role=solvent,事件 role=coproduct
    payload_b = _make_payload(
        "CCO", "CC=O", extras=(("cs-x", "product", WATER),),
        declared_equation=_water_declared("CCO", "CC=O"),
        declared_role="solvent")
    v2b = _run_match(graph, payload_b, PPV1_CRITERIA_V2)
    assert v2b[0]["match_status"] == "matched_participant_coverage_partial"
    review_b = evaluate_participant_exemption(
        payload_b, _event_body_of(payload_b), _states_of(payload_b),
        hypothesis_id="hyp-1", from_states={"cs-sub"},
        to_states={"cs-prod"})
    assert review_b["occurrences"][0]["pred1_record_declared"] == "false"


def test_single_attribution_mixed_extras_event_stays_partial() -> None:
    """单归属断言(任务书 §1.1):混合 extras(一个可豁免已声明水 +
    一个不在豁免集的 NAD)⇒ 每实例恰一个 tier、两实例标签互异、
    事件不升 exact(任一 extras 非 v1_exempt ⇒ 维持 partial)。"""
    nad = ("NC1=NC(=O)C=C2N(C[C@H](O)[C@H](O)[C@H](O)"
           "COP(=O)(O)OP(=O)(O)OC3OC(C)C(O)C3O)C1=NC2(N)N")
    graph = _make_graph("CCO", "CC=O")
    payload = _make_payload(
        "CCO", "CC=O",
        extras=(("cs-w", "product", WATER), ("cs-nad", "product", nad)),
        declared_equation={
            "reactants": [{"smiles": "CCO"}],
            "products": [{"smiles": "CC=O"}, {"smiles": WATER},
                         {"smiles": nad}]})
    v2 = _run_match(graph, payload, PPV1_CRITERIA_V2)
    assert v2[0]["match_status"] == "matched_participant_coverage_partial"
    assert not any(ev.get("exempted_participants")
                   for ev in v2[0]["matched_events"])
    review = evaluate_participant_exemption(
        payload, _event_body_of(payload), _states_of(payload),
        hypothesis_id="hyp-1", from_states={"cs-sub"},
        to_states={"cs-prod"})
    keys = [(o["state_ref"], o["side"], o["role"])
            for o in review["occurrences"]]
    assert len(keys) == len(set(keys)) == 2  # 单归属:键唯一、无遗漏
    tiers = {o["state_ref"]: o["tier"] for o in review["occurrences"]}
    assert tiers["cs-w"] == CRITERIA_TIER_V1_EXEMPT
    assert tiers["cs-nad"] == CRITERIA_TIER_NOT_EXEMPT
    assert review["all_exempt"] is False
    # 豁免未发生 ⇒ 披露为空(披露仅在豁免发生时,任务书 §1.1)
    assert review["exempted_participants"] == []


# ---------------------------------------------------------------- 入口门与批级汇总

def test_evaluate_scientific_v2_summary_and_reference_side_signal() -> None:
    """v2 批级汇总块(criteria_v2):豁免计数 + 参考侧 v1 身份监控。
    参考图声明豁免身份(水节点)⇒ 计数非 0 ⇒ EXIT_CONDITION_SIGNAL_
    nonzero(任务书 §1.1 参考侧监控/退出条件);干净图 ⇒ ok;
    v1 缺省输出零 criteria_v2 键。"""
    # 干净图(无豁免身份节点)⇒ signal ok
    graph = _make_graph("CCO", "CC=O")
    evaluation_input = synth_evaluation_input(
        domain="298", graphs=[graph],
        split_manifest=synth_split_manifest(graph_id="rg-crit2",
                                            group_ids=["sg-a"]),
        exports=[])
    out_v1 = evaluate_scientific(
        dict(evaluation_input), reference_graphs={
            graph["reference_graph_id"]: graph})
    assert "criteria_v2" not in out_v1  # v1 缺省:零新键
    out_v2 = evaluate_scientific(
        dict(evaluation_input),
        reference_graphs={graph["reference_graph_id"]: graph},
        criteria_version=PPV1_CRITERIA_V2)
    block = out_v2["criteria_v2"]
    assert block["criteria_version"] == PPV1_CRITERIA_V2
    assert block["edges_with_exemption"] == 0
    assert block["events_exempted_strict"] == 0
    assert block["reference_side_v1_identity_nodes"] == 0
    assert block["reference_side_v1_identity_signal"] == "ok"
    assert block["preregistration_doc"].endswith(
        "POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md")
    # 参考图声明水节点 ⇒ 退出条件信号
    graph_ref = _make_graph("CCO", "CC=O",
                            extra_product_nodes=(("n-water", WATER),))
    out_sig = evaluate_scientific(
        dict(synth_evaluation_input(
            domain="298", graphs=[graph_ref],
            split_manifest=synth_split_manifest(graph_id="rg-crit2",
                                                group_ids=["sg-a"]),
            exports=[])),
        reference_graphs={graph_ref["reference_graph_id"]: graph_ref},
        criteria_version=PPV1_CRITERIA_V2)
    sig = out_sig["criteria_v2"]
    assert sig["reference_side_v1_identity_nodes"] >= 1
    assert sig["reference_side_v1_identity_signal"] == \
        "EXIT_CONDITION_SIGNAL_nonzero"


def test_criteria_version_rejected_everywhere() -> None:
    """机器挡板:非法 criteria_version 三门同拒(评测器/边匹配/
    判分入口;判分入口经 resolve_criteria_version 同一判据)。"""
    graph = _make_graph("CCO", "CC=O")
    payload = _make_payload("CCO", "CC=O")
    nodes = match_reference_nodes(graph, payload)
    with pytest.raises(EvaluationContractError) as exc_edge:
        match_reference_edges(graph, payload, nodes,
                              criteria_version="ppv1-criteria-v9")
    assert exc_edge.value.detail["kind"] == "criteria_version_invalid"
    evaluation_input = synth_evaluation_input(
        domain="298", graphs=[graph],
        split_manifest=synth_split_manifest(graph_id="rg-crit2",
                                            group_ids=["sg-a"]),
        exports=[])
    with pytest.raises(EvaluationContractError) as exc_eval:
        evaluate_scientific(
            dict(evaluation_input),
            reference_graphs={graph["reference_graph_id"]: graph},
            criteria_version="ppv1-criteria-v9")
    assert exc_eval.value.detail["kind"] == "criteria_version_invalid"
    from pathway_v43.pollutant.s5b_scoring import score_s5b_batch
    with pytest.raises(RuntimeError) as exc_score:
        score_s5b_batch(
            "/nonexistent-batch-root", runs_root="/nonexistent-runs",
            criteria_version="ppv1-criteria-v9")
    assert "criteria_version 非法" in str(exc_score.value)


def test_scoring_side_carries_criteria_version_default_v1() -> None:
    """判分侧版本承载:score_s5b_batch 签名带 criteria_version 且
    缺省 v1(豁免关;metrics 零新键);v2 经同一 resolve 判据。"""
    import inspect
    from pathway_v43.pollutant.s5b_scoring import score_s5b_batch
    sig = inspect.signature(score_s5b_batch)
    assert sig.parameters["criteria_version"].default == PPV1_CRITERIA_V1
    assert sig.parameters["criteria_version"].kind == \
        inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------- 批级 tier
# 单归属计数(P2 回修,criteria-v2 复审 2026-10-14:预注册 §五 批级
# criteria_v2 块补两 tier 计数;occurrences 双 tier 只在评审点完整
# 存在,输出仅保留 v1_exempt 披露子集 ⇒ 逐边 criteria_v2_tier_counts
# 随边带出、批级 tier_counts 汇总闭合)

def test_per_edge_criteria_v2_tier_counts_both_tiers() -> None:
    """逐边 tier 计数:v1_exempt 边(声明水豁免升 exact)记 v1_exempt=1;
    not_exempt 边(无中生水 pred2 fail 维持 partial)记
    not_exempt_maintains_partial=1;v1 缺省零新键。"""
    graph = _make_graph("CCO", "CC=O")
    payload_ok = _make_payload(
        "CCO", "CC=O", extras=(("cs-x", "product", WATER),),
        declared_equation=_water_declared("CCO", "CC=O"))
    v2 = _run_match(graph, payload_ok, PPV1_CRITERIA_V2)
    assert v2[0]["criteria_v2_tier_counts"] == {
        "not_exempt_maintains_partial": 0, "v1_exempt": 1}
    assert v2[0]["matched_events"][0]["exempted_participants"][0][
        "tier"] == CRITERIA_TIER_V1_EXEMPT
    graph_dn = _make_graph("CC", "CC=O")  # 乙烷底物:O 供给 0
    payload_dn = _make_payload(
        "CC", "CC=O", extras=(("cs-x", "product", WATER),),
        declared_equation={"reactants": [{"smiles": "CC"}],
                           "products": [{"smiles": "CC=O"},
                                        {"smiles": WATER}]})
    v2_dn = _run_match(graph_dn, payload_dn, PPV1_CRITERIA_V2)
    assert v2_dn[0]["criteria_v2_tier_counts"] == {
        "not_exempt_maintains_partial": 1, "v1_exempt": 0}
    assert v2_dn[0]["match_status"] == \
        "matched_participant_coverage_partial"
    v1 = _run_match(graph, payload_ok, PPV1_CRITERIA_V1)
    assert "criteria_v2_tier_counts" not in json.dumps(v1)


def test_batch_criteria_v2_tier_counts_real_chain_closure(
        tmp_path: Path) -> None:
    """真实链批级闭合:合成 run(CCO→CC=O+[H][H] 共同产物)对不含
    H₂ 节点的参考图 ⇒ superset 豁免评审 ⇒ H₂ 不在豁免集 ⇒
    批级 tier_counts = {v1_exempt:0, not_exempt_maintains_partial:1},
    且批级 == 逐边 criteria_v2_tier_counts 之和(单归属闭合);
    v1 缺省零新键(criteria_v2 块与逐边键全无)。"""
    from pathway_v43.config import resolve_config
    from pathway_v43.pollutant.evaluation import \
        native_export_reader_from_ledger
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore
    from pathway_v43.storage.run_identity import (
        PROFILE_POLLUTANT_PATHWAY_V1)
    from pathway_v43.workflow.runner import start_run
    from test_ppv1_s4a_endpoint import spec

    run_id = "p2tier"
    plan = {"pools": {"CCO": [
        spec("B", "CC=O", "donor-B", coproducts=["[H][H]"])]},
        "schedule_budget": {"max_select": 1}}
    out = start_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    runs_root = tmp_path / "runs"
    digest = out["native_export"]["export_digest"]
    graph = _make_graph("CCO", "CC=O")
    store = PollutantPathwayStore(
        runs_root / run_id / "pollutant.sqlite")
    ledger = SearchLedger(
        store, ArtifactStore(runs_root, run_id), run_id)
    reader = native_export_reader_from_ledger(ledger, runs_root / run_id)

    def _input() -> dict:
        inp = synth_evaluation_input(
            domain="298", graphs=[graph],
            split_manifest=synth_split_manifest(
                graph_id="rg-crit2", group_ids=["sg-a"]),
            exports=[{"run_id": run_id, "export_digest": digest}])
        inp["run_identity"]["run_id"] = run_id
        return inp

    out2 = evaluate_scientific(
        _input(), reference_graphs={
            graph["reference_graph_id"]: graph},
        native_export_reader=reader, criteria_version=PPV1_CRITERIA_V2)
    block = out2["criteria_v2"]
    assert set(block["tier_counts"]) == set(CRITERIA_TIERS)
    assert block["tier_counts"] == {
        "not_exempt_maintains_partial": 1, "v1_exempt": 0}
    # 单归属闭合:批级 == 全部逐边计数之和
    edge_sum: dict[str, int] = {}
    for sample in out2["sample_results"]:
        for entry in sample["predicted_edge_matches"]:
            for tier, n in entry["criteria_v2_tier_counts"].items():
                assert tier in CRITERIA_TIERS
                edge_sum[tier] = edge_sum.get(tier, 0) + n
    assert edge_sum == block["tier_counts"]
    # v1 缺省:零新键(块与逐边键全无)
    out1 = evaluate_scientific(
        _input(), reference_graphs={
            graph["reference_graph_id"]: graph},
        native_export_reader=reader, criteria_version=PPV1_CRITERIA_V1)
    assert "criteria_v2" not in out1
    dumped = json.dumps(out1)
    assert "criteria_v2_tier_counts" not in dumped
    assert "tier_counts" not in dumped
