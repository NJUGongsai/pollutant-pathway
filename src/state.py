# src/state.py
# LangGraph State Pydantic Schema——M3 MVP + M5 全量字段

from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field

from src.schemas.evidence import (
    SubstrateInfo,
    CandidateReaction,
    RankedEnzyme,
    EvidenceRecord,
    # M5 扩展
    RerankedEnzyme,
    MicrobeCandidate,
    OrganismCandidate,
    TraitRecord,
    PredictedReaction,
    IntentClassification,
)


class EnzymeCrewState(BaseModel):
    """EnzymeCrew 全局状态：贯穿 LangGraph 所有节点"""

    # 用户输入
    user_query: str

    # ====== M5: OrchestratorNode 输出 ======
    intent: Optional[IntentClassification] = None
    pipeline_mode: Literal["m3", "m5"] = "m3"  # 运行模式

    # ====== Node 1: SubstrateNode 输出 ======
    substrate_info: Optional[SubstrateInfo] = None

    # ====== Node 2: ReactionNode 输出 ======
    candidate_reactions: List[CandidateReaction] = Field(default_factory=list)

    # ====== M5: ReactionPredictionNode 输出 (fallback) ======
    predicted_reactions: List[PredictedReaction] = Field(default_factory=list)
    reaction_source: Optional[Literal["retrieved", "predicted", "merged"]] = None

    # ====== Node 3: EnzymePoolNode 输出 ======
    enzyme_pool_b: Optional[List[str]] = None        # B 路线 pool（保留 provenance）
    enzyme_pool_c: Optional[List[str]] = None        # C 路线 pool（保留 provenance）
    enzyme_pool_final: Optional[List[str]] = None    # 实际使用的 pool
    pool_route_used: Optional[Literal["B", "C"]] = None
    pool_size: Optional[int] = None

    # ====== Node 4: EnzymeCAGENode 输出 ======
    ranked_enzymes: Optional[List[RankedEnzyme]] = None
    model_version: str = "v1_20260714"

    # ====== M5: LLMRerankingNode 输出 ======
    reranked_enzymes: Optional[List[RerankedEnzyme]] = None

    # ====== M5: MicrobeSelectionNode 输出 ======
    microbe_candidates: Optional[List[MicrobeCandidate]] = None
    # OrganismAggregator 聚合输出（菌→支持酶集合，按 cumulative_score 降序）
    organism_candidates: Optional[List[OrganismCandidate]] = None

    # ====== M5: TraitFilterNode 输出 ======
    trait_records: Optional[List[TraitRecord]] = None
    trait_filter_passed: Optional[bool] = None

    # ====== M5: EvidenceSynthesisNode 输出 ======
    final_summary: Optional[str] = None  # 结构化最终报告

    # 证据链与不确定性
    evidence_chain: List[EvidenceRecord] = Field(default_factory=list)
    uncertainty_flags: List[str] = Field(default_factory=list)

    # 错误处理
    error: Optional[str] = None
    fail_closed: bool = False
