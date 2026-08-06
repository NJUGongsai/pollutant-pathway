"""P4-R1-B/D typed authority + run namespace (final_design §4.5, §15.3).

``P4Classification`` is a frozen enum — a free string can never be trusted.
``P3AuthorityHandle`` is the ONLY authority a P4 pipeline may consume; it is
produced exclusively by the verified P3 consumer and carries the frozen
manifest version, the current-run namespace binding and the evidence kind.
A caller-written ``P4CapabilityStatus`` is NOT an authority.

``RunNamespace`` binds every run/query/case/fold/snapshot ID and hash plus the
policy/config/component versions. Evidence, candidates, trace, manifest and
the P4 request must all resolve to the SAME namespace (exact match).
"""
from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from reaction_agent.policies.p4_decision_policy import P4_POLICY_VERSION
from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class P4Classification(str, Enum):
    """Frozen evidence classification (final_design §15.3, evidence_kind_semantics)."""
    real = "real"
    synthetic_fixture = "synthetic_fixture"
    blocked = "blocked"
    diagnostic = "diagnostic"


class AuthoritySource(str, Enum):
    """Where an authority handle came from — never inferred from a string."""
    p3_current_run = "p3_current_run"        # verified KernelResult artifact
    p3_interface_only = "p3_interface_only"  # interface parsed, no current run
    synthetic_fixture = "synthetic_fixture"  # fixture authority (machinery only)
    blocked = "blocked"                      # capability absent (typed blocker)


class RunNamespace(StrictModel):
    """Immutably binds the full run identity + freeze versions.

    ``run_namespace_required`` from the frozen p3-p4-3 contract is
    (run_id, case_id, query_id, fold_id, snapshot_id, snapshot_hash). P4 adds
    the policy/config/component versions it recorded its own decisions under.
    """
    run_id: NonEmptyStr
    case_id: NonEmptyStr
    query_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    policy_version: NonEmptyStr = P4_POLICY_VERSION
    config_version: NonEmptyStr = "p1-1"
    component_versions: dict[str, str] = {}

    def matches(self, other: "RunNamespace") -> bool:
        """Exact match on every identity/hash/version field."""
        return self.model_dump() == other.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "RunNamespace":
        """Build from a frozen record (missing optional fields use defaults)."""
        return cls(
            run_id=data.get("run_id", ""),
            case_id=data.get("case_id", ""),
            query_id=data.get("query_id", ""),
            fold_id=data.get("fold_id", ""),
            snapshot_id=data.get("snapshot_id", ""),
            snapshot_hash=data.get("snapshot_hash", ""),
            policy_version=data.get("policy_version", P4_POLICY_VERSION),
            config_version=data.get("config_version", "p1-1"),
            component_versions=data.get("component_versions", {}),
        )


class P3AuthorityHandle(StrictModel):
    """Typed authority handle produced ONLY by the verified P3 consumer.

    ``source`` and ``evidence_kind`` are cross-field validated: a blocked
    handle can never carry ``evidence_kind=real``, and a synthetic-fixture
    handle can never relabel itself ``real``.
    """
    source: AuthoritySource
    manifest_version: NonEmptyStr
    schema_hash: str = ""
    namespace: RunNamespace
    evidence_kind: P4Classification
    blocked_reasons: list[NonEmptyStr] = []

    @model_validator(mode="after")
    def _cross_field_invariants(self) -> "P3AuthorityHandle":
        if self.source == AuthoritySource.blocked:
            if self.evidence_kind != P4Classification.blocked:
                raise ValueError(
                    "blocked authority cannot carry evidence_kind="
                    f"{self.evidence_kind.value!r}")
        elif self.source == AuthoritySource.synthetic_fixture:
            if self.evidence_kind != P4Classification.synthetic_fixture:
                raise ValueError(
                    "synthetic fixture authority cannot relabel evidence_kind="
                    f"{self.evidence_kind.value!r}")
        elif self.source == AuthoritySource.p3_interface_only:
            if self.evidence_kind != P4Classification.diagnostic:
                raise ValueError(
                    "interface-only authority must be diagnostic, got "
                    f"{self.evidence_kind.value!r}")
        # p3_current_run may carry real OR synthetic_fixture (never blocked).
        return self

    @property
    def capability_available(self) -> bool:
        return self.source == AuthoritySource.p3_current_run

    @property
    def verifiable(self) -> bool:
        """True when the handle is backed by a verified current-run artifact."""
        return self.source == AuthoritySource.p3_current_run