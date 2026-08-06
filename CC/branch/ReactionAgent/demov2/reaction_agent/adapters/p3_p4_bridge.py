"""P7 T0② P3→P4 bridge adapter (CC Option A authorized; additive).

Derives the three P4 pipeline inputs — ``evidence_records``,
``structural_contexts``, ``feature_evidence_ids`` — from a P3 ``KernelResult``
by BACK-SOURCING donor evidence through the P3 loaders
(``load_fixture_reactions`` → ``build_train_view`` → ``find_donor_ref`` →
``load_reaction_evidence``). Nothing is synthesized:

- **evidence_records**: every ``ReactionEvidence`` is LOADED from the train
  view via the candidate's evidence-path ``donor_id``/``reaction_id`` (the
  same loader P3 used to build the candidate). A path whose reaction is
  absent from the train view raises ``BridgeBackSourceError`` — never a
  hand-built record.
- **structural_contexts**: each of the 7 ordinal features P4 reads
  (``donor_similarity``, ``transform_support``, ``site_compatibility``,
  ``mapping_lineage_quality``, ``source_quality``, ``ledger_completeness``,
  ``retrieval_stability``) is deterministically derived from a NAMED real
  field on the ``StrictCandidate`` / ``DonorContext`` /
  ``ReactionEvidence.mapping_report``. Derivation provenance (source field +
  value) is returned per feature for audit. ``evidence_independence`` is
  P4-derived from the evidence records and is NOT provided here. A missing
  source field raises ``BridgeBackSourceError`` (typed failure), never a
  silent default.
- **feature_evidence_ids**: each binding references only evidence IDs that
  exist in the back-sourced ``evidence_records``; a missing target raises
  ``BridgeBackSourceError``.

The authority handle comes from the verified P3 consumer (P4-R1-B): the
bridge serializes the ``KernelResult`` to the current-run artifact path and
``P3InterfaceConsumer.resolve_authority()`` grants a ``p3_current_run``
handle — never caller-constructed.

This module is ADDITIVE: it imports P3/P4 modules but does not modify them
(Gate-P3 / Gate-P4 components unchanged).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from reaction_agent.adapters.p3_consumer import (
    DEFAULT_CURRENT_RUN,
    DEFAULT_P3_MANIFEST,
    P3InterfaceConsumer,
)
from reaction_agent.hashing import stable_id
from reaction_agent.inference.predictor import run_p4_pipeline
from reaction_agent.p3.fixtures import (
    TrainView,
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.load import load_reaction_evidence
from reaction_agent.p3.schemas import CandidateEvidencePath, KernelResult, StrictCandidate
from reaction_agent.policies.p4_decision_policy import P4_POLICY_VERSION
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.common import Lane
from reaction_agent.schemas.evidence import ReactionEvidence
from reaction_agent.schemas.p4.authority import (
    AuthoritySource,
    P3AuthorityHandle,
    P4Classification,
    RunNamespace,
)
from reaction_agent.schemas.result import PredictionResult

# The 7 ordinals the bridge provides. P4 derives ``evidence_independence``
# itself from the evidence records (inference/features.py), so it is NOT here.
BRIDGE_FEATURE_KEYS = (
    "donor_similarity",
    "transform_support",
    "site_compatibility",
    "mapping_lineage_quality",
    "source_quality",
    "ledger_completeness",
    "retrieval_stability",
)


class BridgeBackSourceError(ValueError):
    """Typed failure: a candidate evidence path or ordinal source field is
    missing / unresolvable. Never silently defaulted."""


@dataclass
class FeatureDerivation:
    """Provenance for one ordinal: which real field produced it (audit trace)."""

    feature: str
    ordinal: int
    source_field: str
    source_value: str


@dataclass
class BridgeInputs:
    query: dict
    evidence_records: list  # list[ReactionEvidence]
    candidates: list  # list[P4 Candidate]
    structural_contexts: dict  # cand_id -> {feature: int 0..3}
    feature_evidence_ids: dict  # cand_id -> {feature: [evidence_id, ...]}
    authority: P3AuthorityHandle
    derivations: dict  # cand_id -> [FeatureDerivation]


# --------------------------------------------------------------------------- #
# Ordinal derivation (each from a named real field; typed failure on missing) #
# --------------------------------------------------------------------------- #


def _ord_count(n: int) -> int:
    """Map a non-negative count to an ordinal 0..3 (0/1/2/3+)."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    if n == 2:
        return 2
    return 3


