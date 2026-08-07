"""P9-T3 RED tests — Child-run separation (ADR-0006, final_design §22).

Phase A criteria 6: child-run separation — external evidence augmentation goes
through a CHILD run; the frozen parent run is immutable.

Design: external evidence augmentation produces a child run whose manifest
records the parent_run_id and the external evidence_ids. The frozen parent's
evidence_ids / result_hash are never mutated. An existing child id is never
overwritten.

We test the separation policy object (not the full ImmutableRunStore, which is
P4-owned and strict-untouched — we only consume it).
"""
from __future__ import annotations

import pytest

from reaction_agent.p9.external.schemas import ExternalEvidenceRecord, EvidenceProvenance
from reaction_agent.p9.external.child_run import (
    ChildAugmentation,
    ExternalEvidenceAugmenter,
    FrozenParentError,
)


def make_record(hash_: str = "abc123") -> ExternalEvidenceRecord:
    return ExternalEvidenceRecord(
        evidence_id="ext-1",
        source_id="chemrxiv-2024",
        license="CC-BY-4.0",
        provenance=EvidenceProvenance(
            source_version="2024.1",
            retrieval_date="2026-08-01",
            content_hash=hash_,
        ),
        content="reaction A -> B proceeds",
    )


def test_child_augmentation_records_parent_and_evidence() -> None:
    aug = ChildAugmentation(
        child_run_id="child-1",
        parent_run_id="parent-1",
        evidence_ids=["ext-1"],
        augmentation_note="external evidence augmentation",
    )
    assert aug.parent_run_id == "parent-1"
    assert aug.evidence_ids == ["ext-1"]


def test_child_augmentation_requires_parent() -> None:
    with pytest.raises(Exception):
        ChildAugmentation(
            child_run_id="child-1",
            parent_run_id="",
            evidence_ids=[],
            augmentation_note="x",
        )


def test_augmenter_rejects_frozen_parent() -> None:
    """If the parent is frozen, augmentation must be refused (fail-closed)."""
    augmenter = ExternalEvidenceAugmenter()
    with pytest.raises(FrozenParentError):
        augmenter.augment(
            parent_frozen=True,
            parent_run_id="parent-1",
            records=[make_record()],
        )


def test_augmenter_builds_child_manifest_for_active_parent() -> None:
    augmenter = ExternalEvidenceAugmenter()
    child = augmenter.augment(
        parent_frozen=False,
        parent_run_id="parent-1",
        records=[make_record()],
    )
    assert child.parent_run_id == "parent-1"
    assert child.evidence_ids == ["ext-1"]
    assert child.child_run_id.startswith("parent-1")


def test_augmenter_never_mutates_parent() -> None:
    """The parent evidence list passed in must be returned unchanged."""
    augmenter = ExternalEvidenceAugmenter()
    parent_evidence = ["strict-ev-0"]
    child = augmenter.augment(
        parent_frozen=False,
        parent_run_id="parent-1",
        records=[make_record()],
        parent_evidence_ids=parent_evidence,
    )
    # parent evidence list untouched (immutability)
    assert parent_evidence == ["strict-ev-0"]
    # child carries parent evidence + external evidence
    assert "strict-ev-0" in child.evidence_ids
    assert "ext-1" in child.evidence_ids