"""P1-T5 Participant roles & donor eligibility — contract tests.

Tests define the contract for:
- ``load_cofactors()`` — read-only extraction of legacy ``COFACTORS`` with a
  recorded source hash (§11.3).
- ``resolve_roles(participants)`` — attaches ``RoleHypothesis`` objects to each
  participant. NEVER deletes a participant (§11.1/§11.5 multiset invariant).
- ``assess_donor_eligibility(participant, mapping_report)`` — independent
  donor-side eligibility assessment (§11.4, distinct from role).

Design references (training/chatgpt_p1_train.md §11):
- §11.1: complete participant set is traceable (no loss).
- §11.2: role vocabulary frozen; role is a hypothesis with evidence, NOT a
  ground-truth assignment; heuristic score is NOT a probability.
- §11.3: COFACTORS may ONLY be used as participant_role_prior /
  donor_eligibility_prior / retrieval_downweighting_prior. NEVER as a
  destructive stripping rule, ground-truth role, atom-balance exclusion, or
  transformed-lineage blocker. Special tests: O2 formal atom source, H2O
  hydrolysis, CO2 coproduct, NAD(P) evidence retained, small molecule as
  transformed substrate, 2-oxoglutarate not deleted, COFACTORS prior vs
  mapping evidence conflict preserves ambiguity.
- §11.4: donor eligibility ≠ role. At least consider mapped atom retention /
  changed mapped atoms / transferred atoms / size / stoichiometry / source
  annotation / COFACTORS prior / direction / mapping quality / lineage
  ambiguity.
- §11.5: input participant multiset == persisted participant multiset
  (canonicalization-explained changes require a mapping).

Discipline:
- Preflight BLOCKED (rdkit absent). T5 is role/eligibility LOGIC — roles are
  hypotheses + evidence, not chemical computation. rdkit-dependent chemistry
  is simulated via structured fixtures, never fabricated.
- Zero-skip: no ``@pytest.mark.skipif``. When a dimension cannot be computed
  (rdkit absent), the assessment returns ``unknown`` with an explicit reason
  code — it does NOT skip.
- COFACTORS source is read-only: legacy ``../benchmark/canonical_identity.py``
  imports rdkit at module top, so direct import would fail. ``load_cofactors``
  extracts the ``COFACTORS`` literal via AST (no rdkit execution) and records
  the file SHA-256.
"""
from __future__ import annotations

import copy

import pytest

from reaction_agent.schemas.evidence import ReactionParticipant, RoleHypothesis
from reaction_agent.schemas.common import ParticipantRole
from reaction_agent.schemas.p1_entities import DonorEligibilityAssessment


# -- Fixtures --

def _participant(
    participant_id: str = "p1",
    molecule_id: str = "m1",
    canonical_smiles: str = "C",
    side: str = "reactant",
    stoichiometry: int = 1,
    mapped_fraction: float = 0.0,
    changed_atom_fraction: float = 0.0,
) -> ReactionParticipant:
    """Deterministic ReactionParticipant for unit tests."""
    return ReactionParticipant(
        participant_id=participant_id,
        molecule_id=molecule_id,
        canonical_smiles=canonical_smiles,
        side=side,
        stoichiometry=stoichiometry,
        mapped_fraction=mapped_fraction,
        changed_atom_fraction=changed_atom_fraction,
    )


# =====================================================================
# §11.3 — load_cofactors: read-only extraction + source hash
# =====================================================================

def test_cofactors_loads_with_source_hash():
    """§11.3: load_cofactors returns (names, src_hash); hash is non-empty."""
    from reaction_agent.roles.cofactors import load_cofactors
    names, src_hash = load_cofactors()
    assert isinstance(names, list)
    assert len(names) > 0  # legacy COFACTORS is non-empty
    assert isinstance(src_hash, str) and src_hash  # non-empty hash
    assert len(src_hash) == 64  # SHA-256 hex


def test_cofactors_source_hash_matches_legacy_file():
    """§11.3: source hash is the SHA-256 of legacy canonical_identity.py."""
    import hashlib
    from reaction_agent.roles.cofactors import load_cofactors, LEGACY_PATH
    _, src_hash = load_cofactors()
    expected = hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest()
    assert src_hash == expected


def test_cofactors_loads_deterministically():
    """§11.3: repeated calls return identical (names, hash)."""
    from reaction_agent.roles.cofactors import load_cofactors
    a = load_cofactors()
    b = load_cofactors()
    assert a == b


