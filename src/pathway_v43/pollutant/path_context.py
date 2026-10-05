"""PathContext — 路径上下文、条件事实与证据依赖(v2 回修,S2)。

v2(ppv1-context-2 / ppv1-condition-assessment-2 / ppv1-dependency-2,
2026-10-05 回修)相对 v1 的变化(F02/F03/F06):
- **要求按步骤/阶段累积,不覆盖(F02)**:子上下文同键不同要求**双方都
  保留**;评估按全部适用要求的**合取**(任一 conflict → conflict,
  否则任一 unknown → unknown);仅语义完全相同的要求可去重。v1 的
  "同键以假设侧为准"已废除(审核 §6 裁定不接受);
- **事实适用性分场景/阶段/来源(F03)**:上下文持有当前 scenario_ref;
  curated_source 事实仅当 subject_scenario_ref 匹配当前场景才适用
  (历史实验条件=来源场景事实,不自动成为当前事实);phase_id 非空
  的事实只在对应阶段适用;必需物 known_absent ⇒ conflict(未列出 ⇒
  unknown ≠ absent);
- **必要性必须有来源(F03)**:无 source_refs 的 essential 是未核实
  假设 —— 不进门禁(不产生 conflict),但阻止 compatible;
- **值语义分 basis(mimo 4.2 采纳 + Codex 纠偏)**:range(显式区间)/
  point(声明点值)/optimum(最适值,永不产生 conflict,偏离只作
  preference)/label(定性标签,须注册表映射,首版注册表为空 ⇒ unknown,
  禁止现推区间);单数值未声明 basis ⇒ unknown(不自动推为 optimum
  或 range);
- **context_id 冻结全部语义字段(F06)**:事实/要求/假设/依赖/评估
  范围/场景/阶段/转换全部入哈希 —— 不同前提不得共享身份(S3 缓存
  消费的前提);
- **供给环检测为任意长环(F06)**:结构化多边图;环上任一边无来源
  支持即 unresolved_initial_supply(不称化学不可能)。

既有不变量(§6):条件键封闭枚举(首版 7 键);"土壤/污水"不推出氧条件;
观察条件(observed_condition_reference)只作参考不进门禁;preference
只提示;assessed_scope 由聚合派生不继承请求;空要求列表不自动相容;
scenario_transition 须有来源,只影响后续步骤;依赖解决须有来源新
证据并保留轨迹,下游精确匹配不消除上游猜测。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..domain.models import canonical_json, stable_id
from .profile import (
    PPV1_CONDITION_ASSESSMENT_VERSION,
    PPV1_CONTEXT_SCHEMA_VERSION,
    PPV1_DEPENDENCY_SCHEMA_VERSION,
)

PPV1_CONTEXT_SUPPORTED_VERSIONS = ("ppv1-context-2",)

CONDITION_KEY_OXYGEN = "oxygen_regime"
CONDITION_KEY_PH = "pH"
CONDITION_KEY_TEMPERATURE = "temperature_C"
CONDITION_KEY_MATRIX = "matrix"
CONDITION_KEY_ELECTRON_DONOR = "electron_donor"
CONDITION_KEY_ELECTRON_ACCEPTOR = "electron_acceptor"
CONDITION_KEY_GROWTH_SUBSTRATE = "growth_substrate"
CONDITION_KEYS = frozenset({
    CONDITION_KEY_OXYGEN, CONDITION_KEY_PH, CONDITION_KEY_TEMPERATURE,
    CONDITION_KEY_MATRIX, CONDITION_KEY_ELECTRON_DONOR,
    CONDITION_KEY_ELECTRON_ACCEPTOR, CONDITION_KEY_GROWTH_SUBSTRATE,
})

# 区间型条件键(数值/区间语义)
INTERVAL_CONDITION_KEYS = frozenset({CONDITION_KEY_PH,
                                     CONDITION_KEY_TEMPERATURE})
# 物种类键(值=物种引用/枚举;known_absent 有独立语义)
SPECIES_CONDITION_KEYS = frozenset({CONDITION_KEY_ELECTRON_DONOR,
                                    CONDITION_KEY_ELECTRON_ACCEPTOR,
                                    CONDITION_KEY_GROWTH_SUBSTRATE})
OXYGEN_REGIME_VALUES = frozenset({"aerobic", "anaerobic", "facultative"})

# 已登记的 v2 条件键缺口(mimo 4.2(2) + Codex"登记未评估维度"):
# 首版不评估这些维度 ⇒ 相容结论只覆盖已评估维度,不得显示为全维度相容
UNASSESSED_DIMENSIONS = frozenset({
    "biotic_abiotic", "light_regime", "salinity_ionic_strength",
    "redox_regime_eh", "required_trace_elements_cofactors",
    "substrate_concentration", "inoculum_source", "phase_bioavailability",
})

# 定性标签 → 支持区间的注册表(mimo 4.2:标签必须经注册表映射;
# 首版注册表**为空** ⇒ 一切标签 unknown,禁止现推区间)
LABEL_RANGE_REGISTRY: dict[str, dict[str, tuple[float, float]]] = {}

FACT_STATUS_KNOWN_PRESENT = "known_present"
FACT_STATUS_KNOWN_ABSENT = "known_absent"
FACT_STATUS_UNKNOWN = "unknown"
FACT_STATUSES = frozenset({FACT_STATUS_KNOWN_PRESENT,
                           FACT_STATUS_KNOWN_ABSENT, FACT_STATUS_UNKNOWN})

FACT_ORIGIN_USER_INPUT = "user_input"
FACT_ORIGIN_CURATED_SOURCE = "curated_source"
FACT_ORIGIN_SCENARIO_TRANSITION = "scenario_transition"
FACT_ORIGINS = frozenset({FACT_ORIGIN_USER_INPUT,
                          FACT_ORIGIN_CURATED_SOURCE,
                          FACT_ORIGIN_SCENARIO_TRANSITION})

REQUESTED_SCOPE_POSSIBLE = "possible"
REQUESTED_SCOPE_CONDITION_COMPATIBLE = "condition_compatible"
REQUESTED_SCOPES = frozenset({REQUESTED_SCOPE_POSSIBLE,
                              REQUESTED_SCOPE_CONDITION_COMPATIBLE})

ASSESSED_SCOPE_POSSIBLE = "possible"
ASSESSED_SCOPE_CONDITION_COMPATIBLE = "condition_compatible"
ASSESSED_SCOPE_CONFLICTED = "conflicted"

REQUIREMENT_ESSENTIAL = "essential"
REQUIREMENT_PREFERENCE = "preference"
REQUIREMENT_LEVELS = frozenset({REQUIREMENT_ESSENTIAL,
                                REQUIREMENT_PREFERENCE})

# requirement 的依据:来源声明必需 vs 文献观察条件参考(不混)
REQUIREMENT_BASIS_ESSENTIAL_CLAIMED = "essential_claimed_by_source"
REQUIREMENT_BASIS_OBSERVED_REFERENCE = "observed_condition_reference"

# 值语义 basis(F03/mimo 4.2 + Codex 纠偏)
VALUE_BASIS_RANGE = "range"        # 显式支持区间 {lo, hi}
VALUE_BASIS_POINT = "point"        # 声明的必需点值
VALUE_BASIS_OPTIMUM = "optimum"    # 最适值:永不产生 conflict
VALUE_BASIS_LABEL = "label"        # 定性标签:须注册表映射
VALUE_BASIS_UNSPECIFIED = "unspecified"  # 单数值未声明语义 ⇒ unknown
VALUE_BASES = frozenset({VALUE_BASIS_RANGE, VALUE_BASIS_POINT,
                         VALUE_BASIS_OPTIMUM, VALUE_BASIS_LABEL,
                         VALUE_BASIS_UNSPECIFIED})

SATISFIED = "satisfied"
CONFLICT = "conflict"
UNKNOWN = "unknown"
NOT_APPLICABLE = "not_applicable"

DEPENDENCY_SUPPORTED = "supported"
DEPENDENCY_CONTRADICTED = "contradicted"
DEPENDENCY_UNRESOLVED = "unresolved"
DEPENDENCY_STATUSES = frozenset({DEPENDENCY_SUPPORTED,
                                 DEPENDENCY_CONTRADICTED,
                                 DEPENDENCY_UNRESOLVED})


class ConditionContractError(RuntimeError):
    """条件/上下文输入契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _check_finite(value, where: dict) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ConditionContractError(
            f"条件数值非有限:{value!r}", {**where, "value": repr(value)})


