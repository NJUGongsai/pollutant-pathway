"""ChemicalAudit — 检查范围明确,未知不可冒充核实(实施书 §8,S2)。

必需分项(checks 的 name 集合):结构解析/价态、身份信息保真、冻结
有限规则诊断、参与物完整度、元素核算、形式电荷核算、映射/变换中心、
step_scope、条件检查、来源依赖。

- 分子明确无法解析是 parse_check=violated;依赖该解析的后续项是
  status=unknown、reason_code=prerequisite_failed_not_run(H01),
  不伪装全部通过;
- 完整已知参与物和系数才核全反应元素与形式电荷;不能先电荷中和再验
  电荷守恒;不能自动补水/氧/辅酶凑平;声明不完整时可核局部结构差值,
  但 full_balance=unknown(D03);
- 元素及电荷账核实 ≠ 氧化还原转移、辅酶循环、机制、酶催化、热力学
  或速率已核实(biological_support_status 另轴);
- G2(v43-cons-2)仅保留为旧规则诊断(unclassified=覆盖未知,不新增
  惩罚);输入 preview 不改变旧资格或门禁决定;
- 供体诊断输出 strict_target_match / legacy_cn_match /
  reaction_center_match / extra_changes 分轴;对称等价对齐正确处理;
  映射不可得、对齐截断或预期结构有损时受影响轴 unknown(D02);
- admission_policy(P0-4):显式决策表,任何 unknown 不自动 reject;
  条件冲突 → defer(current_scenario_conflict),假设保留不在此场景
  展开;仅条件/账目/映射/step_scope 未知 → retain_conditional 有界
  探索(C06 策略级);
- chemical_reproposal 首版默认 off(SMILES 无法解析时记结构失败,
  不重试到产物通过门禁)。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from rdkit import Chem, RDLogger

from ..domain.models import content_hash, stable_id
from .chemstate import (
    STRUCTURE_ORIGIN_LEGACY_CN_ONLY,
    ChemicalState,
    build_chemical_state,
)
from .hypothesis import (
    COEFFICIENT_KNOWN,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    ReactionHypothesis,
)
from .path_context import (
    PathContext,
    assess_conditions,
)
from .profile import (
    LEGACY_G2_FAMILY_REF,
    PPV1_ADMISSION_POLICY_VERSION,
    PPV1_AUDIT_SCHEMA_VERSION,
    PPV1_DONOR_DIAGNOSTIC_VERSION,
)

RDLogger.DisableLog("rdApp.*")

CHECK_STRUCTURE_PARSE_VALENCE = "structure_parse_valence"
CHECK_IDENTITY_FIDELITY = "identity_fidelity"
CHECK_FINITE_RULE_DIAGNOSTIC = "finite_rule_diagnostic"
CHECK_PARTICIPANT_COMPLETENESS = "participant_completeness"
CHECK_ELEMENT_ACCOUNTING = "element_accounting"
CHECK_FORMAL_CHARGE_ACCOUNTING = "formal_charge_accounting"
CHECK_TRANSFORMATION_CENTER = "transformation_center"
CHECK_STEP_SCOPE = "step_scope_check"
CHECK_CONDITION_CHECK = "condition_check"
CHECK_PROVENANCE_DEPENDENCY = "provenance_dependency"
REQUIRED_CHECK_NAMES = (
    CHECK_STRUCTURE_PARSE_VALENCE, CHECK_IDENTITY_FIDELITY,
    CHECK_FINITE_RULE_DIAGNOSTIC, CHECK_PARTICIPANT_COMPLETENESS,
    CHECK_ELEMENT_ACCOUNTING, CHECK_FORMAL_CHARGE_ACCOUNTING,
    CHECK_TRANSFORMATION_CENTER, CHECK_STEP_SCOPE, CHECK_CONDITION_CHECK,
    CHECK_PROVENANCE_DEPENDENCY,
)

CHECK_VERIFIED = "verified"
CHECK_VIOLATED = "violated"
CHECK_UNKNOWN = "unknown"
CHECK_NOT_APPLICABLE = "not_applicable"
PREREQUISITE_FAILED = "prerequisite_failed_not_run"

# 诊断状态与展开决定分开(§8):admission 的四种处置
ADMISSION_EXPAND = "expand"
ADMISSION_RETAIN_CONDITIONAL = "retain_conditional"
ADMISSION_DEFER = "defer"
ADMISSION_REJECT = "reject"
ADMISSION_DISPOSITIONS = frozenset({ADMISSION_EXPAND,
                                    ADMISSION_RETAIN_CONDITIONAL,
                                    ADMISSION_DEFER, ADMISSION_REJECT})

# admission 决策表里的活动门禁名(引用 frozen_hit60_gate,不修改其真假)
GATE_NAME_DIRECTION_SOURCE = "gate_direction_source"
GATE_NAME_RECORDED_ELIGIBILITY = "gate_recorded_eligibility"
GATE_NAME_SMILES = "gate_smiles"
DEFAULT_REJECT_GATES = frozenset({GATE_NAME_DIRECTION_SOURCE,
                                  GATE_NAME_RECORDED_ELIGIBILITY,
                                  GATE_NAME_SMILES})


class AuditContractError(RuntimeError):
    """审计输入/策略契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 检查对象


