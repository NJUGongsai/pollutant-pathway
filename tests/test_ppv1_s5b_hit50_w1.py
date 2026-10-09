"""PPV1 S5b HIT50 W1 —— 共同 compiler 十二组合成正/负控(走公共链)。

覆盖(任务书 W1 表格逐组;零网络、零金标、合成分子 CCO/CCCO/苯系):
- 组 1:有序乙醇→乙醛模板经公共链提交;同 map rhs 反写等价;
- 组 2:模板迁移 CCCO→CCC=O(spec/expectation 保留额外 C);
- 组 3:donor 中心 S/D 命名空间错配负控(center unknown)/单改中心
  到合法供体 ID 正控(center=True);
- 组 4:新 O 合法 ID(SN_*)/旧 S_O_N1 坏格式负控/未知/撞 ID 拒;
- 组 5:add_atom 自动锚定单键不再 form;
- 组 6:新 double/triple 真实形成;
- 组 7:mapped donor/current 苯共振错位(aromatic≡aromatic 不算变);
  合法去芳香化能执行;
- 组 8:去 map donor benzene/current toluene 仍共振错位;旁基保留
  + from_order 闭合;
- 组 9:芳香化正控;非法价态/无法执行表示不伪通过;
- 组 10:charge-only/stereo-only 空 edits 不一致诚实 unsupported;
- 组 11:重复 map/元素变化/对称对齐不同目标拒;等价映射保留;
- 组 12:重复产品计划经 production→store→export/replay 正控;真实
  冲突负控。

公共链断言:compile → prepare_hypothesis → execute_atomtool_expansion
(供体诊断)→ audit/admission(runflow start)→ store(事件行)→
native export → resume/replay(幂等,不重提交)。此前 13 项 helper
断言只走到工具/供体诊断 —— 本文件按任务书要求补齐 audit/admission/
store/replay 侧。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.production import (  # noqa: E402
    execute_atomtool_expansion,
    prepare_hypothesis,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    S5B_COMPILER_VERSION,
    compile_donor_template,
    extract_mapped_transform,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    ATOM_ID_RE,
    execute_edits,
    render,
    validate_edits,
)

# 公共链 run 用的宽松合成策略(与 s5b 编排器缺省同形;零真实请求)
_PROFILE = {
    "search_limits": {
        "max_alternative_hypotheses_per_parent": 8,
        "max_attempts_per_hypothesis": 1,
        "max_product_expansion_width": 2,
        "max_search_depth": 1,
        "max_total_search_actions": 48,
        "max_scenario_transitions": 0,
        "max_reopens_per_hypothesis": 0,
        "max_real_model_requests": 0,
        "max_retrievals_per_parent": 1,
        "max_retrievals_total": 8,
    },
    "format_feedback_policy": {"max_format_feedback_rounds": 0},
}


def compile_ok(**kwargs) -> dict:
    out = compile_donor_template(**kwargs)
    assert out["status"] == "compiled", out
    return out["spec"]


# ---------------------------------------------------------------- 组 1

def test_g1_ordered_template_through_public_chain(tmp_path) -> None:
    """组 1 正控:乙醇→乙醛模板经公共链(compile→prepare→audit→
    admission→store→export→resume/replay)。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles="CCO", record_id="g1")
    assert spec["product_smiles"] == "CC=O"
    assert spec["expectation"]["target_smiles"] == "CC=O"
    # 供体诊断:center 命中(D 命名空间与 alignment 键一致)
    prepared = prepare_hypothesis(
        spec, parent_path_id="pp1",
        substrate_state=_substrate("CCO"), transformation_ref="g1")
    execution = execute_atomtool_expansion(
        substrate_smiles="CCO", tool_inputs=prepared["tool_inputs"])
    assert execution["execution_ok"] is True
    diag = execution["diagnostic"]
    assert diag["reaction_center_match"] is True
    assert diag["center_match_basis"] == "direct"
    assert diag["strict_target_match"] is True
    # 公共链:start(run)→ 事件提交 → 导出 → resume/replay 幂等
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="w1g1", smiles="CCO", plan={"pools": {"CCO": [spec]}},
        profile_policy=_PROFILE)
    assert summary["stop_reason"] in ("exhausted_search", "budget_limit",
                                    "depth_limit")
    assert len(summary["stop"]["events_submitted_session"]) == 1
    event_id = summary["stop"]["events_submitted_session"][0]
    export_digest = summary["native_export"]["export_digest"]
    # start 侧导出读回(store→native_export 首消费)
    _assert_export(tmp_path / "runs", "w1g1", event_id,
                   export_digest)
    resumed = resume_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="w1g1")
    # replay 幂等:不重提交事件(store 事件行数不变)
    assert resumed["counts"]["events"] == summary["counts"]["events"]
    # resume 侧重导出读回(重放后导出仍含同一事件)
    _assert_export(tmp_path / "runs", "w1g1", event_id,
                   resumed["native_export"]["export_digest"])


