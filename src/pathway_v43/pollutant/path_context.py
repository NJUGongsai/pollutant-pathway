"""PathContext — 路径上下文、条件事实与证据依赖(v3 回修,S2)。

v3(ppv1-context-3 / ppv1-condition-assessment-3 / ppv1-dependency-3,
2026-10-06 R3 回修)相对 v2 的变化(R2-04/05/06 + P2):
- **要求绑定所属边/阶段(R2-04)**:Requirement 引入时的
  phase_id/scenario_ref/边(introduced_edge,最佳努力 = hypothesis_id)
  随要求保存;评估用**该阶段适用**的事实,不得拿新阶段事实重评旧
  要求。derive_child 的 scenario_transition 把旧阶段评估冻结为
  phase_history 历史快照(只影响后续步骤;转换不是反应边);
  路线聚合按选定边逐边合取——任何旧边冲突在路线结果中保持,
  旧要求也不因拿到新阶段事实而假冲突。本步评估
  (current_step_assessment)与全路线评估(route_assessment /
  assessed_scope)分开呈现。
- **不可变性(R2-04)**:Requirement/ConditionFact/Dependency 为
  frozen dataclass;构造/派生路径对嵌套可变值(区间 dict/来源列表/
  轨迹)做深拷贝隔离——兄弟分支修改不得影响父与其他分支。
- **数值/单位/实体作用域(R2-05)**:区间×点双向(点在不确定区间
  ⇒ unknown point_in_uncertain_range;退化区间含点 ⇒ satisfied;
  点在区间外 ⇒ conflict point_outside_interval,理由码独立);
  单位不匹配 ⇒ unknown unit_mismatch(首版无 K→°C 换算,显式拒绝
  比较);物种键按**实体身份**先匹配(他实体缺席/在场不证明本实体
  状态;多种已知供体并存),枚举键(oxygen_regime)封闭集字符串
  不匹配仍 conflict。
- **label 范围定案(P2/复审 4.2(b) 缺口 2)**:label 仅适用于区间键
  (INTERVAL_CONDITION_KEYS)且须注册表映射(首版注册表为空 ⇒
  unknown);物种/枚举/矩阵键字符串是**实体/枚举比对**(value_basis
  =entity),不走 label/注册表。
- **再生支持与启动供给分轴(R2-06)**:resolve_dependency 声明
  support_axis(reaction|regeneration|initial_supply,默认 reaction);
  环上仅有再生/反应关系支持 ⇒ unresolved_initial_supply 保留;
  补可追溯初始供给证据才解决。关系未支持单独披露
  (unsupported_relation_cycles),不混入启动语义;环不自动 reject,
  不称化学不可能。
- **scope/coverage/来源/basis(P2)**:assessment_scope 从**实际执行
  的检查**派生(有事实 ≠ 已检查);声明收窄留痕 scope_narrowed_by,
  且不得隐藏必需未知维度;coverage 按同键最坏状态聚合
  (conflict > unknown > satisfied),区分 assessed_keys 与
  satisfied_keys,逐条结果全保留;同值不同来源不是事实不一致
  (来源全部保留在 fact_sources),值真正不同才走不一致路径;
  构造期/数据类直构校验 basis 与值形状一致(dict⇒range;标量⇒
  point/optimum/unspecified;字符串⇒区间键 label 或实体/枚举键
  entity),不一致抛 ConditionContractError。

v2 已修语义保留(F02/F03/F06):要求按步骤累积不覆盖、合取评估;
事实适用性分场景/阶段/来源;无源 essential 阻止相容不产生冲突;
optimum 永不冲突;单数值未声明 basis ⇒ unknown;context_id 冻结
全部语义字段(含 phase_history 与要求绑定);供给环任意长可检出。
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

from ..domain.models import canonical_json, stable_id
from .profile import (
    PPV1_CONDITION_ASSESSMENT_VERSION,
    PPV1_CONTEXT_SCHEMA_VERSION,
    PPV1_DEPENDENCY_SCHEMA_VERSION,
)

PPV1_CONTEXT_SUPPORTED_VERSIONS = ("ppv1-context-3",)

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

# 区间型条件键(数值/区间语义;定性标签须注册表映射)
INTERVAL_CONDITION_KEYS = frozenset({CONDITION_KEY_PH,
                                     CONDITION_KEY_TEMPERATURE})
# 物种类键(值=物种实体引用;实体身份先匹配;多值可并存)
SPECIES_CONDITION_KEYS = frozenset({CONDITION_KEY_ELECTRON_DONOR,
                                    CONDITION_KEY_ELECTRON_ACCEPTOR,
                                    CONDITION_KEY_GROWTH_SUBSTRATE})
# 枚举键(封闭集;字符串不匹配 = 互斥 ⇒ conflict,C02 语义)
ENUM_CONDITION_KEYS = frozenset({CONDITION_KEY_OXYGEN})
OXYGEN_REGIME_VALUES = frozenset({"aerobic", "anaerobic", "facultative"})

# 键 → 视作键名既定量纲的规范单位(空 = 无单位/未声明,按键名量纲);
# 首版不做换算:非规范单位 ⇒ unit_mismatch ⇒ unknown,不得按数值直比
CONDITION_KEY_UNITS: dict[str, frozenset[str]] = {
    CONDITION_KEY_TEMPERATURE: frozenset({"", "°C", "C", "celsius"}),
    CONDITION_KEY_PH: frozenset({"", "pH", "dimensionless"}),
}

# 已登记的 v2 条件键缺口(mimo 4.2(2) + Codex"登记未评估维度"):
# 首版不评估这些维度 ⇒ 相容结论只覆盖已评估维度,不得显示为全维度相容
UNASSESSED_DIMENSIONS = frozenset({
    "biotic_abiotic", "light_regime", "salinity_ionic_strength",
    "redox_regime_eh", "required_trace_elements_cofactors",
    "substrate_concentration", "inoculum_source", "phase_bioavailability",
})

# 定性标签 → 支持区间的注册表(仅区间键;物种/枚举键不走注册表)
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

# 值语义 basis(R2-05/P2 定案)
VALUE_BASIS_RANGE = "range"        # 显式支持区间 {lo, hi}
VALUE_BASIS_POINT = "point"        # 声明的必需点值
VALUE_BASIS_OPTIMUM = "optimum"    # 最适值:永不产生 conflict
VALUE_BASIS_LABEL = "label"        # 定性标签:仅区间键,须注册表映射
VALUE_BASIS_ENTITY = "entity"      # 实体/枚举身份比对(物种/枚举/矩阵键)
VALUE_BASIS_UNSPECIFIED = "unspecified"  # 单数值未声明语义 ⇒ unknown
VALUE_BASES = frozenset({VALUE_BASIS_RANGE, VALUE_BASIS_POINT,
                         VALUE_BASIS_OPTIMUM, VALUE_BASIS_LABEL,
                         VALUE_BASIS_ENTITY, VALUE_BASIS_UNSPECIFIED})

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

# 依赖支持轴(R2-06):关系证据(reaction/regeneration)与启动供给
# 状态(initial_supply)分轴;默认 reaction(下游命中/关系支持不解决启动)
SUPPORT_AXIS_REACTION = "reaction"
SUPPORT_AXIS_REGENERATION = "regeneration"
SUPPORT_AXIS_INITIAL_SUPPLY = "initial_supply"
SUPPORT_AXES = frozenset({SUPPORT_AXIS_REACTION,
                          SUPPORT_AXIS_REGENERATION,
                          SUPPORT_AXIS_INITIAL_SUPPLY})


class ConditionContractError(RuntimeError):
    """条件/上下文输入契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _check_finite(value, where: dict) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ConditionContractError(
            f"条件数值非有限:{value!r}", {**where, "value": repr(value)})


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------- 条件事实


