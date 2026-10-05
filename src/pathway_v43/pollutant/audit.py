"""ChemicalAudit — 检查范围明确,未知不可冒充核实(v2 回修,S2)。

v2(ppv1-audit-2 / ppv1-admission-2,2026-10-05 回修)相对 v1 的变化:
- **元素账计入全部氢(F01)**:重原子 GetTotalNumHs(隐式+显式属性氢)
  与独立氢顶点都入账,不再漏算 —— v1 只数图顶点导致 CCO→CC=O 假
  verified;底物档案(formula/element_counts)用同一计数基准;
- **电荷账前提(F05/mimo C1)**:参与物状态的 fidelity.formal_charge
  轴 == as_written 才可算;CN 归一化形(原始电荷不可知)⇒ 电荷账
  unknown,不得拿中和后电荷算出假通过;
- **CN-only 状态非结构非法(F05)**:合法投影缺原始结构 → parse 检查
  unknown(structure_unavailable_legacy_cn_only),只有实际输入语法
  非法才是 violated(R1);
- **结构化差值输出(F01/mimo 2.2(1) 采纳+Codex 收紧)**:元素/电荷账
  输出逐元素 Δ 向量、电荷缺口与核算范围;与常见漏项模式(H2O/H+/
  O2/nH)的**数值相符**单独标注(仅表示相符,不证明缺项原因,不含
  电子计量推断);
- **ambiguous 参与物阻止完整账(F01)**:未确认并列计量的重复参与物
  ⇒ participant_completeness=unknown,不得 full/verified;
- **violated 与 unknown 分理由码(P2-1/mimo 3.2(2))**:元素/电荷账
  violated ⇒ retain_conditional + declared_account_violated(独立于
  unknown_checks_present);"来源声明与结构不一致"(有证据)与"无证据"
  分家展示;元素 violated 绝不进入 R6"全部核实";
- **R2b(mimo 3.2(1))**:表示契约违反(零/负/非有限系数、酶计入净
  计量、结构性违约)⇒ reject + contract_violated_representation,
  不冒称结构不可解析或化学不可能;
- **旧门禁版本化 mapper(P2-2)**:legacy_validation_to_gate_decisions
  把旧 validation 产物的 gates/逐产物 verdicts 映射为新 admission
  消费形状,逐产物 accepted/拒因保留,不把总体 gate_ref 当全量结果。

既有不变量(§8):必需分项十项;依赖解析的后续项 unknown +
prerequisite_failed_not_run;完整已知参与物和系数才核全账;不先
中和再验;不自动补水/氧/辅酶;元素及电荷账核实 ≠ 机制/电子转移/
热力学/速率已核实(biological_support_status 另轴);G2 仅旧规则
诊断(unclassified=覆盖未知不惩罚);诊断状态与展开决定分开;
unknown 不自动 reject。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from rdkit import Chem, RDLogger

from ..domain.models import content_hash, stable_id
from .chemstate import (
    FIDELITY_AS_WRITTEN,
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
STRUCTURE_UNAVAILABLE = "structure_unavailable_not_run"

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

# 元素缺口与常见漏项模式的数值相符(Codex 收紧版:仅数值相符,
# 不证明缺项原因,不含电子/质子计量推断)
COMMON_OMISSION_PATTERNS: dict[str, dict[str, Fraction]] = {
    "H2O": {"H": Fraction(2), "O": Fraction(1)},
    "H+": {"H": Fraction(1)},
    "O2": {"O": Fraction(2)},
    "2H": {"H": Fraction(2)},
}


class AuditContractError(RuntimeError):
    """审计输入/策略契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 检查对象


@dataclass
class AuditCheck:
    """单项检查(name/status/reason_code/evidence/coverage/detail)。

    detail(v2):机器可读的结构化输出 —— 元素/电荷账的逐元素 Δ 向量、
    缺口模式数值相符、核算范围等(F01 验收"可机器读取的差值")。
    """

    name: str
    status: str                 # verified | violated | unknown | not_applicable
    reason_code: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    coverage: str = ""          # 覆盖说明(如 only_legacy_rules)
    detail: dict = field(default_factory=dict)

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

    def violated_checks(self) -> list[AuditCheck]:
        return [c for c in self.checks if c.status == CHECK_VIOLATED]


def _mol_of(state: ChemicalState | None):
    if state is None or not state.smiles_isomeric:
        return None
    return Chem.MolFromSmiles(state.smiles_isomeric)