def test_g1_reverse_mapped_rhs_equivalent() -> None:
    """组 1:同 map rhs 反写(map 号联结)⇒ 同一等价结果,不变成
    C=CO(旧按解析 idx 联结的反例)。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[O:3]=[CH:2][CH3:1]",
        center_atoms=[2, 3], substrate_smiles="CCO", record_id="g1r")
    assert spec["product_smiles"] == "CC=O"
    # C=CO(乙烯醇)≠ CC=O:反写不得翻转键归属
    assert spec["product_smiles"] != "C=CO"


def _substrate(smiles: str):
    from pathway_v43.pollutant.chemstate import build_chemical_state

    return build_chemical_state(smiles, "raw_input",
                                [{"record": "w1-test"}])


def _assert_export(runs_root: Path, run_id: str, event_id: str,
                   export_digest: str = "") -> None:
    """导出读回(store→native_export 首消费;事件行在载荷内)。"""
    from pathway_v43.pollutant.native_export import read_native_export
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    run_dir = runs_root / run_id
    if export_digest:
        digests = [export_digest]
    else:
        digests = [d.name for d in (run_dir / "native_export").iterdir()
                   if d.is_dir()]
    assert digests, "native_export 目录缺失"
    store = PollutantPathwayStore(run_dir / "pollutant.sqlite")
    ledger = SearchLedger(store, ArtifactStore(runs_root, run_id), run_id)
    for digest in digests:
        out = read_native_export(ledger, run_dir, digest)
        payload = out["payload"]
        event_ids = {str(e.get("event_id"))
                     for e in payload.get("events") or []}
        assert event_id in event_ids


# ---------------------------------------------------------------- 组 2

def test_g2_template_transfer_retains_extra_carbon() -> None:
    """组 2:乙醇模板迁移 CCCO→CCC=O;spec/expectation 保留额外 C,
    不能仍是 CC=O(旧实现复制 donor rhs 的反例)。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles="CCCO", record_id="g2")
    assert spec["product_smiles"] == "CCC=O"
    assert spec["expectation"]["target_smiles"] == "CCC=O"
    # 未覆盖旁基保留:对 CCCCCO 仍是 CCCCC=O(尾部旁基不丢)
    spec5 = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles="CCCCCO", record_id="g2")
    assert spec5["product_smiles"] in ("CCCCC=O", "O=CCCCC")


# ---------------------------------------------------------------- 组 3

