"""P4 immutable run/trace/manifest schemas (final_design §20, §21, §23).

Content-addressed immutable run:
- same request + same versions + same frozen evidence ⇒ same result hash;
- frozen runs cannot be silently mutated;
- child runs preserve the parent identity and never overwrite the parent
  result.
"""
from __future__ import annotations

from enum import Enum
from reaction_agent.schemas.common import StrictModel, NonEmptyStr
from reaction_agent.schemas.result import StageSummary


class RunFreezeState(str, Enum):
    active = "active"
    frozen = "frozen"


class ComponentVersions(StrictModel):
    """Version pins for every component contributing to a run."""
    normalization_version: NonEmptyStr
    config_version: NonEmptyStr
    policy_version: NonEmptyStr
    kernel_version: NonEmptyStr
    candidate_version: NonEmptyStr
    ranker_version: NonEmptyStr
    snapshot_builder_version: NonEmptyStr


class ImmutableRunManifest(StrictModel):
    """Content-addressed manifest of an immutable prediction run.

    The result hash covers every decision-relevant input (P4-R1-E): the final
    decision, the ranking, the applicability, the support/counterevidence
    hashes, the trace, the namespace, the versions and the classification.
    """
    run_id: NonEmptyStr
    parent_run_id: str | None = None
    request_hash: NonEmptyStr
    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    fold_view_id: str = ""
    versions: ComponentVersions
    trace: StageSummary
    evidence_ids: list[NonEmptyStr]
    independent_group_ids: list[NonEmptyStr]
    result_hash: NonEmptyStr
    freeze_state: RunFreezeState
    capability_status: str = ""
    blocked_reasons: list[NonEmptyStr] = []
    classification: str = "synthetic_fixture"
    decision: dict = {}
    ranking: dict = {}
    applicability: dict = {}
    support_hashes: dict = {}
    counterevidence_hashes: dict = {}
    namespace: dict = {}
