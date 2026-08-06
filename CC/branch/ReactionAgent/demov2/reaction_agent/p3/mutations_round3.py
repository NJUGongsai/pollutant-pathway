"""R3-F real mutation evidence: executable baseline + mutated cases.

Each mutation case provides an EXECUTABLE baseline scenario and mutated
scenario running the REAL production path (loader / transform / sites /
validate / kernel / gate / schemas).  A scenario returns::

    (status, failure_code, artifact_dict)

with status ``PASS`` (invariant held / mutation escaped) or ``FAIL``
(production machinery rejected the mutation) plus the TYPED failure code the
machinery actually emitted.  Unexpected exceptions become ``ERROR`` in the
harness.  The observed failure code is NEVER copied from the expected code —
it comes from the production rejection itself.
"""
from __future__ import annotations

from dataclasses import replace

from reaction_agent.p3.fixtures import (
    DonorEntry,
    ReactionRef,
    TrainView,
    build_train_view,
    canonical_reaction_hash,
    find_donor_ref,
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


def _tv():
    return build_train_view(load_fixture_reactions())


def _oct_load():
    tv = _tv()
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    return tv, donor, ref, dev


def _load_artifact(dev) -> dict:
    return {
        "reaction_id": dev.context.reaction_id,
        "donor_id": dev.donor_id,
        "mapping_status": dev.context.mapping_report.mapping_status.value,
        "ledger_id": dev.context.source_ledger.ledger_id,
        "lineages": len(dev.context.resolved_lineages),
    }


def _attach_fixture_authority(tv: TrainView) -> TrainView:
    """R6-C: freeze the FIXTURE authority for the train view's reactions and
    attach it (synthetic_fixture semantics — never a production authority)."""
    from reaction_agent.p3.fixtures import build_fixture_authority_manifest
    return replace(
        tv,
        authority_manifest=build_fixture_authority_manifest(tv.reactions),
    )


def _forced_tv(fixture):
    """Build a self-consistent train view containing ONE fixture regardless
    of eligibility filtering (reaction hash + snapshot hash recomputed).

    R6-C: the train view always carries a frozen FIXTURE authority (built
    from the indexed content) so the loader never runs without an upstream
    authority handle.
    """
    donor_participant = next(
        p for p in fixture.participants
        if p.participant_id == fixture.donor_participant_id
    )
    lineage = select_primary_lineage(fixture)
    ref = ReactionRef(
        reaction_id=fixture.reaction_id,
        donor_participant_id=fixture.donor_participant_id,
        lineage_id=lineage.lineage_id if lineage else "l0",
        reaction_hash=canonical_reaction_hash(fixture),
    )
    donor = DonorEntry(
        donor_id="donor_forced",
        molecule_id=donor_participant.molecule_id,
        canonical_smiles=donor_participant.canonical_smiles,
        structural_smiles=strip_atom_maps(donor_participant.canonical_smiles),
        donor_eligibility="eligible",
        source_quality="synthetic_fixture",
        fold_id="fold_fx_p3",
        reaction_refs=[ref],
    )
    draft = TrainView(
        fold_id="fold_fx_p3", snapshot_id="fx_snapshot_p3", snapshot_hash="",
        donors=[donor], reactions={fixture.reaction_id: fixture},
    )
    return _attach_fixture_authority(TrainView(
        fold_id=draft.fold_id, snapshot_id=draft.snapshot_id,
        snapshot_hash=recompute_train_view_hash(draft),
        donors=draft.donors, reactions=draft.reactions,
    ))


# -- 1. A/B-only stripped reaction -------------------------------------------
# R4-E: the mutation starts from a COMPLETE, baseline-PASS reaction
# authority (hydrolysis: ester + H2O -> acid + alcohol), strips it to A/B-only
# (removes the co-substrate H2O and the co-product while the source ledger
# still records the contract-required information), recomputes every hash the
# attacker can recompute, and expects the LOADER to reject it on the
# completeness/authority path (INCOMPLETE_REACTION) — NOT on a hand-written
# wrong hash.


def _rebuilt_tv(fx):
    """Self-consistent single-fixture train view (reaction hash + snapshot
    hash recomputed).

    R6-C: the train view always carries a frozen FIXTURE authority (built
    from the indexed content) so the loader never runs without an upstream
    authority handle.
    """
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
        donor_id="donor_forced",
        molecule_id=donor_p.molecule_id,
        canonical_smiles=donor_p.canonical_smiles,
        structural_smiles=strip_atom_maps(donor_p.canonical_smiles),
        donor_eligibility="eligible",
        source_quality="synthetic_fixture",
        fold_id="fold_fx_p3",
        reaction_refs=[ref],
    )
    draft = TrainView(
        fold_id="fold_fx_p3", snapshot_id="fx_snapshot_p3", snapshot_hash="",
        donors=[donor], reactions={fx.reaction_id: fx},
    )
    tv = _attach_fixture_authority(TrainView(
        fold_id=draft.fold_id, snapshot_id=draft.snapshot_id,
        snapshot_hash=recompute_train_view_hash(draft),
        donors=draft.donors, reactions=draft.reactions,
    ))
    return tv, donor, ref


