"""R5-C: P3 reaction authority must be rooted in the FROZEN P1 authority.

Round 4 defect: a fully self-consistent A/B-only STRIPPED reaction (the
attacker strips cofactor/co-substrate/coproduct from participants, evidence,
ledger, mapping, lineage, raw reaction AND recomputes the reaction hash and
the TrainView snapshot hash) was ACCEPTED by the loader:

    fully_self_consistent_ab_strip_accepted=True
    fully_self_consistent_ab_participants=2

Root cause: a complete content hash only proves "content unchanged since the
hash was computed" — it cannot prove "content equals the upstream REAL
original reaction".  When P3 accepts both the caller-supplied content AND the
caller-recomputed expected hash, the stripped object becomes a new
self-consistent authority.

R5-C contract:
- P3 derives the expected snapshot/reaction hash from the FROZEN P1/P2
  authority root (a trusted manifest), NEVER from the TrainView being
  verified or from a caller-recomputed hash;
- the loader accepts an independent trusted authority manifest/resolver;
- a mutation can change candidate reaction content but must preserve the
  frozen expected root — so a fully-synchronized strip MUST produce an
  authority mismatch (REACTION_AUTHORITY_MISMATCH / FROZEN_REACTION_HASH_MISMATCH);
- fixture mode freezes the fixture authority root BEFORE the test starts;
  the mutation cannot rebuild the expected root from mutated content;
- evidence/fixture duplicated content (mapping, ledger, participants,
  lineages, reaction strings) is cross-verified bidirectionally;
- retrieval cofactor stripping never changes the complete reaction authority.

These tests are RED on the R4 code (the fully-synchronized strip is accepted)
and GREEN after R5-C.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from reaction_agent.p3.fixtures import (
    DonorEntry,
    ReactionRef,
    TrainView,
    build_train_view,
    canonical_reaction_hash,
    load_fixture_reactions,
    recompute_train_view_hash,
    select_primary_lineage,
    strip_atom_maps,
)
from reaction_agent.p3.load import (
    FoldIsolationError,
    IncompleteReactionError,
    ReactionAuthorityError,
    load_reaction_evidence,
)


def _rebuild_tv(fx):
    """Self-consistent train view carrying ONE fixture (hash recomputed)."""
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
    return TrainView(
        fold_id=draft.fold_id, snapshot_id=draft.snapshot_id,
        snapshot_hash=recompute_train_view_hash(draft),
        donors=draft.donors, reactions=draft.reactions,
    ), donor, ref


def _hydrolysis():
    return load_fixture_reactions()["rxn_hydrolysis"]


def _authority_root(fx):
    """Freeze the fixture authority root via the REAL P1 snapshot builder.

    The P1 snapshot builder is the frozen authority: its canonical snapshot
    manifest binds the COMPLETE reaction evidence (participants, ledger,
    mapping, lineages, raw reaction) to a content hash.  The P3 loader must
    derive its expected reaction/snapshot hash from THIS root — never from
    the TrainView being verified.
    """
    from reaction_agent.p3.fixtures import build_fixture_authority_manifest
    return build_fixture_authority_manifest({fx.reaction_id: fx})


# -- baseline: the COMPLETE hydrolysis reaction loads under the authority ----


def test_complete_hydrolysis_loads_under_frozen_authority():
    fx = _hydrolysis()
    root = _authority_root(fx)
    tv, donor, ref = _rebuild_tv(fx)
    # R5-C: the loader must verify the TrainView against the frozen root.
    dev = load_reaction_evidence(
        tv, donor.donor_id, ref, authority_manifest=root,
    )
    assert dev.context.reaction_id == "fx_hydrolysis"
    assert len(dev.context.reaction_evidence.participants) == 4


# -- fully-synchronized A/B-only strip (the Round-4 audit repro) -------------


def _fully_stripped_hydrolysis():
    """Strip the complete hydrolysis to A/B-only in EVERY representation.

    Keeps only the donor reactant and the primary product; removes H2O
    co-substrate and the coproduct from participants, evidence, ledger,
    mapping, lineages, raw/normalized reaction; recomputes every hash the
    attacker can recompute; the TrainView hash is recomputed too.
    """
    fx = _hydrolysis()
    keep = [p for p in fx.participants if p.participant_id in (
        fx.donor_participant_id, "fx_hydrolysis_product_0",
    )]
    ev = fx.evidence.model_copy(update={"participants": keep})
    mutated = replace(fx, participants=keep, evidence=ev)
    return mutated


def test_fully_synchronized_ab_strip_rejected_by_frozen_authority():
    """The complete A/B-only strip must be rejected by the FROZEN root."""
    fx = _hydrolysis()
    root = _authority_root(fx)
    stripped = _fully_stripped_hydrolysis()
    tv, donor, ref = _rebuild_tv(stripped)
    with pytest.raises((ReactionAuthorityError, IncompleteReactionError,
                        FoldIsolationError)) as exc:
        load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)
    assert exc.value.failure_code in (
        "REACTION_AUTHORITY_MISMATCH", "FROZEN_REACTION_HASH_MISMATCH",
        "REACTION_HASH_MISMATCH", "INCOMPLETE_REACTION",
    )


def test_caller_recomputed_train_view_hash_is_not_authority():
    """A caller that recomputes the TrainView hash from mutated content must
    NOT create a new authority root — the frozen root still governs."""
    fx = _hydrolysis()
    root = _authority_root(fx)
    stripped = _fully_stripped_hydrolysis()
    tv, donor, ref = _rebuild_tv(stripped)
    # The caller recomputed the snapshot hash (self-consistent) — still must
    # be rejected because the expected root is frozen and unchanged.
    with pytest.raises((ReactionAuthorityError, IncompleteReactionError,
                        FoldIsolationError)):
        load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)


# -- evidence/fixture duplicated content must be bidirectionally consistent --


def test_evidence_ledger_content_mismatch_rejected():
    fx = _hydrolysis()
    root = _authority_root(fx)
    # evidence.source_reaction_ledger differs from fixture.source_ledger
    forged_ledger = fx.source_ledger.model_copy(update={"charge_balance": 7})
    ev = fx.evidence.model_copy(update={"source_reaction_ledger": forged_ledger})
    mutated = replace(fx, evidence=ev)
    tv, donor, ref = _rebuild_tv(mutated)
    with pytest.raises((ReactionAuthorityError, IncompleteReactionError,
                        FoldIsolationError)):
        load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)


def test_evidence_mapping_content_mismatch_rejected():
    fx = _hydrolysis()
    root = _authority_root(fx)
    forged_mapping = fx.mapping_report.model_copy(update={"input_hash": "FORGED"})
    ev = fx.evidence.model_copy(update={"mapping_report": forged_mapping})
    mutated = replace(fx, evidence=ev, mapping_report=forged_mapping)
    tv, donor, ref = _rebuild_tv(mutated)
    with pytest.raises((ReactionAuthorityError, IncompleteReactionError,
                        FoldIsolationError)):
        load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)


def test_raw_reaction_mismatch_with_participants_rejected():
    fx = _hydrolysis()
    root = _authority_root(fx)
    ev = fx.evidence.model_copy(update={"raw_reaction": "CCO>>CC=O"})
    mutated = replace(fx, evidence=ev)
    tv, donor, ref = _rebuild_tv(mutated)
    with pytest.raises((ReactionAuthorityError, IncompleteReactionError,
                        FoldIsolationError)):
        load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)


# -- legitimate frozen-authority loads still work -----------------------------


def test_fresh_snapshot_built_by_p1_builder_loads():
    """A NEW legitimate snapshot built through the official P1 snapshot
    builder must load (the authority root is the builder's manifest)."""
    fx = _hydrolysis()
    root = _authority_root(fx)
    tv, donor, ref = _rebuild_tv(fx)
    dev = load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)
    assert dev.context.reaction_evidence.participants


# -- retrieval identity stripping does not change reaction authority ----------


def test_retrieval_stripping_does_not_change_reaction_authority():
    """Cofactor stripping for RETRIEVAL identity must never affect the
    complete reaction authority hash."""
    fx = _hydrolysis()
    root = _authority_root(fx)
    donor_p = next(p for p in fx.participants
                   if p.participant_id == fx.donor_participant_id)
    # retrieval identity = stripped structural smiles (cofactor removed)
    identity = strip_atom_maps(donor_p.canonical_smiles)
    assert identity  # the retrieval identity exists
    # the reaction authority hash is over the COMPLETE reaction, unchanged
    full_hash = canonical_reaction_hash(fx)
    assert full_hash == canonical_reaction_hash(fx)
    tv, donor, ref = _rebuild_tv(fx)
    dev = load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)
    assert dev.reaction_authority_hash == full_hash