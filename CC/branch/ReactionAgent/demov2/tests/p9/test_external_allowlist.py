"""P9-T3 RED tests — External evidence source allowlist (final_plan §12.3).

Phase A criterion 1: source allowlist — unregistered source rejected.
"""
from __future__ import annotations

import pytest

from reaction_agent.p9.external.schemas import (
    ExternalEvidenceSource,
    SourceEntry,
)
from reaction_agent.p9.external.allowlist import (
    SourceAllowlist,
    UnregisteredSourceError,
)
from reaction_agent.schemas.errors import UnknownReferenceError


def make_source(source_id: str = "chemrxiv-2024") -> ExternalEvidenceSource:
    return ExternalEvidenceSource(
        source_id=source_id,
        source_name="ChemRxiv 2024",
        license="CC-BY-4.0",
        source_version="2024.1",
        homepage="https://chemrxiv.org",
    )


def test_register_and_require_registered_source() -> None:
    al = SourceAllowlist()
    al.register(make_source())
    assert al.is_registered("chemrxiv-2024")
    entry = al.require("chemrxiv-2024")
    assert isinstance(entry, SourceEntry)
    assert entry.license == "CC-BY-4.0"


def test_unregistered_source_rejected() -> None:
    al = SourceAllowlist()
    with pytest.raises(UnregisteredSourceError):
        al.require("unregistered-source")


def test_unregistered_source_requires_unknown_reference_type() -> None:
    """Unregistered source is a reference violation (ADR-0002 style typing)."""
    al = SourceAllowlist()
    with pytest.raises(UnknownReferenceError):
        al.require("nope")


def test_duplicate_register_rejected() -> None:
    al = SourceAllowlist()
    al.register(make_source())
    with pytest.raises(ValueError):
        al.register(make_source())


def test_allowlist_requires_license_and_version_on_source() -> None:
    # Missing license should fail schema validation (strict).
    with pytest.raises(Exception):
        ExternalEvidenceSource(
            source_id="s",
            source_name="S",
            license="",
            source_version="1.0",
            homepage="https://x",
        )