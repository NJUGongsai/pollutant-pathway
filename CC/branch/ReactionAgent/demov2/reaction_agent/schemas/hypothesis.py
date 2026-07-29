"""Hypothesis schemas with strict lane separation and typed targets.

Two lanes, enforced by discriminated union on hypothesis_origin:
1. ProductionSelectionHypothesis (evidence-space selection only)
2. AgentProposedHypothesis (novel T/S, separate lane)

Typed atom/bond target: discriminated union of AtomTarget and BondTarget.
Reference validation via HypothesisReferenceRegistry.
"""

from typing import Annotated, Literal, Union
from pydantic import Field, Discriminator, Tag, field_validator, model_validator
from reaction_agent.schemas.common import StrictModel, NonEmptyStr, TargetKind
from reaction_agent.schemas.errors import UnknownReferenceError


# -- Typed atom/bond targets --

class AtomTarget(StrictModel):
    """Atom target: strict integer atom_id."""
    kind: Literal["atom"] = "atom"
    atom_id: int

    @field_validator("atom_id")
    @classmethod
    def atom_id_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"atom_id must be non-negative, got {v}")
        return v


class BondTarget(StrictModel):
    """Bond target: strict integer begin/end atom IDs; endpoints must differ."""
    kind: Literal["bond"] = "bond"
    begin_atom_id: int
    end_atom_id: int

    @field_validator("begin_atom_id", "end_atom_id")
    @classmethod
    def bond_atom_id_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"bond atom ID must be non-negative, got {v}")
        return v

    @model_validator(mode="after")
    def begin_neq_end(self) -> "BondTarget":
        if self.begin_atom_id == self.end_atom_id:
            raise ValueError(
                f"begin_atom_id and end_atom_id must differ "
                f"(both were {self.begin_atom_id})"
            )
        return self


def _get_target_discriminator(v):
    if isinstance(v, dict):
        return v.get("kind")
    return getattr(v, "kind", None)


TypedTarget = Annotated[
    Union[
        Annotated[AtomTarget, Tag("atom")],
        Annotated[BondTarget, Tag("bond")],
    ],
    Discriminator(_get_target_discriminator),
]


# -- Base hypothesis fields --

class TransformationHypothesis(StrictModel):
    """Transformation hypothesis derived from mapped lineage."""
    transformation_id: NonEmptyStr
    source_lineage_ids: list[NonEmptyStr] = []
    family_id: NonEmptyStr = "unknown"
    mapped_atom_edits: list[dict[str, int]] = []
    bond_deletions: list[dict[str, int]] = []
    bond_additions: list[dict[str, int]] = []
    bond_order_changes: list[dict[str, int]] = []
    atom_attribute_changes: list[dict[str, int]] = []
    transferred_atoms: list[dict[str, int]] = []
    donor_site: dict[str, str] = {}
    local_environment: dict[str, str] = {}
    strict_preconditions: list[dict[str, str]] = []
    allowed_relaxation_ids: list[NonEmptyStr] = []
    ledger_requirements: list[dict[str, str]] = []
    mapping_quality: float = 0.0
    canonical_transform_hash: NonEmptyStr = "pending"


class SiteHypothesis(StrictModel):
    """Transformation-conditioned site hypothesis."""
    site_id: NonEmptyStr
    query_atom_ids: list[int] = []
    query_bond_ids: list[int] = []
    transformation_id: NonEmptyStr
    matched_preconditions: list[dict[str, str]] = []
    failed_preconditions: list[dict[str, str]] = []
    local_environment_similarity: float = 0.0
    symmetry_class: int = 0
    ambiguity_group: str | None = None
    eligibility: bool = False


# -- Reference registry --

