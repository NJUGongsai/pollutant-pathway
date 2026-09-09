# src/graph.py
# LangGraph StateGraph 编排：M3 MVP + M5 全量双模式
#
# M3 线性流:
#   orchestrator → substrate → reaction → enzyme_pool → enzymecage
#
# M5 完整流 (含条件分支):
#   orchestrator → substrate → reaction ─┬─(OK)──→ enzyme_pool → enzymecage → reranking → microbe → trait → synthesis
#                                         └─(不OK)→ reaction_prediction ─→ enzyme_pool → ...

import logging
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import EnzymeCrewState
from src.nodes.orchestrator_node import orchestrator_node
from src.nodes.substrate_node import substrate_node
from src.nodes.reaction_node import reaction_node
from src.nodes.enzyme_pool_node import enzyme_pool_node
from src.nodes.enzymecage_node import enzymecage_node
# M5 节点
from src.nodes.reaction_prediction_node import reaction_prediction_node
from src.nodes.llm_reranking_node import llm_reranking_node
from src.nodes.microbe_selection_node import microbe_selection_node
from src.nodes.organism_selection_node import organism_selection_node
from src.nodes.trait_filter_node import trait_filter_node
from src.nodes.evidence_synthesis_node import evidence_synthesis_node
from src.nodes.multi_step_bridge_node import multi_step_bridge_node

logger = logging.getLogger(__name__)


# ─── 路由函数 ───────────────────────────────────────────────────────

def should_continue(state: EnzymeCrewState) -> str:
    """通用路由: fail_closed → end"""
    if state.fail_closed or state.error:
        logger.warning(f"[Router] Fail-closed: {state.error}")
        return "end"
    return "continue"


def route_after_reaction(state: EnzymeCrewState) -> str:
    """
    ReactionNode 后路由:
    - fail_closed → end
    - M3: 直接到 enzyme_pool
    - M5: 检查候选反应是否足够，不足则走 prediction fallback
    """
    if state.fail_closed or state.error:
        # M5 模式下 reaction 失败不直接 fail，走 prediction
        if state.pipeline_mode == "m5" and not state.fail_closed:
            return "predict"
        return "end"
    if state.pipeline_mode == "m5" and not state.candidate_reactions:
        return "predict"
    return "pool"


def route_after_enzymecage(state: EnzymeCrewState) -> str:
    """
    EnzymeCAGENode 后路由:
    - M3: 结束
    - M5: 继续到 reranking
    """
    if state.fail_closed or state.error:
        return "end"
    if state.pipeline_mode == "m5":
        return "rerank"
    return "end"


def route_after_reranking(state: EnzymeCrewState) -> str:
    """M5: reranking 后路由"""
    if state.fail_closed or state.error:
        return "end"
    return "microbe"


def route_after_microbe(state: EnzymeCrewState) -> str:
    """M5: microbe(映射+聚合) 后路由 → 选菌层"""
    if state.fail_closed or state.error:
        return "end"
    return "organism_selection"


def route_after_organism_selection(state: EnzymeCrewState) -> str:
    """M5: 选菌层后路由。

    选菌 LLM 为硬依赖：若节点置 fail_closed（LLM 不可用）则显式终止，不静默透传。
    """
    if state.fail_closed or state.error:
        return "end"
    return "trait"


def route_after_trait(state: EnzymeCrewState) -> str:
    """M5: trait 后路由"""
    if state.fail_closed or state.error:
        return "end"
    return "synthesis"


def route_after_orchestrator(state: EnzymeCrewState) -> str:
    """orchestrator 后路由（09-02 裁定 5 桥接扩展）。

    - 多步路径（multistep_route 非空）→ 先走桥接拆步。
    - 单步查询 → 直接进 substrate，行为与改造前一致。
    """
    if state.fail_closed or state.error:
        return "end"
    if state.multistep_route is not None:
        return "bridge"
    return "substrate"


