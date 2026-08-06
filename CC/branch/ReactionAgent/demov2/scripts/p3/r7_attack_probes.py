#!/usr/bin/env python
"""R7-A / R7-B attack probes (RED on the R6 code, GREEN after R7 fixes).

Each probe reproduces the EXACT attack the ChatGPT Round 6 audit documented:

R7-A (mutation execution authority): rewrite BOTH the raw marker-delimited
receipt AND the typed fields AND the artifact hash AND the stdout hash of a
real mutated receipt, keeping the whole mutation internally consistent.  The
R6 verifier only checked internal consistency (raw receipt vs typed fields),
so a fully-synchronized rewrite was NOT detected.  After R7-A the submitted
mutation must EXACTLY match the mutation the authority ACTUALLY executed ->
EXECUTED_MUTATION_MISMATCH, verified=False.

R7-B (fixture/production authority type isolation): relabel a caller-built
fixture root as ``production`` (kind + provenance + public self-hash).  The
R6 loader only checked ``kind == "production"``, so the relabeled root was
accepted.  After R7-B the fixture kind is immutable (relabeling raises) and
the real loader requires a ProductionAuthorityHandle type ->
FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY / PRODUCTION_AUTHORITY_UNAVAILABLE.

RED expectation (R6 code): the probe returns a verdict that is NOT FAIL
(verified=True PASS / BLOCKED with no machinery failures), or the relabeled
root is accepted.
GREEN expectation (R7 code): every probe returns FAIL with a typed machinery
failure, or the relabeled root is rejected.
"""
from __future__ import annotations

import hashlib
import json
import sys

sys.path.insert(0, ".")

from reaction_agent.p3.gate import evaluate_gate_artifact, run_p3_gate  # noqa: E402
from reaction_agent.p3.mutation_harness import (  # noqa: E402
    RECEIPT_BEGIN,
    RECEIPT_END,
    parse_strict_receipt,
)


def _sha256(text: str) -> str:
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _artifact():
    report = run_p3_gate(run_mutations=True)
    return report.model_dump(mode="json")


def _rebuild_raw_receipt(payload: dict) -> str:
    return (
        RECEIPT_BEGIN + "\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        + "\n" + RECEIPT_END + "\n"
    )


def probe_simultaneous_raw_and_typed_receipt_rewrite():
    """R7-A: the audit's eight-step repro — rewrite BOTH the raw receipt and
    the typed fields, recompute artifact hash AND stdout hash, keep every
    other contract field legal."""
    artifact = _artifact()
    m = artifact["mutations"][0]
    side = m["mutated"]
    receipt = parse_strict_receipt(side["raw_output"])
    if receipt is None:
        return {"probe": "simultaneous_raw_and_typed_receipt_rewrite",
                "error": "real receipt not parseable"}
    forged_artifact = {**receipt["artifact"], "_forged": True}
    forged_json = json.dumps(
        forged_artifact, ensure_ascii=False, sort_keys=True, default=str,
    )
    receipt = {**receipt, "artifact": forged_artifact,
               "artifact_hash": _sha256(forged_json)}
    side["artifact"] = forged_artifact
    side["artifact_hash"] = _sha256(forged_json)
    side["raw_output"] = _rebuild_raw_receipt(receipt)
    side["stdout_stderr_hash"] = _sha256(side["raw_output"])
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "simultaneous_raw_and_typed_receipt_rewrite",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_missing_mutation():
    artifact = _artifact()
    artifact["mutations"] = artifact["mutations"][1:]
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "missing_mutation",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_extra_mutation():
    artifact = _artifact()
    artifact["mutations"].append(dict(artifact["mutations"][0]))
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "extra_mutation",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_reordered_mutations():
    artifact = _artifact()
    muts = artifact["mutations"]
    muts[0], muts[1] = muts[1], muts[0]
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "reordered_mutations",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_adjudication_rewrite():
    artifact = _artifact()
    m = artifact["mutations"][0]
    m["caught"] = not m["caught"]
    m["valid"] = not m["valid"]
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "adjudication_rewrite",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_fixture_root_relabelled_as_production():
    """R7-B: the audit's repro — relabel a caller-built fixture root as
    production (kind + provenance + public self-hash) and try to load real
    evidence with it."""
    from dataclasses import replace

    from reaction_agent.p3.fixtures import (
        DonorEntry,
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
    from reaction_agent.p3.load import IncompleteReactionError, load_reaction_evidence
    from reaction_agent.p3.schemas import EvidenceKind

    fx = load_fixture_reactions()["rxn_hydrolysis"]
    root = build_fixture_authority_manifest({fx.reaction_id: fx})
    try:
        relabelled = replace(
            root, kind="production", provenance="caller-claims-p1-production",
        )
        relabelled = replace(
            relabelled, manifest_hash=authority_manifest_hash(relabelled),
        )
        relabel_succeeded = True
    except ValueError:
        relabel_succeeded = False
        relabelled = root
    if not relabel_succeeded:
        return {
            "probe": "fixture_root_relabelled_as_production",
            "accepted": False,
            "failure_code": "FIXTURE_KIND_IMMUTABLE",
            "detail": "relabeling a fixture manifest kind is rejected by the type",
        }
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
        donor_id="donor_r7", molecule_id=donor_p.molecule_id,
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
        authority_manifest=relabelled,
    )
    try:
        dev = load_reaction_evidence(
            tv, donor.donor_id, ref, evidence_kind=EvidenceKind.real,
        )
        return {
            "probe": "fixture_root_relabelled_as_production",
            "accepted": True,
            "reaction_id": dev.context.reaction_id,
            "root_kind": relabelled.kind,
            "root_provenance": relabelled.provenance,
        }
    except IncompleteReactionError as exc:
        return {
            "probe": "fixture_root_relabelled_as_production",
            "accepted": False,
            "failure_code": exc.failure_code,
        }