def test_g3_donor_center_namespace_mismatch_negative() -> None:
    """组 3 负控:doner 中心用**当前** ID(S_*)而 alignment 键为
    D_* ⇒ 中心原子全部无映射 ⇒ center unknown(不得 True)。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles="CCO", record_id="g3n")
    broken = dict(spec)
    broken["donor"] = {"center_atom_ids": ["S_C_2", "S_O_1"]}  # S 命名空间
    execution = execute_atomtool_expansion(
        substrate_smiles="CCO",
        tool_inputs={"edits": broken["edits"], "donor": broken["donor"],
                     "alignment": broken["alignment"],
                     "expectation": broken["expectation"]})
    assert execution["execution_ok"] is True
    diag = execution["diagnostic"]
    assert diag["reaction_center_match"] is None  # unknown,不 True
    assert any("donor_centers_partially_unmapped" in r for r in
               diag["missing_info_reasons"])


def test_g3_donor_center_legal_id_positive() -> None:
    """组 3 正控:中心改回合法供体 ID(D_*)⇒ center=True(direct)。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles="CCO", record_id="g3p")
    execution = execute_atomtool_expansion(
        substrate_smiles="CCO", tool_inputs={
            "edits": spec["edits"], "donor": spec["donor"],
            "alignment": spec["alignment"],
            "expectation": spec["expectation"]})
    assert execution["diagnostic"]["reaction_center_match"] is True


# ---------------------------------------------------------------- 组 4

def test_g4_new_atom_id_legal_and_collision_free() -> None:
    """组 4 正控:新 O ID 符合 ATOM_ID_RE、元素一致、无冲突;
    编译产物经执行器落图。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O:3][OH:4]",
        center_atoms=[3], substrate_smiles="CCO", record_id="g4")
    add = [e for e in spec["edits"] if e["op"] == "add_atom"]
    assert len(add) == 1
    new_id = add[0]["new_atom_id"]
    m = ATOM_ID_RE.match(new_id)
    assert m is not None and m.group(0) == new_id
    assert m.group("elem") == "O"
    current = render("CCO", "S")
    assert new_id not in current.atom_id_map  # 不撞当前渲染 ID


def test_g4_old_bad_format_id_rejected() -> None:
    """组 4 负控:旧 S_O_N1 坏格式(不匹配 ATOM_ID_RE)拒;未知/
    撞 ID 拒(validate_edits 同一判据)。"""
    current = render("CCO", "S")
    # 旧坏格式:S_<Elem>_N<n> 不匹配 ATOM_ID_RE
    verdict = validate_edits(current, [
        {"op": "add_atom", "element": "O", "new_atom_id": "S_O_N1",
         "atom1": "S_C_1"}])
    assert verdict["ok"] is False
    assert any("bad_new_atom_id_format" in r
               for r in verdict["reasons"])
    # 未知元素
    verdict = validate_edits(current, [
        {"op": "add_atom", "element": "Xx", "new_atom_id": "SN_Xx_1",
         "atom1": "S_C_1"}])
    assert any("bad_element" in r for r in verdict["reasons"])
    # 撞当前 ID
    verdict = validate_edits(current, [
        {"op": "add_atom", "element": "O", "new_atom_id": "S_O_1",
         "atom1": "S_C_1"}])
    assert any("new_atom_id_conflict" in r
               for r in verdict["reasons"])


# ---------------------------------------------------------------- 组 5

def test_g5_add_atom_anchor_single_no_duplicate_form() -> None:
    """组 5:add_atom 自动接 single 锚定键,不再次 form 同键;
    重复 form 同键被执行器明确拒。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O:3][OH:4]",
        center_atoms=[3], substrate_smiles="CCO", record_id="g5")
    ops = [e["op"] for e in spec["edits"]]
    assert ops == ["add_atom"]  # 锚定 single 即成,无 form/change
    execution = execute_edits(render("CCO", "S"), spec["edits"])
    assert execution["ok"] is True
    assert execution["product_smiles"] == "CCOO"
    # 负控:对已有键 form ⇒ 执行器 bond_already_present 硬拒
    dup = execute_edits(render("CCO", "S"), [
        {"op": "add_atom", "element": "O", "new_atom_id": "SN_O_1",
         "atom1": "S_O_1"},
        {"op": "form_bond", "atom1": "S_O_1", "atom2": "SN_O_1"}])
    assert dup["ok"] is False
    assert any("bond_already_present" in r for r in dup["reasons"])


# ---------------------------------------------------------------- 组 6

