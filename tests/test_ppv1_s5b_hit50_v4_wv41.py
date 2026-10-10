"""PPV1 S5b HIT50 v4 W-V4.1 —— RHEA 主语料 recorded 直通接线
(S5b-corpus-retrieval-1 / s5b-pool-policy-2;零网络、零金标)。

依据:v4 任务书 §4(用户六决策 ①②③,2026-10-10)+ §3 入口矩阵:
corpus_v1(43,177 行=RHEA 37,100 + enviPath 6,077;18,550 master ×
LR/RL 双行;8,502 通配行;全库无原生映射)接入 recorded 直通供给,
判据/分层/推断映射/产物多重集 gate 全部沿用 recorded_source 现行
实现,不另写第二套。

正负控(任务书 §4.4 十一类,W2 七类全保留 + corpus 特有四类):
- 正控:整串严格(RHEA 同构)编译+公共链执行;组分级+共底物声明
  (酯水解:底物=donor 组分 1,水=共底物,编译按完整净产物集合核);
  RL 方向行按自身书写编译;master 双向两行各自供给(双方向分层引用);
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
    EAWAG 通道身份零变化(单变量归因前提)。"""
    assert CORPUS_RETRIEVAL_VERSION == "s5b-corpus-retrieval-1"
    sem = dict(CORPUS_RETRIEVAL_SEMANTICS)
    assert sem["substrate_retrieval_scope"] == "cn_identity_wide"
    assert sem["donor_side_semantics"] == (
        "component_level_with_co_substrate_declaration")
    assert "no strict promotion" in sem["tier_rule"]
    assert sem["wildcard_policy"] == (
        "row_level_unsupported_wildcard_atom_reject")
    assert "both_direction_rows_retained" in sem[
        "master_direction_policy"]
    assert "native" in sem["mapping_policy"]
    # 池策略升版(corpus 直通供给;EAWAG 面不变)
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-2"
    # EAWAG recorded 源身份零变化(判据单一来源不动摇)
    assert RECORDED_SOURCE_VERSION == "s5b-recorded-source-1"


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


def test_wv41_component_level_co_substrate_declaration(tmp_path) -> None:
    """正控(组分级+共底物声明,决策②):底物=donor 组分 1,水组分
    声明为共底物/条件参与物(不静默丢弃);编译按**完整净产物集合**核
    (执行组分 == 记录全量产物)。"""
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
    assert cand["compile"] is not None, cand["compile_reason"]
    spec = cand["compile"]
    # 完整净产物集合核:主产物(乙酸)+共产物(乙醇)== 记录全量
    executed = sorted([spec["product_smiles"]] + spec["coproducts"])
    assert executed == sorted(["CC(=O)O", "CCO"])
    assert spec["compile"]["verified_product_set"] is True
    # spec 携带共底物声明(随池入 plan.pools,冻结可审计)
    meta = spec["corpus"]
    assert [c["smiles"] for c in meta["co_substrates"]] == ["O"]
    assert "declared_conditional_participants" in \
        meta["co_substrate_semantics"]
    assert meta["master_id"] == "90002"
    assert meta["direction"] == "LR"
    # 公共链执行:净产物集合完整进入事件参与物语义
    execution = execute_atomtool_expansion(
        substrate_smiles=_SUB, tool_inputs={
            "edits": spec["edits"], "donor": spec["donor"],
            "alignment": spec["alignment"],
            "expectation": spec["expectation"]})
    assert execution["diagnostic"]["strict_target_match"] is True


