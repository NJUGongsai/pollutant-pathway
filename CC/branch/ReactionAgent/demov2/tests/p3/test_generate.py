"""P3-T6 deterministic graph-edit generation tests (final_plan §6.7)."""
from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.sites import enumerate_sites
from reaction_agent.p3.generate import generate_product
from reaction_agent.p3.schemas import SiteEligibility


def _gen(oct_transform, smiles, query_id="q", case_id="c"):
    query = normalize_query(smiles)
    sites = enumerate_sites(oct_transform, query, query_id=query_id, case_id=case_id)
    eligible = [s for s in sites if s.eligibility is SiteEligibility.eligible]
    reports = [generate_product(oct_transform, s, query, query_id=query_id, case_id=case_id)
               for s in eligible]
    return [r for r in reports if r.failure_code is None]


def test_octanol_carbon_regression(oct_transform):
    # REQUIRED regression: CCCCCCCCO -> CCCCCCCC=O (no carbon loss).
    reports = _gen(oct_transform, "CCCCCCCCO")
    assert reports
    assert reports[0].canonical_product == "CCCCCCCC=O"


def test_butanol_to_butanal(oct_transform):
    reports = _gen(oct_transform, "CCCCO")
    assert reports
    assert reports[0].canonical_product == "CCCC=O"


def test_diol_single_product(oct_transform):
    reports = _gen(oct_transform, "OCCCCCCO")
    assert reports
    identities = {r.canonical_product for r in reports}
    assert identities == {"O=CCCCCCO"}


def test_bond_order_change_reflected(oct_transform):
    reports = _gen(oct_transform, "CCCCCCCCO")
    assert reports[0].canonical_product.count("=") == 1  # one C=O formed


def test_deterministic_generation(oct_transform):
    r1 = _gen(oct_transform, "CCCCCCCCO")
    r2 = _gen(oct_transform, "CCCCCCCCO")
    assert [r.canonical_product for r in r1] == [r.canonical_product for r in r2]
    assert [r.generation_id for r in r1] == [r.generation_id for r in r2]


def test_no_candidate_for_secondary_alcohol(oct_transform):
    query = normalize_query("CC(C)O")
    sites = enumerate_sites(oct_transform, query)
    assert all(s.eligibility is not SiteEligibility.eligible for s in sites)
    # No eligible site -> no generation attempted
    assert not [s for s in sites if s.eligibility is SiteEligibility.eligible]


def test_decarb_generation(train_view):
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    from reaction_agent.p3.transform import extract_transform
    donor, ref = find_donor_ref(train_view, "fx_decarb")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    tr = extract_transform(dev, lineage_id=ref.lineage_id)
    query = normalize_query("CCCC(=O)O")  # butanoic acid
    sites = [s for s in enumerate_sites(tr, query) if s.eligibility is SiteEligibility.eligible]
    assert sites
    reports = [r for r in (generate_product(tr, s, query) for s in sites) if r.failure_code is None]
    assert reports
    assert reports[0].canonical_product == "CCC"  # propane, no carbon loss beyond CO2


def test_reduction_generation(train_view):
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    from reaction_agent.p3.transform import extract_transform
    donor, ref = find_donor_ref(train_view, "fx_reduction")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    tr = extract_transform(dev, lineage_id=ref.lineage_id)
    query = normalize_query("CCCC=O")  # butanal
    sites = [s for s in enumerate_sites(tr, query) if s.eligibility is SiteEligibility.eligible]
    assert sites
    reports = [r for r in (generate_product(tr, s, query) for s in sites) if r.failure_code is None]
    assert reports
    assert reports[0].canonical_product == "CCCCO"  # butanol


def test_generation_report_typed_failure_on_invalid(oct_transform):
    # A transform forced onto a molecule with no compatible site yields no
    # generation report at all (no structure is invented).
    query = normalize_query("CCCCC")
    assert enumerate_sites(oct_transform, query) == []
