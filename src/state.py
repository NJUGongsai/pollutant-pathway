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
    OrganismRecommendation,
    TraitRecord,
    PredictedReaction,
    IntentClassification,
)
from src.schemas.bridge import MultistepRouteInput, MultistepBridgeResult


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
    # OrganismAggregator 聚合输出（菌→支持酶集合，按 MT-D3：supporting-enzyme count 降序+ncbi_taxon_id 升序）
    organism_candidates: Optional[List[OrganismCandidate]] = None

    # ====== M5: OrganismSelectionNode 输出（选菌层 D6 有界理由）======
    # 授权内最小形态：LLM 硬依赖，仅在 MT-D3 确定性顺序上生成有界理由，不覆盖排序/成员。
    # 完整决策层（trait_score 融合）属 M4b/M4c，NOT AUTHORIZED。
    organism_recommendations: Optional[List[OrganismRecommendation]] = None

    # ====== M5: TraitFilterNode 输出 ======
    trait_records: Optional[List[TraitRecord]] = None
    trait_filter_passed: Optional[bool] = None

    # ====== M5: EvidenceSynthesisNode 输出 ======
    final_summary: Optional[str] = None  # 结构化最终报告

    # 证据链与不确定性
    evidence_chain: List[EvidenceRecord] = Field(default_factory=list)
    uncertainty_flags: List[str] = Field(default_factory=list)

    # ====== 防串线锚定字段（09-02 裁定 8：三个真缺口补齐）======
    # 多步桥接下，单步任务与证据必须可锚定到具体 reaction_task_id，防跨步/跨会话串线。
    reaction_task_id: Optional[str] = None   # 当前单步反应任务唯一锚定 id（裁定 5/6 主键）
    source_signature: Optional[str] = None   # 上游数据源签名（工具+版本/SHA），防证据串线
    evidence_hash: Optional[str] = None      # 证据链内容哈希，防篡改/串线

    # ====== M5: 多步—单步桥接智能体（09-02 裁定 5/6）======
    multistep_route: Optional[MultistepRouteInput] = None   # 多步路径输入（非空则先走桥接）
    bridge_result: Optional[MultistepBridgeResult] = None   # 桥接拆步结果（steps + 覆盖统计）

    # 错误处理
    error: Optional[str] = None
    fail_closed: bool = False
