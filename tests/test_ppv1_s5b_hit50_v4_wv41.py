"""PPV1 S5b HIT50 v4 W-V4.1 —— RHEA 主语料 recorded 直通接线
(S5b-corpus-retrieval-1 / s5b-pool-policy-2;零网络、零金标)。
**W-V4.1-R1 回修(Codex v4 复审 S5B-V4-01,2026-10-10)**:
S5b-corpus-retrieval-2 / s5b-pool-policy-3 ——共底物 component
许可收口:没有已审定且实际消费的共底物参与物/原子来源语义时,
有共底物的 component 记录编译前结构化 unsupported
(corpus_cosubstrate_participants_unsupported),不产 spec/不产
event;共用许可规则在 find_corpus_recorded_exact 生效(池/公开链
从源头拿不到坏 spec);判据/AtomTool/冻结评测尺子零改动。
**W-V4b(2026-10-10)**:池策略随 recorded 两通道编译面扩大升版
s5b-pool-policy-4(池成员变化;池策略配置零变化;cosubstrate 许可
零触碰);stereo 消解型夹具按 P1 修订(见 neg2/空池测试)。

依据:v4 任务书 §4(用户六决策 ①②③,2026-10-10)+ §3 入口矩阵
+ Codex v4 复审 §4.3/§8(共底物诚实拒分支最低收口):
corpus_v1(43,177 行=RHEA 37,100 + enviPath 6,077;18,550 master ×
LR/RL 双行;8,502 通配行;全库无原生映射)接入 recorded 直通供给,
判据/分层/推断映射/产物多重集 gate 全部沿用 recorded_source 现行
实现,不另写第二套。

正负控(任务书 §4.4 十一类,W2 七类全保留 + corpus 特有四类;
R1 新增共底物拒族):
- 正控:**整串严格**(RHEA 同构)编译+公共链执行;whole 多组分
  donor 整串入池(底物==donor 全串);RL 方向行整串按自身书写
  编译;master 双向两行各自供给(双方向分层引用);EAWAG 水解
  能力(单组分 donor,find_recorded_exact 零改动);
- **R1 共底物拒族(全形态)**:kind=component 且 co_substrates
  非空 ⇒ 编译前 corpus_cosubstrate_participants_unsupported——
  同根 LR/RL、可锚有机共底物(CCO.CC→CCOCC 键合型)、不可锚
  断连辅因子(吡啶样)、不同元素/未知角色共底物、配平增强
  (CCO.C=C=O→CCOC(C)=O)、底物恒等仅共组分变化、重复组分
  (CCO.CCO)全覆盖;保留源行/方向/共底物声明/可追溯拒因;
- ①源哈希篡改(corpus sha ≠ identity)拒;②CN 同而 strict 异 ⇒
  cn_candidate 不升 strict;③方向反(RL 行按自身书写,不冒充另一侧);
  ④另一底物 ⇒ 不属检索面;⑤过滤单产品卡冒完整 ⇒ product_set_
  mismatch;⑥缺产物/来源 ⇒ record_missing_or_incomplete;⑦映射
  枚举触顶 ⇒ truncated 拒;⑧unmapped 冒原生映射来源拒;⑨provenance
  缺失拒;⑩通配行 unsupported_wildcard_atom 拒;⑪master 双向重复
  不占双槽(池侧同签名去重)+方向冒充拒。

合成夹具与真实 298 金标零重叠(乙醇/丙醇/乙酸乙酯级合成小分子,
沿 W2 既有夹具纪律);授权语料实盘用例只读、缺席则 skip。
"""

from __future__ import annotations

import hashlib
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
    CORPUS_RETRIEVAL_SEMANTICS,
    CORPUS_RETRIEVAL_VERSION,
    RECORDED_SOURCE_VERSION,
    RecordedSourceError,
    compile_recorded_reaction,
    find_corpus_recorded_exact,
    load_corpus_index,
    reset_corpus_cache,
    reset_library_cache,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    ScriptedRealModelAdapter,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_POOL_POLICY_VERSION,
    build_question_batch,
    default_pool_provider,
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

# 合成底物(与真实 298 金标零重叠的合成小分子;W2 夹具纪律)
_SUB = "CCOC(C)=O"          # 乙酸乙酯(组分级匹配/共底物声明)
_SUB_WHOLE = "CCCO"         # 丙醇(整串严格)
_SUB_RL = "CCO"             # 乙醇(RL 行组分级)


def _rhea_row(rid, mid, direction, donor_a, comps, product_b, pcomps,
              *, ec=None, prov="f" * 64, extra=None) -> dict:
    row = {
        "atom_mapping": None, "direction": direction,
        "donor_A_smiles": donor_a, "donor_components": comps,
        "ec": ec, "mapping_status": "absent", "master_id": mid,
        "parse_note": "rxn-parsed", "product_B_smiles": product_b,
        "product_components": pcomps, "provenance_sha256": prov,
        "reaction_smiles": f"{donor_a}>>{product_b}",
        "record_id": rid, "source_id": rid, "source_type": "rhea",
    }
    row.update(extra or {})
    return row


def _envi_row(rid, donor_a, comps, product_b, pcomps, *, prov=None,
              extra=None) -> dict:
    row = {
        "atom_mapping": None, "direction": None,
        "donor_A_smiles": donor_a, "donor_components": comps,
        "ec": None, "mapping_status": "absent", "master_id": None,
        "parse_note": "envipath-eawag-sediment",
        "product_B_smiles": product_b, "product_components": pcomps,
        "provenance_sha256": prov, "reaction_smiles": None,
        "record_id": rid, "source_id": "", "source_type": "envipath",
    }
    row.update(extra or {})
    return row


