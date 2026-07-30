"""P1-T7 SourceReactionLedger builder — contract tests.

Tests define the contract for:
- ``build_source_ledger(reaction_evidence, lineages) -> SourceReactionLedger``
  — builds the source reaction ledger from reaction evidence + resolved
  transformed lineages, filling all §10.1 fields.

Design references (final_design §10.1–§10.4, ADR-0003):
- §10.1: SourceReactionLedger field tree (reactant/product entries, roles,
  stoichiometry, formal atom transfer, mechanistic origin evidence, added
  atom sources, removed atom sinks, element/charge balance, H/proton/electron
  policies, cofactor changes, source/mapping completeness, balance status,
  unknowns, evidence IDs).
- §10.3: balance status vocabulary (fully_balanced_explicit_reaction /
  heavy_atom_balanced_with_implicit_h_e_policy / partial_or_unbalanced_source).
- §10.4: strict eligibility matrix — each new changed heavy atom must have a
  formal source assignment OR explicit unknown_source; when source is needed
  but untraceable, the record is NOT strict-eligible.
- ADR-0003: formal mapping ≠ mechanistic origin. Mapper output → formal
  assignment only; mechanistic origin requires independent evidence.

No-fabrication discipline (brief §13.4):
- Missing stoichiometry → unknown (NOT default 1 asserted as fact).
- Missing H+/e− → explicit policy (NOT silent fill to "balanced").
- Formal mapper → formal assignment (NOT promoted to proven mechanism).
- Unknown atom source → explicit ``unknown_source`` (NOT fabricated source).

Preflight BLOCKED (rdkit absent): element/charge balance real computation
needs rdkit. Tests use structured fixtures that encode the balance outcome
explicitly — the builder does NOT fabricate element counts. Charge balance
IS computable from ``formal_charge`` fields (no rdkit needed). Element
balance is marked ``rdkit_absent_proxy`` when rdkit is unavailable.

Zero-skip: no ``@pytest.mark.skipif``. When a dimension cannot be computed
(rdkit absent), the ledger records ``unknown`` / ``rdkit_absent_proxy`` with
an explicit unknowns entry — it does NOT skip.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.schemas.evidence import ReactionParticipant, RoleHypothesis
from reaction_agent.schemas.common import (
    MappingStatus,
    MappingQualityClass,
    SourceAssignmentMethod,
    ParticipantRole,
    LedgerBalanceStatus,
)
from reaction_agent.schemas.mapping import (
    MappingReport,
    FormalSourceAssignment,
    FormalMappedAtomPair,
    MechanisticAtomOrigin,
    MechanisticAtomPair,
)
from reaction_agent.schemas.ledger import (
    SourceReactionLedger,
    StoichiometricEntry,
    RoleAssignment,
    FormalAtomTransferAssignment,
    MechanisticOriginEvidence,
    AddedAtomSource,
    RemovedAtomSink,
    ElementBalance,
    CofactorChange,
)
from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
from reaction_agent.ledgers.source_builder import build_source_ledger


# =====================================================================
# Fixture helpers (all synthetic / curated — no real data fabricated)
# =====================================================================

def _role(role: str, score: float = 0.8) -> RoleHypothesis:
    """Build a RoleHypothesis for test fixtures."""
    return RoleHypothesis(role=ParticipantRole(role), score=score)


def _participant(
    participant_id: str,
    side: str,
    canonical_smiles: str = "C",
    molecule_id: str | None = None,
    stoichiometry: int | None = None,
    formal_charge: int = 0,
    mapped_fraction: float = 0.0,
    changed_atom_fraction: float = 0.0,
    atom_map_numbers: list[int] | None = None,
    role_hypotheses: list[RoleHypothesis] | None = None,
    provenance: list[str] | None = None,
) -> ReactionParticipant:
    """Deterministic ReactionParticipant for unit tests.

    If ``stoichiometry`` is None, it is NOT passed to the constructor — the
    pydantic default (1) applies, and ``model_fields_set`` will NOT include
    ``stoichiometry``. This lets the builder detect unverified stoichiometry
    (no-fabrication rule: missing stoichiometry → unknown, not default 1).
    """
    kwargs: dict = {
        "participant_id": participant_id,
        "molecule_id": molecule_id or f"mol_{participant_id}",
        "canonical_smiles": canonical_smiles,
        "side": side,
        "formal_charge": formal_charge,
        "mapped_fraction": mapped_fraction,
        "changed_atom_fraction": changed_atom_fraction,
        "atom_map_numbers": atom_map_numbers or [],
        "role_hypotheses": role_hypotheses or [],
    }
    if stoichiometry is not None:
        kwargs["stoichiometry"] = stoichiometry
    if provenance is not None:
        kwargs["provenance"] = provenance
    return ReactionParticipant(**kwargs)


def _atom_pair(
    reactant_pid: str, reactant_atom: int,
    product_pid: str, product_atom: int,
) -> FormalMappedAtomPair:
    return FormalMappedAtomPair(
        reactant_participant_id=reactant_pid,
        reactant_atom_map=reactant_atom,
        product_participant_id=product_pid,
        product_atom_map=product_atom,
    )


def _mapping_report(
    pairs: list[FormalMappedAtomPair],
    *,
    status: str = "fully_mapped",
    fallback: str | None = None,
    input_hash: str = "rh_test_0001",
    ambiguity: bool = False,
    mechanistic_origin: MechanisticAtomOrigin | None = None,
) -> MappingReport:
    """Build a deterministic MappingReport with formal atom pairs.

    Formal mapping only — mechanistic_atom_origin is None unless explicitly
    provided (ADR-0003: mapper never auto-populates mechanism).
    """
    kwargs: dict = {
        "mapper_name": "test_mapper",
        "mapper_version": "1.0",
        "input_hash": input_hash,
        "output_hash": f"{input_hash}_out",
        "mapping_status": MappingStatus(status),
        "mapped_heavy_atom_fraction": 1.0 if status == "fully_mapped" else 0.6,
        "map_number_uniqueness": True,
        "changed_atom_coverage": 1.0,
        "formal_mapped_source_assignment": FormalSourceAssignment(
            mapper_name="test_mapper",
            mapper_version="1.0",
            mapped_atom_pairs=pairs,
            assignment_method=SourceAssignmentMethod.formal_mapped,
            assignment_quality=MappingQualityClass.high_quality,
            assignment_ambiguity=ambiguity,
        ),
    }
    if fallback is not None:
        kwargs["fallback_method"] = fallback
    if mechanistic_origin is not None:
        kwargs["mechanistic_atom_origin"] = mechanistic_origin
    return MappingReport(**kwargs)


def _reaction_evidence(
    participants: list[ReactionParticipant],
    mapping_report: MappingReport | None = None,
    *,
    reaction_id: str = "rxn_001",
    provenance: list[str] | None = None,
) -> "ReactionEvidence":
    """Build a ReactionEvidence with participants + optional mapping."""
    from reaction_agent.schemas.evidence import ReactionEvidence
    kwargs: dict = {
        "reaction_id": reaction_id,
        "source_record_id": f"src_{reaction_id}",
        "source_name": "test_source",
        "raw_reaction": "A>>B",
        "normalized_reaction": "A>>B",
        "participants": participants,
    }
    if mapping_report is not None:
        kwargs["mapping_report"] = mapping_report
    if provenance is not None:
        kwargs["provenance"] = provenance
    return ReactionEvidence(**kwargs)


def _lineage(
    reactant_pid: str,
    product_pid: str,
    atom_maps: list[int] | None = None,
    *,
    ambiguity: str = "none",
    lineage_id: str | None = None,
) -> ResolvedTransformedLineage:
    """Build a resolved transformed lineage for fixture."""
    return ResolvedTransformedLineage(
        lineage_id=lineage_id or f"lin_{reactant_pid}_{product_pid}",
        reactant_participant_id=reactant_pid,
        product_participant_id=product_pid,
        ambiguity=ambiguity,
        transformed_atom_maps=atom_maps or [],
    )


# =====================================================================
# §13.5 Test 1: redox — cofactor change recorded, balance reflects redox
# =====================================================================

def test_redox_cofactor_change_recorded():
    """Redox reaction: NAD+ → NADH cofactor change is recorded in the ledger.

    The ledger must record the cofactor_changes entry (oxidized/reduced forms,
    direction) and set electron_policy to reflect the implicit redox policy
    (NOT silently "balanced").
    """
    nad_plus_smiles = (
        "NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O"
        "[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1"
    )
    nadh_smiles = (
        "NC(=O)c1ccc[nH]1"  # simplified NADH nicotinamide fragment
    )
    sub = _participant("p1", "reactant", "CCO", stoichiometry=1,
                       mapped_fraction=0.9, changed_atom_fraction=0.3,
                       provenance=["src"])
    nad_plus = _participant("p2", "reactant", nad_plus_smiles,
                            stoichiometry=1, provenance=["src"],
                            role_hypotheses=[_role("carrier")])
    prod = _participant("p3", "product", "CC(=O)O", stoichiometry=1,
                        mapped_fraction=0.9, changed_atom_fraction=0.3,
                        provenance=["src"])
    nadh = _participant("p4", "product", nadh_smiles, stoichiometry=1,
                        provenance=["src"],
                        role_hypotheses=[_role("carrier")])
    mr = _mapping_report([_atom_pair("p1", 1, "p3", 1)])
    ev = _reaction_evidence([sub, nad_plus, prod, nadh], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p3", [1])])
    # Cofactor change recorded (NAD+ → NADH direction)
    assert len(ledger.cofactor_changes) >= 1
    cc = ledger.cofactor_changes[0]
    assert cc.direction in ("reduction", "unknown")
    # Electron policy is explicit (not silent "balanced")
    assert ledger.electron_policy != "balanced"
    assert "electron" in ledger.electron_policy or "redox" in ledger.electron_policy \
           or ledger.electron_policy == "unknown"


# =====================================================================
# §13.5 Test 2: O2 incorporation — O2 as formal atom source
# =====================================================================

def test_o2_incorporation_formal_source():
    """O2 incorporation: O2 is recorded as a formal atom source.

    O2 contributes an O atom to the product. The ledger must record this in
    added_atom_sources with formal_assignment=True (formal mapping, NOT
    mechanistic proof). O2 is NOT deleted (§11.3).
    """
    proline = _participant("p1", "reactant", "OC(=O)[C@@H]1CCCN1",
                           stoichiometry=1, mapped_fraction=0.9,
                           atom_map_numbers=[1, 2, 3], provenance=["src"])
    o2 = _participant("p2", "reactant", "O=O", stoichiometry=1,
                      provenance=["src"])
    hydroxyproline = _participant("p3", "product", "OC(=O)[C@@H]1CC[C@H](O)N1",
                                  stoichiometry=1, mapped_fraction=0.9,
                                  atom_map_numbers=[1, 2, 3, 4],
                                  provenance=["src"])
    mr = _mapping_report([
        _atom_pair("p1", 1, "p3", 1),
        _atom_pair("p1", 2, "p3", 2),
        _atom_pair("p2", 4, "p3", 4),  # O2 contributes atom 4
    ])
    ev = _reaction_evidence([proline, o2, hydroxyproline], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p3", [1, 2, 3])])
    # O2 participant preserved (not deleted)
    pids = {e.participant_id for e in ledger.reactant_entries}
    assert "p2" in pids
    # Added atom source records the O2 contribution (formal, not mechanistic)
    o2_sources = [s for s in ledger.added_atom_sources
                  if s.source_participant_id == "p2"]
    assert len(o2_sources) >= 1
    assert all(s.formal_assignment for s in o2_sources)


# =====================================================================
# §13.5 Test 3: hydrolysis — H2O as reactant participant
# =====================================================================

def test_hydrolysis_h2o_preserved_and_sourced():
    """Hydrolysis: H2O participates and its atom contribution is recorded.

    H2O is NOT deleted (§11.3). If H2O contributes an atom via formal mapping,
    it appears in added_atom_sources. The ledger preserves H2O as a reactant.
    """
    ester = _participant("p1", "reactant", "CC(=O)OC", stoichiometry=1,
                         mapped_fraction=0.9, atom_map_numbers=[1, 2, 3],
                         provenance=["src"])
    h2o = _participant("p2", "reactant", "O", stoichiometry=1,
                       provenance=["src"])
    acid = _participant("p3", "product", "CC(=O)O", stoichiometry=1,
                        mapped_fraction=0.9, atom_map_numbers=[1, 2, 4],
                        provenance=["src"])
    mr = _mapping_report([
        _atom_pair("p1", 1, "p3", 1),
        _atom_pair("p1", 2, "p3", 2),
        _atom_pair("p2", 4, "p3", 4),  # H2O contributes O
    ])
    ev = _reaction_evidence([ester, h2o, acid], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p3", [1, 2])])
    # H2O preserved as reactant
    reactant_pids = {e.participant_id for e in ledger.reactant_entries}
    assert "p2" in reactant_pids
    # H2O atom contribution recorded
    h2o_sources = [s for s in ledger.added_atom_sources
                   if s.source_participant_id == "p2"]
    assert len(h2o_sources) >= 1


# =====================================================================
# §13.5 Test 4: decarboxylation — CO2 as coproduct, removed atoms sinked
# =====================================================================

def test_decarboxylation_co2_coproduct_and_sink():
    """Decarboxylation: CO2 is a coproduct; removed carboxyl atoms are sinked.

    The ledger must preserve CO2 as a product entry and record removed atom
    sinks for atoms that left the main substrate. CO2 has NO lineage (the
    mapper did not trace p1→p3), so its atoms must get explicit
    ``unknown_source`` entries (§10.4 gap fix) and balance_status must
    downgrade to ``partial_or_unbalanced_source`` (not strict-eligible).
    """
    substrate = _participant("p1", "reactant", "OC(=O)CCCO", stoichiometry=1,
                             mapped_fraction=0.9, atom_map_numbers=[1, 2, 3, 4],
                             provenance=["src"])
    product = _participant("p2", "product", "CCCO", stoichiometry=1,
                           mapped_fraction=0.9, atom_map_numbers=[3, 4],
                           provenance=["src"])
    # CO2 carries the carboxyl atoms [1, 2] that left the substrate. It has NO
    # lineage (mapper only traced p1→p2), so its atoms are unlineaged.
    co2 = _participant("p3", "product", "O=C=O", stoichiometry=1,
                       provenance=["src"], atom_map_numbers=[1, 2])
    mr = _mapping_report([
        _atom_pair("p1", 3, "p2", 3),
        _atom_pair("p1", 4, "p2", 4),
    ])
    ev = _reaction_evidence([substrate, product, co2], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [3, 4])])
    # CO2 preserved as product
    product_pids = {e.participant_id for e in ledger.product_entries}
    assert "p3" in product_pids
    # Removed atoms (1, 2 — carboxyl) recorded in removed_atom_sinks
    sink_atoms = {s.atom_map_number for s in ledger.removed_atom_sinks}
    assert 1 in sink_atoms or 2 in sink_atoms
    # CO2's unlineaged atoms get unknown_source (§10.4 gap fix)
    co2_unknown_sources = [
        s for s in ledger.added_atom_sources
        if s.source_participant_id == "unknown_source"
    ]
    co2_unknown_atoms = {s.atom_map_number for s in co2_unknown_sources}
    assert 1 in co2_unknown_atoms
    assert 2 in co2_unknown_atoms
    # Balance status downgraded — CO2 atoms untraceable → not strict-eligible
    assert ledger.balance_status == \
        LedgerBalanceStatus.partial_or_unbalanced_source


# =====================================================================
# §13.5 Test 5: transfer — formal atom transfer assignment recorded
# =====================================================================

def test_transfer_formal_assignment_recorded():
    """Transfer reaction: formal atom transfer assignments are recorded.

    The formal mapping pairs become FormalAtomTransferAssignment entries.
    These are FORMAL (assignment_method="formal"), NOT mechanistic.
    """
    donor = _participant("p1", "reactant", "CC(=O)S", stoichiometry=1,
                         mapped_fraction=0.9, atom_map_numbers=[1, 2, 3],
                         provenance=["src"])
    acceptor = _participant("p2", "reactant", "NC", stoichiometry=1,
                            atom_map_numbers=[4], provenance=["src"])
    product = _participant("p3", "product", "CC(=O)NC", stoichiometry=1,
                           mapped_fraction=0.9,
                           atom_map_numbers=[1, 2, 3, 4], provenance=["src"])
    mr = _mapping_report([
        _atom_pair("p1", 1, "p3", 1),
        _atom_pair("p1", 2, "p3", 2),
        _atom_pair("p1", 3, "p3", 3),
        _atom_pair("p2", 4, "p3", 4),
    ])
    ev = _reaction_evidence([donor, acceptor, product], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p3", [1, 2, 3])])
    # Formal atom transfer assignments present
    assert len(ledger.formal_atom_transfer_assignments) >= 1
    fata = ledger.formal_atom_transfer_assignments[0]
    assert fata.assignment_method == "formal"
    assert len(fata.transferred_atom_map_numbers) >= 1


# =====================================================================
# §13.5 Test 6: charge mismatch — balance status reflects imbalance
# =====================================================================

def test_charge_mismatch_yields_partial_balance():
    """Charge mismatch: reactant/product charges don't balance → partial.

    Reactants have total charge +2, products have total charge 0.
    The ledger must record charge_balance != 0 and set balance_status to
    partial_or_unbalanced_source.
    """
    r1 = _participant("p1", "reactant", "C", stoichiometry=1,
                      formal_charge=2, provenance=["src"])
    p1 = _participant("p2", "product", "C", stoichiometry=1,
                      formal_charge=0, provenance=["src"])
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    assert ledger.charge_balance != 0
    assert ledger.balance_status == \
        LedgerBalanceStatus.partial_or_unbalanced_source


# =====================================================================
# §13.5 Test 7: missing stoichiometry → unknown (not default 1 as fact)
# =====================================================================

def test_missing_stoichiometry_is_unknown_not_default_1():
    """Missing stoichiometry: the ledger records unknown, NOT default 1 as fact.

    When a participant is constructed WITHOUT explicit stoichiometry (pydantic
    default 1 applies), the ledger must NOT assert coefficient=1 as a proven
    fact. It records an unknowns entry and source_completeness reflects the
    gap. The StoichiometricEntry still carries the value (lossless) but the
    ledger flags it as unverified.
    """
    # stoichiometry NOT passed → defaults to 1, but model_fields_set excludes it
    r1 = _participant("p1", "reactant", "CCO")  # no stoichiometry, no provenance
    p1 = _participant("p2", "product", "CC(=O)O")
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    # Unknowns entry records the unverified stoichiometry
    unknowns_str = " ".join(ledger.unknowns)
    assert "stoichiometry" in unknowns_str.lower()
    # Source completeness is NOT "complete"
    assert ledger.source_completeness != "complete"


# =====================================================================
# §13.5 Test 8: incomplete source — source_completeness reflects gaps
# =====================================================================

def test_incomplete_source_completeness():
    """Incomplete source: when participants lack provenance, source is incomplete.

    The ledger must set source_completeness to "incomplete" (or "unknown"),
    never silently "complete".
    """
    # Participants without provenance — source annotation missing
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1)
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1)
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    assert ledger.source_completeness in ("incomplete", "unknown")
    assert ledger.source_completeness != "complete"


# =====================================================================
# §13.5 Test 9: ambiguous formal assignment — ambiguity flagged
# =====================================================================

def test_ambiguous_formal_assignment_flagged():
    """Ambiguous formal assignment: assignment_ambiguity is recorded.

    When the mapping report flags assignment_ambiguity=True, the ledger must
    record ``formal_assignment_ambiguous`` in unknowns and downgrade
    balance_status to ``partial_or_unbalanced_source`` (ambiguity prevents
    strict eligibility — §10.3/§10.4).
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    mr = _mapping_report(
        [_atom_pair("p1", 1, "p2", 1), _atom_pair("p1", 2, "p2", 2)],
        ambiguity=True,
    )
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1, 2])])
    # Ambiguity recorded precisely in unknowns
    assert "formal_assignment_ambiguous" in " ".join(ledger.unknowns)
    # Ambiguity downgrades balance_status to partial (not strict-eligible)
    assert ledger.balance_status == \
        LedgerBalanceStatus.partial_or_unbalanced_source


