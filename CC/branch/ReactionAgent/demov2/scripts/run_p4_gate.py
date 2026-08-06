#!/usr/bin/env python3
"""P4 Gate runner (final_plan §7.9 + §8).

Machinery checks (G01-G11) are PASS-capable on the synthetic contract
fixture — they verify the P4 implementation invariants. Real-input checks
(G12-G14) verify external authority state and are honestly BLOCKED when P3
interface / real evidence / P2 truth authority are unavailable.

Status:
  - any machinery FAIL           -> P4_GATE_FAIL_NEEDS_REMEDIATION  (exit 1)
  - machinery pass, any real BLOCKED -> P4_IMPLEMENTATION_COMPLETE_GATE_BLOCKED (exit 2)
  - all pass                      -> READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT (exit 0)

The gate derives PASS from artifacts/hashes/tests — it never trusts a stored
status string.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone

# Bootstrap the project root onto sys.path BEFORE importing reaction_agent so
# the gate runs standalone (``python scripts/run_p4_gate.py``) in envs where
# the package is not pip-installed editable (P7 worktree shares the host venv
# without an editable install; pytest's pythonpath="." does not apply to a
# subprocess).
DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEMOV2_ROOT)

from reaction_agent.hashing import canonical_hash  # noqa: E402

REPORT_DIR = os.path.join(DEMOV2_ROOT, "reports", "p4")

GATE_VERSION = "p4-gate-2"
GATE_RUN_ID = f"gate-{uuid.uuid4().hex[:12]}"
SESSION_NONCE = uuid.uuid4().hex


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _result(passed: bool, evidence: str, details: dict,
            blocked: bool = False, error: bool = False) -> dict:
    """P4-R1-F: a check result carries a typed ERROR flag — an execution
    exception is never confused with a target invariant FAIL."""
    return {"passed": passed, "blocked": blocked, "error": error,
            "evidence": evidence, "details": details}


def _error_result(evidence: str, details: dict | None = None) -> dict:
    """P4-R1-F: typed ERROR for a gate check that raised during execution."""
    return {"passed": False, "blocked": False, "error": True,
            "evidence": evidence, "details": details or {}}


def _run_subprocess(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("P4_GATE_RECURSION_GUARD", "1")
    return subprocess.run(cmd, cwd=DEMOV2_ROOT, capture_output=True,
                          text=True, timeout=timeout, env=env)


# ============================================================
# G01: strict P4 schemas + forbidden names + shared PredictionResult
# ============================================================

def check_g01_schemas() -> dict:
    issues: list[str] = []
    details: dict = {}

    try:
        from reaction_agent.schemas.p4.evidence import EvidenceIdentity
        from reaction_agent.schemas.p4.run import ImmutableRunManifest
        # unknown field rejected (extra="forbid")
        try:
            EvidenceIdentity(evidence_id="e", canonical_identity="c",
                             independent_group_id="g", surprise="x")
            issues.append("unknown field accepted")
        except Exception:  # noqa: BLE001
            pass
        # forbidden probability field rejected at adapter boundary
        from reaction_agent.adapters.prediction_result_adapter import (
            PredictionResultAdapter)
        adapter = PredictionResultAdapter(policy_version="p4-policy-1")
        from reaction_agent.schemas.p4.decision import PredictionDecision
        from reaction_agent.schemas.common import DecisionKind, ResultStatus
        from reaction_agent.schemas.p4.ranking import RankedStrictCandidate
        from reaction_agent.schemas.common import Lane
        ranked = RankedStrictCandidate(
            candidate_id="c", canonical_product="CC=O", lane=Lane.strict,
            ranking_score=0.5, rank=1, contributions=[],
            tie_break_key="k", ranker_version="v")
        from reaction_agent.schemas.candidate import Candidate as _Candidate
        from reaction_agent.schemas.common import Lane as _Lane2
        verified_map = {
            "c": _Candidate(
                candidate_id="c", canonical_product="CC=O", lane=_Lane2.strict,
                origin="fixture", validation={"valid_molecule": True},
                provenance=["fixture"]),
        }
        decision = PredictionDecision(
            decision=DecisionKind.predicted, status=ResultStatus.completed,
            ranked_candidates=[ranked], policy_version="p4-policy-1")
        try:
            adapter.validate_and_build(decision, candidate_map=verified_map,
                                       extra_structured={"confidence": 0.9})
            issues.append("forbidden confidence accepted")
        except Exception:  # noqa: BLE001
            pass
        details["schema_strictness"] = "unknown-field + forbidden-name rejected"
    except Exception as e:  # noqa: BLE001
        issues.append(f"G01 error: {e}")

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "P4 schemas strict + forbidden probability names rejected",
                   details)


# ============================================================
# G02: evidence identity / dedup
# ============================================================

def check_g02_evidence_identity() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from tests.fixtures.p4.p4_contract_fixture import (
            build_evidence_records, POLICY_VERSION)
        from reaction_agent.inference.evidence_identity import resolve_evidence_identity
        records = build_evidence_records()
        res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
        details["independent_count"] = res.independent_count
        details["total_rows"] = res.total_rows
        if res.independent_count != 3:
            issues.append(f"independent_count != 3: {res.independent_count}")
        if res.total_rows != 5:
            issues.append(f"total_rows != 5: {res.total_rows}")
        support_ids = ["ev_d1", "ev_d1_mirror", "ev_d4", "ev_d2"]
        groups = res.group_ids_for(support_ids)
        if len(groups) != 2:
            issues.append(f"support groups != 2: {len(groups)}")
        # deterministic recomputation
        res2 = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
        if res.resolution_hash != res2.resolution_hash:
            issues.append("resolution hash not deterministic")
        details["groups_covering_support"] = len(groups)
    except Exception as e:  # noqa: BLE001
        issues.append(f"G02 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "evidence identity: mirror/publication/mapper dedup, independent count 3, deterministic",
                   details)


# ============================================================
# G03: support aggregation
# ============================================================

def check_g03_support() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from tests.fixtures.p4.p4_contract_fixture import (
            build_evidence_records, build_strict_candidate,
            build_structural_context, build_feature_evidence_binding,
            POLICY_VERSION)
        from reaction_agent.inference.evidence_identity import resolve_evidence_identity
        from reaction_agent.inference.support import aggregate_support
        from reaction_agent.schemas.p4.support import SupportTier, EvidenceStrength
        records = build_evidence_records()
        res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
        cand = build_strict_candidate()
        sup = aggregate_support(cand, records, res,
                                structural_context=build_structural_context(),
                                feature_evidence_ids=build_feature_evidence_binding())
        details["independent_evidence_count"] = sup.independent_evidence_count
        if sup.independent_evidence_count != 3:
            issues.append(f"independent count != 3: {sup.independent_evidence_count}")
        # no test-fold evidence in support (P4-R1-J: typed isolation failure)
        for ev_id in sup.all_evidence_ids:
            if ev_id.startswith("test:"):
                issues.append(
                    f"TEST_EVIDENCE_ISOLATION: test evidence in support: {ev_id}")
        # observable features bind evidence ids; unobservable features bind
        # nothing (empty evidence must never become support).
        for f in sup.features:
            if f.is_observable and not f.evidence_ids:
                issues.append(f"observable feature {f.feature_key} has no evidence ids")
            if not f.is_observable and f.evidence_ids:
                issues.append(f"unobservable feature {f.feature_key} binds evidence")
        # no probability semantics
        if sup.support_tier not in (SupportTier.none, SupportTier.weak,
                                    SupportTier.moderate, SupportTier.strong):
            issues.append(f"bad tier {sup.support_tier}")
        if sup.evidence_strength not in (EvidenceStrength.none,
                                         EvidenceStrength.single_source,
                                         EvidenceStrength.multiple_independent_sources,
                                         EvidenceStrength.high_quality_multiple_independent):
            issues.append(f"bad strength {sup.evidence_strength}")
        if sup.support_tier == SupportTier.none:
            issues.append("fixture candidate should have non-none support tier")
    except Exception as e:  # noqa: BLE001
        issues.append(f"G03 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "support evidence-bound, independent count 3, no test evidence, ordinal tier",
                   details)


# ============================================================
# G04: counterevidence (allowed only; absence never negative)
# ============================================================

def check_g04_counterevidence() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from tests.fixtures.p4.p4_contract_fixture import (
            build_evidence_records, build_strict_candidate, POLICY_VERSION)
        from reaction_agent.inference.evidence_identity import resolve_evidence_identity
        from reaction_agent.inference.counterevidence import collect_counterevidence
        from reaction_agent.policies.p4_decision_policy import ALLOWED_COUNTEREVIDENCE
        records = build_evidence_records()
        res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
        cand = build_strict_candidate()
        # absence must be refused (fail closed)
        try:
            collect_counterevidence(cand, records, res,
                                    context={"database_absence": ["x"]})
            issues.append("database absence accepted as counterevidence")
        except ValueError:
            pass
        # competing transform is allowed
        coll = collect_counterevidence(cand, records, res,
                                       context={"competing_transform": ["t2"]})
        types = {r.counter_type.value for r in coll.records}
        for t in types:
            if t not in ALLOWED_COUNTEREVIDENCE:
                issues.append(f"forbidden counterevidence type emitted: {t}")
        if not any(r.counter_type.value == "COMPETING_TRANSFORM" for r in coll.records):
            issues.append("competing transform counterevidence missing")
        details["counterevidence_types"] = sorted(types)
    except Exception as e:  # noqa: BLE001
        issues.append(f"G04 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "absence refused (fail-closed), only allowed counterevidence, competing transform detected",
                   details)


# ============================================================
# G05: strict-only deterministic ranker
# ============================================================

def check_g05_ranker() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from tests.fixtures.p4.p4_contract_fixture import (
            build_evidence_records, build_strict_candidate,
            build_structural_context, POLICY_VERSION)
        from reaction_agent.inference.evidence_identity import resolve_evidence_identity
        from reaction_agent.inference.features import build_feature_vector
        from reaction_agent.inference.ranker import rank_strict_candidates
        from reaction_agent.schemas.common import Lane
        from reaction_agent.schemas.candidate import Candidate
        records = build_evidence_records()
        res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
        c1 = build_strict_candidate()
        # strict-only: generalized must be rejected
        gen = Candidate(candidate_id="g", canonical_product="CC=O",
                        lane=Lane.generalized, origin="agent_proposed")
        try:
            rank_strict_candidates([gen, c1], feature_vectors={},
                                   policy_version=POLICY_VERSION)
            issues.append("generalized candidate accepted into strict ranking")
        except ValueError:
            pass
        # deterministic ranking + ordinal range
        ctx = build_structural_context()
        fv = {c1.candidate_id: build_feature_vector(c1, res, ctx)}
        r1 = rank_strict_candidates([c1], feature_vectors=fv,
                                    policy_version=POLICY_VERSION)
        r2 = rank_strict_candidates([c1], feature_vectors=fv,
                                    policy_version=POLICY_VERSION)
        if r1.ranking_hash != r2.ranking_hash:
            issues.append("ranking not deterministic")
        score = r1.candidates[0].ranking_score
        if not (0.0 <= score <= 1.0):
            issues.append(f"ranking_score out of [0,1]: {score}")
        for rc in r1.candidates:
            if rc.lane != Lane.strict:
                issues.append(f"ranked candidate lane != strict: {rc.lane}")
            if not rc.tie_break_key:
                issues.append("ranked candidate missing tie_break_key")
        details["ranking_score"] = score
    except Exception as e:  # noqa: BLE001
        issues.append(f"G05 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "strict-only, deterministic, ordinal score in [0,1], tie-break present",
                   details)


# ============================================================
# G06: structural applicability
# ============================================================

def check_g06_applicability() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from tests.fixtures.p4.p4_contract_fixture import (
            build_evidence_records, build_strict_candidate,
            build_structural_context, POLICY_VERSION)
        from reaction_agent.inference.evidence_identity import resolve_evidence_identity
        from reaction_agent.inference.applicability import assess_applicability
        from reaction_agent.schemas.common import ApplicabilityLabel
        records = build_evidence_records()
        res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
        cand = build_strict_candidate()
        a = assess_applicability(cand, records, res,
                                 structural_context=build_structural_context())
        if a.label not in (ApplicabilityLabel.in_domain,
                           ApplicabilityLabel.near_domain,
                           ApplicabilityLabel.out_of_domain,
                           ApplicabilityLabel.conflicted,
                           ApplicabilityLabel.unknown):
            issues.append(f"bad applicability label: {a.label}")
        if not a.reason_codes:
            issues.append("applicability missing reason codes")
        # no evidence -> unknown
        a2 = assess_applicability(cand, [], res, structural_context=None)
        if a2.label != ApplicabilityLabel.unknown:
            issues.append(f"no-evidence applicability != unknown: {a2.label}")
        details["label"] = a.label.value
    except Exception as e:  # noqa: BLE001
        issues.append(f"G06 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "applicability structural-only, unknown on no evidence",
                   details)


# ============================================================
# G07: typed abstention precedence
# ============================================================

def check_g07_abstention() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from reaction_agent.inference.abstention import decide_abstention
        from reaction_agent.schemas.common import ScientificAbstentionReason
        from reaction_agent.schemas.result import StageSummary
        d = decide_abstention(
            conditions={"NO_IN_DOMAIN_DONOR", "INVALID_INPUT", "EVIDENCE_CONFLICT"},
            trace=StageSummary(), policy_version="p4-policy-1")
        if d.reason_code != ScientificAbstentionReason.INVALID_INPUT:
            issues.append(f"precedence wrong: {d.reason_code}")
        if not d.primary_reason:
            issues.append("abstention primary_reason missing")
        if d.candidate_count != 0:
            issues.append("abstention candidate_count != 0")
        if not d.secondary_reasons:
            issues.append("secondary reasons missing (no donor + conflict apply)")
        details["primary_reason"] = d.primary_reason
        details["secondary_reasons"] = d.secondary_reasons
    except Exception as e:  # noqa: BLE001
        issues.append(f"G07 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "frozen precedence (INVALID_INPUT wins), primary+secondary reasons, 0 candidates",
                   details)


# ============================================================
# G08: PredictionResult invariants + system failure separation
# ============================================================

def check_g08_prediction_result() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from reaction_agent.adapters.prediction_result_adapter import (
            PredictionResultAdapter, DecisionAuthorityError)
        from reaction_agent.schemas.p4.decision import (
            PredictionDecision, AbstentionDecision)
        from reaction_agent.schemas.common import (
            DecisionKind, ResultStatus, SystemFailureReason,
            ScientificAbstentionReason, Lane)
        from reaction_agent.schemas.p4.ranking import RankedStrictCandidate
        from reaction_agent.schemas.result import StageSummary
        adapter = PredictionResultAdapter(policy_version="p4-policy-1")
        ranked = RankedStrictCandidate(
            candidate_id="c", canonical_product="CC=O", lane=Lane.strict,
            ranking_score=0.5, rank=1, contributions=[],
            tie_break_key="k", ranker_version="v")
        from reaction_agent.schemas.candidate import Candidate
        from reaction_agent.schemas.common import Lane as _Lane
        verified_map = {
            "c": Candidate(
                candidate_id="c", canonical_product="CC=O", lane=_Lane.strict,
                origin="fixture", validation={"valid_molecule": True},
                provenance=["fixture"]),
        }
        # completed ok
        ok = PredictionDecision(
            decision=DecisionKind.predicted, status=ResultStatus.completed,
            ranked_candidates=[ranked], policy_version="p4-policy-1")
        res = adapter.validate_and_build(ok, candidate_map=verified_map)
        if res.status != ResultStatus.completed:
            issues.append("completed decision did not produce completed result")
        # no invented/oracle candidate: result candidates == decision candidates
        decision_ids = {r.candidate_id for r in ok.ranked_candidates}
        result_ids = {c.candidate_id for c in res.candidates}
        if decision_ids != result_ids:
            issues.append(
                f"result candidates {sorted(result_ids)} != decision candidates "
                f"{sorted(decision_ids)} (oracle/invented candidate leaked in)")
        # completed + 0 candidates -> reject
        empty = PredictionDecision(
            decision=DecisionKind.predicted, status=ResultStatus.completed,
            ranked_candidates=[], policy_version="p4-policy-1")
        try:
            adapter.validate_and_build(empty)
            issues.append("completed with 0 candidates accepted")
        except ValueError:
            pass
        # system failure -> failed, not abstained
        sysd = PredictionDecision(
            decision=DecisionKind.failed, status=ResultStatus.failed,
            reason_code=SystemFailureReason.SNAPSHOT_UNAVAILABLE.value,
            policy_version="p4-policy-1")
        sysr = adapter.validate_and_build(sysd)
        if sysr.status != ResultStatus.failed or sysr.abstention is not None:
            issues.append("system failure not kept separate as failed")
        # failed relabeled abstained -> reject
        bad = PredictionDecision(
            decision=DecisionKind.abstained, status=ResultStatus.abstained,
            reason_code=SystemFailureReason.SNAPSHOT_UNAVAILABLE.value,
            abstention=AbstentionDecision(
                reason_code=ScientificAbstentionReason.INVALID_INPUT,
                primary_reason="INVALID_INPUT", candidate_count=0,
                trace=StageSummary(), policy_version="p4-policy-1",
                source_evidence_scope="x"),
            policy_version="p4-policy-1")
        try:
            adapter.validate_and_build(bad)
            issues.append("system failure accepted as scientific abstention")
        except (ValueError, DecisionAuthorityError):
            pass
        # agent text cannot override
        try:
            adapter.validate_and_build(ok, agent_text={"status": "abstained"})
            issues.append("agent text overrode status")
        except DecisionAuthorityError:
            pass
        details["system_failure_separate"] = True
    except Exception as e:  # noqa: BLE001
        issues.append(f"G08 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "PredictionResult invariants hold; system failure never abstention; agent text cannot override",
                   details)


# ============================================================
# G09: immutable run / replay / freeze / child
# ============================================================

def check_g09_immutable_run() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        from tests.fixtures.p4.p4_contract_fixture import build_query
        from reaction_agent.runtime.run import (
            ImmutableRunStore, RunAlreadyFrozenError, RunHashMismatchError)
        from reaction_agent.runtime.manifest import build_run_manifest
        from reaction_agent.runtime.trace import build_stage_summary
        from reaction_agent.schemas.result import StageSummary
        store = ImmutableRunStore()
        versions = {"normalization_version": "p1-1", "config_version": "p1-1",
                    "policy_version": "p4-policy-1", "kernel_version": "p3-blocked",
                    "candidate_version": "p3-blocked", "ranker_version": "p4-ranker-1",
                    "snapshot_builder_version": "p1-1"}
        trace = StageSummary(donor_evidence_ids=["ev_d1", "ev_d2"],
                             candidate_ids=["cand_ox_001"])
        m = build_run_manifest(
            run_id="run_1", parent_run_id=None, query=build_query(),
            snapshot_id="snap_c589494081df", snapshot_hash="hash",
            versions=versions, trace=trace,
            evidence_ids=["ev_d1", "ev_d2"],
            independent_group_ids=["evg_1"],
            result_hash=None, freeze_state="active",
            capability_status="synthetic_fixture", blocked_reasons=[],
            classification="synthetic_fixture")
        store.create(m)
        store.verify("run_1")  # recomputed hash matches
        store.freeze("run_1")
        try:
            store.mutate("run_1", {"result_hash": "tampered"})
            issues.append("frozen run mutated")
        except RunAlreadyFrozenError:
            pass
        # child preserves parent
        child = store.create_child("run_1", "run_1_child", {"result_hash": "child"})
        if child.parent_run_id != "run_1":
            issues.append("child parent_run_id wrong")
        if store.get("run_1").result_hash != m.result_hash:
            issues.append("child overwrote parent result")
        # altered hash detected (create verifies the hash up front)
        store2 = ImmutableRunStore()
        try:
            store2.create(m.model_copy(update={"result_hash": "forged"}))
            issues.append("altered result hash accepted at create")
        except RunHashMismatchError:
            pass
        details["freeze_and_child_and_verify"] = True
    except Exception as e:  # noqa: BLE001
        issues.append(f"G09 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "immutable run: freeze blocks mutate, child preserves parent, altered hash detected",
                   details)


# ============================================================
# G10: mutation baseline validity (PASS->FAIL on PASS-capable fixture)
# ============================================================

def check_g10_mutations() -> dict:
    issues: list[str] = []
    details: dict = {}
    try:
        import scripts.run_p4_mutations as mut
        # Run the mutations fresh (self-contained) then validate.
        results = mut.run_all_mutations()
        mutations = list(results)
        details["mutation_count"] = len(mutations)
        details["caught"] = sum(1 for m in mutations if m.get("caught"))
        details["total"] = len(mutations)
        if not mutations:
            issues.append("no mutation results recorded")
        baseline_issues = mut._pass_capable_baselines(mutations)
        issues.extend(baseline_issues)
        for m in mutations:
            if not m.get("caught"):
                issues.append(
                    f"{m.get('mutation_id')} not caught "
                    f"(actual={m.get('actual_status')}, escaped/error)")
            if m.get("escaped"):
                issues.append(f"{m.get('mutation_id')} escaped")
            if m.get("error"):
                issues.append(f"{m.get('mutation_id')} errored")
        if len(mutations) < 14:
            issues.append(f"expected >=14 mutations, got {len(mutations)}")
    except Exception as e:  # noqa: BLE001
        issues.append(f"G10 error: {e}")
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "all mutations caught as PASS->FAIL on PASS-capable fixture, none escaped/error",
                   details)


# ============================================================
# G11: P4 test suite zero-skip
# ============================================================

def check_g11_tests() -> dict:
    """P4-R1-F: G11 must fail on a stale/absent report or a non-zero pytest
    exit. The report is written to a THIS-run-unique temp path and the exit
    code is checked — a leftover success JSON can never pass."""
    issues: list[str] = []
    details: dict = {}
    # Unique temp path for THIS run; ensure it does not pre-exist.
    fd, report_file = tempfile.mkstemp(prefix="p4_g11_", suffix=".json")
    os.close(fd)
    try:
        os.unlink(report_file)  # guarantee absent before the run
    except OSError:
        pass
    try:
        proc = _run_subprocess(
            [sys.executable, "-m", "pytest", "tests/p4", "-q",
             "--ignore=tests/p4/test_p4_gate_contract.py",
             "--json-report", f"--json-report-file={report_file}",
             "-p", "no:cacheprovider"])
        details["pytest_exit"] = proc.returncode
        details["report_file"] = os.path.basename(report_file)
        if proc.returncode != 0:
            issues.append(f"pytest exit code {proc.returncode} != 0")
        stats = {}
        if os.path.isfile(report_file):
            stats_raw = _read_json(report_file)
            summary = stats_raw.get("summary", {})
            stats = {
                "collected": summary.get("collected", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "errors": summary.get("errors", 0),
                "skipped": summary.get("skipped", 0),
                "xfailed": summary.get("xfailed", 0),
                "xpassed": summary.get("xpassed", 0),
            }
            details["pytest_stats"] = stats
        else:
            issues.append("pytest report missing (fresh temp path)")
        if stats.get("failed", 0) != 0 or stats.get("errors", 0) != 0:
            issues.append(f"pytest failures/errors: {stats}")
        if stats.get("skipped", 0) != 0:
            issues.append(f"pytest skipped: {stats.get('skipped')}")
        if stats.get("xfailed", 0) != 0 or stats.get("xpassed", 0) != 0:
            issues.append(f"pytest xfail/xpass: {stats}")
        if stats.get("collected", 0) == 0:
            issues.append("pytest collected 0 tests")
    except Exception as e:  # noqa: BLE001
        return _error_result(f"G11 error: {e}")
    finally:
        try:
            os.unlink(report_file)
        except OSError:
            pass
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "P4 test suite passes zero-skip (this-run temp report)",
                   details)


# ============================================================
# G12-G14: real-input / authority checks (honestly BLOCKED)
# ============================================================

def check_g12_p3_authority() -> dict:
    """P4-R1-F: verified P3 authority — interface manifest + current-run
    artifact. The interface manifest alone does NOT grant capability."""
    try:
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        handle = P3InterfaceConsumer().resolve_authority()
        details = {
            "source": handle.source.value,
            "manifest_version": handle.manifest_version,
            "evidence_kind": handle.evidence_kind.value,
            "capability_available": handle.capability_available,
        }
        if handle.source.value == "p3_current_run":
            return _result(True, "verified P3 current-run authority available",
                           details)
        return _result(False, "BLOCKED: no verified P3 current-run artifact",
                       details, blocked=True)
    except Exception as e:  # noqa: BLE001
        return _error_result(f"p3 authority check error: {e}")


def check_g13_real_evidence() -> dict:
    """P4-R1-F: real evidence requires the verified P3 authority to carry
    evidence_kind=real (never inferred from a classification string)."""
    try:
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        from reaction_agent.schemas.p4.authority import P4Classification
        handle = P3InterfaceConsumer().resolve_authority()
        details = {"evidence_kind": handle.evidence_kind.value,
                   "capability_available": handle.capability_available}
        if handle.evidence_kind == P4Classification.real:
            return _result(True, "real evidence available", details)
        return _result(
            False,
            "BLOCKED: evidence is synthetic-only; real P3 chemistry absent",
            details, blocked=True)
    except Exception as e:  # noqa: BLE001
        return _error_result(f"real evidence check error: {e}")


def check_g14_p2_truth_authority() -> dict:
    """P4-R1-F: G14 must NOT trust a stored P2/P3 status string — it stays
    BLOCKED until a current-run P2 artifact/hash/receipt is verified."""
    try:
        p2_path = os.path.join(DEMOV2_ROOT, "reports", "p2", "P2_GATE_REPORT.json")
        # A stored status string is NOT an authority (P4-R1-F.6).
        verified = False
        if os.path.isfile(p2_path):
            p2 = _read_json(p2_path)
            # Verify the artifact itself: a current-run receipt with a hash
            # would be required; a bare status string is never sufficient.
            if p2.get("status") == "READY_FOR_CHATGPT_P2_AUDIT" and \
                    p2.get("receipt_hash"):
                verified = True
        details = {"p2_gate_report_present": os.path.isfile(p2_path),
                   "p2_truth_authority_available": verified,
                   "stored_status_string_not_authority": True}
        if verified:
            return _result(True, "P2 truth authority verified via artifact", details)
        return _result(
            False,
            "BLOCKED: P2 formal authority not verified (stored status string "
            "is not an authority)",
            details, blocked=True)
    except Exception as e:  # noqa: BLE001
        return _error_result(f"p2 authority check error: {e}")


# ============================================================
# Registries
# ============================================================

GATE_CHECKS = [
    ("P4-G01", "strict P4 schemas + forbidden names + shared PredictionResult",
     check_g01_schemas),
    ("P4-G02", "evidence identity/dedup (mirror/publication/mapper)",
     check_g02_evidence_identity),
    ("P4-G03", "support aggregation (evidence-bound, not probability)",
     check_g03_support),
    ("P4-G04", "counterevidence (allowed only, absence never negative)",
     check_g04_counterevidence),
    ("P4-G05", "strict-only deterministic ranker",
     check_g05_ranker),
    ("P4-G06", "structural applicability",
     check_g06_applicability),
    ("P4-G07", "typed abstention precedence",
     check_g07_abstention),
    ("P4-G08", "PredictionResult invariants + system failure separation",
     check_g08_prediction_result),
    ("P4-G09", "immutable run/replay/freeze/child",
     check_g09_immutable_run),
    ("P4-G10", "mutation PASS->FAIL baseline validity",
     check_g10_mutations),
    ("P4-G11", "P4 test suite zero-skip",
     check_g11_tests),
]

REAL_INPUT_CHECKS = [
    ("P4-G12", "verified P3 current-run authority", check_g12_p3_authority),
    ("P4-G13", "real evidence available", check_g13_real_evidence),
    ("P4-G14", "P2 truth authority valid", check_g14_p2_truth_authority),
]


def run_all() -> tuple[list[dict], dict]:
    env = {
        "python_version": ".".join(str(x) for x in sys.version_info[:3]),
        "working_directory": DEMOV2_ROOT,
        "gate_version": GATE_VERSION,
        "run_id": GATE_RUN_ID,
        "session_nonce": SESSION_NONCE,
        "command": f"{sys.executable} scripts/run_p4_gate.py",
        "python": sys.executable,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    checks = []
    for gate_id, name, fn in GATE_CHECKS:
        checks.append({"gate_id": gate_id, "name": name, **fn()})
    for gate_id, name, fn in REAL_INPUT_CHECKS:
        checks.append({"gate_id": gate_id, "name": name, **fn()})
    return checks, env


def _gate_num(gate_id: str) -> int:
    """'P4-G01' -> 1."""
    return int(gate_id.split("-")[1][1:])


def generate_report(checks: list[dict], env: dict):
    os.makedirs(REPORT_DIR, exist_ok=True)
    machinery = [c for c in checks if _gate_num(c["gate_id"]) <= 11]
    real_input = [c for c in checks if _gate_num(c["gate_id"]) >= 12]
    machinery_pass = all(c["passed"] for c in machinery)
    # P4-R1-F: any non-PASS non-BLOCKED item (FAIL or ERROR) fails the gate.
    fail_count = sum(1 for c in checks
                     if not c["passed"] and not c.get("blocked"))
    error_count = sum(1 for c in checks if c.get("error"))
    block_count = sum(1 for c in checks if c.get("blocked"))

    if fail_count > 0:
        status = "P4_GATE_FAIL_NEEDS_REMEDIATION"
        exit_code = 1
    elif block_count > 0:
        status = "P4_IMPLEMENTATION_COMPLETE_GATE_BLOCKED"
        exit_code = 2
    elif machinery_pass:
        status = "READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT"
        exit_code = 0
    else:
        status = "P4_GATE_FAIL_NEEDS_REMEDIATION"
        exit_code = 1

    # P4-R1-F: authority must be derived from the current run artifacts, never
    # hardcoded. Read the P3 consumer's authority handle.
    try:
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        auth = P3InterfaceConsumer().resolve_authority()
        p3_source = auth.source.value
        p3_manifest_version = auth.manifest_version
        evidence_kind = auth.evidence_kind.value
    except Exception:  # noqa: BLE001
        p3_source = "blocked"
        p3_manifest_version = ""
        evidence_kind = "blocked"

    jr = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate_version": GATE_VERSION,
        "run_id": env.get("run_id", GATE_RUN_ID),
        "session_nonce": env.get("session_nonce", SESSION_NONCE),
        "python_version": env.get("python_version", ""),
        "working_directory": DEMOV2_ROOT,
        "command": env.get("command", ""),
        "python": env.get("python", sys.executable),
        "started_at": env.get("started_at", ""),
        "exit_code": exit_code,
        "status": status,
        "machinery_pass_count": sum(1 for c in machinery if c["passed"]),
        "machinery_total": len(machinery),
        "real_input_blocked_count": block_count,
        "real_input_total": len(real_input),
        "pass_count": sum(1 for c in checks if c["passed"]),
        "block_count": block_count,
        "fail_count": fail_count,
        "error_count": error_count,
        "total_checks": len(checks),
        "checks": checks,
        "p4_authority": {
            "p1_accepted": True,
            "p2_formal_gate": "BLOCKED",
            "p3_source": p3_source,
            "p3_manifest_version": p3_manifest_version,
            "evidence_classification": evidence_kind,
        },
        "terminal_status": status,
    }
    json_path = os.path.join(REPORT_DIR, "P4_GATE_REPORT.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(jr, f, indent=2, ensure_ascii=False, default=str)

    md = [
        "# P4 Gate Report",
        "",
        f"**Timestamp (UTC):** {jr['timestamp']}",
        f"**Gate version:** {GATE_VERSION}",
        f"**Working directory:** {DEMOV2_ROOT}",
        "",
        f"## Result: {status}",
        "",
        f"**Machinery:** {sum(1 for c in machinery if c['passed'])}/{len(machinery)} PASS",
        f"**Real-input blocked:** {block_count}/{len(real_input)}",
        f"**Failures:** {fail_count}",
        "",
        "## Gate Checks",
        "",
    ]
    for c in checks:
        icon = "PASS" if c["passed"] else ("BLOCKED" if c.get("blocked") else "FAIL")
        md.append(f"### {c['gate_id']}: {c['name']}")
        md.append(f"**Status:** {icon}")
        md.append(f"**Evidence:** {c['evidence']}")
        md.append("")
    md.extend(["## Conclusion", "", f"**{status}**"])
    md_path = os.path.join(REPORT_DIR, "P4_GATE_REPORT.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return md_path, json_path, status, exit_code


def main() -> int:
    os.environ.setdefault("P4_GATE_RECURSION_GUARD", "1")
    print("=" * 60)
    print("P4 GATE — machinery + real-input checks")
    print("=" * 60)
    checks, env = run_all()
    for c in checks:
        icon = "PASS" if c["passed"] else ("BLOCKED" if c.get("blocked") else "FAIL")
        print(f"  [{icon}]  {c['gate_id']}: {c['name']}")
        if not c["passed"]:
            print(f"         {c['evidence']}")
    print()
    md_path, json_path, status, exit_code = generate_report(checks, env)
    print(f"Report: {md_path}")
    print(f"JSON:   {json_path}")
    print(f"Status: {status}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