@dataclass(frozen=True)
class ConditionFact:
    """一条条件事实(键/值/状态/来源/所属场景/阶段;不可变,R2-04)。"""

    key: str
    value: float | int | str | dict | None
    unit: str = ""
    status: str = FACT_STATUS_UNKNOWN
    origin: str = FACT_ORIGIN_USER_INPUT
    source_ref: str = ""
    subject_scenario_ref: str = ""   # 空=当前场景(user_input);非空须匹配
    phase_id: str = ""               # 非空=仅该阶段适用

    def __post_init__(self) -> None:
        # 深隔离:嵌套区间 dict 拷贝,不与调用方共享可变对象
        if isinstance(self.value, dict):
            object.__setattr__(self, "value", copy.deepcopy(self.value))

    def to_dict(self) -> dict:
        return {
            "key": self.key, "value": copy.deepcopy(self.value),
            "unit": self.unit, "status": self.status,
            "origin": self.origin, "source_ref": self.source_ref,
            "subject_scenario_ref": self.subject_scenario_ref,
            "phase_id": self.phase_id,
        }


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
    """构造条件事实(fail-closed 校验;数值有限性/枚举域/区间形状)。

    单位边界(R2-05):temperature_C/pH 等带量纲键的非规范单位在
    **评估时**判 unit_mismatch ⇒ unknown(不拒构造,事实可入账但
    不参与数值比较);首版无 K→°C 等换算。
    """
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
            elif _is_number(value):
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


@dataclass(frozen=True)
class Requirement:
    """一条环境/供给要求(essential|preference;来源;观察条件另存)。

    不可变(R2-04):frozen dataclass + 嵌套值深拷贝;引入时的所属
    绑定(introduced_phase_id/scenario_ref/introduced_edge = 边的
    hypothesis_id,最佳努力)随要求保存,评估用该阶段适用事实。

    value_basis:range/point/optimum/label/entity/unspecified ——
    label 仅区间键(须注册表映射);entity 是物种/枚举/矩阵键字符串
    的实体/枚举身份比对;unspecified(单数值未声明)按 unknown 处理。
    """

    key: str
    level: str                        # essential | preference
    value: float | int | str | dict | None
    basis: str = REQUIREMENT_BASIS_ESSENTIAL_CLAIMED
    value_basis: str = ""
    source_refs: list[str] = field(default_factory=list)
    applicable_dimensions: list[str] = field(default_factory=list)
    observed_source_conditions: list[dict] = field(default_factory=list)
    note: str = ""
    introduced_phase_id: str = ""     # R2-04:引入阶段(空=未绑定)
    introduced_scenario_ref: str = ""  # R2-04:引入场景
    introduced_edge: str = ""         # R2-04:引入边(hypothesis_id)

    def __post_init__(self) -> None:
        # 深隔离 + basis 校验/推断(数据类直构路径同样把关,P2)
        if isinstance(self.value, dict):
            object.__setattr__(self, "value", copy.deepcopy(self.value))
        object.__setattr__(self, "source_refs", list(self.source_refs))
        object.__setattr__(self, "applicable_dimensions",
                           list(self.applicable_dimensions))
        object.__setattr__(self, "observed_source_conditions",
                           copy.deepcopy(self.observed_source_conditions))
        if not self.value_basis:
            object.__setattr__(self, "value_basis",
                               _infer_value_basis(self.key, self.value,
                                                  None))
        _validate_value_basis_shape(self.key, self.value, self.value_basis)

    def to_dict(self) -> dict:
        return {
            "key": self.key, "level": self.level,
            "value": copy.deepcopy(self.value), "basis": self.basis,
            "value_basis": self.value_basis,
            "source_refs": list(self.source_refs),
            "applicable_dimensions": list(self.applicable_dimensions),
            "observed_source_conditions": copy.deepcopy(
                self.observed_source_conditions),
            "note": self.note,
            "introduced_phase_id": self.introduced_phase_id,
            "introduced_scenario_ref": self.introduced_scenario_ref,
            "introduced_edge": self.introduced_edge,
        }


