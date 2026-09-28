"""候选报告裁决(EC298 Phase B)纯函数层验收测试。

- 逐卡验证:recorded 资格门禁逐项拒因;原始规则/类比卡
  not_validated_for_reporting;多产物卡逐项裁决(部分有效不丢有效项);
  缓存身份与原始字符串重算不符显式拒绝;路径内循环拒绝。
- 裁决排序:选中卡优先、模型 order 相对顺序、deterministic_fallback
  后备键;order_missing 只报告选中卡;同 cn 多卡只占一个位次并保留全部
  来源引用;宽度上限留拒因。
- 不变量:expand ⇒ committed ⇒ reportable ⇒ accepted;report_rank 连续
  从 1 编号且 ≤5;draft 无事件块;final 有事件块或显式 no_event;
  篡改载荷结构化失败。
- rank 解析契约:order 未知 ID/重复/selected 不在首位 = 解析失败;
  缺 order 仍接受。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.services.prediction import parse_model_response  # noqa: E402
from pathway_v43.services.report_adjudication import (  # noqa: E402
    REPORT_ADJUDICATION_POLICY_DEFAULTS,
    AdjudicationError,
    adjudicate_parent,
    resolve_adjudication_validation_refs,
    validate_adjudication_payload,
    validate_card_for_reporting,
)

from wf_helpers import evidence  # noqa: E402

S = cn_identity("CCO")            # 乙醇
B1 = "CC=O"                       # 乙醛
B2 = "C=CO"
B3 = "CC(O)C"
P = cn_identity(B1)


def _rec(rid, prods, *, rank=1, condition_fit="unknown", extra=None):
    return evidence(rid, "recorded_reaction", S, prods, rank=rank,
                    condition_fit=condition_fit, extra=extra)


def _rule(rid, prods, *, rank=2):
    return evidence(rid, "rule_application", S, prods, rank=rank,
                    match_type="rule_template",
                    extra={"mapping_status": "unavailable"})


def _retrieval(cards):
    return {"query": {"substrate_identity": S, "canonical_smiles": S},
            "evidences": cards}


def _selected_validation(card, ok_positions=None):
    """validate_products 产物形状的最小夹具(选中卡)。"""
    ok_positions = ok_positions if ok_positions is not None else \
        [p["position"] for p in card["products"]]
    verdicts = []
    for p in card["products"]:
        ok = p["position"] in ok_positions and cn_identity(
            p["product_smiles"]) is not None
        verdicts.append({
            "position": p["position"],
            "product_smiles": p.get("product_smiles_full")
            or p["product_smiles"],
            "product_identity": p["product_identity"],
            "accepted": ok,
            "reasons": [] if ok else ["fixture_rejected"],
        })
    return {
        "evidence_id": card["evidence_id"],
        "gates": {"direction_source": {"ok": True, "reason": ""},
                  "atom_mapping": {"ok": True, "reason": ""}},
        "verdicts": verdicts,
        "n_accepted": sum(1 for v in verdicts if v["accepted"]),
        "n_total": len(verdicts),
    }


def _rank_result(selected, order, task_id="T-x", attempt=1):
    return {"outcome": "selected", "mode": "rank_candidates",
            "selected_evidence_id": selected, "order": list(order),
            "task_id": task_id, "attempt": attempt}


def _task(cands):
    return {"candidates": [{"evidence_id": c} for c in cands]}


def _adj(cards, *, selected_id, selected_val, result=None, task=None,
         stage="draft", event_commit=None, no_event_reason="",
         decision=None, card_validations=None):
    for c in cards:
        if c["evidence_id"] != selected_id and (
                card_validations is None
                or c["evidence_id"] not in card_validations):
            card_validations = dict(card_validations or {})
            card_validations[c["evidence_id"]] = validate_card_for_reporting(
                card=c, substrate_identity=S, ancestry_cns=[S],
                entry_layer="retrieval")
    validation_refs = {selected_id: {
        "task_id": "T-val", "artifact": "validation",
        "payload_sha256": "0" * 64}}
    for eid in (card_validations or {}):
        validation_refs[eid] = {
            "task_id": "T-adj", "artifact": f"cardval.{eid}",
            "payload_sha256": "1" * 64}
    return adjudicate_parent(
        run_id="r", path_id="p-root", substrate_identity=S,
        retrieval_payload=_retrieval(cards),
        decision_payload=decision or {"accepted_evidence_id": None},
        prediction_task=task, prediction_result=result,
        selected_evidence_id=selected_id, selected_card=next(
            c for c in cards if c["evidence_id"] == selected_id),
        selected_validation=selected_val,
        card_validations=card_validations or {},
        validation_refs=validation_refs,
        stage=stage, event_commit=event_commit,
        no_event_reason=no_event_reason)


# ---------------------------------------------------------------- 逐卡验证


def test_recorded_card_gate_reasons_are_specific():
    conflict = _rec("c1", [B1], condition_fit="conflict")
    out = validate_card_for_reporting(card=conflict, substrate_identity=S,
                                      ancestry_cns=[S],
                                      entry_layer="retrieval")
    assert not out["card_eligible"]
    assert any("condition_conflict" in r for r in out["card_reasons"])

    foreign = _rec("c2", [B1], extra={"query_identity": "OTHER",
                                      "reactant_identity": "OTHER"})
    out = validate_card_for_reporting(card=foreign, substrate_identity=S,
                                      ancestry_cns=[S],
                                      entry_layer="retrieval")
    assert any("substrate_mismatch" in r for r in out["card_reasons"])
    assert any("direction_mismatch" in r for r in out["card_reasons"])


def test_raw_rule_card_not_validated_for_reporting():
    out = validate_card_for_reporting(card=_rule("r1", [B1]),
                                      substrate_identity=S,
                                      ancestry_cns=[S],
                                      entry_layer="retrieval")
    assert out["not_validated_for_reporting"]
    assert not out["card_eligible"]
    assert any("not_validated_for_reporting" in r
               for r in out["card_reasons"])


def test_multi_product_card_adjudicated_per_item():
    card = _rec("c3", [B1, "C(C("])
    out = validate_card_for_reporting(card=card, substrate_identity=S,
                                      ancestry_cns=[S],
                                      entry_layer="retrieval")
    verdicts = {v["position"]: v for v in out["verdicts"]}
    assert verdicts[0]["accepted"] and verdicts[0]["identity_match"]
    assert not verdicts[1]["accepted"]
    assert any("unparseable" in r for r in verdicts[1]["reasons"])


def test_cached_identity_mismatch_rejected_and_cycle_rejected():
    card = _rec("c4", [B1])
    card["products"][0]["product_identity"] = "WRONG"
    out = validate_card_for_reporting(card=card, substrate_identity=S,
                                      ancestry_cns=[S],
                                      entry_layer="retrieval")
    v = out["verdicts"][0]
    assert not v["accepted"] and not v["identity_match"]
    assert any("identity_mismatch" in r for r in v["reasons"])

    loop = _rec("c5", ["CCO"])  # 回到当前底物(祖先链含 S)
    out = validate_card_for_reporting(card=loop, substrate_identity=S,
                                      ancestry_cns=[S],
                                      entry_layer="retrieval")
    assert not out["verdicts"][0]["accepted"]
    assert any("in_path_cycle" in r
               for r in out["verdicts"][0]["reasons"])


# ---------------------------------------------------------------- 裁决排序


def test_rank_mode_selected_first_then_model_order():
    """夹具 1:模型选 A,order 含 B;A 占 @1,B 逐卡验证后排在后面。"""
    a = _rec("a", [B1])
    b = _rec("b", [B2], rank=2)
    result = _rank_result("E-a", ["E-a", "E-b"])
    payload = _adj([a, b], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   result=result, task=_task(["E-a", "E-b"]))
    ranked = [(r["evidence_id"], r["position"], r["report_rank"])
              for r in payload["products"] if r["reportable"]]
    assert ranked == [("E-a", 0, 1), ("E-b", 0, 2)]
    assert payload["rank_basis"] == "model_order"
    # 草稿无事件引用;B 可报告但不提交(无 committed_event_ref/expand)
    assert payload["stage"] == "draft"
    assert all(r["committed_event_ref"] is None
               for r in payload["products"])
    assert all(not r["expand_selected"] for r in payload["products"])
    assert payload["n_reportable"] == 2


def test_unique_recorded_fallback_reports_validated_extra_card():
    """唯一 recorded 直通 + 其他逐卡证明可报告的候选:按冻结后备键排后。"""
    a = _rec("a", [B1])
    b = _rec("b", [B2], rank=2)
    payload = _adj([a, b], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   decision={"accepted_evidence_id": "E-a"})
    assert payload["rank_basis"] == "deterministic_fallback"
    ranked = [(r["evidence_id"], r["report_rank"])
              for r in payload["products"] if r["reportable"]]
    assert ranked == [("E-a", 1), ("E-b", 2)]
    b_entry = next(r for r in payload["products"]
                   if r["evidence_id"] == "E-b")
    assert b_entry["committed_event_ref"] is None
    assert not b_entry["expand_selected"]


def test_order_missing_reports_selected_only():
    a = _rec("a", [B1])
    b = _rec("b", [B2], rank=2)
    result = _rank_result("E-a", [])  # 旧形制未给 order
    payload = _adj([a, b], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   result=result, task=_task(["E-a", "E-b"]))
    assert payload["rank_basis"] == "order_missing_selected_only"
    assert [r["evidence_id"] for r in payload["products"]
            if r["reportable"]] == ["E-a"]
    b_entry = next(r for r in payload["products"]
                   if r["evidence_id"] == "E-b")
    assert any("not_in_model_order_not_promoted" in r
               for r in b_entry["reasons"])


def test_same_cn_multi_card_single_rank_keeps_all_sources():
    """相同 cn 的多卡候选只占一个位次;主条目保留全部来源/验证引用。"""
    a = _rec("a", [B1])
    b = _rec("b", [B1], rank=2)  # 同产物同 cn
    result = _rank_result("E-a", ["E-a", "E-b"])
    payload = _adj([a, b], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   result=result, task=_task(["E-a", "E-b"]))
    ranked = [r for r in payload["products"] if r["reportable"]]
    assert len(ranked) == 1
    dup = next(r for r in payload["products"]
               if r["evidence_id"] == "E-b")
    assert dup["dedup_reason"].startswith("duplicate_cn_of:E-a#0")
    assert ranked[0]["same_identity_sources"] == [{
        "evidence_id": "E-b", "position": 0,
        "validation_ref": dup["validation_ref"],
        "cn_identity": dup["cn_identity"]}]


def test_width_cap_reports_five_and_records_reason():
    prods = [f"CC(=O)C{'C' * (i + 1)}" for i in range(7)]
    prods = [s for s in prods if cn_identity(s)]
    a = _rec("a", prods)
    b = _rec("b", [B1], rank=2)
    result = _rank_result("E-a", ["E-a", "E-b"])
    payload = _adj([a, b], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   result=result, task=_task(["E-a", "E-b"]))
    ranked = [r for r in payload["products"] if r["reportable"]]
    assert len(ranked) == 5
    assert [r["report_rank"] for r in ranked] == [1, 2, 3, 4, 5]
    capped = [r for r in payload["products"]
              if r["dedup_reason"].startswith("report_width_cap")]
    assert len(capped) >= 1


def test_final_with_event_commit_and_invariants():
    a = _rec("a", [B1, B2, B3])
    payload = _adj([a], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   decision={"accepted_evidence_id": "E-a"},
                   stage="final",
                   event_commit={"event_id": "ev-1",
                                 "expand_positions": [0],
                                 "deferred_positions": [1, 2]})
    by_pos = {r["position"]: r for r in payload["products"]}
    assert by_pos[0]["committed_event_ref"] == "ev-1"
    assert by_pos[0]["expand_selected"] is True
    assert by_pos[1]["deferred"] is True
    assert by_pos[1]["expand_selected"] is False
    assert by_pos[2]["committed_event_ref"] == "ev-1"
    assert payload["event"] == {"event_id": "ev-1", "no_event": False,
                                "no_event_reason": ""}
    assert payload["n_committed"] == 3 and payload["n_expand_selected"] == 1
    validate_adjudication_payload(payload)


def test_final_no_event_state():
    """选中卡全被拒:no_event 终态 final 化,无已提交引用,缺拒因报错。"""
    a = _rec("a", [B1])
    base = dict(selected_id="E-a",
                selected_val=_selected_validation(a, ok_positions=[]),
                decision={"accepted_evidence_id": "E-a"}, stage="final")
    with pytest.raises(AdjudicationError):
        _adj([a], no_event_reason="", **base)  # 缺拒因
    payload = _adj([a], no_event_reason="selected_card_all_products_rejected",
                   **base)
    assert payload["event"]["no_event"] is True
    assert all(r["committed_event_ref"] is None
               for r in payload["products"])
    validate_adjudication_payload(payload)


def test_selected_card_not_in_scope_is_error():
    a = _rec("a", [B1])
    with pytest.raises(AdjudicationError):
        adjudicate_parent(
            run_id="r", path_id="p-root", substrate_identity=S,
            retrieval_payload=_retrieval([a]),
            decision_payload={"accepted_evidence_id": None},
            prediction_task=None, prediction_result=None,
            selected_evidence_id="E-gone", selected_card=a,
            selected_validation=_selected_validation(a),
            card_validations={}, validation_refs={}, stage="draft")


def test_tampered_payloads_fail_invariants():
    a = _rec("a", [B1, B2])
    payload = _adj([a], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   decision={"accepted_evidence_id": "E-a"},
                   stage="final",
                   event_commit={"event_id": "ev-1",
                                 "expand_positions": [0],
                                 "deferred_positions": [1]})
    no_event_payload = _adj(
        [a], selected_id="E-a",
        selected_val=_selected_validation(a, ok_positions=[]),
        decision={"accepted_evidence_id": "E-a"}, stage="final",
        no_event_reason="selected_card_all_products_rejected")

    def tamper(mut, *, base=None):
        import copy

        p = copy.deepcopy(base or payload)
        mut(p)
        with pytest.raises(AdjudicationError):
            validate_adjudication_payload(p)

    # 位次跳号
    tamper(lambda p: p["products"][0].__setitem__("report_rank", 2))
    # expand 无事件引用
    tamper(lambda p: (
        p["products"][0].__setitem__("committed_event_ref", None)))
    # reportable 但未通过验证
    tamper(lambda p: (
        p["products"][1].__setitem__("reportable", True),
        p["products"][1].__setitem__("report_rank", 2),
        p["products"][1].__setitem__("accepted", False)))
    # draft 含事件块
    tamper(lambda p: p.__setitem__(
        "stage", "draft") or p["products"][0].__setitem__(
            "committed_event_ref", None))
    # 跨父串线
    tamper(lambda p: p["products"][0].__setitem__("path_id", "p-other"))
    # no_event 缺拒因
    tamper(lambda p: p["event"].__setitem__("no_event_reason", ""),
           base=no_event_payload)
    # no_event 终态含已提交引用
    tamper(lambda p: p["products"][0].__setitem__(
        "committed_event_ref", "ev-1"), base=no_event_payload)


def test_policy_versions_travel_with_payload():
    a = _rec("a", [B1])
    payload = _adj([a], selected_id="E-a",
                   selected_val=_selected_validation(a))
    assert payload["policy"]["policy_version"] == \
        REPORT_ADJUDICATION_POLICY_DEFAULTS["policy_version"]
    assert payload["schema_version"] == "v43-report-adjudication-2"


# ---------------------------------------------------------------- rank 解析


def test_rank_parse_rejects_unknown_duplicate_and_unordered():
    ids = ["E-a", "E-b"]
    ok = json.dumps({"decision": "select", "evidence_id": "E-a",
                     "order": ["E-a", "E-b"], "reasons": {}})
    parsed = parse_model_response("rank_candidates", ok, ids)
    assert parsed.ok

    unknown = json.dumps({"decision": "select", "evidence_id": "E-a",
                          "order": ["E-a", "E-zz"], "reasons": {}})
    assert parse_model_response(
        "rank_candidates", unknown, ids).error_kind == "invalid_evidence_id"

    dup = json.dumps({"decision": "select", "evidence_id": "E-a",
                      "order": ["E-a", "E-a"], "reasons": {}})
    assert parse_model_response(
        "rank_candidates", dup, ids).error_kind == "duplicate_order_id"

    not_first = json.dumps({"decision": "select", "evidence_id": "E-b",
                            "order": ["E-a", "E-b"], "reasons": {}})
    assert parse_model_response(
        "rank_candidates", not_first, ids).error_kind == "selected_not_first"

    missing_from_order = json.dumps({
        "decision": "select", "evidence_id": "E-a",
        "order": ["E-b", "E-a"], "reasons": {}})
    p = parse_model_response("rank_candidates", missing_from_order, ids)
    assert p.error_kind == "selected_not_first"

    no_order = json.dumps({"decision": "select", "evidence_id": "E-a",
                           "reasons": {}})
    parsed = parse_model_response("rank_candidates", no_order, ids)
    assert parsed.ok and parsed.order == []


# ------------------------------------------------- R1 修复回归


def test_dirty_selected_card_never_ranked():
    """R1 P1:模型选中的异底物 recorded 卡资格复验失败 → 零占位、带拒因;
    不凭模型 evidence_id 升格。"""
    a = _rec("a", [B1])
    dirty = _rec("dirty", ["CC#N"], rank=3, extra={
        "query_identity": S,          # 挂牌伪装成同底物
        "reactant_identity": "CN",    # 实际反应底物是甲胺
    })
    result = _rank_result("E-dirty", ["E-dirty", "E-a"])
    payload = _adj([a, dirty], selected_id="E-dirty",
                   selected_val=_selected_validation(dirty),
                   result=result, task=_task(["E-dirty", "E-a"]))
    dirty_entry = next(r for r in payload["products"]
                       if r["evidence_id"] == "E-dirty")
    assert not dirty_entry["reportable"]
    assert dirty_entry["report_rank"] is None
    assert any("substrate_mismatch" in r or "direction_mismatch" in r
               for r in dirty_entry["reasons"])
    dirty_card = next(c for c in payload["cards"]
                      if c["evidence_id"] == "E-dirty")
    assert not dirty_card["card_eligible"] and dirty_card["selected"]
    # 模型 order 未含的干净卡也不因脏卡失败而自动补位(order_missing 语义
    # 由 order_missing 测试覆盖;此处 order=[E-dirty, E-a],A 在 order 内
    # 仍可报告 —— 脏卡不连坐)
    ranked = [r["evidence_id"] for r in payload["products"]
              if r["reportable"]]
    assert ranked == ["E-a"]


def test_donor_not_exact_selected_card_rejected():
    dirty = _rec("d2", [B1], extra={"source_record": {
        "donor_exact_match": False, "btid": "x"}})
    result = _rank_result("E-d2", ["E-d2"])
    payload = _adj([dirty], selected_id="E-d2",
                   selected_val=_selected_validation(dirty),
                   result=result, task=_task(["E-d2"]))
    assert not any(r["reportable"] for r in payload["products"])
    entry = payload["products"][0]
    assert any("donor_not_exact" in r for r in entry["reasons"])
    assert payload["cards"][0]["card_eligible"] is False


def test_task_layer_vs_model_order_layer_separated():
    """R1 P2:任务候选与模型排序分层 —— order 省略 B 时,B in_task=true、
    in_model_order=false、不升格并留显式拒因;选中卡 selected=true。"""
    a = _rec("a", [B1])
    b = _rec("b", [B2], rank=2)
    result = _rank_result("E-a", ["E-a"])  # 模型只排序了 A
    payload = _adj([a, b], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   result=result, task=_task(["E-a", "E-b"]))
    cards = {c["evidence_id"]: c for c in payload["cards"]}
    assert cards["E-a"]["in_task"] and cards["E-a"]["selected"] \
        and cards["E-a"]["in_model_order"]
    assert cards["E-b"]["in_task"] and not cards["E-b"]["selected"]
    assert not cards["E-b"]["in_model_order"]
    assert "in_model_selection_set" not in cards["E-b"]  # 旧混写字段已删
    b_entry = next(r for r in payload["products"]
                   if r["evidence_id"] == "E-b")
    assert not b_entry["reportable"]
    assert any("not_in_model_order_not_promoted" in r
               for r in b_entry["reasons"])


def test_validation_refs_required_and_recorded():
    """R1 P1-2:可报告条目必须带完整验证引用;缺失即不变量违反。"""
    a = _rec("a", [B1])
    payload = _adj([a], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   decision={"accepted_evidence_id": "E-a"})
    ranked = [r for r in payload["products"] if r["reportable"]]
    assert ranked[0]["validation_ref"] == {
        "task_id": "T-val", "artifact": "validation",
        "payload_sha256": "0" * 64}
    import copy

    p = copy.deepcopy(payload)
    p["products"][0]["validation_ref"] = {}
    with pytest.raises(AdjudicationError):
        validate_adjudication_payload(p)
    p = copy.deepcopy(payload)
    del p["products"][0]["validation_ref"]["payload_sha256"]
    with pytest.raises(AdjudicationError):
        validate_adjudication_payload(p)
    p = copy.deepcopy(payload)
    p["products"][0]["validation_ref"]["task_id"] = ""
    with pytest.raises(AdjudicationError):
        validate_adjudication_payload(p)


def test_resolver_rejects_missing_mismatched_refs(tmp_path):
    """R1 P1-2 读取端:引用产物缺失/哈希错指/verdict 不一致 → 结构化失败;
    一致引用回查成功。"""
    import json as _json

    from pathlib import Path as _P

    from pathway_v43.domain.models import content_hash
    from pathway_v43.storage.artifact_store import ArtifactStore

    a = _rec("a", [B1])
    payload = _adj([a], selected_id="E-a",
                   selected_val=_selected_validation(a),
                   decision={"accepted_evidence_id": "E-a"})
    # 构造被引用的真实验证产物(与裁决一致的 verdict)
    ref = payload["products"][0]["validation_ref"]
    val_payload = {
        "schema_version": "v43-validation-1",
        "evidence_id": "E-a",
        "verdicts": [{"position": 0, "product_smiles": B1,
                      "product_identity": P, "accepted": True,
                      "reasons": []}],
    }
    artifacts = ArtifactStore(tmp_path, "r")
    # resolver 以运行目录(含 results/)为根;ArtifactStore 以 runs_root 为根
    run_root = tmp_path / "r"
    env = artifacts.write(ref["task_id"], ref["artifact"], val_payload)
    # 引用里的哈希是夹具固定值,替换为真实落盘哈希后重算载荷一致
    payload["products"][0]["validation_ref"] = {
        **ref, "payload_sha256": env["payload_hash"]}
    summary = resolve_adjudication_validation_refs(run_root, payload)
    assert summary["n_reportable_checked"] == 1

    # 哈希错指
    bad = copy.deepcopy(payload) if False else _json.loads(_json.dumps(payload))
    bad["products"][0]["validation_ref"]["payload_sha256"] = "f" * 64
    with pytest.raises(AdjudicationError):
        resolve_adjudication_validation_refs(run_root, bad)

    # verdict 不一致(accepted 翻转)
    val_payload2 = {**val_payload, "verdicts": [
        {**val_payload["verdicts"][0], "accepted": False}]}
    env2 = artifacts.write("T-other", "validation", val_payload2)
    bad2 = _json.loads(_json.dumps(payload))
    bad2["products"][0]["validation_ref"] = {
        "task_id": "T-other", "artifact": "validation",
        "payload_sha256": env2["payload_hash"]}
    with pytest.raises(AdjudicationError):
        resolve_adjudication_validation_refs(run_root, bad2)

    # 产物缺失
    bad3 = _json.loads(_json.dumps(payload))
    bad3["products"][0]["validation_ref"] = {
        "task_id": "T-gone", "artifact": "validation",
        "payload_sha256": "0" * 64}
    with pytest.raises(AdjudicationError):
        resolve_adjudication_validation_refs(run_root, bad3)