class HypothesisReferenceRegistry(StrictModel):
    """Reference registry with relation integrity (Section 6).

    P0 does not implement a database. This is a typed context object that
    holds known IDs AND their relations for validation purposes.

    Relation maps are part of the typed context. The validator requires
    relation evidence for the IDs a hypothesis cites; missing relation
    evidence is a rejection, not a skip.
    """
    # ID sets (existence)
    reaction_ids: frozenset[str] = frozenset()
    lineage_ids: frozenset[str] = frozenset()
    transformation_ids: frozenset[str] = frozenset()
    site_ids: frozenset[str] = frozenset()
    transformation_family_ids: frozenset[str] = frozenset()
    relaxation_policy_ids: frozenset[str] = frozenset()
    relaxation_ids: frozenset[str] = frozenset()
    source_ledger_ids: frozenset[str] = frozenset()

    # Relation maps (integrity) — fail-closed: missing evidence is a rejection
    lineage_to_reaction_id: dict[str, str] = {}
    transformation_to_lineage_ids: dict[str, list[str]] = {}
    site_to_transformation_id: dict[str, str] = {}
    relaxation_policy_to_allowed_ids: dict[str, list[str]] = {}
    source_ledger_to_reaction_id: dict[str, str] = {}

    @model_validator(mode="after")
    def _validate_relation_consistency(self) -> "HypothesisReferenceRegistry":
        """Validate every relation map's keys/values belong to the corresponding ID sets."""
        errors: list[str] = []
        for lid, rid in self.lineage_to_reaction_id.items():
            if lid not in self.lineage_ids:
                errors.append(f"lineage_to_reaction_id key {lid} not in lineage_ids")
            if rid not in self.reaction_ids:
                errors.append(f"lineage_to_reaction_id[{lid}] value {rid} not in reaction_ids")
        for tid, lids in self.transformation_to_lineage_ids.items():
            if tid not in self.transformation_ids:
                errors.append(f"transformation_to_lineage_ids key {tid} not in transformation_ids")
            for lid in lids:
                if lid not in self.lineage_ids:
                    errors.append(f"transformation_to_lineage_ids[{tid}] value {lid} not in lineage_ids")
        for sid, tid in self.site_to_transformation_id.items():
            if sid not in self.site_ids:
                errors.append(f"site_to_transformation_id key {sid} not in site_ids")
            if tid not in self.transformation_ids:
                errors.append(f"site_to_transformation_id[{sid}] value {tid} not in transformation_ids")
        for pid, rids in self.relaxation_policy_to_allowed_ids.items():
            if pid not in self.relaxation_policy_ids:
                errors.append(f"relaxation_policy_to_allowed_ids key {pid} not in relaxation_policy_ids")
            for rid in rids:
                if rid not in self.relaxation_ids:
                    errors.append(f"relaxation_policy_to_allowed_ids[{pid}] value {rid} not in relaxation_ids")
        for slid, rid in self.source_ledger_to_reaction_id.items():
            if slid not in self.source_ledger_ids:
                errors.append(f"source_ledger_to_reaction_id key {slid} not in source_ledger_ids")
            if rid not in self.reaction_ids:
                errors.append(f"source_ledger_to_reaction_id[{slid}] value {rid} not in reaction_ids")
        if errors:
            raise ValueError("; ".join(errors))
        return self


# -- Production selection hypothesis --

class ProductionSelectionHypothesis(StrictModel):
    """Production lane: LLM selects within evidence-derived space.

    All IDs must reference kernel-generated entities in the registry.
    NO relaxation fields allowed on production selection.
    """
    hypothesis_id: NonEmptyStr
    hypothesis_origin: Literal["agent_selected_from_evidence_space"] = "agent_selected_from_evidence_space"
    support_reaction_ids: list[NonEmptyStr] = []
    support_lineage_ids: list[NonEmptyStr] = []
    transformation_id: NonEmptyStr
    site_id: NonEmptyStr
    rationale_summary: NonEmptyStr = "none"
    policy_version: NonEmptyStr = "0.0.0"


# -- Agent proposed hypothesis --