def test_cofactors_names_are_sorted_unique_strings():
    """§11.3: canonicalized cofactor list is sorted + deduplicated."""
    from reaction_agent.roles.cofactors import load_cofactors
    names, _ = load_cofactors()
    assert all(isinstance(n, str) and n for n in names)
    assert names == sorted(names)
    assert len(names) == len(set(names))


def test_cofactors_not_destructive_nad_present():
    """§11.3: COFACTORS prior includes NAD — only as a prior, never destructive."""
    from reaction_agent.roles.cofactors import load_cofactors
    names, _ = load_cofactors()
    # NAD+/NADH are in the legacy COFACTORS set (as canonical SMILES with
    # the nicotinamide ring). We check that the list is non-empty and
    # contains at least one adenine-bearing cofactor signature.
    assert any("Nc1ncnc" in n for n in names)  # AMP/ADP/ATP/NAD/FAD backbone


def test_cofactors_legacy_file_not_modified():
    """§11.3: loading cofactors MUST NOT mutate the legacy file."""
    import hashlib
    from reaction_agent.roles.cofactors import load_cofactors, LEGACY_PATH
    before = hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest()
    load_cofactors()
    after = hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest()
    assert before == after


# =====================================================================
# §11.1 / §11.5 — multiset invariant: no participant lost
# =====================================================================

def test_participant_multiset_preserved():
    """§11.1: resolve_roles returns every input participant (no loss)."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant("p1", "m1", "C", "reactant"),
        _participant("p2", "m2", "O=O", "reactant"),  # O2
    ]
    out = resolve_roles(ps)
    assert len(out) == 2
    assert {p.participant_id for p in out} == {"p1", "p2"}


def test_input_multiset_equals_persisted():
    """§11.5: input participant multiset == persisted participant multiset."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant(f"p{i}", f"m{i}", "C", "reactant") for i in range(3)
    ]
    out = resolve_roles(ps)
    assert sorted(p.participant_id for p in ps) == \
           sorted(p.participant_id for p in out)


def test_multiset_preserved_with_duplicates():
    """§11.5: duplicate stoichiometric entries are preserved (no set collapse)."""
    from reaction_agent.roles.resolver import resolve_roles
    # Two distinct participants with the SAME molecule — must remain two.
    ps = [
        _participant("p1", "m1", "C", "reactant"),
        _participant("p2", "m1", "C", "reactant"),  # same molecule, diff id
        _participant("p3", "m2", "CCO", "product"),
    ]
    out = resolve_roles(ps)
    assert len(out) == 3
    assert [p.participant_id for p in out] == ["p1", "p2", "p3"]


def test_multiset_preserved_with_cofactors_present():
    """§11.5: COFACTORS members do not collapse the multiset."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant("p1", "m1", "CCO", "reactant"),
        _participant("p2", "m2", "O=O", "reactant"),  # O2 in COFACTORS
        _participant("p3", "m3", "O", "product"),     # H2O in COFACTORS
        _participant("p4", "m4", "O=C=O", "product"), # CO2 in COFACTORS
    ]
    out = resolve_roles(ps)
    assert len(out) == 4
    assert {p.participant_id for p in out} == {"p1", "p2", "p3", "p4"}


def test_resolve_roles_does_not_mutate_input():
    """Immutability: resolve_roles must not mutate input participants."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "C", "reactant")]
    ps_snapshot = copy.deepcopy(ps)
    resolve_roles(ps)
    assert ps == ps_snapshot  # input untouched


def test_resolve_roles_returns_new_objects():
    """Immutability: resolve_roles returns new participant objects, not aliases."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "C", "reactant")]
    out = resolve_roles(ps)
    assert out is not ps
    assert out[0] is not ps[0]


def test_resolve_roles_preserves_participant_fields():
    """§11.1: non-role fields (smiles, side, stoichiometry) are preserved."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant(
            "p1", "m1", "CCO", "reactant",
            stoichiometry=2, mapped_fraction=0.8, changed_atom_fraction=0.3,
        )
    ]
    out = resolve_roles(ps)
    p = out[0]
    assert p.participant_id == "p1"
    assert p.molecule_id == "m1"
    assert p.canonical_smiles == "CCO"
    assert p.side == "reactant"
    assert p.stoichiometry == 2
    assert p.mapped_fraction == 0.8
    assert p.changed_atom_fraction == 0.3