# ---------------------------------------------------------------- 条件事实


@dataclass
class ConditionFact:
    """一条条件事实(键/值/状态/来源/所属场景/阶段)。"""

    key: str
    value: float | int | str | dict | None
    unit: str = ""
    status: str = FACT_STATUS_UNKNOWN
    origin: str = FACT_ORIGIN_USER_INPUT
    source_ref: str = ""
    subject_scenario_ref: str = ""   # 空=当前场景(user_input);非空须匹配
    phase_id: str = ""               # 非空=仅该阶段适用

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _validate_interval(value: dict, where: dict) -> None:
    if not isinstance(value, dict) or "lo" not in value or "hi" not in value:
        raise ConditionContractError(
            f"区间条件值须为 {{lo, hi}}:{value!r}",
            {**where, "value": repr(value)})
    lo, hi = value["lo"], value["hi"]
    for v in (lo, hi):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ConditionContractError(
                f"区间端点须为数值:{value!r}",
                {**where, "value": repr(value)})
        _check_finite(v, where)
    if not lo <= hi:
        raise ConditionContractError(
            f"区间下界须 ≤ 上界:{value!r}", {**where, "value": repr(value)})


def build_condition_fact(
    *, key: str, value=None, unit: str = "",
    status: str = FACT_STATUS_UNKNOWN,
    origin: str = FACT_ORIGIN_USER_INPUT,
    source_ref: str = "", subject_scenario_ref: str = "",
    phase_id: str = "",
) -> ConditionFact:
    """构造条件事实(fail-closed 校验;数值有限性/枚举域/区间形状)。"""
    if key not in CONDITION_KEYS:
        raise ConditionContractError(
            f"未知条件键:{key!r}(第一版限定 {sorted(CONDITION_KEYS)})",
            {"key": key})
    if status not in FACT_STATUSES:
        raise ConditionContractError(
            f"条件状态非法:{status!r}", {"status": status})
    if origin not in FACT_ORIGINS:
        raise ConditionContractError(
            f"条件来源非法:{origin!r}", {"origin": origin})
    where = {"key": key}
    if status == FACT_STATUS_UNKNOWN:
        value = None  # unknown:值不可知,不携带
    else:
        if key in INTERVAL_CONDITION_KEYS:
            if isinstance(value, dict):
                _validate_interval(value, where)
            elif isinstance(value, (int, float)) and not isinstance(
                    value, bool):
                _check_finite(value, where)
            else:
                raise ConditionContractError(
                    f"区间键 {key} 的事实值须为数值或区间:{value!r}",
                    {**where, "value": repr(value)})
        elif key == CONDITION_KEY_OXYGEN:
            if value not in OXYGEN_REGIME_VALUES:
                raise ConditionContractError(
                    f"oxygen_regime 取值非法:{value!r}"
                    f"(允许 {sorted(OXYGEN_REGIME_VALUES)})", {"value": value})
        else:
            if value is None:
                raise ConditionContractError(
                    f"已知状态的条件必须携带值:{key}", {"key": key})
            if isinstance(value, float):
                _check_finite(value, where)
    return ConditionFact(key=key, value=value, unit=unit, status=status,
                         origin=origin, source_ref=source_ref,
                         subject_scenario_ref=subject_scenario_ref,
                         phase_id=phase_id)


