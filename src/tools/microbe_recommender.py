# src/tools/microbe_recommender.py
# M5: 微生物推荐工具
# 封装 UniProt REST 查询（UID → organism）+ 可选委托 M4a Enzyme2OrganismTool。
#
# 纪律说明：
# - 本工具只做"酶 UID → 来源生物"的事实映射（UniProt organism 字段），属 M4a 授权范围。
# - 不做 metaTraits 性状判定 / 污水适配打分（那是 M4b，未立项，见 trait_filter_node）。
# - habitat_match 一律留空并诚实标注"未评估"，绝不编造环境适配结论。

import logging
from typing import List, Optional

import httpx

from src.schemas.evidence import MicrobeCandidate

logger = logging.getLogger(__name__)

UNIPROT_REST = "https://rest.uniprot.org/uniprotkb/{uid}.json"
_HTTP_TIMEOUT = 15.0


def query_organism_by_uid(uid: str) -> Optional[dict]:
    """
    查询单个 UniProt UID 对应的来源生物信息。

    返回 {"organism_name": str, "tax_id": int|None, "source_db": "UniProt"}；
    查询失败（网络异常 / 404 / 结构缺失）返回 None，由上层决定是否降级。
    """
    url = UNIPROT_REST.format(uid=uid)
    try:
        resp = httpx.get(
            url,
            params={"fields": "organism_name,organism_id"},
            headers={"Accept": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning(f"[microbe_recommender] UniProt 网络异常 uid={uid}: {e}")
        return None

    if resp.status_code != 200:
        logger.warning(
            f"[microbe_recommender] UniProt 返回 {resp.status_code} uid={uid}"
        )
        return None

    try:
        data = resp.json()
        org = data.get("organism", {}) or {}
        name = org.get("scientificName")
        if not name:
            return None
        return {
            "organism_name": name,
            "tax_id": org.get("taxonId"),
            "source_db": "UniProt",
        }
    except (ValueError, KeyError) as e:
        logger.warning(f"[microbe_recommender] UniProt 响应解析失败 uid={uid}: {e}")
        return None


def recommend_microbes(
    enzyme_uids: List[str],
    environment: str = "wastewater",
    top_k: int = 5,
) -> List[MicrobeCandidate]:
    """
    给定酶 UID 列表，映射到携带这些酶的来源生物（UniProt organism 字段）。

    数据源:
    1. UniProt REST（当前实装）— UID → scientificName + taxonId
    2. (预留) M4a Enzyme2OrganismTool — 学生侧服务，接口就绪后经 ENZYME2ORGANISM_API_URL 委托

    Args:
        enzyme_uids: 待查询的酶 UniProt ID 列表（通常为 Top-K 排序酶）
        environment: 目标环境（仅记录，不做适配打分，见模块纪律说明）
        top_k: 保留参数，控制返回上限

    Returns:
        MicrobeCandidate 列表；网络不可用时返回空列表（诚实降级，不编造）。
    """
    candidates: List[MicrobeCandidate] = []
    for uid in enzyme_uids[:top_k] if top_k else enzyme_uids:
        info = query_organism_by_uid(uid)
        if info is None:
            continue
        candidates.append(
            MicrobeCandidate(
                organism_name=info["organism_name"],
                tax_id=info["tax_id"],
                enzyme_uid=uid,
                habitat_match=None,  # M4b 未立项，不做污水适配评估
                growth_conditions=None,
                source_db=info["source_db"],
                rationale=(
                    f"UniProt organism 字段映射（目标环境 {environment} 未做性状适配评估，"
                    f"待 M4b metaTraits 集成）"
                ),
            )
        )

    if not candidates:
        logger.warning(
            "[microbe_recommender] 未获得任何 organism 映射（网络不可用或 UID 无命中），返回空列表"
        )
    return candidates
