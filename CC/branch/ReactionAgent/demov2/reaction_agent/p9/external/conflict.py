"""P9-T3: Conflict policy — external evidence vs frozen snapshot (Phase A criterion 4).

Semantics (matches ADR-0003 / ADR-0006): the frozen snapshot is authoritative.
When an external record's source is present in the snapshot with a DIFFERENT
content hash, the snapshot wins and the external record is suppressed —
external evidence can never silently overwrite frozen evidence. The resolution
is deterministic and typed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from reaction_agent.p9.external.schemas import ExternalEvidenceRecord


class ConflictResolution(str, Enum):
    """Deterministic outcome of an external-vs-snapshot comparison."""

    consistent = "consistent"          # snapshot already has the same content hash
    snapshot_wins = "snapshot_wins"    # snapshot differs; external suppressed
    external_accepted = "external_accepted"  # no snapshot entry for this source


@dataclass(frozen=True)
class ConflictResult:
    """Result of a conflict comparison between an external record and the snapshot."""

    resolution: ConflictResolution
    external_suppressed: bool


class ConflictPolicy:
    """Encapsulates the snapshot-authoritative conflict rule.

    Fail-closed: any policy that cannot decide must not accept external
    evidence. The default policy treats the snapshot as authoritative.
    """

    def __init__(self, snapshot_authoritative: bool = True) -> None:
        self._snapshot_authoritative = snapshot_authoritative

    def resolve(
        self,
        record: ExternalEvidenceRecord,
        snapshot_content_hash_by_source: dict[str, str],
    ) -> ConflictResult:
        if not self._snapshot_authoritative:
            # Fail-closed: without snapshot authority we refuse to accept.
            return ConflictResult(
                resolution=ConflictResolution.snapshot_wins,
                external_suppressed=True,
            )
        return resolve_record_conflict(record, snapshot_content_hash_by_source)


def resolve_record_conflict(
    record: ExternalEvidenceRecord,
    snapshot_content_hash_by_source: dict[str, str],
) -> ConflictResult:
    """Compare an external record against the snapshot's content hashes.

    The snapshot is keyed by source_id. If the source is absent from the
    snapshot, there is no conflict → external accepted. If present with the
    same content hash → consistent. If present with a different hash →
    snapshot wins (external suppressed).
    """
    snapshot_hash = snapshot_content_hash_by_source.get(record.source_id)
    if snapshot_hash is None:
        return ConflictResult(
            resolution=ConflictResolution.external_accepted,
            external_suppressed=False,
        )
    if snapshot_hash == record.provenance.content_hash:
        return ConflictResult(
            resolution=ConflictResolution.consistent,
            external_suppressed=False,
        )
    return ConflictResult(
        resolution=ConflictResolution.snapshot_wins,
        external_suppressed=True,
    )