# =====================================================================
# §13.5 Test 10: unknown atom source — not strict eligible
# =====================================================================

def test_unknown_atom_source_not_strict():
    """Unknown atom source: a changed heavy atom with no formal source →
    explicit unknown_source, and balance_status is NOT fully_balanced.

    §10.4: each new changed heavy atom must have a formal source assignment
    OR explicit unknown_source. When source is needed but untraceable, the
    record is NOT strict-eligible (partial_or_unbalanced_source).
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2],
                      mapped_fraction=0.5)  # partial mapping
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2, 3],
                      mapped_fraction=0.5, changed_atom_fraction=0.3)
    # Atom 3 in product has NO formal source (not in mapping pairs)
    mr = _mapping_report(
        [_atom_pair("p1", 1, "p2", 1), _atom_pair("p1", 2, "p2", 2)],
        status="partially_mapped",
    )
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1, 2])])
    # Added atom sources include an unknown_source entry for atom 3
    unknown_sources = [s for s in ledger.added_atom_sources
                       if s.source_participant_id == "unknown_source"]
    assert len(unknown_sources) >= 1
    assert all(not s.formal_assignment for s in unknown_sources)
    # Balance status is NOT fully_balanced (unknown source blocks strict)
    assert ledger.balance_status == \
        LedgerBalanceStatus.partial_or_unbalanced_source


# =====================================================================
# §10.4 gap: unlineaged product atoms — unknown_source (I1 fix)
# =====================================================================

def test_unlineaged_product_atoms_get_unknown_source():
    """Unlineaged product atoms: a product NOT in any lineage must still have
    its atoms checked for formal mapping source.

    §10.4 gap (I1): previously, only products appearing in a lineage had their
    atoms checked. A product with NO lineage (e.g. decarboxylation CO2
    coproduct) was silently skipped — its atoms were never checked for a
    formal source, so the record was incorrectly marked strict-eligible
    (heavy_atom_balanced) even though those atoms have no traceable source.

    Fix: atoms of unlineaged products without a formal mapping pair get
    explicit ``unknown_source`` entries + unknowns record, and
    ``_determine_balance_status`` downgrades accordingly (not strict).
    """
    # Reactant p1 with atoms [1, 2]; product p2 (in lineage) with atoms [1, 2].
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    p2 = _participant("p2", "product", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    # Coproduct p3 (NO lineage) with atoms [3, 4] — no formal mapping source.
    p3 = _participant("p3", "product", "O=C=O", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[3, 4])
    # Mapping only traces p1 → p2; p3's atoms are unmapped.
    mr = _mapping_report([
        _atom_pair("p1", 1, "p2", 1),
        _atom_pair("p1", 2, "p2", 2),
    ])
    ev = _reaction_evidence([r1, p2, p3], mr)
    # Only lineage is p1 → p2; p3 is NOT in any lineage.
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1, 2])])
    # p3's atoms (3, 4) must get explicit unknown_source entries
    unknown_sources = [
        s for s in ledger.added_atom_sources
        if s.source_participant_id == "unknown_source"
    ]
    unknown_atoms = {s.atom_map_number for s in unknown_sources}
    assert 3 in unknown_atoms
    assert 4 in unknown_atoms
    assert all(not s.formal_assignment for s in unknown_sources)
    # Unknowns list records the gap
    unknowns_str = " ".join(ledger.unknowns)
    assert "unknown_atom_source:p3:atom_3" in unknowns_str
    assert "unknown_atom_source:p3:atom_4" in unknowns_str
    # Balance status downgraded (not strict-eligible)
    assert ledger.balance_status == \
        LedgerBalanceStatus.partial_or_unbalanced_source


# =====================================================================
# §13.5 Test 11: mechanistic evidence absent — formal only
# =====================================================================

def test_mechanistic_evidence_absent_formal_only():
    """Mechanistic evidence absent: formal mapping only, no mechanistic origin.

    When the mapping report has NO mechanistic_atom_origin (the default —
    mapper never auto-populates it), the ledger must leave
    mechanistic_origin_evidence empty. Formal assignments are present but
    are NOT promoted to mechanistic proof.
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1])
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    # mechanistic_atom_origin is None (default)
    assert mr.mechanistic_atom_origin is None
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    # Formal assignments present
    assert len(ledger.formal_atom_transfer_assignments) >= 1
    # Mechanistic origin evidence is EMPTY (not fabricated from formal)
    assert ledger.mechanistic_origin_evidence == []