def _allowed_value_bases(key: str, value) -> set[str]:
    """basis 与值形状的一致矩阵(P2:构造期/from_dict 校验)。"""
    if isinstance(value, dict):
        return {VALUE_BASIS_RANGE}
    if _is_number(value):
        return {VALUE_BASIS_POINT, VALUE_BASIS_OPTIMUM,
                VALUE_BASIS_UNSPECIFIED}
    if isinstance(value, str):
        if key in INTERVAL_CONDITION_KEYS:
            return {VALUE_BASIS_LABEL}
        # 物种/枚举/矩阵键:实体/枚举比对;容忍 v2 遗留 unspecified
        # 声明(该声明对比对无作用,不静默改写来源声明)
        return {VALUE_BASIS_ENTITY, VALUE_BASIS_UNSPECIFIED}
    return {VALUE_BASIS_UNSPECIFIED}


def _validate_value_basis_shape(key: str, value, basis: str) -> None:
    if basis not in VALUE_BASES:
        raise ConditionContractError(
            f"值语义 basis 非法:{basis!r}(允许 {sorted(VALUE_BASES)})",
            {"key": key, "basis": basis})
    allowed = _allowed_value_bases(key, value)
    if basis not in allowed:
        raise ConditionContractError(
            f"basis 与值形状不一致:key={key!r} value={value!r} 声明 "
            f"{basis!r}(该形状允许 {sorted(allowed)};不做静默规范化,"
            "不追改来源声明的点值/最适/标签语义)",
            {"key": key, "basis": basis, "value": repr(value),
             "kind": "basis_shape_mismatch"})


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
    if _is_number(value):
        return VALUE_BASIS_UNSPECIFIED  # 单数值未声明语义:从严 unknown
    # 字符串:区间键 = 定性标签;物种/枚举/矩阵键 = 实体/枚举比对
    if key in INTERVAL_CONDITION_KEYS:
        return VALUE_BASIS_LABEL
    return VALUE_BASIS_ENTITY


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
    return Requirement(key=key, level=level, value=value, basis=basis,
                       value_basis=resolved_basis,
                       source_refs=list(source_refs or []),
                       applicable_dimensions=list(
                           applicable_dimensions or []),
                       observed_source_conditions=list(
                           observed_source_conditions or []),
                       note=note)


def _bind_requirement(req: Requirement, *, phase_id: str,
                      scenario_ref: str, edge: str) -> Requirement:
    """引入时绑定所属阶段/场景/边(仅填补空值,不追改既有绑定)。"""
    if (req.introduced_phase_id in ("", phase_id)
            and req.introduced_scenario_ref in ("", scenario_ref)
            and req.introduced_edge in ("", edge)):
        return Requirement(
            key=req.key, level=req.level,
            value=copy.deepcopy(req.value), basis=req.basis,
            value_basis=req.value_basis,
            source_refs=list(req.source_refs),
            applicable_dimensions=list(req.applicable_dimensions),
            observed_source_conditions=copy.deepcopy(
                req.observed_source_conditions),
            note=req.note,
            introduced_phase_id=req.introduced_phase_id or phase_id,
            introduced_scenario_ref=(req.introduced_scenario_ref
                                     or scenario_ref),
            introduced_edge=req.introduced_edge or edge)
    # 预绑定到其他阶段/场景的要求:原样深拷贝保留(按其自身绑定评估)
    return Requirement(**req.to_dict())


def _requirement_copy(req: Requirement) -> Requirement:
    """深拷贝(分支隔离:不与任何现有对象共享嵌套可变值)。"""
    return Requirement(**req.to_dict())


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
    if _is_number(fact_value) and isinstance(req_value, dict):
        rlo, rhi = req_value["lo"], req_value["hi"]
        if rlo <= fact_value <= rhi:
            return SATISFIED     # 输入点位于支持范围
        return CONFLICT          # 点值在支持范围外 = 矛盾
    if _is_number(fact_value) and _is_number(req_value):
        return SATISFIED if fact_value == req_value else CONFLICT
    if fact_value is None or req_value is None:
        return UNKNOWN
    return SATISFIED if fact_value == req_value else CONFLICT


def _semantic_value_signature(fact: ConditionFact):
    """事实的语义值签名(P2:同值不同来源不是不一致)。

    只按 (状态, 值, 单位) 比较——source_ref/origin 等记账字段不参与
    一致性判定;数值做 float 归一(7 与 7.0 同值)。
    """
    value = fact.value
    if _is_number(value):
        value = float(value)
    elif isinstance(value, dict):
        value = {k: (float(v) if _is_number(v) else v)
                 for k, v in value.items()}
    return (fact.status, canonical_json(value), fact.unit)


def _unit_ok(key: str, unit: str) -> bool:
    allowed = CONDITION_KEY_UNITS.get(key)
    if allowed is None:
        return unit == ""  # 无量纲键不携带单位
    return unit in allowed


def _applicable_facts(context: "PathContext",
                      phase_id: str = "") -> dict[str, list[
                          ConditionFact]]:
    """按场景/阶段/来源适用性过滤事实(F03/R2-04)。

    - 阶段:phase_id 非空的事实只在对应阶段适用;评估某条要求时用
      **该要求引入阶段**适用的事实,不拿新阶段事实重评旧要求;
    - user_input:subject_scenario_ref 为空或匹配当前场景 → 适用;
    - curated_source:**必须** subject_scenario_ref 匹配当前场景才适用
      (历史实验条件标的是来源场景,不自动成为当前事实);
    - scenario_transition:同 curated 匹配规则。
    """
    out: dict[str, list[ConditionFact]] = {}
    for f in context.condition_facts:
        if f.phase_id and f.phase_id != phase_id:
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