@dataclass
class AuditCheck:
    """单项检查(name/status/reason_code/evidence/coverage)。"""

    name: str
    status: str                 # verified | violated | unknown | not_applicable
    reason_code: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    coverage: str = ""          # 覆盖说明(如 only_legacy_rules)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ChemicalAudit:
    """§8 全字段;audit_id 由内容派生(幂等)。"""

    audit_id: str
    scope: str
    input_hash: str
    checks: list[AuditCheck] = field(default_factory=list)
    legacy_gate_result_ref: str = ""
    participant_accounting_status: str = "unknown"   # full|partial|unknown
    biological_support_status: str = "unknown"       # supported|inferred|unknown
    admission_disposition: str = ""
    admission_policy_ref: str = PPV1_ADMISSION_POLICY_VERSION
    admission_reasons: list[str] = field(default_factory=list)
    checker_versions: dict = field(default_factory=dict)
    schema_version: str = PPV1_AUDIT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "audit_id": self.audit_id,
            "scope": self.scope,
            "input_hash": self.input_hash,
            "checks": [c.to_dict() for c in self.checks],
            "legacy_gate_result_ref": self.legacy_gate_result_ref,
            "participant_accounting_status":
                self.participant_accounting_status,
            "biological_support_status": self.biological_support_status,
            "admission_disposition": self.admission_disposition,
            "admission_policy_ref": self.admission_policy_ref,
            "admission_reasons": list(self.admission_reasons),
            "checker_versions": dict(self.checker_versions),
        }

    def check_status(self, name: str) -> str:
        for c in self.checks:
            if c.name == name:
                return c.status
        return CHECK_NOT_APPLICABLE


def _mol_of(state: ChemicalState | None):
    if state is None or not state.smiles_isomeric:
        return None
    return Chem.MolFromSmiles(state.smiles_isomeric)


def _element_counts(mol) -> dict[str, int]:
    out: dict[str, int] = {}
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        out[sym] = out.get(sym, 0) + 1
    return out


# ---------------------------------------------------------------- 审计函数


