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

# STRATEGY_VERSION 单一事实源在 models.py(v43-policy-4:Phase D D1 的
# reactant_similar 检索通道与相似参数进入策略身份;变更拒绝旧 run resume)。

# ---------------- 预测策略取值(v43-predpol-3;全部可写入 run_identity)----

PREDICTION_POLICY_VERSION = "v43-predpol-3"

PREDICTION_POLICY_DEFAULTS: dict = {
    "policy_version": PREDICTION_POLICY_VERSION,
    "max_candidates_for_ranking": 8,   # rank_candidates 任务携带的候选上限
    "max_reportable_products": 5,      # 每步最多报告五个候选(任务书 §0)
    "allow_novel_on_mapping_failure": True,
    "allow_novel_on_no_evidence": True,
    "max_parse_retries": 2,            # 解析失败重试上限(不含首次)
    # --- Phase C:类比资格与消融开关 ---
    "analogy_enabled": True,           # false = 类比路由关闭(recorded/rank 不受影响;消融用)
    "max_analogy_donor_candidates": 3,  # 每父节点最多核查的候选供体数(冻结进策略身份)
    "allow_noop_edit": False,          # 空 edits 仅当目标图==当前图且此处允许才成立
    # --- Phase D D1:供体反应物相似度检索(reactant_similar 通道)---
    # 参数卡 docs/PHASE_D_D1_PARAM_CARD.md;threshold<=0 或 top_k<=0 或
    # enabled=false = C0 旧检索配置。相似度只决定召回次序,不替代门禁。
    # 默认关闭(Phase D 预注册判定 no_release:真实 dev 20 四臂对照中
    # D-3 配对 @1 净赢 -2 且 @5 下降,保留 C0;显式开启须过新对照)。
    "reactant_similar_enabled": False,
    "reactant_similar_threshold": 0.45,   # Tanimoto >= 阈值才召回(含边界)
    "reactant_similar_top_k": 16,         # 检索召回上限(与每父评估预算分开计数)
}


def prediction_policy(overrides: dict | None = None) -> dict:
    """合并预测策略取值(显式覆盖 > 默认);版本随块落 run_identity。"""
    pol = dict(PREDICTION_POLICY_DEFAULTS)
    for k, v in (overrides or {}).items():
        if k in pol:
            pol[k] = v
    return pol


# 类比 fallback 拒因词表(与 services.donor_applicability 对齐;此处仅
# 依赖字符串字面量,避免 domain → services 反向依赖)
_ANALOGY_FALLBACKS = (
    "no_mapping", "mapping_ambiguous", "applicability_failed",
    "applicability_unknown", "multiple_competing_transforms",
)


