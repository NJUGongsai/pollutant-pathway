"""PredictionTask 组装与响应解析(任务书 §2 / 验收 §5.1)。

核心断言:任务书由 PathwayStore + 不可变检索产物确定性组装,含完整祖先链
(每步父/子、事件与证据 ID)、检索产物哈希、预算与兄弟;同一分子经不同
来路到达时任务不串线。解析器对非法证据 ID / 非 JSON / 超量产物显式失败。
"""

from __future__ import annotations

import json

from pathway_v43.domain.identity import cn_identity
from pathway_v43.domain.policy import (
    PREDICTION_MODE_ANALOGY,
    PREDICTION_MODE_NOVEL,
    PREDICTION_MODE_RANK,
    decide_prediction_route,
    prediction_policy,
)
from pathway_v43.services.prediction import (
    build_prediction_task,
    parse_model_response,
)

from wf_helpers import CATECHOL, evidence, rank_response, run_scripted

S = cn_identity(CATECHOL)
P1 = cn_identity("O=CCC=CO")
P2 = cn_identity("CC(O)=O")
Q = cn_identity("O=CCO")
R = cn_identity("OCCO")
X = cn_identity("CCCO")


def rec(rid, reactant, prods, **kw):
    return evidence(rid, "recorded_reaction", reactant, prods, **kw)


def rule(rid, reactant, prods, **kw):
    return evidence(rid, "rule_application", reactant, prods,
                    match_type="rule_template", **kw)


def _read_tasks(runs_root, run_id):
    tasks = []
    base = runs_root / run_id / "results"
    for d in sorted(base.iterdir()):
        p = d / "prediction_task.json"
        if p.is_file():
            tasks.append(json.loads(p.read_text(encoding="utf-8"))["payload"])
    return tasks


def test_task_carries_full_two_step_ancestry_with_evidence(tmp_path):
    """验收 5.1a:两步祖先链(S→S11→S211)逐级入任务书,含每步证据引用。"""
    scripted = {
        S: [rec("btRoot", S, [P1])],                 # 唯一 recorded → 确定性直通
        P1: [rec("btA", P1, [Q]),                    # 竞争 recorded → rank
             rec("btB", P1, ["CC=O"])],
        Q: [rule("btR", Q, [R])],                    # S211 路径(规则 → novel)
    }
    import json as _json

    model = fake_model_stub(rank_responses=[_json.dumps({
        "decision": "select", "evidence_id": "E-btA",
        "order": ["E-btA", "E-btB"],
        "reasons": {"E-btB": "证据较弱"}, "reason": "选 btA"})])
    summary, runs = run_scripted(
        "task1", scripted, max_depth=3, max_expansions=6,
        max_frontier_width=2, runs_root=tmp_path, model=model,
    )
    tasks = _read_tasks(runs, "task1")
    # S11(深度 1)的 rank 任务:祖先链到当前为止(当前步尚无事件)
    s11 = [t for t in tasks if len(t["ancestry"]) == 2
           and t["ancestry"][0]["substrate_identity"] == S]
    assert s11 and s11[0]["mode"] == PREDICTION_MODE_RANK
    t = s11[0]
    assert [s["display_name"] for s in t["ancestry"]] == ["S1", "S11"]
    # 事件挂在**子路径**的入边上:S1 无入边;S11 的入边事件 = E-btRoot
    assert t["ancestry"][0]["event_id"] is None
    assert t["ancestry"][1]["evidence_id"] == "E-btRoot"
    assert t["ancestry"][1]["evidence_kind"] == "recorded_reaction"
    assert t["ancestry"][1]["parent_path_id"] == t["ancestry"][0]["path_id"]
    assert t["retrieval"]["payload_hash"] and t["budget"]["llm_remaining"] >= 0
    # S211(深度 2)的 novel 任务:两步祖先事件 + 当前步
    s211 = [t for t in tasks if len(t["ancestry"]) == 3
            and t["ancestry"][2]["substrate_identity"] == Q]
    assert s211 and s211[0]["mode"] == PREDICTION_MODE_NOVEL
    t3 = s211[0]
    assert [s["display_name"] for s in t3["ancestry"]] == [
        "S1", "S11", "S211"]
    # 每步父/子链接 + 入边事件证据(第 2 步事件由模型选中的 btA 提交)
    assert t3["ancestry"][0]["event_id"] is None
    assert t3["ancestry"][1]["evidence_id"] == "E-btRoot"
    assert t3["ancestry"][2]["evidence_id"] == "E-btA"
    assert t3["ancestry"][2]["parent_path_id"] == t3["ancestry"][1]["path_id"]
    assert t3["discipline"]["model_may_not"]


