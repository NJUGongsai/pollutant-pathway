"""P4 evidence identity + dedup schemas (final_design §4.9, final_plan §7.1).

Independent evidence identity resolution:
- mirror rows, same-publication rows, same mapped reaction (mapper
  duplicate), and same donor-transform evidence from the same source lineage
  must NOT be counted as multiple independent support;
- duplicates may be merged but provenance must never be lost;
- a group is one independent support unit.

All identity strings are content-addressed (canonical_hash) so they are
recomputable and version-stable.
"""
from __future__ import annotations

from enum import Enum
from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class DedupDimension(str, Enum):
    """Evidence identity dimensions that can mark rows as the same evidence."""
    source_lineage = "source_lineage"
    database_mirror = "database_mirror"
    same_publication = "same_publication"
    same_normalized_reaction = "same_normalized_reaction"
    mapper_duplicate = "mapper_duplicate"
    same_donor_transform = "same_donor_transform"


class EvidenceIdentity(StrictModel):
    """Per-row resolved evidence identity.

    ``evidence_id``   — raw evidence ID as produced upstream (P1/P3).
    ``canonical_identity`` — content-addressed identity of the observation.
    ``independent_group_id`` — group this row belongs to after dedup; all
      rows that represent the same observation share one group id.
    ``dedup_dimensions`` — which dimensions tied this row to its group.
    ``duplicate_of`` — sibling evidence ids merged into the same group
      (provenance preserved, never deleted).
    """
    evidence_id: NonEmptyStr
    canonical_identity: NonEmptyStr
    independent_group_id: NonEmptyStr
    dedup_dimensions: list[DedupDimension] = []
    duplicate_of: list[NonEmptyStr] = []
    source_lineage: dict[str, str] = {}
    publication: str = ""
    normalized_reaction: str = ""
    donor_transform: dict[str, list[str]] = {}


class IndependentGroup(StrictModel):
    """One independent support unit (a set of deduplicated evidence rows)."""
    group_id: NonEmptyStr
    canonical_identity: NonEmptyStr
    member_evidence_ids: list[NonEmptyStr]
    dedup_dimensions: list[DedupDimension] = []
    is_independent: bool


class EvidenceIdentityResolution(StrictModel):
    """Full evidence identity/dedup resolution for an evidence context."""
    identities: list[EvidenceIdentity]
    groups: list[IndependentGroup]
    independent_count: int
    total_rows: int
    policy_version: NonEmptyStr
    resolution_hash: NonEmptyStr

    def group_ids_for(self, evidence_ids: list[str]) -> list[str]:
        """Distinct independent group ids covering ``evidence_ids`` (dedup)."""
        by_ev = {i.evidence_id: i.independent_group_id for i in self.identities}
        seen: list[str] = []
        for ev_id in evidence_ids:
            gid = by_ev.get(ev_id)
            if gid is not None and gid not in seen:
                seen.append(gid)
        return seen
