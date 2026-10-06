"""PathContext — 路径上下文、条件事实与证据依赖(v5 回修,S2)。

v5(ppv1-context-5 / ppv1-condition-assessment-5 / ppv1-dependency-5,
2026-10-07 R5 回修)相对 v4 的变化(Codex R4 复审 R4-03/04/05 +
R4-02 部分):
- **单位未知不满足(R4-03)**:带量纲且必须显式单位的键
  (temperature_C)空单位事实 = 原来源单位未知 ⇒ 评估
  **unknown(source_unit_unknown)**,不再按数值直比后以
  assumed_canonical 注记落 satisfied;显式规范单位 ⇒ canonical;
  非规范单位 ⇒ unit_mismatch(既有);pH 等无量纲键空单位合法,
  oxygen/matrix/物种键不受影响;
- **live 作用域含 scenario+phase(R4-04)**:live 判定与快照覆盖
  用 (引入场景, 引入阶段) 二元组 —— 同阶段名不同场景的旧要求不再
  被当前场景事实重评(旧边结论由 phase_history 快照承载);接口
  允许只转 scenario,不强迫改阶段名规避;
- **快照覆盖按具体要求签名(R4-04)**:冻结快照记录
  covered_requirement_signatures(该次评估实际覆盖的要求集合)——
  覆盖核对要求**具体要求**被评估,不再"阶段存在即覆盖";空快照
  不能掩盖孤儿必要要求(孤儿 ⇒ 显式 unknown);
- **依赖支持按轴当前有效状态(R4-05)**:每轴取最近一次解决结论
  (contradicted 撤销该轴此前的 supported;后续再生支持不洗掉已
  反驳的初始供给;恢复某轴须该轴新证据);总体 status:任一轴
  contradicted ⇒ contradicted,否则任一轴 supported ⇒ supported;
  support_axes = 当前有效支持轴(不再"曾经支持永久保留");
- **冻结 dict 封 __ior__(R4-02)**:`|=` 就地合并不经 __setitem__,
  子类不覆盖即静默改值;现在与 setitem/update 同样立即 TypeError。

v4(ppv1-context-4 / ppv1-condition-assessment-4 / ppv1-dependency-4,
2026-10-06 R4 回修)相对 v3 的变化(Codex R3-06/07/08/12 + §4 行 1/2/8):
- **路线快照消费入口(R3-06)**:新增 `assess_candidate_conditions(
  context, hypothesis)`——旧边取 phase_history 已记录的 environment_fit
  逐边合取(旧边评估用其记录值,**不拿当前事实重评**;任何旧边
  conflict ⇒ 总 conflict;旧边 unknown 计入 unknown);本候选新增要求
  (= hypothesis.requirements)一律在**当前 scenario+phase 作用域**用
  当前适用事实评估;仍在当前阶段的累积旧要求按 R3 语义 live 评估;
  绑定到无快照覆盖旧阶段的要求显式 unknown(不静默丢弃)。返回对象
  与 assess_conditions 同形状,detail 带逐边来源 route_edge_fits 与
  当前步/路线两层并列结论(§4 行 8)。跨阶段事实(空 phase_id)
  仍可服务多条边。audit 的条件检查改调本函数。
- **嵌套不可变(R3-08)**:Requirement/ConditionFact/Dependency 的
  嵌套集合(source_refs/区间 value/notes/轨迹)构造期深拷贝并转
  tuple/冻结映射;对自身嵌套值的就地修改立即失败,context_id 与
  内容不再"改而不变"。调用方持有原 list/dict 的后续修改不影响对象。
- **构造校验(R3-08)**:`validate_requirement_dict`(level/value 必填、
  level 枚举、区间 lo≤hi、已知条件键、来源/绑定字段类型,结构化
  kind)供假设侧与评估侧共用;`validate_context_object` 供 audit 入口
  对直接对象做缺/未知 schema 版本的结构化拒绝。
- **支持轴按轴保存(§4 行 2)**:resolve_dependency 的 support_axis
  不再"最近覆盖"——依赖按轴集合累积 support_axes;initial_supply
  supported 后再 regeneration supported ⇒ 两轴都在,启动未知不回退;
  初始供给轴无证据 ⇒ 该轴 unknown 保持。
- **继承依赖(R3-07)**:PathContext 新增 dependencies(Dependency
  对象,含 status/support_axes)累积字段,进 context_id 与 to_dict;
  `context.dependency_states()` 覆盖对象+裸引用(缺解析 ≠ 没有依赖)。
- **matrix 未知(R3-12)**:matrix 键无语义关系(无封闭枚举/注册映射/
  范围关系)的字符串不等 ⇒ unknown(matrix_value_unresolved);同字符串
  ⇒ satisfied。氧枚举与物种实体的既有行为不变。
- **单位注记(§4 行 1)**:要求值恒为键规范单位(build_requirement 不
  支持 unit 字段);事实无单位 ⇒ 仍按键规范单位比较,per-requirement
  带 `unit_basis: "assumed_canonical"`(区分已归一输入 "canonical" 与
  原来源单位未知);显式错误单位仍 unknown/unit_mismatch 不变。
- **to_dict 全科学载荷(R3-08)**:condition_facts、
  accumulated_requirements、assumptions、依赖对象(含 status/支持轴)、
  phase_history、requested/assessed scope、scenario_ref、context_id
  全部覆盖(供 audit input_hash 消费)。

v3(R2-04/05/06 + P2)语义保留:要求绑定所属边/阶段、阶段转换冻结
历史快照、本步/路线两层评估、区间×点三态、单位不匹配 unknown、
物种实体先匹配、再生分轴、scope/coverage/来源/basis 规则。

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

PPV1_CONTEXT_SUPPORTED_VERSIONS = (PPV1_CONTEXT_SCHEMA_VERSION,)

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
    CONDITION_KEY_TEMPERATURE: frozenset({"°C", "C", "celsius"}),
    CONDITION_KEY_PH: frozenset({"", "pH", "dimensionless"}),
}
# R4-03:带量纲且单位必须显式声明的键 —— 空单位事实 = 原来源单位未知
# ⇒ 评估 unknown(unit_basis=source_unit_unknown),不得靠
# assumed_canonical 注记落 satisfied/conflict;pH 无量纲("" 合法),
# oxygen/matrix/物种键恒不带单位,不一概判未知
UNIT_REQUIRED_KEYS = frozenset({CONDITION_KEY_TEMPERATURE})

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


# R3-06:要求的引入绑定字段(上下文层出处,属于引入时的边/阶段/场景)
REQUIREMENT_BINDING_FIELDS = (
    "introduced_phase_id", "introduced_scenario_ref", "introduced_edge")


class _FrozenValueDict(dict):
    """冻结的条件值映射(区间 {lo, hi} 等;R3-08)。

    dict 子类:构造后不可就地修改(修改立即 TypeError,不产生
    "改而不变"的身份漂移);与普通 dict 相等、可 JSON 序列化;
    deepcopy 返回冻结副本。to_dict 路径用 _thaw 转回普通可变副本。
    """

    __slots__ = ()

    def _immutable(self, *args, **kwargs):
        raise TypeError(
            "条件嵌套值已冻结(R3-08):就地修改被拒绝;请构造新对象,"
            "让身份随内容真实变化(冻结对象上的 append/update/setitem "
            "不再静默改变评估输入)")

    __setitem__ = _immutable
    __delitem__ = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable
    clear = _immutable
    # R4-02:dict.__ior__ 就地合并不经 __setitem__,子类若不覆盖即
    # 静默改值(复审 frozen_value_dict_ior_bypass 反例:
    # alias |= {"lo":20,"hi":30} 改必要区间而 context_id 不变)
    __ior__ = _immutable

    def __deepcopy__(self, memo):
        return _FrozenValueDict(
            {copy.deepcopy(k, memo): copy.deepcopy(v, memo)
             for k, v in self.items()})

    def __copy__(self):
        return _FrozenValueDict(self)


def _freeze(value):
    """深冻结嵌套值:dict ⇒ 冻结映射;list ⇒ tuple;标量原样。

    构造期调用,同时完成深拷贝(调用方持有的原容器后续修改不影响
    对象内容)。
    """
    if isinstance(value, dict):
        return _FrozenValueDict({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value):
    """冻结值 → 独立普通副本(to_dict 输出调用方可持有的可变载荷)。"""
    if isinstance(value, dict):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(v) for v in value]
    return value


def _check_finite(value, where: dict) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ConditionContractError(
            f"条件数值非有限:{value!r}", {**where, "value": repr(value)})


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------- 条件事实


@dataclass(frozen=True)
class ConditionFact:
    """一条条件事实(键/值/状态/来源/所属场景/阶段;不可变)。

    R3-08:嵌套区间 dict 构造期深拷贝并冻结——对自身 value 的就地
    修改立即失败;调用方持有原 dict 的后续修改不影响本对象。
    """

    key: str
    value: float | int | str | dict | None
    unit: str = ""
    status: str = FACT_STATUS_UNKNOWN
    origin: str = FACT_ORIGIN_USER_INPUT
    source_ref: str = ""
    subject_scenario_ref: str = ""   # 空=当前场景(user_input);非空须匹配
    phase_id: str = ""               # 非空=仅该阶段适用

    def __post_init__(self) -> None:
        # 深隔离 + 冻结(R3-08):嵌套区间 dict 深拷贝转冻结映射
        if isinstance(self.value, (dict, list)):
            object.__setattr__(self, "value", _freeze(self.value))

    def to_dict(self) -> dict:
        return {
            "key": self.key, "value": _thaw(self.value),
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

    不可变:引入时的所属绑定(introduced_phase_id/scenario_ref/
    introduced_edge = 边的 hypothesis_id,最佳努力)随要求保存,
    评估用该阶段适用事实。

    R3-08 嵌套不可变:source_refs/applicable_dimensions/observed_
    source_conditions 构造期深拷贝转 tuple;区间 value 转冻结映射——
    对自身嵌套集合的就地修改(append/__setitem__/update)立即失败,
    不再出现"内容改了、context_id 不变"的前提漂移;调用方持有原
    容器的后续修改不影响本对象。to_dict 输出普通可变副本。

    value_basis:range/point/optimum/label/entity/unspecified ——
    label 仅区间键(须注册表映射);entity 是物种/枚举/矩阵键字符串
    的实体/枚举身份比对;unspecified(单数值未声明)按 unknown 处理。
    """

    key: str
    level: str                        # essential | preference
    value: float | int | str | dict | None
    basis: str = REQUIREMENT_BASIS_ESSENTIAL_CLAIMED
    value_basis: str = ""
    source_refs: tuple[str, ...] = ()
    applicable_dimensions: tuple[str, ...] = ()
    observed_source_conditions: tuple[dict, ...] = ()
    note: str = ""
    introduced_phase_id: str = ""     # R2-04:引入阶段(空=未绑定)
    introduced_scenario_ref: str = ""  # R2-04:引入场景
    introduced_edge: str = ""         # R2-04:引入边(hypothesis_id)

    def __post_init__(self) -> None:
        # 深隔离 + 冻结 + basis 校验/推断(数据类直构路径同样把关)
        if isinstance(self.value, (dict, list)):
            object.__setattr__(self, "value", _freeze(self.value))
        object.__setattr__(self, "source_refs",
                           tuple(self.source_refs))
        object.__setattr__(self, "applicable_dimensions",
                           tuple(self.applicable_dimensions))
        object.__setattr__(
            self, "observed_source_conditions",
            tuple(_freeze(dict(x)) if isinstance(x, dict) else x
                  for x in self.observed_source_conditions))
        if not self.value_basis:
            object.__setattr__(self, "value_basis",
                               _infer_value_basis(self.key, self.value,
                                                  None))
        _validate_value_basis_shape(self.key, self.value, self.value_basis)

    def to_dict(self) -> dict:
        return {
            "key": self.key, "level": self.level,
            "value": _thaw(self.value), "basis": self.basis,
            "value_basis": self.value_basis,
            "source_refs": list(self.source_refs),
            "applicable_dimensions": list(self.applicable_dimensions),
            "observed_source_conditions": [
                _thaw(dict(x)) for x in self.observed_source_conditions],
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
    """构造要求(fail-closed 校验)。

    单位契约(R4-03):**要求值恒为键规范单位** —— 本构造器不支持
    unit 字段(单位只属于事实侧);带量纲键(temperature_C)的事实
    **必须显式携带键规范单位**才参与数值比较(评估 canonical),
    空单位 = 原来源单位未知 ⇒ 评估 unknown(source_unit_unknown),
    非规范单位 ⇒ unit_mismatch ⇒ unknown;pH 等无量纲键空单位合法。
    """
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
) -> tuple[str, str, list[str], dict]:
    """单项评估 → (status, reason, fact_sources, extras)。

    extras(R4-03):unit_basis —— 带量纲键(在 CONDITION_KEY_UNITS)
   的事实被消费时:显式规范单位 ⇒ "canonical"(已归一输入);
    必须显式单位的键(temperature_C)无单位 ⇒ **unknown +
    "source_unit_unknown"**(原来源单位未知;注记不把未知来源升级为
    satisfied/conflict,mimo 4.3 案 A);非规范单位 ⇒ unit_mismatch ⇒
    unknown;pH 等无量纲键空单位合法,不因本契约判未知。
    """
    # 文献观察条件不是必需条件:只作参考,不参与门禁
    if req.basis == REQUIREMENT_BASIS_OBSERVED_REFERENCE:
        return NOT_APPLICABLE, "observed_condition_reference_not_gating", \
            [], {}
    # 无来源必要性(F03):未核实假设 —— 不进门禁(不产生 conflict),
    # 也不作为"来源已证必需";阻止 compatible 由 unknown 语义承担
    if req.level == REQUIREMENT_ESSENTIAL and not req.source_refs:
        return UNKNOWN, "necessity_unsourced_not_gating", [], {}
    facts = fact_lists.get(req.key)
    if not facts:
        # 未列出某共底物 = 未知,不是 absent(C01/F03)
        return UNKNOWN, f"no_applicable_fact:{req.key}", [], {}
    sources = [f.source_ref for f in facts if f.source_ref]
    # 物种键:实体身份先匹配(R2-05)
    if req.key in SPECIES_CONDITION_KEYS and isinstance(req.value, str):
        status, reason, src = _assess_species_requirement(req, facts)
        return status, reason, src, {}
    # 单值维度:适用事实值真正不一致 → 保守 unknown(P2:同值不同
    # 来源不是不一致——按语义值签名比较,来源保留)
    known = [f for f in facts if f.status != FACT_STATUS_UNKNOWN]
    if len({_semantic_value_signature(f) for f in known}) > 1:
        return UNKNOWN, f"conflicting_applicable_facts:{req.key}", sources, \
            {}
    if any(f.status == FACT_STATUS_UNKNOWN for f in facts):
        return UNKNOWN, f"fact_unknown:{req.key}", sources, {}
    fact = facts[0]
    extras: dict = {}
    # 单位边界(R2-05 + R4-03):带量纲键的单位三态分立 ——
    # ① 必须显式单位的键(temperature_C)空单位 = 原来源单位未知 ⇒
    #   unknown(source_unit_unknown),不做数值比较;注记不能把未知
    #   来源升级为已归一;
    # ② 非规范单位(如温度给 K)⇒ unit_mismatch ⇒ unknown(首版无换算,
    #   不按数值直比);
    # ③ 无量纲键(pH ""/显式)与 oxygen/matrix/物种键不受影响,不因
    #   本契约判未知。
    if fact.key in CONDITION_KEY_UNITS:
        if fact.unit == "" and fact.key in UNIT_REQUIRED_KEYS:
            return (UNKNOWN,
                    f"source_unit_unknown:{fact.key}"
                    "(带量纲键的事实未声明单位=原来源单位未知;不按数值"
                    "直比,不以注记升级为已归一;单位归一由事实来源/适配"
                    "器承担)",
                    sources, {"unit_basis": "source_unit_unknown"})
        if not _unit_ok(fact.key, fact.unit):
            return (UNKNOWN,
                    f"unit_mismatch:{fact.key}:{fact.unit!r}"
                    f"(首版无换算,不按数值直比)", sources, {})
        # §4 行 1:显式规范单位 ⇒ 已归一输入(canonical)
        extras["unit_basis"] = "canonical"
    if req.value is None:
        return UNKNOWN, f"requirement_value_unspecified:{req.key}", \
            sources, extras
    # 定性标签:仅区间键须注册表映射;首版注册表为空 ⇒ unknown
    # (物种/枚举/矩阵键字符串是实体/枚举比对,不走 label/注册表)
    if req.value_basis == VALUE_BASIS_LABEL:
        if req.key in INTERVAL_CONDITION_KEYS and str(
                req.value) not in LABEL_RANGE_REGISTRY.get(req.key, {}):
            return UNKNOWN, \
                f"label_without_registered_range:{req.value!r}", sources, \
                extras
    # 最适值:永不产生 conflict(偏离只作 preference 提示)
    if req.value_basis == VALUE_BASIS_OPTIMUM:
        rel = _interval_relation(fact.value, req.value)
        if rel == SATISFIED:
            return SATISFIED, f"at_optimum:{req.key}", sources, extras
        preference_notes.append(
            f"optimum_deviation:{req.key}(最适 {req.value!r},实际 "
            f"{fact.value!r};偏离不构成冲突)")
        return NOT_APPLICABLE, "optimum_deviation_preference_not_gating", \
            sources, extras
    # 单数值未声明 basis:不自动推 optimum/point ⇒ unknown
    if req.value_basis == VALUE_BASIS_UNSPECIFIED and _is_number(
            req.value):
        return UNKNOWN, f"value_basis_unspecified:{req.key}", sources, \
            extras
    # point 语义:声明必需点值;事实为区间时双向分码(R2-05)
    if req.value_basis == VALUE_BASIS_POINT:
        if _is_number(fact.value) and _is_number(req.value):
            return ((SATISFIED if fact.value == req.value else CONFLICT),
                    (f"point_match:{req.key}" if fact.value == req.value
                     else f"point_mismatch:{req.key}"), sources, extras)
        if isinstance(fact.value, dict) and _is_number(req.value):
            lo, hi = fact.value["lo"], fact.value["hi"]
            if not (lo <= req.value <= hi):
                return (CONFLICT,
                        f"point_outside_interval:{req.key}", sources, extras)
            if lo == hi:
                return (SATISFIED,
                        f"point_in_degenerate_interval:{req.key}", sources,
                        extras)
            return (UNKNOWN,
                    f"point_in_uncertain_range:{req.key}", sources, extras)
    # 字符串比对:枚举键(封闭集)不匹配 ⇒ conflict(C02);matrix 键
    # 无语义关系(无封闭枚举/注册映射/范围关系)⇒ 文本不等只证明标签
    # 未解析,不证明环境不相容 ⇒ unknown(R3-12);同词 ⇒ satisfied
    if isinstance(req.value, str) and isinstance(fact.value, str):
        if req.value != fact.value:
            if req.key == CONDITION_KEY_MATRIX:
                return (UNKNOWN,
                        f"matrix_value_unresolved:{req.key}:"
                        f"{req.value}!={fact.value}"
                        "(无封闭枚举/注册映射/范围关系;文本不等不证明"
                        "不相容,同义词/包含关系须注册语义后方可判定)",
                        sources, extras)
            return (CONFLICT,
                    f"value_mismatch:{req.key}:{req.value}!={fact.value}",
                    sources, extras)
        return SATISFIED, f"value_match:{req.key}", sources, extras
    status = _interval_relation(fact.value, req.value)
    reason = {
        SATISFIED: f"within_range:{req.key}",
        CONFLICT: f"range_disjoint_or_outside:{req.key}",
        UNKNOWN: f"partial_overlap_or_point_unknown:{req.key}",
    }[status]
    return status, reason, sources, extras