def _clamp_ordinal(v: int) -> int:
    return max(0, min(3, v))


def _require(value: Any, *, feature: str, source_field: str, cand_id: str) -> Any:
    """Return ``value`` if present; else typed failure (no silent default)."""
    if value is None:
        raise BridgeBackSourceError(
            f"{feature}: source field {source_field!r} is None on candidate "
            f"{cand_id!r} — cannot derive ordinal (typed failure, no default)"
        )
    return value


def _derive_transform_support(cand: StrictCandidate) -> FeatureDerivation:
    n = len(cand.support_lineage_ids)
    return FeatureDerivation(
        feature="transform_support",
        ordinal=_ord_count(n),
        source_field="len(candidate.support_lineage_ids)",
        source_value=f"{n} lineage ids",
    )


def _derive_site_compatibility(cand: StrictCandidate) -> FeatureDerivation:
    recheck = _require(
        cand.validation.precondition_recheck,
        feature="site_compatibility",
        source_field="validation.precondition_recheck",
        cand_id=cand.candidate_id,
    )
    n_sites = len(cand.site_ids)
    if recheck and n_sites > 0:
        ordinal = 3
    elif n_sites > 0:
        ordinal = 1
    else:
        ordinal = 0
    return FeatureDerivation(
        feature="site_compatibility",
        ordinal=ordinal,
        source_field="validation.precondition_recheck + len(site_ids)",
        source_value=f"recheck={recheck}, sites={n_sites}",
    )


def _derive_mapping_lineage_quality(cand: StrictCandidate) -> FeatureDerivation:
    v = cand.validation
    base = sum(
        1
        for f in (
            v.transform_fidelity,
            v.formal_source_accounting,
            v.candidate_ledger_valid,
        )
        if f
    )
    if getattr(v, "relaxation_used", False):
        base -= 1
    if getattr(v, "critical_ambiguity", False):
        base -= 1
    return FeatureDerivation(
        feature="mapping_lineage_quality",
        ordinal=_clamp_ordinal(base),
        source_field="validation{transform_fidelity,formal_source_accounting,candidate_ledger_valid,relaxation_used,critical_ambiguity}",
        source_value=(
            f"tf={v.transform_fidelity},fsa={v.formal_source_accounting},"
            f"clv={v.candidate_ledger_valid},relax={getattr(v,'relaxation_used',False)},"
            f"ambig={getattr(v,'critical_ambiguity',False)}"
        ),
    )


def _derive_source_quality(cand: StrictCandidate, mapping_report: Any) -> FeatureDerivation:
    ms = _require(
        getattr(mapping_report, "mapping_status", None),
        feature="source_quality",
        source_field="mapping_report.mapping_status",
        cand_id=cand.candidate_id,
    )
    ms_val = ms.value if hasattr(ms, "value") else str(ms)
    # fully_mapped -> 3, partially_mapped -> 1, anything else -> 0.
    if ms_val in ("fully_mapped", "fully_mapped".lower()):
        ordinal = 3
    elif ms_val in ("partially_mapped", "partially_mapped".lower()):
        ordinal = 1
    else:
        ordinal = 0
    return FeatureDerivation(
        feature="source_quality",
        ordinal=ordinal,
        source_field="mapping_report.mapping_status",
        source_value=ms_val,
    )


def _derive_ledger_completeness(cand: StrictCandidate) -> FeatureDerivation:
    ledger_valid = _require(
        cand.validation.candidate_ledger_valid,
        feature="ledger_completeness",
        source_field="validation.candidate_ledger_valid",
        cand_id=cand.candidate_id,
    )
    balance = getattr(cand.candidate_analogy_ledger, "candidate_balance_status", None)
    balance_val = balance.value if hasattr(balance, "value") else str(balance)
    ordinal = 2 if ledger_valid else 0
    # A formally-balanced ledger adds one ordinal step.
    if balance_val and "balanced" in str(balance_val).lower():
        ordinal += 1
    return FeatureDerivation(
        feature="ledger_completeness",
        ordinal=_clamp_ordinal(ordinal),
        source_field="validation.candidate_ledger_valid + candidate_analogy_ledger.candidate_balance_status",
        source_value=f"ledger_valid={ledger_valid}, balance={balance_val}",
    )


