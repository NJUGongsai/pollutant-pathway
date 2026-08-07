"""P9-T3: External evidence — allowlist, license/provenance, cache, conflict,
injection isolation, child-run separation, benchmark default off, lane isolation,
intake pipeline.

Public API:
- allowlist:    SourceAllowlist, UnregisteredSourceError
- schemas:      ExternalEvidenceSource, SourceEntry, EvidenceProvenance,
                ExternalEvidenceRecord
- cache:        CacheKey, EvidenceCache
- conflict:     ConflictResolution, ConflictPolicy, resolve_record_conflict
- injection:    InjectionScanResult, scan_content, assert_content_inert
- child_run:    ChildAugmentation, ExternalEvidenceAugmenter, FrozenParentError
- benchmark:    BenchmarkConfig, is_external_in_benchmark
- ingest:       IngestPipeline, IngestResult, IngestRejectionError
"""
from __future__ import annotations

from reaction_agent.p9.external.schemas import (
    ExternalEvidenceSource,
    SourceEntry,
    EvidenceProvenance,
    ExternalEvidenceRecord,
)
from reaction_agent.p9.external.allowlist import (
    SourceAllowlist,
    UnregisteredSourceError,
)
from reaction_agent.p9.external.cache import CacheKey, EvidenceCache
from reaction_agent.p9.external.conflict import (
    ConflictResolution,
    ConflictPolicy,
    resolve_record_conflict,
)
from reaction_agent.p9.external.injection import (
    InjectionScanResult,
    scan_content,
    assert_content_inert,
)
from reaction_agent.p9.external.child_run import (
    ChildAugmentation,
    ExternalEvidenceAugmenter,
    FrozenParentError,
)
from reaction_agent.p9.external.benchmark import (
    BenchmarkConfig,
    is_external_in_benchmark,
)
from reaction_agent.p9.external.ingest import (
    IngestPipeline,
    IngestResult,
    IngestRejectionError,
)

__all__ = [
    # schemas
    "ExternalEvidenceSource",
    "SourceEntry",
    "EvidenceProvenance",
    "ExternalEvidenceRecord",
    # allowlist
    "SourceAllowlist",
    "UnregisteredSourceError",
    # cache
    "CacheKey",
    "EvidenceCache",
    # conflict
    "ConflictResolution",
    "ConflictPolicy",
    "resolve_record_conflict",
    # injection
    "InjectionScanResult",
    "scan_content",
    "assert_content_inert",
    # child-run
    "ChildAugmentation",
    "ExternalEvidenceAugmenter",
    "FrozenParentError",
    # benchmark
    "BenchmarkConfig",
    "is_external_in_benchmark",
    # ingest
    "IngestPipeline",
    "IngestResult",
    "IngestRejectionError",
]