def _synth_corpus_rows() -> list[dict]:
    """合成 corpus(正控 + 负控行;RHEA/enviPath 形态混合)。"""
    return [
        # 正控:整串严格(单组分 donor == 底物,氧化形)
        _rhea_row("rhea:90001", "90000", "LR", _SUB_WHOLE,
                  [_SUB_WHOLE], "CCC(=O)O", ["CCC(=O)O"]),
        # 正控:组分级 + 共底物声明(酯水解;水=共底物)
        _rhea_row("rhea:90003", "90002", "LR", f"{_SUB}.O",
                  [_SUB, "O"], "CC(=O)O.CCO", ["CC(=O)O", "CCO"]),
        # 正控:同 master 的 RL 行(书写方向=生化反方向)
        _rhea_row("rhea:90004", "90002", "RL", "CC(=O)O.CCO",
                  ["CC(=O)O", "CCO"], f"{_SUB}.O", [_SUB, "O"]),
        # 正控:可编译的 RL 行(缩合;底物=乙醇组分)
        _rhea_row("rhea:90006", "90005", "RL", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
        # 正控:同 master 的 LR 行(裂解;底物=整串)
        _rhea_row("rhea:90007", "90005", "LR", "CCOCC",
                  ["CCOCC"], "CCO.CC", ["CCO", "CC"]),
        # 负控②:CN 同而 strict 异(手性 donor vs 非手性底物)
        _rhea_row("rhea:90009", "90008", "LR", "C[C@H](O)Cl",
                  ["C[C@H](O)Cl"], "CC(=O)Cl", ["CC(=O)Cl"]),
        # 负控⑩:通配行(产品侧通配,donor 干净 ⇒ 检索到即拒)
        _rhea_row("rhea:90011", "90010", "LR", _SUB_WHOLE,
                  [_SUB_WHOLE], "*CCO", ["*CCO"]),
        # 负控⑩':donor 侧通配(不可检索=天然不供给)
        _rhea_row("rhea:90013", "90012", "LR", "*C(O)Cl",
                  ["*C(O)Cl"], "*C(=O)Cl", ["*C(=O)Cl"]),
        # 负控⑨:provenance 缺失(enviPath 带产物行 5,497 行实况形态)
        _envi_row("env:SYNTH:0001", _SUB_WHOLE, [_SUB_WHOLE],
                  "CCO", ["CCO"]),
        # 负控⑥':无产物(educt-only 形态;有 provenance)
        _envi_row("env:SYNTH:0002", _SUB_WHOLE, [_SUB_WHOLE],
                  None, [], prov="a" * 64),
        # 负控⑧:原生映射冒充(corpus_v1 全库 absent/null)
        _rhea_row("rhea:90017", "90016", "LR", _SUB_WHOLE,
                  [_SUB_WHOLE], "CC=O", ["CC=O"],
                  extra={"mapping_status": "native",
                         "atom_mapping": "[CH3:1][CH2:2][O:3]>>"}),
        # 负控⑪:master 双向重复(两行同 donor 同产物 ⇒ 池侧单槽)
        _rhea_row("rhea:90019", "90018", "LR", "CCCO",
                  ["CCCO"], "CCC(=O)O", ["CCC(=O)O"]),
        _rhea_row("rhea:90020", "90018", "RL", "CCCO",
                  ["CCCO"], "CCC(=O)O", ["CCC(=O)O"]),
    ]


class _CorpusEngine:
    """W-V4.1 测试桩:identity_block(library+corpus 路径/哈希)+ expand_raw。

    合成库/corpus 行与真实 298 金标零重叠(合成小分子;W2 纪律)。"""

    def __init__(self, tmp: Path, corpus_rows: list[dict] | None = None,
                 library_rows: list[dict] | None = None):
        import tempfile

        self._tmpdir = Path(tempfile.mkdtemp(
            prefix="wv41-synth-", dir=str(tmp)))
        corpus = self._tmpdir / "corpus_v1.jsonl"
        corpus.write_text(
            "\n".join(json.dumps(r) for r in
                      (corpus_rows if corpus_rows is not None
                       else _synth_corpus_rows())) + "\n",
            encoding="utf-8")
        lib = self._tmpdir / "library_full.jsonl"
        lib.write_text(
            "\n".join(json.dumps(r) for r in (library_rows or [])) + "\n",
            encoding="utf-8")
        self.identity_block = {
            "library_path": str(lib),
            "library_sha256": hashlib.sha256(
                lib.read_bytes()).hexdigest(),
            "corpus_v1_path": str(corpus),
            "corpus_v1_sha256": hashlib.sha256(
                corpus.read_bytes()).hexdigest(),
        }
        self._library_rows = library_rows or []

    def expand_raw(self, smiles: str, case_id: str = "c") -> dict:
        rows = []
        seen = set()
        for record in self._library_rows:
            if str(record.get("donor_smiles")) != str(smiles):
                continue
            rid = f"{record['btid']}#{record['reac_id']}"
            if rid in seen:
                continue
            seen.add(rid)
            rows.append({
                "product_smiles": record["product_smiles"],
                "product_smiles_full": record["product_smiles"],
                "source": "eawag_lookup", "layer": "lookup",
                "eawag_reactions": [rid], "donor_exact_match": True,
                "n_evidence": 1, "tanimoto": 1.0,
                "ion_filtered": False, "cofactor_filtered": False,
                "filtered": False,
            })
        return {"lookup": rows, "pred_edges": [], "merged_edges": rows,
                "n_pred_candidates": 0, "n_lookup": len(rows),
                "budget_cut": False, "pool_capped": False,
                "canonical_smiles": smiles}


@pytest.fixture(autouse=True)
def _clean_caches():
    reset_library_cache()
    reset_corpus_cache()
    yield
    reset_library_cache()
    reset_corpus_cache()


# ================================================================ 冻结登记

def test_wv41_semantics_frozen_and_versions_registered() -> None:
    """§1 冻结登记(开工先于接线):检索语义版本 + 池策略升版 +
    EAWAG 通道身份零变化(单变量归因前提)。
    W-V4.1-R1:corpus-retrieval-1→2(共底物 component 许可变化)、
    pool-policy-2→3(池成员变化:组分级 spec 收缩)。"""
    assert CORPUS_RETRIEVAL_VERSION == "s5b-corpus-retrieval-2"
    sem = dict(CORPUS_RETRIEVAL_SEMANTICS)
    assert sem["substrate_retrieval_scope"] == "cn_identity_wide"
    # R1:组分级+共底物声明,且 component-with-co-substrate 编译前拒
    assert "component_level_with_co_substrate_declaration" in \
        sem["donor_side_semantics"]
    assert "structured-unsupported BEFORE compilation" in \
        sem["donor_side_semantics"]
    assert sem["cosubstrate_permission"].startswith(
        "no approved and consumed co-substrate participant")
    assert "no element/role/" in sem["cosubstrate_permission"]
    assert "FULL donor string as lhs" in sem["whole_string_semantics"]
    assert "no strict promotion" in sem["tier_rule"]
    assert sem["wildcard_policy"] == (
        "row_level_unsupported_wildcard_atom_reject")
    assert "both_direction_rows_retained" in sem[
        "master_direction_policy"]
    assert "native" in sem["mapping_policy"]
    # 池策略升版(W-V4b:池成员变化——recorded 两通道编译面因公共
    # 编译判据链修复扩大;池策略配置零变化;cosubstrate 许可零触碰)
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-4"
    # EAWAG recorded 源身份:W-V4b 升版(推断映射预算/枚举面扩展;
    # find_recorded_exact 检索/分层语义不变)
    assert RECORDED_SOURCE_VERSION == "s5b-recorded-source-2"


# ================================================================ 正控族

def test_wv41_whole_string_strict_compiles_and_executes(tmp_path) -> None:
    """正控(RHEA 整串同构):单组分 donor == 底物 ⇒ strict exact,
    推断映射编译,公共链执行(中心/严格目标核对)。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB_WHOLE, engine=engine)
    tiers = {c["tier"] for c in out["candidates"]}
    assert "recorded_strict_exact" in tiers
    # 检索序:strict 整串在前
    first = out["candidates"][0]
    assert first["tier"] == "recorded_strict_exact"
    assert first["donor_match_kind"] == "whole"
    assert first["donor_smiles"] == _SUB_WHOLE
    assert first["direction"] == "LR"
    assert first["source_type"] == "rhea"
    assert first["co_substrates"] == []
    assert first["compile"] is not None, first["compile_reason"]
    spec = first["compile"]
    assert spec["key"] == f"rec-{first['record_key']}"
    assert spec["compile"]["mapping_origin"] == "inferred"
    assert spec["compile"]["verified_product_set"] is True
    assert "corpus" not in spec or spec["corpus"]  # spec 携带 corpus 元数据
    assert spec["corpus"]["donor_match_kind"] == "whole"
    assert spec["corpus"]["direction"] == "LR"
    assert spec["corpus"]["co_substrates"] == []
    # 公共链执行(与编译器同一迁移结果)
    execution = execute_atomtool_expansion(
        substrate_smiles=_SUB_WHOLE, tool_inputs={
            "edits": spec["edits"], "donor": spec["donor"],
            "alignment": spec["alignment"],
            "expectation": spec["expectation"]})
    assert execution["diagnostic"]["reaction_center_match"] is True
    assert execution["diagnostic"]["strict_target_match"] is True
    assert out["diagnostics"]["n_strict_exact"] >= 1


def test_wv41_component_co_substrate_honest_unsupported(tmp_path) -> None:
    """R1 负控(组分级+共底物声明,决策②收口):底物=donor 组分 1,
    水组分声明为共底物(不静默丢弃)——**没有已审定且实际消费的共底物
    参与物/原子来源语义 ⇒ 编译前结构化 unsupported**(不产 spec/不产
    event;新 component 水解如实拒,不给无机器证据的同类例外)。

    拒因与声明完整可追溯:源行 record_key/行号/donor 整串、方向、
    master、共底物声明(SMILES+严格身份)、记录产物。旧行为(把水
    折成 add_atom 新原子、事件只声明底物→产物)在父 HEAD 为红。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB, engine=engine)
    comp = [c for c in out["candidates"]
            if c["donor_match_kind"] == "component"]
    assert comp, out["diagnostics"]
    cand = comp[0]
    assert cand["tier"] == "recorded_strict_exact"
    assert cand["matched_component"] == _SUB
    # 共底物声明:其余组分(水)诚实列出,不冒充单底物反应
    assert [c["smiles"] for c in cand["co_substrates"]] == ["O"]
    assert cand["co_substrates"][0]["strict_identity"] == "O"
    # R1:编译前结构化 unsupported——零 spec、零坏 event 供给
    assert cand["compile"] is None
    assert cand["compile_status"] == "unsupported"
    assert cand["compile_reason"] == \
        "corpus_cosubstrate_participants_unsupported"
    detail = cand["compile_detail"]
    assert detail["record_key"].startswith("rhea:90003@L")
    assert detail["line_no"] >= 1
    assert detail["donor_A_smiles"] == f"{_SUB}.O"
    assert detail["direction"] == "LR"
    assert detail["master_id"] == "90002"
    assert [c["smiles"] for c in detail["co_substrates"]] == ["O"]
    assert detail["products"] == ["CC(=O)O", "CCO"]
    assert "no approved and consumed" in detail["permission_note"]
    # 检索面分层计数 + 专用拒因计数(逐层注明,不冒充编译数)
    d = out["diagnostics"]
    assert d["n_strict_exact"] >= 1
    assert d["n_cosubstrate_participants_unsupported"] >= 1
    assert d["compile_failure_histogram"][
        "corpus_cosubstrate_participants_unsupported"] >= 1
    # 池层:共用许可在 find 入口生效 ⇒ 组分级候选不产池槽
    provider = default_pool_provider(None, engine=engine)
    pool = [s for s in provider(_SUB) if s.get("corpus")]
    assert pool == []