# ---------------------------------------------------------------- 要求


@dataclass
class Requirement:
    """一条环境/供给要求(essential|preference;来源;观察条件另存)。

    value_basis(v2):range/point/optimum/label/unspecified —— 决定该值
    参与判定的语义;unspecified(单数值未声明)按 unknown 处理,不自动
    推断为 optimum 或 range(Codex 纠偏)。
    """

    key: str
    level: str                        # essential | preference
    value: float | int | str | dict | None
    basis: str = REQUIREMENT_BASIS_ESSENTIAL_CLAIMED
    value_basis: str = VALUE_BASIS_UNSPECIFIED
    source_refs: list[str] = field(default_factory=list)
    applicable_dimensions: list[str] = field(default_factory=list)
    observed_source_conditions: list[dict] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _infer_value_basis(key: str, value, explicit: str | None) -> str:
    if explicit is not None:
        if explicit not in VALUE_BASES:
            raise ConditionContractError(
                f"值语义 basis 非法:{explicit!r}(允许 {sorted(VALUE_BASES)})",
                {"basis": explicit})
        return explicit
    if value is None:
        return VALUE_BASIS_UNSPECIFIED
    if isinstance(value, dict):
        return VALUE_BASIS_RANGE
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return VALUE_BASIS_UNSPECIFIED  # 单数值未声明语义:从严 unknown
    return VALUE_BASIS_LABEL  # 区间键上的字符串值 = 定性标签


def build_requirement(*, key: str, level: str, value=None,
                      basis: str = REQUIREMENT_BASIS_ESSENTIAL_CLAIMED,
                      value_basis: str | None = None,
                      source_refs: list[str] | None = None,
                      applicable_dimensions: list[str] | None = None,
                      observed_source_conditions: list[dict] | None = None,
                      note: str = "") -> Requirement:
    if key not in CONDITION_KEYS:
        raise ConditionContractError(
            f"未知条件键:{key!r}", {"key": key})
    if level not in REQUIREMENT_LEVELS:
        raise ConditionContractError(
            f"要求级别非法:{level!r}", {"level": level})
    if basis not in (REQUIREMENT_BASIS_ESSENTIAL_CLAIMED,
                     REQUIREMENT_BASIS_OBSERVED_REFERENCE):
        raise ConditionContractError(f"要求依据非法:{basis!r}",
                                     {"basis": basis})
    where = {"key": key}
    if key in INTERVAL_CONDITION_KEYS and isinstance(value, dict):
        _validate_interval(value, where)
    if isinstance(value, float):
        _check_finite(value, where)
    if key == CONDITION_KEY_OXYGEN and isinstance(value, str) and \
            value not in OXYGEN_REGIME_VALUES:
        raise ConditionContractError(
            f"oxygen_regime 要求取值非法:{value!r}", {"value": value})
    resolved_basis = _infer_value_basis(key, value, value_basis)
    if isinstance(value, dict):
        resolved_basis = VALUE_BASIS_RANGE  # 区间形状即 range
    return Requirement(key=key, level=level, value=value, basis=basis,
                       value_basis=resolved_basis,
                       source_refs=list(source_refs or []),
                       applicable_dimensions=list(
                           applicable_dimensions or []),
                       observed_source_conditions=list(
                           observed_source_conditions or []),
                       note=note)


# ---------------------------------------------------------------- 评估