def case_ab_only_baseline():
    """R5-C: baseline loads a COMPLETE hydrolysis reaction under the FROZEN
    authority root (built by the P1 snapshot builder before the run)."""
    fixtures = load_fixture_reactions()
    fx = fixtures["rxn_hydrolysis"]
    from reaction_agent.p3.fixtures import build_fixture_authority_manifest
    root = build_fixture_authority_manifest({"rxn_hydrolysis": fx})
    tv, donor, ref = _rebuilt_tv(fx)
    dev = load_reaction_evidence(
        tv, donor.donor_id, ref, authority_manifest=root,
    )
    return "PASS", "", {
        "reaction_id": dev.context.reaction_id,
        "participants": len(dev.context.reaction_evidence.participants),
        "authority_snapshot_hash": root.snapshot_hash,
    }


def case_ab_only_mutated():
    """R5-C: the fully-synchronized A/B-only strip is rejected by the FROZEN
    authority root.

    Steps (per the R5-C remediation): start from the frozen-authority
    baseline-PASS complete hydrolysis; strip ALL A/B-only representations
    (participants, ledger refs, mapping, lineages, raw reaction strings);
    recompute every hash the attacker can recompute (local reaction hash +
    caller TrainView hash); DO NOT replace the frozen expected root; go
    through the REAL P3 loader path; the loader must reject with
    FROZEN_REACTION_HASH_MISMATCH / REACTION_AUTHORITY_MISMATCH /
    INCOMPLETE_REACTION — never because a participant/ledger set mismatch
    was deliberately left in.
    """
    from reaction_agent.p3.fixtures import build_fixture_authority_manifest
    fixtures = load_fixture_reactions()
    fx = fixtures["rxn_hydrolysis"]
    # FROZEN root from the COMPLETE baseline — never rebuilt from mutated content.
    root = build_fixture_authority_manifest({"rxn_hydrolysis": fx})
    # Fully-synchronized strip: A/B-only in every representation.
    keep = [p for p in fx.participants if p.participant_id in (
        fx.donor_participant_id,
        "fx_hydrolysis_product_0",
    )]
    ev = fx.evidence.model_copy(update={"participants": keep})
    mutated = replace(fx, participants=keep, evidence=ev)
    tv, donor, ref = _rebuilt_tv(mutated)
    try:
        load_reaction_evidence(tv, donor.donor_id, ref, authority_manifest=root)
    except (IncompleteReactionError, FoldIsolationError) as exc:
        return "FAIL", exc.failure_code, {"rejected": "ab_only_stripped"}
    return "PASS", "", {"accepted": "ab_only_stripped"}


# -- 2. Deleted participant ----------------------------------------------------


def case_deleted_participant_baseline():
    _, _, _, dev = _oct_load()
    return "PASS", "", _load_artifact(dev)


def case_deleted_participant_mutated():
    tv, donor, ref, _ = _oct_load()
    fixture = tv.reactions["rxn_oct"]
    mutated_evidence = fixture.evidence.model_copy(update={
        "participants": fixture.evidence.participants[:1],
    })
    mutated = replace(fixture, evidence=mutated_evidence)
    # R4-B: participants are part of the reaction authority preimage — the
    # mutation must recompute the authority hash and the snapshot hash so it
    # stays self-consistent, and the rejection comes from the COMPLETE-RECORD
    # consistency check (participant multiset mismatch -> INCOMPLETE_REACTION),
    # never from a stale hash (a shallower gate).
    new_ref = ReactionRef(
        reaction_id=ref.reaction_id,
        donor_participant_id=ref.donor_participant_id,
        lineage_id=ref.lineage_id,
        reaction_hash=canonical_reaction_hash(mutated),
    )
    new_donors = [
        replace(d, reaction_refs=[
            new_ref if r.reaction_id == ref.reaction_id else r
            for r in d.reaction_refs
        ])
        for d in tv.donors
    ]
    draft = TrainView(
        fold_id=tv.fold_id, snapshot_id=tv.snapshot_id, snapshot_hash="",
        donors=new_donors,
        reactions={**tv.reactions, "rxn_oct": mutated},
    )
    mutated_tv = _attach_fixture_authority(TrainView(
        fold_id=draft.fold_id, snapshot_id=draft.snapshot_id,
        snapshot_hash=recompute_train_view_hash(draft),
        donors=draft.donors, reactions=draft.reactions,
    ))
    try:
        load_reaction_evidence(mutated_tv, donor.donor_id, new_ref)
    except IncompleteReactionError as exc:
        return "FAIL", exc.failure_code, {"rejected": "deleted_participant"}
    return "PASS", "", {"accepted": "deleted_participant"}


