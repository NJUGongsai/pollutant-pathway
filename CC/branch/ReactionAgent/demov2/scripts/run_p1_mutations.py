#!/usr/bin/env python3
"""P1 Gate mutation runner — 8 mutations on isolated temp copies (§18.3).

For each mutation:
1. Create a temp copy of the evidence JSON (or test file)
2. Apply the mutation
3. Run the specific gate check function (monkeypatched to read the temp copy)
4. Record expected fail vs actual fail

Mutations ONLY touch temp copies — formal code is never polluted (§18.3).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEMOV2_ROOT)

# Import gate check functions and helpers
from scripts.run_p1_gate import (  # noqa: E402
    check_g03_legacy_lineage_audit,
    check_g04_mapping_adapter,
    check_g05_participant_roles,
    check_g06_lineage_graph,
    check_g08_eligibility_quarantine,
    check_g09_snapshot_reproducibility,
    check_g10_manual_audit_tests,
    REPORT_DIR, DATA_AUDIT_DIR, DEMOV2_ROOT,
)
import scripts.run_p1_gate as gate_mod  # noqa: E402


def _read_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _write_json(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _run_check_with_patched_dir(check_fn, patch_attr: str, temp_dir: str) -> dict:
    """Run a gate check function with REPORT_DIR/DATA_AUDIT_DIR patched."""
    old = getattr(gate_mod, patch_attr)
    setattr(gate_mod, patch_attr, temp_dir)
    try:
        return check_fn()
    finally:
        setattr(gate_mod, patch_attr, old)


def mutation_1_delete_participant_preservation() -> dict:
    """Mutation 1: delete participant preservation check (invariant_holds=False).

    Expected: G05 FAIL (multiset invariant does not hold).
    """
    with tempfile.TemporaryDirectory(prefix="p1_mutation_1_") as tmpdir:
        src = os.path.join(REPORT_DIR, "participant_role_sample.json")
        dst = os.path.join(tmpdir, "participant_role_sample.json")
        data = _read_json(src)
        # Mutation: set invariant_holds=False and break counts
        data["multiset_invariant"]["invariant_holds"] = False
        data["multiset_invariant"]["input_count"] = 5
        data["multiset_invariant"]["output_count"] = 3
        _write_json(dst, data)
        result = _run_check_with_patched_dir(
            check_g05_participant_roles, "REPORT_DIR", tmpdir)
        return {"mutation": "delete participant preservation (invariant_holds=False)",
                "expected": "G05 FAIL", "actual_passed": result["passed"],
                "actual_blocked": result.get("blocked", False),
                "evidence": result["evidence"][:200],
                "caught": not result["passed"]}


def mutation_2_critical_tie_take_max() -> dict:
    """Mutation 2: critical tie takes max (silent pick instead of ambiguity set).

    Expected: G06 FAIL (no-silent-tie not verified).
    """
    with tempfile.TemporaryDirectory(prefix="p1_mutation_2_") as tmpdir:
        src = os.path.join(REPORT_DIR, "lineage_regression_cases.json")
        dst = os.path.join(tmpdir, "lineage_regression_cases.json")
        data = _read_json(src)
        # Mutation: in tie case, set strict_eligible_count=1 (silent pick)
        # and remove ambiguity_sets
        for c in data.get("regression_cases", []):
            if "tie" in c.get("case", "").lower():
                c["strict_eligible_count"] = 1
                c["ambiguity_sets"] = []
                c["failure_reason"] = "silent_max_pick"
        _write_json(dst, data)
        result = _run_check_with_patched_dir(
            check_g06_lineage_graph, "REPORT_DIR", tmpdir)
        return {"mutation": "critical tie takes max (silent pick)",
                "expected": "G06 FAIL", "actual_passed": result["passed"],
                "actual_blocked": result.get("blocked", False),
                "evidence": result["evidence"][:200],
                "caught": not result["passed"]}


def mutation_3_mcs_full_mapping() -> dict:
    """Mutation 3: MCS marked as full mapping (assignment_method=mcs_full).

    Expected: G04 FAIL (assignment_method is not formal_mapped).
    Note: G04 is BLOCKED when integration_status != INTEGRATION_COMPLETE.
    The mutation changes the assignment_method field, but since G04 checks
    integration_status first and returns BLOCKED, we also patch the
    integration status to INTEGRATION_COMPLETE to test the assignment_method
    check specifically.
    """
    with tempfile.TemporaryDirectory(prefix="p1_mutation_3_") as tmpdir:
        src = os.path.join(REPORT_DIR, "mapping_integration_sample.json")
        dst = os.path.join(tmpdir, "mapping_integration_sample.json")
        data = _read_json(src)
        # Mutation: set assignment_method to mcs_full_mapping
        fake = data.get("unit_contract", {}).get("fake_mapper_sample", {})
        fake["formal_mapped_source_assignment"]["assignment_method"] = "mcs_full_mapping"
        # Also set integration to COMPLETE so G04 doesn't BLOCK first
        data["real_mapper_integration"]["status"] = "INTEGRATION_COMPLETE"
        data["real_mapper_integration"]["all_backends_unavailable"] = False
        _write_json(dst, data)
        result = _run_check_with_patched_dir(
            check_g04_mapping_adapter, "REPORT_DIR", tmpdir)
        return {"mutation": "MCS marked as full mapping (assignment_method=mcs_full_mapping)",
                "expected": "G04 FAIL", "actual_passed": result["passed"],
                "actual_blocked": result.get("blocked", False),
                "evidence": result["evidence"][:200],
                "caught": not result["passed"] and not result.get("blocked", False)}


def mutation_4_mapper_fills_mechanism() -> dict:
    """Mutation 4: mapper automatically fills mechanism (formal_only_verified=False).

    Expected: G04 FAIL (formal_only_verified is not True).
    """
    with tempfile.TemporaryDirectory(prefix="p1_mutation_4_") as tmpdir:
        src = os.path.join(REPORT_DIR, "mapping_integration_sample.json")
        dst = os.path.join(tmpdir, "mapping_integration_sample.json")
        data = _read_json(src)
        # Mutation: set formal_only_verified=False
        data["unit_contract"]["formal_only_verified"] = False
        # Also set integration to COMPLETE so G04 doesn't BLOCK first
        data["real_mapper_integration"]["status"] = "INTEGRATION_COMPLETE"
        data["real_mapper_integration"]["all_backends_unavailable"] = False
        _write_json(dst, data)
        result = _run_check_with_patched_dir(
            check_g04_mapping_adapter, "REPORT_DIR", tmpdir)
        return {"mutation": "mapper fills mechanism (formal_only_verified=False)",
                "expected": "G04 FAIL", "actual_passed": result["passed"],
                "actual_blocked": result.get("blocked", False),
                "evidence": result["evidence"][:200],
                "caught": not result["passed"] and not result.get("blocked", False)}


def mutation_5_quarantine_into_production() -> dict:
    """Mutation 5: quarantine record enters production index.

    Expected: G08 FAIL (prohibited/quarantine row in production).
    """
    with tempfile.TemporaryDirectory(prefix="p1_mutation_5_") as tmpdir:
        src = os.path.join(REPORT_DIR, "eligibility_matrix_execution.json")
        dst = os.path.join(tmpdir, "eligibility_matrix_execution.json")
        data = _read_json(src)
        # Mutation: set a quarantined row's evaluation_bucket to production
        for r in data.get("policy_manifest", []):
            if r.get("quarantine_behavior") == "quarantined":
                r["evaluation_bucket"] = "production"
                break
        _write_json(dst, data)
        result = _run_check_with_patched_dir(
            check_g08_eligibility_quarantine, "REPORT_DIR", tmpdir)
        return {"mutation": "quarantine record into production index",
                "expected": "G08 FAIL", "actual_passed": result["passed"],
                "actual_blocked": result.get("blocked", False),
                "evidence": result["evidence"][:200],
                "caught": not result["passed"]}


def mutation_6_snapshot_nondeterministic() -> dict:
    """Mutation 6: snapshot hash is non-deterministic (same_hash_3way=False).

    Expected: G09 FAIL (deterministic rebuild failed).
    """
    with tempfile.TemporaryDirectory(prefix="p1_mutation_6_") as tmpdir:
        src = os.path.join(REPORT_DIR, "snapshot_build_sample.json")
        dst = os.path.join(tmpdir, "snapshot_build_sample.json")
        data = _read_json(src)
        # Mutation: set same_hash_3way=False and make hashes differ
        fs = data.get("fixture_snapshot", {})
        fs["determinism_evidence"]["same_hash_3way"] = False
        fs["build_a"]["snapshot_hash"] = "aaa111"
        fs["build_b"]["snapshot_hash"] = "bbb222"
        _write_json(dst, data)
        result = _run_check_with_patched_dir(
            check_g09_snapshot_reproducibility, "REPORT_DIR", tmpdir)
        return {"mutation": "snapshot hash non-deterministic (same_hash_3way=False)",
                "expected": "G09 FAIL", "actual_passed": result["passed"],
                "actual_blocked": result.get("blocked", False),
                "evidence": result["evidence"][:200],
                "caught": not result["passed"]}


def mutation_7_delete_proline_2og_case() -> dict:
    """Mutation 7: delete proline/2OG required case from regression cases.

    Expected: G06 FAIL (case count < 14 or proline case not found).
    """
    with tempfile.TemporaryDirectory(prefix="p1_mutation_7_") as tmpdir:
        src = os.path.join(REPORT_DIR, "lineage_regression_cases.json")
        dst = os.path.join(tmpdir, "lineage_regression_cases.json")
        data = _read_json(src)
        # Mutation: remove the proline case
        data["regression_cases"] = [
            c for c in data.get("regression_cases", [])
            if "proline" not in c.get("case", "").lower()
        ]
        _write_json(dst, data)
        result = _run_check_with_patched_dir(
            check_g06_lineage_graph, "REPORT_DIR", tmpdir)
        return {"mutation": "delete proline/2OG required case",
                "expected": "G06 FAIL", "actual_passed": result["passed"],
                "actual_blocked": result.get("blocked", False),
                "evidence": result["evidence"][:200],
                "caught": not result["passed"]}


def mutation_8_add_skipped_test() -> dict:
    """Mutation 8: add a skipped/xfailed test to the suite.

    Expected: G10 FAIL (pytest has skipped tests, §17 zero-skip violated).

    This mutation calls the actual ``check_g10_manual_audit_tests`` function
    (not just a standalone pytest run) so its verification strength matches
    M1-M7. G10's pytest subprocess is monkeypatched to run on a temp dir
    containing a skip + xfail test, and G10's audit report is faked to COMPLETE
    so the skip detection is the sole reason for FAIL (not a pre-existing
    BLOCKED on annotator status).
    """
    import subprocess
    from unittest.mock import patch

    with tempfile.TemporaryDirectory(prefix="p1_mutation_8_") as tmpdir:
        # 1. Fake a COMPLETE manual audit report so G10 is NOT blocked on
        #    annotator/adjudication status — the skip detection must be the
        #    sole reason for FAIL.
        fake_audit = {
            "status": "COMPLETE",
            "annotator_a_status": "COMPLETE",
            "annotator_b_status": "COMPLETE",
            "adjudication_status": "COMPLETE",
            "protocol_frozen_before_results": True,
            "pass_threshold_frozen": {f"H{i}": "frozen" for i in range(1, 8)},
            "catastrophic_error_count": 0,
            "pass_status": "PASS",
            "annotator_a_file": None,
            "annotator_b_file": None,
        }
        _write_json(os.path.join(tmpdir, "manual_audit_report.json"), fake_audit)

        # 2. Temp test dir with a skip + xfail test (§17 zero-skip violation)
        skip_test_dir = os.path.join(tmpdir, "skip_tests")
        os.makedirs(skip_test_dir, exist_ok=True)
        with open(os.path.join(skip_test_dir, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(skip_test_dir, "test_mutation_skip.py"), "w") as f:
            f.write(
                "import pytest\n"
                "@pytest.mark.skip(reason='mutation test')\n"
                "def test_mutation_skipped():\n"
                "    assert True\n"
                "\n"
                "@pytest.mark.xfail\n"
                "def test_mutation_xfailed():\n"
                "    assert False\n"
            )

        # 3. Monkeypatch G10: redirect its pytest subprocess to the skip test
        #    dir, and point REPORT_DIR at the temp dir (fake complete audit).
        #    Save/restore .pytest_gate_p1_report.json so the mutation does not
        #    pollute DEMOV2_ROOT for subsequent test runs (§18.3 temp-copy only).
        original_run_subprocess = gate_mod._run_subprocess
        gate_report = os.path.join(gate_mod.DEMOV2_ROOT, ".pytest_gate_p1_report.json")
        saved_report = None
        if os.path.isfile(gate_report):
            with open(gate_report) as f:
                saved_report = f.read()

        def patched_run_subprocess(cmd, timeout=300):
            # Intercept the G10 pytest call and redirect tests/ → skip_test_dir
            if "pytest" in cmd and "tests/" in cmd:
                new_cmd = []
                for arg in cmd:
                    if arg == "tests/":
                        new_cmd.append(skip_test_dir)
                    elif arg.startswith("--ignore="):
                        # drop the contract-test ignore (not in temp dir)
                        continue
                    else:
                        new_cmd.append(arg)
                return subprocess.run(
                    new_cmd, cwd=gate_mod.DEMOV2_ROOT,
                    capture_output=True, text=True, timeout=timeout,
                )
            return original_run_subprocess(cmd, timeout)

        try:
            with patch.object(gate_mod, "REPORT_DIR", tmpdir), \
                 patch.object(gate_mod, "_run_subprocess", patched_run_subprocess):
                result = check_g10_manual_audit_tests()
        finally:
            # Restore the gate report file so the mutation leaves no trace
            if saved_report is not None:
                with open(gate_report, "w") as f:
                    f.write(saved_report)
            elif os.path.isfile(gate_report):
                os.remove(gate_report)

        stats = result.get("details", {}).get("pytest_stats", {})
        return {
            "mutation": "add skipped/xfailed test",
            "expected": "G10 zero-skip FAIL",
            "actual_passed": result["passed"],
            "actual_blocked": result.get("blocked", False),
            "evidence": (
                f"G10 check called directly; pytest_stats={stats}; "
                f"passed={result['passed']}, blocked={result.get('blocked', False)}"),
            "caught": (not result["passed"] and not result.get("blocked", False)),
        }


# =====================================================================
# §6 Round 2 mutations M9–M25 (anti-false-positive)
# =====================================================================

def _has_impl(result: dict) -> bool:
    return bool(result.get("implementation_failures"))


def _impl_text(result: dict) -> str:
    return "; ".join(result.get("implementation_failures", []))


# --- G03 mutations (M9–M11): fake COMPLETE must be caught ---

def mutation_9_g03_complete_zero_records() -> dict:
    """M9: G03 verdict=COMPLETE but total_reactions=0 / audited=0.

    Expected: G03 implementation FAILURE (M9 — fake complete with zero records),
    NOT a silent BLOCKED."""
    with tempfile.TemporaryDirectory(prefix="p1_m9_") as tmpdir:
        src = os.path.join(DATA_AUDIT_DIR, "legacy_lineage_audit.json")
        data = _read_json(src)
        data["verdict"] = "COMPLETE"
        data["verdict_reasons"] = []
        data["counts"]["total_reactions"] = 0
        data["counts"]["audited_reactions"] = 0
        data["real_source_status"]["real_reaction_source_found"] = True
        data["real_source_status"]["source_confirmed_by_env"] = True
        data["proline_2og_case"]["source_record_found"] = True
        data["proline_2og_case"]["status"] = "found"
        _write_json(os.path.join(tmpdir, "legacy_lineage_audit.json"), data)
        result = _run_check_with_patched_dir(
            check_g03_legacy_lineage_audit, "DATA_AUDIT_DIR", tmpdir)
        caught = _has_impl(result) and "total_reactions" in _impl_text(result)
        return _mk("M9", "G03 verdict COMPLETE but zero audited records",
                   "G03 implementation FAIL (zero records)", result, caught)


def mutation_10_g03_complete_empty_source_ids() -> dict:
    """M10: G03 verdict=COMPLETE but source_ids/examples empty.

    Expected: G03 implementation FAILURE (empty source_ids)."""
    with tempfile.TemporaryDirectory(prefix="p1_m10_") as tmpdir:
        src = os.path.join(DATA_AUDIT_DIR, "legacy_lineage_audit.json")
        data = _read_json(src)
        data["verdict"] = "COMPLETE"
        data["verdict_reasons"] = []
        data["counts"]["total_reactions"] = 10
        data["counts"]["audited_reactions"] = 10
        data["real_source_status"]["real_reaction_source_found"] = True
        data["real_source_status"]["source_confirmed_by_env"] = True
        data["proline_2og_case"]["source_record_found"] = True
        data["proline_2og_case"]["status"] = "found"
        data["source_ids"] = []
        data["examples"] = []
        _write_json(os.path.join(tmpdir, "legacy_lineage_audit.json"), data)
        result = _run_check_with_patched_dir(
            check_g03_legacy_lineage_audit, "DATA_AUDIT_DIR", tmpdir)
        caught = _has_impl(result) and "source_ids" in _impl_text(result)
        return _mk("M10", "G03 verdict COMPLETE but source_ids/examples empty",
                   "G03 implementation FAIL (empty source_ids)", result, caught)


def mutation_11_g03_legacy_hash_mismatch() -> dict:
    """M11: G03 stored legacy module hash != actual file hash.

    Expected: G03 implementation FAILURE (hash mismatch)."""
    with tempfile.TemporaryDirectory(prefix="p1_m11_") as tmpdir:
        src = os.path.join(DATA_AUDIT_DIR, "legacy_lineage_audit.json")
        data = _read_json(src)
        data["legacy_module"]["sha256"] = "deadbeef" * 8  # wrong hash
        _write_json(os.path.join(tmpdir, "legacy_lineage_audit.json"), data)
        result = _run_check_with_patched_dir(
            check_g03_legacy_lineage_audit, "DATA_AUDIT_DIR", tmpdir)
        caught = _has_impl(result) and "hash mismatch" in _impl_text(result)
        return _mk("M11", "G03 legacy source file hash mismatch",
                   "G03 implementation FAIL (hash mismatch)", result, caught)


# --- G04 mutations (M12–M13): status-only promotion must not bypass live probe ---

def mutation_12_g04_status_only_promotion() -> dict:
    """M12: JSON says COMPLETE while an injected live adapter is a skeleton.

    The production adapter is now implemented, so the old mutation premise
    (assuming the repository adapter itself remained a skeleton) became stale.
    Injecting a skeleton at the live boundary preserves the original anti-false-
    positive invariant without rewriting production code.

    Expected: G04 still does not PASS because the live probe overrides JSON."""
    with tempfile.TemporaryDirectory(prefix="p1_m12_") as tmpdir:
        src = os.path.join(REPORT_DIR, "mapping_integration_sample.json")
        data = _read_json(src)
        data["real_mapper_integration"]["status"] = "INTEGRATION_COMPLETE"
        data["real_mapper_integration"]["all_backends_unavailable"] = False
        data["real_mapper_integration"]["reason"] = ""
        _write_json(os.path.join(tmpdir, "mapping_integration_sample.json"), data)
        class _InjectedSkeletonAdapter:
            backend = "rdkit"

            def __init__(self, *args, **kwargs):
                pass

            def is_available(self):
                return True

            def map_reaction(self, reaction):
                raise NotImplementedError("INTEGRATION_BLOCKED injected skeleton")

        from unittest.mock import patch
        with patch(
            "reaction_agent.mapping.adapter.RealMapperAdapter",
            _InjectedSkeletonAdapter,
        ):
            result = _run_check_with_patched_dir(
                check_g04_mapping_adapter, "REPORT_DIR", tmpdir)
        # Caught = did NOT pass (live probe prevented fake PASS) AND live probe
        # evidence is present (proves it was the probe, not a coincidental block).
        live_probed = result.get("details", {}).get("live_map_reaction_error") is not None
        caught = (not result["passed"]) and live_probed
        return _mk("M12", "G04 status-only promotion against injected live skeleton",
                   "G04 BLOCKED via live probe (no fake PASS)", result, caught)


def mutation_13_g04_unavailable_but_complete() -> dict:
    """M13: G04 all_backends_unavailable=true but status=COMPLETE (contradictory).

    Expected: G04 does NOT pass — the contradictory JSON is not trusted."""
    with tempfile.TemporaryDirectory(prefix="p1_m13_") as tmpdir:
        src = os.path.join(REPORT_DIR, "mapping_integration_sample.json")
        data = _read_json(src)
        data["real_mapper_integration"]["status"] = "INTEGRATION_COMPLETE"
        data["real_mapper_integration"]["all_backends_unavailable"] = True
        _write_json(os.path.join(tmpdir, "mapping_integration_sample.json"), data)
        result = _run_check_with_patched_dir(
            check_g04_mapping_adapter, "REPORT_DIR", tmpdir)
        caught = not result["passed"]
        return _mk("M13", "G04 all_backends_unavailable=true but status COMPLETE",
                   "G04 not PASS (contradictory JSON rejected)", result, caught)


# --- G06 mutations (M14–M15): proline case + forbidden lineage ---

def mutation_14_g06_remove_proline_keep_count() -> dict:
    """M14: G06 remove proline case while keeping >=14 cases.

    Expected: G06 implementation FAILURE (proline case missing)."""
    with tempfile.TemporaryDirectory(prefix="p1_m14_") as tmpdir:
        src = os.path.join(REPORT_DIR, "lineage_regression_cases.json")
        data = _read_json(src)
        cases = data.get("regression_cases", [])
        proline = [c for c in cases if "proline" in c.get("case", "").lower()]
        non_proline = [c for c in cases if "proline" not in c.get("case", "").lower()]
        # Pad with duplicates of a non-proline case to keep count >= 14
        while len(non_proline) < 14 and non_proline:
            non_proline.append(dict(non_proline[0]))
        data["regression_cases"] = non_proline
        _write_json(os.path.join(tmpdir, "lineage_regression_cases.json"), data)
        result = _run_check_with_patched_dir(
            check_g06_lineage_graph, "REPORT_DIR", tmpdir)
        caught = _has_impl(result) and "proline" in _impl_text(result).lower()
        return _mk("M14", "G06 remove proline case while keeping >=14 cases",
                   "G06 implementation FAIL (proline missing)", result, caught)


def mutation_15_g06_inject_forbidden_pair() -> dict:
    """M15: G06 inject forbidden 2OG->hydroxyproline strict pair.

    Expected: G06 implementation FAILURE (forbidden cross-lineage pairing)."""
    with tempfile.TemporaryDirectory(prefix="p1_m15_") as tmpdir:
        src = os.path.join(REPORT_DIR, "lineage_regression_cases.json")
        data = _read_json(src)
        for c in data.get("regression_cases", []):
            if "proline" in c.get("case", "").lower():
                # Inject a forbidden pair: a second reactant -> p1 (product of r1)
                # so p1 comes from two reactants (2OG->hydroxyproline class).
                pairs = c.get("strict_eligible_pairs", [])
                pairs.append(["r2", "p1"])
                c["strict_eligible_pairs"] = pairs
                break
        _write_json(os.path.join(tmpdir, "lineage_regression_cases.json"), data)
        result = _run_check_with_patched_dir(
            check_g06_lineage_graph, "REPORT_DIR", tmpdir)
        caught = _has_impl(result) and "forbidden" in _impl_text(result).lower()
        return _mk("M15", "G06 inject forbidden 2OG->hydroxyproline strict pair",
                   "G06 implementation FAIL (forbidden pairing)", result, caught)


# --- G08 mutations (M16–M17): incomplete source/mapping must not enter strict ---

def _g08_strict_item_with(mapping_completeness="complete", source_completeness="complete"):
    """Build a GENUINELY strict item with overridable completeness fields.

    Critical-2 (§6.7/§8.1): the baseline (all defaults) MUST classify as
    ``strict_eligible`` so that M16/M17 are caught by their SPECIFIC mutation
    (failed mapping / incomplete source), not vacuously by an unrelated
    precondition failure. The mapping therefore supports BOTH atom maps and the
    lineage is explicitly resolved.
    """
    from reaction_agent.schemas.common import (
        LedgerBalanceStatus, LineageResolutionQuality, MappingStatus,
        MappingQualityClass, ParticipantRole, SourceAssignmentMethod,
    )
    from reaction_agent.schemas.evidence import ReactionEvidence, ReactionParticipant
    from reaction_agent.schemas.ledger import RoleAssignment, SourceReactionLedger
    from reaction_agent.schemas.mapping import (
        FormalMappedAtomPair, FormalSourceAssignment, MappingReport,
    )
    from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
    from reaction_agent.eligibility.engine import decide_eligibility
    from reaction_agent.schemas.common import EligibilityStatus

    # R7-01B: genuine fully-mapped baseline — CC (2 heavy atoms) with 2 maps.
    r1 = ReactionParticipant(participant_id="r1", molecule_id="mol_r1",
                             canonical_smiles="CC", side="reactant", atom_map_numbers=[1, 2],
                             mapped_fraction=1.0)
    p1 = ReactionParticipant(participant_id="p1", molecule_id="mol_p1",
                             canonical_smiles="CC", side="product", atom_map_numbers=[1, 2],
                             mapped_fraction=1.0)
    mr = MappingReport(
        mapper_name="fake", mapper_version="v1", mapper_parameters={},
        input_hash="i", output_hash="o", mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0, map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="fake", mapper_version="v1",
            mapped_atom_pairs=[
                FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=1,
                    product_participant_id="p1", product_atom_map=1),
                FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=2,
                    product_participant_id="p1", product_atom_map=2),
            ],
            assignment_method=SourceAssignmentMethod.formal_mapped,
            assignment_quality=MappingQualityClass.high_quality, assignment_ambiguity=False),
        fallback_method=None)
    ev = ReactionEvidence(reaction_id="rxn_m", source_record_id="src_m",
                          source_name="s", raw_reaction="CC>>CC", normalized_reaction="CC>>CC",
                          direction="forward", participants=[r1, p1], mapping_report=mr)
    ld = SourceReactionLedger(
        ledger_id="srl_m", reaction_evidence_id="rxn_m",
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        charge_balance=0,
        role_assignments=[
            RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9)],
        hydrogen_policy="explicit", proton_policy="explicit", electron_policy="explicit",
        source_completeness=source_completeness, mapping_completeness=mapping_completeness)
    lins = [ResolvedTransformedLineage(lineage_id="lin_r1_p1",
            reactant_participant_id="r1", product_participant_id="p1",
            ambiguity="none", transformed_atom_maps=[1, 2],
            resolution_quality=LineageResolutionQuality.resolved)]
    d = decide_eligibility(ev, ld, lins)
    return d, EligibilityStatus


def mutation_16_g08_failed_mapping_enters_strict() -> dict:
    """M16: mapping_completeness=failed + fully_balanced → must NOT be strict.

    Expected: decide_eligibility returns non-strict (fail-closed)."""
    d, ES = _g08_strict_item_with(mapping_completeness="failed")
    caught = d.eligibility != ES.strict_eligible
    return {"mutation_id": "M16",
            "mutation": "G08 mapping_completeness=failed enters strict production",
            "expected": "decide_eligibility non-strict (fail-closed)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"eligibility={d.eligibility.value}, reason={d.reason[:120]}",
            "caught": caught}


def mutation_17_g08_incomplete_source_enters_strict() -> dict:
    """M17: source_completeness=incomplete + fully_balanced → must NOT be strict.

    Expected: decide_eligibility returns non-strict (fail-closed)."""
    d, ES = _g08_strict_item_with(source_completeness="incomplete")
    caught = d.eligibility != ES.strict_eligible
    return {"mutation_id": "M17",
            "mutation": "G08 source_completeness=incomplete enters strict production",
            "expected": "decide_eligibility non-strict (fail-closed)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"eligibility={d.eligibility.value}, reason={d.reason[:120]}",
            "caught": caught}


# --- G09 mutations (M18–M21): nested evidence mutation must change hash ---

def _g09_hash_with(mutator) -> str:
    """Build a strict item, optionally mutate it, return compute_snapshot_hash."""
    from reaction_agent.snapshot.builder import compute_snapshot_hash, SnapshotEvidenceItem
    from scripts.run_p1_gate import _g09_item_strict, _g09_t10_fixture_config
    item = _g09_item_strict()
    if mutator is not None:
        mutator(item)
    items = [item, _g09_item_strict.__wrapped__() if hasattr(_g09_item_strict, "__wrapped__")
             else None]
    # Use a single-item list for clean before/after comparison
    config = _g09_t10_fixture_config(os.path.join(tempfile.gettempdir(), "m_snap"))
    return compute_snapshot_hash(config, [item])


def _g09_mutation(mutation_id, desc, mutator) -> dict:
    """Build hash before/after a nested mutation; caught = hash changed."""
    from reaction_agent.snapshot.builder import compute_snapshot_hash
    from scripts.run_p1_gate import _g09_item_strict, _g09_t10_fixture_config
    base = _g09_item_strict()
    config = _g09_t10_fixture_config(os.path.join(tempfile.gettempdir(), "m_snap"))
    h_before = compute_snapshot_hash(config, [base])
    mutated = _g09_item_strict()
    mutator(mutated)
    h_after = compute_snapshot_hash(config, [mutated])
    caught = h_before != h_after
    return {"mutation_id": mutation_id, "mutation": desc,
            "expected": "snapshot hash changes (tampering detected)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"before={h_before[:16]}... after={h_after[:16]}... changed={caught}",
            "caught": caught}


def mutation_18_g09_participant_provenance_no_hash_change() -> dict:
    """M18: mutate participant provenance → hash must change."""
    return _g09_mutation("M18", "G09 mutate participant provenance without hash change",
                         lambda it: it.reaction_evidence.participants[0].provenance.append("x"))


def mutation_19_g09_mapping_pair_no_hash_change() -> dict:
    """M19: mutate mapping pair → hash must change."""
    def m(it):
        it.reaction_evidence.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs[0].product_atom_map = 99
    return _g09_mutation("M19", "G09 mutate mapping pair without hash change", m)


def mutation_20_g09_source_ledger_no_hash_change() -> dict:
    """M20: mutate source ledger → hash must change."""
    return _g09_mutation("M20", "G09 mutate source ledger without hash change",
                         lambda it: it.source_ledger.unknowns.append("u"))


def mutation_21_g09_transformed_lineage_no_hash_change() -> dict:
    """M21: mutate transformed lineage atom maps → hash must change."""
    return _g09_mutation("M21", "G09 mutate transformed lineage without hash change",
                         lambda it: it.lineages[0].transformed_atom_maps.append(99))


# --- G10 mutations (M22–M24): fake complete / non-independent / missing adjudication ---

def _g10_fake_audit(*, ann_files=True, same_id=False, disagreement=0,
                    adjudication_complete=True, adjudication_file=True) -> dict:
    """Build a fake COMPLETE manual audit report for G10 mutation tests."""
    audit = {
        "status": "COMPLETE",
        "annotator_a_status": "COMPLETE",
        "annotator_b_status": "COMPLETE",
        "adjudication_status": "COMPLETE" if adjudication_complete else "NOT_PRODUCED",
        "protocol_frozen_before_results": True,
        "pass_threshold_frozen": {f"H{i}": "frozen" for i in range(1, 8)},
        "catastrophic_error_count": 0,
        "disagreement_count": disagreement,
        "pass_status": "PASS",
        "annotator_a_id": "annotator_A",
        "annotator_b_id": "annotator_A" if same_id else "annotator_B",
    }
    if ann_files:
        # Write real parseable annotation files in a temp dir
        td = tempfile.mkdtemp(prefix="p1_g10_ann_")
        for role in ("annotator_a_file", "annotator_b_file"):
            fp = os.path.join(td, f"{role}.json")
            with open(fp, "w") as f:
                json.dump({"annotations": [], "annotator_id": audit[role.replace("_file", "_id")]}, f)
            audit[role] = fp
    else:
        audit["annotator_a_file"] = None
        audit["annotator_b_file"] = None
    if adjudication_file and adjudication_complete:
        td2 = tempfile.mkdtemp(prefix="p1_g10_adj_")
        fp = os.path.join(td2, "adjudication.json")
        with open(fp, "w") as f:
            json.dump({"adjudications": []}, f)
        audit["adjudication_file"] = fp
    else:
        audit["adjudication_file"] = None
    return audit


def _run_g10_with_audit(audit: dict) -> dict:
    """Run check_g10 with a temp REPORT_DIR containing the fake audit.

    Patches the pytest subprocess to a trivial passing test dir so the audit
    checks (not the test suite) are the focus. Returns the G10 result."""
    import subprocess
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix="p1_m_g10_") as tmpdir:
        _write_json(os.path.join(tmpdir, "manual_audit_report.json"), audit)
        # Trivial passing test dir so G10's pytest subprocess is green
        td = os.path.join(tmpdir, "ok_tests")
        os.makedirs(td, exist_ok=True)
        with open(os.path.join(td, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(td, "test_ok.py"), "w") as f:
            f.write("def test_ok():\n    assert True\n")
        gate_report = os.path.join(DEMOV2_ROOT, ".pytest_gate_p1_report.json")
        saved = None
        if os.path.isfile(gate_report):
            with open(gate_report) as f:
                saved = f.read()

        def patched(cmd, timeout=300):
            if "pytest" in cmd and "tests/" in cmd:
                new_cmd = [td if a == "tests/" else a for a in cmd
                           if not a.startswith("--ignore=")]
                return subprocess.run(new_cmd, cwd=DEMOV2_ROOT,
                                      capture_output=True, text=True, timeout=timeout)
            return gate_mod._run_subprocess(cmd, timeout)
        try:
            with patch.object(gate_mod, "REPORT_DIR", tmpdir), \
                 patch.object(gate_mod, "_run_subprocess", patched):
                result = check_g10_manual_audit_tests()
        finally:
            if saved is not None:
                with open(gate_report, "w") as f:
                    f.write(saved)
            elif os.path.isfile(gate_report):
                os.remove(gate_report)
        return result


def mutation_22_g10_complete_null_files() -> dict:
    """M22: G10 statuses COMPLETE but annotator files null.

    Expected: G10 implementation FAILURE (fake complete, null files)."""
    audit = _g10_fake_audit(ann_files=False)
    result = _run_g10_with_audit(audit)
    impl = _impl_text(result)
    caught = _has_impl(result) and ("null" in impl or "missing" in impl or "fake complete" in impl)
    return _mk("M22", "G10 COMPLETE statuses with null annotation files",
               "G10 implementation FAIL (null annotation files)", result, caught)


def mutation_23_g10_same_annotator_id() -> dict:
    """M23: G10 annotator A ID == B ID (not independent).

    Expected: G10 implementation FAILURE (non-independent annotators)."""
    audit = _g10_fake_audit(ann_files=True, same_id=True)
    result = _run_g10_with_audit(audit)
    impl = _impl_text(result)
    caught = _has_impl(result) and "annotator_a_id" in impl
    return _mk("M23", "G10 same annotator ID for A and B",
               "G10 implementation FAIL (non-independent annotators)", result, caught)


def mutation_24_g10_missing_adjudication() -> dict:
    """M24: G10 disagreement_count > 0 but adjudication missing.

    Expected: G10 implementation FAILURE (adjudication must cover disagreements)."""
    audit = _g10_fake_audit(ann_files=True, disagreement=2,
                            adjudication_complete=False, adjudication_file=False)
    audit["adjudication_status"] = "NOT_PRODUCED"
    result = _run_g10_with_audit(audit)
    impl = _impl_text(result)
    caught = _has_impl(result) and "disagreement" in impl.lower()
    return _mk("M24", "G10 missing adjudication for disagreement",
               "G10 implementation FAIL (adjudication missing)", result, caught)


# --- §5.1 aggregation mutation (M25) ---

def mutation_25_blocked_gate_with_impl_failure() -> dict:
    """M25: a blocked gate that also contains an implementation failure must
    be reported as FAIL, NOT masked as BLOCKED.

    §8.2: calls the REAL ``aggregate_gate_status`` authority from the gate
    module — NOT a second copy of the aggregation logic — so this mutation
    proves the actual report aggregation cannot regress.
    """
    from scripts.run_p1_gate import aggregate_gate_status
    fake_checks = [
        {"gate_id": "P1-GXX", "name": "test", "passed": False, "blocked": True,
         "evidence": "BLOCKED: dep; IMPLEMENTATION ISSUES: bug",
         "details": {},
         "implementation_failures": ["bug"],
         "external_blockers": ["dep"]},
        {"gate_id": "P1-GYY", "name": "ok", "passed": True, "blocked": False,
         "evidence": "ok", "details": {},
         "implementation_failures": [], "external_blockers": []},
    ]
    agg = aggregate_gate_status(fake_checks)
    # The gate with BOTH a blocker and an impl failure must be counted as FAIL,
    # never masked as BLOCKED, and drive overall NOT_READY.
    caught = (
        "P1-GXX" in agg["impl_fail_gates"]
        and "P1-GXX" not in agg["blocked_gates"]
        and agg["fail_count"] == 1
        and agg["status"] == "NOT_READY_FOR_CHATGPT_AUDIT"
    )
    return {"mutation_id": "M25",
            "mutation": "blocked Gate also contains implementation failure",
            "expected": "Gate reported as FAIL (impl not masked by BLOCKED)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": (f"impl_fail_gates={agg['impl_fail_gates']}, "
                         f"blocked_gates={agg['blocked_gates']}, "
                         f"status={agg['status']} "
                         f"(via real aggregate_gate_status authority)"),
            "caught": caught}


def _mk(mid, mutation, expected, result, caught) -> dict:
    return {"mutation_id": mid, "mutation": mutation, "expected": expected,
            "actual_passed": result.get("passed"), "actual_blocked": result.get("blocked"),
            "evidence": (_impl_text(result) or result.get("evidence", ""))[:300],
            "caught": caught}


# =====================================================================
# Round 3 §8.3 — M26–M41
# M26–M31: complete-evidence hash coverage (Critical-1). A scientific field
#   changes → the record/snapshot hash MUST change. caught = hash changed.
# M32–M41: strict cross-invariants (Critical-2). A single bad field on an
#   otherwise-strict record → engine MUST NOT return strict_eligible (or the
#   builder must fail closed). caught = not strict / build fails.
# =====================================================================

def _strict_inputs():
    """Return (ev, ledger, lineages) for a GENUINELY strict-eligible record.

    Baseline (unmutated) classifies as ``strict_eligible``; M32–M40 apply ONE
    violating mutation and assert the engine no longer returns strict, proving
    the specific cross-invariant (not a vacuous unrelated failure) is enforced.
    """
    from reaction_agent.schemas.common import (
        LedgerBalanceStatus, LineageResolutionQuality, MappingStatus,
        MappingQualityClass, ParticipantRole, SourceAssignmentMethod,
    )
    from reaction_agent.schemas.evidence import ReactionEvidence, ReactionParticipant
    from reaction_agent.schemas.ledger import RoleAssignment, SourceReactionLedger
    from reaction_agent.schemas.mapping import (
        FormalMappedAtomPair, FormalSourceAssignment, MappingReport,
    )
    from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage

    # R7-01B: genuine fully-mapped baseline — CC (2 heavy atoms) with 2 maps.
    r1 = ReactionParticipant(participant_id="r1", molecule_id="mol_r1",
                             canonical_smiles="CC", side="reactant", atom_map_numbers=[1, 2],
                             mapped_fraction=1.0)
    p1 = ReactionParticipant(participant_id="p1", molecule_id="mol_p1",
                             canonical_smiles="CC", side="product", atom_map_numbers=[1, 2],
                             mapped_fraction=1.0)
    mr = MappingReport(
        mapper_name="fake", mapper_version="v1", mapper_parameters={},
        input_hash="i", output_hash="o", mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0, map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="fake", mapper_version="v1",
            mapped_atom_pairs=[
                FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                     product_participant_id="p1", product_atom_map=1),
                FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=2,
                                     product_participant_id="p1", product_atom_map=2),
            ],
            assignment_method=SourceAssignmentMethod.formal_mapped,
            assignment_quality=MappingQualityClass.high_quality, assignment_ambiguity=False),
        fallback_method=None)
    ev = ReactionEvidence(reaction_id="rxn_m", source_record_id="src_m",
                          source_name="s", raw_reaction="CC>>CC", normalized_reaction="CC>>CC",
                          direction="forward", participants=[r1, p1], mapping_report=mr)
    ld = SourceReactionLedger(
        ledger_id="srl_m", reaction_evidence_id="rxn_m",
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        charge_balance=0,
        role_assignments=[
            RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9)],
        hydrogen_policy="explicit", proton_policy="explicit", electron_policy="explicit",
        source_completeness="complete", mapping_completeness="complete")
    lins = [ResolvedTransformedLineage(lineage_id="lin_r1_p1",
            reactant_participant_id="r1", product_participant_id="p1",
            ambiguity="none", transformed_atom_maps=[1, 2],
            resolution_quality=LineageResolutionQuality.resolved)]
    return ev, ld, lins


def _assert_baseline_strict() -> bool:
    """Guard: the unmutated _strict_inputs MUST be strict (else M32–M40 vacuous)."""
    from reaction_agent.eligibility.engine import decide_eligibility
    from reaction_agent.schemas.common import EligibilityStatus
    ev, ld, lins = _strict_inputs()
    return decide_eligibility(ev, ld, lins).eligibility == EligibilityStatus.strict_eligible


def _strict_violation_mutation(mid, desc, mutate) -> dict:
    """Apply a violating mutation to a genuinely-strict record; caught = the
    engine no longer returns strict_eligible AND the baseline WAS strict."""
    from reaction_agent.eligibility.engine import decide_eligibility
    from reaction_agent.schemas.common import EligibilityStatus
    if not _assert_baseline_strict():
        return {"mutation_id": mid, "mutation": desc,
                "expected": "engine non-strict (baseline strict)",
                "actual_passed": False, "actual_blocked": False,
                "evidence": "VACUOUS: baseline _strict_inputs is not strict_eligible",
                "caught": False}
    ev, ld, lins = _strict_inputs()
    ev, ld, lins = mutate(ev, ld, lins)
    d = decide_eligibility(ev, ld, lins)
    caught = d.eligibility != EligibilityStatus.strict_eligible
    return {"mutation_id": mid, "mutation": desc,
            "expected": "decide_eligibility non-strict (fail-closed)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"eligibility={d.eligibility.value}, reason={d.reason[:140]}",
            "caught": caught}


# --- M26–M29: reaction-evidence scientific fields must be hash-covered ---

def mutation_26_reaction_provenance_no_hash_change() -> dict:
    """M26: reaction-level provenance changes → snapshot hash must change."""
    return _g09_mutation("M26", "reaction-level provenance changes but hash unchanged",
                         lambda it: it.reaction_evidence.provenance.append("tampered_reaction_prov"))


def mutation_27_source_citation_no_hash_change() -> dict:
    """M27: source URI/citation changes → snapshot hash must change."""
    def m(it):
        it.reaction_evidence.source_uri_or_citation = "doi:10.0000/tampered"
    return _g09_mutation("M27", "source citation changes but hash unchanged", m)


def mutation_28_fragment_lineage_no_hash_change() -> dict:
    """M28: fragment-lineage / ambiguity evidence changes → hash must change."""
    def m(it):
        it.reaction_evidence.fragment_lineage_graph["frag_1"] = "r1"
        it.reaction_evidence.ambiguity_sets.append({"set": "tampered"})
    return _g09_mutation("M28", "fragment-lineage/ambiguity evidence changes but hash unchanged", m)


def mutation_29_quality_quarantine_no_hash_change() -> dict:
    """M29: quality-report / quarantine evidence changes → hash must change."""
    def m(it):
        it.reaction_evidence.quality_report["purity"] = "tampered_low"
        it.reaction_evidence.quarantine = "tampered_quarantine_note"
    return _g09_mutation("M29", "quality/quarantine evidence changes but hash unchanged", m)


# --- M30–M31: complete decision / quarantine record must be hash-covered ---

def mutation_30_eligibility_decision_no_hash_change() -> dict:
    """M30: EligibilityDecision warnings/evidence changes → record hash must change."""
    from reaction_agent.snapshot.builder import _record_content_hash, _classify_lane
    from reaction_agent.eligibility.engine import decide_eligibility
    ev, ld, lins = _strict_inputs()
    decision = decide_eligibility(ev, ld, lins)
    lane = _classify_lane(decision)
    h_before = _record_content_hash(ev, decision, None, ld, lins, lane)
    mutated = decision.model_copy(update={
        "required_warnings": list(decision.required_warnings) + ["tampered_warning"],
        "evidence_ids": list(decision.evidence_ids) + ["tampered_evidence"],
    })
    h_after = _record_content_hash(ev, mutated, None, ld, lins, lane)
    caught = h_before != h_after
    return {"mutation_id": "M30",
            "mutation": "EligibilityDecision warning/evidence changes but hash unchanged",
            "expected": "record content hash changes (complete decision hashed)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"before={h_before[:16]}... after={h_after[:16]}... changed={caught}",
            "caught": caught}


def mutation_31_quarantine_record_no_hash_change() -> dict:
    """M31: QuarantineRecord changes → record content hash must change."""
    from reaction_agent.snapshot.builder import _record_content_hash, _classify_lane
    from reaction_agent.eligibility.engine import decide_eligibility, build_quarantine_record
    from scripts.run_p1_gate import _g09_item_quarantine
    it = _g09_item_quarantine()
    ev, ld, lins = it.reaction_evidence, it.source_ledger, it.lineages
    decision = decide_eligibility(ev, ld, lins)
    qr = build_quarantine_record(decision, ev)
    if qr is None:
        return {"mutation_id": "M31",
                "mutation": "QuarantineRecord changes but hash unchanged",
                "expected": "record content hash changes (complete quarantine record hashed)",
                "actual_passed": False, "actual_blocked": False,
                "evidence": "SETUP ERROR: quarantine fixture did not produce a QuarantineRecord",
                "caught": False}
    lane = _classify_lane(decision)
    h_before = _record_content_hash(ev, decision, qr, ld, lins, lane)
    mutated = qr.model_copy(update={
        "notes": qr.notes + " tampered",
        "evidence_ids": list(qr.evidence_ids) + ["tampered_evidence"],
    })
    h_after = _record_content_hash(ev, decision, mutated, ld, lins, lane)
    caught = h_before != h_after
    return {"mutation_id": "M31",
            "mutation": "QuarantineRecord changes but hash unchanged",
            "expected": "record content hash changes (complete quarantine record hashed)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"before={h_before[:16]}... after={h_after[:16]}... changed={caught}",
            "caught": caught}


# --- M32–M40: strict cross-invariants (engine must fail closed) ---

def mutation_32_low_mapped_fraction_enters_strict() -> dict:
    def m(ev, ld, lins):
        ev.mapping_report.mapped_heavy_atom_fraction = 0.8
        return ev, ld, lins
    return _strict_violation_mutation(
        "M32", "mapped_heavy_atom_fraction < strict threshold enters strict", m)


def mutation_33_assignment_ambiguity_enters_strict() -> dict:
    def m(ev, ld, lins):
        ev.mapping_report.formal_mapped_source_assignment.assignment_ambiguity = True
        return ev, ld, lins
    return _strict_violation_mutation(
        "M33", "formal assignment ambiguity enters strict", m)


def mutation_34_unknown_participant_enters_strict() -> dict:
    from reaction_agent.schemas.mapping import FormalMappedAtomPair
    def m(ev, ld, lins):
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs.append(
            FormalMappedAtomPair(reactant_participant_id="ghost_reactant", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M34", "formal pair unknown participant enters strict", m)


def mutation_35_unknown_atom_map_enters_strict() -> dict:
    from reaction_agent.schemas.mapping import FormalMappedAtomPair
    def m(ev, ld, lins):
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs.append(
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=99,
                                 product_participant_id="p1", product_atom_map=1))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M35", "formal pair unknown atom map enters strict", m)


def mutation_36_wrong_side_participant_enters_strict() -> dict:
    from reaction_agent.schemas.mapping import FormalMappedAtomPair
    def m(ev, ld, lins):
        # reactant slot references a PRODUCT-side participant (wrong side)
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs.append(
            FormalMappedAtomPair(reactant_participant_id="p1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=2))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M36", "formal pair wrong-side participant enters strict", m)


def mutation_37_unresolved_lineage_enters_strict() -> dict:
    from reaction_agent.schemas.common import LineageResolutionQuality
    def m(ev, ld, lins):
        lins[0].resolution_quality = LineageResolutionQuality.unresolved
        return ev, ld, lins
    return _strict_violation_mutation(
        "M37", "unresolved/failed lineage enters strict", m)


def mutation_38_partial_ambiguity_enters_strict() -> dict:
    def m(ev, ld, lins):
        lins[0].ambiguity = "partial"
        return ev, ld, lins
    return _strict_violation_mutation(
        "M38", "partial identity ambiguity enters strict", m)


def mutation_39_lineage_unsupported_by_mapping_enters_strict() -> dict:
    def m(ev, ld, lins):
        # lineage claims a transformed atom map not present in the formal mapping
        lins[0].transformed_atom_maps = [1, 2, 77]
        return ev, ld, lins
    return _strict_violation_mutation(
        "M39", "lineage unsupported by formal mapping enters strict", m)


def mutation_40_two_reactants_one_product_enters_strict() -> dict:
    from reaction_agent.schemas.evidence import ReactionParticipant
    from reaction_agent.schemas.mapping import FormalMappedAtomPair
    from reaction_agent.schemas.ledger import RoleAssignment
    from reaction_agent.schemas.common import ParticipantRole, LineageResolutionQuality
    from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
    def m(ev, ld, lins):
        # Expand p1 to a 4-heavy product carrying maps 1-4, add a second
        # reactant r2 (CC, maps 3,4) and its pairs + lineage so TWO distinct
        # reactants claim the SAME transformed product p1 (no typed merge
        # authority -> forbidden pairing, the 2OG->hydroxyproline class).
        ev.participants[1].canonical_smiles = "CCCC"
        ev.participants[1].atom_map_numbers = [1, 2, 3, 4]
        r2 = ReactionParticipant(participant_id="r2", molecule_id="mol_r2",
                                 canonical_smiles="CC", side="reactant",
                                 atom_map_numbers=[3, 4], mapped_fraction=1.0)
        ev.participants.append(r2)
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs.extend([
            FormalMappedAtomPair(reactant_participant_id="r2", reactant_atom_map=3,
                                 product_participant_id="p1", product_atom_map=3),
            FormalMappedAtomPair(reactant_participant_id="r2", reactant_atom_map=4,
                                 product_participant_id="p1", product_atom_map=4),
        ])
        ld.role_assignments.append(
            RoleAssignment(participant_id="r2", role=ParticipantRole.transformed_substrate, score=0.9))
        lins.append(ResolvedTransformedLineage(
            lineage_id="lin_r2_p1", reactant_participant_id="r2", product_participant_id="p1",
            ambiguity="none", transformed_atom_maps=[3, 4],
            resolution_quality=LineageResolutionQuality.resolved))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M40", "two reactants claim one transformed product and enter strict", m)


def mutation_41_ledger_disagreement_builds_strict() -> dict:
    """M41: embedded/external source ledgers disagree → builder must fail closed.

    caught = build_snapshot / compute_snapshot_hash raises (never builds an
    inconsistent snapshot, §5.4).
    """
    import copy
    from reaction_agent.snapshot.builder import (
        compute_snapshot_hash, SnapshotEvidenceItem, SnapshotBuildError,
    )
    from scripts.run_p1_gate import _g09_item_strict, _g09_t10_fixture_config
    it = _g09_item_strict()
    # Attach an EMBEDDED ledger that disagrees with the external source_ledger.
    embedded = copy.deepcopy(it.source_ledger)
    embedded.unknowns.append("embedded_only_disagreement")
    it.reaction_evidence.source_reaction_ledger = embedded
    config = _g09_t10_fixture_config(os.path.join(tempfile.gettempdir(), "m41_snap"))
    caught = False
    evidence = ""
    try:
        compute_snapshot_hash(config, [it])
        evidence = "builder did NOT fail closed — built snapshot from inconsistent ledgers"
    except SnapshotBuildError as e:
        caught = True
        evidence = f"fail-closed SnapshotBuildError: {str(e)[:160]}"
    return {"mutation_id": "M41",
            "mutation": "embedded/external source ledgers disagree but snapshot builds strict",
            "expected": "builder fails closed (SnapshotBuildError), no strict snapshot",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": evidence, "caught": caught}


# =====================================================================
# Round 4 §12 — M42–M56
# M42–M55: strict eligibility cross-invariants that Round 3 left fail-open.
#   Each starts from a genuinely-strict baseline (_strict_inputs) and applies
#   ONE violating change; caught = engine no longer returns strict_eligible.
# M56: proves the Round-4 mandatory-node gate wiring is real — shadowing a
#   mandatory G08/G09 test file makes the corresponding Gate FAIL (never a
#   silent PASS on a shrunken collection). M56a=G08, M56b=G09.
# =====================================================================

def mutation_42_nonzero_element_delta_enters_strict() -> dict:
    from reaction_agent.schemas.ledger import ElementBalance
    def m(ev, ld, lins):
        # balanced ledger, but an element row reports a non-zero net delta
        ld.element_balance.append(
            ElementBalance(element="C", reactant_count=2, product_count=2, delta=1))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M42", "non-zero element delta on a balanced ledger enters strict", m)


def mutation_43_explicit_quarantine_enters_strict() -> dict:
    def m(ev, ld, lins):
        ev.quarantine = "curator_flagged_identity_uncertain"
        return ev, ld, lins
    return _strict_violation_mutation(
        "M43", "explicit ReactionEvidence.quarantine enters production strict", m)


def mutation_44_identity_ambiguity_set_enters_strict() -> dict:
    def m(ev, ld, lins):
        ev.ambiguity_sets.append({"set_id": "amb_1", "members": "r1|p1"})
        return ev, ld, lins
    return _strict_violation_mutation(
        "M44", "identity ambiguity set enters strict", m)


def mutation_45_embedded_external_lineage_conflict_enters_strict() -> dict:
    def m(ev, ld, lins):
        # embedded lineage id list disagrees with the external typed lineages
        ev.resolved_transformed_lineages = ["lin_conflicting"]
        return ev, ld, lins
    return _strict_violation_mutation(
        "M45", "embedded lineage id conflicts with external lineage enters strict", m)


def mutation_46_uncontrolled_direction_enters_strict() -> dict:
    def m(ev, ld, lins):
        ev.direction = "sideways"
        return ev, ld, lins
    return _strict_violation_mutation(
        "M46", "uncontrolled direction value 'sideways' enters strict", m)


def mutation_47_participant_low_mapped_fraction_enters_strict() -> dict:
    def m(ev, ld, lins):
        ev.participants[0].mapped_fraction = 0.25
        return ev, ld, lins
    return _strict_violation_mutation(
        "M47", "participant mapped_fraction 0.25 enters strict", m)


def mutation_48_dropped_formal_pair_uncovered_map_enters_strict() -> dict:
    def m(ev, ld, lins):
        # remove a real formal pair while the summary still claims full mapping
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs.pop()
        return ev, ld, lins
    return _strict_violation_mutation(
        "M48", "dropped formal pair (uncovered declared atom map) enters strict", m)


def mutation_49_reverse_collision_enters_strict() -> dict:
    def m(ev, ld, lins):
        # second reactant atom now targets the SAME product atom as the first
        pairs = ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs
        pairs[1].product_atom_map = 1
        return ev, ld, lins
    return _strict_violation_mutation(
        "M49", "two reactant atoms target one product atom (reverse collision) enters strict", m)


def mutation_50_added_atom_source_ghost_enters_strict() -> dict:
    from reaction_agent.schemas.ledger import AddedAtomSource
    def m(ev, ld, lins):
        ld.added_atom_sources.append(
            AddedAtomSource(atom_map_number=1, source_participant_id="ghost_src"))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M50", "AddedAtomSource ghost participant enters strict", m)


def mutation_51_role_assignment_ghost_enters_strict() -> dict:
    from reaction_agent.schemas.ledger import RoleAssignment
    from reaction_agent.schemas.common import ParticipantRole
    def m(ev, ld, lins):
        ld.role_assignments.append(
            RoleAssignment(participant_id="ghost_role",
                           role=ParticipantRole.transformed_substrate, score=0.9))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M51", "RoleAssignment ghost participant enters strict", m)


def mutation_52_stoichiometry_ghost_enters_strict() -> dict:
    from reaction_agent.schemas.ledger import StoichiometricEntry
    def m(ev, ld, lins):
        ld.stoichiometry.append(
            StoichiometricEntry(participant_id="ghost_stoich", coefficient=1, side="reactant"))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M52", "StoichiometricEntry ghost participant enters strict", m)


def mutation_53_formal_atom_transfer_ghost_enters_strict() -> dict:
    from reaction_agent.schemas.ledger import FormalAtomTransferAssignment
    def m(ev, ld, lins):
        ld.formal_atom_transfer_assignments.append(
            FormalAtomTransferAssignment(source_participant_id="ghost_fat",
                                         target_participant_id="p1"))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M53", "FormalAtomTransferAssignment ghost participant enters strict", m)


def mutation_54_generic_ledger_unknown_enters_strict() -> dict:
    def m(ev, ld, lins):
        ld.unknowns.append("identity_source_unknown")
        return ev, ld, lins
    return _strict_violation_mutation(
        "M54", "generic ledger unknown enters strict", m)


def mutation_55_duplicate_lineage_enters_strict() -> dict:
    import copy
    def m(ev, ld, lins):
        lins.append(copy.deepcopy(lins[0]))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M55", "duplicate lineage id/content enters strict", m)


def mutation_56_gate_wiring_protects_mandatory_tests() -> dict:
    """M56: shadowing a MANDATORY gate test file makes the corresponding Gate
    FAIL (proves the Round-4 mandatory-node wiring is real — deleting/renaming
    a required strict/complete-evidence node is caught, never a silent PASS on
    a shrunken collection). Reversible: the file content is restored in finally.

    M56a: G08 mandatory cross-invariant test node missing  -> G08 FAIL
    M56b: G09 mandatory complete-evidence test node missing -> G09 FAIL
    M56c: G08 mandatory Round-5 reference-integrity node missing -> G08 FAIL
    M56d: G08 mandatory Round-6 node missing (single function removed) -> G08 FAIL
    M56e: G08 mandatory Round-7 node missing (single function removed) -> G08 FAIL
    M56f: G08 Round-8 production-partition node missing -> G08 FAIL
    M56g: G09 Round-8 diagnostic-integrity node missing -> G09 FAIL
    M56h: G09 Round-9 manifest-required-field node missing -> G09 FAIL
    M56i: G09 Round-9 snapshot-identity node missing -> G09 FAIL
    M56j: G09 Round-10 record_count boolean mandatory node missing -> G09 FAIL
    M56k: G09 Round-10 build_status required/type mandatory node missing -> G09 FAIL
    M56l: G09 Round-10 reconstructed-return mandatory node missing -> G09 FAIL
    """
    def _prove(sub_id, rel_file, check_fn, gate_id):
        abs_file = os.path.join(DEMOV2_ROOT, rel_file)
        if not os.path.isfile(abs_file):
            return {"mutation_id": sub_id,
                    "mutation": f"{gate_id} mandatory test file shadowed ({rel_file})",
                    "expected": f"{gate_id} FAIL (mandatory node not collected)",
                    "actual_passed": False, "actual_blocked": False,
                    "evidence": f"SETUP ERROR: baseline mandatory file absent: {rel_file}",
                    "caught": False}
        with open(abs_file) as f:
            original = f.read()
        caught = False
        evidence = ""
        try:
            # shadow: a collectable module that no longer defines the mandatory nodes
            with open(abs_file, "w") as f:
                f.write("def test_m56_shadow_placeholder():\n    assert True\n")
            result = check_fn()
            impl = result.get("implementation_failures", [])
            node_hits = sum(1 for x in impl
                            if "MANDATORY test node not collected" in x)
            caught = (not result.get("passed")) and node_hits > 0
            evidence = (f"{gate_id} passed={result.get('passed')} "
                        f"mandatory_node_missing_hits={node_hits}: "
                        f"{'; '.join(impl)[:200]}")
        finally:
            with open(abs_file, "w") as f:
                f.write(original)
        return {"mutation_id": sub_id,
                "mutation": f"{gate_id} mandatory test file shadowed ({rel_file})",
                "expected": f"{gate_id} FAIL (mandatory node not collected)",
                "actual_passed": caught, "actual_blocked": False,
                "evidence": evidence, "caught": caught}

    def _prove_single_node_removed(sub_id: str, rel_file: str, func_name: str,
                                   check_fn, gate_id: str) -> dict:
        """Remove ONE test function from a mandatory test file and prove the
        corresponding Gate FAILs (Round 6 §14.8: deleting a single Round-6 node
        is caught, not just whole-file shadowing). Reversible via finally."""
        abs_file = os.path.join(DEMOV2_ROOT, rel_file)
        if not os.path.isfile(abs_file):
            return {"mutation_id": sub_id,
                    "mutation": f"{gate_id} single node removed ({func_name})",
                    "expected": f"{gate_id} FAIL (mandatory node not collected)",
                    "actual_passed": False, "actual_blocked": False,
                    "evidence": f"SETUP ERROR: baseline mandatory file absent: {rel_file}",
                    "caught": False}
        with open(abs_file) as f:
            original = f.read()
        caught = False
        evidence = ""
        try:
            lines = original.splitlines()
            out: list[str] = []
            skipping = False
            for line in lines:
                if line.startswith(f"def {func_name}("):
                    skipping = True
                    continue
                if skipping and line.startswith("def "):
                    skipping = False
                if not skipping:
                    out.append(line)
            modified = "\n".join(out)
            if modified == original:
                return {"mutation_id": sub_id,
                        "mutation": f"{gate_id} single node removed ({func_name})",
                        "expected": f"{gate_id} FAIL (mandatory node not collected)",
                        "actual_passed": False, "actual_blocked": False,
                        "evidence": f"SETUP ERROR: function {func_name} not found in {rel_file}",
                        "caught": False}
            with open(abs_file, "w") as f:
                f.write(modified)
            result = check_fn()
            impl = result.get("implementation_failures", [])
            node_hits = sum(1 for x in impl if "MANDATORY test node not collected" in x)
            caught = (not result.get("passed")) and node_hits > 0
            evidence = (f"{gate_id} passed={result.get('passed')} "
                        f"mandatory_node_missing_hits={node_hits}: "
                        f"{'; '.join(impl)[:200]}")
        finally:
            with open(abs_file, "w") as f:
                f.write(original)
        return {"mutation_id": sub_id,
                "mutation": f"{gate_id} single node removed ({func_name})",
                "expected": f"{gate_id} FAIL (mandatory node not collected)",
                "actual_passed": caught, "actual_blocked": False,
                "evidence": evidence, "caught": caught}

    a = _prove("M56a", gate_mod._G08_CROSS_INVARIANT_FILE,
               check_g08_eligibility_quarantine, "P1-G08")
    b = _prove("M56b", gate_mod._G09_COMPLETE_EVIDENCE_FILE,
               check_g09_snapshot_reproducibility, "P1-G09")
    c = _prove("M56c", gate_mod._G08_REFERENCE_INTEGRITY_FILE,
               check_g08_eligibility_quarantine, "P1-G08")
    # Round 6 §14.8: removing a SINGLE Round-6 mandatory node (not the whole
    # file) must also make G08 FAIL.
    d = _prove_single_node_removed(
        "M56d", gate_mod._G08_REFERENCE_INTEGRITY_FILE,
        "test_uncontrolled_cofactor_direction_never_strict",
        check_g08_eligibility_quarantine, "P1-G08")
    # Round 7 §14.8: deleting a SINGLE Round-7 mandatory node must also FAIL G08.
    e = _prove_single_node_removed(
        "M56e", gate_mod._G08_REFERENCE_INTEGRITY_FILE,
        "test_heavy_atom_map_count_underflow_never_strict",
        check_g08_eligibility_quarantine, "P1-G08")
    # Round 8 §13: deleting a Round-8 G08 production-partition node must FAIL G08,
    # and deleting a Round-8 G09 diagnostic-integrity node must FAIL G09.
    f = _prove_single_node_removed(
        "M56f", gate_mod._G08_INDEX_PARTITION_FILE,
        "test_loader_rejects_hash_coherent_diagnostic_in_production",
        check_g08_eligibility_quarantine, "P1-G08")
    g = _prove_single_node_removed(
        "M56g", gate_mod._G09_INDEX_PARTITION_FILE,
        "test_snapshot_manifest_persists_diagnostic_index_hash",
        check_g09_snapshot_reproducibility, "P1-G09")
    # Round 9 §10: deleting a Round-9 manifest-required-field node or a
    # snapshot-identity node must also FAIL G09.
    h = _prove_single_node_removed(
        "M56h", gate_mod._G09_INDEX_PARTITION_FILE,
        "test_loader_rejects_missing_manifest_diagnostic_index_hash",
        check_g09_snapshot_reproducibility, "P1-G09")
    i = _prove_single_node_removed(
        "M56i", gate_mod._G09_INDEX_PARTITION_FILE,
        "test_loader_rejects_snapshot_identity_mismatch",
        check_g09_snapshot_reproducibility, "P1-G09")
    # Round 10: deleting a Round-10 manifest type-authority node must also
    # FAIL G09. M56j deletes the record_count boolean node, M56k the
    # build_status required/type node, M56l the reconstructed-return node —
    # the three Round-10 protection families the task book (§4) requires.
    j = _prove_single_node_removed(
        "M56j", gate_mod._G09_MANIFEST_AUTHORITY_FILE,
        "test_loader_rejects_manifest_record_count_bool",
        check_g09_snapshot_reproducibility, "P1-G09")
    k = _prove_single_node_removed(
        "M56k", gate_mod._G09_MANIFEST_AUTHORITY_FILE,
        "test_loader_rejects_missing_manifest_build_status",
        check_g09_snapshot_reproducibility, "P1-G09")
    l = _prove_single_node_removed(
        "M56l", gate_mod._G09_MANIFEST_AUTHORITY_FILE,
        "test_loader_returns_recomputed_manifest_counts",
        check_g09_snapshot_reproducibility, "P1-G09")
    caught = (a["caught"] and b["caught"] and c["caught"] and d["caught"]
              and e["caught"] and f["caught"] and g["caught"]
              and h["caught"] and i["caught"]
              and j["caught"] and k["caught"] and l["caught"])
    return {"mutation_id": "M56",
            "mutation": "remove/shadow G08/G09 mandatory test node -> corresponding Gate FAIL",
            "expected": "G08 and G09 FAIL when their mandatory test node is missing "
                        "(incl. Round-5 reference-integrity + single Round-6 node + "
                        "single Round-7 node + Round-8 production-partition + "
                        "Round-8 diagnostic-integrity + Round-9 manifest-required-field "
                        "+ Round-9 snapshot-identity node + Round-10 record_count-bool "
                        "+ Round-10 build_status + Round-10 reconstructed-return node)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": (f"M56a={a['caught']} M56b={b['caught']} M56c={c['caught']} "
                         f"M56d={d['caught']} M56e={e['caught']} "
                         f"M56f={f['caught']} M56g={g['caught']} "
                         f"M56h={h['caught']} M56i={i['caught']} "
                         f"M56j={j['caught']} M56k={k['caught']} M56l={l['caught']}"),
            "caught": caught,
            "sub_results": [a, b, c, d, e, f, g, h, i, j, k, l]}


# =====================================================================
# Round 5 §12 — M57–M72
# Each starts from a genuinely-strict baseline and applies ONE violating
# change; caught = the engine no longer returns strict_eligible (or routes to
# the correct lane). M57/M72 also verify the PUBLIC build_snapshot records
# lane is non-strict (proves the public API cannot bypass the boundary §6.2).
# M56c (above) proves the Round-5 G08 mandatory nodes are deletion-protected.
# =====================================================================

def _strict_public_dual(mid: str, desc: str, mutate_item) -> dict:
    """Apply ONE mutation to a genuine strict baseline item; caught = the
    direct ``decide_eligibility`` is not strict AND the public
    ``build_snapshot`` records.jsonl lane is not strict."""
    import json
    import os
    import tempfile

    from reaction_agent.eligibility.engine import decide_eligibility
    from reaction_agent.schemas.common import EligibilityStatus
    from reaction_agent.snapshot.builder import build_snapshot
    from scripts.run_p1_gate import _g09_item_strict, _g09_t10_fixture_config

    if not _assert_baseline_strict():
        return {"mutation_id": mid, "mutation": desc,
                "expected": "non-strict direct + non-strict public lane",
                "actual_passed": False, "actual_blocked": False,
                "evidence": "VACUOUS: baseline _strict_inputs is not strict_eligible",
                "caught": False}
    item = _g09_item_strict()
    mutate_item(item)
    ev, ld, lins = item.reaction_evidence, item.source_ledger, item.lineages
    d = decide_eligibility(ev, ld, lins)
    direct_caught = d.eligibility != EligibilityStatus.strict_eligible
    public_caught = False
    public_lane = "?"
    with tempfile.TemporaryDirectory(prefix="m_pub_") as td:
        cfg = _g09_t10_fixture_config(os.path.join(td, "snaps"))
        man = build_snapshot(cfg, iter([item]))
        snap_dir = os.path.join(cfg.output_snapshot_root, man.snapshot_id)
        with open(os.path.join(snap_dir, "records.jsonl")) as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec["reaction_evidence"]["reaction_id"] == ev.reaction_id:
                    public_lane = rec["lane"]
                    public_caught = rec["lane"] != "strict"
                    break
    caught = direct_caught and public_caught
    return {"mutation_id": mid, "mutation": desc,
            "expected": "decide_eligibility non-strict AND public records lane non-strict",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": (f"direct_eligibility={d.eligibility.value} "
                         f"public_lane={public_lane!r} reason={d.reason[:120]}"),
            "caught": caught}


def mutation_57_added_atom_source_unknown_map_enters_strict() -> dict:
    """M57: AddedAtomSource references an EXISTING participant but an unknown
    atom map → never strict; public records lane not strict."""
    from reaction_agent.schemas.ledger import AddedAtomSource
    def m(ev, ld, lins):
        ld.added_atom_sources.append(
            AddedAtomSource(atom_map_number=999, source_participant_id="r1"))
        return ev, ld, lins
    def m_item(item):
        from reaction_agent.schemas.ledger import AddedAtomSource
        item.source_ledger.added_atom_sources.append(
            AddedAtomSource(atom_map_number=999, source_participant_id="r1"))
    direct = _strict_violation_mutation(
        "M57a", "AddedAtomSource existing participant + unknown map enters strict", m)
    public = _strict_public_dual(
        "M57b", "AddedAtomSource existing participant + unknown map via public API", m_item)
    caught = direct["caught"] and public["caught"]
    return {"mutation_id": "M57",
            "mutation": "AddedAtomSource participant exists but atom map missing enters strict",
            "expected": "never strict (direct) AND public records lane != strict",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M57a caught={direct['caught']}; M57b caught={public['caught']}",
            "caught": caught, "sub_results": [direct, public]}


def mutation_58_reactant_entry_ghost_enters_strict() -> dict:
    """M58: reactant_entries ghost participant → never strict."""
    from reaction_agent.schemas.ledger import StoichiometricEntry
    def m(ev, ld, lins):
        ld.reactant_entries.append(
            StoichiometricEntry(participant_id="ghost_r", coefficient=1, side="reactant"))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M58", "reactant_entries ghost participant enters strict", m)


def mutation_59_product_entry_ghost_enters_strict() -> dict:
    """M59: product_entries ghost participant → never strict."""
    from reaction_agent.schemas.ledger import StoichiometricEntry
    def m(ev, ld, lins):
        ld.product_entries.append(
            StoichiometricEntry(participant_id="ghost_p", coefficient=1, side="product"))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M59", "product_entries ghost participant enters strict", m)


def mutation_60_stoichiometry_role_conflicts_enter_strict() -> dict:
    """M60: stoichiometry wrong-side / coefficient<=0 / contradictory role
    assignment → never strict (M60a/M60b/M60c)."""
    from reaction_agent.schemas.common import ParticipantRole
    from reaction_agent.schemas.ledger import RoleAssignment, StoichiometricEntry
    def m_a(ev, ld, lins):
        ld.stoichiometry.append(
            StoichiometricEntry(participant_id="r1", coefficient=1, side="product"))
        return ev, ld, lins
    def m_b(ev, ld, lins):
        ld.stoichiometry.append(
            StoichiometricEntry(participant_id="r1", coefficient=-2, side="reactant"))
        return ev, ld, lins
    def m_c(ev, ld, lins):
        ld.role_assignments.append(
            RoleAssignment(participant_id="r1", role=ParticipantRole.cofactor, score=0.9))
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M60a", "stoichiometry wrong-side enters strict", m_a)
    b = _strict_violation_mutation(
        "M60b", "stoichiometry coefficient<=0 enters strict", m_b)
    c = _strict_violation_mutation(
        "M60c", "contradictory role assignment enters strict", m_c)
    caught = a["caught"] and b["caught"] and c["caught"]
    return {"mutation_id": "M60",
            "mutation": "stoichiometry wrong-side / coefficient<=0 / contradictory role assignment enters strict",
            "expected": "never strict (all three)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": (f"M60a={a['caught']} M60b={b['caught']} M60c={c['caught']}"),
            "caught": caught, "sub_results": [a, b, c]}


def mutation_61_formal_transfer_reversed_sides_enters_strict() -> dict:
    """M61: FormalAtomTransfer endpoints EXIST but sides reversed → never strict."""
    from reaction_agent.schemas.ledger import FormalAtomTransferAssignment
    def m(ev, ld, lins):
        ld.formal_atom_transfer_assignments.append(
            FormalAtomTransferAssignment(source_participant_id="p1",
                                         target_participant_id="r1",
                                         transferred_atom_map_numbers=[999]))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M61", "FormalAtomTransfer endpoints exist but sides reversed enters strict", m)


def mutation_62_formal_transfer_map_conflicts_enter_strict() -> dict:
    """M62: FormalAtomTransfer transferred map missing / conflicting with
    formal pairs → never strict (M62a/M62b)."""
    from reaction_agent.schemas.evidence import ReactionParticipant
    from reaction_agent.schemas.ledger import FormalAtomTransferAssignment
    from reaction_agent.schemas.mapping import FormalMappedAtomPair
    def m_a(ev, ld, lins):
        ld.formal_atom_transfer_assignments.append(
            FormalAtomTransferAssignment(source_participant_id="r1",
                                         target_participant_id="p1",
                                         transferred_atom_map_numbers=[999]))
        return ev, ld, lins
    def m_b(ev, ld, lins):
        # r2:3 is formally mapped ONLY onto p2; FAT r2→p1 transferring 3 is
        # unsupported by the formal r2→p1 edge (pair conflict).
        r2 = ReactionParticipant(participant_id="r2", molecule_id="mol_r2",
                                 canonical_smiles="O=O", side="reactant",
                                 atom_map_numbers=[3], mapped_fraction=1.0)
        p2 = ReactionParticipant(participant_id="p2", molecule_id="mol_p2",
                                 canonical_smiles="O=C=O", side="product",
                                 atom_map_numbers=[3], mapped_fraction=1.0)
        ev.participants.append(r2)
        ev.participants.append(p2)
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs.append(
            FormalMappedAtomPair(reactant_participant_id="r2", reactant_atom_map=3,
                                 product_participant_id="p2", product_atom_map=3))
        ld.formal_atom_transfer_assignments.append(
            FormalAtomTransferAssignment(source_participant_id="r2",
                                         target_participant_id="p1",
                                         transferred_atom_map_numbers=[3]))
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M62a", "FormalAtomTransfer unknown transferred map enters strict", m_a)
    b = _strict_violation_mutation(
        "M62b", "FormalAtomTransfer conflicts with formal pairs enters strict", m_b)
    caught = a["caught"] and b["caught"]
    return {"mutation_id": "M62",
            "mutation": "FormalAtomTransfer unknown/conflicting map enters strict",
            "expected": "never strict (both)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M62a={a['caught']} M62b={b['caught']}",
            "caught": caught, "sub_results": [a, b]}


def mutation_63_removed_atom_sink_ghost_enters_strict() -> dict:
    """M63: RemovedAtomSink ghost participant / unknown map → never strict
    (M63a/M63b)."""
    from reaction_agent.schemas.ledger import RemovedAtomSink
    def m_a(ev, ld, lins):
        ld.removed_atom_sinks.append(
            RemovedAtomSink(atom_map_number=1, sink_participant_id="ghost_sink"))
        return ev, ld, lins
    def m_b(ev, ld, lins):
        ld.removed_atom_sinks.append(
            RemovedAtomSink(atom_map_number=999, sink_participant_id="p1"))
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M63a", "RemovedAtomSink ghost participant enters strict", m_a)
    b = _strict_violation_mutation(
        "M63b", "RemovedAtomSink unknown map enters strict", m_b)
    caught = a["caught"] and b["caught"]
    return {"mutation_id": "M63",
            "mutation": "RemovedAtomSink ghost participant/map enters strict",
            "expected": "never strict (both)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M63a={a['caught']} M63b={b['caught']}",
            "caught": caught, "sub_results": [a, b]}


def mutation_64_cofactor_change_ghost_enters_strict() -> dict:
    """M64: CofactorChange ghost participant → never strict."""
    from reaction_agent.schemas.ledger import CofactorChange
    def m(ev, ld, lins):
        ld.cofactor_changes.append(CofactorChange(participant_id="ghost_cof", direction="oxidized"))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M64", "CofactorChange ghost participant enters strict", m)


def mutation_65_mechanistic_evidence_ghost_enters_strict() -> dict:
    """M65: MechanisticOriginEvidence ghost participant / unknown target map /
    dangling AddedAtomSource evidence linkage → never strict
    (M65a/M65b/M65c)."""
    from reaction_agent.schemas.ledger import (
        AddedAtomSource, MechanisticOriginEvidence)
    def m_a(ev, ld, lins):
        ld.mechanistic_origin_evidence.append(MechanisticOriginEvidence(
            evidence_id="mech_1", evidence_type="isotope_tracing",
            source_participant_id="ghost_mech", target_atom_map_numbers=[1]))
        return ev, ld, lins
    def m_b(ev, ld, lins):
        ld.mechanistic_origin_evidence.append(MechanisticOriginEvidence(
            evidence_id="mech_1", evidence_type="isotope_tracing",
            source_participant_id="r1", target_atom_map_numbers=[999]))
        return ev, ld, lins
    def m_c(ev, ld, lins):
        ld.added_atom_sources.append(AddedAtomSource(
            atom_map_number=1, source_participant_id="r1",
            mechanistic_evidence_id="mech_nonexistent"))
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M65a", "MechanisticOriginEvidence ghost participant enters strict", m_a)
    b = _strict_violation_mutation(
        "M65b", "MechanisticOriginEvidence unknown target map enters strict", m_b)
    c = _strict_violation_mutation(
        "M65c", "AddedAtomSource dangling mechanistic evidence linkage enters strict", m_c)
    caught = a["caught"] and b["caught"] and c["caught"]
    return {"mutation_id": "M65",
            "mutation": "MechanisticOriginEvidence ghost/map/dangling-linkage enters strict",
            "expected": "never strict (all three)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M65a={a['caught']} M65b={b['caught']} M65c={c['caught']}",
            "caught": caught, "sub_results": [a, b, c]}


def mutation_66_negative_element_count_enters_strict() -> dict:
    """M66: negative element counts → never strict (quarantined as a
    structural data contradiction)."""
    from reaction_agent.schemas.ledger import ElementBalance
    def m(ev, ld, lins):
        ld.element_balance.append(
            ElementBalance(element="C", reactant_count=-1, product_count=1, delta=2))
        return ev, ld, lins
    return _strict_violation_mutation(
        "M66", "negative element counts enter strict", m)


def mutation_67_partial_consistent_delta_mislabeled() -> dict:
    """M67: partial ledger with a CONSISTENT non-zero delta must NOT be
    quarantined as a 'fully-balanced contradiction' and must NOT be strict."""
    from reaction_agent.eligibility.engine import decide_eligibility
    from reaction_agent.schemas.common import (
        EligibilityStatus, LedgerBalanceStatus)
    from reaction_agent.schemas.ledger import ElementBalance
    if not _assert_baseline_strict():
        return {"mutation_id": "M67",
                "mutation": "partial ledger consistent non-zero delta mislabeled",
                "expected": "non-strict + non-quarantine + honest reason",
                "actual_passed": False, "actual_blocked": False,
                "evidence": "VACUOUS: baseline _strict_inputs is not strict_eligible",
                "caught": False}
    ev, ld, lins = _strict_inputs()
    ld.balance_status = LedgerBalanceStatus.partial_or_unbalanced_source
    ld.element_balance.append(
        ElementBalance(element="C", reactant_count=2, product_count=3, delta=1))
    d = decide_eligibility(ev, ld, lins)
    not_strict = d.eligibility != EligibilityStatus.strict_eligible
    not_quarantined = d.eligibility != EligibilityStatus.quarantine
    not_mislabeled = "fully_balanced" not in d.reason
    caught = not_strict and not_quarantined and not_mislabeled
    return {"mutation_id": "M67",
            "mutation": "partial ledger consistent non-zero delta mislabeled as fully-balanced contradiction",
            "expected": "non-strict AND non-quarantine AND reason not claiming fully-balanced",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"eligibility={d.eligibility.value} reason={d.reason[:140]}",
            "caught": caught}


def mutation_68_participant_map_duplicate_enters_strict() -> dict:
    """M68: within-participant duplicate atom map (self-report uniqueness=True
    cannot override content) → never strict."""
    def m(ev, ld, lins):
        ev.participants[0].atom_map_numbers = [1, 1, 2]
        return ev, ld, lins
    return _strict_violation_mutation(
        "M68", "within-participant duplicate atom map enters strict", m)


def mutation_69_same_side_map_collision_enters_strict() -> dict:
    """M69: same-side cross-participant atom map collision → never strict."""
    from reaction_agent.schemas.evidence import ReactionParticipant
    def m(ev, ld, lins):
        r2 = ReactionParticipant(participant_id="r2", molecule_id="mol_r2",
                                 canonical_smiles="OO", side="reactant",
                                 atom_map_numbers=[1, 2], mapped_fraction=1.0)
        ev.participants.append(r2)
        return ev, ld, lins
    return _strict_violation_mutation(
        "M69", "same-side cross-participant atom map collision enters strict", m)


def mutation_70_duplicate_id_or_uncontrolled_side_enters_strict() -> dict:
    """M70: duplicate participant ID / uncontrolled participant side → never
    strict (M70a/M70b)."""
    from reaction_agent.schemas.evidence import ReactionParticipant
    def m_a(ev, ld, lins):
        r1b = ReactionParticipant(participant_id="r1", molecule_id="mol_r1b",
                                  canonical_smiles="CCN", side="reactant",
                                  atom_map_numbers=[3, 4], mapped_fraction=1.0)
        ev.participants.append(r1b)
        return ev, ld, lins
    def m_b(ev, ld, lins):
        m1 = ReactionParticipant(participant_id="m1", molecule_id="mol_m1",
                                 canonical_smiles="CCC", side="middle",
                                 atom_map_numbers=[], mapped_fraction=1.0)
        ev.participants.append(m1)
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M70a", "duplicate participant ID enters strict", m_a)
    b = _strict_violation_mutation(
        "M70b", "uncontrolled participant side enters strict", m_b)
    caught = a["caught"] and b["caught"]
    return {"mutation_id": "M70",
            "mutation": "duplicate participant ID / uncontrolled participant side enters strict",
            "expected": "never strict (both)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M70a={a['caught']} M70b={b['caught']}",
            "caught": caught, "sub_results": [a, b]}


def mutation_71_duplicate_embedded_lineage_ids_enters_strict() -> dict:
    """M71: duplicate embedded lineage IDs (set-consistent with external) →
    never strict."""
    def m(ev, ld, lins):
        ev.resolved_transformed_lineages = ["lin_r1_p1", "lin_r1_p1"]
        return ev, ld, lins
    return _strict_violation_mutation(
        "M71", "duplicate embedded lineage IDs enter strict", m)


def mutation_72_reordered_map_duplicate_lineage_enters_strict() -> dict:
    """M72: reordered-map semantic duplicate lineage → never strict; public
    records lane not strict (M72a/M72b)."""
    from reaction_agent.schemas.common import LineageResolutionQuality
    from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
    def m(ev, ld, lins):
        lins.append(ResolvedTransformedLineage(
            lineage_id="lin_r1_p1_b", reactant_participant_id="r1",
            product_participant_id="p1", ambiguity="none",
            transformed_atom_maps=[2, 1],
            resolution_quality=LineageResolutionQuality.resolved,
            evidence_ids=["lin_ev_1"]))
        return ev, ld, lins
    def m_item(item):
        from reaction_agent.schemas.common import LineageResolutionQuality
        from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
        item.lineages.append(ResolvedTransformedLineage(
            lineage_id="lin_r1_p1_b", reactant_participant_id="r1",
            product_participant_id="p1", ambiguity="none",
            transformed_atom_maps=[2, 1],
            resolution_quality=LineageResolutionQuality.resolved,
            evidence_ids=["lin_ev_1"]))
    direct = _strict_violation_mutation(
        "M72a", "reordered-map semantic duplicate lineage enters strict", m)
    public = _strict_public_dual(
        "M72b", "reordered-map semantic duplicate lineage via public API", m_item)
    caught = direct["caught"] and public["caught"]
    return {"mutation_id": "M72",
            "mutation": "reordered-map semantic duplicate lineage enters strict (direct + public)",
            "expected": "never strict (direct) AND public records lane != strict",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M72a caught={direct['caught']}; M72b caught={public['caught']}",
            "caught": caught, "sub_results": [direct, public]}


# =====================================================================
# Round 6 §15 — M73–M77
# Each starts from a genuinely-strict baseline and applies ONE confirmed
# Round-6 fail-open; caught = the engine no longer returns strict_eligible
# via the target invariant reason (and the public records lane is non-strict
# where the table requires it).
# =====================================================================

def mutation_73_uncontrolled_cofactor_direction_enters_strict() -> dict:
    """M73: an EXISTING cofactor participant with an uncontrolled direction
    must never be strict (direct + public)."""
    from reaction_agent.schemas.ledger import CofactorChange
    def m(ev, ld, lins):
        ld.cofactor_changes.append(
            CofactorChange(participant_id="r1", direction="sideways"))
        return ev, ld, lins
    def m_item(item):
        from reaction_agent.schemas.ledger import CofactorChange
        item.source_ledger.cofactor_changes.append(
            CofactorChange(participant_id="r1", direction="sideways"))
    direct = _strict_violation_mutation(
        "M73a", "existing cofactor participant + uncontrolled direction enters strict", m)
    public = _strict_public_dual(
        "M73b", "existing cofactor participant + uncontrolled direction via public API", m_item)
    caught = direct["caught"] and public["caught"]
    return {"mutation_id": "M73",
            "mutation": "existing cofactor participant + uncontrolled direction enters strict",
            "expected": "never strict (direct) AND public records lane != strict",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M73a={direct['caught']} M73b={public['caught']}",
            "caught": caught, "sub_results": [direct, public]}


def mutation_74_stoich_authority_conflicts_enter_strict() -> dict:
    """M74: same participant/side with duplicate/conflicting coefficients in
    reactant_entries / product_entries / stoichiometry → never strict
    (M74a/M74b/M74c)."""
    from reaction_agent.schemas.ledger import StoichiometricEntry
    def m_a(ev, ld, lins):
        ld.reactant_entries.extend([
            StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
            StoichiometricEntry(participant_id="r1", coefficient=2, side="reactant")])
        return ev, ld, lins
    def m_b(ev, ld, lins):
        ld.product_entries.extend([
            StoichiometricEntry(participant_id="p1", coefficient=1, side="product"),
            StoichiometricEntry(participant_id="p1", coefficient=2, side="product")])
        return ev, ld, lins
    def m_c(ev, ld, lins):
        ld.stoichiometry.extend([
            StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
            StoichiometricEntry(participant_id="r1", coefficient=2, side="reactant")])
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M74a", "conflicting reactant entry coefficients enter strict", m_a)
    b = _strict_violation_mutation(
        "M74b", "conflicting product entry coefficients enter strict", m_b)
    c = _strict_violation_mutation(
        "M74c", "conflicting stoichiometry coefficients enter strict", m_c)
    caught = a["caught"] and b["caught"] and c["caught"]
    return {"mutation_id": "M74",
            "mutation": "same participant/side duplicate/conflicting coefficients enter strict",
            "expected": "never strict (all three collections)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M74a={a['caught']} M74b={b['caught']} M74c={c['caught']}",
            "caught": caught, "sub_results": [a, b, c]}


def mutation_75_mechanistic_reactant_only_target_enters_strict() -> dict:
    """M75: mechanistic target map exists ONLY on the reactant side — must be
    caught by the PRODUCT-side map registry, not a global map union."""
    from reaction_agent.eligibility.engine import decide_eligibility
    from reaction_agent.schemas.common import (
        EligibilityStatus, LedgerBalanceStatus, LineageResolutionQuality,
        MappingQualityClass, MappingStatus, ParticipantRole, SourceAssignmentMethod)
    from reaction_agent.schemas.evidence import ReactionEvidence, ReactionParticipant
    from reaction_agent.schemas.ledger import (
        MechanisticOriginEvidence, RoleAssignment, SourceReactionLedger)
    from reaction_agent.schemas.mapping import (
        FormalMappedAtomPair, FormalSourceAssignment, MappingReport)
    from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage

    def build():
        # r1=CCO (3 heavy, 3 maps) and p1=CCN (3 heavy, 3 maps) are heavy-atom
        # consistent; map 3 exists ONLY on the reactant side.
        r1 = ReactionParticipant(participant_id="r1", molecule_id="mol_r1",
                                 canonical_smiles="CCO", side="reactant",
                                 atom_map_numbers=[1, 2, 3], mapped_fraction=1.0)
        p1 = ReactionParticipant(participant_id="p1", molecule_id="mol_p1",
                                 canonical_smiles="CCN", side="product",
                                 atom_map_numbers=[1, 2, 4], mapped_fraction=1.0)
        mr = MappingReport(
            mapper_name="fake", mapper_version="v1", mapper_parameters={},
            input_hash="i", output_hash="o", mapping_status=MappingStatus.fully_mapped,
            mapped_heavy_atom_fraction=1.0, map_number_uniqueness=True, changed_atom_coverage=1.0,
            formal_mapped_source_assignment=FormalSourceAssignment(
                mapper_name="fake", mapper_version="v1",
                mapped_atom_pairs=[
                    FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1, product_participant_id="p1", product_atom_map=1),
                    FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=2, product_participant_id="p1", product_atom_map=2),
                    FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=3, product_participant_id="p1", product_atom_map=4)],
                assignment_method=SourceAssignmentMethod.formal_mapped,
                assignment_quality=MappingQualityClass.high_quality, assignment_ambiguity=False),
            fallback_method=None)
        ev = ReactionEvidence(reaction_id="rxn_m75", source_record_id="src_m75", source_name="s",
                              source_version="v1", raw_reaction="A>>B", normalized_reaction="A>>B",
                              direction="forward", participants=[r1, p1], mapping_report=mr,
                              provenance=["rxn_prov_a"])
        ld = SourceReactionLedger(
            ledger_id="srl_m75", reaction_evidence_id="rxn_m75",
            balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction, charge_balance=0,
            role_assignments=[
                RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
                RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9)],
            source_completeness="complete", mapping_completeness="complete",
            hydrogen_policy="explicit", proton_policy="explicit", electron_policy="explicit")
        lins = [ResolvedTransformedLineage(lineage_id="lin_r1_p1", reactant_participant_id="r1",
                                           product_participant_id="p1", ambiguity="none",
                                           transformed_atom_maps=[1, 2, 3],
                                           resolution_quality=LineageResolutionQuality.resolved,
                                           evidence_ids=["lin_ev_1"])]
        return ev, ld, lins

    ev, ld, lins = build()
    baseline = decide_eligibility(ev, ld, lins)
    if baseline.eligibility != EligibilityStatus.strict_eligible:
        return {"mutation_id": "M75",
                "mutation": "mechanistic reactant-only target map enters strict",
                "expected": "caught by product-side map registry",
                "actual_passed": False, "actual_blocked": False,
                "evidence": f"VACUOUS: baseline not strict ({baseline.eligibility.value})",
                "caught": False}
    ld.mechanistic_origin_evidence.append(MechanisticOriginEvidence(
        evidence_id="me_r_only", evidence_type="isotope_tracing",
        source_participant_id="r1", target_atom_map_numbers=[3]))
    d = decide_eligibility(ev, ld, lins)
    caught = (d.eligibility != EligibilityStatus.strict_eligible
              and "mechanistic_evidence_map_product_side" in d.reason)
    return {"mutation_id": "M75",
            "mutation": "mechanistic reactant-only target map enters strict",
            "expected": "never strict via product-side map registry",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"eligibility={d.eligibility.value} reason={d.reason[:120]}",
            "caught": caught}


def mutation_76_empty_or_duplicate_formal_transfer_enters_strict() -> dict:
    """M76: FAT with empty / duplicate transferred maps must never be strict
    (M76a/M76b) and the public lane must not be strict (M76c)."""
    from reaction_agent.schemas.ledger import FormalAtomTransferAssignment
    def m_a(ev, ld, lins):
        ld.formal_atom_transfer_assignments.append(
            FormalAtomTransferAssignment(source_participant_id="r1", target_participant_id="p1"))
        return ev, ld, lins
    def m_b(ev, ld, lins):
        ld.formal_atom_transfer_assignments.append(
            FormalAtomTransferAssignment(source_participant_id="r1", target_participant_id="p1",
                                         transferred_atom_map_numbers=[1, 1]))
        return ev, ld, lins
    def m_item(item):
        from reaction_agent.schemas.ledger import FormalAtomTransferAssignment
        item.source_ledger.formal_atom_transfer_assignments.append(
            FormalAtomTransferAssignment(source_participant_id="r1", target_participant_id="p1"))
    a = _strict_violation_mutation(
        "M76a", "empty formal transfer maps enter strict", m_a)
    b = _strict_violation_mutation(
        "M76b", "duplicate formal transfer maps enter strict", m_b)
    public = _strict_public_dual(
        "M76c", "empty formal transfer via public API", m_item)
    caught = a["caught"] and b["caught"] and public["caught"]
    return {"mutation_id": "M76",
            "mutation": "empty/duplicate formal transfer assignment enters strict",
            "expected": "never strict (direct) AND public records lane != strict",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M76a={a['caught']} M76b={b['caught']} M76c={public['caught']}",
            "caught": caught, "sub_results": [a, b, public]}


def mutation_77_heavy_atom_empty_maps_enters_strict() -> dict:
    """M77: a heavy-atom participant with empty atom maps and mapped_fraction
    =1.0 must never be strict (direct + public)."""
    from reaction_agent.schemas.evidence import ReactionParticipant
    def m(ev, ld, lins):
        ev.participants.append(ReactionParticipant(
            participant_id="x1", molecule_id="mol_x1", canonical_smiles="CC",
            side="reactant", atom_map_numbers=[], mapped_fraction=1.0))
        return ev, ld, lins
    def m_item(item):
        from reaction_agent.schemas.evidence import ReactionParticipant
        item.reaction_evidence.participants.append(ReactionParticipant(
            participant_id="x1", molecule_id="mol_x1", canonical_smiles="CC",
            side="reactant", atom_map_numbers=[], mapped_fraction=1.0))
    direct = _strict_violation_mutation(
        "M77a", "heavy-atom participant empty maps + mf=1.0 enters strict", m)
    public = _strict_public_dual(
        "M77b", "heavy-atom participant empty maps via public API", m_item)
    caught = direct["caught"] and public["caught"]
    return {"mutation_id": "M77",
            "mutation": "heavy-atom participant with empty maps + mapped_fraction=1.0 enters strict",
            "expected": "never strict (direct) AND public records lane != strict",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M77a={direct['caught']} M77b={public['caught']}",
            "caught": caught, "sub_results": [direct, public]}


# =====================================================================
# Round 7 §15 — M78–M83
# M78 heavy-atom map count underflow/overflow (never strict; public non-production)
# M79 map IDs 0/negative (never strict; public non-production)
# M80 duplicate/conflicting AddedAtomSource/RemovedAtomSink (never strict)
# M81 duplicate FAT / duplicate mechanistic target maps (never strict)
# M82 RemovedAtomSink formal_assignment=False (never strict; public non-production)
# M83 records diagnostic but wrongly injected into production index
#     (index-aware public boundary / G08 must FAIL — R7-06)
# =====================================================================

def _strict_public_index_dual(mid: str, desc: str, mutate_item) -> dict:
    """Like ``_strict_public_dual`` but ALSO verifies the record is NOT in the
    production index (R7-05 index-aware boundary). caught = direct non-strict
    AND public records lane != strict AND reaction_id not in production_index."""
    import json
    import os
    import tempfile

    from reaction_agent.eligibility.engine import decide_eligibility
    from reaction_agent.schemas.common import EligibilityStatus
    from reaction_agent.snapshot.builder import build_snapshot
    from scripts.run_p1_gate import _g09_item_strict, _g09_t10_fixture_config

    if not _assert_baseline_strict():
        return {"mutation_id": mid, "mutation": desc,
                "expected": "non-strict direct + non-strict public lane + non-production",
                "actual_passed": False, "actual_blocked": False,
                "evidence": "VACUOUS: baseline _strict_inputs is not strict_eligible",
                "caught": False}
    item = _g09_item_strict()
    mutate_item(item)
    ev, ld, lins = item.reaction_evidence, item.source_ledger, item.lineages
    d = decide_eligibility(ev, ld, lins)
    direct_caught = d.eligibility != EligibilityStatus.strict_eligible
    public_lane = "?"
    in_production = True
    with tempfile.TemporaryDirectory(prefix="m_pubidx_") as td:
        cfg = _g09_t10_fixture_config(os.path.join(td, "snaps"))
        man = build_snapshot(cfg, iter([item]))
        snap_dir = os.path.join(cfg.output_snapshot_root, man.snapshot_id)
        with open(os.path.join(snap_dir, "records.jsonl")) as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec["reaction_evidence"]["reaction_id"] == ev.reaction_id:
                    public_lane = rec["lane"]
                    break
        prod_ids: list[str] = []
        with open(os.path.join(snap_dir, "production_index.jsonl")) as f:
            for line in f:
                if not line.strip():
                    continue
                prod_ids.append(json.loads(line)["reaction_evidence"]["reaction_id"])
        in_production = ev.reaction_id in prod_ids
    caught = direct_caught and (public_lane != "strict") and not in_production
    return {"mutation_id": mid, "mutation": desc,
            "expected": "non-strict direct AND non-strict public lane AND non-production",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": (f"direct_eligibility={d.eligibility.value} "
                         f"public_lane={public_lane!r} in_production={in_production} "
                         f"reason={d.reason[:120]}"),
            "caught": caught}


def mutation_78_heavy_map_count_mismatch_enters_strict() -> dict:
    """M78: heavy-atom map count underflow/overflow must never be strict
    (M78a underflow direct / M78b overflow direct / M78c underflow public /
    M78d overflow public)."""
    from reaction_agent.schemas.evidence import ReactionParticipant
    from reaction_agent.schemas.mapping import FormalMappedAtomPair
    def m_under(ev, ld, lins):
        ev.participants[0].canonical_smiles = "CC"
        ev.participants[0].atom_map_numbers = [1]
        ev.participants[1].canonical_smiles = "CC"
        ev.participants[1].atom_map_numbers = [1]
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs = [
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1)]
        lins[0].transformed_atom_maps = [1]
        return ev, ld, lins
    def m_over(ev, ld, lins):
        ev.participants[0].canonical_smiles = "C"
        ev.participants[0].atom_map_numbers = [1, 2]
        ev.participants[1].canonical_smiles = "C"
        ev.participants[1].atom_map_numbers = [1, 2]
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs = [
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1),
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=2,
                                 product_participant_id="p1", product_atom_map=2)]
        return ev, ld, lins
    def m_under_item(item):
        item.reaction_evidence.participants[0].canonical_smiles = "CC"
        item.reaction_evidence.participants[0].atom_map_numbers = [1]
        item.reaction_evidence.participants[1].canonical_smiles = "CC"
        item.reaction_evidence.participants[1].atom_map_numbers = [1]
        item.reaction_evidence.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs = [
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1)]
        item.lineages[0].transformed_atom_maps = [1]
    def m_over_item(item):
        item.reaction_evidence.participants[0].canonical_smiles = "C"
        item.reaction_evidence.participants[0].atom_map_numbers = [1, 2]
        item.reaction_evidence.participants[1].canonical_smiles = "C"
        item.reaction_evidence.participants[1].atom_map_numbers = [1, 2]
        item.reaction_evidence.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs = [
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1),
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=2,
                                 product_participant_id="p1", product_atom_map=2)]
    a = _strict_violation_mutation(
        "M78a", "heavy-atom map-count underflow enters strict", m_under)
    b = _strict_violation_mutation(
        "M78b", "heavy-atom map-count overflow enters strict", m_over)
    c = _strict_public_index_dual(
        "M78c", "heavy-atom map-count underflow via public API", m_under_item)
    d = _strict_public_index_dual(
        "M78d", "heavy-atom map-count overflow via public API", m_over_item)
    caught = a["caught"] and b["caught"] and c["caught"] and d["caught"]
    return {"mutation_id": "M78",
            "mutation": "heavy-atom map count underflow/overflow enters strict (direct + public)",
            "expected": "never strict (direct) AND public lane != strict AND non-production",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M78a={a['caught']} M78b={b['caught']} M78c={c['caught']} M78d={d['caught']}",
            "caught": caught, "sub_results": [a, b, c, d]}


def mutation_79_nonpositive_map_ids_enter_strict() -> dict:
    """M79: atom map IDs containing 0/negative must never be strict
    (M79a zero / M79b negative / M79c public)."""
    from reaction_agent.schemas.mapping import FormalMappedAtomPair
    def m_zero(ev, ld, lins):
        ev.participants[0].atom_map_numbers = [0, 1]
        ev.participants[1].atom_map_numbers = [0, 1]
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs = [
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=0,
                                 product_participant_id="p1", product_atom_map=0),
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1)]
        lins[0].transformed_atom_maps = [0, 1]
        return ev, ld, lins
    def m_neg(ev, ld, lins):
        ev.participants[0].atom_map_numbers = [-1, 1]
        ev.participants[1].atom_map_numbers = [-1, 1]
        ev.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs = [
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=-1,
                                 product_participant_id="p1", product_atom_map=-1),
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1)]
        lins[0].transformed_atom_maps = [-1, 1]
        return ev, ld, lins
    def m_item(item):
        item.reaction_evidence.participants[0].atom_map_numbers = [0, 1]
        item.reaction_evidence.participants[1].atom_map_numbers = [0, 1]
        item.reaction_evidence.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs = [
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=0,
                                 product_participant_id="p1", product_atom_map=0),
            FormalMappedAtomPair(reactant_participant_id="r1", reactant_atom_map=1,
                                 product_participant_id="p1", product_atom_map=1)]
        item.lineages[0].transformed_atom_maps = [0, 1]
    a = _strict_violation_mutation(
        "M79a", "zero atom map identifier enters strict", m_zero)
    b = _strict_violation_mutation(
        "M79b", "negative atom map identifier enters strict", m_neg)
    c = _strict_public_index_dual(
        "M79c", "nonpositive atom maps via public API", m_item)
    caught = a["caught"] and b["caught"] and c["caught"]
    return {"mutation_id": "M79",
            "mutation": "atom map IDs containing 0/negative enter strict (direct + public)",
            "expected": "never strict (direct) AND public lane != strict AND non-production",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M79a={a['caught']} M79b={b['caught']} M79c={c['caught']}",
            "caught": caught, "sub_results": [a, b, c]}


def mutation_80_atom_source_sink_duplicates_enter_strict() -> dict:
    """M80: duplicate/conflicting AddedAtomSource / RemovedAtomSink must never
    be strict (M80a dup AAS / M80b conf AAS / M80c dup sink / M80d conf sink)."""
    from reaction_agent.schemas.ledger import AddedAtomSource, RemovedAtomSink
    src = AddedAtomSource(atom_map_number=1, source_participant_id="r1",
                          formal_assignment=True)
    sink = RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                           formal_assignment=True)
    def m_dup_aas(ev, ld, lins):
        ld.added_atom_sources.extend([src, src])
        return ev, ld, lins
    def m_conf_aas(ev, ld, lins):
        ld.added_atom_sources.extend([
            AddedAtomSource(atom_map_number=1, source_participant_id="r1",
                            formal_assignment=True),
            AddedAtomSource(atom_map_number=1, source_participant_id="p1",
                            formal_assignment=True)])
        return ev, ld, lins
    def m_dup_sink(ev, ld, lins):
        ld.removed_atom_sinks.extend([sink, sink])
        return ev, ld, lins
    def m_conf_sink(ev, ld, lins):
        ld.removed_atom_sinks.extend([
            RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                            formal_assignment=True),
            RemovedAtomSink(atom_map_number=1, sink_participant_id="p1",
                            formal_assignment=True)])
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M80a", "duplicate AddedAtomSource enters strict", m_dup_aas)
    b = _strict_violation_mutation(
        "M80b", "conflicting AddedAtomSource enters strict", m_conf_aas)
    c = _strict_violation_mutation(
        "M80c", "duplicate RemovedAtomSink enters strict", m_dup_sink)
    d = _strict_violation_mutation(
        "M80d", "conflicting RemovedAtomSink enters strict", m_conf_sink)
    caught = a["caught"] and b["caught"] and c["caught"] and d["caught"]
    return {"mutation_id": "M80",
            "mutation": "duplicate/conflicting AddedAtomSource/RemovedAtomSink enter strict",
            "expected": "never strict (all four)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": (f"M80a={a['caught']} M80b={b['caught']} "
                         f"M80c={c['caught']} M80d={d['caught']}"),
            "caught": caught, "sub_results": [a, b, c, d]}


def mutation_81_transfer_mechanistic_duplicates_enter_strict() -> dict:
    """M81: duplicate FAT assignment / conflicting FAT / duplicate mechanistic
    target maps must never be strict (M81a dup FAT / M81b conf FAT /
    M81c dup mechanistic target)."""
    from reaction_agent.schemas.ledger import (
        FormalAtomTransferAssignment, MechanisticOriginEvidence)
    fat = FormalAtomTransferAssignment(source_participant_id="r1",
                                       target_participant_id="p1",
                                       transferred_atom_map_numbers=[1])
    def m_dup_fat(ev, ld, lins):
        ld.formal_atom_transfer_assignments.extend([fat, fat])
        return ev, ld, lins
    def m_conf_fat(ev, ld, lins):
        from reaction_agent.schemas.evidence import ReactionParticipant
        p2 = ReactionParticipant(participant_id="p2", molecule_id="mol_p2",
                                 canonical_smiles="CC", side="product",
                                 atom_map_numbers=[3, 4], mapped_fraction=1.0)
        ev.participants.append(p2)
        ld.formal_atom_transfer_assignments.extend([
            FormalAtomTransferAssignment(source_participant_id="r1",
                                         target_participant_id="p1",
                                         transferred_atom_map_numbers=[1]),
            FormalAtomTransferAssignment(source_participant_id="r1",
                                         target_participant_id="p2",
                                         transferred_atom_map_numbers=[1])])
        return ev, ld, lins
    def m_dup_mech(ev, ld, lins):
        ld.mechanistic_origin_evidence.append(MechanisticOriginEvidence(
            evidence_id="me_dup", evidence_type="isotope_tracing",
            source_participant_id="r1", target_atom_map_numbers=[1, 1]))
        return ev, ld, lins
    a = _strict_violation_mutation(
        "M81a", "duplicate FAT assignment enters strict", m_dup_fat)
    b = _strict_violation_mutation(
        "M81b", "conflicting FAT assignments enter strict", m_conf_fat)
    c = _strict_violation_mutation(
        "M81c", "duplicate mechanistic target maps enter strict", m_dup_mech)
    caught = a["caught"] and b["caught"] and c["caught"]
    return {"mutation_id": "M81",
            "mutation": "duplicate FAT / conflicting FAT / duplicate mechanistic target maps enter strict",
            "expected": "never strict (all three)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M81a={a['caught']} M81b={b['caught']} M81c={c['caught']}",
            "caught": caught, "sub_results": [a, b, c]}


def mutation_82_unbacked_removed_atom_sink_enters_strict() -> dict:
    """M82: RemovedAtomSink formal_assignment=False (no other authority) must
    never be strict (M82a direct / M82b public)."""
    from reaction_agent.schemas.ledger import RemovedAtomSink
    def m(ev, ld, lins):
        ld.removed_atom_sinks.append(RemovedAtomSink(
            atom_map_number=1, sink_participant_id="r1", formal_assignment=False))
        return ev, ld, lins
    def m_item(item):
        from reaction_agent.schemas.ledger import RemovedAtomSink
        item.source_ledger.removed_atom_sinks.append(RemovedAtomSink(
            atom_map_number=1, sink_participant_id="r1", formal_assignment=False))
    direct = _strict_violation_mutation(
        "M82a", "unbacked non-formal RemovedAtomSink enters strict", m)
    public = _strict_public_index_dual(
        "M82b", "unbacked non-formal RemovedAtomSink via public API", m_item)
    caught = direct["caught"] and public["caught"]
    return {"mutation_id": "M82",
            "mutation": "RemovedAtomSink formal_assignment=False without authority enters strict",
            "expected": "never strict (direct) AND public lane != strict AND non-production",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M82a={direct['caught']} M82b={public['caught']}",
            "caught": caught, "sub_results": [direct, public]}


def mutation_83_index_only_leakage_detected() -> dict:
    """M83 (R8 §14.1, corrected): keep records.jsonl lane=diagnostic but inject
    the diagnostic reaction into production_index.jsonl, then call the REAL
    public ``load_snapshot`` (the centralized index-partition validator). The
    loader must fail closed with ``index_partition_wrong_lane``. NOT a
    mutation-runner self-assert and NOT a generic hash mismatch — this proves
    the G08/G09 target authority itself rejects the index-only leak. Temp dir
    only; never touches real workspace files."""
    import json
    import os
    import tempfile

    from reaction_agent.snapshot.builder import build_snapshot
    from reaction_agent.snapshot.loader import (
        SnapshotHashMismatchError,
        load_snapshot,
    )
    from scripts.run_p1_gate import _g09_item_diagnostic, _g09_t10_fixture_config

    item = _g09_item_diagnostic(rid="rxn_m83diag")
    caught = False
    evidence = ""
    with tempfile.TemporaryDirectory(prefix="m83_") as td:
        cfg = _g09_t10_fixture_config(os.path.join(td, "snaps"))
        man = build_snapshot(cfg, iter([item]))
        snap_dir = os.path.join(cfg.output_snapshot_root, man.snapshot_id)
        rec = None
        with open(os.path.join(snap_dir, "records.jsonl")) as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r["reaction_evidence"]["reaction_id"] == "rxn_m83diag":
                    rec = r
                    break
        records_lane = rec["lane"]
        # 1. BEFORE mutation: the real loader accepts the legal snapshot
        loader_before_ok = True
        try:
            load_snapshot(snap_dir)
        except Exception as e:  # noqa: BLE001
            loader_before_ok = False
            evidence = f"SETUP ERROR: pre-mutation load_snapshot failed: {e}"
        prod_before = _read_jsonl_prod(snap_dir)
        # 2. inject the diagnostic record into production (ONLY change; records
        #    lane stays diagnostic)
        with open(os.path.join(snap_dir, "production_index.jsonl"), "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        prod_after = _read_jsonl_prod(snap_dir)
        # 3. REAL public authority: load_snapshot must fail closed on the leak
        try:
            load_snapshot(snap_dir)
            caught = False
            evidence = (f"REAL loader ACCEPTED the production leak "
                        f"(records_lane={records_lane!r} "
                        f"prod_after={prod_after})")
        except SnapshotHashMismatchError as e:
            msg = str(e)
            if "index_partition_wrong_lane" in msg:
                caught = True
                evidence = (f"real loader FAILED on index-only leak: "
                            f"{msg[:160]} (records_lane={records_lane!r} "
                            f"prod_before={prod_before} prod_after={prod_after})")
            else:
                caught = False
                evidence = (f"loader failed for the WRONG reason "
                            f"(no index_partition_wrong_lane token): {msg[:160]}")
        except Exception as e:  # noqa: BLE001
            caught = False
            evidence = (f"loader failed with unexpected exception type "
                        f"{type(e).__name__}: {str(e)[:160]}")
        if not loader_before_ok:
            caught = False
    return {"mutation_id": "M83",
            "mutation": "records diagnostic but wrongly injected into production index (index-only leakage)",
            "expected": "real public load_snapshot / G08-G09 authority FAIL "
                        "(index_partition_wrong_lane)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": evidence, "caught": caught}


def mutation_84_diagnostic_member_deletion() -> dict:
    """M84 (R8 §14.2): delete an expected member from diagnostic_index.jsonl
    (manifest / snapshot_hash / COMPLETE untouched). The REAL public
    ``load_snapshot`` must reject with ``index_partition_missing`` (the audit
    evidence cannot silently vanish) — not a missing-file / JSON-parse error."""
    import json
    import os
    import tempfile

    from reaction_agent.snapshot.builder import build_snapshot
    from reaction_agent.snapshot.loader import (
        SnapshotHashMismatchError,
        load_snapshot,
    )
    from scripts.run_p1_gate import _g09_item_diagnostic, _g09_t10_fixture_config

    item = _g09_item_diagnostic(rid="rxn_m84diag")
    caught = False
    evidence = ""
    with tempfile.TemporaryDirectory(prefix="m84_") as td:
        cfg = _g09_t10_fixture_config(os.path.join(td, "snaps"))
        man = build_snapshot(cfg, iter([item]))
        snap_dir = os.path.join(cfg.output_snapshot_root, man.snapshot_id)
        # 1. BEFORE mutation: real loader accepts the legal snapshot
        try:
            load_snapshot(snap_dir)
            loader_before_ok = True
        except Exception as e:  # noqa: BLE001
            loader_before_ok = False
            evidence = f"SETUP ERROR: pre-mutation load_snapshot failed: {e}"
        diag_path = os.path.join(snap_dir, "diagnostic_index.jsonl")
        with open(diag_path, encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
        diag_before = len(lines)
        # 2. delete the expected diagnostic member (ONLY change)
        with open(diag_path, "w", encoding="utf-8") as f:
            pass
        # 3. REAL loader must reject with index_partition_missing
        try:
            load_snapshot(snap_dir)
            caught = False
            evidence = (f"REAL loader ACCEPTED an empty diagnostic_index "
                        f"(member deleted, metadata untouched)")
        except SnapshotHashMismatchError as e:
            msg = str(e)
            if "index_partition_missing" in msg or "diagnostic_index_hash_mismatch" in msg:
                caught = True
                evidence = (f"real loader FAILED on diagnostic member deletion: "
                            f"{msg[:160]} (diag_before={diag_before} diag_after=0)")
            else:
                caught = False
                evidence = (f"loader failed for the WRONG reason "
                            f"(no partition token): {msg[:160]}")
        except Exception as e:  # noqa: BLE001
            caught = False
            evidence = (f"loader failed with unexpected exception type "
                        f"{type(e).__name__}: {str(e)[:160]}")
        if not loader_before_ok:
            caught = False
    return {"mutation_id": "M84",
            "mutation": "delete expected diagnostic_index member (metadata untouched)",
            "expected": "real load_snapshot FAIL (index_partition_missing or "
                        "diagnostic_index_hash_mismatch)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": evidence, "caught": caught}


def mutation_85_index_nested_payload_mutation() -> dict:
    """M85 (R8 §14.3): mutate a production_index entry's nested chemistry
    payload while keeping its self-reported ``record_content_hash`` (records /
    manifest / snapshot_hash / COMPLETE untouched). The REAL public
    ``load_snapshot`` must reject by REHASHING the index entry payload
    (``index_entry_content_mismatch``) — never trusting the self-reported hash."""
    import json
    import os
    import tempfile

    from reaction_agent.snapshot.builder import build_snapshot
    from reaction_agent.snapshot.loader import (
        SnapshotHashMismatchError,
        load_snapshot,
    )
    from scripts.run_p1_gate import _g09_item_strict, _g09_t10_fixture_config

    item = _g09_item_strict(rid="rxn_m85strict")
    caught = False
    evidence = ""
    with tempfile.TemporaryDirectory(prefix="m85_") as td:
        cfg = _g09_t10_fixture_config(os.path.join(td, "snaps"))
        man = build_snapshot(cfg, iter([item]))
        snap_dir = os.path.join(cfg.output_snapshot_root, man.snapshot_id)
        # 1. BEFORE mutation: real loader accepts the legal snapshot
        try:
            load_snapshot(snap_dir)
            loader_before_ok = True
        except Exception as e:  # noqa: BLE001
            loader_before_ok = False
            evidence = f"SETUP ERROR: pre-mutation load_snapshot failed: {e}"
        prod_path = os.path.join(snap_dir, "production_index.jsonl")
        with open(prod_path, encoding="utf-8") as f:
            prods = [json.loads(ln) for ln in f if ln.strip()]
        stored_hash = prods[0]["record_content_hash"]
        # 2. mutate ONLY the nested chemistry payload (entry hash untouched)
        prods[0]["reaction_evidence"]["participants"][0]["canonical_smiles"] = "C#N"
        assert prods[0]["record_content_hash"] == stored_hash
        with open(prod_path, "w", encoding="utf-8") as f:
            for p in prods:
                f.write(json.dumps(p, sort_keys=True) + "\n")
        # 3. REAL loader must reject by rehashing the index entry payload
        try:
            load_snapshot(snap_dir)
            caught = False
            evidence = ("REAL loader ACCEPTED a production_index entry whose "
                        "nested payload was mutated (self-reported hash kept)")
        except SnapshotHashMismatchError as e:
            msg = str(e)
            if "index_entry_content_mismatch" in msg or "index_entry_hash_mismatch" in msg:
                caught = True
                evidence = (f"real loader FAILED on nested index payload mutation: "
                            f"{msg[:160]} (entry hash kept={stored_hash[:12]}...)")
            else:
                caught = False
                evidence = (f"loader failed for the WRONG reason "
                            f"(no index_entry token): {msg[:160]}")
        except Exception as e:  # noqa: BLE001
            caught = False
            evidence = (f"loader failed with unexpected exception type "
                        f"{type(e).__name__}: {str(e)[:160]}")
        if not loader_before_ok:
            caught = False
    return {"mutation_id": "M85",
            "mutation": "mutate production_index entry nested payload (hash kept)",
            "expected": "real load_snapshot FAIL (index_entry_content_mismatch or "
                        "index_entry_hash_mismatch)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": evidence, "caught": caught}


def _manifest_authority_mutation(
    rid: str,
    item_fn,
    mutate: object,
    expected_tokens: list[str],
    desc: str,
    mid: str,
) -> dict:
    """Shared Round 9 manifest-authority mutation probe: build a legal snapshot,
    confirm the REAL loader accepts it pre-mutation, apply ONE manifest
    authority mutation, then require the REAL public load_snapshot to fail
    closed with a manifest-specific token. Temp dir only; never touches real
    workspace files."""
    import json
    import os
    import tempfile

    from reaction_agent.snapshot.builder import build_snapshot
    from reaction_agent.snapshot.loader import (
        SnapshotHashMismatchError,
        load_snapshot,
    )
    from scripts.run_p1_gate import _g09_t10_fixture_config

    caught = False
    evidence = ""
    with tempfile.TemporaryDirectory(prefix="m9x_") as td:
        cfg = _g09_t10_fixture_config(os.path.join(td, "snaps"))
        man = build_snapshot(cfg, iter([item_fn(rid)]))
        snap_dir = os.path.join(cfg.output_snapshot_root, man.snapshot_id)
        try:
            load_snapshot(snap_dir)
            loader_before_ok = True
        except Exception as e:  # noqa: BLE001
            loader_before_ok = False
            evidence = f"SETUP ERROR: pre-mutation load_snapshot failed: {e}"
        mpath = os.path.join(snap_dir, "manifest.json")
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
        mutate(manifest)
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, indent=2)
        try:
            load_snapshot(snap_dir)
            caught = False
            evidence = f"REAL loader ACCEPTED the mutation ({desc})"
        except SnapshotHashMismatchError as e:
            msg = str(e)
            if any(t in msg for t in expected_tokens):
                caught = True
                evidence = f"real loader FAILED on {desc}: {msg[:170]}"
            else:
                caught = False
                evidence = (f"loader failed for the WRONG reason "
                            f"(no {expected_tokens} token): {msg[:170]}")
        except Exception as e:  # noqa: BLE001
            caught = False
            evidence = (f"loader failed with unexpected exception type "
                        f"{type(e).__name__}: {str(e)[:170]}")
        if not loader_before_ok:
            caught = False
    return {"mutation_id": mid,
            "mutation": desc,
            "expected": f"real load_snapshot FAIL ({expected_tokens[0]})",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": evidence, "caught": caught}


def mutation_86_required_manifest_diagnostic_hash_deletion() -> dict:
    """M86 (R9 §11): delete the required manifest diagnostic_index_hash field
    (every other artifact untouched) → real load_snapshot must fail closed with
    manifest_required_field_missing (never skipped via .get())."""
    from scripts.run_p1_gate import _g09_item_diagnostic
    return _manifest_authority_mutation(
        "rxn_m86diag",
        _g09_item_diagnostic,
        lambda m: m.pop("diagnostic_index_hash", None),
        ["manifest_required_field_missing"],
        "delete required manifest diagnostic_index_hash field",
        "M86")


def mutation_87_manifest_summary_mutation() -> dict:
    """M87 (R9 §11): tamper manifest summary fields — lane count, record count,
    source summary, index hash — each must be rejected by the real loader with
    the matching manifest token. Split into M87a–M87d; every sub-result is
    reported in structured evidence."""
    from scripts.run_p1_gate import _g09_item_diagnostic, _g09_item_strict
    a = _manifest_authority_mutation(
        "rxn_m87a",
        _g09_item_diagnostic,
        lambda m: m.update({"diagnostic_count": 999}),
        ["manifest_count_mismatch"],
        "tamper manifest diagnostic_count=999",
        "M87a")
    b = _manifest_authority_mutation(
        "rxn_m87b",
        _g09_item_diagnostic,
        lambda m: m.update({"record_count": 999}),
        ["manifest_count_mismatch"],
        "tamper manifest record_count=999",
        "M87b")
    c = _manifest_authority_mutation(
        "rxn_m87c",
        _g09_item_diagnostic,
        lambda m: m.update({"source_counts": {"forged_source": 999}}),
        ["manifest_source_counts_mismatch"],
        "tamper manifest source_counts (forged mapping)",
        "M87c")
    d = _manifest_authority_mutation(
        "rxn_m87d",
        _g09_item_strict,
        lambda m: m.update({"production_index_hash": "f" * 64}),
        ["manifest_index_hash_mismatch"],
        "tamper manifest production_index_hash (forged)",
        "M87d")
    caught = a["caught"] and b["caught"] and c["caught"] and d["caught"]
    return {"mutation_id": "M87",
            "mutation": "tamper manifest summary fields (counts / source summary / index hash)",
            "expected": "real load_snapshot FAIL (manifest-specific token per tamper)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": (f"M87a={a['caught']} M87b={b['caught']} "
                         f"M87c={c['caught']} M87d={d['caught']}"),
            "caught": caught,
            "sub_results": [a, b, c, d]}


def mutation_88_snapshot_identity_forgery() -> dict:
    """M88 (R9 §11): forge manifest.snapshot_id (snapshot hash / COMPLETE /
    indexes / records untouched) → real load_snapshot must fail closed with
    snapshot_identity_mismatch."""
    from scripts.run_p1_gate import _g09_item_diagnostic
    return _manifest_authority_mutation(
        "rxn_m88diag",
        _g09_item_diagnostic,
        lambda m: m.update({"snapshot_id": "snap_forged000000"}),
        ["snapshot_identity_mismatch"],
        "forge manifest snapshot_id",
        "M88")


# =====================================================================
# Round 10 §5 — M89–M91: manifest type-authority loader mutations.
# Each builds a ONE-RECORD valid snapshot, proves the REAL public load_snapshot
# accepts it pre-mutation, applies ONE manifest.json authority mutation (the
# ONLY file rewritten — records / indexes / snapshot_hash / COMPLETE marker
# stay byte-identical, proven by _snapshot_fingerprint), then requires the REAL
# public load_snapshot to fail closed with a stable manifest_* token — never a
# mutation-runner self-assert.
# =====================================================================

def _snapshot_fingerprint(snap_dir: str) -> str:
    """SHA-256 over every file in the snapshot EXCEPT manifest.json.

    Proves a loader mutation rewrote ONLY manifest.json — records / indexes /
    COMPLETE marker / snapshot_hash stay byte-identical (task §5: M89 'keep
    records/indexes/hash/COMPLETE unchanged')."""
    import hashlib
    h = hashlib.sha256()
    for name in sorted(os.listdir(snap_dir)):
        path = os.path.join(snap_dir, name)
        if name == "manifest.json" or not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            h.update(name.encode("utf-8"))
            h.update(b"\x00")
            h.update(f.read())
            h.update(b"\x00")
    return h.hexdigest()


def _round10_loader_mutation(
    mid: str,
    item_fn,
    mutate,
    expected_tokens: list[str],
    expected_exc: object,
    desc: str,
) -> dict:
    """Shared Round 10 loader-authority mutation probe.

    Build a one-record valid snapshot, confirm the REAL public load_snapshot
    accepts it pre-mutation, apply ONE manifest.json authority mutation (only
    manifest.json rewritten; the non-manifest artifacts are byte-identical),
    then require the REAL public load_snapshot to fail closed. ``expected_tokens``
    are matched against a SnapshotHashMismatchError message; ``expected_exc``
    (e.g. SnapshotIncompleteError) matches the exact exception type for the
    semantic (not manifest type) failure. Temp dir only."""
    import json
    import os
    import tempfile

    from reaction_agent.snapshot.builder import build_snapshot
    from reaction_agent.snapshot.loader import (
        SnapshotHashMismatchError,
        load_snapshot,
    )
    from scripts.run_p1_gate import _g09_t10_fixture_config

    caught = False
    evidence = ""
    with tempfile.TemporaryDirectory(prefix="m9x_") as td:
        cfg = _g09_t10_fixture_config(os.path.join(td, "snaps"))
        man = build_snapshot(cfg, iter([item_fn()]))
        snap_dir = os.path.join(cfg.output_snapshot_root, man.snapshot_id)
        # 1. BEFORE mutation: real loader accepts the legal snapshot
        try:
            load_snapshot(snap_dir)
            loader_before_ok = True
        except Exception as e:  # noqa: BLE001
            loader_before_ok = False
            evidence = f"SETUP ERROR: pre-mutation load_snapshot failed: {e}"
        # 2. non-manifest artifacts must be byte-identical across the mutation
        before_fingerprint = _snapshot_fingerprint(snap_dir)
        mpath = os.path.join(snap_dir, "manifest.json")
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
        mutate(manifest)
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, indent=2)
        after_fingerprint = _snapshot_fingerprint(snap_dir)
        artifacts_untouched = before_fingerprint == after_fingerprint
        # 3. REAL loader must fail closed on the manifest mutation
        try:
            load_snapshot(snap_dir)
            caught = False
            evidence = f"REAL loader ACCEPTED the mutation ({desc})"
        except SnapshotHashMismatchError as e:
            msg = str(e)
            if any(t in msg for t in expected_tokens):
                caught = True
                evidence = f"real loader FAILED on {desc}: {msg[:170]}"
            else:
                caught = False
                evidence = (f"loader failed for the WRONG reason "
                            f"(no {expected_tokens} token): {msg[:170]}")
        except Exception as e:  # noqa: BLE001
            if expected_exc is not None and isinstance(e, expected_exc):
                caught = True
                evidence = f"real loader FAILED on {desc}: {str(e)[:170]}"
            else:
                caught = False
                evidence = (f"loader failed with unexpected exception type "
                            f"{type(e).__name__}: {str(e)[:170]}")
        if not loader_before_ok:
            caught = False
        if not artifacts_untouched:
            caught = False
            evidence = (f"SETUP ERROR: mutation rewrote non-manifest artifacts "
                        f"(records/indexes/hash/COMPLETE): {evidence}")
    return {"mutation_id": mid,
            "mutation": desc,
            "expected": (f"real load_snapshot FAIL ("
                         f"{expected_tokens[0] if expected_tokens else expected_exc.__name__})"),
            "actual_passed": caught, "actual_blocked": False,
            "evidence": evidence, "caught": caught}