def _assess_species_requirement(req: Requirement,
                                facts: list[ConditionFact],
                                ) -> tuple[str, str, list[str]]:
    """物种键评估(R2-05):实体身份先匹配;多值并存。

    - 必需实体有自身事实:known_absent ⇒ conflict(实体自身缺席);
      known_present ⇒ satisfied;unknown ⇒ unknown;
    - 无自身事实:他实体在场/缺席不证明本实体状态 ⇒ unknown
      (未列出 ≠ absent;多种已知供体可并存,不按键 last-wins);
    - 同实体同阶段同场景既有 present 又有 absent ⇒ 值真正不一致 ⇒
      保守 unknown。
    """
    entity = req.value
    same = [f for f in facts if f.value == entity]
    sources = [f.source_ref for f in facts if f.source_ref]
    if not same:
        others = sorted({str(f.value) for f in facts})
        reason = (f"entity_not_among_known_facts:{req.key}:"
                  f"required={entity!r},known={others}"
                  if others else
                  f"no_applicable_fact:{req.key}")
        return UNKNOWN, reason, sources
    if any(f.status == FACT_STATUS_KNOWN_ABSENT for f in same) and \
            any(f.status == FACT_STATUS_KNOWN_PRESENT for f in same):
        return (UNKNOWN,
                f"conflicting_applicable_facts:{req.key}", sources)
    first = same[0]
    if first.status == FACT_STATUS_UNKNOWN:
        return UNKNOWN, f"fact_unknown:{req.key}", sources
    if first.status == FACT_STATUS_KNOWN_ABSENT:
        return (CONFLICT,
                f"required_entity_known_absent:{req.key}", sources)
    return SATISFIED, f"entity_present:{req.key}", sources


def _assess_requirement(
    req: Requirement, fact_lists: dict[str, list[ConditionFact]],
    preference_notes: list[str],
) -> tuple[str, str, list[str]]:
    """单项评估 → (status, reason, fact_sources)。"""
    # 文献观察条件不是必需条件:只作参考,不参与门禁
    if req.basis == REQUIREMENT_BASIS_OBSERVED_REFERENCE:
        return NOT_APPLICABLE, "observed_condition_reference_not_gating", []
    # 无来源必要性(F03):未核实假设 —— 不进门禁(不产生 conflict),
    # 也不作为"来源已证必需";阻止 compatible 由 unknown 语义承担
    if req.level == REQUIREMENT_ESSENTIAL and not req.source_refs:
        return UNKNOWN, "necessity_unsourced_not_gating", []
    facts = fact_lists.get(req.key)
    if not facts:
        # 未列出某共底物 = 未知,不是 absent(C01/F03)
        return UNKNOWN, f"no_applicable_fact:{req.key}", []
    sources = [f.source_ref for f in facts if f.source_ref]
    # 物种键:实体身份先匹配(R2-05)
    if req.key in SPECIES_CONDITION_KEYS and isinstance(req.value, str):
        return _assess_species_requirement(req, facts)
    # 单值维度:适用事实值真正不一致 → 保守 unknown(P2:同值不同
    # 来源不是不一致——按语义值签名比较,来源保留)
    known = [f for f in facts if f.status != FACT_STATUS_UNKNOWN]
    if len({_semantic_value_signature(f) for f in known}) > 1:
        return UNKNOWN, f"conflicting_applicable_facts:{req.key}", sources
    if any(f.status == FACT_STATUS_UNKNOWN for f in facts):
        return UNKNOWN, f"fact_unknown:{req.key}", sources
    fact = facts[0]
    # 单位边界(R2-05):带量纲键的非规范单位 ⇒ 不做数值比较
    if not _unit_ok(fact.key, fact.unit):
        return (UNKNOWN,
                f"unit_mismatch:{fact.key}:{fact.unit!r}"
                f"(首版无换算,不按数值直比)", sources)
    if req.value is None:
        return UNKNOWN, f"requirement_value_unspecified:{req.key}", sources
    # 定性标签:仅区间键须注册表映射;首版注册表为空 ⇒ unknown
    # (物种/枚举/矩阵键字符串是实体/枚举比对,不走 label/注册表)
    if req.value_basis == VALUE_BASIS_LABEL:
        if req.key in INTERVAL_CONDITION_KEYS and str(
                req.value) not in LABEL_RANGE_REGISTRY.get(req.key, {}):
            return UNKNOWN, \
                f"label_without_registered_range:{req.value!r}", sources
    # 最适值:永不产生 conflict(偏离只作 preference 提示)
    if req.value_basis == VALUE_BASIS_OPTIMUM:
        rel = _interval_relation(fact.value, req.value)
        if rel == SATISFIED:
            return SATISFIED, f"at_optimum:{req.key}", sources
        preference_notes.append(
            f"optimum_deviation:{req.key}(最适 {req.value!r},实际 "
            f"{fact.value!r};偏离不构成冲突)")
        return NOT_APPLICABLE, "optimum_deviation_preference_not_gating", \
            sources
    # 单数值未声明 basis:不自动推 optimum/point ⇒ unknown
    if req.value_basis == VALUE_BASIS_UNSPECIFIED and _is_number(
            req.value):
        return UNKNOWN, f"value_basis_unspecified:{req.key}", sources
    # point 语义:声明必需点值;事实为区间时双向分码(R2-05)
    if req.value_basis == VALUE_BASIS_POINT:
        if _is_number(fact.value) and _is_number(req.value):
            return ((SATISFIED if fact.value == req.value else CONFLICT),
                    (f"point_match:{req.key}" if fact.value == req.value
                     else f"point_mismatch:{req.key}"), sources)
        if isinstance(fact.value, dict) and _is_number(req.value):
            lo, hi = fact.value["lo"], fact.value["hi"]
            if not (lo <= req.value <= hi):
                return (CONFLICT,
                        f"point_outside_interval:{req.key}", sources)
            if lo == hi:
                return (SATISFIED,
                        f"point_in_degenerate_interval:{req.key}", sources)
            return (UNKNOWN,
                    f"point_in_uncertain_range:{req.key}", sources)
    # 实体/枚举比对:枚举键(封闭集)与开放单值键字符串不匹配 ⇒
    # conflict(不得为过测试把所有字符串改 unknown;C02)
    if isinstance(req.value, str) and isinstance(fact.value, str):
        if req.value != fact.value:
            return (CONFLICT,
                    f"value_mismatch:{req.key}:{req.value}!={fact.value}",
                    sources)
        return SATISFIED, f"value_match:{req.key}", sources
    status = _interval_relation(fact.value, req.value)
    reason = {
        SATISFIED: f"within_range:{req.key}",
        CONFLICT: f"range_disjoint_or_outside:{req.key}",
        UNKNOWN: f"partial_overlap_or_point_unknown:{req.key}",
    }[status]
    return status, reason, sources