def decide_prediction_route(
    outcome: str,
    evidences: list[dict],
    substrate_identity: str,
    policy: dict,
    *,
    model_enabled: bool,
    llm_remaining: int = 0,
    proposals_remaining: int = 0,
    eligibility: dict | None = None,
) -> tuple[str, str]:
    """预测协议路由(任务书 §2 三模式;纯函数,确定性)。

    返回 (mode | "", reason)。mode 为空 = 不进模型,按 outcome 走
    mark_awaiting_prediction / mark_dead_end(第一阶段语义)。

    1. commit_recorded → 永不进模型(唯一 recorded 确定性直通);
    2. usable recorded ≥2 → rank_candidates(模型只能在既有候选中裁决);
    3. 存在**通过适用性门禁**的类比证据(eligibility.status=applicable)
       → analogy_edit;``mapping_status=resolved`` 单独出现不再触发
       (Phase C:来源找回 ≠ 迁移资格);
    4. 规则/类比卡但资格不可用/失败/歧义 → 按具体拒因(no_mapping /
       mapping_ambiguous / applicability_failed / applicability_unknown /
       multiple_competing_transforms)走受约束 novel 或显式停留;
    5. ``analogy_enabled=false``(消融开关)→ 类比路由不进入,recorded/
       rank 语义不变;预测性证据按既有 novel 策略与预算处置;
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
        if not policy.get("analogy_enabled", True):
            # 消融开关:类比路由整体关闭;预测性证据按既有 novel 语义处置
            if policy.get("allow_novel_on_mapping_failure") \
                    and proposals_remaining > 0:
                return PREDICTION_MODE_NOVEL, (
                    "analogy_disabled_novel_allowed:类比开关关闭,"
                    "策略允许受约束新提案")
            return "", "analogy_disabled_hold"
        status = (eligibility or {}).get("status", "")
        fallback = (eligibility or {}).get("fallback_reason", "")
        if status == "applicable":
            selected = (eligibility or {}).get("selected") or {}
            return PREDICTION_MODE_ANALOGY, (
                f"applicable_donor:{fallback or 'gated'}:"
                f"{selected.get('record_id', '')}"
                f"@{selected.get('evidence_id', '')}"
            )
        # 未通过资格门禁:按具体拒因 fallback(不统称"无证据")
        if fallback not in _ANALOGY_FALLBACKS:
            # 资格块未评估(纯函数直调):按证据卡上是否带供体引用推断
            # 最诚实的默认拒因 —— 有 refs 而未评估 = 无法判断;无 refs =
            # 根本没有映射来源
            has_refs = any(
                e.get("donor_refs")
                for e in evidences
                if e.get("kind") in (EVIDENCE_KIND_RULE, EVIDENCE_KIND_ANALOG)
            )
            fallback = ("applicability_unknown" if has_refs
                        else "no_mapping")
        if policy.get("allow_novel_on_mapping_failure") \
                and proposals_remaining > 0:
            return PREDICTION_MODE_NOVEL, (
                f"{fallback}:类比供体未通过适用性门禁,"
                "策略允许受约束新提案")
        return "", f"{fallback}_hold"
    if outcome == OUTCOME_DEAD_END and policy.get("allow_novel_on_no_evidence") \
            and proposals_remaining > 0:
        return PREDICTION_MODE_NOVEL, "no_evidence_novel_allowed"
    return "", "no_model_route"


def recorded_eligibility_reasons(evidence: dict,
                                 substrate_identity: str) -> list[str]:
    """recorded 卡的**完整证据资格判据**(逐项拒因;单一事实源)。

    同一判据服务于四处(Phase B R1 修复:消除选中卡资格绕过):
    1. classify_evidence 的可用 recorded 分级(accept 前提);
    2. rank_candidates 任务候选筛选(prediction.py;此前只查 kind+条件,
       不核身份/精确挂牌,模型可选中异底物卡);
    3. 候选裁决的逐卡验证(report_adjudication);
    4. 选中卡复验(不凭模型 evidence_id 升格脏卡)。

    判据:同规范底物(query/reactant identity 双核对)、方向与来源精确
    挂牌(match_type + source_id + donor_exact_match)、条件无冲突。
    条件缺失(unknown)不算冲突 —— 缺数据不猜测;显式 conflict 不可用。
    """
    reasons: list[str] = []
    if evidence.get("kind") != EVIDENCE_KIND_RECORDED:
        return reasons
    if evidence.get("match_type") != "exact_donor_cn_match":
        reasons.append(
            "direction_or_source:recorded 证据缺少精确底物匹配挂牌")
    if not evidence.get("source_id"):
        reasons.append("direction_or_source:缺少来源 ID")
    if evidence.get("query_identity") != substrate_identity:
        reasons.append("substrate_mismatch:query_identity 非当前规范底物")
    if evidence.get("reactant_identity") != substrate_identity:
        reasons.append("direction_mismatch:反应底物与当前分子不一致")
    if evidence.get("condition_fit") == CONDITION_CONFLICT:
        reasons.append("condition_conflict:来源条件与本任务条件冲突")
    record = evidence.get("source_record") or {}
    if record.get("donor_exact_match") is False:
        reasons.append("donor_not_exact:来源非同规范底物精确记录")
    return reasons


def _usable_recorded(evidence: dict, substrate_identity: str) -> bool:
    """已记录反应的接受前提 = kind 为 recorded 且完整资格判据无拒因。

    (recorded_eligibility_reasons 对非 recorded 卡返回空表 = "门禁不适用";
    分级语义要求显式排除非 recorded —— 否则规则/类比卡会被误判 usable。)
    """
    return (evidence.get("kind") == EVIDENCE_KIND_RECORDED
            and not recorded_eligibility_reasons(evidence, substrate_identity))


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
