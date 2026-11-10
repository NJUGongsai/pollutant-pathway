"""类比来源适配 — 供体找回、映射质量、对齐与检索卡 v2 字段(任务书 §1)。

真实资产:按稳定 record_id 从 assets/analog/corpus_templates_v1.jsonl 解析
映射模板;歧义产物如实 ambiguous;无映射记录如实 unmapped。分支逻辑用
假 resolver 覆盖;EngineReactionFinder 注入 resolver 后的卡字段有专项。
"""

from __future__ import annotations

from pathway_v43.adapters.asset_manifest import verify_repo_manifest
from pathway_v43.config import resolve_config
from pathway_v43.domain.identity import cn_identity
from pathway_v43.services.analog_source import (
    MAPPING_AMBIGUOUS,
    MAPPING_UNAVAILABLE,
    QUALITY_BIJECTION,
    QUALITY_UNMAPPED,
    AnalogSourceResolver,
    build_card_mapping_fields,
)
from pathway_v43.services.reaction_finder import (
    EngineReactionFinder,
    ReactionContext,
)

from test_finder_real import FakeEngine, _raw  # 复用最小引擎替身
from wf_helpers import CATECHOL

S = cn_identity(CATECHOL)
REAL_RECORD = "env:EAWAG-BBD:bt0001#r0022"  # 辛醇→辛醛(mapped_bijection)


_RESOLVER_CACHE: dict = {}


def _resolver() -> AnalogSourceResolver:
    """进程内复用一个 resolver(构造含 149MB 清单核验;只读资产)。"""
    if "r" not in _RESOLVER_CACHE:
        _RESOLVER_CACHE["r"] = AnalogSourceResolver(resolve_config())
    return _RESOLVER_CACHE["r"]


def test_resolve_template_by_stable_record_id():
    """稳定 ID 找回:映射 lhs/rhs、反应中心、质量、文件与 SHA、行号。"""
    r = _resolver()
    ref = r.resolve_template(REAL_RECORD)
    assert ref is not None
    assert ref.record_id == REAL_RECORD
    assert ref.index == "analog_corpus_templates"
    assert "[CH2:8]" in ref.mapped_lhs and "[CH:8]=[O:9]" in ref.mapped_rhs
    assert ref.center_atoms == [8, 9]
    assert ref.mapping_quality == QUALITY_BIJECTION
    assert ref.reactant_smiles == "CCCCCCCCO"
    assert ref.product_smiles == "CCCCCCCC=O"
    assert ref.asset_file == "analog/corpus_templates_v1.jsonl"
    manifest = verify_repo_manifest(resolve_config().assets_root)
    assert ref.asset_sha256 == manifest["files"][ref.asset_file]
    assert ref.line_no >= 1


def test_resolve_missing_record_returns_none_not_fabricated():
    assert _resolver().resolve_template("env:DOES:NOT#EXIST") is None


def test_alignment_full_then_center_and_refusal():
    r = _resolver()
    ref = r.resolve_template(REAL_RECORD)
    # 全供体(辛醇)非戊醇子结构 → 反应中心(CH2-OH,映射编号 8/9)对齐
    aligned = r.align(ref, "CCCCCO")
    assert aligned.alignment is not None
    assert aligned.alignment["strategy"] == "reaction_center_substructure"
    assert aligned.alignment["alignment"] == {"7": 4, "8": 5}
    # 完全无法对齐(苯)→ alignment None(不假成功)
    assert r.align(r.resolve_template(REAL_RECORD), "c1ccccc1").alignment is None
    # 供体与当前分子相同:不算类比
    same = r.align(r.resolve_template(REAL_RECORD), "CCCCCCCCO")
    assert same.alignment is None


def test_ambiguous_product_reports_all_templates():
    """多条模板产出同一产物 → ambiguous + 逐条 refs(不挑一条冒充唯一)。"""
    fields = build_card_mapping_fields(_resolver(), "CC=O", "CCCCCO")
    assert fields["mapping_status"] == MAPPING_AMBIGUOUS
    assert fields["mapping_reason"].startswith("ambiguous:")
    assert len(fields["donor_refs"]) >= 2
    assert all(d["asset_sha256"] for d in fields["donor_refs"])


