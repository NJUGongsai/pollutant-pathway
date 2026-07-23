# src/tools/enzymecage_client.py
# EnzymeCAGE v1 调用适配器（M3I6-A：晨羽同环境 Python import）
#
# 部署形态：
#   - 生产：LangGraph 与冻结 wrapper 都跑在晨羽同一 Python 3.12.3 环境。
#           通过 `from enzymecage_wrapper import predict` 直接调用。
#   - 本地：ENZYMECAGE_DRY_RUN=1 走 mock 返回，仅用于 pool 构造与 dry-run。
#
# 冻结身份（不改动）：
#   model_version = v1_20260714
#   ensemble seeds = [40, 41, 42, 43, 44]
#
# 调用契约（学生 #6 交付确认）：
#   request:  EnzymeCAGERequest(reaction_smiles, enzyme_pool_uids, top_k, return_ci)
#   response: EnzymeCAGEResponse(ranked_enzymes[list[RankedEnzyme]],
#             model_version, evidence_hash)
#
# 失败语义（学生 #6 §六）：
#   - top_k / 类型越界      → Pydantic ValidationError（不进入 forward）
#   - package root 未设置   → RuntimeError
#   - GPU 数不是 1           → RuntimeError
#   - 反应缺 DRFP/分子图     → MissingReactionAssetError（forward 前 fail-closed）
#   - 部分 UID 缺资产        → 静默过滤
#   - 所有 UID 无效          → 返回空 ranked_enzymes（不 forward）
#
# 本模块保持节点层调用签名不变：call_enzymecage(reaction_smiles, enzyme_pool_uids)。

import hashlib
import logging
import os
import sys
from typing import List, Optional

from src.schemas.evidence import RankedEnzyme
from config.settings import (
    D4_WRAPPER_ROOT,
    ENZYMECAGE_CODE_ROOT,
    ENZYMECAGE_V1_PACKAGE_ROOT,
    ENZYMECAGE_MODEL_VERSION,
    ENZYMECAGE_TOP_K,
    ENZYMECAGE_RETURN_CI,
    ENZYMECAGE_DRY_RUN,
)

logger = logging.getLogger(__name__)


# ---------- lazy import: enzymecage_wrapper ----------

_predict_fn = None
_request_cls = None


def _load_wrapper():
    """
    首次调用时按学生 #6 §三 的环境变量把三个 package root 加到 sys.path，
    再 import enzymecage_wrapper 冻结符号。
    仅在生产（晨羽同环境）路径执行。
    """
    global _predict_fn, _request_cls
    if _predict_fn is not None:
        return

    if not D4_WRAPPER_ROOT or not ENZYMECAGE_V1_PACKAGE_ROOT:
        raise RuntimeError(
            "EnzymeCAGE wrapper 加载失败：D4_WRAPPER_ROOT 或 ENZYMECAGE_V1_PACKAGE_ROOT 未设置。\n"
            "请在晨羽同环境部署时通过环境变量或 .env 提供三个稳定绝对路径：\n"
            "  D4_WRAPPER_ROOT / ENZYMECAGE_CODE_ROOT / ENZYMECAGE_V1_PACKAGE_ROOT\n"
            "本地开发可设置 ENZYMECAGE_DRY_RUN=1 走 mock。"
        )

    # 按学生 #6 §三 顺序：wrapper → code → v1 package，全部前置到 sys.path
    for root in (D4_WRAPPER_ROOT, ENZYMECAGE_CODE_ROOT, ENZYMECAGE_V1_PACKAGE_ROOT):
        if root and root not in sys.path:
            sys.path.insert(0, root)

    try:
        from enzymecage_wrapper import EnzymeCAGERequest, predict  # noqa
    except ImportError as e:
        raise RuntimeError(
            f"无法 import enzymecage_wrapper：{e}\n"
            f"请核对晨羽环境激活状态与三个 package root 是否指向已验收目录。"
        ) from e

    _predict_fn = predict
    _request_cls = EnzymeCAGERequest
    logger.info(
        f"EnzymeCAGE wrapper 加载成功（model_version={ENZYMECAGE_MODEL_VERSION}）"
    )


# ---------- mock: 本地 dry-run ----------

