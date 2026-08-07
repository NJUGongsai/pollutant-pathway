"""P9-T1: AgentProposedHypothesis lane — schema, eight-step validation chain,
lane-pinned candidate, and consumption gate (final_plan §12.1, final_design
§19.2, ADR-0002).

The agent_proposed lane is a physically isolated, exploratory, NON-production
lane. An ``AgentProposedHypothesis`` (the §19.2 field set, defined unchanged in
``reaction_agent.schemas.hypothesis``) must pass the full eight-step chain:

    1. support validation        — support IDs exist + relation integrity
    2. registered vocabulary     — family + relaxation IDs registered (no free text)
    3. compiler                  — typed targets -> deterministic CompiledGraphEdit
    4. site validation           — typed targets belong to the current query
    5. graph edit                — apply compiled delta to the query molecule
    6. molecule validation       — sanitization + heavy-atom conservation
    7. dual-ledger validation    — lane non-contamination + ledger existence
    8. grounding validation      — family grounded by a cited support reaction

On pass, a lane-pinned ``AgentProposedCandidate`` is emitted (exploratory, NOT a
strict ``Candidate`` / NOT production rank). The independent report is in
``reaction_agent.p9.agent_proposed.report``.

Hard boundary (strict untouched): this module only ADDS new files. It consumes
the locked §19.2 schema, the registry/context validators, the dual-ledger
schemas, and the strict ``Candidate`` (for anti-masquerade contrast) — it never
imports or modifies the strict channel (P3-P6), P7, or P8.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import LedgerBalanceStatus, NonEmptyStr, StrictModel
from reaction_agent.schemas.errors import ContractViolation, UnknownReferenceError
from reaction_agent.schemas.hypothesis import (
    AgentProposedHypothesis,
    AtomTarget,
    BondTarget,
    HypothesisReferenceRegistry,
    validate_hypothesis_references,
)
from reaction_agent.schemas.ledger import CandidateAnalogyLedger, SourceReactionLedger

from reaction_agent.p9.agent_proposed.policy import (
    CHAIN_CHECK_NAMES,
    AgentProposedChainPolicy,
    DEFAULT_AGENT_PROPOSED_CHAIN_POLICY,
)

# RDKit is the chemistry backend for graph-edit + molecule validation. The lane
# uses it DIRECTLY (not via the strict P3 kernel) to stay physically isolated.
from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")


# ---------------------------------------------------------------------------
# Error typing (mirrors P8 R1-05)
# ---------------------------------------------------------------------------


class AgentProposedValidationError(ContractViolation):
    """Raised when an agent_proposed hypothesis fails a non-reference rule.

    Reference violations (unknown IDs / missing relations) keep using
    ``UnknownReferenceError``; this type is reserved for validation failures
    such as compilation, site-target mismatch, molecule validation, lane
    contamination, or grounding failure.
    """


# ---------------------------------------------------------------------------
# Controlled reject vocabulary (no free text — ADR-0002 "user semantics clear")
# ---------------------------------------------------------------------------


class AgentProposedRejectReasonCode(str, Enum):
    """Why an agent_proposed hypothesis was rejected from the lane (one per chain step)."""

    support_validation_failed = "support_validation_failed"
    registered_vocabulary_violation = "registered_vocabulary_violation"
    compilation_failed = "compilation_failed"
    site_validation_failed = "site_validation_failed"
    graph_edit_failed = "graph_edit_failed"
    molecule_validation_failed = "molecule_validation_failed"
    dual_ledger_violation = "dual_ledger_violation"
    grounding_failed = "grounding_failed"


# ---------------------------------------------------------------------------
# Step 3 output: deterministic compiled graph edit
# ---------------------------------------------------------------------------


class CompiledGraphEdit(StrictModel):
    """Deterministic descriptor compiled from the typed target set (step 3).

    Atom targets -> recorded atom IDs (attribute-change sites, no removal).
    Bond targets -> recorded bond endpoint pairs (bond-edit sites).
    ``compile_hash`` is order-invariant (sorted, deduplicated) so identical
    target sets always compile to the same hash (reproducibility).
    """

    atom_target_ids: list[int] = []
    bond_target_pairs: list[tuple[int, int]] = []
    target_count: int = Field(ge=0)
    compile_hash: NonEmptyStr


# ---------------------------------------------------------------------------
# Step 5/6 output: edited molecule
# ---------------------------------------------------------------------------


class EditedMolecule(StrictModel):
    """Result of applying the compiled graph edit to the query molecule.

    ``sanitized`` is True iff RDKit could sanitize the edited structure (valence
    + kekulization). Heavy-atom conservation is enforced in step 6:
    ``heavy_atom_count_after`` must equal ``heavy_atom_count_before`` (agent-
    proposed edits change bonds/attributes, never add/remove heavy atoms).
    """

    query_smiles: NonEmptyStr
    edited_smiles: str = ""
    heavy_atom_count_before: int = 0
    heavy_atom_count_after: int = 0
    sanitized: bool = False


# ---------------------------------------------------------------------------
# Lane-pinned validation record (R1-04 trace pattern)
# ---------------------------------------------------------------------------


class AgentProposedValidation(StrictModel):
    """Lane-tagged validation record for an agent_proposed candidate.

    ``lane`` is pinned to "agent_proposed" so no agent_proposed output can
    claim a strict validation (no strict masquerade). ``status`` is a
    controlled vocabulary word. ``chain_policy_content_hash`` records the exact
    chain artifact the hypothesis was validated against, so a consumer never
    trusts an embedded status without the matching fingerprint.
    """

    lane: Literal["agent_proposed"] = "agent_proposed"
    status: Literal["validated"] = "validated"
    checks: list[NonEmptyStr] = []
    chain_policy_content_hash: NonEmptyStr


# ---------------------------------------------------------------------------
# Lane-pinned OUTPUT (NOT a strict Candidate)
# ---------------------------------------------------------------------------


class AgentProposedCandidate(StrictModel):
    """A validated agent_proposed lane candidate. NOT a strict ``Candidate``.

    Lane is Literal-pinned to "agent_proposed"; ``exploratory`` is pinned True;
    ``output_semantics`` is pinned ``exploratory_non_production``. The product
    SMILES lives in ``edited_product_smiles`` (NOT ``canonical_product``) and
    there is no ``ranking_score`` / ``run_id`` / ``decision`` — the type is
    structurally incompatible with the strict ``Candidate``.
    """

    hypothesis_id: NonEmptyStr
    lane: Literal["agent_proposed"] = "agent_proposed"
    output_semantics: Literal["exploratory_non_production"] = "exploratory_non_production"
    exploratory: Literal[True] = True
    transformation_family_id: NonEmptyStr
    compiled_graph_edit: CompiledGraphEdit
    edited_product_smiles: str = ""
    support_reaction_ids: list[NonEmptyStr] = []
    support_lineage_ids: list[NonEmptyStr] = []
    relaxation_policy_id: str | None = None
    allowed_relaxation_ids: list[NonEmptyStr] = []
    rationale_summary: NonEmptyStr = "none"
    policy_version: NonEmptyStr
    validation: AgentProposedValidation


# ---------------------------------------------------------------------------
# Validation context
# ---------------------------------------------------------------------------


class QueryMoleculeContext(StrictModel):
    """The current query molecule + its atom-map vocabulary (site validation)."""

    smiles: NonEmptyStr
    query_atom_ids: frozenset[int]
    query_bond_pairs: frozenset[tuple[int, int]] = frozenset()


class LaneScopedCandidateLedger(StrictModel):
    """Agent-proposed-scoped wrapper around a strict ``CandidateAnalogyLedger``.

    ``lane`` is pinned to "agent_proposed" so a strict-lane ledger cannot
    masquerade as agent-proposed evidence (lane non-contamination, step 7).
    The wrapper is ADDITIVE — the strict ``CandidateAnalogyLedger`` schema is
    not modified.
    """

    lane: Literal["agent_proposed"] = "agent_proposed"
    underlying: CandidateAnalogyLedger


class AgentProposedValidationContext(StrictModel):
    """Full validation context for the eight-step chain.

    - ``registry``: ID existence + relation evidence (steps 1-2).
    - ``chain_policy``: the frozen chain artifact (content-hash trace).
    - ``query_molecule``: the current query (steps 4-6); None is a rejection.
    - ``source_ledgers`` / ``agent_candidate_ledgers``: dual-ledger evidence (step 7).
    - ``strict_candidate_ids``: strict-lane candidate IDs (lane non-contamination).
    - ``family_grounding``: family_id -> reaction_ids that document it (step 8).
    """

    registry: HypothesisReferenceRegistry
    chain_policy: AgentProposedChainPolicy = DEFAULT_AGENT_PROPOSED_CHAIN_POLICY
    query_molecule: QueryMoleculeContext | None = None
    source_ledgers: dict[str, SourceReactionLedger] = {}
    agent_candidate_ledgers: dict[str, LaneScopedCandidateLedger] = {}
    strict_candidate_ids: frozenset[str] = frozenset()
    family_grounding: dict[str, list[str]] = {}


# ---------------------------------------------------------------------------
# Chemistry helpers (RDKit, direct — lane-isolated from the P3 kernel)
# ---------------------------------------------------------------------------


def _heavy_atom_count_smiles(smiles: str) -> int:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0
    return sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() != 1)


def _heavy_atom_count_mol(mol) -> int:
    return sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() != 1)


def _map_to_idx(mol) -> dict[int, int]:
    return {
        atom.GetAtomMapNum(): atom.GetIdx()
        for atom in mol.GetAtoms()
        if atom.GetAtomMapNum() > 0
    }


# ---------------------------------------------------------------------------
# Step 3: compiler
# ---------------------------------------------------------------------------


def compile_typed_targets(targets: list) -> CompiledGraphEdit:
    """Compile a typed target set into a deterministic ``CompiledGraphEdit``.

    Order-invariant: sorting + deduplication means the same target set always
    compiles to the same ``compile_hash`` (reproducibility). An empty target
    set is a compilation failure (the schema also enforces non-emptiness).
    """
    if not targets:
        raise AgentProposedValidationError(
            "typed_target_atom_or_bond_set must not be empty (compiler step)"
        )
    atom_ids = sorted({t.atom_id for t in targets if isinstance(t, AtomTarget)})
    bond_pairs = sorted(
        {
            (min(t.begin_atom_id, t.end_atom_id), max(t.begin_atom_id, t.end_atom_id))
            for t in targets
            if isinstance(t, BondTarget)
        }
    )
    body = {
        "atom_target_ids": atom_ids,
        "bond_target_pairs": [list(p) for p in bond_pairs],
        "target_count": len(atom_ids) + len(bond_pairs),
    }
    return CompiledGraphEdit(
        atom_target_ids=atom_ids,
        bond_target_pairs=[tuple(p) for p in bond_pairs],
        target_count=len(atom_ids) + len(bond_pairs),
        compile_hash=canonical_hash(body),
    )


# ---------------------------------------------------------------------------
# Step 4: site validation (typed targets belong to the current query)
# ---------------------------------------------------------------------------


def _validate_site_targets(
    hypothesis: AgentProposedHypothesis, query: QueryMoleculeContext
) -> None:
    errors: list[str] = []
    for target in hypothesis.typed_target_atom_or_bond_set:
        if isinstance(target, AtomTarget):
            if target.atom_id not in query.query_atom_ids:
                errors.append(f"atom target {target.atom_id} not in query atoms")
        elif isinstance(target, BondTarget):
            pair = (target.begin_atom_id, target.end_atom_id)
            rev = (target.end_atom_id, target.begin_atom_id)
            if pair not in query.query_bond_pairs and rev not in query.query_bond_pairs:
                errors.append(f"bond target {pair} not in query bonds")
            if target.begin_atom_id not in query.query_atom_ids:
                errors.append(f"bond target endpoint {target.begin_atom_id} not in query atoms")
            if target.end_atom_id not in query.query_atom_ids:
                errors.append(f"bond target endpoint {target.end_atom_id} not in query atoms")
    if errors:
        raise UnknownReferenceError("; ".join(errors))


# ---------------------------------------------------------------------------
# Step 5: graph edit (apply compiled delta to the query molecule)
# ---------------------------------------------------------------------------


def apply_graph_edit(
    compiled: CompiledGraphEdit, query: QueryMoleculeContext
) -> EditedMolecule:
    """Apply the compiled graph edit to the query molecule (step 5).

    Bond targets -> bond DELETIONS (the bond between the two atom-map endpoints
    is removed). Atom targets -> attribute-change sites (recorded, no structural
    removal — agent-proposed edits never add/remove heavy atoms).

    Raises ``AgentProposedValidationError`` if the query SMILES is invalid, a
    cited bond does not exist, OR the edit would be an identity edit (an
    atom-target-only hypothesis whose attribute-change vocabulary is not yet
    implemented — rejected to prevent the query molecule from masquerading as a
    new_valid candidate, R1-03).
    """
    # R1-03: an atom-target-only hypothesis would produce an identity edit (the
    # query molecule unchanged) because atom attribute-change edits are not yet
    # implemented. Reject it under a controlled reason rather than emit the query
    # as a new_valid candidate. A mixed hypothesis (atom + bond targets) is fine:
    # the bond deletion already makes the edit non-identity.
    if compiled.atom_target_ids and not compiled.bond_target_pairs:
        raise AgentProposedValidationError(
            "atom-target-only hypotheses require a registered attribute-change "
            "vocabulary (not yet implemented); rejected to prevent an identity edit "
            "masquerading as new_valid"
        )
    mol = Chem.MolFromSmiles(query.smiles)
    if mol is None:
        raise AgentProposedValidationError(f"invalid query SMILES: {query.smiles}")
    rwmol = Chem.RWMol(mol)
    before = _heavy_atom_count_mol(rwmol)
    map_to_idx = _map_to_idx(rwmol)

    for (a, b) in compiled.bond_target_pairs:
        ia = map_to_idx.get(a)
        ib = map_to_idx.get(b)
        if ia is None or ib is None:
            raise AgentProposedValidationError(
                f"bond target ({a},{b}) atom map not found in query molecule"
            )
        bond = rwmol.GetBondBetweenAtoms(ia, ib)
        if bond is None:
            raise AgentProposedValidationError(
                f"no bond between atom maps {a},{b} in query molecule to delete"
            )
        rwmol.RemoveBond(ia, ib)

    edited = rwmol.GetMol()
    try:
        Chem.SanitizeMol(edited)
        sanitized = True
    except Exception:
        sanitized = False
    edited_smiles = Chem.MolToSmiles(edited) if sanitized else ""
    after = _heavy_atom_count_smiles(edited_smiles) if edited_smiles else before
    return EditedMolecule(
        query_smiles=query.smiles,
        edited_smiles=edited_smiles,
        heavy_atom_count_before=before,
        heavy_atom_count_after=after,
        sanitized=sanitized,
    )


# ---------------------------------------------------------------------------
# Step 6: molecule validation
# ---------------------------------------------------------------------------


def validate_molecule(edited: EditedMolecule) -> None:
    """Validate the edited molecule (step 6): sanitization + heavy-atom conservation."""
    if not edited.sanitized:
        raise AgentProposedValidationError(
            "edited molecule failed RDKit sanitization (broken valence/kekulization)"
        )
    if edited.heavy_atom_count_after != edited.heavy_atom_count_before:
        raise AgentProposedValidationError(
            f"heavy-atom conservation violated: before={edited.heavy_atom_count_before}, "
            f"after={edited.heavy_atom_count_after}"
        )
    if not edited.edited_smiles:
        raise AgentProposedValidationError("edited molecule produced empty SMILES")


# ---------------------------------------------------------------------------
# Step 7: dual-ledger validation (lane non-contamination + existence)
# ---------------------------------------------------------------------------


def _synthesize_agent_lane_ledger(
    hypothesis: AgentProposedHypothesis,
    context: "AgentProposedValidationContext",
) -> LaneScopedCandidateLedger:
    """Synthesize an agent-lane candidate ledger from a cited support reaction.

    R1-01: step 7 is MANDATORY — there is no path that emits a validated
    candidate without running ``validate_dual_ledger``. When the context does
    not supply a scoped ledger for this hypothesis (the normal builder path,
    where a new candidate's ledger cannot be pre-registered), the chain
    synthesizes one from a cited support reaction's source ledger. This closes
    the chicken-and-egg gap and makes the ``dual_ledger_validation`` check a
    true attestation rather than a false claim.

    Fail-closed: if NO cited support reaction has a registered source ledger in
    the context, step 7 cannot run and the chain rejects the hypothesis.
    """
    # reverse-lookup: reaction_id -> source_ledger_id(s) that ground it
    rid_to_source_ledgers: dict[str, list[str]] = {}
    for sl_id, rid in context.registry.source_ledger_to_reaction_id.items():
        rid_to_source_ledgers.setdefault(rid, []).append(sl_id)

    found_source_ledger_id: str | None = None
    for rid in hypothesis.support_reaction_ids:
        for sl_id in rid_to_source_ledgers.get(rid, []):
            if sl_id in context.source_ledgers:
                found_source_ledger_id = sl_id
                break
        if found_source_ledger_id is not None:
            break

    if found_source_ledger_id is None:
        raise AgentProposedValidationError(
            "step 7 cannot synthesize an agent-lane ledger: none of the cited "
            f"support reactions {list(hypothesis.support_reaction_ids)} has a "
            "registered source ledger in the context (dual-ledger validation is "
            "mandatory — no false attestation)"
        )

    # fresh agent-lane candidate id (NOT in strict_candidate_ids by namespace)
    agent_candidate_id = f"agent_cand_{hypothesis.hypothesis_id}"
    agent_ledger_id = f"agent_ledger_{hypothesis.hypothesis_id}"
    return LaneScopedCandidateLedger(
        lane="agent_proposed",
        underlying=CandidateAnalogyLedger(
            ledger_id=agent_ledger_id,
            source_ledger_id=found_source_ledger_id,
            candidate_id=agent_candidate_id,
            candidate_balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        ),
    )


def validate_dual_ledger(
    hypothesis_id: str,
    scoped_ledger: LaneScopedCandidateLedger,
    context: AgentProposedValidationContext,
) -> None:
    """Validate an agent-proposed candidate ledger (step 7).

    - Lane non-contamination: ``underlying.candidate_id`` must NOT be a strict-
      lane candidate ID (an agent_proposed hypothesis cannot piggyback on a
      strict candidate's proven ledger).
    - Existence: ``underlying.source_ledger_id`` must be registered in the
      context's source ledgers.
    """
    underlying = scoped_ledger.underlying
    ref_errors: list[str] = []
    val_errors: list[str] = []

    if underlying.candidate_id in context.strict_candidate_ids:
        val_errors.append(
            f"candidate_id {underlying.candidate_id} is a strict-lane candidate "
            "(lane contamination: agent_proposed cannot piggyback on a strict ledger)"
        )
    if underlying.source_ledger_id not in context.source_ledgers:
        ref_errors.append(f"unknown source_ledger_id: {underlying.source_ledger_id}")

    if ref_errors:
        raise UnknownReferenceError("; ".join(ref_errors))
    if val_errors:
        raise AgentProposedValidationError("; ".join(val_errors))


# ---------------------------------------------------------------------------
# Step 8: grounding validation
# ---------------------------------------------------------------------------


def validate_grounding(
    hypothesis: AgentProposedHypothesis, context: AgentProposedValidationContext
) -> None:
    """Validate that the proposed family is grounded by a cited support reaction.

    Fail-closed: the family must have grounding evidence in ``family_grounding``
    AND at least one cited support reaction must appear in that grounding set.
    """
    family = hypothesis.transformation_family_id
    if family not in context.family_grounding:
        raise AgentProposedValidationError(
            f"transformation_family_id {family} has no grounding evidence "
            "(not in family_grounding)"
        )
    grounding_reactions = set(context.family_grounding[family])
    cited = set(hypothesis.support_reaction_ids)
    if not (grounding_reactions & cited):
        raise AgentProposedValidationError(
            f"family {family} grounded by {sorted(grounding_reactions)} but "
            f"hypothesis cites none of them (support_reaction_ids={sorted(cited)})"
        )


# ---------------------------------------------------------------------------
# The full eight-step chain
# ---------------------------------------------------------------------------


def validate_agent_proposed_hypothesis(
    hypothesis: AgentProposedHypothesis,
    context: AgentProposedValidationContext,
) -> tuple[CompiledGraphEdit, EditedMolecule]:
    """Run the full eight-step validation chain.

    Raises:
    - ``UnknownReferenceError`` for reference violations (steps 1-2, 4, 7).
    - ``AgentProposedValidationError`` for non-reference violations (steps 3,
      5-8).

    Returns ``(compiled, edited)`` on success (for the builder to emit a
    lane-pinned candidate).
    """
    # Steps 1-2: support validation + registered vocabulary (registry references).
    # The existing registry validator is fail-closed for both existence and
    # relation integrity, and checks the agent-proposed relaxation vocabulary.
    validate_hypothesis_references(hypothesis, context.registry)

    # Step 3: compiler
    compiled = compile_typed_targets(hypothesis.typed_target_atom_or_bond_set)

    # Step 4: site validation — typed targets belong to the current query
    if context.query_molecule is None:
        raise AgentProposedValidationError(
            "query_molecule context not provided (cannot validate site targets)"
        )
    _validate_site_targets(hypothesis, context.query_molecule)

    # Step 5: graph edit
    edited = apply_graph_edit(compiled, context.query_molecule)

    # Step 6: molecule validation
    validate_molecule(edited)

    # Step 7: dual-ledger validation — MANDATORY (R1-01: no silent skip, no
    # false attestation). Use the scoped ledger supplied in the context if one
    # exists; otherwise synthesize an agent-lane ledger from a cited support
    # reaction's source ledger (the normal builder path, where a new
    # candidate's ledger cannot be pre-registered). ``validate_dual_ledger``
    # ALWAYS runs — the ``dual_ledger_validation`` check burned into the record
    # is therefore a true attestation.
    scoped = context.agent_candidate_ledgers.get(hypothesis.hypothesis_id)
    if scoped is None:
        scoped = _synthesize_agent_lane_ledger(hypothesis, context)
    validate_dual_ledger(hypothesis.hypothesis_id, scoped, context)

    # Step 8: grounding validation
    validate_grounding(hypothesis, context)

    return compiled, edited


# ---------------------------------------------------------------------------
# Builder — runs the chain, burns checks AFTER pass, emits lane-pinned candidate
# ---------------------------------------------------------------------------


def build_agent_proposed_candidate(
    hypothesis: AgentProposedHypothesis,
    context: AgentProposedValidationContext,
) -> AgentProposedCandidate:
    """Run the full chain and produce a validated ``AgentProposedCandidate``.

    Raises ``UnknownReferenceError`` / ``AgentProposedValidationError`` (via
    ``validate_agent_proposed_hypothesis``) or pydantic ``ValidationError`` on
    any violation — fail-closed.

    R1-04: the post-chain ``checks`` list and the chain ``content_hash`` are
    burned into the validation record immutably ONLY after the chain passes.

    Defense-in-depth: the hypothesis is re-validated at the schema level before
    the chain runs, so a hypothesis mutated post-construction (e.g. via
    ``model_copy``) cannot bypass the §19.2 field contract — schema violations
    surface as ``ValidationError`` here, distinct from the chain's own
    ``AgentProposedValidationError`` / ``UnknownReferenceError``.
    """
    # re-validate the §19.2 schema (catches e.g. an empty target set before the
    # chain's compiler step even runs)
    hypothesis = AgentProposedHypothesis.model_validate(hypothesis.model_dump())
    compiled, edited = validate_agent_proposed_hypothesis(hypothesis, context)

    base_validation = AgentProposedValidation(
        lane="agent_proposed",
        status="validated",
        checks=[],
        chain_policy_content_hash=context.chain_policy.content_hash,
    )
    candidate = AgentProposedCandidate(
        hypothesis_id=hypothesis.hypothesis_id,
        lane="agent_proposed",
        transformation_family_id=hypothesis.transformation_family_id,
        compiled_graph_edit=compiled,
        edited_product_smiles=edited.edited_smiles,
        support_reaction_ids=list(hypothesis.support_reaction_ids),
        support_lineage_ids=list(hypothesis.support_lineage_ids),
        relaxation_policy_id=hypothesis.relaxation_policy_id,
        allowed_relaxation_ids=list(hypothesis.allowed_relaxation_ids),
        rationale_summary=hypothesis.rationale_summary,
        policy_version=hypothesis.policy_version,
        validation=base_validation,
    )
    # burn the checks immutably AFTER the chain passed (R1-04)
    return candidate.model_copy(
        update={
            "validation": base_validation.model_copy(
                update={"checks": list(CHAIN_CHECK_NAMES)}
            )
        }
    )


# ---------------------------------------------------------------------------
# Consumption gate (re-run the chain, never trust the embedded record)
# ---------------------------------------------------------------------------


def revalidate_agent_proposed_candidate(
    candidate,
    context: AgentProposedValidationContext,
) -> None:
    """Consumption gate (R1-04 / OA-2 pattern): re-run the chain on a candidate.

    - Lane guard: rejects any input whose lane is not ``agent_proposed`` (a
      strict ``Candidate`` with ``lane=strict`` is rejected here — no cross-lane
      raw-score mixing, no strict masquerade).
    - Re-run: reconstructs the typed targets from ``compiled_graph_edit``,
      rebuilds the hypothesis, and re-runs the full chain. The embedded
      ``validation.status`` / ``checks`` record is NEVER trusted.
    - Lie detection: the recomputed ``edited_product_smiles`` must match the
      stored value — a candidate whose embedded record claims "validated" but
      whose stored SMILES was tampered is caught here.
    """
    # lane guard
    if getattr(candidate, "lane", None) != "agent_proposed":
        raise AgentProposedValidationError(
            "revalidate_agent_proposed_candidate only accepts agent_proposed-lane "
            "candidates; "
            f"input lane={getattr(candidate, 'lane', None)!r} "
            "(strict inputs are rejected to prevent cross-lane mixing and strict masquerade)"
        )

    compiled = candidate.compiled_graph_edit
    typed_targets: list = []
    for aid in compiled.atom_target_ids:
        typed_targets.append(AtomTarget(atom_id=aid))
    for pair in compiled.bond_target_pairs:
        a, b = int(pair[0]), int(pair[1])
        typed_targets.append(BondTarget(begin_atom_id=a, end_atom_id=b))

    hypothesis = AgentProposedHypothesis(
        hypothesis_id=candidate.hypothesis_id,
        hypothesis_origin="agent_proposed",
        support_reaction_ids=list(candidate.support_reaction_ids),
        support_lineage_ids=list(candidate.support_lineage_ids),
        transformation_family_id=candidate.transformation_family_id,
        typed_target_atom_or_bond_set=typed_targets,
        relaxation_policy_id=candidate.relaxation_policy_id,
        allowed_relaxation_ids=list(candidate.allowed_relaxation_ids),
        rationale_summary=candidate.rationale_summary,
        policy_version=candidate.policy_version,
    )

    _, edited = validate_agent_proposed_hypothesis(hypothesis, context)

    # the re-run recomputed the edited SMILES — it must match the stored value
    if edited.edited_smiles != candidate.edited_product_smiles:
        raise AgentProposedValidationError(
            f"recomputed edited_product_smiles {edited.edited_smiles!r} does not match "
            f"stored {candidate.edited_product_smiles!r} (embedded record is not trusted)"
        )


__all__ = [
    "AgentProposedValidationError",
    "AgentProposedRejectReasonCode",
    "CompiledGraphEdit",
    "EditedMolecule",
    "AgentProposedValidation",
    "AgentProposedCandidate",
    "QueryMoleculeContext",
    "LaneScopedCandidateLedger",
    "AgentProposedValidationContext",
    "compile_typed_targets",
    "apply_graph_edit",
    "validate_molecule",
    "validate_dual_ledger",
    "validate_grounding",
    "validate_agent_proposed_hypothesis",
    "build_agent_proposed_candidate",
    "revalidate_agent_proposed_candidate",
]
