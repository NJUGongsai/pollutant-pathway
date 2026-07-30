"""Participant role resolver + donor eligibility assessor (§11.2–§11.5).

``resolve_roles`` attaches ``RoleHypothesis`` objects to each participant.
It NEVER deletes a participant (§11.1/§11.5 multiset invariant). Roles are
hypotheses with evidence codes, NOT ground-truth assignments (§11.2). The
heuristic score is an ordering hint in [0, 1], NOT a probability.

``assess_donor_eligibility`` is an INDEPENDENT donor-side assessment (§11.4),
distinct from role. It evaluates the §11.4 dimensions (mapped atom retention,
changed mapped atoms, transferred atoms, size/complexity, stoichiometry,
source annotation, COFACTORS prior, reaction direction, mapping quality,
lineage ambiguity) and returns a ``DonorEligibilityAssessment``.

COFACTORS discipline (§11.3): the cofactor list is loaded once via
``load_cofactors`` and used ONLY as:
- ``participant_role_prior`` — adds a weak cofactor/carrier hypothesis.
- ``donor_eligibility_prior`` — downweights eligibility with an explicit reason.
- ``retrieval_downweighting_prior`` — (consumed downstream, not here).

It is NEVER used to delete a participant, force a ground-truth role, exclude
from atom balance, or block a transformed lineage. When the COFACTORS prior
conflicts with mapping evidence, BOTH hypotheses are retained (ambiguity
preserved, §11.3).

P0 schema constraint: ``RoleHypothesis`` (schemas/evidence.py) has
``role`` / ``score`` / ``evidence_codes`` only — no ``policy_version`` or
``ambiguity`` field. These are encoded as:
- ``policy_version`` → evidence code ``"policy_version=p1-t5-1"``.
- ``ambiguity`` → multiple competing ``RoleHypothesis`` entries retained
  (§11.2 "角色可保留多个 hypotheses，不强迫伪造唯一真值").
"""
from __future__ import annotations

from reaction_agent.roles.cofactors import load_cofactors
from reaction_agent.schemas.common import ParticipantRole
from reaction_agent.schemas.evidence import ReactionParticipant, RoleHypothesis
from reaction_agent.schemas.p1_entities import DonorEligibilityAssessment


# -- Policy version (encoded in evidence codes; P0 RoleHypothesis has no field) --
POLICY_VERSION = "p1-t5-1"
_POLICY_CODE = f"policy_version={POLICY_VERSION}"

# -- Prior strengths (ordering hints in [0, 1], NOT probabilities) --
_BASELINE_PRIOR = 0.2   # unknown / no-evidence baseline
_COFACTOR_PRIOR = 0.4   # COFACTORS membership prior (weak, non-definitive)
_SIDE_PRIOR = 0.25      # side-based weak prior
_MAPPING_PRIOR = 0.5    # mapping-derived evidence (stronger than cofactor prior)


def _cofactors_set() -> frozenset[str]:
    """Return the COFACTORS prior as a frozenset for O(1) membership tests."""
    names, _ = load_cofactors()
    return frozenset(names)


def _cofactors_source_hash() -> str:
    """Return the COFACTORS source hash (for evidence provenance)."""
    _, src_hash = load_cofactors()
    return src_hash


def _is_small_molecule(smiles: str) -> bool:
    """Heuristic small-molecule detector (rdkit absent — no heavy-atom count).

    §11.3/§11.4: size is a PRIOR, never a hard rule. This heuristic uses
    SMILES length as a coarse proxy for molecular size. It is intentionally
    conservative: only clearly-small inorganics (``O``, ``O=O``, ``O=C=O``,
    ``N``, ``[Fe+2]``, single-atom / <=4-char SMILES) are flagged. Organic
    cofactors (NAD, ATP, CoA) are NOT flagged as small — they are flagged via
    COFACTORS membership instead.

    This never disqualifies a participant from being a donor; it only
    contributes a ``size_prior`` reason code to donor eligibility.
    """
    if not smiles:
        return False
    # Conservative length proxy: <=5 chars captures O, O=O, O=C=O, N, [Fe+2],
    # OO, but not organic molecules.
    return len(smiles) <= 5