# =====================================================================
# §13.5 Test 12: unbound mechanistic evidence reject
# =====================================================================

def test_unbound_mechanistic_evidence_rejected():
    """Unbound mechanistic evidence: evidence IDs without mechanistic object
    are rejected by the MappingReport schema (ADR-0003 §12).

    The ledger builder consumes a valid MappingReport; the schema itself
    enforces that mechanistic_origin_evidence_ids non-empty requires
    mechanistic_atom_origin. This test verifies the schema rejects the
    unbound case, so the builder never sees an invalid input.
    """
    with pytest.raises(ValidationError, match="unbound|mechanistic"):
        MappingReport(
            mapper_name="test", mapper_version="1.0",
            input_hash="abc", output_hash="def",
            mapping_status=MappingStatus.fully_mapped,
            mapped_heavy_atom_fraction=1.0,
            map_number_uniqueness=True,
            changed_atom_coverage=1.0,
            mechanistic_origin_evidence_ids=["ev1"],  # non-empty
            # mechanistic_atom_origin is None → unbound → rejected
        )


# =====================================================================
# §13.5 Test 13: complete participant preservation
# =====================================================================

def test_complete_participant_preservation():
    """Complete participant preservation: every participant appears in the ledger.

    §11.1/§11.5: the complete participant set is traceable — no loss. The
    ledger's reactant_entries + product_entries must include every input
    participant_id. This holds even for cofactors, carriers, and small
    molecules (§11.3: COFACTORS is not destructive).
    """
    ps = [
        _participant("p1", "reactant", "OC(=O)[C@@H]1CCCN1", stoichiometry=1,
                     provenance=["src"]),
        _participant("p2", "reactant", "OC(=O)C(=O)CCC(=O)O", stoichiometry=1,
                     provenance=["src"]),
        _participant("p3", "reactant", "O=O", stoichiometry=1,
                     provenance=["src"]),  # O2
        _participant("p4", "product", "OC(=O)[C@@H]1CC[C@H](O)N1",
                     stoichiometry=1, provenance=["src"]),
        _participant("p5", "product", "OC(=O)CCC(=O)O", stoichiometry=1,
                     provenance=["src"]),
        _participant("p6", "product", "O=C=O", stoichiometry=1,
                     provenance=["src"]),  # CO2
    ]
    mr = _mapping_report([
        _atom_pair("p1", 1, "p4", 1),
        _atom_pair("p2", 5, "p5", 5),
    ])
    ev = _reaction_evidence(ps, mr)
    ledger = build_source_ledger(
        ev, [_lineage("p1", "p4", [1]), _lineage("p2", "p5", [5])])
    # Every participant appears in reactant_entries or product_entries
    ledger_pids = (
        {e.participant_id for e in ledger.reactant_entries}
        | {e.participant_id for e in ledger.product_entries}
    )
    input_pids = {p.participant_id for p in ps}
    assert ledger_pids == input_pids  # no loss, no fabrication


