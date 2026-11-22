"""v44-Next v1.3 机理排序规则（T1-C + T12-B，默认关闭）。

设计边界
--------
- **不做全局学习式排序器**：只在 ``calibrate_submittable_ranking`` 已产出的
  合法 top-5 内做少量、可解释的机理重排；每条规则都带触发条件与禁用条件。
- **默认关闭**：仅当计划键 ``enable_v13_rank_rules``（T1-C R1）或
  ``enable_v13_stage1_rank_calibration``（T12-B Stage-1 大类精排）为真（由
  ``consensus_and_smart_backfill`` 透传）时生效；两个开关关闭时调用方不进入
  对应规则，与 v1.2/T1 逐题零漂移。
- **只用已有事实**：候选的共产物声明完整性、与池模板的精确相似度、先验分、
  池声明序、以及 T11 Stage-1 已预测的 (primary, secondary) 大类与确定性
  ``classify_reaction_12class`` 类别；不引入新的 LLM 调用或外部数据。
- **零删除候选**：T12-B 只改 top-5 顺序（可选档把池内已核验候选提到首位时，
  被挤出 top-5 的候选仍留在池里，只影响提交序，不改候选集合的合法性判定）。

规则清单（v1.3.0）
------------------
R1 ``coproduct_completeness_exact_anchor``（离去共产物完整性 + 精确池锚点）::

    若 top-1 候选
      - 声明了未解释的共产物（``undeclared`` 非空），且
      - 与池模板相似度缺失或 < 0.80（弱支撑/类似物），
    而 top-5 内存在
      - 无未解释共产物（离去基团/共产物声明完整），且
      - 与池模板相似度 >= 0.95（精确锚点），
    则把后者中先验分最高者升到 Slot 1。

化学直觉：主产物 + 完整共产物声明才能闭合质量平衡；当模型首推项缺共产物
声明且只是弱相似类似物时，优先选择已有精确模板支撑、共产物声明完整的候选。

离线证据（两域调参集，严格 v4）：见
``docs/reports/V13_T1_OFFLINE_REPORT_2026-11-13.md`` §4。
"""

from __future__ import annotations

from typing import Any, Iterable

RANK_RULES_VERSION = "v13-rank-rules-1"

RULE_COPRODUCT_COMPLETENESS = "coproduct_completeness_exact_anchor"

WEAK_SIMILARITY_CEILING = 0.80
EXACT_ANCHOR_SIMILARITY = 0.95

# --------------------------------------------------------------------------
# T12-B：响应后 Stage-1 大类一致性精排（``enable_v13_stage1_rank_calibration``）
# --------------------------------------------------------------------------

STAGE1_RANK_VERSION = "v13-stage1-rank-1"

RULE_STAGE1_PRIMARY = "stage1_primary_class_override"
RULE_STAGE1_SECONDARY = "stage1_secondary_class_override"
RULE_STAGE1_POOL_INTRO = "stage1_pool_primary_introduction"
RULE_STAGE1_TAIL_ORDER = "stage1_tail_class_order"

# 规则参数默认值（少数可解释阈值；全部来自 T11 已冻结的 Stage-1 召回事实
# 与既有先验分档位，不做连续拟合）。离线扫参只用于「5 折交叉验证的候选
# 集合」，最终值写死在这里并由单测锁定。
STAGE1_DEFAULT_PARAMS: dict[str, Any] = {
    "version": STAGE1_RANK_VERSION,
    # 触发面：只处理 top-1 落入「既非 primary 也非 secondary」的题
    "trigger_when_top1_off_class": True,
    # top-1 保护：强锚点/高先验的 top-1 不动（防误伤既有正解）
    "protect_top1_exact_sim": 0.95,
    "protect_top1_prior": 200.0,
    "protect_top1_rec_sim": 0.90,
    # 候选支撑门槛（primary 档）
    "primary_rec_min_sim": 0.90,
    "primary_exact_sim": 0.98,
    "primary_prior": 165.0,
    "primary_min_fams": 2,
    "primary_novel_cb_prior": 140.0,
    # secondary 档更严（Stage-1 真正落在 secondary 的只有 15.2pp）
    "allow_secondary": True,
    "secondary_rec_min_sim": 0.95,
    "secondary_exact_sim": 0.98,
    # 尾部（Slot 2..5）同类优先排序：默认关闭（先证明不误伤 Hit@3/@5）
    "reorder_tail": False,
    # 池内候选提位档（第二档；默认关闭，单独测量净增益与误伤）
    "pool_introduction": False,
    "pool_intro_exact_sim": 0.98,
    "pool_intro_prior": 165.0,
}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _has_undeclared(entry: dict) -> bool:
    return bool(entry.get("undeclared"))


