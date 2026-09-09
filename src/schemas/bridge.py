# src/schemas/bridge.py
# 多步—单步桥接智能体契约（09-02 裁定 5 / 裁定 6 冻结字段）
#
# 背景：
#   现有 11 节点编排是「单步」流程（底物 → 反应 → 酶 → 菌）。多步降解路径
#   （A → B → C → D）需拆成单步反应任务逐段匹配酶。裁定 5 同意增加桥接智能体，
#   裁定 6 要求按 reaction_task_id 统计宿主跨步骤覆盖。
#
# 硬约束（裁定 5）：
#   - 按「反应边」拆单步；每步一个 reaction_task_id。
#   - 某步找不到酶 → enzyme_match_status = UNMATCHED_ENZYME，
#     严格禁止拿其他步骤的酶替代（防跨步串线）。

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class MultistepRouteInput(BaseModel):
    """多步降解路径输入（桥接智能体入参）。

    reactant_smiles 按「路径节点顺序」给出相邻节点，每相邻两节点构成一条反应边
    （A, B, C, D 三条边：A>>B、B>>C、C>>D）。
    """

    route_id: str
    reactant_smiles: List[str] = Field(min_length=2)  # 需 ≥2 个节点才能构成至少一条边
    source_tool: str = "enviPath"     # 整条路径默认来源工具（每步可引用）
    reaction_source: Literal["retrieved", "predicted", "merged"] = "retrieved"
    branch_id: Optional[str] = None   # 线性路径为 None


class MultistepStep(BaseModel):
    """多步路径中单个反应步任务（裁定 5 冻结的最小契约字段，一一对应）。"""

    route_id: str                    # 多步路径唯一 id
    reaction_task_id: str            # 单步反应任务唯一锚定 id（防串线主键，裁定 6 聚合键）
    source_node_id: str              # 该步上游节点 id（底物节点）
    target_node_id: str              # 该步下游节点 id（产物节点）
    depth: int = Field(ge=1)         # 路径深度，从 1 起
    branch_id: Optional[str] = None  # 分支 id（线性路径为 None）
    substrate_smiles: str            # 该步底物
    product_smiles: str              # 该步产物
    reaction_smiles: str             # "{substrate}>>{product}" 半反应
    reaction_source: Literal["retrieved", "predicted", "merged"]
    source_tool: str                 # enviPath / BioTransformer / ECLIPSE / ...
    predicted_ec: Optional[List[str]] = None          # 该步预测 EC（无则 None）
    reaction_asset_status: Literal["proxy", "real", "missing"] = "missing"  # 裁定 4 双轨
    enzyme_match_status: Literal["MATCHED", "UNMATCHED_ENZYME", "PENDING"] = "PENDING"

    # —— 实现扩展（非冻结契约字段）：该步酶匹配结果承载 ——
    matched_enzyme_uids: List[str] = Field(default_factory=list)  # UNMATCHED_ENZYME 时必须为空


class OrganismStepCoverage(BaseModel):
    """宿主跨步骤覆盖统计（裁定 6 冻结）。"""

    organism_uid: str                # = str(ncbi_taxon_id)（严格保守 strain/species 边界）
    organism_name: str               # 来源菌名称（物种级代表菌株不冒充原酶来源菌株）
    reaction_task_ids: List[str] = Field(default_factory=list)  # 该宿主覆盖的步骤 id
    covered_step_count: int = 0      # 覆盖步数（= len(reaction_task_ids)）
    covered_depths: List[int] = Field(default_factory=list)     # 覆盖的 depth 列表


class MultistepBridgeResult(BaseModel):
    """桥接智能体输出（组装进 state）。"""

    route_id: str
    steps: List[MultistepStep] = Field(default_factory=list)
    organism_step_coverages: List[OrganismStepCoverage] = Field(default_factory=list)