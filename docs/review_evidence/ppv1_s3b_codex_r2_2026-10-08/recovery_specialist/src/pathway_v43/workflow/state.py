"""LangGraph 执行 State — 小而明确,只持稳定引用(ARCHITECTURE §2)。

这不是化学路径图:化学事实在 PathwayStore,证据/裁决/校验/预测全文在
results/<task_id>/ 产物,State 只保存 run/path 标识、任务 ID、预算快照、
阶段与停止原因。节点可能被恢复语义重放,State 字段写入必须幂等。
"""

from __future__ import annotations

from typing import TypedDict


class Budget(TypedDict, total=False):
    max_depth: int
    max_expansions: int
    max_frontier_width: int
    used_expansions: int
    # 预测预算(任务书 §2:LLM/提案剩余额度进任务书;记账取持久事实源)
    max_llm_calls: int
    used_llm_calls: int
    max_proposals: int
    used_proposals: int


class WorkflowState(TypedDict, total=False):
    run_id: str
    root_smiles: str
    root_cn: str
    active_path_id: str
    active_substrate_identity: str
    graph_revision: int
    retrieval_task_id: str
    retrieval_reused: bool          # True = 命中既有产物,未重新检索(幂等证据)
    decision_task_id: str
    validation_task_id: str
    adjudication_task_id: str       # 候选报告裁决产物任务(Phase B;草稿+最终)
    budget: Budget
    phase: str                      # init|explore|classify|select|export|done|failed
    last_outcome: str               # commit_recorded|awaiting_prediction|dead_end
    stop_reason: str
    error: dict
    # ---- 预测分支引用(任务书 §4:State 只加任务/预测/校验产物引用与预算快照)
    prediction_mode: str            # ""|rank_candidates|analogy_edit|novel_proposal
    prediction_task_id: str
    prediction_response_ref: str    # "<task_id>/prediction_response[#attempt]"
    predicted_evidence_id: str      # 模型选中/构造的卡(validate_products 取用)
    prediction_failed: bool