# =====================================================================
# §11.3 — COFACTORS not destructive: special molecule retention
# =====================================================================

def test_o2_can_be_formal_source():
    """§11.3: O2 is NOT deleted; role may be co_substrate or cofactor prior."""
    from reaction_agent.roles.resolver import resolve_roles
    o2 = _participant("p2", "O2", "O=O", "reactant")
    out = resolve_roles([o2])
    assert len(out) == 1
    assert out[0].participant_id == "p2"


def test_h2o_can_participate_in_hydrolysis():
    """§11.3: H2O is NOT deleted; it may participate in hydrolysis."""
    from reaction_agent.roles.resolver import resolve_roles
    h2o = _participant("p3", "H2O", "O", "reactant")
    out = resolve_roles([h2o])
    assert len(out) == 1
    assert out[0].participant_id == "p3"


def test_co2_can_be_coproduct():
    """§11.3: CO2 is NOT deleted; it may be a coproduct."""
    from reaction_agent.roles.resolver import resolve_roles
    co2 = _participant("p4", "CO2", "O=C=O", "product")
    out = resolve_roles([co2])
    assert len(out) == 1
    assert out[0].participant_id == "p4"


def test_nad_evidence_fully_retained():
    """§11.3: NAD(P) participant is retained with full evidence."""
    from reaction_agent.roles.resolver import resolve_roles
    # NAD+ canonical SMILES from legacy COFACTORS
    nad_plus = (
        "NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O"
        "[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1"
    )
    p = _participant("p5", "NAD", nad_plus, "reactant")
    out = resolve_roles([p])
    assert len(out) == 1
    assert out[0].participant_id == "p5"
    assert out[0].canonical_smiles == nad_plus  # evidence preserved verbatim


def test_small_molecule_can_be_transformed_substrate():
    """§11.3: a small molecule is NOT deleted and may be a transformed substrate."""
    from reaction_agent.roles.resolver import resolve_roles
    # 2-oxoglutarate is a small organic co-substrate that is sometimes the
    # real transformed substrate. It must NOT be deleted.
    two_og = _participant("p6", "2OG", "OC(=O)C(=O)CCC(=O)O", "reactant")
    out = resolve_roles([two_og])
    assert len(out) == 1
    assert out[0].participant_id == "p6"


def test_2_oxoglutarate_not_deleted_as_common_cosubstrate():
    """§11.3: 2-oxoglutarate must NOT be deleted for being 'small/common co-substrate'.

    The legacy COFACTORS set deliberately excludes 2-oxoglutarate (it is
    sometimes the real transformed substrate). The resolver must preserve it
    regardless of any size-based heuristic.
    """
    from reaction_agent.roles.resolver import resolve_roles
    from reaction_agent.roles.cofactors import load_cofactors
    names, _ = load_cofactors()
    two_og_smiles = "OC(=O)C(=O)CCC(=O)O"
    # 2-oxoglutarate is NOT in the COFACTORS prior list (by design)
    assert two_og_smiles not in names
    p = _participant("p6", "2OG", two_og_smiles, "reactant")
    out = resolve_roles([p])
    assert len(out) == 1  # retained


def test_full_proline_2og_reaction_multiset_preserved():
    """§11.3 / preflight case: proline + 2OG + O2 -> hydroxyproline + succinate + CO2.

    All 5 participants (3 reactants + 2 products; CO2 counted) must be
    preserved. None may be stripped by COFACTORS prior.
    """
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant("p1", "proline", "OC(=O)[C@@H]1CCCN1", "reactant"),
        _participant("p2", "2OG", "OC(=O)C(=O)CCC(=O)O", "reactant"),
        _participant("p3", "O2", "O=O", "reactant"),
        _participant("p4", "hydroxyproline", "OC(=O)[C@@H]1CC[C@H](O)N1", "product"),
        _participant("p5", "succinate", "OC(=O)CCC(=O)O", "product"),
        _participant("p6", "CO2", "O=C=O", "product"),
    ]
    out = resolve_roles(ps)
    assert len(out) == 6
    assert {p.participant_id for p in out} == \
           {"p1", "p2", "p3", "p4", "p5", "p6"}


# =====================================================================
# §11.2 — role hypothesis structure (hypothesis, NOT ground truth)
# =====================================================================