# =====================================================================
# Brief skeleton tests: balance status typed, H+ policy, formal≠mechanism
# =====================================================================

def test_balance_status_typed():
    """balance_status is a LedgerBalanceStatus enum value (§10.3 vocabulary)."""
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"])
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    assert isinstance(ledger.balance_status, LedgerBalanceStatus)
    assert ledger.balance_status in (
        LedgerBalanceStatus.fully_balanced_explicit_reaction,
        LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        LedgerBalanceStatus.partial_or_unbalanced_source,
    )


def test_missing_h_plus_has_policy_not_silent_fill():
    """Missing H+/e− → explicit policy, not silent fill to "balanced".

    The hydrogen_policy / proton_policy / electron_policy fields must never
    be silently set to "balanced" when H+/e− balance is not explicitly
    verified. They must be "unknown" or an explicit implicit-policy label.
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    # Policies are explicit (never silently "balanced")
    for policy in (ledger.hydrogen_policy, ledger.proton_policy,
                   ledger.electron_policy):
        assert policy != "balanced"
        assert isinstance(policy, str) and policy  # non-empty


def test_formal_mapper_not_mechanism():
    """Formal mapper output → formal assignment, NOT promoted to mechanism.

    The formal_atom_transfer_assignments use assignment_method="formal".
    The mechanistic_origin_evidence list is empty unless independent
    evidence exists (ADR-0003).
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2])
    mr = _mapping_report([
        _atom_pair("p1", 1, "p2", 1),
        _atom_pair("p1", 2, "p2", 2),
    ])
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1, 2])])
    # Formal assignments use "formal" method
    for fata in ledger.formal_atom_transfer_assignments:
        assert fata.assignment_method == "formal"
    # No mechanistic evidence fabricated
    assert ledger.mechanistic_origin_evidence == []