def test_wv41_rl_row_follows_own_writing_both_directions_supply(
        tmp_path) -> None:
    """决策③ 双向保留(R1 修订):master 90005 的 LR(裂解)整串行
    照旧编译供给(底物=donor 全串 CCOCC ⇒ whole,co_substrates 空);
    RL 行(缩合,底物=乙醇组分)命中检索面、按本行书写引用——但
    **组分带共底物(乙基)⇒ 编译前结构化 unsupported**(R1 收口:
    乙醇→CCOCC 单底物事件=共底物原子折成新增原子,不供给)。"""
    engine = _CorpusEngine(tmp_path)
    # 整串底物 → LR 行(裂解):whole 正控保持
    out_lr = find_corpus_recorded_exact(
        substrate_smiles="CCOCC", engine=engine)
    lr = [c for c in out_lr["candidates"]
          if c["record_id"] == "rhea:90007"]
    assert lr and lr[0]["tier"] == "recorded_strict_exact"
    assert lr[0]["direction"] == "LR"
    assert lr[0]["donor_match_kind"] == "whole"
    assert lr[0]["co_substrates"] == []
    assert lr[0]["compile"] is not None
    assert sorted([lr[0]["compile"]["product_smiles"]]
                  + lr[0]["compile"]["coproducts"]) == \
        sorted(["CCO", "CC"])
    # 组分底物(乙醇)→ RL 行(缩合):检索面命中、本行书写引用,
    # R1 共底物许可 ⇒ 编译前拒(可锚有机共底物,方向声明保留)
    out_rl = find_corpus_recorded_exact(
        substrate_smiles=_SUB_RL, engine=engine)
    rl = [c for c in out_rl["candidates"]
          if c["record_id"] == "rhea:90006"]
    assert rl, out_rl["diagnostics"]
    assert rl[0]["direction"] == "RL"
    assert rl[0]["master_id"] == "90005"
    assert rl[0]["donor_match_kind"] == "component"
    assert rl[0]["matched_component"] == _SUB_RL
    assert [c["smiles"] for c in rl[0]["co_substrates"]] == ["CC"]
    assert rl[0]["compile"] is None
    assert rl[0]["compile_reason"] == \
        "corpus_cosubstrate_participants_unsupported"
    assert rl[0]["compile_detail"]["direction"] == "RL"
    assert rl[0]["compile_detail"]["donor_A_smiles"] == "CCO.CC"
    # 酯水解 master 90002 的 RL 行:底物=酸侧组分,检索面命中、按
    # 自身书写引用(不冒充 LR 侧);组分带共底物 ⇒ 同根同拒
    out_acid = find_corpus_recorded_exact(
        substrate_smiles="CC(=O)O", engine=engine)
    acid_rows = {c["record_id"] for c in out_acid["candidates"]}
    assert "rhea:90004" in acid_rows
    for c in out_acid["candidates"]:
        if c["record_id"] == "rhea:90004":
            assert c["direction"] == "RL"
            assert c["matched_component"] == "CC(=O)O"
            assert c["compile"] is None
            assert c["compile_reason"] == \
                "corpus_cosubstrate_participants_unsupported"