def mutation_89_manifest_record_count_boolean() -> dict:
    """M89 (R10 §5): manifest.record_count=true must be rejected by the REAL
    loader with manifest_field_type_invalid. JSON booleans are instances of
    int in Python, so only the exact-type check (``type(value) is int``) —
    never ``isinstance`` — can catch ``true``. records / indexes / snapshot_hash
    / COMPLETE unchanged (only manifest.json rewritten)."""
    from scripts.run_p1_gate import _g09_item_strict
    return _round10_loader_mutation(
        "M89",
        _g09_item_strict,
        lambda m: m.update({"record_count": True}),
        ["manifest_field_type_invalid"],
        None,
        "set manifest.record_count=true (boolean in exact-int field)",
    )


def mutation_90_failure_counts_nested_type() -> dict:
    """M90 (R10 §5): failure_counts_by_reason nested count typed ``true`` /
    ``1.0`` must be rejected by the REAL loader with manifest_field_type_invalid
    (M90a count=true, M90b count=1.0). The existing real reason key's value is
    mutated so the exact-type nested shape check (not a foreign-key injection)
    is what fails closed."""
    from scripts.run_p1_gate import _g09_item_diagnostic

    def m90a(m):
        key = next(iter(m["failure_counts_by_reason"]))
        m["failure_counts_by_reason"][key] = True

    def m90b(m):
        key = next(iter(m["failure_counts_by_reason"]))
        m["failure_counts_by_reason"][key] = 1.0

    a = _round10_loader_mutation(
        "M90a", _g09_item_diagnostic, m90a,
        ["manifest_field_type_invalid"], None,
        "set failure_counts_by_reason count=true",
    )
    b = _round10_loader_mutation(
        "M90b", _g09_item_diagnostic, m90b,
        ["manifest_field_type_invalid"], None,
        "set failure_counts_by_reason count=1.0",
    )
    caught = a["caught"] and b["caught"]
    return {"mutation_id": "M90",
            "mutation": "nested failure_counts_by_reason count typed true/1.0",
            "expected": "real load_snapshot FAIL (manifest_field_type_invalid, both)",
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M90a={a['caught']} M90b={b['caught']}",
            "caught": caught, "sub_results": [a, b]}


