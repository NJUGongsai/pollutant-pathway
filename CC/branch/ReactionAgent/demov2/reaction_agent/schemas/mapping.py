"""Atom mapping report schema (final_design §8, ADR-0003).

Key principle: formal mapping ≠ mechanistic origin.
Generic mappers provide formal correspondence ONLY.
Mechanistic atom origin requires independent evidence.

Section 10: the typed object is the authoritative source of truth; flat
fields are derived for backward-compatible output and must not contradict
the typed object when explicitly provided.
- formal_mapped_source_assignment (typed object, authoritative)
- mechanistic_atom_origin (typed object, requires evidence)
- source_assignment_method / quality / ambiguity (flat, derived from typed)
- mechanistic_origin_evidence_ids (flat, derived from typed)

Section 11: atom pairs are typed skeletons (FormalMappedAtomPair,
MechanisticAtomPair), not arbitrary dict.

Section 12 (ADR-0003): unbound mechanistic evidence is prohibited —
mechanistic_origin_evidence_ids non-empty requires mechanistic_atom_origin.
"""

from pydantic import field_validator, model_validator
from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    MappingStatus,
    MappingQualityClass,
    SourceAssignmentMethod,
)


# -- Typed atom pair skeletons (Section 11) --

class FormalMappedAtomPair(StrictModel):
    """Typed formal atom correspondence pair (Section 11).

    Replaces arbitrary dict. Formal mapping only — NOT mechanistic evidence.
    """
    reactant_participant_id: NonEmptyStr
    reactant_atom_map: int
    product_participant_id: NonEmptyStr
    product_atom_map: int


class MechanisticAtomPair(StrictModel):
    """Typed mechanistic atom origin pair (Section 11).

    Replaces arbitrary dict. Must reference an existing mechanistic evidence
    ID declared on the enclosing MechanisticAtomOrigin.
    """
    source_participant_id: NonEmptyStr
    source_atom_identifier: int
    target_participant_id: NonEmptyStr
    target_atom_identifier: int
    evidence_id: NonEmptyStr


class FormalSourceAssignment(StrictModel):
    """Formal atom-to-atom correspondence from a mapper.
    This is NOT mechanistic evidence."""
    mapper_name: NonEmptyStr
    mapper_version: NonEmptyStr
    mapped_atom_pairs: list[FormalMappedAtomPair] = []
    assignment_method: SourceAssignmentMethod = SourceAssignmentMethod.unknown
    assignment_quality: MappingQualityClass = MappingQualityClass.unknown
    assignment_ambiguity: bool = False


