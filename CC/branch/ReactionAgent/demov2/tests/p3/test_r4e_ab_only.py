"""R4-E: A/B-only stripped reactions must be rejected by reaction
completeness/authority — never by a shallow hand-written hash.

Round 3's A/B-only mutation forged the snapshot hash (``FOLD_AUTHORITY_HASH``)
and never exercised the completeness path.  This test locks the corrected
contract:

- a stripped reaction (cofactor/co-substrate removed) must be REJECTED by the
  production loader with a typed completeness failure;
- a stripped source ledger (participant references removed while the
  participants remain) must also be REJECTED — participant set and ledger
  participant set must be exactly equal (bidirectional completeness).
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from reaction_agent.p3.fixtures import (
    DonorEntry,
    ReactionRef,
    TrainView,
    canonical_reaction_hash,
    load_fixture_reactions,
    recompute_train_view_hash,
    select_primary_lineage,
    strip_atom_maps,
)
from reaction_agent.p3.load import IncompleteReactionError, load_reaction_evidence

H2O_PID = "fx_hydrolysis_reactant_1"


def _rebuild_tv(fx):
    """Self-consistent train view carrying ONE fixture (hash recomputed).

    R6-C: the train view always carries a frozen FIXTURE authority (built
    from the indexed content) so the loader never runs without an upstream
    authority handle.
    """
    from reaction_agent.p3.fixtures import build_fixture_authority_manifest
    donor_pid = fx.donor_participant_id
    donor_p = next(p for p in fx.participants if p.participant_id == donor_pid)
    lineage = select_primary_lineage(fx)
    ref = ReactionRef(
        reaction_id=fx.reaction_id,
        donor_participant_id=donor_pid,
        lineage_id=lineage.lineage_id if lineage else "l0",
        reaction_hash=canonical_reaction_hash(fx),
    )
    donor = DonorEntry(
        donor_id="donor_ab", molecule_id=donor_p.molecule_id,
        canonical_smiles=donor_p.canonical_smiles,
        structural_smiles=strip_atom_maps(donor_p.canonical_smiles),
        donor_eligibility="eligible", source_quality="synthetic_fixture",
        fold_id="fold_fx_p3", reaction_refs=[ref],
    )
    draft = TrainView(
        fold_id="fold_fx_p3", snapshot_id="fx_snapshot_p3", snapshot_hash="",
        donors=[donor], reactions={fx.reaction_id: fx},
    )
    tv = TrainView(
        fold_id=draft.fold_id, snapshot_id=draft.snapshot_id,
        snapshot_hash=recompute_train_view_hash(draft),
        donors=draft.donors, reactions=draft.reactions,
    )
    tv = replace(tv, authority_manifest=build_fixture_authority_manifest({fx.reaction_id: fx}))
    return tv, donor, ref


def _load(fx):
    tv, donor, ref = _rebuild_tv(fx)
    return load_reaction_evidence(tv, donor.donor_id, ref)


def _hydrolysis():
    return load_fixture_reactions()["rxn_hydrolysis"]


# -- baseline: the COMPLETE hydrolysis reaction (with co-substrate H2O) -----


def test_complete_hydrolysis_reaction_loads():
    dev = _load(_hydrolysis())
    assert dev.context.reaction_id == "fx_hydrolysis"
    assert len(dev.context.reaction_evidence.participants) == 4


# -- stripped participants (A/B-only) keeping the ledger ---------------------


def test_stripped_participants_keeping_ledger_rejected():
    fx = _hydrolysis()
    # A/B-only: keep only the donor reactant and the primary product; the
    # source ledger still records the co-substrate (R4-E: contract-required
    # information is stripped -> reject).
    keep = [p for p in fx.participants if p.participant_id in (
        fx.donor_participant_id, "fx_hydrolysis_product_0",
    )]
    ev = fx.evidence.model_copy(update={"participants": keep})
    mutated = replace(fx, evidence=ev)
    with pytest.raises(IncompleteReactionError) as exc:
        _load(mutated)
    assert exc.value.failure_code == "INCOMPLETE_REACTION"


# -- stripped ledger (references removed) keeping the participants -----------


def test_stripped_ledger_keeping_participants_rejected():
    fx = _hydrolysis()
    led = fx.source_ledger
    stripped = led.model_copy(update={
        "reactant_entries": [
            e for e in led.reactant_entries if e.participant_id != H2O_PID
        ],
        "role_assignments": [
            r for r in led.role_assignments if r.participant_id != H2O_PID
        ],
        "stoichiometry": [
            e for e in led.stoichiometry if e.participant_id != H2O_PID
        ],
        "added_atom_sources": [
            s for s in led.added_atom_sources
            if s.source_participant_id != H2O_PID
        ],
        "formal_atom_transfer_assignments": [
            t for t in led.formal_atom_transfer_assignments
            if t.source_participant_id != H2O_PID
        ],
    })
    # R6-C: the strip must be representation-consistent (the evidence embeds
    # a copy of the source ledger) so the fixture authority can be frozen
    # from the SAME (stripped) content; the rejection then comes from the
    # R4-E exact-equality completeness check.
    ev = fx.evidence.model_copy(update={"source_reaction_ledger": stripped})
    mutated = replace(fx, source_ledger=stripped, evidence=ev)
    with pytest.raises(IncompleteReactionError) as exc:
        _load(mutated)
    assert exc.value.failure_code == "INCOMPLETE_REACTION"


# -- the completeness check must be bidirectional (exact set equality) -------


def test_ledger_participant_set_exactly_equals_participant_set():
    fx = _hydrolysis()
    led = fx.source_ledger
    led_pids = {
        e.participant_id for e in led.stoichiometry
    } | {
        r.participant_id for r in led.role_assignments
    }
    participant_pids = {p.participant_id for p in fx.participants}
    # The complete record satisfies the exact-equality contract.
    assert led_pids == participant_pids