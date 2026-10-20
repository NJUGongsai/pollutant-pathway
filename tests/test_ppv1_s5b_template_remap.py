"""PPV1 S5b T-G Step D1.2 单测族 —— 确定性模板补映射(§2 任务书)。

依据:docs/TASK_T_G_D1_REMAP_IMPL_2026-10-19.md §2(规则级合成 /
编译级合成 / 回归 smoke)+ D1 探针结论(reports/ppv1_s5b/
t_g_fix_2026-10-19/d1_probe/;交集 0/17,干跑 17/17 提取层救回)。
版本承载:s5b-compiler-5→6(T-H 部署轮身份自洽门后;transform_no_change 唯一触发点;公共编译
面行为变化)+ 规则版本 template-remap-1。

控件矩阵(纯合成、零 LLM、零网络;不含题面/金标):
- 规则级(complete_template_mapping):removed-only / added-only /
  双边 / matched 不处理 / no_gap 原样回显 / 解析失败 fail_closed /
  新鲜号 > max 且按原子索引确定性递增 / 决定性与幂等;
- 编译级:tnc 合成模板(自造半映射键;离场基团未映射——不复用任何
  真实记录串)补映射后跨过提取层(compiled,带 template_remap 披露;
  另负控=补映射后后续层稳定拒[no_alignment],不得再是 tnc);
  负控=no_gap 退化模板保持原 tnc(applied=false 披露);
- P3(F,任务书 §3):**签名巧合专项负控**——两侧未映射分量签名相同
  (元素多重集+边界附着 map 同)但化学对应不同(拓扑不同);v0 配对
  视其 matched、不写号 ⇒ 不得伪装新变化:原 tnc 如实拒(fail-
  closed),测试钉死;
- 回归 smoke:非 tnc 路径(compiled/拒因)零新增键、形状不变。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    S5B_COMPILER_VERSION,
    S5B_TEMPLATE_REMAP_VERSION,
    S5bCompileError,
    _remap_pair_components,
    _remap_unmapped_components,
    complete_template_mapping,
    compile_donor_template,
    extract_mapped_transform,
)
from rdkit import Chem, RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

# 合成模板(自造;零真实记录串):removed = 离场甲基未映射(lhs 半映射键)
_TPL_REM_L = "[CH3:1][CH2:2][O:3]C"
_TPL_REM_R = "[CH3:1][CH2:2][O:3]"
# 合成模板:added = 新增氨基未映射(rhs 半映射键)
_TPL_ADD_L = "[CH3:1][CH2:2][O:3]"
_TPL_ADD_R = "[CH3:1][CH2:2][O:3]N"
# 合成模板:双边(离场甲基 + 新增氨基)
_TPL_BOTH_L = "[CH3:1][CH2:2][O:3]C"
_TPL_BOTH_R = "[CH3:1][CH2:2][O:3]N"


def _tnc_raises(lhs: str, rhs: str) -> None:
    """改前控制:同一对串在提取层必拒 transform_no_change。"""
    with pytest.raises(S5bCompileError) as excinfo:
        extract_mapped_transform(lhs, rhs)
    assert excinfo.value.reason == "transform_no_change"


# ================================================================ 规则级


def test_rule_removed_only_writes_lhs_fresh_map() -> None:
    """removed 分量(lhs 独有未映射基团)⇒ 新号写回 lhs;rhs 原串保留。"""
    r = complete_template_mapping(_TPL_REM_L, _TPL_REM_R)
    assert r["status"] == "remapped"
    assert r["rule_version"] == "template-remap-1"
    assert r["n_new_maps"] == 1
    assert r["mapped_lhs"] == "[CH3:1][CH2:2][O:3][CH3:4]"
    assert r["mapped_rhs"] == _TPL_REM_R  # 未改侧不 canonical 化
    _tnc_raises(_TPL_REM_L, _TPL_REM_R)
    t = extract_mapped_transform(r["mapped_lhs"], r["mapped_rhs"])
    assert t["removed_maps"] == [4]
    assert t["added_maps"] == []
    assert [c["map1"] for c in t["bond_changes"]] == [3]


def test_rule_added_only_writes_rhs_fresh_map() -> None:
    """added 分量(rhs 独有未映射基团)⇒ 新号写回 rhs;lhs 原串保留。"""
    r = complete_template_mapping(_TPL_ADD_L, _TPL_ADD_R)
    assert r["status"] == "remapped"
    assert r["n_new_maps"] == 1
    assert r["mapped_lhs"] == _TPL_ADD_L
    assert r["mapped_rhs"] == "[CH3:1][CH2:2][O:3][NH2:4]"
    _tnc_raises(_TPL_ADD_L, _TPL_ADD_R)
    t = extract_mapped_transform(r["mapped_lhs"], r["mapped_rhs"])
    assert t["added_maps"] == [4]
    assert t["removed_maps"] == []


def test_rule_both_sides_continuous_fresh_numbers() -> None:
    """双边:removed 先得号、added 续号(v0 计数器跨侧连续)。"""
    r = complete_template_mapping(_TPL_BOTH_L, _TPL_BOTH_R)
    assert r["status"] == "remapped"
    assert r["n_new_maps"] == 2
    assert r["mapped_lhs"] == "[CH3:1][CH2:2][O:3][CH3:4]"
    assert r["mapped_rhs"] == "[CH3:1][CH2:2][O:3][NH2:5]"
    _tnc_raises(_TPL_BOTH_L, _TPL_BOTH_R)
    t = extract_mapped_transform(r["mapped_lhs"], r["mapped_rhs"])
    assert t["removed_maps"] == [4]
    assert t["added_maps"] == [5]


def test_rule_matched_not_processed() -> None:
    """matched 不处理(v0 无对应规则):签名相同的分量不写号。

    (a) 仅 matched ⇒ no_gap 原样;(b) matched + rhs 独有分量 ⇒ 只写
    rhs 分量,matched 分量两侧原样不获号。"""
    # (a) 两侧同一未映射分量(CCC 附着 O2):签名相同 ⇒ matched ⇒ no_gap
    lhs = "[CH3:1][O:2]CCC"
    r = complete_template_mapping(lhs, lhs)
    assert r["status"] == "no_gap"
    assert r["n_new_maps"] == 0
    assert r["mapped_lhs"] == lhs and r["mapped_rhs"] == lhs
    # (b) matched(CCC@O2)+ rhs 独有 N ⇒ 仅 N 获新号 3
    rhs = "[CH3:1][O:2]CCC.N"
    r = complete_template_mapping(lhs, rhs)
    assert r["status"] == "remapped"
    assert r["n_new_maps"] == 1
    assert r["mapped_lhs"] == lhs  # lhs 无 removed ⇒ 原串保留
    mol_r = Chem.MolFromSmiles(r["mapped_rhs"])
    assert mol_r is not None
    mapped = {a.GetAtomMapNum() for a in mol_r.GetAtoms()
              if a.GetAtomMapNum()}
    assert mapped == {1, 2, 3}
    # matched 分量(CCC @ O2)保持无号:恰 3 个未映射原子(全碳)
    unmapped = [a for a in mol_r.GetAtoms() if a.GetAtomMapNum() == 0]
    assert len(unmapped) == 3
    assert all(a.GetSymbol() == "C" for a in unmapped)
    # matched 分量的链头仍挂 O2(结构关系保持)
    o2 = next(a for a in mol_r.GetAtoms() if a.GetAtomMapNum() == 2)
    assert any(n.GetAtomicNum() == 6 and n.GetAtomMapNum() == 0
               for n in o2.GetNeighbors())
    n_atom = next(a for a in mol_r.GetAtoms() if a.GetAtomMapNum() == 3)
    assert n_atom.GetSymbol() == "N" and n_atom.GetDegree() == 0


def test_rule_no_gap_echoes_input() -> None:
    """no_gap(零缺口/全映射)⇒ 两串原样回显、零新号。"""
    r = complete_template_mapping("[CH3:1][CH2:2][OH:3]",
                                  "[CH3:1][CH:2]=[O:3]")
    assert r["status"] == "no_gap"
    assert r["n_new_maps"] == 0
    assert r["mapped_lhs"] == "[CH3:1][CH2:2][OH:3]"
    assert r["mapped_rhs"] == "[CH3:1][CH:2]=[O:3]"


def test_rule_fail_closed_unparseable() -> None:
    """双侧/单侧解析失败 ⇒ fail_closed,串原样不改。"""
    r = complete_template_mapping("not_a_smiles", "[CH3:1]")
    assert r["status"] == "fail_closed"
    assert r["reason"] == "side_unparseable"
    assert r["n_new_maps"] == 0
    assert r["mapped_lhs"] == "not_a_smiles"
    assert r["rule_version"] == S5B_TEMPLATE_REMAP_VERSION
    r2 = complete_template_mapping("[CH3:1]", "also_not_smiles")
    assert r2["status"] == "fail_closed"


def test_rule_fresh_numbers_above_max_and_index_ordered() -> None:
    """新鲜号从 max(双侧现有号)+1 起;分量内按原子索引排序递增。"""
    # 链状分量:lhs [O:9]CCC 的未映射 idx 2,3,4(索引序 = 链序)
    r = complete_template_mapping("[CH3:3][O:9]CCC", "[CH3:3][O:9]CC")
    assert r["status"] == "remapped"
    mol = Chem.MolFromSmiles(r["mapped_lhs"])
    assert mol is not None
    by_map = {a.GetAtomMapNum(): a for a in mol.GetAtoms()
              if a.GetAtomMapNum()}
    # lhs 分量获 10,11,12(> 现有 max 9);rhs 分量续 13,14
    assert set(by_map) >= {3, 9, 10, 11, 12}
    o9 = by_map[9]
    c10 = next(n for n in o9.GetNeighbors() if n.GetAtomMapNum() == 10)
    nb10 = {n.GetAtomMapNum() for n in c10.GetNeighbors()}
    nb11 = {n.GetAtomMapNum() for n in by_map[11].GetNeighbors()}
    nb12 = {n.GetAtomMapNum() for n in by_map[12].GetNeighbors()}
    # 分量内按原子索引(链序)递增:10-11-12 沿链、10 挂 O9
    assert nb10 == {9, 11} and nb11 == {10, 12} and nb12 == {11}
    assert all(m > 9 for m in (10, 11, 12))
    mol_r = Chem.MolFromSmiles(r["mapped_rhs"])
    rhs_maps = {a.GetAtomMapNum() for a in mol_r.GetAtoms()
                if a.GetAtomMapNum()}
    assert rhs_maps == {3, 9, 13, 14}  # 续号:removed 先,added 后
    assert r["n_new_maps"] == 5


def test_rule_deterministic_and_idempotent() -> None:
    """同输入两次调用逐字节同;对已补串再调用 = no_gap 原样返回。"""
    r1 = complete_template_mapping(_TPL_BOTH_L, _TPL_BOTH_R)
    r2 = complete_template_mapping(_TPL_BOTH_L, _TPL_BOTH_R)
    assert r1 == r2
    r3 = complete_template_mapping(r1["mapped_lhs"], r1["mapped_rhs"])
    assert r3["status"] == "no_gap"
    assert r3["mapped_lhs"] == r1["mapped_lhs"]
    assert r3["mapped_rhs"] == r1["mapped_rhs"]
    r4 = complete_template_mapping(r1["mapped_lhs"], r1["mapped_rhs"])
    assert r4 == r3


# ================================================================ 编译级


def test_compile_tnc_synthetic_remaps_to_compiled() -> None:
    """tnc 合成模板(离场基团未映射)补映射后跨过提取层:compiled +
    template_remap 披露(applied=true / n_new_maps)。"""
    _tnc_raises(_TPL_REM_L, _TPL_REM_R)  # 改前控制:提取层必拒
    out = compile_donor_template(
        mapped_lhs=_TPL_REM_L, mapped_rhs=_TPL_REM_R,
        center_atoms=[], substrate_smiles="CCOC",
        record_id="d12-syn-removed")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["template_remap"] == {
        "applied": True, "rule_version": "template-remap-1",
        "n_new_maps": 1}
    assert spec["edits"] == [{"op": "break_bond", "atom1": "S_O_1",
                              "atom2": "S_C_3"}]
    assert spec["expectation"]["target_smiles"] == "C.CCO"
    assert spec["product_smiles"] == "C"
    assert spec["coproducts"] == ["CCO"]
    assert spec["compile"]["compiler_version"] == "s5b-compiler-6"


def test_compile_remap_applied_later_layer_stable_reject() -> None:
    """补映射已生效但后续层稳定拒(底物不含中心)⇒ no_alignment,
    不得再是 transform_no_change;detail 附 applied=true 披露。"""
    out = compile_donor_template(
        mapped_lhs=_TPL_REM_L, mapped_rhs=_TPL_REM_R,
        center_atoms=[], substrate_smiles="c1ccccc1",
        record_id="d12-syn-noalign")
    assert out["status"] == "unsupported"
    assert out["reason"] == "no_alignment"
    assert out["reason"] != "transform_no_change"
    assert out["detail"]["template_remap"] == {
        "applied": True, "rule_version": "template-remap-1",
        "n_new_maps": 1}


def test_compile_negative_no_gap_degenerate_stays_tnc() -> None:
    """负控:no_gap 退化模板(全映射恒等)保持**原** tnc 拒因;
    detail 附 applied=false 披露(区分「未应用」)。"""
    lhs = "[CH3:1][CH2:2][OH:3]"
    out = compile_donor_template(
        mapped_lhs=lhs, mapped_rhs=lhs, center_atoms=[],
        substrate_smiles="CCO", record_id="d12-syn-degenerate")
    assert out["status"] == "unsupported"
    assert out["reason"] == "transform_no_change"
    assert out["detail"]["template_remap"] == {
        "applied": False, "rule_version": "template-remap-1",
        "n_new_maps": 0}


def test_signature_coincidence_fail_closed() -> None:
    """P3(F,任务书 §3)——签名巧合专项负控:两侧未映射分量**签名
    相同**(元素多重集 + 边界附着 map 同)但**化学对应不同**(拓扑
    不同)。v0 按签名视其 matched、不写号 ⇒ **错误映射不得伪装新
    变化**:原 tnc 如实拒(fail-closed),机读披露 applied=false;
    测试钉死(含签名相同/结构不同的机械前置证明)。"""
    lhs = "[CH3:1][O:2]CCCO"    # O2-C-C-C-O 直链挂 O2
    rhs = "[CH3:1][O:2]C(C)CO"  # O2-C(-C)-C-O 支链挂 O2
    # 机械前置:两侧未映射分量签名确实相同(元素多重集 + 边界元组)
    sig_l = [c["signature"] for c in
             _remap_unmapped_components(Chem.MolFromSmiles(lhs))]
    sig_r = [c["signature"] for c in
             _remap_unmapped_components(Chem.MolFromSmiles(rhs))]
    assert len(sig_l) == 1 and sig_l == sig_r
    paired = _remap_pair_components(
        _remap_unmapped_components(Chem.MolFromSmiles(lhs)),
        _remap_unmapped_components(Chem.MolFromSmiles(rhs)))
    assert len(paired["matched"]) == 1
    assert not paired["removed"] and not paired["added"]
    # 机械前置:化学对应不同(去 map 后 canonical 不同 ⇒ 拓扑不同)
    def _strip(s: str) -> str:
        m = Chem.MolFromSmiles(s)
        for a in m.GetAtoms():
            a.SetAtomMapNum(0)
        return Chem.MolToSmiles(m)
    assert _strip(lhs) != _strip(rhs)
    # 规则级:matched 不处理 ⇒ no_gap、零新号、串原样
    r = complete_template_mapping(lhs, rhs)
    assert r["status"] == "no_gap"
    assert r["n_new_maps"] == 0
    assert r["mapped_lhs"] == lhs and r["mapped_rhs"] == rhs
    # 编译级:如实拒 = 原 tnc(不得伪装新变化/不得误编译)
    _tnc_raises(lhs, rhs)
    out = compile_donor_template(
        mapped_lhs=lhs, mapped_rhs=rhs, center_atoms=[],
        substrate_smiles="COCCCO", record_id="d12-syn-coincidence")
    assert out["status"] == "unsupported"
    assert out["reason"] == "transform_no_change"
    assert out["detail"]["template_remap"] == {
        "applied": False, "rule_version": "template-remap-1",
        "n_new_maps": 0}


# ================================================================ 回归 smoke


def test_regression_nontnc_paths_zero_new_keys() -> None:
    """非 tnc 路径零新增键(smoke):compiled 与非 tnc 拒因与改前同形。"""
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[], substrate_smiles="CCO",
        record_id="d12-syn-nontnc")
    assert out["status"] == "compiled"
    assert "template_remap" not in out["spec"]
    assert "template_remap" not in out["spec"]["compile"]
    # 非 tnc 拒因(解析失败):detail 形状与改前同(零新增键)
    out_bad = compile_donor_template(
        mapped_lhs="not_a_smiles", mapped_rhs="[CH3:1]",
        center_atoms=[], substrate_smiles="CCO",
        record_id="d12-syn-bad")
    assert out_bad["status"] == "unsupported"
    assert out_bad["reason"] == "lhs_unparseable"
    assert sorted(out_bad["detail"]) == ["side", "smiles"]
    # 非 tnc 拒因(重复 map):pre-flight 非 tnc 异常立即重抛,零触碰
    out_dup = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:1]", mapped_rhs="[CH3:1][CH2:2]",
        center_atoms=[], substrate_smiles="CC",
        record_id="d12-syn-dup")
    assert out_dup["status"] == "unsupported"
    assert out_dup["reason"].startswith("duplicate_map_no")
    assert "template_remap" not in out_dup["detail"]


def test_versions_registered() -> None:
    """版本登记:s5b-compiler-6(补映射接线+产物侧身份自洽门)+
    template-remap-1(规则)。"""
    assert S5B_COMPILER_VERSION == "s5b-compiler-6"
    assert S5B_TEMPLATE_REMAP_VERSION == "template-remap-1"