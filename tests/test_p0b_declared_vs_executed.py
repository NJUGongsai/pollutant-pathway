"""T-H P0b/D-6 旁路披露回归(合同
docs/T_H_P0B_D6_CONTRACT_2026-10-20.md;零模型、零网络)。

覆盖:
- 四态互斥与冻结优先级;8 项合成正负控(合法多碎片、合法 copy、
  仅立体差、明确矛盾、解析失败、空声明、未核执行范围、开关关闭等价);
- R1 装配共同多重集(重复 coproduct 缺一份不一致/份数齐全一致)与
  copy 严格 state_ref 引用(结构对应只作另一披露轴);
- R2 缺资料保留 unknown(missing_production_report/missing_spec/
  event_assembly_unavailable),明确空参与物仍可判不一致;
- R3 stereo_only 只证明去掉立体后仍相等;纯同位素差输出诚实的
  principal_isomeric_unspecified,连接差仍 principal_absent;
- 上述 R1-R3 在共用 reconcile 与公开 derive 两层均有正负控;
- 生产报告纯函数与原生聚合派生共用同一来源;
- 原生结果默认关闭零新增键/零字节漂移;开启只加可选块;
- 导出 manifest 的 diagnostic_bindings 与显式读取校验。

本文件只覆盖本任务字段与开关,不改既有断言口径。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.models import canonical_json  # noqa: E402
from pathway_v43.pollutant.endpoint import read_run_endpoint  # noqa: E402
from pathway_v43.pollutant.native_export import (  # noqa: E402
    NativeExportContractError,
    export_native_result,
    read_declared_vs_executed,
)
from pathway_v43.pollutant.native_result import (  # noqa: E402
    build_native_result,
    declared_vs_executed_block,
    derive_declared_vs_executed,
    strip_declared_vs_executed,
)
from pathway_v43.pollutant.production import (  # noqa: E402
    P0B_D6_DIAGNOSTIC_SCHEMA,
    build_declaration_disclosure,
    p0b_d6_diagnostics_enabled,
    reconcile_declared_vs_executed,
)

from test_ppv1_s4a_endpoint import ledger_for, spec, start  # noqa: E402

RUN_ID = "p0b"


# ---------------------------------------------------------------- 纯函数控制


def _disclosure(main: str, coproducts=(), copies=(), *,
                compiled: bool = False) -> dict:
    spec = {
        "product_smiles": main,
        "coproducts": list(coproducts),
        "declared_copy_components": list(copies),
    }
    if compiled:
        spec["compile"] = {"compiler_version": "synthetic-control"}
    return build_declaration_disclosure(spec)


def _execution(product: str, *, ok: bool = True) -> dict:
    return {
        "execution_ok": ok,
        "result": {"ok": ok, "product_smiles": product},
    }


def _reconcile(disclosure, execution, *, refs=("p1",), smiles=("CCO",),
               expectation: str = "", origin: str = "novel",
               projection=None, report: bool = True) -> dict:
    return reconcile_declared_vs_executed(
        disclosure,
        execution=execution,
        event_product_refs=list(refs) if refs is not None else None,
        event_product_smiles=list(smiles) if smiles is not None else None,
        expectation_target=expectation,
        projection_ranks=projection if projection is not None else [
            {"report_rank": 1, "state_ref": "p1"}],
        state_smiles_by_ref={"p1": "CCO", "p2": "CC=O", "c1": "Cl"},
        audit_center={"center_match": True, "strict_target_match": True,
                      "declaration_mismatch": False,
                      "proof_scope": "self_contained_recompute"},
        origin=origin,
        production_report_present=report,
    )


def test_control_c1_legal_multi_fragment() -> None:
    """合法主产物 + 多碎片:执行多出组分是披露,不是不一致。"""
    row = _reconcile(
        _disclosure("CCO", ["CC=O"]),
        _execution("CCO.CC=O.CCC"),
        refs=("p1", "p2"), smiles=("CCO", "CC=O"),
        expectation="CCO.CC=O")
    assert row["status"] == "consistent"
    assert row["component_relation"]["principal_in_executed"] is True
    assert row["component_relation"]["executed_extra"] == 1
    assert row["component_relation"]["relation"] == \
        "declared_subset_executed"
    assert row["inconsistency_subclass"] is None


def test_control_c2_legal_copy() -> None:
    """合法 copy:记录声明、未执行、被事件产物侧引用、不进 expectation。"""
    row = _reconcile(
        _disclosure("CCO", copies=[{
            "smiles": "Cl", "state_ref": "c1",
            "component_source": "record_declared_copy"}]),
        _execution("CCO"),
        refs=("p1", "c1"), smiles=("CCO", "Cl"), expectation="CCO")
    assert row["status"] == "consistent"
    assert row["copy"]["applicable"] is True
    assert row["copy"]["in_event_products"] is True
    assert row["copy"]["structure_in_event_products"] is True
    assert row["copy"]["in_executed"] is False
    assert row["copy"]["in_expectation"] is False


def test_control_c2_negative_copy_in_expectation() -> None:
    row = _reconcile(
        _disclosure("CCO", copies=[{
            "smiles": "Cl", "state_ref": "c1",
            "component_source": "record_declared_copy"}]),
        _execution("CCO"),
        refs=("p1", "c1"), smiles=("CCO", "Cl"), expectation="CCO.Cl")
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == "copy_contract_violation"
    assert "copy_in_expectation" in row["reason_codes"]


def test_control_c3_stereo_only_subclass() -> None:
    """仅立体差 ⇒ inconsistent 的立体子类,不得并入结构不同。"""
    row = _reconcile(
        _disclosure("C[C@H](O)Cl"), _execution("C[C@@H](O)Cl"),
        expectation="C[C@H](O)Cl")
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == "principal_stereo_only"
    assert row["component_relation"]["principal_in_executed"] is False
    assert row["component_relation"][
        "principal_nonstereo_in_executed"] is True
    assert row["component_relation"]["principal_flat_in_executed"] is True


def test_control_c4_explicit_contradiction() -> None:
    row = _reconcile(
        _disclosure("CCO"), _execution("CCC"), expectation="CCO")
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == "principal_absent"
    assert "principal_absent_from_executed" in row["reason_codes"]
    assert row["component_relation"]["relation"] == "disjoint"


def test_control_c5_parse_failure_is_unknown() -> None:
    row = _reconcile(
        _disclosure("not-a-smiles"), _execution("CCO"),
        expectation="CCO")
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "principal_unparseable"
    assert row["proof_scope"]["unverified_ranges"] == [
        "principal_unparseable"]


def test_control_c6_empty_declaration_not_applicable() -> None:
    row = _reconcile(
        _disclosure(""), _execution(""), refs=(), smiles=(),
        expectation="")
    assert row["status"] == "not_applicable"
    assert row["applicability"] == "not_applicable"


def test_control_c7_unverified_execution_is_unknown() -> None:
    row = _reconcile(
        _disclosure("CCO"), _execution("CCO", ok=False),
        expectation="CCO")
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "execution_not_verified"
    assert row["proof_scope"]["unverified_ranges"] == [
        "execution_not_verified"]
    assert row["proof_scope"]["does_not_prove"]


def test_control_c8_switch_off_is_byte_equivalent() -> None:
    """开关关闭:纯派生不产生块;原生 payload 零新增键。"""
    payload = _synthetic_native_payload()
    assert p0b_d6_diagnostics_enabled({}) is False
    assert p0b_d6_diagnostics_enabled(
        {"PPV1_P0B_D6_DIAGNOSTICS": "1"}) is True
    assert "declared_vs_executed" not in payload
    block = declared_vs_executed_block(payload)
    assert block["n_events"] == 2
    enriched = dict(payload)
    enriched["declared_vs_executed"] = block
    stripped = strip_declared_vs_executed(enriched)
    assert canonical_json(stripped) == canonical_json(
        strip_declared_vs_executed(payload))


# ---------------------------------------------------------------- R1-R3 回归
# Codex 终审 R1-R4 同根正负控;全部为合成输入,不含真实题面/金标结构。

_MAIN = "CCO"
_OTHER = "CCC"
_COPRODUCT = "CC=O"
_COPY = "Cl"
_ISOTOPE = "[13CH3]CO"
_STEREO_A = "C[C@H](O)Cl"
_STEREO_B = "C[C@@H](O)Cl"


def _copy_entry(ref: str = "c1", smiles: str = _COPY) -> dict:
    return {"state_ref": ref, "smiles": smiles,
            "component_source": "record_declared_copy"}


def _derive_payload(*, declared: str = _MAIN, executed: str = _MAIN,
                    coproducts=(), copies=(), participants="default",
                    report: bool = True, action: bool = True,
                    expectation=_MAIN, state_smiles=None) -> dict:
    """最小原生结果形状:可分别制造来源/装配资料缺口(R2 矩阵)。"""
    spec = {
        "product_smiles": declared,
        "coproducts": list(coproducts),
        "declared_copy_components": [dict(c) for c in copies],
        "expectation": {"target_smiles": expectation},
    }
    if participants == "default":
        parts = [{"state_ref": "p1", "side": "product"}]
    elif participants == "invalid_type":
        parts = "not-a-list"
    else:
        parts = participants
    states = {"p1": declared}
    states.update(state_smiles or {})
    event = {
        "event_id": "ev-1", "created_at": "2026-01-01T00:00:01",
        "payload": ({} if parts is None
                    else {"participants": parts}),
    }
    actions = ([{"action_id": "a-1", "payload": {
        "logical_proposal_id": "novel-r1r3", "spec": spec}}]
        if action else [])
    reports = ([{"action_id": "a-1", "production_payload": {
        "event_id": "ev-1", "status": "submitted", "action_id": "a-1",
        "execution": {
            "execution_ok": True,
            "result": {"ok": True, "product_smiles": executed},
            "tool_inputs": {"expectation": {
                "target_smiles": expectation}},
            "center_evidence": {
                "center_match": True, "strict_target_match": False,
                "declaration_mismatch": False,
                "proof_scope": "self_contained_recompute"}},
        "report_projection": {"product_ranks": [
            {"report_rank": 1, "state_ref": "p1"}]}}}]
        if report else [])
    return {
        "run_id": "synthetic-r1r3",
        "states": [{"state_id": sid,
                    "payload": {"state_id": sid, "smiles_isomeric": smi}}
                   for sid, smi in states.items()],
        "events": [event],
        "search_actions": actions,
        "audit_production_reports": reports,
    }


def _derive_one(payload: dict) -> dict:
    rows = derive_declared_vs_executed(payload)
    assert len(rows) == 1
    return rows[0]


# ---- R1:装配共同多重集 + copy 严格 state_ref 引用 ----

def test_r1_reconcile_duplicate_coproduct_missing_one() -> None:
    row = _reconcile(
        _disclosure(_MAIN, [_COPY, _COPY]),
        _execution(_MAIN),
        refs=("p1", "c1"), smiles=(_MAIN, _COPY))
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == \
        "declared_coproduct_missing_from_event"
    assert row["assembly"]["event_product_components"] == 2
    assert row["assembly"]["declared_generated_present"] == 2


def test_r1_reconcile_duplicate_coproduct_complete() -> None:
    row = _reconcile(
        _disclosure(_MAIN, [_COPY, _COPY]),
        _execution(_MAIN),
        refs=("p1", "c1", "c1"), smiles=(_MAIN, _COPY, _COPY))
    assert row["status"] == "consistent"
    assert row["assembly"]["event_product_components"] == 3
    assert row["assembly"]["declared_generated_present"] == 3


def test_r1_reconcile_copy_reference_required_not_structure() -> None:
    # 声明 copy 的 state_ref 不在事件;同结构以另一个 ref 出现 ⇒ 仅结构轴真,
    # 引用轴假 ⇒ 不一致(不得用结构对应 OR 替代引用)。
    row = _reconcile(
        _disclosure(_MAIN, copies=[_copy_entry("c9")]),
        _execution(_MAIN),
        refs=("p1", "c8"), smiles=(_MAIN, _COPY))
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == "copy_contract_violation"
    assert "copy_missing_from_event" in row["reason_codes"]
    assert row["copy"]["in_event_products"] is False
    assert row["copy"]["structure_in_event_products"] is True
    assert row["assembly"]["copy_refs_present"] == 0


def test_r1_derive_duplicate_coproduct_negative() -> None:
    row = _derive_one(_derive_payload(
        coproducts=[_COPRODUCT, _COPRODUCT],
        participants=[{"state_ref": "p1", "side": "product"},
                      {"state_ref": "c1", "side": "product"}],
        state_smiles={"c1": _COPRODUCT}))
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == \
        "declared_coproduct_missing_from_event"
    assert row["assembly"]["event_product_components"] == 2
    assert row["assembly"]["declared_generated_present"] == 2


def test_r1_derive_duplicate_coproduct_positive() -> None:
    row = _derive_one(_derive_payload(
        coproducts=[_COPRODUCT, _COPRODUCT],
        participants=[{"state_ref": "p1", "side": "product"},
                      {"state_ref": "c1", "side": "product"},
                      {"state_ref": "c1", "side": "product"}],
        state_smiles={"c1": _COPRODUCT}))
    assert row["status"] == "consistent"
    assert row["assembly"]["event_product_components"] == 3
    assert row["assembly"]["declared_generated_present"] == 3


def test_r1_derive_copy_reference_missing() -> None:
    row = _derive_one(_derive_payload(
        copies=[_copy_entry("c9")],
        participants=[{"state_ref": "p1", "side": "product"},
                      {"state_ref": "c8", "side": "product"}],
        state_smiles={"c8": _COPY}))
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == "copy_contract_violation"
    assert row["copy"]["in_event_products"] is False
    assert row["copy"]["structure_in_event_products"] is True


def test_r1_derive_legal_copy_positive() -> None:
    row = _derive_one(_derive_payload(
        copies=[_copy_entry("c1")],
        participants=[{"state_ref": "p1", "side": "product"},
                      {"state_ref": "c1", "side": "product"}],
        state_smiles={"c1": _COPY}))
    assert row["status"] == "consistent"
    assert row["copy"]["in_event_products"] is True
    assert row["copy"]["structure_in_event_products"] is True
    assert row["copy"]["in_executed"] is False
    assert row["copy"]["in_expectation"] is False


# ---- R2:缺资料保留 unknown,只有确知为空才 not_applicable ----

def test_r2_reconcile_missing_report_is_unknown() -> None:
    row = _reconcile(
        _disclosure(_MAIN), _execution(_MAIN), report=False)
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "missing_production_report"
    assert "missing_production_report" in \
        row["proof_scope"]["unverified_ranges"]


def test_r2_reconcile_missing_spec_is_unknown() -> None:
    row = reconcile_declared_vs_executed(
        build_declaration_disclosure(None),
        execution=_execution(_MAIN),
        event_product_refs=["p1"], event_product_smiles=[_MAIN],
        origin="novel", production_report_present=True)
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "missing_spec"


def test_r2_reconcile_missing_assembly_material_is_unknown() -> None:
    row = _reconcile(
        _disclosure(_MAIN, [_COPY]), _execution(_MAIN),
        refs=None, smiles=None)
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "event_assembly_unavailable"
    assert row["proof_scope"]["unverified_ranges"] == [
        "event_assembly_unavailable"]


def test_r2_reconcile_bad_type_assembly_is_unknown() -> None:
    row = _reconcile(
        _disclosure(_MAIN, [_COPY]), _execution(_MAIN),
        refs=["p1"], smiles=None)
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "event_assembly_unavailable"


def test_r2_reconcile_explicit_empty_assembly_is_known_empty() -> None:
    row = _reconcile(
        _disclosure(_MAIN, [_COPY]), _execution(_MAIN),
        refs=(), smiles=())
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == \
        "declared_coproduct_missing_from_event"
    assert row["assembly"]["event_product_components"] == 0


def test_r2_derive_missing_report_is_unknown() -> None:
    row = _derive_one(_derive_payload(report=False))
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "missing_production_report"


def test_r2_derive_missing_spec_is_unknown() -> None:
    row = _derive_one(_derive_payload(action=False))
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "missing_spec"


def test_r2_derive_missing_assembly_field_is_unknown() -> None:
    row = _derive_one(_derive_payload(
        coproducts=[_COPY], participants=None))
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "event_assembly_unavailable"
    assert row["proof_scope"]["unverified_ranges"] == [
        "event_assembly_unavailable"]


def test_r2_derive_bad_assembly_type_is_unknown() -> None:
    row = _derive_one(_derive_payload(
        coproducts=[_COPY], participants="invalid_type"))
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "event_assembly_unavailable"


def test_r2_derive_explicit_empty_assembly_is_inconsistent() -> None:
    row = _derive_one(_derive_payload(
        coproducts=[_COPY], participants=[]))
    assert row["status"] == "inconsistent"
    assert row["assembly"]["event_product_components"] == 0


def test_r2_derive_known_empty_declaration_is_not_applicable() -> None:
    row = _derive_one(_derive_payload(
        declared="", executed="", participants=[], expectation=""))
    assert row["status"] == "not_applicable"
    assert row["applicability"] == "not_applicable"


def test_r2_derive_legal_complete_and_contradiction() -> None:
    legal = _derive_one(_derive_payload(
        coproducts=[_COPY],
        participants=[{"state_ref": "p1", "side": "product"},
                      {"state_ref": "c1", "side": "product"}],
        state_smiles={"c1": _COPY}))
    assert legal["status"] == "consistent"
    contradiction = _derive_one(_derive_payload(executed=_OTHER))
    assert contradiction["status"] == "inconsistent"
    assert contradiction["inconsistency_subclass"] == "principal_absent"


def test_r2_derive_parse_failure_is_unknown() -> None:
    row = _derive_one(_derive_payload(
        declared="not-a-smiles", expectation="not-a-smiles"))
    assert row["status"] == "unknown"
    assert row["unknown_reason"] == "principal_unparseable"
    assert "principal_unparseable" in \
        row["proof_scope"]["unverified_ranges"]


# ---- R3:stereo_only 必须证明只剩立体差;同位素差不得混入 ----

def test_r3_reconcile_pure_isotope_is_unspecified_not_stereo() -> None:
    row = _reconcile(
        _disclosure(_ISOTOPE), _execution(_MAIN),
        expectation=_ISOTOPE)
    assert row["status"] == "inconsistent"
    assert row["inconsistency_subclass"] == \
        "principal_isomeric_unspecified"
    assert "principal_isomeric_unspecified_diff" in row["reason_codes"]
    assert row["component_relation"]["principal_in_executed"] is False
    assert row["component_relation"][
        "principal_nonstereo_in_executed"] is False
    assert row["component_relation"][
        "principal_nonisomeric_in_executed"] is True


def test_r3_reconcile_connection_difference_is_principal_absent() -> None:
    row = _reconcile(
        _disclosure(_MAIN), _execution(_OTHER), expectation=_MAIN)
    assert row["inconsistency_subclass"] == "principal_absent"
    assert row["component_relation"][
        "principal_nonstereo_in_executed"] is False
    assert row["component_relation"][
        "principal_nonisomeric_in_executed"] is False


def test_r3_derive_stereo_isotope_connection_matrix() -> None:
    stereo = _derive_one(_derive_payload(
        declared=_STEREO_A, executed=_STEREO_B, expectation=_STEREO_A))
    assert stereo["status"] == "inconsistent"
    assert stereo["inconsistency_subclass"] == "principal_stereo_only"
    assert stereo["component_relation"][
        "principal_nonstereo_in_executed"] is True

    isotope = _derive_one(_derive_payload(
        declared=_ISOTOPE, executed=_MAIN, expectation=_ISOTOPE))
    assert isotope["status"] == "inconsistent"
    assert isotope["inconsistency_subclass"] == \
        "principal_isomeric_unspecified"
    assert isotope["component_relation"][
        "principal_nonstereo_in_executed"] is False
    assert isotope["component_relation"][
        "principal_nonisomeric_in_executed"] is True

    connection = _derive_one(_derive_payload(
        declared=_MAIN, executed=_OTHER, expectation=_MAIN))
    assert connection["inconsistency_subclass"] == "principal_absent"
    assert connection["component_relation"][
        "principal_nonisomeric_in_executed"] is False

    unknown = _derive_one(_derive_payload(
        declared="not-a-smiles", expectation="not-a-smiles"))
    assert unknown["status"] == "unknown"
    assert unknown["unknown_reason"] == "principal_unparseable"


def _synthetic_native_payload() -> dict:
    """最小原生结果形状(事件/action/report/states),不落盘。"""
    spec_a = {
        "product_smiles": "CCO", "coproducts": [],
        "edits": [{"op": "noop"}],
        "expectation": {"target_smiles": "CCO"},
        "declared_copy_components": [],
        "compile": {"compiler_version": "synthetic-control"},
    }
    spec_b = {
        "product_smiles": "CCO", "coproducts": [],
        "edits": [{"op": "noop"}],
        "expectation": {"target_smiles": "CCC"},
        "declared_copy_components": [],
    }
    events = [
        {"event_id": "ev-1", "created_at": "2026-01-01T00:00:01",
         "payload": {"participants": [
             {"state_ref": "p1", "side": "product"}]}},
        {"event_id": "ev-2", "created_at": "2026-01-01T00:00:02",
         "payload": {"participants": [
             {"state_ref": "p1", "side": "product"}]}},
    ]
    reports = []
    for eid, aid, product in (("ev-1", "a-1", "CCO"),
                              ("ev-2", "a-2", "CCC")):
        reports.append({
            "action_id": aid,
            "production_payload": {
                "event_id": eid, "status": "submitted",
                "action_id": aid,
                "execution": {
                    "execution_ok": True,
                    "result": {"ok": True, "product_smiles": product},
                    "tool_inputs": {"expectation": {
                        "target_smiles": product}},
                    "center_evidence": {
                        "center_match": True,
                        "strict_target_match": True,
                        "declaration_mismatch": False,
                        "proof_scope": "self_contained_recompute"},
                },
                "report_projection": {"product_ranks": [
                    {"report_rank": 1, "state_ref": "p1"}]},
            },
        })
    return {
        "run_id": "synthetic-run",
        "states": [{"state_id": "p1",
                    "payload": {"state_id": "p1",
                                "smiles_isomeric": "CCO"}}],
        "events": events,
        "search_actions": [
            {"action_id": "a-1", "payload": {
                "logical_proposal_id": "tpl-x", "spec": spec_a}},
            {"action_id": "a-2", "payload": {
                "logical_proposal_id": "novel-x", "spec": spec_b}},
        ],
        "audit_production_reports": reports,
    }


def test_derive_synthetic_payload_statuses() -> None:
    rows = derive_declared_vs_executed(
        _synthetic_native_payload(), qid_by_run_id={"synthetic-run": "q1"})
    assert len(rows) == 2
    assert rows[0]["status"] == "consistent"
    assert rows[0]["origin"] == "template"
    assert rows[0]["qid_prefix"] == "q1"
    assert rows[1]["status"] == "inconsistent"
    assert rows[1]["origin"] == "novel"
    # 无 SMILES/结构正文
    text = json.dumps(rows, ensure_ascii=False)
    assert "CCO" not in text and "CCC" not in text


def test_read_declared_vs_executed_binding() -> None:
    from pathway_v43.domain.models import content_hash

    block = declared_vs_executed_block(_synthetic_native_payload())
    payload = {"declared_vs_executed": block}
    assert read_declared_vs_executed(payload) is block
    manifest = {"diagnostic_bindings": {"declared_vs_executed": {
        "schema": block["schema"], "version": block["version"],
        "rule_version": block["rule_version"],
        "n_events": block["n_events"],
        "digest": content_hash(block)}}}
    assert read_declared_vs_executed(payload, manifest) is block
    bad = json.loads(json.dumps(manifest))
    bad["diagnostic_bindings"]["declared_vs_executed"]["digest"] = "0" * 64
    with pytest.raises(NativeExportContractError):
        read_declared_vs_executed(payload, bad)
    tampered = json.loads(json.dumps(block))
    tampered["n_events"] = 99
    with pytest.raises(NativeExportContractError):
        read_declared_vs_executed(
            {"declared_vs_executed": tampered})


# ---------------------------------------------------------------- 集成(公共链)


def _run_fixture(tmp_path: Path):
    plan = {
        "pools": {"CCO": [spec("B", "CC=O", "donor-B",
                               coproducts=["[H][H]"])]},
        "schedule_budget": {"max_select": 1},
    }
    runs_root = tmp_path / "runs"
    start(tmp_path, RUN_ID, plan)
    ledger = ledger_for(runs_root, RUN_ID)
    return runs_root, ledger


def test_build_native_result_switch_off_on(tmp_path: Path,
                                           monkeypatch) -> None:
    monkeypatch.delenv("PPV1_P0B_D6_DIAGNOSTICS", raising=False)
    runs_root, ledger = _run_fixture(tmp_path)
    endpoint = read_run_endpoint(ledger, RUN_ID)
    off = build_native_result(
        ledger, endpoint_record=endpoint,
        include_declared_vs_executed=False)
    default = build_native_result(ledger, endpoint_record=endpoint)
    on = build_native_result(
        ledger, endpoint_record=endpoint,
        include_declared_vs_executed=True)
    assert "declared_vs_executed" not in off
    assert canonical_json(off) == canonical_json(default)
    block = on["declared_vs_executed"]
    assert block["schema"] == P0B_D6_DIAGNOSTIC_SCHEMA
    assert block["n_events"] == len(on["events"])
    assert sum(block["counts"].values()) == block["n_events"]
    # 剔字段后既有事实零漂移(只差 content_digest 与新增块)
    for key in off:
        if key == "content_digest":
            continue
        assert on[key] == off[key]
    assert canonical_json(strip_declared_vs_executed(on)) == \
        canonical_json(strip_declared_vs_executed(off))
    # 导出绑定:关闭无 diagnostic_bindings,开启有且可显式读取
    off_export = export_native_result(ledger, off, runs_root / RUN_ID)
    on_export = export_native_result(ledger, on, runs_root / RUN_ID)
    off_manifest = json.loads(
        Path(off_export["manifest_path"]).read_text(encoding="utf-8"))
    on_manifest = json.loads(
        Path(on_export["manifest_path"]).read_text(encoding="utf-8"))
    on_payload = json.loads(
        Path(on_export["payload_path"]).read_text(encoding="utf-8"))
    assert "diagnostic_bindings" not in off_manifest
    assert "diagnostic_bindings" in on_manifest
    read_back = read_declared_vs_executed(on_payload, on_manifest)
    assert read_back["n_events"] == block["n_events"]
    with pytest.raises(NativeExportContractError):
        read_declared_vs_executed(on_payload, off_manifest)