def test_same_molecule_two_routes_two_tasks_no_cross_talk(tmp_path):
    """验收 5.1b:同一分子经两条来路到达 → 两份任务,祖先链互不串线;
    兄弟路径同样只含自己来路的(任务书 §2,不串线)。"""
    scripted = {
        S: [rec("btRoot", S, [P1, P2])],
        P1: [rec("btA", P1, [Q])],
        P2: [rec("btB", P2, [Q, X])],   # S12 有两条子路径:S221(Q)与 S222(X)
        Q: [rule("btR", Q, [R])],
    }
    model = fake_model_stub(default_novel=True)
    summary, runs = run_scripted(
        "task2", scripted, max_depth=3, max_expansions=5,
        max_frontier_width=2, runs_root=tmp_path, model=model,
    )
    tasks = [t for t in _read_tasks(runs, "task2")
             if t["current"]["identity"] == Q]
    assert len(tasks) == 2, "两条 Q 来路各组装一份任务书"
    ids = {t["task_ref"] for t in tasks}
    assert len(ids) == 2, "task_id 不同(检索哈希/路径参与派生)"
    chains = {"->".join(s["display_name"] for s in t["ancestry"])
              for t in tasks}
    assert chains == {"S1->S11->S211", "S1->S12->S221"}
    # 每份任务只携带自己来路的父路径引用
    for t in tasks:
        parent_ids = {s["path_id"] for s in t["ancestry"]}
        other = [x for x in tasks if x["task_ref"] != t["task_ref"]]
        assert not (parent_ids & {s["path_id"] for s in other[0]["ancestry"]}
                    - {t["ancestry"][0]["path_id"]}), \
            "两条来路的祖先链不得串线"
    # 兄弟路径互不串线:S11 只有 S211 一个子路径 → S211 任务无兄弟
    # (S12 的 S221/S222 不得串入);S12 已有另一条子路径 S222 →
    # S221 任务的兄弟恰含它,不含自身
    s211 = next(t for t in tasks
                if t["ancestry"][1]["substrate_identity"] == P1)
    s221 = next(t for t in tasks
                if t["ancestry"][1]["substrate_identity"] == P2)
    assert s211["siblings"] == []
    sibs = s221["siblings"]
    assert len(sibs) == 1
    sib = sibs[0]
    assert sib["substrate_identity"] == X
    assert sib["display_name"] == "S222"
    assert sib["evidence_id"] == "E-btB"
    assert sib["evidence_kind"] == "recorded_reaction"
    assert sib["event_id"] == s221["ancestry"][2]["event_id"], \
        "兄弟与当前路径同源:同一父事件提交的产物路径"
    assert sib["path_id"] != s221["path_id"], "兄弟不含当前路径自身"
    for t in tasks:
        assert all(s["path_id"] != t["path_id"] for s in t["siblings"])
    assert sib["path_id"] not in {s["path_id"] for s in s211["ancestry"]}
    for t in tasks:
        assert t["mode"] == PREDICTION_MODE_NOVEL


def test_sibling_paths_in_task_from_committed_parent_event(tmp_path):
    """任务书 §2:父路径事件已提交且已有另一条子路径时,后续预测任务的
    siblings 携带那条兄弟(身份/状态/位次/入边事件引用/展示名),不含当前
    路径自身;根路径无兄弟 → 空列表(如实,不硬凑)。"""
    scripted = {
        S: [rec("bt1", S, [P1, P2]), rec("bt2", S, ["O=C=O"])],  # 竞争 → rank
        P1: [rule("btR1", P1, [R])],   # S11:仅规则 → novel(此时 S12 已提交)
        P2: [],
    }
    model = fake_model_stub(rank_responses=[rank_response("E-bt1")],
                            default_novel=True)
    _, runs = run_scripted(
        "sib1", scripted, max_depth=2, max_expansions=2,
        max_frontier_width=2, runs_root=tmp_path, model=model,
    )
    tasks = _read_tasks(runs, "sib1")
    root_task = next(t for t in tasks if t["mode"] == PREDICTION_MODE_RANK)
    assert root_task["siblings"] == [], "根路径无兄弟"
    s11 = next(t for t in tasks if t["current"]["identity"] == P1)
    sibs = s11["siblings"]
    assert len(sibs) == 1
    sib = sibs[0]
    assert sib["substrate_identity"] == P2
    assert sib["display_name"] == "S12"   # S{深度}{位次链} 第一阶段口径
    assert sib["status"] == "frontier"    # 组装时点 S12 已提交、未探索
    assert sib["depth"] == 1
    assert sib["product_position"] == 1   # 原始产物位次,不重排
    assert sib["evidence_id"] == "E-bt1"
    assert sib["evidence_kind"] == "recorded_reaction"
    assert sib["event_id"]
    assert sib["path_id"] != s11["path_id"], "不含当前路径自身"


