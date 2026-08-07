"""P9-T3: External evidence schemas (final_plan §12.3, ADR-0006, final_design §22).

External evidence is a post-hoc, append-only augmentation source. It is
strictly isolated from the strict (P3-P6) channel and from the frozen primary
run. Every record:

- carries a source allowlist entry (source_id / license / version);
- carries license + provenance metadata (source_version, retrieval_date,
  content_hash) — mandatory, no empty provenance;
- pins ``lane = "external"`` so it can never be promoted into the strict lane;
- is a StrictModel (extra='forbid') — unknown fields cannot be injected.

Hard boundary (strict untouched): this module only ADDS new p9 code. It does
not modify the strict channel, the shared hypothesis union, or the P4 run
store. It reuses ``schemas.common.StrictModel`` for strict typing.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class ExternalEvidenceSource(StrictModel):
    """A registered external evidence source (allowlist entry).

    ``license`` and ``source_version`` are mandatory: external evidence without
    a license / version cannot be trusted for provenance (Phase A criterion 2).
    """

    source_id: NonEmptyStr
    source_name: NonEmptyStr
    license: NonEmptyStr
    source_version: NonEmptyStr
    homepage: NonEmptyStr

    @field_validator("license")
    @classmethod
    def _license_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("license must not be empty")
        return v


class SourceEntry(StrictModel):
    """A frozen allowlist entry (immutable copy of a source at registration)."""

    source_id: NonEmptyStr
    source_name: NonEmptyStr
    license: NonEmptyStr
    source_version: NonEmptyStr
    homepage: NonEmptyStr


class EvidenceProvenance(StrictModel):
    """Provenance + cache stamp for an external evidence record.

    ``content_hash`` uniquely identifies the retrieved content; ``retrieval_date``
    is the date/version stamp used for cache keying and reproducibility (Phase A
    criterion 3).
    """

    source_version: NonEmptyStr
    retrieval_date: NonEmptyStr
    content_hash: NonEmptyStr

    @field_validator("content_hash")
    @classmethod
    def _content_hash_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content_hash must not be empty")
        return v

    @field_validator("retrieval_date")
    @classmethod
    def _date_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("retrieval_date must not be empty")
        return v


class ExternalEvidenceRecord(StrictModel):
    """A single piece of external evidence (data, never instructions).

    ``lane`` is pinned to "external" (Literal) so no external output can claim a
    strict-lane validation or be promoted into the strict candidate set (Phase A
    criterion 8). ``content`` is treated strictly as DATA by the injection
    scanner (``reaction_agent.p9.external.injection``) — see criterion 5.
    """

    evidence_id: NonEmptyStr
    source_id: NonEmptyStr
    license: NonEmptyStr
    provenance: EvidenceProvenance
    content: NonEmptyStr
    lane: Literal["external"] = "external"

    @field_validator("license")
    @classmethod
    def _license_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("license must not be empty")
        return v