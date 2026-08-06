"""P3-T5 conditioned site tests (final_plan §6.6)."""
from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.sites import enumerate_sites
from reaction_agent.p3.schemas import SiteEligibility


def _sites(oct_transform, smiles, query_id="q", case_id="c"):
    query = normalize_query(smiles)
    return enumerate_sites(oct_transform, query, query_id=query_id, case_id=case_id)


def test_single_site_octanol(oct_transform):
    sites = _sites(oct_transform, "CCCCCCCCO")
    assert len(sites) == 1
    assert sites[0].eligibility is SiteEligibility.eligible
    assert 8 in [int(k) for k in sites[0].atom_map_correspondence]


def test_no_site_alkane(oct_transform):
    sites = _sites(oct_transform, "CCCCC")
    assert sites == []


def test_wrong_functional_group_secondary_alcohol(oct_transform):
    sites = _sites(oct_transform, "CC(C)O")
    # site is found (C-C-O pattern matches) but precondition fails
    assert len(sites) == 1
    assert sites[0].eligibility is SiteEligibility.ineligible
    assert sites[0].failed_preconditions


def test_symmetric_dedup(oct_transform):
    sites = _sites(oct_transform, "OCCCCCCO")
    assert len(sites) == 1  # two symmetric sites collapse


def test_asymmetric_two_sites(oct_transform):
    sites = _sites(oct_transform, "OCCCC(C)CO")
    assert len(sites) == 2
    # Two distinct non-symmetric sites are independent valid sites, NOT an
    # ambiguity group: ambiguity_group is 0 for both (R2-E).
    assert sites[0].ambiguity_group == 0
    assert sites[1].ambiguity_group == 0
    assert sites[0].symmetry_class != sites[1].symmetry_class


def test_atom_order_invariance(oct_transform):
    s1 = _sites(oct_transform, "OCCCCCCCC")
    s2 = _sites(oct_transform, "CCCCCCCCO")
    assert len(s1) == len(s2)
    assert [s.eligibility for s in s1] == [s.eligibility for s in s2]


def test_stable_site_id(oct_transform):
    s1 = _sites(oct_transform, "CCCCCCCCO", query_id="q1")
    s2 = _sites(oct_transform, "CCCCCCCCO", query_id="q2")
    assert s1[0].site_id == s2[0].site_id


def test_multiple_valid_sites_retained(oct_transform):
    # 2-methyl-1,6-hexanediol is NOT symmetric: both OH ends are primary
    # alcohols but at different distances from the methyl branch -> two
    # distinct sites, both retained.
    sites = _sites(oct_transform, "OCCCCC(C)CO")
    assert len(sites) == 2
    assert all(s.eligibility is SiteEligibility.eligible for s in sites)