def _effective_phase(req: Requirement, context_phase_id: str) -> str:
    """要求的有效评估阶段:引入绑定优先,未绑定 = 当前阶段。"""
    return req.introduced_phase_id or context_phase_id


@dataclass
class ConditionAssessment:
    """条件评估结果(单项 + 合取聚合;v3)。

    assessment_scope = **实际执行的检查**覆盖的键(从评估过的必要
    要求派生,不继承声明;有事实 ≠ 已检查);declared_scope 是调用
    方声明(只能收窄,收窄留痕 scope_narrowed_by,且不能隐藏必需
    未知维度)。requirement_coverage 按同键最坏状态聚合
    (conflict > unknown > satisfied),assessed_keys 与
    satisfied_keys 分开,逐条 per_requirement 全保留不 last-wins。
    """

    per_requirement: list[dict]
    environment_fit: str          # compatible | unknown | conflict
    assessed_scope: str           # condition_compatible | possible | conflicted
    assessment_scope: list[str]   # 实际已评估的环境维度(执行派生)
    unassessed_dimensions: list[str]  # 已登记未评估维度(相容结论的边界)
    requirement_coverage: dict
    preference_notes: list[str]
    declared_scope: list[str] = field(default_factory=list)
    scope_narrowed: bool = False
    scope_narrowed_by: list[str] = field(default_factory=list)
    schema_version: str = PPV1_CONDITION_ASSESSMENT_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _worst_status(statuses: list[str]) -> str:
    if CONFLICT in statuses:
        return CONFLICT
    if UNKNOWN in statuses:
        return UNKNOWN
    return SATISFIED


def aggregate_environment_fit(
    *,
    facts: list[ConditionFact],
    requirements: list[Requirement],
    declared_scope: list[str] | None = None,
    scenario_ref: str = "",
    phase_id: str = "",
) -> ConditionAssessment:
    """条件聚合(§6 + F02/F03/R2-04/R2-05:全部适用要求的**合取**,
    不按键覆盖;每条要求按其**引入阶段**适用的事实评估)。

    - 任一 essential(有来源)与适用事实冲突 → conflict;
    - 无冲突但任一 unknown(缺事实/覆盖未知/无源必要性/值语义未声明/
      标签无注册映射/单位不匹配/点在不确定区间/要求空)→ unknown
      (空要求列表不自动相容);
    - 全部满足、必要要求非空且声明覆盖非空 → compatible;相容结论
      只覆盖实际评估维度(assessment_scope),已登记未评估维度
      (UNASSESSED_DIMENSIONS)显式随附。
    """
    ctx_probe = PathContext(
        context_id="", parent_context_ref="", phase_id=phase_id,
        requested_scope=REQUESTED_SCOPE_POSSIBLE,
        condition_facts=[_fact_copy(x) for x in facts],
        scenario_ref=scenario_ref)
    fact_lists_by_phase: dict[str, dict[str, list[ConditionFact]]] = {}

    def _facts_for(phase: str) -> dict[str, list[ConditionFact]]:
        if phase not in fact_lists_by_phase:
            fact_lists_by_phase[phase] = _applicable_facts(ctx_probe, phase)
        return fact_lists_by_phase[phase]

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
        fact_lists = _facts_for(_effective_phase(req, phase_id))
        status, reason, sources = _assess_requirement(req, fact_lists,
                                                      notes)
        per.append({"key": req.key, "level": req.level, "status": status,
                    "reason": reason, "basis": req.basis,
                    "value_basis": req.value_basis,
                    "sourced": bool(req.source_refs),
                    "introduced_phase_id": _effective_phase(req, phase_id),
                    "introduced_edge": req.introduced_edge,
                    "fact_sources": sources})
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
    # P2:已评估维度从实际执行的检查派生(评过的必要要求键),
    # 不继承声明——评过氧不得到"氧+pH+温度已评估";有事实 ≠ 已检查
    assessed_keys = sorted({p["key"] for p in per
                            if p["level"] == REQUIREMENT_ESSENTIAL
                            and p["basis"]
                            == REQUIREMENT_BASIS_ESSENTIAL_CLAIMED})
    # 同键最坏状态(P2:不 last-wins;"评过且冲突"可呈现)
    key_status: dict[str, str] = {}
    for p in per:
        if p["status"] == NOT_APPLICABLE:
            continue
        key_status[p["key"]] = _worst_status(
            [key_status.get(p["key"], SATISFIED), p["status"]])
    satisfied_keys = sorted(k for k, s in key_status.items()
                            if s == SATISFIED)
    narrowed_by = sorted(k for k in assessed_keys if k not in scope)
    fit = UNKNOWN
    if any_conflict:
        fit = CONFLICT
    elif (not any_unknown and essential and scope
          and set(satisfied_keys) >= {r.key for r in essential}):
        # 全部必要要求 satisfied(optimum 等永不门禁的行是 N/A,
        # 不构成满足 ⇒ 保持 unknown,不冒充相容)
        fit = "compatible"
    assessed = {
        CONFLICT: ASSESSED_SCOPE_CONFLICTED,
        "compatible": ASSESSED_SCOPE_CONDITION_COMPATIBLE,
        UNKNOWN: ASSESSED_SCOPE_POSSIBLE,
    }[fit]
    return ConditionAssessment(
        per_requirement=per, environment_fit=fit, assessed_scope=assessed,
        assessment_scope=assessed_keys,
        unassessed_dimensions=sorted(UNASSESSED_DIMENSIONS),
        requirement_coverage={
            "essential_keys": sorted({r.key for r in essential}),
            "assessed_keys": assessed_keys,
            "satisfied_keys": satisfied_keys,
            "covered_keys": list(satisfied_keys),
            "unknown_keys": sorted(k for k, s in key_status.items()
                                   if s == UNKNOWN),
            "conflict_keys": sorted(k for k, s in key_status.items()
                                    if s == CONFLICT),
        },
        preference_notes=notes,
        declared_scope=scope,
        scope_narrowed=bool(narrowed_by),
        scope_narrowed_by=narrowed_by,
    )


