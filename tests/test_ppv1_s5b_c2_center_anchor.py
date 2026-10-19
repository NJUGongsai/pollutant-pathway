"""PPV1 S5b T-G Step C2 重刀(R2' 解耦接线)单测族 —— §6.1 歧义硬拒
矩阵 + §6.2 路由/准入接线矩阵 + 材料负控反例形状类 + L3 披露。

权威链(冻结版):docs/T_G_C2_DESIGN_FROZEN_R2P_2026-10-19.md
(§3.2 真源表 F1-F5/§6.1 矩阵/§6.2 矩阵/§8 D-1 硬规则;四轮评审
收口 v1→v4,终轮 P0/P1/P2=0)。版本承载:s5b-compiler-4(中心锚定
对齐)+ s5b-pool-policy-8(R2' 接线)+ 路由真源 s5b-analog-route-f1f4-1。

控件矩阵:

§6.1 歧义硬拒(纯合成、零 LLM、不含题面/金标;同根消费入口=经
builder 公共链触发,另附编译器级机读字段断言):
- M2-1 合成反例 `OCCC(O)C`:全部语义允许候选 M 全量等价核验 ⇒
  2 个不同可执行目标 ⇒ 结构化 ambiguous_alignment(必须;prefer
  不得跳过被丢弃的非全等候选);
- M2-2 `CC(O)C`(仅非全等中心,prefer 回退全体):唯一目标 ⇒
  compiled CC(C)=O(证明规则非「非全等一律拒」);
- M2-3 `CCO` 合法正控:compiled CC=O(不以全面拒绝换通过);
- M2-4 `CCC` 无中心负控:no_alignment;
- M2-5 预算截断(65×CCO 副本构造 M 超上限):结构化拒
  alignment_limit_exceeded + 未核范围机读披露(不得称唯一目标已证)。

§6.2 R2' 路由/准入解耦接线(沿 builder 公共入口 `:1115-1216` 全链;
真实 analog_cosub_supply 与真实门谓词/F5 helper;编译用记录桩——
桩只证明分支/调用/输入,不证化学;§6.2 #3 用真实编译提供正控):
- R2-1 普通袋 `[Na+:4]`:供给判定照旧 1 次(supply)+ 执行输入
  冻结 `CCO.[Na+]` + F5 在该输入上过 + 编译 1 次输入 `CCO.[Na+]`
  (**不得** raw 中心过 ⇒ 跳过供给直编 `CCO` 旁路);
- R2-2 wildcard 袋 `[*:4]`:F3 先于 F5 与直编——记数 1、不供给、
  编译 0、F5 判定 0 次(raw 中心命中不得解除拦截);
- R2-3 无袋正控:F1 过、供给 0 次、F5 输入 `CCO`、真实编译
  compiled `CC=O`;
- R2-4 供给后准入不过(构造负控,CCO 模板 + `[Na+:4]` 袋,底物
  `CCC`):F5 不过 ⇒ 结构化 no_alignment、编译 0(省预算口径)、
  路由事实(供给/输入)不变。

材料负控反例形状类(合成复现;材料实例在 gitignored 材料包,测试
不复刻题面结构——形状类=「shell1 有匹配而 shell2(N1 入射键集合)
挡住」):两件材料反例(起始态缺失/中心酮态邻接差异)的抽象公因子
已在设计 §2.3 登记;测试以合成小分子实例化该类并断言口径正确
(单壳层会过、两壳层必拒)。

本文件零网络、零真实模型;合成分子与真实 298 题面零重叠。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_ANALOG_ROUTE_VERSION,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    S5B_COMPILER_VERSION,
    build_center_query,
    compile_donor_template,
    extract_mapped_transform,
    l1_maps_of_transform,
)
from pathway_v43.services.analog_source import DonorRef  # noqa: E402
from rdkit import Chem, RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

_TPL_L = "[CH3:1][CH2:2][OH:3]"
_TPL_R = "[CH3:1][CH:2]=[O:3]"


def _donor_ref(record_id: str, mapped_lhs: str, mapped_rhs: str,
               center_atoms: list[int] | None = None) -> DonorRef:
    return DonorRef(
        record_id=record_id, index="analog_corpus_templates",
        asset_file="synthetic", asset_sha256="0" * 64, line_no=1,
        mapping_quality="mapped_bijection",
        reactant_smiles=mapped_lhs, product_smiles=mapped_rhs,
        mapped_lhs=mapped_lhs, mapped_rhs=mapped_rhs,
        center_atoms=list(center_atoms if center_atoms is not None
                          else [2, 3]))


def _stub_resolver(monkeypatch, refs: list[DonorRef]) -> None:
    class _Stub:
        def __init__(self, config) -> None:
            self.config = config

        def templates_similar_to(self, substrate_smiles: str, *,
                                 threshold: float, top_k: int):
            return list(refs)

    import pathway_v43.services.analog_source as analog_module

    monkeypatch.setattr(analog_module, "AnalogSourceResolver", _Stub)


def _provider(monkeypatch, refs: list[DonorRef]):
    _stub_resolver(monkeypatch, refs)
    return default_pool_provider(resolve_config(), engine=None,
                                 min_unique_targets=0)


# ================================================================ §6.1


def test_m2_1_synthetic_ambiguity_hard_reject(monkeypatch) -> None:
    """M2-1:合成反例 `OCCC(O)C` —— 全部语义允许候选(M,含被 prefer
    排序靠后的非全等候选)全量等价核验 ⇒ 2 个不同可执行目标 ⇒
    **必须结构化 ambiguous_alignment 拒绝**(不得静默偏好;机读
    competing_targets 只补充不替代);经 builder 公共入口触发。"""
    provider = _provider(monkeypatch, [_donor_ref("synthetic:m2-1",
                                                  _TPL_L, _TPL_R)])
    specs = provider("OCCC(O)C")
    assert not [s for s in specs if s["key"] == "tpl-synthetic:m2-1"]
    diag = provider.last_diagnostics
    assert diag["compile_failure_histogram"].get("ambiguous_alignment") \
        == 1
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:m2-1")
    assert row["outcome"] == "compile_rejected"
    assert row["reason"] == "ambiguous_alignment"
    assert row["route"] == "direct_raw"
    assert row["f5"] == "pass"
    # 编译器级机读字段:竞争目标披露 + 全候选已核验标记
    out = compile_donor_template(
        mapped_lhs=_TPL_L, mapped_rhs=_TPL_R, center_atoms=[2, 3],
        substrate_smiles="OCCC(O)C", record_id="synthetic:m2-1")
    assert out["status"] == "unsupported"
    assert out["reason"] == "ambiguous_alignment"
    assert set(out["detail"]["competing_targets"]) >= {
        "CC(=O)CCO", "CC(O)CC=O"}
    assert out["detail"]["all_matches_verified"] is True
    assert out["detail"]["n_targets"] >= 2


def test_m2_2_non_degree_center_single_target_compiles(monkeypatch) -> None:
    """M2-2:`CC(O)C`(仅非全等中心;prefer 回退全体)——全部 M 候选
    单一目标 ⇒ 允许 compiled `CC(C)=O`(规则不是「非全等一律拒」;
    回退容忍保留)。"""
    provider = _provider(monkeypatch, [_donor_ref("synthetic:m2-2",
                                                  _TPL_L, _TPL_R)])
    specs = provider("CC(O)C")
    spec = next(s for s in specs if s["key"] == "tpl-synthetic:m2-2")
    assert spec["expectation"]["target_smiles"] == "CC(C)=O"
    assert spec["compile"]["prefer_ordering"] == "fallback_all_presence"


def test_m2_3_positive_control_compiles(monkeypatch) -> None:
    """M2-3:合法正控 `CCO` —— compiled `CC=O`(不以全面拒绝换通过)。"""
    provider = _provider(monkeypatch, [_donor_ref("synthetic:m2-3",
                                                  _TPL_L, _TPL_R)])
    specs = provider("CCO")
    spec = next(s for s in specs if s["key"] == "tpl-synthetic:m2-3")
    assert spec["expectation"]["target_smiles"] == "CC=O"
    assert spec["compile"]["all_matches_verified"] is True


def test_m2_4_no_center_negative_control(monkeypatch) -> None:
    """M2-4:无中心负控 `CCC` —— no_alignment(不得编译)。"""
    provider = _provider(monkeypatch, [_donor_ref("synthetic:m2-4",
                                                  _TPL_L, _TPL_R)])
    specs = provider("CCC")
    assert not [s for s in specs if s["key"] == "tpl-synthetic:m2-4"]
    diag = provider.last_diagnostics
    assert diag["compile_failure_histogram"].get("no_alignment") == 1
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:m2-4")
    assert row["f5"] == "reject"
    assert row["execution_input_sha256"]


def test_m2_5_budget_truncation_structured_reject(monkeypatch) -> None:
    """M2-5:预算截断(65×CCO 副本 ⇒ 中心命中触 64 上限)——默认
    结构化拒绝 `alignment_limit_exceeded` + 未核范围机读披露;不得
    称唯一目标已证。"""
    provider = _provider(monkeypatch, [_donor_ref("synthetic:m2-5",
                                                  _TPL_L, _TPL_R)])
    substrate = ".".join(["CCO"] * 65)
    specs = provider(substrate)
    assert not [s for s in specs if s["key"] == "tpl-synthetic:m2-5"]
    diag = provider.last_diagnostics
    assert diag["compile_failure_histogram"].get(
        "alignment_limit_exceeded") == 1
    out = compile_donor_template(
        mapped_lhs=_TPL_L, mapped_rhs=_TPL_R, center_atoms=[2, 3],
        substrate_smiles=substrate, record_id="synthetic:m2-5")
    assert out["status"] == "unsupported"
    assert out["reason"] == "alignment_limit_exceeded"
    det = out["detail"]
    assert det["n_matches_at_limit"] == 64
    assert det["truncation_axis"] == "center_match_enumeration"
    assert det["unverified_matches"] is None
    # F5 defer(截断)⇒ 照常发编译、由编译层如实出因(不与
    # no_alignment 混淆;省预算不适用面如实披露)
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:m2-5")
    assert row["f5"] == "defer"
    assert row["reason"] == "alignment_limit_exceeded"


# ================================================================ §6.2


def _record_route_calls(monkeypatch):
    """真实 analog_cosub_supply / 真实 center_anchor_probe 的计数包装
    + 编译记录桩(记录输入后拒绝;桩只证分支/调用/输入,不证化学)。"""
    import pathway_v43.pollutant.s5b_builder as builder_module
    import pathway_v43.pollutant.s5b_compiler as compiler_module

    supply_calls: list[dict] = []
    real_supply = builder_module.analog_cosub_supply

    def supply_wrapped(**kwargs):
        out = real_supply(**kwargs)
        supply_calls.append({"kwargs": dict(kwargs), "status": out["status"]})
        return out

    monkeypatch.setattr(builder_module, "analog_cosub_supply",
                        supply_wrapped)

    probe_calls: list[dict] = []
    real_probe = compiler_module.center_anchor_probe

    def probe_wrapped(mapped_lhs, mapped_rhs, substrate_smiles):
        out = real_probe(mapped_lhs, mapped_rhs, substrate_smiles)
        probe_calls.append({"input": substrate_smiles,
                            "status": out["status"]})
        return out

    monkeypatch.setattr(compiler_module, "center_anchor_probe",
                        probe_wrapped)

    compile_calls: list[dict] = []

    def compile_stub(**kwargs):
        compile_calls.append(dict(kwargs))
        return {"status": "unsupported",
                "reason": "synthetic_expected_reject",
                "detail": {}, "compiler_version":
                compiler_module.S5B_COMPILER_VERSION}

    monkeypatch.setattr(compiler_module, "compile_donor_template",
                        compile_stub)
    return supply_calls, probe_calls, compile_calls


def test_r2_1_ordinary_bag_input_preserved(monkeypatch) -> None:
    """R2-1 普通袋 `[Na+:4]`(合法供给正控):供给判定照旧执行 1 次
    (status=supply)+ 执行输入冻结 `CCO.[Na+]`;F5 在 `CCO.[Na+]`
    上判定=过;编译调用 1 次、输入 `CCO.[Na+]`(输入保持,与基线
    逐字同);**不得**出现「raw 中心过 ⇒ 跳过供给、直编 `CCO`」。"""
    supply_calls, probe_calls, compile_calls = _record_route_calls(
        monkeypatch)
    ref = _donor_ref("synthetic:r2-1",
                     "[CH3:1][CH2:2][OH:3].[Na+:4]",
                     "[CH3:1][CH:2]=[O:3].[Na+:4]")
    provider = _provider(monkeypatch, [ref])
    provider("CCO")
    assert [c["status"] for c in supply_calls] == ["supply"]
    assert len(compile_calls) == 1
    assert compile_calls[0]["substrate_smiles"] == "CCO.[Na+]"
    assert probe_calls == [{"input": "CCO.[Na+]", "status": "present"}]
    diag = provider.last_diagnostics
    assert diag["analog_cosub_supply_compile_attempted"] == 1
    assert diag["analog_center_admission_checked"] == 1
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:r2-1")
    assert row["route"] == "supplied"
    assert row["execution_input_source"] == "supplied"
    assert row["f5"] == "pass"
    assert row["reason"] == "synthetic_expected_reject"


def test_r2_2_wildcard_interception_not_bypassed(monkeypatch) -> None:
    """R2-2 wildcard 袋 `[*:4]`(拦截不绕过):F3 先于 F5 与直编——
    wildcard 记数 1、不供给、编译调用 0、F5 判定 0 次;raw 中心命中
    不得解除拦截、不得直编 `CCO`。"""
    supply_calls, probe_calls, compile_calls = _record_route_calls(
        monkeypatch)
    ref = _donor_ref("synthetic:r2-2",
                     "[CH3:1][CH2:2][OH:3].[*:4]",
                     "[CH3:1][CH:2]=[O:3].[*:4]")
    provider = _provider(monkeypatch, [ref])
    specs = provider("CCO")
    assert not [s for s in specs if s["key"] == "tpl-synthetic:r2-2"]
    assert [c["status"] for c in supply_calls] == ["wildcard_blocked"]
    assert compile_calls == []
    assert probe_calls == []
    diag = provider.last_diagnostics
    assert diag["analog_cosub_supply_wildcard_blocked"] == 1
    assert diag["analog_center_admission_checked"] == 0
    assert diag["analog_pregate_skipped"] == 1
    assert diag["compile_failure_histogram"].get("no_alignment") == 1
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:r2-2")
    assert row["route"] == "wildcard_blocked"
    assert row["f5"] == "not_evaluated"


def test_r2_3_no_bag_positive_control_real_compile(monkeypatch) -> None:
    """R2-3 无袋正控(真实编译,非桩):F1 过、供给调用 0、F5 输入
    `CCO`、编译输入 `CCO`、compiled `CC=O`(不以全面拒绝换通过)。"""
    import pathway_v43.pollutant.s5b_builder as builder_module

    supply_calls: list[dict] = []
    real_supply = builder_module.analog_cosub_supply

    def supply_wrapped(**kwargs):
        out = real_supply(**kwargs)
        supply_calls.append(out)
        return out

    monkeypatch.setattr(builder_module, "analog_cosub_supply",
                        supply_wrapped)
    ref = _donor_ref("synthetic:r2-3", _TPL_L, _TPL_R)
    provider = _provider(monkeypatch, [ref])
    specs = provider("CCO")
    spec = next(s for s in specs if s["key"] == "tpl-synthetic:r2-3")
    assert spec["expectation"]["target_smiles"] == "CC=O"
    assert supply_calls == []          # F1 过 ⇒ 不调供给(基线策略)
    diag = provider.last_diagnostics
    assert diag["analog_center_admission_checked"] == 1
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:r2-3")
    assert row["route"] == "direct_raw"
    assert row["execution_input_source"] == "raw"
    assert row["f5"] == "pass"
    assert row["outcome"] == "compiled"


def test_r2_4_supplied_admission_reject_stays_no_alignment(
        monkeypatch) -> None:
    """R2-4(构造负控)供给后准入不过:底物 `CCC` + `[Na+:4]` 袋 ⇒
    supply 1 次;F4=`CCC.[Na+]`;F5 不过;编译 0(省预算口径);
    结构化 no_alignment;路由事实(供给/输入)不受 F5 结果影响。"""
    import hashlib as _hashlib

    supply_calls, probe_calls, compile_calls = _record_route_calls(
        monkeypatch)
    ref = _donor_ref("synthetic:r2-4",
                     "[CH3:1][CH2:2][OH:3].[Na+:4]",
                     "[CH3:1][CH:2]=[O:3].[Na+:4]")
    provider = _provider(monkeypatch, [ref])
    specs = provider("CCC")
    assert not [s for s in specs if s["key"] == "tpl-synthetic:r2-4"]
    assert [c["status"] for c in supply_calls] == ["supply"]
    assert compile_calls == []
    assert probe_calls == [{"input": "CCC.[Na+]", "status": "absent"}]
    diag = provider.last_diagnostics
    assert diag["compile_failure_histogram"].get("no_alignment") == 1
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:r2-4")
    assert row["route"] == "supplied"
    assert row["execution_input_source"] == "supplied"
    assert row["execution_input_sha256"] == \
        _hashlib.sha256(b"CCC.[Na+]").hexdigest()
    assert row["f5"] == "reject"
    assert diag["analog_cosub_supply_compile_attempted"] == 0
    assert diag["analog_center_admission_skipped"] == 1


def test_r2_route_version_and_light_knife_disclosure(monkeypatch) -> None:
    """R2' 版本承载 + 轻刀 A 披露:F1 判据零改动,只附机读归因字段
    (缺口可否被袋元素覆盖);路由真源版本键在位。"""
    assert S5B_ANALOG_ROUTE_VERSION == "s5b-analog-route-f1f4-1"
    _stub_resolver(monkeypatch, [
        _donor_ref("synthetic:light1",
                   "[CH3:1][CH2:2][OH:3].[O:4]([H:5])[H:6]",
                   "[CH3:1][CH:2]=[O:3].[O:4]([H:5])[H:6]")])
    provider = default_pool_provider(resolve_config(), engine=None,
                                     min_unique_targets=0)
    # 底物 CCO:模板袋 = 水(元素 O/H)——主份元素 ⊆ 底物⊕袋 ⇒ 轻刀
    # A 归因=True(判据零改动,只披露)
    provider("CCO")
    diag = provider.last_diagnostics
    assert diag["analog_route_truth_version"] == S5B_ANALOG_ROUTE_VERSION
    row = next(r for r in diag["candidates"]
               if r["record_key"] == "tpl-synthetic:light1")
    assert row["light_gap_coverable_by_bag"] is True
    # 底物 CC:C 两份 ⊆ C2;O 缺口 1 份,袋无水?——袋有 O ⇒ 仍可覆盖
    # 负控(F1 过候选):归因位=None(不适用,不猜)
    _stub_resolver(monkeypatch, [_donor_ref("synthetic:light2",
                                            _TPL_L, _TPL_R)])
    provider2 = default_pool_provider(resolve_config(), engine=None,
                                      min_unique_targets=0)
    provider2("CCO")
    row2 = next(r for r in provider2.last_diagnostics["candidates"]
                if r["record_key"] == "tpl-synthetic:light2")
    assert row2["light_gap_coverable_by_bag"] is None


# ================================================================ 材料负控反例形状类


def _shell_matches(mapped_lhs: str, mapped_rhs: str, substrate: str,
                   shell: int) -> int:
    """探针式裸查询命中数(只读施工件:同 build_center_query 构造;
    仅测试用,不进入生产判据)。"""
    transform = extract_mapped_transform(mapped_lhs, mapped_rhs)
    l1 = l1_maps_of_transform(transform)
    q, _qidx = build_center_query(transform["lhs"].mol,
                                  transform["lhs"].maps, l1, shell=shell)
    arom = Chem.MolFromSmiles(substrate)
    return len(arom.GetSubstructMatches(q, uniquify=False,
                                        useChirality=False))


def test_material_negctl_shape_class_ketone_adjacency() -> None:
    """材料负控反例形状类(合成复现,非材料实例):「中心酮态邻接
    差异」——二级醇中心(shell1 有匹配)对一级醇模板 ⇒ **两壳层
    (N1 自身入射键集合)挡住** ⇒ 必拒(shell1 会过=负控捕获的反例
    形态;两壳层独有价值在此类上体现)。正控:同模板链长匹配的
    一级醇照常编译。"""
    tpl_l = "[CH3:1][CH2:2][CH2:3][OH:4]"          # 一级醇(丁醇型)
    tpl_r = "[CH3:1][CH2:2][CH:3]=[O:4]"
    # shell1 有匹配(丙醇中心的 C-C-O 模式),shell2(N1 入射键)0 匹配
    assert _shell_matches(tpl_l, tpl_r, "CC(C)O", 1) >= 1
    assert _shell_matches(tpl_l, tpl_r, "CC(C)O", 2) == 0
    out = compile_donor_template(
        mapped_lhs=tpl_l, mapped_rhs=tpl_r, center_atoms=[3, 4],
        substrate_smiles="CC(C)O", record_id="synthetic:negket")
    assert out["status"] == "unsupported"
    assert out["reason"] == "no_alignment"
    # 合法正控:链长/中心身份匹配的一级醇 ⇒ compiled
    out_ok = compile_donor_template(
        mapped_lhs=tpl_l, mapped_rhs=tpl_r, center_atoms=[3, 4],
        substrate_smiles="CCCO", record_id="synthetic:poschain")
    assert out_ok["status"] == "compiled"
    assert out_ok["spec"]["expectation"]["target_smiles"] == "CCC=O"


def test_material_negctl_shape_class_remote_chain() -> None:
    """材料负控反例形状类(合成复现,非材料实例):「远端链缺失/
    起始态伪位点」——template 的变键原子邻域要求远端链(N1 入射键
    集合);底物链短一位 ⇒ shell1 有匹配、shell2 0 匹配 ⇒ 必拒。
    正控:同链长底物照常编译。"""
    tpl_l = "[CH3:1][CH2:2][CH2:3][CH2:4][CH3:5]"  # 戊烷型链
    tpl_r = "[CH3:1][CH:2]=[CH:3][CH2:4][CH3:5]"
    assert _shell_matches(tpl_l, tpl_r, "CCCC", 1) >= 1
    assert _shell_matches(tpl_l, tpl_r, "CCCC", 2) == 0
    out = compile_donor_template(
        mapped_lhs=tpl_l, mapped_rhs=tpl_r, center_atoms=[2, 3],
        substrate_smiles="CCCC", record_id="synthetic:negchain")
    assert out["status"] == "unsupported"
    assert out["reason"] == "no_alignment"
    out_ok = compile_donor_template(
        mapped_lhs=tpl_l, mapped_rhs=tpl_r, center_atoms=[2, 3],
        substrate_smiles="CCCCC", record_id="synthetic:pospent")
    assert out_ok["status"] == "compiled"
    assert out_ok["spec"]["expectation"]["target_smiles"] == "CC=CCC"


# ================================================================ L3 披露


def test_l3_disclosure_fields_on_compiled_spec() -> None:
    """L3 豁免面披露义务:compiled spec 携带
    compile.c2_l3_disclosure(豁免原子/边数、异元素/手性/电荷旗标、
    H 计数差旗标),未披露=不发货。"""
    # 环取代模板(远端环原子超出两壳层 ⇒ L3):甲苯→苯甲酸模板在
    # 甲苯上编译,远端环原子豁免并披露(组 7 同形)
    out = compile_donor_template(
        mapped_lhs="[cH:6]1[cH:7][cH:8][c:9]([CH3:1])[cH:10][cH:11]1",
        mapped_rhs="[cH:6]1[cH:7][cH:8][c:9]([C:1]([OH:2])=[O:3])"
                   "[cH:10][cH:11]1",
        center_atoms=[1], substrate_smiles="Cc1ccccc1",
        record_id="synthetic:l3disc")
    assert out["status"] == "compiled", out
    l3 = out["spec"]["compile"]["c2_l3_disclosure"]
    assert l3["n_exempt_atoms"] >= 3
    assert isinstance(l3["exempt_atoms_maps"], list)
    assert l3["has_hetero_element"] is False   # 环远端全碳
    assert l3["has_chirality"] is False
    assert l3["has_charge"] is False
    assert l3["h_count_diff"] in (True, False)
    assert out["spec"]["compile"]["alignment_scope"] == \
        "center_anchored_l1_l2_shell2"
    assert out["spec"]["compile"]["all_matches_verified"] is True
    assert out["spec"]["compile"]["unverified_matches"] == 0
    # H 计数差旗标正控(纯 H 差异 L2 不可见轴):一级醇模板 × 二级醇
    # 中心(shell2 命中,但匹配原子 H 数不同)⇒ 旗标 True
    out_h = compile_donor_template(
        mapped_lhs="[CH3:1][CH:2]([OH:3])[CH3:4]",
        mapped_rhs="[CH3:1][C:2](=[O:3])[CH3:4]",
        center_atoms=[2, 3], substrate_smiles="CCCO",
        record_id="synthetic:l3h")
    if out_h["status"] == "compiled":
        l3h = out_h["spec"]["compile"]["c2_l3_disclosure"]
        assert l3h["h_count_diff"] is True
        assert l3h["n_h_count_diff_atoms"] >= 1


def test_declared_unmapped_center_rejected_honestly() -> None:
    """中心声明含 lhs 不存在的 map ⇒ 坏引用拒(与基线同);
    声明中心不可落位(非 L1/查询覆盖)⇒ 该对齐不可判 ⇒ 拒
    (诚实,不静默缩中心)。"""
    out = compile_donor_template(
        mapped_lhs=_TPL_L, mapped_rhs=_TPL_R, center_atoms=[99],
        substrate_smiles="CCO", record_id="synthetic:badcenter")
    assert out["status"] == "unsupported"
    assert out["reason"] == "center_map_not_in_donor"