def mutation_91_build_status_authority_order() -> dict:
    """M91 (R10 §5): build_status authority ORDER — the loader must gate
    build_status presence → exact-str type → semantic completeness in that
    sequence (Task A §7 frozen semantics):
      M91a delete build_status     -> manifest_required_field_missing
      M91b build_status=true       -> manifest_field_type_invalid
      M91c build_status="partial"  -> SnapshotIncompleteError (legitimate type,
                                      incomplete semantic — NOT a manifest type
                                      failure)
    All three call the REAL public load_snapshot."""
    from reaction_agent.snapshot.loader import SnapshotIncompleteError
    from scripts.run_p1_gate import _g09_item_diagnostic
    a = _round10_loader_mutation(
        "M91a", _g09_item_diagnostic,
        lambda m: m.pop("build_status", None),
        ["manifest_required_field_missing"], None,
        "delete build_status",
    )
    b = _round10_loader_mutation(
        "M91b", _g09_item_diagnostic,
        lambda m: m.update({"build_status": True}),
        ["manifest_field_type_invalid"], None,
        "set build_status=true",
    )
    c = _round10_loader_mutation(
        "M91c", _g09_item_diagnostic,
        lambda m: m.update({"build_status": "partial"}),
        [], SnapshotIncompleteError,
        "set build_status='partial' (legitimate type, incomplete semantic)",
    )
    caught = a["caught"] and b["caught"] and c["caught"]
    return {"mutation_id": "M91",
            "mutation": "build_status authority order (delete / boolean / partial)",
            "expected": ("missing->manifest_required_field_missing, "
                         "true->manifest_field_type_invalid, "
                         "partial->SnapshotIncompleteError"),
            "actual_passed": caught, "actual_blocked": False,
            "evidence": f"M91a={a['caught']} M91b={b['caught']} M91c={c['caught']}",
            "caught": caught, "sub_results": [a, b, c]}


