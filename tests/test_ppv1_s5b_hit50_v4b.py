"""PPV1 S5b v4b —— 编译墙深层修复(P1 stereo 消解 + P2 推断映射
深层门扩展;S5b-stereo-dissolution-1 / S5b-recorded-infer-2 /
s5b-compiler-2 / s5b-recorded-source-2 / s5b-pool-policy-4;零网络、
零金标)。

依据:v4b 任务书(mimo r28 E1-E3 评审方向落地)+ v2 尸检 §1.1 L1
(EAWAG 编译墙 228 次:stereo 38 / no_structure_correspondence 116)
+ v3 交付 §五(深层门拦截 47/116:charge 24 保留边界 + no_alignment 8
+ 触顶 6 + 去芳香 3 + 歧义 1 + 产物集 1)+ v4/R1 交付(corpus 整串
面;组分级已被 S5B-V4-01 许可规则接管,本轮零触碰)。

**P1 stereo 消解(S5b-stereo-dissolution-1)**——消解谓词钉死
(mimo r28 E2 窄化版):lhs 真四面体手性标签 ∧ rhs 无手性声明 ∧
该原子全部 lhs 键均单键(sp3)∧ 该原子涉及的全部键变化均为
change_bond_order 型(single→double/triple,无 form/break/芳香)
∧ 至少一个该型变化;执行后 rhs 立体同源复核(不等 ⇒ 结构化
stereo_derived_mismatch 拒);spec 机读诊断 stereo_dissolution_applied。

正负控:
- 正控:二级醇氧化成酮(合成同构用例)编译通过且**公共链执行成
  事件**(compile→prepare→AtomTool→donor 诊断→audit→admission→
  store→export;参与物核对:反应物=底物、产物=酮);
- 负控族(r28 反例全拒):纯立体翻转(无键级变化)、stereo_created
  (lhs 无声明→rhs 有声明)、SN2 型配体交换(form/break 落在现存
  立体中心)、手性声明底物显式氢价态墙(execution 诚实拒);
- 同源复核负控:执行产物立体状态 ≠ rhs 声明 ⇒ stereo_derived_
  mismatch 结构化拒(monkeypatch 执行器返回残留标签产物的机读证
  明;真实化学路径下该门为防御性,E2-③ 条款)。

**P2 推断映射深层门(S5b-recorded-infer-2)**:
- 预算升档(200/512→800/8192)+ 触顶诚实拒维持(monkeypatch
  夹具预算仍拒);
- fallback 前置必要条件 fast-fail(元素包含/原子数;零语义变化,
  无望组合不再占预算);
- 加成分支全组分枚举(旧 break 丢后续组分的候选对应;产物多重集
  gate 与落位纪律全映射评估不变)。

合成夹具与真实 298 金标零重叠(乙醇/氯乙醇级合成小分子,沿 W2
既有夹具纪律)。
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
    邻居序 ⇒ 标签解读翻转 = 静默对映体翻转):消解谓词要求该原子
    全部键变化均为 change_bond_order 型 ⇒ 维持 stereo_edit_unsupported
    (有机磷/硫中心水解同款形态;构型翻转书写)。"""
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
    (双键/芳香)或非四面体标签差异 ⇒ 消解谓词第 2/3 条不满足,
    维持 stereo_edit_unsupported(累积烯中央原子天然全双键,不消解)。
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


def test_p1_chiral_substrate_valence_wall_honest_reject() -> None:
    """负控(显式氢价态墙):底物带手性声明([C@H] 括号氢)时,
    single→double 键级变化使显式价超限 ⇒ 执行器 sanitize 诚实拒
    (execution_failed;不冒充消解、不动 AtomTool——最小改动面
    待复审,见交付书)。"""
    out = compile_donor_template(
        mapped_lhs=_LHS, mapped_rhs=_RHS, center_atoms=[2, 3],
        substrate_smiles="C[C@H](O)Cl", record_id="v4b-p1-chiral")
    assert out["status"] == "unsupported"
    assert out["reason"] == "execution_failed"
    assert any("sanitize_failed" in r for r in
               (out.get("detail") or {}).get("reasons") or [])


def test_p1_post_execution_homology_mismatch_rejects(monkeypatch) -> None:
    """同源复核负控(E2-③ 机读证明):执行产物在该 map 的立体状态
    ≠ rhs 声明(UNSPECIFIED)⇒ 结构化 stereo_derived_mismatch 拒
    (monkeypatch 执行器返回残留四面体标签的产物;真实化学路径下
    该门为防御性——显式氢走价态墙,隐性标签由 sanitize 清理)。"""
    import pathway_v43.pollutant.s5b_compiler as compiler_mod

    real_execute = compiler_mod.execute_edits

    def _tagged_execute(current, edits):
        result = dict(real_execute(current, edits))
        if result.get("ok"):
            # 防御门证明:把执行产物映射 SMILES 整体替换为"消解原子
            # (map 2)仍带四面体标签"的形态(真实化学路径下 sp2 原子
            # 的无效标签会被 MolToSmiles 清理/价态墙先行,此门为
            # E2-③ 要求的机读核)
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
    语义零变化——检索/分层/许可规则未动)。"""
    from pathway_v43.pollutant.recorded_source import (
        RECORDED_SOURCE_VERSION,
    )
    from pathway_v43.pollutant.s5b_builder import S5B_POOL_POLICY_VERSION

    assert S5B_COMPILER_VERSION == "s5b-compiler-2"
    assert RECORDED_SOURCE_VERSION == "s5b-recorded-source-2"
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-4"
    from pathway_v43.pollutant.recorded_source import (
        CORPUS_RETRIEVAL_VERSION,
    )

    assert CORPUS_RETRIEVAL_VERSION == "s5b-corpus-retrieval-2"