def _classify_cofactor_prior(smiles: str) -> ParticipantRole:
    """Classify a COFACTORS member into a prior role (cofactor or carrier).

    Per §6.2/§11.3: NAD(P)/FAD/FMN are electron/proton CARRIERS; ATP/ADP/AMP/
    CoA/SAM/phosphate are COFACTORS; small inorganics (O2, H2O, CO2, NH3) are
    not forced into any single role — they get ``cofactor`` as a weak prior
    but retain ``unknown`` and any mapping-derived hypotheses (ambiguity
    preserved, §11.3).
    """
    # Carrier signatures: nicotinamide (NAD/NADP), flavin (FAD/FMN)
    carrier_markers = ("NC(=O)c1ccc[n+]", "NC(=O)C1=CN",
                       "Cc1cc2nc3c(=O)", "Cc1cc2c(cc1C)N(")
    if any(smiles.startswith(m) for m in carrier_markers):
        return ParticipantRole.carrier
    # Everything else in COFACTORS (ATP/ADP/AMP/CoA/SAM/phosphate/inorganics)
    # gets a cofactor prior.
    return ParticipantRole.cofactor


def _side_based_prior(side: str) -> tuple[ParticipantRole, str]:
    """Weak side-based prior: reactant→co_substrate, product→coproduct.

    Returns (role, evidence_code). This is a weak prior only — never a
    ground-truth assignment.
    """
    if side == "reactant":
        return (ParticipantRole.co_substrate, "side_prior_reactant")
    if side == "product":
        return (ParticipantRole.coproduct, "side_prior_product")
    return (ParticipantRole.unknown, "side_prior_unknown_side")


def _has_mapping_evidence(p: ReactionParticipant) -> bool:
    """Whether the participant carries mapping-derived evidence.

    Mapping evidence = mapped_fraction > 0 OR changed_atom_fraction > 0 OR
    atom_map_numbers non-empty. This is used to decide whether to add
    mapping-derived role hypotheses (transformed_substrate / transformed_product).
    """
    return (
        p.mapped_fraction > 0.0
        or p.changed_atom_fraction > 0.0
        or len(p.atom_map_numbers) > 0
    )


def _mapping_derived_hypotheses(
    p: ReactionParticipant,
) -> list[RoleHypothesis]:
    """Mapping-derived role hypotheses (§11.3: ambiguity preserved).

    If the participant has mapping evidence (mapped atoms retained / changed),
    add a transformed_substrate (reactant) or transformed_product (product)
    hypothesis. These are CONTESTABLE — they coexist with any COFACTORS prior.
    """
    if not _has_mapping_evidence(p):
        return []
    codes = [_POLICY_CODE, "mapping_derived_evidence"]
    if p.mapped_fraction > 0.0:
        codes.append(f"mapped_fraction={p.mapped_fraction:.2f}")
    if p.changed_atom_fraction > 0.0:
        codes.append(f"changed_atom_fraction={p.changed_atom_fraction:.2f}")
    if p.atom_map_numbers:
        codes.append(f"atom_map_count={len(p.atom_map_numbers)}")
    if p.side == "reactant":
        return [RoleHypothesis(
            role=ParticipantRole.transformed_substrate,
            score=_MAPPING_PRIOR,
            evidence_codes=codes,
        )]
    if p.side == "product":
        return [RoleHypothesis(
            role=ParticipantRole.transformed_product,
            score=_MAPPING_PRIOR,
            evidence_codes=codes,
        )]
    return []


def _build_role_hypotheses(
    p: ReactionParticipant, cofactors: frozenset[str],
) -> list[RoleHypothesis]:
    """Build the full set of role hypotheses for a participant.

    Order of evidence strength (all are hypotheses, none is ground truth):
    1. ``unknown`` baseline (always present — no forced unique truth).
    2. side-based weak prior (co_substrate / coproduct).
    3. COFACTORS prior (cofactor / carrier) — if member.
    4. mapping-derived (transformed_substrate / transformed_product) — if
       mapping evidence present. Coexists with COFACTORS prior (ambiguity).

    §11.3: when COFACTORS prior conflicts with mapping evidence, BOTH are
    retained. ``unknown`` is always retained so no participant is forced to
    a definitive role.
    """
    hyps: list[RoleHypothesis] = []

    # 1. unknown baseline — always present (§11.2: no forced unique truth)
    hyps.append(RoleHypothesis(
        role=ParticipantRole.unknown,
        score=_BASELINE_PRIOR,
        evidence_codes=[_POLICY_CODE, "default_unknown_no_evidence"],
    ))

    # 2. side-based weak prior
    side_role, side_code = _side_based_prior(p.side)
    if side_role is not ParticipantRole.unknown:
        hyps.append(RoleHypothesis(
            role=side_role,
            score=_SIDE_PRIOR,
            evidence_codes=[_POLICY_CODE, side_code],
        ))

    # 3. COFACTORS prior (§11.3: only a prior, never destructive)
    if p.canonical_smiles in cofactors:
        prior_role = _classify_cofactor_prior(p.canonical_smiles)
        hyps.append(RoleHypothesis(
            role=prior_role,
            score=_COFACTOR_PRIOR,
            evidence_codes=[
                _POLICY_CODE,
                "cofactors_prior",
                f"cofactors_source_hash={_cofactors_source_hash()[:12]}",
            ],
        ))

    # 4. mapping-derived (§11.3: ambiguity preserved — coexists with prior)
    hyps.extend(_mapping_derived_hypotheses(p))

    return hyps