def test_model_never_sees_display_name_only_identity(tmp_path):
    """任务书 current/ancestry 都带稳定 ID;展示名只是冗余视图。"""
    scripted = {
        S: [rec("btRoot", S, [P1])],
        P1: [rec("btA", P1, ["O=CCO"]), rec("btB", P1, ["CC=O"])],
    }
    model = fake_model_stub(default_novel=True)
    _, runs = run_scripted("task3", scripted, max_depth=2,
                           max_expansions=4, runs_root=tmp_path, model=model)
    tasks = _read_tasks(runs, "task3")
    s11 = [t for t in tasks if len(t["ancestry"]) == 2][0]
    # current = S11 的底物本身(P1);身份是稳定 ID,不是从展示名推的
    assert s11["current"]["identity"] == cn_identity("O=CCC=CO")
    assert s11["ancestry"][1]["substrate_identity"] == cn_identity("O=CCC=CO")
    assert s11["ancestry"][1]["display_name"] == "S11"  # 仅冗余视图
    assert s11["ancestry"][1]["path_id"] not in ("", "S11")


# ------------------------------------------------ 解析器(确定性,零模型)


def test_parse_rank_select_and_invalid_evidence_id():
    task_ids = ["E-a", "E-b"]
    p = parse_model_response(
        PREDICTION_MODE_RANK,
        json.dumps({"decision": "select", "evidence_id": "E-b",
                    "order": ["E-b", "E-a"], "reasons": {"E-a": "慢"},
                    "reason": "选 b"}),
        task_ids,
    )
    assert p.ok and p.selected_evidence_id == "E-b" and p.order == [
        "E-b", "E-a"]
    bad = parse_model_response(
        PREDICTION_MODE_RANK,
        json.dumps({"decision": "select", "evidence_id": "E-NOPE",
                    "reason": "x"}),
        task_ids,
    )
    assert not bad.ok and bad.error_kind == "invalid_evidence_id"


def test_parse_rank_cannot_rewrite_products():
    """rank 协议只允许裁决;响应里出现自造产物字段也不改变选卡语义。"""
    p = parse_model_response(
        PREDICTION_MODE_RANK,
        json.dumps({"decision": "select", "evidence_id": "E-a",
                    "new_product_smiles": "C1=CC=C(C=C1)O", "reason": "x"}),
        ["E-a"],
    )
    assert p.ok and p.selected_evidence_id == "E-a"
    assert not hasattr(p, "products") or not p.products


def test_parse_non_json_and_empty_are_explicit():
    for raw in ("", "这不是 JSON", "{\"decision\":"):
        p = parse_model_response(PREDICTION_MODE_RANK, raw, ["E-a"])
        assert not p.ok
        assert p.error_kind in ("empty_response", "not_json", "bad_shape")


def test_parse_analogy_apply_and_abstain():
    p = parse_model_response(
        PREDICTION_MODE_ANALOGY,
        json.dumps({"decision": "apply", "target_molecode": "graph TB",
                    "edits": [], "reason": "迁移氧化"}),
        None,
    )
    assert p.ok and p.decision == "apply" and p.target_molecode == "graph TB"
    a = parse_model_response(
        PREDICTION_MODE_ANALOGY,
        json.dumps({"decision": "abstain", "reason": "对不上"}),
        None,
    )
    assert a.ok and a.decision == "abstain"
    missing = parse_model_response(
        PREDICTION_MODE_ANALOGY,
        json.dumps({"decision": "apply", "reason": "没有 target"}),
        None,
    )
    assert not missing.ok and missing.error_kind == "bad_shape"


