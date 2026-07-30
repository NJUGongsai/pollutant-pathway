"""AtomMapper protocol (chatgpt_p1_train.md §10.1).

Minimal Protocol: any mapper (fake or real) must implement ``map_reaction``
which consumes a NormalizedReactionRecord and produces a MappingReport.

The Protocol captures the §10.1 capture list via the MappingReport fields:
- mapper_name / mapper_version / mapper_parameters (typed)
- input_hash / output_hash (content-addressed)
- mapping_status (§10.2 frozen vocabulary)
- quality_flags (§10.3 dimensions)
- fallback_method (§10.5 — MCS/center-pair must be explicit)

§10.4 invariant: a generic mapper produces formal_mapped_source_assignment
ONLY. It must never auto-populate mechanistic_atom_origin — that requires
independent curated/isotope/mechanistic evidence.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from reaction_agent.schemas.mapping import MappingReport
from reaction_agent.schemas.p1_entities import NormalizedReactionRecord


@runtime_checkable
class AtomMapper(Protocol):
    """Atom-mapping adapter protocol (§10.1).

    Implementations MUST:
    - Capture mapper_name, mapper_version, mapper_parameters, input_hash,
      output_hash, mapping_status, quality_flags, fallback_method in the
      returned MappingReport (§10.1 capture list).
    - Produce formal_mapped_source_assignment ONLY (§10.4). Never
      auto-populate mechanistic_atom_origin.
    - Downgrade mapping_status when fallback_method is MCS/center-pair (§10.5).
    - Use the §10.2 frozen MappingStatus vocabulary.
    """

    def map_reaction(self, reaction: NormalizedReactionRecord) -> MappingReport:
        """Map atoms for a normalized reaction record.

        Args:
            reaction: NormalizedReactionRecord with normalized_reaction SMILES.

        Returns:
            MappingReport with formal atom mapping. Never includes
            mechanistic_atom_origin (§10.4).
        """
        ...
