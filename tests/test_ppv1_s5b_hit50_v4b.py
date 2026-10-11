"""PPV1 S5b v4b —— 编译墙深层修复(P1 stereo 消解 + P2 推断映射
深层门扩展;S5b-stereo-dissolution-1 / S5b-recorded-infer-2 /
s5b-compiler-3(R1)/ s5b-recorded-source-2 / s5b-pool-policy-4;零
网络、零金标)。

**R1 回修(2026-10-10,Codex v4b 复审 §4 唯一 P1 = S5B-V4B-01 +
mimo r33 S1/S2 采纳条件)**:旧消解门把"产物不写手性标签"当成
"产物已无立体中心"——两个磷 + 一个硫合成反例(Codex 复审真实
公共链反例,证据 docs/review_evidence/ppv1_v4b_codex_2026-10-10/
stereo/)获 stereo_dissolution_applied 并提交事件,但执行产物原子
仍是**潜在**立体中心(P:Atom_Tetrahedral/未指派;S:
Atom_TrigonalBipyramidal),违反 mimo r28 E2 放行条件(执行 +
sanitize 后该原子非立体中心)。修法 = 组合:mimo r33 S2-b ② 元素
域守卫(谓词条件 0:元素域 = 碳,非碳四面体中心不消解)拦入口 +
S2-b ① 双轴复核(执行后同源复核扩展为"该原子不出现在执行产物
RDKit FindPotentialStereo 潜在立体中心清单(含未指派,仅原子轴
类型;键轴 E/Z 条目的 centeredOn 是键索引,不属本轴)")作防御。

R1 负控/正控:
- 三反例(磷×2 + 硫×1,Codex 复审 §4.2 原样输入)修后必须拒
  (stereo_edit_unsupported;父 HEAD 上 compiled ⇒ 红);
- 条件 2/条件 3 隔离负控(mimo r33 S1-c):rhs 无声明 ∧ 带标签
  原子 lhs 含非单键(亚砜形态);rhs 无声明 ∧ 断/成键落该原子
  (SN2 不翻转书写形态);
- 复核双轴负控:monkeypatch 执行产物为"无已指派标签但仍为潜在
  四面体中心"形态 ⇒ stereo_derived_mismatch 拒(父 HEAD 上旧单轴
  复核放行 ⇒ 红);键轴(E/Z)条目索引与原子索引碰撞防御;
- 碳正控(合成二级醇→酮、recorded 通道、公共链成事件)零回退
  (父 HEAD 同绿)。

依据:v4b 任务书(mimo r28 E1-E3 评审方向落地)+ v2 尸检 §1.1 L1
(EAWAG 编译墙 228 次:stereo 38 / no_structure_correspondence 116)
+ v3 交付 §五(深层门拦截 47/116:charge 24 保留边界 + no_alignment 8
+ 触顶 6 + 去芳香 3 + 歧义 1 + 产物集 1)+ v4/R1 交付(corpus 整串
面;组分级已被 S5B-V4-01 许可规则接管,本轮零触碰)。

**P1 stereo 消解(S5b-stereo-dissolution-1;R1 收口后)**——消解
谓词钉死(mimo r28 E2 窄化版 + r33 S2-b ②):0. 元素域 = 碳
∧ 1. lhs 真四面体手性标签 ∧ 2. rhs 无手性声明 ∧ 3. 该原子全部
lhs 键均单键(sp3)∧ 4. 该原子涉及的全部键变化均为
change_bond_order 型(single→double/triple,无 form/break/芳香)
∧ 5. 至少一个该型变化;执行后 rhs 立体同源复核(双轴:已指派
标签轴 + 潜在立体中心清单轴;不等 ⇒ 结构化 stereo_derived_
mismatch 拒);spec 机读诊断 stereo_dissolution_applied(语义串
带元素域/复核轴限定,r33 S2-c)。

正负控:
- 正控:二级醇氧化成酮(合成同构用例)编译通过且**公共链执行成
  事件**(compile→prepare→AtomTool→donor 诊断→audit→admission→
  store→export;参与物核对:反应物=底物、产物=酮);
- 负控族(r28 反例**标签变化形态**全拒,r33 S1-a 限定;同标签
  断/成键残留见交付书登记,不在本轮):纯立体翻转(无键级变化)、
  stereo_created(lhs 无声明→rhs 有声明)、SN2 型配体交换、非碳
  四面体中心(P/S 反例族);手性声明底物显式氢价态墙已按 v4b
  §十.1 登记 + mimo r33 S3 条款在 hwall 轮(v43-atomtool-2)放宽
  ——本文件旧负控翻转为正控(见
  test_p1_chiral_substrate_dissolution_now_compiles),价态墙
  负控面迁至 tests/test_ppv1_s5b_hwall.py;
- 同源复核负控:执行产物立体状态 ≠ rhs 声明(残留标签轴/潜在
  中心轴)⇒ stereo_derived_mismatch 结构化拒(monkeypatch 执行器
  返回残留标签/潜在中心产物的机读证明;真实化学路径下标签轴为
  防御性——hwall 放宽后显式氢随键级升高由执行器记账消耗,隐性
  标签由 sanitize 清理;潜在中心轴在碳面由谓词结构性保证,
  双轴为执行器行为漂移防御)。

**P2 推断映射深层门(S5b-recorded-infer-2)**:
- 预算升档(200/512→800/8192)+ 触顶诚实拒维持(monkeypatch
  夹具预算仍拒);
- fallback 前置必要条件 fast-fail(元素包含/原子数;零语义变化,
  无望组合不再占预算);
- 加成分支全组分枚举(旧 break 丢后续组分的候选对应;产物多重集
  gate 与落位纪律全映射评估不变)。

合成夹具与真实 298 金标零重叠(乙醇/氯乙醇级合成小分子,沿 W2
既有夹具纪律;R1 反例族为规则级合成 P/S 小分子,与真实 298 金标
零重叠,不外推 298 已发生同错)。
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
)
from pathway_v43.pollutant.recorded_source import (  # noqa: E402
    compile_recorded_reaction,
    infer_reaction_mapping,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    ScriptedRealModelAdapter,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    S5B_COMPILER_VERSION,
    compile_donor_template,
    extract_mapped_transform,
)

_PROFILE = {
    "search_limits": {
        "max_alternative_hypotheses_per_parent": 8,
        "max_attempts_per_hypothesis": 1,
        "max_product_expansion_width": 2,
        "max_search_depth": 1,
        "max_total_search_actions": 48,
        "max_scenario_transitions": 0,
        "max_reopens_per_hypothesis": 0,
        "max_real_model_requests": 4,
        "max_retrievals_per_parent": 1,
        "max_retrievals_total": 8,
    },
    "format_feedback_policy": {"max_format_feedback_rounds": 0},
}

# 合成夹具(与真实 298 金标零重叠):2-氯丙醇 → 氯丙酮(二级醇
# 氧化成酮同构;模板 lhs 手性 sp3 中心,C-O single→double 消解)
_LHS = "[CH3:1][C@H:2]([OH:3])[Cl:4]"
_RHS = "[CH3:1][C:2](=[O:3])[Cl:4]"
_SUB = "CC(O)Cl"          # 底物无手性声明(消解可执行)
_KETONE = "CC(=O)Cl"


# ================================================================ P1 正控

def test_p1_secondary_alcohol_oxidation_compiles_and_executes(
        tmp_path) -> None:
    """P1 正控:二级醇氧化成酮(合成同构用例)编译通过且执行成
    事件(公共链:compile→prepare→AtomTool→donor 诊断→audit→
    admission→store→export)。"""
    out = compile_donor_template(
        mapped_lhs=_LHS, mapped_rhs=_RHS, center_atoms=[2, 3],
        substrate_smiles=_SUB, record_id="v4b-p1-pos",
        mapping_origin="native", key_prefix="tpl")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["expectation"]["target_smiles"] == _KETONE
    assert spec["product_smiles"] == _KETONE
    assert spec["coproducts"] == []
    # 消解机读诊断(E2-④):手性 map 落账,供下游统计
    assert spec["compile"]["stereo_dissolution_applied"] == [2]
    assert "chiral_sp3_center_dissolved_by_bond_order_change" in \
        spec["compile"]["stereo_dissolution_semantics"]
    # R1(S2-c):语义串限定元素域(碳)与复核双轴
    semantics = spec["compile"]["stereo_dissolution_semantics"]
    assert "element domain: C only" in semantics
    assert "FindPotentialStereo" in semantics
    assert "non-carbon tetrahedral centers" in semantics
    # 编辑表达:仅键级变化(single→double;无立体 op、无 form/break)
    ops = [e["op"] for e in spec["edits"]]
    assert ops == ["change_bond_order"]
    # 公共链执行(production 层:中心/严格目标核对)
    execution = execute_atomtool_expansion(
        substrate_smiles=_SUB, tool_inputs={
            "edits": spec["edits"], "donor": spec["donor"],
            "alignment": spec["alignment"],
            "expectation": spec["expectation"]})
    assert execution["diagnostic"]["reaction_center_match"] is True
    assert execution["diagnostic"]["strict_target_match"] is True
    # 端到端:池 spec → runflow → 事件(store→export 参与物核对)
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="v4b-p1-chain", smiles=_SUB,
        plan={"pools": {_SUB: [dict(spec, key="tpl-v4b-p1",
                                    transformation_ref="v4b-p1-pos",
                                    origin_group_key="v4b:v4b-p1-pos",
                                    coefficient=1)]}},
        profile_policy=dict(
            _PROFILE, search_limits=dict(
                _PROFILE["search_limits"], max_real_model_requests=0)))
    assert summary["counts"]["events"] >= 1
    import sqlite3

    conn = sqlite3.connect(
        str(tmp_path / "runs" / "v4b-p1-chain" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    events = [json.loads(r["payload"]) for r in conn.execute(
        "SELECT payload FROM events")]
    states = {str(r["state_id"]): json.loads(r["payload"]) for r in
              conn.execute("SELECT state_id, payload FROM states")}
    conn.close()
    reactants, products = set(), set()
    for payload in events:
        for p in (payload.get("participants") or []):
            state = states.get(str(p.get("state_ref") or "")) or {}
            if p.get("side") == "reactant":
                reactants.add(str(state.get("smiles_isomeric") or ""))
            if p.get("side") == "product":
                products.add(str(state.get("smiles_isomeric") or ""))
    assert reactants == {_SUB}, reactants
    assert products == {_KETONE}, products


def test_p1_recorded_channel_chiral_donor_compiles() -> None:
    """P1 正控(recorded 通道同构):手性 donor + 非手性底物(cn 层
    形态)经 compile_recorded_reaction(推断映射公共判据链)编译,
    产物多重集 gate 核对一致。"""
    out = compile_recorded_reaction(
        substrate_smiles="CC(O)c1ccccc1",
        donor_smiles="C[C@@H](O)c1ccccc1",
        products=["CC(=O)c1ccccc1"], record_id="v4b-p1-rec")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["product_smiles"] == "CC(=O)c1ccccc1"
    assert spec["coproducts"] == []
    assert spec["compile"]["verified_product_set"] is True
    assert spec["compile"]["stereo_dissolution_applied"] == [2]


# ================================================================ P1 负控族

def test_p1_pure_inversion_without_bond_change_rejected() -> None:
    """负控(r28 E1 反例:纯立体翻转,无键级变化):消解谓词要求
    至少一个 single→double/triple 变化 ⇒ 维持 stereo_edit_unsupported
    (w1 g10 同款,消解后不放宽)。"""
    out = compile_donor_template(
        mapped_lhs="[CH3:1][C@@H:2](O)[CH3:3]",
        mapped_rhs="[CH3:1][C@H:2](O)[CH3:3]",
        center_atoms=[2], substrate_smiles="CC(C)O",
        record_id="v4b-p1-neg-inv")
    assert out["status"] == "unsupported"
    assert out["reason"] == "stereo_edit_unsupported"
    assert out["detail"]["stereo_changed_maps"] == [2]


def test_p1_stereo_creation_rejected() -> None:
    """负控(r28 E1-1 反例:stereo_created——lhs 无手性声明 → rhs
    有声明;手性是**新信息**,sanitize 无法从键级编辑派生):维持
    stereo_edit_unsupported,不静默产出未指定中心。"""
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH:2]([OH:3])[Cl:4]",
        mapped_rhs="[CH3:1][C@H:2]([OH:3])[Cl:4]",
        center_atoms=[2, 3], substrate_smiles=_SUB,
        record_id="v4b-p1-neg-cr")
    assert out["status"] == "unsupported"
    assert out["reason"] == "stereo_edit_unsupported"
    assert out["detail"]["stereo_changed_maps"] == [2]


def test_p1_sn2_ligand_exchange_rejected() -> None:
    """负控(r28 E1-2 反例:SN2 型配体交换——break/form 落在现存
    立体中心上;RDKit CW/CCW 锚定键表顺序,RemoveBond/AddBond 移动
    邻居序 ⇒ 标签解读翻转 = 静默对映体翻转):维持
    stereo_edit_unsupported(有机磷/硫中心水解同款形态;构型翻转
    书写)。

    S1-c 归因更正(mimo r33):本夹具 rhs 写了 ``[C@@H]``(标签
    变化),实际在谓词第 1 条(rhs 有手性声明)即拒;**条件 3
    (rhs 无声明 ∧ 断/成键落该原子)的隔离负控**见
    ``test_r1_condition3_break_form_isolation``(R1 新增)。"""
    # Cl 离去(map 4 removed)+ Br 到达(map 5 added),中心 [C@H:2]
    # 手性声明改变([C@@H]:消解谓词第 3 条不满足——form/break 落在
    # 该原子)⇒ 维持拒
    out = compile_donor_template(
        mapped_lhs="[CH3:1][C@H:2]([OH:3])[Cl:4]",
        mapped_rhs="[CH3:1][C@@H:2]([OH:3])[Br:5]",
        center_atoms=[2], substrate_smiles=_SUB,
        record_id="v4b-p1-neg-sn2")
    assert out["status"] == "unsupported"
    assert out["reason"] == "stereo_edit_unsupported"
    assert out["detail"]["stereo_changed_maps"] == [2]


def test_p1_non_tetrahedral_and_aromatic_centers_not_dissolved() -> None:
    """负控(r28 E1-4:非四面体/非 sp3 中心):lhs 原子有非单键
    (双键/芳香)或非四面体标签差异 ⇒ 维持 stereo_edit_unsupported
    (累积烯中央原子天然全双键,不消解)。

    S1-c 归因更正(mimo r33):本夹具 rhs 写了 ``[C@@H]``(标签
    变化),实际在谓词第 1 条(rhs 有手性声明)即拒;**条件 2
    (rhs 无声明 ∧ 带标签原子 lhs 含非单键)的隔离负控**见
    ``test_r1_condition2_non_single_bond_isolation``(R1 新增)。
    手性保留原子 map 4 的差异均为键级(不含立体)时不受影响。"""
    # sp2 手性声明的原子(lhs [C@H] 但含双键 ⇒ 不可能为四面体标签,
    # 构造为芳香环上的立体差异被 RDKit 解析为普通原子):
    # 用 lhs 双键 + 立体翻转组合:键级变化双键不在原子,原子差异纯立体
    out = compile_donor_template(
        mapped_lhs="[CH3:1][C@H:2]([OH:3])C=O",
        mapped_rhs="[CH3:1][C@@H:2]([OH:3])C=O",
        center_atoms=[2, 3], substrate_smiles="CC(O)C=O",
        record_id="v4b-p1-neg-nonsp3")
    assert out["status"] == "unsupported"
    assert out["reason"] == "stereo_edit_unsupported"


def test_p1_chiral_substrate_dissolution_now_compiles() -> None:
    """正控(原负控翻转,2026-10-11 hwall 轮):底物带手性声明
    ([C@H] 括号氢)的消解型模板,single→double 后显式价超限曾撞
    执行器价态墙(本测试旧形态:execution_failed 诚实拒;v4b 交付
    书 §十.1 登记 + mimo r33 S3"执行器记账假阴性,非化学边界,
    列下轮优先"条款)。本轮按登记实施 AtomTool 显式氢记账放宽
    (v43-atomtool-2):键级升高伴随端点括号显式氢按级差消耗(脱氢
    记账语义),手性声明底物与隐式氢底物同口径编译;父 HEAD 上
    compiled ⇒ 红(翻转证明)。负控面(真实超价仍拒/显式氢不可洗
    非法编辑/同位素 H 不动)见 tests/test_ppv1_s5b_hwall.py。"""
    out = compile_donor_template(
        mapped_lhs=_LHS, mapped_rhs=_RHS, center_atoms=[2, 3],
        substrate_smiles="C[C@H](O)Cl", record_id="v4b-p1-chiral")
    assert out["status"] == "compiled", out
    assert out["spec"]["expectation"]["target_smiles"] == _KETONE
    assert out["spec"]["compile"]["stereo_dissolution_applied"] == [2]


def test_p1_post_execution_homology_mismatch_rejects(monkeypatch) -> None:
    """同源复核负控(E2-③ 机读证明):执行产物在该 map 的立体状态
    ≠ rhs 声明(UNSPECIFIED)⇒ 结构化 stereo_derived_mismatch 拒
    (monkeypatch 执行器返回残留四面体标签的产物;真实化学路径下
    该门为防御性——hwall 轮后显式氢随键级升高由执行器记账消耗,
    隐性标签由 sanitize 清理)。"""
    import pathway_v43.pollutant.s5b_compiler as compiler_mod

    real_execute = compiler_mod.execute_edits

    def _tagged_execute(current, edits):
        result = dict(real_execute(current, edits))
        if result.get("ok"):
            # 防御门证明:把执行产物映射 SMILES 整体替换为"消解原子
            # (map 2)仍带四面体标签"的形态(真实化学路径下 sp2 原子
            # 的无效标签会被 MolToSmiles 清理/hwall 轮后显式氢随键级
            # 升高由执行器记账消耗,此门为 E2-③ 要求的机读核)
            result["product_mapped_smiles"] = \
                "[CH3:1][C@H:2]([OH:3])[Cl:4]"
        return result

    monkeypatch.setattr(compiler_mod, "execute_edits", _tagged_execute)
    out = compile_donor_template(
        mapped_lhs=_LHS, mapped_rhs=_RHS, center_atoms=[2, 3],
        substrate_smiles=_SUB, record_id="v4b-p1-mismatch")
    assert out["status"] == "unsupported"
    assert out["reason"] == "stereo_derived_mismatch"
    assert any("map2" in r for r in
               (out.get("detail") or {}).get("reasons") or [])
    # 复核 helper 直测:UNSPECIFIED 通过、非 UNSPECIFIED/缺映射 失配
    from pathway_v43.pollutant.s5b_compiler import (
        _stereo_dissolution_mismatch,
    )

    ok_exec = {"atom_id_map": {"S_C_2": 1},
               "product_mapped_smiles": "[CH3:1][C:2](=[O:3])[Cl:4]"}
    assert _stereo_dissolution_mismatch(ok_exec, {2: "S_C_2"}, [2]) == []
    bad_exec = {"atom_id_map": {"S_C_2": 1},
                "product_mapped_smiles": "[CH3:1][C@H:2]([OH:3])[Cl:4]"}
    assert _stereo_dissolution_mismatch(
        bad_exec, {2: "S_C_2"}, [2]) == [(2, "CHI_TETRAHEDRAL_CCW")]
    assert _stereo_dissolution_mismatch(
        {"atom_id_map": {}, "product_mapped_smiles": "CC"},
        {2: "S_C_2"}, [2]) == [(2, "None")]


# ================================================================ R1(S5B-V4B-01)

# Codex v4b 复审 §4.2 真实公共链反例族(原样输入;证据
# docs/review_evidence/ppv1_v4b_codex_2026-10-10/stereo/public/)。
# 规则级合成反例,与真实 298 金标零重叠。
_R1_COUNTEREXAMPLES = [
    # P3:lhs P 真四面体标签、全单键;rhs 无声明;仅 P-O single→double
    ("phosphorus_three",
     "[P@:1]([OH:2])([CH3:3])[CH2:4][CH3:5]",
     "[P:1](=[O:2])([CH3:3])[CH2:4][CH3:5]",
     [1, 2], "CCP(C)O"),
    # P4:四配位 P(无氢表示依赖)
    ("phosphorus_four",
     "[P@:1]([OH:2])([CH3:3])([CH2:4][CH3:5])[CH2:6][CH2:7][CH3:8]",
     "[P:1](=[O:2])([CH3:3])([CH2:4][CH3:5])[CH2:6][CH2:7][CH3:8]",
     [1, 2], "CCC[P](C)(O)CC"),
    # S4:同根以 S 替 P(执行后潜在类型 Atom_TrigonalBipyramidal)
    ("sulfur_four",
     "[S@:1]([OH:2])([CH3:3])([CH2:4][CH3:5])[CH2:6][CH2:7][CH3:8]",
     "[S:1](=[O:2])([CH3:3])([CH2:4][CH3:5])[CH2:6][CH2:7][CH3:8]",
     [1, 2], "CCC[S](C)(O)CC"),
]


@pytest.mark.parametrize("name,lhs,rhs,center,substrate",
                         _R1_COUNTEREXAMPLES)
def test_r1_noncarbon_dissolution_rejected(name, lhs, rhs, center,
                                            substrate) -> None:
    """R1 负控(S5B-V4B-01,Codex 反例族):非碳四面体中心(P/S)
    的"标签消失"不构成消解——single→double 后执行产物原子仍是
    潜在立体中心(P:Atom_Tetrahedral/未指派;S:
    Atom_TrigonalBipyramidal),违反 mimo r28 E2 放行条件。

    修后(元素域守卫,谓词条件 0):P/S 例落 stereo_changed ⇒
    stereo_edit_unsupported,零消解 spec/事件。父 HEAD(9a0a60ea)
    上三例均 compiled 且 stereo_dissolution_applied=[1] ⇒ 红。"""
    out = compile_donor_template(
        mapped_lhs=lhs, mapped_rhs=rhs, center_atoms=center,
        substrate_smiles=substrate, record_id=f"v4b-r1-{name}")
    assert out["status"] == "unsupported", out
    assert out["reason"] == "stereo_edit_unsupported"
    assert out["detail"]["stereo_changed_maps"] == [1]
    assert "spec" not in out


def test_r1_noncarbon_recheck_catches_without_element_guard() -> None:
    """R1 防御纵深证明(mimo r33 S2-b ① 轴,不依赖元素守卫):对
    Codex P3 案的**真实执行产物**(``CC[PH](C)=O``,P 为潜在
    四面体中心/未指派)直接跑复核 helper——即使谓词放行(模拟
    元素守卫缺席),双轴复核的潜在立体中心轴也能拒(旧单轴
    "无已指派标签 ⇒ 通过"是空窗;父 HEAD 上该轴不存在 ⇒ 红)。"""
    from pathway_v43.pollutant.s5b_compiler import (
        _stereo_dissolution_mismatch,
    )

    # P3 执行产物映射形式(P = map 3 = idx 2;当前 ID S_P_1 → idx 2)
    exec_p = {"atom_id_map": {"S_P_1": 2},
              "product_mapped_smiles":
                  "[CH3:1][CH2:2][PH:3]([CH3:4])=[O:5]"}
    assert _stereo_dissolution_mismatch(
        exec_p, {1: "S_P_1"}, [1]) == [(1, "potential:Atom_Tetrahedral")]
    # S4 执行产物(S 为潜在三角双锥;同根防御)
    exec_s = {"atom_id_map": {"S_S_1": 3},
              "product_mapped_smiles":
                  "[CH3:1][CH2:2][CH2:3][SH:4]([CH3:5])(=[O:6])"
                  "[CH2:7][CH2:8][CH3:9]"}
    mismatched_s = _stereo_dissolution_mismatch(exec_s, {1: "S_S_1"}, [1])
    assert mismatched_s == [(1, "potential:Atom_TrigonalBipyramidal")], \
        mismatched_s


def test_r1_condition2_non_single_bond_isolation() -> None:
    """R1 隔离负控(mimo r33 S1-c,条件 2):rhs 无声明 ∧ 带标签
    原子在 lhs 含非单键 ⇒ 拒(维持 stereo_edit_unsupported)。

    形态选择说明:碳的该形态**进不了判定环**——RDKit 解析即清掉
    sp2 碳的四面体标签(下方断言实测,该解析行为如实写入测试);
    故用亚砜(真四面体 S 标签 + S=O 双键)构造。该例同时不满足
    R1 元素域守卫(条件 0,S ∉ C)——条件 0 与条件 2 在此形态
    同时为假,拒因同归 stereo_edit_unsupported。"""
    from rdkit import Chem

    # RDKit 解析行为披露(S1-c):sp2 碳的手性标签在解析即被清除
    # ⇒ 碳的"标签原子含非单键"形态不可能进入消解判定环
    m = Chem.MolFromSmiles("[CH3:1][C@:2](=[O:3])[Cl:4]")
    assert m is not None
    assert all(a.GetChiralTag() == Chem.ChiralType.CHI_UNSPECIFIED
               for a in m.GetAtoms())
    # 亚砜形态:S 真四面体标签(解析保留)+ S=O 双键;rhs 无声明
    out = compile_donor_template(
        mapped_lhs="C[S@:1](=O)F", mapped_rhs="C[S:1](=O)F",
        center_atoms=[1], substrate_smiles="CS(C)(=O)F",
        record_id="v4b-r1-cond2")
    assert out["status"] == "unsupported", out
    assert out["reason"] == "stereo_edit_unsupported"
    assert out["detail"]["stereo_changed_maps"] == [1]


def test_r1_condition3_break_form_isolation() -> None:
    """R1 隔离负控(mimo r33 S1-c,条件 3):rhs 无声明 ∧ 断/成键
    落在该原子(C 离去 + Br 到达,SN2 不翻转书写形态)⇒ 拒
    (维持 stereo_edit_unsupported;元素域/标签条件均满足,唯
    断/成键形态不满足)。"""
    out = compile_donor_template(
        mapped_lhs="[CH3:1][C@H:2]([OH:3])[Cl:4]",
        mapped_rhs="[CH3:1][C:2]([OH:3])[Br:5]",
        center_atoms=[2], substrate_smiles="CC(O)Cl",
        record_id="v4b-r1-cond3")
    assert out["status"] == "unsupported", out
    assert out["reason"] == "stereo_edit_unsupported"
    assert out["detail"]["stereo_changed_maps"] == [2]


def test_r1_potential_center_recheck_axis_rejects(monkeypatch) -> None:
    """R1 复核双轴负控(mimo r33 S2-b ① / S2-a):执行产物该原子
    **无已指派标签但仍为潜在四面体中心**(map 2 = 未取代二级碳,
    UNCH2 变 CH)⇒ 旧单轴复核(只查标签)通过、编译放行;R1 双轴
    复核按潜在立体中心轴拒(父 HEAD 上 compiled ⇒ 红)。"""
    import pathway_v43.pollutant.s5b_compiler as compiler_mod

    real_execute = compiler_mod.execute_edits

    def _unlabeled_potential_execute(current, edits):
        result = dict(real_execute(current, edits))
        if result.get("ok"):
            # 把执行产物替换为"map 2 原子无标签、仍为潜在四面体
            # 中心"的形态(真实碳路径下谓词结构性保证 sp2 ⇒ 不出现;
            # 此门为执行器/序列化行为漂移的防御轴)
            result["product_mapped_smiles"] = \
                "[CH3:1][CH:2]([OH:3])[Cl:4]"
        return result

    monkeypatch.setattr(compiler_mod, "execute_edits",
                        _unlabeled_potential_execute)
    out = compile_donor_template(
        mapped_lhs=_LHS, mapped_rhs=_RHS, center_atoms=[2, 3],
        substrate_smiles=_SUB, record_id="v4b-r1-potaxis")
    assert out["status"] == "unsupported", out
    assert out["reason"] == "stereo_derived_mismatch"
    reasons = (out.get("detail") or {}).get("reasons") or []
    assert any("map2" in r and "potential:Atom_Tetrahedral" in r
               for r in reasons), reasons


def test_r1_recheck_helper_two_axes_and_bond_axis_collision() -> None:
    """R1 复核 helper 直测(双轴 + 键轴碰撞防御):

    - 已指派标签轴:非 UNSPECIFIED 标签失配(既有轴);
    - 潜在立体中心轴:无标签但为潜在四面体中心 ⇒ 失配
      (``potential:<类型>``;P/S 真实执行产物同拒,见上一测试);
    - 键轴碰撞防御:FindPotentialStereo 的键轴条目(E/Z,
      ``Bond_Double``)centeredOn 是**键索引**,与原子索引数值可能
      碰撞——该原子无原子轴条目时不得误失配(范围只限该原子,
      仅原子轴类型);
    - 映射缺失 fail-closed(既有轴维持)。"""
    from pathway_v43.pollutant.s5b_compiler import (
        _stereo_dissolution_mismatch,
    )

    # (a) 合格:sp2 碳(酮)无标签且不在潜在中心清单
    ok_exec = {"atom_id_map": {"S_C_2": 1},
               "product_mapped_smiles": "[CH3:1][C:2](=[O:3])[Cl:4]"}
    assert _stereo_dissolution_mismatch(ok_exec, {2: "S_C_2"}, [2]) == []
    # (b) 潜在立体中心轴:无标签、未指派潜在四面体中心 ⇒ 失配
    pot_exec = {"atom_id_map": {"S_C_2": 1},
                "product_mapped_smiles": "[CH3:1][CH:2]([OH:3])[Cl:4]"}
    assert _stereo_dissolution_mismatch(
        pot_exec, {2: "S_C_2"}, [2]) == [(2, "potential:Atom_Tetrahedral")]
    # (c) 键轴碰撞:map 2 原子(idx 1)无原子轴条目,而产物另有
    # 未指派 E/Z 双键(键轴条目,centeredOn 为键索引)⇒ 不误失配
    ez_exec = {"atom_id_map": {"S_C_2": 1},
               "product_mapped_smiles":
                   "[CH3:1][CH:2][CH:3]=[CH:4][CH3:5]"}
    assert _stereo_dissolution_mismatch(
        ez_exec, {2: "S_C_2"}, [2]) == []
    # (d) 映射缺失 fail-closed(既有轴维持)
    assert _stereo_dissolution_mismatch(
        {"atom_id_map": {}, "product_mapped_smiles": "CC"},
        {2: "S_C_2"}, [2]) == [(2, "None")]


# ================================================================ P2 正负控

def test_p2_budget_limits_registered_and_truncation_keeps() -> None:
    """P2:预算升档登记(match 800 / 调用 8192)+ 触顶诚实拒维持
    (monkeypatch 夹具预算 ⇒ 仍 truncated 拒;歧义披露纪律不变)。"""
    import pathway_v43.pollutant.recorded_source as rs

    assert rs._INFER_MATCH_LIMIT == 800
    assert rs._INFER_BOND_DIFF_CALL_LIMIT == 8192
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(rs, "_INFER_MATCH_LIMIT", 1)
        mappings = rs.infer_reaction_mapping("CCO", ["COC"])
        assert mappings and mappings[0].get("truncated") is True
        out = rs.compile_recorded_reaction(
            substrate_smiles="CCO", donor_smiles="CCO",
            products=["COC"], record_id="v4b-p2-trunc")
        assert out["status"] == "unsupported"
        assert out["reason"] == "mapping_enumeration_truncated"
    finally:
        monkey.undo()


def test_p2_fallback_fastfail_necessary_conditions() -> None:
    """P2:fallback 前置必要条件(元素包含/原子数)——无望组合
    直接空返回(零语义变化:与全枚举空结果同判 no_structure_
    correspondence;不再占用组合预算)。"""
    # 元素缺席:donor O 不在产物 ⇒ 任意键差无解
    assert infer_reaction_mapping("CCO", ["CCS"]) == []
    # 原子数:donor 原子多于产物并集且标准分支无解(查询必无解)
    assert infer_reaction_mapping("CSC", ["CC"]) == []
    # 单元:_elements_contained(子结构匹配必要条件)
    from rdkit import Chem

    from pathway_v43.pollutant.recorded_source import (
        _elements_contained,
    )

    assert _elements_contained(
        Chem.MolFromSmiles("CCO"), Chem.MolFromSmiles("CCOCC")) is True
    assert _elements_contained(
        Chem.MolFromSmiles("CCO"), Chem.MolFromSmiles("CCS")) is False
    assert _elements_contained(
        Chem.MolFromSmiles("CCC"), Chem.MolFromSmiles("CC")) is False


def test_p2_addition_branch_enumerates_all_components() -> None:
    """P2:加成/生成分支全组分枚举——donor 可容纳于多个产物组分时,
    全部组分的候选对应均枚举(旧实现在首个组分后 break;候选面交由
    编译 + 产物多重集 gate + 落位纪律评估,判据零放宽)。"""
    # donor CCO(3 原子)⊆ 两个产物组分(CCO.CCO);旧:仅首组分
    # 的像;新:两组分的像均在候选映射内
    mappings = infer_reaction_mapping("CCO", ["CCO", "CCO"])
    assert mappings, "全组分枚举应给出两组件的候选对应"
    images = [tuple(sorted(m["donor_to_union"].values()))
              for m in mappings]
    comp_a = any(all(u < 3 for u in img) for img in images)
    comp_b = any(all(u >= 3 for u in img) for img in images)
    assert comp_a and comp_b, images
    # 判据不放宽:跨组分新原子无锚 ⇒ 编译诚实拒(产物多重集/落位
    # 纪律评估;不因枚举面扩大而放行)
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CCO", "CCO"], record_id="v4b-p2-addall")
    assert out["status"] == "unsupported"
    assert out["reason"] in ("new_atom_unanchorable",
                             "transform_no_change",
                             "new_atom_placement_incomplete",
                             "product_set_mismatch")


def test_p2_no_correspondence_and_gates_unchanged() -> None:
    """P2 负控族(判据零放宽):元素缺席 no_structure_correspondence
    保持;过滤单产品卡 product_set_mismatch 保持(缺行诚实拒不
    冒充)。"""
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CCS"], record_id="v4b-p2-neg-elem")
    assert out["status"] == "unsupported"
    assert out["reason"] == "no_structure_correspondence"
    out2 = compile_recorded_reaction(
        substrate_smiles="CCOCC", donor_smiles="CCOCC",
        products=["CCO"], record_id="v4b-p2-neg-psm")
    assert out2["status"] == "unsupported"
    assert out2["reason"] == "product_set_mismatch"


def test_p2_standard_paths_unchanged() -> None:
    """P2:标准(零键差)路径零行为变化(v3 wv2 同款断言回放):
    加成(乙醇→乙醛)与裂解(丁烷)照旧;n_bond_diff=0。"""
    mappings = infer_reaction_mapping("CCO", ["CC=O"])
    assert mappings
    assert all(m.get("n_bond_diff", 0) == 0 for m in mappings)
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CC=O"], record_id="v4b-p2-std")
    assert out["status"] == "compiled", out
    assert out["spec"]["compile"]["n_bond_diff"] == 0


# ================================================================ 版本

def test_v4b_versions_registered() -> None:
    """P3:版本登记(编译器/recorded 源/池策略升版;corpus 检索
    语义零变化——检索/分层/许可规则未动)。

    R1:s5b-compiler-2 → **s5b-compiler-3**(S5B-V4B-01 收口:消解
    元素域收窄为碳 + 执行后复核双轴,公共编译判据链行为变化);
    recorded-source-2 / pool-policy-4 / corpus-retrieval-2 **维持**
    (recorded 侧零判据改动;池成员零变化——碳消解唯一 298 槽
    bt0002#r0032 保留、非碳反例不在语料,复审 §4 拒例零收紧面)。
    W-D2(共底物参与物语义):recorded-source-2→3(union gate 可选
    参数扩展)、pool-policy-4→5(拷贝子集重新入池)、corpus-
    retrieval-2→3(三分类守门)——s5b-compiler-3 维持(编译判据
    零触碰;net_reaction_signature 拷贝扩展对无拷贝 spec 逐字节
    不变);EAWAG/整串缺省路径行为字节等价(负控见 cosub_d2 族)。"""
    from pathway_v43.pollutant.recorded_source import (
        RECORDED_SOURCE_VERSION,
    )
    from pathway_v43.pollutant.s5b_builder import S5B_POOL_POLICY_VERSION

    assert S5B_COMPILER_VERSION == "s5b-compiler-3"
    assert RECORDED_SOURCE_VERSION == "s5b-recorded-source-3"
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-5"
    from pathway_v43.pollutant.recorded_source import (
        CORPUS_RETRIEVAL_VERSION,
    )

    assert CORPUS_RETRIEVAL_VERSION == "s5b-corpus-retrieval-6"