# -- 3. Partial mapping ---------------------------------------------------------


def case_partial_mapping_baseline():
    fixtures = load_fixture_reactions()
    tv = _forced_tv(fixtures["rxn_oct"])
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    return "PASS", "", _load_artifact(dev)


def case_partial_mapping_mutated():
    from reaction_agent.p3.fixtures import build_fixture_reaction
    fx = build_fixture_reaction(
        name="partial_map",
        reactant_smiles=["[CH3:1][CH2:2][OH:3]"],
        product_smiles=["[CH3:1][CH:2]=O"],  # product O unmapped -> partial
    )
    tv = _forced_tv(fx)
    donor, ref = find_donor_ref(tv, "fx_partial_map")
    try:
        load_reaction_evidence(tv, donor.donor_id, ref)
    except IncompleteReactionError as exc:
        return "FAIL", exc.failure_code, {"rejected": "partial_mapping"}
    return "PASS", "", {"accepted": "partial_mapping"}


# -- 4. Missing lineage ----------------------------------------------------------


def case_missing_lineage_baseline():
    _, _, _, dev = _oct_load()
    return "PASS", "", _load_artifact(dev)


def case_missing_lineage_mutated():
    fixtures = load_fixture_reactions()
    fx = fixtures["rxn_oct"]
    evidence = fx.evidence.model_copy(update={"resolved_transformed_lineages": []})
    fixture2 = replace(fx, evidence=evidence, lineages=[])
    tv = _forced_tv(fixture2)
    donor, ref = find_donor_ref(tv, "fx_oct")
    try:
        load_reaction_evidence(tv, donor.donor_id, ref)
    except IncompleteReactionError as exc:
        return "FAIL", exc.failure_code, {"rejected": "missing_lineage"}
    return "PASS", "", {"accepted": "missing_lineage"}


# -- 5. Skipped preconditions ----------------------------------------------------


def _oct_transform():
    from reaction_agent.p3.transform import extract_transform
    _, _, ref, dev = _oct_load()
    return extract_transform(dev, lineage_id=ref.lineage_id)


def case_preconditions_baseline():
    from reaction_agent.p3.normalize import normalize_query
    from reaction_agent.p3.sites import enumerate_sites
    from reaction_agent.p3.schemas import SiteEligibility
    tr = _oct_transform()
    query = normalize_query("CCCCCCCCO")
    sites = enumerate_sites(tr, query)
    eligible = [s for s in sites if s.eligibility is SiteEligibility.eligible]
    if not eligible:
        return "FAIL", "NO_ELIGIBLE_SITE", {"eligible_sites": 0}
    return "PASS", "", {"eligible_sites": len(eligible)}


def case_preconditions_mutated():
    from reaction_agent.p3.normalize import normalize_query
    from reaction_agent.p3.sites import enumerate_sites
    from reaction_agent.p3.schemas import SiteEligibility
    tr = _oct_transform()
    query = normalize_query("CC(C)O")  # secondary alcohol
    sites = enumerate_sites(tr, query)
    eligible = [s for s in sites if s.eligibility is SiteEligibility.eligible]
    if eligible:
        return "PASS", "", {"eligible_sites": len(eligible)}  # false positive
    failed = sum(len(s.failed_preconditions) for s in sites)
    return "FAIL", "PRECONDITION_FAILED", {
        "eligible_sites": 0, "failed_preconditions": failed,
    }


# -- 6. Forged source ledger ------------------------------------------------------


