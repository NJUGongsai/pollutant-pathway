"""R7-B: fixture authority and production authority are TYPE-ISOLATED.

ChatGPT P3 Round 6 audit finding (NOT CLOSED):

``FrozenAuthorityManifest`` was a plain, public, constructible dataclass
(``kind: str`` / ``provenance: str`` / ``manifest_hash: str``).  The
production loader's core check was ``train_view.authority_manifest.kind ==
"production"``, and ``authority_manifest_hash()`` is public with every
self-hash input caller-controlled.  A caller could therefore build a fixture
root, ``dataclasses.replace`` its ``kind`` to ``production``, change the
provenance, recompute the public self-hash, and the production loader
accepted it.

R7-B contract:
- fixture manifest and production authority are DIFFERENT types;
- ``build_fixture_authority_manifest()`` ALWAYS returns a
  ``FixtureAuthorityManifest`` whose ``kind`` is FIXED at
  ``synthetic_fixture`` (``__post_init__`` rejects any relabeling);
- the real loader REQUIRES a ``ProductionAuthorityHandle`` — a plain
  ``kind="production"`` manifest is never accepted;
- ``ProductionAuthorityHandle`` can ONLY be created by the internal P1/P2
  authority adapter (module-private proof token); a public caller cannot
  construct one;
- while the real P1/P2 root is unavailable, the real loader / kernel return
  ``PRODUCTION_AUTHORITY_UNAVAILABLE`` (typed BLOCKED) — they never
  manufacture a production root;
- fixture mode continues to allow fixture authority, and evidence kind stays
  synthetic fixture;
- the self-hash is an integrity check only, never a provenance authority.

These tests are RED on the R6 code and GREEN after R7-B.
"""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from reaction_agent.p3.fixtures import (
    DonorEntry,
    FixtureAuthorityManifest,
    FrozenAuthorityManifest,
    ProductionAuthorityHandle,
    ReactionRef,
    TrainView,
    authority_manifest_hash,
    build_fixture_authority_manifest,
    canonical_reaction_hash,
    load_fixture_reactions,
    recompute_train_view_hash,
    select_primary_lineage,
    strip_atom_maps,
)
from reaction_agent.p3.load import (
    IncompleteReactionError,
    load_reaction_evidence,
)
from reaction_agent.p3.kernel import run_kernel
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
        donor_id="donor_r7b", molecule_id=donor_p.molecule_id,
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


def _frozen_root():
    fx = _hydrolysis()
    return build_fixture_authority_manifest({fx.reaction_id: fx})


# -- 1. the audit's decisive repro: relabel + rehash as production ------------


def test_fixture_root_relabelled_and_rehashed_as_production_is_rejected():
    """The audit's exact five-step attack against the seven-step repro:

    The attacker tries to turn a caller-built fixture root into a production
    authority by relabeling ``kind``, changing provenance and recomputing the
    public self-hash.  R7-B type isolation makes this IMPOSSIBLE: the fixture
    type's ``kind`` is fixed (relabeling raises), and even a fixture root
    passed unchanged to the real loader is rejected with
    ``FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY``.
    """
    fx = _hydrolysis()
    root = _frozen_root()

    # 1. build the fixture root (public API) — it is a FixtureAuthorityManifest.
    assert isinstance(root, FixtureAuthorityManifest)
    assert isinstance(root, FrozenAuthorityManifest)  # backward-compatible alias
    assert root.kind == "synthetic_fixture"

    # 2.+3. relabel kind -> production + change provenance: the FIXED kind
    # makes the relabel itself fail (type isolation, not a loader check).
    with pytest.raises(ValueError):
        replace(root, kind="production", provenance="caller-claims-p1-production")

    # 4. recomputing the public self-hash is fine but grants nothing — the
    # type is still a fixture manifest.
    recomputed = replace(root, provenance="caller-claims-p1-production")
    recomputed = replace(
        recomputed, manifest_hash=authority_manifest_hash(recomputed)
    )
    assert isinstance(recomputed, FixtureAuthorityManifest)

    # 5.+6. the real loader must reject the fixture root (even with a
    # recomputed self-hash) under EvidenceKind.real.
    tv, donor, ref = _rebuild_tv(fx, authority=recomputed)
    with pytest.raises(IncompleteReactionError) as exc:
        load_reaction_evidence(
            tv, donor.donor_id, ref, evidence_kind=EvidenceKind.real,
        )
    assert exc.value.failure_code == (
        "FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY"
    ), f"got {exc.value.failure_code}"


# -- 2. fixture kind is immutable --------------------------------------------


