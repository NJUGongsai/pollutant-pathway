"""真实资产烟测(带 fake 模型)— 验收 §5.6/§5.7(slow)。

catechol(Oc1ccccc1O)在真实引擎下命中 3 条竞争已记录反应 → rank_candidates
协议;假模型按检索首位裁决,事件确定性入账。逐卡核对 evidence/asset 哈希、
run_identity 的预测/MoleCode 身份块、事件 model_ref。真实提供者(有凭证时)
的手工验证流程见 README;无凭证时如实标注未实测(本文件不冒充在线验证)。
"""

from __future__ import annotations

import json

import pytest

from pathway_v43.config import resolve_config
from pathway_v43.domain.identity import cn_identity
from pathway_v43.domain.policy import PREDICTION_MODE_RANK
from pathway_v43.services.reaction_finder import (
    EngineReactionFinder,
    ReactionContext,
)

from wf_helpers import CATECHOL, fake_model, run_scripted

pytestmark = pytest.mark.slow

S = cn_identity(CATECHOL)


def _real_finder_with_donor_recovery():
    from pathway_v43.adapters.v3_engine import get_engine
    from pathway_v43.services.analog_source import AnalogSourceResolver

    config = resolve_config()
    engine = get_engine(config)
    resolver = AnalogSourceResolver(config)
    return EngineReactionFinder(engine, config, analog_resolver=resolver)


class _TopRecordedFake:
    """策略假模型:读任务书,在既有 recorded 候选中选检索首位(不虚构)。"""

    provider = "fake"
    model_id = "fake-top-recorded-v1"

    def complete(self, *, mode, system_prompt, user_payload,
                 idempotency_key=None, temperature=0.0):
        from pathway_v43.adapters.llm_client import LLMResponse

        if mode == PREDICTION_MODE_RANK:
            task = json.loads(user_payload)
            recorded = [c for c in task["candidates"]
                        if c["kind"] == "recorded_reaction"]
            top = min(recorded, key=lambda c: c["retrieval_rank"])
            raw = json.dumps({
                "decision": "select",
                "evidence_id": top["evidence_id"],
                "order": [c["evidence_id"] for c in recorded],
                "reasons": {c["evidence_id"]: "逐条裁决留痕"
                            for c in recorded},
                "reason": "选择检索首位已记录反应(测试固定策略)",
            }, ensure_ascii=False)
            return LLMResponse(ok=True, raw_text=raw, usage={"fake": True})
        return LLMResponse(ok=False, error_kind="empty_response")


def _model():
    """fake ModelSetup(替换 client 为策略假模型;身份块仍走标准装配)。"""
    setup = fake_model(script={})
    setup.client = _TopRecordedFake()
    setup.model_id = _TopRecordedFake.model_id
    return setup


def test_real_catechol_rank_candidates_smoke(tmp_path):
    """真实资产 + 假模型:竞争已记录反应 → rank → 选中卡确定性入账。"""
    finder = _real_finder_with_donor_recovery()
    model = _model()
    from pathway_v43.workflow import start_run

    summary = start_run(
        config=resolve_config(), runs_root=tmp_path, run_id="real-pred",
        smiles=CATECHOL, max_depth=1, max_expansions=2,
        max_frontier_width=2, finder=finder, scripted=False, model=model,
    )
    # 3 条竞争 recorded → rank_candidates → 选中卡提交
    assert summary["counts"]["reaction_events"] == 1
    assert summary["budget"]["used_llm_calls"] == 1
    assert summary["stop_reason"] == "completed"

    run_dir = tmp_path / "real-pred"
    # ---- 任务书:候选含 3 条 recorded;模式 rank_candidates ----
    task = json.loads(next(
        (run_dir / "results").glob("*/prediction_task.json")
    ).read_text(encoding="utf-8"))["payload"]
    assert task["mode"] == PREDICTION_MODE_RANK
    kinds = [c["kind"] for c in task["candidates"]]
    assert kinds.count("recorded_reaction") == 3
    assert task["model"]["provider"] == "fake"
    assert task["discipline"]["model_may_not"]

    # ---- 逐卡核对 evidence/asset 哈希(任务书 §5.6) ----
    retrieval = json.loads(next(
        (run_dir / "results").glob("*/retrieval.json")
    ).read_text(encoding="utf-8"))["payload"]
    from pathway_v43.adapters.asset_manifest import verify_repo_manifest

    manifest = verify_repo_manifest(resolve_config().assets_root)
    assert retrieval["schema_version"] == "v43-retrieval-2"
    assert len(retrieval["evidences"]) >= 90  # catechol 全量证据卡
    for ev in retrieval["evidences"]:
        assert ev["asset_file"] and ev["asset_sha256"]
        assert ev["asset_file"] in manifest["files"]
        assert ev["asset_sha256"] == manifest["files"][ev["asset_file"]]
        assert ev["asset_sources"], "逐成分来源必须留痕"
        for src in ev["asset_sources"]:
            assert src["asset_file"] in manifest["files"]
            assert src["asset_sha256"] == manifest["files"][src["asset_file"]]
        assert ev["mapping_status"] in ("resolved", "ambiguous", "unavailable")

    # ---- run_identity:预测/MoleCode 身份块 ----
    identity = json.loads(
        (run_dir / "run_identity.json").read_text(encoding="utf-8"))
    assert identity["prediction"]["enabled"] is True
    assert identity["prediction"]["provider"] == "fake"
    # S1 E1:rank_candidates_v2(ranker_v2.md,协议臂提示词)为常驻第四键,
    # 两版 prompt 的 SHA 恒在身份(装载哪个由 policy 开关决定)
    assert set(identity["prediction"]["prompt_versions"]) == {
        "rank_candidates", "rank_candidates_v2",
        "analogy_edit", "novel_proposal"}
    assert identity["molecode"]["upstream_commit"].startswith("a4df3b04")
    assert identity["strategy"]["max_llm_calls"] >= 1

    # ---- 事件与报告 ----
    report = json.loads(
        (run_dir / "report" / "pathway.json").read_text(encoding="utf-8"))
    ev = report["reaction_events"][0]
    assert ev["kind"] == "recorded_reaction"
    assert ev["model_ref"].startswith("prediction:")
    assert report["summary"]["llm_calls"]["n_calls"] == 1
    assert report["llm_calls"]["n_orphaned_calls"] == 0


def test_real_donor_recovery_attempt_recorded(tmp_path):
    """真实检索卡带 v2 映射字段;找回结果如实(unavailable/ambiguous 为主)。

    引擎预测边不携带 record_id,供体找回走"产物→模板/记录"反查;
    多数产物无法唯一定位供体 —— 如实标注,不编造映射。"""
    finder = _real_finder_with_donor_recovery()
    envelope = finder.find(ReactionContext(
        run_id="precheck2", path_id="precheck2",
        substrate_smiles=S, substrate_identity=S))
    analogs = [e for e in envelope["evidences"]
               if e["kind"] in ("rule_application", "analog_reaction")]
    assert analogs
    statuses = {e["mapping_status"] for e in analogs}
    assert statuses <= {"resolved", "ambiguous", "unavailable"}
    for ev in analogs:
        assert ev["mapping_reason"]
        # resolved 必须带对齐供体;unavailable 不得伪造 alignment
        if ev["mapping_status"] == "resolved":
            aligned = [r for r in ev["donor_refs"] if r.get("alignment")]
            assert aligned
        else:
            assert all(not r.get("alignment") for r in ev["donor_refs"])
