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
    # 原输入 SMILES token（规范化前）——T6-R3 裁定 6：保留原文便于来源可追踪，
    # canonical lowercase aromatic 直接接受时不丢失原始表示。
    raw_substrate_smiles: Optional[str] = None
    substrate_name: Optional[str] = None
    # 取值：
    #   user_smiles     — 用户直接供 SMILES
    #   user_inchi      — 用户直接供 InChI
    #   pubchem_lookup  — LLM 提取名字 → PubChem 官方查表得到 SMILES（2026-07-22 引入）
    #   llm_parsed      — LLM 直接生成 SMILES（已知不可靠，仅作兼容/兼内部回退）
    source: Literal["user_smiles", "user_inchi", "pubchem_lookup", "llm_parsed"]
    provenance: str


class CandidateReaction(BaseModel):
    """候选反应

    source_tag/source_tool 强制非空（T6-R3 裁定 3）：任何构造点必须显式标注来源，
    未知来源显式写 unknown/unavailable，禁止缺省或默认 enviPath（避免零调用时来源误归因）。
    """
    reaction_smiles: str
    similarity_score: float
    source: Literal["retrieved", "predicted"] = "retrieved"
    source_tag: str        # 来源细粒度标签：similarity_retrieval_route_c / biotransformer_envmicro / depending_v32 / mock_dry_run / unknown
    source_tool: str       # 来源工具名：reaction_retriever / reaction_predictor / unknown
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
    """推荐微生物（M5: MicrobeSelectionNode 输出）——单酶→菌事实映射"""
    organism_name: str
    tax_id: Optional[int] = None
    enzyme_uid: str             # 该微生物携带的目标酶
    habitat_match: Optional[str] = None   # 与污水环境的匹配度描述
    growth_conditions: Optional[str] = None
    source_db: Optional[str] = None       # UniProt / KEGG / 文献
    # M4a 证据分级（框架 §3.2 OrganismHit 契约：UniProt SwissProt=reviewed / TrEMBL=unreviewed）
    # MT-D2（2026-07-18 裁定）：v1 不输出 organism_confidence float，
    #   禁止把 reviewed/unreviewed 映射成 0-1 confidence；evidence_level 作为原始维度保留。
    evidence_level: Optional[Literal["reviewed", "unreviewed", "predicted"]] = None
    rationale: Optional[str] = None


class SupportingEnzyme(BaseModel):
    """支持某候选菌的单酶记录（镜像学生权威实现 microbe_crew.tools.organism_aggregator.SupportingEnzyme）。

    保留原始 EnzymeCAGE 分 / rank / CI，不折算、不合成 confidence（MT-D2）。
    """
    uid: str
    score: float
    rank: int
    ensemble_ci: Optional[tuple[float, float]] = None


# ─── M4a 酶→菌原始证据维度（严格镜像学生 microbe_crew.tools.enzyme2organism_tool）───
# MT-D2：确定性代码透传原始证据维度（reviewed 状态 / annotation score / protein existence /
#   KEGG multiplicity），不合成 confidence float；LLM 不得创造数值。
# MT-D1：v1 仅纳入 UniProt reviewed (Swiss-Prot) 宿主；KEGG 作独立交叉证据（保留 multiplicity）。

class UniProtReviewedHostEvidence(BaseModel):
    """UniProt reviewed 宿主证据（与学生同名字段）。"""
    source_database: Literal["UniProtKB"] = "UniProtKB"
    source_url: str
    response_sha256: str
    primary_accession: str
    entry_type: Literal["UniProtKB reviewed (Swiss-Prot)"]
    reviewed: Literal[True] = True
    scientific_organism_name: str
    ncbi_taxon_id: int = Field(gt=0)
    lineage: List[str] = Field(default_factory=list)
    annotation_score: float
    protein_existence: str


class KEGGSupplementEvidence(BaseModel):
    """KEGG 独立补充证据：基因映射 multiplicity 原样保留（不折叠为单一宿主）。"""
    source_database: Literal["KEGG"] = "KEGG"
    source_url: str
    response_sha256: str
    gene_ids: List[str] = Field(default_factory=list)
    multiplicity: int = Field(ge=0)
    state: Literal["missing", "single", "multiple"]


