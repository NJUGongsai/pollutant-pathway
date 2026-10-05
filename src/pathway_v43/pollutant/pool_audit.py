"""候选池处理审计 — 阶段可重放(实施书 §7.3/§17.2,S2)。

- 记录**实际发生**的阶段,不伪造统一顺序:
  retrieved_raw → typed_and_grouped → structure_screened →
  finite_rule_preview → deduped → ordered → bounded → injected_to_model;
- 每阶段保存 input/output hash、计数、逐项处置码、来源分布、排序键
  版本、字符/token 预算和截断原因;
- 输入侧 preview(input_preview_policy)只有 off | diagnostic 两档,
  **进策略身份**:
  * off:记录该检查未执行及原因,不冒称"已做 G2";
  * diagnostic:只附有限规则诊断(复用冻结 conservation_filter_and_rank),
    不根据其结果改写候选池成员、档位或原顺序(不消费其筛选/排序
    结果;G2 的 unclassified 是覆盖未知,不新增惩罚);
- 首版新池排序:稳定原检索位次,来源/假设 ID tie-break
  (PPV1_POOL_ORDER_VERSION);未经验证的分数不跨来源解释为概率;
- bounded 截断后的有限池可以不覆盖全检索池,必须诚实报告(截断数量、
  来源分布、原因)。

injected_to_model 阶段在 S3 才有真实模型任务;S2 只提供阶段记录
结构与占位断言(未实施注入时显式记录 not_applicable)。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import canonical_json, content_hash
from ..validation.conservation import conservation_filter_and_rank
from .profile import (
    INPUT_PREVIEW_DIAGNOSTIC,
    INPUT_PREVIEW_OFF,
    PPV1_INPUT_PREVIEW_VERSION,
    PPV1_POOL_AUDIT_SCHEMA_VERSION,
    PPV1_POOL_ORDER_VERSION,
)

POOL_STAGE_RETRIEVED_RAW = "retrieved_raw"
POOL_STAGE_TYPED_AND_GROUPED = "typed_and_grouped"
POOL_STAGE_STRUCTURE_SCREENED = "structure_screened"
POOL_STAGE_FINITE_RULE_PREVIEW = "finite_rule_preview"
POOL_STAGE_DEDUPLICATED = "deduped"
POOL_STAGE_ORDERED = "ordered"
POOL_STAGE_BOUNDED = "bounded"
POOL_STAGE_INJECTED_TO_MODEL = "injected_to_model"
POOL_STAGES = (
    POOL_STAGE_RETRIEVED_RAW, POOL_STAGE_TYPED_AND_GROUPED,
    POOL_STAGE_STRUCTURE_SCREENED, POOL_STAGE_FINITE_RULE_PREVIEW,
    POOL_STAGE_DEDUPLICATED, POOL_STAGE_ORDERED, POOL_STAGE_BOUNDED,
    POOL_STAGE_INJECTED_TO_MODEL,
)


@dataclass
class PoolStageTrace:
    """单阶段记录(§7.3:hash/计数/处置/来源分布/排序键/预算/截断)。

    from_previous(v2/P2-5):False = 本阶段输入**不是**上一已执行阶段的
    原样输出(阶段跳过/显式注入/外部改写),必须在 transition_reason
    登记原因;True 时相邻阶段的 hash 连续性由 build_pool_audit 校验。
    """

    stage: str
    input_hash: str
    output_hash: str
    n_input: int
    n_output: int
    item_dispositions: list[dict]     # [{id, disposition_code, note}]
    source_origin_distribution: dict  # source_origin → count
    order_key_version: str = ""
    char_budget: int | None = None
    token_budget: int | None = None
    truncation_reason: str = ""
    from_previous: bool = True
    transition_reason: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class PoolAuditRecord:
    """一个父节点候选池的完整处理审计(阶段序列 + preview 状态)。"""

    run_id: str
    path_id: str
    stages: list[PoolStageTrace] = field(default_factory=list)
    input_preview_policy: str = INPUT_PREVIEW_OFF
    input_preview_version: str = PPV1_INPUT_PREVIEW_VERSION
    input_preview: dict = field(default_factory=dict)
    schema_version: str = PPV1_POOL_AUDIT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "path_id": self.path_id,
            "stages": [s.to_dict() for s in self.stages],
            "input_preview_policy": self.input_preview_policy,
            "input_preview_version": self.input_preview_version,
            "input_preview": dict(self.input_preview),
        }


class PoolAuditError(RuntimeError):
    """池审计契约违反(阶段顺序/内容一致性;fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _source_origin_distribution(items: list[dict]) -> dict:
    out: dict[str, int] = {}
    for it in items:
        origin = str(it.get("source_origin", "unknown"))
        out[origin] = out.get(origin, 0) + 1
    return out


def record_pool_stage(
    *,
    stage: str,
    input_items: list[dict],
    output_items: list[dict],
    item_dispositions: list[dict] | None = None,
    order_key_version: str = "",
    char_budget: int | None = None,
    token_budget: int | None = None,
    truncation_reason: str = "",
    from_previous: bool = True,
    transition_reason: str = "",
) -> PoolStageTrace:
    """单阶段落账(纯记录;hash 由内容派生,可重放核对)。"""
    if stage not in POOL_STAGES:
        raise PoolAuditError(
            f"未知池阶段:{stage!r}(允许顺序 {list(POOL_STAGES)})",
            {"stage": stage})
    return PoolStageTrace(
        stage=stage,
        input_hash=content_hash(input_items),
        output_hash=content_hash(output_items),
        n_input=len(input_items),
        n_output=len(output_items),
        item_dispositions=[dict(d) for d in item_dispositions or []],
        source_origin_distribution=_source_origin_distribution(output_items),
        order_key_version=order_key_version,
        char_budget=char_budget,
        token_budget=token_budget,
        truncation_reason=truncation_reason,
        from_previous=from_previous,
        transition_reason=transition_reason,
    )


def build_pool_audit(
    *,
    run_id: str,
    path_id: str,
    stages: list[PoolStageTrace],
    input_preview_policy: str,
    input_preview: dict | None = None,
) -> PoolAuditRecord:
    """组装池审计(阶段顺序 + **相邻阶段哈希链**校验,P2-5)。

    - off 且未附诊断块:自动记录 {"status": "not_run", ...}(不冒称
      已做 G2);diagnostic 必须传入实际诊断块(缺失 fail-closed);
    - 相邻已执行阶段:后一阶段 input_hash 必须等于前一阶段
      output_hash(前一输出 a、下一输入 b 的拼接不能再生成审计);
    - 阶段跳过/显式注入:该阶段 from_previous=False 且 transition_reason
      必填,hash 连续性豁免但转换留痕。
    """
    seen = [s.stage for s in stages]
    expected = list(POOL_STAGES)
    filtered = [s for s in expected if s in seen]
    if seen != filtered:
        raise PoolAuditError(
            f"池阶段顺序非法:{seen}(须为 §7.3 声明顺序的子序列)",
            {"stages": seen})
    if input_preview_policy not in (INPUT_PREVIEW_OFF,
                                    INPUT_PREVIEW_DIAGNOSTIC):
        raise PoolAuditError(
            f"input_preview_policy 非法:{input_preview_policy!r}",
            {"input_preview_policy": input_preview_policy})
    for prev, nxt in zip(stages, stages[1:]):
        adjacent_in_protocol = (
            expected.index(nxt.stage) == expected.index(prev.stage) + 1)
        if not nxt.from_previous:
            if not nxt.transition_reason:
                raise PoolAuditError(
                    f"阶段 {nxt.stage} 声明输入非前阶段原样输出,但未登记 "
                    "transition_reason(阶段跳过/显式注入必须留痕)",
                    {"stage": nxt.stage})
            continue
        if adjacent_in_protocol and nxt.input_hash != prev.output_hash:
            raise PoolAuditError(
                f"相邻阶段哈希链断裂:{prev.stage}→{nxt.stage}"
                f"(前输出 {prev.output_hash[:12]}…,后输入 "
                f"{nxt.input_hash[:12]}…;拼接审计不合法,跳过/注入须"
                "显式登记 from_previous=False + transition_reason)",
                {"prev_stage": prev.stage, "next_stage": nxt.stage})
    if input_preview_policy == INPUT_PREVIEW_OFF:
        block = input_preview or {
            "policy": INPUT_PREVIEW_OFF, "status": "not_run",
            "reason": "input_preview_policy_off",
            "version": PPV1_INPUT_PREVIEW_VERSION,
        }
    else:
        if not input_preview:
            raise PoolAuditError(
                "input_preview_policy=diagnostic 必须附诊断块(缺失即"
                "fail-closed,不静默当 off)")
        block = input_preview
    return PoolAuditRecord(
        run_id=run_id, path_id=path_id, stages=list(stages),
        input_preview_policy=input_preview_policy,
        input_preview=block,
    )


def run_input_preview(
    *,
    substrate_smiles: str,
    candidates: list[dict],
    surface_text: str = "",
    policy: str = INPUT_PREVIEW_OFF,
) -> dict:
    """输入侧有限规则 preview(§17.2:off | diagnostic,不改池)。

    - off:{"status": "not_run", "reason": "input_preview_policy_off"} —— 
      记录未执行与原因,不冒称"已做 G2";
    - diagnostic:调用冻结 conservation_filter_and_rank(与输出侧同函数
      同参数形状),**只取诊断**:逐候选 tier/g3b/拒因随诊断块返回;
      excluded/ranked 的**筛选与排序结果不被消费** —— 返回的
      pool_unchanged=True 且原始候选顺序/成员不变;
    - G2 的 unclassified 是覆盖未知:诊断如实转记,不新增惩罚。
    """
    if policy == INPUT_PREVIEW_OFF:
        return {
            "policy": INPUT_PREVIEW_OFF,
            "status": "not_run",
            "reason": "input_preview_policy_off",
            "version": PPV1_INPUT_PREVIEW_VERSION,
        }
    if policy != INPUT_PREVIEW_DIAGNOSTIC:
        raise PoolAuditError(
            f"input_preview_policy 非法:{policy!r}", {"policy": policy})
    result = conservation_filter_and_rank(
        substrate_smiles=substrate_smiles,
        candidates=[{"smiles": c.get("smiles", ""),
                     "note": c.get("note", "")} for c in candidates],
        surface_text=surface_text)
    env = result.to_dict()
    per_candidate = {}

    def _register(judgment: dict, disposition: str) -> None:
        idx = str(judgment.get("original_position",
                               judgment.get("index", "")))
        per_candidate[idx] = {
            "disposition": disposition,
            "tier": judgment.get("tier", ""),
            "g3b_contradiction": bool(
                (judgment.get("g3b") or {}).get("contradiction")),
            "reasons": list(judgment.get("rules", [])),
        }

    for judgment in env.get("ranked", []):
        _register(judgment, "diagnostic_only")
    for judgment in env.get("excluded", []):
        _register(judgment, "diagnostic_only_excluded_reported")
    return {
        "policy": INPUT_PREVIEW_DIAGNOSTIC,
        "status": ("diagnostic_only" if env.get("status") == "ok"
                   else "hold_reported"),
        "pool_unchanged": True,   # 筛选/排序结果不被消费
        "n_candidates": env.get("n_candidates", 0),
        "versions": env.get("versions", {}),
        "diagnostics": per_candidate,
        "note": ("诊断不改变池成员、档位或原顺序;excluded 项仅被报告,"
                 "不从池中移除(§17.2)"),
        "version": PPV1_INPUT_PREVIEW_VERSION,
    }


def order_pool(
    items: list[dict],
    *,
    limit: int | None = None,
) -> tuple[list[dict], dict]:
    """首版新池排序 + 有界截断(§7.3;P2-5:limit 值域校验)。

    排序键:(retrieval_rank, source_origin, evidence_id/hypothesis_id) ——
    稳定原检索位次,来源/ID tie-break;未经验证的分数不作排序键(不跨
    来源解释为概率)。limit:None = 不限;必须为 ≥0 的整数(负数拒绝,
    不再落进 Python 切片静默保留一部分)。截断披露:n_truncated、
    来源分布、原因。截断后的有限池不覆盖全检索池时,如实报告。
    """
    if limit is not None and (isinstance(limit, bool)
                               or not isinstance(limit, int) or limit < 0):
        raise PoolAuditError(
            f"limit 非法:{limit!r}(None=不限;否则须为 ≥0 的整数)",
            {"limit": limit})

    def key(it: dict):
        rank = it.get("retrieval_rank")
        rank = rank if isinstance(rank, int) else 1 << 30
        return (rank, str(it.get("source_origin", "unknown")),
                str(it.get("evidence_id") or it.get("hypothesis_id") or ""))

    ordered = sorted(items, key=key)
    if limit is None or limit >= len(ordered):
        return ordered, {
            "n_input": len(items), "n_kept": len(ordered),
            "n_truncated": 0, "truncated_source_origins": {},
            "truncation_reason": "",
            "order_key_version": PPV1_POOL_ORDER_VERSION,
            "covers_full_pool": True,
        }
    kept = ordered[:limit]
    truncated = ordered[limit:]
    return kept, {
        "n_input": len(items), "n_kept": len(kept),
        "n_truncated": len(truncated),
        "truncated_source_origins": _source_origin_distribution(truncated),
        "truncation_reason": f"bounded_pool_limit:{limit}",
        "order_key_version": PPV1_POOL_ORDER_VERSION,
        "covers_full_pool": False,
    }


def dedupe_pool(items: list[dict], *, dedupe_key: str) -> tuple[
        list[dict], list[dict]]:
    """池内去重(相同键保留首个;归并仅用于报告去重,§5.4)。

    返回 (保留池, 去重记录[{id, duplicate_of, key}])。反应假设归并
    不能仅凭 CN 对 —— 调用方应传足够强的 dedupe_key(如 evidence_id/
    hypothesis_id),不传 cn。
    """
    if dedupe_key in ("cn", "cn_identity", "product_identity"):
        raise PoolAuditError(
            "去重键不得使用 CN(反应假设归并不能仅凭 CN 对;§5.4)",
            {"dedupe_key": dedupe_key})
    kept: list[dict] = []
    seen: dict = {}
    dup_records: list[dict] = []
    for it in items:
        k = it.get(dedupe_key)
        if k is None:
            kept.append(it)  # 无键项保留(不猜等价)
            continue
        if k in seen:
            dup_records.append({
                "id": str(it.get("evidence_id")
                          or it.get("hypothesis_id") or ""),
                "duplicate_of": str(seen[k]),
                "key": str(k),
            })
            continue
        seen[k] = (it.get("evidence_id")
                   or it.get("hypothesis_id") or "")
        kept.append(it)
    return kept, dup_records


def stage_chain_hashes(stages: list[PoolStageTrace]) -> list[dict]:
    """阶段链完整性视图(上阶段 output_hash 应与下阶段 input 一致性
    由调用方核对;本函数输出原始 hash 序列供审计)。"""
    return [{"stage": s.stage, "input_hash": s.input_hash,
             "output_hash": s.output_hash} for s in stages]
