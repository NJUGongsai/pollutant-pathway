"""ChemicalAudit — 检查范围明确,未知不可冒充核实(v3 回修,S2)。

v3(ppv1-audit-3 / ppv1-admission-3,2026-10-06 R3 回修)相对 v2 的变化
(Codex R2 复审 R2-01/02/03/12 + mimo R2 §3/5 采纳边界):
- **必需检查覆盖(R2-01)**:admission 的 R6"全部核实"要求全部必需
  适用检查被实际执行且 verified —— 窄 audit_scope 只是诊断(缺覆盖
  ⇒ R5c 不 expand);真正语义不适用的项(如关闭的有限规则诊断、
  multistep 汇总边)可 NA 但须带理由;**因缺输入而未执行的检查记
  unknown(reason=*_not_run),不得记 not_applicable**(context 缺失 ⇒
  condition_check=unknown(condition_assessment_not_run),mimo 3.2(1));
- **缺参与物 state 不崩溃(R2-01)**:悬空 state 引用单列
  participant_state_refs 检查(violated/participant_state_missing),
  parse 检查记 unknown(不能核),受影响后续项 unknown +
  prerequisite_failed_not_run;admission 走 **R1b** 拒绝(账本/引用
  完整性问题,不压平成 R1"结构不可解析",mimo 3.2(2));
- **变换中心不采信自报签名(R2-01/5.3)**:
  transformation_signature_status=verified 只是声明;检查 verified 须
  供 center_evidence(注册版本化确定性 checker 的输出,如供体诊断),
  缺证据 ⇒ unknown(center_evidence_missing)——"verified 不得靠模型
  或调用方字符串";
- **R5d 触发集合显式限定**(mimo 3.2(4)):{element_accounting,
  formal_charge_accounting};其他 violated 走 R5v declared_violated_
  other,不冒称"声明账不一致";
- **input_hash 覆盖实际科学输入**(R2-07):hypothesis 完整语义载荷
  (含 requirements/assumptions/dependency_refs)、参与物 state 身份、
  context 身份、audit_scope、checker 版本 —— 不把一个引用 ID 当完整
  输入证明;
- **供体诊断实际净变化**(R2-03):判定基础 = 实际变化集(键 diff ∪
  原子增删 ∪ 逐原子形式电荷/氢数/立体 diff),声明的编辑原子单独列
  declaration_only 不参与判定;零净变化 ⇒ center=unknown
  (no_executed_change) 永不 True;声明–执行一致性对账
  (declaration_mismatches);symmetric_equivalent 须由**联合图映射**
  (整个中心集合存在单一自同构像)证明,单原子对称轨道不冒充;
  extra_changes 补 ΔH 与 Δ立体;plain 产物与 mapped 图对账;
- **冻结门禁逐产物拒绝真实消费(R2-12)**:decide_admission 消费
  mapper 的 per_product_verdicts —— 全部共同产物被拒 ⇒ reject,
  部分 ⇒ retain_conditional(被拒产物保留拒因、不可展开),不删除
  被拒共同产物凑合法事件,不改冻结门禁真假;消费开关由策略显式
  版本化(per_product_gate_consumption);
- **身份保真分轴呈现**(mimo 1.4(4)):参与物任一保真轴非
  as_written ⇒ identity_fidelity=unknown(列轴),不再
  verified+reason 注记混读;
- **元素账口径注记**(mimo 2.2(a)):D/T 并入元素 H(同位素不入
  本账)、自由基电子不入账;verified 仅指元素与形式电荷数值闭合;
  radical 保真轴为已知缺口(身份层区分自由基,本轴未实现);
- **omission 模式结构化**(mimo 2.3(2)):omission_pattern_matches
  为结构化字段 {pattern, excess_on, missing_from, element_delta};
  H+ 模式输出名 H+_count1(仅 H 计数 1 的模式名,不含质子/电子计量)。

未落地条款(contract clause, implementation pending,不得当已检查):
local_delta(局部结构差,S3/展示层)、edge_kind(互变/质子化边,S3)、
cn_identity 的 basis: scoring_key 标记(S3)。完整供体变换模板的
供体侧预期键变化对比留 S3 接线;当前诊断命名:**实际净变化区域
诊断**,不冒充完整变换一致。

v2(ppv1-audit-2,2026-10-05 回修)的变化:全氢元素账(F01);电荷账
fidelity 前提(F05);CN-only 非结构非法(F05);结构化差值(F01);
ambiguous 参与物阻止完整账(F01);violated/unknown 分码(P2-1);
R2b(mimo 3.2(1));旧门禁版本化 mapper(P2-2)。

既有不变量(§8):必需分项;依赖解析的后续项 unknown +
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
    PPV1_CHEMSTATE_SCHEMA_VERSION,
    PPV1_CONDITION_ASSESSMENT_VERSION,
    PPV1_DONOR_DIAGNOSTIC_VERSION,
    PPV1_GATE_MAPPER_VERSION,
    PPV1_HYPOTHESIS_SCHEMA_VERSION,
)

RDLogger.DisableLog("rdApp.*")

CHECK_STRUCTURE_PARSE_VALENCE = "structure_parse_valence"
CHECK_IDENTITY_FIDELITY = "identity_fidelity"
CHECK_FINITE_RULE_DIAGNOSTIC = "finite_rule_diagnostic"
CHECK_PARTICIPANT_COMPLETENESS = "participant_completeness"
CHECK_PARTICIPANT_STATE_REFS = "participant_state_refs"
CHECK_ELEMENT_ACCOUNTING = "element_accounting"
CHECK_FORMAL_CHARGE_ACCOUNTING = "formal_charge_accounting"
CHECK_TRANSFORMATION_CENTER = "transformation_center"
CHECK_STEP_SCOPE = "step_scope_check"
CHECK_CONDITION_CHECK = "condition_check"
CHECK_PROVENANCE_DEPENDENCY = "provenance_dependency"
REQUIRED_CHECK_NAMES = (
    CHECK_STRUCTURE_PARSE_VALENCE, CHECK_IDENTITY_FIDELITY,
    CHECK_FINITE_RULE_DIAGNOSTIC, CHECK_PARTICIPANT_COMPLETENESS,
    CHECK_PARTICIPANT_STATE_REFS, CHECK_ELEMENT_ACCOUNTING,
    CHECK_FORMAL_CHARGE_ACCOUNTING, CHECK_TRANSFORMATION_CENTER,
    CHECK_STEP_SCOPE, CHECK_CONDITION_CHECK,
    CHECK_PROVENANCE_DEPENDENCY,
)
# R5d(声明账 violated)的显式触发集合(mimo 3.2(4):其他 violated
# 用 R5v 独立码,防止将来新增检查静默挂进"声明账不一致")
R5D_TRIGGER_CHECKS = frozenset({CHECK_ELEMENT_ACCOUNTING,
                                CHECK_FORMAL_CHARGE_ACCOUNTING})
# 语义 NA 白名单(真不适用,允许在 R6 覆盖核算中缺席;缺输入未执行
# 不在此列 —— 那些必须 unknown)。键:检查名;值:允许的 reason 片段。
SEMANTIC_NA_ALLOWED = {
    CHECK_FINITE_RULE_DIAGNOSTIC: (
        "not_provided", "legacy_g2_diagnostic_reference",
        "input_preview_diagnostic_only_coverage_limited",
        "input_preview_off"),
    CHECK_STEP_SCOPE: ("multistep_summary_kept_as_summary_edge",),
}

# 变换中心检查接受证据的注册确定性 checker 版本(R2-01:自报签名/
# 模型字符串不是检查结果;其他注册 checker 须独立列项评审后加入)
CENTER_CHECKER_REGISTRY = frozenset({PPV1_DONOR_DIAGNOSTIC_VERSION})

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
    center_evidence: dict | None = None,
) -> ChemicalAudit:
    """§7.1 固定接口:hypothesis × audit_scope × policy → ChemicalAudit。

    - states 优先;缺项时从 raw_structures 现场构建(F07:state_ref 与
      构建出的实际身份不一致即拒绝);
    - 参与物 state 引用悬空(**账本/引用完整性问题,非结构非法**,
      R2-01):单列 participant_state_refs 检查 violated
      (participant_state_missing),parse 检查记 unknown(不能核),
      受影响后续项 unknown + prerequisite_failed_not_run,不崩溃;
    - CN-only 状态(F05)不判结构非法:parse 检查 unknown +
      structure_unavailable_legacy_cn_only;
    - context 缺失 ⇒ condition_check=unknown
      (condition_assessment_not_run)—— 缺输入未执行不是语义不适用
      (R2-01/mimo 3.2(1)),不得记 not_applicable;
    - center_evidence(R2-01):注册版本化确定性 checker(见
      CENTER_CHECKER_REGISTRY)的变换中心证据;自报
      transformation_signature_status 不是检查结果 —— 无证据时中心
      检查 unknown(center_evidence_missing);
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
        "chemstate": PPV1_CHEMSTATE_SCHEMA_VERSION,
        "hypothesis": PPV1_HYPOTHESIS_SCHEMA_VERSION,
        "condition_assessment": PPV1_CONDITION_ASSESSMENT_VERSION,
        "donor_diagnostic": PPV1_DONOR_DIAGNOSTIC_VERSION,
        "legacy_g2_family": LEGACY_G2_FAMILY_REF,
    }
    # ---- ① 结构解析/价态(CN-only ≠ 非法,F05;悬空引用 ≠ 语法非法) ----
    parse_ok = True
    structure_unavailable = False  # CN-only 等合法缺结构:unknown 不是 violated
    missing_state_refs: list[str] = []
    for p in hypothesis.participants:
        if p.state_ref not in states:
            missing_state_refs.append(p.state_ref)
    if missing_state_refs:
        # 悬空 state 引用:账本/引用完整性问题(R2-01)。parse 检查不能
        # 核(unknown),单列 violated 检查供 admission R1b 拒绝;后续
        # 依赖结构的检查 unknown + prerequisite_failed_not_run。
        parse_ok = False
        checks.append(AuditCheck(
            name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_UNKNOWN,
            reason_code="participant_state_missing"
                        "(引用悬空,结构无法核,非语法非法)",
            evidence_refs=sorted(missing_state_refs)[:10],
            coverage="participants_with_state"))
        checks.append(AuditCheck(
            name=CHECK_PARTICIPANT_STATE_REFS, status=CHECK_VIOLATED,
            reason_code="participant_state_missing",
            evidence_refs=sorted(missing_state_refs)[:10],
            coverage="state_ledger_references"))
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
        # 引用齐全时,状态引用检查 verified(账本完整性轴,与 parse
        # 分轴;同 parse ①不进 scope 门 —— 纯账本检查,不可被窄 scope
        # 诊断跳过)
        checks.append(AuditCheck(
            name=CHECK_PARTICIPANT_STATE_REFS, status=CHECK_VERIFIED,
            reason_code="all_participant_states_resolved",
            coverage="state_ledger_references"))

    prerequisite_failed = not parse_ok  # violated:后续 not_run

    def _dependent(name: str, coverage: str) -> AuditCheck:
        reason = (PREREQUISITE_FAILED if prerequisite_failed
                  else STRUCTURE_UNAVAILABLE)
        return AuditCheck(name=name, status=CHECK_UNKNOWN,
                          reason_code=reason, evidence_refs=[],
                          coverage=coverage)

    # ---- ② 身份信息保真(分轴呈现,mimo 1.4(4)) ----
    if CHECK_IDENTITY_FIDELITY in requested:
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_IDENTITY_FIDELITY, "state_ids"))
        else:
            axis_notes = []
            for p in hypothesis.participants:
                st = states.get(p.state_ref)
                if st is None:
                    continue
                if st.structure_origin == STRUCTURE_ORIGIN_LEGACY_CN_ONLY:
                    axis_notes.append(f"cn_only:{p.state_ref}")
                fidelity = st.representation_fidelity or {}
                for axis, value in sorted(fidelity.items()):
                    if value != FIDELITY_AS_WRITTEN:
                        axis_notes.append(
                            f"{p.state_ref}:{axis}={value}")
            checks.append(AuditCheck(
                name=CHECK_IDENTITY_FIDELITY,
                status=(CHECK_UNKNOWN if axis_notes
                        else CHECK_VERIFIED),
                reason_code=("identity_fidelity_axes_not_as_written:"
                             + ";".join(axis_notes[:20])
                             if axis_notes
                             else "identity_states_consistent"),
                coverage="state_ids",
                detail={"fidelity_axis_notes": axis_notes[:50]}))

    # ---- ③ 冻结有限规则诊断(真正语义 NA:关闭/未提供的旧诊断) ----
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
        # 电荷算假通过 —— 该判定先于"结构不可用"笼统归因。
        # R2-01:悬空引用不在此崩溃(states.get 可为 None),账本轴由
        # participant_state_refs 检查承接。
        charge_unavailable = [
            p.state_ref for p in hypothesis.participants
            if (states.get(p.state_ref) is not None
                and (states[p.state_ref].representation_fidelity or {})
                .get("formal_charge") != FIDELITY_AS_WRITTEN)]
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

    # ---- ⑦ 映射/变换中心(证据门:自报签名不是检查结果,R2-01) ----
    if CHECK_TRANSFORMATION_CENTER in requested:
        sig = hypothesis.transformation_signature_status
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_TRANSFORMATION_CENTER,
                                     "mapping_dependent"))
        elif center_evidence is None:
            # 无确定性证据:自报 verified 不授信(mimo 5.3/R2-01);
            # declared 状态保留在 detail,不当作检查结果
            checks.append(AuditCheck(
                name=CHECK_TRANSFORMATION_CENTER, status=CHECK_UNKNOWN,
                reason_code="center_evidence_missing"
                "(自报 transformation_signature_status 不是检查结果;"
                f"declared={sig or 'unavailable'})",
                coverage="mapping_dependent",
                detail={"declared_signature_status": sig or ""}))
        else:
            checker = str(center_evidence.get("checker_version", ""))
            if checker not in CENTER_CHECKER_REGISTRY:
                checks.append(AuditCheck(
                    name=CHECK_TRANSFORMATION_CENTER, status=CHECK_UNKNOWN,
                    reason_code=f"center_checker_not_registered:{checker}"
                    "(确定性中心 checker 须注册并独立列项评审)",
                    coverage="mapping_dependent",
                    detail={"declared_signature_status": sig or "",
                            "checker_version": checker}))
            else:
                mismatch = bool(center_evidence.get("declaration_mismatch"))
                center_match = center_evidence.get("center_match")
                refs = [str(r) for r in center_evidence.get(
                    "evidence_refs", [])][:10]
                if mismatch or center_match is None:
                    checks.append(AuditCheck(
                        name=CHECK_TRANSFORMATION_CENTER,
                        status=CHECK_UNKNOWN,
                        reason_code=(
                            "center_evidence_inconclusive"
                            + ("_declaration_mismatch" if mismatch else "")
                            + ("_center_unknown" if center_match is None
                               else "")),
                        evidence_refs=refs, coverage="mapping_dependent",
                        detail={"declared_signature_status": sig or "",
                                "checker_version": checker}))
                elif center_match is True:
                    checks.append(AuditCheck(
                        name=CHECK_TRANSFORMATION_CENTER,
                        status=CHECK_VERIFIED,
                        reason_code=(
                            "center_evidence_verified"
                            f":{checker}(basis="
                            f"{center_evidence.get('center_match_basis', '')})"),
                        evidence_refs=refs, coverage="mapping_dependent",
                        detail={"declared_signature_status": sig or "",
                                "checker_version": checker}))
                else:  # center_match is False:声明中心与实际变化偏离
                    checks.append(AuditCheck(
                        name=CHECK_TRANSFORMATION_CENTER,
                        status=CHECK_VIOLATED,
                        reason_code=(
                            f"center_mismatch_per_deterministic_checker:"
                            f"{checker}"),
                        evidence_refs=refs, coverage="mapping_dependent",
                        detail={"declared_signature_status": sig or "",
                                "checker_version": checker}))

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

    # ---- ⑨ 条件检查(缺输入未执行 = unknown,不是语义 NA,R2-01) ----
    if CHECK_CONDITION_CHECK in requested:
        if context is None:
            checks.append(AuditCheck(
                name=CHECK_CONDITION_CHECK, status=CHECK_UNKNOWN,
                reason_code="condition_assessment_not_run"
                "(缺 context 未执行;不得以无冲突措辞呈现)",
                coverage="declared_dimensions"))
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
    # input_hash 覆盖实际科学输入(R2-07):hypothesis 完整语义载荷(含
    # requirements/assumptions/dependency_refs)、参与物 state 身份、
    # context 身份、audit_scope、checker 版本与中心证据 checker ——
    # 不把一个 hypothesis_id 引用当完整输入证明;同 id 不同前提/上下文
    # ⇒ 不同 input_hash。
    input_fingerprint = {
        "audit_schema": PPV1_AUDIT_SCHEMA_VERSION,
        "hypothesis": hypothesis.to_dict(),
        "participant_state_ids": sorted(states.keys()),
        "context_id": context.context_id if context is not None else None,
        "audit_scope": sorted(requested),
        "checker_versions": versions,
        "center_evidence_checker": (
            str((center_evidence or {}).get("checker_version", ""))
            if center_evidence is not None else ""),
        "legacy_gate_result_ref": (
            (legacy_gate_result or {}).get("gate_ref", "")),
    }
    return ChemicalAudit(
        audit_id=audit_id, scope=scope, input_hash=stable_id(
            "ain", content_hash(input_fingerprint)),
        checks=checks,
        legacy_gate_result_ref=(
            (legacy_gate_result or {}).get("gate_ref", "")),
        participant_accounting_status=participant_accounting,
        biological_support_status="unknown",
        checker_versions=versions,
    )