def _interval_relation(fact_value, req_value) -> str:
    """区间/点值关系 → satisfied | conflict | unknown(§6 语义)。"""
    if isinstance(fact_value, dict) and isinstance(req_value, dict):
        flo, fhi = fact_value["lo"], fact_value["hi"]
        rlo, rhi = req_value["lo"], req_value["hi"]
        if fhi < rlo or flo > rhi:
            return CONFLICT      # 无交集
        if flo >= rlo and fhi <= rhi:
            return SATISFIED     # 实际区间完整落在支持范围内
        return UNKNOWN           # 部分相交但实际值不确定
    if isinstance(fact_value, (int, float)) and isinstance(req_value, dict):
        rlo, rhi = req_value["lo"], req_value["hi"]
        if rlo <= fact_value <= rhi:
            return SATISFIED     # 输入点位于支持范围
        return CONFLICT          # 点值在支持范围外 = 矛盾
    if isinstance(fact_value, (int, float)) and isinstance(
            req_value, (int, float)):
        return SATISFIED if fact_value == req_value else CONFLICT
    if fact_value is None or req_value is None:
        return UNKNOWN
    return SATISFIED if fact_value == req_value else CONFLICT


def _applicable_facts(context: "PathContext") -> dict[str, list[
        ConditionFact]]:
    """按场景/阶段/来源适用性过滤事实(F03)。

    - user_input:subject_scenario_ref 为空或匹配当前场景 → 适用;
    - curated_source:**必须** subject_scenario_ref 匹配当前场景才适用
      (历史实验条件标的是来源场景,不自动成为当前事实;来源的
      培养/实验设置属来源场景事实,同样只有显式采用该场景才作数);
    - scenario_transition:同 curated 匹配规则,且 phase_id 限定生效;
    - phase_id 非空的事实只在对应阶段适用(转换只影响后续步骤)。
    """
    out: dict[str, list[ConditionFact]] = {}
    for f in context.condition_facts:
        if f.phase_id and f.phase_id != context.phase_id:
            continue
        if f.origin in (FACT_ORIGIN_CURATED_SOURCE,
                        FACT_ORIGIN_SCENARIO_TRANSITION):
            if f.subject_scenario_ref != context.scenario_ref:
                continue
        elif f.subject_scenario_ref and f.subject_scenario_ref != \
                context.scenario_ref:
            continue
        out.setdefault(f.key, []).append(f)
    return out


def _assess_requirement(
    req: Requirement, fact_lists: dict[str, list[ConditionFact]],
    preference_notes: list[str],
) -> tuple[str, str]:
    """单项评估 → (status, reason)。"""
    # 文献观察条件不是必需条件:只作参考,不参与门禁
    if req.basis == REQUIREMENT_BASIS_OBSERVED_REFERENCE:
        return NOT_APPLICABLE, "observed_condition_reference_not_gating"
    # 无来源必要性(F03):未核实假设 —— 不进门禁(不产生 conflict),
    # 也不作为"来源已证必需";阻止 compatible 由 unknown 语义承担
    if req.level == REQUIREMENT_ESSENTIAL and not req.source_refs:
        return UNKNOWN, "necessity_unsourced_not_gating"
    facts = fact_lists.get(req.key)
    if not facts:
        # 未列出某共底物 = 未知,不是 absent(C01/F03)
        return UNKNOWN, f"no_applicable_fact:{req.key}"
    if len(facts) > 1:
        # 同键多条适用事实且互不一致 → 保守 unknown(不任选其一)
        signatures = {(f.status, canonical_json(f.to_dict()))
                      for f in facts}
        if len(signatures) > 1:
            return UNKNOWN, f"conflicting_applicable_facts:{req.key}"
    fact = facts[0]
    if fact.status == FACT_STATUS_UNKNOWN:
        return UNKNOWN, f"fact_unknown:{req.key}"
    # 必需物已知缺席 ⇒ 冲突(物质身份与供应存在分开,F03)
    if fact.status == FACT_STATUS_KNOWN_ABSENT:
        return CONFLICT, f"required_entity_known_absent:{req.key}"
    if req.value is None:
        return UNKNOWN, f"requirement_value_unspecified:{req.key}"
    # 定性标签:须注册表映射;首版注册表为空 ⇒ unknown(禁止现推区间)
    if req.value_basis == VALUE_BASIS_LABEL:
        if req.key in INTERVAL_CONDITION_KEYS and str(
                req.value) not in LABEL_RANGE_REGISTRY.get(req.key, {}):
            return UNKNOWN, \
                f"label_without_registered_range:{req.value!r}"
        # 物种类键上的字符串值按物种/枚举比较
    # 最适值:永不产生 conflict(偏离只作 preference 提示)
    if req.value_basis == VALUE_BASIS_OPTIMUM:
        rel = _interval_relation(fact.value, req.value)
        if rel == SATISFIED:
            return SATISFIED, f"at_optimum:{req.key}"
        preference_notes.append(
            f"optimum_deviation:{req.key}(最适 {req.value!r},实际 "
            f"{fact.value!r};偏离不构成冲突)")
        return NOT_APPLICABLE, "optimum_deviation_preference_not_gating"
    # 单数值未声明 basis:不自动推 optimum/point ⇒ unknown
    if req.value_basis == VALUE_BASIS_UNSPECIFIED and isinstance(
            req.value, (int, float)):
        return UNKNOWN, f"value_basis_unspecified:{req.key}"
    # point 语义:声明必需点值
    if req.value_basis == VALUE_BASIS_POINT and isinstance(
            fact.value, (int, float)) and isinstance(
            req.value, (int, float)):
        return (SATISFIED if fact.value == req.value else CONFLICT,
                f"point_match:{req.key}" if fact.value == req.value
                else f"point_mismatch:{req.key}")
    # 物种/枚举类:值不同且双方已知 → 冲突
    if isinstance(req.value, str) and isinstance(fact.value, str):
        if req.value != fact.value:
            return (CONFLICT,
                    f"value_mismatch:{req.key}:{req.value}!={fact.value}")
        return SATISFIED, f"value_match:{req.key}"
    status = _interval_relation(fact.value, req.value)
    reason = {
        SATISFIED: f"within_range:{req.key}",
        CONFLICT: f"range_disjoint_or_outside:{req.key}",
        UNKNOWN: f"partial_overlap_or_point_unknown:{req.key}",
    }[status]
    return status, reason