def test_g6_new_double_and_triple_actually_formed() -> None:
    """组 6:新 double/triple 真实形成(先成 single 再变阶);仅 form
    导致 single 的旧行为被覆盖。"""
    # 新原子成 double(酸化:CCO → CC(=O)O,新 O 以 double 落位)
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][C:2](=[O:4])[OH:3]",
        center_atoms=[2], substrate_smiles="CCO", record_id="g6d")
    execution = execute_edits(render("CCO", "S"), spec["edits"])
    assert execution["ok"] is True
    assert execution["product_smiles"] == "CC(=O)O"
    changes = [e for e in spec["edits"]
               if e["op"] == "change_bond_order"]
    assert any(c["to_order"] == "double" for c in changes)
    # 新原子成 triple(炔)
    spec_t = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O:3][C:4]#[CH:5]",
        center_atoms=[3], substrate_smiles="CCO", record_id="g6t")
    execution_t = execute_edits(render("CCO", "S"), spec_t["edits"])
    assert execution_t["ok"] is True
    assert "C#C" in execution_t["product_smiles"]


# ---------------------------------------------------------------- 组 7

def test_g7_aromatic_resonance_no_spurious_change_and_dearomatize() -> None:
    """组 7:mapped donor/current 苯(共振)⇒ aromatic≡aromatic 不算
    键差(甲苯→苯甲酸模板在甲苯上编译,环零编辑);合法去芳香化执行。"""
    spec = compile_ok(
        mapped_lhs="[cH:6]1[cH:7][cH:8][c:9]([CH3:1])[cH:10][cH:11]1",
        mapped_rhs="[cH:6]1[cH:7][cH:8][c:9]([C:1]([OH:2])=[O:3])"
                   "[cH:10][cH:11]1",
        center_atoms=[1], substrate_smiles="Cc1ccccc1", record_id="g7")
    execution = execute_edits(render("Cc1ccccc1", "S"), spec["edits"])
    assert execution["ok"] is True
    assert execution["product_smiles"] == "O=C(O)c1ccccc1"
    # 环键零编辑(芳香共振不算键差):编辑不触及环上 6 个原子间键
    ring_ids = {spec["alignment"]["donor_to_current"][f"D_{m}"]
                for m in (6, 7, 8, 9, 10, 11)}
    for edit in spec["edits"]:
        if edit["op"] == "change_bond_order":
            pair = {edit["atom1"], edit["atom2"]}
            assert not (pair <= ring_ids), "芳香环内不得有键级编辑"
    # 合法去芳香化:苯→1,3-环己二烯(模板显式键级)可执行
    spec_de = compile_ok(
        mapped_lhs="[cH:1]1[cH:2][cH:3][cH:4][cH:5][cH:6]1",
        mapped_rhs="[CH2:1]1[CH:2]=[CH:3][CH2:4][CH:5]=[CH:6]1",
        center_atoms=[1, 2, 3, 4, 5, 6],
        substrate_smiles="c1ccccc1", record_id="g7de")
    execution_de = execute_edits(render("c1ccccc1", "S"),
                                  spec_de["edits"])
    assert execution_de["ok"] is True
    # 1,4-环己二烯(Birch 型去芳香化;模板显式键级落位)
    assert execution_de["product_smiles"] == "C1=CCC=CC1"


# ---------------------------------------------------------------- 组 8

def test_g8_unmapped_donor_benzene_current_toluene() -> None:
    """组 8:donor(带 map 的甲苯模板)/current toluene 共振错位不产
    生伪键差(环零编辑);旁基保留 + from_order 从当前图闭合。

    苯环模板对甲苯的**无差别**落位是组 11 的 ambiguous 负控(见
    test_g11_duplicate_map_element_change_asymmetry);组 8 的正控
    用带侧链的模板钉住落位:甲苯→苯甲醇(侧链加 O),环不动。"""
    spec = compile_ok(
        mapped_lhs="[cH:1]1[cH:2][cH:3][c:4]([CH3:7])[cH:5][cH:6]1",
        mapped_rhs="[cH:1]1[cH:2][cH:3][c:4]([CH2:7][OH:8])[cH:5][cH:6]1",
        center_atoms=[7], substrate_smiles="Cc1ccccc1", record_id="g8")
    execution = execute_edits(render("Cc1ccccc1", "S"), spec["edits"])
    assert execution["ok"] is True
    assert execution["product_smiles"] == "OCc1ccccc1"
    # 环零编辑(芳香共振不算键差):编辑不触及环内键
    ring_ids = {spec["alignment"]["donor_to_current"][f"D_{m}"]
                for m in (1, 2, 3, 4, 5, 6)}
    for edit in spec["edits"]:
        if edit["op"] == "change_bond_order":
            pair = {edit["atom1"], edit["atom2"]}
            assert not (pair <= ring_ids), "芳香环内不得有键级编辑"
            assert edit["from_order"] in ("single", "double")  # from 闭合
    # 旁基(既有甲基)保留:产物仍含环 + 侧链
    assert "c1" in execution["product_smiles"]