def _mock_predict(reaction_smiles: str, enzyme_pool_uids: List[str]) -> List[RankedEnzyme]:
    """
    本地 dry-run 使用：不调用真实模型，按 UID 字典序生成确定性 rank。
    仅用于验证上游 pool 构造与 State 传递路径，不用于任何评估。
    """
    if not enzyme_pool_uids:
        return []
    uids_sorted = sorted(set(enzyme_pool_uids))[: ENZYMECAGE_TOP_K]
    results = []
    for i, uid in enumerate(uids_sorted, start=1):
        # 确定性伪 score：与 UID 挂钩，保证同 UID 结果一致
        pseudo = int(hashlib.md5(uid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        score = round(0.5 + 0.5 * pseudo, 4)
        results.append(RankedEnzyme(
            uid=uid,
            score=score,
            rank=i,
            ensemble_ci=(score - 0.05, score + 0.05) if ENZYMECAGE_RETURN_CI else None,
        ))
    logger.warning(
        f"[DRY_RUN] mock predict 返回 {len(results)} 条伪结果，不构成任何真实排序证据"
    )
    return results


# ---------- 对外接口（签名保持不变） ----------

def call_enzymecage(
    reaction_smiles: str,
    enzyme_pool_uids: List[str],
    top_k: Optional[int] = None,
    return_ci: Optional[bool] = None,
) -> List[RankedEnzyme]:
    """
    调用 EnzymeCAGE v1 冻结 wrapper（M3I6-A：Python import）。

    Args:
        reaction_smiles: canonical reaction SMILES
        enzyme_pool_uids: 上游 B-primary/C-fallback 输出的 pool UID 列表
        top_k: 覆盖默认 top_k（1 <= top_k <= 100）
        return_ci: 覆盖默认 return_ci

    Returns:
        List[RankedEnzyme]，长度 = min(top_k, 有效唯一 UID 数)

    Raises:
        RuntimeError: 环境变量缺失、GPU 配置错误、wrapper 未加载
        其他 Pydantic/Missing*Asset 错误由 wrapper 原样抛出
    """
    if not enzyme_pool_uids:
        logger.warning("enzyme_pool_uids 为空，跳过 EnzymeCAGE 调用")
        return []

    tk = top_k if top_k is not None else ENZYMECAGE_TOP_K
    rc = return_ci if return_ci is not None else ENZYMECAGE_RETURN_CI

    logger.info(
        f"Calling EnzymeCAGE (mode={'DRY_RUN' if ENZYMECAGE_DRY_RUN else 'IMPORT'}): "
        f"{len(enzyme_pool_uids)} UIDs, top_k={tk}, "
        f"reaction={reaction_smiles[:60]}..."
    )

    if ENZYMECAGE_DRY_RUN:
        return _mock_predict(reaction_smiles, enzyme_pool_uids)

    _load_wrapper()
    request = _request_cls(
        reaction_smiles=reaction_smiles,
        enzyme_pool_uids=list(enzyme_pool_uids),
        top_k=tk,
        return_ci=rc,
    )
    response = _predict_fn(request)

    # 冻结 model_version 一致性检查（不修改，只在不一致时提示）
    if getattr(response, "model_version", None) != ENZYMECAGE_MODEL_VERSION:
        logger.warning(
            f"EnzymeCAGE 返回 model_version={response.model_version} "
            f"与配置 {ENZYMECAGE_MODEL_VERSION} 不一致，请核对晨羽 wrapper 身份"
        )

    results: List[RankedEnzyme] = []
    for item in response.ranked_enzymes:
        ci = None
        raw_ci = getattr(item, "ensemble_ci", None)
        if raw_ci is not None:
            ci = (float(raw_ci[0]), float(raw_ci[1]))
        results.append(RankedEnzyme(
            uid=item.uid,
            score=float(item.score),
            rank=int(item.rank),
            ensemble_ci=ci,
        ))

    logger.info(
        f"EnzymeCAGE 返回 {len(results)} 条 ranked_enzymes "
        f"(evidence_hash={getattr(response, 'evidence_hash', 'N/A')[:16]}...)"
    )
    return results


def health_check() -> bool:
    """
    健康检查：仅在生产模式尝试懒加载 wrapper；dry-run 恒为 True。
    """
    if ENZYMECAGE_DRY_RUN:
        return True
    try:
        _load_wrapper()
        return _predict_fn is not None
    except Exception as e:
        logger.warning(f"EnzymeCAGE health check 失败: {e}")
        return False
