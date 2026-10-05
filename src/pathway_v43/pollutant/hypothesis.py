"""ReactionHypothesis — 先定义反应假设,再提交事件(实施书 §5.2,S1)。

- 参与物 participants[]:每项 state_ref + side + role + coefficient;
  已知系数必须是正有限有理数(Fraction);未知系数 null+unknown;
  禁止 known+null、零、负数或非有限数(H02 输入契约,fail-closed);
- 重复参与物不用集合去重丢系数:同侧、同物种、同角色且**调用方明确
  声明为并列计量贡献**(parallel_contribution=True)的重复项可求和,
  保留原条目与归并轨迹;含义/系数未知则保留歧义(ambiguous 标记),
  不猜(H03);
- 同一已知裂解反应的共同产物属于一个假设/事件;未提供副产物或共底物
  可保留 partial 假设,但完整配平必须 unknown;
- 模型新输出用 proposals[](每项一条独立假设);不同假设是备选解释,
  不据此断言互斥;
- 历史 novel 平列表语义不明确 → legacy_relationship_unspecified,
  不静默拆成单产物反应,也不重解释为已证实共同产物(A04);
- step_scope=multistep_summary 保留为汇总边,不冒充净酶反应;
- hypothesis_id 来自冻结反应语义(参与物规范化 + 转化引用 + 来源组
  键);无法确认等价的来源不强制合并(不同来源组键 → 不同 id)。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction

from ..domain.models import canonical_json, stable_id
from .profile import PPV1_HYPOTHESIS_SCHEMA_VERSION

PPV1_HYPOTHESIS_SUPPORTED_VERSIONS = ("ppv1-hypothesis-3",)

PARTICIPANT_SIDE_REACTANT = "reactant"
PARTICIPANT_SIDE_PRODUCT = "product"
PARTICIPANT_SIDES = frozenset({PARTICIPANT_SIDE_REACTANT,
                               PARTICIPANT_SIDE_PRODUCT})

PARTICIPANT_ROLE_PRIMARY_SUBSTRATE = "primary_substrate"
PARTICIPANT_ROLE_COSUBSTRATE = "cosubstrate"
PARTICIPANT_ROLE_PRINCIPAL_PRODUCT = "principal_product"
PARTICIPANT_ROLE_COPRODUCT = "coproduct"
PARTICIPANT_ROLE_UNKNOWN = "unknown"
PARTICIPANT_ROLES = frozenset({
    PARTICIPANT_ROLE_PRIMARY_SUBSTRATE, PARTICIPANT_ROLE_COSUBSTRATE,
    PARTICIPANT_ROLE_PRINCIPAL_PRODUCT, PARTICIPANT_ROLE_COPRODUCT,
    PARTICIPANT_ROLE_UNKNOWN,
})

COEFFICIENT_KNOWN = "known"
COEFFICIENT_UNKNOWN = "unknown"

PARTICIPANT_LIST_SOURCE_COMPLETE = "source_complete"
PARTICIPANT_LIST_DECLARED_COMPLETE = "declared_complete"
PARTICIPANT_LIST_PARTIAL = "partial"
PARTICIPANT_LIST_UNKNOWN = "unknown"
PARTICIPANT_LIST_STATUSES = frozenset({
    PARTICIPANT_LIST_SOURCE_COMPLETE, PARTICIPANT_LIST_DECLARED_COMPLETE,
    PARTICIPANT_LIST_PARTIAL, PARTICIPANT_LIST_UNKNOWN,
})

STEP_SCOPE_NET_REACTION = "net_reaction"
STEP_SCOPE_ELEMENTARY_STEP = "elementary_step"
STEP_SCOPE_MULTISTEP_SUMMARY = "multistep_summary"
STEP_SCOPE_UNKNOWN = "unknown"
STEP_SCOPES = frozenset({
    STEP_SCOPE_NET_REACTION, STEP_SCOPE_ELEMENTARY_STEP,
    STEP_SCOPE_MULTISTEP_SUMMARY, STEP_SCOPE_UNKNOWN,
})

LEGACY_RELATIONSHIP_UNSPECIFIED = "legacy_relationship_unspecified"


class HypothesisContractError(RuntimeError):
    """参与物/假设输入契约违反(结构化 fail-closed,含定位信息)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def parse_coefficient(value) -> Fraction:
    """系数 → 正有限 Fraction(H02:零/负/非有限/known+null 拒绝)。"""
    if value is None:
        raise HypothesisContractError(
            "系数为 null:未知系数须标 coefficient_status=unknown,不得 "
            "以 known+null 表示", {"kind": "known_coefficient_null"})
    if isinstance(value, bool):
        raise HypothesisContractError(
            f"系数非法(bool):{value!r}", {"kind": "invalid_coefficient_type",
                                        "value": repr(value)})
    if isinstance(value, Fraction):
        frac = value
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise HypothesisContractError(
                f"系数非有限数值:{value!r}", {"kind": "non_finite_coefficient",
                                             "value": repr(value)})
        frac = Fraction(str(value))
    elif isinstance(value, int):
        frac = Fraction(value)
    elif isinstance(value, str):
        try:
            frac = Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise HypothesisContractError(
                f"系数无法解析为有理数:{value!r}",
                {"kind": "invalid_coefficient", "value": value,
                 "error": str(exc)}) from exc
    else:
        raise HypothesisContractError(
            f"系数类型非法:{type(value).__name__}",
            {"kind": "invalid_coefficient_type", "value": repr(value)})
    if frac <= 0:
        raise HypothesisContractError(
            f"系数必须为正:{value!r}(零/负数拒绝;该拒绝是输入表示层"
            "契约,不宣称反应本身化学不可能)",
            {"kind": "non_positive_coefficient", "value": repr(value)})
    return frac