def _read_jsonl_prod(snap_dir: str) -> list:
    import json
    import os
    ids = []
    with open(os.path.join(snap_dir, "production_index.jsonl")) as f:
        for line in f:
            if not line.strip():
                continue
            ids.append(json.loads(line)["reaction_evidence"]["reaction_id"])
    return ids


def run_all_mutations() -> list[dict]:
    """Run all 72 mutations (M1–M8 original + M9–M25 Round 2 + M26–M41 Round 3
    + M42–M56 Round 4 + M57–M72 Round 5)."""
    mutations = [
        mutation_1_delete_participant_preservation,
        mutation_2_critical_tie_take_max,
        mutation_3_mcs_full_mapping,
        mutation_4_mapper_fills_mechanism,
        mutation_5_quarantine_into_production,
        mutation_6_snapshot_nondeterministic,
        mutation_7_delete_proline_2og_case,
        mutation_8_add_skipped_test,
        mutation_9_g03_complete_zero_records,
        mutation_10_g03_complete_empty_source_ids,
        mutation_11_g03_legacy_hash_mismatch,
        mutation_12_g04_status_only_promotion,
        mutation_13_g04_unavailable_but_complete,
        mutation_14_g06_remove_proline_keep_count,
        mutation_15_g06_inject_forbidden_pair,
        mutation_16_g08_failed_mapping_enters_strict,
        mutation_17_g08_incomplete_source_enters_strict,
        mutation_18_g09_participant_provenance_no_hash_change,
        mutation_19_g09_mapping_pair_no_hash_change,
        mutation_20_g09_source_ledger_no_hash_change,
        mutation_21_g09_transformed_lineage_no_hash_change,
        mutation_22_g10_complete_null_files,
        mutation_23_g10_same_annotator_id,
        mutation_24_g10_missing_adjudication,
        mutation_25_blocked_gate_with_impl_failure,
        mutation_26_reaction_provenance_no_hash_change,
        mutation_27_source_citation_no_hash_change,
        mutation_28_fragment_lineage_no_hash_change,
        mutation_29_quality_quarantine_no_hash_change,
        mutation_30_eligibility_decision_no_hash_change,
        mutation_31_quarantine_record_no_hash_change,
        mutation_32_low_mapped_fraction_enters_strict,
        mutation_33_assignment_ambiguity_enters_strict,
        mutation_34_unknown_participant_enters_strict,
        mutation_35_unknown_atom_map_enters_strict,
        mutation_36_wrong_side_participant_enters_strict,
        mutation_37_unresolved_lineage_enters_strict,
        mutation_38_partial_ambiguity_enters_strict,
        mutation_39_lineage_unsupported_by_mapping_enters_strict,
        mutation_40_two_reactants_one_product_enters_strict,
        mutation_41_ledger_disagreement_builds_strict,
        mutation_42_nonzero_element_delta_enters_strict,
        mutation_43_explicit_quarantine_enters_strict,
        mutation_44_identity_ambiguity_set_enters_strict,
        mutation_45_embedded_external_lineage_conflict_enters_strict,
        mutation_46_uncontrolled_direction_enters_strict,
        mutation_47_participant_low_mapped_fraction_enters_strict,
        mutation_48_dropped_formal_pair_uncovered_map_enters_strict,
        mutation_49_reverse_collision_enters_strict,
        mutation_50_added_atom_source_ghost_enters_strict,
        mutation_51_role_assignment_ghost_enters_strict,
        mutation_52_stoichiometry_ghost_enters_strict,
        mutation_53_formal_atom_transfer_ghost_enters_strict,
        mutation_54_generic_ledger_unknown_enters_strict,
        mutation_55_duplicate_lineage_enters_strict,
        mutation_56_gate_wiring_protects_mandatory_tests,
        mutation_57_added_atom_source_unknown_map_enters_strict,
        mutation_58_reactant_entry_ghost_enters_strict,
        mutation_59_product_entry_ghost_enters_strict,
        mutation_60_stoichiometry_role_conflicts_enter_strict,
        mutation_61_formal_transfer_reversed_sides_enters_strict,
        mutation_62_formal_transfer_map_conflicts_enter_strict,
        mutation_63_removed_atom_sink_ghost_enters_strict,
        mutation_64_cofactor_change_ghost_enters_strict,
        mutation_65_mechanistic_evidence_ghost_enters_strict,
        mutation_66_negative_element_count_enters_strict,
        mutation_67_partial_consistent_delta_mislabeled,
        mutation_68_participant_map_duplicate_enters_strict,
        mutation_69_same_side_map_collision_enters_strict,
        mutation_70_duplicate_id_or_uncontrolled_side_enters_strict,
        mutation_71_duplicate_embedded_lineage_ids_enters_strict,
        mutation_72_reordered_map_duplicate_lineage_enters_strict,
        mutation_73_uncontrolled_cofactor_direction_enters_strict,
        mutation_74_stoich_authority_conflicts_enter_strict,
        mutation_75_mechanistic_reactant_only_target_enters_strict,
        mutation_76_empty_or_duplicate_formal_transfer_enters_strict,
        mutation_77_heavy_atom_empty_maps_enters_strict,
        mutation_78_heavy_map_count_mismatch_enters_strict,
        mutation_79_nonpositive_map_ids_enter_strict,
        mutation_80_atom_source_sink_duplicates_enter_strict,
        mutation_81_transfer_mechanistic_duplicates_enter_strict,
        mutation_82_unbacked_removed_atom_sink_enters_strict,
        mutation_83_index_only_leakage_detected,
        mutation_84_diagnostic_member_deletion,
        mutation_85_index_nested_payload_mutation,
        mutation_86_required_manifest_diagnostic_hash_deletion,
        mutation_87_manifest_summary_mutation,
        mutation_88_snapshot_identity_forgery,
        mutation_89_manifest_record_count_boolean,
        mutation_90_failure_counts_nested_type,
        mutation_91_build_status_authority_order,
    ]
    results = []
    for i, mut_fn in enumerate(mutations, 1):
        try:
            result = mut_fn()
            result["mutation_id"] = f"M{i}"
            results.append(result)
            status = "CAUGHT" if result["caught"] else "MISSED"
            print(f"  [{status}] M{i}: {result['mutation']}")
            print(f"         expected={result['expected']}, passed={result['actual_passed']}, blocked={result['actual_blocked']}")
        except Exception as e:  # noqa: BLE001
            results.append({
                "mutation_id": f"M{i}",
                "mutation": mut_fn.__doc__.strip().split("\n")[0] if mut_fn.__doc__ else f"mutation_{i}",
                "expected": "GATE FAIL",
                "actual_passed": None,
                "actual_blocked": None,
                "evidence": f"ERROR: {e}",
                "caught": False,
                "error": str(e),
            })
            print(f"  [ERROR] M{i}: {e}")
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("P1 GATE MUTATION RUNNER — 91 Mutations on Temp Copies (§18.3 + §6 + §12 + §15 + Round 7 + Round 8 + Round 9 + Round 10)")
    print("=" * 60)
    print()
    results = run_all_mutations()
    caught = sum(1 for r in results if r.get("caught"))
    print(f"\nResult: {caught}/{len(results)} mutations caught")
    # Write full results to JSON (M1–M83 summary, §12 + §15)
    out_path = os.path.join(DEMOV2_ROOT, "reports", "p1", "mutation_results.json")
    _write_json(out_path, {"mutations": results, "caught": caught, "total": len(results)})
    print(f"Results: {out_path}")

    # Round 4 (§12) + Round 5 (§12) split outputs. All derive from the SAME
    # results (single source of truth) so per-item expected/actual/caught stay
    # visible.
    def _by_ids(id_lo: int, id_hi: int) -> list[dict]:
        picked = []
        for r in results:
            mid = r.get("mutation_id", "")
            if mid.startswith("M") and mid[1:].isdigit():
                n = int(mid[1:])
                if id_lo <= n <= id_hi:
                    picked.append(r)
        return picked

    semantic_r4 = _by_ids(42, 55)
    sem_r4_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "eligibility_semantic_invariant_results_round_4.json")
    _write_json(sem_r4_path, {
        "description": "Round 4 strict eligibility cross-invariant mutations (M42–M55): "
                       "each starts strict and one violating change must exit strict.",
        "mutations": semantic_r4,
        "caught": sum(1 for r in semantic_r4 if r.get("caught")),
        "total": len(semantic_r4)})
    print(f"Results: {sem_r4_path}")

    gate_fp_r4 = _by_ids(56, 56)
    gfp_r4_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "gate_false_positive_mutation_results_round_4.json")
    _write_json(gfp_r4_path, {
        "description": "Round 4 gate-wiring false-positive mutation (M56/M56a/M56b): "
                       "shadowing a mandatory G08/G09 test node must FAIL the gate.",
        "mutations": gate_fp_r4,
        "caught": sum(1 for r in gate_fp_r4 if r.get("caught")),
        "total": len(gate_fp_r4)})
    print(f"Results: {gfp_r4_path}")

    # Round 5 (§12): reference-integrity / semantic-invariant mutations
    # M57–M72, plus the M56 gate-wiring protection (now incl. M56c — the
    # Round-5 G08 node deletion protection).
    r5 = _by_ids(57, 72)
    ri_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                           "eligibility_reference_integrity_results_round_5.json")
    _write_json(ri_path, {
        "description": "Round 5 ledger participant/map reference integrity + element/"
                       "partial + lineage canonical duplicate + public boundary "
                       "mutations (M57–M72): each starts strict and one violating "
                       "change must exit strict / avoid mislabeling.",
        "mutations": r5,
        "caught": sum(1 for r in r5 if r.get("caught")),
        "total": len(r5)})
    print(f"Results: {ri_path}")

    sem_r5_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "eligibility_semantic_invariant_results_round_5.json")
    _write_json(sem_r5_path, {
        "description": "Round 5 strict eligibility semantic invariants (M57–M72): "
                       "AddedAtomSource/entries/stoichiometry/FAT/sinks/cofactor/"
                       "mechanistic/element/participant-map/lineage invariants.",
        "mutations": r5,
        "caught": sum(1 for r in r5 if r.get("caught")),
        "total": len(r5)})
    print(f"Results: {sem_r5_path}")

    gate_fp_r5 = _by_ids(56, 56)
    gfp_r5_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "gate_false_positive_mutation_results_round_5.json")
    _write_json(gfp_r5_path, {
        "description": "Round 5 gate-wiring false-positive mutation "
                       "(M56/M56a/M56b/M56c): shadowing a mandatory G08/G09 "
                       "test node — including the Round-5 reference-integrity "
                       "node — must FAIL the gate.",
        "mutations": gate_fp_r5,
        "caught": sum(1 for r in gate_fp_r5 if r.get("caught")),
        "total": len(gate_fp_r5)})
    print(f"Results: {gfp_r5_path}")

    # Round 6 (§15): M73–M77 reference-integrity/semantic mutations, plus the
    # M56 gate-wiring protection now including M56d (single Round-6 node
    # deletion protection).
    r6 = _by_ids(73, 77)
    ri_r6_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                              "eligibility_reference_integrity_results_round_6.json")
    _write_json(ri_r6_path, {
        "description": "Round 6 cofactor-direction / stoich-authority / "
                       "mechanistic-product-registry / empty-FAT / heavy-atom "
                       "mutations (M73–M77): each starts strict and one "
                       "violating change must exit strict via the target "
                       "invariant.",
        "mutations": r6,
        "caught": sum(1 for r in r6 if r.get("caught")),
        "total": len(r6)})
    print(f"Results: {ri_r6_path}")

    sem_r6_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "eligibility_semantic_invariant_results_round_6.json")
    _write_json(sem_r6_path, {
        "description": "Round 6 strict eligibility semantic invariants "
                       "(M73–M77): R6-01..R6-05 confirmed fail-opens.",
        "mutations": r6,
        "caught": sum(1 for r in r6 if r.get("caught")),
        "total": len(r6)})
    print(f"Results: {sem_r6_path}")

    gate_fp_r6 = _by_ids(56, 56)
    gfp_r6_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "gate_false_positive_mutation_results_round_6.json")
    _write_json(gfp_r6_path, {
        "description": "Round 6 gate-wiring false-positive mutation "
                       "(M56/M56a/M56b/M56c/M56d): shadowing a mandatory "
                       "G08/G09 test node — including a SINGLE Round-6 node "
                       "removal — must FAIL the gate.",
        "mutations": gate_fp_r6,
        "caught": sum(1 for r in gate_fp_r6 if r.get("caught")),
        "total": len(gate_fp_r6)})
    print(f"Results: {gfp_r6_path}")

    # Round 7 (§15): M78–M83 reference-integrity / semantic / gate-false-
    # positive mutations. M78 heavy-atom map count, M79 nonpositive map IDs,
    # M80 atom source/sink duplicates, M81 FAT/mechanistic duplicates,
    # M82 unbacked sink, M83 index-only leakage. M83 also exercises the
    # index-aware public boundary (R7-06).
    r7 = _by_ids(78, 83)
    ri_r7_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                              "eligibility_reference_integrity_results_round_7.json")
    _write_json(ri_r7_path, {
        "description": "Round 7 heavy-atom map count / positive map IDs / "
                       "atom source-sink duplicates / FAT-mechanistic duplicates "
                       "/ unbacked sink / index-only leakage mutations (M78–M83): "
                       "each starts strict and one violating change must exit "
                       "strict via the target invariant, or the index-aware "
                       "public boundary must FAIL on an index-only leak.",
        "mutations": r7,
        "caught": sum(1 for r in r7 if r.get("caught")),
        "total": len(r7)})
    print(f"Results: {ri_r7_path}")

    sem_r7_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "eligibility_semantic_invariant_results_round_7.json")
    _write_json(sem_r7_path, {
        "description": "Round 7 strict eligibility semantic invariants "
                       "(M78–M83): R7-01..R7-06 confirmed fail-opens.",
        "mutations": r7,
        "caught": sum(1 for r in r7 if r.get("caught")),
        "total": len(r7)})
    print(f"Results: {sem_r7_path}")

    gate_fp_r7 = _by_ids(83, 83)
    gfp_r7_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "gate_false_positive_mutation_results_round_7.json")
    _write_json(gfp_r7_path, {
        "description": "Round 7 index-only leakage mutation (M83): a diagnostic "
                       "record injected into the production index must be caught "
                       "by the index-aware public boundary (R7-06).",
        "mutations": gate_fp_r7,
        "caught": sum(1 for r in gate_fp_r7 if r.get("caught")),
        "total": len(gate_fp_r7)})
    print(f"Results: {gfp_r7_path}")

    # Round 8 (§R8-20): index-partition integrity mutations (M83 corrected,
    # M84 diagnostic member deletion, M85 nested index payload mutation) — all
    # caught by the REAL public load_snapshot / centralized index-partition
    # validator, never a mutation-runner self-assert.
    r8 = _by_ids(83, 85)
    r8_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                           "index_partition_integrity_results_round_8.json")
    _write_json(r8_path, {
        "description": "Round 8 index partition integrity mutations (M83–M85): "
                       "the real public load_snapshot must fail closed on a "
                       "hash-coherent wrong-partition leak, a deleted diagnostic "
                       "member, and a mutated nested index entry payload — with "
                       "stable index_partition_* / index_entry_* reason tokens.",
        "mutations": r8,
        "caught": sum(1 for r in r8 if r.get("caught")),
        "total": len(r8)})
    print(f"Results: {r8_path}")

    gate_fp_r8 = _by_ids(56, 56)
    gfp_r8_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "gate_false_positive_mutation_results_round_8.json")
    _write_json(gfp_r8_path, {
        "description": "Round 8 gate wiring mutations (M56 incl. M56f/M56g): "
                       "deleting a Round-8 G08 production-partition node or a "
                       "Round-8 G09 diagnostic-integrity node must FAIL the "
                       "corresponding Gate (no silent PASS on a shrunken manifest).",
        "mutations": gate_fp_r8,
        "caught": sum(1 for r in gate_fp_r8 if r.get("caught")),
        "total": len(gate_fp_r8)})
    print(f"Results: {gfp_r8_path}")

    # Round 9 (§R9-16): manifest-authority integrity mutations (M86 required
    # field deletion, M87 summary tampering with M87a–M87d, M88 snapshot
    # identity forgery) — all caught by the REAL public load_snapshot /
    # centralized manifest-authority validator with manifest-specific tokens.
    r9 = _by_ids(86, 88)
    r9_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                           "manifest_authority_integrity_results_round_9.json")
    _write_json(r9_path, {
        "description": "Round 9 manifest authority integrity mutations (M86–M88): "
                       "the real public load_snapshot must fail closed on a deleted "
                       "required manifest field, tampered summary fields (counts / "
                       "source summary / index hash), and a forged snapshot_id — "
                       "with stable manifest_* / snapshot_identity_mismatch tokens.",
        "mutations": r9,
        "caught": sum(1 for r in r9 if r.get("caught")),
        "total": len(r9)})
    print(f"Results: {r9_path}")

    gate_fp_r9 = _by_ids(56, 56)
    gfp_r9_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                               "gate_false_positive_mutation_results_round_9.json")
    _write_json(gfp_r9_path, {
        "description": "Round 9 gate wiring mutations (M56 incl. M56h/M56i): "
                       "deleting a Round-9 manifest-required-field node or a "
                       "Round-9 snapshot-identity node must FAIL the corresponding "
                       "Gate (no silent PASS on a shrunken manifest).",
        "mutations": gate_fp_r9,
        "caught": sum(1 for r in gate_fp_r9 if r.get("caught")),
        "total": len(gate_fp_r9)})
    print(f"Results: {gfp_r9_path}")

    # Round 10 (§5/§6): manifest type-authority loader mutations (M89–M91) and
    # the M56j–M56l deletion-protection evidence. Both derive from the SAME
    # results object (single source of truth) — per-item expected / actual /
    # exception / reason token / caught stay visible.
    r10 = _by_ids(89, 91)
    mta_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                            "manifest_type_authority_results_round_10.json")
    _write_json(mta_path, {
        "description": "Round 10 manifest type-authority loader mutations "
                       "(M89–M91): the real public load_snapshot must fail "
                       "closed on record_count=true, nested failure-count "
                       "bool/float, and the build_status authority order "
                       "(delete/boolean/partial) — with stable manifest_* / "
                       "SnapshotIncompleteError outcomes and byte-identical "
                       "non-manifest artifacts.",
        "mutations": r10,
        "caught": sum(1 for r in r10 if r.get("caught")),
        "total": len(r10)})
    print(f"Results: {mta_path}")

    m56 = next((r for r in results if r.get("mutation_id") == "M56"), {})
    m56jkl = [s for s in m56.get("sub_results", [])
              if s.get("mutation_id") in ("M56j", "M56k", "M56l")]
    gfp_r10_path = os.path.join(DEMOV2_ROOT, "reports", "p1",
                                "gate_false_positive_mutation_results_round_10.json")
    _write_json(gfp_r10_path, {
        "description": "Round 10 gate-wiring deletion protection (M56j–M56l): "
                       "deleting a Round-10 manifest type-authority mandatory "
                       "node (record_count boolean / build_status required-type / "
                       "reconstructed-return) must FAIL G09 with mandatory-node-"
                       "missing evidence (real Gate result, not a substring pass).",
        "mutations": m56jkl,
        "caught": sum(1 for s in m56jkl if s.get("caught")),
        "total": len(m56jkl)})
    print(f"Results: {gfp_r10_path}")