def _element_accounting(reactant_side, product_side, states) -> AuditCheck:
    """全量元素账(F01:全部氢;系数加权;不补水/氧/辅酶凑平)。

    输出逐元素 Δ = Σ(反应物) − Σ(产物) 与常见漏项模式的结构化数值
    相符标注(mimo 2.3(2):{pattern, excess_on, missing_from,
    element_delta};仅数值相符:不证明缺项原因,不含电子/质子计量,
    H+ 模式名 H+_count1 仅表示 H 计数)。

    口径注记(mimo 2.2(a)):D/T 并入元素 H(同位素差异只在身份/同位素
    轴体现,不入本账);自由基未配对电子不入账;本账 verified 仅指元素
    与形式电荷的数值闭合,不指同位素计量、电子转移或机制。radical 保真
    轴为已知缺口(身份层区分自由基;本轴未实现)。
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
        "accounting_notes": (
            "isotopes_D_T_counted_as_H; radical_electrons_not_counted; "
            "verified_only_element_and_formal_charge_closure"),
        "omission_pattern_matches": [],
        "omission_pattern_semantics": (
            "omission_pattern_matches 仅表示缺口向量与该常见模式逐元素"
            "数值相符(excess_on=多出侧,missing_from=缺写侧;不证明"
            "实际缺该物质、不推断遗漏原因、不含电子/质子计量;"
            "H+_count1 仅表示 H 计数为 1 的模式名)"),
    }
    if diffs:
        for name, pattern in COMMON_OMISSION_PATTERNS.items():
            for excess_on, sign in (("reactant_side", 1),
                                    ("product_side", -1)):
                signed = {k: sign * v for k, v in pattern.items()}
                if diffs == signed:
                    detail["omission_pattern_matches"].append({
                        "pattern": ("H+_count1" if name == "H+" else name),
                        "excess_on": excess_on,
                        "missing_from": ("product_side"
                                         if excess_on == "reactant_side"
                                         else "reactant_side"),
                        "element_delta": {k: str(v)
                                          for k, v in sorted(signed.items())},
                    })
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
    """P0-4:admission 策略(schema + 完整决策表;v3 +R1b +R5v +R5c
    +逐产物门禁消费)。

    规则(评估顺序固定,首中即决):
    R1  structure_unparseable      → reject  (实际输入语法非法;CN-only
        等合法缺结构走 unknown,悬空引用走 R1b,不进本行)
    R1b participant_state_missing  → reject  (参与物 state 引用悬空 =
        账本/引用完整性问题,理由码保留,不压平成"结构不可解析",
        R2-01/mimo 3.2(2))
    R2  active_gate_rejected       → reject  (活动门禁显式拒绝;仅
        reject_gates 名单内 —— 不暗改冻结判据,新门禁须独立评审)
    R2p per_product_gate_rejected  → reject(全部共同产物被拒)/
        retain_conditional(部分被拒:被拒产物保留拒因、不可展开,
        不删除被拒共同产物凑合法事件)(R2-12;消费开关
        per_product_gate_consumption 由策略显式版本化)
    R2b contract_violated_       → reject  (表示契约违反:零/负/非有限
        representation                  系数、酶计入净计量、结构性违约;
        理由码写死 representation = 非化学,mimo 3.2(1) 采纳)
    R3  current_scenario_conflict  → defer   (有来源 essential 条件与当前
        场景已知事实冲突;action=blocked,假设保留不在此场景展开)
    R4  budget_or_wait             → defer   (独立原因)
    R5d declared_account_violated  → retain_conditional(触发集合显式限定
        {element_accounting, formal_charge_accounting},mimo 3.2(4);
        账不平只证明声明内部矛盾,不证明反应不存在;绝不进入 R6)
    R5v declared_violated_other    → retain_conditional(其他检查 violated
        的独立码 —— 如确定性 checker 的中心偏离;不冒称"声明账不一致")
    R5c required_check_coverage_   → retain_conditional(必需适用检查未
        missing                        被执行/不在审计内:窄 audit_scope 只
                                       能作诊断,R6 覆盖核算不通过,R2-01)
    R5  unknown_checks_present     → retain_conditional(检查 unknown/
        因缺输入未执行;继承未解决依赖)
    R6  default_all_verified       → expand(全部必需适用检查覆盖且
        verified,无 unknown/violated/缺输入未执行;语义 NA 白名单
        除外)
    R7  no_applicable_checks       → retain_conditional(无适用检查:
        保守保留,不冒充核实;理由与 R5 分开)

    任何 unknown 不自动 reject;新增"诊断转拒绝"必须扩本表并升版本。
    chemical_reproposal 首版 off。
    """

    policy_version: str = PPV1_ADMISSION_POLICY_VERSION
    reject_gates: frozenset = frozenset(DEFAULT_REJECT_GATES)
    chemical_reproposal: str = "off"
    per_product_gate_consumption: str = "on"
    rules: tuple = (
        ("R1", "structure_unparseable", ADMISSION_REJECT),
        ("R1b", "participant_state_missing", ADMISSION_REJECT),
        ("R2", "active_gate_rejected", ADMISSION_REJECT),
        ("R2p", "per_product_gate_rejected",
         ADMISSION_REJECT + "|" + ADMISSION_RETAIN_CONDITIONAL),
        ("R2b", "contract_violated_representation", ADMISSION_REJECT),
        ("R3", "current_scenario_conflict", ADMISSION_DEFER),
        ("R4", "budget_or_wait", ADMISSION_DEFER),
        ("R5d", "declared_account_violated", ADMISSION_RETAIN_CONDITIONAL),
        ("R5v", "declared_violated_other", ADMISSION_RETAIN_CONDITIONAL),
        ("R5c", "required_check_coverage_missing",
         ADMISSION_RETAIN_CONDITIONAL),
        ("R5", "unknown_checks_present", ADMISSION_RETAIN_CONDITIONAL),
        ("R6", "default_all_verified", ADMISSION_EXPAND),
        ("R7", "no_applicable_checks", ADMISSION_RETAIN_CONDITIONAL),
    )

    def to_dict(self) -> dict:
        return {
            "policy_version": self.policy_version,
            "reject_gates": sorted(self.reject_gates),
            "chemical_reproposal": self.chemical_reproposal,
            "per_product_gate_consumption":
                self.per_product_gate_consumption,
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
                "reject_gates 含未知门禁(新增门禁须独立列项评审,不暗改;"
                "mapper 的 gate_atom_mapping_declared 为只读旁证,启用为"
                "拒绝门禁须扩 DEFAULT_REJECT_GATES 并升策略版本)",
                {"unknown_gates": sorted(unknown_gates)})
        repro = d.get("chemical_reproposal", "off")
        if repro not in ("off", "on"):
            raise AuditContractError(
                f"chemical_reproposal 非法:{repro!r}", {"value": repro})
        per_product = d.get("per_product_gate_consumption", "on")
        if per_product not in ("on", "off"):
            raise AuditContractError(
                f"per_product_gate_consumption 非法:{per_product!r}",
                {"value": per_product})
        return cls(reject_gates=gates, chemical_reproposal=repro,
                   per_product_gate_consumption=per_product)


DEFAULT_ADMISSION_POLICY = AdmissionPolicy()


def _semantic_na_allowed(check: AuditCheck) -> bool:
    """真实语义不适用(允许缺席 R6 覆盖核算);缺输入未执行不算。"""
    allowed = SEMANTIC_NA_ALLOWED.get(check.name, ())
    reason = check.reason_code or ""
    return any(fragment in reason for fragment in allowed)


def _required_coverage_gaps(audit: ChemicalAudit) -> list[str]:
    """必需适用检查的覆盖缺口(R2-01:窄 scope 只是诊断)。

    缺口 = REQUIRED_CHECK_NAMES 中:审计内不存在,或状态 NA 但不在
    语义 NA 白名单(reason 不匹配)。verified/violated/unknown 都算
    已覆盖(它们进入对应决策行),只有"没执行"不算。
    """
    present = {c.name: c for c in audit.checks}
    gaps = []
    for name in REQUIRED_CHECK_NAMES:
        check = present.get(name)
        if check is None:
            gaps.append(name)
        elif check.status == CHECK_NOT_APPLICABLE \
                and not _semantic_na_allowed(check):
            gaps.append(name)
    return gaps


def decide_admission(
    audit: ChemicalAudit,
    *,
    policy: AdmissionPolicy | None = None,
    gate_decisions: dict[str, dict] | None = None,
    budget_state: dict | None = None,
    contract_violation: dict | None = None,
    product_state_refs: list[str] | None = None,
) -> tuple[str, list[str]]:
    """audit × 策略 → (admission_disposition, reasons)(纯函数)。

    gate_decisions:legacy_validation_to_gate_decisions 的输出(或手工
    同形状)。门禁键为 dict 且在 policy.reject_gates 内者参与 R2;
    per_product_verdicts(逐产物 verdict,含 position/accepted/reasons)
    被 R2p **真实消费** —— 全部共同产物被拒 ⇒ reject;部分 ⇒
    retain_conditional,被拒产物保留拒因、不可展开(R2-12:不删除被拒
    共同产物凑合法事件、不改冻结门禁真假、不把明确拒绝降成普通
    unknown)。gate_ref 为原产物引用,不参与判定。
    product_state_refs:共同产物 state_ref 按位次顺序(可选,用于把
    逐产物拒因落到具体产物引用;缺省用 position 表述)。
    budget_state:{"exhausted": bool, "waiting": bool, "reason": str}。
    contract_violation(R2b):表示契约违反的调用方报告(如 Hypothesis-
    ContractError 的 detail)→ reject + contract_violated_representation
    —— 不冒称结构不可解析或化学不可能。构造期异常 detail 必须由调用
    方映射传入(接口契约条款:不传则 R2b 不可达)。
    """
    pol = policy or DEFAULT_ADMISSION_POLICY
    reasons: list[str] = []

    # R1:实际输入语法非法 → reject(悬空引用走 R1b,CN-only 是 unknown)
    parse_check = next(
        (c for c in audit.checks
         if c.name == CHECK_STRUCTURE_PARSE_VALENCE), None)
    if parse_check is not None and parse_check.status == CHECK_VIOLATED:
        return ADMISSION_REJECT, ["R1:structure_unparseable"]

    # R1b:参与物 state 引用悬空(账本/引用完整性,非结构非法,R2-01)
    refs_check = next(
        (c for c in audit.checks
         if c.name == CHECK_PARTICIPANT_STATE_REFS), None)
    if refs_check is not None and refs_check.status == CHECK_VIOLATED:
        return ADMISSION_REJECT, [
            "R1b:participant_state_missing(账本/引用完整性问题,悬空"
            " state 引用;非结构不可解析):"
            + (refs_check.reason_code or "participant_state_missing")]

    # R2/R2p:活动门禁拒绝 + 逐产物门禁拒绝真实消费(R2-12)
    for gate_name, decision in (gate_decisions or {}).items():
        if not isinstance(decision, dict):
            continue  # per_product_verdicts(list)/gate_ref(dict 引用块)
        if gate_name in pol.reject_gates and not decision.get("ok", True):
            reasons.append(
                f"R2:active_gate_rejected:{gate_name}:"
                f"{decision.get('reason', '')[:120]}")
    if any(r.startswith("R2:") for r in reasons):
        return ADMISSION_REJECT, reasons

    if pol.per_product_gate_consumption == "on":
        per_product = (gate_decisions or {}).get("per_product_verdicts")
        per_product = per_product if isinstance(per_product, list) else []
        if per_product:
            rejected = [v for v in per_product
                        if not bool(v.get("accepted", False))]
            if rejected:
                def _product_label(v: dict) -> str:
                    pos = v.get("position")
                    if product_state_refs is not None \
                            and isinstance(pos, int) \
                            and 0 <= pos < len(product_state_refs):
                        return (f"position:{pos}:"
                                f"{product_state_refs[pos]}")
                    return f"position:{pos}"

                detail = ";".join(
                    f"{_product_label(v)}:"
                    + ",".join(str(r) for r in v.get("reasons", []))[:120]
                    for v in rejected)
                if len(rejected) == len(per_product):
                    return ADMISSION_REJECT, [
                        "R2p:per_product_gate_rejected:"
                        "all_products_gate_rejected(全部共同产物被活动"
                        "门禁拒绝;不改冻结门禁真假):" + detail]
                return ADMISSION_RETAIN_CONDITIONAL, [
                    "R2p:per_product_gate_rejected:some_products_gate_"
                    "rejected(部分共同产物被活动门禁拒绝:被拒产物保留"
                    "在事件中、拒因可追溯、不可展开;不删除被拒共同产物"
                    "凑合法事件):" + detail]

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

    # R5d:声明账 violated(触发集合显式限定 {元素,电荷},mimo 3.2(4))
    violated = audit.violated_checks()
    account_violated = [c for c in violated
                        if c.name in R5D_TRIGGER_CHECKS]
    if account_violated:
        return ADMISSION_RETAIN_CONDITIONAL, [
            "R5d:declared_account_violated(声明与结构不一致,有证据的"
            "发现;不 reject —— 账不平不证明反应不存在;绝不计入"
            "'全部核实'):" + ",".join(c.name for c in account_violated)]

    # R5v:其他检查 violated(独立码,不冒称声明账不一致)
    other_violated = [c for c in violated
                      if c.name not in R5D_TRIGGER_CHECKS]
    if other_violated:
        return ADMISSION_RETAIN_CONDITIONAL, [
            "R5v:declared_violated_other(确定性检查发现的不一致,"
            "非元素/电荷声明账;不 reject):"
            + ",".join(c.name for c in other_violated)]

    # R5c:必需适用检查覆盖缺口(窄 audit_scope 只能作诊断,R2-01)
    coverage_gaps = _required_coverage_gaps(audit)
    if coverage_gaps:
        return ADMISSION_RETAIN_CONDITIONAL, [
            "R5c:required_check_coverage_missing(必需适用检查未执行/"
            "不在审计内;窄 scope 只是诊断,不满足 admission 覆盖核算):"
            + ",".join(coverage_gaps)]

    # R5:存在 unknown 检查(含因缺输入未执行)→ retain_conditional
    unknown_names = [c.name for c in audit.checks
                     if c.status == CHECK_UNKNOWN]
    if unknown_names:
        return ADMISSION_RETAIN_CONDITIONAL, [
            "R5:unknown_checks_present(不自动拒绝;可有界探索可能路径,"
            f"继承未解决依赖;未知步长不进确认单步指标):"
            + ",".join(unknown_names)]

    # R6:全部必需适用检查覆盖且 verified,无 unknown/violated/缺输入未执行
    # (语义 NA 白名单内的检查不阻塞)→ expand
    all_verified_or_semantic_na = all(
        c.status == CHECK_VERIFIED
        or (c.status == CHECK_NOT_APPLICABLE and _semantic_na_allowed(c))
        for c in audit.checks)
    if audit.checks and all_verified_or_semantic_na \
            and not coverage_gaps:
        return ADMISSION_EXPAND, ["R6:all_verified_no_conflict"]

    # R7:无适用检查:保守 retain(理由与 R5 分开,不冒充核实)
    return ADMISSION_RETAIN_CONDITIONAL, [
        "R7:no_applicable_checks_conservative_retain(无适用检查证据,"
        "不默认 expand,不以无证据冒充核实)"]


# ---------------------------------------------------- 旧门禁 → 新 admission(P2-2)


LEGACY_GATE_MAPPER_VERSION = PPV1_GATE_MAPPER_VERSION


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
    """§8 供体诊断(v3:实际净变化判定 + 声明–执行对账 + 联合中心映射)。

    本诊断的**命名与范围**:供体迁移的**实际净变化区域诊断** —— 核验
    (i)执行前后结构的真实净变化集合(键 diff ∪ 原子增删 ∪ 逐原子
    形式电荷/氢数/立体 diff),(ii)声明编辑与实际执行是否对账,
    (iii)实际变化是否局限于对齐后的供体中心区域(**或其联合对称像**)。
    **不**核验供体反应自身的变换模板(供体侧预期键变化对比,S3 接线);
    图等价 ≠ 酶识别/机制等价(symmetric_equivalent 只是拓扑对称证据)。

    strict 轴使用与 ChemicalState 同一事实源的严格表示(含增强立体与
    v3 规范化:ABS/整组反转归一);legacy_cn_match 仅旁证,不进计数。
    center_match_basis ∈ {direct, symmetric_equivalent},仅 True 时
    非空;symmetric_equivalent 由**联合图映射**证明(存在单一自同构把
    整个中心集合映到实际变化集合),单原子对称轨道不冒充联合等价
    (R2-03)。
    """

    strict_target_match: bool | None
    legacy_cn_match: bool | None       # 旁证(corroborating),不进计数
    reaction_center_match: bool | None
    center_match_basis: str = ""       # direct | symmetric_equivalent(仅 True)
    extra_changes: list[dict] = field(default_factory=list)  # 逐原子 Δ 摘要
    alignment_ref: str = ""
    missing_info_reasons: list[str] = field(default_factory=list)
    executed_bond_changes: list[dict] = field(default_factory=list)
    # v3(R2-03):
    declaration_only: list[str] = field(default_factory=list)
        # 声明触及但实际未变化的原子(不参与 center 判定)
    declaration_mismatches: list[str] = field(default_factory=list)
        # 声明–执行对账失败明细(缺失声明变化/未声明变化)
    equivalence_basis: str = ""        # 等价类验证口径(提供类时)
    joint_mapping: dict = field(default_factory=dict)
        # symmetric_equivalent 的联合映射证据(中心像/自同构数)
    net_change_empty: bool = False     # 执行前后结构身份一致(零净变化)
    schema_version: str = PPV1_DONOR_DIAGNOSTIC_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _edit_atom_ids(edits: list[dict]) -> set[str]:
    """真实编辑协议(v43-editproto-2)中出现的原子标识(atom1/atom2)。"""
    out: set[str] = set()
    for edit in edits or []:
        for key in ("atom1", "atom2", "new_atom_id"):
            if edit.get(key) is not None:
                out.add(str(edit[key]))
    return out


_MAX_AUTOMORPHISM_MATCHES = 1024


def _kekulized(mol: Chem.Mol) -> Chem.Mol:
    """芳香表示归一副本(Kekulé 化;失败原样返回 —— 同一分子图)。"""
    try:
        m = Chem.Mol(mol)
        Chem.Kekulize(m, clearAromaticFlags=True)
        return m
    except Exception:
        return Chem.Mol(mol)


def _bond_changes(before: Chem.Mol, after_mapped: Chem.Mol,
                  id_to_idx_after: dict[str, int]) -> list[dict]:
    """执行前后结构的实际键变化集合(键级/成断键;原子增删另列)。

    before/after 均按 Kekulé 归一后再比较(芳香/kekulé 表示差异不是
    化学变化)。after_mapped:带映射号的执行图产物(映射号 = 执行图
    原子 idx+1);id_to_idx_after:MoleCode ID → 执行图 idx。
    返回 [{atom1_id, atom2_id, kind: order_change|bond_formed|bond_broken,
    from_order, to_order}]。
    """
    before_k = _kekulized(before)
    after_k = _kekulized(after_mapped)
    before_bonds: dict[frozenset, str] = {}
    for bond in before_k.GetBonds():
        key = frozenset((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()))
        before_bonds[key] = _bond_order_name(bond.GetBondType())
    after_bonds: dict[frozenset, str] = {}
    for bond in after_k.GetBonds():
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


def _cip_of(mol: Chem.Mol) -> dict[int, str]:
    """逐原子 CIP 立体描述符(阶无关;未指定/非手性不在表)。"""
    out: dict[int, str] = {}
    try:
        m = Chem.Mol(mol)
        Chem.AssignStereochemistry(m, cleanIt=True, force=True)
        for atom in m.GetAtoms():
            cip = atom.GetProp("_CIPCode") if atom.HasProp("_CIPCode") \
                else None
            if cip:
                out[atom.GetIdx()] = cip
    except Exception:
        pass
    return out


def _atom_property_diffs(
        before: Chem.Mol, after_mapped: Chem.Mol,
        id_to_idx_before: dict[str, int],
        id_to_idx_after: dict[str, int]) -> tuple[set[str], dict[str, dict]]:
    """逐原子属性 diff(形式电荷/氢数/CIP 立体)∪ 原子增删。

    返回 (变化原子 ID 集, 逐 id 的 before/after 属性记录)。after 按
    映射号对齐(idx+1)。属性不变但被键变化触及的原子不在本 diff 集
    (由键 diff 承接);CIP 立体用阶无关描述符(同 CIP 即同构型)。
    """
    after_by_mapnum = {atom.GetAtomMapNum() - 1: atom
                       for atom in after_mapped.GetAtoms()}
    before_cip = _cip_of(before)
    # after 的 CIP 按映射号(构造 idx)对齐:解析序 ≠ 构造序,必须用
    # mapnum-1 作键;映射号本身不影响 CIP 判定
    after_cip: dict[int, str] = {}
    try:
        m_after = Chem.Mol(after_mapped)
        Chem.AssignStereochemistry(m_after, cleanIt=True, force=True)
        for atom in m_after.GetAtoms():
            if atom.GetAtomMapNum() and atom.HasProp("_CIPCode"):
                after_cip[atom.GetAtomMapNum() - 1] = \
                    atom.GetProp("_CIPCode")
    except Exception:
        pass

    changed: set[str] = set()
    records: dict[str, dict] = {}
    all_ids = set(id_to_idx_before) | set(id_to_idx_after)
    for aid in sorted(all_ids):
        bi = id_to_idx_before.get(aid)
        ai = id_to_idx_after.get(aid)
        if bi is None and ai is not None:
            records[aid] = {"presence": "atom_added",
                            "element": after_by_mapnum[ai].GetSymbol()
                            if ai in after_by_mapnum else ""}
            changed.add(aid)
        elif ai is None and bi is not None:
            records[aid] = {"presence": "atom_removed",
                            "element": before.GetAtomWithIdx(bi).GetSymbol()}
            changed.add(aid)
        else:
            b_atom = before.GetAtomWithIdx(bi)
            a_atom = after_by_mapnum.get(ai)
            if a_atom is None:
                continue  # 映射号缺失,无法对齐(中心判定按未解析处理)
            b_charge, a_charge = (b_atom.GetFormalCharge(),
                                  a_atom.GetFormalCharge())
            b_h, a_h = b_atom.GetTotalNumHs(), a_atom.GetTotalNumHs()
            b_cip, a_cip = before_cip.get(bi, ""), after_cip.get(ai, "")
            deltas = []
            if b_charge != a_charge:
                deltas.append("formal_charge")
            if b_h != a_h:
                deltas.append("h_count")
            if b_cip != a_cip:
                deltas.append("stereo")
            if deltas:
                changed.add(aid)
            records[aid] = {
                "element": b_atom.GetSymbol(),
                "formal_charge": [b_charge, a_charge],
                "h_count": [b_h, a_h],
                "cip": [b_cip, a_cip],
                "property_delta": ";".join(deltas)}
    return changed, records


def _declared_expectations(edits: list[dict]) -> tuple[
        list[dict], list[str]]:
    """从声明编辑提取期望键变化与新增原子(供对账)。

    返回 (期望键变化列表, 声明新增原子 ID 列表)。期望键变化:
    {pair: frozenset(ids), from_order, to_order, op}。
    """
    expectations: list[dict] = []
    added: list[str] = []
    for edit in edits or []:
        op = str(edit.get("op", "")).lower()
        a1 = edit.get("atom1")
        a2 = edit.get("atom2")
        if op == "change_bond_order":
            expectations.append({
                "pair": frozenset({str(a1), str(a2)}),
                "from_order": str(edit.get("from_order", "")).lower(),
                "to_order": str(edit.get("to_order", "")).lower(),
                "op": op})
        elif op in ("break_bond", "form_bond"):
            expectations.append({
                "pair": frozenset({str(a1), str(a2)}),
                "from_order": "", "to_order": "", "op": op})
        elif op == "add_atom":
            added.append(str(edit.get("new_atom_id", "")))
    return expectations, added


def _declaration_accounting(
        edits: list[dict], bond_changes: list[dict],
        added_atom_ids: list[str]) -> list[str]:
    """声明–执行一致性对账(R2-03/mimo 5.2(a))。

    - 声明的每条键变化(原子对+from/to)须在实际键变化中出现;
    - 实际出现的每条键变化须被某条声明编辑覆盖(原子对);
    - 声明 add_atom 的新原子须实际存在;实际新增原子须被声明。
    返回失配明细(空列表 = 对账一致)。
    """
    mismatches: list[str] = []
    expected, declared_added = _declared_expectations(edits)
    actual_pairs = {frozenset({c["atom1_id"], c["atom2_id"]}): c
                    for c in bond_changes}
    # 正向:声明 → 实际
    for exp in expected:
        pair = exp["pair"]
        actual = actual_pairs.get(pair)
        if actual is None:
            mismatches.append(
                f"declared_change_not_executed:{sorted(pair)}:"
                f"{exp['op']}:{exp['from_order']}->{exp['to_order']}")
            continue
        if exp["op"] == "change_bond_order":
            if actual.get("to_order", "") != exp["to_order"]:
                mismatches.append(
                    f"declared_to_order_mismatch:{sorted(pair)}:"
                    f"declared:{exp['to_order']}"
                    f":actual:{actual.get('to_order')}")
            # from_order 容差:芳香感知归一后 from 可能重排;此处只核
            # to(方向性)与 pair —— from 的表示差异由 Kekulé 归一吸收
        elif exp["op"] == "break_bond" and actual.get("kind") != \
                "bond_broken":
            mismatches.append(
                f"declared_break_executed_as:{sorted(pair)}:"
                f"{actual.get('kind')}")
        elif exp["op"] == "form_bond" and actual.get("kind") != \
                "bond_formed":
            mismatches.append(
                f"declared_form_executed_as:{sorted(pair)}:"
                f"{actual.get('kind')}")
    # 反向:实际 → 声明
    declared_pairs = {exp["pair"] for exp in expected}
    for pair, actual in actual_pairs.items():
        if pair not in declared_pairs:
            mismatches.append(
                f"undeclared_bond_change:{sorted(pair)}:"
                f"{actual.get('kind')}:{actual.get('from_order')}"
                f"->{actual.get('to_order')}")
    # 原子增删
    actual_added = set(added_atom_ids)
    for new_id in declared_added:
        if new_id and new_id not in actual_added:
            mismatches.append(f"declared_atom_not_added:{new_id}")
    declared_added_set = {n for n in declared_added if n}
    for new_id in sorted(actual_added):
        if new_id not in declared_added_set:
            mismatches.append(f"undeclared_atom_added:{new_id}")
    return mismatches


def _validate_equivalence_classes(equivalence_classes: list,
                                  current_mol: Chem.Mol,
                                  id_to_idx: dict[str, int]) -> tuple[
                                      dict[str, set[str]], list[list[str]]]:
    """等价类从分子图验证(F11:不采信自报任意集合)。

    仅当等价类成员在当前分子图上对称等价(RDKit 无 tie-breaking 的
    canonical rank 同类;口径 equivalence_basis=
    canonical_rank_breakTies_false,拓扑对称的实现近似,非完整自同构
    群枚举)时采信;含非等价成员或未知原子的类整体弃用并记入
    rejected(不部分采用)。返回 (采信的等价展开 dict, 被拒的类列表)。

    v3 注意:等价类**不再参与 center 判定**(由联合图映射取代,
    R2-03);本验证仅作披露 —— 自报类的采信/拒用状态进
    missing_info_reasons。
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