def resolve_roles(
    participants: list[ReactionParticipant],
) -> list[ReactionParticipant]:
    """Attach role hypotheses to each participant. NEVER delete a participant.

    §11.1/§11.5 multiset invariant: ``len(output) == len(input)`` and every
    input participant_id appears in the output (order preserved). No
    participant is stripped, regardless of COFACTORS membership, size, or
    side.

    §11.2: roles are hypotheses with evidence codes + policy_version. The
    heuristic score is an ordering hint in [0, 1], NOT a probability.

    §11.3: COFACTORS is used ONLY as ``participant_role_prior``. It adds a
    weak cofactor/carrier hypothesis but never forces ground truth, never
    deletes, never excludes from atom balance, never blocks transformed
    lineage. When prior conflicts with mapping evidence, both are retained.

    Immutability: input participants are NOT mutated. New participant objects
    are returned (via ``model_copy``) with updated ``role_hypotheses``; all
    other fields are preserved verbatim.
    """
    cofactors = _cofactors_set()
    out: list[ReactionParticipant] = []
    for p in participants:
        hyps = _build_role_hypotheses(p, cofactors)
        # model_copy(update=...) returns a new object; non-role fields
        # preserved verbatim (§11.1: stoichiometry, smiles, side, maps).
        out.append(p.model_copy(update={"role_hypotheses": hyps}))
    return out


# =====================================================================
# §11.4 — donor eligibility (distinct from role)
# =====================================================================


def _eligibility_from_dimensions(
    core_dims: dict[str, str],
    context_dims: dict[str, str],
) -> tuple[str, list[str]]:
    """Aggregate dimension verdicts into an eligibility + reason codes.

    Core dimensions (mapping-derived: retention, changed atoms, transferred
    atoms, mapping quality, lineage ambiguity) drive the verdict. Context
    dimensions (size, stoichiometry, source annotation, COFACTORS prior,
    direction) only contribute reason codes and may DOWNGRADE eligible →
    conditionally_eligible (e.g. COFACTORS prior downweight, §11.3). Context
    never upgrades unknown → conditional.

    Verdict prefix convention:
    - ``eligible_*``  — positive evidence
    - ``conditional_*`` — evidence pending conditions
    - ``unknown_*``   — insufficient evidence (never fabricated)
    - ``not_*`` (excl. ``not_applicable_*``) — disqualifying evidence
    - ``not_applicable_*`` — dimension not relevant (skipped in aggregation)

    Aggregation:
    1. core ``not_`` (excl. not_applicable) + no core ``eligible_`` → not_eligible
    2. core ``eligible_`` → eligible, unless COFACTORS prior downgrades →
       conditionally_eligible
    3. core ``conditional_`` → conditionally_eligible
    4. core ``unknown_`` only → unknown
    5. otherwise → unknown
    """
    all_codes = list(core_dims.values()) + list(context_dims.values())
    core_verdicts = list(core_dims.values())

    core_eligible = any(v.startswith("eligible_") for v in core_verdicts)
    core_conditional = any(
        v.startswith("conditional_") for v in core_verdicts
    )
    core_not = any(
        v.startswith("not_") and not v.startswith("not_applicable_")
        for v in core_verdicts
    )

    # Context downweight: COFACTORS prior present → downgrade eligible.
    cofactor_downweight = any(
        "cofactors_prior" in k and "downweight" in v
        for k, v in context_dims.items()
    )

    if core_not and not core_eligible:
        return ("not_eligible", all_codes)
    if core_eligible:
        if cofactor_downweight:
            return ("conditionally_eligible", all_codes)
        return ("eligible", all_codes)
    if core_conditional:
        return ("conditionally_eligible", all_codes)
    return ("unknown", all_codes)