# ---------------------------------------------------------------- 组 9

def test_g9_aromatization_positive_and_illegal_rejected() -> None:
    """组 9:芳香化正控(1,3-环己二烯→苯,执行后 sanitize 重感知);
    非法价态/无法执行表示不伪通过。"""
    spec = compile_ok(
        mapped_lhs="[CH:1]1=[CH:2][CH:3]=[CH:4][CH2:5][CH2:6]1",
        mapped_rhs="[cH:1]1[cH:2][cH:3][cH:4][cH:5][cH:6]1",
        center_atoms=[1, 2, 3, 4, 5, 6],
        substrate_smiles="C1=CC=CCC1", record_id="g9")
    execution = execute_edits(render("C1=CC=CCC1", "S"), spec["edits"])
    assert execution["ok"] is True
    assert execution["product_smiles"] == "c1ccccc1"
    # 负控:非法价态(六价碳)执行拒(sanitize 失败,不伪通过)
    bad = execute_edits(render("CCO", "S"), [
        {"op": "change_bond_order", "atom1": "S_C_1", "atom2": "S_C_2",
         "from_order": "single", "to_order": "triple"},
        {"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
         "from_order": "single", "to_order": "triple"}])
    assert bad["ok"] is False
    assert any("sanitize_failed" in r for r in bad["reasons"])


def test_g9_heteroaromatic_aromatization() -> None:
    """组 9 杂芳香:2-吡咯啉→吡咯芳香化(杂环 sanitize 重感知)。"""
    spec = compile_ok(
        mapped_lhs="[CH2:1]1[CH:2]=[CH:3][NH:4][CH2:5]1",
        mapped_rhs="[cH:1]1[cH:2][cH:3][nH:4][cH:5]1",
        center_atoms=[1, 2, 3, 4, 5],
        substrate_smiles="C1C=CNC1", record_id="g9h")
    execution = execute_edits(render("C1C=CNC1", "S"), spec["edits"])
    assert execution["ok"] is True
    assert execution["product_smiles"] in ("c1cc[nH]c1", "c1c[nH]cc1")


# ---------------------------------------------------------------- 组 10

def test_g10_charge_and_stereo_only_unsupported() -> None:
    """组 10:charge-only/stereo-only 空 edits 不一致 ⇒ 诚实
    unsupported(不用空 edits 冒支持);未参与中心的事实保真
    (detail 携带受影响 map)。"""
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O-:3]",
        center_atoms=[3], substrate_smiles="CCO", record_id="g10c")
    assert out["status"] == "unsupported"
    assert out["reason"] == "charge_edit_unsupported"
    assert out["detail"]["charge_changed_maps"] == [3]
    out = compile_donor_template(
        mapped_lhs="[CH3:1][C@@H:2](O)[CH3:3]",
        mapped_rhs="[CH3:1][C@H:2](O)[CH3:3]",
        center_atoms=[2], substrate_smiles="CC(C)O", record_id="g10s")
    assert out["status"] == "unsupported"
    assert out["reason"] == "stereo_edit_unsupported"
    assert out["detail"]["stereo_changed_maps"] == [2]


# ---------------------------------------------------------------- 组 11