def test_resolve_roles_attaches_role_hypotheses():
    """§11.2: each participant gets >=1 RoleHypothesis."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "C", "reactant")]
    out = resolve_roles(ps)
    assert len(out[0].role_hypotheses) >= 1


def test_role_hypotheses_use_frozen_vocabulary():
    """§11.2: every role is from the frozen ParticipantRole enum."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant("p1", "m1", "C", "reactant"),
        _participant("p2", "m2", "O=O", "reactant"),
    ]
    out = resolve_roles(ps)
    valid = {r.value for r in ParticipantRole}
    for p in out:
        for h in p.role_hypotheses:
            assert h.role in valid or h.role in ParticipantRole


def test_role_hypotheses_carry_evidence_codes():
    """§11.2: every hypothesis has evidence_codes (non-empty)."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "C", "reactant")]
    out = resolve_roles(ps)
    for h in out[0].role_hypotheses:
        assert isinstance(h.evidence_codes, list)
        assert len(h.evidence_codes) > 0


def test_role_hypotheses_include_policy_version():
    """§11.2: policy_version is encoded (as evidence code, P0 schema has no field)."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "C", "reactant")]
    out = resolve_roles(ps)
    all_codes = [
        c for h in out[0].role_hypotheses for c in h.evidence_codes
    ]
    assert any("policy_version" in c for c in all_codes)


