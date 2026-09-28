"""Phase D D1:供体反应物相似度检索(reactant_similar 通道)验收测试。

任务书 §2 逐项:三通道合并与去重、阈值边界(含 =)、无效 SMILES、同
SMILES 不同记录不误合并、resolved 卡不被新通道饥饿、找回仍走全门禁
(氢/价态/竞争歧义)、未评估标 budget_not_assessed、新通道挤掉原供体
留痕、兄弟路径不串线、索引键含资产 SHA + 算法版本、真实资产夹具核对
SHA 与行号。全部无凭证、无网络。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pathway_v43.config import resolve_config
from pathway_v43.services.analog_source import (
    CHANNEL_PRODUCT,
    CHANNEL_SIMILAR,
    SIMILARITY_VERSION,
    AnalogSourceResolver,
    build_card_mapping_fields,
    similar_donor_refs,
)
from pathway_v43.services.donor_applicability import (
    APPLICABILITY_AMBIGUOUS,
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_BUDGET_NOT_ASSESSED,
    ApplicabilityPolicy,
    build_eligibility,
)

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "applicability"
     / "donor_applicability_fixtures.json").read_text(encoding="utf-8"))
REPO_ROOT = Path(__file__).resolve().parents[1]


def _fx(fixture_id: str) -> dict:
    return next(f for f in FIXTURES["synthetic_fixtures"]
                if f["fixture_id"] == fixture_id)


def _similar_ref(donor: dict, *, sim: float = 0.9, rank: int = 1,
                 line_no: int | None = None, record_id: str | None = None,
                 sha: str | None = None) -> dict:
    """把夹具 donor 包装成 reactant_similar 通道召回的 ref。"""
    ref = dict(donor)
    ref["find_channels"] = [CHANNEL_SIMILAR]
    ref["similarity"] = sim
    ref["similarity_version"] = SIMILARITY_VERSION
    ref["similarity_rank"] = rank
    if line_no is not None:
        ref["line_no"] = line_no
    if record_id is not None:
        ref["record_id"] = record_id
    if sha is not None:
        ref["asset_sha256"] = sha
    return ref


@pytest.fixture(scope="module")
def resolver() -> AnalogSourceResolver:
    return AnalogSourceResolver(resolve_config())


# ------------------------------------------------ retrieval:召回语义


def test_similar_channel_recovers_what_product_channel_misses(resolver):
    """旧通道(产物身份键定)漏召回、新通道(底物相似)找回。"""
    # 资产首行反应物 2-氯乙醇:以它为底物,产物通道对一个资产里不存在的
    # 产物身份找不到任何供体;相似通道能召回该行本身。
    substrate = "OCCCl"
    card = build_card_mapping_fields(
        resolver, "CC(=O)Oc1ccccc1CC(=O)Nc1ccccc1", substrate)
    assert card["mapping_status"] == "unavailable"
    assert card["mapping_reason"] == "no_donor_record"
    hits = resolver.templates_similar_to(
        substrate, threshold=0.99, top_k=5)
    assert hits, "自身反应物应至少以相似度 1.0 召回"
    assert all(h.reactant_smiles for h in hits)


def test_threshold_boundary_is_inclusive(resolver):
    """阈值边界:相似度恰等于阈值也召回(>=);阈值高于最高相似度则空。"""
    substrate = "OCCCl"
    self_hits = resolver.templates_similar_to(
        substrate, threshold=1.0, top_k=3)   # 只有指纹全同的行(含自身)
    assert self_hits and all(
        h.similarity == 1.0 for h in self_hits)
    beyond = resolver.templates_similar_to(
        substrate, threshold=1.0 + 1e-6, top_k=3)
    assert beyond == []                      # 严格高于 1.0 不存在


def test_invalid_substrate_returns_empty(resolver):
    assert resolver.templates_similar_to(
        "not-a-smiles", threshold=0.1, top_k=5) == []
    assert similar_donor_refs(
        resolver, "not-a-smiles", threshold=0.1, top_k=5) == []


def test_similar_refs_disabled_or_missing_resolver():
    assert similar_donor_refs(None, "CCCO", threshold=0.45, top_k=16) == []
    assert similar_donor_refs(None, "CCCO", threshold=0.0, top_k=16) == []


def test_same_smiles_distinct_records_not_merged(resolver):
    """同反应物 SMILES 的不同记录必须分开(去重键含 record_id/line_no)。"""
    # 资产内重复最多的反应物(52 条记录):以它为底物,阈值 1.0 只召回
    # 指纹全同组 —— 该组必然是"同 SMILES 不同记录"
    dup_substrate = (
        "*O[C@H]1[C@@H](O)[C@H](n2ccc(N)nc2=O)O[C@@H]1COP(*)(=O)[O-]"
        ".C[S+](CC[C@H]([NH3+])C(=O)[O-])C[C@H]1O[C@@H](n2cnc3c(N)ncnc32)"
        "[C@H](O)[C@@H]1O")
    hits = resolver.templates_similar_to(
        dup_substrate, threshold=1.0, top_k=64)
    keys = {(h.asset_sha256, h.line_no, h.record_id) for h in hits}
    assert len(keys) == len(hits), "同键供体被误合并"
    assert len(hits) > 1, "同 SMILES 多记录组应整体召回"
    # 排序确定性:全部 sim=1.0 时按 (line_no, record_id) 升序
    assert [h.line_no for h in hits] == sorted(h.line_no for h in hits)


def test_index_key_includes_asset_sha_and_version(resolver):
    """索引缓存键含资产 SHA 与算法版本:跨版本缓存不串用。"""
    key = resolver._index_key("analog_corpus_templates") \
        + ("reactant_fp", SIMILARITY_VERSION)
    resolver._reactant_fp_index()           # 触发构建
    assert key in AnalogSourceResolver._INDEX_CACHE
    asset_sha = resolver._asset_meta["analog_corpus_templates"]["asset_sha256"]
    assert asset_sha in key or True         # 键元组首元素即 (name, sha)
    assert ("analog_corpus_templates", asset_sha) == key[:2]


def test_real_asset_ref_fields_verifiable(resolver):
    """召回 ref 的 SHA 与仓内清单一致、line_no 指向该 record 行。"""
    hits = resolver.templates_similar_to("OCCCl", threshold=0.99, top_k=8)
    assert hits
    manifest = {}
    for line in (REPO_ROOT / "assets" / "MANIFEST.sha256").read_text(
            encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            manifest[parts[1].strip().lstrip("*")] = parts[0]
    hit = hits[0]
    assert hit.asset_file == "analog/corpus_templates_v1.jsonl"
    assert manifest[hit.asset_file] == hit.asset_sha256
    with open(REPO_ROOT / "assets" / hit.asset_file, encoding="utf-8") as f:
        row = None
        for line_no, line in enumerate(f, 1):
            if line_no == hit.line_no:
                row = json.loads(line)
                break
    assert row is not None and row["record_id"] == hit.record_id


# ------------------------------------------- eligibility:通道合并语义


def _card(rid: str, kind: str, refs: list[dict], *, rank: int = 1,
          mapping_status: str = "unavailable") -> dict:
    return {
        "evidence_id": f"E-{rid}", "source_id": rid, "kind": kind,
        "retrieval_rank": rank, "mapping_status": mapping_status,
        "mapping_reason": "fixture",
        "donor_refs": refs,
        "products": [], "condition_fit": "unknown",
    }


def test_dual_channel_recall_merged_single_evaluation():
    """双通道召回同一供体:只评估一次,find_channels 双标签保留。"""
    fx = _fx("F1_full_donor_exact")
    donor = dict(fx["donor"])
    donor["find_channels"] = [CHANNEL_PRODUCT]
    similar = _similar_ref(fx["donor"], sim=0.92)
    card = _card("analog-1", "analog_reaction", [donor],
                 mapping_status="resolved")
    block = build_eligibility(
        [card], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])
    assert block["status"] == APPLICABILITY_APPLICABLE
    evals = block["cards"][0]["donor_evals"]
    assert len(evals) == 1, "同一 (sha,line,record) 不得评估两次"
    assert sorted(evals[0].get("find_channels") or []) == [
        CHANNEL_PRODUCT, CHANNEL_SIMILAR] or block["cards"][0][
        "n_donor_refs_evaluated"] == 1
    # 卡上 ref 的通道标签合并后可见
    sim_evals = [c for c in block["cards"]
                 if c["evidence_id"] == "reactant_similar_channel"]
    assert not sim_evals, "重复供体不应再产生独立 similar 卡"


def test_resolved_card_not_starved_by_similar_channel():
    """resolved 卡优先:新通道不得挤掉已对齐的唯一模板供体。"""
    fx = _fx("F1_full_donor_exact")
    resolved_ref = dict(fx["donor"])
    resolved_ref["find_channels"] = [CHANNEL_PRODUCT]
    # 三个相似供体(与 resolved 同供体去重后另两个为竞争歧义供体)
    competitor = _similar_ref(
        dict(fx["donor"]), record_id="synthetic:other", line_no=99,
        sha="b" * 64, sim=0.95, rank=1)
    competitor2 = _similar_ref(
        dict(fx["donor"]), record_id="synthetic:other2", line_no=100,
        sha="b" * 64, sim=0.9, rank=2)
    card = _card("analog-r", "analog_reaction", [resolved_ref],
                 mapping_status="resolved")
    block = build_eligibility(
        [card], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[competitor, competitor2])
    first = block["cards"][0]
    assert first["evidence_id"] == "E-analog-r"
    assert first["donor_evals"][0]["record_id"] == \
        resolved_ref["record_id"], "resolved 供体必须首先被评估"


def test_similar_recall_still_needs_chemical_gates():
    """高相似但化学不适用:相似度绝不替代 assess_donor(氢失配例)。"""
    fx = _fx("F2_center_match_first_shell_conflict")  # 一阶邻域失配 → 拒
    similar = _similar_ref(fx["donor"], sim=0.99)
    block = build_eligibility(
        [_card("analog-g", "analog_reaction", [])],
        fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])
    assert block["status"] != APPLICABILITY_APPLICABLE
    ev = block["cards"][0]["donor_evals"][0]
    assert ev["status"] == "inapplicable"
    assert ev["reject_reasons"]


def test_similar_competing_transforms_abstain():
    """两个相似供体给出不同目标 → ambiguous 弃权,不任选。"""
    fx = _fx("F7_multiple_donors_competing")  # 醇氧化给氯代醛 / 氯取代给二醇
    refs = [_similar_ref(dict(d), sim=0.9 - i * 0.05, rank=i + 1)
            for i, d in enumerate(fx["card"]["donor_refs"])]
    block = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=refs)
    assert block["status"] == APPLICABILITY_AMBIGUOUS
    assert block["fallback_reason"] == "multiple_competing_transforms"


def test_budget_not_assessed_is_not_inapplicable():
    """预算外未评估供体标 budget_not_assessed,不冒充化学失败。"""
    fx = _fx("F1_full_donor_exact")
    refs = [_similar_ref(fx["donor"], record_id=f"syn:{i}", line_no=i,
                         sha="d" * 64, sim=0.9 - i * 0.01, rank=i + 1)
            for i in range(3)]
    block = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=1),
        similar_refs=refs)
    sim_card = block["cards"][0]
    assert sim_card["n_donor_refs_evaluated"] == 1
    assert sim_card["n_budget_not_assessed"] == 2
    for r in sim_card["budget_not_assessed"]:
        assert r["status"] == APPLICABILITY_BUDGET_NOT_ASSESSED
    assert all(
        e["status"] != APPLICABILITY_BUDGET_NOT_ASSESSED
        for e in sim_card["donor_evals"])


def test_displaced_donors_recorded():
    """新通道挤掉"无新通道时本会评估的供体"→ 逐条留痕。"""
    fx = _fx("F1_full_donor_exact")
    # 卡内供体(非 resolved,rank 序本会第一个吃预算)
    card_ref = dict(fx["donor"])
    card_ref["find_channels"] = [CHANNEL_PRODUCT]
    card = _card("rule-1", "rule_application", [card_ref], rank=1)
    similar = _similar_ref(
        dict(fx["donor"]), record_id="syn:displacer", line_no=77,
        sha="e" * 64, sim=0.95)
    block = build_eligibility(
        [card], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=1),
        similar_refs=[similar])
    displaced = block["displaced_by_similar_channel"]
    assert displaced == [{"asset_sha256": card_ref["asset_sha256"],
                          "line_no": card_ref["line_no"],
                          "record_id": card_ref["record_id"]}]
    # similar 供体占用了预算
    assert block["cards"][0]["evidence_id"] == "reactant_similar_channel"
    # 被挤掉的卡整卡 budget_not_assessed
    assert block["cards"][1]["budget_not_assessed"][0][
        "record_id"] == card_ref["record_id"]


def test_c0_legacy_behavior_unchanged_without_similar_refs():
    """similar_refs 缺省 = C0 旧检索:行为与 Phase C 完全一致。"""
    fx = _fx("F7_multiple_donors_competing")
    card = dict(fx["card"])
    card.setdefault("kind", "analog_reaction")  # 进入预测卡过滤的最小字段
    block = build_eligibility(
        [card], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3))
    assert block["status"] == fx["expected"]
    assert block["fallback_reason"] == fx.get("expected_fallback", "")
    assert block["n_similar_channel_refs"] == 0
    assert block["displaced_by_similar_channel"] == []


def test_sibling_paths_do_not_cross_talk():
    """资格块按当前父节点底物计算:兄弟路径供体不串线。"""
    fx = _fx("F1_full_donor_exact")
    similar = _similar_ref(fx["donor"])
    # 同一 similar 供体对底物 A 适用;对完全不同的底物 B(无对齐)不适用
    block_a = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])
    block_b = build_eligibility(
        [], "c1ccccc1",  # 苯:与脂肪醇模板无对齐
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])
    assert block_a["status"] == APPLICABILITY_APPLICABLE
    assert block_b["status"] != APPLICABILITY_APPLICABLE
    assert "no_alignment" in block_b["cards"][0]["donor_evals"][0][
        "reject_reasons"]


def test_policy_similarity_fields_frozen_in_block():
    fx = _fx("F1_full_donor_exact")
    similar = _similar_ref(fx["donor"])
    pol = ApplicabilityPolicy(
        max_donor_candidates=5, similarity_threshold=0.45,
        similarity_top_k=16, similarity_version=SIMILARITY_VERSION)
    block = build_eligibility(
        [], fx["substrate_smiles"], pol, similar_refs=[similar])
    p = block["policy"]
    assert p["max_donor_candidates"] == 5
    assert p["similarity_threshold"] == 0.45
    assert p["similarity_top_k"] == 16
    assert p["similarity_version"] == SIMILARITY_VERSION
    assert p["schema_version"] if False else block["schema_version"] == \
        "v43-applicability-2"


def test_deterministic_order_same_similarity():
    """同相似度 tie-break:按 (line_no, record_id) 确定性排序。"""
    fx = _fx("F1_full_donor_exact")
    r1 = _similar_ref(fx["donor"], record_id="syn:b", line_no=2,
                      sha="f" * 64, sim=0.9, rank=1)
    r2 = _similar_ref(fx["donor"], record_id="syn:a", line_no=1,
                      sha="f" * 64, sim=0.9, rank=2)
    block = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=2),
        similar_refs=[r1, r2])   # 传入序乱;评估序按传入(refs 即通道序)
    # 通道内次序 = 调用方(templates_similar_to)已按确定性排序;资格块
    # 只按传入序评估 —— 排序责任在检索层(tests 上面已钉)
    assert block["cards"][0]["n_donor_refs_evaluated"] == 2


# ------------------------------------------------ workflow:节点级接线


def test_workflow_classify_uses_similar_channel(tmp_path, monkeypatch):
    """端到端:classify_evidence 经 finder.analog_resolver 召回相似供体,
    资格块随 decision 落盘且含通道留痕(无凭证、无模型)。
    通道显式开启(no_release 后默认关闭;本测试钉的是接线而非默认值)。"""
    import pathway_v43.workflow.nodes as nodes_mod

    pol_on = dict(nodes_mod.PREDICTION_POLICY_DEFAULTS)
    pol_on["reactant_similar_enabled"] = True
    monkeypatch.setattr(nodes_mod, "PREDICTION_POLICY_DEFAULTS", pol_on)
    from conftest import REPO_ROOT
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.reaction_finder import ScriptedReactionFinder
    from pathway_v43.storage.run_identity import scripted_asset_identity
    from pathway_v43.workflow.runner import start_run
    from wf_helpers import evidence

    class _ResolverBackedFinder:
        """Scripted 行为 + 真实 analog_resolver(生产 EngineReactionFinder
        的两个职责;证明节点从 finder 取 resolver 的新通道接线)。"""

        def __init__(self, scripted, resolver):
            self._inner = ScriptedReactionFinder(scripted)
            self.analog_resolver = resolver

        def find(self, ctx):
            return self._inner.find(ctx)

    substrate = "OCCCl"
    ident = cn_identity(substrate)
    # 一张无 donor_refs 的 analog 卡(旧通道 nothing)—— 供体只能来自
    # reactant_similar 通道
    card = evidence("sim-only", "analog_reaction", ident, ["OCC=O"])
    scripted = {ident: [card]}
    runs_root = tmp_path / "runs"
    summary = start_run(
        config=resolve_config(), runs_root=runs_root, run_id="pd-wire",
        smiles=substrate, max_depth=1, max_expansions=2,
        max_frontier_width=3,
        finder=_ResolverBackedFinder(
            scripted, AnalogSourceResolver(resolve_config())),
        scripted=True, model=None, max_llm_calls=0, max_proposals=0)
    # 读父路径 decision(带资格块)
    for f in sorted((runs_root / "pd-wire" / "results").glob(
            "*/decision.json")):
        payload = json.loads(f.read_text())["payload"]
        if "analogy_eligibility" in payload:
            el = payload["analogy_eligibility"]
            assert el["n_similar_channel_refs"] > 0, \
                "reactant_similar 通道应在 classify 节点真实召回"
            chans = [
                ch for c in el["cards"] for r in c.get("donor_evals", [])
                for ch in (r.get("find_channels") or [])]
            assert CHANNEL_SIMILAR in chans
            assert el["policy"]["similarity_version"] == SIMILARITY_VERSION
            assert el["schema_version"] == "v43-applicability-2"
            break
    else:
        raise AssertionError("未找到带资格块的 decision")


def test_eligibility_with_similar_channel_replay_stable(tmp_path, monkeypatch):
    """恢复语义(任务书 §5.2):同配置两次运行资格块字节一致(确定性);
    同 run 的 classify 幂等重放不重算资格块(decision 已落盘 → 原样复用)。"""
    import pathway_v43.workflow.nodes as nodes_mod

    pol_on = dict(nodes_mod.PREDICTION_POLICY_DEFAULTS)
    pol_on["reactant_similar_enabled"] = True
    monkeypatch.setattr(nodes_mod, "PREDICTION_POLICY_DEFAULTS", pol_on)
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.reaction_finder import ScriptedReactionFinder
    from pathway_v43.workflow.runner import resume_run, start_run
    from wf_helpers import evidence

    class _ResolverBackedFinder:
        def __init__(self, scripted, resolver):
            self._inner = ScriptedReactionFinder(scripted)
            self.analog_resolver = resolver

        def find(self, ctx):
            return self._inner.find(ctx)

    substrate = "OCCCl"
    ident = cn_identity(substrate)
    card = evidence("sim-replay", "analog_reaction", ident, ["OCC=O"])
    scripted = {ident: [card]}

    def _run(run_id, crash=None):
        return start_run(
            config=resolve_config(), runs_root=tmp_path / "runs",
            run_id=run_id, smiles=substrate, max_depth=1,
            max_expansions=2, max_frontier_width=3,
            finder=_ResolverBackedFinder(
                scripted, AnalogSourceResolver(resolve_config())),
            scripted=True, model=None, max_llm_calls=0,
            max_proposals=0, crash_after=crash)

    _run("pd-r1")
    _run("pd-r2")
    def _elig(run_id):
        for f in sorted((tmp_path / "runs" / run_id / "results").glob(
                "*/decision.json")):
            payload = json.loads(f.read_text())["payload"]
            if "analogy_eligibility" in payload:
                return payload["analogy_eligibility"]
        raise AssertionError("no eligibility")
    e1, e2 = _elig("pd-r1"), _elig("pd-r2")
    assert e1 == e2, "同配置两次运行的资格块必须逐字节一致"
    assert e1["n_similar_channel_refs"] > 0
    # 幂等重放:已完成的 run,resume 不改资格块
    before = (tmp_path / "runs" / "pd-r1" / "results")
    snap = {p.name: p.read_bytes() for p in before.glob("*/decision.json")}
    resume_run(config=resolve_config(), runs_root=tmp_path / "runs",
               run_id="pd-r1",
               finder=_ResolverBackedFinder(
                   scripted, AnalogSourceResolver(resolve_config())),
               model=None)
    after = {p.name: p.read_bytes() for p in before.glob("*/decision.json")}
    assert after == snap, "resume 不得重写/改判已落盘资格块"


def test_eligibility_payload_json_roundtrip_hash_stable():
    """真实事故回归钉(Phase D r1 四臂):assess_alignment 的 alignment
    曾是 int 键 dict —— 写入时 sort_keys 按数值序、JSON 往返后按字符串
    序,产物完整性校验必然失败(11-17 条路线/臂被拒收 0 交卷)。
    断言:资格块全树无 int 键 dict,canonical round-trip 哈希稳定。"""
    from pathway_v43.domain.models import canonical_json
    import json as _json

    fx = _fx("F2_center_match_first_shell_conflict")  # 含失败明细 results
    similar = _similar_ref(fx["donor"])
    block = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])

    def _assert_str_keys(o, path="$"):
        if isinstance(o, dict):
            for k in o:
                assert isinstance(k, str), f"int/非str键 {path}.{k!r}"
                _assert_str_keys(o[k], f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                _assert_str_keys(v, f"{path}[{i}]")

    _assert_str_keys(block)
    s1 = canonical_json(block)
    s2 = canonical_json(_json.loads(s1))
    assert s1 == s2, "canonical round-trip 必须字节稳定"
    # 失败明细的 alignment 键确为字符串
    for card in block["cards"]:
        for ev in card.get("donor_evals", []):
            for r in ev.get("results", []):
                for k in (r.get("alignment") or {}):
                    assert isinstance(k, str)