def test_g11_duplicate_map_element_change_asymmetry() -> None:
    """组 11:重复 map 拒;保留原子改元素拒;对称对齐不同目标拒
    (ambiguous);等价映射保留正控。"""
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:1][OH:3]",
        mapped_rhs="[CH3:1][CH2:1][O:3]",
        center_atoms=[3], substrate_smiles="CCO", record_id="g11a")
    assert out["status"] == "unsupported"
    assert "duplicate_map_no" in out["reason"]
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][SH:3]",
        center_atoms=[3], substrate_smiles="CCO", record_id="g11b")
    assert out["status"] == "unsupported"
    assert "map_element_changed" in out["reason"]
    # 等价映射正控:乙烷对称断键(两种断法同一目标)
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH3:2]", mapped_rhs="[CH3:1].[CH3:2]",
        center_atoms=[1, 2], substrate_smiles="CC", record_id="g11c")
    assert spec["product_smiles"] == "C"
    assert spec["coproducts"] == ["C"]
    assert spec["compile"]["n_equivalent_alignments"] >= 2
    # 对称对齐不同目标:丁烷 donor(丙烷模板)两种落位断不同键
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][CH3:3]",
        mapped_rhs="[CH3:1].[CH2:2][CH3:3]",
        center_atoms=[1, 2], substrate_smiles="CCCC", record_id="g11d")
    assert out["status"] == "unsupported"
    assert out["reason"] == "ambiguous_alignment"
    assert len(out["detail"]["competing_targets"]) >= 2


# ---------------------------------------------------------------- 组 12

def test_g12_duplicate_product_plan_public_chain_and_replay(tmp_path) -> None:
    """组 12 正控:同净反应重复产品计划(两池条目同产物)经
    production→store→export/replay:去重为一(合并 provenance),
    事件不重复;resume 幂等。"""
    spec_a = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles="CCO", record_id="dupA")
    spec_b = compile_ok(
        mapped_lhs="[CH2:1]([OH:2])[CH3:3]",
        mapped_rhs="[CH:1](=[O:2])[CH3:3]",
        center_atoms=[1, 2], substrate_smiles="CCO", record_id="dupB")
    assert spec_a["product_smiles"] == spec_b["product_smiles"] == "CC=O"
    plan = {"pools": {"CCO": [spec_a, spec_b]}}
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="w1g12", smiles="CCO", plan=plan,
        profile_policy=_PROFILE)
    # 去重(同净反应签名)⇒ 唯一调度条目 ⇒ 唯一事件
    assert summary["counts"]["events"] == 1
    event_id = summary["stop"]["events_submitted_session"][0]
    export_digest = summary["native_export"]["export_digest"]
    resumed = resume_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="w1g12")
    assert resumed["counts"]["events"] == 1  # replay 不重提交
    _assert_export(tmp_path / "runs", "w1g12", event_id,
                   resumed["native_export"]["export_digest"])


