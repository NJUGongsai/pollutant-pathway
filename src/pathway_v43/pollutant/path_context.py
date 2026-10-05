"""PathContext — 路径上下文、条件事实与证据依赖(实施书 §6,S2)。

- 第一版条件键限定:oxygen_regime、pH、temperature_C、matrix、
  electron_donor、electron_acceptor、growth_substrate;未知键
  fail-closed;
- 未列出某共底物 ≠ 已证实没有它(status=unknown ≠ known_absent);
  "土壤/污水"不推出氧条件;条件缺失不得从有限守恒工具的隐式
  H₂O/O₂ 中补造;
- 历史文献条件只进 candidate source_conditions(Requirement 的
  observed_source_conditions / basis=observed_condition_reference),
  不直接成为当前 condition_facts;观察条件 ≠ 必需条件;
- 聚合规则(§6):有来源 essential 与明确已知事实矛盾 → conflict;
  声明覆盖维度内全部必要要求有来源并满足 → compatible(输出
  assessment_scope 与 requirement_coverage);缺事实/覆盖未知/要求
  空 → unknown(空列表不自动相容);preference 只提示不作门禁;
- pH/温度:无交集 → conflict;部分交集但实际值不确定 → unknown;
  输入点位于支持范围才判满足;
- assessed_scope 由聚合结果**派生**,不继承 requested_scope:请求
  condition_compatible 但评估未知时最终仍是 possible(C05);
- 子路径上下文 = 父路径事实/必要依赖 + 本步新增要求;分支隔离
  (各自 context_id);scenario_transition 仅允许用户/来源提供并显式
  记录,不追改此前步骤;
- 依赖对象 status 固定 supported|contradicted|unresolved;子路径继承;
  下游精确匹配不消除上游猜测;只有有来源新证据或显式阶段转换才能
  解决,并保留更新轨迹;重复引用不升级支持。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import canonical_json, stable_id
from .profile import PPV1_CONDITION_ASSESSMENT_VERSION, \
    PPV1_CONTEXT_SCHEMA_VERSION, PPV1_DEPENDENCY_SCHEMA_VERSION

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
# 枚举型条件键(取值域)
OXYGEN_REGIME_VALUES = frozenset({"aerobic", "anaerobic", "facultative"})

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


# ---------------------------------------------------------------- 条件事实


@dataclass
class ConditionFact:
    """一条当前场景条件事实(键/值/状态/来源/所属场景)。"""

    key: str
    value: float | int | str | dict | None   # 数值/枚举/区间 {lo, hi}
    unit: str = ""
    status: str = FACT_STATUS_UNKNOWN
    origin: str = FACT_ORIGIN_USER_INPUT
    source_ref: str = ""
    subject_scenario_ref: str = ""
    phase_id: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _validate_interval(value: dict) -> None:
    if not isinstance(value, dict) or "lo" not in value or "hi" not in value:
        raise ConditionContractError(
            f"区间条件值须为 {{lo, hi}}:{value!r}", {"value": repr(value)})
    lo, hi = value["lo"], value["hi"]
    for v in (lo, hi):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ConditionContractError(
                f"区间端点须为数值:{value!r}", {"value": repr(value)})
    if not lo <= hi:
        raise ConditionContractError(
            f"区间下界须 ≤ 上界:{value!r}", {"value": repr(value)})


def build_condition_fact(
    *, key: str, value=None, unit: str = "",
    status: str = FACT_STATUS_UNKNOWN,
    origin: str = FACT_ORIGIN_USER_INPUT,
    source_ref: str = "", subject_scenario_ref: str = "",
    phase_id: str = "",
) -> ConditionFact:
    """构造条件事实(fail-closed 校验;unknown 值也允许但须显式)。"""
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
    if status == FACT_STATUS_UNKNOWN:
        value = None  # unknown:值不可知,不携带
    else:
        if key in INTERVAL_CONDITION_KEYS and isinstance(value, dict):
            _validate_interval(value)
        elif key == CONDITION_KEY_OXYGEN:
            if value not in OXYGEN_REGIME_VALUES:
                raise ConditionContractError(
                    f"oxygen_regime 取值非法:{value!r}"
                    f"(允许 {sorted(OXYGEN_REGIME_VALUES)})", {"value": value})
        elif key in (CONDITION_KEY_PH, CONDITION_KEY_TEMPERATURE) \
                and isinstance(value, (int, float)):
            pass  # 点值
        elif value is None:
            raise ConditionContractError(
                f"已知状态的条件必须携带值:{key}", {"key": key})
    return ConditionFact(key=key, value=value, unit=unit, status=status,
                         origin=origin, source_ref=source_ref,
                         subject_scenario_ref=subject_scenario_ref,
                         phase_id=phase_id)


# ---------------------------------------------------------------- 要求


@dataclass
class Requirement:
    """一条环境/供给要求(essential|preference;来源;观察条件另存)。"""

    key: str
    level: str                        # essential | preference
    value: float | int | str | dict | None
    basis: str = REQUIREMENT_BASIS_ESSENTIAL_CLAIMED  # essential | observed
    source_refs: list[str] = field(default_factory=list)
    applicable_dimensions: list[str] = field(default_factory=list)
    observed_source_conditions: list[dict] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def build_requirement(*, key: str, level: str, value=None,
                      basis: str = REQUIREMENT_BASIS_ESSENTIAL_CLAIMED,
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
    if key in INTERVAL_CONDITION_KEYS and isinstance(value, dict):
        _validate_interval(value)
    if key == CONDITION_KEY_OXYGEN and value is not None \
            and value not in OXYGEN_REGIME_VALUES:
        raise ConditionContractError(
            f"oxygen_regime 要求取值非法:{value!r}", {"value": value})
    return Requirement(key=key, level=level, value=value, basis=basis,
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
    # 枚举/字符串键:相等判满足,不等判冲突(有事实才有此分支)
    return SATISFIED if fact_value == req_value else CONFLICT


def _assess_requirement(
    req: Requirement, facts: dict[str, ConditionFact],
) -> tuple[str, str]:
    """单项评估 → (status, reason)。"""
    # 文献观察条件不是必需条件:只作参考,不参与门禁(优先判定,
    # 缺事实也按 not_applicable,不混入 unknown 聚合)
    if req.basis == REQUIREMENT_BASIS_OBSERVED_REFERENCE:
        return NOT_APPLICABLE, "observed_condition_reference_not_gating"
    fact = facts.get(req.key)
    if fact is None or fact.status == FACT_STATUS_UNKNOWN:
        # 未列出某共底物 = 未知,不是 absent(C01)
        return UNKNOWN, f"no_fact:{req.key}"
    if req.value is None:
        # 要求声明了键但未声明值域:有事实也无法判满足 → unknown
        return UNKNOWN, f"requirement_value_unspecified:{req.key}"
    if isinstance(req.value, str) and isinstance(fact.value, str):
        # 物种/枚举类:值不同且双方已知 → 冲突;缺方 → unknown(上面已挡)
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
    """条件评估结果(单项 + 聚合;§7.1 assess_conditions 的输出)。"""

    per_requirement: list[dict]
    environment_fit: str          # compatible | unknown | conflict
    assessed_scope: str           # condition_compatible | possible | conflicted
    assessment_scope: list[str]   # 声明覆盖的环境维度
    requirement_coverage: dict    # covered / unknown / missing 计数与键
    preference_notes: list[str]
    schema_version: str = PPV1_CONDITION_ASSESSMENT_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def aggregate_environment_fit(
    *,
    facts: list[ConditionFact],
    requirements: list[Requirement],
    declared_scope: list[str] | None = None,
) -> ConditionAssessment:
    """条件聚合(§6 规则;空要求列表 → unknown,不自动相容)。"""
    fact_map = {f.key: f for f in facts}
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
                        "reason": "preference_not_gating"})
            continue
        status, reason = _assess_requirement(req, fact_map)
        per.append({"key": req.key, "level": req.level, "status": status,
                    "reason": reason, "basis": req.basis})
        if status == CONFLICT:
            any_conflict = True
        elif status == UNKNOWN:
            any_unknown = True
    essential = [r for r in requirements
                 if r.level == REQUIREMENT_ESSENTIAL
                 and r.basis == REQUIREMENT_BASIS_ESSENTIAL_CLAIMED]
    if not essential:
        any_unknown = True  # (有效)必要要求为空:未知,不自动相容

    scope = [k for k in (declared_scope or [])
             if k in CONDITION_KEYS]
    covered = [r.key for r in essential if r.key in scope]
    essential_key_set = {r.key for r in essential}
    fit = UNKNOWN
    if any_conflict:
        fit = CONFLICT
    elif (not any_unknown and essential
          and set(covered) == essential_key_set and scope):
        fit = "compatible"  # 声明覆盖维度 ⊇ 全部必要要求且已满足
    assessed = {
        CONFLICT: ASSESSED_SCOPE_CONFLICTED,
        "compatible": ASSESSED_SCOPE_CONDITION_COMPATIBLE,
        UNKNOWN: ASSESSED_SCOPE_POSSIBLE,
    }[fit]
    return ConditionAssessment(
        per_requirement=per, environment_fit=fit, assessed_scope=assessed,
        assessment_scope=scope,
        requirement_coverage={
            "essential_keys": sorted({r.key for r in essential}),
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

    评估范围 = 上下文累积的必要要求(父路径继承,§6)+ 该假设自带的
    requirements(本步新增);两者合并,同键以假设侧为准(derive_child
    的冲突已在上下文 assumptions 显式记录)。
    """
    hyp_reqs = getattr(hypothesis, "requirements", None)
    if hyp_reqs is None and isinstance(hypothesis, dict):
        hyp_reqs = hypothesis.get("requirements", [])
    hyp_reqs = list(hyp_reqs or [])
    requirements: list[Requirement] = []
    by_key: dict[str, Requirement] = {}
    for r in list(context.accumulated_requirements) + hyp_reqs:
        req = r if isinstance(r, Requirement) else Requirement(**r)
        requirements.append(req)
        by_key[req.key] = req
    return aggregate_environment_fit(
        facts=context.condition_facts,
        requirements=[by_key[k] for k in sorted(by_key)],
        declared_scope=context.assessment_scope)


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


