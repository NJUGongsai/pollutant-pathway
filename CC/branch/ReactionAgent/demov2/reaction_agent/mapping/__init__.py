"""P1-T4 Atom-mapping adapter package.

Implements the minimal AtomMapper Protocol (§10.1) + a deterministic
FakeAtomMapper for unit tests + a RealMapperAdapter skeleton for real
mapper integration. Formal mapping only — never auto-generates mechanistic
evidence (§10.4). MCS/center-pair fallback downgrades status (§10.5).
"""
from reaction_agent.mapping.base import AtomMapper
from reaction_agent.mapping.adapter import (
    FakeAtomMapper,
    RealMapperAdapter,
    compute_quality_flags,
)

__all__ = [
    "AtomMapper",
    "FakeAtomMapper",
    "RealMapperAdapter",
    "compute_quality_flags",
]
