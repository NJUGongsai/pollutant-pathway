"""P9-T3: External evidence cache (final_plan §12.3, Phase A criterion 3).

Cache keyed by (source_id, content_hash). A cache hit returns the same record
with its original date/version stamp (reproducibility). A different content
hash is a distinct entry — never a silent overwrite. Unknown keys return None.
"""
from __future__ import annotations

from dataclasses import dataclass

from reaction_agent.p9.external.schemas import ExternalEvidenceRecord


@dataclass(frozen=True)
class CacheKey:
    """Cache key: source identity + content hash (uniquely identifies content)."""

    source_id: str
    content_hash: str


class EvidenceCache:
    """In-memory immutable cache of external evidence records.

    ``put`` is put-if-absent: a key that already exists is never overwritten
    (the original record with its date/version stamp is preserved). A different
    content hash is a distinct key — never a silent overwrite. Unknown keys
    return None.
    """

    def __init__(self) -> None:
        self._entries: dict[CacheKey, ExternalEvidenceRecord] = {}

    def put(self, record: ExternalEvidenceRecord) -> ExternalEvidenceRecord | None:
        """Insert or return existing. Never overwrites an existing entry.

        Returns the existing record if the key is already present, or None
        if this was a fresh insert (caller can distinguish).
        """
        key = CacheKey(
            source_id=record.source_id,
            content_hash=record.provenance.content_hash,
        )
        # Put-if-absent: preserve the original record and its date/version stamp.
        existing = self._entries.get(key)
        if existing is not None:
            return existing
        # Distinct content hash is a distinct key — never a silent overwrite of
        # the same content_hash (a different content_hash is a different key).
        self._entries[key] = record
        return None

    def get(self, key: CacheKey) -> ExternalEvidenceRecord | None:
        return self._entries.get(key)

    def has_evidence_id(self, evidence_id: str) -> bool:
        """Check if an evidence_id exists in the cache (P9D-R1-01)."""
        return any(r.evidence_id == evidence_id for r in self._entries.values())

    def __len__(self) -> int:
        return len(self._entries)