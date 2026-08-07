"""P9-T3: Source allowlist (final_plan §12.3, Phase A criterion 1).

Only registered sources may contribute external evidence. An unregistered
source is a reference violation (``UnknownReferenceError`` subtype, matching
the ADR-0002 error-typing convention) and is rejected fail-closed.
"""
from __future__ import annotations

from reaction_agent.schemas.errors import UnknownReferenceError
from reaction_agent.p9.external.schemas import (
    ExternalEvidenceSource,
    SourceEntry,
)


class UnregisteredSourceError(UnknownReferenceError):
    """Raised when evidence cites a source that is not on the allowlist."""


class SourceAllowlist:
    """Registry of registered external evidence sources.

    Immutable entries: ``register`` snapshots the source into a frozen
    ``SourceEntry``; ``require`` returns the entry or raises
    ``UnregisteredSourceError``.
    """

    def __init__(self) -> None:
        self._entries: dict[str, SourceEntry] = {}

    def register(self, source: ExternalEvidenceSource) -> None:
        if source.source_id in self._entries:
            raise ValueError(f"source already registered: {source.source_id}")
        self._entries[source.source_id] = SourceEntry(
            source_id=source.source_id,
            source_name=source.source_name,
            license=source.license,
            source_version=source.source_version,
            homepage=source.homepage,
        )

    def is_registered(self, source_id: str) -> bool:
        return source_id in self._entries

    def require(self, source_id: str) -> SourceEntry:
        if source_id not in self._entries:
            raise UnregisteredSourceError(f"unregistered source: {source_id}")
        return self._entries[source_id]

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._entries