def audit_hypothesis(
    hypothesis: ReactionHypothesis,
    *,
    run_id: str = "",
    scope: str = "hypothesis_admission",
    states: dict[str, ChemicalState] | None = None,
    raw_structures: dict[str, str] | None = None,
    context: PathContext | None = None,
    audit_scope: set[str] | None = None,
    legacy_gate_result: dict | None = None,
    finite_rule_diagnostic: dict | None = None,
    unresolved_dependency_ids: list[str] | None = None,
) -> ChemicalAudit:
    """§7.1 固定接口:hypothesis × audit_scope × policy → ChemicalAudit。

    - states 优先;缺项时从 raw_structures 现场构建(解析失败如实记
      parse violated);
    - audit_scope 为 None 时跑全部必需分项;条件检查无 context 时记
      not_applicable;
    - finite_rule_diagnostic:调用方预先跑好的输入 preview 诊断块
      (§17.2:off 时传 {"status": "not_run", ...});此处只登记引用,
      不改旧门禁真假;
    - admission 不在此决定(见 decide_admission;状态与展开分开)。
    """
    states = dict(states or {})
    for ref, structure in (raw_structures or {}).items():
        if ref not in states:
            states[ref] = build_chemical_state(
                structure, "source_product")
    requested = set(audit_scope or REQUIRED_CHECK_NAMES)

    checks: list[AuditCheck] = []
    versions = {
        "audit": PPV1_AUDIT_SCHEMA_VERSION,
        "chemstate": "ppv1-chemstate-1",
        "legacy_g2_family": LEGACY_G2_FAMILY_REF,
    }
    # ---- ① 结构解析/价态 ----
    parse_ok = True
    missing_state_refs: list[str] = []
    for p in hypothesis.participants:
        if p.state_ref not in states:
            missing_state_refs.append(p.state_ref)
    if missing_state_refs:
        parse_ok = False
        checks.append(AuditCheck(
            name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_VIOLATED,
            reason_code="participant_state_missing",
            evidence_refs=sorted(missing_state_refs)[:10],
            coverage="participants_with_state"))
    else:
        unparseable = [p.state_ref for p in hypothesis.participants
                       if not states[p.state_ref].smiles_isomeric]
        if unparseable:
            parse_ok = False
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_VIOLATED,
                reason_code="unparseable_smiles",
                evidence_refs=sorted(unparseable)[:10],
                coverage="participants_with_state"))
        else:
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_VERIFIED,
                reason_code="all_participants_parse",
                coverage="participants_with_state"))

    prerequisite_failed = not parse_ok

    def _dependent(name: str, coverage: str) -> AuditCheck:
        return AuditCheck(
            name=name, status=CHECK_UNKNOWN,
            reason_code=PREREQUISITE_FAILED, evidence_refs=[],
            coverage=coverage)

    # ---- ② 身份信息保真 ----
    if CHECK_IDENTITY_FIDELITY in requested:
        if prerequisite_failed:
            checks.append(_dependent(CHECK_IDENTITY_FIDELITY, "state_ids"))
        else:
            notes = []
            ok = True
            for p in hypothesis.participants:
                st = states.get(p.state_ref)
                if st is None:
                    continue
                if st.structure_origin == STRUCTURE_ORIGIN_LEGACY_CN_ONLY:
                    ok = False
                    notes.append(f"cn_only:{p.state_ref}")
                if st.representation_fidelity == "archive_recovered":
                    notes.append(f"archive_form:{p.state_ref}")
            checks.append(AuditCheck(
                name=CHECK_IDENTITY_FIDELITY,
                status=(CHECK_UNKNOWN if not ok else CHECK_VERIFIED),
                reason_code=(";".join(notes) if notes
                             else "identity_states_consistent"),
                coverage="state_ids"))

    # ---- ③ 冻结有限规则诊断 ----
    if CHECK_FINITE_RULE_DIAGNOSTIC in requested:
        diag = finite_rule_diagnostic or {"status": "not_run",
                                          "reason": "not_provided"}
        status = CHECK_NOT_APPLICABLE if diag.get("status") == "not_run" \
            else CHECK_UNKNOWN
        reason = diag.get("reason", "")
        if diag.get("status") in ("diagnostic_only", "hold_reported"):
            reason = "input_preview_diagnostic_only_coverage_limited"
        checks.append(AuditCheck(
            name=CHECK_FINITE_RULE_DIAGNOSTIC, status=status,
            reason_code=reason or "legacy_g2_diagnostic_reference",
            evidence_refs=[LEGACY_G2_FAMILY_REF],
            coverage="only_legacy_rules_H_O_free_fragment_counts"))

    # ---- ④ 参与物完整度 ----
    if CHECK_PARTICIPANT_COMPLETENESS in requested:
        status_list = hypothesis.participant_list_status
        if prerequisite_failed:
            checks.append(_dependent(CHECK_PARTICIPANT_COMPLETENESS,
                                     "participant_list"))
        elif status_list in ("source_complete", "declared_complete"):
            has_unknown_coeff = any(
                p.coefficient_status != COEFFICIENT_KNOWN
                for p in hypothesis.participants)
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS,
                status=(CHECK_UNKNOWN if has_unknown_coeff
                        else CHECK_VERIFIED),
                reason_code=("coefficients_unknown_declared_complete"
                             if has_unknown_coeff
                             else "declared_complete_with_known_coefficients"),
                coverage="participant_list"))
        else:
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS, status=CHECK_UNKNOWN,
                reason_code=f"participant_list_status:{status_list}",
                coverage="participant_list"))

    # ---- ⑤⑥ 元素/形式电荷核算 ----
    full_known = (
        hypothesis.participant_list_status in ("source_complete",
                                               "declared_complete")
        and all(p.coefficient_status == COEFFICIENT_KNOWN
                for p in hypothesis.participants))
    reactant_side = [p for p in hypothesis.participants
                     if p.side == PARTICIPANT_SIDE_REACTANT]
    product_side = [p for p in hypothesis.participants
                    if p.side == PARTICIPANT_SIDE_PRODUCT]
    if CHECK_ELEMENT_ACCOUNTING in requested:
        if prerequisite_failed:
            checks.append(_dependent(CHECK_ELEMENT_ACCOUNTING, "full_balance"))
        elif full_known:
            elem_balance, elem_reason = _element_accounting(
                reactant_side, product_side, states)
            checks.append(AuditCheck(
                name=CHECK_ELEMENT_ACCOUNTING, status=elem_balance,
                reason_code=elem_reason, coverage="full_balance"))
        else:
            checks.append(AuditCheck(
                name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="partial_or_unknown_participants_full_balance"
                            "_unknown_local_diff_only",
                coverage="full_balance"))
    if CHECK_FORMAL_CHARGE_ACCOUNTING in requested:
        if prerequisite_failed:
            checks.append(_dependent(
                CHECK_FORMAL_CHARGE_ACCOUNTING, "full_balance"))
        elif full_known:
            charge_status, charge_reason = _charge_accounting(
                reactant_side, product_side, states)
            checks.append(AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=charge_status,
                reason_code=charge_reason, coverage="full_balance"))
        else:
            checks.append(AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="partial_or_unknown_participants_full_balance"
                            "_unknown",
                coverage="full_balance"))

    # ---- ⑦ 映射/变换中心 ----
    if CHECK_TRANSFORMATION_CENTER in requested:
        sig = hypothesis.transformation_signature_status
        if prerequisite_failed:
            checks.append(_dependent(CHECK_TRANSFORMATION_CENTER,
                                     "mapping_dependent"))
        elif sig == "verified":
            checks.append(AuditCheck(
                name=CHECK_TRANSFORMATION_CENTER, status=CHECK_VERIFIED,
                reason_code="transformation_signature_verified",
                coverage="mapping_dependent"))
        else:
            checks.append(AuditCheck(
                name=CHECK_TRANSFORMATION_CENTER, status=CHECK_UNKNOWN,
                reason_code="transformation_signature_status:"
                            f"{sig or 'unavailable'}(映射不可得不猜中心)",
                coverage="mapping_dependent"))

    # ---- ⑧ step_scope ----
    if CHECK_STEP_SCOPE in requested:
        if hypothesis.step_scope == "unknown":
            checks.append(AuditCheck(
                name=CHECK_STEP_SCOPE, status=CHECK_UNKNOWN,
                reason_code="step_scope_unknown(汇总边不冒充净反应)",
                coverage="step_scope"))
        elif hypothesis.step_scope == "multistep_summary":
            checks.append(AuditCheck(
                name=CHECK_STEP_SCOPE, status=CHECK_NOT_APPLICABLE,
                reason_code="multistep_summary_kept_as_summary_edge",
                coverage="step_scope"))
        else:
            checks.append(AuditCheck(
                name=CHECK_STEP_SCOPE, status=CHECK_VERIFIED,
                reason_code=f"step_scope:{hypothesis.step_scope}",
                evidence_refs=list(hypothesis.step_scope_evidence_refs),
                coverage="step_scope"))

    # ---- ⑨ 条件检查 ----
    if CHECK_CONDITION_CHECK in requested:
        if context is None:
            checks.append(AuditCheck(
                name=CHECK_CONDITION_CHECK, status=CHECK_NOT_APPLICABLE,
                reason_code="no_context", coverage="declared_dimensions"))
        elif prerequisite_failed:
            checks.append(_dependent(CHECK_CONDITION_CHECK,
                                     "declared_dimensions"))
        else:
            assessment = assess_conditions(context, hypothesis)
            status_map = {
                "conflict": CHECK_VIOLATED,
                "compatible": CHECK_VERIFIED,
                "unknown": CHECK_UNKNOWN,
            }
            checks.append(AuditCheck(
                name=CHECK_CONDITION_CHECK,
                status=status_map[assessment.environment_fit],
                reason_code=(
                    f"environment_fit:{assessment.environment_fit}"
                    f";coverage:{';'.join(assessment.assessment_scope)}"),
                coverage="declared_dimensions"))

    # ---- ⑩ 来源依赖 ----
    if CHECK_PROVENANCE_DEPENDENCY in requested:
        unresolved = list(unresolved_dependency_ids or [])
        if unresolved:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_UNKNOWN,
                reason_code="unresolved_dependencies_inherited",
                evidence_refs=unresolved[:10], coverage="dependency_set"))
        else:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_VERIFIED,
                reason_code="no_unresolved_dependencies",
                coverage="dependency_set"))

    audit_id = stable_id(
        "audit", hypothesis.hypothesis_id, scope,
        content_hash([c.to_dict() for c in checks]))
    participant_accounting = ("full" if full_known and not prerequisite_failed
                              else "partial" if not prerequisite_failed
                              else "unknown")
    return ChemicalAudit(
        audit_id=audit_id, scope=scope, input_hash=stable_id(
            "ain", hypothesis.hypothesis_id),
        checks=checks,
        legacy_gate_result_ref=(
            (legacy_gate_result or {}).get("gate_ref", "")),
        participant_accounting_status=participant_accounting,
        biological_support_status="unknown",
        checker_versions=versions,
    )