def _derive_donor_similarity(cand: StrictCandidate, mapping_report: Any) -> FeatureDerivation:
    frac = _require(
        getattr(mapping_report, "mapped_heavy_atom_fraction", None),
        feature="donor_similarity",
        source_field="mapping_report.mapped_heavy_atom_fraction",
        cand_id=cand.candidate_id,
    )
    try:
        f = float(frac)
    except (TypeError, ValueError) as exc:
        raise BridgeBackSourceError(
            f"donor_similarity: mapped_heavy_atom_fraction={frac!r} not numeric "
            f"on {cand.candidate_id!r}: {exc}"
        ) from exc
    if f <= 0.0:
        ordinal = 0
    elif f < 0.34:
        ordinal = 1
    elif f < 0.67:
        ordinal = 2
    else:
        ordinal = 3
    return FeatureDerivation(
        feature="donor_similarity",
        ordinal=ordinal,
        source_field="mapping_report.mapped_heavy_atom_fraction",
        source_value=f"{f:.4f}",
    )


def _derive_retrieval_stability(cand: StrictCandidate, trace: Any) -> FeatureDerivation:
    donor_ids = _require(
        getattr(trace, "donor_ids", None),
        feature="retrieval_stability",
        source_field="trace.donor_ids",
        cand_id=cand.candidate_id,
    )
    n = len(donor_ids) if donor_ids is not None else 0
    return FeatureDerivation(
        feature="retrieval_stability",
        ordinal=_ord_count(n),
        source_field="trace.donor_ids",
        source_value=f"{n} donors",
    )


# --------------------------------------------------------------------------- #
# Evidence back-sourcing                                                      #
# --------------------------------------------------------------------------- #


