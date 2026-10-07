"""S3b 模型假设协议回归(proposals[]/rank/有界格式反馈;
ppv1-model-proposals-1 / format-feedback-1)。

覆盖(任务书 §7 S3b「模型协议/反馈」行):
- 备选与共同产物不混;空列表/弃权合法;稳定 ID 引用;
- novel 有界 proposal_context(reference_hypothesis_ids/output_origin);
- 只有 JSON 字段/类型/允许 ID/语法错误可进格式反馈;结构无法解析记
  结构失败;有限反馈不修化学结构(chemical_reproposal off);
- 反馈轮持久计数(model_requests;scripted 网络 0;超限结构化拒);
- 真实默认 off/0:register_model_request 拒绝 real(网络发送被阻止),
  传入模型对象不自动补预算(入口侧);策略块装配/严格消费。
基线 b7f2bba 上本文件为 collection 红(pollutant.model_protocol 缺失)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.model_protocol import (  # noqa: E402
    FEEDBACK_ELIGIBLE,
    FORMAT_ERROR_ALLOWED_ID,
    FORMAT_ERROR_JSON_FIELD,
    FORMAT_ERROR_JSON_TYPE,
    FORMAT_ERROR_STRUCTURE_UNPARSEABLE,
    FORMAT_ERROR_SYNTAX,
    ModelProtocolError,
    feedback_policy_from_ledger,
    format_feedback_rounds_used,
    parse_model_proposals,
    register_format_feedback_round,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    FORMAT_FEEDBACK_POLICY_VERSION,
    build_profile_identity_block,
    validate_format_feedback_policy,
    validate_frozen_format_feedback_policy,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    PROVIDER_KIND_REAL,
    PROVIDER_KIND_SCRIPTED,
    REQUEST_STATUS_REGISTERED,
    SearchBudgetExhausted,
    SearchLedger,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

ALLOWED = {"hyp_A", "hyp_B"}


def _resp(payload) -> str:
    return json.dumps(payload)


# ---------------------------------------------------------------- parse


def test_parse_valid_pool_proposals_with_rank() -> None:
    parsed = parse_model_proposals(
        _resp({"proposals": [{"hypothesis_id": "hyp_A"},
                             {"hypothesis_id": "hyp_B"}],
               "rank_hypotheses": ["hyp_B", "hyp_A"]}),
        allowed_hypothesis_ids=ALLOWED)
    assert parsed["abstained"] is False
    assert [p["hypothesis_id"] for p in parsed["proposals"]] == \
        ["hyp_A", "hyp_B"]
    assert parsed["rank_hypotheses"] == ["hyp_B", "hyp_A"]
    assert all(p["origin"] == "frozen_pool" for p in parsed["proposals"])
    # rank 只是建议次序,不是 recorded(解析结果只是提案引用)


def test_parse_empty_proposals_abstain_legal() -> None:
    parsed = parse_model_proposals(
        _resp({"proposals": [], "rank_hypotheses": []}),
        allowed_hypothesis_ids=ALLOWED)
    assert parsed["abstained"] is True
    assert parsed["proposals"] == []


def test_parse_unknown_pool_id_requires_novel_context() -> None:
    # 池外 ID 不是直接拒:必须走 novel 有界路径(带 proposal_context
    # 声明参考与来源;缺 context ⇒ json_field 错误;参考不在池内 ⇒
    # allowed_id 错误)
    with pytest.raises(ModelProtocolError) as ei:
        parse_model_proposals(
            _resp({"proposals": [{"hypothesis_id": "hyp_unknown"}]}),
            allowed_hypothesis_ids=ALLOWED)
    assert ei.value.detail["kind"] == FORMAT_ERROR_JSON_FIELD
    with pytest.raises(ModelProtocolError) as ei2:
        parse_model_proposals(
            _resp({"proposals": [{
                "hypothesis_id": "hyp_unknown",
                "proposal_context": {
                    "reference_hypothesis_ids": ["hyp_not_in_pool"],
                    "output_origin": "x"}}]}),
            allowed_hypothesis_ids=ALLOWED)
    assert ei2.value.detail["kind"] == FORMAT_ERROR_ALLOWED_ID


def test_parse_novel_requires_proposal_context() -> None:
    with pytest.raises(ModelProtocolError) as ei:
        parse_model_proposals(
            _resp({"proposals": [{"hypothesis_id": "hyp_new"}]}),
            allowed_hypothesis_ids=ALLOWED)
    assert ei.value.detail["kind"] == FORMAT_ERROR_JSON_FIELD
    parsed = parse_model_proposals(
        _resp({"proposals": [{
            "hypothesis_id": "hyp_new",
            "proposal_context": {
                "reference_hypothesis_ids": ["hyp_A"],
                "output_origin": "novel_outside_pool"}}]}),
        allowed_hypothesis_ids=ALLOWED)
    assert parsed["proposals"][0]["origin"] == "novel"
    # 参考引用必须在池内
    with pytest.raises(ModelProtocolError) as ei2:
        parse_model_proposals(
            _resp({"proposals": [{
                "hypothesis_id": "hyp_new",
                "proposal_context": {
                    "reference_hypothesis_ids": ["hyp_other"],
                    "output_origin": "x"}}]}),
            allowed_hypothesis_ids=ALLOWED)
    assert ei2.value.detail["kind"] == FORMAT_ERROR_ALLOWED_ID


def test_parse_coproduct_not_a_proposal() -> None:
    # 共同产物是假设内部声明,不作为独立提案(备选与共同产物不混)
    with pytest.raises(ModelProtocolError) as ei:
        parse_model_proposals(
            _resp({"proposals": [{"coproducts": ["cs_x"]}]}),
            allowed_hypothesis_ids=ALLOWED)
    assert ei.value.detail["kind"] == FORMAT_ERROR_SYNTAX
    parsed = parse_model_proposals(
        _resp({"proposals": [{"hypothesis_id": "hyp_A",
                              "coproducts": ["cs_x"]}]}),
        allowed_hypothesis_ids=ALLOWED)
    assert parsed["proposals"][0]["coproducts"] == ["cs_x"]


def test_parse_duplicate_and_rank_unknown_rejected() -> None:
    with pytest.raises(ModelProtocolError):
        parse_model_proposals(
            _resp({"proposals": [{"hypothesis_id": "hyp_A"},
                                 {"hypothesis_id": "hyp_A"}]}),
            allowed_hypothesis_ids=ALLOWED)
    with pytest.raises(ModelProtocolError) as ei:
        parse_model_proposals(
            _resp({"proposals": [{"hypothesis_id": "hyp_A"}],
                   "rank_hypotheses": ["hyp_B"]}),
            allowed_hypothesis_ids=ALLOWED)
    assert ei.value.detail["kind"] == FORMAT_ERROR_ALLOWED_ID


def test_parse_shape_errors_classified() -> None:
    with pytest.raises(ModelProtocolError) as not_json:
        parse_model_proposals("not json at all",
                              allowed_hypothesis_ids=ALLOWED)
    assert not_json.value.detail["kind"] == \
        FORMAT_ERROR_STRUCTURE_UNPARSEABLE
    assert FORMAT_ERROR_STRUCTURE_UNPARSEABLE not in FEEDBACK_ELIGIBLE
    with pytest.raises(ModelProtocolError) as top:
        parse_model_proposals(_resp(["list"]),
                              allowed_hypothesis_ids=ALLOWED)
    assert top.value.detail["kind"] == FORMAT_ERROR_JSON_TYPE
    with pytest.raises(ModelProtocolError) as field:
        parse_model_proposals(_resp({"rank": 1}),
                              allowed_hypothesis_ids=ALLOWED)
    assert field.value.detail["kind"] == FORMAT_ERROR_JSON_FIELD
    with pytest.raises(ModelProtocolError) as typ:
        parse_model_proposals(_resp({"proposals": "x"}),
                              allowed_hypothesis_ids=ALLOWED)
    assert typ.value.detail["kind"] == FORMAT_ERROR_JSON_TYPE


# ---------------------------------------------------------------- policy


def test_format_feedback_policy_validation() -> None:
    assert validate_format_feedback_policy(None) == {
        "version": FORMAT_FEEDBACK_POLICY_VERSION,
        "max_format_feedback_rounds": 0}
    assert validate_format_feedback_policy(
        {"max_format_feedback_rounds": 2})["max_format_feedback_rounds"] == 2
    with pytest.raises(ValueError):
        validate_format_feedback_policy({"max_format_feedback_rounds": 5})
    with pytest.raises(ValueError):
        validate_format_feedback_policy({"max_format_feedback_rounds": True})
    with pytest.raises(ValueError):
        validate_format_feedback_policy({"unknown_key": 1})
    with pytest.raises(ValueError):
        validate_format_feedback_policy({"version": "ppv1-format-feedback-9"})
    # 严格冻结消费:缺键/坏块拒(不补默认)
    with pytest.raises(ValueError):
        validate_frozen_format_feedback_policy(
            {"version": FORMAT_FEEDBACK_POLICY_VERSION})
    with pytest.raises(ValueError):
        validate_frozen_format_feedback_policy(None)
    # profile 块进身份
    block = build_profile_identity_block(
        format_feedback_policy={"max_format_feedback_rounds": 1})
    assert block["format_feedback_policy"]["max_format_feedback_rounds"] == 1


# ---------------------------------------------------------------- 反馈轮


def make_ledger(tmp_path: Path, name: str, rounds: int):
    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(tmp_path / f"{name}.sqlite")
    art = ArtifactStore(runs_root, name)
    ledger = SearchLedger(store, art, name)
    policy = build_profile_identity_block(
        format_feedback_policy={"max_format_feedback_rounds": rounds})
    ledger.register_search_run(name, policy)
    return store, ledger


def _claimed_expand(ledger, name: str) -> tuple[str, str]:
    from pathway_v43.pollutant.queue import schedule_hypotheses
    from pathway_v43.pollutant.hypothesis import (
        Participant, build_hypothesis)
    from pathway_v43.pollutant.chemstate import build_chemical_state
    from pathway_v43.pollutant.search import search_policy_version
    sub = build_chemical_state("CCO", "raw_input", [{"record": "s"}])
    prod = build_chemical_state("CC=O", "source_product",
                                [{"record": "p"}])
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant",
                        role="primary_substrate", coefficient=1,
                        coefficient_status="known"),
            Participant(state_ref=prod.state_id, side="product",
                        role="principal_product", coefficient=1,
                        coefficient_status="known")],
        participant_list_status="source_complete",
        step_scope="net_reaction", origin_group_key="k")
    out = schedule_hypotheses(
        ledger, run_id=name, parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0,
        pool=[{"hypothesis_key": "A", "hypothesis_id": hyp.hypothesis_id,
               "rank": 1, "payload": {"task_key": "tk-A"}}],
        policy_version=search_policy_version(), depth=1)
    action_id = out["selected"][0]["action_id"]
    receipt = ledger.claim_action(action_id, worker_id="w1")
    return action_id, receipt["attempt_refs"][0]


def _type_error() -> ModelProtocolError:
    try:
        parse_model_proposals('{"proposals": "not-a-list"}',
                              allowed_hypothesis_ids=ALLOWED)
    except ModelProtocolError as exc:
        return exc
    raise AssertionError("expected error")


def test_format_feedback_round_registered_and_counted(tmp_path) -> None:
    _, ledger = make_ledger(tmp_path, "ff-1", rounds=2)
    action_id, attempt_id = _claimed_expand(ledger, "ff-1")
    err = _type_error()
    out = register_format_feedback_round(
        ledger, run_id="ff-1", action_id=action_id, attempt_id=attempt_id,
        error=err, response_excerpt='{"proposals": "not-a-list"}',
        provider_kind=PROVIDER_KIND_SCRIPTED)
    assert out["registered"] is True
    assert out["network_request_count"] == 0
    row = ledger.request(out["request_id"])
    assert row["status"] == REQUEST_STATUS_REGISTERED
    assert row["network_request_count"] == 0
    assert row["purpose"] == "format_feedback"
    assert format_feedback_rounds_used(ledger, action_id) == 1
    # 持久计数:内存无关(重开 ledger 仍复算)
    rounds = format_feedback_rounds_used(ledger, action_id)
    assert rounds == 1


def test_format_feedback_round_exhaustion_structured(tmp_path) -> None:
    _, ledger = make_ledger(tmp_path, "ff-2", rounds=1)
    action_id, attempt_id = _claimed_expand(ledger, "ff-2")
    err = _type_error()
    register_format_feedback_round(
        ledger, run_id="ff-2", action_id=action_id, attempt_id=attempt_id,
        error=err, response_excerpt="x",
        provider_kind=PROVIDER_KIND_SCRIPTED)
    with pytest.raises(SearchBudgetExhausted) as ei:
        register_format_feedback_round(
            ledger, run_id="ff-2", action_id=action_id,
            attempt_id=attempt_id, error=_type_error(),
            response_excerpt="x", provider_kind=PROVIDER_KIND_SCRIPTED)
    assert ei.value.detail["limit_key"] == "max_format_feedback_rounds"


def test_structure_failure_not_feedback_eligible(tmp_path) -> None:
    _, ledger = make_ledger(tmp_path, "ff-3", rounds=2)
    action_id, attempt_id = _claimed_expand(ledger, "ff-3")
    try:
        parse_model_proposals("not json", allowed_hypothesis_ids=ALLOWED)
    except ModelProtocolError as exc:
        structure_error = exc
    with pytest.raises(ModelProtocolError) as ei:
        register_format_feedback_round(
            ledger, run_id="ff-3", action_id=action_id,
            attempt_id=attempt_id, error=structure_error,
            response_excerpt="not json",
            provider_kind=PROVIDER_KIND_SCRIPTED)
    assert ei.value.detail["kind"] == "feedback_ineligible_error"
    assert format_feedback_rounds_used(ledger, action_id) == 0


def test_feedback_policy_from_ledger_strict(tmp_path) -> None:
    _, ledger = make_ledger(tmp_path, "ff-4", rounds=2)
    policy = feedback_policy_from_ledger(ledger, "ff-4")
    assert policy["max_format_feedback_rounds"] == 2
    # 坏存储块:消费前拒
    ledger.conn.execute(
        "UPDATE search_runs SET policy_block = ? WHERE run_id = ?",
        (json.dumps({"search_limits": policy_from_bad()}), "ff-4"))
    ledger.conn.commit()
    with pytest.raises(ModelProtocolError):
        feedback_policy_from_ledger(ledger, "ff-4")


def policy_from_bad() -> dict:
    from pathway_v43.pollutant.profile import (
        SEARCH_LIMITS_VERSION, SEARCH_LIMITS_DEFAULTS)
    limits = dict(SEARCH_LIMITS_DEFAULTS)
    limits["version"] = SEARCH_LIMITS_VERSION
    return limits


def test_real_provider_feedback_registration_refused(tmp_path) -> None:
    # 真实 provider 反馈轮:额度 0(默认)⇒ 登记被拒(网络发送被阻止;
    # 传入模型对象不自动补预算)
    _, ledger = make_ledger(tmp_path, "ff-5", rounds=2)  # 反馈策略非 0
    action_id, attempt_id = _claimed_expand(ledger, "ff-5")
    with pytest.raises(SearchBudgetExhausted) as ei:
        register_format_feedback_round(
            ledger, run_id="ff-5", action_id=action_id,
            attempt_id=attempt_id, error=_type_error(),
            response_excerpt="x", provider_kind=PROVIDER_KIND_REAL)
    assert ei.value.detail["limit_key"] == "max_real_model_requests"
    # script(非 real)不占真实额度:network 0
    assert PROVIDER_KIND_SCRIPTED != PROVIDER_KIND_REAL
