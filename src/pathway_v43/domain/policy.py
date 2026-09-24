"""证据分级与选择策略 — 可测试的纯函数层(任务书 §1.3 + 预测路由 §2)。

初始策略(v43-policy-1)+ 预测路由(v43-policy-2):
- 只自动接受「单一、同规范底物、方向正确、无已知条件冲突」的 recorded_reaction;
- 多条竞争已记录反应不因引擎分数最高就自动淘汰其余 → rank_candidates(有模型时);
- 仅规则/类比证据 → 按 donor 映射找回状态路由 analogy_edit / novel_proposal / 停留;
- 无有效证据 → 策略允许时 novel_proposal,否则 dead_end;
- **唯一可用 recorded 永不进模型**(确定性直通不变);
- frontier 按创建顺序展开;一个事件只展开前 max_frontier_width 条产物路径,
  其余合法候选标 deferred(不删除、不隐瞒)。
"""

from __future__ import annotations

from .models import (
    CONDITION_CONFLICT,
    Decision,
    EVIDENCE_KIND_ANALOG,
    EVIDENCE_KIND_RECORDED,
    EVIDENCE_KIND_RULE,
    PREDICTION_MODE_ANALOGY,
    PREDICTION_MODE_NOVEL,
    PREDICTION_MODE_RANK,
    STRATEGY_VERSION,
)

OUTCOME_COMMIT_RECORDED = "commit_recorded"
OUTCOME_AWAITING_PREDICTION = "awaiting_prediction"
OUTCOME_DEAD_END = "dead_end"

STRATEGY_VERSION = "v43-policy-2"  # v2:预测路由进入策略(变更拒绝旧 run resume)

# ---------------- 预测策略取值(v43-predpol-1;全部可写入 run_identity)----

PREDICTION_POLICY_VERSION = "v43-predpol-1"

PREDICTION_POLICY_DEFAULTS: dict = {
    "policy_version": PREDICTION_POLICY_VERSION,
    "max_candidates_for_ranking": 8,   # rank_candidates 任务携带的候选上限
    "max_reportable_products": 5,      # 每步最多报告五个候选(任务书 §0)
    "allow_novel_on_mapping_failure": True,
    "allow_novel_on_no_evidence": True,
    "max_parse_retries": 2,            # 解析失败重试上限(不含首次)
}


def prediction_policy(overrides: dict | None = None) -> dict:
    """合并预测策略取值(显式覆盖 > 默认);版本随块落 run_identity。"""
    pol = dict(PREDICTION_POLICY_DEFAULTS)
    for k, v in (overrides or {}).items():
        if k in pol:
            pol[k] = v
    return pol


def decide_prediction_route(
    outcome: str,
    evidences: list[dict],
    substrate_identity: str,
    policy: dict,
    *,
    model_enabled: bool,
    llm_remaining: int = 0,
    proposals_remaining: int = 0,
) -> tuple[str, str]:
    """预测协议路由(任务书 §2 三模式;纯函数,确定性)。

    返回 (mode | "", reason)。mode 为空 = 不进模型,按 outcome 走
    mark_awaiting_prediction / mark_dead_end(第一阶段语义)。

    1. commit_recorded → 永不进模型(唯一 recorded 确定性直通);
    2. usable recorded ≥2 → rank_candidates(模型只能在既有候选中裁决);
    3. 存在 mapping_status=resolved 的规则/类比卡 → analogy_edit;
    4. 规则/类比卡但映射不可用/歧义 → 策略允许则 novel_proposal,否则停留;
    5. 无可用证据(dead_end)→ 策略允许则 novel_proposal,否则 dead_end;
    6. 预算(LLM 调用/提案)耗尽 → 不进模型(停留原状态,不静默烧钱)。
    """
    if outcome == OUTCOME_COMMIT_RECORDED:
        return "", "unique_recorded_deterministic_bypass"
    if not model_enabled:
        return "", "model_not_configured"
    if llm_remaining <= 0:
        return "", "llm_budget_exhausted"
    usable_recorded = [
        e for e in evidences if _usable_recorded(e, substrate_identity)
    ]
    if len(usable_recorded) > 1:
        return PREDICTION_MODE_RANK, (
            f"competitive_recorded_reactions:{len(usable_recorded)} 条可接受"
            "已记录反应竞争,模型裁决适用性/顺序"
        )
    has_predictive = any(
        e.get("kind") in (EVIDENCE_KIND_RULE, EVIDENCE_KIND_ANALOG)
        and e.get("condition_fit") != CONDITION_CONFLICT
        for e in evidences
    )
    if has_predictive:
        aligned = [
            e for e in evidences
            if e.get("mapping_status") == "resolved"
        ]
        if aligned:
            return PREDICTION_MODE_ANALOGY, (
                "aligned_analog_donor:存在已找回映射且对齐当前分子的类比证据"
            )
        if policy.get("allow_novel_on_mapping_failure") \
                and proposals_remaining > 0:
            return PREDICTION_MODE_NOVEL, (
                "mapping_unavailable_novel_allowed:规则/类比映射不可用,"
                "策略允许受约束新提案(拒因留任务书/响应)"
            )
        return "", "mapping_unavailable_hold"
    if outcome == OUTCOME_DEAD_END and policy.get("allow_novel_on_no_evidence") \
            and proposals_remaining > 0:
        return PREDICTION_MODE_NOVEL, "no_evidence_novel_allowed"
    return "", "no_model_route"


