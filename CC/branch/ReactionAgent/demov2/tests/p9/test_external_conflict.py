"""P9-T3 RED tests — Conflict policy (external evidence vs snapshot).

Phase A criterion 4: conflict policy — deterministic behavior when external
evidence conflicts with the frozen snapshot.

Design (matches ADR-0003/ADR-0006): external evidence is a *post-hoc*
appended evidence source. When an external record's key (source + content) is
already present in the frozen snapshot with a DIFFERENT content hash, the
snapshot is authoritative — external evidence cannot silently overwrite
frozen evidence. The conflict resolution is deterministic and typed.
"""
from __future__ import annotations

from reaction_agent.p9.external.schemas import ExternalEvidenceRecord, EvidenceProvenance
from reaction_agent.p9.external.conflict import (
    ConflictResolution,
    ConflictPolicy,
    resolve_record_conflict,
)


def make_record(content_hash: str = "abc123", evidence_id: str = "ext-1") -> ExternalEvidenceRecord:
    return ExternalEvidenceRecord(
        evidence_id=evidence_id,
        source_id="chemrxiv-2024",
        license="CC-BY-4.0",
        provenance=EvidenceProvenance(
            source_version="2024.1",
            retrieval_date="2026-08-01",
            content_hash=content_hash,
        ),
        content="reaction A -> B proceeds",
    )


def test_snapshot_authoritative_on_conflict() -> None:
    ext = make_record(content_hash="ext-hash")
    snapshot_hash = {"chemrxiv-2024": "snapshot-hash"}  # differing content hash
    res = resolve_record_conflict(ext, snapshot_hash)
    assert res.resolution == ConflictResolution.snapshot_wins
    assert res.external_suppressed is True


def test_no_conflict_when_absent_from_snapshot() -> None:
    ext = make_record(content_hash="ext-hash")
    res = resolve_record_conflict(ext, {})
    assert res.resolution == ConflictResolution.external_accepted
    assert res.external_suppressed is False


def test_no_conflict_when_snapshot_matches() -> None:
    ext = make_record(content_hash="abc123")
    res = resolve_record_conflict(ext, {"chemrxiv-2024": "abc123"})
    assert res.resolution == ConflictResolution.consistent
    assert res.external_suppressed is False


def test_conflict_policy_fails_closed() -> None:
    """A policy that cannot decide must not accept external evidence."""
    policy = ConflictPolicy(snapshot_authoritative=True)
    ext = make_record(content_hash="ext-hash")
    res = policy.resolve(ext, {"chemrxiv-2024": "snapshot-hash"})
    assert res.resolution == ConflictResolution.snapshot_wins
    assert res.external_suppressed is True


def test_snapshot_key_uses_source_id() -> None:
    ext = make_record(content_hash="ext-hash")
    # snapshot keyed by a different source should not conflict
    res = resolve_record_conflict(ext, {"other-source": "snapshot-hash"})
    assert res.resolution == ConflictResolution.external_accepted