def element_counts_full(mol: Chem.Mol) -> dict[str, Fraction]:
    """全部氢计入的元素组成(F01:隐式/显式属性氢/独立氢顶点不重不漏)。

    - 重原子按 symbol 计数;其氢 = GetTotalNumHs()(隐式+显式属性,
      不含独立顶点邻居氢,避免与独立 [H] 顶点重复);
    - 独立氢顶点([H])自身按 H 计数。
    """
    counts: dict[str, Fraction] = {}
    for atom in mol.GetAtoms():
        symbol = atom.GetSymbol()
        counts[symbol] = counts.get(symbol, Fraction(0)) + Fraction(1)
        if symbol != "H":
            n_h = atom.GetTotalNumHs()  # 隐式+显式属性氢
            if n_h:
                counts["H"] = counts.get("H", Fraction(0)) + Fraction(n_h)
    return {k: v for k, v in counts.items() if v != 0}


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

    - states 优先;缺项时从 raw_structures 现场构建(F07:state_ref 与
      构建出的实际身份不一致即拒绝);
    - CN-only 状态(F05)不判结构非法:parse 检查 unknown +
      structure_unavailable_legacy_cn_only;依赖结构的账目检查
      unknown(structure_unavailable_not_run);
    - admission 不在此决定(见 decide_admission;状态与展开分开)。
    """
    states = dict(states or {})
    for ref, structure in (raw_structures or {}).items():
        if ref not in states:
            built = build_chemical_state(structure, "source_product")
            if built.state_id != ref:
                raise AuditContractError(
                    "raw_structures 的 state_ref 与结构实际身份不一致"
                    "(不得以其他分子冒充)",
                    {"state_ref": ref, "actual_state_id": built.state_id})
            states[ref] = built
    requested = set(audit_scope or REQUIRED_CHECK_NAMES)

    checks: list[AuditCheck] = []
    versions = {
        "audit": PPV1_AUDIT_SCHEMA_VERSION,
        "chemstate": "ppv1-chemstate-2",
        "legacy_g2_family": LEGACY_G2_FAMILY_REF,
    }
    # ---- ① 结构解析/价态(CN-only ≠ 非法,F05) ----
    parse_ok = True
    structure_unavailable = False  # CN-only 等合法缺结构:unknown 不是 violated
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
                       if states[p.state_ref].smiles_isomeric == ""
                       and states[p.state_ref].structure_origin
                       != STRUCTURE_ORIGIN_LEGACY_CN_ONLY]
        cn_only = [p.state_ref for p in hypothesis.participants
                   if states[p.state_ref].structure_origin
                   == STRUCTURE_ORIGIN_LEGACY_CN_ONLY]
        if unparseable:
            parse_ok = False
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_VIOLATED,
                reason_code="unparseable_smiles",
                evidence_refs=sorted(unparseable)[:10],
                coverage="participants_with_state"))
        elif cn_only:
            structure_unavailable = True
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_UNKNOWN,
                reason_code="structure_unavailable_legacy_cn_only"
                "(合法投影缺原始结构,非结构化学非法)",
                evidence_refs=sorted(cn_only)[:10],
                coverage="participants_with_state"))
        else:
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_VERIFIED,
                reason_code="all_participants_parse",
                coverage="participants_with_state"))

    prerequisite_failed = not parse_ok  # violated:后续 not_run

    def _dependent(name: str, coverage: str) -> AuditCheck:
        reason = (PREREQUISITE_FAILED if prerequisite_failed
                  else STRUCTURE_UNAVAILABLE)
        return AuditCheck(name=name, status=CHECK_UNKNOWN,
                          reason_code=reason, evidence_refs=[],
                          coverage=coverage)

    # ---- ② 身份信息保真 ----
    if CHECK_IDENTITY_FIDELITY in requested:
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_IDENTITY_FIDELITY, "state_ids"))
        else:
            notes = []
            ok = True
            for p in hypothesis.participants:
                st = states.get(p.state_ref)
                if st is None:
                    continue
                fidelity = st.representation_fidelity or {}
                if st.structure_origin == STRUCTURE_ORIGIN_LEGACY_CN_ONLY:
                    ok = False
                    notes.append(f"cn_only:{p.state_ref}")
                if fidelity.get("stereo") == "absent_in_archive":
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

    # ---- ④ 参与物完整度(ambiguous 阻止 full,F01) ----
    status_list = hypothesis.participant_list_status
    all_known_coeffs = all(p.coefficient_status == COEFFICIENT_KNOWN
                           for p in hypothesis.participants)
    if CHECK_PARTICIPANT_COMPLETENESS in requested:
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_PARTICIPANT_COMPLETENESS,
                                     "participant_list"))
        elif hypothesis.ambiguous_participants:
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS, status=CHECK_UNKNOWN,
                reason_code="ambiguous_duplicate_participants_not_summed"
                "(未确认并列计量的重复参与物不得授予完整账)",
                coverage="participant_list"))
        elif status_list in ("source_complete", "declared_complete"):
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS,
                status=(CHECK_UNKNOWN if not all_known_coeffs
                        else CHECK_VERIFIED),
                reason_code=("coefficients_unknown_declared_complete"
                             if not all_known_coeffs
                             else "declared_complete_with_known_coefficients"),
                coverage="participant_list"))
        else:
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS, status=CHECK_UNKNOWN,
                reason_code=f"participant_list_status:{status_list}",
                coverage="participant_list"))

    # ---- ⑤⑥ 元素/形式电荷核算(全氢 + 电荷轴前提 + 结构化差值) ----
    full_known = (
        hypothesis.participant_list_status in ("source_complete",
                                               "declared_complete")
        and all_known_coeffs
        and not hypothesis.ambiguous_participants)
    reactant_side = [p for p in hypothesis.participants
                     if p.side == PARTICIPANT_SIDE_REACTANT]
    product_side = [p for p in hypothesis.participants
                    if p.side == PARTICIPANT_SIDE_PRODUCT]
    if CHECK_ELEMENT_ACCOUNTING in requested:
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_ELEMENT_ACCOUNTING,
                                     "full_balance"))
        elif full_known:
            elem_check = _element_accounting(
                reactant_side, product_side, states)
            checks.append(elem_check)
        else:
            checks.append(AuditCheck(
                name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="partial_or_unknown_participants_full_balance"
                            "_unknown",
                coverage="full_balance",
                detail={"accounting_scope": "not_run_incomplete_list"}))
    if CHECK_FORMAL_CHARGE_ACCOUNTING in requested:
        # 电荷轴前提(F05/mimo C1)优先:参与物原始电荷不可知(含 CN-only
        # 的中和形)⇒ unknown(original_charge_unavailable),不拿中和后
        # 电荷算假通过 —— 该判定先于"结构不可用"笼统归因
        charge_unavailable = [
            p.state_ref for p in hypothesis.participants
            if (states.get(p.state_ref).representation_fidelity or {})
            .get("formal_charge") != FIDELITY_AS_WRITTEN]
        if full_known and charge_unavailable:
            checks.append(AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="original_charge_unavailable"
                "(CN/中和形输入的电荷账不可算,不得拿中和后电荷算)",
                evidence_refs=charge_unavailable[:10],
                coverage="full_balance"))
        elif prerequisite_failed or structure_unavailable:
            checks.append(_dependent(
                CHECK_FORMAL_CHARGE_ACCOUNTING, "full_balance"))
        elif full_known:
            checks.append(_charge_accounting(
                reactant_side, product_side, states))
        else:
            checks.append(AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="partial_or_unknown_participants_full_balance"
                            "_unknown",
                coverage="full_balance"))

    # ---- ⑦ 映射/变换中心 ----
    if CHECK_TRANSFORMATION_CENTER in requested:
        sig = hypothesis.transformation_signature_status
        if prerequisite_failed or structure_unavailable:
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
                coverage="declared_dimensions",
                detail={"unassessed_dimensions":
                        list(assessment.unassessed_dimensions),
                        "assessment_scope":
                            list(assessment.assessment_scope)}))

    # ---- ⑩ 来源依赖(F06:引用存在但状态未提供 ⇒ 不得视为已解决) ----
    if CHECK_PROVENANCE_DEPENDENCY in requested:
        refs = list(getattr(hypothesis, "dependency_refs", []) or [])
        unresolved = list(unresolved_dependency_ids) \
            if unresolved_dependency_ids is not None else None
        if unresolved:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_UNKNOWN,
                reason_code="unresolved_dependencies_inherited",
                evidence_refs=unresolved[:10], coverage="dependency_set"))
        elif refs and unresolved is None:
            # 有依赖引用但调用方未提供解析状态:不能视为已解决(F06)
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_UNKNOWN,
                reason_code="dependency_resolution_not_provided",
                evidence_refs=refs[:10], coverage="dependency_set"))
        elif refs:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_VERIFIED,
                reason_code="all_dependency_refs_reported_resolved",
                evidence_refs=refs[:10], coverage="dependency_set"))
        else:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_VERIFIED,
                reason_code="no_unresolved_dependencies",
                coverage="dependency_set"))

    audit_id = stable_id(
        "audit", hypothesis.hypothesis_id, scope,
        content_hash([c.to_dict() for c in checks]))
    participant_accounting = (
        "full" if full_known and not prerequisite_failed
        and not structure_unavailable
        else "partial" if not prerequisite_failed
        and not structure_unavailable
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


def _element_accounting(reactant_side, product_side, states) -> AuditCheck:
    """全量元素账(F01:全部氢;系数加权;不补水/氧/辅酶凑平)。

    输出逐元素 Δ = Σ(反应物) − Σ(产物) 与常见漏项模式的数值相符
    (仅数值相符:不证明缺项原因,不含电子/质子计量推断,Codex 收紧)。
    """
    totals: dict[str, Fraction] = {}
    for p, sign in [(p, 1) for p in reactant_side] + [
            (p, -1) for p in product_side]:
        mol = _mol_of(states.get(p.state_ref))
        if mol is None:
            return AuditCheck(
                name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code=f"state_unavailable:{p.state_ref}",
                coverage="full_balance")
        coeff = p.coefficient if p.coefficient is not None else Fraction(0)
        for sym, n in element_counts_full(mol).items():
            totals[sym] = totals.get(sym, Fraction(0)) + sign * n * coeff
    diffs = {sym: v for sym, v in totals.items() if v != 0}
    detail = {
        "element_delta": {sym: str(v) for sym, v in sorted(diffs.items())},
        "accounting_scope": "full_balance_all_hydrogen",
        "omission_pattern_matches": [],
        "omission_pattern_semantics": (
            "pattern_matches 仅表示缺口向量与该常见模式逐元素数值相符"
            "(含方向:reactant_side=反应物侧多出/缺写产物,product_side="
            "产物侧多出/缺写反应物);不证明实际缺该物质、不推断遗漏原因,"
            "不含电子/质子计量"),
    }
    if diffs:
        for name, pattern in COMMON_OMISSION_PATTERNS.items():
            for direction, sign in (("reactant_side", 1),
                                    ("product_side", -1)):
                signed = {k: sign * v for k, v in pattern.items()}
                if diffs == signed:
                    detail["omission_pattern_matches"].append(
                        f"{name}:{direction}")
        detail_str = ";".join(
            f"{sym}:{v}" for sym, v in sorted(diffs.items()))
        return AuditCheck(
            name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_VIOLATED,
            reason_code=f"declared_account_violated:element_imbalance:"
                        f"{detail_str}",
            coverage="full_balance", detail=detail)
    return AuditCheck(
        name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_VERIFIED,
        reason_code="elements_balanced_all_hydrogen",
        coverage="full_balance", detail=detail)


def _charge_accounting(reactant_side, product_side, states) -> AuditCheck:
    """形式电荷账(原始 formal_charge;不先中和;结构化差值输出)。"""
    total = Fraction(0)
    for p, sign in [(p, 1) for p in reactant_side] + [
            (p, -1) for p in product_side]:
        st = states.get(p.state_ref)
        if st is None or st.formal_charge is None:
            return AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code=f"charge_unavailable:{p.state_ref}",
                coverage="full_balance")
        coeff = p.coefficient if p.coefficient is not None else Fraction(0)
        total += sign * st.formal_charge * coeff
    detail = {
        "charge_delta": str(total),
        "accounting_scope": "full_balance_original_formal_charge",
    }
    if total != 0:
        return AuditCheck(
            name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_VIOLATED,
            reason_code=f"declared_account_violated:charge_imbalance:"
                        f"{total}",
            coverage="full_balance", detail=detail)
    return AuditCheck(
        name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_VERIFIED,
        reason_code="formal_charge_balanced",
        coverage="full_balance", detail=detail)


# ---------------------------------------------------------------- admission


@dataclass
class AdmissionPolicy:
    """P0-4:admission 策略(schema + 完整决策表;v2 +R2b +violated 分码)。

    规则(评估顺序固定,首中即决):
    R1  structure_unparseable      → reject  (实际输入语法非法;CN-only
        等合法缺结构走 unknown,不进本行,F05)
    R2  active_gate_rejected       → reject  (活动门禁显式拒绝;仅
        reject_gates 名单内 —— 不暗改冻结判据,新门禁须独立评审)
    R2b contract_violated_       → reject  (表示契约违反:零/负/非有限
        representation                  系数、酶计入净计量、结构性违约;
        理由码写死 representation = 非化学,mimo 3.2(1) 采纳)
    R3  current_scenario_conflict  → defer   (有来源 essential 条件与当前
        场景已知事实冲突;action=blocked,假设保留不在此场景展开)
    R4  budget_or_wait             → defer   (独立原因)
    R5d declared_account_violated  → retain_conditional(元素/电荷账
        violated = **声明与结构不一致**(有证据的发现),独立理由码,
        与 unknown 分家;不 reject —— 账不平只证明声明内部矛盾,不
        证明反应不存在;绝不进入 R6"全部核实")
    R5  unknown_checks_present     → retain_conditional(仅条件/完整账/
        映射/step_scope 未知;继承未解决依赖)
    R6  default_all_verified       → expand
    R7  no_applicable_checks       → retain_conditional(无适用检查:
        保守保留,不冒充核实;理由与 R5 分开)

    任何 unknown 不自动 reject;新增"诊断转拒绝"必须扩本表并升版本。
    chemical_reproposal 首版 off。
    """

    policy_version: str = PPV1_ADMISSION_POLICY_VERSION
    reject_gates: frozenset = frozenset(DEFAULT_REJECT_GATES)
    chemical_reproposal: str = "off"
    rules: tuple = (
        ("R1", "structure_unparseable", ADMISSION_REJECT),
        ("R2", "active_gate_rejected", ADMISSION_REJECT),
        ("R2b", "contract_violated_representation", ADMISSION_REJECT),
        ("R3", "current_scenario_conflict", ADMISSION_DEFER),
        ("R4", "budget_or_wait", ADMISSION_DEFER),
        ("R5d", "declared_account_violated", ADMISSION_RETAIN_CONDITIONAL),
        ("R5", "unknown_checks_present", ADMISSION_RETAIN_CONDITIONAL),
        ("R6", "default_all_verified", ADMISSION_EXPAND),
        ("R7", "no_applicable_checks", ADMISSION_RETAIN_CONDITIONAL),
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
    contract_violation: dict | None = None,
) -> tuple[str, list[str]]:
    """audit × 策略 → (admission_disposition, reasons)(纯函数)。

    gate_decisions:{"<gate_name>": {"ok": bool, "reason": str}}(活动
    门禁的既有真假;本函数不改判,只按 policy.reject_gates 消费)。
    budget_state:{"exhausted": bool, "waiting": bool, "reason": str}。
    contract_violation(R2b):表示契约违反的调用方报告(如 Hypothesis-
    ContractError 的 detail)→ reject + contract_violated_representation
    —— 不冒称结构不可解析或化学不可能。
    """
    pol = policy or DEFAULT_ADMISSION_POLICY
    reasons: list[str] = []

    # R1:实际输入语法非法 → reject(CN-only 合法缺结构是 unknown,不到此)
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

    # R2b:表示契约违反(构造层报告;非化学)
    if contract_violation is not None:
        detail_code = str(contract_violation.get(
            "kind", contract_violation.get("reason_code", ""))[:120])
        return ADMISSION_REJECT, [
            "R2b:contract_violated_representation:"
            f"{detail_code}(输入表示违反契约,非结构不可解析、"
            "非化学不可能)"]

    # R3:当前场景有来源必要条件冲突 → defer(blocked)
    if audit.check_status(CHECK_CONDITION_CHECK) == CHECK_VIOLATED:
        return ADMISSION_DEFER, [
            "R3:current_scenario_conflict(当前环境相容路线不展开;"
            "假设保留,留原因,可展示为需不同条件的备选)"]

    # R4:预算/等待 → defer(独立原因)
    bs = budget_state or {}
    if bs.get("exhausted") or bs.get("waiting"):
        return ADMISSION_DEFER, [
            f"R4:budget_or_wait:{bs.get('reason', 'budget_or_waiting')}"]

    # R5d:声明账 violated(有证据的不一致;独立理由码,与 unknown 分家)
    violated = audit.violated_checks()
    if violated:
        names = [c.name for c in violated]
        return ADMISSION_RETAIN_CONDITIONAL, [
            "R5d:declared_account_violated(声明与结构不一致,有证据的"
            "发现;不 reject —— 账不平不证明反应不存在;绝不计入"
            "'全部核实'):" + ",".join(names)]

    # R5:存在 unknown 检查 → retain_conditional(继承依赖)
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

    # R7:无适用检查:保守 retain(理由与 R5 分开,不冒充核实)
    return ADMISSION_RETAIN_CONDITIONAL, [
        "R7:no_applicable_checks_conservative_retain(无适用检查证据,"
        "不默认 expand,不以无证据冒充核实)"]


# ---------------------------------------------------- 旧门禁 → 新 admission(P2-2)


LEGACY_GATE_MAPPER_VERSION = "ppv1-gate-mapper-1"


def legacy_validation_to_gate_decisions(
    validation_payload: dict,
) -> dict:
    """旧 validation 产物 → 新 admission 的 gate_decisions 形状(版本化)。

    旧产物(nodes.validate_products 的 validation.json payload)结构:
    {"evidence_id", "gates": {"direction_source": {ok, reason},
     "atom_mapping": {ok, reason, value},
     "recorded_eligibility": {ok, reason}},
     "verdicts": [{position, accepted, reasons, ...}], ...}。

    映射:
    - gate_direction_source / gate_recorded_eligibility 进入默认
      reject 名单形状({"ok", "reason"} 原样透传,不改判);
    - gate_atom_mapping_declared 附带(不在默认 reject 名单,供策略
      显式消费);
    - **逐产物 verdicts 全量保留**(每共同产物的 accepted/拒因),
      不把总体 gates 摘要当作全量结果(元素门禁体现在逐产物 verdict);
    - gate_ref:原产物引用(调用方传 task_id/artifact hash)。
    """
    gates = validation_payload.get("gates") or {}
    out: dict[str, dict] = {}
    if "direction_source" in gates:
        out[GATE_NAME_DIRECTION_SOURCE] = {
            "ok": bool(gates["direction_source"].get("ok", False)),
            "reason": str(gates["direction_source"].get("reason", ""))[:300]}
    if "recorded_eligibility" in gates:
        out[GATE_NAME_RECORDED_ELIGIBILITY] = {
            "ok": bool(gates["recorded_eligibility"].get("ok", False)),
            "reason": str(gates["recorded_eligibility"].get(
                "reason", ""))[:300]}
    if "atom_mapping" in gates:
        out["gate_atom_mapping_declared"] = {
            "ok": bool(gates["atom_mapping"].get("ok", False)),
            "reason": str(gates["atom_mapping"].get("reason", ""))[:300],
            "value": gates["atom_mapping"].get("value")}
    out["per_product_verdicts"] = [
        {"position": v.get("position"),
         "accepted": bool(v.get("accepted", False)),
         "reasons": list(v.get("reasons", []))}
        for v in validation_payload.get("verdicts", [])]
    out["gate_ref"] = {
        "evidence_id": validation_payload.get("evidence_id", ""),
        "mapper_version": LEGACY_GATE_MAPPER_VERSION,
    }
    return out


# ---------------------------------------------------------------- 供体诊断


@dataclass
class DonorConsistencyDiagnostic:
    """§8 供体诊断(v2:真实编辑协议 + basis 字段 + 等价类验证)。

    strict 轴使用与 ChemicalState 同一事实源的严格表示(含增强立体);
    legacy_cn_match 仅旁证(corroborating),任何汇总/计数不得以 CN
    计"一致数";reaction_center_match 依据实际键变化与可追溯映射,
    带 center_match_basis ∈ {direct, symmetric_equivalent};等价关系
    从分子图自同构验证,不采信调用方自报任意集合。
    """

    strict_target_match: bool | None
    legacy_cn_match: bool | None       # 旁证(corroborating),不进计数
    reaction_center_match: bool | None
    center_match_basis: str = ""       # direct | symmetric_equivalent
    extra_changes: list[dict] = field(default_factory=list)  # 逐原子 Δ 摘要
    alignment_ref: str = ""
    missing_info_reasons: list[str] = field(default_factory=list)
    executed_bond_changes: list[dict] = field(default_factory=list)
    schema_version: str = PPV1_DONOR_DIAGNOSTIC_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _edit_atom_ids(edits: list[dict]) -> set[str]:
    """真实编辑协议(v43-editproto-2)中出现的原子标识(atom1/atom2)。"""
    out: set[str] = set()
    for edit in edits or []:
        for key in ("atom1", "atom2"):
            if edit.get(key) is not None:
                out.add(str(edit[key]))
    return out


def _bond_changes(before: Chem.Mol, after_mapped: Chem.Mol,
                  id_to_idx_after: dict[str, int]) -> list[dict]:
    """执行前后结构的实际键变化集合(键级/成断键;原子增删另列)。

    after_mapped:带映射号的执行图产物(映射号 = 执行图原子 idx+1,
    execute_edits 的 product_mapped_smiles);id_to_idx_after:
    MoleCode ID → 执行图 idx(执行输出的 atom_id_map)。
    返回 [{atom1_id, atom2_id, kind: order_change|bond_formed|bond_broken,
    from_order, to_order}]。
    """
    before_bonds: dict[frozenset, str] = {}
    for bond in before.GetBonds():
        key = frozenset((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()))
        before_bonds[key] = _bond_order_name(bond.GetBondType())
    after_bonds: dict[frozenset, str] = {}
    for bond in after_mapped.GetBonds():
        a = bond.GetBeginAtom().GetAtomMapNum() - 1
        b = bond.GetEndAtom().GetAtomMapNum() - 1
        after_bonds[frozenset((a, b))] = _bond_order_name(bond.GetBondType())

    def idx_to_id(idx: int) -> str:
        for aid, i in id_to_idx_after.items():
            if i == idx:
                return aid
        return f"idx:{idx}"

    changes: list[dict] = []
    for key, order_after in after_bonds.items():
        order_before = before_bonds.get(key)
        a, b = tuple(key)
        if order_before is None:
            changes.append({"atom1_id": idx_to_id(a),
                            "atom2_id": idx_to_id(b),
                            "kind": "bond_formed",
                            "from_order": "", "to_order": order_after})
        elif order_before != order_after:
            changes.append({"atom1_id": idx_to_id(a),
                            "atom2_id": idx_to_id(b),
                            "kind": "order_change",
                            "from_order": order_before,
                            "to_order": order_after})
    for key, order_before in before_bonds.items():
        if key not in after_bonds:
            a, b = tuple(key)
            changes.append({"atom1_id": idx_to_id(a),
                            "atom2_id": idx_to_id(b),
                            "kind": "bond_broken",
                            "from_order": order_before, "to_order": ""})
    changes.sort(key=lambda c: (c["atom1_id"], c["atom2_id"], c["kind"]))
    return changes


def _bond_order_name(bond_type) -> str:
    return {Chem.BondType.SINGLE: "single",
            Chem.BondType.DOUBLE: "double",
            Chem.BondType.TRIPLE: "triple"}.get(bond_type, str(bond_type))


def _validate_equivalence_classes(equivalence_classes: list,
                                  current_mol: Chem.Mol,
                                  id_to_idx: dict[str, int]) -> tuple[
                                      dict[str, set[str]], list[list[str]]]:
    """等价类从分子图自同构验证(F11:不采信自报任意集合)。

    仅当等价类成员在当前分子图上对称等价(RDKit 无 tie-breaking 的
    canonical rank 同类)时,该等价类才被采信;含非等价成员或未知
    原子的类整体弃用并记入 rejected(不部分采用)。返回
    (采信的等价展开 dict, 被拒的类列表)。
    """
    if current_mol is None:
        return {}, [list(c) for c in (equivalence_classes or [])]
    symmetry_classes = list(Chem.CanonicalRankAtoms(
        current_mol, breakTies=False))
    out: dict[str, set[str]] = {}
    rejected: list[list[str]] = []
    for eq_class in equivalence_classes or []:
        members = [str(a) for a in eq_class]
        idxs = [id_to_idx.get(m) for m in members]
        if any(i is None for i in idxs):
            rejected.append(members)
            continue
        ranks = {symmetry_classes[i] for i in idxs}
        if len(ranks) == 1:
            for m in members:
                out.setdefault(m, set()).update(members)
        else:
            rejected.append(members)
    return out, rejected


def check_edit_against_donor(
    *,
    current: dict,
    donor: dict,
    alignment: dict,
    expectation: dict,
    result: dict,
    edits: list[dict],
) -> DonorConsistencyDiagnostic:
    """§7.1 固定接口(v2):消费**真实 AtomTool 编辑协议**的诊断。

    输入(与 v43-editproto-2 / execute_edits 输出对接):
    - current: {"smiles": str, "atom_id_map": {id: idx}}(编辑前
      MoleculeRender 的渲染事实;atom_id_map 用于等价类验证);
    - donor: {"center_atom_ids": [...]}(供体反应变换中心的供体侧原子);
    - alignment: {"status": resolved|ambiguous|unavailable,
      "donor_to_current": {donor_atom: current_atom},
      "equivalence_classes": [[atom, ...]](须过分子图自同构验证),
      "ref": str};
    - expectation: {"target_smiles": str}(供体迁移预期产物);
    - result: execute_edits 的输出 dict(ok/product_smiles/
      product_mapped_smiles/atom_id_map);ok=False ⇒ 全轴 unknown +
      execution_failed(编辑没有成功执行,无从诊断);
    - edits: 真实协议编辑列表(op/atom1/atom2/from_order/to_order/…)。

    判定:
    - strict_target_match:实际产物 vs 预期产物的严格身份(与
      ChemicalState 同源,含增强立体);
    - reaction_center_match:依据**实际键变化集合**(执行前后结构 diff)
      与供体中心(经对齐映射)比对 —— 全部中心原子须有映射(缺 ⇒
      unknown);键变化全部位于中心区域(direct)或其**经验证的**
      对称等价像(symmetric_equivalent)⇒ True;中心区域外存在键
      变化 ⇒ False + extra_changes(逐原子 Δ 摘要);
    - legacy_cn_match:CN 旁证(corroborating;不进计数)。
    """
    missing: list[str] = []
    alignment_status = str(alignment.get("status", "unavailable"))
    if alignment_status not in ("resolved", "ambiguous", "unavailable"):
        raise AuditContractError(
            f"alignment.status 非法:{alignment_status!r}",
            {"status": alignment_status})
    alignment_ref = str(alignment.get("ref", "") or stable_id(
        "align", str(alignment.get("donor_to_current", ""))))

    execution_ok = bool(result.get("ok"))
    if not execution_ok:
        return DonorConsistencyDiagnostic(
            strict_target_match=None, legacy_cn_match=None,
            reaction_center_match=None, center_match_basis="",
            alignment_ref=alignment_ref,
            missing_info_reasons=[
                "execution_failed:" +
                ";".join(result.get("reasons", []) or [])[:200]],
            executed_bond_changes=[])

    # ---- 执行图事实 ----
    current_smiles = current.get("smiles", "")
    mol_before = Chem.MolFromSmiles(str(current_smiles)) \
        if current_smiles else None
    product_mapped = result.get("product_mapped_smiles", "")
    mol_after = Chem.MolFromSmiles(str(product_mapped)) \
        if product_mapped else None
    id_to_idx_after = {
        str(k): int(v) for k, v in (result.get("atom_id_map") or {}).items()}
    if mol_before is None or mol_after is None:
        return DonorConsistencyDiagnostic(
            strict_target_match=None, legacy_cn_match=None,
            reaction_center_match=None, alignment_ref=alignment_ref,
            missing_info_reasons=["before_or_after_structure_unparseable"],
            executed_bond_changes=[])
    id_to_idx_before = {
        str(k): int(v) for k, v in (current.get("atom_id_map") or {}).items()}
    bond_changes = _bond_changes(mol_before, mol_after, id_to_idx_after)

    # ---- strict(与 ChemicalState 同源严格表示) ----
    strict = None
    cn_match = None
    result_smiles = result.get("product_smiles")
    expected_smiles = expectation.get("target_smiles")
    if result_smiles and expected_smiles:
        from .chemstate import strict_identity_of, ChemicalStateError

        try:
            strict = (strict_identity_of(str(result_smiles))
                      == strict_identity_of(str(expected_smiles)))
        except ChemicalStateError:
            strict = None
            missing.append("target_or_result_unparseable")
        from ..domain.identity import cn_identity as _cn

        cn_a = _cn(str(result_smiles))
        cn_b = _cn(str(expected_smiles))
        if cn_a is not None and cn_b is not None:
            cn_match = cn_a == cn_b
    else:
        missing.append("target_or_result_smiles_missing")

    # ---- reaction center(实际键变化 + 对齐映射 + 等价类验证) ----
    center_match = None
    basis = ""
    extra_changes: list[dict] = []
    donor_centers = [str(a) for a in (donor.get("center_atom_ids") or [])]
    changed_atoms = {c["atom1_id"] for c in bond_changes} | {
        c["atom2_id"] for c in bond_changes}
    # add_atom 的锚与新增原子也在变化集中(新增原子的 id 由执行图带出)
    changed_atoms |= _edit_atom_ids(edits)

    if alignment_status != "resolved":
        center_match = None
        missing.append(f"alignment_{alignment_status}_center_unknown")
    elif not donor_centers or not changed_atoms:
        center_match = None
        missing.append("center_or_edits_unavailable")
    else:
        mapping = {
            str(k): str(v)
            for k, v in (alignment.get("donor_to_current") or {}).items()}
        # 等价类验证(F11:自报集合须过分子图自同构;被拒的类不采信)
        equivalence, rejected_classes = _validate_equivalence_classes(
            alignment.get("equivalence_classes") or [],
            mol_before, id_to_idx_before)
        if rejected_classes:
            missing.append(
                "equivalence_class_rejected_by_graph_automorphism:"
                + ";".join(",".join(c) for c in rejected_classes)[:160]
                + "(非等价成员的类不被采信)")
        # 全部供体中心原子必须有映射(部分缺映射 ⇒ unknown,不部分判定)
        unmapped = [d for d in donor_centers if d not in mapping]
        if unmapped:
            center_match = None
            missing.append(
                "donor_centers_partially_unmapped:" + ",".join(unmapped))
        else:
            center_direct = {mapping[d] for d in donor_centers}
            center_extended = set(center_direct)
            for atom in center_direct:
                center_extended |= equivalence.get(atom, set())
            outside = changed_atoms - center_extended
            if not outside:
                center_match = True
                # basis:命中方式(直接映射命中 ⇒ direct;等价像命中 ⇒
                # symmetric_equivalent —— 图等价不证明酶识别/机制等价)
                used_equiv = any(
                    atom not in center_direct and atom in equivalence
                    for atom in changed_atoms)
                basis = ("symmetric_equivalent" if used_equiv
                         else "direct")
                extra_changes = []
            elif changed_atoms & center_extended:
                center_match = False  # 中心内外都有变化 ⇒ 偏离
                basis = "direct"
                extra_changes = _atom_change_summary(
                    outside, mol_before, mol_after, id_to_idx_after)
            else:
                center_match = False  # 全部变化在中心区域外
                basis = "direct"
                extra_changes = _atom_change_summary(
                    outside, mol_before, mol_after, id_to_idx_after)

    return DonorConsistencyDiagnostic(
        strict_target_match=strict, legacy_cn_match=cn_match,
        reaction_center_match=center_match, center_match_basis=basis,
        extra_changes=extra_changes, alignment_ref=alignment_ref,
        missing_info_reasons=missing,
        executed_bond_changes=bond_changes)


def _atom_change_summary(atoms: set[str], before: Chem.Mol,
                         after: Chem.Mol, id_to_idx_after: dict) -> list[
                             dict]:
    """中心区域外变化原子的逐原子 Δ 摘要(元素/形式电荷语言可读)。"""
    out = []
    for aid in sorted(atoms):
        idx = id_to_idx_after.get(aid)
        entry = {"atom_id": aid, "delta": []}
        if idx is not None and idx < after.GetNumAtoms():
            atom = after.GetAtomWithIdx(idx)
            entry["element"] = atom.GetSymbol()
            entry["formal_charge"] = atom.GetFormalCharge()
            entry["delta"].append("present_in_product")
        else:
            entry["delta"].append("absent_in_product_or_unmapped")
        out.append(entry)
    return out