def _rule_coproduct_completeness_exact_anchor(
    first: dict, cand: dict
) -> bool:
    """R1：top-1 共产物声明不完整且弱相似；候选精确命中池模板且声明完整。"""
    if not _has_undeclared(first):
        return False
    if _as_float(first.get("raw_sim")) >= WEAK_SIMILARITY_CEILING:
        return False
    if _has_undeclared(cand):
        return False
    return _as_float(cand.get("raw_sim")) >= EXACT_ANCHOR_SIMILARITY


_RULES = (
    (RULE_COPRODUCT_COMPLETENESS,
     _rule_coproduct_completeness_exact_anchor),
)


def apply_v13_rank_rules(
    top5: Iterable[dict],
    *,
    enabled: bool = False,
    target_slots: int = 5,
) -> tuple[list[dict], dict]:
    """在合法 top-5 上应用机理规则；返回 (新列表, 触发说明)。

    未启用或未触发时原样返回同一列表对象（调用方可据此零成本判定）。
    列表内元素为 ``calibrate_submittable_ranking`` 的候选记录，需含
    ``undeclared``、``raw_sim``、``prior``、``eff_rk`` 字段。
    """
    ordered = list(top5)
    note: dict[str, Any] = {
        "version": RANK_RULES_VERSION,
        "enabled": bool(enabled),
        "triggered_rules": [],
        "promoted_src": None,
    }
    if not enabled or len(ordered) <= 1:
        return ordered, note

    first = ordered[0]
    best_idx: int | None = None
    best_rule = ""
    best_key: tuple[float, int] | None = None
    for idx, cand in enumerate(ordered[1:], start=1):
        for rule_name, predicate in _RULES:
            if not predicate(first, cand):
                continue
            key = (_as_float(cand.get("prior")), -int(cand.get("eff_rk") or 0))
            if best_key is None or key > best_key:
                best_idx, best_rule, best_key = idx, rule_name, key

    if best_idx is None:
        return ordered, note
    promoted = ordered[best_idx]
    ordered = [promoted] + [
        c for i, c in enumerate(ordered) if i != best_idx
    ]
    note["triggered_rules"].append(best_rule)
    note["promoted_src"] = str(promoted.get("src") or "")
    return ordered[: int(target_slots)], note


def v13_rank_rule_entry_fields(
    *,
    undeclared: Iterable[Any] | None,
    raw_sim: Any,
    prior: Any,
    eff_rk: Any,
    src: str,
) -> dict:
    """构造规则消费的最小记录（供 ``calibrate_submittable_ranking`` 复用）。"""
    return {
        "src": str(src),
        "undeclared": list(undeclared or []),
        "raw_sim": _as_float(raw_sim),
        "prior": _as_float(prior),
        "eff_rk": int(eff_rk) if eff_rk is not None else 0,
    }


# --------------------------------------------------------------------------
# T12-B：Stage-1 大类一致性精排
# --------------------------------------------------------------------------