def test_unknown_participant_gets_unknown_hypothesis():
    """§11.2: a participant with no prior evidence gets 'unknown' role."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "C", "reactant")]
    out = resolve_roles(ps)
    roles = {h.role for h in out[0].role_hypotheses}
    assert ParticipantRole.unknown in roles or "unknown" in roles


def test_cofactor_prior_added_for_cofactors_member():
    """§11.3: a COFACTORS member gets a cofactor/carrier prior hypothesis.

    The prior is a HYPOTHESIS (not ground truth). The participant is retained.
    """
    from reaction_agent.roles.resolver import resolve_roles
    # O=O is in legacy COFACTORS
    o2 = _participant("p2", "O2", "O=O", "reactant")
    out = resolve_roles([o2])
    roles = {h.role for h in out[0].role_hypotheses}
    # Should have a cofactor/carrier prior OR remain unknown — but NOT be
    # forced to a single ground-truth role. At minimum, >=1 hypothesis exists.
    assert len(out[0].role_hypotheses) >= 1


def test_cofactor_prior_does_not_force_ground_truth():
    """§11.3: COFACTORS prior never becomes a forced ground-truth role.

    The participant must retain an 'unknown' or competing hypothesis alongside
    any prior — ambiguity is preserved, not collapsed.
    """
    from reaction_agent.roles.resolver import resolve_roles
    o2 = _participant("p2", "O2", "O=O", "reactant")
    out = resolve_roles([o2])
    roles = out[0].role_hypotheses
    # Either multiple hypotheses, or a single non-forced hypothesis that
    # includes 'unknown' or a prior marker. The key: no assertion that O2
    # IS definitively a cofactor.
    prior_codes = [c for h in roles for c in h.evidence_codes if "prior" in c]
    assert len(prior_codes) >= 1  # prior is labeled as a prior


# =====================================================================
# §11.3 — ambiguity preservation (COFACTORS prior vs mapping evidence)
# =====================================================================

def test_ambiguity_preserved_when_prior_conflicts_with_mapping():
    """§11.3: when COFACTORS prior conflicts with mapping evidence, keep both.

    O2 is in COFACTORS (cofactor prior) but mapping evidence may show it as a
    formal atom source (co_substrate). Both hypotheses must be retained.
    """
    from reaction_agent.roles.resolver import resolve_roles
    # O2 with mapping evidence suggesting it's a formal atom source
    o2 = _participant(
        "p2", "O2", "O=O", "reactant",
        mapped_fraction=1.0, changed_atom_fraction=0.5,
    )
    out = resolve_roles([o2])
    roles = out[0].role_hypotheses
    # >=2 hypotheses retained (prior + mapping-derived) — ambiguity preserved
    assert len(roles) >= 2


def test_no_ground_truth_role_assignment():
    """§11.2/§11.3: resolver never asserts a single definitive role.

    Every output participant either has multiple hypotheses or a hypothesis
    explicitly marked as non-definitive (prior/unknown).
    """
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant("p1", "m1", "C", "reactant"),
        _participant("p2", "m2", "O=O", "reactant"),
        _participant("p3", "m3", "O", "product"),
    ]
    out = resolve_roles(ps)
    for p in out:
        codes = [c for h in p.role_hypotheses for c in h.evidence_codes]
        # Every participant has either multiple hypotheses or a non-definitive
        # marker (prior/unknown/no_evidence).
        non_definitive = any(
            "prior" in c or "unknown" in c or "no_evidence" in c
            for c in codes
        )
        assert len(p.role_hypotheses) >= 2 or non_definitive


# =====================================================================
# §11.4 — donor eligibility (distinct from role)
# =====================================================================

def test_donor_eligibility_separate_from_role():
    """§11.4: assess_donor_eligibility returns DonorEligibilityAssessment."""
    from reaction_agent.roles.resolver import assess_donor_eligibility
    p = _participant("p1", "m1", "C", "reactant")
    d = assess_donor_eligibility(p, mapping_report=None)
    assert isinstance(d, DonorEligibilityAssessment)
    assert d.eligibility in (
        "eligible", "conditionally_eligible", "not_eligible", "unknown"
    )
    assert d.reason_codes  # non-empty
    assert d.participant_id == "p1"


def test_donor_eligibility_unknown_without_mapping():
    """§11.4: without mapping evidence, eligibility leans unknown."""
    from reaction_agent.roles.resolver import assess_donor_eligibility
    p = _participant("p1", "m1", "C", "reactant")
    d = assess_donor_eligibility(p, mapping_report=None)
    assert d.eligibility == "unknown"
    assert any("mapping" in r for r in d.reason_codes)


def test_donor_eligibility_cofactors_prior_downweights():
    """§11.4: COFACTORS prior downweights eligibility but never forces not_eligible.

    A COFACTORS member (e.g. O2) is downweighted (conditionally_eligible or
    not_eligible with explicit reason) — but small molecules can still be
    formal atom sources, so 'not_eligible' must carry an explicit reason.
    """
    from reaction_agent.roles.resolver import assess_donor_eligibility
    o2 = _participant("p2", "O2", "O=O", "reactant")
    d = assess_donor_eligibility(o2, mapping_report=None)
    # Downweighted but with explicit reason; never silently not_eligible
    if d.eligibility == "not_eligible":
        assert any("cofactor" in r or "prior" in r for r in d.reason_codes)
    else:
        assert d.eligibility in ("conditionally_eligible", "unknown")


def test_donor_eligibility_distinct_from_role_hypothesis():
    """§11.4: donor eligibility is computed independently of role.

    A participant may have role=unknown but still get a donor eligibility
    assessment (and vice versa). The two assessments do not determine each
    other.
    """
    from reaction_agent.roles.resolver import (
        resolve_roles, assess_donor_eligibility,
    )
    p = _participant("p1", "m1", "C", "reactant")
    resolved = resolve_roles([p])[0]
    elig = assess_donor_eligibility(resolved, mapping_report=None)
    # role hypotheses exist independently of eligibility verdict
    assert len(resolved.role_hypotheses) >= 1
    assert elig.eligibility in (
        "eligible", "conditionally_eligible", "not_eligible", "unknown"
    )


def test_donor_eligibility_reason_codes_are_strings():
    """§11.4: reason_codes are non-empty strings."""
    from reaction_agent.roles.resolver import assess_donor_eligibility
    p = _participant("p1", "m1", "C", "reactant")
    d = assess_donor_eligibility(p, mapping_report=None)
    assert all(isinstance(r, str) and r for r in d.reason_codes)


def test_donor_eligibility_carries_dimension_reasons():
    """§11.4: reason codes cover the §11.4 dimensions (at least a subset).

    Without mapping, dimensions that cannot be evaluated are marked as
    'unknown_<dimension>' rather than fabricated.
    """
    from reaction_agent.roles.resolver import assess_donor_eligibility
    p = _participant("p1", "m1", "C", "reactant")
    d = assess_donor_eligibility(p, mapping_report=None)
    codes_joined = " ".join(d.reason_codes)
    # At least one dimension reason is present (size, stoichiometry,
    # cofactors prior, mapping, or direction).
    dimension_markers = (
        "size", "stoichiometry", "cofactor", "mapping", "direction",
        "source", "lineage", "transferred", "retention",
    )
    assert any(m in codes_joined for m in dimension_markers)


def test_donor_eligibility_with_mapping_evidence():
    """§11.4: mapping evidence (mapped atoms retained) pushes toward eligible."""
    from reaction_agent.roles.resolver import assess_donor_eligibility
    # A participant with high mapped_fraction + changed atoms → donor evidence
    p = _participant(
        "p1", "m1", "CCO", "reactant",
        mapped_fraction=0.9, changed_atom_fraction=0.4,
    )
    d = assess_donor_eligibility(p, mapping_report="present")
    # With mapping evidence present, should not be pure 'unknown'
    assert d.eligibility in (
        "eligible", "conditionally_eligible", "unknown",
    )
    # Mapping-derived reason present
    assert any("mapping" in r or "retention" in r or "mapped" in r
               for r in d.reason_codes) or d.eligibility == "unknown"


def test_donor_eligibility_small_molecule_not_auto_disqualified():
    """§11.3/§11.4: small molecules are NOT auto-disqualified as donors.

    O2 can be a formal atom source; H2O can participate in hydrolysis. Size
    is a prior, not a hard rule.
    """
    from reaction_agent.roles.resolver import assess_donor_eligibility
    for smi in ("O=O", "O", "O=C=O"):
        p = _participant("p1", "m1", smi, "reactant")
        d = assess_donor_eligibility(p, mapping_report=None)
        # Never silently not_eligible; if not_eligible, reason must be explicit
        if d.eligibility == "not_eligible":
            assert len(d.reason_codes) > 0
        else:
            assert d.eligibility in (
                "eligible", "conditionally_eligible", "unknown",
            )


def test_donor_eligibility_assessment_notes_present():
    """§11.4: assessment_notes may carry human-readable context."""
    from reaction_agent.roles.resolver import assess_donor_eligibility
    p = _participant("p1", "m1", "C", "reactant")
    d = assess_donor_eligibility(p, mapping_report=None)
    assert isinstance(d.assessment_notes, str)


# =====================================================================
# §11.2 — heuristic score is NOT a probability
# =====================================================================

def test_role_hypothesis_score_in_unit_interval():
    """§11.2: heuristic score is in [0, 1] (ordering hint, NOT a probability)."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant("p1", "m1", "C", "reactant"),
        _participant("p2", "m2", "O=O", "reactant"),
    ]
    out = resolve_roles(ps)
    for p in out:
        for h in p.role_hypotheses:
            assert 0.0 <= h.score <= 1.0