@dataclass
class ConditionAssessment:
    """条件评估结果(单项 + 合取聚合;v2)。"""

    per_requirement: list[dict]
    environment_fit: str          # compatible | unknown | conflict
    assessed_scope: str           # condition_compatible | possible | conflicted
    assessment_scope: list[str]   # 声明覆盖的环境维度(已评估)
    unassessed_dimensions: list[str]  # 已登记未评估维度(相容结论的边界)
    requirement_coverage: dict
    preference_notes: list[str]
    schema_version: str = PPV1_CONDITION_ASSESSMENT_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def aggregate_environment_fit(
    *,
    facts: list[ConditionFact],
    requirements: list[Requirement],
    declared_scope: list[str] | None = None,
    scenario_ref: str = "",
    phase_id: str = "",
) -> ConditionAssessment:
    """条件聚合(§6 + F02/F03:全部适用要求的**合取**,不按键覆盖)。

    - 任一 essential(有来源)与适用事实冲突 → conflict;
    - 无冲突但任一 unknown(缺事实/覆盖未知/无源必要性/值语义未声明/
      标签无注册映射/要求空)→ unknown(空要求列表不自动相容);
    - 全部满足且声明覆盖维度 ⊇ 全部必要要求键 → compatible;相容结论
      只覆盖 assessment_scope 列出的维度,已登记未评估维度
      (UNASSESSED_DIMENSIONS)显式随附,不得读作全维度相容。
    """
    ctx_probe = PathContext(
        context_id="", parent_context_ref="", phase_id=phase_id,
        requested_scope=REQUESTED_SCOPE_POSSIBLE,
        condition_facts=list(facts), scenario_ref=scenario_ref)
    fact_lists = _applicable_facts(ctx_probe)
    per: list[dict] = []
    notes: list[str] = []
    any_conflict = False
    any_unknown = False
    for req in requirements:
        if req.level == REQUIREMENT_PREFERENCE:
            notes.append(f"preference:{req.key}={req.value!r}(只提示,"
                         "不作冲突门)")
            per.append({"key": req.key, "level": req.level,
                        "status": NOT_APPLICABLE,
                        "reason": "preference_not_gating",
                        "basis": req.basis})
            continue
        status, reason = _assess_requirement(req, fact_lists, notes)
        per.append({"key": req.key, "level": req.level, "status": status,
                    "reason": reason, "basis": req.basis,
                    "value_basis": req.value_basis,
                    "sourced": bool(req.source_refs)})
        if status == CONFLICT:
            any_conflict = True
        elif status == UNKNOWN:
            any_unknown = True
    essential = [r for r in requirements
                 if r.level == REQUIREMENT_ESSENTIAL
                 and r.basis == REQUIREMENT_BASIS_ESSENTIAL_CLAIMED]
    if not essential:
        any_unknown = True  # (有效)必要要求为空:未知,不自动相容

    scope = [k for k in (declared_scope or []) if k in CONDITION_KEYS]
    per_status = {p["key"]: p["status"] for p in per}
    essential_key_set = {r.key for r in essential}
    covered = [k for k in essential_key_set
               if per_status.get(k) == SATISFIED and k in scope]
    fit = UNKNOWN
    if any_conflict:
        fit = CONFLICT
    elif (not any_unknown and essential
          and set(covered) == essential_key_set and scope):
        fit = "compatible"  # 全部必要要求 satisfied 且覆盖声明完整
    assessed = {
        CONFLICT: ASSESSED_SCOPE_CONFLICTED,
        "compatible": ASSESSED_SCOPE_CONDITION_COMPATIBLE,
        UNKNOWN: ASSESSED_SCOPE_POSSIBLE,
    }[fit]
    return ConditionAssessment(
        per_requirement=per, environment_fit=fit, assessed_scope=assessed,
        assessment_scope=scope,
        unassessed_dimensions=sorted(UNASSESSED_DIMENSIONS),
        requirement_coverage={
            "essential_keys": sorted(essential_key_set),
            "covered_keys": covered,
            "unknown_keys": sorted(
                p["key"] for p in per if p["status"] == UNKNOWN),
            "conflict_keys": sorted(
                p["key"] for p in per if p["status"] == CONFLICT),
        },
        preference_notes=notes,
    )


