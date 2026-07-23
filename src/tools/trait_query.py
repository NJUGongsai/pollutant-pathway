# src/tools/trait_query.py
# M5: metaTraits 性状查询工具
# 查询微生物污水相关性状 (schema v1.1)

import logging
from typing import List, Optional

from src.schemas.evidence import TraitRecord

logger = logging.getLogger(__name__)

# 污水相关性状 allowlist (v1 最小保守, MT-D4-A 裁定)
# strong (7): 来自学生 MT-D5 调研确认
# medium (2): 来自学生 MT-D5 调研确认
# biofilm formation → 不使用 (M3D4-A 裁定)
WASTEWATER_TRAITS_ALLOWLIST = [
    # Strong relevance (7)
    "aerobic_chemoheterotrophy",
    "fermentation",
    "nitrate_reduction",
    "denitrification",
    "sulfate_reduction",
    "methanogenesis",
    "aromatic_compound_degradation",
    # Medium relevance (2)
    "cellulolysis",
    "xylanolysis",
]


def query_traits(
    tax_ids: List[int],
    traits: Optional[List[str]] = None,
) -> List[TraitRecord]:
    """
    查询指定微生物的污水相关性状。
    
    数据源: metaTraits 下载面 (MT-D5 已验证)
    注意: API v1 (/api/v1) 返回 404，使用下载面替代
    
    Args:
        tax_ids: 微生物 taxonomy ID 列表
        traits: 待查询性状列表 (默认 WASTEWATER_TRAITS_ALLOWLIST)
        
    Returns:
        TraitRecord 列表
    """
    if traits is None:
        traits = WASTEWATER_TRAITS_ALLOWLIST

    # ─── TODO M5: 实际实现 ───────────────────────────────
    # 方案: 预下载 metaTraits 数据 → 本地 SQLite/Parquet 查询
    # 或: 调用 metaTraits 下载面 bulk export → 过滤
    # 
    # 返回格式遵循 schema v1.1:
    #   is_ai: 独立布尔
    #   majority_label: 独立聚合标签
    #   source_database / source_url: 出处
    # ────────────────────────────────────────────────────────

    logger.warning(f"[trait_query] Not implemented, querying {len(tax_ids)} taxa × {len(traits)} traits")
    return []


def apply_soft_filter(
    trait_records: List[TraitRecord],
    candidates: list,
) -> list:
    """
    Soft filter: 不剔除候选微生物，只标记缺失性状。
    (v1 保守策略: 全走 soft)
    
    TODO M5: 实现标记逻辑
    """
    # 占位: 全部通过
    return candidates
