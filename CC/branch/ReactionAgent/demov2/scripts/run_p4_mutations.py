#!/usr/bin/env python3
"""P4 Gate mutation runner (anti-false-positive, PASS->FAIL on PASS-capable fixture).

Every mutation is applied ONLY inside a temporary module patch (restored
afterward) — formal code is never polluted. For each mutation:
1. Run the target gate check on the CLEAN fixture -> must PASS (PASS-capable
   baseline; a BLOCKED baseline cannot prove a caught mutation);
2. Apply the patch (simulates the defect);
3. Run the check again -> must FAIL (caught);
4. escaped / error / missed are NOT counted as caught.

Results are written to reports/p4/P4_MUTATION_RESULTS.json.
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEMOV2_ROOT)
REPORT_DIR = os.path.join(DEMOV2_ROOT, "reports", "p4")
RESULTS_PATH = os.path.join(REPORT_DIR, "P4_MUTATION_RESULTS.json")

# Check functions from the gate.
from scripts.run_p4_gate import (  # noqa: E402
    check_g01_schemas,
    check_g02_evidence_identity,
    check_g03_support,
    check_g04_counterevidence,
    check_g05_ranker,
    check_g07_abstention,
    check_g08_prediction_result,
    check_g09_immutable_run,
)

# Modules patched by mutations.
import reaction_agent.inference.evidence_identity as evid_mod  # noqa: E402
import reaction_agent.inference.support as support_mod  # noqa: E402
import reaction_agent.inference.counterevidence as ce_mod  # noqa: E402
import reaction_agent.inference.ranker as ranker_mod  # noqa: E402
import reaction_agent.inference.abstention as abst_mod  # noqa: E402
import reaction_agent.adapters.prediction_result_adapter as adapter_mod  # noqa: E402
import reaction_agent.runtime.run as run_mod  # noqa: E402
import reaction_agent.runtime.manifest as manifest_mod  # noqa: E402
from reaction_agent.schemas.p4.evidence import DedupDimension  # noqa: E402


@contextmanager
def _patch(patch_spec):
    """Temporarily patch module attribute(s); always restore."""
    specs = patch_spec if isinstance(patch_spec, list) else [patch_spec]
    saved = []
    for module, attr, value in specs:
        saved.append((module, attr, getattr(module, attr)))
        setattr(module, attr, value)
    try:
        yield
    finally:
        for module, attr, old in saved:
            setattr(module, attr, old)


# =====================================================================
# Mutations (each targets one PASS-capable gate check)
# =====================================================================

def _run_one(mutation: dict) -> dict:
    """P4-R1-F: a mutation is caught ONLY when the baseline is PASS, the
    mutated check executes normally (no exception), and the expected failure
    code appears exactly. Execution exceptions are typed ERROR, never caught."""
    mid = mutation["id"]
    name = mutation["name"]
    check_fn = mutation["check_fn"]
    patch_spec = mutation["patch"]
    expected = mutation.get("expected_failure_code")

    # 1. baseline: clean code must PASS the check (PASS-capable fixture).
    #    An exception during baseline is a typed ERROR, not a PASS/FAIL.
    try:
        baseline = check_fn()
    except Exception as e:  # noqa: BLE001
        return {
            "mutation_id": mid, "mutation": name,
            "baseline_status": "ERROR",
            "expected_status": "FAIL", "actual_status": "NO_RUN",
            "caught": False, "escaped": False, "error": True,
            "evidence": f"baseline error: {e}",
        }
    if baseline["passed"] and not baseline.get("blocked"):
        baseline_status = "PASS"
    elif baseline.get("blocked"):
        baseline_status = "BLOCKED"
    else:
        baseline_status = "FAIL"

    if baseline_status != "PASS":
        return {
            "mutation_id": mid, "mutation": name,
            "baseline_status": baseline_status,
            "expected_status": "FAIL", "actual_status": "NO_RUN",
            "caught": False, "escaped": True, "error": False,
            "evidence": f"baseline {baseline_status} not PASS-capable",
        }

    # 2. apply mutation, run check.
    try:
        with _patch(patch_spec):
            mutated = check_fn()
        if mutated.get("error"):
            return {
                "mutation_id": mid, "mutation": name,
                "baseline_status": "PASS",
                "expected_status": "FAIL", "actual_status": "ERROR",
                "caught": False, "escaped": False, "error": True,
                "evidence": mutated.get("evidence", "")[:200],
            }
        actual_status = ("FAIL" if not mutated["passed"] and not mutated.get("blocked")
                         else "PASS" if mutated["passed"] else "BLOCKED")
        if expected is None:
            caught = (actual_status == "FAIL")
        else:
            evidence_blob = f"{mutated.get('evidence', '')} {mutated.get('failure_code', '')}"
            caught = (actual_status == "FAIL" and expected in evidence_blob)
        return {
            "mutation_id": mid, "mutation": name,
            "baseline_status": "PASS",
            "expected_status": "FAIL", "actual_status": actual_status,
            "caught": caught, "escaped": (actual_status == "PASS"),
            "error": False,
            "expected_failure_code": expected,
            "failure_code": mutated.get("failure_code", "") or "",
            "evidence": mutated.get("evidence", "")[:200],
        }
    except Exception as e:  # noqa: BLE001
        return {
            "mutation_id": mid, "mutation": name,
            "baseline_status": "PASS",
            "expected_status": "FAIL", "actual_status": "ERROR",
            "caught": False, "escaped": False, "error": True,
            "evidence": f"mutation error: {e}",
        }


# -- M14 target check: forged PASS-from-BLOCKED-baseline must be flagged ----

def _pass_capable_baselines(mutations: list[dict]) -> list[str]:
    issues: list[str] = []
    for m in mutations:
        if m.get("baseline_status") != "PASS":
            issues.append(
                f"{m.get('mutation_id')} baseline {m.get('baseline_status')} "
                f"not PASS (BLOCKED baseline cannot prove a caught mutation)")
    return issues


def check_m14_stored_pass_artifact() -> dict:
    """A stored PASS-status with a failing (BLOCKED-baseline) artifact must be
    rejected. The check PASSES when the forged report is flagged."""
    forged = [{"mutation_id": "M00", "baseline_status": "BLOCKED",
               "caught": True, "escaped": False, "error": False}]
    issues = _pass_capable_baselines(forged)
    passed = bool(issues)
    return {
        "passed": passed, "blocked": False,
        "evidence": ("forged BLOCKED-baseline report flagged"
                     if passed else "forged BLOCKED-baseline report NOT flagged"),
        "details": {"flagged": len(issues)},
    }


# -- mutation definitions ---------------------------------------------------

def _noop(*args, **kwargs):
    return None


def _same_dimension_none(a, b):
    return None


_orig_same_dimension = evid_mod._same_dimension


def _skip_same_publication(a, b):
    d = _orig_same_dimension(a, b)
    if d == DedupDimension.same_publication:
        return None
    return d


_orig_all_evidence_ids = support_mod._all_evidence_ids


def _add_test_evidence(evidence_records):
    # P4-R1-F M04: use the pre-patch original so the mutation does NOT recurse
    # into itself; the defect is a test-fold evidence id leaking into support.
    return _orig_all_evidence_ids(evidence_records) + ["test:ev_999"]


_orig_build_candidates = adapter_mod.PredictionResultAdapter._build_candidates


def _inject_oracle(self, decision, candidate_map):
    out = _orig_build_candidates(self, decision, candidate_map)
    if decision.status.value == "completed":
        from reaction_agent.schemas.candidate import Candidate
        from reaction_agent.schemas.common import Lane
        out.append(Candidate(
            candidate_id="oracle_injected", canonical_product="CC=O",
            lane=Lane.strict, origin="oracle"))
    return out


def _noop_reject_forbidden_fields(self, structured):
    return None


def _noop_assert_all_strict(candidates):
    return None


_orig_mutate = run_mod.ImmutableRunStore.mutate


def _mutate_after_freeze(self, run_id, updates):
    run = self.get(run_id)
    mutated = run.manifest.model_copy(update=updates)
    self._runs[run_id] = run_mod.RuntimeRun(mutated)
    return self._runs[run_id]


def _drop_competing_transform():
    return {k: v for k, v in ce_mod._CONTEXT_TYPE_MAP.items()
            if k != "competing_transform"}


def _noop_system_failure_guard(self, decision):
    return None


_orig_validate_and_build = adapter_mod.PredictionResultAdapter.validate_and_build


def _swallow_invariant(self, decision, **kwargs):
    try:
        return _orig_validate_and_build(self, decision, **kwargs)
    except ValueError:
        return None


_orig_decide_abstention = abst_mod.decide_abstention


def _strip_abstention_reason(*args, **kwargs):
    d = _orig_decide_abstention(*args, **kwargs)
    return d.model_copy(update={"primary_reason": ""})


def _always_match_recompute(manifest):
    return manifest.result_hash


def _verify_always_ok(self):
    """P4-R1-F M13: a broken verify that always claims integrity."""
    return self._manifest.result_hash


def _lenient_baselines(mutations):
    return []


MUTATIONS = [
    {
        "id": "M01", "name": "duplicate evidence rows counted independent",
        "check_fn": check_g02_evidence_identity,
        "patch": (evid_mod, "_same_dimension", _same_dimension_none),
        "expected_failure_code": "independent_count != 3",
    },
    {
        "id": "M02", "name": "source mirror relabeled independent",
        "check_fn": check_g02_evidence_identity,
        "patch": (evid_mod, "_same_dimension", _skip_same_publication),
        "expected_failure_code": "independent_count != 3",
    },
    {
        "id": "M03", "name": "database absence turned negative",
        "check_fn": check_g04_counterevidence,
        "patch": (ce_mod, "_reject_forbidden", _noop),
        "expected_failure_code": "database absence accepted",
    },
    {
        "id": "M04", "name": "test evidence inserted into support",
        "check_fn": check_g03_support,
        "patch": (support_mod, "_all_evidence_ids", _add_test_evidence),
        "expected_failure_code": "TEST_EVIDENCE_ISOLATION",
    },
    {
        "id": "M05", "name": "oracle output inserted into primary",
        "check_fn": check_g08_prediction_result,
        "patch": (adapter_mod.PredictionResultAdapter, "_build_candidates",
                  _inject_oracle),
        "expected_failure_code": "oracle_injected",
    },
    {
        "id": "M06", "name": "probability/confidence field injected",
        "check_fn": check_g01_schemas,
        "patch": (adapter_mod.PredictionResultAdapter,
                  "_reject_forbidden_fields", _noop_reject_forbidden_fields),
        "expected_failure_code": "forbidden confidence accepted",
    },
    {
        "id": "M07", "name": "strict candidate assigned generalized lane",
        "check_fn": check_g05_ranker,
        "patch": (ranker_mod, "_assert_all_strict", _noop_assert_all_strict),
        "expected_failure_code": "generalized candidate accepted",
    },
    {
        "id": "M08", "name": "rank changed after freeze",
        "check_fn": check_g09_immutable_run,
        "patch": (run_mod.ImmutableRunStore, "mutate", _mutate_after_freeze),
        "expected_failure_code": "frozen run mutated",
    },
    {
        "id": "M09", "name": "conflict removed from trace",
        "check_fn": check_g04_counterevidence,
        "patch": (ce_mod, "_CONTEXT_TYPE_MAP", _drop_competing_transform()),
        "expected_failure_code": "competing transform counterevidence missing",
    },
    {
        "id": "M10", "name": "system failure relabeled abstained",
        "check_fn": check_g08_prediction_result,
        "patch": [
            (adapter_mod.PredictionResultAdapter,
             "_assert_system_failure_not_abstention", _noop_system_failure_guard),
            (adapter_mod.PredictionResultAdapter,
             "_assert_reason_consistency", _noop_system_failure_guard),
        ],
        "expected_failure_code": "system failure accepted as scientific abstention",
    },
    {
        "id": "M11", "name": "abstention reason deleted",
        "check_fn": check_g07_abstention,
        "patch": (abst_mod, "decide_abstention", _strip_abstention_reason),
        "expected_failure_code": "abstention primary_reason missing",
    },
    {
        "id": "M12", "name": "completed result with zero candidates",
        "check_fn": check_g08_prediction_result,
        "patch": (adapter_mod.PredictionResultAdapter, "validate_and_build",
                  _swallow_invariant),
        "expected_failure_code": "completed with 0 candidates accepted",
    },
    {
        "id": "M13", "name": "altered result hash",
        "check_fn": check_g09_immutable_run,
        "patch": (run_mod.RuntimeRun, "verify", _verify_always_ok),
        "expected_failure_code": "altered result hash accepted at create",
    },
    {
        "id": "M14", "name": "stored PASS status with failing (BLOCKED-baseline) artifact",
        "check_fn": check_m14_stored_pass_artifact,
        "patch": (__import__("sys").modules[__name__], "_pass_capable_baselines",
                  _lenient_baselines),
        "expected_failure_code": "forged BLOCKED-baseline report NOT flagged",
    },
]


# =====================================================================
# Runner + results
# =====================================================================

def run_all_mutations() -> list[dict]:
    results = []
    for m in MUTATIONS:
        r = _run_one(m)
        results.append(r)
        # incremental write so gate G10 can validate mid-run state.
        os.makedirs(REPORT_DIR, exist_ok=True)
        _write_results(results)
    return results


def _write_results(results: list[dict]) -> None:
    caught = sum(1 for r in results if r.get("caught"))
    os.makedirs(REPORT_DIR, exist_ok=True)
    payload = {
        "runner_version": "p4-mutation-runner-1",
        "total": len(results),
        "caught": caught,
        "escaped": sum(1 for r in results if r.get("escaped")),
        "errored": sum(1 for r in results if r.get("error")),
        "baseline_valid": not _pass_capable_baselines(results),
        "mutations": results,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)


def validate_mutation_results() -> dict:
    """Read + validate the mutation results JSON (used by gate G10)."""
    try:
        with open(RESULTS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"mutations": [], "total": 0, "caught": 0,
                "baseline_valid": False, "baseline_issues": ["results file missing"]}
    mutations = data.get("mutations", [])
    issues = _pass_capable_baselines(mutations)
    return {
        "mutations": mutations,
        "total": data.get("total", len(mutations)),
        "caught": data.get("caught", sum(1 for m in mutations if m.get("caught"))),
        "baseline_valid": not issues,
        "baseline_issues": issues,
    }


def main() -> int:
    print("=" * 60)
    print("P4 MUTATIONS — PASS->FAIL on PASS-capable fixture")
    print("=" * 60)
    results = run_all_mutations()
    caught = sum(1 for r in results if r.get("caught"))
    for r in results:
        status = "CAUGHT" if r.get("caught") else (
            "ESCAPED" if r.get("escaped") else
            "ERROR" if r.get("error") else "MISSED")
        print(f"  [{status}]  {r['mutation_id']}: {r['mutation']}")
    print()
    print(f"Caught: {caught}/{len(results)}")
    print(f"Results: {RESULTS_PATH}")
    return 0 if caught == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