def detect_circular_dependencies(
    dependencies: list[Dependency],
) -> dict:
    """共底物循环诊断(§17.4 H04 的 S2 部分)。

    输入依赖的 statement 以 "supplies:" 前缀声明供给关系(导入/构造方
    责任保持声明风格一致)。有启动/再生支持(status=supported)的环
    不阻断;未知 → unresolved_initial_supply,依显式策略处理,不称
    化学不可能。
    """
    supplies = [d for d in dependencies if d.statement.startswith("supplies:")]
    # 供给对:statement 形如 "supplies:<src>:<dst>"
    pairs: dict[str, str] = {}
    for dep in supplies:
        parts = dep.statement.split(":")
        if len(parts) >= 3:
            pairs.setdefault(parts[1], parts[2])
    cycles: list[tuple[str, str]] = []
    for src, dst in pairs.items():
        if pairs.get(dst) == src and (dst, src) not in cycles:
            cycles.append((src, dst))
    unresolved: list[tuple[str, str]] = []
    for a, b in cycles:
        edge_deps = [d for d in supplies
                     if f"supplies:{a}:{b}" in d.statement
                     or f"supplies:{b}:{a}" in d.statement]
        if not all(d.status == DEPENDENCY_SUPPORTED for d in edge_deps):
            unresolved.append((a, b))
    return {
        "cycles": [list(c) for c in sorted(cycles)],
        "unresolved_initial_supply": [list(c) for c in sorted(unresolved)],
        "note": ("cosubstrate_cycle:有启动/再生支持不自动阻断;未知标 "
                 "unresolved_initial_supply,依显式策略处理,不称化学不可能"),
    }