# =====================================================================
# Additional contract tests: immutability, ID stability, empty input
# =====================================================================

def test_build_source_ledger_does_not_mutate_input():
    """Immutability: build_source_ledger must not mutate reaction_evidence."""
    import copy
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"])
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr)
    ev_snapshot = copy.deepcopy(ev)
    lineages = [_lineage("p1", "p2", [1])]
    lineages_snapshot = copy.deepcopy(lineages)
    build_source_ledger(ev, lineages)
    assert ev == ev_snapshot
    assert lineages == lineages_snapshot


def test_build_source_ledger_empty_participants():
    """Empty input: no participants → empty ledger, no fabrication."""
    ev = _reaction_evidence([], None)
    ledger = build_source_ledger(ev, [])
    assert ledger.reactant_entries == []
    assert ledger.product_entries == []
    assert ledger.balance_status == \
        LedgerBalanceStatus.partial_or_unbalanced_source


def test_build_source_ledger_returns_source_reaction_ledger():
    """build_source_ledger returns a SourceReactionLedger instance."""
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"])
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    assert isinstance(ledger, SourceReactionLedger)


def test_ledger_id_and_reaction_evidence_id_stable():
    """ledger_id and reaction_evidence_id are stable + non-empty."""
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"])
    mr = _mapping_report([_atom_pair("p1", 1, "p2", 1)])
    ev = _reaction_evidence([r1, p1], mr, reaction_id="rxn_stable_001")
    l1 = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    l2 = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    assert l1.ledger_id == l2.ledger_id  # deterministic
    assert l1.reaction_evidence_id == "rxn_stable_001"
    assert l1.ledger_id.startswith("srl_")


