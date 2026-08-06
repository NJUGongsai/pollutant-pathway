"""R6-C: the frozen P1/P2 authority must be the ONLY production authority.

ChatGPT P3 Round 5 audit findings (NOT CLOSED):

1. ``TrainView.authority_manifest`` defaults to None; ``build_train_view()``
   does not attach one; the default ``run_kernel()`` path builds a train view
   WITHOUT a frozen authority; ``load_reaction_evidence(..., authority_manifest=None)``
   tolerates a missing manifest; the public ``build_fixture_authority_manifest``
   lets a caller rebuild the root from current content; the frozen validator
   ``continue``s past missing reaction IDs and the manifest snapshot identity
   is not cross-bound in the production path.

R6-C contract:
- a production TrainView MUST carry an upstream authority handle (fail-closed
  MISSING_AUTHORITY when absent — a manually-constructed train view is not a
  production authority);
- the default kernel WITHOUT an upstream authority is BLOCKED / FAIL-CLOSED
  before any donor/reaction processing;
- a caller-built fixture manifest (``build_fixture_authority_manifest``) can
  NEVER be accepted as a production (P1/P2) authority — the loader rejects it
  in production mode with FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY;
- the manifest reaction ID set must EXACTLY equal the train view reaction
  refs — a missing OR extra reaction ID fails closed (no ``continue``);
- snapshot identity / snapshot hash / reaction hashes / authority version /
  kind / provenance are cross-bound through the manifest self-hash;
- a FULLY-SYNCHRONIZED A/B-only strip (participants, evidence, ledger,
  mapping, lineages, raw/normalized reaction, fixture reaction strings and
  local hashes ALL rebuilt consistently) is rejected by the FROZEN root
  (FROZEN_REACTION_HASH_MISMATCH) while the upstream root stays unchanged;
- the REAL retrieval identity/cofactor stripping path never mutates the
  complete reaction object or its authority hash.

These tests are RED on the R5 code (default train view has no authority,
caller-built fixture manifest passes as production, missing reaction IDs are
skipped) and GREEN after R6-C.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from reaction_agent.p3.fixtures import (
    DonorEntry,
    ReactionRef,
    TrainView,
    authority_manifest_hash,
    build_fixture_authority_manifest,
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
    load_reaction_evidence,
)
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.retrieve import retrieve_donors
from reaction_agent.p3.schemas import EvidenceKind


def _hydrolysis():
    return load_fixture_reactions()["rxn_hydrolysis"]


def _rebuild_tv(fx, authority=None):
    """Self-consistent single-fixture train view with an optional authority."""
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
        donor_id="donor_r6c", molecule_id=donor_p.molecule_id,
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
        authority_manifest=authority,
    )
    return tv, donor, ref


_FX = None


def _frozen_root():
    """The FIXTURE authority frozen from the COMPLETE hydrolysis."""
    global _FX
    if _FX is None:
        _FX = _hydrolysis()
    return build_fixture_authority_manifest({_FX.reaction_id: _FX})


# -- 1. production train view requires upstream authority ---------------------


def test_production_train_view_requires_upstream_authority():
    fx = _hydrolysis()
    tv, donor, ref = _rebuild_tv(fx, authority=None)
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv, donor.donor_id, ref)
    assert exc.value.failure_code == "MISSING_AUTHORITY"


# -- 2. default kernel blocks without upstream authority ----------------------


def test_default_kernel_blocks_without_upstream_authority():
    fx = _hydrolysis()
    tv, donor, ref = _rebuild_tv(fx, authority=None)
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r6c_noauth", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv,
    )
    assert result.status.value in ("blocked", "failed"), (
        f"kernel without upstream authority must fail-closed, got "
        f"{result.status.value}"
    )
    assert any(f.failure_code == "MISSING_AUTHORITY" for f in result.failures), (
        f"kernel must report MISSING_AUTHORITY, got {[f.failure_code for f in result.failures]}"
    )


# -- 3. caller-built fixture manifest is not a production authority -----------


def test_caller_built_fixture_manifest_is_not_production_authority():
    fx = _hydrolysis()
    root = _frozen_root()
    assert root.kind == "synthetic_fixture", (
        "fixture authority must be explicitly synthetic_fixture"
    )
    tv, donor, ref = _rebuild_tv(fx, authority=root)
    with pytest.raises(IncompleteReactionError) as exc:
        load_reaction_evidence(
            tv, donor.donor_id, ref, evidence_kind=EvidenceKind.real,
        )
    assert exc.value.failure_code == (
        "FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY"
    ), f"got {exc.value.failure_code}"


# -- 4./5. manifest reaction ID set must exactly equal the train view refs ----


def test_manifest_missing_reaction_id_fails_closed():
    fx = _hydrolysis()
    root = _frozen_root()
    # A manifest that does NOT cover the train view's reaction (missing ID).
    stripped_root = replace(root, reaction_hashes={})
    # recompute the manifest self-hash so the exact-set check is reached
    stripped_root = replace(
        stripped_root, manifest_hash=authority_manifest_hash(stripped_root),
    )
    tv, donor, ref = _rebuild_tv(fx, authority=stripped_root)
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv, donor.donor_id, ref)
    assert exc.value.failure_code == "FROZEN_MISSING_REACTION_ID", (
        f"got {exc.value.failure_code}"
    )


def test_manifest_extra_reaction_id_fails_closed():
    fx = _hydrolysis()
    root = _frozen_root()
    # A manifest that declares an EXTRA reaction the train view does not have.
    extra_root = replace(
        root,
        reaction_hashes={**root.reaction_hashes, "fx_NONEXISTENT": "x" * 64},
    )
    extra_root = replace(
        extra_root, manifest_hash=authority_manifest_hash(extra_root),
    )
    tv, donor, ref = _rebuild_tv(fx, authority=extra_root)
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv, donor.donor_id, ref)
    assert exc.value.failure_code == "FROZEN_EXTRA_REACTION_ID", (
        f"got {exc.value.failure_code}"
    )


# -- 6. snapshot identity / reaction hashes / version are cross-bound --------


def test_snapshot_identity_and_reaction_hashes_are_cross_bound():
    fx = _hydrolysis()
    root = _frozen_root()
    tv, donor, ref = _rebuild_tv(fx, authority=root)
    # Baseline: the complete reaction loads under the frozen root.
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    assert dev.context.reaction_id == "fx_hydrolysis"

    # Tampering with ANY cross-bound field breaks the manifest self-hash.
    tampered_snapshot = replace(root, snapshot_id="FORGED_SNAPSHOT")
    tv2, donor2, ref2 = _rebuild_tv(fx, authority=tampered_snapshot)
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv2, donor2.donor_id, ref2)
    assert exc.value.failure_code == "FROZEN_MANIFEST_SELF_HASH_MISMATCH", (
        f"snapshot identity tamper: got {exc.value.failure_code}"
    )

    tampered_hash = replace(root, snapshot_hash="deadbeef" * 8)
    tv3, donor3, ref3 = _rebuild_tv(fx, authority=tampered_hash)
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv3, donor3.donor_id, ref3)
    assert exc.value.failure_code == "FROZEN_MANIFEST_SELF_HASH_MISMATCH", (
        f"snapshot hash tamper: got {exc.value.failure_code}"
    )

    tampered_version = replace(root, version="p3-forged")
    tv4, donor4, ref4 = _rebuild_tv(fx, authority=tampered_version)
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv4, donor4.donor_id, ref4)
    assert exc.value.failure_code == "FROZEN_MANIFEST_SELF_HASH_MISMATCH", (
        f"version tamper: got {exc.value.failure_code}"
    )

    tampered_rx = replace(
        root, reaction_hashes={**root.reaction_hashes, "fx_hydrolysis": "y" * 64},
    )
    tv5, donor5, ref5 = _rebuild_tv(fx, authority=tampered_rx)
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv5, donor5.donor_id, ref5)
    assert exc.value.failure_code == "FROZEN_MANIFEST_SELF_HASH_MISMATCH", (
        f"reaction hash tamper: got {exc.value.failure_code}"
    )


# -- 7. fully-synchronized all-representations A/B strip is rejected ---------


def _fully_synchronized_ab_strip():
    """Strip hydrolysis to A/B-only in EVERY representation, keeping the
    record internally consistent so the ONLY rejection is the frozen
    authority root.

    Strips: participants, evidence participants, mapping (mapped pairs),
    source ledger (all entry families), lineages, raw/normalized reaction and
    fixture reactant/product SMILES.  The local reaction hash and train-view
    hash are recomputed by the caller; the upstream frozen root is NOT
    touched.
    """
    fx = _hydrolysis()
    keep_ids = {fx.donor_participant_id, "fx_hydrolysis_product_0"}
    keep = [p for p in fx.participants if p.participant_id in keep_ids]
    kept_lineages = [
        l for l in fx.lineages
        if l.reactant_participant_id in keep_ids
        and l.product_participant_id in keep_ids
    ]
    # mapping: keep only pairs referencing the A/B participants
    fma = fx.mapping_report.formal_mapped_source_assignment
    new_fma = None
    if fma is not None:
        new_fma = fma.model_copy(update={
            "mapped_atom_pairs": [
                p for p in fma.mapped_atom_pairs
                if p.reactant_participant_id in keep_ids
                and p.product_participant_id in keep_ids
            ],
        })
    new_mapping = fx.mapping_report.model_copy(update={
        "formal_mapped_source_assignment": new_fma,
    })
    # source ledger: keep only entries referencing the A/B participants
    led = fx.source_ledger
    new_led = led.model_copy(update={
        "reactant_entries": [
            e for e in led.reactant_entries if e.participant_id in keep_ids
        ],
        "product_entries": [
            e for e in led.product_entries if e.participant_id in keep_ids
        ],
        "role_assignments": [
            r for r in led.role_assignments if r.participant_id in keep_ids
        ],
        "stoichiometry": [
            e for e in led.stoichiometry if e.participant_id in keep_ids
        ],
        "formal_atom_transfer_assignments": [
            t for t in led.formal_atom_transfer_assignments
            if t.source_participant_id in keep_ids
            and t.target_participant_id in keep_ids
        ],
        "added_atom_sources": [
            s for s in led.added_atom_sources
            if s.source_participant_id in keep_ids
        ],
        "removed_atom_sinks": [
            s for s in led.removed_atom_sinks if s.sink_participant_id in keep_ids
        ],
    })
    reactant_smiles = [fx.reactant_smiles[0]]
    product_smiles = [fx.product_smiles[0]]
    ab_reaction = ".".join(reactant_smiles) + ">>" + ".".join(product_smiles)
    ev = fx.evidence.model_copy(update={
        "participants": keep,
        "resolved_transformed_lineages": [l.lineage_id for l in kept_lineages],
        "mapping_report": new_mapping,
        "source_reaction_ledger": new_led,
        "raw_reaction": ab_reaction,
        "normalized_reaction": ab_reaction,
    })
    return replace(
        fx, participants=keep, evidence=ev, mapping_report=new_mapping,
        lineages=kept_lineages, source_ledger=new_led,
        reactant_smiles=reactant_smiles, product_smiles=product_smiles,
    )


def test_fully_synchronized_all_representations_ab_strip_rejected():
    fx = _hydrolysis()
    root = _frozen_root()
    stripped = _fully_synchronized_ab_strip()
    # Sanity: the strip is genuinely synchronized (every representation A/B).
    assert len(stripped.participants) == 2
    assert len(stripped.source_ledger.reactant_entries) == 1
    assert len(stripped.evidence.participants) == 2
    assert stripped.evidence.raw_reaction == (
        ".".join(stripped.reactant_smiles) + ">>" + ".".join(stripped.product_smiles)
    )
    # The caller recomputed the local hashes (self-consistent train view) ...
    tv, donor, ref = _rebuild_tv(stripped, authority=root)
    # ... but the upstream frozen root is UNCHANGED and governs.
    assert root.reaction_hashes["fx_hydrolysis"] != canonical_reaction_hash(stripped)
    with pytest.raises((FoldIsolationError, IncompleteReactionError)) as exc:
        load_reaction_evidence(tv, donor.donor_id, ref)
    assert exc.value.failure_code == "FROZEN_REACTION_HASH_MISMATCH", (
        f"got {exc.value.failure_code}"
    )


# -- 8. real retrieval stripping never mutates the reaction authority --------


def test_real_retrieval_stripping_does_not_mutate_complete_reaction_authority():
    fx = _hydrolysis()
    root = _frozen_root()
    tv, donor, ref = _rebuild_tv(fx, authority=root)
    # Capture the complete reaction authority + object BEFORE retrieval.
    before_hash = canonical_reaction_hash(fx)
    before_dump = fx.evidence.model_dump(mode="json")
    # Run the REAL retrieval pipeline (identity/cofactor stripping + dedup +
    # fingerprint ranking) on the actual train view.
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, tv)
    assert result.donors, "retrieval must run on the real train view"
    # The complete reaction object and its authority hash are UNCHANGED.
    assert canonical_reaction_hash(fx) == before_hash, (
        "retrieval must not mutate the complete reaction authority hash"
    )
    assert fx.evidence.model_dump(mode="json") == before_dump, (
        "retrieval must not mutate the complete reaction evidence object"
    )
    # The loader still accepts the complete reaction under the frozen root.
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    assert dev.reaction_authority_hash == before_hash