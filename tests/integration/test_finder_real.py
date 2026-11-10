"""ReactionFinder — 反应 ID 聚合、证据分级映射、资产身份与真实引擎抽查。

分组/分级用假引擎确定性覆盖;真实引擎 integration 带 slow 标记
(catechol:3 条不同反应 ID 的已记录反应,带本仓资产身份)。
"""

from __future__ import annotations

import pytest

from pathway_v43.adapters.asset_manifest import verify_repo_manifest
from pathway_v43.config import resolve_config
from pathway_v43.domain.identity import cn_identity
from pathway_v43.services.reaction_finder import (
    EngineReactionFinder,
    ReactionContext,
    ScriptedReactionFinder,
)

from wf_helpers import CATECHOL

S = cn_identity(CATECHOL)


class _FakeX:
    """真实资产文件路径(引擎装载后的 TEMPLATES/ENVIPATH_RULES 替身)。"""

    def __init__(self, root):
        self.TEMPLATES = str(root / "v3_reactions/templates/uspto_templates.json")
        self.ENVIPATH_RULES = str(
            root / "v3_reactions/envipath/templates_implicitH.jsonl")


class FakeEngine:
    """expand_raw 输出的最小替身:一条反应双产物 + 规则/检索边。"""

    def __init__(self, raw, asset_identity, config=None):
        self._raw = raw
        self._asset_identity = asset_identity
        if config is not None:
            self._X = _FakeX(config.assets_root)
            self.identity_block = {
                "library_path": str(
                    config.assets_root / "v3_reactions/library/library_full.jsonl"),
                "corpus_v1_path": str(
                    config.assets_root / "v3_reactions/corpus_env/corpus_v1.jsonl"),
            }

    def expand_raw(self, smiles, case_id="case"):
        assert smiles == S
        return self._raw

    def asset_identity(self):
        return self._asset_identity


def _raw(lookup, pred_edges):
    merged = list(lookup) + list(pred_edges)
    return {
        "smiles": CATECHOL, "canonical_smiles": S,
        "lookup": lookup, "pred_edges": pred_edges, "merged_edges": merged,
        "n_pred_candidates": len(pred_edges), "n_lookup": len(lookup),
        "budget_cut": False, "pool_capped": False,
    }


def _asset_identity():
    manifest = verify_repo_manifest(resolve_config().assets_root)
    return {"retrieval_assets": {
        "assets_root": manifest["assets_root"],
        "manifest_sha256": manifest["manifest_sha256"],
        "n_manifest_files": manifest["n_files"],
        "core_files": {"library": {
            "sha256": manifest["files"]["v3_reactions/library/library_full.jsonl"],
        }},
    }}


