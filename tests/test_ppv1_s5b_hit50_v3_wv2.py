"""PPV1 S5b HIT50 v3 W-V2 —— recorded 编译墙:有界键差结构对应 +
产物多重集门全映射评估(S5b-recorded-bonddiff-1)。

依据:v3 任务书 W-V2 + 尸检 §1.1 L1(116 次 no_structure_
correspondence;28 次 product_set_mismatch)+ W-V0 后分类探针
(v2 批 298 题只读复跑,靶点清单见交付书)。修复为**通用机制**:
- ``infer_reaction_mapping``:标准(零键差)枚举无解 ⇒ 有界键差
  fallback(删 donor ≤2 条键的允许不连通 any-bond 查询在产物并集
  匹配;断键/成键重排与跨组分断裂+新增原子的记录恢复对应;预算/
  歧义披露不变;标准路径成功时零行为变化);
- ``compile_recorded_reaction``:产物多重集 gate 在全部候选映射上
  评估,择可复现者;无可复现 ⇒ 原 ambiguous/product_set_mismatch
  判据保留(过滤缺失仍诚实拒);
- ``s5b_compiler``:保留原子间新成键(form_bond)在无新增原子时
  同样落位(纯重排可表达;旧实现静默丢弃 —— 已证缺口)。

正负控(任务书 W-V2.2/W-V2.3):断键重排类编译通过且产物多重集
核对一致;水解型(跨组分断裂+新原子)编译通过;无对应/触顶/歧义
仍拒;W2 负控族(filtered 单产品卡冒完整)保留。合成分子与真实
298 金标零重叠。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.recorded_source import (  # noqa: E402
    compile_recorded_reaction,
    infer_reaction_mapping,
)
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    compile_donor_template,
)


# ================================================================ 正控

def test_wv2_rearrangement_compiles_with_product_multiset() -> None:
    """正控(断键重排类):CCO → COC(断 C-C、成 C-O;同元素集、
    连通性重排)。旧实现:no_structure_correspondence(标准两分支
    都无法表达);新版:fallback 对应 + form_bond 编译,产物多重集
    核对一致。"""
    mappings = infer_reaction_mapping("CCO", ["COC"])
    assert mappings, "重排对应应枚举出候选(有界键差 fallback)"
    assert all(m.get("n_bond_diff", 0) >= 1 for m in mappings)
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["COC"], record_id="wv2-rearr")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["product_smiles"] == "COC"
    assert spec["coproducts"] == []
    # 产物多重集核对一致(strict exact 最终门)
    assert spec["compile"]["verified_product_set"] is True
    assert spec["compile"]["n_bond_diff"] == 1
    # 编辑表达:断键 + 成键(保留原子间;无新增原子)
    ops = [e["op"] for e in spec["edits"]]
    assert "break_bond" in ops and "form_bond" in ops
    assert "add_atom" not in ops


def test_wv2_hydrolysis_type_compiles_with_new_atom() -> None:
    """正控(跨组分断裂+新增原子;水解型):乙酸甲酯 → 乙酸 + 甲醇
    (酯键断;甲醇 O 为记录产物中的新原子,锚定落位)。标准加成分支
    (donor ⊆ 单一组分)无法表达;fallback 恢复。"""
    mappings = infer_reaction_mapping("CC(=O)OC", ["CC(=O)O", "CO"])
    assert mappings
    out = compile_recorded_reaction(
        substrate_smiles="CC(=O)OC", donor_smiles="CC(=O)OC",
        products=["CC(=O)O", "CO"], record_id="wv2-hyd")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["product_smiles"] == "CC(=O)O"
    assert spec["coproducts"] == ["CO"]
    assert spec["compile"]["verified_product_set"] is True
    assert spec["compile"]["n_bond_diff"] == 1
    ops = [e["op"] for e in spec["edits"]]
    assert "break_bond" in ops
    assert "add_atom" in ops  # 甲醇 O(记录产物中的新原子)锚定落位


def test_wv2_standard_zero_bond_diff_path_unchanged() -> None:
    """标准(零键差)路径零行为变化:乙醇→乙醛(加成分支)与丁烷
    裂解(裂解分支)照旧;成功记录不带 n_bond_diff 语义(=0)。"""
    mappings = infer_reaction_mapping("CCO", ["CC=O"])
    assert mappings
    assert all(m.get("n_bond_diff", 0) == 0 for m in mappings)
    butane = infer_reaction_mapping("CCCC", ["CCC", "C"])
    assert len(butane) >= 2  # 对称多解如实枚举(W2 既有断言)
    out = compile_recorded_reaction(
        substrate_smiles="CCOCC", donor_smiles="CCOCC",
        products=["CCO", "CC"], record_id="wv2-std")
    assert out["status"] == "compiled", out
    assert out["spec"]["compile"]["n_bond_diff"] == 0


def test_wv2_compiler_form_bond_between_retained_atoms() -> None:
    """compiler 直测:保留原子间新成键在**无新增原子**时同样落位
    (纯重排模板;旧实现 ``if not added: return {}`` 静默丢弃该键
    —— 已证缺口)。mapped 双侧键差 = 断 C1-C2、成 C1-O3。"""
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][O:3][CH3:2]",
        center_atoms=[1, 2, 3],
        substrate_smiles="CCO", record_id="wv2-formbond")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["expectation"]["target_smiles"] == "COC"
    ops = [e["op"] for e in spec["edits"]]
    assert "break_bond" in ops and "form_bond" in ops


# ================================================================ 负控

def test_wv2_no_correspondence_honest_reject() -> None:
    """负控(语料真实无对应):产物并集缺 donor 元素(O)⇒ 标准
    与 fallback 都无解 ⇒ no_structure_correspondence 保持(不为
    数量压力放行任意补原子)。"""
    mappings = infer_reaction_mapping("CCO", ["CCS"])
    assert mappings == []
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CCS"], record_id="wv2-neg-elem")
    assert out["status"] == "unsupported"
    assert out["reason"] == "no_structure_correspondence"


def test_wv2_enumeration_truncated_rejects(monkeypatch) -> None:
    """负控(触顶):枚举预算触顶 ⇒ truncated ⇒ 拒(不静默取首解;
    预算纪律与标准分支同源)。"""
    import pathway_v43.pollutant.recorded_source as rs

    monkeypatch.setattr(rs, "_INFER_MATCH_LIMIT", 1)
    # 首个删键组合即产生候选 ⇒ 触顶(truncated=True)
    mappings = rs.infer_reaction_mapping("CCO", ["COC"])
    assert mappings and mappings[0].get("truncated") is True
    out = rs.compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["COC"], record_id="wv2-neg-trunc")
    assert out["status"] == "unsupported"
    assert out["reason"] == "mapping_enumeration_truncated"


def test_wv2_ambiguous_multi_target_without_reproducible_rejects() -> None:
    """负控(歧义仍拒):多 distinct 目标且无一复现库记录净产物
    集合 ⇒ ambiguous_mapping(候选披露;不取首个猜)。"""
    # 底物含酯为子结构、记录为 donor 级净产物:候选映射编译到不同
    # 目标(底物上下文),无一 == 记录多重集
    out = compile_recorded_reaction(
        substrate_smiles="CCOCC(=O)OC", donor_smiles="CC(=O)OC",
        products=["CC(=O)O", "CO"], record_id="wv2-neg-amb")
    assert out["status"] == "unsupported"
    assert out["reason"] == "ambiguous_mapping"
    assert out["detail"]["n_reproducible"] == 0


def test_wv2_filtered_single_product_card_still_rejected() -> None:
    """W2 负控族保留(filtered 单产品卡冒完整):离去组分缺行 ⇒
    product_set_mismatch 诚实拒(不冒充完整 record)。"""
    out = compile_recorded_reaction(
        substrate_smiles="CCOCC", donor_smiles="CCOCC",
        products=["CCO"], record_id="wv2-neg-psm")
    assert out["status"] == "unsupported"
    assert out["reason"] == "product_set_mismatch"


def test_wv2_product_multiset_gate_covers_all_mappings() -> None:
    """W-V2.3:产物多重集 gate 在全部候选映射上评估——可复现者被
    选中且 disclosed(n_bond_diff/n_mappings);无可复现的单目标 ⇒
    product_set_mismatch(首个判据保留)。"""
    # 乙酸甲酯水解:12 个候选映射(含等价/无效对应),gate 选中
    # 复现记录多重集者
    out = compile_recorded_reaction(
        substrate_smiles="CC(=O)OC", donor_smiles="CC(=O)OC",
        products=["CC(=O)O", "CO"], record_id="wv2-gate")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["compile"]["verified_product_set"] is True
    assert spec["compile"]["n_mappings"] >= 2
    assert spec["compile"]["n_equivalent_mappings"] >= 1
    # 单目标不可复现(缺产物)⇒ 诚实拒(同 filtered 负控路径)
    out2 = compile_recorded_reaction(
        substrate_smiles="CCOCC(=O)OCC", donor_smiles="CCOCC(=O)OCC",
        products=["CCOCC(=O)O"], record_id="wv2-gate2")
    assert out2["status"] == "unsupported"
    assert out2["reason"] == "product_set_mismatch"