def _usable_recorded(evidence: dict, substrate_identity: str) -> bool:
    """已记录反应的接受前提:同一规范底物 + 方向正确 + 条件无冲突。

    方向与底物匹配由来源保证(eawag lookup 为同规范底物精确键命中,
    donor_exact_match);此处再核对证据卡上的身份字段,双保险。
    条件缺失(unknown)不算冲突 —— 缺数据不猜测;显式 conflict 不可用。
    """
    if evidence.get("kind") != EVIDENCE_KIND_RECORDED:
        return False
    if evidence.get("condition_fit") == CONDITION_CONFLICT:
        return False
    if evidence.get("query_identity") != substrate_identity:
        return False
    if evidence.get("reactant_identity") != substrate_identity:
        return False
    record = evidence.get("source_record") or {}
    if record.get("donor_exact_match") is False:
        return False
    return True


def _tier_note(ev: dict, substrate_identity: str) -> tuple[str, str]:
    kind = ev.get("kind")
    if _usable_recorded(ev, substrate_identity):
        return "recorded_usable", "同规范底物且方向正确的已记录反应"
    if kind == EVIDENCE_KIND_RECORDED:
        return "recorded_not_usable", "已记录反应但条件冲突或身份/方向不符;不升格使用"
    return kind or "unknown", "非已记录反应;不自动升格为实测"


def classify_evidence(
    evidences: list[dict],
    run_id: str,
    path_id: str,
    substrate_identity: str,
) -> Decision:
    """证据 → 裁决。全部证据都保留在 considered 里,不删除任何候选。"""
    considered: list[dict] = []
    recorded: list[dict] = []
    rule_or_analog = False
    for ev in sorted(evidences, key=lambda e: e.get("retrieval_rank", 0)):
        tier, note = _tier_note(ev, substrate_identity)
        if tier == "recorded_usable":
            recorded.append(ev)
        elif ev.get("kind") in (EVIDENCE_KIND_RULE, EVIDENCE_KIND_ANALOG):
            rule_or_analog = True
        considered.append(
            {"evidence_id": ev["evidence_id"], "kind": ev.get("kind"),
             "source_id": ev.get("source_id", ""),
             "retrieval_rank": ev.get("retrieval_rank"),
             "tier": tier, "note": note}
        )

    if len(recorded) == 1:
        ev = recorded[0]
        return Decision(
            run_id=run_id, path_id=path_id,
            outcome=OUTCOME_COMMIT_RECORDED,
            accepted_evidence_id=ev["evidence_id"],
            reason="唯一可接受的已记录反应(同规范底物、方向正确、条件无冲突)",
            considered=considered,
        )
    if len(recorded) > 1:
        return Decision(
            run_id=run_id, path_id=path_id,
            outcome=OUTCOME_AWAITING_PREDICTION,
            accepted_evidence_id=None,
            reason=f"competitive_recorded_reactions:{len(recorded)} 条已记录反应竞争,"
                   "不以引擎分数自动淘汰,留待预测裁决",
            considered=considered,
        )
    if rule_or_analog:
        return Decision(
            run_id=run_id, path_id=path_id,
            outcome=OUTCOME_AWAITING_PREDICTION,
            accepted_evidence_id=None,
            reason="only_rule_or_analog:仅有规则/类比证据,属预测而非实测",
            considered=considered,
        )
    if evidences:
        # 只有条件冲突/身份不符的已记录反应:无可用证据,明示拒因
        return Decision(
            run_id=run_id, path_id=path_id,
            outcome=OUTCOME_DEAD_END,
            accepted_evidence_id=None,
            reason="recorded_not_usable:已记录反应存在但条件冲突或底物/方向不符",
            considered=considered,
        )
    return Decision(
        run_id=run_id, path_id=path_id,
        outcome=OUTCOME_DEAD_END,
        accepted_evidence_id=None,
        reason="no_evidence:检索无任何证据",
        considered=considered,
    )


def select_frontier(
    frontier_paths: list[dict],
    used_expansions: int,
    max_expansions: int,
    max_depth: int,
) -> tuple[dict | None, str]:
    """从 frontier 选下一条待探索路径(按 seq 升序,防御性内部排序)。

    返回 (路径或 None, 说明)。深度到限的路径不在此处改状态 —— 由调用方
    标注 depth_limit;本函数只按 (预算, 深度) 跳过并说明。
    """
    if used_expansions >= max_expansions:
        return None, "budget_exhausted"
    for path in sorted(frontier_paths, key=lambda p: p.get("seq", 0)):
        if path["depth"] >= max_depth:
            continue  # 调用方负责标 depth_limit;这里只跳过
        return path, "selected"
    return None, "frontier_empty_or_depth_capped"


def schedule_products(
    product_paths: list[dict], max_frontier_width: int
) -> tuple[list[dict], list[dict]]:
    """一个事件的产物路径 → (继续展开, 暂缓)。保持原始产物顺序。"""
    expandable = product_paths[:max_frontier_width]
    deferred = product_paths[max_frontier_width:]
    return expandable, deferred


def stop_reason(
    *,
    any_awaiting: bool,
    used_expansions: int,
    max_expansions: int,
    frontier_remaining: int,
    llm_budget_exhausted: bool = False,
) -> str:
    """run 级停止原因:LLM 预算耗尽 > awaiting_prediction > budget > completed。

    LLM 预算耗尽优先于 awaiting_prediction:待预测路径因无调用额度而停留
    时,如实报告耗尽而不是"待预测"(两者都会终止 run,含义不同)。
    """
    if any_awaiting and llm_budget_exhausted:
        return "budget_exhausted"
    if any_awaiting:
        return "awaiting_prediction"
    if used_expansions >= max_expansions and frontier_remaining > 0:
        return "budget_exhausted"
    return "completed"
