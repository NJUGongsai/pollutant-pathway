"""P3 shared test fixtures.

All fixtures are synthetic_fixture (never real evidence).
"""
import pytest

from reaction_agent.p3.fixtures import (
    TrainView,
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)
from reaction_agent.p3.load import load_reaction_evidence
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.normalize import normalize_query


@pytest.fixture(scope="session")
def fixture_reactions():
    return load_fixture_reactions()


@pytest.fixture(scope="session")
def train_view(fixture_reactions) -> TrainView:
    return build_train_view(fixture_reactions)


@pytest.fixture(scope="session")
def oct_donor_ref(train_view):
    return find_donor_ref(train_view, "fx_oct")


@pytest.fixture(scope="session")
def oct_donor_evidence(train_view, oct_donor_ref):
    donor, ref = oct_donor_ref
    return load_reaction_evidence(
        train_view, donor.donor_id, ref, query_id="q_oct", case_id="c_oct"
    )


@pytest.fixture(scope="session")
def oct_transform(oct_donor_evidence):
    from reaction_agent.p3.transform import extract_transform
    return extract_transform(oct_donor_evidence, query_id="q_oct", case_id="c_oct")


@pytest.fixture(scope="session")
def oct_query():
    return normalize_query("CCCCCCCCO")
