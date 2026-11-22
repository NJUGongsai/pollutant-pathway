# -*- coding: utf-8 -*-
"""adjudication_v14.py — v1.4 T14-3 成对互换机理裁决的**排序层**（默认 OFF）。

定位
----
本模块只做一件极小的事：把一份**已脱敏的外部裁决判决**
（由 ``scripts/eval/v14_t14s3_adjudicator.py`` 在离线批量调用后导出）
翻译成 ``selected_top_keys`` 的位次调整。它**不**新增候选、**不**删除候选、
**不**放宽任何化学身份/立体/角色判据（G1）：进入重排的键集合必须是调用方
已经过 `prepare_hypothesis` + 执行 + 审计 + 准入的 Top-N 之一。

内容寻址与同源约束
------------------
``candidate_display_from_prepared`` 与
``scripts/eval/v13_t4_judge_rerank._candidate_display`` **逐字节同源**：
同一假设在 runflow 侧（``prepared_entries``）与评测侧（``pollutant.sqlite``
导出事件）算出的展示串必须一致，否则 ``*_sha256`` 匹配会静默失配。两侧
都只消费**结构本身**：不带假设 ID、规则 ID、先验分、来源或角色标签。

开关纪律
--------
``enable_v14_pairwise_adjudication=False``（生产默认）⇒ 调用方根本不进本
模块 ⇒ 生产/重放链路零字节漂移。``plan`` 里残留的
``v14_adjudication_external`` 不能绕过开关：``sanitize_adjudication_external``
只在开关打开时被调用。
"""

from __future__ import annotations

import hashlib

# ---------------------------------------------------------------- 常量

ROLE_PRINCIPAL_PRODUCT = "principal_product"

VERDICT_PROMOTE_CHALLENGER = "promote_challenger"
VERDICT_REORDER_PREFIX = "reorder_prefix"

#: 允许进入 runflow 的脱敏字段白名单（其余键一律丢弃，防 plan 夹带）。
ADJUDICATION_EXTERNAL_FIELDS: tuple[str, ...] = (
    "verdict",
    "defender_sha256",
    "challenger_sha256",
    "order_sha256s",
    "gate_tag",
)


# ---------------------------------------------------------------- 展示串


def candidate_display_from_prepared(prep: dict) -> str:
    """假设侧候选展示串（与 T4 评委 ``_candidate_display`` 同源同形）。

    遍历 ``prep["hypothesis"].participants`` 中 ``side == "product"`` 的
    参与物，从 ``prep["states"][state_ref].smiles_isomeric`` 取结构：
    ``role == "principal_product"`` 排前（``role_rank = 0``，Python 稳定
    排序保持原相对序），其余排后（``role_rank = 1``）；按首次出现去重后
    用 ``" + "`` 拼接。空结构/缺状态一律跳过（与评测侧同规则）。
    """
    hypothesis = (prep or {}).get("hypothesis")
    states = (prep or {}).get("states") or {}
    parts: list[tuple[int, str]] = []
    for participant in getattr(hypothesis, "participants", None) or []:
        if str(getattr(participant, "side", "")) != "product":
            continue
        state_ref = str(getattr(participant, "state_ref", "") or "")
        state = states.get(state_ref)
        smiles = str(getattr(state, "smiles_isomeric", "") or "")
        if not smiles:
            continue
        role_rank = (
            0
            if str(getattr(participant, "role", "")) == ROLE_PRINCIPAL_PRODUCT
            else 1
        )
        parts.append((role_rank, smiles))
    if not parts:
        return ""
    parts.sort(key=lambda item: item[0])
    ordered: list[str] = []
    for _rank, smiles in parts:
        if smiles not in ordered:
            ordered.append(smiles)
    return " + ".join(ordered)