def coefficient_to_json(frac: Fraction | None) -> str | None:
    return str(frac) if frac is not None else None


def coefficient_from_json(value: str | None) -> Fraction | None:
    return Fraction(value) if value is not None else None


@dataclass
class Participant:
    """参与物条目(计量层;来源支持在 provenance 层,不混入)。

    构造即校验(H02 fail-closed):coefficient 接受 int/float/str/Fraction,
    一律归一为正有限 Fraction;known+null、零/负/非有限、unknown+数值
    均拒绝。系数未知用 coefficient=None + status=unknown。
    """

    state_ref: str                     # ChemicalState.state_id
    side: str                          # reactant | product
    role: str                          # §5.2 角色枚举
    coefficient: Fraction | None       # 正有理数;None = 未知
    coefficient_status: str            # known | unknown
    parallel_contribution: bool = False  # 调用方明确声明:并列计量贡献
    merged_from: list[str] = field(default_factory=list)  # 归并轨迹(H03)
    entry_id: str = ""                 # 原条目指纹(归并前)

    def __post_init__(self) -> None:
        if self.coefficient_status == COEFFICIENT_UNKNOWN:
            if self.coefficient is not None:
                raise HypothesisContractError(
                    "unknown 系数必须为 null(不能携带数值)",
                    {"kind": "unknown_coefficient_with_value",
                     "state_ref": self.state_ref})
            return
        if self.coefficient_status != COEFFICIENT_KNOWN:
            raise HypothesisContractError(
                f"coefficient_status 非法:{self.coefficient_status!r}",
                {"kind": "invalid_coefficient_status",
                 "coefficient_status": self.coefficient_status})
        if self.coefficient is None:
            raise HypothesisContractError(
                "known 系数不能为 null(known+null 禁止)",
                {"kind": "known_coefficient_null",
                 "state_ref": self.state_ref})
        if not isinstance(self.coefficient, Fraction):
            # int/float/str → Fraction(非法值在 parse_coefficient 拒绝)
            self.coefficient = parse_coefficient(self.coefficient)
        else:
            parse_coefficient(self.coefficient)  # 正性/有限复核

    def to_dict(self) -> dict:
        return {
            "state_ref": self.state_ref, "side": self.side,
            "role": self.role, "coefficient": coefficient_to_json(
                self.coefficient),
            "coefficient_status": self.coefficient_status,
            "parallel_contribution": self.parallel_contribution,
            "merged_from": list(self.merged_from),
            "entry_id": self.entry_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Participant":
        return cls(
            state_ref=d["state_ref"], side=d["side"], role=d["role"],
            coefficient=coefficient_from_json(d.get("coefficient")),
            coefficient_status=d["coefficient_status"],
            parallel_contribution=bool(d.get("parallel_contribution", False)),
            merged_from=list(d.get("merged_from", [])),
            entry_id=d.get("entry_id", ""),
        )


def _entry_fingerprint(p: Participant) -> str:
    return stable_id("pentry", p.state_ref, p.side, p.role,
                     coefficient_to_json(p.coefficient) or "null",
                     str(p.parallel_contribution))


def _validate_participant(p: Participant, index: int) -> None:
    where = {"participant_index": index, "state_ref": p.state_ref}
    if p.side not in PARTICIPANT_SIDES:
        raise HypothesisContractError(
            f"参与物 side 非法:{p.side!r}", {**where, "side": p.side})
    if p.role not in PARTICIPANT_ROLES:
        raise HypothesisContractError(
            f"参与物 role 非法:{p.role!r}", {**where, "role": p.role})
    if p.coefficient_status == COEFFICIENT_KNOWN:
        if p.coefficient is None:
            raise HypothesisContractError(
                "known 系数不能为 null(known+null 禁止)",
                {**where, "kind": "known_coefficient_null"})
        parse_coefficient(p.coefficient)  # 正性/有限复核
    elif p.coefficient_status == COEFFICIENT_UNKNOWN:
        if p.coefficient is not None:
            raise HypothesisContractError(
                "unknown 系数必须为 null(不能携带数值)",
                {**where, "kind": "unknown_coefficient_with_value"})
    else:
        raise HypothesisContractError(
            f"coefficient_status 非法:{p.coefficient_status!r}",
            {**where, "coefficient_status": p.coefficient_status})


def normalize_participants(
    participants: list[Participant],
) -> tuple[list[Participant], bool]:
    """并列计量归并(§17.4 H03;保守、显式、可回溯)。

    规则:
    - 同 (side, state_ref, role) 且**全部**条目 parallel_contribution=True
      且系数 known → 求和为一个条目,merged_from 保留原条目指纹;
    - 同 (side, state_ref, role) 但声明不全/系数 unknown/角色 unknown
      → 保留重复条目并返回 ambiguous=True(保留歧义,不猜);
    - 来源重复引用不得重复加计量:同一来源的重复引用应在导入层只产生
      一条参与物(本函数不做来源去重 —— 那是 provenance 层的职责)。

    返回 (归并后列表, 是否存在保留歧义的重复)。
    """
    for i, p in enumerate(participants):
        _validate_participant(p, i)
    groups: dict[tuple[str, str, str], list[Participant]] = {}
    order: list[tuple[str, str, str]] = []
    for p in participants:
        if not p.entry_id:
            p.entry_id = _entry_fingerprint(p)
        key = (p.side, p.state_ref, p.role)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)
    out: list[Participant] = []
    ambiguous = False
    for key in order:
        entries = groups[key]
        mergeable = (
            len(entries) > 1
            and all(e.parallel_contribution and e.role != PARTICIPANT_ROLE_UNKNOWN
                    for e in entries)
            and all(e.coefficient is not None for e in entries)
        )
        if mergeable:
            merged_coeff = sum(
                (e.coefficient for e in entries), Fraction(0))
            merged = Participant(
                state_ref=entries[0].state_ref, side=entries[0].side,
                role=entries[0].role, coefficient=merged_coeff,
                coefficient_status=COEFFICIENT_KNOWN,
                parallel_contribution=True,
                merged_from=[e.entry_id for e in entries],
                entry_id=stable_id("pmerged", *[e.entry_id for e in entries]),
            )
            out.append(merged)
        else:
            if len(entries) > 1:
                ambiguous = True  # 保留歧义,不静默去重/求和
            out.extend(entries)
    return out, ambiguous


