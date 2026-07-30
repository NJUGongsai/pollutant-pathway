"""Immutable snapshot builder + read-only loader (§16.1-16.7).

Re-exports the public API:
- ``build_snapshot(config, evidence_iter) -> SnapshotManifest`` (atomic finalize)
- ``load_snapshot(snapshot_id_or_path, root=None) -> SnapshotRecord`` (read-only)
- ``compute_snapshot_hash(config, items) -> str`` (hash without writing)
- ``SnapshotEvidenceItem`` (frozen input item)
"""

from reaction_agent.snapshot.builder import (
    build_snapshot,
    compute_snapshot_hash,
    SnapshotEvidenceItem,
    SnapshotBuildError,
    SnapshotExistsError,
    BUILDER_VERSION,
)
from reaction_agent.snapshot.loader import (
    load_snapshot,
    SnapshotNotFoundError,
    SnapshotIncompleteError,
    SnapshotHashMismatchError,
)

__all__ = [
    "build_snapshot",
    "compute_snapshot_hash",
    "SnapshotEvidenceItem",
    "SnapshotBuildError",
    "SnapshotExistsError",
    "BUILDER_VERSION",
    "load_snapshot",
    "SnapshotNotFoundError",
    "SnapshotIncompleteError",
    "SnapshotHashMismatchError",
]
