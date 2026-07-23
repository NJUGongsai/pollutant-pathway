# src/schemas/evidence.py
# 证据链与子模型（M3 + M5 全量）

from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# M3 核心模型
# ═══════════════════════════════════════════════════════════════

class SubstrateInfo(BaseModel):
    """底物解析结果"""
    substrate_smiles: str
    substrate_name: Optional[str] = None
    # 取值：
    #   user_smiles     — 用户直接供 SMILES
    #   user_inchi      — 用户直接供 InChI
    #   pubchem_lookup  — LLM 提取名字 → PubChem 官方查表得到 SMILES（2026-07-22 引入）
    #   llm_parsed      — LLM 直接生成 SMILES（已知不可靠，仅作兼容/兼内部回退）
    source: Literal["user_smiles", "user_inchi", "pubchem_lookup", "llm_parsed"]
    provenance: str


class CandidateReaction(BaseModel):
    """候选反应"""
    reaction_smiles: str
    similarity_score: float
    source: Literal["retrieved", "predicted"] = "retrieved"
    rhea_id: Optional[str] = None
    ec_numbers: Optional[List[str]] = None


class RankedEnzyme(BaseModel):
    """EnzymeCAGE 排序结果"""
    uid: str
    score: float
    rank: int
    ensemble_ci: Optional[tuple[float, float]] = None


class EvidenceRecord(BaseModel):
    """证据链记录"""
    stage: str          # "substrate" / "reaction" / "pool" / "ranking" / "reranking" / "microbe" / "trait" / "synthesis"
    action: str         # 具体动作描述
    data: dict[str, Any]
    timestamp: str


# ═══════════════════════════════════════════════════════════════
# M5 扩展模型
# ═══════════════════════════════════════════════════════════════

class RerankedEnzyme(BaseModel):
    """LLM 重排序后的酶（M5: LLMRerankingNode 输出）"""
    uid: str
    original_rank: int
    reranked_rank: int
    original_score: float
    rerank_rationale: str       # LLM 给出的排序理由
    confidence: Optional[float] = None


class MicrobeCandidate(BaseModel):
    """推荐微生物（M5: MicrobeSelectionNode 输出）"""
    organism_name: str
    tax_id: Optional[int] = None
    enzyme_uid: str             # 该微生物携带的目标酶
    habitat_match: Optional[str] = None   # 与污水环境的匹配度描述
    growth_conditions: Optional[str] = None
    source_db: Optional[str] = None       # UniProt / KEGG / 文献
    rationale: Optional[str] = None


class TraitRecord(BaseModel):
    """性状记录（M5: TraitFilterNode，集成 metaTraits）"""
    trait_name: str
    value: Any
    is_ai: bool                    # 独立布尔
    majority_label: Optional[str] = None  # 独立聚合标签
    source_database: Optional[str] = None
    source_url: Optional[str] = None
    tax_id: Optional[int] = None


class PredictedReaction(BaseModel):
    """预测反应（M5: ReactionPredictionNode fallback 输出）"""
    reaction_smiles: str
    prediction_method: str        # "retrosynthesis" / "llm_generation" / ...
    confidence: float
    provenance: str


class IntentClassification(BaseModel):
    """用户意图分类（M5: OrchestratorNode LLM 输出）"""
    intent: Literal[
        "enzyme_recommendation",     # 标准底物→反应→酶流程
        "microbe_recommendation",    # 进一步推荐微生物
        "trait_query",               # 查询微生物性状
        "reaction_exploration",      # 探索反应路径
        "general_question",          # 一般问题
    ]
    confidence: float
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