class AgentProposedHypothesis(StrictModel):
    """Agent-proposed lane: novel T/S from LLM.

    Must pass full validation chain before receiving candidate_id.
    Uses typed targets (AtomTarget/BondTarget), not free text.
    Relaxation IDs must exist in registry.
    """
    hypothesis_id: NonEmptyStr
    hypothesis_origin: Literal["agent_proposed"] = "agent_proposed"
    support_reaction_ids: list[NonEmptyStr] = []
    support_lineage_ids: list[NonEmptyStr] = []
    transformation_family_id: NonEmptyStr
    typed_target_atom_or_bond_set: list[TypedTarget] = []
    relaxation_policy_id: str | None = None
    allowed_relaxation_ids: list[NonEmptyStr] = []
    rationale_summary: NonEmptyStr = "none"
    policy_version: NonEmptyStr = "0.0.0"

    @field_validator("typed_target_atom_or_bond_set")
    @classmethod
    def require_non_empty_target_set(cls, v: list) -> list:
        if not v:
            raise ValueError("typed_target_atom_or_bond_set must not be empty")
        return v


# -- Reference validation function --

def validate_hypothesis_references(
    hypothesis: Union[ProductionSelectionHypothesis, AgentProposedHypothesis],
    registry: HypothesisReferenceRegistry,
) -> None:
    """Validate all ID references AND relations in a hypothesis.

    Raises UnknownReferenceError for:
    - any ID not found in registry (existence)
    - any missing relation evidence or relation violation (integrity)

    Missing relation coverage is a rejection, not a skip.
    """
    errors: list[str] = []

    # -- ID existence (shared by both lanes) --
    for rid in hypothesis.support_reaction_ids:
        if rid not in registry.reaction_ids:
            errors.append(f"unknown support_reaction_id: {rid}")
    for lid in hypothesis.support_lineage_ids:
        if lid not in registry.lineage_ids:
            errors.append(f"unknown support_lineage_id: {lid}")

    if isinstance(hypothesis, ProductionSelectionHypothesis):
        # rule 1: support reactions non-empty
        if not hypothesis.support_reaction_ids:
            errors.append("support_reaction_ids must not be empty (production acceptance requires support reactions)")
        # rule 2: support lineages non-empty
        if not hypothesis.support_lineage_ids:
            errors.append("support_lineage_ids must not be empty (production acceptance requires support lineages)")
        # existence
        if hypothesis.transformation_id not in registry.transformation_ids:
            errors.append(f"unknown transformation_id: {hypothesis.transformation_id}")
        if hypothesis.site_id not in registry.site_ids:
            errors.append(f"unknown site_id: {hypothesis.site_id}")
        # rules 5,6: lineage -> reaction (fail-closed: missing mapping = error)
        for lid in hypothesis.support_lineage_ids:
            if lid not in registry.lineage_to_reaction_id:
                errors.append(f"lineage {lid} has no lineage_to_reaction_id mapping (relation evidence missing)")
            else:
                owner = registry.lineage_to_reaction_id[lid]
                if owner not in hypothesis.support_reaction_ids:
                    errors.append(f"lineage {lid} belongs to reaction {owner}, not in support_reaction_ids")
        # rules 8,9,10: transformation -> lineage (fail-closed)
        tid = hypothesis.transformation_id
        if tid not in registry.transformation_to_lineage_ids:
            errors.append(f"transformation {tid} has no transformation_to_lineage_ids mapping (relation evidence missing)")
        else:
            sources = set(registry.transformation_to_lineage_ids[tid])
            if not sources:
                errors.append(f"transformation {tid} has empty source lineage list")
            else:
                cited = set(hypothesis.support_lineage_ids)
                if not (sources & cited):
                    errors.append(f"transformation {tid} derives from {sorted(sources)}, none cited in support_lineage_ids {sorted(cited)}")
        # rules 12,13: site -> transformation (fail-closed)
        sid = hypothesis.site_id
        if sid not in registry.site_to_transformation_id:
            errors.append(f"site {sid} has no site_to_transformation_id mapping (relation evidence missing)")
        else:
            owner_t = registry.site_to_transformation_id[sid]
            if owner_t != hypothesis.transformation_id:
                errors.append(f"site {sid} belongs to transformation {owner_t}, not {hypothesis.transformation_id}")

    elif isinstance(hypothesis, AgentProposedHypothesis):
        if hypothesis.transformation_family_id not in registry.transformation_family_ids:
            errors.append(f"unknown transformation_family_id: {hypothesis.transformation_family_id}")
        allowed = hypothesis.allowed_relaxation_ids
        policy = hypothesis.relaxation_policy_id
        # allowed non-empty => policy non-null
        if allowed and policy is None:
            errors.append(f"allowed_relaxation_ids non-empty {allowed} but relaxation_policy_id is null")
        # policy non-null => policy exists + map covers it + each relaxation allowed under it
        if policy is not None:
            if policy not in registry.relaxation_policy_ids:
                errors.append(f"unknown relaxation_policy_id: {policy}")
            if policy not in registry.relaxation_policy_to_allowed_ids:
                errors.append(f"policy {policy} not covered by relaxation_policy_to_allowed_ids (relation evidence missing)")
            else:
                policy_allowed = set(registry.relaxation_policy_to_allowed_ids[policy])
                for rel_id in allowed:
                    if rel_id not in policy_allowed:
                        errors.append(f"relaxation {rel_id} not allowed under policy {policy}")
        # each relaxation globally exists
        for rel_id in allowed:
            if rel_id not in registry.relaxation_ids:
                errors.append(f"unknown allowed_relaxation_id: {rel_id}")

    if errors:
        raise UnknownReferenceError("; ".join(errors))