def _fact_copy(f: ConditionFact) -> ConditionFact:
    return ConditionFact(**f.to_dict())


def assess_conditions(context: "PathContext",
                      hypothesis) -> ConditionAssessment:
    """§7.1 固定接口:上下文 × 假设要求 → 条件评估(纯函数)。

    评估范围 = 上下文累积的全部必要要求(父路径继承,含同键多条,
    **不去重不覆盖**,F02;R2-04:每条按其引入阶段评估)+ 该假设自带
    requirements(逐条并入,按假设所属 = 当前阶段/边评估)。
    事实按当前 scenario_ref 与各要求引入阶段的适用性过滤(F03)。
    """
    hyp_reqs = getattr(hypothesis, "requirements", None)
    if hyp_reqs is None and isinstance(hypothesis, dict):
        hyp_reqs = hypothesis.get("requirements", [])
    hyp_reqs = list(hyp_reqs or [])
    merged: list[Requirement] = list(context.accumulated_requirements)
    existing = {canonical_json(r.to_dict()) for r in merged}
    for raw in hyp_reqs:
        req = _requirement_copy(raw) if isinstance(raw, Requirement) \
            else Requirement(**dict(raw))
        req = _bind_requirement(
            req, phase_id=context.phase_id,
            scenario_ref=context.scenario_ref,
            edge=getattr(hypothesis, "hypothesis_id", ""))
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