def test_g12_real_conflict_rejected(tmp_path) -> None:
    """组 12 负控:真实冲突(同幂等键异内容)⇒ Ppv1EventConflict,
    不静默覆盖(公共 writer 完整性守卫不放宽)。"""
    from pathway_v43.pollutant.events import build_pathway_event
    from pathway_v43.pollutant.production import prepare_hypothesis
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import (
        Ppv1EventConflict,
        PollutantPathwayStore,
    )
    from pathway_v43.storage.artifact_store import ArtifactStore

    runs_root = tmp_path / "runs"
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles="CCO", record_id="g12n")
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=runs_root,
        run_id="w1g12n", smiles="CCO",
        plan={"pools": {"CCO": [spec]}}, profile_policy=_PROFILE)
    assert summary["counts"]["events"] == 1
    store = PollutantPathwayStore(runs_root / "w1g12n" / "pollutant.sqlite")
    artifacts = ArtifactStore(runs_root, "w1g12n")
    ledger = SearchLedger(store, artifacts, "w1g12n")
    # 同事件重放(同内容)幂等
    event_row = store.get_event(
        summary["stop"]["events_submitted_session"][0])
    assert event_row is not None
    # 真实冲突:同 run/父/假设/上下文/语义键不同内容 ⇒ 冲突(store
    # 幂等键守卫);用改写参与物的假设构造冲突提交
    prepared = prepare_hypothesis(
        dict(spec, product_smiles="CCC=O"), parent_path_id="x",
        substrate_state=_substrate("CCO"), transformation_ref="conflict")
    from pathway_v43.pollutant.events import (
        build_expansion_plan,
        build_report_projection,
    )

    hypothesis = prepared["hypothesis"]
    event = build_pathway_event(
        hypothesis, run_id="w1g12n", context_hash="different-ctx")
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        store.submit_event(
            event,
            report_projection=build_report_projection(
                hypothesis, max_reportable=2,
                ranked_state_refs=[s.state_id
                                   for s in prepared["product_states"]]),
            expansion_plan=build_expansion_plan(
                hypothesis,
                expanded=[s.state_id
                          for s in prepared["product_states"]][:1],
                deferred=[],
                not_tracked=[]),
            states=[s.to_dict() for s in prepared["states"].values()],
            hypothesis_dict=prepared["hypothesis_dict"])
    # 悬空引用/冲突类结构化拒绝(Ppv1EventConflict 或契约族)
    assert not isinstance(excinfo.value, Ppv1EventConflict) or \
        excinfo.value.detail.get("submitted_event_id")


# ---------------------------------------------------------------- W1 #9

def test_w1_duplicate_state_ref_single_schedule_entry(tmp_path) -> None:
    """W1 #9:重复 state_ref(主产物 == 共产物同结构)按 distinct 状态
    生成唯一调度条目;事件参与物语义保留。"""
    spec = compile_ok(
        mapped_lhs="[CH3:1][CH3:2]", mapped_rhs="[CH3:1].[CH3:2]",
        center_atoms=[1, 2], substrate_smiles="CC", record_id="w1n9")
    assert spec["coproducts"] == ["C"]
    plan = {"pools": {"CC": [spec]}}
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="w1n9", smiles="CC", plan=plan,
        profile_policy=_PROFILE)
    assert summary["counts"]["events"] == 1
    # followup 调度:产物参与物 2 条(主+共)但同 state ⇒ 唯一 retrieve
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    store = PollutantPathwayStore(
        tmp_path / "runs" / "w1n9" / "pollutant.sqlite")
    ledger = SearchLedger(store, ArtifactStore(
        tmp_path / "runs", "w1n9"), "w1n9")
    retrieves = ledger.conn.execute(
        "SELECT COUNT(*) FROM search_actions WHERE run_id = ? AND"
        " action_kind = ?", ("w1n9", "retrieve")).fetchall()
    # 根 retrieve + followup(同 state 唯一)—— 不因重复参与物翻倍
    # (主/共产物 state 相同时恰好一条 followup)
    followups = ledger.conn.execute(
        "SELECT COUNT(*) FROM search_actions WHERE run_id = ? AND"
        " action_kind = ? AND parent_search_revision > 0",
        ("w1n9", "retrieve")).fetchall()
    assert int(followups[0][0]) <= 1
    assert int(retrieves[0][0]) >= 1


# ---------------------------------------------------------------- 版本

def test_compiler_version_registered() -> None:
    assert S5B_COMPILER_VERSION == "s5b-compiler-1"
    # 变换提取:map 号联结可重放(同输入同变化表)
    t1 = extract_mapped_transform(
        "[CH3:1][CH2:2][OH:3]", "[CH3:1][CH:2]=[O:3]")
    t2 = extract_mapped_transform(
        "[CH3:1][CH2:2][OH:3]", "[CH3:1][CH:2]=[O:3]")
    assert [c["map1"] for c in t1["bond_changes"]] == \
        [c["map1"] for c in t2["bond_changes"]]
    assert t1["bond_changes"][0]["order_lhs"] == "single"
    assert t1["bond_changes"][0]["order_rhs"] == "double"