def _element_accounting(reactant_side, product_side, states) -> tuple[
        str, str]:
    """全量元素账(系数加权;不补水/氧/辅酶凑平)。"""
    totals: dict[str, Fraction] = {}
    for p, sign in [(p, 1) for p in reactant_side] + [
            (p, -1) for p in product_side]:
        mol = _mol_of(states.get(p.state_ref))
        if mol is None:
            return CHECK_UNKNOWN, f"state_unavailable:{p.state_ref}"
        coeff = p.coefficient if p.coefficient is not None else Fraction(0)
        for sym, n in _element_counts(mol).items():
            totals[sym] = totals.get(sym, Fraction(0)) + sign * n * coeff
    diffs = {sym: v for sym, v in totals.items() if v != 0}
    if diffs:
        detail = ";".join(f"{sym}:{v}" for sym, v in sorted(diffs.items()))
        return CHECK_VIOLATED, f"element_imbalance:{detail}"
    return CHECK_VERIFIED, "elements_balanced"


def _charge_accounting(reactant_side, product_side, states) -> tuple[
        str, str]:
    """形式电荷账(用原始 formal_charge;不能先中和再验)。"""
    total = Fraction(0)
    for p, sign in [(p, 1) for p in reactant_side] + [
            (p, -1) for p in product_side]:
        st = states.get(p.state_ref)
        if st is None or st.formal_charge is None:
            return CHECK_UNKNOWN, f"charge_unavailable:{p.state_ref}"
        coeff = p.coefficient if p.coefficient is not None else Fraction(0)
        total += sign * st.formal_charge * coeff
    if total != 0:
        return CHECK_VIOLATED, f"charge_imbalance:{total}"
    return CHECK_VERIFIED, "formal_charge_balanced"


