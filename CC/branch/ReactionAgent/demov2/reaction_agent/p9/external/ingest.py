"""P9-T3: External evidence intake pipeline (P9A-R1-01, Phase A criterion 1/5).

Single fail-closed entry point for ingesting external evidence records.
The pipeline enforces a deterministic ordering of checks:

1. **allowlist**: ``SourceAllowlist.require`` — unregistered source rejected.
2. **injection**: ``assert_content_inert`` — control directives in content rejected.
3. **license cross-check**: record.license must match the registered source entry.
4. **conflict**: ``resolve_record_conflict`` — snapshot-conflicting record suppressed.
5. **cache**: ``EvidenceCache.put`` — record cached (put-if-absent preserves original).

Each check is mandatory and in-order. No external evidence enters the system
without passing all applicable checks. Pipeline consumers receive a typed
``IngestResult`` describing the outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from reaction_agent.p9.external.schemas import ExternalEvidenceRecord
from reaction_agent.p9.external.allowlist import SourceAllowlist
from reaction_agent.p9.external.cache import EvidenceCache, CacheKey
from reaction_agent.p9.external.conflict import (
    ConflictResolution,
    resolve_record_conflict,
)
from reaction_agent.p9.external.injection import assert_content_inert


class IngestRejectionError(Exception):
    """Raised when an external evidence record is rejected during intake.

    Reasons include: unregistered source, injection payload, license mismatch,
    or other validation failure.
    """


@dataclass(frozen=True)
class IngestResult:
    """Result of ingesting a single external evidence record.

    ``resolution`` is one of:
    - ``"accepted"``: record passed all checks and was cached.
    - ``"snapshot_wins"``: record was suppressed due to snapshot conflict.
      The record is NOT cached.
    - ``"rejected"``: record was rejected (unregistered source, injection
      payload, license mismatch). Not cached. (Raised as ``IngestRejectionError``
      or ``UnregisteredSourceError`` — ``rejected`` is reserved for future use.)

    ``cache`` is the EvidenceCache instance for records that were accepted.
    ``suppressed`` is a convenience boolean.
    """

    resolution: str
    suppressed: bool
    cache: EvidenceCache | None = None


class IngestPipeline:
    """Single fail-closed intake pipeline for external evidence records.

    Usage::

        pipeline = IngestPipeline()
        result = pipeline.ingest(
            record=my_record,
            allowlist=my_allowlist,
            cache=my_cache,
            snapshot_content_hash_by_source={},
        )
    """

    def ingest(
        self,
        *,
        record: ExternalEvidenceRecord,
        allowlist: SourceAllowlist,
        cache: EvidenceCache,
        snapshot_content_hash_by_source: dict[str, str] | None = None,
    ) -> IngestResult:
        # Step 1: allowlist — unregistered source rejected
        entry = allowlist.require(record.source_id)

        # Step 2: injection scan — control directives rejected
        try:
            assert_content_inert(record.content)
        except ValueError as exc:
            raise IngestRejectionError(str(exc)) from exc

        # Step 3: license cross-check — record must match registered source
        if record.license != entry.license:
            raise IngestRejectionError(
                f"license mismatch: record has {record.license!r}, "
                f"registered source {entry.source_id} has {entry.license!r}"
            )

        # Step 4: conflict check — snapshot-conflicting record suppressed
        conflict = resolve_record_conflict(
            record, snapshot_content_hash_by_source or {}
        )
        if conflict.resolution == ConflictResolution.snapshot_wins:
            return IngestResult(
                resolution="snapshot_wins",
                suppressed=True,
                cache=cache,
            )

        # Step 5: cache — put-if-absent preserves original
        cache.put(record)

        return IngestResult(
            resolution="accepted",
            suppressed=False,
            cache=cache,
        )