class MechanisticAtomOrigin(StrictModel):
    """Experimentally proven mechanistic atom origin.
    Requires independent evidence IDs (isotope tracing, curated mapping).
    A generic mapper MUST NOT auto-populate this."""
    evidence_ids: list[NonEmptyStr]  # at least 1 required
    evidence_type: NonEmptyStr  # e.g. "isotope_tracing", "curated_mechanism"
    mechanistic_atom_pairs: list[MechanisticAtomPair] = []
    provenance: list[NonEmptyStr] = []

    @field_validator("evidence_ids")
    @classmethod
    def require_at_least_one_evidence_id(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("mechanistic_atom_origin requires at least 1 evidence ID")
        return v

    @model_validator(mode="after")
    def validate_pair_evidence_ids(self) -> "MechanisticAtomOrigin":
        """Section 11: each mechanistic_atom_pair must reference a declared evidence ID."""
        valid_ids = set(self.evidence_ids)
        for pair in self.mechanistic_atom_pairs:
            if pair.evidence_id not in valid_ids:
                raise ValueError(
                    f"mechanistic_atom_pair references unknown evidence_id: "
                    f"{pair.evidence_id}"
                )
        return self


class MappingReport(StrictModel):
    """Atom mapping report for a reaction.

    formal and mechanistic are separate typed objects (authoritative).
    Flat fields are derived from typed objects for backward-compatible output
    and must not contradict them (Section 10).
    Default: mechanistic_origin is None (mapper does NOT produce it).

    Section 12 (ADR-0003): unbound mechanistic evidence is prohibited —
    mechanistic_origin_evidence_ids non-empty requires mechanistic_atom_origin.
    """
    mapper_name: NonEmptyStr
    mapper_version: NonEmptyStr
    mapper_parameters: dict[str, str] = {}
    input_hash: NonEmptyStr
    output_hash: NonEmptyStr
    mapping_status: MappingStatus
    mapped_heavy_atom_fraction: float
    map_number_uniqueness: bool
    changed_atom_coverage: float

    # Formal assignment (always present from mapper)
    formal_mapped_source_assignment: FormalSourceAssignment | None = None

    # Mechanistic origin (NEVER auto-populated by mapper)
    mechanistic_atom_origin: MechanisticAtomOrigin | None = None

    # Legacy flat fields (derived from typed objects; must be consistent if
    # explicitly provided — Section 10)
    source_assignment_method: SourceAssignmentMethod = SourceAssignmentMethod.unknown
    source_assignment_quality: MappingQualityClass = MappingQualityClass.unknown
    source_assignment_ambiguity: bool = False
    mechanistic_origin_evidence_ids: list[NonEmptyStr] = []

    fallback_method: str | None = None
    quality_flags: list[NonEmptyStr] = []

    symmetry_ambiguity: bool = False
    resonance_tautomer_ambiguity: bool = False

    @field_validator("mapped_heavy_atom_fraction", "changed_atom_coverage")
    @classmethod
    def fraction_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Fraction must be in [0, 1], got {v}")
        return v

    @model_validator(mode="after")
    def enforce_formal_mechanistic_separation(self) -> "MappingReport":
        """Sections 10/12: typed/flat consistency, derivation, no unbound evidence."""

        fields_set = self.model_fields_set

        # -- Section 12: unbound evidence prohibited (ADR-0003) --
        if ("mechanistic_origin_evidence_ids" in fields_set
                and self.mechanistic_origin_evidence_ids
                and self.mechanistic_atom_origin is None):
            raise ValueError(
                "mechanistic_origin_evidence_ids is non-empty but mechanistic_atom_origin "
                "is None. Unbound mechanistic evidence is prohibited (Section 12, ADR-0003). "
                "Provide mechanistic_atom_origin with matching evidence_ids."
            )

        # -- Section 10: typed/flat consistency + derivation (formal assignment) --
        if self.formal_mapped_source_assignment is not None:
            fma = self.formal_mapped_source_assignment
            if "source_assignment_method" in fields_set:
                if fma.assignment_method != self.source_assignment_method:
                    raise ValueError(
                        f"assignment_method conflict: typed={fma.assignment_method.value}, "
                        f"flat={self.source_assignment_method.value}"
                    )
            else:
                object.__setattr__(
                    self, "source_assignment_method", fma.assignment_method
                )
            if "source_assignment_quality" in fields_set:
                if fma.assignment_quality != self.source_assignment_quality:
                    raise ValueError(
                        f"assignment_quality conflict: typed={fma.assignment_quality.value}, "
                        f"flat={self.source_assignment_quality.value}"
                    )
            else:
                object.__setattr__(
                    self, "source_assignment_quality", fma.assignment_quality
                )
            if "source_assignment_ambiguity" in fields_set:
                if fma.assignment_ambiguity != self.source_assignment_ambiguity:
                    raise ValueError(
                        f"assignment_ambiguity conflict: typed={fma.assignment_ambiguity}, "
                        f"flat={self.source_assignment_ambiguity}"
                    )
            else:
                object.__setattr__(
                    self, "source_assignment_ambiguity", fma.assignment_ambiguity
                )

        # -- Section 10: typed/flat consistency + derivation (mechanistic evidence) --
        if self.mechanistic_atom_origin is not None:
            if "mechanistic_origin_evidence_ids" in fields_set:
                typed_ids = set(self.mechanistic_atom_origin.evidence_ids)
                flat_ids = set(self.mechanistic_origin_evidence_ids)
                if typed_ids != flat_ids:
                    raise ValueError(
                        f"mechanistic evidence IDs conflict: "
                        f"typed={sorted(typed_ids)}, flat={sorted(flat_ids)}"
                    )
            else:
                object.__setattr__(
                    self,
                    "mechanistic_origin_evidence_ids",
                    list(self.mechanistic_atom_origin.evidence_ids),
                )

        return self
