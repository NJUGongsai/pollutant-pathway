"""PPV1 S5b hwall —— AtomTool 显式氢价态墙放宽(S5b-hwall-1;
v43-atomtool-2;零网络、零金标)。

依据:v4b 交付书 §十.1 登记(显式氢价态墙 = 编译墙攻坚残留的执行
器记账假阴性,最小改动面 ~3 行)+ mimo r33 S3-b/S3-4 条款(唯一
推荐项:"它不是化学边界而是执行器记账限制";采纳条件 ①只动
numExplicitHs 记账,图中原子级 H/同位素 H 不受影响;②负控须含
"真实超价仍拒、novel 通道全量重跑";③规则文字补"键级升高伴随
显式氢消耗 = 脱氢记账语义")。

修法( ``services/atom_tool.execute_edits`` change_bond_order 分支):
键级**升高**时,变化键两端点的**括号显式氢**(numExplicitHs,
noImplicit 记账)按级差消耗(存量不足截 0)。与隐式氢原子同口径
——隐式 H 由 sanitize 按剩余价自动重算,括号原子固定记账才有此墙。
凯库勒空间外的键级词、form/break/add_atom 路径、非氢原子价态检查
零触碰;图中独立 H 原子(含同位素 [2H])是真实图原子不在记账面。

正控(EAWAG 实盘形态的合成同构 + 真实授权语料形态):
- 括号氢手性底物 single→double 消解执行成功(v4b 旧负控翻转的
  执行器层同根证明;两种对映体书写);
- 级差记账:single→triple 每端点按级差消耗 2 H;
- 非端点立体中心零触碰(仅变化键端点消耗,其余手性保留);
- recorded 通道 strict 层形态(手性二级醇→酮,双对映体)+
  甾体多手性中心形态(bt0002#r1147 实盘同构:仅 17-醇中心消解,
  其余中心保留);
- production 层(novel 同根公共链):手性底物 reaction_center_
  match/strict_target_match 均 True。

负控(mimo r33 采纳条件逐条):
- 真实超价仍拒:括号氢存量不足(1 H 撞 triple)⇒ sanitize 诚实拒;
- 括号无 H 中心(季碳)墙完整 ⇒ 拒;
- 显式氢不可洗非法编辑:form_bond/add_atom 路径不在放宽面 ⇒ 拒;
- 同位素 H([2H] 独立图原子)不受记账影响 ⇒ 拒(条件 ①);
- 非氢原子(醚 O)价态越界仍拒;
- 既有六价碳负控(w1 g9)与本文件零重复合保持(全量回归覆盖);
- EDIT_PROTOCOL_VERSION 不变(线协议零改动;不变量,父同绿)。

合成夹具与真实 298 金标零重叠(W2 既有夹具纪律:氯乙醇/乙二醇/
甾体骨架为授权语料公开记录形态;判分零 LLM)。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from pathway_v43.services.atom_tool import (  # noqa: E402
    ATOMTOOL_VERSION,
    EDIT_PROTOCOL_VERSION,
    execute_edits,
    render,
)

# v4b 既有夹具(2-氯丙醇 → 氯乙酰氯同构;与真实 298 金标零重叠)
_LHS = "[CH3:1][C@H:2]([OH:3])[Cl:4]"
_RHS = "[CH3:1][C:2](=[O:3])[Cl:4]"
_KETONE = "CC(=O)Cl"


# ================================================================ 正控

def test_hwall_bracket_h_consumed_on_bond_raise_executes() -> None:
    """正控(执行器层):括号显式氢手性中心 single→double,端点
    显式氢按级差消耗(脱氢记账语义)⇒ 执行成功;两种对映体书写
    同口径(v4b 旧价态墙负控的执行器层同根;父 HEAD 上红)。"""
    for sub in ("C[C@H](O)Cl", "C[C@@H](O)Cl"):
        cur = render(sub, "S")
        center_id = next(a for a in cur.atom_ids
                         if a.endswith("_C_") or a.split("_")[-2] == "C")
        # 中心原子 = 手性碳:取带 CIP 后缀的 ID(_R/_S)
        center_id = next(a for a in cur.atom_ids if a[-2:] in ("_R", "_S"))
        out = execute_edits(cur, [{
            "op": "change_bond_order",
            "atom1": center_id, "atom2": cur.atom_ids[2],
            "from_order": "single", "to_order": "double"}])
        assert out["ok"] is True, (sub, out)
        assert out["product_smiles"] == _KETONE, (sub, out)


def test_hwall_level_diff_consumes_two_h_on_single_to_triple() -> None:
    """正控(级差记账):single→triple 端点按级差消耗 2 H(存量足)
    ⇒ 执行成功([CH3][CH2][OH] → C#CO;两端点各耗 2 H)。"""
    cur = render("[CH3][CH2][OH]", "S")
    out = execute_edits(cur, [{
        "op": "change_bond_order",
        "atom1": "S_C_1", "atom2": "S_C_2",
        "from_order": "single", "to_order": "triple"}])
    assert out["ok"] is True, out
    assert out["product_smiles"] == "C#CO", out


def test_hwall_non_endpoint_stereocenter_untouched() -> None:
    """正控(不触碰手性判定):变化键端点之一消费显式氢消解,链上
    其余括号氢立体中心非端点 ⇒ 记账零触碰、手性标签保留(放行面
    只到端点;消毒解原子的手性由 sanitize 自然结算,非本层声明)。"""
    cur = render("C[C@H](O)[C@@H](F)Cl", "S")
    out = execute_edits(cur, [{
        "op": "change_bond_order",
        "atom1": "S_C_1", "atom2": "S_C_2_S",
        "from_order": "single", "to_order": "double"}])
    assert out["ok"] is True, out
    # 非端点立体中心(S_C_3_S,[C@@H](F)Cl)保留:产物仍带立体声明
    assert "@" in out["product_smiles"], out
    assert "Cl" in out["product_smiles"] and "F" in out["product_smiles"]


def test_hwall_recorded_channel_chiral_substrate_compiles() -> None:
    """正控(recorded 通道 strict 层形态,EAWAG bt0002#r0032 实盘
    同构 4 例):手性声明底物(两种对映体)+ 手性 donor,推断映射
    编译通过——v4b 轮曾撞 execution_failed 价态墙的 strict_exact
    形态(父 HEAD 上红)。"""
    from pathway_v43.pollutant.recorded_source import (
        compile_recorded_reaction,
    )

    for sub in ("C[C@H](O)c1ccccc1", "C[C@@H](O)c1ccccc1"):
        out = compile_recorded_reaction(
            substrate_smiles=sub,
            donor_smiles="C[C@@H](O)c1ccccc1",
            products=["CC(=O)c1ccccc1"], record_id="hwall-rec-pea")
        assert out["status"] == "compiled", (sub, out)
        assert out["spec"]["product_smiles"] == "CC(=O)c1ccccc1"
        assert out["spec"]["coproducts"] == []
        assert out["spec"]["compile"]["stereo_dissolution_applied"] == [2]


def test_hwall_steroid_multicenter_strict_form_compiles() -> None:
    """正控(EAWAG bt0002#r1147 实盘同构,甾体多手性中心):仅
    17-醇中心随 single→double 消解(显式氢消耗),其余手性中心
    键级不变零触碰 ⇒ 编译通过(v4b 轮第 5 例价态墙形态;父 HEAD
    上红)。真实授权语料公开记录形态,只读语料、零金标。"""
    from pathway_v43.pollutant.recorded_source import (
        compile_recorded_reaction,
    )

    out = compile_recorded_reaction(
        substrate_smiles=("C[C@]12CC[C@H]3[C@@H](CCC4=CC(=O)CC[C@@]43C)"
                          "[C@@H]1CC[C@@H]2O"),
        donor_smiles=("C[C@]12CC[C@H]3[C@@H](CCC4=CC(=O)CC[C@]34C)"
                      "[C@@H]1CC[C@@H]2O"),
        products=[("C[C@]12CC[C@H]3[C@@H](CCC4=CC(=O)CC[C@]34C)"
                   "[C@@H]1CCC2=O")],
        record_id="env:EAWAG-BBD:bt0002#r1147")
    assert out["status"] == "compiled", out


def test_hwall_production_layer_center_and_strict_match(tmp_path) -> None:
    """正控(production 层,novel 通道同根公共链):手性声明底物经
    真实 render→execute_edits→donor 诊断,reaction_center_match 与
    strict_target_match 均 True(条件 ②"novel 通道全量重跑"的生产
    层直测;全量回归另行覆盖 novel 全家)。"""
    from pathway_v43.pollutant.production import (
        execute_atomtool_expansion,
    )
    from pathway_v43.pollutant.s5b_compiler import compile_donor_template

    out = compile_donor_template(
        mapped_lhs=_LHS, mapped_rhs=_RHS, center_atoms=[2, 3],
        substrate_smiles="C[C@H](O)Cl", record_id="hwall-prod",
        mapping_origin="native", key_prefix="tpl")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    execution = execute_atomtool_expansion(
        substrate_smiles="C[C@H](O)Cl", tool_inputs={
            "edits": spec["edits"], "donor": spec["donor"],
            "alignment": spec["alignment"],
            "expectation": spec["expectation"]})
    assert execution["execution_ok"] is True
    assert execution["diagnostic"]["reaction_center_match"] is True
    assert execution["diagnostic"]["strict_target_match"] is True


# ================================================================ 负控

def test_hwall_clamped_overvalence_still_rejected() -> None:
    """负控(真实超价仍拒,mimo r33 条款 ②):括号氢存量 1 而
    single→triple 需耗 2 ⇒ 截 0 后键级显式价仍超限 ⇒ sanitize
    诚实拒(记账放宽不制造合法化)。"""
    cur = render("Cl[C@H](F)Br", "S")
    out = execute_edits(cur, [{
        "op": "change_bond_order",
        "atom1": "S_C_1_S", "atom2": "S_Br_1",
        "from_order": "single", "to_order": "triple"}])
    assert out["ok"] is False, out
    assert any("sanitize_failed" in r for r in out["reasons"]), out


def test_hwall_quaternary_no_h_wall_intact() -> None:
    """负控(无氢可耗):括号季碳中心(numExplicitHs=0)键级升高
    ⇒ 无记账可放,真实超价照旧 ⇒ sanitize 拒(放宽面只在"显式氢
    随键级升高消耗",不是无条件放行)。"""
    cur = render("C[C@](O)(Cl)c1ccccc1", "S")
    out = execute_edits(cur, [{
        "op": "change_bond_order",
        "atom1": "S_C_2_S", "atom2": "S_O_1",
        "from_order": "single", "to_order": "double"}])
    assert out["ok"] is False, out
    assert any("sanitize_failed" in r for r in out["reasons"]), out


def test_hwall_form_bond_not_relaxed() -> None:
    """负控(显式氢不可洗非法编辑,mimo r33 条款 ①边界):form_
    bond 路径不在放宽面 —— 括号氢手性中心再成一根新键(跨组分
    form_bond)⇒ 键数超价照旧 ⇒ sanitize 拒(放宽只随 change_
    bond_order 键级升高,新键不消耗记账氢;add_atom 路径自带的
    成键同面,均零触碰)。"""
    cur = render("C[C@H](O)Cl.N", "S")
    assert "S_N_1" in cur.atom_ids
    out = execute_edits(cur, [
        {"op": "form_bond", "atom1": "S_C_2_R", "atom2": "S_N_1"}])
    assert out["ok"] is False, out
    assert any("sanitize_failed" in r for r in out["reasons"]), out


def test_hwall_isotope_h_separate_atom_still_wall() -> None:
    """负控(同位素 H 不受影响,mimo r33 条款 ①):[2H] 是真实图
    原子(S_H_1),不在 numExplicitHs 记账面 ⇒ 键级升高后真实键数
    超价 ⇒ sanitize 诚实拒(记账放宽只及括号氢计数)。"""
    cur = render("C[C@]([2H])(O)c1ccccc1", "S")
    assert "S_H_1" in cur.atom_ids  # 同位素 H = 独立图原子
    out = execute_edits(cur, [{
        "op": "change_bond_order",
        "atom1": "S_C_2_S", "atom2": "S_O_1",
        "from_order": "single", "to_order": "double"}])
    assert out["ok"] is False, out
    assert any("sanitize_failed" in r for r in out["reasons"]), out


def test_hwall_non_hypogen_atom_valence_unchanged() -> None:
    """负控(非氢原子价态越界仍拒):醚 O(两键中性)被 single→
    double ⇒ O 价态越界与显式氢记账无关 ⇒ sanitize 拒(w1 g9
    六价碳负控的非氢同族;父 HEAD 同绿)。"""
    cur = render("[CH3][O][CH3]", "S")
    out = execute_edits(cur, [{
        "op": "change_bond_order",
        "atom1": "S_C_1", "atom2": "S_O_1",
        "from_order": "single", "to_order": "double"}])
    assert out["ok"] is False, out
    assert any("sanitize_failed" in r for r in out["reasons"]), out


def test_hwall_edit_protocol_version_unchanged() -> None:
    """不变量(线协议零改动):EDIT_PROTOCOL_VERSION 维持
    v43-editproto-2(op/字段表不动;放宽只在执行器记账语义,随
    ATOMTOOL_VERSION 承载)。父 HEAD 同绿。"""
    assert EDIT_PROTOCOL_VERSION == "v43-editproto-2"
    assert ATOMTOOL_VERSION == "v43-atomtool-2"
