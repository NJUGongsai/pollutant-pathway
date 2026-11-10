"""条件路由 — classify 三分支 + 预测分支 + 主循环的继续/导出。"""

from __future__ import annotations

from .state import WorkflowState


def route_after_classify(state: WorkflowState) -> str:
    """commit_recorded → 确定性校验;有预测模式 → 预测分支;否则原语义。"""
    if state.get("last_outcome", "dead_end") == "commit_recorded":
        return "validate_products"
    if state.get("prediction_mode"):
        return "prepare_prediction"
    if state.get("last_outcome") == "awaiting_prediction":
        return "mark_awaiting_prediction"
    return "mark_dead_end"


def route_after_prepare(state: WorkflowState) -> str:
    """prepare 成功(挂起任务)→ 调用模型;prepare 显式停留 → 主循环。

    R1 修复(pb_0117 事故):prepare 失败(资格供体缺失/表示有损等)经
    ``_hold_or_dead`` 只改 state 字段,旧固定边仍把控制流送进 call_model,
    后者以空/陈旧 task_id 读产物触发裸 ``TypeError`` 使 worker 崩溃。
    成功的显式信号 = phase=="call_model" 且挂起了任务 id。
    """
    if state.get("phase") == "call_model" and state.get("prediction_task_id"):
        return "call_model"
    return "select_frontier"


def route_after_call_model(state: WorkflowState) -> str:
    """预测结果可入校验流(选中/提案)→ apply;显式停留 → 主循环。"""
    if state.get("phase") == "apply_prediction":
        return "apply_prediction"
    return "select_frontier"


def route_after_apply(state: WorkflowState) -> str:
    """选中既有卡 / 提案卡 → validate_products;否则主循环。"""
    if state.get("last_outcome") == "commit_recorded":
        return "validate_products"
    return "select_frontier"


def route_after_validate(state: WorkflowState) -> str:
    """Phase B:validate 之后一律先做候选报告裁决(固定草稿 → 提交或
    no_event 终态),不再直连提交/死端。"""
    return "adjudicate_candidates"


def route_after_adjudicate(state: WorkflowState) -> str:
    """草稿中选中卡有合格产品 → 提交事件;全被拒 → 死端(裁决已 no_event
    终态最终化)。"""
    return "commit_pathway" if state.get("last_outcome") == "commit_recorded" \
        else "mark_dead_end"


def route_after_select(state: WorkflowState) -> str:
    return "retrieve_reactions" if state.get("phase") == "explore" \
        else "export_results"


def route_after_normalize(state: WorkflowState) -> str:
    return "export_results" if state.get("phase") == "failed" \
        else "select_frontier"