def stage1_rank_params(overrides: dict | None = None) -> dict[str, Any]:
    """默认参数 + 显式覆盖（离线扫参/单测用；生产只用默认值）。"""
    params = dict(STAGE1_DEFAULT_PARAMS)
    for key, value in (overrides or {}).items():
        params[str(key)] = value
    return params


def _valid_class(label: Any) -> bool:
    """12 类受控词表校验（惰性导入，避免与 s5_hybrid_choice 循环导入）。"""
    from .s5_hybrid_choice import REACTION_CLASS_12_LABEL_SET

    return str(label or "") in REACTION_CLASS_12_LABEL_SET


def _off_class(entry: dict, primary: str, secondary: str) -> bool:
    cls = str(entry.get("cls") or "")
    return cls != primary and cls != secondary


def _top1_protected(first: dict, params: dict) -> bool:
    """top-1 保护：任何强锚点/高先验候选都不因 Stage-1 预测被压后。

    防误伤的核心闸：Stage-1 Top-1 只有 71.2%（B121 v6 金标题），
    预测错时若 top-1 本身已是精确 Recorded/极高先验，重排只会亏。
    """
    if _as_float(first.get("raw_sim")) >= float(
            params["protect_top1_exact_sim"]):
        return True
    if _as_float(first.get("prior")) >= float(params["protect_top1_prior"]):
        return True
    return bool(first.get("is_rec")) and _as_float(
        first.get("raw_sim")) >= float(params["protect_top1_rec_sim"])


def _cand_support(cand: dict, *, tier: str, params: dict) -> bool:
    """候选支撑门槛（只认既有事实：跨源/精确锚点/先验分）。"""
    sim = _as_float(cand.get("raw_sim"))
    prior = _as_float(cand.get("prior"))
    n_fams = int(cand.get("n_fams") or 0)
    if tier == "primary":
        return bool(
            (cand.get("is_rec") and sim >= float(
                params["primary_rec_min_sim"]))
            or sim >= float(params["primary_exact_sim"])
            or (prior >= float(params["primary_prior"])
                and n_fams >= int(params["primary_min_fams"]))
            or (cand.get("is_novel") and cand.get("cb")
                and prior >= float(params["primary_novel_cb_prior"])))
    return bool(
        (cand.get("is_rec") and sim >= float(
            params["secondary_rec_min_sim"]))
        or sim >= float(params["secondary_exact_sim"]))