# ---------------------------------------------------------------- admission


@dataclass
class AdmissionPolicy:
    """P0-4:admission 策略(schema + 完整决策表;显式、有序、fail-closed)。

    规则(评估顺序固定,首中即决):
    R1 structure_unparseable      → reject  (parse violated:结构非法)
    R2 active_gate_rejected       → reject  (活动门禁显式拒绝;仅
        reject_gates 名单内的门禁违规触发 —— 不暗改冻结判据,新 profile
        自行声明引用哪些门)
    R3 current_scenario_conflict  → defer   (有来源 essential 条件与当前
        场景已知事实冲突;action=blocked,假设保留不在此场景展开)
    R4 budget_or_wait             → defer   (预算/等待状态,独立原因)
    R5 unknown_checks_present     → retain_conditional(仅条件/完整账/
        映射/step_scope 未知:可有界探索,继承未解决依赖;未知步长不进
        确认单步指标)
    R6 default_all_verified       → expand  (全部核实且无冲突)

    任何 unknown 不自动 reject;新增"诊断转拒绝"必须扩本表并升版本。
    chemical_reproposal 首版 off(§7.2:SMILES 无法解析记结构失败)。
    """

    policy_version: str = PPV1_ADMISSION_POLICY_VERSION
    reject_gates: frozenset = frozenset(DEFAULT_REJECT_GATES)
    chemical_reproposal: str = "off"
    rules: tuple = (
        ("R1", "structure_unparseable", ADMISSION_REJECT),
        ("R2", "active_gate_rejected", ADMISSION_REJECT),
        ("R3", "current_scenario_conflict", ADMISSION_DEFER),
        ("R4", "budget_or_wait", ADMISSION_DEFER),
        ("R5", "unknown_checks_present", ADMISSION_RETAIN_CONDITIONAL),
        ("R6", "default_all_verified", ADMISSION_EXPAND),
    )

    def to_dict(self) -> dict:
        return {
            "policy_version": self.policy_version,
            "reject_gates": sorted(self.reject_gates),
            "chemical_reproposal": self.chemical_reproposal,
            "rules": [
                {"rule_id": rid, "condition": cond, "disposition": disp}
                for rid, cond, disp in self.rules],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AdmissionPolicy":
        version = d.get("policy_version", "")
        if version != PPV1_ADMISSION_POLICY_VERSION:
            raise AuditContractError(
                f"admission policy 版本未知:{version!r}(支持 "
                f"{PPV1_ADMISSION_POLICY_VERSION})",
                {"policy_version": version})
        gates = frozenset(d.get("reject_gates", DEFAULT_REJECT_GATES))
        unknown_gates = gates - DEFAULT_REJECT_GATES
        if unknown_gates:
            raise AuditContractError(
                "reject_gates 含未知门禁(新增门禁须独立列项评审,不暗改)",
                {"unknown_gates": sorted(unknown_gates)})
        repro = d.get("chemical_reproposal", "off")
        if repro not in ("off", "on"):
            raise AuditContractError(
                f"chemical_reproposal 非法:{repro!r}", {"value": repro})
        return cls(reject_gates=gates, chemical_reproposal=repro)


DEFAULT_ADMISSION_POLICY = AdmissionPolicy()


def decide_admission(
    audit: ChemicalAudit,
    *,
    policy: AdmissionPolicy | None = None,
    gate_decisions: dict[str, dict] | None = None,
    budget_state: dict | None = None,
) -> tuple[str, list[str]]:
    """audit × 策略 → (admission_disposition, reasons)(纯函数)。

    gate_decisions:{"<gate_name>": {"ok": bool, "reason": str}}(活动
    门禁的既有真假;本函数不改判,只按 policy.reject_gates 消费)。
    budget_state:{"exhausted": bool, "waiting": bool, "reason": str}。
    """
    pol = policy or DEFAULT_ADMISSION_POLICY
    reasons: list[str] = []

    # R1:结构非法 → reject
    if audit.check_status(CHECK_STRUCTURE_PARSE_VALENCE) == CHECK_VIOLATED:
        return ADMISSION_REJECT, ["R1:structure_unparseable"]

    # R2:活动门禁显式拒绝(仅名单内;不暗改冻结判据)
    for gate_name, decision in (gate_decisions or {}).items():
        if gate_name in pol.reject_gates and not decision.get("ok", True):
            reasons.append(
                f"R2:active_gate_rejected:{gate_name}:"
                f"{decision.get('reason', '')[:120]}")
    if any(r.startswith("R2:") for r in reasons):
        return ADMISSION_REJECT, reasons

    # R3:当前场景有来源必要条件冲突 → defer(blocked;不在此场景展开)
    if audit.check_status(CHECK_CONDITION_CHECK) == CHECK_VIOLATED:
        return ADMISSION_DEFER, [
            "R3:current_scenario_conflict(当前环境相容路线不展开;"
            "假设保留,留原因,可展示为需不同条件的备选)"]

    # R4:预算/等待 → defer(独立原因)
    bs = budget_state or {}
    if bs.get("exhausted") or bs.get("waiting"):
        return ADMISSION_DEFER, [
            f"R4:budget_or_wait:{bs.get('reason', 'budget_or_waiting')}"]

    # R5:存在 unknown 检查 → retain_conditional(有界探索,继承依赖)
    unknown_names = [c.name for c in audit.checks
                     if c.status == CHECK_UNKNOWN]
    if unknown_names:
        return ADMISSION_RETAIN_CONDITIONAL, [
            "R5:unknown_checks_present(不自动拒绝;可有界探索可能路径,"
            f"继承未解决依赖;未知步长不进确认单步指标):"
            + ",".join(unknown_names)]

    # R6:全部核实且无冲突 → expand
    applicable = [c for c in audit.checks
                  if c.status not in (CHECK_NOT_APPLICABLE,)]
    if applicable and all(c.status == CHECK_VERIFIED for c in applicable):
        return ADMISSION_EXPAND, ["R6:all_verified_no_conflict"]
    # 没有任何 applicable 检查(空审计):保守 retain_conditional,
    # 不默认 expand(不以无证据冒充核实)
    return ADMISSION_RETAIN_CONDITIONAL, [
        "R5:empty_audit_no_evidence_to_expand(保守保留,不冒充核实)"]


# ---------------------------------------------------------------- 供体诊断


@dataclass
class DonorConsistencyDiagnostic:
    """§8 供体诊断(分轴输出;版本 PPV1_DONOR_DIAGNOSTIC_VERSION)。"""

    strict_target_match: bool | None   # None = 无法判定(信息缺失)
    legacy_cn_match: bool | None       # CN 旁证(不作结构事实)
    reaction_center_match: bool | None # 依映射;对称等价正确处理
    extra_changes: list[str] = field(default_factory=list)
    alignment_ref: str = ""
    missing_info_reasons: list[str] = field(default_factory=list)
    schema_version: str = PPV1_DONOR_DIAGNOSTIC_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def check_edit_against_donor(
    *,
    current: dict,
    donor: dict,
    alignment: dict,
    expectation: dict,
    result: dict,
    edits: list[dict],
) -> DonorConsistencyDiagnostic:
    """§7.1 固定接口:编辑结果对供体预期/变换中心的一致性诊断(纯函数)。

    输入(宽松 dict,结构化校验):
    - current: {"smiles": str}(编辑前严格结构)
    - donor: {"center_atom_ids": [...]}(供体反应变换中心,供体侧原子)
    - alignment: {"status": resolved|ambiguous|unavailable,
      "donor_to_current": {donor_atom: current_atom},
      "equivalence_classes": [[atom, atom, ...]]}(对称等价类)
    - expectation: {"target_smiles": str}(供体迁移预期产物)
    - result: {"product_smiles": str, "edit_atom_ids": [...]}(实际)
    - edits: [{"atom_id": ..., "op": ...}](实际编辑)

    分轴语义(D01/D02):
    - strict_target_match:实际产物与预期产物的严格 isomeric canonical
      一致(合法编辑但偏离预期 → False;解析失败/输入缺失 → None +
      missing_info_reasons);
    - legacy_cn_match:CN 一致(仅旁证,不称严格结构一致);
    - reaction_center_match:对齐 resolved 时,实际编辑原子集与供体
      中心(经对齐映射 + 等价类)比对;对称等价变体不误拒;对齐
      ambiguous/unavailable/截断 → None(受影响轴 unknown,不猜中心);
      立体信息未知不使已有充分映射支持的 center 判定变 unknown;
    - extra_changes:不属于中心(及等价类)的编辑原子列表。
    """
    missing: list[str] = []
    alignment_status = str(alignment.get("status", "unavailable"))
    if alignment_status not in ("resolved", "ambiguous", "unavailable"):
        raise AuditContractError(
            f"alignment.status 非法:{alignment_status!r}",
            {"status": alignment_status})
    alignment_ref = str(alignment.get("ref", "") or stable_id(
        "align", str(alignment.get("donor_to_current", ""))))

    # ---- strict target match ----
    strict = None
    result_smiles = result.get("product_smiles")
    expected_smiles = expectation.get("target_smiles")
    if result_smiles and expected_smiles:
        m_result = Chem.MolFromSmiles(str(result_smiles))
        m_expect = Chem.MolFromSmiles(str(expected_smiles))
        if m_result is None or m_expect is None:
            missing.append("target_or_result_unparseable")
            strict = None
        else:
            strict = (Chem.MolToSmiles(m_result)
                      == Chem.MolToSmiles(m_expect))
    else:
        missing.append("target_or_result_smiles_missing")
        strict = None

    # ---- legacy CN match(旁证) ----
    cn_match = None
    if result_smiles and expected_smiles:
        from ..domain.identity import cn_identity as _cn

        cn_a, cn_b = _cn(str(result_smiles)), _cn(str(expected_smiles))
        if cn_a is not None and cn_b is not None:
            cn_match = cn_a == cn_b

    # ---- reaction center match ----
    center_match = None
    extra_changes: list[str] = []
    edit_atom_ids = [str(e.get("atom_id")) for e in edits
                     if e.get("atom_id") is not None]
    donor_centers = [str(a) for a in (donor.get("center_atom_ids") or [])]
    if alignment_status != "resolved":
        center_match = None
        missing.append(
            f"alignment_{alignment_status}_center_unknown"
            if alignment_status == "ambiguous"
            else f"alignment_{alignment_status}_center_unknown")
    elif not donor_centers or not edit_atom_ids:
        center_match = None
        missing.append("center_or_edits_unavailable")
    else:
        mapping = {
            str(k): str(v)
            for k, v in (alignment.get("donor_to_current") or {}).items()}
        # 对称等价类:current 侧原子的等价展开
        equivalence: dict[str, set[str]] = {}
        for eq_class in (alignment.get("equivalence_classes") or []):
            members = {str(a) for a in eq_class}
            for m in members:
                equivalence.setdefault(m, set()).update(members)
        donor_center_current = set()
        for d_atom in donor_centers:
            mapped = mapping.get(d_atom)
            if mapped is None:
                missing.append(f"donor_center_unmapped:{d_atom}")
                continue
            group = {mapped} | equivalence.get(mapped, set())
            donor_center_current.update(group)
        if not donor_center_current:
            center_match = None
            missing.append("donor_centers_not_aligned")
        else:
            center_atoms = set(edit_atom_ids) & donor_center_current
            center_match = bool(center_atoms) and not (
                set(edit_atom_ids) - donor_center_current)
            # extra_changes:不属于中心(及等价类)的编辑原子
            extra_changes = sorted(
                set(edit_atom_ids) - donor_center_current)
            if center_match:
                extra_changes = []

    return DonorConsistencyDiagnostic(
        strict_target_match=strict, legacy_cn_match=cn_match,
        reaction_center_match=center_match,
        extra_changes=extra_changes, alignment_ref=alignment_ref,
        missing_info_reasons=missing,
    )