def test_wv41_rl_row_follows_own_writing_both_directions_supply(
        tmp_path) -> None:
    """正控(决策③ 双向保留):master 90005 的 LR(裂解)与 RL(缩合)
    双行均保留为可供给候选——底物命中哪侧的 donor,就按**该行自身
    书写**编译(RL 行 donor 侧=乙醇+乙基,方向声明 RL;方向反冒充
    =按另一侧书写编译,本通道结构性不可能:编译输入即本行 donor)。"""
    engine = _CorpusEngine(tmp_path)
    # 整串底物 → LR 行(裂解)
    out_lr = find_corpus_recorded_exact(
        substrate_smiles="CCOCC", engine=engine)
    lr = [c for c in out_lr["candidates"]
          if c["record_id"] == "rhea:90007"]
    assert lr and lr[0]["tier"] == "recorded_strict_exact"
    assert lr[0]["direction"] == "LR"
    assert lr[0]["compile"] is not None
    assert sorted([lr[0]["compile"]["product_smiles"]]
                  + lr[0]["compile"]["coproducts"]) == \
        sorted(["CCO", "CC"])
    # 组分底物(乙醇)→ RL 行(缩合;按 RL 行自身 donor→products)
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
    assert rl[0]["compile"] is not None, rl[0]["compile_reason"]
    spec = rl[0]["compile"]
    # 按本行书写:乙醇(+共底物乙基声明)→ CCOCC
    assert spec["product_smiles"] == "CCOCC"
    assert spec["coproducts"] == []
    assert spec["corpus"]["direction"] == "RL"
    # 酯水解 master 90002 的 RL 行:底物=酸侧组分,检索面命中但按
    # 自身书写编译(不冒充 LR 侧)——编不过即诚实拒,不换向
    out_acid = find_corpus_recorded_exact(
        substrate_smiles="CC(=O)O", engine=engine)
    acid_rows = {c["record_id"] for c in out_acid["candidates"]}
    assert "rhea:90004" in acid_rows
    for c in out_acid["candidates"]:
        if c["record_id"] == "rhea:90004":
            assert c["direction"] == "RL"
            assert c["matched_component"] == "CC(=O)O"


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
    # 水解记录如实走编译(电荷编辑不支持 ⇒ 诚实拒,非接线缺陷)
    if c["compile"] is None:
        assert c["compile_status"] == "unsupported"
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
    recorded_cn_candidate 不升 strict(分层判据同源,不改)。"""
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
    # 编译层如实拒(立体编辑不支持,不冒充 strict 通过)
    assert cands[0]["compile_status"] == "unsupported"
    assert cands[0]["compile_reason"] == "stereo_edit_unsupported"


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
    """池接线(s5b-pool-policy-2):EAWAG 面(引擎 lookup 序)保持
  零变化在前,corpus 候选按(tier,整串→组分,行号)序追加在后;
  corpus_channel=False ⇒ 纯 EAWAG 面(v3 形态,消融对照)。"""
    library_rows = [
        {"btid": "btX", "donor_id": "CCO", "donor_smiles": "CCO",
         "package": "SYNTH", "product_sb": "CC=O",
         "product_smiles": "CC=O", "reac_id": "r0001"},
    ]
    corpus_rows = [
        # corpus 通道:CCO → CCOCC(RL 缩合行)
        _rhea_row("rhea:90006", "90005", "RL", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
    ]
    engine = _CorpusEngine(tmp_path, corpus_rows=corpus_rows,
                           library_rows=library_rows)
    provider = default_pool_provider(None, engine=engine)
    pool = provider("CCO")
    keys = [s["key"] for s in pool]
    # EAWAG 在前(引擎序),corpus 追加在后;不同净反应各占一槽
    assert keys == ["rec-btX#r0001", "rec-rhea:90006@L1"], keys
    diag = provider.last_diagnostics
    assert diag["pool_policy_version"] == "s5b-pool-policy-2"
    assert diag["n_recorded_strict_exact"] == 1
    assert diag["n_corpus_strict_exact"] == 1
    assert "corpus_diagnostics" in diag
    assert diag["corpus_diagnostics"]["corpus_retrieval_version"] == \
        CORPUS_RETRIEVAL_VERSION
    # corpus spec 携带共底物声明与 corpus 元数据
    corpus_spec = pool[1]
    assert [c["smiles"] for c in corpus_spec["corpus"]
            ["co_substrates"]] == ["CC"]
    # 消融开关:corpus_channel=False ⇒ 纯 EAWAG 面(v3 形态)
    provider_v3 = default_pool_provider(
        None, engine=engine, corpus_channel=False)
    pool_v3 = provider_v3("CCO")
    assert [s["key"] for s in pool_v3] == ["rec-btX#r0001"]
    assert "corpus_diagnostics" not in provider_v3.last_diagnostics


def test_wv41_pool_corpus_all_unsupported_honest_empty(tmp_path) -> None:
    """池诚实边界:corpus 候选全编译失败(通配/电荷等)⇒ 空池 +
  失败直方图如实(检索命中数不冒充供给,更不冒充命中)。"""
    corpus_rows = [
        _rhea_row("rhea:90009", "90008", "LR", "C[C@H](O)Cl",
                  ["C[C@H](O)Cl"], "CC(=O)Cl", ["CC(=O)Cl"]),
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


# ================================================================ 端到端

def test_wv41_end_to_end_synthetic_batch(tmp_path) -> None:
    """端到端合成批(零真实模型调用):builder(build_question_batch,
  corpus 接线池)→ run_inputs plan.pools → runflow decide(scripted
  first_pool)→ 公共链执行 → 事件导出(sqlite events 参与物 = 完整
  净产物集合);共底物声明随 spec 冻结入 plan(内容哈希可审计)。"""
    engine = _CorpusEngine(tmp_path)
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps({
        "qid": "wv41-syn-1", "substrate_smiles": _SUB,
        "products_smiles": ["CC(=O)O", "CCO"],
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
    specs = run_input["plan"]["pools"][_SUB]
    corpus_specs = [s for s in specs if s.get("corpus")]
    assert corpus_specs, specs
    spec = corpus_specs[0]
    assert spec["corpus"]["co_substrates"][0]["smiles"] == "O"
    # runflow decide(scripted first_pool;零真实网络)+ 公共链执行
    model = ScriptedRealModelAdapter(
        strategy="first_pool", model_id="wv41-model")
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"], smiles=_SUB,
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
    # 事件参与物:产物侧 = 完整净产物集合(乙酸 + 乙醇)
    products = set()
    for payload in events:
        for p in (payload.get("participants") or []):
            if p.get("side") == "product":
                state = states.get(str(p.get("state_ref") or "")) or {}
                products.add(str(state.get("smiles_isomeric") or ""))
    assert "CC(=O)O" in products and "CCO" in products, products
    # 假设层可追溯:transformation_ref = corpus record_key(行唯一键)
    assert any(str(h.get("transformation_ref") or "").startswith(
        "rhea:90003@L") for h in hyps), \
        [h.get("transformation_ref") for h in hyps]