# -- Query-aware validation context (Section 6) --

class HypothesisValidationContext(StrictModel):
    """Full validation context: registry + query target context.

    Used by validate_hypothesis_against_context to additionally verify that
    atom/bond targets belong to the current query.

    Query context is three-state: None means "not provided" (a rejection when
    a target requires that context), frozenset() means "explicitly empty".
    """
    registry: HypothesisReferenceRegistry
    query_id: str | None = None
    query_atom_ids: frozenset[int] | None = None
    query_bond_pairs: frozenset[tuple[int, int]] | None = None
    candidate_ids: frozenset[str] = frozenset()


def validate_hypothesis_against_context(
    hypothesis: Union[ProductionSelectionHypothesis, AgentProposedHypothesis],
    context: HypothesisValidationContext,
) -> None:
    """Validate hypothesis against full context (registry relations + query targets).

    Raises UnknownReferenceError for relation violations or targets absent
    from the current query.
    """
    # First: ID existence + relation integrity via registry
    validate_hypothesis_references(hypothesis, context.registry)

    errors: list[str] = []

    # Agent-proposed: atom/bond target -> query membership (fail-closed)
    if isinstance(hypothesis, AgentProposedHypothesis):
        if context.query_atom_ids is None:
            errors.append("query_atom_ids context not provided (cannot validate atom/bond targets)")
        else:
            for target in hypothesis.typed_target_atom_or_bond_set:
                if isinstance(target, AtomTarget):
                    if target.atom_id not in context.query_atom_ids:
                        errors.append(f"atom target {target.atom_id} not in query atoms")
                elif isinstance(target, BondTarget):
                    if context.query_bond_pairs is None:
                        errors.append(f"bond target ({target.begin_atom_id},{target.end_atom_id}) present but query_bond_pairs context not provided")
                    else:
                        pair = (target.begin_atom_id, target.end_atom_id)
                        rev = (target.end_atom_id, target.begin_atom_id)
                        if pair not in context.query_bond_pairs and rev not in context.query_bond_pairs:
                            errors.append(f"bond target {pair} not in query bonds")
                        if target.begin_atom_id not in context.query_atom_ids:
                            errors.append(f"bond target endpoint {target.begin_atom_id} not in query atoms")
                        if target.end_atom_id not in context.query_atom_ids:
                            errors.append(f"bond target endpoint {target.end_atom_id} not in query atoms")

    if errors:
        raise UnknownReferenceError("; ".join(errors))


# -- Discriminated union for lane enforcement --

def _get_hypothesis_discriminator(v):
    if isinstance(v, dict):
        return v.get("hypothesis_origin")
    return getattr(v, "hypothesis_origin", None)


Hypothesis = Annotated[
    Union[
        Annotated[ProductionSelectionHypothesis, Tag("agent_selected_from_evidence_space")],
        Annotated[AgentProposedHypothesis, Tag("agent_proposed")],
    ],
    Discriminator(_get_hypothesis_discriminator),
]
