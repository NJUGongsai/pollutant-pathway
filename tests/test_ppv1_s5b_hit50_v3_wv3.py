"""PPV1 S5b HIT50 v3 W-V3 —— 池深审计与适用性门前置(S5b-pool-pregate-1)。

依据:v3 任务书 W-V3 + 尸检 §1.4(池深 1.18→0.493;analog 编译失败
no_alignment 1955 / transform_no_change 1660)+ W-V3 零模型审计探针
(v2 批 298 题检索面同 corpus 只读重编译,全部数字见交付书):
- no_alignment 1946 中 1829 = 元素缺席(检索噪声,编译必拒)⇒ 前置
  门(template_elements_fit,同源必要条件)在检索层拒、省编译预算,
  **不改池成员/失败原因口径**;
- 真供给损失(v1 曾执行 ∧ v2 拒)= 47 条(39 transform_no_change
  语料 v1 未映射反应原子 + 8 stereo);语料 v2 换装净更差(76<84
  compiled,center 数据缺陷 59)⇒ 不换;stereo 边界维持 unsupported
  (W-V2.4 保留条款,升级须设计复审)。

正负控(任务书 W-V3.3):v1 曾命中的 analog 模板类(合成同构用例:
去氯水解模板)编译通过入池且执行成事件;真不适用(元素缺席)模板
在检索层拒且不占槽。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.real_model import (  # noqa: E402
    ScriptedRealModelAdapter,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    compile_donor_template,
    template_elements_fit,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

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

# 合成 analog 模板(去氯水解;v1 命中模板类同构:Br/Cl→OH 替换或
# 断键离去;与真实 298 金标零重叠的合成小分子)
_DECHLOR_LHS = "[OH:1][c:2]1[cH:3][cH:4][cH:5][cH:6][c:7]1[Cl:8]"
_DECHLOR_RHS = "[OH:1][c:2]1[cH:3][cH:4][cH:5][cH:6][cH:7]1"
_SUBSTRATE = "Oc1ccccc1Cl"


def _ref(record_id: str, lhs: str, rhs: str,
         center: list[int]) -> SimpleNamespace:
    return SimpleNamespace(record_id=record_id, mapped_lhs=lhs,
                           mapped_rhs=rhs, center_atoms=center)


def _patch_resolver(monkeypatch, refs_by_substrate: dict):
    """把 builder 内构造的 AnalogSourceResolver 换成合成检索面。"""
    import pathway_v43.services.analog_source as analog_source

    class _FakeResolver:
        analog_corpus_version = "v1"

        def __init__(self, config):
            self.config = config

        def templates_similar_to(self, substrate, threshold=0.45,
                                 top_k=24):
            return list(refs_by_substrate.get(str(substrate), []))

    monkeypatch.setattr(analog_source, "AnalogSourceResolver",
                        _FakeResolver)


# ================================================================ 前置门

def test_wv3_template_elements_fit_unit() -> None:
    """对齐必要条件 helper:元素多重集 ⊆ 判定;解析失败 fail-open
    (坏输入仍由编译层结构化拒,前置门不新增拒因)。"""
    assert template_elements_fit(_DECHLOR_LHS, _SUBSTRATE) is True
    # Br 荧光团模板对氯酚底物:Br 缺席 ⇒ False
    assert template_elements_fit(
        _DECHLOR_LHS.replace("[Cl:8]", "[Br:8]"), _SUBSTRATE) is False
    # 解析失败 ⇒ True(不拒编译层会拒的东西)
    assert template_elements_fit("not-a-smiles", _SUBSTRATE) is True
    assert template_elements_fit(_DECHLOR_LHS, "not-a-smiles") is True
    assert template_elements_fit("", _SUBSTRATE) is True


def test_wv3_pregate_pool_unchanged_and_diagnostics(
        monkeypatch) -> None:
    """前置门:元素缺席模板在检索层拒(no_alignment 同口径计数;
    另计 analog_pregate_skipped),池成员与编译失败直方图语义不变,
    省编译预算(编译调用不发生)。"""
    good = _ref("syn-dechlor", _DECHLOR_LHS, _DECHLOR_RHS, [7, 8])
    bad = _ref("syn-bromo", _DECHLOR_LHS.replace("[Cl:8]", "[Br:8]"),
               _DECHLOR_RHS, [7, 8])
    _patch_resolver(monkeypatch, {_SUBSTRATE: [bad, good]})
    provider = default_pool_provider(resolve_config(), engine=None)
    pool = provider(_SUBSTRATE)
    diag = provider.last_diagnostics
    # 池成员:仅好模板编译入池(坏模板被前置门拒,不占槽)
    assert [s["key"] for s in pool] == ["tpl-syn-dechlor"]
    assert pool[0]["product_smiles"] == "Oc1ccccc1"
    # 失败口径:no_alignment 计数含前置拒(语义与编译层一致)
    assert diag["compile_failure_histogram"] == {"no_alignment": 1}
    assert diag["analog_pregate_skipped"] == 1
    assert diag["n_analog_compiled"] == 1
    # 前置门真不调用编译:monkeypatch 编译入口计数(同判据证据)
    import pathway_v43.pollutant.s5b_compiler as compiler_mod

    calls = {"n": 0}
    real_compile = compiler_mod.compile_donor_template

    def _counting(*args, **kwargs):
        calls["n"] += 1
        return real_compile(*args, **kwargs)

    monkeypatch.setattr(compiler_mod, "compile_donor_template", _counting)
    provider2 = default_pool_provider(resolve_config(), engine=None)
    pool2 = provider2(_SUBSTRATE)
    assert calls["n"] == 1  # 仅好模板进编译
    assert [s["key"] for s in pool2] == ["tpl-syn-dechlor"]


# ================================================================ 全链

def test_wv3_analog_template_compiles_into_pool_and_executes(
        tmp_path) -> None:
    """正控(v1 曾命中的 analog 模板类合成同构用例):corpus 形状
    模板 → provider 编译入池 → 公共链执行成事件(产物=苯酚+离去
    Cl 组分,净产物集合完整)。"""
    good = _ref("syn-dechlor", _DECHLOR_LHS, _DECHLOR_RHS, [7, 8])
    compiled = compile_donor_template(
        mapped_lhs=_DECHLOR_LHS, mapped_rhs=_DECHLOR_RHS,
        center_atoms=[7, 8], substrate_smiles=_SUBSTRATE,
        record_id="syn-dechlor", mapping_origin="native",
        alignment_ref="corpus-template:syn-dechlor", key_prefix="tpl")
    assert compiled["status"] == "compiled", compiled
    spec = dict(compiled["spec"])
    spec["key"] = "tpl-syn-dechlor"
    spec["transformation_ref"] = "syn-dechlor"
    spec["origin_group_key"] = "analog-template:syn-dechlor"
    spec["coefficient"] = 1
    # 无模型(池直供)执行:事件提交 + 产物组分完整
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="wv3-chain", smiles=_SUBSTRATE,
        plan={"pools": {_SUBSTRATE: [spec]}},
        profile_policy=dict(
            _PROFILE, search_limits=dict(
                _PROFILE["search_limits"], max_real_model_requests=0)))
    assert summary["counts"]["events"] >= 1
    import sqlite3

    conn = sqlite3.connect(
        str(tmp_path / "runs" / "wv3-chain" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    events = [json.loads(r["payload"]) for r in conn.execute(
        "SELECT payload FROM events")]
    states = {str(r["state_id"]): json.loads(r["payload"]) for r in
              conn.execute("SELECT state_id, payload FROM states")}
    conn.close()
    products = set()
    for payload in events:
        for p in (payload.get("participants") or []):
            if p.get("side") == "product":
                state = states.get(str(p.get("state_ref") or "")) or {}
                products.add(str(state.get("smiles_isomeric") or ""))
    # 净产物集合完整:主产物苯酚 + 离去 Cl 组分(事件参与物语义)
    assert "Oc1ccccc1" in products and "Cl" in products, products


# ================================================================ 边界冻结

def test_wv3_stereo_boundary_stays_unsupported() -> None:
    """负控(边界冻结):W-V3 审计证实的真供给损失类之一 = 立体
    消解型氧化(v1 命中模板 env:EAWAG-BBD:bt0002#r0032:手性二级醇
    → 酮,立体中心随 sp3→sp2 消解)。stereo 边界维持 unsupported
    (W-V2.4 保留条款:升级须先交设计复审,不因数量压力放行)。
    使用仓内授权语料资产(只读;缺席则跳过)。"""
    from pathway_v43.services.analog_source import AnalogSourceResolver

    corpus = (REPO_ROOT / "assets" / "analog" /
              "corpus_templates_v1.jsonl")
    if not corpus.is_file():
        pytest.skip("仓内 analog 语料缺席")
    resolver = AnalogSourceResolver(resolve_config())
    ref = resolver.resolve_template("env:EAWAG-BBD:bt0002#r0032")
    if ref is None:
        pytest.skip("语料无该 record")
    out = compile_donor_template(
        mapped_lhs=str(ref.mapped_lhs or ""),
        mapped_rhs=str(ref.mapped_rhs or ""),
        center_atoms=[int(x) for x in (ref.center_atoms or [])],
        substrate_smiles="CC(O)c1ccccc1",
        record_id="env:EAWAG-BBD:bt0002#r0032",
        mapping_origin="native",
        alignment_ref="corpus-template:env:EAWAG-BBD:bt0002#r0032",
        key_prefix="tpl")
    assert out["status"] == "unsupported"
    assert out["reason"] == "stereo_edit_unsupported"