@dataclass(frozen=True)
class Dependency:
    """证据依赖(§6;status 固定三值;解决保留轨迹;不可变,R2-04)。

    R2-06 支持分轴:support_axis 区分 reaction/regeneration(关系
    支持)与 initial_supply(启动供给状态)——关系全 supported 不
    等于启动供给已知。
    """

    dependency_id: str
    kind: str                      # cosubstrate_supply | mechanism | …
    statement: str
    status: str = DEPENDENCY_UNRESOLVED
    source_refs: list[str] = field(default_factory=list)
    introduced_at_hypothesis_id: str = ""
    resolution_log: list[dict] = field(default_factory=list)
    support_axis: str = SUPPORT_AXIS_REACTION  # 最近一次解决的支持轴
    schema_version: str = PPV1_DEPENDENCY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_refs", list(self.source_refs))
        object.__setattr__(self, "resolution_log",
                           copy.deepcopy(self.resolution_log))

    def to_dict(self) -> dict:
        return {
            "dependency_id": self.dependency_id, "kind": self.kind,
            "statement": self.statement, "status": self.status,
            "source_refs": list(self.source_refs),
            "introduced_at_hypothesis_id":
                self.introduced_at_hypothesis_id,
            "resolution_log": copy.deepcopy(self.resolution_log),
            "support_axis": self.support_axis,
            "schema_version": self.schema_version,
        }


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
                       resolution: str, note: str = "",
                       support_axis: str = SUPPORT_AXIS_REACTION
                       ) -> Dependency:
    """解决/反驳依赖(只有有来源新证据或显式转换才可调;保留轨迹)。

    下游精确匹配不能消除上游猜测 —— 调用方须只在持有**来源新证据**
    (source_refs)时调用;resolution ∈ supported|contradicted。
    support_axis(R2-06)声明该证据支持哪一轴:reaction/regeneration
    = 关系支持(不解决启动供给);initial_supply = 可追溯初始供给
    (解决环的启动未知)。默认 reaction:关系证据不自动变成启动证据。
    重复引用不升级支持(轨迹如实追加,不乘分数)。
    """
    if resolution not in (DEPENDENCY_SUPPORTED, DEPENDENCY_CONTRADICTED):
        raise ConditionContractError(
            f"解决状态非法:{resolution!r}", {"resolution": resolution})
    if support_axis not in SUPPORT_AXES:
        raise ConditionContractError(
            f"支持轴非法:{support_axis!r}(允许 {sorted(SUPPORT_AXES)})",
            {"support_axis": support_axis})
    if not new_evidence:
        raise ConditionContractError(
            "解决依赖需要来源新证据(下游精确匹配不消除上游猜测)",
            {"dependency_id": dep.dependency_id})
    log = copy.deepcopy(list(dep.resolution_log))
    log.append({"resolution": resolution, "evidence": list(new_evidence),
                "note": note, "support_axis": support_axis})
    return Dependency(
        dependency_id=dep.dependency_id, kind=dep.kind,
        statement=dep.statement, status=resolution,
        source_refs=list(dep.source_refs),
        introduced_at_hypothesis_id=dep.introduced_at_hypothesis_id,
        resolution_log=log,
        support_axis=support_axis,
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
    """共底物供给环诊断(§17.4 H04;R2-06:支持分轴)。

    - 多边图(同源可有多个供给目标),DFS 检出全部简单环;
    - **启动供给与关系支持分轴(R2-06)**:环上没有任何
      initial_supply 轴支持的依赖 ⇒ 计入 unresolved_initial_supply
      (未知启动供给,依显式策略处理,不称化学不可能);
      环上全部关系 supported(含 regeneration)只表示关系成立,
      **不**删除启动未知;
    - 关系未支持(status != supported)单独披露
      (unsupported_relation_cycles),不混入启动语义;
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
    unsupported_relation: list[list[str]] = []
    for cycle in sorted(cycles):
        deps = _edge_deps(cycle)
        has_initial = any(
            d.status == DEPENDENCY_SUPPORTED
            and d.support_axis == SUPPORT_AXIS_INITIAL_SUPPLY
            for d in deps)
        if not has_initial:
            unresolved.append(list(cycle))
        if not all(d.status == DEPENDENCY_SUPPORTED for d in deps):
            unsupported_relation.append(list(cycle))
    return {
        "cycles": [list(c) for c in sorted(cycles)],
        "unresolved_initial_supply": unresolved,
        "unsupported_relation_cycles": unsupported_relation,
        "note": ("cosubstrate_cycle:有启动/再生支持不自动阻断;仅再生/"
                 "关系支持不解决初始供给,未知标 unresolved_initial_"
                 "supply,依显式策略处理,不称化学不可能;下游命中不"
                 "自动解决上游依赖"),
    }


# ---------------------------------------------------------------- 上下文


@dataclass
class PathContext:
    """路径上下文(§6 全字段;v3;分支隔离;JSON 往返)。

    scenario_ref:当前场景身份(F03)——curated_source 事实按其匹配
    适用;历史/来源场景事实(subject_scenario_ref 不匹配)不成为当前
    事实。context_id 冻结全部语义字段(F06;含 phase_history 与要求
    绑定)。

    phase_history(R2-04):scenario_transition 时冻结的旧阶段评估
    快照(environment_fit + per_requirement,含来源);只影响后续
    步骤,不追改此前步骤,也不写成反应边。路线聚合
    (route_assessment/assessed_scope)= 历史快照逐边合取 + 当前
    阶段 live 评估;本步评估(current_step_assessment)单独呈现。
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
    phase_history: list[dict] = field(default_factory=list)
    schema_version: str = PPV1_CONTEXT_SCHEMA_VERSION

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
            "scenario_transition": copy.deepcopy(self.scenario_transition),
            "phase_history": copy.deepcopy(self.phase_history),
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
            phase_history=copy.deepcopy(list(d.get("phase_history", []))),
        )

    # ---- 评估(两层:本步 vs 全路线,R2-04) ----

    def current_step_assessment(self) -> ConditionAssessment:
        """本步(当前阶段)评估:只含当前阶段有效绑定的必要要求,
        按当前阶段适用事实评估。"""
        reqs = [r for r in self.accumulated_requirements
                if _effective_phase(r, self.phase_id) == self.phase_id]
        return aggregate_environment_fit(
            facts=self.condition_facts, requirements=reqs,
            declared_scope=self.assessment_scope,
            scenario_ref=self.scenario_ref, phase_id=self.phase_id)

    def route_assessment(self) -> ConditionAssessment:
        """全路线评估:历史阶段快照(冻结)逐边合取 + 当前阶段 live。

        任何旧边冲突在路线结果中保持;旧要求不拿新阶段事实重评。
        空阶段(无可评估必要要求)不贡献未知,也不产生相容声明。
        """
        live = self.current_step_assessment()
        history = list(self.phase_history)
        if not history:
            return live
        contributors = [h for h in history
                        if h.get("has_gate_requirements")]
        live_has_reqs = bool(live.requirement_coverage["essential_keys"])
        if not contributors and not live_has_reqs:
            return live
        fits = [h["environment_fit"] for h in contributors]
        if live_has_reqs:
            fits.append(live.environment_fit)
        if CONFLICT in fits:
            fit = CONFLICT
        elif UNKNOWN in fits:
            fit = UNKNOWN
        else:
            fit = "compatible"
        per = [row for h in contributors
               for row in h.get("per_requirement", [])] \
            + (live.per_requirement if live_has_reqs else [])
        notes = [n for h in contributors
                 for n in h.get("preference_notes", [])] \
            + live.preference_notes
        key_status: dict[str, str] = {}
        for p in per:
            if p.get("status") == NOT_APPLICABLE:
                continue
            key_status[p["key"]] = _worst_status(
                [key_status.get(p["key"], SATISFIED), p["status"]])
        scopes = sorted({k for h in contributors
                         for k in h.get("assessment_scope", [])}
                        | set(live.assessment_scope if live_has_reqs
                              else []))
        assessed = {
            CONFLICT: ASSESSED_SCOPE_CONFLICTED,
            "compatible": ASSESSED_SCOPE_CONDITION_COMPATIBLE,
            UNKNOWN: ASSESSED_SCOPE_POSSIBLE,
        }[fit]
        return ConditionAssessment(
            per_requirement=per, environment_fit=fit,
            assessed_scope=assessed, assessment_scope=scopes,
            unassessed_dimensions=sorted(UNASSESSED_DIMENSIONS),
            requirement_coverage={
                "essential_keys": sorted(key_status),
                "assessed_keys": sorted(key_status),
                "satisfied_keys": sorted(k for k, s in key_status.items()
                                         if s == SATISFIED),
                "covered_keys": sorted(k for k, s in key_status.items()
                                       if s == SATISFIED),
                "unknown_keys": sorted(k for k, s in key_status.items()
                                       if s == UNKNOWN),
                "conflict_keys": sorted(k for k, s in key_status.items()
                                        if s == CONFLICT),
            },
            preference_notes=notes,
            declared_scope=live.declared_scope,
            scope_narrowed=live.scope_narrowed,
            scope_narrowed_by=live.scope_narrowed_by,
        )

    @property
    def assessed_scope(self) -> str:
        """路线级派生结果(历史快照 + 当前阶段;不继承
        requested_scope,C05/F02:旧边冲突保持,子评估不回 compatible)。"""
        return self.route_assessment().assessed_scope


