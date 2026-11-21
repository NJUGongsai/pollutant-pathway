"""ppv1-route-status-v1 — 反应预测 / 降解路径线五态路线状态与失败分离契约。

定位与红线：
1. 本模块为独立伴随 schema 与校验器，**不修改**任何已冻结的判分器实现
   （``evaluation.py``、``s5b_scoring.py``、``score_disclosure_v4cn.py``）。
2. 主成绩（``ppv1-criteria-v6`` 单一参考 Hit@1/3/5，失败题留分母按未命中计）
   永远保持不可变（``primary_score_immutable=True``）；五态分类与双口径汇总
   只作披露与诊断，不回写主成绩。
3. 未命中单一参考的案例，**未经师姐 / 专家书面复核确认，一律 fail-closed 落为
   ``UNRESOLVED``（科学判定 ``NE``，不记 ``0``）**；``OUTSIDE_GOLD_PLAUSIBLE``
   只记 ``NE``（``OUTSIDE_COVERAGE``），仅经复核且附具体化学矛盾证据的
   ``OUTSIDE_GOLD_CONTRADICTED`` 才可记 ``ZERO``（``WRONG_CHEMISTRY``）。
4. 工程/交付失败（``LENGTH_EMPTY`` / ``INVALID_JSON`` / ``RESULT_UNKNOWN`` /
   ``RUN_ERROR`` / ``NO_EVENT``）与科学零分严格分离：交付轴单列，科学层记
   ``NE``（``ENGINEERING_FAILURE``）；同时在汇总时提供主口径（含在分母）与
   敏感性口径（剔除工程失败后的分母）。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

ROUTE_STATUS_SCHEMA_VERSION = "ppv1-route-status-v1"
ALLOWED_EXPERT_ROLES = frozenset({"domain_expert", "senior_chemist"})


class RouteStatus(str, Enum):
    """黄老师 2026-11-18 来信定义的五态路线状态。"""

    IN_GOLD_EXACT = "IN_GOLD_EXACT"
    IN_GOLD_PARTIAL = "IN_GOLD_PARTIAL"
    OUTSIDE_GOLD_PLAUSIBLE = "OUTSIDE_GOLD_PLAUSIBLE"
    OUTSIDE_GOLD_CONTRADICTED = "OUTSIDE_GOLD_CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"


class DeliveryStatus(str, Enum):
    """交付 / 工程执行状态（与科学判定层正交）。"""

    OK = "OK"
    LENGTH_EMPTY = "LENGTH_EMPTY"
    INVALID_JSON = "INVALID_JSON"
    RESULT_UNKNOWN = "RESULT_UNKNOWN"
    RUN_ERROR = "RUN_ERROR"
    NO_EVENT = "NO_EVENT"


class ZeroReason(str, Enum):
    """未命中 / 零分归因标签。"""

    NONE = "NONE"
    WRONG_CHEMISTRY = "WRONG_CHEMISTRY"
    MISSING_MODULE = "MISSING_MODULE"
    OUTSIDE_COVERAGE = "OUTSIDE_COVERAGE"
    ENGINEERING_FAILURE = "ENGINEERING_FAILURE"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ScientificEvalLabel(str, Enum):
    """科学层判定标签（NE = Not Evaluated，不记科学 0 分）。"""

    HIT_EXACT = "HIT_EXACT"
    HIT_PARTIAL = "HIT_PARTIAL"
    NE = "NE"
    ZERO = "ZERO"


_OUTSIDE_GOLD_VERDICTS = frozenset(
    {
        RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
        RouteStatus.OUTSIDE_GOLD_CONTRADICTED,
        RouteStatus.UNRESOLVED,
    }
)
_API_OR_FORMAT_FAILURE_STATUSES = frozenset(
    {
        DeliveryStatus.LENGTH_EMPTY,
        DeliveryStatus.INVALID_JSON,
        DeliveryStatus.RESULT_UNKNOWN,
        DeliveryStatus.RUN_ERROR,
    }
)


@dataclass(frozen=True)
class ExpertReviewRecord:
    """师姐 / 领域化学专家对参考范围外路线的复核记录。"""

    reviewer_id: str
    reviewer_role: str
    reviewed_at: str
    verdict: RouteStatus
    evidence: str
    confirmed: bool = True

    def __post_init__(self) -> None:
        verdict = (
            self.verdict
            if isinstance(self.verdict, RouteStatus)
            else RouteStatus(self.verdict)
        )
        object.__setattr__(self, "verdict", verdict)
        if verdict not in _OUTSIDE_GOLD_VERDICTS:
            raise ValueError(
                f"ExpertReviewRecord.verdict 必须是三态之一 {_OUTSIDE_GOLD_VERDICTS}, "
                f"实际为 {verdict!r}"
            )
        if not isinstance(self.reviewer_id, str) or not self.reviewer_id.strip():
            raise ValueError("ExpertReviewRecord.reviewer_id 不能为空")
        if self.reviewer_role not in ALLOWED_EXPERT_ROLES:
            raise ValueError(
                f"ExpertReviewRecord.reviewer_role 必须在 {sorted(ALLOWED_EXPERT_ROLES)} 中, "
                f"实际为 {self.reviewer_role!r}"
            )
        if not isinstance(self.reviewed_at, str) or not self.reviewed_at.strip():
            raise ValueError("ExpertReviewRecord.reviewed_at 不能为空")
        if self.confirmed and verdict == RouteStatus.OUTSIDE_GOLD_CONTRADICTED:
            if not isinstance(self.evidence, str) or not self.evidence.strip():
                raise ValueError(
                    "OUTSIDE_GOLD_CONTRADICTED 经确认时必须附非空化学矛盾 evidence"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "reviewed_at": self.reviewed_at,
            "verdict": self.verdict.value,
            "evidence": self.evidence,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExpertReviewRecord:
        return cls(
            reviewer_id=str(data["reviewer_id"]),
            reviewer_role=str(data["reviewer_role"]),
            reviewed_at=str(data["reviewed_at"]),
            verdict=RouteStatus(data["verdict"]),
            evidence=str(data.get("evidence", "")),
            confirmed=bool(data.get("confirmed", True)),
        )


@dataclass(frozen=True)
class RouteStatusRecord:
    """单道题的五态路线状态与工程/科学分离记录。"""

    schema_version: str
    qid: str
    case_id: str
    caliber: str
    hit_rank: int | None
    delivery_status: DeliveryStatus
    route_status: RouteStatus
    scientific_eval_label: ScientificEvalLabel
    zero_reason: ZeroReason
    expert_review: ExpertReviewRecord | None = None
    primary_score_immutable: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "delivery_status",
            self.delivery_status
            if isinstance(self.delivery_status, DeliveryStatus)
            else DeliveryStatus(self.delivery_status),
        )
        object.__setattr__(
            self,
            "route_status",
            self.route_status
            if isinstance(self.route_status, RouteStatus)
            else RouteStatus(self.route_status),
        )
        object.__setattr__(
            self,
            "scientific_eval_label",
            self.scientific_eval_label
            if isinstance(self.scientific_eval_label, ScientificEvalLabel)
            else ScientificEvalLabel(self.scientific_eval_label),
        )
        object.__setattr__(
            self,
            "zero_reason",
            self.zero_reason
            if isinstance(self.zero_reason, ZeroReason)
            else ZeroReason(self.zero_reason),
        )
        validate_route_status_record(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "qid": self.qid,
            "case_id": self.case_id,
            "caliber": self.caliber,
            "hit_rank": self.hit_rank,
            "delivery_status": self.delivery_status.value,
            "route_status": self.route_status.value,
            "scientific_eval_label": self.scientific_eval_label.value,
            "zero_reason": self.zero_reason.value,
            "expert_review": (
                self.expert_review.to_dict() if self.expert_review is not None else None
            ),
            "primary_score_immutable": self.primary_score_immutable,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RouteStatusRecord:
        raw_review = data.get("expert_review")
        expert_review = (
            ExpertReviewRecord.from_dict(raw_review)
            if isinstance(raw_review, Mapping)
            else None
        )
        hit_rank_val = data.get("hit_rank")
        return cls(
            schema_version=str(data["schema_version"]),
            qid=str(data["qid"]),
            case_id=str(data["case_id"]),
            caliber=str(data["caliber"]),
            hit_rank=int(hit_rank_val) if hit_rank_val is not None else None,
            delivery_status=DeliveryStatus(data["delivery_status"]),
            route_status=RouteStatus(data["route_status"]),
            scientific_eval_label=ScientificEvalLabel(data["scientific_eval_label"]),
            zero_reason=ZeroReason(data["zero_reason"]),
            expert_review=expert_review,
            primary_score_immutable=bool(data["primary_score_immutable"]),
            notes=str(data.get("notes", "")),
        )


def validate_route_status_record(record: RouteStatusRecord) -> None:
    """严格校验五态记录是否符合冻结与专家复核红线，违约一律抛出 ValueError。"""
    if record.schema_version != ROUTE_STATUS_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version 必须为 {ROUTE_STATUS_SCHEMA_VERSION!r}, 实际为 {record.schema_version!r}"
        )
    if record.primary_score_immutable is not True:
        raise ValueError("primary_score_immutable 必须为 True，披露层严禁回写主成绩")
    if not isinstance(record.qid, str) or not record.qid.strip():
        raise ValueError("qid 不能为空")
    if not isinstance(record.case_id, str) or not record.case_id.strip():
        raise ValueError("case_id 不能为空")
    if not isinstance(record.caliber, str) or not record.caliber.strip():
        raise ValueError("caliber 不能为空")
    if record.hit_rank is not None and (isinstance(record.hit_rank, bool) or record.hit_rank < 1):
        raise ValueError(f"hit_rank 若非 None 则必须是 >= 1 的整数，实际为 {record.hit_rank!r}")

    if record.delivery_status != DeliveryStatus.OK:
        if record.hit_rank is not None:
            raise ValueError("delivery_status != OK 时 hit_rank 必须为 None")
        if record.route_status != RouteStatus.UNRESOLVED:
            raise ValueError("工程/交付失败时 route_status 必须为 UNRESOLVED")
        if record.scientific_eval_label != ScientificEvalLabel.NE:
            raise ValueError("工程/交付失败时科学层必须记 NE，不得记 ZERO")
        if record.zero_reason != ZeroReason.ENGINEERING_FAILURE:
            raise ValueError("工程/交付失败时 zero_reason 必须为 ENGINEERING_FAILURE")
        return

    if record.route_status == RouteStatus.IN_GOLD_EXACT:
        if record.scientific_eval_label != ScientificEvalLabel.HIT_EXACT:
            raise ValueError("IN_GOLD_EXACT 的 scientific_eval_label 必须为 HIT_EXACT")
        if record.zero_reason != ZeroReason.NONE:
            raise ValueError("IN_GOLD_EXACT 的 zero_reason 必须为 NONE")
        return

    if record.route_status == RouteStatus.IN_GOLD_PARTIAL:
        if record.scientific_eval_label != ScientificEvalLabel.HIT_PARTIAL:
            raise ValueError("IN_GOLD_PARTIAL 的 scientific_eval_label 必须为 HIT_PARTIAL")
        if record.zero_reason != ZeroReason.NONE:
            raise ValueError("IN_GOLD_PARTIAL 的 zero_reason 必须为 NONE")
        return

    if record.route_status == RouteStatus.OUTSIDE_GOLD_PLAUSIBLE:
        if (
            record.expert_review is None
            or not record.expert_review.confirmed
            or record.expert_review.verdict != RouteStatus.OUTSIDE_GOLD_PLAUSIBLE
        ):
            raise ValueError(
                "OUTSIDE_GOLD_PLAUSIBLE 必须附已确认且同结论的 ExpertReviewRecord"
            )
        if record.scientific_eval_label != ScientificEvalLabel.NE:
            raise ValueError("OUTSIDE_GOLD_PLAUSIBLE 科学层必须记 NE，严禁记 ZERO")
        if record.zero_reason != ZeroReason.OUTSIDE_COVERAGE:
            raise ValueError("OUTSIDE_GOLD_PLAUSIBLE 的 zero_reason 必须为 OUTSIDE_COVERAGE")
        return

    if record.route_status == RouteStatus.OUTSIDE_GOLD_CONTRADICTED:
        if (
            record.expert_review is None
            or not record.expert_review.confirmed
            or record.expert_review.verdict != RouteStatus.OUTSIDE_GOLD_CONTRADICTED
            or not record.expert_review.evidence.strip()
        ):
            raise ValueError(
                "OUTSIDE_GOLD_CONTRADICTED 必须附已确认且含非空证据的 ExpertReviewRecord"
            )
        if record.scientific_eval_label != ScientificEvalLabel.ZERO:
            raise ValueError("OUTSIDE_GOLD_CONTRADICTED 的 scientific_eval_label 必须为 ZERO")
        if record.zero_reason != ZeroReason.WRONG_CHEMISTRY:
            raise ValueError("OUTSIDE_GOLD_CONTRADICTED 的 zero_reason 必须为 WRONG_CHEMISTRY")
        return

    # RouteStatus.UNRESOLVED (delivery_status == OK)
    if record.scientific_eval_label != ScientificEvalLabel.NE:
        raise ValueError("UNRESOLVED 未经核实必须记 NE，严禁记 ZERO")
    if record.zero_reason != ZeroReason.UNRESOLVED:
        raise ValueError("delivery_status == OK 且 UNRESOLVED 时 zero_reason 必须为 UNRESOLVED")


def classify_route_status(
    *,
    qid: str,
    case_id: str,
    caliber: str = "ppv1-criteria-v6",
    hit_rank: int | None = None,
    match_bucket: str | None = None,
    delivery_status: DeliveryStatus | str = DeliveryStatus.OK,
    expert_review: ExpertReviewRecord | None = None,
    notes: str = "",
) -> RouteStatusRecord:
    """将单题判分桶与交付状态（及可选专家复核）确定性地映射为五态记录。"""
    d_status = (
        delivery_status
        if isinstance(delivery_status, DeliveryStatus)
        else DeliveryStatus(delivery_status)
    )
    if match_bucket == "unmatched_no_event" and d_status == DeliveryStatus.OK:
        d_status = DeliveryStatus.NO_EVENT

    # 规则 1：工程/交付失败与科学判定严格分离（未产生合规候选事件同理归入交付轴）。
    if d_status != DeliveryStatus.OK:
        if hit_rank is not None:
            raise ValueError(
                f"delivery_status={d_status.value} 时不应存在 hit_rank={hit_rank!r}"
            )
        return RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid=qid,
            case_id=case_id,
            caliber=caliber,
            hit_rank=None,
            delivery_status=d_status,
            route_status=RouteStatus.UNRESOLVED,
            scientific_eval_label=ScientificEvalLabel.NE,
            zero_reason=ZeroReason.ENGINEERING_FAILURE,
            expert_review=expert_review,
            primary_score_immutable=True,
            notes=notes,
        )

    # 规则 2：单一参考下主产物精确命中。
    if match_bucket == "matched_product_hit" or (
        match_bucket is None and hit_rank is not None and hit_rank >= 1
    ):
        return RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid=qid,
            case_id=case_id,
            caliber=caliber,
            hit_rank=hit_rank,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.IN_GOLD_EXACT,
            scientific_eval_label=ScientificEvalLabel.HIT_EXACT,
            zero_reason=ZeroReason.NONE,
            expert_review=None,
            primary_score_immutable=True,
            notes=notes,
        )

    # 规则 3：Gold 内部分命中。
    if match_bucket == "product_hit_partial":
        return RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid=qid,
            case_id=case_id,
            caliber=caliber,
            hit_rank=None,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.IN_GOLD_PARTIAL,
            scientific_eval_label=ScientificEvalLabel.HIT_PARTIAL,
            zero_reason=ZeroReason.NONE,
            expert_review=None,
            primary_score_immutable=True,
            notes=notes,
        )

    # 规则 4：未命中单一参考，无已确认专家复核时 fail-closed 落为 UNRESOLVED（NE）。
    if expert_review is None or not expert_review.confirmed:
        return RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid=qid,
            case_id=case_id,
            caliber=caliber,
            hit_rank=None,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.UNRESOLVED,
            scientific_eval_label=ScientificEvalLabel.NE,
            zero_reason=ZeroReason.UNRESOLVED,
            expert_review=expert_review,
            primary_score_immutable=True,
            notes=notes,
        )

    if expert_review.verdict == RouteStatus.OUTSIDE_GOLD_PLAUSIBLE:
        return RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid=qid,
            case_id=case_id,
            caliber=caliber,
            hit_rank=None,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
            scientific_eval_label=ScientificEvalLabel.NE,
            zero_reason=ZeroReason.OUTSIDE_COVERAGE,
            expert_review=expert_review,
            primary_score_immutable=True,
            notes=notes,
        )

    if expert_review.verdict == RouteStatus.OUTSIDE_GOLD_CONTRADICTED:
        return RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid=qid,
            case_id=case_id,
            caliber=caliber,
            hit_rank=None,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.OUTSIDE_GOLD_CONTRADICTED,
            scientific_eval_label=ScientificEvalLabel.ZERO,
            zero_reason=ZeroReason.WRONG_CHEMISTRY,
            expert_review=expert_review,
            primary_score_immutable=True,
            notes=notes,
        )

    return RouteStatusRecord(
        schema_version=ROUTE_STATUS_SCHEMA_VERSION,
        qid=qid,
        case_id=case_id,
        caliber=caliber,
        hit_rank=None,
        delivery_status=DeliveryStatus.OK,
        route_status=RouteStatus.UNRESOLVED,
        scientific_eval_label=ScientificEvalLabel.NE,
        zero_reason=ZeroReason.UNRESOLVED,
        expert_review=expert_review,
        primary_score_immutable=True,
        notes=notes,
    )


def _hit_at_k_block(records: list[RouteStatusRecord], ks: tuple[int, ...]) -> dict[str, Any]:
    denom = len(records)
    out: dict[str, Any] = {"denominator": denom}
    for k in ks:
        cnt = sum(
            1
            for r in records
            if r.route_status == RouteStatus.IN_GOLD_EXACT
            and r.hit_rank is not None
            and 1 <= r.hit_rank <= k
        )
        out[f"hit@{k}"] = {
            "count": cnt,
            "denominator": denom,
            "pct": round(100.0 * cnt / denom, 2) if denom > 0 else None,
        }
    return out


def summarize_route_statuses(
    records: Iterable[RouteStatusRecord],
    *,
    ks: tuple[int, ...] = (1, 3, 5),
) -> dict[str, Any]:
    """按双口径（主口径含失败 vs 敏感性口径剔除工程失败/无事件）汇总五态记录。"""
    recs = list(records)
    for rec in recs:
        validate_route_status_record(rec)

    api_or_format_fails = [
        r for r in recs if r.delivery_status in _API_OR_FORMAT_FAILURE_STATUSES
    ]
    no_events = [r for r in recs if r.delivery_status == DeliveryStatus.NO_EVENT]
    delivery_ok = [r for r in recs if r.delivery_status == DeliveryStatus.OK]
    non_api_fail = [
        r for r in recs if r.delivery_status not in _API_OR_FORMAT_FAILURE_STATUSES
    ]

    return {
        "schema_version": ROUTE_STATUS_SCHEMA_VERSION,
        "n_total": len(recs),
        "n_delivery_ok": len(delivery_ok),
        "n_api_or_format_failures": len(api_or_format_fails),
        "n_no_event": len(no_events),
        "n_engineering_failures": len(api_or_format_fails) + len(no_events),
        "route_status_counts": {
            s.value: sum(1 for r in recs if r.route_status == s)
            for s in RouteStatus
        },
        "delivery_status_counts": {
            s.value: sum(1 for r in recs if r.delivery_status == s)
            for s in DeliveryStatus
        },
        "scientific_eval_label_counts": {
            s.value: sum(1 for r in recs if r.scientific_eval_label == s)
            for s in ScientificEvalLabel
        },
        "zero_reason_counts": {
            s.value: sum(1 for r in recs if r.zero_reason == s)
            for s in ZeroReason
        },
        "primary_hit_at_k": _hit_at_k_block(recs, ks),
        "sensitivity_excl_engineering_fail_hit_at_k": _hit_at_k_block(non_api_fail, ks),
        "sensitivity_excl_no_event_hit_at_k": _hit_at_k_block(delivery_ok, ks),
    }