def probe_fixture_root_passed_to_real_loader():
    """R7-B: a fixture root (unchanged) passed to the real loader."""
    from reaction_agent.p3.fixtures import (
        DonorEntry,
        ReactionRef,
        TrainView,
        build_fixture_authority_manifest,
        canonical_reaction_hash,
        load_fixture_reactions,
        recompute_train_view_hash,
        select_primary_lineage,
        strip_atom_maps,
    )
    from reaction_agent.p3.load import IncompleteReactionError, load_reaction_evidence
    from reaction_agent.p3.schemas import EvidenceKind

    fx = load_fixture_reactions()["rxn_hydrolysis"]
    root = build_fixture_authority_manifest({fx.reaction_id: fx})
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
        donor_id="donor_r7", molecule_id=donor_p.molecule_id,
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
        authority_manifest=root,
    )
    try:
        dev = load_reaction_evidence(
            tv, donor.donor_id, ref, evidence_kind=EvidenceKind.real,
        )
        return {
            "probe": "fixture_root_passed_to_real_loader",
            "accepted": True,
            "reaction_id": dev.context.reaction_id,
        }
    except IncompleteReactionError as exc:
        return {
            "probe": "fixture_root_passed_to_real_loader",
            "accepted": False,
            "failure_code": exc.failure_code,
        }


def probe_public_production_handle_construction():
    """R7-B: a public caller cannot construct a ProductionAuthorityHandle."""
    from reaction_agent.p3.fixtures import ProductionAuthorityHandle

    try:
        ProductionAuthorityHandle(
            snapshot_id="s", snapshot_hash="h", reaction_hashes={},
        )
        return {
            "probe": "public_production_handle_construction",
            "accepted": True,
        }
    except TypeError as exc:
        return {
            "probe": "public_production_handle_construction",
            "accepted": False,
            "failure_code": "PRODUCTION_HANDLE_NOT_CONSTRUCTIBLE",
            "detail": str(exc)[:120],
        }


def probe_real_gate_artifact():
    """Baseline: the real gate artifact must still pass machinery verification."""
    artifact = _artifact()
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "real_gate_artifact",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


PROBES = [
    probe_simultaneous_raw_and_typed_receipt_rewrite,
    probe_missing_mutation,
    probe_extra_mutation,
    probe_reordered_mutations,
    probe_adjudication_rewrite,
    probe_fixture_root_relabelled_as_production,
    probe_fixture_root_passed_to_real_loader,
    probe_public_production_handle_construction,
    probe_real_gate_artifact,
]


def main() -> int:
    results = []
    for probe in PROBES:
        try:
            results.append(probe())
        except Exception as exc:  # noqa: BLE001 - probe must not crash the run
            results.append({
                "probe": probe.__name__,
                "error": f"{type(exc).__name__}: {exc}",
            })
    payload = {"probes": results}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())