# ---------------------------------------------------------------- 上下文


@dataclass
class PathContext:
    """路径上下文(§6 全字段;分支隔离;JSON 往返)。"""

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
    scenario_transition: dict | None = None
    schema_version: str = PPV1_CONTEXT_SCHEMA_VERSION

    @property
    def assessed_scope(self) -> str:
        """由事实×要求派生,不继承 requested_scope(C05)。"""
        return aggregate_environment_fit(
            facts=self.condition_facts,
            requirements=self.accumulated_requirements,
            declared_scope=self.assessment_scope,
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
            "scenario_transition": self.scenario_transition,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PathContext":
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
            scenario_transition=d.get("scenario_transition"),
        )


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
) -> PathContext:
    """构造根/独立上下文(分支各自构建,不共享可变对象)。"""
    if requested_scope not in REQUESTED_SCOPES:
        raise ConditionContractError(
            f"requested_scope 非法:{requested_scope!r}",
            {"requested_scope": requested_scope})
    facts = list(condition_facts or [])
    requirements = list(accumulated_requirements or [])
    context_hash = stable_id(
        "pc", parent_context_ref, phase_id,
        canonical_json([f.to_dict() for f in facts]),
        canonical_json([r.to_dict() for r in requirements]))
    return PathContext(
        context_id=context_hash, parent_context_ref=parent_context_ref,
        phase_id=phase_id, requested_scope=requested_scope,
        condition_facts=facts, accumulated_requirements=requirements,
        assumptions=list(assumptions or []),
        dependency_refs=list(dependency_refs or []),
        assessment_scope=list(assessment_scope or []),
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

    - 父上下文不可变(返回新对象;分支间不互相污染);
    - 新增需求与父需求同键冲突时显式记录到 assumptions(同一固定
      场景中新增需求矛盾须显式记录,不静默覆盖);
    - scenario_transition:仅用户/来源提供的显式转换(带 source_ref);
      转换只影响后续步骤,不追改此前反应的环境冲突。
    """
    if scenario_transition is not None:
        if not scenario_transition.get("source_ref"):
            raise ConditionContractError(
                "阶段转换必须有来源(用户/来源提供;不自行换场景)",
                {"scenario_transition": scenario_transition})
    parent_reqs = {r.key: r for r in parent.accumulated_requirements}
    merged: list[Requirement] = list(parent.accumulated_requirements)
    conflict_notes: list[str] = []
    for req in (step_requirements or []):
        existing = parent_reqs.get(req.key)
        if existing is not None and canonical_json(
                existing.to_dict()) != canonical_json(req.to_dict()):
            conflict_notes.append(
                f"requirement_conflict_at_same_scenario:{req.key}:"
                f"parent={existing.value!r},step={req.value!r}(显式记录,"
                "不静默覆盖)")
        elif existing is None:
            merged.append(req)
    assumptions = list(parent.assumptions) + list(step_assumptions or []) \
        + conflict_notes
    phase_id = parent.phase_id
    if scenario_transition is not None:
        phase_id = str(scenario_transition.get("new_phase_id",
                                               parent.phase_id))
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
        scenario_transition=scenario_transition,
    )
    # 同固定场景中同键要求冲突:显式记录后保留双方(不静默覆盖),
    # 评估时按各自值分别核算
    context_hash = stable_id(
        "pc", parent.context_id, phase_id,
        canonical_json([f.to_dict() for f in child.condition_facts]),
        canonical_json([r.to_dict() for r in merged]),
        canonical_json(assumptions))
    child.context_id = context_hash
    return child