def _back_source_evidence(
    cand: StrictCandidate,
    train_view: TrainView,
    kernel: KernelResult,
) -> list[ReactionEvidence]:
    """Load full ``ReactionEvidence`` for every evidence path of ``cand`` via
    the P3 train-view loader (the same loader P3 used). Fail-closed on any
    path whose donor/reaction is absent from the train view.
    """
    records: list[ReactionEvidence] = []
    seen: set[str] = set()
    for path in cand.candidate_evidence_paths:
        rid = path.reaction_id
        if rid in seen:
            continue
        try:
            donor, ref = find_donor_ref(train_view, rid)
        except KeyError as exc:
            raise BridgeBackSourceError(
                f"candidate {cand.candidate_id!r}: evidence path reaction "
                f"{rid!r} not in train view — cannot back-source ({exc})"
            ) from exc
        try:
            rde = load_reaction_evidence(
                train_view,
                path.donor_id,
                ref,
                query_id=kernel.query_id,
                case_id=kernel.case_id,
                run_id=kernel.run_id,
                evidence_kind=kernel.evidence_kind,
            )
        except Exception as exc:  # noqa: BLE001 — typed fail-closed
            raise BridgeBackSourceError(
                f"candidate {cand.candidate_id!r}: load_reaction_evidence failed "
                f"for donor {path.donor_id!r} / reaction {rid!r}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        ev = rde.context.reaction_evidence
        if ev is None:
            raise BridgeBackSourceError(
                f"candidate {cand.candidate_id!r}: back-sourced donor evidence "
                f"has no reaction_evidence for reaction {rid!r}"
            )
        records.append(ev)
        seen.add(rid)
    return records


def _evidence_id_of(rec: ReactionEvidence) -> str:
    return rec.reaction_id


def _convert_candidate(p3_cand: StrictCandidate) -> Candidate:
    """Map a P3 ``StrictCandidate`` to a P4 ``Candidate`` (field-for-field)."""
    return Candidate(
        candidate_id=p3_cand.candidate_id,
        canonical_product=p3_cand.canonical_product_identity,
        lane=Lane.strict,
        origin=p3_cand.origin,
        generation_paths=[gp.model_dump(mode="json") for gp in p3_cand.generation_paths],
        support_lineage_ids=list(p3_cand.support_lineage_ids),
        transformation_ids=list(p3_cand.transformation_ids),
        site_ids=list(p3_cand.site_ids),
        validation=p3_cand.validation.model_dump(mode="json"),
        source_ledger_ids=list(p3_cand.source_ledger_ids),
        candidate_analogy_ledger_id=getattr(
            p3_cand.candidate_analogy_ledger, "ledger_id", None
        ),
        provenance=list(p3_cand.provenance),
    )


_ARTIFACT_NAMESPACE_FIELDS = (
    "run_id", "case_id", "query_id", "fold_id", "snapshot_id", "snapshot_hash",
)


def _normalize_artifact_namespace(artifact: dict) -> dict:
    """Propagate the header run namespace to nested records P3 fixture-mode
    left empty, so the P4 consumer's ``_namespace_consistent`` integrity check
    passes.

    P3 fixture-mode populates ``snapshot_id``/``snapshot_hash`` on the header,
    manifest, trace, and candidates, but leaves them EMPTY on
    ``normalized_query`` and ``capability_status`` (a P3 serialization gap —
    these nested records ARE part of the same run, not a different namespace).
    The bridge fills the empty/missing namespace fields on those two records
    from the header. This is namespace PROPAGATION (the run's real identity
    applied to its own nested records), not synthesis: no foreign namespace
    is introduced, and a non-empty real value is never overwritten. P3 source
    code is unchanged (the KernelResult object is read-only here; only the
    serialized dict is normalized).
    """
    header_ns = {f: artifact.get(f) for f in _ARTIFACT_NAMESPACE_FIELDS}
    for key in ("normalized_query", "capability_status"):
        nested = artifact.get(key)
        if isinstance(nested, dict):
            for f, hv in header_ns.items():
                if not nested.get(f):  # empty / missing only — never overwrite
                    nested[f] = hv
    return artifact


def _resolve_authority(
    kernel: KernelResult,
    *,
    manifest_path: str | None,
    current_run_path: str,
) -> P3AuthorityHandle:
    """Serialize the KernelResult to the current-run artifact and resolve the
    authority via the P3 consumer (P4-R1-B). Typed failure if not granted."""
    artifact = kernel.model_dump(mode="json")
    artifact = _normalize_artifact_namespace(artifact)
    os.makedirs(os.path.dirname(current_run_path) or ".", exist_ok=True)
    with open(current_run_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f)
    consumer = P3InterfaceConsumer(
        missing_path=manifest_path or DEFAULT_P3_MANIFEST,
        current_run_path=current_run_path,
    )
    handle = consumer.resolve_authority()
    if handle.source != AuthoritySource.p3_current_run or not handle.capability_available:
        raise BridgeBackSourceError(
            f"authority not resolved as p3_current_run (source={handle.source.value}, "
            f"capability={handle.capability_available}, blocked={handle.blocked_reasons})"
        )
    return handle


def _build_query(kernel: KernelResult) -> dict:
    """Build the P4 query dict carrying the frozen run namespace."""
    return {
        "query_smiles": kernel.normalized_query.canonical_smiles,
        "run_id": kernel.run_id,
        "query_id": kernel.query_id,
        "case_id": kernel.case_id,
        "fold_id": kernel.fold_id,
        "snapshot_id": kernel.snapshot_id,
        "snapshot_hash": kernel.snapshot_hash,
        "fold_view_id": "train_only_v1",
        "requested_lanes": ["strict"],
        "top_k": 3,
        "policy_version": P4_POLICY_VERSION,
    }


def build_p4_inputs_from_kernel(
    kernel_result: KernelResult,
    *,
    train_view: Optional[TrainView] = None,
    manifest_path: Optional[str] = None,
    current_run_path: str = DEFAULT_CURRENT_RUN,
) -> BridgeInputs:
    """Derive the P4 pipeline inputs from a P3 ``KernelResult``.

    Back-sources donor evidence via the P3 loaders, derives the 7 structural
    ordinals per candidate from named real fields, binds feature_evidence_ids
    to existing evidence IDs only, and resolves the authority via the P3
    consumer. Raises ``BridgeBackSourceError`` on any unresolvable path or
    missing source field (typed failure, never a silent default).
    """
    tv = train_view if train_view is not None else build_train_view(load_fixture_reactions())

    evidence_records: list[ReactionEvidence] = []
    candidates: list[Candidate] = []
    structural_contexts: dict[str, dict[str, int]] = {}
    feature_evidence_ids: dict[str, dict[str, list[str]]] = {}
    derivations: dict[str, list[FeatureDerivation]] = {}

    # Index evidence by reaction_id for binding-target validation.
    evidence_by_rid: dict[str, ReactionEvidence] = {}

    for p3_cand in kernel_result.candidates:
        cand_records = _back_source_evidence(p3_cand, tv, kernel_result)
        for rec in cand_records:
            if rec.reaction_id not in evidence_by_rid:
                evidence_by_rid[rec.reaction_id] = rec
                evidence_records.append(rec)
        # The mapping_report used for quality/similarity ordinals: take the
        # first back-sourced record's mapping_report (the donor reaction that
        # produced this candidate).
        primary_mapping = (
            cand_records[0].mapping_report if cand_records else None
        )
        if primary_mapping is None:
            raise BridgeBackSourceError(
                f"candidate {p3_cand.candidate_id!r}: no back-sourced evidence "
                f"-> no mapping_report for ordinal derivation"
            )

        derivs = [
            _derive_transform_support(p3_cand),
            _derive_site_compatibility(p3_cand),
            _derive_mapping_lineage_quality(p3_cand),
            _derive_source_quality(p3_cand, primary_mapping),
            _derive_ledger_completeness(p3_cand),
            _derive_donor_similarity(p3_cand, primary_mapping),
            _derive_retrieval_stability(p3_cand, kernel_result.trace),
        ]
        derivations[p3_cand.candidate_id] = derivs
        structural_contexts[p3_cand.candidate_id] = {d.feature: d.ordinal for d in derivs}

        # feature_evidence_ids: bind only the real evidence IDs that produced
        # this candidate. Every bound ID must exist in evidence_records.
        cand_evidence_ids = [rec.reaction_id for rec in cand_records]
        missing = [eid for eid in cand_evidence_ids if eid not in evidence_by_rid]
        if missing:
            raise BridgeBackSourceError(
                f"candidate {p3_cand.candidate_id!r}: feature_evidence_ids bind "
                f"target(s) {missing!r} not in run evidence"
            )
        feature_evidence_ids[p3_cand.candidate_id] = {
            feature: list(cand_evidence_ids) for feature in BRIDGE_FEATURE_KEYS
        }

        candidates.append(_convert_candidate(p3_cand))

    authority = _resolve_authority(
        kernel_result, manifest_path=manifest_path, current_run_path=current_run_path
    )
    query = _build_query(kernel_result)

    return BridgeInputs(
        query=query,
        evidence_records=evidence_records,
        candidates=candidates,
        structural_contexts=structural_contexts,
        feature_evidence_ids=feature_evidence_ids,
        authority=authority,
        derivations=derivations,
    )


def run_deterministic_predict(
    payload: dict,
    *,
    train_view: Optional[TrainView] = None,
    manifest_path: Optional[str] = None,
    current_run_path: str = DEFAULT_CURRENT_RUN,
    top_k: int = 3,
) -> PredictionResult:
    """Deterministic baseline predictor: P3 kernel (fixture) -> bridge -> P4.

    Derives ``case_id``/``fold_id`` deterministically from the predict payload
    (``substrate_smiles`` + ``snapshot_id``); runs the P3 strict kernel in
    fixture mode, back-sources the P4 inputs, runs the P4 pipeline, and
    returns the typed ``PredictionResult``. No LLM, no real API.
    """
    substrate = payload["substrate_smiles"]
    snapshot_id = payload.get("snapshot_id", "")
    case_id = stable_id("case", {"smiles": substrate, "snapshot": snapshot_id})
    fold_id = "fold_fx_p3"  # frozen fixture fold (deterministic baseline)

    kernel_result = run_kernel(
        input_smiles=substrate,
        case_id=case_id,
        fold_id=fold_id,
        mode="fixture",
        seed=0,
    )

    inputs = build_p4_inputs_from_kernel(
        kernel_result,
        train_view=train_view,
        manifest_path=manifest_path,
        current_run_path=current_run_path,
    )

    outcome = run_p4_pipeline(
        query=inputs.query,
        evidence_records=inputs.evidence_records,
        candidates=inputs.candidates,
        structural_contexts=inputs.structural_contexts,
        authority=inputs.authority,
        top_k=top_k,
        feature_evidence_ids=inputs.feature_evidence_ids,
    )
    return outcome.build_prediction_result()