def test_parse_novel_caps_at_five_products():
    products = [{"smiles": "CCO", "note": "n"} for _ in range(6)]
    p = parse_model_response(PREDICTION_MODE_NOVEL, json.dumps(
        {"decision": "propose", "products": products, "reason": "x"}), None)
    assert not p.ok and p.error_kind == "too_many_products"
    ok5 = parse_model_response(PREDICTION_MODE_NOVEL, json.dumps(
        {"decision": "propose", "products": products[:5], "reason": "x"}), None)
    assert ok5.ok and len(ok5.products) == 5


# ------------------------------------------------ 路由纯函数(§5.3 前半)


def _ev(kind, **kw):
    base = evidence("E-x", kind, S, ["CC(O)=O"],
                    match_type=("exact_donor_cn_match" if kind ==
                                "recorded_reaction" else "other"),
                    **kw)
    return base


def test_route_unique_recorded_never_hits_model():
    mode, _ = decide_prediction_route(
        "commit_recorded", [_ev("recorded_reaction")], S,
        prediction_policy(), model_enabled=True, llm_remaining=5,
        proposals_remaining=5)
    assert mode == ""


def test_route_competitive_recorded_to_rank():
    mode, reason = decide_prediction_route(
        "awaiting_prediction",
        [_ev("recorded_reaction"), _ev("recorded_reaction")],
        S, prediction_policy(), model_enabled=True, llm_remaining=5,
        proposals_remaining=5)
    assert mode == PREDICTION_MODE_RANK and "竞争" in reason


def test_route_analog_resolved_vs_unmapped():
    resolved = _ev("analog_reaction")
    resolved["mapping_status"] = "resolved"
    mode, _ = decide_prediction_route(
        "awaiting_prediction", [resolved], S, prediction_policy(),
        model_enabled=True, llm_remaining=5, proposals_remaining=5)
    assert mode == PREDICTION_MODE_ANALOGY
    unmapped = _ev("analog_reaction")
    unmapped["mapping_status"] = "unavailable"
    mode, reason = decide_prediction_route(
        "awaiting_prediction", [unmapped], S, prediction_policy(),
        model_enabled=True, llm_remaining=5, proposals_remaining=5)
    assert mode == PREDICTION_MODE_NOVEL and "mapping" in reason
    pol = prediction_policy({"allow_novel_on_mapping_failure": False})
    mode, reason = decide_prediction_route(
        "awaiting_prediction", [unmapped], S, pol,
        model_enabled=True, llm_remaining=5, proposals_remaining=5)
    assert mode == "" and "hold" in reason


def test_route_no_evidence_and_budget_gates():
    mode, _ = decide_prediction_route(
        "dead_end", [], S, prediction_policy(), model_enabled=True,
        llm_remaining=5, proposals_remaining=5)
    assert mode == PREDICTION_MODE_NOVEL
    mode, reason = decide_prediction_route(
        "dead_end", [], S, prediction_policy(), model_enabled=True,
        llm_remaining=0, proposals_remaining=5)
    assert mode == "" and "llm_budget" in reason
    mode, _ = decide_prediction_route(
        "dead_end", [], S, prediction_policy(), model_enabled=True,
        llm_remaining=5, proposals_remaining=0)
    assert mode == ""
    mode, reason = decide_prediction_route(
        "awaiting_prediction", [_ev("recorded_reaction")], S,
        prediction_policy(), model_enabled=False, llm_remaining=5,
        proposals_remaining=5)
    assert mode == "" and reason == "model_not_configured"


# ------------------------------------------------ 内部工具


def fake_model_stub(default_novel: bool = False,
                    rank_responses: list[str] | None = None):
    """带缺省 novel 响应的假模型(任务组装测试不需要真实响应内容)。"""
    from wf_helpers import fake_model

    default = {}
    if default_novel:
        default[PREDICTION_MODE_NOVEL] = json.dumps({
            "decision": "propose",
            "products": [{"smiles": "OCCO", "note": "氧化"}],
            "uncertainty": "high", "reason": "测试缺省提案",
        })
    return fake_model(script={PREDICTION_MODE_RANK: rank_responses or []},
                      default_by_mode=default)