def _effective_phase(req: Requirement, context_phase_id: str) -> str:
    """要求的有效评估阶段:引入绑定优先,未绑定 = 当前阶段。"""
    return req.introduced_phase_id or context_phase_id


def _effective_scope(req: Requirement, context_scenario_ref: str,
                     context_phase_id: str) -> tuple[str, str]:
    """要求的有效评估作用域(R4-04):(引入场景, 引入阶段)。

    引入绑定优先(场景空 = 未绑定,视作当前场景);live 判定必须
    scenario+phase **同时**匹配 —— 只比 phase 会让"同阶段名、不同
    场景"的旧要求被当前场景事实重评(复审 new_same_local_phase_
    different_scenario 反例:旧有氧要求在 sB:p0 被无氧事实重评出
    conflict);接口允许只转 scenario,不强迫改阶段名规避。
    """
    return (req.introduced_scenario_ref or context_scenario_ref,
            req.introduced_phase_id or context_phase_id)


def _requirement_covered_by_snapshot(
        req: Requirement, phase_history: list[dict],
        context_scenario_ref: str, context_phase_id: str) -> bool:
    """快照覆盖核对(R4-04):**具体要求**的评估被快照承载,而非仅
    阶段存在。

    derive_child_context 冻结快照时记录 covered_requirement_
    signatures(该次评估实际覆盖的全部要求签名);覆盖 = 存在快照
    其 (phase_id, scenario_ref) 匹配该要求的引入作用域,且其签名
    ∈ covered_requirement_signatures。空快照(无必要要求)不再掩盖
    孤儿必要要求(复审 orphan_covered_by_empty_unrelated_snapshot
    反例:空快照的 has_gate_requirements=False 使绑定 p0 的 essential
    pH 从评估中消失,audit verified/R6)。
    """
    scenario, phase = _effective_scope(req, context_scenario_ref,
                                       context_phase_id)
    sig = canonical_json(req.to_dict())
    for h in phase_history:
        if h.get("phase_id") != phase:
            continue
        if req.introduced_scenario_ref and \
                h.get("scenario_ref") != req.introduced_scenario_ref:
            continue
        if sig in (h.get("covered_requirement_signatures") or []):
            return True
    return False


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
    # R3-06/§4 行 8:评估 detail(双层结论 + 逐边来源 route_edge_fits;
    # per-requirement 级注记如 unit_basis 直接附在逐行结果上)
    detail: dict = field(default_factory=dict)

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
        status, reason, sources, extras = _assess_requirement(
            req, fact_lists, notes)
        row = {"key": req.key, "level": req.level, "status": status,
               "reason": reason, "basis": req.basis,
               "value_basis": req.value_basis,
               "sourced": bool(req.source_refs),
               "introduced_phase_id": _effective_phase(req, phase_id),
               "introduced_edge": req.introduced_edge,
               "fact_sources": sources}
        row.update(extras)  # §4 行 1:unit_basis 等逐行注记
        per.append(row)
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

    R3-06 说明:本函数保留为"累积重评"语义(逐条按其引入阶段过滤
    当前事实集合评估);**审计的条件检查应改调
    assess_candidate_conditions**——后者消费 phase_history 路线快照
    (旧边用记录值,不拿当前事实重评)并把本候选新增要求放在当前
    作用域评估,本函数在跨场景转换后会用当前事实集合重评旧边要求
    (R3-06 两行反例的根源)。
    """
    hyp_id = ""
    if isinstance(hypothesis, dict):
        hyp_id = str(hypothesis.get("hypothesis_id", ""))
        hyp_reqs = hypothesis.get("requirements", [])
    else:
        hyp_id = str(getattr(hypothesis, "hypothesis_id", "") or "")
        hyp_reqs = getattr(hypothesis, "requirements", None)
    hyp_reqs = list(hyp_reqs or [])
    merged: list[Requirement] = list(context.accumulated_requirements)
    existing = {canonical_json(r.to_dict()) for r in merged}
    for i, raw in enumerate(hyp_reqs):
        if isinstance(raw, Requirement):
            req = _requirement_copy(raw)
        elif isinstance(raw, dict):
            validate_requirement_dict(
                raw, where={"requirement_index": i})
            req = Requirement(**dict(raw))
        else:
            raise ConditionContractError(
                f"假设要求必须是 dict 或 Requirement:"
                f"{type(raw).__name__}",
                {"kind": "requirement_object_not_supported",
                 "requirement_index": i})
        req = _bind_requirement(
            req, phase_id=context.phase_id,
            scenario_ref=context.scenario_ref,
            edge=hyp_id)
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


def assess_candidate_conditions(
        context: PathContext, hypothesis) -> ConditionAssessment:
    """R3-06 契约入口:路线快照消费 + 本候选新增要求当前作用域评估。

    - **旧边路线快照**:context.phase_history 中已记录的各边
      environment_fit 逐边合取——任何旧边 conflict ⇒ 总 conflict;
      旧边 unknown ⇒ 计入 unknown;**旧边评估用其记录值,不拿当前
      事实重评**(不消费跨场景的当前事实集合);
    - **本候选新增要求** = hypothesis.requirements(调用方传给
      build_hypothesis 的新要求),一律在**当前 scenario+phase 作用域**
      用当前适用事实评估(重绑定为当前 phase/scenario/本假设边;
      外来预填绑定在构造入口已被 foreign_requirement_binding 拒绝,
      dict 直入路径在此重绑定防绕过);
    - **context 累积旧要求并入路线语义**:已由 phase_history 快照
      承载的按快照;仍在当前阶段的按 R3 语义 live 评估;绑定到
      无快照覆盖旧阶段的 ⇒ 显式 unknown(不静默丢弃,不重评);
    - 跨阶段事实(空 phase_id)可服务多条边(保持);
    - 返回对象与 assess_conditions 同形状;detail 带逐边来源
      route_edge_fits 与当前步/路线两层并列结论(§4 行 8:任一层
      单独出现不得代表整体)。
    """
    if isinstance(hypothesis, dict):
        hyp_id = str(hypothesis.get("hypothesis_id", ""))
        raw_reqs = list(hypothesis.get("requirements") or [])
    else:
        hyp_id = str(getattr(hypothesis, "hypothesis_id", "") or "")
        raw_reqs = list(getattr(hypothesis, "requirements", None) or [])
    # 本候选新增要求:重绑定为当前作用域(R3-06 核心语义)
    new_reqs: list[Requirement] = []
    for i, raw in enumerate(raw_reqs):
        if isinstance(raw, Requirement):
            req = _requirement_copy(raw)
        elif isinstance(raw, dict):
            validate_requirement_dict(
                raw, where={"requirement_index": i})
            req = Requirement(**dict(raw))
        else:
            raise ConditionContractError(
                f"假设要求必须是 dict 或 Requirement:"
                f"{type(raw).__name__}",
                {"kind": "requirement_object_not_supported",
                 "requirement_index": i})
        new_reqs.append(Requirement(
            key=req.key, level=req.level, value=req.value,
            basis=req.basis, value_basis=req.value_basis,
            source_refs=tuple(req.source_refs),
            applicable_dimensions=tuple(req.applicable_dimensions),
            observed_source_conditions=tuple(
                req.observed_source_conditions),
            note=req.note,
            introduced_phase_id=context.phase_id,
            introduced_scenario_ref=context.scenario_ref,
            introduced_edge=hyp_id))
    # 当前阶段 live(R4-04:scenario+phase 同时匹配;仍在当前作用域的
    # 累积旧要求 + 本候选新要求)
    live_reqs = [r for r in context.accumulated_requirements
                 if _effective_scope(r, context.scenario_ref,
                                     context.phase_id)
                 == (context.scenario_ref, context.phase_id)]
    merged = list(live_reqs)
    seen = {canonical_json(r.to_dict()) for r in merged}
    for req in new_reqs:
        sig = canonical_json(req.to_dict())
        if sig not in seen:  # F02:仅语义完全相同去重
            merged.append(req)
            seen.add(sig)
    live = aggregate_environment_fit(
        facts=context.condition_facts, requirements=merged,
        declared_scope=context.assessment_scope,
        scenario_ref=context.scenario_ref, phase_id=context.phase_id)
    # 旧边:phase_history 记录值(不重评)
    history = [h for h in context.phase_history
               if h.get("has_gate_requirements")]
    # 孤儿绑定:绑定旧作用域且无快照**按签名**承载 ⇒ 显式未知
    # (fail-closed;R4-04:阶段存在 ≠ 覆盖,空快照不能掩盖孤儿必要要求)
    orphan_rows: list[dict] = []
    for r in context.accumulated_requirements:
        eff_scope = _effective_scope(r, context.scenario_ref,
                                     context.phase_id)
        if eff_scope == (context.scenario_ref, context.phase_id):
            continue
        if _requirement_covered_by_snapshot(
                r, context.phase_history, context.scenario_ref,
                context.phase_id):
            continue
        orphan_rows.append({
            "key": r.key, "level": r.level, "status": UNKNOWN,
            "reason": (f"requirement_binding_not_in_route_snapshot:"
                       f"{eff_scope[0]}:{eff_scope[1]}"
                       "(绑定旧作用域且无历史快照按签名承载该要求的评估;"
                       "显式未知,不静默丢弃,也不拿当前事实重评)"),
            "basis": r.basis, "value_basis": r.value_basis,
            "sourced": bool(r.source_refs),
            "introduced_phase_id": eff_scope[1],
            "introduced_edge": r.introduced_edge,
            "fact_sources": [],
            "route_edge_source": "orphan_binding",
        })
    # 路线合取:旧边记录值 + 当前边 live
    fits = [h["environment_fit"] for h in history]
    live_has = bool(live.requirement_coverage["essential_keys"])
    if live_has:
        fits.append(live.environment_fit)
    if CONFLICT in fits:
        fit = CONFLICT
    elif UNKNOWN in fits or orphan_rows or not fits:
        fit = UNKNOWN   # 空要求列表不自动相容;孤儿绑定计入未知
    else:
        fit = "compatible"
    # 逐条结果:旧边快照行(标记来源) + 当前步行 + 孤儿行
    per: list[dict] = []
    notes: list[str] = []
    for h in history:
        tag = f"phase_history:{h.get('phase_id')}/{h.get('scenario_ref')}"
        for row in h.get("per_requirement", []):
            out = dict(row)
            out["route_edge_source"] = tag
            per.append(out)
        notes.extend(h.get("preference_notes", []))
    for row in live.per_requirement:
        out = dict(row)
        out["route_edge_source"] = "current_step"
        per.append(out)
    notes.extend(live.preference_notes)
    per.extend(orphan_rows)
    key_status: dict[str, str] = {}
    for p in per:
        if p.get("status") == NOT_APPLICABLE:
            continue
        key_status[p["key"]] = _worst_status(
            [key_status.get(p["key"], SATISFIED), p["status"]])
    scopes = sorted(
        {k for h in history for k in h.get("assessment_scope", [])}
        | set(live.assessment_scope if live_has else []))
    assessed = {
        CONFLICT: ASSESSED_SCOPE_CONFLICTED,
        "compatible": ASSESSED_SCOPE_CONDITION_COMPATIBLE,
        UNKNOWN: ASSESSED_SCOPE_POSSIBLE,
    }[fit]
    route_edge_fits: list[dict] = [
        {"phase_id": h.get("phase_id"),
         "scenario_ref": h.get("scenario_ref"),
         "environment_fit": h.get("environment_fit"),
         "source": "phase_history",
         "snapshot_basis": h.get("snapshot_basis", ""),
         "source_ref": h.get("source_ref", "")}
        for h in history]
    if live_has:
        route_edge_fits.append({
            "phase_id": context.phase_id,
            "scenario_ref": context.scenario_ref,
            "environment_fit": live.environment_fit,
            "source": "current_step_candidate"})
    return ConditionAssessment(
        per_requirement=per, environment_fit=fit, assessed_scope=assessed,
        assessment_scope=scopes,
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
        detail={
            "route_edge_fits": route_edge_fits,
            # §4 行 8:两层结论并列——当前步(本候选 live)与
            # 路线(历史快照合取);任一层单独出现不得代表整体
            "current_step_environment_fit": live.environment_fit,
            "route_environment_fit": fit,
            "semantics": ("route_snapshot_edges(recorded_values)"
                          "+candidate_requirements(current_scope)"),
        },
    )


def validate_context_object(context) -> None:
    """直接 context 对象的版本门(R3-08;audit 入口接线用)。

    缺 schema_version / 未知版本 ⇒ 结构化 ConditionContractError
    (kind:context_schema_version_missing / context_schema_version_
    unknown);非 PathContext ⇒ context_object_invalid_type。
    合法对象返回 None。from_dict 已有同款门;本函数覆盖**直接对象**
    (绕过 from_dict 的调用路径)。
    """
    if not isinstance(context, PathContext):
        raise ConditionContractError(
            f"audit 输入必须是 PathContext 对象:"
            f"{type(context).__name__}",
            {"kind": "context_object_invalid_type",
             "got": type(context).__name__})
    version = getattr(context, "schema_version", None)
    if not version:
        raise ConditionContractError(
            "PathContext 缺 schema_version(直接对象版本门;fail-closed)",
            {"kind": "context_schema_version_missing"})
    if version not in PPV1_CONTEXT_SUPPORTED_VERSIONS:
        raise ConditionContractError(
            f"PathContext schema 版本未知:{version!r}(支持 "
            f"{list(PPV1_CONTEXT_SUPPORTED_VERSIONS)};fail-closed)",
            {"schema_version": version,
             "kind": "context_schema_version_unknown"})


def validate_requirement_dict(raw: dict,
                              where: dict | None = None) -> None:
    """要求字典的构造期契约校验(R3-08;结构化 kind,fail-closed)。

    hypothesis.build_hypothesis 与评估入口(assess_conditions /
    assess_candidate_conditions / PathContext.from_dict)共用:
    - 元素必须是 dict(Requirement 对象在假设入口不受支持,由调用方
      转结构化错误;本函数对非 dict 同样结构化拒绝);
    - level 必填且 ∈ {essential, preference};value 必填(键缺失拒);
    - key 必须是已知条件键;区间值 lo ≤ hi;
    - basis/value_basis 合法且与值形状一致(复用
      _validate_value_basis_shape);
    - source_refs/applicable_dimensions/observed_source_conditions 与
      绑定字段类型校验;未知字段拒绝(不静默忽略)。
    """
    ctx = dict(where or {})
    if not isinstance(raw, dict):
        raise ConditionContractError(
            f"要求必须是 dict:{type(raw).__name__}(Requirement 对象"
            "在假设/评估字典入口不受支持)",
            {"kind": "requirement_object_not_supported",
             "got": type(raw).__name__, **ctx})
    known_fields = {
        "key", "level", "value", "basis", "value_basis", "source_refs",
        "applicable_dimensions", "observed_source_conditions", "note",
        *REQUIREMENT_BINDING_FIELDS,
    }
    for k in raw:
        if k not in known_fields:
            raise ConditionContractError(
                f"要求含未知字段:{k!r}(允许 {sorted(known_fields)})",
                {"kind": "unknown_requirement_field", "field": k, **ctx})
    for required in ("key", "level", "value"):
        if required not in raw:
            raise ConditionContractError(
                f"要求缺必填字段:{required}",
                {"kind": "missing_requirement_field", "field": required,
                 **ctx})
    key = raw["key"]
    if not isinstance(key, str) or key not in CONDITION_KEYS:
        raise ConditionContractError(
            f"未知条件键:{key!r}(第一版限定 {sorted(CONDITION_KEYS)})",
            {"kind": "unknown_condition_key", "key": key, **ctx})
    level = raw["level"]
    if not isinstance(level, str) or level not in REQUIREMENT_LEVELS:
        raise ConditionContractError(
            f"要求级别非法:{level!r}(允许 "
            f"{sorted(REQUIREMENT_LEVELS)})",
            {"kind": "invalid_requirement_level", "level": level, **ctx})
    basis = raw.get("basis", REQUIREMENT_BASIS_ESSENTIAL_CLAIMED)
    if basis not in (REQUIREMENT_BASIS_ESSENTIAL_CLAIMED,
                     REQUIREMENT_BASIS_OBSERVED_REFERENCE):
        raise ConditionContractError(
            f"要求依据非法:{basis!r}", {"kind": "invalid_requirement_basis",
                                    "basis": basis, **ctx})
    value = raw["value"]
    where2 = {"key": key, **ctx}
    if isinstance(value, bool):
        raise ConditionContractError(
            f"要求值类型非法(bool):{value!r}",
            {"kind": "invalid_requirement_value", "value": repr(value),
             **ctx})
    if isinstance(value, float):
        _check_finite(value, where2)
    if key in INTERVAL_CONDITION_KEYS and isinstance(value, dict):
        try:
            _validate_interval(value, where2)
        except ConditionContractError as exc:
            raise ConditionContractError(
                str(exc), {**exc.detail, "kind": "invalid_interval",
                           **ctx}) from exc
    if key == CONDITION_KEY_OXYGEN and isinstance(value, str) and \
            value not in OXYGEN_REGIME_VALUES:
        raise ConditionContractError(
            f"oxygen_regime 要求取值非法:{value!r}(允许 "
            f"{sorted(OXYGEN_REGIME_VALUES)})",
            {"kind": "invalid_oxygen_value", "value": value, **ctx})
    value_basis = raw.get("value_basis", "")
    if value_basis:
        if not isinstance(value_basis, str) or \
                value_basis not in VALUE_BASES:
            raise ConditionContractError(
                f"值语义 basis 非法:{value_basis!r}(允许 "
                f"{sorted(VALUE_BASES)})",
                {"kind": "invalid_value_basis", "basis": value_basis,
                 **ctx})
        _validate_value_basis_shape(key, value, value_basis)
    else:
        # 未声明 ⇒ 按推断复核形状(与 Requirement.__post_init__ 同规则)
        _validate_value_basis_shape(
            key, value, _infer_value_basis(key, value, None))
    for field_name, item_kind in (
            ("source_refs", "invalid_source_refs"),
            ("applicable_dimensions", "invalid_applicable_dimensions")):
        items = raw.get(field_name)
        if items is None:
            continue
        if not isinstance(items, (list, tuple)) or not all(
                isinstance(x, str) for x in items):
            raise ConditionContractError(
                f"{field_name} 必须是字符串列表:{items!r}",
                {"kind": item_kind, "field": field_name, **ctx})
    observed = raw.get("observed_source_conditions")
    if observed is not None and (
            not isinstance(observed, (list, tuple))
            or not all(isinstance(x, dict) for x in observed)):
        raise ConditionContractError(
            f"observed_source_conditions 必须是 dict 列表:{observed!r}",
            {"kind": "invalid_observed_source_conditions", **ctx})
    note = raw.get("note", "")
    if not isinstance(note, str):
        raise ConditionContractError(
            f"note 必须是字符串:{note!r}",
            {"kind": "invalid_requirement_note", **ctx})
    for field_name in REQUIREMENT_BINDING_FIELDS:
        binding = raw.get(field_name, "")
        if not isinstance(binding, str):
            raise ConditionContractError(
                f"要求绑定字段 {field_name} 必须是字符串:{binding!r}",
                {"kind": "invalid_requirement_binding_type",
                 "field": field_name, **ctx})


# ---------------------------------------------------------------- 依赖


@dataclass(frozen=True)
class Dependency:
    """证据依赖(§6;status 固定三值;解决保留轨迹;不可变)。

    R2-06 支持分轴;R4-05 改为**按轴当前有效状态**:
    - resolution_log 是轴状态的唯一事实源 —— 每轴取其**最近一次**
      解决事件的结论(contradicted 撤销该轴此前的 supported);
    - support_axes = **当前有效支持**的轴集合(不再"曾经支持过就
      永久保留"——复审 contradicted_initial_axis_restored_by_
      regeneration 反例:initial_supply supported→该轴 contradicted→
      仅 regeneration supported,support_axes 仍保留初始支持、全局
      status=supported,audit 当作已解决进 R6);
    - 总体 status:任一轴当前 contradicted ⇒ contradicted;否则任一
      轴当前 supported ⇒ supported;否则 unresolved;
    - 恢复某轴须有**该轴**新证据(该轴新的 supported 事件;
      regeneration 支持不重新证明已反驳的初始供给);
    - 重复引用不升级支持(轨迹如实追加,不乘分数)。

    R3-08 嵌套不可变:source_refs/resolution_log 构造期深拷贝转
    tuple/冻结映射——对自身轨迹的就地修改立即失败。
    """

    dependency_id: str
    kind: str                      # cosubstrate_supply | mechanism | …
    statement: str
    status: str = DEPENDENCY_UNRESOLVED
    source_refs: tuple[str, ...] = ()
    introduced_at_hypothesis_id: str = ""
    resolution_log: tuple[dict, ...] = ()
    support_axis: str = SUPPORT_AXIS_REACTION  # 最近一次解决声明的轴
    support_axes: tuple[str, ...] = ()  # R4-05:当前有效支持的轴集合
    schema_version: str = PPV1_DEPENDENCY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        object.__setattr__(
            self, "resolution_log",
            tuple(_freeze(dict(x)) if isinstance(x, dict) else x
                  for x in self.resolution_log))
        # R4-05:轨迹存在 ⇒ 轴状态/总体状态从轨迹重推导(构造入口
        # 同一把关,serialization 往返不漂移);无轨迹的旧载荷兼容
        # (仅 support_axis + supported)按其唯一轴补齐,不丢失轴信息
        states = _axis_states_from_log(self.resolution_log)
        if states:
            object.__setattr__(
                self, "support_axes",
                tuple(sorted(a for a, s in states.items()
                             if s == DEPENDENCY_SUPPORTED)))
            object.__setattr__(self, "status",
                               _overall_status_from_axis_states(states))
        elif not self.support_axes and self.support_axis and \
                self.status == DEPENDENCY_SUPPORTED:
            object.__setattr__(self, "support_axes",
                               (self.support_axis,))

    def to_dict(self) -> dict:
        return {
            "dependency_id": self.dependency_id, "kind": self.kind,
            "statement": self.statement, "status": self.status,
            "source_refs": list(self.source_refs),
            "introduced_at_hypothesis_id":
                self.introduced_at_hypothesis_id,
            "resolution_log": [_thaw(dict(x)) for x in self.resolution_log],
            "support_axis": self.support_axis,
            "support_axes": list(self.support_axes),
            "schema_version": self.schema_version,
        }


def _axis_states_from_log(
        resolution_log: tuple[dict, ...]) -> dict[str, str]:
    """轨迹 → 每轴最近一次解决结论(R4-05 轴状态的事实源)。"""
    states: dict[str, str] = {}
    for entry in resolution_log:
        if not isinstance(entry, dict):
            continue
        axis = str(entry.get("support_axis", "") or "")
        resolution = str(entry.get("resolution", "") or "")
        if axis in SUPPORT_AXES and resolution in (
                DEPENDENCY_SUPPORTED, DEPENDENCY_CONTRADICTED):
            states[axis] = resolution
    return states


def _overall_status_from_axis_states(states: dict[str, str]) -> str:
    """轴状态 → 总体状态(R4-05:任一轴 contradicted ⇒ contradicted;
    否则任一轴 supported ⇒ supported;否则 unresolved)。"""
    if DEPENDENCY_CONTRADICTED in states.values():
        return DEPENDENCY_CONTRADICTED
    if DEPENDENCY_SUPPORTED in states.values():
        return DEPENDENCY_SUPPORTED
    return DEPENDENCY_UNRESOLVED


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

    R4-05 **按轴当前有效状态**(不再"最近覆盖"或"曾经支持永久保留"):
    - 该轴取本次事件结论;其他轴保留各自最近结论(contradicted
      撤销该轴此前的 supported;后续再生支持不洗掉已反驳的初始供给);
    - support_axes = 当前有效支持的轴;总体 status:任一轴
      contradicted ⇒ contradicted,否则任一轴 supported ⇒ supported;
    - 恢复某轴须有该轴新证据(该轴新的 supported 事件);
    - 重复引用不升级支持(轨迹如实追加,不乘分数)。
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
    log = list(dep.resolution_log)
    log.append({"resolution": resolution, "evidence": list(new_evidence),
                "note": note, "support_axis": support_axis})
    states = _axis_states_from_log(tuple(
        _freeze(dict(x)) if isinstance(x, dict) else x for x in log))
    return Dependency(
        dependency_id=dep.dependency_id, kind=dep.kind,
        statement=dep.statement,
        status=_overall_status_from_axis_states(states),
        source_refs=tuple(dep.source_refs),
        introduced_at_hypothesis_id=dep.introduced_at_hypothesis_id,
        resolution_log=log,
        support_axis=support_axis,
        support_axes=tuple(sorted(a for a, s in states.items()
                                  if s == DEPENDENCY_SUPPORTED)),
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
    """共底物供给环诊断(§17.4 H04;R2-06/§4 行 2:支持分轴按轴累积)。

    - 多边图(同源可有多个供给目标),DFS 检出全部简单环;
    - **启动供给与关系支持分轴**:环上没有任何 initial_supply 轴
      支持的依赖 ⇒ 计入 unresolved_initial_supply(未知启动供给,
      依显式策略处理,不称化学不可能);环上全部关系 supported
      (含 regeneration)只表示关系成立,**不**删除启动未知;
      支持轴按轴集合累积(support_axes),后续 regeneration 支持
      不覆盖/回退已支持的 initial_supply 轴;
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
        # §4 行 2:初始供给轴按累积集合判定(不被后续再生支持覆盖)
        has_initial = any(
            d.status == DEPENDENCY_SUPPORTED
            and SUPPORT_AXIS_INITIAL_SUPPLY in d.support_axes
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
                 "supply,依显式策略处理,不称化学不可能;支持轴按轴"
                 "累积不回退;下游命中不自动解决上游依赖"),
    }


