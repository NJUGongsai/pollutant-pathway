# -*- coding: utf-8 -*-
"""consensus_v13.py — v1.3 T13-B 多次采样 RRF + Stage-1 共识融合（默认 OFF）。

定位
----
零放宽：本模块**只对既有合法候选做排序融合**——
- 候选来源 = 各 pass 的 ``top-5``（来自 ``calibrate_submittable_ranking``
  已过编译/执行/审计/准入的 ``submittable`` 行）∪ ``submittable`` 全集；
- **不新增**任何身份/角色/写法判定，**不删除**池内候选（G1 主口径）：
  融合结果只是同一批既有候选的位次排列，落账仍走既有调度/提交面；
- 默认关闭（``enable_v13_multi_sample_consensus=False``）⇒ 调用方不走
  本模块，生产行为逐字节不变。

打分公式（透明、确定性、可复算）
--------------------------------
对候选 ``c``（键 = ``src``）::

    rrf_score(c) = Σ_{p ∈ 非空 pass, c 在 p 的 top-5} 1 / (rrf_k + rank_p + 1)
    score(c) = rrf_score(c)
             + (multi_pass_bonus if n_passes_present(c) >= 2 else 0.0)
             + stage1_bonus(c)          # 匹配 primary/secondary 类时的固定加项
             + (rec_exact_bonus if is_rec and raw_sim >= rec_exact_sim else 0.0)
             + rec_sim_weight * raw_sim
             + prior / prior_divisor

- ``rank_p`` = 该候选在 pass ``p`` 的 top-5 中的 **0 基位次**（公式里的
  ``+1`` 使它与标准 RRF 的 1 基位次等价）；
- ``stage1_bonus`` = ``stage1_primary_bonus``（``cls == primary_class``）/
  ``stage1_secondary_bonus``（``cls`` ∈ secondary 类且不等于 primary）/
  0.0（无有效路由或类不匹配）；
- 破平次序：``(-score, pass_0 位次或 999, eff_rk, src)``（全确定性）。

两条保护（防止单批噪声把已证实锚点挤掉）
----------------------------------------
1. **全票一致首位保护**（``protect_top1_unanimous``）：所有非空 pass 的
   rank-0 候选同键 ⇒ 该候选锁死首位。
2. **强锚点首 pass 保护**：``pass_0[0]`` 满足
   ``is_rec and raw_sim >= protect_top1_exact_sim`` 或
   ``prior >= protect_top1_prior`` 时，只有同时具备「多 pass 共识
   （``n_passes_present >= 2``）+ Stage-1 类支撑（stage1_bonus > 0）」
   双支撑的候选才允许把它挤下首位；否则锚点锁首。触发与未触发都写进
   ``note``（``protections``）。

v1.4 T14-1A 扩展（**默认全部关闭/零作用 ⇒ 与 v1.3 逐位一致**）
-------------------------------------------------------------
新增三个默认关闭的可选参数（原 11 键原值不动）::

    equiv_cluster_mode:      "none"（默认，按 ``_candidate_key`` 计票）
                             / "strict"（按候选既有 ``p_st`` 严格主产物身份
                             归簇，缺失 ``p_st`` 回退 ``src``）
                             / "cn_neutral"（按受护栏约束的**去质子**主产物
                             规范身份归簇：``normalize_charge_smiles`` +
                             ``chemstate._identity_key``，失败回退
                             ``p_st`` → ``src``）
    novel_low_sim_pool_boost: 0.0（题面池候选最高 ``raw_sim`` 低于
                             ``low_sim_pool_threshold`` 且候选 ``is_novel``
                             且（``n_passes_present >= 2`` 或匹配 Stage-1
                             ``primary_class``）时给的破错池锚定加分）
    low_sim_pool_threshold:  0.60
    dedup_equiv_in_top5:     True（仅 ``equiv_cluster_mode != "none"`` 生效：
                             同一等价簇在 Top-5 只占一个槽位）

等价簇合票（``equiv_cluster_mode != "none"``）只改**投票单元**，不碰任何
候选行内容：

- 同一 pass 内多个候选落入同一等价簇 ⇒ 取该 pass 内**最小 rank** 计入该
  簇在该 pass 的投票（单 pass 不重复刷票）；
- 跨 pass 聚合簇的 ``rrf_score`` / ``n_passes_present``；
- 簇代表行（representative ``src``）确定性取簇内**单行基础分**
  （``stage1_bonus + rec_exact_bonus + sim_bonus + prior_bonus``）最高者，
  平局按 ``not is_novel`` 优先、``pass0_pos``、``eff_rk``、``src``；
- 输出行原封不动来自既有合法候选（``rows_by_key`` / ``example_by_key``），
  不改 SMILES/事件/角色，不产生同簇重复占位。

红线：零 LLM、零网络、零金标；本模块只消费调用方给的候选行。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

CONSENSUS_VERSION = "v13-multi-sample-consensus-1"
# v1.4 T14-1A：等价簇合票版本标签（只在 equiv_cluster_mode != "none" 时写进
# note 的 ``equiv_version``；默认路径不出现该键）。
CONSENSUS_EQUIV_VERSION = "v14-equiv-cluster-2"

CONSENSUS_DEFAULT_PARAMS: dict[str, Any] = {
    "rrf_k": 2.0,
    "multi_pass_bonus": 0.25,
    "stage1_primary_bonus": 0.18,
    "stage1_secondary_bonus": 0.07,
    "rec_exact_sim": 0.95,
    "rec_exact_bonus": 0.10,
    "rec_sim_weight": 0.08,
    "prior_divisor": 2000.0,
    "protect_top1_unanimous": True,
    "protect_top1_exact_sim": 0.98,
    "protect_top1_prior": 210.0,
    # ---- v1.4 T14-1A 新增（默认关闭/零作用；原 11 键原值不变）----
    "equiv_cluster_mode": "none",
    "novel_low_sim_pool_boost": 0.0,
    "low_sim_pool_threshold": 0.60,
    "dedup_equiv_in_top5": True,
    # ---- v1.4 T14-4 新增（只在 ``pass_eligible_keys`` 非 None 时消费；
    # 默认参数 + ``pass_eligible_keys=None`` ⇒ 既有分数 100% 逐字节不变）--
    # 资格率归一化 RRF：``rrf *= (n_pool_passes + alpha) / (n_elig + alpha)``。
    # RRF ``k=60`` 下 rank1 与 rank2 仅差 1.6%，``alpha=0.0`` 才保证跨池
    # 全票 #1 不被旧池常驻项反超；参数保留供网格/CV 核验。
    "elig_norm_alpha": 0.0,
    # 至少在 ``elig_norm_min_elig`` 个有池 pass 中具备参选资格才做放大
    # （防单路孤立项虚胖）。
    "elig_norm_min_elig": 2,
    # 资格感知全票锁（仅 ``pass_eligible_keys is not None`` 时生效）。
    "protect_top1_unanimous_eligible": True,
    # 全票锁的 Stage-1 尊重：默认 False 零漂移；显式 True 时非 Stage-1
    # 的全票锁可被更强 Stage-1 竞争者解除。
    "unanimous_respect_stage1": False,
}

EQUIV_CLUSTER_MODES: tuple[str, ...] = (
    "none", "strict", "cn_neutral", "v6_neutral")

CONSENSUS_FORMULA = (
    "rrf_score = sum(1/(rrf_k+rank+1)) over passes containing the candidate"
    " (rank = 0-based position); score = rrf_score"
    " + (multi_pass_bonus if n_passes>=2 else 0)"
    " + stage1_bonus(primary/secondary class match)"
    " + (rec_exact_bonus if is_rec and raw_sim>=rec_exact_sim else 0)"
    " + rec_sim_weight*raw_sim + prior/prior_divisor")


def consensus_params(overrides: dict | None = None) -> dict[str, Any]:
    """默认参数 + 显式覆盖（离线扫参/单测用；生产只用默认值）。"""
    params = dict(CONSENSUS_DEFAULT_PARAMS)
    for key, value in (overrides or {}).items():
        params[str(key)] = value
    return params


# v1.4 T14-1A：plan 级开关白名单（生产唯一入口；默认全 False ⇒ 零漂移）。
V14_EQUIV_CLUSTER_MODES: tuple[str, ...] = ("strict", "cn_neutral", "v6_neutral")
V14_RAW_ORDER_PASS_MODES: tuple[str, ...] = ("raw_v13", "guarded_r2_r7")
V14_DEFAULT_EQUIV_MODE = "strict"
V14_DEFAULT_PASS_MODE = "raw_v13"
V14_DEFAULT_NOVEL_LOW_SIM_BOOST = 0.12
V14_DEFAULT_LOW_SIM_POOL_THRESHOLD = 0.60
# v1.4 T14-4：跨池资格率归一化的默认值（只在开关打开时注入）。
V14_DEFAULT_ELIG_NORM_ALPHA = 0.0
V14_DEFAULT_ELIG_NORM_MIN_ELIG = 2
# 研究参数里属于 v1.4 的键：**只有**对应 plan 开关为真才允许生效
# （防止 plan patch 绕过开关直接激活新机制 ⇒ 开关是唯一生产入口）。
_V14_GATED_PARAM_KEYS: tuple[str, ...] = (
    "equiv_cluster_mode",
    "novel_low_sim_pool_boost",
    "low_sim_pool_threshold",
    "dedup_equiv_in_top5",
    "consensus_pass_mode",
    "elig_norm_alpha",
    "elig_norm_min_elig",
    "protect_top1_unanimous_eligible",
    "unanimous_respect_stage1",
    "elig_norm_floor",
    "multipass_consensus_v3",
)


def _v14_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def consensus_params_from_plan(plan: dict | None,
                               base: dict | None = None) -> dict | None:
    """把 plan 的 v1.4 开关归一成内部共识参数（默认全关 ⇒ ``None``）。

    - ``enable_v14_equiv_product_consensus``：打开同产物等价簇合票；
      子模式 ``v14_equiv_cluster_mode`` = ``"strict"``（默认，按严格主产物
      ``p_st`` 归簇）/ ``"cn_neutral"``（去质子规范身份归簇）；非法值
      回退 ``"strict"``（开关显式打开时的保守默认）。
    - ``enable_v14_novel_low_sim_boost``：打开破错池锚定加分；
      ``v14_novel_low_sim_boost``（默认 0.12，<=0 视为关闭）与
      ``v14_low_sim_pool_threshold``（默认 0.60，非法/越界回退默认）。
    - ``enable_v14_raw_order_consensus``：共识各 pass 改变 v1.1 规则消费；
      子模式 ``v14_consensus_pass_mode`` = ``"raw_v13"``（默认，保留模型
      原始合法序）/ ``"guarded_r2_r7"``（只收紧 Rule 2/7）；非法值回退
      ``"raw_v13"``。

    ``base`` 为既有 ``plan.v13_consensus_params``（研究期参数覆盖）：本
    函数先剔除其中全部 v1.4 键，再按开关重新注入 ⇒ **开关关闭时新机制
    100% 不生效**（G1：默认 False 零漂移；不能靠 plan patch 绕过开关）。
    返回 ``None`` 表示"无任何参数覆盖"（调用方保持既有 ``None`` 语义）。

    v1.4 T14-4：``enable_v14_cross_pool_elig_norm`` 打开跨池资格率归一化
    （``elig_norm_alpha`` 默认 0.0、``elig_norm_min_elig`` 默认 2；
    ``protect_top1_unanimous_eligible`` 默认 True、``unanimous_respect_
    stage1`` 默认 False —— 均可用 ``v14_*`` plan 键显式覆盖）。
    """
    merged = dict(base or {})
    for key in _V14_GATED_PARAM_KEYS:
        merged.pop(key, None)
    source = dict(plan or {})
    if bool(source.get("enable_v14_equiv_product_consensus", False)):
        mode = str(source.get("v14_equiv_cluster_mode")
                   or V14_DEFAULT_EQUIV_MODE).strip().lower()
        if mode not in V14_EQUIV_CLUSTER_MODES:
            mode = V14_DEFAULT_EQUIV_MODE
        merged["equiv_cluster_mode"] = mode
        if "v14_dedup_equiv_in_top5" in source:
            merged["dedup_equiv_in_top5"] = bool(
                source.get("v14_dedup_equiv_in_top5"))
    if bool(source.get("enable_v14_novel_low_sim_boost", False)):
        boost = _v14_float(
            source.get("v14_novel_low_sim_boost"),
            V14_DEFAULT_NOVEL_LOW_SIM_BOOST)
        threshold = _v14_float(
            source.get("v14_low_sim_pool_threshold"),
            V14_DEFAULT_LOW_SIM_POOL_THRESHOLD)
        if not (0.0 < threshold <= 1.0):
            threshold = V14_DEFAULT_LOW_SIM_POOL_THRESHOLD
        merged["novel_low_sim_pool_boost"] = boost if boost > 0.0 else 0.0
        merged["low_sim_pool_threshold"] = threshold
    if bool(source.get("enable_v14_raw_order_consensus", False)):
        mode = str(source.get("v14_consensus_pass_mode")
                   or V14_DEFAULT_PASS_MODE).strip().lower()
        if mode not in V14_RAW_ORDER_PASS_MODES:
            mode = V14_DEFAULT_PASS_MODE
        merged["consensus_pass_mode"] = mode
    if bool(source.get("enable_v14_cross_pool_elig_norm", False)):
        # v1.4 T14-4：跨池资格率归一化。alpha >= 0；min_elig >= 1
        # （非法值回退默认）。两个保护子项默认 = 任务书口径。
        alpha = _v14_float(source.get("v14_elig_norm_alpha"),
                           V14_DEFAULT_ELIG_NORM_ALPHA)
        if not (alpha >= 0.0):
            alpha = V14_DEFAULT_ELIG_NORM_ALPHA
        min_elig = int(_v14_float(source.get("v14_elig_norm_min_elig"),
                                  float(V14_DEFAULT_ELIG_NORM_MIN_ELIG)))
        if min_elig < 1:
            min_elig = V14_DEFAULT_ELIG_NORM_MIN_ELIG
        merged["elig_norm_alpha"] = float(alpha)
        merged["elig_norm_min_elig"] = int(min_elig)
        merged["protect_top1_unanimous_eligible"] = bool(
            source.get("v14_protect_top1_unanimous_eligible", True))
        merged["unanimous_respect_stage1"] = bool(
            source.get("v14_unanimous_respect_stage1", False))
    if bool(source.get("enable_v14_multipass_consensus_v3", False)):
        # v1.4 T14-4 Consensus v3：标准 2-pass RRF 尺度归一（rrf *= 2/N）+
        # 跨池 novel 半池资格对等（top1>=1 & np>=2）+ 首位多数票破强锚锁。
        # N=2 时三项数学上恒等为 1.0x / 空动作；零新增数值超参。
        merged["multipass_consensus_v3"] = True
    # 保持既有 None / {} 语义（base 显式给空 dict ⇒ 仍返回空 dict）。
    if base is not None or merged:
        return merged
    return None


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _valid_class(label: Any) -> bool:
    """12 类受控词表校验（惰性导入，避免与 s5_hybrid_choice 循环导入）。"""
    from .s5_hybrid_choice import is_valid_reaction_class_12

    return bool(is_valid_reaction_class_12(str(label or "")))


def routing_classes(routing: dict | None) -> tuple[str, tuple[str, ...]]:
    """归一 Stage-1 路由：``(primary_class, secondary_classes)``。

    兼容 ``secondary_class``（单值）与 ``secondary_classes``（列表）；
    只保留 12 类受控词表内的标签（无效/缺失 ⇒ 空）。primary 与
    secondary 重复时 secondary 侧去重（primary 优先，不加两次分）。
    """
    raw = dict(routing or {})
    primary = str(raw.get("primary_class") or "")
    if not _valid_class(primary):
        primary = ""
    secondary: list[str] = []
    listed = raw.get("secondary_classes")
    if isinstance(listed, (list, tuple)):
        secondary.extend(str(item or "") for item in listed)
    single = str(raw.get("secondary_class") or "")
    if single:
        secondary.append(single)
    seen: set[str] = {primary} if primary else set()
    out: list[str] = []
    for label in secondary:
        if not _valid_class(label) or label in seen:
            continue
        seen.add(label)
        out.append(label)
    return primary, tuple(out)


def _stage1_bonus(row: dict, primary: str,
                  secondary: tuple[str, ...], params: dict) -> float:
    cls = str(row.get("cls") or "")
    if primary and cls == primary:
        return _as_float(params["stage1_primary_bonus"])
    if cls and cls in secondary:
        return _as_float(params["stage1_secondary_bonus"])
    return 0.0


def _candidate_key(row: dict) -> str:
    """候选身份：``src``（既有逻辑键）；缺失时退 ``p_st``（严格产物身份）。

    两者都缺 ⇒ 空串（调用方跳过该行，不猜身份）。
    """
    return str(row.get("src") or row.get("p_st") or "")


def _is_strong_anchor(row: dict, params: dict) -> bool:
    if not row:
        return False
    if bool(row.get("is_rec")) and _as_float(
            row.get("raw_sim")) >= _as_float(params["protect_top1_exact_sim"]):
        return True
    return _as_float(row.get("prior")) >= _as_float(params["protect_top1_prior"])


@lru_cache(maxsize=32768)
def _neutral_identity(smiles: str) -> str:
    """``cn_neutral`` 簇身份：去质子规范身份（惰性导入，零新增判据）。

    只做**既有**域函数的组合：``domain.identity.normalize_charge_smiles``
    （电荷归一化 canonical）+ ``pollutant.chemstate._identity_key``（化学
    CX 事实子集身份）。任何失败 ⇒ 空串（调用方回退 ``p_st`` → ``src``，
    不猜身份）。
    """
    text = str(smiles or "")
    if not text:
        return ""
    try:
        from rdkit import Chem

        from ..domain.identity import normalize_charge_smiles
        from ..pollutant.chemstate import _identity_key

        normalized = normalize_charge_smiles(text)
        if not normalized:
            return ""
        mol = Chem.MolFromSmiles(normalized)
        if mol is None:
            return ""
        return str(_identity_key(mol) or "")
    except Exception:  # noqa: BLE001 —— 失败即回退，不猜身份
        return ""


@lru_cache(maxsize=32768)
def _v6_neutral_identity(smiles: str) -> str:
    """``v6_neutral`` 簇身份：v6 主口径「电荷中和 → 严格身份」归簇。

    v1.4 T14-4：多组分（含 ``.``）盐保护 —— 与
    ``score_disclosure_v4cn.py`` 护栏 4 对齐，**不去盐合并**（直接返回
    空串，使 ``_cluster_identity`` 回退 ``st:{p_st}``）；单组分则复用
    库内 ``_neutral_identity``（与 ``cn_neutral`` 同一中和事实源），
    非空时加 ``v6n:`` 前缀（只作内部聚类键；``note`` 只写
    ``cluster-1..n`` 不透明别名，零 SMILES）。
    """
    text = str(smiles or "")
    if not text or "." in text:
        return ""
    val = _neutral_identity(text)
    return f"v6n:{val}" if val else ""


def _equiv_cluster_mode(params: dict) -> str:
    """合法化 ``equiv_cluster_mode``（未知值 ⇒ ``"none"``，fail-safe）。"""
    mode = str(params.get("equiv_cluster_mode") or "none").strip().lower()
    return mode if mode in EQUIV_CLUSTER_MODES else "none"


def _cluster_identity(row: dict, mode: str) -> str:
    """候选行的等价簇身份（``mode == "none"`` 时退回 ``_candidate_key``）。

    返回值只用于**本函数内**的投票聚合：``strict``/``cn_neutral`` 会带
    产物 SMILES 片段，故**禁止**写进 ``note``（对外披露用不透明别名）。
    """
    if mode == "none":
        return _candidate_key(row)
    p_st = str(row.get("p_st") or "")
    if mode == "strict":
        return f"st:{p_st}" if p_st else f"src:{_candidate_key(row)}"
    if mode == "v6_neutral":
        # v1.4 T14-4：v6 主口径（电荷中和 → 严格身份）归簇；多组分/失败
        # ⇒ 回退 p_st → src（不跨组分猜身份、不去盐合并）。
        neutral6 = _v6_neutral_identity(str(row.get("p_smi") or ""))
        if neutral6:
            return neutral6
        if p_st:
            return f"st:{p_st}"
        return f"src:{_candidate_key(row)}"
    neutral = _neutral_identity(str(row.get("p_smi") or ""))
    if neutral:
        return f"cn:{neutral}"
    if p_st:
        return f"st:{p_st}"
    return f"src:{_candidate_key(row)}"


def _pool_max_raw_sim(rows_by_key: dict[str, dict],
                      ordered_passes: list[list[dict]]) -> float:
    """题面池候选最高 ``raw_sim``（只看非 ``novel`` 行；无池行 ⇒ ``0.0``）。

    ``novel`` 行不属于"题面池候选"，不参与该最大值（否则高分 novel 会把
    破错池锚定加分自我压制）。池行全部缺席（例如零池盲写批）⇒ ``0.0``
    ⇒ 阈值条件自然成立（这正是该加分的用武之地）。
    """
    best: float | None = None
    for row in rows_by_key.values():
        if bool(row.get("is_novel")):
            continue
        value = _as_float(row.get("raw_sim"))
        best = value if best is None else max(best, value)
    if best is None:
        for current in ordered_passes:
            for row in current:
                if bool(row.get("is_novel")):
                    continue
                value = _as_float(row.get("raw_sim"))
                best = value if best is None else max(best, value)
    return 0.0 if best is None else float(best)


def _novel_low_sim_boost(row: dict, pool_max_raw_sim: float,
                         routing_primary: str, n_passes: int,
                         params: dict) -> float:
    """破错池锚定加分（默认 ``0.0`` ⇒ 恒返回 ``0.0``，零漂移）。"""
    boost = _as_float(params.get("novel_low_sim_pool_boost"))
    if boost <= 0.0 or not bool(row.get("is_novel")):
        return 0.0
    if not (float(pool_max_raw_sim) < _as_float(
            params.get("low_sim_pool_threshold"))):
        return 0.0
    primary_match = bool(routing_primary) and \
        str(row.get("cls") or "") == str(routing_primary)
    if int(n_passes) >= 2 or primary_match:
        return boost
    return 0.0


def _pass_rrf_contrib(ranks: dict[int, int], rrf_k: float) -> float:
    """单候选/单簇的基础 RRF 项 ``sum(1/(rrf_k+rank+1))``（改前同款）。

    资格率归一化（v1.4 T14-4）不在此处按 pass 加权：它是对**整条候选**
    的 RRF 总分乘一个可解释因子 ``(n_pool+alpha)/(n_elig+alpha)``（见
    ``_elig_norm_factor``），两套口径不可混用。
    """
    total = 0.0
    for rank in ranks.values():
        total += 1.0 / (float(rrf_k) + float(rank) + 1.0)
    return total


def _elig_norm_factor(
    ranks: dict[int, int],
    *,
    ordered_elig: list[set[str] | None],
    non_empty_pool_passes: list[int],
    n_pool_passes: int,
    params: dict,
    is_novel: bool,
    key: str | None = None,
    cluster_keys: set[str] | None = None,
) -> tuple[float, list[int] | None]:
    """v1.4 T14-4：跨池资格率归一化因子（非池/单池 ⇒ 1.0 零作用）。

    - 只对**池候选**（``not is_novel``）且 ``n_pool_passes >= 2`` 生效；
    - 资格 pass 判定（与任务书逐字对齐）：
      非簇模式 ``elig[idx] is None or key in elig[idx] or idx in ranks``；
      簇模式 ``elig[idx] is None or idx in ranks or bool(c_keys & elig[idx])``；
    - ``min_elig <= n_elig < n_pool_passes`` ⇒ 乘
      ``(n_pool_passes + alpha) / (n_elig + alpha)``；否则 1.0。
    返回 ``(factor, elig_indices)``；``elig_indices`` 供资格感知全票锁复用。
    """
    if is_novel or n_pool_passes < 2:
        return 1.0, None
    elig_indices: list[int] = []
    for idx in non_empty_pool_passes:
        eligible = (ordered_elig[idx] if idx < len(ordered_elig) else None)
        if eligible is None:
            elig_indices.append(idx)
            continue
        if idx in ranks:
            elig_indices.append(idx)
            continue
        if cluster_keys is not None:
            if bool(set(cluster_keys) & eligible):
                elig_indices.append(idx)
        elif key is not None and key in eligible:
            elig_indices.append(idx)
    n_elig = len(elig_indices)
    min_elig = int(_as_float(params.get("elig_norm_min_elig")) or 2)
    alpha = max(0.0, _as_float(params.get("elig_norm_alpha")))
    if min_elig <= n_elig < n_pool_passes:
        return ((float(n_pool_passes) + alpha) / (float(n_elig) + alpha),
                elig_indices)
    return 1.0, elig_indices


def _apply_v3_rrf_scaling(
    rrf_raw: float,
    *,
    elig_factor: float,
    elig_enabled: bool,
    is_pure_novel: bool,
    n_passes_total: int,
    n_passes_present: int,
    top1_votes: int,
    v3_enabled: bool,
) -> tuple[float, float, float]:
    """v1.4 Consensus v3：统一（非簇 + 等价簇同源）RRF 尺度与跨池 novel 对等缩放。

    返回 ``(rrf_scaled, effective_elig_factor, novel_elig_factor)``：
    - ``v3_enabled=False`` ⇒ 原封不动乘 ``elig_factor``（仅 ``elig_enabled`` 时），
      零漂移；
    - ``v3_enabled=True``：
      1) 池候选资格放大上限 ``<= 3.0``（防 N>=9 时 2-pass 偶然项过度放大）；
      2) 纯 novel 候选/簇在 ``N>=3 & np>=2 & top1_votes>=1`` 时享半池资格对等
         ``N / max(np, 0.5*N)``（上限 2.0x）；
      3) ``N>=2`` 时将 RRF 归一到标准 2-pass 尺度 ``rrf *= 2.0 / N``（N=2 恒为
         1.0x 零漂移；N>=3 时保持语料/Stage-1/先验与 N=2 完全同比例）。
    """
    eff_elig = float(elig_factor)
    if elig_enabled and v3_enabled:
        eff_elig = min(3.0, eff_elig)
    rrf = float(rrf_raw) * (eff_elig if elig_enabled else 1.0)
    novel_factor = 1.0
    if v3_enabled:
        if (is_pure_novel and int(n_passes_total) >= 3
                and int(n_passes_present) >= 2 and int(top1_votes) >= 1):
            denom = max(float(n_passes_present), 0.5 * float(n_passes_total))
            novel_factor = float(n_passes_total) / max(1e-9, denom)
            rrf = rrf * novel_factor
        if int(n_passes_total) >= 2:
            rrf = rrf * (2.0 / float(n_passes_total))
    return float(rrf), float(eff_elig), float(novel_factor)


def _can_displace_strong_anchor(
    *,
    challenger_n_passes: int,
    challenger_stage1_bonus: float,
    challenger_top1_votes: int,
    anchor_top1_votes: int,
    v3_enabled: bool,
) -> tuple[bool, bool]:
    """强锚点首 pass 保护破锁条件（非簇 + 等价簇共用同源判据）。

    返回 ``(allow_displace, by_top1_majority)``。N=2 时非锚挑战者最多 1 张
    rank-0 票，``challenger_top1_votes >= 2`` 恒假 ⇒ N=2 严格零漂移。
    """
    stage1_double = (
        int(challenger_n_passes) >= 2 and float(challenger_stage1_bonus) > 0.0
    )
    top1_maj = bool(
        v3_enabled
        and int(challenger_top1_votes) >= 2
        and int(challenger_top1_votes) > int(anchor_top1_votes)
    )
    return (stage1_double or top1_maj), top1_maj


def _stage1_override_candidate(
    scored_items: list[dict],
    locked_item: dict | None,
    n_passes_total: int,
) -> dict | None:
    """``unanimous_respect_stage1``：返回可解除全票锁的 Stage-1 竞争者。

    条件（任务书逐条）：被锁项 ``stage1_bonus == 0.0``；存在另一项
    ``score > locked_score``、``stage1_bonus > 0.0`` 且
    ``n_passes_present >= max(2, len(ordered_passes) - 1)``。取满足
    条件的最高分项（按调用方排序后的首项）；无 ⇒ None。
    """
    if locked_item is None:
        return None
    if float(locked_item.get("stage1_bonus") or 0.0) != 0.0:
        return None
    threshold = max(2, int(n_passes_total) - 1)
    best: dict | None = None
    for item in scored_items:
        if item is locked_item:
            continue
        if float(item.get("score") or 0.0) <= float(
                locked_item.get("score") or 0.0):
            continue
        if float(item.get("stage1_bonus") or 0.0) <= 0.0:
            continue
        if int(item.get("n_passes_present") or 0) < threshold:
            continue
        if best is None or float(item["score"]) > float(best["score"]):
            best = item
    return best


def _single_row_base(row: dict, routing_primary: str,
                     routing_secondary: tuple[str, ...], params: dict) -> float:
    """单行基础分（不含 RRF / 多 pass 加项）：簇代表选择的确定性依据。"""
    stage1_bonus = _stage1_bonus(row, routing_primary, routing_secondary, params)
    rec_exact = 0.0
    if bool(row.get("is_rec")) and _as_float(
            row.get("raw_sim")) >= _as_float(params["rec_exact_sim"]):
        rec_exact = _as_float(params["rec_exact_bonus"])
    sim_bonus = _as_float(params["rec_sim_weight"]) * _as_float(
        row.get("raw_sim"))
    prior_bonus = _as_float(row.get("prior")) / max(
        1e-9, _as_float(params["prior_divisor"]))
    return float(stage1_bonus + rec_exact + sim_bonus + prior_bonus)


def fuse_multi_sample_top5(
    pass_top5_lists: list[list[dict]],
    submittable_by_key: dict[str, dict] | None,
    stage1_routing: dict | None = None,
    params: dict | None = None,
    target_slots: int = 5,
    pass_eligible_keys: list[set[str] | None] | None = None,
) -> tuple[list[dict], dict]:
    """多采样 RRF + Stage-1 共识融合（零放宽、零删池、确定性）。

    参数
    ----
    ``pass_top5_lists``：
        每 pass 一个**已校准** top-5 列表（``calibrate_submittable_ranking``
        产出的 candidate dict；元素须含 ``src``，推荐含 ``cls``/
        ``raw_sim``/``prior``/``is_rec``/``is_novel``/``cb``/``eff_rk``）。
        空列表/``None`` 项被忽略。**pass 0 = 主采样**（强锚点保护的参照）。
    ``submittable_by_key``：
        ``src -> candidate dict`` 的**全部合法候选**索引（来自同一
        ``calibrate_submittable_ranking`` 内部构建的 submittable 全集）。
        融合位次不足 ``target_slots`` 时按既有 ``eff_rk`` 确定性补位，
        不新增候选。
    ``stage1_routing``：
        ``{"primary_class": ..., "secondary_class"/"secondary_classes": ...}``；
        无效/缺失 ⇒ 无类加分（不猜类别）。
    ``params``：默认 ``CONSENSUS_DEFAULT_PARAMS`` + 覆盖。
    ``target_slots``：返回条数上限（默认 5，零删除语义只对**池**成立：
        融合列表只是位次，不把未入选候选从池里删掉）。
    ``pass_eligible_keys``（v1.4 T14-4，默认 ``None``）：
        与 ``pass_top5_lists`` **1:1** 对齐的每 pass 资格键集合；某项
        ``None`` = 该 pass 无资格信息。**只有非 None 才消费**（默认零
        漂移）：池候选的 RRF 总分乘资格率因子
        ``(n_pool_passes+alpha)/(n_elig+alpha)``（``elig_norm_min_elig``
        <= ``n_elig`` < ``n_pool_passes`` 时），并启用资格感知全票锁
        （``protect_top1_unanimous_eligible``）与可选 Stage-1 尊重
        （``unanimous_respect_stage1``）。

    返回 ``(fused_rows[:target_slots], note)``；``note`` 为可解释机读记录
    （公式/参数/路由/逐行分数分解/保护触发/补位来源），不含 SMILES。
    """
    p = consensus_params(params)
    routing_primary, routing_secondary = routing_classes(stage1_routing)
    slots = max(0, int(target_slots))
    equiv_mode = _equiv_cluster_mode(p)
    rows_by_key: dict[str, dict] = {
        str(key): dict(value)
        for key, value in (submittable_by_key or {}).items()
        if str(key)}

    ordered_passes: list[list[dict]] = []
    ordered_elig: list[set[str] | None] = []
    for raw_idx, raw_pass in enumerate(pass_top5_lists or []):
        current: list[dict] = []
        seen_in_pass: set[str] = set()
        for row in (raw_pass or []):
            if not isinstance(row, dict):
                continue
            key = _candidate_key(row)
            if not key or key in seen_in_pass:
                continue
            seen_in_pass.add(key)
            current.append(row)
        if current:
            ordered_passes.append(current)
            if pass_eligible_keys is not None:
                # 与 ordered_passes 同序（按**原始** pass 索引取资格集；
                # 空 pass 不进融合 ⇒ 也不进资格对齐）。
                eligible = (pass_eligible_keys[raw_idx]
                            if raw_idx < len(pass_eligible_keys) else None)
                ordered_elig.append(
                    None if eligible is None else {str(k) for k in eligible})

    note: dict[str, Any] = {
        "version": CONSENSUS_VERSION,
        "enabled": True,
        "formula": CONSENSUS_FORMULA,
        "params": {k: p[k] for k in sorted(p)},
        "stage1_routing": {
            "primary_class": routing_primary or None,
            "secondary_classes": list(routing_secondary),
            "used": bool(routing_primary or routing_secondary),
        },
        "n_passes": len(ordered_passes),
        "n_submittable": len(rows_by_key),
        "protections": [],
        "rows": [],
        "fused_keys": [],
        "filled_from_submittable": [],
        "skipped": "",
        # v1.4 T14-1A：等价簇模式披露（"none" 时 equiv_clusters 恒为空）。
        "equiv_cluster_mode": equiv_mode,
        "equiv_clusters": [],
    }
    # ---- v1.4 T14-4：跨池资格率归一化（pass_eligible_keys=None ⇒ 零漂移）--
    v3_enabled = bool(p.get("multipass_consensus_v3", False))
    n_passes_total = len(ordered_passes)
    if v3_enabled:
        note["consensus_v3"] = {
            "enabled": True,
            "n_passes_total": int(n_passes_total),
            "rrf_n2_scale": round(
                2.0 / float(n_passes_total), 6) if n_passes_total >= 2 else 1.0,
        }
    elig_enabled = pass_eligible_keys is not None
    non_empty_pool_passes: list[int] = []
    n_pool_passes = 0
    if elig_enabled:
        non_empty_pool_passes = [
            idx for idx, ek in enumerate(ordered_elig)
            if ek is None or len(ek) > 0]
        n_pool_passes = len(non_empty_pool_passes)
        note["elig_norm"] = {
            "enabled": True,
            "formula": (
                "pool_candidate rrf *= (n_pool_passes + alpha) / "
                "(n_elig + alpha) when min_elig <= n_elig < n_pool_passes"),
            "alpha": round(max(0.0, _as_float(p.get("elig_norm_alpha"))), 6),
            "min_elig": int(_as_float(p.get("elig_norm_min_elig")) or 2),
            "n_pool_passes": int(n_pool_passes),
            "pass_eligible_sizes": [
                (None if ek is None else len(ek)) for ek in ordered_elig],
        }
    if slots == 0:
        note["skipped"] = "target_slots_zero"
        return [], note
    if not ordered_passes and not rows_by_key:
        note["skipped"] = "no_candidates"
        return [], note

    if equiv_mode != "none":
        return _fuse_equiv_cluster_top5(
            p=p, slots=slots, rows_by_key=rows_by_key,
            ordered_passes=ordered_passes,
            routing_primary=routing_primary,
            routing_secondary=routing_secondary,
            equiv_mode=equiv_mode, note=note,
            ordered_elig=ordered_elig,
            non_empty_pool_passes=non_empty_pool_passes,
            n_pool_passes=n_pool_passes,
            elig_enabled=elig_enabled)

    pool_max_raw_sim = _pool_max_raw_sim(rows_by_key, ordered_passes)

    # ---- 汇聚：每候选的 pass 位次 / 出现次数 / 代表行 ----
    ranks_by_key: dict[str, dict[int, int]] = {}
    order_first_seen: dict[str, int] = {}
    example_by_key: dict[str, dict] = {}
    seen_counter = 0
    for pass_idx, current in enumerate(ordered_passes):
        for rank, row in enumerate(current):
            key = _candidate_key(row)
            if key not in ranks_by_key:
                ranks_by_key[key] = {}
                order_first_seen[key] = seen_counter
                seen_counter += 1
                example_by_key[key] = dict(row)
            ranks_by_key[key].setdefault(pass_idx, rank)

    pass0_keys = ([_candidate_key(r) for r in ordered_passes[0]]
                  if ordered_passes else [])
    pass0_pos = {key: idx for idx, key in enumerate(pass0_keys)}

    def _row_for(key: str) -> dict:
        base = dict(rows_by_key.get(key) or example_by_key.get(key) or {})
        if not base:
            base = dict(example_by_key.get(key) or {})
        base.setdefault("src", key)
        return base

    scored: list[dict[str, Any]] = []
    for key, ranks in ranks_by_key.items():
        row = _row_for(key)
        rrf_raw = _pass_rrf_contrib(ranks, _as_float(p["rrf_k"]))
        elig_factor = 1.0
        elig_indices: list[int] | None = None
        if elig_enabled:
            elig_factor, elig_indices = _elig_norm_factor(
                ranks, ordered_elig=ordered_elig,
                non_empty_pool_passes=non_empty_pool_passes,
                n_pool_passes=n_pool_passes, params=p,
                is_novel=bool(row.get("is_novel")), key=key)
        n_passes = len(ranks)
        top1_votes = sum(1 for rk in ranks.values() if int(rk) == 0)
        rrf, elig_factor, novel_elig_factor = _apply_v3_rrf_scaling(
            rrf_raw,
            elig_factor=elig_factor,
            elig_enabled=elig_enabled,
            is_pure_novel=bool(row.get("is_novel")),
            n_passes_total=n_passes_total,
            n_passes_present=n_passes,
            top1_votes=top1_votes,
            v3_enabled=v3_enabled,
        )
        stage1_bonus = _stage1_bonus(row, routing_primary,
                                     routing_secondary, p)
        rec_exact = 0.0
        if bool(row.get("is_rec")) and _as_float(
                row.get("raw_sim")) >= _as_float(p["rec_exact_sim"]):
            rec_exact = _as_float(p["rec_exact_bonus"])
        multi_bonus = (_as_float(p["multi_pass_bonus"])
                       if n_passes >= 2 else 0.0)
        sim_bonus = _as_float(p["rec_sim_weight"]) * _as_float(
            row.get("raw_sim"))
        prior_bonus = _as_float(row.get("prior")) / max(
            1e-9, _as_float(p["prior_divisor"]))
        low_sim_boost = _novel_low_sim_boost(
            row, pool_max_raw_sim, routing_primary, n_passes, p)
        score = (rrf + multi_bonus + stage1_bonus + rec_exact
                 + sim_bonus + prior_bonus + low_sim_boost)
        scored.append({
            "key": key,
            "row": row,
            "score": float(score),
            "rrf_score": float(rrf),
            "elig_norm_factor": float(elig_factor),
            "novel_elig_factor": float(novel_elig_factor),
            "elig_indices": elig_indices,
            "n_passes_present": int(n_passes),
            "top1_votes": int(top1_votes),
            "pass_ranks": {str(pidx): int(rank)
                           for pidx, rank in sorted(ranks.items())},
            "multi_pass_bonus": float(multi_bonus),
            "stage1_bonus": float(stage1_bonus),
            "rec_exact_bonus": float(rec_exact),
            "sim_bonus": float(sim_bonus),
            "prior_bonus": float(prior_bonus),
            "low_sim_pool_boost": float(low_sim_boost),
        })

    def _break_key(item: dict[str, Any]) -> tuple:
        key = item["key"]
        return (
            -float(item["score"]),
            int(pass0_pos.get(key, 999)),
            int(_as_float(item["row"].get("eff_rk")) or 9999),
            key,
        )

    # ---- 保护 1：全票一致首位 ----
    locked_key = ""
    if ordered_passes and bool(p.get("protect_top1_unanimous")):
        firsts = {_candidate_key(current[0]) for current in ordered_passes
                  if current}
        if len(firsts) == 1:
            locked_key = next(iter(firsts))
            note["protections"].append({
                "kind": "unanimous_top1_locked",
                "src": locked_key,
                "n_passes": len(ordered_passes),
            })

    # ---- 保护 1b（v1.4 T14-4）：资格感知全票锁 ----
    # 全局全票未命中（旧池 pass 根本不含新池候选）时，允许对「在全部
    # 有资格 pass 中均位列第 1 且主池 Pass 0 中合格」的池候选/池簇锁定。
    # 0 in elig_indices + 同一 Pass 0 仅一个 rank==0 ⇒ 至多 1 个。
    if (not locked_key and elig_enabled and ordered_passes
            and bool(p.get("protect_top1_unanimous_eligible", True))):
        min_elig = int(_as_float(p.get("elig_norm_min_elig")) or 2)
        eligible_locks = [
            item for item in scored
            if not bool(item["row"].get("is_novel"))
            and item.get("elig_indices") is not None
            and min_elig <= len(item["elig_indices"]) < n_pool_passes
            and 0 in item["elig_indices"]
            and all(ranks_position == 0
                    for ranks_position in (
                        item["pass_ranks"].get(str(idx))
                        for idx in item["elig_indices"]))]
        if eligible_locks:
            best = sorted(eligible_locks, key=_break_key)[0]
            locked_key = best["key"]
            note["protections"].append({
                "kind": "unanimous_eligible_top1_locked",
                "src": locked_key,
                "n_elig": len(best["elig_indices"]),
                "n_pool_passes": int(n_pool_passes),
                "elig_passes": [int(x) for x in best["elig_indices"]],
            })

    # ---- 保护 2：pass_0 强锚点首 pass 保护 ----
    if not locked_key and ordered_passes:
        anchor_key = _candidate_key(ordered_passes[0][0])
        anchor_row = _row_for(anchor_key) if anchor_key else {}
        if anchor_key and _is_strong_anchor(anchor_row, p):
            candidates = sorted(
                (item for item in scored if item["key"] != anchor_key),
                key=_break_key)
            challenger = candidates[0] if candidates else None
            anchor_item = next(
                (item for item in scored if item["key"] == anchor_key), None)
            if challenger is not None and \
                    float(challenger["score"]) > float(
                        anchor_item["score"] if anchor_item is not None else 0.0):
                anchor_top1 = int(
                    anchor_item["top1_votes"]
                    if anchor_item is not None else 0)
                double_support, by_top1_maj = _can_displace_strong_anchor(
                    challenger_n_passes=int(challenger["n_passes_present"]),
                    challenger_stage1_bonus=float(challenger["stage1_bonus"]),
                    challenger_top1_votes=int(challenger["top1_votes"]),
                    anchor_top1_votes=anchor_top1,
                    v3_enabled=v3_enabled,
                )
                if double_support:
                    prot_entry: dict[str, Any] = {
                        "kind": "strong_anchor_displaced",
                        "src": anchor_key,
                        "by": challenger["key"],
                        "n_passes_present":
                            int(challenger["n_passes_present"]),
                        "stage1_bonus": float(challenger["stage1_bonus"]),
                    }
                    if by_top1_maj:
                        prot_entry["top1_majority_override"] = True
                        prot_entry["challenger_top1_votes"] = int(
                            challenger["top1_votes"])
                        prot_entry["anchor_top1_votes"] = int(anchor_top1)
                    note["protections"].append(prot_entry)
                else:
                    locked_key = anchor_key
                    note["protections"].append({
                        "kind": "strong_anchor_protected",
                        "src": anchor_key,
                        "challenger": challenger["key"],
                        "challenger_n_passes_present":
                            int(challenger["n_passes_present"]),
                        "challenger_stage1_bonus":
                            float(challenger["stage1_bonus"]),
                    })

    # ---- v1.4 T14-4：全票锁的 Stage-1 尊重（默认 False ⇒ 零漂移）----
    if locked_key and bool(p.get("unanimous_respect_stage1")):
        locked_item = next((item for item in scored
                            if item["key"] == locked_key), None)
        override = _stage1_override_candidate(
            sorted(scored, key=_break_key), locked_item,
            len(ordered_passes))
        if override is not None:
            note["protections"].append({
                "kind": "unanimous_stage1_override",
                "src": locked_key,
                "by": override["key"],
                "n_passes_present": int(
                    override["n_passes_present"]),
                "stage1_bonus": float(override["stage1_bonus"]),
            })
            locked_key = ""

    ordered = [item for item in sorted(scored, key=_break_key)
               if item["key"] != locked_key]
    if locked_key:
        locked_item = next((item for item in scored
                            if item["key"] == locked_key), None)
        if locked_item is not None:
            ordered = [locked_item] + ordered

    fused_rows: list[dict] = []
    fused_keys: list[str] = []
    for item in ordered:
        if len(fused_rows) >= slots:
            break
        fused_rows.append(dict(item["row"]))
        fused_keys.append(item["key"])

    # ---- 不足槽位：按既有 eff_rk 确定性补位（只补既有合法候选） ----
    if len(fused_rows) < slots:
        for key, row in sorted(
                rows_by_key.items(),
                key=lambda pair: (
                    int(_as_float(pair[1].get("eff_rk")) or 9999), pair[0])):
            if len(fused_rows) >= slots:
                break
            if key in fused_keys:
                continue
            fused_rows.append(dict(row))
            fused_keys.append(key)
            note["filled_from_submittable"].append(key)

    note["rows"] = [
        {
            "src": item["key"],
            "cls": str(item["row"].get("cls") or ""),
            "score": round(float(item["score"]), 6),
            "rrf_score": round(float(item["rrf_score"]), 6),
            "n_passes_present": int(item["n_passes_present"]),
            "pass_ranks": item["pass_ranks"],
            "multi_pass_bonus": round(float(item["multi_pass_bonus"]), 6),
            "stage1_bonus": round(float(item["stage1_bonus"]), 6),
            "rec_exact_bonus": round(float(item["rec_exact_bonus"]), 6),
            "sim_bonus": round(float(item["sim_bonus"]), 6),
            "prior_bonus": round(float(item["prior_bonus"]), 6),
            "low_sim_pool_boost": round(
                float(item.get("low_sim_pool_boost") or 0.0), 6),
            "is_rec": bool(item["row"].get("is_rec")),
            "is_novel": bool(item["row"].get("is_novel")),
            "raw_sim": round(_as_float(item["row"].get("raw_sim")), 6),
            "prior": round(_as_float(item["row"].get("prior")), 6),
            "eff_rk": int(_as_float(item["row"].get("eff_rk")) or 0),
            "first_seen": int(order_first_seen.get(item["key"], 0)),
        }
        for item in sorted(scored, key=_break_key)
    ]
    if elig_enabled:
        # v1.4 T14-4：资格率披露只进 note（不改变分数/键序；默认无该键）。
        for row_note, item in zip(
                note["rows"], sorted(scored, key=_break_key)):
            row_note["elig_norm_factor"] = round(
                float(item.get("elig_norm_factor") or 1.0), 6)
            row_note["n_elig"] = (
                None if item.get("elig_indices") is None
                else int(len(item["elig_indices"])))
    note["fused_keys"] = list(fused_keys)
    return fused_rows[:slots], note


def _fuse_equiv_cluster_top5(
    *,
    p: dict,
    slots: int,
    rows_by_key: dict[str, dict],
    ordered_passes: list[list[dict]],
    routing_primary: str,
    routing_secondary: tuple[str, ...],
    equiv_mode: str,
    note: dict,
    ordered_elig: list[set[str] | None] | None = None,
    non_empty_pool_passes: list[int] | None = None,
    n_pool_passes: int = 0,
    elig_enabled: bool = False,
) -> tuple[list[dict], dict]:
    """v1.4 T14-1A：同产物等价簇合票（只改投票单元，不改候选行）。

    调用前 ``note`` 已由 ``fuse_multi_sample_top5`` 建好基础字段；本函数
    只填 ``rows`` / ``fused_keys`` / ``filled_from_submittable`` /
    ``protections`` / ``equiv_clusters``，并把每个簇的**不透明别名**
    （``cluster-1..n``）写进 ``note``；**绝不**把 ``p_st`` / ``cn`` 身份串
    （含产物 SMILES 片段）写进 note。

    v1.4 T14-4：``elig_enabled`` 为真时按**簇级池成员**做资格率归一化
    （簇内任一池成员命中该 pass 资格即视为该 pass 有资格）；失败/无池
    成员的簇（纯 novel 簇）不参与放大。默认 ``False`` ⇒ 零漂移。
    """
    note["equiv_version"] = CONSENSUS_EQUIV_VERSION
    note["dedup_equiv_in_top5"] = bool(p.get("dedup_equiv_in_top5", True))
    dedup = bool(p.get("dedup_equiv_in_top5", True))
    pool_max_raw_sim = _pool_max_raw_sim(rows_by_key, ordered_passes)
    elig_norm_on = bool(elig_enabled)
    elig_aligned: list[set[str] | None] = (
        list(ordered_elig) if elig_norm_on else [])
    pool_passes: list[int] = (
        list(non_empty_pool_passes or []) if elig_norm_on else [])
    n_pool_total = int(n_pool_passes) if elig_norm_on else 0

    example_by_key: dict[str, dict] = {}
    for current in ordered_passes:
        for row in current:
            key = _candidate_key(row)
            if key and key not in example_by_key:
                example_by_key[key] = dict(row)

    def _row_for(key: str) -> dict:
        base = dict(rows_by_key.get(key) or example_by_key.get(key) or {})
        base.setdefault("src", key)
        return base

    pass0_keys = ([_candidate_key(r) for r in ordered_passes[0]]
                  if ordered_passes else [])
    pass0_pos = {key: idx for idx, key in enumerate(pass0_keys)}

    # ---- 每 pass 内的簇最小位次（单 pass 不重复刷票）----
    cluster_order: list[str] = []
    cluster_pass_rank: dict[str, dict[int, int]] = {}
    cluster_members: dict[str, list[str]] = {}
    cluster_first_seen: dict[str, int] = {}
    # v1.4 T14-4：簇内**池**成员键（novel 成员不计入资格判定）。
    cluster_pool_keys: dict[str, set[str]] = {}
    seen_counter = 0
    for pass_idx, current in enumerate(ordered_passes):
        for rank, row in enumerate(current):
            key = _candidate_key(row)
            cid = _cluster_identity(row, equiv_mode) or f"src:{key}"
            if cid not in cluster_pass_rank:
                cluster_order.append(cid)
                cluster_pass_rank[cid] = {}
                cluster_members[cid] = []
                cluster_first_seen[cid] = seen_counter
                cluster_pool_keys[cid] = set()
            seen_counter += 1
            # 同一 pass 内同簇多行 ⇒ 只记**最小 rank**（列表顺序即便是
            # 非 rank 序也不刷票）。
            prev_rank = cluster_pass_rank[cid].get(pass_idx)
            if prev_rank is None or int(rank) < int(prev_rank):
                cluster_pass_rank[cid][pass_idx] = int(rank)
            members = cluster_members[cid]
            if key and key not in members:
                members.append(key)
            if key and not bool(row.get("is_novel")):
                cluster_pool_keys[cid].add(key)
    # 不透明别名（对外披露面；簇身份串可能含产物 SMILES 片段）
    alias_by_cluster = {
        cid: f"cluster-{idx + 1}" for idx, cid in enumerate(cluster_order)}

    def _member_sort_key(key: str) -> tuple:
        row = _row_for(key)
        return (
            -_single_row_base(row, routing_primary, routing_secondary, p),
            0 if not bool(row.get("is_novel")) else 1,
            int(pass0_pos.get(key, 999)),
            int(_as_float(row.get("eff_rk")) or 9999),
            key,
        )

    def _representative(cid: str) -> str:
        members = cluster_members.get(cid) or []
        if not members:
            return ""
        return min(members, key=_member_sort_key)

    v3_enabled = bool(p.get("multipass_consensus_v3", False))
    n_passes_total = len(ordered_passes)

    def _cluster_score(cid: str) -> dict[str, Any]:
        rep = _representative(cid)
        row = _row_for(rep)
        ranks = cluster_pass_rank.get(cid) or {}
        rrf_raw = _pass_rrf_contrib(ranks, _as_float(p["rrf_k"]))
        elig_factor = 1.0
        elig_indices: list[int] | None = None
        pool_keys = cluster_pool_keys.get(cid) or set()
        if elig_norm_on:
            # 纯 novel 簇（无池成员）不参与跨池资格率放大。
            if pool_keys:
                elig_factor, elig_indices = _elig_norm_factor(
                    ranks, ordered_elig=elig_aligned,
                    non_empty_pool_passes=pool_passes,
                    n_pool_passes=n_pool_total, params=p,
                    is_novel=False, cluster_keys=pool_keys)
        n_passes = len(ranks)
        top1_votes = sum(1 for rk in ranks.values() if int(rk) == 0)
        rrf, elig_factor, novel_elig_factor = _apply_v3_rrf_scaling(
            rrf_raw,
            elig_factor=elig_factor,
            elig_enabled=elig_norm_on,
            is_pure_novel=(not bool(pool_keys)) and bool(row.get("is_novel")),
            n_passes_total=n_passes_total,
            n_passes_present=n_passes,
            top1_votes=top1_votes,
            v3_enabled=v3_enabled,
        )
        stage1_bonus = _stage1_bonus(row, routing_primary,
                                     routing_secondary, p)
        rec_exact = 0.0
        if bool(row.get("is_rec")) and _as_float(
                row.get("raw_sim")) >= _as_float(p["rec_exact_sim"]):
            rec_exact = _as_float(p["rec_exact_bonus"])
        multi_bonus = (_as_float(p["multi_pass_bonus"])
                       if n_passes >= 2 else 0.0)
        sim_bonus = _as_float(p["rec_sim_weight"]) * _as_float(
            row.get("raw_sim"))
        prior_bonus = _as_float(row.get("prior")) / max(
            1e-9, _as_float(p["prior_divisor"]))
        low_sim_boost = _novel_low_sim_boost(
            row, pool_max_raw_sim, routing_primary, n_passes, p)
        score = (rrf + multi_bonus + stage1_bonus + rec_exact
                 + sim_bonus + prior_bonus + low_sim_boost)
        return {
            "cluster": cid,
            "representative": rep,
            "row": row,
            "score": float(score),
            "rrf_score": float(rrf),
            "elig_norm_factor": float(elig_factor),
            "novel_elig_factor": float(novel_elig_factor),
            "elig_indices": elig_indices,
            "n_passes_present": int(n_passes),
            "top1_votes": int(top1_votes),
            "pass_ranks": {str(pidx): int(rank)
                           for pidx, rank in sorted(ranks.items())},
            "multi_pass_bonus": float(multi_bonus),
            "stage1_bonus": float(stage1_bonus),
            "rec_exact_bonus": float(rec_exact),
            "sim_bonus": float(sim_bonus),
            "prior_bonus": float(prior_bonus),
            "low_sim_pool_boost": float(low_sim_boost),
        }

    scored: dict[str, dict[str, Any]] = {
        cid: _cluster_score(cid) for cid in cluster_order}

    def _break_key(cid: str) -> tuple:
        item = scored[cid]
        member_positions = [
            pass0_pos[key] for key in cluster_members.get(cid) or []
            if key in pass0_pos]
        return (
            -float(item["score"]),
            min(member_positions, default=999),
            int(_as_float(item["row"].get("eff_rk")) or 9999),
            str(item["representative"]),
        )

    # ---- 保护 1（簇级）：全票一致首位 ----
    locked_cluster = ""
    if ordered_passes and bool(p.get("protect_top1_unanimous")):
        firsts = {
            _cluster_identity(current[0], equiv_mode)
            or f"src:{_candidate_key(current[0])}"
            for current in ordered_passes if current}
        if len(firsts) == 1:
            cid = next(iter(firsts))
            if cid in scored:
                locked_cluster = cid
                note["protections"].append({
                    "kind": "unanimous_top1_locked",
                    "src": scored[cid]["representative"],
                    "cluster": alias_by_cluster.get(cid, ""),
                    "n_passes": len(ordered_passes),
                    "equiv_cluster": True,
                })

    # ---- 保护 1b（v1.4 T14-4，簇级）：资格感知全票锁 ----
    if (not locked_cluster and elig_norm_on and ordered_passes
            and bool(p.get("protect_top1_unanimous_eligible", True))):
        min_elig = int(_as_float(p.get("elig_norm_min_elig")) or 2)
        eligible_locks = [
            cid for cid in cluster_order
            if (cluster_pool_keys.get(cid) or set())
            and scored[cid].get("elig_indices") is not None
            and min_elig <= len(scored[cid]["elig_indices"]) < n_pool_total
            and 0 in scored[cid]["elig_indices"]
            and all(scored[cid]["pass_ranks"].get(str(idx)) == 0
                    for idx in scored[cid]["elig_indices"])]
        if eligible_locks:
            best = sorted(eligible_locks, key=_break_key)[0]
            locked_cluster = best
            note["protections"].append({
                "kind": "unanimous_eligible_top1_locked",
                "src": scored[best]["representative"],
                "cluster": alias_by_cluster.get(best, ""),
                "n_elig": len(scored[best]["elig_indices"]),
                "n_pool_passes": int(n_pool_total),
                "elig_passes": [int(x) for x in scored[best]["elig_indices"]],
                "equiv_cluster": True,
            })

    # ---- 保护 2（簇级）：pass_0 强锚点首 pass 保护 ----
    if not locked_cluster and ordered_passes:
        anchor_key = _candidate_key(ordered_passes[0][0])
        anchor_cid = (_cluster_identity(ordered_passes[0][0], equiv_mode)
                      or f"src:{anchor_key}")
        if anchor_cid in scored:
            anchor_row = scored[anchor_cid]["row"]
            if _is_strong_anchor(anchor_row, p):
                challengers = sorted(
                    (cid for cid in cluster_order if cid != anchor_cid),
                    key=_break_key)
                challenger = challengers[0] if challengers else None
                if challenger is not None and float(
                        scored[challenger]["score"]) > float(
                            scored[anchor_cid]["score"]):
                    double_support, by_top1_maj = _can_displace_strong_anchor(
                        challenger_n_passes=int(
                            scored[challenger]["n_passes_present"]),
                        challenger_stage1_bonus=float(
                            scored[challenger]["stage1_bonus"]),
                        challenger_top1_votes=int(
                            scored[challenger]["top1_votes"]),
                        anchor_top1_votes=int(
                            scored[anchor_cid]["top1_votes"]),
                        v3_enabled=v3_enabled,
                    )
                    if double_support:
                        prot_entry = {
                            "kind": "strong_anchor_displaced",
                            "src": scored[anchor_cid]["representative"],
                            "by": scored[challenger]["representative"],
                            "cluster": alias_by_cluster.get(anchor_cid, ""),
                            "n_passes_present": int(
                                scored[challenger]["n_passes_present"]),
                            "stage1_bonus": float(
                                scored[challenger]["stage1_bonus"]),
                            "equiv_cluster": True,
                        }
                        if by_top1_maj:
                            prot_entry["top1_majority_override"] = True
                            prot_entry["challenger_top1_votes"] = int(
                                scored[challenger]["top1_votes"])
                            prot_entry["anchor_top1_votes"] = int(
                                scored[anchor_cid]["top1_votes"])
                        note["protections"].append(prot_entry)
                    else:
                        locked_cluster = anchor_cid
                        note["protections"].append({
                            "kind": "strong_anchor_protected",
                            "src": scored[anchor_cid]["representative"],
                            "challenger": scored[challenger][
                                "representative"],
                            "cluster": alias_by_cluster.get(anchor_cid, ""),
                            "challenger_n_passes_present": int(
                                scored[challenger]["n_passes_present"]),
                            "challenger_stage1_bonus": float(
                                scored[challenger]["stage1_bonus"]),
                            "equiv_cluster": True,
                        })

    # ---- v1.4 T14-4（簇级）：资格感知全票锁的 Stage-1 尊重 ----
    if locked_cluster and elig_norm_on and bool(
            p.get("unanimous_respect_stage1")):
        override = _stage1_override_candidate(
            [scored[cid] for cid in sorted(cluster_order, key=_break_key)],
            scored.get(locked_cluster), len(ordered_passes))
        if override is not None:
            note["protections"].append({
                "kind": "unanimous_stage1_override",
                "src": scored[locked_cluster]["representative"],
                "by": override["representative"],
                "cluster": alias_by_cluster.get(locked_cluster, ""),
                "n_passes_present": int(override["n_passes_present"]),
                "stage1_bonus": float(override["stage1_bonus"]),
                "equiv_cluster": True,
            })
            locked_cluster = ""

    ordered_clusters = [cid for cid in sorted(cluster_order, key=_break_key)
                        if cid != locked_cluster]
    if locked_cluster:
        ordered_clusters = [locked_cluster] + ordered_clusters

    fused_rows: list[dict] = []
    fused_keys: list[str] = []
    emitted_clusters: set[str] = set()
    for cid in ordered_clusters:
        if len(fused_rows) >= slots:
            break
        rep = _representative(cid)
        if not rep:
            continue
        fused_rows.append(dict(_row_for(rep)))
        fused_keys.append(rep)
        emitted_clusters.add(cid)
        if dedup:
            continue
        # dedup 关闭时，同簇其余成员按单行基础分确定性继续占用槽位。
        others = sorted(
            (key for key in cluster_members.get(cid) or [] if key != rep),
            key=_member_sort_key)
        for key in others:
            if len(fused_rows) >= slots:
                break
            fused_rows.append(dict(_row_for(key)))
            fused_keys.append(key)

    # ---- 不足槽位：按既有 eff_rk 确定性补位（只补既有合法候选） ----
    if len(fused_rows) < slots:
        for key, row in sorted(
                rows_by_key.items(),
                key=lambda pair: (
                    int(_as_float(pair[1].get("eff_rk")) or 9999), pair[0])):
            if len(fused_rows) >= slots:
                break
            if key in fused_keys:
                continue
            if dedup:
                cid = (_cluster_identity(row, equiv_mode) or f"src:{key}")
                if cid in emitted_clusters:
                    continue
            fused_rows.append(dict(row))
            fused_keys.append(key)
            note["filled_from_submittable"].append(key)

    note["equiv_clusters"] = [
        {
            "cluster": alias_by_cluster.get(cid, ""),
            "representative": str(scored[cid]["representative"]),
            "n_members": len(cluster_members.get(cid) or []),
            "member_srcs": list(cluster_members.get(cid) or []),
            "n_passes_present": int(scored[cid]["n_passes_present"]),
            "score": round(float(scored[cid]["score"]), 6),
        }
        for cid in sorted(cluster_order, key=_break_key)
    ]
    note["rows"] = [
        {
            "src": str(scored[cid]["representative"]),
            "cluster": alias_by_cluster.get(cid, ""),
            "n_members": len(cluster_members.get(cid) or []),
            "cls": str(scored[cid]["row"].get("cls") or ""),
            "score": round(float(scored[cid]["score"]), 6),
            "rrf_score": round(float(scored[cid]["rrf_score"]), 6),
            "n_passes_present": int(scored[cid]["n_passes_present"]),
            "pass_ranks": scored[cid]["pass_ranks"],
            "multi_pass_bonus": round(
                float(scored[cid]["multi_pass_bonus"]), 6),
            "stage1_bonus": round(float(scored[cid]["stage1_bonus"]), 6),
            "rec_exact_bonus": round(
                float(scored[cid]["rec_exact_bonus"]), 6),
            "sim_bonus": round(float(scored[cid]["sim_bonus"]), 6),
            "prior_bonus": round(float(scored[cid]["prior_bonus"]), 6),
            "low_sim_pool_boost": round(
                float(scored[cid]["low_sim_pool_boost"]), 6),
            "is_rec": bool(scored[cid]["row"].get("is_rec")),
            "is_novel": bool(scored[cid]["row"].get("is_novel")),
            "raw_sim": round(_as_float(
                scored[cid]["row"].get("raw_sim")), 6),
            "prior": round(_as_float(scored[cid]["row"].get("prior")), 6),
            "eff_rk": int(
                _as_float(scored[cid]["row"].get("eff_rk")) or 0),
            "first_seen": int(cluster_first_seen.get(cid, 0)),
        }
        for cid in sorted(cluster_order, key=_break_key)
    ]
    if elig_norm_on:
        # v1.4 T14-4：资格率披露只进 note（不改变分数/键序；默认无该键）。
        # note["rows"] 与下式同一排序 ⇒ 逐项 zip 对齐。
        for row_note, cid in zip(note["rows"],
                                 sorted(cluster_order, key=_break_key)):
            row_note["elig_norm_factor"] = round(
                float(scored[cid].get("elig_norm_factor") or 1.0), 6)
            row_note["n_elig"] = (
                None if scored[cid].get("elig_indices") is None
                else int(len(scored[cid]["elig_indices"])))
    note["fused_keys"] = list(fused_keys)
    return fused_rows[:slots], note
