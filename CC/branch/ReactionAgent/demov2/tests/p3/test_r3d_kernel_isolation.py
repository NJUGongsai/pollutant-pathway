"""R3-D: a bad donor reaction must be ISOLATED by the kernel, never crash it.

Round 2 defect: the reaction-load / transform-extraction exception branches
passed ``detail=exc`` into ``StageTraceEntry`` which has no ``detail`` field —
a malformed reaction therefore crashed the whole run with a Pydantic
``ValidationError`` instead of producing a typed, isolated failure.

These tests run the kernel through its REAL production path (run_kernel on a
train view that contains one or more corrupted reactions) and require:
- no exception escapes run_kernel;
- a declared JSON-serializable typed diagnostic (str(exc), never an
  Exception object) with reaction ID + component + failure code;
- good reactions keep producing candidates next to a bad one;
- all-bad reactions yield a structured result with typed failures;
- deterministic replay;
- JSON-serializable trace.
"""
import json
from dataclasses import replace

from reaction_agent.p3.fixtures import (
    build_train_view,
    load_fixture_reactions,
)
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.schemas import KernelStatus
from reaction_agent.schemas.common import MappingStatus


def _corrupt_donor_smiles(fixture):
    """Corrupt the donor participant's mapped SMILES (unparseable), keeping
    every ID / cross-reference consistent so the loader passes and the
    transform extraction stage is the one that fails."""
    donor_pid = fixture.donor_participant_id
    participants = [
        p.model_copy(update={"canonical_smiles": "NOT_A_SMILES_%%%"})
        if p.participant_id == donor_pid else p
        for p in fixture.participants
    ]
    evidence = fixture.evidence.model_copy(update={"participants": participants})
    return replace(fixture, participants=participants, evidence=evidence)


def _partial_mapping_fixture(fixture):
    """Downgrade the mapping status so the LOADER rejects the reaction."""
    mapping = fixture.mapping_report.model_copy(
        update={"mapping_status": MappingStatus.partially_mapped}
    )
    return replace(fixture, mapping_report=mapping)


def _tv_with(*, corrupted=(), partial=()):
    fixtures = load_fixture_reactions()
    for name in corrupted:
        fixtures[name] = _corrupt_donor_smiles(fixtures[name])
    for name in partial:
        fixtures[name] = _partial_mapping_fixture(fixtures[name])
    return build_train_view(fixtures)


def test_one_good_one_bad_reaction_does_not_crash():
    # rxn_oct is corrupted (transform extraction fails); rxn_oct_dehyd and the
    # other donors stay good and MUST keep being processed.
    tv = _tv_with(corrupted=("rxn_oct",))
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r3d_mix", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv,
    )
    # The good dehydration reaction of the same donor still produces its
    # candidate — the bad reaction was isolated, not fatal.
    identities = {c.canonical_product_identity for c in result.candidates}
    assert "C=CCCCCCC" in identities
    # A typed failure records the isolated bad reaction.
    assert result.failures, "isolated bad reaction must be recorded"
    bad = [f for f in result.failures if f.category == "system"]
    assert bad, "a corrupted reaction is a system/data-integrity failure"
    assert any(f.component for f in bad)
    assert all(f.failure_code for f in bad)
    assert all(f.detail for f in bad)
    # The exception object itself must never be stored (str only).
    assert all(isinstance(f.detail, str) for f in bad)


def test_bad_reaction_trace_entry_is_typed_and_json_serializable():
    tv = _tv_with(corrupted=("rxn_oct",))
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r3d_trace", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv,
    )
    failed_stages = [s for s in result.trace.stages if s.failure_code]
    assert failed_stages, "trace must record the failed reaction stage"
    for entry in failed_stages:
        # reaction ID + component + failure code + str diagnostic
        assert entry.input_ref, "trace entry must name the failing reaction"
        assert entry.detail and isinstance(entry.detail, str)
        assert entry.component
    # Whole trace must be JSON-serializable (no Exception objects anywhere).
    json.dumps(result.trace.model_dump(mode="json"))
    json.dumps(result.model_dump(mode="json"))


def test_all_reactions_bad_returns_structured_typed_failures():
    # Corrupt every donor reaction: the result must be structured (no crash)
    # with typed failures and zero candidates.
    tv = _tv_with(corrupted=("rxn_oct", "rxn_oct_dehyd"))
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r3d_all_bad", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv,
    )
    assert result.status is KernelStatus.failed
    assert result.candidates == []
    assert result.failures
    assert all(f.category == "system" for f in result.failures)
    assert any(f.failure_code == "TRANSFORM_EXTRACTION_FAILED"
               for f in result.failures)


def test_loader_failure_isolated_with_typed_code():
    tv = _tv_with(partial=("rxn_oct",))
    result = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r3d_loader", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv,
    )
    # The partial-map reaction is rejected by the loader and isolated; the
    # remaining good reactions still run.
    identities = {c.canonical_product_identity for c in result.candidates}
    assert "C=CCCCCCC" in identities
    codes = {f.failure_code for f in result.failures}
    assert "PARTIAL_MAP" in codes


def test_deterministic_replay_with_bad_reaction():
    tv = _tv_with(corrupted=("rxn_oct",))
    r1 = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r3d_replay", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv, seed=3,
    )
    r2 = run_kernel(
        input_smiles="CCCCCCCCO", case_id="r3d_replay", fold_id="fold_fx_p3",
        mode="fixture", train_view=tv, seed=3,
    )
    assert [c.candidate_id for c in r1.candidates] == \
        [c.candidate_id for c in r2.candidates]
    assert [(f.failure_code, f.component, f.detail) for f in r1.failures] == \
        [(f.failure_code, f.component, f.detail) for f in r2.failures]
    assert [s.model_dump(mode="json") for s in r1.trace.stages] == \
        [s.model_dump(mode="json") for s in r2.trace.stages]
