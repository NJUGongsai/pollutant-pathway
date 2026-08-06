"""R4-B: reaction authority preimage MUST fully bind reaction evidence.

ChatGPT P3 Round 3 audit independently showed that mutating the following
authority-relevant fields did NOT change the canonical reaction hash:
raw_reaction, source_name, source_version, source_uri_or_citation,
provenance, quality_report (plus fragment_lineage_graph, ambiguity_sets,
transformation_hypotheses, snapshot_id, quarantine, participant
formal_charge / role_hypotheses / changed_atom_fraction).

Every field-level mutation below must change the hash (or trigger a typed
rejection).  The tests mutate the REAL reaction content and recompute the
hash through the production preimage — never by hand-tampering the hash
string itself.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from reaction_agent.p3.fixtures import (
    canonical_reaction_hash,
    load_fixture_reactions,
)


@pytest.fixture(scope="module")
def rxn_fixture():
    return load_fixture_reactions()["rxn_oct"]


def _hash_of(fx) -> str:
    return canonical_reaction_hash(fx)


def _mutate_evidence(fx, **updates):
    return replace(fx, evidence=fx.evidence.model_copy(update=updates))


def _mutate_participant(fx, index, **updates):
    participants = list(fx.evidence.participants)
    participants[index] = participants[index].model_copy(update=updates)
    return _mutate_evidence(fx, participants=participants)


# -- source metadata ---------------------------------------------------------


def test_source_name_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, source_name="FORGED")) != base


def test_source_version_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, source_version="FORGED")) != base


def test_source_uri_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, source_uri_or_citation="FORGED")) != base


def test_source_record_id_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, source_record_id="FORGED")) != base


# -- raw reaction ------------------------------------------------------------


def test_raw_reaction_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, raw_reaction="FORGED>>FORGED")) != base


def test_normalized_reaction_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, normalized_reaction="FORGED>>FORGED")) != base


def test_direction_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, direction="FORGED")) != base


# -- participant mapped/canonical structure ----------------------------------


def test_participant_canonical_structure_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(
        rxn_fixture, 0, canonical_smiles="[CH3:1][CH2:1][CH2:1][CH2:1][CH2:1][CH2:1][CH2:1][CH2:1][OH:1]"
    )) != base


def test_participant_molecule_id_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, molecule_id="FORGED")) != base


def test_participant_side_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, side="FORGED")) != base


def test_participant_stoichiometry_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, stoichiometry=7)) != base


def test_participant_atom_map_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, atom_map_numbers=[1, 2, 3])) != base


def test_participant_mapped_fraction_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, mapped_fraction=0.5)) != base


# -- participant formal charge / role hypotheses / donor eligibility ---------


def test_participant_formal_charge_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, formal_charge=1)) != base


def test_participant_changed_atom_fraction_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, changed_atom_fraction=0.9)) != base


def test_participant_role_hypotheses_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    from reaction_agent.schemas.evidence import RoleHypothesis
    from reaction_agent.schemas.common import ParticipantRole
    assert _hash_of(_mutate_participant(
        rxn_fixture, 0,
        role_hypotheses=[RoleHypothesis(role=ParticipantRole.transformed_product, score=1.0)],
    )) != base


def test_participant_donor_eligibility_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, donor_eligibility=False)) != base


def test_participant_provenance_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_participant(rxn_fixture, 0, provenance=["FORGED"])) != base


# -- mapping report / lineage graph / ambiguity / hypotheses -----------------


def test_mapping_report_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    mr = rxn_fixture.mapping_report.model_copy(update={"input_hash": "FORGED"})
    mutated = replace(rxn_fixture, mapping_report=mr)
    assert _hash_of(mutated) != base


def test_fragment_lineage_graph_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(
        rxn_fixture, fragment_lineage_graph={"FORGED": "x"}
    )) != base


def test_ambiguity_sets_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(
        rxn_fixture, ambiguity_sets=[{"FORGED": "x"}]
    )) != base


def test_transformation_hypotheses_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(
        rxn_fixture, transformation_hypotheses=["FORGED"]
    )) != base


def test_resolved_lineages_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(
        rxn_fixture, resolved_transformed_lineages=["FORGED"]
    )) != base


# -- provenance / quality report / snapshot / quarantine ---------------------


def test_provenance_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, provenance=["FORGED"])) != base


def test_quality_report_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(
        rxn_fixture, quality_report={"FORGED": "yes"}
    )) != base


def test_snapshot_id_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, snapshot_id="FORGED")) != base


def test_quarantine_change_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    assert _hash_of(_mutate_evidence(rxn_fixture, quarantine="FORGED")) != base


# -- same reaction id, different content -------------------------------------


def test_same_reaction_id_different_content_changes_hash(rxn_fixture):
    base = _hash_of(rxn_fixture)
    # Same reaction_id, different raw content entirely.
    mutated = _mutate_evidence(rxn_fixture, raw_reaction="CCO>>CC=O")
    assert _hash_of(mutated) != base


# -- semantically irrelevant ordering must NOT change the hash ---------------


def test_equivalent_ordering_does_not_change_hash(rxn_fixture):
    head = _hash_of(rxn_fixture)
    # Reversing participant order and resolved-lineage order is a
    # semantically irrelevant input reordering.
    participants = list(reversed(rxn_fixture.evidence.participants))
    ev = rxn_fixture.evidence.model_copy(update={"participants": participants})
    reordered = replace(rxn_fixture, evidence=ev)
    assert _hash_of(reordered) == head


# -- non-semantic wall-clock timing must NOT change the hash -----------------


def test_runtime_ms_is_non_semantic_and_excluded(rxn_fixture):
    # R4-B: mapper_parameters.runtime_ms is a wall-clock performance metric,
    # NOT reaction semantics.  It is explicitly excluded from the authority
    # preimage, so a timing difference must never change the hash.
    head = _hash_of(rxn_fixture)
    mr = rxn_fixture.mapping_report.model_copy(update={
        "mapper_parameters": {
            **rxn_fixture.mapping_report.mapper_parameters,
            "runtime_ms": "9999",
        },
    })
    mutated = replace(rxn_fixture, mapping_report=mr)
    assert _hash_of(mutated) == head