def test_traceability_only_records_marked_unmapped_unavailable():
    """corpus_v1 溯源记录(mapping_status=absent)→ unmapped + unavailable。"""
    r = _resolver()
    refs = r.records_producing("CCCCC(=O)[O-]")  # rhea:10001 的产物
    assert refs, "corpus_v1 应有可溯源记录"
    assert all(x.index == "corpus_v1" for x in refs)
    assert all(x.mapping_quality == QUALITY_UNMAPPED for x in refs)
    fields = build_card_mapping_fields(r, "CCCCC(=O)[O-]", "CCCCCO")
    assert fields["mapping_status"] == MAPPING_UNAVAILABLE
    assert fields["mapping_reason"] == "no_mapped_template:traceability_only"


def test_no_donor_record_unavailable_with_reason():
    fields = build_card_mapping_fields(_resolver(), "NOT-A-REAL-PRODUCT-XYZ",
                                       S)
    assert fields["mapping_status"] == MAPPING_UNAVAILABLE
    assert fields["mapping_reason"] == "no_donor_record"
    assert fields["donor_refs"] == []


class _FakeResolver:
    """分支逻辑替身:唯一模板 + 对齐成功。"""

    def __init__(self, refs, alignment=True):
        self._refs = refs
        self._alignment = alignment

    def templates_producing(self, pid):
        return self._refs

    def records_producing(self, pid):
        return []

    def align(self, ref, smi):
        from pathway_v43.services.analog_source import DonorRef

        ref.alignment = ({"strategy": "full_donor_substructure",
                          "n_aligned": 2, "alignment": {"0": 0, "1": 1}}
                         if self._alignment else None)
        return ref


def _donor(record_id="env:T:1"):
    from pathway_v43.services.analog_source import DonorRef

    return DonorRef(
        record_id=record_id, index="analog_corpus_templates",
        asset_file="analog/corpus_templates_v1.jsonl", asset_sha256="a" * 64,
        line_no=2, mapping_quality=QUALITY_BIJECTION,
        reactant_smiles="CCO", product_smiles="CC=O",
        mapped_lhs="[CH3:1][CH2:2][OH:3]", mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3],
    )


def test_resolved_unique_aligned_template():
    fields = build_card_mapping_fields(_FakeResolver([_donor()]), "CC=O",
                                       "CCCCCO")
    assert fields["mapping_status"] == "resolved"
    assert fields["donor_refs"][0]["alignment"]["strategy"]


def test_unaligned_unique_template_is_unavailable_not_resolved():
    fields = build_card_mapping_fields(
        _FakeResolver([_donor()], alignment=False), "CC=O", "c1ccccc1")
    assert fields["mapping_status"] == MAPPING_UNAVAILABLE
    assert fields["mapping_reason"] == "donor_not_aligned"


def test_finder_without_resolver_marks_not_attempted():
    """检索卡 v2:未接 resolver 时如实 unavailable:not_attempted。"""
    pred = [{"product_smiles": "CCO", "source": "retrieval",
             "layer": "prediction", "edge_score": 0.3}]
    finder = EngineReactionFinder(
        FakeEngine(_raw([], pred), _asset_identity(), config=resolve_config()),
        resolve_config(),
    )
    env = finder.find(ReactionContext(
        run_id="r", path_id="p", substrate_smiles=S, substrate_identity=S))
    card = next(e for e in env["evidences"] if e["kind"] == "analog_reaction")
    assert card["mapping_status"] == "unavailable"
    assert card["mapping_reason"] == "not_attempted:no_resolver"
    assert card["donor_refs"] == []
    assert card["atom_mapping"] == "unavailable"  # 原生映射字段不变


def test_finder_with_resolver_stamps_mapping_fields():
    pred = [{"product_smiles": "CC=O", "source": "retrieval",
             "layer": "prediction", "edge_score": 0.3}]
    finder = EngineReactionFinder(
        FakeEngine(_raw([], pred), _asset_identity(), config=resolve_config()),
        resolve_config(), analog_resolver=_resolver(),
    )
    env = finder.find(ReactionContext(
        run_id="r", path_id="p", substrate_smiles=S, substrate_identity=S))
    card = next(e for e in env["evidences"] if e["kind"] == "analog_reaction")
    assert card["mapping_status"] == MAPPING_AMBIGUOUS  # CC=O 多模板
    assert card["donor_refs"]


def _asset_identity():
    from test_finder_real import _asset_identity as ai

    return ai()