def assess_conditions(context: "PathContext",
                      hypothesis) -> ConditionAssessment:
    """§7.1 固定接口:上下文 × 假设要求 → 条件评估(纯函数)。

    评估范围 = 上下文累积的全部必要要求(父路径继承,含同键多条,
    **不去重不覆盖**,F02)+ 该假设自带 requirements(逐条并入)。
    事实按当前 scenario_ref/phase_id 的适用性过滤(F03)。
    """
    hyp_reqs = getattr(hypothesis, "requirements", None)
    if hyp_reqs is None and isinstance(hypothesis, dict):
        hyp_reqs = hypothesis.get("requirements", [])
    hyp_reqs = list(hyp_reqs or [])
    merged: list[Requirement] = list(context.accumulated_requirements)
    existing = {canonical_json(r.to_dict()) for r in merged}
    for r in hyp_reqs:
        req = r if isinstance(r, Requirement) else Requirement(**r)
        # 仅语义完全相同的要求去重(F02);不同来源/不同区间/不同值
        # 一律保留(按合取评估,不覆盖)
        sig = canonical_json(req.to_dict())
        if sig not in existing:
            merged.append(req)
            existing.add(sig)
    return aggregate_environment_fit(
        facts=context.condition_facts, requirements=merged,
        declared_scope=context.assessment_scope,
        scenario_ref=context.scenario_ref, phase_id=context.phase_id)


# ---------------------------------------------------------------- 依赖


@dataclass
class Dependency:
    """证据依赖(§6;status 固定三值;解决保留轨迹)。"""

    dependency_id: str
    kind: str                      # cosubstrate_supply | mechanism | …
    statement: str
    status: str = DEPENDENCY_UNRESOLVED
    source_refs: list[str] = field(default_factory=list)
    introduced_at_hypothesis_id: str = ""
    resolution_log: list[dict] = field(default_factory=list)
    schema_version: str = PPV1_DEPENDENCY_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def build_dependency(*, kind: str, statement: str,
                     source_refs: list[str] | None = None,
                     introduced_at_hypothesis_id: str = "") -> Dependency:
    did = stable_id("dep", kind, statement,
                    "\x00".join(source_refs or []))
    return Dependency(dependency_id=did, kind=kind, statement=statement,
                      status=DEPENDENCY_UNRESOLVED,
                      source_refs=list(source_refs or []),
                      introduced_at_hypothesis_id=introduced_at_hypothesis_id)


def resolve_dependency(dep: Dependency, *, new_evidence: list[str],
                       resolution: str, note: str = "") -> Dependency:
    """解决/反驳依赖(只有有来源新证据或显式转换才可调;保留轨迹)。

    下游精确匹配不能消除上游猜测 —— 调用方须只在持有**来源新证据**
    (source_refs)时调用;resolution ∈ supported|contradicted。
    重复引用不升级支持(轨迹如实追加,不乘分数)。
    """
    if resolution not in (DEPENDENCY_SUPPORTED, DEPENDENCY_CONTRADICTED):
        raise ConditionContractError(
            f"解决状态非法:{resolution!r}", {"resolution": resolution})
    if not new_evidence:
        raise ConditionContractError(
            "解决依赖需要来源新证据(下游精确匹配不消除上游猜测)",
            {"dependency_id": dep.dependency_id})
    log = list(dep.resolution_log)
    log.append({"resolution": resolution, "evidence": list(new_evidence),
                "note": note})
    return Dependency(
        dependency_id=dep.dependency_id, kind=dep.kind,
        statement=dep.statement, status=resolution,
        source_refs=list(dep.source_refs),
        introduced_at_hypothesis_id=dep.introduced_at_hypothesis_id,
        resolution_log=log,
    )


def _parse_supply_edge(statement: str) -> tuple[str, str] | None:
    """supplies:<src>:<dst> → (src, dst);其余返回 None。"""
    parts = statement.split(":")
    if len(parts) >= 3 and parts[0] == "supplies":
        return parts[1], parts[2]
    return None