def candidate_display_sha256(display: str) -> str:
    """展示串内容 Hash（UTF-8 字节，无归一化/无裁剪 ⇒ 可逐字节复核）。"""
    return hashlib.sha256(str(display or "").encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 脱敏


def sanitize_adjudication_external(raw: object) -> dict | None:
    """只保留白名单字段的结构化脱敏字典（非 dict ⇒ ``None``）。

    ``order_sha256s`` 归一成 ``list[str]``（非 list ⇒ 空 list，让下游按
    "缺声明" 处理而不是猜一个顺序）。
    """
    if not isinstance(raw, dict):
        return None
    out: dict = {}
    for field in ADJUDICATION_EXTERNAL_FIELDS:
        if field not in raw:
            continue
        value = raw[field]
        if field == "order_sha256s":
            out[field] = [
                str(item) for item in value
            ] if isinstance(value, list) else []
            continue
        out[field] = str(value or "")
    return out


# ---------------------------------------------------------------- 重排


def apply_pairwise_adjudication(
    *,
    selected_top_keys: list[str],
    sha_by_key: dict[str, str],
    external: dict | None,
) -> tuple[list[str], dict]:
    """按外部脱敏判决调整 Top-N 位次；返回 ``(新键序, 脱敏披露)``。

    披露字段固定为 ``enabled / applied / verdict / promoted_from_rank /
    gate_tag / skipped``（零 SMILES、零 QID、零先验分）。

    安全守卫（fail-safe，全部"不改序 + 记 skipped"）：
    - 候选 < 2；
    - ``defender_sha256`` 非空但与第 1 位实际 SHA 不符（视图漂移 ⇒ 拒动，
      防把判决套到别的候选上）；
    - ``promote_challenger`` 但 ``challenger_sha256`` 空/未命中；
    - ``reorder_prefix`` 但 ``order_sha256s`` 空/一个都没匹配上；
    - 未知 verdict。
    """
    keys = [str(key) for key in (selected_top_keys or [])]
    ext = external if isinstance(external, dict) else {}
    verdict = str(ext.get("verdict") or "")
    disclosure: dict = {
        "enabled": True,
        "applied": False,
        "verdict": verdict,
        "promoted_from_rank": None,
        "gate_tag": str(ext.get("gate_tag") or ""),
        "skipped": "",
    }
    if len(keys) < 2:
        disclosure["skipped"] = "fewer_than_two_candidates"
        return keys, disclosure

    defender = str(ext.get("defender_sha256") or "")
    if defender and sha_by_key.get(keys[0]) != defender:
        disclosure["skipped"] = "defender_sha256_mismatch"
        return keys, disclosure

    if verdict == VERDICT_PROMOTE_CHALLENGER:
        challenger = str(ext.get("challenger_sha256") or "")
        if not challenger:
            disclosure["skipped"] = "challenger_sha256_missing"
            return keys, disclosure
        for index in range(1, len(keys)):
            if sha_by_key.get(keys[index]) != challenger:
                continue
            reordered = [
                keys[index],
                *keys[:index],
                *keys[index + 1:],
            ]
            disclosure["applied"] = True
            disclosure["promoted_from_rank"] = index + 1
            return reordered, disclosure
        disclosure["skipped"] = "challenger_not_found"
        return keys, disclosure

    if verdict == VERDICT_REORDER_PREFIX:
        order = [str(item) for item in (ext.get("order_sha256s") or [])]
        if not order:
            disclosure["skipped"] = "order_sha256s_missing"
            return keys, disclosure
        taken: set[int] = set()
        picked: list[str] = []
        for wanted in order:
            hit = None
            for index, key in enumerate(keys):
                if index in taken:
                    continue
                if sha_by_key.get(key) == wanted:
                    hit = index
                    break
            if hit is None:
                continue
            taken.add(hit)
            picked.append(keys[hit])
        if not picked:
            disclosure["skipped"] = "order_sha256s_not_found"
            return keys, disclosure
        rest = [key for index, key in enumerate(keys) if index not in taken]
        reordered = picked + rest
        if reordered == keys:
            disclosure["skipped"] = "order_unchanged"
            return keys, disclosure
        disclosure["applied"] = True
        return reordered, disclosure

    disclosure["skipped"] = "verdict_unknown"
    return keys, disclosure


__all__ = [
    "ADJUDICATION_EXTERNAL_FIELDS",
    "ROLE_PRINCIPAL_PRODUCT",
    "VERDICT_PROMOTE_CHALLENGER",
    "VERDICT_REORDER_PREFIX",
    "apply_pairwise_adjudication",
    "candidate_display_from_prepared",
    "candidate_display_sha256",
    "sanitize_adjudication_external",
]