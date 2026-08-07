"""P9-T3: Child-run separation (ADR-0006, final_design §22, Phase A criterion 6).

External evidence augmentation REQUIRES a child run: the child manifests
preserve the parent identity (parent_run_id) and carry the external
evidence_ids appended to the parent's evidence set. A FRoZEN parent is never
augmented — augmentation is refused fail-closed (``FrozenParentError``). The
parent's own evidence list is never mutated (immutability).

This module models the separation contract. It does NOT modify the P4 run
store (strict-untouched) — it only defines the augmentation semantics on top
of it.
"""
from __future__ import annotations

from pydantic import Field

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
        child_run_id = f"{parent_run_id}-ext"
        return ChildAugmentation(
            child_run_id=child_run_id,
            parent_run_id=parent_run_id,
            evidence_ids=parent_evidence + external_ids,
            augmentation_note="external evidence augmentation",
        )