def detect_circular_dependencies(
    dependencies: list[Dependency],
) -> dict:
    """共底物供给环诊断(§17.4 H04;v2:任意长环,结构化多边图)。

    - 多边图(同源可有多个供给目标),DFS 检出全部简单环;
    - 环上任一供给依赖无来源支持(status != supported)⇒ 该环计入
      unresolved_initial_supply(未知启动供给,依显式策略处理,
      不称化学不可能);环上全部 supported = 有启动/再生支持,不阻断;
    - 下游命中(反应证据)不自动解决上游依赖 —— 支持状态由
      resolve_dependency 的来源新证据语义管理,此处不代改。
    """
    adjacency: dict[str, dict[str, list[Dependency]]] = {}
    for dep in dependencies:
        edge = _parse_supply_edge(dep.statement)
        if edge is None:
            continue
        src, dst = edge
        adjacency.setdefault(src, {}).setdefault(dst, []).append(dep)

    cycles: set[tuple[str, ...]] = set()

    def _dfs(start: str, node: str, path: list[str],
             visited_local: set[str]) -> None:
        for nxt in adjacency.get(node, {}):
            if nxt == start and len(path) >= 1:
                # 规范化:旋转到最小起点(去重同环不同入口)
                rotated = [tuple(path[i:] + path[:i])
                           for i in range(len(path))]
                cycles.add(min(rotated))
            elif nxt not in visited_local and nxt != start:
                _dfs(start, nxt, path + [nxt], visited_local | {nxt})

    for src in adjacency:
        _dfs(src, src, [src], {src})

    def _edge_deps(cycle: tuple[str, ...]) -> list[Dependency]:
        out: list[Dependency] = []
        for i, node in enumerate(cycle):
            nxt = cycle[(i + 1) % len(cycle)]
            out.extend(adjacency.get(node, {}).get(nxt, []))
        return out

    unresolved: list[list[str]] = []
    for cycle in sorted(cycles):
        deps = _edge_deps(cycle)
        if not all(d.status == DEPENDENCY_SUPPORTED for d in deps):
            unresolved.append(list(cycle))
    return {
        "cycles": [list(c) for c in sorted(cycles)],
        "unresolved_initial_supply": unresolved,
        "note": ("cosubstrate_cycle:有启动/再生支持不自动阻断;未知标 "
                 "unresolved_initial_supply,依显式策略处理,不称化学"
                 "不可能;下游命中不自动解决上游依赖"),
    }


# ---------------------------------------------------------------- 上下文


