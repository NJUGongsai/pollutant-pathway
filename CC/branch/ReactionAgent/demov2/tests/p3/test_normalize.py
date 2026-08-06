"""P3-T1 normalization contract tests (final_plan §6.2)."""
import pytest

from reaction_agent.p3.normalize import (
    InvalidQueryError,
    equivalent_identity,
    normalize_query,
)
from reaction_agent.p3.schemas import EvidenceKind, NormalizationPolicy


# -- R2-A signed formal charge ----------------------------------------------


def test_negative_formal_charge_is_valid():
    q = normalize_query("[Cl-]")
    assert q.formal_charge == -1


def test_negative_formal_charge_alkoxide():
    q = normalize_query("C[O-]")
    assert q.formal_charge == -1


def test_positive_formal_charge_is_valid():
    q = normalize_query("C[N+](C)(C)C")
    assert q.formal_charge == 1


def test_neutral_formal_charge():
    q = normalize_query("CCCCCCCCO")
    assert q.formal_charge == 0


def test_multifragment_total_formal_charge():
    q = normalize_query("CCO.[Na+]")
    assert q.formal_charge == 1


# -- R2-A isotope policy ----------------------------------------------------


def test_preserve_isotopes_policy_distinguishes_identity():
    policy = NormalizationPolicy(version="p3-1", isotope_policy="preserve_isotopes")
    q_c12 = normalize_query("C", policy=policy)
    q_c13 = normalize_query("[13CH4]", policy=policy)
    assert q_c12.identity_hash != q_c13.identity_hash


def test_stereo_agnostic_identity_preserves_isotope():
    # stereo ignored for identity must NOT silently delete isotope markers
    policy = NormalizationPolicy(
        version="p3-1",
        isotope_policy="preserve_isotopes",
        stereo_policy="ignore_stereo_for_identity",
    )
    q_c12 = normalize_query("C", policy=policy)
    q_c13 = normalize_query("[13CH4]", policy=policy)
    assert q_c12.identity_hash != q_c13.identity_hash


def test_isotope_preserved_in_canonical_smiles():
    q = normalize_query("[13CH4]")
    assert "13" in q.canonical_smiles


# -- R2-A evidence kind from run context ------------------------------------


def test_normalize_evidence_kind_parameter():
    q = normalize_query("CCCCCCCCO", evidence_kind=EvidenceKind.synthetic_fixture)
    assert q.evidence_kind is EvidenceKind.synthetic_fixture
    q2 = normalize_query("CCCCCCCCO", evidence_kind=EvidenceKind.real)
    assert q2.evidence_kind is EvidenceKind.real


def test_equivalent_smiles_same_identity():
    q1 = normalize_query("CCCCCCCCO")
    q2 = normalize_query("CCCCCCCCO")
    assert q1.identity_hash == q2.identity_hash
    assert equivalent_identity(q1, q2)


def test_atom_permutation_same_identity():
    q1 = normalize_query("CCCCCCCCO")
    q2 = normalize_query("OCCCCCCCC")
    assert q1.identity_hash == q2.identity_hash
    assert equivalent_identity(q1, q2)


def test_canonical_smiles_normalized():
    q = normalize_query("OCCCCCCCC")
    assert q.canonical_smiles == "CCCCCCCCO"


def test_invalid_input_typed_error():
    with pytest.raises(InvalidQueryError):
        normalize_query("C1CC1C(C(C")


def test_empty_input_typed_error():
    with pytest.raises(InvalidQueryError):
        normalize_query("   ")


def test_salt_multi_fragment_preserved():
    q = normalize_query("CCO.[Na+]")
    assert q.fragment_count == 2
    assert q.heavy_atom_count == 4  # CCO (3) + Na (1)
    assert q.evidence_kind is EvidenceKind.real


def test_explicit_implicit_h_equivalent():
    # Same molecule written with explicit vs implicit H on a site carbon.
    q1 = normalize_query("CCCCO")
    q2 = normalize_query("[CH3][CH2][CH2][CH2][OH]")
    assert q1.identity_hash == q2.identity_hash


def test_charge_preserved():
    q = normalize_query("C[N+](C)(C)C")
    assert q.formal_charge == 1


def test_stereo_agnostic_identity():
    q1 = normalize_query("C[C@H](O)C")
    q2 = normalize_query("C[C@@H](O)C")
    # default stereo_policy ignores stereo for identity
    assert q1.identity_hash == q2.identity_hash


def test_identity_hash_deterministic():
    q1 = normalize_query("CCCCCCCCO")
    q2 = normalize_query("CCCCCCCCO")
    assert q1.identity_hash == q2.identity_hash
    assert q1.query_id == q2.query_id


def test_normalized_query_is_real_evidence_kind():
    q = normalize_query("CCCCCCCCO")
    assert q.evidence_kind is EvidenceKind.real
