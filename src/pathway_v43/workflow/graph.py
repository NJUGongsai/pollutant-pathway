"""StateGraph 构建 — LangGraph 是唯一编排层;节点可能是确定性代码。

流程(任务书 §1.3 + §4 预测分支):

    START → normalize_input → select_frontier → retrieve_reactions
          → classify_evidence
              ├─ 唯一可接受已记录反应 → validate_products ─┐
              ├─ 需要预测且有模型 → prepare_prediction → call_model
              │     ├─ 选中既有卡/提案卡 → apply_prediction → validate_products ─┐
              │     └─ held/弃权/失败 → select_frontier(显式停留,原因入账)
              ├─ 需要预测但无模型 → mark_awaiting_prediction(明确停待预测)
              └─ 无有效证据 → mark_dead_end
          → adjudicate_candidates(Phase B 候选报告裁决:草稿固定)
              ├─ 选中卡有合格产品 → commit_pathway(提交事件 + 最终裁决)
              └─ 全被拒 → mark_dead_end(no_event 终态已最终化)
          → select_frontier(循环,预算与深度受控)
          → export_results → END

模型不能直接修改 State、SQLite 账本或 frontier:模型输出只产生"选中既有卡"
或"提案卡",一律经 validate_products 确定性门禁后由 commit_pathway 入账。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver

from . import nodes, routing
from .nodes import Services
from .state import WorkflowState


def build_graph(services: Services,
                checkpointer: BaseCheckpointSaver | None = None):
    g = StateGraph(WorkflowState)
    g.add_node("normalize_input", nodes.normalize_input(services))
    g.add_node("select_frontier", nodes.select_frontier_node(services))
    g.add_node("retrieve_reactions", nodes.retrieve_reactions(services))
    g.add_node("classify_evidence", nodes.classify_evidence(services))
    g.add_node("prepare_prediction", nodes.prepare_prediction(services))
    g.add_node("call_model", nodes.call_model(services))
    g.add_node("apply_prediction", nodes.apply_prediction(services))
    g.add_node("validate_products", nodes.validate_products_node(services))
    g.add_node("adjudicate_candidates", nodes.adjudicate_candidates(services))
    g.add_node("commit_pathway", nodes.commit_pathway(services))
    g.add_node("mark_awaiting_prediction",
               nodes.mark_awaiting_prediction(services))
    g.add_node("mark_dead_end", nodes.mark_dead_end(services))
    g.add_node("export_results", nodes.export_results(services))

    g.add_edge(START, "normalize_input")
    g.add_conditional_edges(
        "normalize_input", routing.route_after_normalize,
        {"select_frontier": "select_frontier",
         "export_results": "export_results"},
    )
    g.add_conditional_edges(
        "select_frontier", routing.route_after_select,
        {"retrieve_reactions": "retrieve_reactions",
         "export_results": "export_results"},
    )
    g.add_edge("retrieve_reactions", "classify_evidence")
    g.add_conditional_edges(
        "classify_evidence", routing.route_after_classify,
        {"validate_products": "validate_products",
         "prepare_prediction": "prepare_prediction",
         "mark_awaiting_prediction": "mark_awaiting_prediction",
         "mark_dead_end": "mark_dead_end"},
    )
    g.add_edge("prepare_prediction", "call_model")
    g.add_conditional_edges(
        "call_model", routing.route_after_call_model,
        {"apply_prediction": "apply_prediction",
         "select_frontier": "select_frontier"},
    )
    g.add_conditional_edges(
        "apply_prediction", routing.route_after_apply,
        {"validate_products": "validate_products",
         "select_frontier": "select_frontier"},
    )
    g.add_edge("validate_products", "adjudicate_candidates")
    g.add_conditional_edges(
        "adjudicate_candidates", routing.route_after_adjudicate,
        {"commit_pathway": "commit_pathway",
         "mark_dead_end": "mark_dead_end"},
    )
    g.add_edge("commit_pathway", "select_frontier")
    g.add_edge("mark_awaiting_prediction", "select_frontier")
    g.add_edge("mark_dead_end", "select_frontier")
    g.add_edge("export_results", END)

    return g.compile(checkpointer=checkpointer)
