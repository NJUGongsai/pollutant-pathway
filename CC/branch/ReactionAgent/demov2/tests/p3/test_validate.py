"""P3-T7 candidate validation tests (final_plan §6.8)."""
from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.sites import enumerate_sites
from reaction_agent.p3.generate import generate_product
from reaction_agent.p3.validate import validate_candidate
from reaction_agent.p3.schemas import SiteEligibility
from reaction_agent.hashing import stable_id


def _validated_oct(train_view, oct_transform, smiles="CCCCCCCCO"):
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    donor, ref = find_donor_ref(train_view, "fx_oct")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    query = normalize_query(smiles)
    sites = [s for s in enumerate_sites(oct_transform, query)
             if s.eligibility is SiteEligibility.eligible]
    assert sites
    site = sites[0]
    report = generate_product(oct_transform, site, query)
    assert report.failure_code is None
    candidate_id = stable_id("cand", {"identity": report.canonical_product})
    return validate_candidate(
        dev, oct_transform, site, report, query,
        candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )


def test_valid_candidate_passes_all_gates(train_view, oct_transform):
    validation, cal = _validated_oct(train_view, oct_transform)
    assert validation.valid_molecule is True
    assert validation.transform_fidelity is True
    assert validation.precondition_recheck is True
    assert validation.formal_source_accounting is True
    assert validation.candidate_ledger_valid is True
    assert validation.relaxation_used is False
    assert validation.critical_ambiguity is False
    assert validation.failure_code is None


def test_candidate_analogy_ledger_source_linkage(train_view, oct_transform):
    _, cal = _validated_oct(train_view, oct_transform)
    assert cal.source_ledger_id
    assert cal.candidate_id
    assert cal.query_candidate_adaptation is not None
    assert cal.inherited_donor_context
    assert "donor_context_is_assumption_not_x_y_fact" in cal.inherited_assumptions


def test_failed_precondition_rejects_site(train_view, oct_transform):
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    donor, ref = find_donor_ref(train_view, "fx_oct")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    query = normalize_query("CC(C)O")
    sites = enumerate_sites(oct_transform, query)
    assert sites and sites[0].eligibility is SiteEligibility.ineligible


def test_heavy_atom_count_fidelity(train_view, oct_transform):
    validation, _ = _validated_oct(train_view, oct_transform)
    assert validation.transform_fidelity is True