def test_fully_balanced_explicit_reaction_status():
    """A fully-recorded, fully-mapped, charge-balanced reaction with all
    changed atoms sourced → fully_balanced_explicit_reaction.

    This is the positive case: complete provenance, explicit stoichiometry,
    fully mapped, charge balanced, all changed atoms have formal sources.
    H+/e− policy is implicit (heavy-atom balanced) but the reaction itself
    is explicit.
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      formal_charge=0, provenance=["src"],
                      atom_map_numbers=[1, 2], mapped_fraction=1.0)
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      formal_charge=0, provenance=["src"],
                      atom_map_numbers=[1, 2], mapped_fraction=1.0)
    mr = _mapping_report([
        _atom_pair("p1", 1, "p2", 1),
        _atom_pair("p1", 2, "p2", 2),
    ])
    ev = _reaction_evidence([r1, p1], mr, provenance=["src"])
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1, 2])])
    # All changed atoms have formal sources; charge balanced; stoichiometry explicit
    assert ledger.charge_balance == 0
    assert ledger.balance_status in (
        LedgerBalanceStatus.fully_balanced_explicit_reaction,
        LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
    )


def test_mechanistic_origin_evidence_recorded_when_present():
    """When the mapping report HAS mechanistic_atom_origin (independent
    evidence), the ledger records it in mechanistic_origin_evidence.

    This is the positive case: isotope tracing evidence exists → mechanistic
    origin is recorded (NOT fabricated from formal mapping).
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1])
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1])
    mo = MechanisticAtomOrigin(
        evidence_ids=["isotope_001"],
        evidence_type="isotope_tracing",
        mechanistic_atom_pairs=[MechanisticAtomPair(
            source_participant_id="p1", source_atom_identifier=1,
            target_participant_id="p2", target_atom_identifier=1,
            evidence_id="isotope_001",
        )],
    )
    mr = _mapping_report(
        [_atom_pair("p1", 1, "p2", 1)], mechanistic_origin=mo,
    )
    ev = _reaction_evidence([r1, p1], mr)
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1])])
    assert len(ledger.mechanistic_origin_evidence) >= 1
    mee = ledger.mechanistic_origin_evidence[0]
    assert mee.evidence_id == "isotope_001"
    assert mee.evidence_type == "isotope_tracing"


def test_no_unknowns_when_complete():
    """A complete reaction with full provenance has minimal unknowns.

    When all participants have provenance, stoichiometry is explicit, and
    mapping is fully_mapped, the unknowns list should not contain
    stoichiometry or source-completeness gaps.
    """
    r1 = _participant("p1", "reactant", "CCO", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2],
                      mapped_fraction=1.0)
    p1 = _participant("p2", "product", "CC(=O)O", stoichiometry=1,
                      provenance=["src"], atom_map_numbers=[1, 2],
                      mapped_fraction=1.0)
    mr = _mapping_report([
        _atom_pair("p1", 1, "p2", 1),
        _atom_pair("p1", 2, "p2", 2),
    ])
    ev = _reaction_evidence([r1, p1], mr, provenance=["src"])
    ledger = build_source_ledger(ev, [_lineage("p1", "p2", [1, 2])])
    unknowns_str = " ".join(ledger.unknowns).lower()
    assert "stoichiometry_unverified" not in unknowns_str
    assert "source_incomplete" not in unknowns_str