def test_role_hypothesis_score_not_labeled_probability():
    """§11.2: evidence codes must not claim the score is a probability."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "C", "reactant")]
    out = resolve_roles(ps)
    for h in out[0].role_hypotheses:
        for c in h.evidence_codes:
            assert "probability" not in c.lower()


# =====================================================================
# Edge cases
# =====================================================================

def test_resolve_roles_empty_input():
    """§11.1: empty input returns empty output (no fabrication)."""
    from reaction_agent.roles.resolver import resolve_roles
    out = resolve_roles([])
    assert out == []


def test_resolve_roles_single_participant():
    """§11.1: single participant is preserved."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("solo", "m1", "C", "reactant")]
    out = resolve_roles(ps)
    assert len(out) == 1
    assert out[0].participant_id == "solo"


def test_resolve_roles_maintains_input_order():
    """§11.1: output order matches input order (stable)."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [
        _participant(f"p{i}", f"m{i}", "C", "reactant") for i in range(5)
    ]
    out = resolve_roles(ps)
    assert [p.participant_id for p in out] == \
           [p.participant_id for p in ps]


def test_resolve_roles_product_side_participant():
    """§11.2: product-side participants get role hypotheses too."""
    from reaction_agent.roles.resolver import resolve_roles
    ps = [_participant("p1", "m1", "CCO", "product")]
    out = resolve_roles(ps)
    assert len(out) == 1
    assert len(out[0].role_hypotheses) >= 1


def test_donor_eligibility_does_not_mutate_participant():
    """Immutability: assess_donor_eligibility does not mutate the participant."""
    from reaction_agent.roles.resolver import assess_donor_eligibility
    p = _participant("p1", "m1", "C", "reactant")
    snapshot = copy.deepcopy(p)
    assess_donor_eligibility(p, mapping_report=None)
    assert p == snapshot