def test_same_reaction_multiple_products_grouped_one_card():
    """同一反应 ID 的两个产物聚合为一张证据卡;不同反应 ID 是竞争反应。"""
    lookup = [
        {"product_smiles": "O=CCC=CO", "product_smiles_full": "O=CCC=CO",
         "source": "eawag_lookup", "layer": "lookup",
         "eawag_reactions": ["bt0001#r0001"], "donor_exact_match": True,
         "n_evidence": 2, "tanimoto": 0.61, "ion_filtered": False,
         "cofactor_filtered": False, "filtered": False},
        {"product_smiles": "CC(O)=O", "product_smiles_full": "CC(O)=O",
         "source": "eawag_lookup", "layer": "lookup",
         "eawag_reactions": ["bt0001#r0001"], "donor_exact_match": True,
         "n_evidence": 2, "tanimoto": 0.35, "ion_filtered": False,
         "cofactor_filtered": False, "filtered": False},
        {"product_smiles": "O=C=O", "product_smiles_full": "O=C=O",
         "source": "eawag_lookup", "layer": "lookup",
         "eawag_reactions": ["bt0002#r0007"], "donor_exact_match": True,
         "n_evidence": 1, "tanimoto": 0.22, "ion_filtered": False,
         "cofactor_filtered": False, "filtered": False},
    ]
    pred_edges = [
        {"product_smiles": "Oc1ccccc1O>>x", "source": "envipath+retrieval",
         "layer": "prediction", "edge_score": 0.4, "p_envipath": 0.4},
        {"product_smiles": "CCO", "source": "retrieval", "layer": "prediction",
         "edge_score": 0.3, "p_retrieval": 0.3},
    ]
    finder = EngineReactionFinder(
        FakeEngine(_raw(lookup, pred_edges), _asset_identity(),
                   config=resolve_config()),
        resolve_config(),
    )
    envelope = finder.find(ReactionContext(
        run_id="r", path_id="p1", substrate_smiles=S, substrate_identity=S))
    evidences = envelope["evidences"]
    recorded = [e for e in evidences if e["kind"] == "recorded_reaction"]
    assert len(recorded) == 2  # bt0001#r0001 与 bt0002#r0007
    multi = next(e for e in recorded if e["source_id"] == "bt0001#r0001")
    assert [p["position"] for p in multi["products"]] == [0, 1]
    assert multi["match_type"] == "exact_donor_cn_match"
    assert multi["atom_mapping"] == "unavailable"
    assert multi["condition_fit"] == "unknown"
    assert multi["source_record"]["donor_exact_match"] is True
    # 引擎原始顺序:组内按 merged 排名,卡间按首产物排名
    assert multi["retrieval_rank"] == 1
    assert recorded[1]["source_id"] == "bt0002#r0007"
    # 预测块:envipath → 规则;retrieval → 类比;都不是 recorded
    kinds = {e["source_id"]: e["kind"] for e in evidences}
    assert kinds["envipath+retrieval"] == "rule_application"
    assert kinds["retrieval"] == "analog_reaction"

    # ---- P1 修复回归:逐卡溯源与分数出处 ----
    from pathlib import Path

    manifest = verify_repo_manifest(resolve_config().assets_root)
    manifest_files = manifest["files"]
    assets_root = Path(resolve_config().assets_root)
    by_source = {e["source_id"]: e for e in evidences}
    # 每张卡都有资产文件与哈希,且哈希与总清单一致
    for ev in evidences:
        assert ev["asset_file"], ev["source_id"]
        assert ev["asset_sha256"], ev["source_id"]
        assert manifest_files[ev["asset_file"]] == ev["asset_sha256"]
        assert (assets_root / ev["asset_file"]).is_file()
        # 全部参与来源逐一溯源(主来源与 asset_file 一致)
        assert ev["asset_sources"], ev["source_id"]
        assert ev["asset_sources"][0]["asset_file"] == ev["asset_file"]
        for src in ev["asset_sources"]:
            assert manifest_files[src["asset_file"]] == src["asset_sha256"]
    assert by_source["bt0001#r0001"]["asset_file"] == \
        "v3_reactions/library/library_full.jsonl"
    # 组合来源(envipath+retrieval)两个成分各自列出文件与哈希(P2 修复回归)
    combined = by_source["envipath+retrieval"]
    assert [s["role"] for s in combined["asset_sources"]] == \
        ["envipath", "retrieval"]
    assert combined["asset_sources"][0]["asset_file"] == \
        "v3_reactions/envipath/templates_implicitH.jsonl"
    assert combined["asset_sources"][1]["asset_file"] == \
        "v3_reactions/corpus_env/corpus_v1.jsonl"
    # recorded 卡的库名以实际文件为准,与 asset_file 同源(P2 修复回归)
    assert multi["source_record"]["library_file"] == multi["asset_file"]
    assert multi["source_record"]["library_sha256"] == multi["asset_sha256"]
    assert "library" not in multi["source_record"] or \
        multi["source_record"]["library"] != "EAWAG-BBD donor_product.jsonl"
    assert by_source["retrieval"]["asset_file"] == \
        "v3_reactions/corpus_env/corpus_v1.jsonl"
    # score_semantics 声明数字实际出处,不再统一糊成一个字符串
    sems = {e["source_id"]: e["score_semantics"] for e in evidences}
    assert sems["bt0001#r0001"] == "eawag_lookup_tanimoto"
    assert sems["envipath+retrieval"] == "engine_pred_edge_score:edge_score"
    assert sems["retrieval"] == "engine_pred_edge_score:edge_score"
    tanimoto_edge = dict(by_source["retrieval"])
    # 引擎原始 score_semantics 若存在则透传(不覆盖)
    edge2 = {"product_smiles": "CCO", "source": "retrieval",
             "layer": "prediction", "tanimoto": 0.42,
             "score_semantics": "corpus_neighbor_tanimoto"}
    env2 = EngineReactionFinder(
        FakeEngine(_raw([], [edge2]), _asset_identity(),
                   config=resolve_config()),
        resolve_config(),
    ).find(ReactionContext(run_id="r", path_id="p", substrate_smiles=S,
                           substrate_identity=S))
    assert env2["evidences"][0]["score_semantics"] == "corpus_neighbor_tanimoto"
    # 资产身份:清单 SHA 与 library 文件 SHA 逐项记录
    assets = envelope["retrieval_assets"]
    assert assets["manifest_sha256"] == manifest["manifest_sha256"]
    assert assets["source_file"] == "v3_reactions/library/library_full.jsonl"
    assert assets["source_file_sha256"] == \
        manifest["files"]["v3_reactions/library/library_full.jsonl"]


