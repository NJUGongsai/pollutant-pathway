# src/nodes/trait_filter_node.py
# M5: metaTraits 性状过滤节点
# 对推荐的微生物进行污水相关性状筛选

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord, TraitRecord

logger = logging.getLogger(__name__)


# ─── M4b 纪律锁定说明 ────────────────────────────────────────────
# 本节点对应 M4b（metaTraits 运行时性状筛选）。Task 7 已裁定走 (a):
# 只交付契约（MicrobeTraitTool / TraitValue schema），运行时不启动，
# 原因: MT-TQ-02 upstream 数据面未定 + M4b 未正式立项。
#
# 因此本节点保持「诚实 soft-passthrough」——不剔除任何候选、不编造性状，
# 只显式标注锁定状态并置 uncertainty flag，供 evidence_synthesis 汇报。
# ⚠️ 未经 M4b 立项，禁止在此接入真实 metaTraits 查询（否则打脸 Task 7 裁定）。
M4B_LOCK_STATUS = "m4b_locked_contract_only"
M4B_LOCK_NOTE = (
    "trait_filter: M4b 性状运行时未启动（Task 7 裁定走 (a) 只交契约，"
    "MT-TQ-02 upstream 未定 + 未立项）。当前为诚实 soft-passthrough，未做污水性状筛选。"
)


def trait_filter_node(state: EnzymeCrewState) -> dict:
    """
    TraitFilterNode (M5 / M4b): metaTraits 污水性状筛选 —— 当前 M4b 锁定，合规占位

    输入: state.microbe_candidates
    输出: state.trait_records + state.trait_filter_passed

    纪律 (Task 7 裁定 (a)):
    - M4b 运行时未立项，本节点不接入真实 metaTraits 查询
    - 保持 soft-passthrough: 不剔除候选、不编造性状，只显式标注锁定
    - 契约已就绪 (MicrobeTraitTool / TraitValue schema)，立项后在此接线

    预留筛选维度 (立项后启用):
    - 9 个污水候选性状 (strong 7 + medium 2)
    - biofilm formation → 不使用 (M3D4-A 裁定)
    - 全走 soft filter (v1 最小保守 allowlist)
    """
    if not state.microbe_candidates:
        logger.info("[TraitFilterNode] No microbe candidates, skipping trait filter")
        return {"trait_filter_passed": None}

    logger.info(
        f"[TraitFilterNode] M4b locked (contract-only); soft-passthrough "
        f"{len(state.microbe_candidates)} candidates without trait filtering"
    )

    # M4b 锁定：不接入真实 metaTraits，诚实占位，全部通过
    trait_records: list[TraitRecord] = []
    trait_filter_passed = True  # soft filter 语义: 默认通过，不剔除

    uncertainty_flags = list(state.uncertainty_flags)
    uncertainty_flags.append(M4B_LOCK_NOTE)

    evidence = EvidenceRecord(
        stage="trait",
        action="trait_filter_m4b_locked",
        data={
            "input_candidates": len(state.microbe_candidates),
            "filter_mode": "soft_passthrough",
            "status": M4B_LOCK_STATUS,
            "lock_reason": "Task 7 (a): contract-only, MT-TQ-02 upstream undecided, M4b not chartered",
            "traits_applied": 0,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "trait_records": trait_records,
        "trait_filter_passed": trait_filter_passed,
        "uncertainty_flags": uncertainty_flags,
        "evidence_chain": state.evidence_chain + [evidence],
    }