@dataclass
class ReactionHypothesis:
    """反应假设(§5.2 全字段;参与物经 normalize 后入账)。"""

    hypothesis_id: str
    parent_path_id: str
    substrate_state_ref: str
    participants: list[Participant]
    participant_list_status: str
    step_scope: str
    transformation_ref: str = ""
    transformation_signature_status: str = "unknown"  # verified|unknown|…
    step_scope_evidence_refs: list[str] = field(default_factory=list)
    provenance_refs: list[str] = field(default_factory=list)
    support_group_refs: list[str] = field(default_factory=list)
    requirements: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    dependency_refs: list[str] = field(default_factory=list)
    audit_ref: str = ""
    model_decision_ref: str = ""
    legacy_relationship_status: str = ""   # A04:legacy 平列表挂牌
    ambiguous_participants: bool = False   # H03:保留歧义标记
    schema_version: str = PPV1_HYPOTHESIS_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "hypothesis_id": self.hypothesis_id,
            "parent_path_id": self.parent_path_id,
            "substrate_state_ref": self.substrate_state_ref,
            "participants": [p.to_dict() for p in self.participants],
            "participant_list_status": self.participant_list_status,
            "step_scope": self.step_scope,
            "transformation_ref": self.transformation_ref,
            "transformation_signature_status": (
                self.transformation_signature_status),
            "step_scope_evidence_refs": list(self.step_scope_evidence_refs),
            "provenance_refs": list(self.provenance_refs),
            "support_group_refs": list(self.support_group_refs),
            "requirements": [dict(r) for r in self.requirements],
            "assumptions": list(self.assumptions),
            "dependency_refs": list(self.dependency_refs),
            "audit_ref": self.audit_ref,
            "model_decision_ref": self.model_decision_ref,
            "legacy_relationship_status": self.legacy_relationship_status,
            "ambiguous_participants": self.ambiguous_participants,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReactionHypothesis":
        version = d.get("schema_version")
        if version not in PPV1_HYPOTHESIS_SUPPORTED_VERSIONS:
            raise HypothesisContractError(
                f"ReactionHypothesis schema 版本未知:{version!r}(支持 "
                f"{list(PPV1_HYPOTHESIS_SUPPORTED_VERSIONS)};fail-closed)",
                {"schema_version": version})
        return cls(
            hypothesis_id=d["hypothesis_id"],
            parent_path_id=d["parent_path_id"],
            substrate_state_ref=d["substrate_state_ref"],
            participants=[Participant.from_dict(p)
                          for p in d["participants"]],
            participant_list_status=d["participant_list_status"],
            step_scope=d["step_scope"],
            transformation_ref=d.get("transformation_ref", ""),
            transformation_signature_status=d.get(
                "transformation_signature_status", "unknown"),
            step_scope_evidence_refs=list(
                d.get("step_scope_evidence_refs", [])),
            provenance_refs=list(d.get("provenance_refs", [])),
            support_group_refs=list(d.get("support_group_refs", [])),
            requirements=[dict(r) for r in d.get("requirements", [])],
            assumptions=list(d.get("assumptions", [])),
            dependency_refs=list(d.get("dependency_refs", [])),
            audit_ref=d.get("audit_ref", ""),
            model_decision_ref=d.get("model_decision_ref", ""),
            legacy_relationship_status=d.get(
                "legacy_relationship_status", ""),
            ambiguous_participants=bool(d.get("ambiguous_participants", False)),
            schema_version=version,
        )


