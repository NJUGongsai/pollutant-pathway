"""P9-T3: Child-run separation (ADR-0006, final_design §22, Phase A criterion 6).

External evidence augmentation REQUIRES a child run: the child manifests
preserve the parent identity (parent_run_id) and carry the external
evidence_ids appended to the parent's evidence set. A frozen parent is never
augmented — augmentation is refused fail-closed (``FrozenParentError``). The
parent's own evidence list is never mutated (immutability).

Child_run_id is content-addressed: it is derived from the parent_run_id + a
hash of the evidence IDs. This ensures:
- same parent + same evidence set → same child_run_id (idempotent)
- same parent + different evidence set → different child_run_id (no collision)

This module models the separation contract. It does NOT modify the P4 run
store (strict-untouched) — it only defines the augmentation semantics on top
of it.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import StrictModel, NonEmptyStr
from reaction_agent.p9.external.schemas import ExternalEvidenceRecord


class FrozenParentError(Exception):
    """Raised when attempting to augment a frozen parent run."""


class ChildAugmentation(StrictModel):
    """A child-run augmentation of a parent run with external evidence."""

    child_run_id: NonEmptyStr
    parent_run_id: NonEmptyStr
    evidence_ids: list[NonEmptyStr]
    augmentation_note: NonEmptyStr


def _compute_child_run_id(parent_run_id: str, evidence_ids: list[str]) -> str:
    """Content-addressed child_run_id from parent + evidence set hash.

    Same parent + same evidence set → same id (idempotent).
    Different evidence set → different id (no collision).
    """
    evidence_hash = canonical_hash(sorted(evidence_ids))[:12]
    return f"{parent_run_id}-ext-{evidence_hash}"


class ExternalEvidenceAugmenter:
    """Builds a child-run augmentation manifest for a set of external records.

    The parent evidence list is never mutated; the child carries the union of
    parent + external evidence. A frozen parent is refused.
    """

    def augment(
        self,
        *,
        parent_frozen: bool,
        parent_run_id: str,
        records: list[ExternalEvidenceRecord],
        parent_evidence_ids: list[str] | None = None,
    ) -> ChildAugmentation:
        if parent_frozen:
            raise FrozenParentError(
                f"cannot augment frozen parent run {parent_run_id}"
            )
        parent_evidence = list(parent_evidence_ids or [])
        external_ids = [r.evidence_id for r in records]
        combined = parent_evidence + external_ids
        child_run_id = _compute_child_run_id(parent_run_id, combined)
        return ChildAugmentation(
            child_run_id=child_run_id,
            parent_run_id=parent_run_id,
            evidence_ids=combined,
            augmentation_note="external evidence augmentation",
        )