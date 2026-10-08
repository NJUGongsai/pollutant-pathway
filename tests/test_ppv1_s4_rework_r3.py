"""S4 回修 r3 回归(PPV1-ISO-01:同位素 diff 并入实际净变化集)。

基线:HEAD 2ff919f(复审 R3 docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_
R3_2026-10-08.md §4 唯一阻塞)。冻结判据五 §5(冻结正文 394–396 行)
早已把实际净变化定义为"键 diff ∪ 电荷/立体/同位素变化集";本批是
**既有承诺的实现兑现**(方案 A,不改冻结正文/判定规则):

- 逐原子 isotope diff 入 deltas("isotope" 机读码)/records
  ("isotope":[before,after])/changed atoms/中心外 extra_changes/
  中心属性披露;audit 复算链(_rerun_proof_record 重跑同一 checker)
  同轴 ⇒ 中心外同位素变化按既有"中心外变化 ⇒ center False"处理,
  不再漏核后 center verified/full/R6;
- 纯同位素差异不再以 net_change_only_in_stereo_representation 误标
  "仅立体"(身份轴混谈),走真实轴(isotope delta + 中心范围判定);
  该理由码的残余语义(真·非四面体等立体表示差异)保持。

红绿口径(对直接父 2ff919f 同字节运行):
- 行为红:mixed_outside_isotope 反例在父上 center True → audit
  verified → R6 expand(生产 submitted);本文件断言 False/violated/
  R5v/非 expand;
- 字段红:isotope 披露键(records["isotope"]/extra_changes isotope
  before/after)父上不存在;
- 版本红:见 test_ppv1_profile.py / test_ppv1_s4b_export.py 的
  ppv1-profile-20 / ppv1-donor-diagnostic-10 字面量;
- 正常控保持(父绿子绿,不翻红):正常键变、原有 13C 保持、中心内
  isotope、全中心范围控制、strict False → violated、非四面体
  stereo-only → unknown。

规则级合成夹具;模型 off,无金标/封存材料。工具返回的同位素反例
用合成工具返回复现(与评审 R3 isotope_contract 同法:先真实执行
AtomTool,再只在返回通道上一致置 13C)—— 不宣称原 AtomTool 会编辑
同位素(冻结协议无该 op),不认证实验/机制。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rdkit import Chem  # noqa: E402

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    ADMISSION_RETAIN_CONDITIONAL,
    CHECK_TRANSFORMATION_CENTER,
    CHECK_VIOLATED,
    AuditContractError,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    build_chemical_state,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    PARTICIPANT_LIST_DECLARED_COMPLETE,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    COEFFICIENT_KNOWN,
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    CONDITION_KEY_OXYGEN,
    FACT_STATUS_KNOWN_PRESENT,
    REQUESTED_SCOPE_CONDITION_COMPATIBLE,
    build_condition_fact,
    build_path_context,
    build_requirement,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
    render,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
LABELED_ACETALDEHYDE = "[13CH3]C=O"
HYDROGEN = "[H][H]"
SRC = ["src:rule-iso"]
BOND_EDIT = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]


# ---------------------------------------------------------------- 夹具段


def _current(smiles: str, name: str = "S") -> dict:
    """render(评审 isotope_contract 同法;roundtrip 的往返身份门会
    拒绝同位素/非四面体表示 —— 该门属 AtomTool 表示能力边界,与本轴
    无关,诊断消费的是 render 的渲染事实)。"""
    rendered = render(smiles, name=name)
    return {"smiles": rendered.smiles,
            "atom_id_map": dict(rendered.atom_id_map)}, rendered


def _mutate_tool_result_isotope(tool_result: dict, idmap: dict,
                                atom_id: str, isotope: int) -> dict:
    """真实 tool 结果 → 合成同位素改后返回(plain/mapped 一致;
    评审 R3 isotope_contract 同法:不 patch 审核结论,不宣称原
    AtomTool 会编辑同位素 —— 冻结协议无该 op)。"""
    mutated = copy.deepcopy(tool_result)
    mapped = Chem.MolFromSmiles(mutated["product_mapped_smiles"])
    assert mapped is not None
    target_idx = idmap[atom_id]
    atom = next(a for a in mapped.GetAtoms()
                if a.GetAtomMapNum() - 1 == target_idx)
    atom.SetIsotope(isotope)
    plain = Chem.Mol(mapped)
    for a in plain.GetAtoms():
        a.SetAtomMapNum(0)
    mutated["product_mapped_smiles"] = Chem.MolToSmiles(mapped)
    mutated["product_smiles"] = Chem.MolToSmiles(plain)
    return mutated


def _donor_alignment(center_ids: list[str]):
    donor = {"center_atom_ids": [f"d{i}" for i in range(len(center_ids))]}
    mapping = dict(zip(donor["center_atom_ids"], center_ids))
    alignment = {"status": "resolved", "donor_to_current": mapping,
                 "equivalence_classes": [], "ref": "iso-align"}
    return donor, alignment


def _ethanol_bond_execution():
    current, rendered = _current(ETHANOL)
    execution = execute_edits(rendered, BOND_EDIT)
    assert execution["ok"] is True
    return current, rendered, execution


def _states(*smiles):
    return {s: build_chemical_state(s, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
            for s in smiles}


def _sub(ref):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
                       role="primary_substrate", coefficient=1,
                       coefficient_status=COEFFICIENT_KNOWN)


def _prod(ref, role="principal_product"):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT,
                       role=role, coefficient=1,
                       coefficient_status=COEFFICIENT_KNOWN)


def _hypothesis(states, sub_smi, prod_smi, coproduct=HYDROGEN):
    """CCO → <产物> + [H][H] 全氢配平假设(与评审 8 分案同构)。"""
    sub = states[sub_smi]
    prod = states[prod_smi]
    participants = [_sub(sub.state_id), _prod(prod.state_id)]
    if coproduct:
        participants.append(_prod(states[coproduct].state_id,
                                  role="coproduct"))
    return build_hypothesis(
        parent_path_id="p-iso", substrate_state_ref=sub.state_id,
        participants=participants,
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="iso-r3")


def _aerobic_context():
    return build_path_context(
        requested_scope=REQUESTED_SCOPE_CONDITION_COMPATIBLE,
        condition_facts=[
            build_condition_fact(key=CONDITION_KEY_OXYGEN,
                                 value="aerobic",
                                 status=FACT_STATUS_KNOWN_PRESENT)],
        accumulated_requirements=[
            build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC)],
        assessment_scope=["oxygen_regime"])


# ================================================== 诊断层(行为红主组)


def test_iso01_pure_isotope_real_axis_not_stereo_mislabel() -> None:
    """PPV1-ISO-01(纯同位素):CCO→[13CH3]CO 零编辑、中心声明在
    S_C_2/S_O_1 ⇒ 修复前 center None + 理由码误标"仅立体";修复后
    isotope delta 入实际净变化 ⇒ 中心外变化 ⇒ center False,理由为
    真实轴(isotope),不再冒用立体码。"""
    current, rendered = _current(ETHANOL)
    idmap = current["atom_id_map"]
    tool = execute_edits(rendered, [])
    assert tool["ok"] is True
    result = _mutate_tool_result_isotope(tool, idmap, "S_C_1", 13)
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": result["product_smiles"]},
        result=result, edits=[])
    # 身份键含同位素 ⇒ 非零净变化(不是"零变化"分支)
    assert diag.net_change_empty is False
    # 真实轴:中心外同位素变化 ⇒ center False(不再 None/立体码)
    assert diag.reaction_center_match is False
    assert diag.strict_target_match is True  # 严格目标轴仍核对
    assert diag.declaration_mismatches == []
    assert not any("net_change_only_in_stereo_representation" in x
                   for x in diag.missing_info_reasons), \
        "纯同位素差异不得再以'仅立体表示'理由码误标(身份轴混谈)"
    assert not any("no_executed_change" in x
                   for x in diag.missing_info_reasons)
    # 披露:中心外逐原子 Δ 摘要携带 isotope before/after
    outside = [e for e in diag.extra_changes
               if e["atom_id"] == "S_C_1"]
    assert outside and outside[0]["isotope"] == {"before": 0, "after": 13}
    assert "isotope" in outside[0]["delta"]


def test_iso01_mixed_outside_isotope_center_false() -> None:
    """PPV1-ISO-01 核心反例(混合):真实 AtomTool 执行 CCO 的
    C_2–O_1 single→double 后,合成返回把**中心外** S_C_1 置 13C
    (plain/mapped 一致)⇒ 修复前 center True(变化集漏同位素轴);
    修复后 S_C_1 入 changed atoms ⇒ 中心外 ⇒ center False。"""
    current, rendered, tool = _ethanol_bond_execution()
    result = _mutate_tool_result_isotope(tool, current["atom_id_map"],
                                         "S_C_1", 13)
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": result["product_smiles"]},
        result=result, edits=BOND_EDIT)
    assert diag.reaction_center_match is False  # 父上为 True(漏核)
    assert diag.strict_target_match is True
    assert diag.declaration_mismatches == []
    assert diag.missing_info_reasons == []  # 无 unknown 遮挡语义冒充
    # 中心外变化的逐原子披露:isotope 轴可见
    iso = [e for e in diag.extra_changes if e["atom_id"] == "S_C_1"]
    assert iso and iso[0]["isotope"] == {"before": 0, "after": 13}


def test_iso01_mixed_inside_center_still_true() -> None:
    """中心内 isotope(范围控制):S_O_1(在声明中心内)置 18 ⇒ 变化
    集 ⊆ 中心 ⇒ center True 保持(不因"带标签"一概拒绝)。"""
    current, rendered, tool = _ethanol_bond_execution()
    result = _mutate_tool_result_isotope(tool, current["atom_id_map"],
                                         "S_O_1", 18)
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": result["product_smiles"]},
        result=result, edits=BOND_EDIT)
    assert diag.reaction_center_match is True
    # 中心属性披露携带 isotope 轴(字段)
    entry = next(e for e in diag.center_property_deltas
                 if e["atom_id"] == "S_O_1")
    assert entry["isotope"] == [0, 18]
    assert "isotope" in entry["property_delta"]


def test_iso01_all_atoms_center_scope_control() -> None:
    """范围控制:把全部受变原子(含 S_C_1)列入中心 ⇒ center True
    (评审登记的合法范围控制,保持;不认证同位素核反应/现实可行性)。"""
    current, rendered, tool = _ethanol_bond_execution()
    result = _mutate_tool_result_isotope(tool, current["atom_id_map"],
                                         "S_C_1", 13)
    all_ids = sorted(current["atom_id_map"])
    donor, alignment = _donor_alignment(all_ids)
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": result["product_smiles"]},
        result=result, edits=BOND_EDIT)
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "direct"


def test_iso01_retained_isotope_bond_change_still_true() -> None:
    """原有 13C 保持正控:[13CH3]CO→[13CH3]C=O(标签前后相同,
    键变在中心内)⇒ center True(正常控保持,不因带标签结构一概
    拒绝)。"""
    current, rendered = _current("[13CH3]CO")
    execution = execute_edits(rendered, BOND_EDIT)
    assert execution["ok"] is True
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=BOND_EDIT)
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is True
    # isotope 轴披露存在且前后相同(13→13 无差异:不入变化集;
    # 披露键仍公开,字段红锚点)
    for entry in diag.center_property_deltas:
        assert "isotope" in entry
        assert entry["isotope"][0] == entry["isotope"][1]


def test_iso01_non_tetra_stereo_only_still_unknown_stereo_code() -> None:
    """非四面体 stereo-only 正控保持:身份不同而图轴空(无同位素差
    异)⇒ 仍走 net_change_only_in_stereo_representation + 公开
    unsupported 清单(center unknown);同位素轴入集不吞并该轴。"""
    current, rendered = _current("Cl[Pt@SP1](Br)(I)F")
    mapped = Chem.MolFromSmiles(rendered.smiles)
    for atom in mapped.GetAtoms():
        atom.SetAtomMapNum(atom.GetIdx() + 1)
    pt = next(a for a in mapped.GetAtoms() if a.GetSymbol() == "Pt")
    pt.SetIntProp("_chiralPermutation", 2)
    plain = Chem.Mol(mapped)
    for atom in plain.GetAtoms():
        atom.SetAtomMapNum(0)
    result = {"ok": True, "reasons": [], "n_edits": 0,
              "product_smiles": Chem.MolToSmiles(plain),
              "product_mapped_smiles": Chem.MolToSmiles(mapped),
              "atom_id_map": dict(rendered.atom_id_map),
              "protocol_version": "v43-editproto-2"}
    ids = {v: k for k, v in rendered.atom_id_map.items()}
    donor, alignment = _donor_alignment([ids[1]])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": result["product_smiles"]},
        result=result, edits=[])
    assert diag.reaction_center_match is None
    assert any("net_change_only_in_stereo_representation" in x
               for x in diag.missing_info_reasons)
    assert diag.stereo_comparison_unsupported_atoms  # 公开清单保留


def test_iso01_wrong_target_strict_false_still_violated() -> None:
    """strict False 正控保持:expected target 与消费结果不同 ⇒
    strict False ⇒ 中心 violated(分支优先级不因 isotope 轴改变)。"""
    current, rendered, tool = _ethanol_bond_execution()
    result = _mutate_tool_result_isotope(tool, current["atom_id_map"],
                                         "S_C_1", 13)
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": tool["product_smiles"]},
        result=result, edits=BOND_EDIT)
    assert diag.strict_target_match is False


def test_iso01_diagnostic_version_bumped() -> None:
    """契约身份登记:donor-diagnostic-9(同位素轴入实际净变化集
    ⇒ checker 语义变更须升版;profile 身份块随登记,见
    test_ppv1_profile.py)。"""
    current, rendered, tool = _ethanol_bond_execution()
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": tool["product_smiles"]},
        result=tool, edits=BOND_EDIT)
    evidence = center_evidence_from_donor_diagnostic(diag)
    assert evidence["checker_version"] == "ppv1-donor-diagnostic-10"


# ================================================== audit/admission 层


def test_iso01_mixed_outside_audit_violated_not_expand() -> None:
    """混合反例过公开 audit 重算 + 准入:修复前 center verified/
    coverage full/R6 expand;修复后中心 violated(center_mismatch_
    per_deterministic_checker)⇒ R5v retain_conditional,不 expand。"""
    current, rendered, tool = _ethanol_bond_execution()
    result = _mutate_tool_result_isotope(tool, current["atom_id_map"],
                                         "S_C_1", 13)
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": result["product_smiles"]},
        result=result, edits=BOND_EDIT)
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, LABELED_ACETALDEHYDE, HYDROGEN)
    hyp = _hypothesis(states, ETHANOL, LABELED_ACETALDEHYDE)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_VIOLATED  # 父上为 verified(过度授信)
    assert "center_mismatch_per_deterministic_checker" in \
        center.reason_code
    # 中心轴如实分轴披露:中心外 isotope 不再消失
    assert center.detail["center_match"] is False
    disposition, reasons = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert disposition == ADMISSION_RETAIN_CONDITIONAL
    assert any(r.startswith("R5v:declared_violated_other") for r in reasons)
    assert disposition != ADMISSION_EXPAND  # 不再 R6


def test_iso01_mixed_outside_tampered_true_blocked_by_recompute() -> None:
    """公开重算携带 isotope 轴:自报 center_match=True(篡改)而
    proof_record 复算为 False ⇒ integrity mismatch 结构化拒绝
    (父上复算亦为 True,篡改曾不被检出)。"""
    current, rendered, tool = _ethanol_bond_execution()
    result = _mutate_tool_result_isotope(tool, current["atom_id_map"],
                                         "S_C_1", 13)
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": result["product_smiles"]},
        result=result, edits=BOND_EDIT)
    evidence = center_evidence_from_donor_diagnostic(diag)
    evidence["center_match"] = True  # 篡改自报轴
    states = _states(ETHANOL, LABELED_ACETALDEHYDE, HYDROGEN)
    hyp = _hypothesis(states, ETHANOL, LABELED_ACETALDEHYDE)
    with pytest.raises(AuditContractError) as excinfo:
        audit_hypothesis(
            hyp, states={s.state_id: s for s in states.values()},
            context=_aerobic_context(), center_evidence=evidence)
    assert excinfo.value.detail["kind"] == \
        "center_evidence_integrity_mismatch"


def test_iso01_retained_control_audit_verified_r6() -> None:
    """原有 13C 保持 + 正常键变正控过完整链:center verified ⇒
    R6 expand(正常控保持,父绿子绿)。"""
    current, rendered = _current("[13CH3]CO")
    execution = execute_edits(rendered, BOND_EDIT)
    assert execution["ok"] is True
    donor, alignment = _donor_alignment(["S_C_2", "S_O_1"])
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=BOND_EDIT)
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states("[13CH3]CO", "[13CH3]C=O", HYDROGEN)
    hyp = _hypothesis(states, "[13CH3]CO", "[13CH3]C=O")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == "verified"
    disposition, reasons = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert disposition == ADMISSION_EXPAND
    assert any(r.startswith("R6:") for r in reasons)


# ================================================== production caller 层


def _production_setup(tmp_path: Path, name: str, substrate: str,
                      product: str):
    """评审 R3 production_probe 同构:注册 run + 状态/上下文 + 调度
    并认领 expand action(生产链真实函数,唯一替换是工具输出通道)。"""
    from unittest.mock import patch

    from pathway_v43.pollutant.production import (
        expand_hypothesis_production,
        persist_context,
        prepare_hypothesis,
    )
    from pathway_v43.pollutant.profile import build_profile_identity_block
    from pathway_v43.pollutant.queue import schedule_hypotheses
    from pathway_v43.pollutant.search import (
        SearchLedger,
        search_policy_version,
    )
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(tmp_path / f"{name}.sqlite")
    art = ArtifactStore(runs_root, name)
    ledger = SearchLedger(store, art, name)
    policy = build_profile_identity_block()
    ledger.register_search_run(name, policy)
    sub = build_chemical_state(substrate, "raw_input",
                               [{"record": f"synthetic:{name}"}])
    store.put_state(sub.to_dict())
    product_state = build_chemical_state(product, "source_product",
                                         [{"record": "synthetic:product"}])
    hydrogen = build_chemical_state(HYDROGEN, "source_product",
                                    [{"record": "synthetic:hydrogen"}])
    context = _aerobic_context()
    context_ref = persist_context(art, context)
    participants = [
        {"state_ref": sub.state_id, "side": "reactant",
         "role": "primary_substrate", "coefficient": 1,
         "coefficient_status": "known"},
        {"state_ref": product_state.state_id, "side": "product",
         "role": "principal_product", "coefficient": 1,
         "coefficient_status": "known"},
        {"state_ref": hydrogen.state_id, "side": "product",
         "role": "coproduct", "coefficient": 1,
         "coefficient_status": "known"}]
    spec = {"key": "B", "product_smiles": product,
            "coefficient": 1, "coproducts": [HYDROGEN],
            "participants": participants,
            "participant_list_status": "declared_complete",
            "transformation_ref": "synthetic:donor",
            "origin_group_key": f"synthetic:{name}",
            "edits": copy.deepcopy(BOND_EDIT),
            "donor": {"center_atom_ids": ["dC", "dO"]},
            "alignment": {"status": "resolved",
                          "donor_to_current": {"dC": "S_C_2",
                                               "dO": "S_O_1"},
                          "equivalence_classes": [],
                          "ref": "synthetic:align"},
            "expectation": {"target_smiles": product}}
    prepared = prepare_hypothesis(spec, parent_path_id="synthetic:path",
                                  substrate_state=sub,
                                  transformation_ref=spec[
                                      "transformation_ref"])
    queued = schedule_hypotheses(
        ledger, run_id=name, parent_path_id="synthetic:path",
        context_ref=context_ref, parent_search_revision=0,
        pool=[{"hypothesis_key": "B",
               "hypothesis_id": prepared["hypothesis"].hypothesis_id,
               "rank": 1,
               "payload": {"task_key": "tk-B", "spec": spec,
                           "substrate_smiles": substrate,
                           "context_ref": context_ref,
                           "parent_path_id": "synthetic:path",
                           "depth": 1}}],
        policy_version=search_policy_version(), depth=1)
    action_id = queued["selected"][0]["action_id"]
    receipt = ledger.claim_action(action_id, worker_id="synthetic:w")
    attempt_id = receipt["attempt_refs"][0]

    def _run(inject: bool):
        from unittest.mock import patch

        from pathway_v43.pollutant import production as pm

        real_execute = pm.execute_edits

        def controlled(current, edits):
            raw = real_execute(current, edits)
            changed = copy.deepcopy(raw)
            if inject:
                m = Chem.MolFromSmiles(changed["product_mapped_smiles"])
                assert m is not None
                a = next(a for a in m.GetAtoms()
                         if a.GetAtomMapNum() - 1 ==
                         current.atom_id_map["S_C_1"])
                a.SetIsotope(13)
                plain = Chem.Mol(m)
                for a in plain.GetAtoms():
                    a.SetAtomMapNum(0)
                changed["product_mapped_smiles"] = Chem.MolToSmiles(m)
                changed["product_smiles"] = Chem.MolToSmiles(plain)
            return changed

        with patch.object(pm, "execute_edits", controlled):
            return expand_hypothesis_production(
                ledger, action_id, prepared=prepared, context=context,
                worker_id="synthetic:w", attempt_id=attempt_id,
                task_key="tk-B", substrate_state=sub,
                limits=ledger._limits(name), depth=1)

    return ledger, _run


def test_iso01_production_mixed_outside_not_r6(tmp_path) -> None:
    """生产 caller 反例(评审 R3 4.3):唯一替换 execute_edits 的
    输出通道(内部先真实执行 AtomTool,混合案再一致置中心外 13C;
    donor/converter/audit/admission/writer/complete 全真实)⇒
    修复前 status=submitted + center verified/full + expand/R6;
    修复后中心 violated、非 expand/R6(按已登记策略诚实处理:
    retain_conditional 提交保留,轴结论如实)。"""
    ledger, run = _production_setup(tmp_path, "prod-iso-mixed",
                                    ETHANOL, LABELED_ACETALDEHYDE)
    output = run(inject=True)
    assert output["status"] == "submitted"
    admission = output["admission"]
    assert admission["disposition"] != ADMISSION_EXPAND  # 不再 R6
    assert not any(r.startswith("R6:") for r in admission["reasons"])
    center = next(c for c in output["audit"]["checks"]
                  if c["name"] == CHECK_TRANSFORMATION_CENTER)
    assert center["status"] == CHECK_VIOLATED  # 父上 verified
    assert center["detail"]["center_match"] is False
    assert admission["disposition"] == ADMISSION_RETAIN_CONDITIONAL
    assert any(r.startswith("R5v:declared_violated_other")
               for r in admission["reasons"])
    ledger.conn.close()


def test_iso01_production_bond_control_still_r6(tmp_path) -> None:
    """生产正控保持:无替换的真实键变化(CCO→CC=O)⇒ expand/R6/
    submitted/action done(父绿子绿)。"""
    from pathway_v43.pollutant.search import ACTION_STATUS_DONE

    ledger, run = _production_setup(tmp_path, "prod-iso-bond",
                                    ETHANOL, ACETALDEHYDE)
    output = run(inject=False)
    assert output["status"] == "submitted"
    assert output["admission"]["disposition"] == ADMISSION_EXPAND
    assert any(r.startswith("R6:") for r in output["admission"]["reasons"])
    center = next(c for c in output["audit"]["checks"]
                  if c["name"] == CHECK_TRANSFORMATION_CENTER)
    assert center["status"] == "verified"
    assert ledger.store.counts()["events"] == 1
    assert output["completed"]["completed"] is True
    ledger.conn.close()


def test_iso01_production_retained_isotope_control_still_r6(
        tmp_path) -> None:
    """生产正控保持:原有 13C 保持([13CH3]CO→[13CH3]C=O,无合成
    改标签)⇒ expand/R6/submitted(不因带标签结构一概拒绝)。"""
    ledger, run = _production_setup(tmp_path, "prod-iso-kept",
                                    "[13CH3]CO", "[13CH3]C=O")
    output = run(inject=False)
    assert output["status"] == "submitted"
    assert output["admission"]["disposition"] == ADMISSION_EXPAND
    assert any(r.startswith("R6:") for r in output["admission"]["reasons"])
    center = next(c for c in output["audit"]["checks"]
                  if c["name"] == CHECK_TRANSFORMATION_CENTER)
    assert center["status"] == "verified"
    ledger.conn.close()