def apply_stage1_class_calibration(
    top5: Iterable[dict],
    *,
    routing: dict | None,
    params: dict | None = None,
    pool_rest: Iterable[dict] | None = None,
    target_slots: int = 5,
) -> tuple[list[dict], dict]:
    """响应后 Stage-1 大类一致性精排（默认关闭的 T12-B 规则面）。

    输入 ``top5`` 为 ``calibrate_submittable_ranking`` 已产出且已过
    T1-C 规则的候选记录（``src``/``cls``/``is_rec``/``raw_sim``/``prior``/
    ``n_fams``/``is_novel``/``cb``/``eff_rk``）。``routing`` 为
    ``{"primary_class": ..., "secondary_class": ...}``（T11 Stage-1 预测；
    解析失败/缺 primary ⇒ 本函数原样返回）。

    规则（每条都有触发与禁用条件）::

      R-S1 ``stage1_primary_class_override``
        top-1 类别 ∉ {primary, secondary} 且 top-1 非强锚点（保护闸），
        top-2..5 内存在类别 = primary 且支撑达标的候选 ⇒ 其最佳者升首位。
      R-S2 ``stage1_secondary_class_override``
        同上但只认 secondary 类，且支撑门槛更严（Stage-1 的 secondary
        正确率显著低于 primary）。
      R-S3 ``stage1_pool_primary_introduction``（参数档，默认关）
        top-5 内无合规候选时，从池内已核验候选（``pool_rest``）取
        primary 类精确锚点提到首位（挤出的第 5 名仍在池内，不删除）。
      R-S4 ``stage1_tail_class_order``（参数档，默认关）
        Slot 2..5 内把「同类且支撑达标」候选稳定前置（提升 Hit@3/@5）。
    """
    p = stage1_rank_params(params)
    ordered = list(top5)
    routing = dict(routing or {})
    primary = str(routing.get("primary_class") or "")
    secondary = str(routing.get("secondary_class") or "")
    note: dict[str, Any] = {
        "version": str(p.get("version") or STAGE1_RANK_VERSION),
        "enabled": True,
        "routing_source": str(routing.get("source") or ""),
        "primary_class": primary or None,
        "secondary_class": secondary or None,
        "triggered_rules": [],
        "promoted_src": None,
        "skipped": "",
    }
    if not _valid_class(primary):
        note["skipped"] = "routing_missing_or_invalid"
        return ordered, note
    if len(ordered) <= 1:
        note["skipped"] = "top5_too_short"
        return ordered, note

    first = ordered[0]
    if bool(p.get("trigger_when_top1_off_class")) and \
            not _off_class(first, primary, secondary):
        note["skipped"] = "top1_on_class"
        return ordered, note
    if _top1_protected(first, p):
        note["skipped"] = "top1_protected"
        return ordered, note

    picks = [
        (idx, cand) for idx, cand in enumerate(ordered[1:], start=1)
        if str(cand.get("cls") or "") == primary
        and _cand_support(cand, tier="primary", params=p)
    ]
    rule = RULE_STAGE1_PRIMARY
    if not picks and bool(p.get("allow_secondary")) and \
            _valid_class(secondary):
        picks = [
            (idx, cand) for idx, cand in enumerate(ordered[1:], start=1)
            if str(cand.get("cls") or "") == secondary
            and _cand_support(cand, tier="secondary", params=p)
        ]
        rule = RULE_STAGE1_SECONDARY

    if picks:
        best_idx, promoted = max(
            picks,
            key=lambda pair: (_as_float(pair[1].get("prior")),
                              -int(pair[1].get("eff_rk") or 0)))
        ordered = [promoted] + [
            c for i, c in enumerate(ordered) if i != best_idx]
        note["triggered_rules"].append(rule)
        note["promoted_src"] = str(promoted.get("src") or "")
    elif bool(p.get("pool_introduction")):
        # 池内合规候选提位档：只认 primary 类 + 精确锚点 + 高先验
        pool_cands = [
            c for c in (pool_rest or [])
            if str(c.get("cls") or "") == primary
            and (bool(c.get("is_rec"))
                 or _as_float(c.get("raw_sim")) >= float(
                     p["pool_intro_exact_sim"]))
            and _as_float(c.get("prior")) >= float(p["pool_intro_prior"])
        ]
        if pool_cands:
            promoted = max(
                pool_cands,
                key=lambda c: (_as_float(c.get("prior")),
                               -int(c.get("pidx") or 99)))
            kept = ordered[: max(1, int(target_slots) - 1)]
            ordered = [promoted] + kept
            note["triggered_rules"].append(RULE_STAGE1_POOL_INTRO)
            note["promoted_src"] = str(promoted.get("src") or "")

    if bool(p.get("reorder_tail")) and len(ordered) > 2:
        head = ordered[0]
        tail = ordered[1:]

        def _tail_key(cand: dict) -> tuple[int, int]:
            on = str(cand.get("cls") or "") in (primary, secondary)
            ok = bool(on and (
                _cand_support(cand, tier="primary", params=p)
                or _cand_support(cand, tier="secondary", params=p)))
            return (0 if ok else 1, int(cand.get("eff_rk") or 0))

        if any(_tail_key(c)[0] == 0 for c in tail):
            tail = sorted(tail, key=_tail_key)
            if [id(c) for c in tail] != [id(c) for c in ordered[1:]]:
                note["triggered_rules"].append(RULE_STAGE1_TAIL_ORDER)
            ordered = [head] + tail

    return ordered[: int(target_slots)], note