def assess_donor_eligibility(
    participant: ReactionParticipant,
    mapping_report: object | None = None,
) -> DonorEligibilityAssessment:
    """Independent donor-side eligibility assessment (§11.4).

    Donor eligibility is NOT role (§11.4). A participant may have role=unknown
    but still be donor-eligible (or vice versa). This function evaluates the
    §11.4 dimensions and returns a ``DonorEligibilityAssessment``.

    Dimensions (§11.4): mapped atom retention, changed mapped atoms,
    transferred atoms, size/complexity, stoichiometry, source annotation,
    COFACTORS prior, reaction direction, mapping quality, lineage ambiguity.

    Without ``mapping_report`` (None), mapping-dependent dimensions return
    ``unknown_<dimension>`` (never fabricated). With mapping evidence
    present (non-None mapping_report OR participant.mapped_fraction > 0),
    retention/changed/transferred dimensions contribute evidence.

    §11.3: COFACTORS prior downweights (conditionally_eligible) but never
    forces not_eligible silently — small molecules can be formal atom sources.

    Immutability: the participant is NOT mutated.
    """
    cofactors = _cofactors_set()
    p = participant
    # Core dimensions (mapping-derived) — drive the verdict.
    core_dims: dict[str, str] = {}
    # Context dimensions (priors) — reason codes + eligible→conditional downweight.
    context_dims: dict[str, str] = {}

    # -- CORE: mapped atom retention --
    if mapping_report is None and p.mapped_fraction == 0.0:
        core_dims["mapped_atom_retention"] = "unknown_mapping_unavailable"
    elif p.mapped_fraction > 0.0:
        core_dims["mapped_atom_retention"] = (
            f"eligible_mapped_retention_fraction={p.mapped_fraction:.2f}"
        )
    else:
        core_dims["mapped_atom_retention"] = "unknown_mapping_present_no_fraction"

    # -- CORE: changed mapped atoms --
    if p.changed_atom_fraction > 0.0:
        core_dims["changed_mapped_atoms"] = (
            f"eligible_changed_atoms_fraction={p.changed_atom_fraction:.2f}"
        )
    elif mapping_report is None:
        core_dims["changed_mapped_atoms"] = "unknown_changed_atoms_no_mapping"
    else:
        core_dims["changed_mapped_atoms"] = "conditional_no_changed_atoms_observed"

    # -- CORE: transferred atoms (requires mechanistic evidence) --
    core_dims["transferred_atoms"] = "unknown_no_mechanistic_evidence"

    # -- CORE: mapping quality --
    if mapping_report is None:
        core_dims["mapping_quality"] = "unknown_mapping_report_absent"
    else:
        core_dims["mapping_quality"] = "conditional_mapping_report_present"

    # -- CORE: lineage ambiguity (requires resolved lineage) --
    core_dims["lineage_ambiguity"] = "unknown_lineage_not_resolved"

    # -- CONTEXT: size / complexity (prior only, never disqualifying — §11.3) --
    if _is_small_molecule(p.canonical_smiles):
        context_dims["size_complexity"] = "conditional_small_molecule_size_prior"
    else:
        context_dims["size_complexity"] = "not_applicable_size_nontrivial"

    # -- CONTEXT: stoichiometry (informational; never disqualifying) --
    context_dims["stoichiometry"] = (
        f"not_applicable_stoichiometry={p.stoichiometry}"
    )

    # -- CONTEXT: source annotation (provenance presence) --
    if p.provenance:
        context_dims["source_annotation"] = "not_applicable_provenance_present"
    else:
        context_dims["source_annotation"] = "not_applicable_no_provenance"

    # -- CONTEXT: COFACTORS prior (§11.3: downweight, never silent not_eligible) --
    if p.canonical_smiles in cofactors:
        context_dims["cofactors_prior"] = (
            "conditional_cofactors_prior_downweight"
        )
    else:
        context_dims["cofactors_prior"] = "not_applicable_not_a_cofactor"

    # -- CONTEXT: reaction direction (side as weak proxy; direction is on
    # ReactionEvidence, not ReactionParticipant) --
    context_dims["reaction_direction"] = f"not_applicable_side={p.side}"

    eligibility, reason_codes = _eligibility_from_dimensions(
        core_dims, context_dims
    )

    # Build human-readable notes summarizing the dimension verdicts.
    notes_lines = [f"{k}={v}" for k, v in {**core_dims, **context_dims}.items()]
    assessment_notes = (
        f"Donor eligibility assessed per §11.4 "
        f"({len(core_dims)} core + {len(context_dims)} context dimensions). "
        f"Policy version {POLICY_VERSION}. "
        f"Dimensions: " + "; ".join(notes_lines)
    )

    return DonorEligibilityAssessment(
        participant_id=p.participant_id,
        eligibility=eligibility,
        reason_codes=reason_codes,
        evidence_ids=[],
        assessment_notes=assessment_notes,
    )