def _validate_parts():
    from reaction_agent.p3.normalize import normalize_query
    from reaction_agent.p3.sites import enumerate_sites
    from reaction_agent.p3.generate import generate_product
    from reaction_agent.p3.validate import validate_candidate
    from reaction_agent.p3.schemas import SiteEligibility
    from reaction_agent.hashing import stable_id
    _, _, ref, dev = _oct_load()
    tr = _oct_transform()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q)
            if s.eligibility is SiteEligibility.eligible][0]
    report = generate_product(tr, site, q)
    candidate_id = stable_id("cand", {
        "identity": report.canonical_product, "version": "p3-1",
    })
    validation, cal = validate_candidate(
        dev, tr, site, report, q, candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    return ref, dev, tr, site, report, q, candidate_id, validation, cal


def case_forged_ledger_baseline():
    ref, dev, tr, site, report, q, cid, _, _ = _validate_parts()
    from reaction_agent.p3.validate import validate_candidate
    validation, _ = validate_candidate(
        dev, tr, site, report, q, candidate_id=cid,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    if validation.failure_code:
        return "FAIL", validation.failure_code, validation.model_dump(mode="json")
    return "PASS", "", {"failure_code": None}


def case_forged_ledger_mutated():
    ref, dev, tr, site, report, q, cid, _, _ = _validate_parts()
    from reaction_agent.p3.validate import validate_candidate
    validation, _ = validate_candidate(
        dev, tr, site, report, q, candidate_id=cid,
        source_ledger_id="srl_FORGED",
    )
    if validation.failure_code:
        return "FAIL", validation.failure_code, validation.model_dump(mode="json")
    return "PASS", "", {"accepted": "forged_source_ledger"}


# -- 7. Fold pollution -------------------------------------------------------------


def case_fold_pollution_baseline():
    _, _, _, dev = _oct_load()
    return "PASS", "", _load_artifact(dev)


def case_fold_pollution_mutated():
    tv = _tv()
    polluted = TrainView(
        fold_id="fold_test",  # wrong fold
        snapshot_id=tv.snapshot_id, snapshot_hash=tv.snapshot_hash,
        donors=tv.donors, reactions=tv.reactions,
        authority_manifest=tv.authority_manifest,
    )
    donor, ref = find_donor_ref(tv, "fx_oct")
    try:
        load_reaction_evidence(polluted, donor.donor_id, ref)
    except FoldIsolationError as exc:
        return "FAIL", exc.failure_code, {"rejected": "fold_pollution"}
    return "PASS", "", {"accepted": "fold_pollution"}


# -- 8. Relaxed edit in strict lane -------------------------------------------------


def _valid_candidate():
    from reaction_agent.p3.schemas import (
        CandidateEvidencePath,
        StrictCandidate,
        compute_candidate_path_binding,
    )
    ref, dev, tr, site, report, q, cid, validation, cal = _validate_parts()
    ns = {
        "run_id": "run_mrelax", "case_id": "case_mrelax",
        "query_id": q.query_id, "fold_id": "fold_fx_p3",
        "snapshot_id": dev.snapshot_id, "snapshot_hash": dev.snapshot_hash,
    }
    fields = {
        "donor_id": dev.donor_id, "reaction_id": ref.reaction_id,
        "lineage_id": ref.lineage_id,
        "transformation_id": tr.transformation_id, "site_id": site.site_id,
        "generation_report": report,
        "source_ledger_id": dev.context.source_ledger.ledger_id,
        "candidate_analogy_ledger": cal,
    }
    path_id, path_hash = compute_candidate_path_binding(**fields, **ns)
    path = CandidateEvidencePath(
        **fields, validation=validation, path_id=path_id, path_hash=path_hash,
    )
    candidate = StrictCandidate(
        candidate_id=cid,
        canonical_product_identity=report.canonical_product,
        lane="strict", origin="deterministic_kernel",
        generation_paths=[report],
        support_lineage_ids=[ref.lineage_id],
        transformation_ids=[tr.transformation_id],
        site_ids=[site.site_id],
        validation=validation,
        source_ledger_ids=[dev.context.source_ledger.ledger_id],
        candidate_analogy_ledger=cal,
        candidate_evidence_paths=[path],
        provenance=["kernel:p3-1"],
        **ns,
    )
    return candidate


def case_relaxed_edit_baseline():
    candidate = _valid_candidate()
    return "PASS", "", {"candidate_id": candidate.candidate_id}


def case_relaxed_edit_mutated():
    from pydantic import ValidationError
    candidate = _valid_candidate()
    relaxed_validation = candidate.validation.model_copy(update={
        "relaxation_used": True,
    })
    forged = candidate.model_copy(update={
        "validation": relaxed_validation,
        "candidate_evidence_paths": [
            candidate.candidate_evidence_paths[0].model_copy(update={
                "validation": relaxed_validation,
            }),
        ],
    })
    try:
        type(candidate).model_validate(forged.model_dump(mode="json"))
    except ValidationError:
        return "FAIL", "RELAXATION_USED", {"rejected": "relaxed_edit"}
    return "PASS", "", {"accepted": "relaxed_edit"}


# -- 9. System failure as abstention --------------------------------------------------


def _minimal_blocked_result():
    from reaction_agent.p3.schemas import (
        CandidateTrace,
        CapabilityStatus,
        EvidenceKind,
        KernelFailure,
        KernelResult,
        KernelRunManifest,
        KernelStage,
        KernelStatus,
        NormalizationPolicy,
        NormalizedQuery,
        StageTraceEntry,
    )
    ns = {
        "run_id": "run_msys", "query_id": "q_msys", "case_id": "case_msys",
        "fold_id": "fold_msys",
    }
    manifest = KernelRunManifest(
        request="CCO", request_hash="h_request", **ns,
    )
    query = NormalizedQuery(
        input_smiles="CCO", canonical_smiles="CCO", identity_hash="h_id",
        heavy_atom_count=3, formal_charge=0, fragment_count=1,
        normalization_policy=NormalizationPolicy(version="p3-1"),
        evidence_kind=EvidenceKind.blocked, **ns,
    )
    capability = CapabilityStatus(**ns)
    trace = CandidateTrace(
        stages=[StageTraceEntry(stage=KernelStage.RECEIVED)],
        evidence_kind=EvidenceKind.blocked, **ns,
    )
    return KernelResult(
        status=KernelStatus.blocked,
        manifest=manifest, normalized_query=query,
        capability_status=capability, candidates=[], trace=trace,
        failures=[KernelFailure(
            failure_code="CAPABILITY_UNAVAILABLE", category="system",
            reason="real_snapshot unavailable", component="real_snapshot",
        )],
        evidence_kind=EvidenceKind.blocked, **ns,
    )


def case_system_as_abstention_baseline():
    result = _minimal_blocked_result()
    return "PASS", "", {"status": result.status.value}


def case_system_as_abstention_mutated():
    from pydantic import ValidationError
    from reaction_agent.p3.schemas import KernelFailure, KernelStatus
    base = _minimal_blocked_result()
    forged = base.model_copy(update={
        "status": KernelStatus.failed,
        "failures": [KernelFailure(
            failure_code="NO_COMPATIBLE_SITE", category="scientific",
            reason="fake abstention", component="decide",
        )],
    })
    try:
        type(base).model_validate(forged.model_dump(mode="json"))
    except ValidationError:
        return "FAIL", "SYSTEM_FAILURE_AS_ABSTENTION", {
            "rejected": "system_failure_as_abstention",
        }
    return "PASS", "", {"accepted": "system_failure_as_abstention"}


# -- 10. Forged Gate PASS ---------------------------------------------------------


def case_forged_gate_pass_baseline():
    """R5-B / R6-A: the baseline is a REAL executed gate chain — the
    production item constructors (kernel runs + capability probes) produce
    the typed items and the runner registers them as the opaque
    GateExecutionAuthority (R6-A: registration is private; the typed items
    are the trusted execution).

    The synthetic-valid mutation helper was REMOVED (R5-B: a fabricated /
    synthetic-valid mutation baseline must never enter Gate authority).
    This case deliberately does NOT call ``run_p3_gate`` (which would
    recursively execute the mutation suite from inside a harness subprocess);
    it verifies the execution-authority chain directly: the typed items are
    produced by REAL kernel executions and registered as the execution
    authority, so the machinery is proven executable.
    """
    from reaction_agent.p3.gate import (
        _kernel_machinery_items,
        _real_evidence_items,
        _register_execution_authority,
        _replay_item,
    )
    ns = {
        "fold_id": "fold_fx_p3",
        "snapshot_id": "fx_snapshot_p3",
        "snapshot_hash": "h",
    }
    items = [_replay_item(ns)] + _kernel_machinery_items(ns) + _real_evidence_items(ns)
    # R6-A: the runner registers the executed items as an opaque authority
    # (keyed by the run identity).  A public caller cannot construct one.
    _register_execution_authority("p3_gate", items)
    ok = (
        len(items) == 10
        and all(i.evidence for i in items)
        and all(i.status in ("PASS", "BLOCKED") for i in items)
    )
    if not ok:
        return "FAIL", "GATE_ITEMS_NOT_EXECUTED", {"items": len(items)}
    return "PASS", "", {"items": len(items), "verdict": "executed"}


def case_forged_gate_pass_mutated():
    from reaction_agent.p3.gate import evaluate_gate_artifact
    from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash
    # A valid schema hash but status-string items only: the rejection must
    # come from "stored status strings are never authority".  R5-A: without
    # the trusted execution context this can never be verified.
    forged = {
        "status": "PASS",
        "interface_manifest_schema_hash": manifest_schema_hash(build_interface_manifest()),
        "items": {f"G{i:02d}": "PASS" for i in range(1, 11)},
    }
    evaluation = evaluate_gate_artifact(forged)
    if evaluation.verdict == "PASS":
        return "PASS", "", {"accepted": "forged_gate_pass"}
    code = (
        evaluation.machinery_failures[0]
        if evaluation.machinery_failures else "GATE_REJECTED"
    )
    return "FAIL", code, {"verdict": evaluation.verdict}


# -- 11. Reaction hash forgery (R3-B) -----------------------------------------------


def case_reaction_hash_baseline():
    _, _, _, dev = _oct_load()
    return "PASS", "", _load_artifact(dev)


def case_reaction_hash_mutated():
    tv, donor, ref, _ = _oct_load()
    forged = ReactionRef(
        reaction_id=ref.reaction_id,
        donor_participant_id=ref.donor_participant_id,
        lineage_id=ref.lineage_id,
        reaction_hash="forged_reaction_hash_value",
    )
    try:
        load_reaction_evidence(tv, donor.donor_id, forged)
    except ReactionAuthorityError as exc:
        return "FAIL", exc.failure_code, {"rejected": "reaction_hash_forgery"}
    return "PASS", "", {"accepted": "reaction_hash_forgery"}


# -- 12. Transform hash collision (R3-C) ---------------------------------------------


def case_transform_collision_baseline():
    from reaction_agent.p3.transform import verify_transform_binding
    tr = _oct_transform()
    verify_transform_binding(tr)
    return "PASS", "", {"transformation_id": tr.transformation_id}


def case_transform_collision_mutated():
    from reaction_agent.p3.transform import (
        TransformBindingError,
        verify_transform_binding,
    )
    tr = _oct_transform()
    if tr.transferred_atoms:
        forged_atom = tr.transferred_atoms[0]
        mutated_atom = forged_atom.model_copy(update={
            "bonds_to": [{"atom_map": 1, "order": 2}],
        })
        kept = [mutated_atom] + list(tr.transferred_atoms[1:])
        forged = tr.model_copy(update={"transferred_atoms": kept})
    else:
        # octanol oxidation has no transferred atoms; mutate a bond order.
        forged = tr.model_copy(update={
            "bond_changes": [
                bc.model_copy(update={"new_order": 3})
                if bc.new_order is not None else bc
                for bc in tr.bond_changes
            ],
        })
    try:
        verify_transform_binding(forged)
    except TransformBindingError as exc:
        return "FAIL", exc.failure_code, {"rejected": "transform_collision"}
    return "PASS", "", {"accepted": "transform_collision"}


# -- 13. Forged evidence path (R3-E) ---------------------------------------------------


def case_forged_path_baseline():
    candidate = _valid_candidate()
    return "PASS", "", {"candidate_id": candidate.candidate_id}


def case_forged_path_mutated():
    from pydantic import ValidationError
    candidate = _valid_candidate()
    forged_path = candidate.candidate_evidence_paths[0].model_copy(update={
        "lineage_id": "lin_FORGED",
    })
    forged = candidate.model_copy(update={
        "candidate_evidence_paths": [forged_path],
        "support_lineage_ids": ["lin_FORGED"],
    })
    try:
        type(candidate).model_validate(forged.model_dump(mode="json"))
    except ValidationError:
        return "FAIL", "FORGED_EVIDENCE_PATH", {"rejected": "forged_path"}
    return "PASS", "", {"accepted": "forged_path"}


# -- 14. Bad reaction kernel crash (R3-D) ---------------------------------------------


def _corrupted_train_view():
    fixtures = load_fixture_reactions()
    fx = fixtures["rxn_oct"]
    donor_pid = fx.donor_participant_id
    participants = [
        p.model_copy(update={"canonical_smiles": "NOT_A_SMILES_%%%"})
        if p.participant_id == donor_pid else p
        for p in fx.participants
    ]
    evidence = fx.evidence.model_copy(update={"participants": participants})
    fixtures["rxn_oct"] = replace(fx, participants=participants, evidence=evidence)
    return build_train_view(fixtures)


def case_bad_reaction_baseline():
    from reaction_agent.p3.kernel import run_kernel
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="m_bad_base", fold_id="fold_fx_p3",
        mode="fixture",
    )
    if result.status.value != "completed" or not result.candidates:
        return "FAIL", "BASELINE_KERNEL_UNHEALTHY", {
            "status": result.status.value,
        }
    return "PASS", "", {"candidates": len(result.candidates)}


def case_bad_reaction_mutated():
    from reaction_agent.p3.kernel import run_kernel
    tv = _corrupted_train_view()
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="m_bad_mut", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv,
    )
    # The production kernel must ISOLATE the bad reaction: structured result,
    # typed system failures, and the good reactions still processed.
    system_failures = [f for f in result.failures if f.category == "system"]
    if not system_failures:
        return "PASS", "", {"accepted": "bad_reaction_not_recorded"}
    identities = {c.canonical_product_identity for c in result.candidates}
    if "C=CCCCCCC" not in identities:
        return "PASS", "", {"accepted": "good_reaction_lost"}
    return "FAIL", system_failures[0].failure_code, {
        "status": result.status.value,
        "system_failures": len(system_failures),
        "candidates": len(result.candidates),
    }