def route_after_bridge(state: EnzymeCrewState) -> str:
    """多步桥接后路由：拆步后首步进入单步链路（多步循环由上层 checkpointer 驱动）。"""
    if state.fail_closed or state.error:
        return "end"
    return "substrate"


# ─── 图构建 ─────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    构建统一 LangGraph (M3 + M5 共用同一张图)
    
    模式通过 state.pipeline_mode 控制:
    - "m3": orchestrator(passthrough) → substrate → reaction → pool → cage → END
    - "m5": 全量流程含 fallback 分支 + 后处理节点
    """
    workflow = StateGraph(EnzymeCrewState)

    # ── 注册所有节点 ──
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("substrate", substrate_node)
    workflow.add_node("reaction", reaction_node)
    workflow.add_node("reaction_prediction", reaction_prediction_node)  # M5 fallback
    workflow.add_node("enzyme_pool", enzyme_pool_node)
    workflow.add_node("enzymecage", enzymecage_node)
    workflow.add_node("reranking", llm_reranking_node)                  # M5
    workflow.add_node("microbe", microbe_selection_node)                # M5
    workflow.add_node("organism_selection", organism_selection_node)    # M5 选菌层（LLM 硬依赖）
    workflow.add_node("trait", trait_filter_node)                       # M5
    workflow.add_node("synthesis", evidence_synthesis_node)             # M5
    workflow.add_node("bridge", multi_step_bridge_node)                 # M5 多步桥接（裁定 5）

    # ── 入口 ──
    workflow.set_entry_point("orchestrator")

    # ── 边 ──
    # orchestrator → bridge（多步）/ substrate（单步）
    workflow.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"bridge": "bridge", "substrate": "substrate", "end": END},
    )

    # bridge → substrate（拆步后首步进入单步链路）
    workflow.add_conditional_edges(
        "bridge",
        route_after_bridge,
        {"substrate": "substrate", "end": END},
    )

    # substrate → reaction
    workflow.add_conditional_edges(
        "substrate",
        should_continue,
        {"continue": "reaction", "end": END},
    )

    # reaction → pool / prediction / end (条件分支)
    workflow.add_conditional_edges(
        "reaction",
        route_after_reaction,
        {"pool": "enzyme_pool", "predict": "reaction_prediction", "end": END},
    )

    # reaction_prediction → pool / end
    workflow.add_conditional_edges(
        "reaction_prediction",
        should_continue,
        {"continue": "enzyme_pool", "end": END},
    )

    # enzyme_pool → enzymecage
    workflow.add_conditional_edges(
        "enzyme_pool",
        should_continue,
        {"continue": "enzymecage", "end": END},
    )

    # enzymecage → rerank (M5) / end (M3)
    workflow.add_conditional_edges(
        "enzymecage",
        route_after_enzymecage,
        {"rerank": "reranking", "end": END},
    )

    # reranking → microbe
    workflow.add_conditional_edges(
        "reranking",
        route_after_reranking,
        {"microbe": "microbe", "end": END},
    )

    # microbe → organism_selection（选菌层）
    workflow.add_conditional_edges(
        "microbe",
        route_after_microbe,
        {"organism_selection": "organism_selection", "end": END},
    )

    # organism_selection → trait / end（选菌 LLM 硬依赖，fail_closed → end）
    workflow.add_conditional_edges(
        "organism_selection",
        route_after_organism_selection,
        {"trait": "trait", "end": END},
    )

    # trait → synthesis
    workflow.add_conditional_edges(
        "trait",
        route_after_trait,
        {"synthesis": "synthesis", "end": END},
    )

    # synthesis → END
    workflow.add_edge("synthesis", END)

    return workflow


def compile_graph(checkpointer=None):
    """编译并返回可执行图。

    checkpointer: 可注入外部持久化 checkpointer；默认用内存 MemorySaver，
    支持多步桥接循环 / 断点续跑 / 状态回溯（09-02 补齐状态持久化真缺口）。
    """
    workflow = build_graph()
    return workflow.compile(checkpointer=checkpointer or MemorySaver())
