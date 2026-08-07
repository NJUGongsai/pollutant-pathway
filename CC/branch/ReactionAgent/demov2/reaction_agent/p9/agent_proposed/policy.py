"""P9-T1: Frozen validation-chain policy for the agent_proposed lane
(final_plan §12.1, final_design §19.2, ADR-0002).

Pins the eight-step validation chain version + step order, and exposes a
content hash so a validated candidate's record names the exact chain artifact
it was validated against (R1-04 trace pattern, mirroring P8's
``GeneralizedValidation.policy_content_hash``).

The agent_proposed lane is a physically isolated, exploratory, NON-production
lane. This module only ADDS new files; it never imports or modifies the strict
channel (P3-P6), the shared hypothesis union, P7, or P8.
"""
from __future__ import annotations

import re

from pydantic import ConfigDict, Field, field_validator, model_validator

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import NonEmptyStr, StrictModel


# ---------------------------------------------------------------------------
# The frozen eight-step validation chain (final_design §19.2)
# ---------------------------------------------------------------------------

CHAIN_STEPS: list[str] = [
    "support_validation",
    "registered_vocabulary",
    "compiler",
    "site_validation",
    "graph_edit",
    "molecule_validation",
    "dual_ledger_validation",
    "grounding_validation",
]

#: Names burned into the validation record AFTER the chain passes (mirrors P8
#: ``VALIDATED_CHECKS``). Order matches ``CHAIN_STEPS``.
CHAIN_CHECK_NAMES: list[str] = list(CHAIN_STEPS)


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _validate_semver(v: str) -> str:
    """Strict semver ``X.Y.Z`` (no prerelease/build tokens)."""
    if not _SEMVER_RE.match(v):
        raise ValueError(f"version must be semver X.Y.Z, got {v!r}")
    return v


# ---------------------------------------------------------------------------
# Frozen chain policy artifact (immutable, content-hashed)
# ---------------------------------------------------------------------------


class AgentProposedChainPolicy(StrictModel):
    """Frozen validation-chain policy for the agent_proposed lane.

    ``policy_id`` is the stable logical identity; ``version`` is semver; the
    ``chain_steps`` order is frozen (a reordered/extended chain is a different
    policy and must bump ``version``). ``content_hash`` fingerprints the exact
    chain artifact so a consumer never trusts an embedded validation status
    without the matching fingerprint (R1-04 trace).
    """

    model_config = ConfigDict(**StrictModel.model_config, frozen=True)

    policy_id: NonEmptyStr = "agent_proposed_validation_chain"
    version: NonEmptyStr
    chain_steps: list[NonEmptyStr]
    content_hash: NonEmptyStr

    @field_validator("version")
    @classmethod
    def _semver_version(cls, v: str) -> str:
        return _validate_semver(v)

    @model_validator(mode="after")
    def _verify_chain_steps(self) -> "AgentProposedChainPolicy":
        if list(self.chain_steps) != CHAIN_STEPS:
            raise ValueError(
                f"chain_steps must equal the frozen 8-step chain "
                f"{CHAIN_STEPS}, got {list(self.chain_steps)}"
            )
        return self

    @model_validator(mode="after")
    def _verify_content_hash(self) -> "AgentProposedChainPolicy":
        body = self.model_dump(exclude={"content_hash"})
        recomputed = canonical_hash(body)
        if self.content_hash != recomputed:
            raise ValueError(
                f"content_hash mismatch: expected {recomputed}, got {self.content_hash}"
            )
        return self

    @classmethod
    def create(cls, *, version: str = "1.0.0") -> "AgentProposedChainPolicy":
        """Build a policy, computing its content_hash over the frozen body."""
        body = {
            "policy_id": "agent_proposed_validation_chain",
            "version": _validate_semver(version),
            "chain_steps": list(CHAIN_STEPS),
        }
        return cls(**body, content_hash=canonical_hash(body))


#: The default frozen chain policy agents validate against.
DEFAULT_AGENT_PROPOSED_CHAIN_POLICY = AgentProposedChainPolicy.create(version="1.0.0")


__all__ = [
    "CHAIN_STEPS",
    "CHAIN_CHECK_NAMES",
    "AgentProposedChainPolicy",
    "DEFAULT_AGENT_PROPOSED_CHAIN_POLICY",
]