# -- Registry -------------------------------------------------------------------------
#
# R5-B: the mutation registry is a TYPED FROZEN CONTRACT.  Every entry binds
# the FULL metadata — mutation ID, target Gate item, expected failure code,
# baseline case, mutated case, component and schema version — NOT just the
# mutation ID.  The Gate compares the complete metadata and binds the
# canonical registry hash (``mutation_registry_hash``) to the current Gate
# execution.  A mutation whose target/expected/component/schema differ from
# the registry is a machinery failure even when the ID set matches.

MUTATION_REGISTRY = [
    {
        "mutation_id": "m_ab_only_stripped_reaction",
        "target_gate_item": "G03",
        # R5-C: the fully-synchronized A/B-only strip (every representation
        # stripped + local hashes recomputed) is rejected by the FROZEN
        # authority root via the real loader path — observed
        # FROZEN_REACTION_HASH_MISMATCH, never a shallow forged hash.
        "expected_failure_code": "FROZEN_REACTION_HASH_MISMATCH",
        "baseline": case_ab_only_baseline,
        "mutated": case_ab_only_mutated,
        "baseline_case": "case_ab_only_baseline",
        "mutated_case": "case_ab_only_mutated",
        "component": "reaction_agent.p3.load",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_deleted_participant",
        "target_gate_item": "G03",
        "expected_failure_code": "INCOMPLETE_REACTION",
        "baseline": case_deleted_participant_baseline,
        "mutated": case_deleted_participant_mutated,
        "baseline_case": "case_deleted_participant_baseline",
        "mutated_case": "case_deleted_participant_mutated",
        "component": "reaction_agent.p3.load",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_partial_mapping",
        "target_gate_item": "G03",
        "expected_failure_code": "PARTIAL_MAP",
        "baseline": case_partial_mapping_baseline,
        "mutated": case_partial_mapping_mutated,
        "baseline_case": "case_partial_mapping_baseline",
        "mutated_case": "case_partial_mapping_mutated",
        "component": "reaction_agent.p3.load",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_missing_lineage",
        "target_gate_item": "G03",
        "expected_failure_code": "INCOMPLETE_REACTION",
        "baseline": case_missing_lineage_baseline,
        "mutated": case_missing_lineage_mutated,
        "baseline_case": "case_missing_lineage_baseline",
        "mutated_case": "case_missing_lineage_mutated",
        "component": "reaction_agent.p3.load",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_skipped_preconditions",
        "target_gate_item": "G06",
        "expected_failure_code": "PRECONDITION_FAILED",
        "baseline": case_preconditions_baseline,
        "mutated": case_preconditions_mutated,
        "baseline_case": "case_preconditions_baseline",
        "mutated_case": "case_preconditions_mutated",
        "component": "reaction_agent.p3.sites",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_forged_source_ledger",
        "target_gate_item": "G07",
        "expected_failure_code": "FORGED_SOURCE_LEDGER",
        "baseline": case_forged_ledger_baseline,
        "mutated": case_forged_ledger_mutated,
        "baseline_case": "case_forged_ledger_baseline",
        "mutated_case": "case_forged_ledger_mutated",
        "component": "reaction_agent.p3.validate",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_fold_pollution",
        "target_gate_item": "G02",
        "expected_failure_code": "FOLD_ISOLATION",
        "baseline": case_fold_pollution_baseline,
        "mutated": case_fold_pollution_mutated,
        "baseline_case": "case_fold_pollution_baseline",
        "mutated_case": "case_fold_pollution_mutated",
        "component": "reaction_agent.p3.load",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_relaxed_edit_strict",
        "target_gate_item": "G08",
        "expected_failure_code": "RELAXATION_USED",
        "baseline": case_relaxed_edit_baseline,
        "mutated": case_relaxed_edit_mutated,
        "baseline_case": "case_relaxed_edit_baseline",
        "mutated_case": "case_relaxed_edit_mutated",
        "component": "reaction_agent.p3.schemas",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_system_failure_as_abstention",
        "target_gate_item": "G09",
        "expected_failure_code": "SYSTEM_FAILURE_AS_ABSTENTION",
        "baseline": case_system_as_abstention_baseline,
        "mutated": case_system_as_abstention_mutated,
        "baseline_case": "case_system_as_abstention_baseline",
        "mutated_case": "case_system_as_abstention_mutated",
        "component": "reaction_agent.p3.schemas",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_forged_gate_pass",
        "target_gate_item": "G10",
        "expected_failure_code": "ARTIFACTLESS_PASS",
        "baseline": case_forged_gate_pass_baseline,
        "mutated": case_forged_gate_pass_mutated,
        "baseline_case": "case_forged_gate_pass_baseline",
        "mutated_case": "case_forged_gate_pass_mutated",
        "component": "reaction_agent.p3.gate",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_reaction_hash_forgery",
        "target_gate_item": "G03",
        "expected_failure_code": "REACTION_HASH_MISMATCH",
        "baseline": case_reaction_hash_baseline,
        "mutated": case_reaction_hash_mutated,
        "baseline_case": "case_reaction_hash_baseline",
        "mutated_case": "case_reaction_hash_mutated",
        "component": "reaction_agent.p3.load",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_transform_hash_collision",
        "target_gate_item": "G02",
        "expected_failure_code": "TRANSFORM_HASH_COLLISION",
        "baseline": case_transform_collision_baseline,
        "mutated": case_transform_collision_mutated,
        "baseline_case": "case_transform_collision_baseline",
        "mutated_case": "case_transform_collision_mutated",
        "component": "reaction_agent.p3.transform",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_forged_evidence_path",
        "target_gate_item": "G07",
        "expected_failure_code": "FORGED_EVIDENCE_PATH",
        "baseline": case_forged_path_baseline,
        "mutated": case_forged_path_mutated,
        "baseline_case": "case_forged_path_baseline",
        "mutated_case": "case_forged_path_mutated",
        "component": "reaction_agent.p3.schemas",
        "schema_version": "p3-1",
    },
    {
        "mutation_id": "m_bad_reaction_kernel_crash",
        "target_gate_item": "G06",
        "expected_failure_code": "TRANSFORM_EXTRACTION_FAILED",
        "baseline": case_bad_reaction_baseline,
        "mutated": case_bad_reaction_mutated,
        "baseline_case": "case_bad_reaction_baseline",
        "mutated_case": "case_bad_reaction_mutated",
        "component": "reaction_agent.p3.kernel",
        "schema_version": "p3-1",
    },
]