@dataclass
class PathContext:
    """路径上下文(§6 全字段;v2 +scenario_ref;分支隔离;JSON 往返)。

    scenario_ref:当前场景身份(F03)——curated_source 事实按其匹配
    适用;历史/来源场景事实(subject_scenario_ref 不匹配)不成为当前
    事实。context_id 冻结全部语义字段(F06)。
    """

    context_id: str
    parent_context_ref: str
    phase_id: str
    requested_scope: str
    condition_facts: list[ConditionFact] = field(default_factory=list)
    accumulated_requirements: list[Requirement] = field(
        default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    dependency_refs: list[str] = field(default_factory=list)
    assessment_scope: list[str] = field(default_factory=list)
    scenario_ref: str = ""
    scenario_transition: dict | None = None
    schema_version: str = PPV1_CONTEXT_SCHEMA_VERSION

    @property
    def assessed_scope(self) -> str:
        """由事实×要求派生,不继承 requested_scope(C05)。"""
        return aggregate_environment_fit(
            facts=self.condition_facts,
            requirements=self.accumulated_requirements,
            declared_scope=self.assessment_scope,
            scenario_ref=self.scenario_ref, phase_id=self.phase_id,
        ).assessed_scope

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "context_id": self.context_id,
            "parent_context_ref": self.parent_context_ref,
            "phase_id": self.phase_id,
            "requested_scope": self.requested_scope,
            "condition_facts": [f.to_dict() for f in self.condition_facts],
            "accumulated_requirements": [r.to_dict() for r in
                                         self.accumulated_requirements],
            "assumptions": list(self.assumptions),
            "dependency_refs": list(self.dependency_refs),
            "assessment_scope": list(self.assessment_scope),
            "scenario_ref": self.scenario_ref,
            "scenario_transition": self.scenario_transition,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PathContext":
        version = d.get("schema_version")
        if version not in PPV1_CONTEXT_SUPPORTED_VERSIONS:
            raise ConditionContractError(
                f"PathContext schema 版本未知:{version!r}(支持 "
                f"{list(PPV1_CONTEXT_SUPPORTED_VERSIONS)};fail-closed)",
                {"schema_version": version})
        return cls(
            context_id=d["context_id"],
            parent_context_ref=d.get("parent_context_ref", ""),
            phase_id=d.get("phase_id", ""),
            requested_scope=d.get("requested_scope",
                                  REQUESTED_SCOPE_POSSIBLE),
            condition_facts=[ConditionFact(**f)
                             for f in d.get("condition_facts", [])],
            accumulated_requirements=[Requirement(**r) for r in
                                      d.get("accumulated_requirements", [])],
            assumptions=list(d.get("assumptions", [])),
            dependency_refs=list(d.get("dependency_refs", [])),
            assessment_scope=list(d.get("assessment_scope", [])),
            scenario_ref=d.get("scenario_ref", ""),
            scenario_transition=d.get("scenario_transition"),
        )


def _context_hash(
    *, parent_context_ref: str, phase_id: str, requested_scope: str,
    facts: list[ConditionFact], requirements: list[Requirement],
    assumptions: list[str], dependency_refs: list[str],
    assessment_scope: list[str], scenario_ref: str,
    scenario_transition: dict | None,
) -> str:
    """context_id = 全部语义字段的冻结哈希(F06)。

    影响科学前提/评估范围/继承依赖的字段全部入哈希;S3 的缓存与图
    节点不得混用不同前提的上下文身份。
    """
    return stable_id(
        "pc", parent_context_ref, phase_id, requested_scope, scenario_ref,
        canonical_json([f.to_dict() for f in facts]),
        canonical_json([r.to_dict() for r in requirements]),
        canonical_json(sorted(assumptions)),
        canonical_json(sorted(dependency_refs)),
        canonical_json(sorted(assessment_scope)),
        canonical_json(scenario_transition or {}))


def build_path_context(
    *,
    parent_context_ref: str = "",
    phase_id: str = "phase-0",
    requested_scope: str = REQUESTED_SCOPE_POSSIBLE,
    condition_facts: list[ConditionFact] | None = None,
    accumulated_requirements: list[Requirement] | None = None,
    assumptions: list[str] | None = None,
    dependency_refs: list[str] | None = None,
    assessment_scope: list[str] | None = None,
    scenario_ref: str = "",
) -> PathContext:
    """构造根/独立上下文(分支各自构建,不共享可变对象)。"""
    if requested_scope not in REQUESTED_SCOPES:
        raise ConditionContractError(
            f"requested_scope 非法:{requested_scope!r}",
            {"requested_scope": requested_scope})
    facts = list(condition_facts or [])
    requirements = list(accumulated_requirements or [])
    context_hash = _context_hash(
        parent_context_ref=parent_context_ref, phase_id=phase_id,
        requested_scope=requested_scope, facts=facts,
        requirements=requirements, assumptions=list(assumptions or []),
        dependency_refs=list(dependency_refs or []),
        assessment_scope=list(assessment_scope or []),
        scenario_ref=scenario_ref, scenario_transition=None)
    return PathContext(
        context_id=context_hash, parent_context_ref=parent_context_ref,
        phase_id=phase_id, requested_scope=requested_scope,
        condition_facts=facts, accumulated_requirements=requirements,
        assumptions=list(assumptions or []),
        dependency_refs=list(dependency_refs or []),
        assessment_scope=list(assessment_scope or []),
        scenario_ref=scenario_ref,
    )


def derive_child_context(
    parent: PathContext,
    *,
    step_requirements: list[Requirement] | None = None,
    step_assumptions: list[str] | None = None,
    step_dependency_refs: list[str] | None = None,
    scenario_transition: dict | None = None,
) -> PathContext:
    """子路径上下文 = 父事实/必要依赖 + 本步新增(分支隔离,C03)。

    F02:同键不同要求**双方都保留**(父要求与子要求并存在
    accumulated_requirements,评估按合取;不再"以假设侧为准");
    仅语义完全相同(canonical JSON 一致)的要求去重。同固定场景的
    同键差异仍显式记入 assumptions(供审阅;判定由合取承担)。
    scenario_transition:仅用户/来源提供的显式转换(带 source_ref);
    转换只影响后续步骤,不追改此前步骤。
    """
    if scenario_transition is not None:
        if not scenario_transition.get("source_ref"):
            raise ConditionContractError(
                "阶段转换必须有来源(用户/来源提供;不自行换场景)",
                {"scenario_transition": scenario_transition})
    merged: list[Requirement] = list(parent.accumulated_requirements)
    seen = {canonical_json(r.to_dict()) for r in merged}
    conflict_notes: list[str] = []
    parent_by_key: dict[str, list[Requirement]] = {}
    for r in parent.accumulated_requirements:
        parent_by_key.setdefault(r.key, []).append(r)
    for req in (step_requirements or []):
        sig = canonical_json(req.to_dict())
        if sig in seen:
            continue  # 语义完全相同:去重
        merged.append(req)
        seen.add(sig)
        existing = parent_by_key.get(req.key)
        if existing:
            conflict_notes.append(
                f"requirement_differs_at_same_scenario:{req.key}:"
                f"parent={[e.value for e in existing]},step={req.value}"
                "(双方保留,按合取评估;显式记录,不覆盖)")
    assumptions = list(parent.assumptions) + list(step_assumptions or []) \
        + conflict_notes
    phase_id = parent.phase_id
    scenario_ref = parent.scenario_ref
    if scenario_transition is not None:
        phase_id = str(scenario_transition.get("new_phase_id",
                                               parent.phase_id))
        scenario_ref = str(scenario_transition.get(
            "new_scenario_ref", parent.scenario_ref))
    child = PathContext(
        context_id="",
        parent_context_ref=parent.context_id,
        phase_id=phase_id,
        requested_scope=parent.requested_scope,
        condition_facts=[ConditionFact(**f.to_dict())
                         for f in parent.condition_facts],
        accumulated_requirements=merged,
        assumptions=assumptions,
        dependency_refs=list(parent.dependency_refs)
        + list(step_dependency_refs or []),
        assessment_scope=list(parent.assessment_scope),
        scenario_ref=scenario_ref,
        scenario_transition=scenario_transition,
    )
    child.context_id = _context_hash(
        parent_context_ref=parent.context_id, phase_id=phase_id,
        requested_scope=child.requested_scope,
        facts=child.condition_facts, requirements=merged,
        assumptions=assumptions,
        dependency_refs=child.dependency_refs,
        assessment_scope=child.assessment_scope,
        scenario_ref=scenario_ref,
        scenario_transition=scenario_transition)
    return child