def _context_hash(
    *, parent_context_ref: str, phase_id: str, requested_scope: str,
    facts: list[ConditionFact], requirements: list[Requirement],
    assumptions: list[str], dependency_refs: list[str],
    assessment_scope: list[str], scenario_ref: str,
    scenario_transition: dict | None, phase_history: list[dict],
) -> str:
    """context_id = 全部语义字段的冻结哈希(F06 + R2-04)。

    影响科学前提/评估范围/继承依赖/阶段历史的字段全部入哈希;S3 的
    缓存与图节点不得混用不同前提的上下文身份。
    """
    return stable_id(
        "pc", parent_context_ref, phase_id, requested_scope, scenario_ref,
        canonical_json([f.to_dict() for f in facts]),
        canonical_json([r.to_dict() for r in requirements]),
        canonical_json(sorted(assumptions)),
        canonical_json(sorted(dependency_refs)),
        canonical_json(sorted(assessment_scope)),
        canonical_json(scenario_transition or {}),
        canonical_json(phase_history or []))


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
    """构造根/独立上下文(分支各自构建,不共享可变对象)。

    要求在引入时绑定当前 phase_id/scenario_ref(R2-04;边为空 =
    根上下文引入)。
    """
    if requested_scope not in REQUESTED_SCOPES:
        raise ConditionContractError(
            f"requested_scope 非法:{requested_scope!r}",
            {"requested_scope": requested_scope})
    facts = [_fact_copy(f) for f in (condition_facts or [])]
    requirements = [
        _bind_requirement(_requirement_copy(r), phase_id=phase_id,
                          scenario_ref=scenario_ref, edge="")
        for r in (accumulated_requirements or [])]
    context_hash = _context_hash(
        parent_context_ref=parent_context_ref, phase_id=phase_id,
        requested_scope=requested_scope, facts=facts,
        requirements=requirements, assumptions=list(assumptions or []),
        dependency_refs=list(dependency_refs or []),
        assessment_scope=list(assessment_scope or []),
        scenario_ref=scenario_ref, scenario_transition=None,
        phase_history=[])
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
    step_edge_ref: str = "",
) -> PathContext:
    """子路径上下文 = 父事实/必要依赖 + 本步新增(分支隔离,C03)。

    F02:同键同场景不同要求**双方都保留**(按合取评估,不覆盖);
    仅语义完全相同(canonical JSON 一致)的要求去重。
    R2-04:scenario_transition(须带 source_ref)把父阶段评估冻结为
    phase_history 历史快照;转换只影响后续步骤,不追改此前步骤,
    也不写成反应边;旧要求保留原阶段绑定,不拿新阶段事实重评。
    step_edge_ref:本步边的最佳努力标识(hypothesis_id),随新引入
    要求保存。
    """
    if scenario_transition is not None:
        if not scenario_transition.get("source_ref"):
            raise ConditionContractError(
                "阶段转换必须有来源(用户/来源提供;不自行换场景)",
                {"scenario_transition": scenario_transition})
    phase_id = parent.phase_id
    scenario_ref = parent.scenario_ref
    if scenario_transition is not None:
        phase_id = str(scenario_transition.get("new_phase_id",
                                               parent.phase_id))
        scenario_ref = str(scenario_transition.get(
            "new_scenario_ref", parent.scenario_ref))
    merged: list[Requirement] = [
        _requirement_copy(r) for r in parent.accumulated_requirements]
    seen = {canonical_json(r.to_dict()) for r in merged}
    conflict_notes: list[str] = []
    parent_by_scope: dict[tuple[str, str, str], list[Requirement]] = {}
    for r in parent.accumulated_requirements:
        key = (_effective_phase(r, phase_id), r.introduced_scenario_ref,
               r.key)
        parent_by_scope.setdefault(key, []).append(r)
    for req in (step_requirements or []):
        bound = _bind_requirement(_requirement_copy(req),
                                  phase_id=phase_id,
                                  scenario_ref=scenario_ref,
                                  edge=step_edge_ref)
        sig = canonical_json(bound.to_dict())
        if sig in seen:
            continue  # 语义完全相同:去重
        merged.append(bound)
        seen.add(sig)
        scope_key = (bound.introduced_phase_id or phase_id,
                     bound.introduced_scenario_ref, bound.key)
        existing = parent_by_scope.get(scope_key)
        if existing:
            conflict_notes.append(
                f"requirement_differs_at_same_scenario:{bound.key}:"
                f"parent={[e.value for e in existing]},step={bound.value}"
                "(双方保留,按各自阶段适用事实合取评估;显式记录,不覆盖)")
    assumptions = list(parent.assumptions) + list(step_assumptions or []) \
        + conflict_notes
    phase_history = copy.deepcopy(list(parent.phase_history))
    if scenario_transition is not None:
        # 冻结父阶段评估为历史快照(旧边结果保留;不追改;不是反应边)
        snapshot = parent.current_step_assessment()
        phase_history.append({
            "phase_id": parent.phase_id,
            "scenario_ref": parent.scenario_ref,
            "environment_fit": snapshot.environment_fit,
            "assessed_scope": snapshot.assessed_scope,
            "assessment_scope": list(snapshot.assessment_scope),
            "per_requirement": copy.deepcopy(snapshot.per_requirement),
            "requirement_coverage": copy.deepcopy(
                snapshot.requirement_coverage),
            "preference_notes": list(snapshot.preference_notes),
            "has_gate_requirements": bool(
                snapshot.requirement_coverage["essential_keys"]),
            "snapshot_basis": "scenario_transition",
            "source_ref": scenario_transition.get("source_ref", ""),
        })
    child = PathContext(
        context_id="",
        parent_context_ref=parent.context_id,
        phase_id=phase_id,
        requested_scope=parent.requested_scope,
        condition_facts=[_fact_copy(f) for f in parent.condition_facts],
        accumulated_requirements=merged,
        assumptions=assumptions,
        dependency_refs=list(parent.dependency_refs)
        + list(step_dependency_refs or []),
        assessment_scope=list(parent.assessment_scope),
        scenario_ref=scenario_ref,
        scenario_transition=copy.deepcopy(scenario_transition),
        phase_history=phase_history,
    )
    child.context_id = _context_hash(
        parent_context_ref=parent.context_id, phase_id=phase_id,
        requested_scope=child.requested_scope,
        facts=child.condition_facts, requirements=merged,
        assumptions=assumptions,
        dependency_refs=child.dependency_refs,
        assessment_scope=child.assessment_scope,
        scenario_ref=scenario_ref,
        scenario_transition=scenario_transition,
        phase_history=phase_history)
    return child