class SourceError(BaseModel):
    """单个数据源查询失败 / 排除的结构化留痕（包括 unreviewed 排除）。"""
    source_database: Literal["UniProtKB", "KEGG"]
    source_url: str
    error_type: str
    message: str


class EnzymeSourceProvenance(BaseModel):
    """单酶的多源原始证据（镜像学生 EnzymeHostMapping / EnzymeSourceProvenance）。"""
    enzyme_uid: str
    uniprot_reviewed: Optional[UniProtReviewedHostEvidence] = None
    kegg: Optional[KEGGSupplementEvidence] = None
    source_errors: List[SourceError] = Field(default_factory=list)


class OrganismCandidate(BaseModel):
    """聚合后的候选菌（M5: OrganismAggregator 输出，框架 §3.3）

    严格对齐学生权威实现（microbe_crew/tools/organism_aggregator.py，15 tests passed）：
    - MT-D3（2026-07-16 裁定 B / 学生 07-27 DECIDED_AND_IMPLEMENTED）排序主键 =
      supporting-enzyme count 降序 + NCBI taxon ID 数字升序 tie-break。
    - MT-D2：v1 不输出 organism_confidence float；原始证据维度经 per_enzyme_source_provenance 透传。
    - MT-D1：仅按 reviewed 宿主的 NCBI taxon 分组；无 reviewed 映射的酶不纳入。
    - aggregation_notes 为导师侧可观测性附加字段（学生 schema 无此项，不影响排序/语义）。
    """
    organism_uid: str                     # = str(ncbi_taxon_id)
    taxonomy_namespace: Literal["NCBI_taxon"] = "NCBI_taxon"
    ncbi_taxon_id: int
    organism_name: str                    # 组内首个（按 rank,uid 排序）scientific name
    organism_name_variants: List[str] = Field(default_factory=list)  # 同 taxon 下去重名称
    supporting_enzymes: List[SupportingEnzyme] = Field(default_factory=list)
    supporting_enzyme_count: int          # MT-D3 排序主键（降序）
    per_enzyme_source_provenance: List[EnzymeSourceProvenance] = Field(default_factory=list)  # MT-D2 原始维度透传
    default_order_rank: int = 0           # 排序后 1-based 名次
    aggregation_notes: Optional[str] = None


class OrganismRecommendation(BaseModel):
    """选菌层（MicrobeSelectionAgent）有界推荐——D6 约束下的 LLM 理由层。

    授权边界（学生 07-27 §4.6 / D6）：M4b TraitFilterLayer 与 M4c 完整决策层 NOT AUTHORIZED，
    当前仅允许「按既有聚合主键（MT-D3）呈现 Top-K + 生成有界理由」。因此本模型：
    - 不含 trait_score / total_score（依赖 M4b，锁定）。
    - default_order_rank 直接沿用 OrganismCandidate 的 MT-D3 确定性名次，LLM 不得覆盖。
    - 候选池成员由确定性聚合决定，LLM 不得增删。

    D6 硬约束：每条 recommended 至少引用 2 条可追溯 evidence；证据不足置
    insufficient_evidence/unknown；冲突 / no_robust_majority 进 uncertainty_flags；
    禁止把 soft evidence 改写成 hard exclusion。
    """
    organism_uid: str
    organism_name: str
    ncbi_taxon_id: int
    default_order_rank: int                       # 沿用 MT-D3 确定性名次（LLM 不覆盖）
    supporting_enzyme_count: int
    recommendation_status: Literal["recommended", "insufficient_evidence", "unknown"]
    cited_evidence: List[str] = Field(default_factory=list)  # D6：recommended 需 ≥2 条可追溯 evidence
    rationale: str                                # LLM 有界理由（仅解释既有证据，不创造数值）
    uncertainty_flags: List[str] = Field(default_factory=list)


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