def test_pred_block_source_containing_lookup_not_recorded():
    lookup = []
    pred_edges = [{"product_smiles": "CCO", "source": "eawag_lookup_x",
                   "layer": "prediction", "edge_score": 0.5}]
    finder = EngineReactionFinder(
        FakeEngine(_raw(lookup, pred_edges), _asset_identity(),
                   config=resolve_config()),
        resolve_config(),
    )
    envelope = finder.find(ReactionContext(
        run_id="r", path_id="p", substrate_smiles=S, substrate_identity=S))
    assert envelope["evidences"][0]["kind"] == "rule_application"


def test_scripted_finder_envelope_and_counter(tmp_path):
    from wf_helpers import evidence

    counter = tmp_path / "cnt.txt"
    finder = ScriptedReactionFinder(
        {S: [evidence("bt0#r0", "recorded_reaction", S, ["CC(O)=O"])]},
        counter_path=str(counter),
    )
    ctx = ReactionContext(run_id="r", path_id="p", substrate_smiles=S,
                          substrate_identity=S)
    e1 = finder.find(ctx)
    assert not counter.exists() or counter.read_text() == "1"
    e2 = finder.find(ctx)
    assert counter.read_text() == "2"
    assert e1["evidences"][0]["evidence_id"] == e2["evidences"][0]["evidence_id"]


@pytest.mark.slow
def test_real_engine_catechol_recorded_evidences():
    """真实引擎 integration:catechol 的已记录反应证据与资产身份。"""
    from pathway_v43.adapters.v3_engine import get_engine

    config = resolve_config()
    finder = EngineReactionFinder(get_engine(config), config)
    envelope = finder.find(ReactionContext(
        run_id="real", path_id="real_root", substrate_smiles=CATECHOL,
        substrate_identity=S))
    recorded = [e for e in envelope["evidences"]
                if e["kind"] == "recorded_reaction"]
    assert len(recorded) == 3  # 实测:bt0254#r0601 / bt0008#r0307 / EAWAG-SOIL
    assert all(e["match_type"] == "exact_donor_cn_match" for e in recorded)
    assert all(e["query_identity"] == S for e in recorded)
    assert all(e["products"] for e in recorded)
    assert {e["source_id"] for e in recorded} == {
        "bt0254#r0601", "bt0008#r0307",
        "EAWAG-SOIL:97c2b761-abf3-42fa-b945-b0690722b30b"
        "#aa547ff7-0ef2-4a2c-8af6-4826da76ba1a"}
    assert all(e["atom_mapping"] == "unavailable" for e in envelope["evidences"])
    assert all(e["condition_fit"] == "unknown" for e in envelope["evidences"])
    manifest = verify_repo_manifest(config.assets_root)
    assert envelope["retrieval_assets"]["manifest_sha256"] == \
        manifest["manifest_sha256"]
    # 逐卡溯源:每张卡(含 98 张规则/类比卡)都有资产文件与清单一致哈希
    for ev in envelope["evidences"]:
        assert ev["asset_file"], ev["source_id"]
        assert manifest["files"][ev["asset_file"]] == ev["asset_sha256"]
        # 组合来源逐成分溯源(P2 修复回归)
        assert ev["asset_sources"]
        assert ev["asset_sources"][0]["asset_file"] == ev["asset_file"]
        for src in ev["asset_sources"]:
            assert manifest["files"][src["asset_file"]] == src["asset_sha256"]
    recorded_files = {e["asset_file"] for e in recorded}
    assert recorded_files == {"v3_reactions/library/library_full.jsonl"}
    # recorded 卡库名与实际文件同源(P2 修复回归)
    assert all(e["source_record"]["library_file"] == e["asset_file"]
               for e in recorded)
    # 引擎原始顺序保留:retrieval_rank 1 起始且单调
    ranks = [e["retrieval_rank"] for e in envelope["evidences"]]
    assert ranks == sorted(ranks) and ranks[0] == 1