def test_fixture_manifest_kind_is_immutable():
    """Relabeling the kind of a fixture manifest must fail by construction."""
    root = _frozen_root()
    with pytest.raises(ValueError):
        replace(root, kind="production")
    with pytest.raises(ValueError):
        FixtureAuthorityManifest(
            snapshot_id=root.snapshot_id,
            snapshot_hash=root.snapshot_hash,
            reaction_hashes=root.reaction_hashes,
            kind="production",
        )


# -- 3. fixture root passed to real loader is rejected ------------------------


def test_fixture_root_passed_to_real_loader_is_rejected():
    """Even WITHOUT any relabeling, a fixture root is never a production
    authority — the real loader rejects it with a typed code."""
    fx = _hydrolysis()
    root = _frozen_root()
    tv, donor, ref = _rebuild_tv(fx, authority=root)
    with pytest.raises(IncompleteReactionError) as exc:
        load_reaction_evidence(
            tv, donor.donor_id, ref, evidence_kind=EvidenceKind.real,
        )
    assert exc.value.failure_code == (
        "FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY"
    ), f"got {exc.value.failure_code}"


# -- 4. public caller cannot construct a production handle --------------------


def test_public_caller_cannot_construct_production_handle():
    """ProductionAuthorityHandle requires the module-private proof token; a
    public caller cannot construct one, and a fixture manifest can never be
    converted into one."""
    root = _frozen_root()
    with pytest.raises(TypeError):
        ProductionAuthorityHandle(
            snapshot_id=root.snapshot_id,
            snapshot_hash=root.snapshot_hash,
            reaction_hashes=root.reaction_hashes,
        )
    # dataclasses.replace preserves the (private) proof, so a caller cannot
    # inject a fake proof either — the proof is not even creatable.
    with pytest.raises(TypeError):
        ProductionAuthorityHandle(
            snapshot_id="s", snapshot_hash="h", reaction_hashes={},
            _proof=object(),
        )


# -- 5. real kernel with a fixture authority blocks with a typed code ---------


def test_real_kernel_with_fixture_authority_returns_production_authority_unavailable(monkeypatch):
    """The real-mode kernel must not accept a fixture authority as a
    production root.  While the real P1/P2 root is unavailable it returns
    PRODUCTION_AUTHORITY_UNAVAILABLE (typed BLOCKED) — it never manufactures
    a production root."""
    fx = _hydrolysis()
    root = _frozen_root()
    tv, donor, ref = _rebuild_tv(fx, authority=root)
    from reaction_agent.p3.schemas import CapabilityStatus
    fake_cap = CapabilityStatus(
        run_id="r", query_id="q", fold_id="fold_fx_p3", case_id="c",
        snapshot_id="snap_x", snapshot_hash="h" * 64,
    )
    monkeypatch.setattr(
        "reaction_agent.p3.kernel.build_capability_status",
        lambda *args, **kwargs: (fake_cap, []),
    )
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r7b_real", fold_id="fold_fx_p3",
        mode="real", train_view=tv,
    )
    assert result.status.value in ("blocked", "failed"), (
        f"real kernel with fixture authority must fail-closed, got "
        f"{result.status.value}"
    )
    assert any(
        f.failure_code == "PRODUCTION_AUTHORITY_UNAVAILABLE"
        for f in result.failures
    ), f"got {[f.failure_code for f in result.failures]}"


# -- 6. fixture mode still works with a fixture authority ---------------------


def test_fixture_mode_still_works_with_fixture_authority():
    """Fixture mode continues to allow the fixture authority; the evidence
    kind stays synthetic_fixture (never elevated to real)."""
    fx = _hydrolysis()
    root = _frozen_root()
    tv, donor, ref = _rebuild_tv(fx, authority=root)
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    assert dev.evidence_kind is EvidenceKind.synthetic_fixture
    assert dev.context.evidence_kind is EvidenceKind.synthetic_fixture
    assert dev.context.reaction_id == "fx_hydrolysis"


# -- 7. invalid authority root fails closed -----------------------------------


def test_invalid_authority_root_fails_closed():
    """A bare dict / arbitrary object smuggled as the authority root must be
    rejected with INVALID_AUTHORITY_ROOT (fail-closed)."""
    fx = _hydrolysis()
    tv, donor, ref = _rebuild_tv(fx, authority={"kind": "production"})
    from reaction_agent.p3.load import FoldIsolationError
    with pytest.raises(FoldIsolationError) as exc:
        load_reaction_evidence(tv, donor.donor_id, ref)
    assert exc.value.failure_code == "INVALID_AUTHORITY_ROOT", (
        f"got {exc.value.failure_code}"
    )