def _joint_symmetric_image(
        before: Chem.Mol, center_idxs: set[int],
        changed_idxs: set[int]) -> dict | None | str:
    """联合中心对称:存在单一自同构把**整个**中心集合映到实际变化集合。

    返回 dict(找到,含中心像与自同构数)/ None(确定不存在)/
    "truncated"(搜索截断,不确定 ⇒ 上层记 unknown)。单原子各自可
    替换不等于整个中心存在一致替换(R2-03 联合反例)。
    """
    if not center_idxs or not changed_idxs:
        return None
    if len(center_idxs) != len(changed_idxs):
        return None
    try:
        matches = before.GetSubstructMatches(
            before, uniquify=False, useChirality=False,
            maxMatches=_MAX_AUTOMORPHISM_MATCHES)
    except Exception:
        return "truncated"
    if len(matches) >= _MAX_AUTOMORPHISM_MATCHES:
        return "truncated"
    for match in matches:
        image = {match[i] for i in center_idxs if i < len(match)}
        if image == set(changed_idxs):
            return {"center_image": sorted(image),
                    "n_automorphisms": len(matches)}
    return None


def check_edit_against_donor(
    *,
    current: dict,
    donor: dict,
    alignment: dict,
    expectation: dict,
    result: dict,
    edits: list[dict],
) -> DonorConsistencyDiagnostic:
    """§7.1 固定接口(v3):消费**真实 AtomTool 编辑协议**的诊断。

    输入(与 v43-editproto-2 / execute_edits 输出对接):
    - current: {"smiles": str, "atom_id_map": {id: idx}}(编辑前
      MoleculeRender 的渲染事实);
    - donor: {"center_atom_ids": [...]}(供体反应变换中心的供体侧原子);
    - alignment: {"status": resolved|ambiguous|unavailable,
      "donor_to_current": {donor_atom: current_atom},
      "equivalence_classes": [[atom, ...]](验证后仅披露,不参与判定),
      "ref": str};
    - expectation: {"target_smiles": str}(供体迁移预期产物);
    - result: execute_edits 的输出 dict(ok/product_smiles/
      product_mapped_smiles/atom_id_map);ok=False ⇒ 全轴 unknown +
      execution_failed;
    - edits: 真实协议编辑列表(break_bond/form_bond/change_bond_order/
      add_atom,含 atom1/atom2/new_atom_id)。

    v3 判定基础 = **实际净变化集合**(R2-03):
    - 结构身份一致(执行前后同一分子)⇒ 零净变化 ⇒ center=
      unknown(no_executed_change),永不 True —— 声明的编辑原子单独
      列 declaration_only,不并入变化集(v2 的"声明触及即命中"废除);
    - 声明–执行对账(_declaration_accounting):不一致 ⇒
      declaration_mismatches,strict/center 不得 verified(unknown);
    - plain 产物与 mapped 执行图对账:不一致 ⇒ 两轴 unknown +
      plain_product_mapped_product_disagreement;
    - center:实际变化 ⊆ 对齐中心(direct)或存在联合自同构像
      (symmetric_equivalent)⇒ True;中心外变化 ⇒ False +
      extra_changes(逐原子 element/形式电荷/ΔH/Δ立体 before/after);
    - 全部供体中心原子必须有映射(部分缺 ⇒ unknown,不部分判定);
      自同构搜索截断 ⇒ unknown(automorphism_search_truncated)。
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

    # ---- plain 产物 vs mapped 执行图对账(R2-03) ----
    representation_disagreement = False
    result_smiles = result.get("product_smiles")
    plain_mol = Chem.MolFromSmiles(str(result_smiles)) \
        if result_smiles else None
    if result_smiles and product_mapped:
        from .chemstate import normalized_structure_smiles

        if plain_mol is None:
            representation_disagreement = True
            missing.append("plain_product_unparseable")
        elif normalized_structure_smiles(plain_mol) != \
                normalized_structure_smiles(mol_after):
            representation_disagreement = True
            missing.append(
                "plain_product_mapped_product_disagreement(执行图与"
                "对外产物不一致,两轴不可判)")

    # ---- 实际净变化集合 ----
    # 结构身份一致 ⇒ 零净变化(所有表示差异都被规范化吸收)
    from .chemstate import normalized_structure_smiles as _norm_smiles

    net_change_empty = (_norm_smiles(mol_before)
                        == _norm_smiles(mol_after))
    if net_change_empty:
        missing.append(
            "no_executed_change(实际净变化为空:声明触及≠已发生;"
            "center 不可判 True)")
    if net_change_empty:
        bond_changes: list[dict] = []
        atom_changed: set[str] = set()
        atom_records: dict[str, dict] = {}
    else:
        bond_changes = _bond_changes(mol_before, mol_after,
                                     id_to_idx_after)
        atom_changed, atom_records = _atom_property_diffs(
            mol_before, mol_after, id_to_idx_before, id_to_idx_after)
    added_atom_ids = [aid for aid in id_to_idx_after
                      if aid not in id_to_idx_before]
    changed_atoms = ({c["atom1_id"] for c in bond_changes}
                     | {c["atom2_id"] for c in bond_changes}
                     | atom_changed)
    declaration_only = sorted(_edit_atom_ids(edits) - changed_atoms)

    # ---- 声明–执行对账 ----
    declaration_mismatches = _declaration_accounting(
        edits, bond_changes, added_atom_ids)

    # ---- strict(与 ChemicalState 同源规范化严格表示;含对账前提) ----
    strict = None
    cn_match = None
    expected_smiles = expectation.get("target_smiles")
    if representation_disagreement:
        strict = None
    elif declaration_mismatches:
        # 声明与执行不一致 ⇒ strict 至少 unknown(mimo 5.2(a):该轴
        # 不得 verified —— 产物碰巧等于预期不能掩盖对账失败)
        strict = None
    elif result_smiles and expected_smiles:
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
    elif not representation_disagreement:
        missing.append("target_or_result_smiles_missing")

    # ---- reaction center(实际净变化 + 对齐映射 + 联合对称) ----
    center_match = None
    basis = ""
    extra_changes: list[dict] = []
    joint_mapping: dict = {}
    equivalence_basis = ""
    donor_centers = [str(a) for a in (donor.get("center_atom_ids") or [])]

    if declaration_mismatches:
        # 声明与执行不一致 ⇒ 中心不可判(至少 unknown,mimo 5.2(a))
        center_match = None
        missing.extend(declaration_mismatches[:10])
    elif representation_disagreement:
        center_match = None  # 执行图不可信(与对外产物不一致)
    elif alignment_status != "resolved":
        center_match = None
        missing.append(f"alignment_{alignment_status}_center_unknown")
    elif not donor_centers:
        center_match = None
        missing.append("center_or_edits_unavailable")
    elif not changed_atoms:
        # 零净变化:实际什么都没发生 ⇒ 永不 True(R2-03)
        center_match = None
        missing.append(
            "no_executed_change(实际净变化为空:声明触及≠已发生;"
            "center 不可判 True)")
    else:
        mapping = {
            str(k): str(v)
            for k, v in (alignment.get("donor_to_current") or {}).items()}
        # 等价类验证(仅披露;v3 不再参与判定,由联合映射取代)
        _, rejected_classes = _validate_equivalence_classes(
            alignment.get("equivalence_classes") or [],
            mol_before, id_to_idx_before)
        equivalence_basis = "canonical_rank_breakTies_false"
        if rejected_classes:
            missing.append(
                "equivalence_class_rejected_by_graph_automorphism:"
                + ";".join(",".join(c) for c in rejected_classes)[:160]
                + "(非等价成员的类不被采信;等价类不参与 v3 center 判定)")
        # 全部供体中心原子必须有映射(部分缺映射 ⇒ unknown)
        unmapped = [d for d in donor_centers if d not in mapping]
        if unmapped:
            center_match = None
            missing.append(
                "donor_centers_partially_unmapped:" + ",".join(unmapped))
        else:
            center_direct = {mapping[d] for d in donor_centers}
            outside = changed_atoms - center_direct
            if not outside:
                center_match = True
                basis = "direct"
                extra_changes = []
            else:
                # 联合对称:单一自同构把整个中心集合映到实际变化集合
                center_idxs = {id_to_idx_before[a] for a in center_direct
                               if a in id_to_idx_before}
                changed_idxs = {id_to_idx_before[a] for a in changed_atoms
                                if a in id_to_idx_before}
                if len(changed_idxs) != len(changed_atoms):
                    # 变化集含新增原子等无 before 索引的原子:
                    # 联合映射不可能 ⇒ 偏离(新增原子须在中心声明内)
                    center_match = False
                    basis = ""
                    extra_changes = _atom_change_summary(
                        outside, mol_before, mol_after, id_to_idx_after,
                        atom_records)
                else:
                    joint = _joint_symmetric_image(
                        mol_before, center_idxs, changed_idxs)
                    if joint == "truncated":
                        center_match = None
                        basis = ""
                        missing.append(
                            "automorphism_search_truncated(联合映射搜索"
                            "截断,中心不可判)")
                    elif isinstance(joint, dict):
                        center_match = True
                        basis = "symmetric_equivalent"
                        joint_mapping = dict(joint)
                        joint_mapping["equivalence_note"] = (
                            "图等价≠酶识别/机制等价(拓扑对称证据)")
                        extra_changes = []
                    else:
                        center_match = False  # 联合映射不存在 ⇒ 偏离
                        basis = ""
                        extra_changes = _atom_change_summary(
                            outside, mol_before, mol_after, id_to_idx_after,
                            atom_records)

    return DonorConsistencyDiagnostic(
        strict_target_match=strict, legacy_cn_match=cn_match,
        reaction_center_match=center_match, center_match_basis=basis,
        extra_changes=extra_changes, alignment_ref=alignment_ref,
        missing_info_reasons=missing,
        executed_bond_changes=bond_changes,
        declaration_only=declaration_only,
        declaration_mismatches=declaration_mismatches,
        equivalence_basis=(equivalence_basis
                           if alignment.get("equivalence_classes")
                           else ""),
        joint_mapping=joint_mapping,
        net_change_empty=net_change_empty)


def _atom_change_summary(atoms: set[str], before: Chem.Mol,
                         after: Chem.Mol, id_to_idx_after: dict,
                         atom_records: dict[str, dict] | None = None,
                         ) -> list[dict]:
    """中心区域外变化原子的逐原子 Δ 摘要(element/电荷/ΔH/Δ立体)。

    v3(mimo 5.2(a)):补 ΔH 与 Δ立体;电荷输出 before/after 而非
    仅产物值;atom_records 提供 _atom_property_diffs 的逐 id 记录。
    """
    out = []
    records = atom_records or {}
    for aid in sorted(atoms):
        rec = dict(records.get(aid) or {})
        entry = {"atom_id": aid, "delta": []}
        idx = id_to_idx_after.get(aid)
        if "presence" in rec:
            entry["delta"].append(rec["presence"])
            entry["element"] = rec.get("element", "")
            if "formal_charge" in rec:
                entry["formal_charge"] = rec["formal_charge"]
            if "h_count" in rec:
                entry["h_count"] = rec["h_count"]
            if "cip" in rec:
                entry["stereo"] = rec["cip"]
            out.append(entry)
            continue
        if idx is not None:
            after_atom = None
            for atom in after.GetAtoms():
                if atom.GetAtomMapNum() - 1 == idx:
                    after_atom = atom
                    break
        else:
            after_atom = None
        entry["element"] = rec.get("element", "")
        if "formal_charge" in rec:
            entry["formal_charge"] = {
                "before": rec["formal_charge"][0],
                "after": rec["formal_charge"][1]}
        if "h_count" in rec:
            entry["h_count"] = {
                "before": rec["h_count"][0],
                "after": rec["h_count"][1]}
        if "cip" in rec:
            entry["stereo"] = {
                "before_cip": rec["cip"][0] or None,
                "after_cip": rec["cip"][1] or None}
        if rec.get("property_delta"):
            entry["delta"].extend(
                d for d in str(rec["property_delta"]).split(";") if d)
        if after_atom is not None:
            entry["delta"].append("present_in_product")
        else:
            entry["delta"].append("absent_in_product_or_unmapped")
        out.append(entry)
    return out


def center_evidence_from_donor_diagnostic(
        diagnostic: DonorConsistencyDiagnostic) -> dict:
    """供体诊断 → audit 的 center_evidence(R2-01 证据门接线助手)。

    transformation_center 检查的 verified 须有注册版本化确定性 checker
    的证据;本助手把 DonorConsistencyDiagnostic 转成该证据形状
    (checker_version ∈ CENTER_CHECKER_REGISTRY)。S3 搜索接线时由
    执行流调用;audit_hypothesis(center_evidence=…) 消费。
    """
    return {
        "checker_version": PPV1_DONOR_DIAGNOSTIC_VERSION,
        "center_match": diagnostic.reaction_center_match,
        "declaration_mismatch": bool(diagnostic.declaration_mismatches),
        "center_match_basis": diagnostic.center_match_basis,
        "evidence_refs": [diagnostic.alignment_ref],
    }