def test_wv41_cosubstrate_component_reject_family(tmp_path) -> None:
    """R1 负控族(Codex v4 §4.3/§8.4 全形态):有共底物的 component
    记录,不问元素/角色/可锚性/方向/是否配平/底物是否恒等——一律
    编译前结构化 unsupported(零 spec/零 event),拒因可追溯;同批
    整串/whole 多组分正控照旧编译。

    覆盖:同根 LR/RL 双方向、可锚有机共底物(键合,父 HEAD 可编译
    =真行为红)、不可锚断连辅因子(吡啶样)、不同元素共底物(S)、
    未知角色(苯)、配平增强(乙烯酮,父 HEAD 可编译)、仅共组分
    变化(底物恒等)、重复组分(CCO.CCO);正控 = whole 氧化 +
    whole 多组分(CCO.CC 整串)。"""
    rows = [
        # 负控:同根 LR/RL(可锚有机共底物 CC;两方向各自成行)
        _rhea_row("rhea:91001", "91000", "LR", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
        _rhea_row("rhea:91002", "91000", "RL", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
        # 负控:不可锚断连辅因子(吡啶共底物;产物氢化吡啶断连)
        _rhea_row("rhea:91003", "91001", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
        # 负控:不同元素共底物(S;产物键合噻唑样)
        _rhea_row("rhea:91004", "91002", "LR", "CCO.CCS",
                  ["CCO", "CCS"], "CCOCCS", ["CCOCCS"]),
        # 负控:未知角色共底物(苯;产物联苯型键合)
        _rhea_row("rhea:91005", "91003", "LR", "CCO.c1ccccc1",
                  ["CCO", "c1ccccc1"], "CCOc1ccccc1",
                  ["CCOc1ccccc1"]),
        # 负控:配平增强(乙烯酮;左右元素/氢数相同,父 HEAD 可编译)
        _rhea_row("rhea:91006", "91004", "LR", "CCO.C=C=O",
                  ["CCO", "C=C=O"], "CCOC(C)=O", ["CCOC(C)=O"]),
        # 负控:底物恒等、仅共组分变化(CC → C=C;底物 CCO 双侧恒等)
        _rhea_row("rhea:91007", "91005", "LR", "CCO.CC",
                  ["CCO", "CC"], "CCO.C=C", ["CCO", "C=C"]),
        # 负控:重复组分(CCO.CCO → CCOCC;第二当量乙醇也是共底物)
        _rhea_row("rhea:91008", "91006", "LR", "CCO.CCO",
                  ["CCO", "CCO"], "CCOCC", ["CCOCC"]),
        # 正控:整串氧化(单组分 donor == 底物,whole)
        _rhea_row("rhea:91011", "91010", "LR", "CCO",
                  ["CCO"], "CC=O", ["CC=O"]),
        # 正控:whole 多组分(donor 全串 == 底物;共底物声明空集)
        _rhea_row("rhea:91012", "91011", "LR", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
    ]
    engine = _CorpusEngine(tmp_path, corpus_rows=rows)
    # ---- 负控族:组分底物(乙醇)⇒ 全部 component 候选编译前拒 ----
    out = find_corpus_recorded_exact(
        substrate_smiles="CCO", engine=engine)
    comp = [c for c in out["candidates"]
            if c["donor_match_kind"] == "component"]
    rejected = {c["record_id"] for c in comp}
    # 91012 对底物 CCO 同样是 component(带 CC 共底物)⇒ 一并拒;
    # 同一行对底物 "CCO.CC" 才是 whole 正控(下方验证)
    assert rejected == {
        "rhea:91001", "rhea:91002", "rhea:91003", "rhea:91004",
        "rhea:91005", "rhea:91006", "rhea:91007", "rhea:91008",
        "rhea:91012"}, sorted(rejected)
    for c in comp:
        assert c["compile"] is None
        assert c["compile_status"] == "unsupported"
        assert c["compile_reason"] == \
            "corpus_cosubstrate_participants_unsupported"
        # 拒因可追溯:源行/方向/共底物声明/记录产物全保留
        d = c["compile_detail"]
        assert d["record_key"].startswith(c["record_id"] + "@L")
        assert d["donor_A_smiles"] == ".".join(
            [c["matched_component"]] +
            [x["smiles"] for x in c["co_substrates"]])
        assert d["direction"] in ("LR", "RL", None)
        assert d["master_id"]
        assert d["products"]
        assert d["permission_note"].startswith(
            "no approved and consumed")
    # 同根 LR/RL 双方向全覆盖(两行各成候选,同因同拒)
    dirs = {c["record_id"]: c["direction"]
            for c in comp if c["record_id"] in
            ("rhea:91001", "rhea:91002")}
    assert dirs == {"rhea:91001": "LR", "rhea:91002": "RL"}
    # 可锚/不可锚/元素/角色/配平/恒等/重复:拒因无例外(单一类目)
    d = out["diagnostics"]
    assert d["n_cosubstrate_participants_unsupported"] == 9
    assert d["compile_failure_histogram"][
        "corpus_cosubstrate_participants_unsupported"] == 9
    # ---- 正控:整串(whole)照旧编译(合法供给保持) ----
    whole = [c for c in out["candidates"]
             if c["donor_match_kind"] == "whole"]
    assert {c["record_id"] for c in whole} == {"rhea:91011"}
    assert whole[0]["compile"] is not None
    assert whole[0]["co_substrates"] == []
    # ---- 正控:whole 多组分(底物==donor 全串)----
    out_multi = find_corpus_recorded_exact(
        substrate_smiles="CCO.CC", engine=engine)
    multi = {c["record_id"]: c for c in out_multi["candidates"]}
    assert "rhea:91012" in multi
    assert multi["rhea:91012"]["donor_match_kind"] == "whole"
    assert multi["rhea:91012"]["co_substrates"] == []
    assert multi["rhea:91012"]["compile"] is not None
    spec = multi["rhea:91012"]["compile"]
    assert [spec["product_smiles"]] + spec["coproducts"] == ["CCOCC"]
    # 池层共用许可:组分候选零槽,整串/whole 正常供给
    provider = default_pool_provider(None, engine=engine)
    pool = provider("CCO")
    rec_keys = [s["key"] for s in pool]
    assert rec_keys == ["rec-rhea:91011@L9"], rec_keys


def test_wv41_real_corpus_asset_retrieval(tmp_path) -> None:
    """授权语料实盘(只读):真 corpus_v1(43,177 行)装配入口
    sha 锚定回读 + 真实 RHEA 行检索/分层/方向字段(资产缺席 skip;
    编译结果如实——真记录的编译失败不是接线缺陷)。"""
    corpus = REPO_ROOT / "assets" / "v3_reactions" / \
        "corpus_env" / "corpus_v1.jsonl"
    if not corpus.is_file():
        pytest.skip("仓内授权 corpus_v1 资产缺席")

    class _RealCorpusEngine:
        identity_block = {
            "corpus_v1_path": str(corpus),
            "corpus_v1_sha256": hashlib.sha256(
                corpus.read_bytes()).hexdigest(),
        }

    engine = _RealCorpusEngine()
    out = find_corpus_recorded_exact(
        substrate_smiles="CCCCC(N)=O", engine=engine, max_reactions=4)
    d = out["diagnostics"]
    assert d["corpus_n_rows"] == 43177
    assert d["corpus_v1_sha256"] == engine.identity_block[
        "corpus_v1_sha256"]
    # 真实 master 10000 LR 行:底物=donor 组分(戊酰胺),水=共底物
    cands = {c["record_id"]: c for c in out["candidates"]}
    assert "rhea:10001" in cands, d
    c = cands["rhea:10001"]
    assert c["tier"] == "recorded_strict_exact"
    assert c["donor_match_kind"] == "component"
    assert c["direction"] == "LR"
    assert c["master_id"] == "10000"
    assert c["ec"] == "3.5.1.50"
    assert [x["smiles"] for x in c["co_substrates"]] == ["O"]
    # R1:新 component 水解也缺参与物规则 ⇒ 如实拒并披露(不给无
    # 机器证据的同类例外);拒因编译前、可追溯(源行/方向/水声明)
    assert c["compile"] is None
    assert c["compile_reason"] == \
        "corpus_cosubstrate_participants_unsupported"
    assert c["compile_detail"]["co_substrates"][0]["smiles"] == "O"
    assert d["n_cosubstrate_participants_unsupported"] >= 1
    # mapping_origin 全部 inferred(全库无原生映射)
    for cand in out["candidates"]:
        if cand["compile"] is not None:
            assert cand["compile"]["compile"]["mapping_origin"] == \
                "inferred"


# ================================================================ 负控族
# (W2 七类 ①–⑦ + corpus 特有 ⑧–⑪;任务书 §4.4 合计十一类)

def test_wv41_neg1_source_hash_tamper_fail_closed(tmp_path) -> None:
    """负控①:corpus 文件 sha ≠ 引擎身份记录(篡改/漂移)⇒
    fail-closed 拒(corpus_hash_mismatch;load_library_index 同款)。"""
    engine = _CorpusEngine(tmp_path)
    path = Path(engine.identity_block["corpus_v1_path"])
    path.write_text(path.read_text() + json.dumps(
        _rhea_row("rhea:99999", "99998", "LR", "CCCO", ["CCCO"],
                  "CCO", ["CCO"])) + "\n", encoding="utf-8")
    with pytest.raises(RecordedSourceError) as excinfo:
        load_corpus_index(engine)
    assert excinfo.value.detail["kind"] == "corpus_hash_mismatch"
    # 身份块缺 corpus 键 ⇒ fail-closed(不静默降级为无 corpus 通道)
    class _NoCorpusEngine:
        identity_block = {"library_path": "x", "library_sha256": "y"}

    with pytest.raises(RecordedSourceError) as excinfo2:
        load_corpus_index(_NoCorpusEngine())
    assert excinfo2.value.detail["kind"] == "corpus_identity_missing"


def test_wv41_neg2_cn_match_not_promoted_to_strict(tmp_path) -> None:
    """负控②(决策①):CN 同(立体盲)而 strict 异 ⇒
    recorded_cn_candidate 不升 strict(分层判据同源,不改)。
    W-V4b 注:该夹具的立体差异恰为消解型(手性 sp3 中心随 C-O
    single→double 键级变化消解,donor 手性声明为派生属性)——编译
    现按 S5b-stereo-dissolution-1 通过(执行后同源复核过),但分层
    仍不升格:strict 供给与 cn 候选的分层判据零变化。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles="CC(O)Cl", engine=engine)
    cands = [c for c in out["candidates"]
             if c["record_id"] == "rhea:90009"]
    assert cands, out["diagnostics"]
    assert cands[0]["tier"] == "recorded_cn_candidate"
    assert cands[0]["donor_smiles"] == "C[C@H](O)Cl"
    # 严格身份不同:计数分层如实
    d = out["diagnostics"]
    assert d["n_strict_exact"] == 0
    assert d["n_cn_candidate"] >= 1
    # W-V4b:消解型立体差异编译通过(手性=键级变化派生属性;执行后
    # 立体同源复核;spec 机读诊断披露)——但 tier 仍是 cn,不升 strict
    assert cands[0]["compile"] is not None
    spec = cands[0]["compile"]
    assert spec["compile"]["stereo_dissolution_applied"] == [2]
    assert spec["expectation"]["target_smiles"] == "CC(=O)Cl"


def test_wv41_neg3_other_substrate_not_in_retrieval_face(tmp_path) -> None:
    """负控③④:另一底物(donor 不含该底物,整串/组分均不命中)⇒
    不属检索面(候选空;方向反形态=底物在产物侧,同样不命中)。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles="c1ccccc1", engine=engine)
    assert out["candidates"] == []
    assert out["diagnostics"]["n_matched_rows"] == 0
    # 不可解析底物:诚实空面(不猜)
    out2 = find_corpus_recorded_exact(
        substrate_smiles="not-a-smiles", engine=engine)
    assert out2["candidates"] == []
    assert out2["diagnostics"]["kind"] == "substrate_unparseable"


def test_wv41_neg5_filtered_single_product_card_rejected(tmp_path) -> None:
    """负控⑤:corpus 记录声明产物集不完整(单产品卡冒完整)⇒
    编译执行组分 ≠ 记录产物集 ⇒ product_set_mismatch 诚实拒
    (compile_recorded_reaction 判据零改动)。"""
    engine = _CorpusEngine(tmp_path)
    # 记录:CCCO → CCO(实际执行还产 C ⇒ 缺行)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB_WHOLE, engine=engine)
    psm = [c for c in out["candidates"]
           if c["compile_reason"] == "product_set_mismatch"]
    # 合成夹具:补一条缺产物记录直接验证编译层判据
    compiled = compile_recorded_reaction(
        substrate_smiles="CCCO", donor_smiles="CCCO",
        products=["CCO"], record_id="wv41-neg-psm")
    assert compiled["status"] == "unsupported"
    assert compiled["reason"] == "product_set_mismatch"
    assert psm == [] or all(c["compile"] is None for c in psm)


def test_wv41_neg6_missing_products_rejected(tmp_path) -> None:
    """负控⑥':缺产物(enviPath educt-only 580 行/RHEA no-structure
    2 行形态)⇒ record_missing_or_incomplete 同款诚实拒。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB_WHOLE, engine=engine)
    hist = out["diagnostics"]["compile_failure_histogram"]
    assert hist.get("record_missing_or_incomplete") == 1


def test_wv41_neg7_mapping_enumeration_truncated_rejects(
        tmp_path, monkeypatch) -> None:
    """负控⑦:推断映射枚举触顶 ⇒ truncated 歧义披露拒(预算纪律
    同源;不静默取首解)。corpus 通道与 EAWAG 共用同一入口。"""
    import pathway_v43.pollutant.recorded_source as rs

    engine = _CorpusEngine(tmp_path)
    monkeypatch.setattr(rs, "_INFER_MATCH_LIMIT", 1)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB_WHOLE, engine=engine)
    hist = out["diagnostics"]["compile_failure_histogram"]
    assert hist.get("mapping_enumeration_truncated", 0) >= 1


def test_wv41_neg8_native_mapping_claim_rejected(tmp_path) -> None:
    """负控⑧:corpus_v1 全库无原生映射——冒充原生映射来源的记录
    (mapping_status!=absent 或 atom_mapping 非空)⇒ 结构化拒
    corpus_native_mapping_claimed;通道产出 mapping_origin 恒 inferred。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB_WHOLE, engine=engine)
    hist = out["diagnostics"]["compile_failure_histogram"]
    assert hist.get("corpus_native_mapping_claimed") == 1
    # 拒因在候选前:冒充行不产候选
    ids = {c["record_id"] for c in out["candidates"]}
    assert "rhea:90017" not in ids
    # 通道产出的所有 compiled spec:mapping_origin 恒 inferred
    for cand in out["candidates"]:
        if cand["compile"] is not None:
            assert cand["compile"]["compile"]["mapping_origin"] == \
                "inferred"


def test_wv41_neg9_provenance_missing_rejected(tmp_path) -> None:
    """负控⑨:记录缺 provenance_sha256(实测 enviPath 带产物行
    5,497 行形态)⇒ corpus_provenance_missing 结构化拒(存在性披露,
    不冒充内容完整性证明)。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB_WHOLE, engine=engine)
    hist = out["diagnostics"]["compile_failure_histogram"]
    assert hist.get("corpus_provenance_missing") == 1
    ids = {c["record_id"] for c in out["candidates"]}
    assert "env:SYNTH:0001" not in ids
    # RHEA 行 provenance 携带披露(存在性,构造期来源指纹)
    for cand in out["candidates"]:
        if cand["source_type"] == "rhea":
            assert cand["provenance_sha256"]
            if cand["compile"] is not None:
                assert cand["compile"]["corpus"][
                    "provenance_sha256"] == cand["provenance_sha256"]


def test_wv41_neg10_wildcard_rows_rejected(tmp_path) -> None:
    """负控⑩(决策③):通配行(含 *)⇒ unsupported_wildcard_atom
    行级拒,不冒充可编译——产品侧通配检索到即拒计数;donor 侧通配
    组分不可检索(天然不供给,不进检索面)。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles=_SUB_WHOLE, engine=engine)
    hist = out["diagnostics"]["compile_failure_histogram"]
    # rhea:90011(donor 干净 CCCO、产物 *CCO):检索到即拒
    assert hist.get("unsupported_wildcard_atom") == 1
    ids = {c["record_id"] for c in out["candidates"]}
    assert "rhea:90011" not in ids
    # rhea:90013(donor 侧通配):不在检索面(不可检索=不供给)
    assert "rhea:90013" not in ids
    assert out["diagnostics"]["n_matched_rows"] >= 5  # 干净面仍在


def test_wv41_neg11_master_duplicate_no_double_slot(tmp_path) -> None:
    """负控⑪:master 90018 双行同 donor 同产物(双向重复形态)⇒
  两行各成候选(分层引用,record_key 互异)但池侧同净反应签名去重
  ——单槽,合并 provenance 留痕;诊断披露 n_master_multirow。"""
    engine = _CorpusEngine(tmp_path)
    out = find_corpus_recorded_exact(
        substrate_smiles="CCCO", engine=engine)
    dups = [c for c in out["candidates"]
            if c["master_id"] == "90018"]
    assert len(dups) == 2, dups
    assert {c["record_id"] for c in dups} == \
        {"rhea:90019", "rhea:90020"}
    assert {c["direction"] for c in dups} == {"LR", "RL"}
    assert {c["record_key"] for c in dups} == {
        "rhea:90019@L12", "rhea:90020@L13"}
    assert out["diagnostics"]["n_master_multirow"] == 1
    # 池侧:同净反应去重单槽(merged provenance 披露双源)
    provider = default_pool_provider(None, engine=engine)
    pool = [s for s in provider("CCCO")
            if str(s.get("key", "")).startswith("rec-rhea:900")]
    # 90001 与 90019/90020 同净反应(丙醇→丙酸)⇒ 全部并为单槽
    rec_specs = [s for s in pool
                 if str(s["key"]).startswith("rec-")]
    assert len(rec_specs) == 1, [s["key"] for s in pool]
    merged = rec_specs[0]["compile"].get("merged_source_keys") or []
    assert len(merged) >= 2  # 同净反应多源合并留痕(不占双槽)


# ================================================================ 池接线

def test_wv41_pool_corpus_appended_after_eawag(tmp_path) -> None:
    """池接线(W-V4b:s5b-pool-policy-4):EAWAG 面(引擎 lookup 序)保持
    零变化在前,corpus **整串**候选追加在后(不同净反应各占一槽);
    component-with-co-substrate 候选(行号更小)共用许可 ⇒ 零池槽 +
    拒因计数(父 HEAD 该行入池=真行为红);corpus_channel=False ⇒
    纯 EAWAG 面(消融对照)。

    corpus 整串行 CCO→CCCO 为合成接线夹具(W2 夹具纪律:合成小分子,
    与真实 298 金标零重叠;仅验证池序/元数据,非化学正控)。"""
    library_rows = [
        {"btid": "btX", "donor_id": "CCO", "donor_smiles": "CCO",
         "package": "SYNTH", "product_sb": "CC=O",
         "product_smiles": "CC=O", "reac_id": "r0001"},
    ]
    corpus_rows = [
        # L1:component 行(带 CC 共底物)——R1 许可 ⇒ 不入池
        _rhea_row("rhea:90006", "90005", "RL", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
        # L2:整串行(单组分 donor)——合法供给
        _rhea_row("rhea:90008", "90007", "LR", "CCO",
                  ["CCO"], "CCCO", ["CCCO"]),
    ]
    engine = _CorpusEngine(tmp_path, corpus_rows=corpus_rows,
                           library_rows=library_rows)
    provider = default_pool_provider(None, engine=engine)
    pool = provider("CCO")
    keys = [s["key"] for s in pool]
    # EAWAG 在前(引擎序),corpus 整串追加在后;component 行零槽
    assert keys == ["rec-btX#r0001", "rec-rhea:90008@L2"], keys
    diag = provider.last_diagnostics
    assert diag["pool_policy_version"] == "s5b-pool-policy-4"
    assert diag["n_recorded_strict_exact"] == 1
    assert diag["n_corpus_strict_exact"] == 2  # 检索分层(strict 层 2 行)
    assert "corpus_diagnostics" in diag
    assert diag["corpus_diagnostics"]["corpus_retrieval_version"] == \
        CORPUS_RETRIEVAL_VERSION
    # 共用许可在 find 入口生效:component 行不产池槽,拒因入直方图
    assert diag["compile_failure_histogram"][
        "corpus_cosubstrate_participants_unsupported"] == 1
    # corpus spec 携带整串语义(共底物声明=空集)
    corpus_spec = pool[1]
    assert corpus_spec["corpus"]["co_substrates"] == []
    assert "empty_set_whole_string_semantics" in \
        corpus_spec["corpus"]["co_substrate_semantics"]
    # 消融开关:corpus_channel=False ⇒ 纯 EAWAG 面(v3 形态)
    provider_v3 = default_pool_provider(
        None, engine=engine, corpus_channel=False)
    pool_v3 = provider_v3("CCO")
    assert [s["key"] for s in pool_v3] == ["rec-btX#r0001"]
    assert "corpus_diagnostics" not in provider_v3.last_diagnostics


def test_wv41_pool_corpus_all_unsupported_honest_empty(tmp_path) -> None:
    """池诚实边界:corpus 候选全编译失败(通配/电荷/共底物等)⇒
    空池 + 失败直方图如实(检索命中数不冒充供给,更不冒充命中)。
    W-V4b:立体夹具改为**纯立体翻转**(C[@H]→C[@@H],无键级变化
    ——消解谓词要求 single→double/triple 变化,纯翻转不消解,维持
    stereo_edit_unsupported;旧夹具 C[C@H](O)Cl→CC(=O)Cl 属消解型,
    现按 P1 编译通过,不再是"全失败"形态)。"""
    corpus_rows = [
        _rhea_row("rhea:90009", "90008", "LR", "C[C@H](O)Cl",
                  ["C[C@H](O)Cl"], "C[C@@H](O)Cl", ["C[C@@H](O)Cl"]),
    ]
    engine = _CorpusEngine(tmp_path, corpus_rows=corpus_rows,
                           library_rows=[])
    provider = default_pool_provider(None, engine=engine)
    pool = provider("CC(O)Cl")
    assert pool == []
    diag = provider.last_diagnostics
    assert diag["n_corpus_cn_candidate"] == 1
    assert diag["compile_failure_histogram"].get(
        "stereo_edit_unsupported") == 1
    # R1:共底物候选全拒 ⇒ 同样诚实空池(拒因 = 编译前许可,非编译层)
    corpus_rows2 = [
        _rhea_row("rhea:90006", "90005", "RL", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
    ]
    (tmp_path / "b").mkdir()
    engine2 = _CorpusEngine(tmp_path / "b", corpus_rows=corpus_rows2,
                            library_rows=[])
    provider2 = default_pool_provider(None, engine=engine2)
    assert provider2("CCO") == []
    diag2 = provider2.last_diagnostics
    assert diag2["n_corpus_strict_exact"] == 1  # 检索分层仍如实计数
    assert diag2["compile_failure_histogram"].get(
        "corpus_cosubstrate_participants_unsupported") == 1


def test_wv41_eawag_hydrolysis_capability_preserved(tmp_path) -> None:
    """R1 正控:旧 EAWAG 水解能力保持——EAWAG 库记录**单组分 donor**
    (记录本身不声明共底物)经 find_recorded_exact(字节零改动)
    照旧检索+编译(跨组分断裂+新原子,v3 W-V2 能力);R1 收口只关
    corpus component 通道,不动 EAWAG 面。"""
    from pathway_v43.pollutant.recorded_source import find_recorded_exact

    library_rows = [
        {"btid": "btH", "donor_id": "CC(=O)OC",
         "donor_smiles": "CC(=O)OC", "package": "SYNTH",
         "product_sb": "CC(=O)O", "product_smiles": "CC(=O)O",
         "reac_id": "r0001"},
        {"btid": "btH", "donor_id": "CC(=O)OC",
         "donor_smiles": "CC(=O)OC", "package": "SYNTH",
         "product_sb": "CO", "product_smiles": "CO",
         "reac_id": "r0001"},
    ]
    engine = _CorpusEngine(tmp_path, corpus_rows=[],
                           library_rows=library_rows)
    out = find_recorded_exact(
        substrate_smiles="CC(=O)OC", engine=engine)
    cands = out["candidates"]
    assert cands, out["diagnostics"]
    cand = cands[0]
    assert cand["tier"] == "recorded_strict_exact"
    assert cand["compile"] is not None, cand["compile_reason"]
    spec = cand["compile"]
    # 旧水解能力:执行组分 == {乙酸, 甲醇}(跨组分断裂+新原子锚定)
    assert sorted([spec["product_smiles"]] + spec["coproducts"]) == \
        sorted(["CC(=O)O", "CO"])
    assert spec["compile"]["verified_product_set"] is True
    # 池层:EAWAG 通道照旧供给(spec 无 corpus 元数据 = EAWAG 面)
    provider = default_pool_provider(None, engine=engine)
    pool = provider("CC(=O)OC")
    assert [s["key"] for s in pool] == ["rec-btH#r0001"]
    assert all(not s.get("corpus") for s in pool)


# ================================================================ 端到端

def test_wv41_end_to_end_synthetic_batch(tmp_path) -> None:
    """端到端合成批(零真实模型调用;R1 修订为整串供给):builder
    (build_question_batch,corpus 整串接线池)→ run_inputs plan.pools
    → runflow decide(scripted first_pool)→ 公共链执行 → 事件导出
    (sqlite events 参与物:反应物=底物、产物=记录产物;整串语义下
    无共底物参与物,事件与记录声明一致);spec 的 corpus 元数据随
    plan 冻结(内容哈希可审计)。"""
    engine = _CorpusEngine(tmp_path)
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps({
        "qid": "wv41-syn-1", "substrate_smiles": _SUB_WHOLE,
        "products_smiles": ["CCC(=O)O"],
    }) + "\n", encoding="utf-8")
    provider = default_pool_provider(None, engine=engine)
    manifest = build_question_batch(
        questions, tmp_path / "batch", batch_tag="wv41-synth",
        pool_provider=provider, provider_kind="scripted",
        synthetic_review=True)
    assert manifest["n_questions"] == 1
    entry = manifest["entries"][0]
    assert entry["pool_size"] >= 1
    assert "corpus_diagnostics" in entry["pool_diagnostics"]
    run_input = json.loads(
        (tmp_path / "batch" / "run_inputs" / "wv41-syn-1.json"
         ).read_text(encoding="utf-8"))
    specs = run_input["plan"]["pools"][_SUB_WHOLE]
    corpus_specs = [s for s in specs if s.get("corpus")]
    assert corpus_specs, specs
    spec = corpus_specs[0]
    # 整串语义:共底物声明 = 空集(component 带共底物行零供给)
    assert spec["corpus"]["co_substrates"] == []
    # runflow decide(scripted first_pool;零真实网络)+ 公共链执行
    model = ScriptedRealModelAdapter(
        strategy="first_pool", model_id="wv41-model")
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"], smiles=_SUB_WHOLE,
        plan=run_input["plan"], model=model,
        profile_policy=dict(
            _PROFILE, search_limits=dict(
                _PROFILE["search_limits"], max_real_model_requests=4)))
    assert summary["counts"]["events"] >= 1
    import sqlite3

    conn = sqlite3.connect(
        str(tmp_path / "runs" / run_input["run_id"] /
            "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    events = [json.loads(r["payload"]) for r in conn.execute(
        "SELECT payload FROM events")]
    states = {str(r["state_id"]): json.loads(r["payload"]) for r in
              conn.execute("SELECT state_id, payload FROM states")}
    hyps = [json.loads(r["payload"]) for r in conn.execute(
        "SELECT payload FROM hypotheses")]
    conn.close()
    # 事件参与物(原生事件表核,不只断言 metadata):反应物=底物
    # (丙醇),产物=记录产物(丙酸)——无共底物"幽灵原子"参与物
    reactants = set()
    products = set()
    for payload in events:
        for p in (payload.get("participants") or []):
            state = states.get(str(p.get("state_ref") or "")) or {}
            if p.get("side") == "reactant":
                reactants.add(str(state.get("smiles_isomeric") or ""))
            if p.get("side") == "product":
                products.add(str(state.get("smiles_isomeric") or ""))
    assert reactants == {_SUB_WHOLE}, reactants
    assert products == {"CCC(=O)O"}, products
    # 假设层可追溯:transformation_ref = corpus record_key(行唯一键)
    assert any(str(h.get("transformation_ref") or "").startswith(
        "rhea:90001@L") for h in hyps), \
        [h.get("transformation_ref") for h in hyps]
