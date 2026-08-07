"""P9-T3 RED tests — External evidence record: license/provenance + cache + date/version.

Phase A criteria 2-3: license/provenance metadata enforced; cache + date/version stamps.

- Every external evidence record must carry license + provenance (source_version,
  retrieval_date, content_hash). Records without them are rejected.
- Cache keyed by (source_id, content_hash); a cache hit returns the same record
  with its original date/version stamp (reproducibility). A newer content hash
  for the same source is a distinct entry (no silent overwrite).
"""
from __future__ import annotations

import pytest

from reaction_agent.p9.external.schemas import (
    ExternalEvidenceSource,
    ExternalEvidenceRecord,
    EvidenceProvenance,
)
from reaction_agent.p9.external.cache import EvidenceCache, CacheKey


def make_source() -> ExternalEvidenceSource:
    return ExternalEvidenceSource(
        source_id="chemrxiv-2024",
        source_name="ChemRxiv 2024",
        license="CC-BY-4.0",
        source_version="2024.1",
        homepage="https://chemrxiv.org",
    )


def make_provenance(**over) -> EvidenceProvenance:
    base = dict(
        source_version="2024.1",
        retrieval_date="2026-08-01",
        content_hash="abc123",
    )
    base.update(over)
    return EvidenceProvenance(**base)


def make_record(**over) -> ExternalEvidenceRecord:
    base = dict(
        evidence_id="ext-1",
        source_id="chemrxiv-2024",
        license="CC-BY-4.0",
        provenance=make_provenance(),
        content="reaction A -> B proceeds with 90% yield",
    )
    # route content_hash into provenance (it is a provenance field)
    if "content_hash" in over:
        ch = over.pop("content_hash")
        base["provenance"] = make_provenance(content_hash=ch)
    base.update(over)
    return ExternalEvidenceRecord(**base)


def test_record_requires_license() -> None:
    with pytest.raises(Exception):
        make_record(license="")


def test_record_requires_provenance() -> None:
    with pytest.raises(Exception):
        make_record(provenance=None)


def test_record_requires_content_hash_in_provenance() -> None:
    with pytest.raises(Exception):
        make_record(provenance=make_provenance(content_hash=""))


def test_record_requires_retrieval_date_in_provenance() -> None:
    with pytest.raises(Exception):
        make_record(provenance=make_provenance(retrieval_date=""))


def test_cache_put_and_get_roundtrip() -> None:
    cache = EvidenceCache()
    rec = make_record()
    cache.put(rec)
    got = cache.get(CacheKey(source_id="chemrxiv-2024", content_hash="abc123"))
    assert got is not None
    assert got.evidence_id == "ext-1"


def test_cache_hit_preserves_date_version_stamp() -> None:
    cache = EvidenceCache()
    rec = make_record(
        provenance=make_provenance(retrieval_date="2026-08-01")
    )
    cache.put(rec)
    got = cache.get(CacheKey(source_id="chemrxiv-2024", content_hash="abc123"))
    assert got.provenance.retrieval_date == "2026-08-01"
    assert got.provenance.source_version == "2024.1"


def test_cache_miss_returns_none() -> None:
    cache = EvidenceCache()
    assert cache.get(CacheKey(source_id="x", content_hash="y")) is None


def test_different_content_hash_is_distinct_entry() -> None:
    cache = EvidenceCache()
    cache.put(make_record(content_hash="abc123"))
    cache.put(
        make_record(
            evidence_id="ext-2",
            provenance=make_provenance(content_hash="def456"),
        )
    )
    first = cache.get(CacheKey(source_id="chemrxiv-2024", content_hash="abc123"))
    second = cache.get(CacheKey(source_id="chemrxiv-2024", content_hash="def456"))
    assert first is not None and second is not None
    assert first.evidence_id == "ext-1"
    assert second.evidence_id == "ext-2"


def test_cache_key_is_hashable() -> None:
    k = CacheKey(source_id="chemrxiv-2024", content_hash="abc123")
    d = {k: 1}
    assert d[k] == 1


def test_unknown_fields_rejected() -> None:
    """StrictModel: extra='forbid' — an injected field is rejected (injection guard)."""
    with pytest.raises(Exception):
        make_record(injected_field="nope")