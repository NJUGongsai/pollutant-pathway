"""P3-T9 Deterministic predictor lifecycle (final_plan §6.10).

Lifecycle: RECEIVED -> NORMALIZED -> BASELINE_EVIDENCE_LOADED ->
HYPOTHESES_COMPILED -> SITES_ENUMERATED -> CANDIDATES_VALIDATED.

Output: unranked validated strict candidates + complete trace.  P3 does NOT
output rank / probability / final abstention decision (P4 owns those).

Modes:
- ``fixture`` : runs the machinery end-to-end on explicit synthetic fixtures
  (evidence_kind=synthetic_fixture).  Verifies machinery only.
- ``real``    : requires a real frozen snapshot + automatic donor view; when
  absent, returns status=blocked with typed system blockers (never a fake PASS).
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.p3.capability import build_capability_status
from reaction_agent.p3.fixtures import (
    TrainView,
    build_train_view,
    load_fixture_reactions,
)
from reaction_agent.p3.generate import generate_product
from reaction_agent.p3.load import (
    FoldIsolationError,
    IncompleteReactionError,
    load_reaction_evidence,
)
from reaction_agent.p3.normalize import (
    ChemistryBackendUnavailableError,
    InvalidQueryError,
    NormalizationPolicy,
    normalize_query,
)
from reaction_agent.p3.retrieve import RetrievalConfig, retrieve_donors
from reaction_agent.p3.schemas import (
    CandidateTrace,
    CapabilityStatus,
    ComponentVersion,
    EvidenceKind,
    KernelFailure,
    KernelResult,
    KernelRunManifest,
    KernelStage,
    KernelStatus,
    NormalizedQuery,
    StageTraceEntry,
    StrictCandidate,
)
from reaction_agent.p3.sites import enumerate_sites
from reaction_agent.p3.store import CandidateStore, _product_identity
from reaction_agent.p3.transform import TransformExtractionError, extract_transform
from reaction_agent.p3.validate import validate_candidate

KERNEL_VERSION = "p3-1"


def _run_manifest(
    *,
    run_id: str,
    request: str,
    request_hash: str,
    query_id: str,
    case_id: str,
    fold_id: str,
    snapshot_id: str,
    snapshot_hash: str,
    config: dict[str, str],
    seed: int,
) -> KernelRunManifest:
    manifest = KernelRunManifest(
        run_id=run_id,
        request=request,
        request_hash=request_hash,
        query_id=query_id,
        case_id=case_id,
        fold_id=fold_id,
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        config=config,
        component_versions=[
            ComponentVersion(name="p3_kernel", version=KERNEL_VERSION),
            ComponentVersion(name="normalization", version="p3-1"),
            ComponentVersion(name="retrieval", version="p3-1"),
            ComponentVersion(name="transform", version="p3-1"),
            ComponentVersion(name="graph_edit", version="p3-1"),
            ComponentVersion(name="validation", version="p3-1"),
            ComponentVersion(name="candidate_store", version="p3-1"),
        ],
        seed=seed,
        kernel_version=KERNEL_VERSION,
        schema_version="p3-1",
    )
    manifest = manifest.model_copy(update={
        "manifest_hash": canonical_hash(manifest.model_dump(mode="json"))
    })
    return manifest


def _scientific_failure(code: str, reason: str, component: str = "") -> KernelFailure:
    return KernelFailure(
        failure_code=code,
        category="scientific",
        reason=reason,
        component=component,
    )


def run_kernel(
    *,
    input_smiles: str,
    case_id: str,
    fold_id: str,
    mode: str = "fixture",
    snapshot_path: str | None = None,
    train_view: TrainView | None = None,
    seed: int = 0,
    policy: NormalizationPolicy | None = None,
    retrieval_config: RetrievalConfig | None = None,
    max_donors: int = 5,
) -> KernelResult:
    """Run the strict one-step kernel (deterministic baseline).

    Returns a KernelResult.  Scientific stops (no donor / no site / invalid
    input) yield status=completed with zero candidates plus a scientific
    KernelFailure.  System blockers (missing capability in real mode) yield
    status=blocked or failed with typed system failures.
    """
    run_id = stable_id("run", {
        "query": input_smiles,
        "case": case_id,
        "fold": fold_id,
        "mode": mode,
        "seed": seed,
    })
    query_id = stable_id("query", {"smiles": input_smiles, "seed": seed})
    request = canonical_hash({
        "query_smiles": input_smiles,
        "case_id": case_id,
        "fold_id": fold_id,
        "mode": mode,
        "seed": seed,
    })
    stages: list[StageTraceEntry] = []
    stages.append(StageTraceEntry(
        stage=KernelStage.RECEIVED,
        input_ref=input_smiles,
        content_hash=request,
    ))

    capability_status, system_failures = build_capability_status(
        run_id, query_id, fold_id, case_id, snapshot_path
    )

    # -- Normalize ----------------------------------------------------------
    try:
        query: NormalizedQuery = normalize_query(
            input_smiles, policy=policy, query_id=query_id,
            evidence_kind=_mode_kind(mode),
            run_id=run_id, case_id=case_id, fold_id=fold_id,
            snapshot_id=capability_status.snapshot_id,
            snapshot_hash=capability_status.snapshot_hash,
        )
        stages.append(StageTraceEntry(
            stage=KernelStage.NORMALIZED,
            output_ref=query.canonical_smiles,
            content_hash=query.identity_hash,
        ))
    except InvalidQueryError as exc:
        stages.append(StageTraceEntry(
            stage=KernelStage.NORMALIZED,
            failure_code="INVALID_INPUT",
            content_hash=canonical_hash({"invalid": input_smiles}),
        ))
        manifest = _run_manifest(
            run_id=run_id, request=input_smiles, request_hash=request,
            query_id=query_id, case_id=case_id, fold_id=fold_id,
            snapshot_id=capability_status.snapshot_id,
            snapshot_hash=capability_status.snapshot_hash,
            config={"mode": mode, "seed": str(seed)}, seed=seed,
        )
        trace = CandidateTrace(
            run_id=run_id, query_id=query_id, case_id=case_id, fold_id=fold_id,
            snapshot_id=capability_status.snapshot_id,
            snapshot_hash=capability_status.snapshot_hash,
            stages=stages, evidence_kind=_mode_kind(mode),
        )
        placeholder = _placeholder_query(input_smiles, query_id, _mode_kind(mode),
                                     run_id=run_id, case_id=case_id, fold_id=fold_id)
        return KernelResult(
            run_id=run_id, status=KernelStatus.completed, query_id=query_id,
            case_id=case_id, fold_id=fold_id,
            snapshot_id=capability_status.snapshot_id,
            snapshot_hash=capability_status.snapshot_hash,
            manifest=manifest, normalized_query=placeholder,
            capability_status=capability_status, candidates=[],
            trace=trace,
            failures=[_scientific_failure("INVALID_INPUT", str(exc), "normalize")],
            evidence_kind=_mode_kind(mode),
        )
    except ChemistryBackendUnavailableError as exc:
        return _system_failed_result(
            run_id, query_id, case_id, fold_id, capability_status, input_smiles,
            request, stages, system_failures + [KernelFailure(
                failure_code="CHEMISTRY_BACKEND_UNAVAILABLE", category="system",
                reason=str(exc), component="normalize",
            )], mode,
        )

    evidence_kind = _mode_kind(mode)

    # -- Evidence mode gate -------------------------------------------------
    if mode == "real":
        missing = [
            f for f in system_failures
            if f.failure_code == "CAPABILITY_UNAVAILABLE"
        ]
        if missing:
            trace = CandidateTrace(
                run_id=run_id, query_id=query_id, case_id=case_id,
                fold_id=fold_id, snapshot_id=capability_status.snapshot_id,
                snapshot_hash=capability_status.snapshot_hash,
                stages=stages, evidence_kind=EvidenceKind.blocked,
            )
            manifest = _run_manifest(
                run_id=run_id, request=input_smiles, request_hash=request,
                query_id=query_id, case_id=case_id, fold_id=fold_id,
                snapshot_id=capability_status.snapshot_id,
                snapshot_hash=capability_status.snapshot_hash,
                config={"mode": mode, "seed": str(seed)}, seed=seed,
            )
            return KernelResult(
                run_id=run_id, status=KernelStatus.blocked, query_id=query_id,
                case_id=case_id, fold_id=fold_id,
                snapshot_id=capability_status.snapshot_id,
                snapshot_hash=capability_status.snapshot_hash,
                manifest=manifest, normalized_query=query,
                capability_status=capability_status, candidates=[],
                trace=trace, failures=missing, evidence_kind=EvidenceKind.blocked,
            )

    # -- Baseline evidence load (retrieve distinct donors) ------------------
    if train_view is None:
        # R6-C: the default fixture path ALWAYS freezes a fixture authority
        # (synthetic_fixture semantics) so the machinery train view never
        # exists without an upstream authority handle.
        train_view = build_train_view(load_fixture_reactions())

    # R6-C: the train view MUST carry a frozen authority manifest — a
    # manually-constructed train view without an upstream authority handle
    # is fail-closed BEFORE any donor/reaction processing.
    if train_view.authority_manifest is None:
        return _system_failed_result(
            run_id, query_id, case_id, fold_id, capability_status, input_smiles,
            request, stages, system_failures + [KernelFailure(
                failure_code="MISSING_AUTHORITY", category="system",
                reason=(
                    "train view carries no frozen authority manifest; "
                    "production processing requires an upstream P1/P2 "
                    "authority"
                ),
                component="load",
            )], mode,
        )

    # R7-B: real mode requires a ProductionAuthorityHandle — the ONLY type
    # accepted as a production (P1/P2) authority.  A fixture manifest (even
    # one whose caller recomputed a self-hash) is never a production root;
    # while the real P1/P2 root is unavailable, the kernel returns
    # PRODUCTION_AUTHORITY_UNAVAILABLE (typed BLOCKED) instead of
    # manufacturing a production root.
    if mode == "real":
        from reaction_agent.p3.fixtures import ProductionAuthorityHandle
        if not isinstance(train_view.authority_manifest, ProductionAuthorityHandle):
            return _system_failed_result(
                run_id, query_id, case_id, fold_id, capability_status, input_smiles,
                request, stages, system_failures + [KernelFailure(
                    failure_code="PRODUCTION_AUTHORITY_UNAVAILABLE", category="system",
                    reason=(
                        "real mode requires a ProductionAuthorityHandle "
                        "created by the internal P1/P2 authority adapter; a "
                        "fixture manifest is never a production authority"
                    ),
                    component="load",
                )], mode,
            )

    # Fold authority: the caller-supplied fold must match the frozen train
    # view fold.  The train view is the ONLY fold authority (R2-B).
    if fold_id and fold_id != train_view.fold_id:
        raise FoldIsolationError(
            f"requested fold {fold_id!r} != train view fold {train_view.fold_id!r}"
        )

    retrieval = retrieve_donors(query, train_view, retrieval_config)
    stages.append(StageTraceEntry(
        stage=KernelStage.BASELINE_EVIDENCE_LOADED,
        output_ref=retrieval.stop_reason,
        evidence_ids=[d.donor_id for d in retrieval.donors],
        metrics={"distinct_donors": len(retrieval.donors),
                 "dedup_skipped": retrieval.dedup_skipped,
                 "excluded_quarantine": retrieval.excluded_quarantine},
    ))

    if not retrieval.donors:
        manifest = _run_manifest(
            run_id=run_id, request=input_smiles, request_hash=request,
            query_id=query_id, case_id=case_id, fold_id=fold_id,
            snapshot_id=train_view.snapshot_id, snapshot_hash=train_view.snapshot_hash,
            config={"mode": mode, "seed": str(seed)}, seed=seed,
        )
        trace = CandidateTrace(
            run_id=run_id, query_id=query_id, case_id=case_id, fold_id=fold_id,
            snapshot_id=train_view.snapshot_id, snapshot_hash=train_view.snapshot_hash,
            stages=stages, evidence_kind=evidence_kind,
        )
        return KernelResult(
            run_id=run_id, status=KernelStatus.completed, query_id=query_id,
            case_id=case_id, fold_id=fold_id,
            snapshot_id=train_view.snapshot_id, snapshot_hash=train_view.snapshot_hash,
            manifest=manifest, normalized_query=query,
            capability_status=capability_status, candidates=[], trace=trace,
            failures=[_scientific_failure(
                "NO_IN_DOMAIN_DONOR", retrieval.stop_reason, "retrieve")],
            evidence_kind=evidence_kind,
        )

    # -- Per-donor x per-reaction: load, transform, sites, generate, validate
    store = CandidateStore(
        run_id=run_id, case_id=case_id, query_id=query_id, fold_id=fold_id,
        snapshot_id=train_view.snapshot_id, snapshot_hash=train_view.snapshot_hash,
        query=query, evidence_kind=evidence_kind,
    )
    donor_ids: list[str] = []
    reaction_ids_processed: list[str] = []
    transformation_ids: list[str] = []
    site_ids: list[str] = []
    generation_ids: list[str] = []
    source_ledger_ids: list[str] = []
    all_sites_found = False
    eligible_site_found = False
    reaction_system_failures: list[KernelFailure] = []

    def _isolate_reaction_failure(
        *, reaction_id: str, component: str, failure_code: str, detail: str,
    ) -> None:
        """R3-D: record one bad reaction as a typed, JSON-serializable stage
        diagnostic + system failure.  ``str(exc)`` only — NEVER an Exception
        object.  The run continues with the remaining donor reactions."""
        stages.append(StageTraceEntry(
            stage=KernelStage.HYPOTHESES_COMPILED,
            input_ref=reaction_id,
            component=component,
            failure_code=failure_code,
            detail=detail,
        ))
        reaction_system_failures.append(KernelFailure(
            failure_code=failure_code,
            category="system",
            reason=f"donor reaction {reaction_id} could not be processed",
            component=component,
            detail=detail,
        ))

    for donor in retrieval.donors[:max_donors]:
        if donor.donor_id not in donor_ids:
            donor_ids.append(donor.donor_id)
        for ref in donor.eligible_reaction_refs:
            reaction_ids_processed.append(ref.reaction_id)
            try:
                donor_evidence = load_reaction_evidence(
                    train_view, donor.donor_id, ref,
                    query_id=query_id, case_id=case_id, run_id=run_id,
                    evidence_kind=evidence_kind,
                )
            except (IncompleteReactionError, FoldIsolationError) as exc:
                _isolate_reaction_failure(
                    reaction_id=ref.reaction_id,
                    component="load",
                    failure_code=getattr(exc, "failure_code", "INCOMPLETE_REACTION"),
                    detail=str(exc),
                )
                continue
            except Exception as exc:  # noqa: BLE001 - R3-D isolation, never a crash
                _isolate_reaction_failure(
                    reaction_id=ref.reaction_id,
                    component="load",
                    failure_code="REACTION_LOAD_ERROR",
                    detail=f"{type(exc).__name__}: {exc}",
                )
                continue

            try:
                transform = extract_transform(
                    donor_evidence, lineage_id=ref.lineage_id,
                    query_id=query_id, case_id=case_id, run_id=run_id,
                )
            except TransformExtractionError as exc:
                _isolate_reaction_failure(
                    reaction_id=ref.reaction_id,
                    component="transform",
                    failure_code=getattr(
                        exc, "failure_code", "TRANSFORM_EXTRACTION_FAILED"
                    ),
                    detail=str(exc),
                )
                continue
            except Exception as exc:  # noqa: BLE001 - R3-D isolation, never a crash
                _isolate_reaction_failure(
                    reaction_id=ref.reaction_id,
                    component="transform",
                    failure_code="TRANSFORM_EXTRACTION_ERROR",
                    detail=f"{type(exc).__name__}: {exc}",
                )
                continue

            transformation_ids.append(transform.transformation_id)
            source_ledger_ids.append(donor_evidence.context.source_ledger.ledger_id)
            stages.append(StageTraceEntry(
                stage=KernelStage.HYPOTHESES_COMPILED,
                output_ref=transform.transformation_id,
                evidence_ids=[
                    donor.donor_id, ref.reaction_id, transform.transformation_id,
                ],
            ))

            try:
                sites = enumerate_sites(transform, query, query_id=query_id, case_id=case_id)
                if sites:
                    all_sites_found = True
                stages.append(StageTraceEntry(
                    stage=KernelStage.SITES_ENUMERATED,
                    evidence_ids=[s.site_id for s in sites],
                    metrics={"sites": len(sites)},
                ))
                for site in sites:
                    site_ids.append(site.site_id)
                    if site.eligibility.value != "eligible":
                        continue
                    eligible_site_found = True
                    report = generate_product(
                        transform, site, query, query_id=query_id, case_id=case_id
                    )
                    generation_ids.append(report.generation_id)
                    if report.failure_code:
                        continue
                    candidate_id = stable_id("cand", {
                        "identity": _product_identity(
                            report.canonical_product, query.normalization_policy
                        ),
                        "version": "p3-1",
                    })
                    validation, cal = validate_candidate(
                        donor_evidence, transform, site, report, query,
                        candidate_id=candidate_id,
                        source_ledger_id=donor_evidence.context.source_ledger.ledger_id,
                        case_id=case_id,
                    )
                    if validation.failure_code:
                        continue
                    store.add(
                        donor_id=donor.donor_id,
                        reaction_id=ref.reaction_id,
                        lineage_id=ref.lineage_id,
                        report=report, transform=transform, site=site,
                        validation=validation, candidate_analogy_ledger=cal,
                        source_ledger_id=donor_evidence.context.source_ledger.ledger_id,
                    )
            except Exception as exc:  # noqa: BLE001 - R3-D isolation, never a crash
                _isolate_reaction_failure(
                    reaction_id=ref.reaction_id,
                    component="kernel",
                    failure_code="REACTION_PROCESSING_ERROR",
                    detail=f"{type(exc).__name__}: {exc}",
                )
                continue

    candidates: list[StrictCandidate] = store.finalize()
    stages.append(StageTraceEntry(
        stage=KernelStage.CANDIDATES_VALIDATED,
        evidence_ids=[c.candidate_id for c in candidates],
        metrics={"candidates": len(candidates),
                 "eligible_sites": int(eligible_site_found),
                 "sites_found": int(all_sites_found)},
    ))

    manifest = _run_manifest(
        run_id=run_id, request=input_smiles, request_hash=request,
        query_id=query_id, case_id=case_id, fold_id=fold_id,
        snapshot_id=train_view.snapshot_id, snapshot_hash=train_view.snapshot_hash,
        config={"mode": mode, "seed": str(seed), "max_donors": str(max_donors)},
        seed=seed,
    )
    trace = CandidateTrace(
        run_id=run_id, query_id=query_id, case_id=case_id, fold_id=fold_id,
        snapshot_id=train_view.snapshot_id, snapshot_hash=train_view.snapshot_hash,
        stages=stages,
        donor_ids=donor_ids, transformation_ids=transformation_ids,
        site_ids=site_ids, generation_ids=generation_ids,
        candidate_ids=[c.candidate_id for c in candidates],
        source_ledger_ids=source_ledger_ids, evidence_kind=evidence_kind,
    )

    failures: list[KernelFailure] = []
    # R3-D: isolated per-reaction failures are SYSTEM / data-integrity
    # failures.  They dominate the scientific-stop bookkeeping (a system
    # failure is never relabeled as a scientific abstention), and they make
    # the run status ``failed`` while candidates produced by OTHER donor
    # reactions are preserved.
    if reaction_system_failures:
        failures = list(reaction_system_failures)
        status = KernelStatus.failed
    else:
        status = KernelStatus.completed
        if not candidates and not all_sites_found:
            failures.append(_scientific_failure(
                "NO_COMPATIBLE_SITE",
                "no transform-compatible site enumerated on X",
                "sites",
            ))
        elif not candidates and all_sites_found:
            failures.append(_scientific_failure(
                "ALL_CANDIDATES_CHEMICALLY_INVALID",
                "sites were found but no candidate passed strict validation",
                "validation",
            ))

    return KernelResult(
        run_id=run_id, status=status, query_id=query_id,
        case_id=case_id, fold_id=fold_id,
        snapshot_id=train_view.snapshot_id, snapshot_hash=train_view.snapshot_hash,
        manifest=manifest, normalized_query=query,
        capability_status=capability_status, candidates=candidates,
        trace=trace, failures=failures, evidence_kind=evidence_kind,
    )


def _mode_kind(mode: str) -> EvidenceKind:
    if mode == "real":
        return EvidenceKind.real
    return EvidenceKind.synthetic_fixture


def _placeholder_query(
    input_smiles: str, query_id: str, evidence_kind: EvidenceKind,
    *, run_id: str = "", case_id: str = "", fold_id: str = "",
) -> NormalizedQuery:
    # canonical_smiles must be a non-empty string; for an invalid/unparseable
    # input we record the raw input (never a repaired/fabricated SMILES).
    # fragment_count=1 denotes the single (unparseable) input fragment.
    canonical = input_smiles if input_smiles.strip() else "INVALID_INPUT"
    return NormalizedQuery(
        query_id=query_id,
        run_id=run_id or f"diag_run_{query_id}",
        case_id=case_id or f"diag_case_{query_id}",
        fold_id=fold_id or "diag_fold",
        input_smiles=input_smiles,
        canonical_smiles=canonical,
        identity_hash=canonical_hash({"invalid": input_smiles}),
        heavy_atom_count=0, formal_charge=0, fragment_count=1,
        normalization_policy=NormalizationPolicy(version="p3-1"),
        evidence_kind=evidence_kind,
    )


def _system_failed_result(
    run_id, query_id, case_id, fold_id, capability_status, input_smiles,
    request, stages, system_failures, mode,
) -> KernelResult:
    manifest = _run_manifest(
        run_id=run_id, request=input_smiles, request_hash=request,
        query_id=query_id, case_id=case_id, fold_id=fold_id,
        snapshot_id=capability_status.snapshot_id,
        snapshot_hash=capability_status.snapshot_hash,
        config={"mode": mode}, seed=0,
    )
    trace = CandidateTrace(
        run_id=run_id, query_id=query_id, case_id=case_id, fold_id=fold_id,
        snapshot_id=capability_status.snapshot_id,
        snapshot_hash=capability_status.snapshot_hash,
        stages=stages, evidence_kind=EvidenceKind.blocked,
    )
    return KernelResult(
        run_id=run_id, status=KernelStatus.failed, query_id=query_id,
        case_id=case_id, fold_id=fold_id,
        snapshot_id=capability_status.snapshot_id,
        snapshot_hash=capability_status.snapshot_hash,
        manifest=manifest,
        normalized_query=_placeholder_query(input_smiles, query_id, EvidenceKind.blocked,
                                             run_id=run_id, case_id=case_id, fold_id=fold_id),
        capability_status=capability_status, candidates=[], trace=trace,
        failures=system_failures, evidence_kind=EvidenceKind.blocked,
    )
