"""P9-T3 RED tests — Benchmark default off + lane non-contamination.

Phase A criteria 7-8:
7. benchmark default off — external evidence is NOT included in the default
   benchmark; it must be explicitly enabled.
8. lane non-contamination — external evidence never changes the strict lane's
   candidate set / ranking; it remains an isolated augmentation lane.
"""
from __future__ import annotations

import pytest

from reaction_agent.p9.external.benchmark import (
    BenchmarkConfig,
    is_external_in_benchmark,
)
from reaction_agent.p9.external.schemas import ExternalEvidenceRecord, EvidenceProvenance


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


def test_external_benchmark_default_off() -> None:
    cfg = BenchmarkConfig()
    assert cfg.include_external is False


def test_is_external_in_benchmark_default_false() -> None:
    assert is_external_in_benchmark(BenchmarkConfig()) is False


def test_explicitly_enabled() -> None:
    cfg = BenchmarkConfig(include_external=True)
    assert is_external_in_benchmark(cfg) is True


def test_strict_benchmark_never_pulls_external() -> None:
    """A strict benchmark (no external flag) excludes external evidence even if
    records exist."""
    cfg = BenchmarkConfig(include_external=False)
    records = [make_record()]
    included = [r for r in records if is_external_in_benchmark(cfg)]
    # external records are included only when the flag is on
    assert included == []


def test_lane_non_contamination_property() -> None:
    """External evidence carries a fixed 'external' lane; it can never be
    promoted into the strict lane's candidate set."""
    rec = make_record()
    assert rec.lane == "external"
    from reaction_agent.schemas.common import Lane
    # the strict lane is a distinct value; a record cannot be both
    assert rec.lane != Lane.strict.value