# R5-B: canonical registry hash.  The Gate binds this hash to the current
# execution; a registry drift (any metadata change) invalidates the whole
# mutation set.
MUTATION_REGISTRY_VERSION = "p3-r5-1"


def mutation_registry_hash() -> str:
    """Canonical hash of the FROZEN mutation contract (R5-B).

    Covers mutation ID, target Gate item, expected failure code, baseline
    case, mutated case, component and schema version for EVERY entry — the
    full metadata, not just the ID set.
    """
    from reaction_agent.hashing import canonical_hash

    contract = {
        "version": MUTATION_REGISTRY_VERSION,
        "entries": [
            {
                "mutation_id": c["mutation_id"],
                "target_gate_item": c["target_gate_item"],
                "expected_failure_code": c["expected_failure_code"],
                "baseline_case": c["baseline_case"],
                "mutated_case": c["mutated_case"],
                "component": c["component"],
                "schema_version": c["schema_version"],
            }
            for c in MUTATION_REGISTRY
        ],
    }
    return canonical_hash(contract)


def case_by_id(mutation_id: str) -> dict:
    for case in MUTATION_REGISTRY:
        if case["mutation_id"] == mutation_id:
            return case
    raise KeyError(f"unknown mutation case {mutation_id!r}")


def run_case(mutation_id: str, variant: str):
    """Execute ONE scenario in-process. Returns (status, code, artifact)."""
    case = case_by_id(mutation_id)
    if variant not in ("baseline", "mutated"):
        raise ValueError(f"unknown variant {variant!r}")
    return case[variant]()