def build_hypothesis(
    *,
    parent_path_id: str,
    substrate_state_ref: str,
    participants: list[Participant],
    participant_list_status: str,
    step_scope: str,
    transformation_ref: str = "",
    transformation_signature_status: str = "unknown",
    step_scope_evidence_refs: list[str] | None = None,
    provenance_refs: list[str] | None = None,
    support_group_refs: list[str] | None = None,
    requirements: list[dict] | None = None,
    assumptions: list[str] | None = None,
    dependency_refs: list[str] | None = None,
    audit_ref: str = "",
    model_decision_ref: str = "",
    legacy_relationship_status: str = "",
    origin_group_key: str = "",
) -> ReactionHypothesis:
    """构造反应假设(参与物先过 H02/H03 契约与归并)。

    hypothesis_id = 冻结反应语义哈希(父路径 + 底物状态 + 参与物规范化 +
    转化引用 + 参与物列表状态 + step_scope + 来源组键 + **科学前提**
    (requirements 全语义/顺序无关、assumptions、dependency_refs,
    R2-07))。origin_group_key 是调用方给的来源组指纹(如同一供体记录);
    不同来源组键默认不合并(无法确认等价时不强制合并)。
    """
    if not participants:
        raise HypothesisContractError(
            "反应假设至少需要一个参与物", {"parent_path_id": parent_path_id})
    if participant_list_status not in PARTICIPANT_LIST_STATUSES:
        raise HypothesisContractError(
            f"participant_list_status 非法:{participant_list_status!r}",
            {"participant_list_status": participant_list_status})
    if step_scope not in STEP_SCOPES:
        raise HypothesisContractError(
            f"step_scope 非法:{step_scope!r}", {"step_scope": step_scope})
    # 底物锚点(F07):substrate_state_ref 必须是本假设的 reactant 侧
    # primary_substrate 参与物 —— 引用不属于反应物锚点的状态属于
    # 结构性违约,不能构造后又被审计为"全核实"
    anchor_ok = any(
        p.side == PARTICIPANT_SIDE_REACTANT
        and p.role == PARTICIPANT_ROLE_PRIMARY_SUBSTRATE
        and p.state_ref == substrate_state_ref
        for p in participants)
    if not anchor_ok:
        raise HypothesisContractError(
            "substrate_state_ref 不是本假设的 reactant 侧 primary_"
            "substrate 参与物(底物锚点违约)",
            {"kind": "substrate_anchor_violation",
             "substrate_state_ref": substrate_state_ref,
             "parent_path_id": parent_path_id})
    normalized, ambiguous = normalize_participants(list(participants))
    if participant_list_status in (
            PARTICIPANT_LIST_SOURCE_COMPLETE, PARTICIPANT_LIST_DECLARED_COMPLETE
    ) and not any(
            p.side == PARTICIPANT_SIDE_PRODUCT for p in normalized):
        raise HypothesisContractError(
            "完整声明的假设必须至少有一个产物侧参与物",
            {"parent_path_id": parent_path_id})
    semantic = canonical_json([p.to_dict() for p in normalized])
    # R2-07:科学前提入身份 —— requirements(essential/preference 全语义,
    # 顺序无关)、assumptions、dependency_refs 均影响假设语义:同父/同
    # 结构/同来源但要求有氧/无氧/带未解决依赖是三个不同假设,可共存
    # 落账;相同语义重放 ⇒ 同 id 幂等。
    hypothesis_id = stable_id(
        "hyp", parent_path_id, substrate_state_ref, semantic,
        transformation_ref, participant_list_status, step_scope,
        origin_group_key,
        canonical_json(sorted(canonical_json(dict(r))
                              for r in (requirements or []))),
        canonical_json(sorted(assumptions or [])),
        canonical_json(sorted(dependency_refs or [])))
    return ReactionHypothesis(
        hypothesis_id=hypothesis_id,
        parent_path_id=parent_path_id,
        substrate_state_ref=substrate_state_ref,
        participants=normalized,
        participant_list_status=participant_list_status,
        step_scope=step_scope,
        transformation_ref=transformation_ref,
        transformation_signature_status=transformation_signature_status,
        step_scope_evidence_refs=list(step_scope_evidence_refs or []),
        provenance_refs=list(provenance_refs or []),
        support_group_refs=list(support_group_refs or []),
        requirements=[dict(r) for r in requirements or []],
        assumptions=list(assumptions or []),
        dependency_refs=list(dependency_refs or []),
        audit_ref=audit_ref,
        model_decision_ref=model_decision_ref,
        legacy_relationship_status=legacy_relationship_status,
        ambiguous_participants=ambiguous,
    )