def test_retrieval_v1_cards_read_compatibly():
    """v43-retrieval-1 旧卡(无 donor 字段)经 v2 代码路径兼容读取:
    mapping 视为 unavailable,不崩、不编造。"""
    from pathway_v43.domain.policy import classify_evidence
    from pathway_v43.validation.gates import validate_event_products

    old_card = {
        "evidence_id": "E-old1", "source_id": "bt1",
        "kind": "recorded_reaction",
        "query_identity": S, "match_type": "exact_donor_cn_match",
        "reactant_smiles": S, "reactant_identity": S,
        "products": [{"position": 0, "product_smiles": P1,
                      "product_smiles_full": P1,
                      "product_identity": P1, "score": 0.5,
                      "score_semantics": "eawag_lookup_tanimoto"}],
        "atom_mapping": "unavailable", "condition_fit": "unknown",
        "retrieval_rank": 1, "score": 0.5,
        "score_semantics": "eawag_lookup_tanimoto",
        "source_record": {"donor_exact_match": True},
        "asset_file": "v3_reactions/library/library_full.jsonl",
        "asset_sha256": "0" * 64,
    }  # 没有 donor_refs / mapping_status / mapping_reason(v1 形状)
    decision = classify_evidence([old_card], "r", "p", S)
    assert decision.outcome == "commit_recorded"
    verdicts = validate_event_products(
        evidence=old_card, ancestry_cns=[S], existing_sibling_cns=set())
    assert verdicts[0].accepted
    assert old_card.get("mapping_status", "unavailable") == "unavailable"


def test_real_provider_without_credentials_structurally_unavailable():
    """无凭证时真实提供者显式不可用(错误信息不含任何密钥值);
    在线调用本机未实测,不以假模型冒充。"""
    import os

    from pathway_v43.adapters import llm_client

    saved = {k: os.environ.pop(k) for k in (
        llm_client.LLM_BASE_URL_ENV, llm_client.LLM_API_KEY_ENV,
        llm_client.LLM_MODEL_ENV) if k in os.environ}
    try:
        probe = llm_client.real_provider_env()
        assert probe["api_key_set"] is False
        try:
            llm_client.resolve_model_setup("real")
            raised = None
        except llm_client.ModelNotConfigured as exc:
            raised = exc
        assert raised is not None
        assert "V43_LLM_API_KEY" in str(raised)
        for env_val in saved.values():
            assert env_val not in str(raised)
    finally:
        os.environ.update(saved)


# ------------------------------------------ 真实提供者传输层(异常分类)


def _complete_with_transport_error(monkeypatch, exc):
    """monkeypatch urllib.request.urlopen 抛指定异常(无网络);
    complete 必须返回结构化 LLMResponse(ok=False),不得抛异常。"""
    import urllib.request

    from pathway_v43.adapters.llm_client import OpenAICompatibleClient

    def fake_urlopen(req, timeout=None):
        raise exc

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleClient(
        base_url="https://llm.example/v1", api_key="test-key", model="m",
        timeout_s=5,
    )
    return client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u", idempotency_key="ik")


def test_real_provider_timeout_error_structured(monkeypatch):
    """裸 TimeoutError(socket.timeout 的 3.10+ 别名)→ error_kind=timeout。
    修复前 except 匹配不存在的 urllib.error.TimeoutExpired → AttributeError。"""
    resp = _complete_with_transport_error(monkeypatch, TimeoutError())
    assert resp.ok is False
    assert resp.error_kind == "timeout"


def test_real_provider_urlerror_with_timeout_reason(monkeypatch):
    """URLError(reason=TimeoutError())→ error_kind=timeout。"""
    import urllib.error

    resp = _complete_with_transport_error(
        monkeypatch, urllib.error.URLError(TimeoutError()))
    assert resp.ok is False
    assert resp.error_kind == "timeout"


def test_real_provider_urlerror_transport_error(monkeypatch):
    """URLError(非超时原因,如连接被拒)→ transport_error,消息仅类型名。"""
    import urllib.error

    resp = _complete_with_transport_error(
        monkeypatch, urllib.error.URLError(OSError("conn refused")))
    assert resp.ok is False
    assert resp.error_kind == "transport_error"
    assert resp.error_message == "OSError"


def test_real_provider_http_error_transport_error(monkeypatch):
    """HTTPError(URLError 子类)→ transport_error,消息保留异常类型名。"""
    import urllib.error

    resp = _complete_with_transport_error(
        monkeypatch, urllib.error.HTTPError(
            "https://llm.example/v1/chat/completions", 503, "Service Unavailable",
            {}, None))
    assert resp.ok is False
    assert resp.error_kind == "transport_error"
    assert resp.error_message == "HTTPError"