# ---------------------------------------------------------------- 上下文


@dataclass
class PathContext:
    """路径上下文(§6 全字段;v4;分支隔离;JSON 往返)。

    scenario_ref:当前场景身份(F03)——curated_source 事实按其匹配
    适用;历史/来源场景事实(subject_scenario_ref 不匹配)不成为当前
    事实。context_id 冻结全部语义字段(F06;含 phase_history、要求
    绑定与**依赖对象及其解析状态/支持轴**,R3-08)。

    phase_history(R2-04):scenario_transition 时冻结的旧阶段评估
    快照(environment_fit + per_requirement,含来源);只影响后续
    步骤,不追改此前步骤,也不写成反应边。路线聚合
    (route_assessment/assessed_scope)= 历史快照逐边合取 + 当前
    阶段 live 评估;本步评估(current_step_assessment)单独呈现。
    R3-06:审计消费入口为 assess_candidate_conditions(模块级函数,
    快照记录值 + 本候选新要求当前作用域)。

    dependencies(R3-07):上下文累积的依赖对象(含 status/支持轴);
    dependency_states() 覆盖对象与裸引用——**缺解析 ≠ 没有依赖**,
    audit 侧做 hypothesis.dependency_refs ∪ context 依赖并集。
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
    dependencies: list[Dependency] = field(default_factory=list)
    assessment_scope: list[str] = field(default_factory=list)
    scenario_ref: str = ""
    scenario_transition: dict | None = None
    phase_history: list[dict] = field(default_factory=list)
    schema_version: str = PPV1_CONTEXT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        """全部科学载荷(R3-08:audit input_hash 消费 content_hash(
        to_dict());requested/assessed scope、依赖对象(含 status/
        支持轴)、phase_history、场景/阶段、context_id 全覆盖)。"""
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
            "dependencies": [d.to_dict() for d in self.dependencies],
            "assessment_scope": list(self.assessment_scope),
            "scenario_ref": self.scenario_ref,
            "scenario_transition": copy.deepcopy(self.scenario_transition),
            "phase_history": copy.deepcopy(self.phase_history),
            # 路线级派生结果(历史快照 + 当前阶段;派生字段,from_dict
            # 不回读)
            "assessed_scope": self.assessed_scope,
        }

    def dependency_states(self) -> dict[str, dict]:
        """上下文累积依赖的解析状态(R3-07;契约:audit 做
        hypothesis.dependency_refs ∪ 本结果并集)。

        返回 {dependency_id: {"status": supported|contradicted|
        unresolved, "support_axes": [当前有效支持轴(R4-05)],
        "axis_status": {axis: supported|contradicted(逐轴当前
        有效状态)}, "statement": str}}——覆盖依赖**对象**与**裸引用**:
        裸引用无对象/无解析 ⇒ unresolved(引用存在但解析未提供,不等于
        没有依赖);空上下文 ⇒ 空字典。
        """
        states: dict[str, dict] = {}
        for dep in self.dependencies:
            axis_states = _axis_states_from_log(dep.resolution_log)
            states[dep.dependency_id] = {
                "status": dep.status,
                "support_axes": sorted(dep.support_axes),
                "axis_status": dict(sorted(axis_states.items())),
                "statement": dep.statement,
            }
        for ref in self.dependency_refs:
            if ref not in states:
                states[ref] = {"status": DEPENDENCY_UNRESOLVED,
                               "support_axes": [], "axis_status": {},
                               "statement": ""}
        return states

    @classmethod
    def from_dict(cls, d: dict) -> "PathContext":
        version = d.get("schema_version")
        if version not in PPV1_CONTEXT_SUPPORTED_VERSIONS:
            raise ConditionContractError(
                f"PathContext schema 版本未知:{version!r}(支持 "
                f"{list(PPV1_CONTEXT_SUPPORTED_VERSIONS)};fail-closed)",
                {"schema_version": version,
                 "kind": "context_schema_version_unknown"})
        dependencies = []
        for raw_dep in d.get("dependencies", []):
            if not isinstance(raw_dep, dict):
                raise ConditionContractError(
                    "上下文依赖载荷必须是 dict", {"kind":
                    "context_dependency_invalid_type"})
            dependencies.append(Dependency(**raw_dep))
        requirements = []
        for raw in d.get("accumulated_requirements", []):
            if isinstance(raw, Requirement):
                requirements.append(_requirement_copy(raw))
                continue
            validate_requirement_dict(raw)
            requirements.append(Requirement(**dict(raw)))
        return cls(
            context_id=d["context_id"],
            parent_context_ref=d.get("parent_context_ref", ""),
            phase_id=d.get("phase_id", ""),
            requested_scope=d.get("requested_scope",
                                  REQUESTED_SCOPE_POSSIBLE),
            condition_facts=[ConditionFact(**f)
                             for f in d.get("condition_facts", [])],
            accumulated_requirements=requirements,
            assumptions=list(d.get("assumptions", [])),
            dependency_refs=list(d.get("dependency_refs", [])),
            dependencies=dependencies,
            assessment_scope=list(d.get("assessment_scope", [])),
            scenario_ref=d.get("scenario_ref", ""),
            scenario_transition=d.get("scenario_transition"),
            phase_history=copy.deepcopy(list(d.get("phase_history", []))),
        )

    # ---- 评估(两层:本步 vs 全路线,R2-04) ----

    def current_step_assessment(self) -> ConditionAssessment:
        """本步(当前阶段)评估:只含当前阶段有效绑定的必要要求,
        按当前阶段适用事实评估。

        R4-04:live 判定含 scenario+phase —— 引入场景 ≠ 当前场景的
        要求不 live(其结论由 phase_history 快照承载,不拿当前场景
        事实重评);跨阶段事实(空 phase_id)仍可服务多条边。
        """
        reqs = [r for r in self.accumulated_requirements
                if _effective_scope(r, self.scenario_ref, self.phase_id)
                == (self.scenario_ref, self.phase_id)]
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
    dependencies: list[Dependency],
    assessment_scope: list[str], scenario_ref: str,
    scenario_transition: dict | None, phase_history: list[dict],
) -> str:
    """context_id = 全部语义字段的冻结哈希(F06 + R2-04 + R3-08)。

    影响科学前提/评估范围/继承依赖/阶段历史的字段全部入哈希——含
    依赖对象及其解析状态/支持轴(R3-08:依赖已解决 vs unresolved
    是不同科学前提);S3 的缓存与图节点不得混用不同前提的上下文
    身份。
    """
    return stable_id(
        "pc", parent_context_ref, phase_id, requested_scope, scenario_ref,
        canonical_json([f.to_dict() for f in facts]),
        canonical_json([r.to_dict() for r in requirements]),
        canonical_json(sorted(assumptions)),
        canonical_json(sorted(dependency_refs)),
        canonical_json([d.to_dict() for d in dependencies]),
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
    dependencies: list[Dependency] | None = None,
    assessment_scope: list[str] | None = None,
    scenario_ref: str = "",
) -> PathContext:
    """构造根/独立上下文(分支各自构建,不共享可变对象)。

    要求在引入时绑定当前 phase_id/scenario_ref(R2-04;边为空 =
    根上下文引入)。dependencies(R3-07)为上下文累积的依赖对象
    (深拷贝隔离;其 dependency_id 并入 dependency_refs)。
    """
    if requested_scope not in REQUESTED_SCOPES:
        raise ConditionContractError(
            f"requested_scope 非法:{requested_scope!r}",
            {"requested_scope": requested_scope})
    deps = _merge_dependencies(dependencies or [])
    refs = list(dict.fromkeys(list(dependency_refs or [])
                              + [d.dependency_id for d in deps]))
    facts = [_fact_copy(f) for f in (condition_facts or [])]
    requirements = [
        _bind_requirement(_requirement_copy(r), phase_id=phase_id,
                          scenario_ref=scenario_ref, edge="")
        for r in (accumulated_requirements or [])]
    context_hash = _context_hash(
        parent_context_ref=parent_context_ref, phase_id=phase_id,
        requested_scope=requested_scope, facts=facts,
        requirements=requirements, assumptions=list(assumptions or []),
        dependency_refs=refs, dependencies=deps,
        assessment_scope=list(assessment_scope or []),
        scenario_ref=scenario_ref, scenario_transition=None,
        phase_history=[])
    return PathContext(
        context_id=context_hash, parent_context_ref=parent_context_ref,
        phase_id=phase_id, requested_scope=requested_scope,
        condition_facts=facts, accumulated_requirements=requirements,
        assumptions=list(assumptions or []),
        dependency_refs=refs, dependencies=deps,
        assessment_scope=list(assessment_scope or []),
        scenario_ref=scenario_ref,
    )


def _merge_dependencies(items: list[Dependency]) -> list[Dependency]:
    """依赖对象合并(按 dependency_id,后者覆盖前者——解析轨迹保留
    在 resolution_log;分支隔离:全部深拷贝)。"""
    merged: dict[str, Dependency] = {}
    for dep in items:
        if not isinstance(dep, Dependency):
            raise ConditionContractError(
                "上下文依赖必须是 Dependency 对象",
                {"kind": "context_dependency_invalid_type",
                 "got": type(dep).__name__})
        merged[dep.dependency_id] = Dependency(**dep.to_dict())
    return list(merged.values())


def derive_child_context(
    parent: PathContext,
    *,
    step_requirements: list[Requirement] | None = None,
    step_assumptions: list[str] | None = None,
    step_dependency_refs: list[str] | None = None,
    step_dependencies: list[Dependency] | None = None,
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
    R3-07:step_dependencies 为本步新增/更新的依赖对象(按
    dependency_id 后者覆盖——解析轨迹保留;其 id 并入 refs)。
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
    # 依赖:父对象(继承)+ 本步新增/更新(同 id 后者覆盖,轨迹保留)
    dependencies = _merge_dependencies(
        list(parent.dependencies) + list(step_dependencies or []))
    dependency_refs = list(dict.fromkeys(
        list(parent.dependency_refs) + list(step_dependency_refs or [])
        + [d.dependency_id for d in dependencies]))
    phase_history = copy.deepcopy(list(parent.phase_history))
    if scenario_transition is not None:
        # 冻结父阶段评估为历史快照(旧边结果保留;不追改;不是反应边)
        snapshot = parent.current_step_assessment()
        # R4-04:记录该次评估**实际覆盖**的要求签名(快照覆盖核对用
        # 具体要求,不是仅阶段存在 —— 空快照不能掩盖孤儿必要要求)
        snapshot_reqs = [
            r for r in parent.accumulated_requirements
            if _effective_scope(r, parent.scenario_ref, parent.phase_id)
            == (parent.scenario_ref, parent.phase_id)]
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
            "covered_requirement_signatures": [
                canonical_json(r.to_dict()) for r in snapshot_reqs],
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
        dependency_refs=dependency_refs,
        dependencies=dependencies,
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
        dependency_refs=dependency_refs,
        dependencies=dependencies,
        assessment_scope=child.assessment_scope,
        scenario_ref=scenario_ref,
        scenario_transition=scenario_transition,
        phase_history=phase_history)
    return child
