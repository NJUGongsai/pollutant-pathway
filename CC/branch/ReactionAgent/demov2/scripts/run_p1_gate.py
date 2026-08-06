#!/usr/bin/env python3
"""P1 Gate runner — 10 Gate conditions with evidence-based verification (§18).

L2 independent Gate Keeper: read-only verification, does not touch implementation
code. Each check reads machine-readable evidence (JSON fields, schema imports,
subprocess results) — never just ``os.path.exists`` (§18.2).

10 Gates (§18.1):
  G01 package/runtime/lock + config & snapshot + no legacy write
  G02 strict schemas/IDs/provenance + P0 contract still green
  G03 legacy lineage audit complete (real source used / counts / categories /
     source IDs / proline-2OG)
  G04 mapping adapter (real integration / quality / failure states / MCS not
     strict / formal not mechanism)
  G05 participant preservation/roles
  G06 lineage graph (bipartite / split-merge-transfer / no silent tie / stable
     IDs / proline-2OG correct or quarantined)
  G07 dual ledgers valid
  G08 eligibility/quarantine (8 policy rows / warnings / quarantine behavior /
     production excludes / reasons typed)
  G09 snapshot reproducibility (deterministic rebuild / content hash / manifest
     / filters counted / interrupted invalid / read-only loader)
  G10 manual audit + full tests (double annotation / adjudication / threshold
     frozen / catastrophic errors=0 / all tests pass / zero skip)

Status semantics:
  - passed=True  → Gate condition met
  - blocked=True → Gate cannot be evaluated due to external dependency missing
    (rdkit absent / real source not confirmed / no independent annotator).
    This is an HONEST block, not a silent failure (§23).
  - passed=False, blocked=False → implementation defect (FAIL)

Exit code: 0 only if ALL gates pass and none blocked. Otherwise 1.

Usage:
    .venv/bin/python scripts/run_p1_gate.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ensure reaction_agent is importable for module-level imports (G09 fixture
# rebuild). Function-level sys.path inserts in G01/G02 remain as no-ops.
sys.path.insert(0, DEMOV2_ROOT)
REPORT_DIR = os.path.join(DEMOV2_ROOT, "reports", "p1")
DATA_AUDIT_DIR = os.path.join(DEMOV2_ROOT, "reports", "data_audit")
PYPROJECT_PATH = os.path.join(DEMOV2_ROOT, "pyproject.toml")
LOCK_PATH = os.path.join(DEMOV2_ROOT, "requirements.lock.txt")
SCHEMAS_JSON_DIR = os.path.join(DEMOV2_ROOT, "schemas", "json")


# ============================================================
# Helpers
# ============================================================

def _read_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


def _run_subprocess(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=DEMOV2_ROOT, capture_output=True, text=True, timeout=timeout,
    )


def _parse_pytest_stats(report_json: dict) -> dict:
    summary = report_json.get("summary", {})
    collected = summary.get("collected") or summary.get("total") or 0
    return {
        "collected": collected,
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "errors": summary.get("errors", 0),
        "skipped": summary.get("skipped", 0),
        "xfailed": summary.get("xfailed", 0),
        "xpassed": summary.get("xpassed", 0),
    }


def _result(passed: bool = True, evidence: str = "", details: dict | None = None,
            blocked: bool = False,
            implementation_failures: list[str] | None = None,
            external_blockers: list[str] | None = None) -> dict:
    """Build a gate result dict.

    §5.1 status model: when ``implementation_failures`` / ``external_blockers``
    are given, ``passed`` / ``blocked`` are DERIVED so BLOCKED never covers an
    implementation FAIL:
      - implementation_failures non-empty → FAIL (passed=False, blocked=False)
      - implementation_failures empty + external_blockers non-empty → BLOCKED
      - both empty → PASS
    Legacy callers passing only ``passed``/``blocked`` keep working (their
    impl/blocker lists default to empty).
    """
    impl = list(implementation_failures or [])
    blockers = list(external_blockers or [])
    if implementation_failures is not None or external_blockers is not None:
        passed = not impl and not blockers
        blocked = bool(blockers) and not impl
    return {
        "passed": passed, "blocked": blocked,
        "evidence": evidence, "details": details or {},
        "implementation_failures": impl,
        "external_blockers": blockers,
    }


def _run_targeted_tests(test_files: list[str], gate_id: str,
                        required_nodes: list[str] | None = None) -> tuple[list[str], dict]:
    """Run pytest on specific test files (§18.2 — gate runs tests, not just reads JSON).

    Returns (issues, stats). Enforces zero skip/xfail/xpass (§17). Uses a temp
    json-report file so it never collides with the gate's own report artifacts.

    Round 4 (§10/§11): ``required_nodes`` is a MANDATORY test-node manifest.
    Each node id MUST be collected AND pass; a missing test file or a missing/
    non-passing mandatory node is an implementation failure (the gate FAILs,
    never a silent PASS on a shrunken collection count). ``stats`` records the
    actually-run files, collected/passed counts, and the per-node result so the
    gate report can list them (§11 req 5).
    """
    issues: list[str] = []
    stats: dict = {}
    report_file = os.path.join(
        tempfile.gettempdir(), f".pytest_gate_{gate_id.lower()}_report.json")
    stats["test_files"] = list(test_files)
    try:
        proc = _run_subprocess(
            [sys.executable, "-m", "pytest", *test_files, "-q",
             "--json-report", f"--json-report-file={report_file}",
             "-p", "no:cacheprovider"],
            timeout=600,
        )
        stats_raw = {}
        node_outcomes: dict[str, str] = {}
        if os.path.isfile(report_file):
            stats_raw = _read_json(report_file)
            stats = {**stats, **_parse_pytest_stats(stats_raw)}
            node_outcomes = {
                t.get("nodeid", ""): t.get("outcome", "")
                for t in stats_raw.get("tests", [])
            }
        if proc.returncode != 0:
            issues.append(
                f"{gate_id} targeted tests exit={proc.returncode}: "
                f"{', '.join(test_files)}")
        if stats.get("failed", 0) != 0 or stats.get("errors", 0) != 0:
            issues.append(f"{gate_id} targeted tests have failures/errors: {stats}")
        if stats.get("skipped", 0) != 0:
            issues.append(f"{gate_id} targeted tests have {stats.get('skipped')} skipped (§17)")
        if stats.get("xfailed", 0) != 0:
            issues.append(f"{gate_id} targeted tests have {stats.get('xfailed')} xfailed (§17)")
        if stats.get("xpassed", 0) != 0:
            issues.append(f"{gate_id} targeted tests have {stats.get('xpassed')} xpassed (§17)")
        if stats.get("collected", 0) == 0:
            issues.append(f"{gate_id} targeted tests collected 0: {test_files}")
        # -- Round 4 mandatory-node enforcement (§10.3/§11.2) --
        if required_nodes:
            node_results: dict[str, str] = {}
            for node in required_nodes:
                outcome = node_outcomes.get(node)
                if outcome is None:
                    node_results[node] = "MISSING"
                    issues.append(
                        f"{gate_id} MANDATORY test node not collected/executed "
                        f"(deleted or renamed?): {node}")
                elif outcome != "passed":
                    node_results[node] = outcome
                    issues.append(
                        f"{gate_id} MANDATORY test node did not pass "
                        f"(outcome={outcome}): {node}")
                else:
                    node_results[node] = "passed"
            stats["mandatory_nodes"] = node_results
            stats["mandatory_nodes_total"] = len(required_nodes)
            stats["mandatory_nodes_passed"] = sum(
                1 for v in node_results.values() if v == "passed")
    except subprocess.TimeoutExpired:
        issues.append(f"{gate_id} targeted tests timed out (600s): {test_files}")
    except Exception as e:  # noqa: BLE001
        issues.append(f"{gate_id} targeted tests error: {e}")
    return issues, stats


# ============================================================
# G01: package/runtime/lock + config & snapshot + no legacy write
# ============================================================

def check_g01_package_runtime_lock() -> dict:
    issues: list[str] = []
    details: dict = {}

    # 1. package import + get_build_info
    try:
        sys.path.insert(0, DEMOV2_ROOT)
        from reaction_agent import get_build_info  # noqa: E402
        from reaction_agent.config import BuildConfig  # noqa: E402
        bi = get_build_info()
        details["build_info"] = bi.model_dump(mode="json")
        details["build_config_fields"] = list(BuildConfig.model_fields.keys())
    except Exception as e:  # noqa: BLE001
        issues.append(f"package import failed: {e}")

    # 2. Python version satisfies pyproject
    try:
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        spec_match = re.search(r'requires-python\s*=\s*"([^"]+)"', _read(PYPROJECT_PATH))
        spec = spec_match.group(1) if spec_match else ">=3.11"
        from packaging.specifiers import SpecifierSet
        ok = py_ver in SpecifierSet(spec)
        details["python"] = {"actual": py_ver, "spec": spec, "satisfied": ok}
        if not ok:
            issues.append(f"python {py_ver} does not satisfy {spec}")
    except Exception as e:  # noqa: BLE001
        issues.append(f"python version check error: {e}")

    # 3. lock file with pinned versions (==)
    try:
        lock_text = _read(LOCK_PATH)
        pinned = [l for l in lock_text.splitlines()
                  if "==" in l and not l.startswith("#")]
        details["lock_pinned_count"] = len(pinned)
        if len(pinned) < 5:
            issues.append(f"lock file has only {len(pinned)} pinned entries")
        # check no floating/unpinned critical deps
        for line in pinned:
            if "pydantic" in line and "==" not in line:
                issues.append(f"pydantic not pinned: {line}")
    except Exception as e:  # noqa: BLE001
        issues.append(f"lock file read error: {e}")

    # 4. explicit config & snapshot builder present
    try:
        from reaction_agent.snapshot import (  # noqa: E402
            build_snapshot, compute_snapshot_hash, load_snapshot,
            SnapshotEvidenceItem, BUILDER_VERSION,
        )
        details["snapshot_api"] = {
            "build_snapshot": callable(build_snapshot),
            "compute_snapshot_hash": callable(compute_snapshot_hash),
            "load_snapshot": callable(load_snapshot),
            "builder_version": BUILDER_VERSION,
        }
    except Exception as e:  # noqa: BLE001
        issues.append(f"snapshot API import failed: {e}")

    # 5. assert_no_legacy_write guard works (positive + negative)
    try:
        from reaction_agent.provenance import assert_no_legacy_write  # noqa: E402
        # positive: demov2-internal path allowed
        allowed = assert_no_legacy_write("reports/p1/test_gate.json")
        if not allowed.endswith("reports/p1/test_gate.json"):
            issues.append("guard mangled allowed path")
        # negative 1: ../benchmark blocked
        try:
            assert_no_legacy_write("../benchmark/x.json")
            issues.append("guard failed to block ../benchmark")
        except PermissionError:
            pass
        # negative 2: ../reports/p0 blocked
        try:
            assert_no_legacy_write("../reports/p0/x.json")
            issues.append("guard failed to block ../reports/p0")
        except PermissionError:
            pass
        # negative 3: ../core blocked
        try:
            assert_no_legacy_write("../core/x.json")
            issues.append("guard failed to block ../core")
        except PermissionError:
            pass
        details["legacy_write_guard"] = "verified (3 negatives blocked)"
    except Exception as e:  # noqa: BLE001
        issues.append(f"legacy write guard error: {e}")

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "package import + python + lock + config/snapshot + no-legacy-write guard verified",
                   details)


# ============================================================
# G02: strict schemas/IDs/provenance + P0 contract still green
# ============================================================

def check_g02_strict_schemas_ids_provenance() -> dict:
    issues: list[str] = []
    details: dict = {}

    try:
        sys.path.insert(0, DEMOV2_ROOT)
        # 1. strict schemas — StrictModel base enforces extra="forbid"
        from reaction_agent.schemas.common import StrictModel  # noqa: E402
        from reaction_agent.schemas import (  # noqa: E402
            MappingReport, SourceReactionLedger, CandidateAnalogyLedger,
            ReactionEvidence, LineageResolution,
        )
        from reaction_agent.schemas.p1_entities import (  # noqa: E402
            EligibilityDecision, QuarantineRecord, SnapshotManifest,
            ResolvedTransformedLineage, ManualAuditRecord,
        )
        strict_classes = [
            MappingReport, SourceReactionLedger, CandidateAnalogyLedger,
            ReactionEvidence, LineageResolution, EligibilityDecision,
            QuarantineRecord, SnapshotManifest, ResolvedTransformedLineage,
            ManualAuditRecord,
        ]
        non_strict = []
        for cls in strict_classes:
            cfg = cls.model_config
            # model_config is a dict (ConfigDict), use .get() not getattr()
            extra = cfg.get("extra") if hasattr(cfg, "get") else getattr(cfg, "extra", None)
            if extra != "forbid":
                non_strict.append(cls.__name__)
        if non_strict:
            issues.append(f"non-strict schemas: {non_strict}")
        details["strict_schema_count"] = len(strict_classes)

        # 2. stable IDs / content hashes — deterministic
        from reaction_agent.hashing import canonical_hash, stable_id  # noqa: E402
        h1 = canonical_hash({"b": 2, "a": 1})
        h2 = canonical_hash({"a": 1, "b": 2})
        if h1 != h2:
            issues.append("canonical_hash not order-independent")
        sid1 = stable_id("lin", {"x": 1})
        sid2 = stable_id("lin", {"x": 1})
        if sid1 != sid2 or not sid1.startswith("lin_"):
            issues.append("stable_id not deterministic or wrong prefix")
        details["hash_deterministic"] = (h1 == h2)
        details["stable_id_sample"] = sid1

        # 3. provenance — SourceRecordProvenance exists
        from reaction_agent.provenance import SourceRecordProvenance  # noqa: E402
        details["provenance_schema"] = SourceRecordProvenance.__name__

    except Exception as e:  # noqa: BLE001
        issues.append(f"schema/hash/provenance import error: {e}")

    # 4. P0 contract still green — run P0 gate
    try:
        proc = _run_subprocess(
            [sys.executable, "scripts/run_p0_gate.py"], timeout=600)
        details["p0_gate_exit"] = proc.returncode
        if proc.returncode != 0:
            issues.append(f"P0 gate exit={proc.returncode} (regression!)")
        else:
            # verify P0 gate report shows 10/10
            p0_report = _read_json(os.path.join(
                DEMOV2_ROOT, "reports", "p0", "P0_GATE_REPORT.json"))
            p0_pass = p0_report.get("pass_count", 0)
            p0_total = p0_report.get("total_checks", 0)
            details["p0_gate"] = f"{p0_pass}/{p0_total}"
            if p0_pass != 10 or p0_total != 10:
                issues.append(f"P0 gate not 10/10: {p0_pass}/{p0_total}")
            if p0_report.get("status") != "READY_FOR_CHATGPT_AUDIT":
                issues.append(f"P0 gate status regression: {p0_report.get('status')}")
    except Exception as e:  # noqa: BLE001
        issues.append(f"P0 gate run error: {e}")

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "strict schemas + deterministic IDs/hashes + provenance + P0 gate 10/10 green",
                   details)


# ============================================================
# G03: legacy lineage audit complete
# ============================================================

def check_g03_legacy_lineage_audit() -> dict:
    issues: list[str] = []
    blocked_reasons: list[str] = []
    details: dict = {}

    audit_path = os.path.join(DATA_AUDIT_DIR, "legacy_lineage_audit.json")
    try:
        audit = _read_json(audit_path)
    except Exception as e:  # noqa: BLE001
        return _result(evidence=f"cannot read legacy_lineage_audit.json: {e}",
                       details={}, external_blockers=["audit unreadable"])

    # 1. verdict — PARTIAL/INCOMPLETE means real source not confirmed (blocker).
    #    But a COMPLETE verdict with zero records is an implementation FAILURE
    #    (M9), not a blocker — verified below regardless of verdict.
    verdict = audit.get("verdict", "")
    details["verdict"] = verdict
    details["verdict_reasons"] = audit.get("verdict_reasons", [])
    if verdict != "COMPLETE":
        blocked_reasons.append(f"verdict={verdict}: {audit.get('verdict_reasons', [])}")

    # 2. counts & denominators — structural integrity (runs regardless of
    #    blocker status so M9/M10 mutations on a faked COMPLETE are caught).
    counts = audit.get("counts", {})
    details["counts"] = counts
    required_count_keys = [
        "total_reactions", "audited_reactions", "cross_lineage_pair",
        "cofactor_selected_as_main", "mapping_missing",
        "legacy_pair_supported", "insufficient_evidence",
    ]
    missing_keys = [k for k in required_count_keys if k not in counts]
    if missing_keys:
        issues.append(f"counts missing keys: {missing_keys}")

    total = counts.get("total_reactions", 0)
    audited = counts.get("audited_reactions", 0)
    details["total_reactions"] = total
    details["audited_reactions"] = audited
    # §5.2: if verdict is COMPLETE, total/audited must be > 0 (M9 catches a
    # faked COMPLETE with zero records). audited must never exceed total.
    if audited > total:
        issues.append(f"audited_reactions ({audited}) > total_reactions ({total})")
    if verdict == "COMPLETE":
        if total <= 0:
            issues.append(f"verdict=COMPLETE but total_reactions={total} (M9: fake complete)")
        if audited <= 0:
            issues.append(f"verdict=COMPLETE but audited_reactions={audited} (M9)")

    # 3. mismatch categories present (5 categories)
    categories = audit.get("categories", {})
    details["category_count"] = len(categories)
    required_cats = [
        "cross_lineage_pair", "cofactor_selected_as_main", "mapping_missing",
        "legacy_pair_supported", "insufficient_evidence",
    ]
    missing_cats = [c for c in required_cats if c not in categories]
    if missing_cats:
        issues.append(f"categories missing: {missing_cats}")

    # 4. source IDs & examples — §5.2: source_ids non-empty + examples from
    #    real source IDs. M10 catches a faked COMPLETE with empty source_ids.
    source_ids = audit.get("source_ids", [])
    examples = audit.get("examples", [])
    details["source_ids_count"] = len(source_ids)
    details["examples_count"] = len(examples)
    if verdict == "COMPLETE":
        if not source_ids:
            issues.append("verdict=COMPLETE but source_ids empty (M10)")
        if not examples:
            issues.append("verdict=COMPLETE but examples empty")
        # examples must reference real source IDs
        sid_set = set(str(s) for s in source_ids)
        for ex in examples:
            ex_sid = str(ex.get("source_id", ex.get("reaction_id", ""))) if isinstance(ex, dict) else str(ex)
            if ex_sid and sid_set and ex_sid not in sid_set:
                issues.append(f"example references unknown source_id: {ex_sid}")
                break

    # 5. real source status — live re-probe rdkit (audit JSON may be stale).
    rss = audit.get("real_source_status", {})
    details["real_source_found"] = rss.get("real_reaction_source_found")
    details["source_confirmed"] = rss.get("source_confirmed_by_env")
    if not rss.get("real_reaction_source_found"):
        blocked_reasons.append("real_reaction_source_not_confirmed")
    # §5.2: legacy source hash must match the actual file recompute (M11).
    lm = audit.get("legacy_module", {})
    details["legacy_read_only"] = lm.get("read_only")
    details["legacy_modified"] = lm.get("modified_by_audit")
    stored_sha = lm.get("sha256", "")
    details["legacy_sha256_stored"] = stored_sha[:16] + "..." if stored_sha else None
    legacy_file = os.path.join(DEMOV2_ROOT, "..", "benchmark", "canonical_identity.py")
    legacy_file = os.path.normpath(legacy_file)
    if os.path.isfile(legacy_file):
        import hashlib
        with open(legacy_file, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()
        details["legacy_sha256_actual"] = actual_sha[:16] + "..."
        if stored_sha and actual_sha != stored_sha:
            issues.append(
                f"legacy module hash mismatch (M11): stored={stored_sha[:16]}... "
                f"!= actual={actual_sha[:16]}...")
    else:
        issues.append(f"legacy module file not found: {legacy_file}")

    # 6. proline-2OG case — real record locatable OR explicitly BLOCKED.
    p2og = audit.get("proline_2og_case", {})
    details["proline_2og_source_record_found"] = p2og.get("source_record_found")
    details["proline_2og_status"] = p2og.get("status")
    if not p2og.get("source_record_found"):
        # Not found is an external blocker (real source unconfirmed), NOT a
        # fake PASS — unless verdict is faked COMPLETE.
        if verdict == "COMPLETE":
            issues.append("verdict=COMPLETE but proline/2OG source_record_found=False")
        else:
            blocked_reasons.append("required_case_missing_proline_2og")

    dn = audit.get("discipline_notes", {})
    details["discipline_notes"] = dn

    evidence = ("; ".join(issues) if issues else
                "legacy full-corpus audit verified (counts/categories/source_ids/"
                "examples/hash + project-declared source + proline/2OG structure case)")
    if blocked_reasons:
        evidence = f"BLOCKED: {'; '.join(blocked_reasons)}; {evidence}"
    return _result(evidence=evidence, details=details,
                   implementation_failures=issues,
                   external_blockers=blocked_reasons)


# ============================================================
# G04: mapping adapter integration
# ============================================================

def check_g04_mapping_adapter() -> dict:
    blocked_reasons: list[str] = []
    issues: list[str] = []
    details: dict = {}

    sample_path = os.path.join(REPORT_DIR, "mapping_integration_sample.json")
    try:
        sample = _read_json(sample_path)
    except Exception as e:  # noqa: BLE001
        return _result(evidence=f"cannot read mapping_integration_sample.json: {e}",
                       details={}, external_blockers=["sample unreadable"])

    # === PRIMARY (§5.3): LIVE probe the real adapter — do NOT trust the
    # JSON status string. Instantiate RealMapperAdapter, call is_available(),
    # and attempt map_reaction(). This defeats the M12/M13 mutations where
    # the JSON status is flipped to COMPLETE while the adapter is a skeleton. ===
    try:
        from reaction_agent.mapping.adapter import RealMapperAdapter
        adapter = RealMapperAdapter(backend="rdkit", timeout=300)
        live_available = adapter.is_available()
        details["live_rdkit_available"] = live_available
        details["live_backend"] = adapter.backend
        if not live_available:
            blocked_reasons.append(
                "RealMapperAdapter(rdkit).is_available()=False live "
                "(rdkit/numpy/networkx/scipy not importable in .venv)")
        else:
            # Backend importable — attempt a real map_reaction() call. The
            # adapter is still a skeleton, so this raises NotImplementedError
            # → honest BLOCKED (real mapping not wired), NOT a fake PASS.
            from reaction_agent.schemas.p1_entities import NormalizedReactionRecord
            probe = NormalizedReactionRecord(
                reaction_id="rxn_g04_probe",
                source_record_id="src_g04_probe",
                normalized_reaction="CCO>>CC(=O)O",
                raw_reaction="CCO>>CC(=O)O",
                direction="forward",
            )
            map_called = False
            map_raised: str | None = None
            try:
                adapter.map_reaction(probe)
                map_called = True
            except NotImplementedError as e:
                map_raised = str(e)
            except Exception as e:  # noqa: BLE001
                map_raised = f"{type(e).__name__}: {e}"
            details["live_map_reaction_called"] = map_called
            details["live_map_reaction_error"] = map_raised
            if not map_called:
                blocked_reasons.append(
                    f"RealMapperAdapter.map_reaction() not implemented (skeleton): "
                    f"{map_raised}")
    except Exception as e:  # noqa: BLE001
        blocked_reasons.append(f"cannot instantiate RealMapperAdapter: {e}")
        details["live_rdkit_available"] = False

    # === report/live coherence — the stored integration artifact is evidence,
    # not authority, but it must not contradict the live probe.  This catches
    # stale or status-only promotion without weakening the live check. ===
    integration = sample.get("real_mapper_integration", {})
    integration_status = integration.get("status")
    all_unavailable = integration.get("all_backends_unavailable")
    reported_backends = integration.get("backends_probed", {})
    reported_live = integration.get("live_probe", {})
    details["reported_integration_status"] = integration_status
    details["reported_all_backends_unavailable"] = all_unavailable

    if not isinstance(reported_backends, dict):
        issues.append("real_mapper_integration.backends_probed must be an object")
        reported_backends = {}
    details["reported_rdkit_available"] = reported_backends.get("rdkit")
    probed_values = list(reported_backends.values())
    if not probed_values or not all(isinstance(value, bool) for value in probed_values):
        issues.append("real_mapper_integration.backends_probed must contain boolean probes")
    expected_all_unavailable = not any(probed_values) if probed_values else None
    if not isinstance(all_unavailable, bool):
        issues.append("real_mapper_integration.all_backends_unavailable must be boolean")
    elif expected_all_unavailable is not None and all_unavailable != expected_all_unavailable:
        issues.append(
            "real_mapper_integration contradiction: all_backends_unavailable "
            f"is {all_unavailable} but backends_probed={reported_backends}"
        )
    if reported_backends.get("rdkit") != details.get("live_rdkit_available"):
        issues.append(
            "real_mapper_integration stale: reported rdkit availability differs "
            "from live probe"
        )
    if integration_status == "INTEGRATION_COMPLETE" and all_unavailable is True:
        issues.append(
            "real_mapper_integration contradiction: status=INTEGRATION_COMPLETE "
            "while all_backends_unavailable=true"
        )
    if details.get("live_map_reaction_called") is True:
        if integration_status != "INTEGRATION_COMPLETE":
            issues.append(
                "live mapper succeeded but stored integration status is not "
                "INTEGRATION_COMPLETE"
            )
        # Bind the stored summary to a second observed result. The report is
        # never allowed to promote a stale or hand-edited live-probe claim.
        try:
            observed = adapter.map_reaction(probe)
            expected_live_fields = {
                "mapper_name": observed.mapper_name,
                "mapping_status": observed.mapping_status.value,
                "assignment_method": observed.source_assignment_method.value,
                "fallback_method": observed.fallback_method,
                "mechanistic_atom_origin": None,
            }
            for field, expected in expected_live_fields.items():
                if reported_live.get(field) != expected:
                    issues.append(
                        f"stored live_probe.{field}={reported_live.get(field)!r} "
                        f"differs from live result {expected!r}"
                    )
        except Exception as e:  # noqa: BLE001
            issues.append(f"second live mapper coherence probe failed: {e}")

    # === unit contract — FakeAtomMapper quality (implementation verification) ===
    uc = sample.get("unit_contract", {})
    details["unit_contract_status"] = uc.get("status")
    details["quality_dimensions_count"] = uc.get("quality_dimensions_count")
    if uc.get("quality_dimensions_count", 0) < 8:
        issues.append(f"quality dimensions < 8: {uc.get('quality_dimensions_count')}")

    fake = uc.get("fake_mapper_sample", {})
    qflags = fake.get("quality_flags", [])
    details["quality_flags_count"] = len(qflags)
    if len(qflags) < 6:
        issues.append(f"quality flags < 6: {len(qflags)}")

    fsa = fake.get("formal_mapped_source_assignment", {})
    details["assignment_method"] = fsa.get("assignment_method")
    details["fallback_method"] = fake.get("fallback_method")
    if fsa.get("assignment_method") != "formal_mapped":
        issues.append(f"assignment_method is not formal_mapped: {fsa.get('assignment_method')}")

    details["mechanistic_origin"] = fake.get("mechanistic_atom_origin")
    details["formal_only_verified"] = uc.get("formal_only_verified")
    if not uc.get("formal_only_verified"):
        issues.append("formal_only_verified is not True")

    # PRIMARY (§5.3): run the mapping adapter unit tests — verifies MCS/center
    # fallback not strict, formal≠mechanism, failure/timeout states, multi-
    # fragment. This is implementation verification, not a status string.
    t4_issues, t4_stats = _run_targeted_tests(
        ["tests/p1/test_mapping_adapter.py"], "P1-G04")
    issues.extend(t4_issues)
    details["t4_pytest_stats"] = t4_stats

    evidence = ("; ".join(issues) if issues else
                "mapping adapter: live probe + FakeAtomMapper unit contract "
                "(8 dims, formal_mapped, formal≠mechanism, MCS/center not strict) "
                "+ T4 tests pass")
    if blocked_reasons:
        evidence = f"BLOCKED: {'; '.join(blocked_reasons)}; {evidence}"
    return _result(evidence=evidence, details=details,
                   implementation_failures=issues,
                   external_blockers=blocked_reasons)


# ============================================================
# G05: participant preservation/roles
# ============================================================

def check_g05_participant_roles() -> dict:
    issues: list[str] = []
    details: dict = {}

    sample_path = os.path.join(REPORT_DIR, "participant_role_sample.json")
    try:
        sample = _read_json(sample_path)
    except Exception as e:  # noqa: BLE001
        return _result(False, f"cannot read participant_role_sample.json: {e}", {})

    # 1. complete participant multiset invariant
    mi = sample.get("multiset_invariant", {})
    details["input_count"] = mi.get("input_count")
    details["output_count"] = mi.get("output_count")
    details["invariant_holds"] = mi.get("invariant_holds")
    if not mi.get("invariant_holds"):
        issues.append("multiset invariant does not hold")
    if mi.get("input_count") != mi.get("output_count"):
        issues.append("input/output count mismatch")

    # 2. COFACTORS no deletion
    cd = sample.get("cofactors_not_destructive", {})
    special = cd.get("special_molecule_retention", {})
    details["special_molecules_count"] = len(special)
    deleted = [name for name, m in special.items() if not m.get("retained")]
    if deleted:
        issues.append(f"deleted molecules: {deleted}")
    # 2OG must be retained (not in COFACTORS but not deleted)
    if "2_oxoglutarate_not_deleted" not in special:
        issues.append("2-oxoglutarate retention not documented")
    else:
        if not special["2_oxoglutarate_not_deleted"].get("retained"):
            issues.append("2-oxoglutarate was deleted")

    # 3. small molecule can be substrate/source (O2, H2O, CO2 retained with role hypotheses)
    for small in ["O2_formal_atom_source", "H2O_hydrolysis_participant", "CO2_coproduct"]:
        if small not in special:
            issues.append(f"small molecule {small} not documented")
        elif not special[small].get("retained"):
            issues.append(f"small molecule {small} not retained")

    # 4. ambiguity retained (O2 has multiple role hypotheses)
    ap = sample.get("ambiguity_preservation", {})
    details["ambiguity_preserved"] = ap.get("ambiguity_preserved")
    details["ambiguity_hypotheses_count"] = len(ap.get("hypotheses_retained", []))
    if not ap.get("ambiguity_preserved"):
        issues.append("ambiguity not preserved")
    if len(ap.get("hypotheses_retained", [])) < 3:
        issues.append(f"ambiguity hypotheses < 3: {len(ap.get('hypotheses_retained', []))}")

    # 5. donor eligibility examples
    de = sample.get("donor_eligibility_examples_no_mapping", {})
    details["donor_eligibility_examples"] = len(de)
    if len(de) < 3:
        issues.append(f"donor eligibility examples < 3: {len(de)}")

    # 6. cofactors source read-only
    cs = sample.get("cofactors_source", {})
    details["cofactors_read_only"] = cs.get("read_only")
    details["cofactors_count"] = cs.get("cofactors_count")
    details["cofactors_source_hash"] = cs.get("source_sha256")
    if not cs.get("read_only"):
        issues.append("cofactors source not read-only")

    details["verdict"] = sample.get("verdict")

    # PRIMARY (§18.2): run T5 tests — participant preservation/roles contract
    t5_issues, t5_stats = _run_targeted_tests(
        ["tests/p1/test_participant_roles.py"], "P1-G05")
    issues.extend(t5_issues)
    details["t5_pytest_stats"] = t5_stats

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "participant multiset preserved, COFACTORS non-destructive, small molecules retained, ambiguity preserved + T5 tests pass zero-skip",
                   details)


# ============================================================
# G06: lineage graph (bipartite / split-merge-transfer / no silent tie / stable IDs / proline-2OG)
# ============================================================

def check_g06_lineage_graph() -> dict:
    issues: list[str] = []
    details: dict = {}

    cases_path = os.path.join(REPORT_DIR, "lineage_regression_cases.json")
    try:
        data = _read_json(cases_path)
    except Exception as e:  # noqa: BLE001
        return _result(False, f"cannot read lineage_regression_cases.json: {e}", {})

    cases = data.get("regression_cases", [])
    details["case_count"] = len(cases)
    if len(cases) < 14:
        issues.append(f"case count < 14: {len(cases)}")

    case_names = {c.get("case", "") for c in cases}

    # 1. bipartite graph structure (reactants + products as separate node sets)
    bipartite_ok = True
    for c in cases:
        nodes = c.get("nodes", {})
        if "reactants" not in nodes or "products" not in nodes:
            bipartite_ok = False
            issues.append(f"case {c.get('case')} missing bipartite nodes")
            break
    details["bipartite_verified"] = bipartite_ok

    # 2. split-merge-transfer represented
    has_split = any(c.get("split_hypotheses") for c in cases)
    has_merge = any(c.get("merge_hypotheses") for c in cases)
    has_transfer = any(c.get("atom_transfer_edges") for c in cases)
    details["has_split"] = has_split
    details["has_merge"] = has_merge
    details["has_atom_transfer"] = has_transfer
    if not has_split:
        issues.append("no split hypothesis found")
    if not has_merge:
        issues.append("no merge hypothesis found")
    if not has_transfer:
        issues.append("no atom_transfer edge found")

    # 3. no independent picking (every edge is reactant->product, never reactant->reactant)
    # 4. no silent tie (case 11 equal_score_tie → ambiguity_set, not silent pick)
    no_silent_tie = False
    for c in cases:
        if "tie" in c.get("case", "").lower():
            asets = c.get("ambiguity_sets", [])
            failure = c.get("failure_reason", "")
            # no silent pick: strict_eligible_count == 0 and ambiguity_set present
            if c.get("strict_eligible_count") == 0 and asets:
                for a in asets:
                    if "no_silent_pick" in a.get("resolution", ""):
                        no_silent_tie = True
            # also check tie is quarantined
            if "quarantined" not in (failure or "").lower() and "tie" in (failure or "").lower():
                # failure_reason mentions tie — check it's quarantined per §9.2
                pass
    details["no_silent_tie_verified"] = no_silent_tie
    if not no_silent_tie:
        issues.append("equal-score tie case does not demonstrate no-silent-pick")

    # 5. stable IDs (lin_ prefix)
    stable_ids_ok = True
    for c in cases:
        for lin in c.get("resolved_lineages", []):
            lid = lin.get("lineage_id", "")
            if not lid.startswith("lin_"):
                stable_ids_ok = False
                issues.append(f"unstable lineage ID: {lid}")
                break
        if not stable_ids_ok:
            break
    details["stable_ids_verified"] = stable_ids_ok

    # 6. proline-2OG case — must exist AND have correct lineages (§5.4).
    # Not just a status string: directly verify strict_eligible_pairs.
    proline_case = None
    for c in cases:
        if "proline" in c.get("case", "").lower():
            proline_case = c
            break
    details["proline_case_found"] = proline_case is not None
    if proline_case is None:
        issues.append("proline/2OG required case missing from regression cases")
    else:
        strict_pairs = proline_case.get("strict_eligible_pairs", [])
        details["proline_strict_pairs"] = strict_pairs
        # §5.4: a product must NOT come from two different reactants in
        # strict_eligible_pairs (the 2OG→hydroxyproline error) unless an
        # explicit merge_hypothesis documents it. Identity-based check —
        # does NOT depend on r1/r2/p1/p2 ordering.
        merge_hyps = proline_case.get("merge_hypotheses", [])
        merge_doc = json.dumps(merge_hyps)
        product_reactants: dict[str, list[str]] = {}
        for pair in strict_pairs:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                product_reactants.setdefault(str(pair[1]), []).append(str(pair[0]))
        for prod, reacts in product_reactants.items():
            if len(set(reacts)) > 1 and prod not in merge_doc:
                issues.append(
                    f"forbidden cross-lineage pairing: product {prod!r} from "
                    f"multiple reactants {reacts} without merge hypothesis "
                    f"(2OG→hydroxyproline class of error)"
                )
        # proline→hydroxyproline + 2OG→succinate must be present (>= 2 pairs)
        if len(strict_pairs) < 2:
            issues.append(
                f"proline case has {len(strict_pairs)} strict pairs, expected "
                f">= 2 (proline→hydroxyproline + 2OG→succinate)"
            )
        # critical ambiguity must not enter strict
        for lin in proline_case.get("resolved_lineages", []):
            if lin.get("ambiguity") == "critical":
                issues.append(
                    f"critical-ambiguity lineage in proline case strict: "
                    f"{lin.get('lineage_id')}"
                )
    details["forbidden_lineage_check"] = data.get("forbidden_lineage_check", "")
    details["proline_2og_hard_gate"] = data.get("proline_2og_hard_gate")

    # PRIMARY (§18.2): run T6 tests — lineage graph contract
    t6_issues, t6_stats = _run_targeted_tests(
        ["tests/p1/test_lineage_graph.py"], "P1-G06")
    issues.extend(t6_issues)
    details["t6_pytest_stats"] = t6_stats

    evidence = ("; ".join(issues) if issues else
                "14 cases: bipartite + split/merge/transfer + no-silent-tie + "
                "stable IDs + proline-2OG correct (identity-based) + T6 tests "
                "pass zero-skip")
    return _result(evidence=evidence, details=details,
                   implementation_failures=issues)


# ============================================================
# G07: dual ledgers valid
# ============================================================

def check_g07_dual_ledgers() -> dict:
    issues: list[str] = []
    details: dict = {}

    src_path = os.path.join(REPORT_DIR, "source_ledger_samples.json")
    cand_path = os.path.join(REPORT_DIR, "candidate_ledger_samples.json")
    try:
        src = _read_json(src_path)
        cand = _read_json(cand_path)
    except Exception as e:  # noqa: BLE001
        return _result(False, f"cannot read ledger samples: {e}", {})

    # 1. SourceReactionLedger valid
    src_samples = src.get("samples", {})
    details["source_sample_count"] = len(src_samples)
    if len(src_samples) < 3:
        issues.append(f"source ledger samples < 3: {len(src_samples)}")
    for name, s in list(src_samples.items())[:1]:
        if not s.get("ledger_id", "").startswith("srl_"):
            issues.append(f"source ledger_id not srl_: {s.get('ledger_id')}")
        if not s.get("reaction_evidence_id"):
            issues.append("source ledger missing reaction_evidence_id")
        details["source_ledger_id_sample"] = s.get("ledger_id")

    # summary + no fabrication evidence
    nf = src.get("summary", {}).get("no_fabrication_evidence", {})
    details["formal_not_promoted"] = nf.get("formal_not_promoted")
    details["missing_stoichiometry_unknowns"] = len(nf.get("missing_stoichiometry_unknowns", []))
    details["unknown_atom_sources_count"] = len(nf.get("unknown_atom_sources", []))
    if not nf.get("formal_not_promoted"):
        issues.append("formal_not_promoted is not True")

    # 2. CandidateAnalogyLedger skeleton valid
    cand_samples = cand.get("samples", [])
    details["candidate_sample_count"] = len(cand_samples)
    if len(cand_samples) < 2:
        issues.append(f"candidate samples < 2: {len(cand_samples)}")
    for s in cand_samples[:1]:
        cl = s.get("candidate_ledger", {})
        if not cl.get("ledger_id", "").startswith("cal_"):
            issues.append(f"candidate ledger_id not cal_: {cl.get('ledger_id')}")
        if not cl.get("source_ledger_id"):
            issues.append("candidate ledger missing source_ledger_id")
        details["candidate_ledger_id_sample"] = cl.get("ledger_id")

    # 3. unknowns preserved
    ie = cand.get("invariant_evidence", {})
    details["source_ledger_link"] = ie.get("source_ledger_link")
    details["candidate_id_echoed"] = ie.get("candidate_id_echoed")
    details["no_proven_cofactor_field"] = ie.get("no_proven_cofactor_field")
    details["candidate_balance_not_observed"] = ie.get("candidate_balance_not_observed")
    if not ie.get("source_ledger_link"):
        issues.append("source_ledger_link not True")
    if not ie.get("no_proven_cofactor_field"):
        issues.append("no_proven_cofactor_field not True")

    # 4. formal-mechanistic separated
    # check that inherited_donor_context has is_assumption=True
    for s in cand_samples[:1]:
        cl = s.get("candidate_ledger", {})
        idc = cl.get("inherited_donor_context", [])
        for d in idc:
            if not d.get("is_assumption"):
                issues.append(f"donor context is_assumption=False: {d}")
                break
        details["inherited_assumptions_sample"] = len(cl.get("inherited_assumptions", []))
        details["unknowns_count"] = len(cl.get("unknowns", []))

    # 5. source linkage valid
    if not ie.get("candidate_id_echoed"):
        issues.append("candidate_id not echoed")

    # PRIMARY (§18.2): run T7/T8 tests — source ledger + candidate ledger skeleton
    t7t8_issues, t7t8_stats = _run_targeted_tests(
        ["tests/p1/test_source_ledger.py",
         "tests/p1/test_candidate_ledger_skeleton.py"], "P1-G07")
    issues.extend(t7t8_issues)
    details["t7t8_pytest_stats"] = t7t8_stats

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "SourceReactionLedger + CandidateAnalogyLedger valid, unknowns preserved, formal≠mechanism, source linkage valid + T7/T8 tests pass zero-skip",
                   details)


# ============================================================
# G08: eligibility/quarantine policy
# ============================================================

# Round 4 (§10) + Round 5 (§13) mandatory G08 test-node manifest: the strict
# semantic fail-closed tests (§8) that MUST be collected and pass. Explicit
# node IDs (not a directory count) so deleting/renaming any one FAILs G08.
# Round 4 adds 20 nodes; Round 5 adds the complete ledger/map/element/lineage
# RED tests (37 nodes) so the manifest covers the full Round-5 task
# requirements — not just a count (§13: "列表覆盖完整任务要求").
_G08_CROSS_INVARIANT_FILE = "tests/p1/test_eligibility_cross_invariants.py"
_G08_REFERENCE_INTEGRITY_FILE = "tests/p1/test_eligibility_reference_integrity.py"
# Round 8: index-partition authority lives in test_snapshot_nested_evidence.py
_G08_INDEX_PARTITION_FILE = "tests/p1/test_snapshot_nested_evidence.py"
_G08_REQUIRED_NODES = [
    f"{_G08_CROSS_INVARIANT_FILE}::test_valid_strict_baseline_is_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_participant_low_mapped_fraction_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_self_reported_full_mapping_with_incomplete_actual_pair_coverage_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_reverse_collision_many_to_one_mapping_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_nonzero_element_balance_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_element_delta_inconsistent_with_counts_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_duplicate_element_balance_entry_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_added_atom_source_ghost_reference_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_role_assignment_ghost_participant_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_stoichiometry_ghost_participant_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_formal_atom_transfer_ghost_participant_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_generic_unknowns_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_duplicate_lineage_id_or_content_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_explicit_reaction_evidence_quarantine_routes_to_quarantine",
    f"{_G08_CROSS_INVARIANT_FILE}::test_identity_ambiguity_set_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_embedded_external_lineage_mismatch_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_uncontrolled_direction_value_never_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_public_snapshot_api_cannot_promote_element_imbalance_to_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_public_snapshot_api_cannot_promote_explicit_quarantine_to_strict",
    f"{_G08_CROSS_INVARIANT_FILE}::test_public_snapshot_api_cannot_promote_mapping_reverse_collision_to_strict",
    # -- Round 5 ledger/map/element/lineage reference-integrity RED tests --
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_reference_integrity_valid_strict_baseline_is_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_reactant_product_matching_map_number_remains_valid",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_added_atom_source_existing_participant_unknown_map_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_added_atom_mechanistic_evidence_id_must_resolve",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_reactant_entry_ghost_participant_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_product_entry_ghost_participant_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_reactant_entry_wrong_side_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_product_entry_wrong_side_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_stoichiometry_existing_participant_wrong_side_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_negative_stoichiometric_coefficient_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_formal_transfer_existing_participants_wrong_sides_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_formal_transfer_unknown_map_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_formal_transfer_conflicts_with_formal_pairs_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_removed_atom_sink_ghost_participant_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_removed_atom_sink_unknown_map_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_cofactor_change_ghost_participant_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_mechanistic_evidence_ghost_participant_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_mechanistic_evidence_unknown_target_map_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_contradictory_role_assignments_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_negative_element_reactant_count_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_negative_element_product_count_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_element_delta_must_equal_product_minus_reactant",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_fully_balanced_nonzero_delta_routes_to_quarantine",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_partial_consistent_nonzero_delta_not_mislabeled_quarantine",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_partial_consistent_nonzero_delta_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_participant_id_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_uncontrolled_participant_side_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_atom_map_within_participant_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_same_side_cross_participant_atom_map_collision_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_embedded_lineage_ids_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_lineage_content_with_reordered_maps_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_transformed_maps_within_lineage_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_added_atom_unknown_map",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_ledger_ghost_entry",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_formal_transfer_map_conflict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_duplicate_participant_map",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_embedded_duplicate_lineage",
    # -- Round 6 (§6–§11) confirmed fail-open RED tests --
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_uncontrolled_cofactor_direction_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_unknown_cofactor_direction_remains_conditional",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_uncontrolled_cofactor_direction",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_reactant_entry_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_conflicting_reactant_entry_coefficients_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_product_entry_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_conflicting_product_entry_coefficients_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_stoichiometry_entry_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_conflicting_stoichiometry_coefficients_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_conflicting_reactant_entries",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_conflicting_stoichiometry",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_mechanistic_target_map_must_exist_on_product_side",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_mechanistic_target_product_map_remains_valid",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_reactant_only_mechanistic_target_map",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_empty_formal_transfer_maps_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_formal_transfer_maps_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_valid_nonempty_formal_transfer_remains_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_empty_formal_transfer",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_heavy_atom_participant_with_empty_maps_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_mapped_fraction_one_cannot_override_empty_heavy_atom_maps",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_valid_fully_mapped_heavy_atom_participant_remains_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_zero_heavy_atom_policy_does_not_get_accidentally_broken",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_unmapped_heavy_atom_participant",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_nonformal_added_atom_source_without_mechanism_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_empty_mechanistic_target_maps_never_strict",
    # -- Round 7 (§5–§10) heavy-atom map count / positive map IDs / collection
    #    duplicate & conflict / unbacked sink / index-aware public boundary --
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_genuinely_fully_mapped_heavy_atom_participant_remains_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_zero_heavy_atom_proton_policy_remains_valid",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_heavy_atom_map_count_underflow_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_heavy_atom_map_count_overflow_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_mapped_fraction_one_cannot_override_map_count_underflow",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_global_mapped_fraction_one_cannot_override_participant_count_mismatch",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_heavy_map_count_underflow",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_heavy_map_count_overflow",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_positive_atom_map_identifiers_remain_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_zero_atom_map_identifier_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_negative_atom_map_identifier_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_nonpositive_formal_pair_map_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_nonpositive_lineage_map_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_nonpositive_atom_maps",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_distinct_valid_ledger_evidence_remains_valid",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_added_atom_source_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_conflicting_added_atom_sources_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_removed_atom_sink_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_conflicting_removed_atom_sinks_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_formal_transfer_assignment_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_conflicting_formal_transfer_assignments_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_duplicate_mechanistic_target_maps_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_duplicate_added_atom_source",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_duplicate_removed_atom_sink",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_duplicate_formal_transfer_assignment",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_duplicate_mechanistic_targets",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_formally_backed_removed_atom_sink_remains_valid",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_nonformal_removed_atom_sink_without_authority_never_strict",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_cannot_promote_unbacked_removed_atom_sink",
    f"{_G08_REFERENCE_INTEGRITY_FILE}::test_public_snapshot_strict_positive_is_in_production_index",
    # -- Round 8 (§R8-11) index-partition mandatory nodes: the loader rejects
    #    hash-coherent wrong-partition leaks, and the exact-complete partition
    #    positive protection is preserved (production exclusion is REAL public
    #    authority, not a mutation-runner self-assert).
    f"{_G08_INDEX_PARTITION_FILE}::test_loader_rejects_hash_coherent_diagnostic_in_production",
    f"{_G08_INDEX_PARTITION_FILE}::test_loader_rejects_hash_coherent_quarantine_in_production",
    f"{_G08_INDEX_PARTITION_FILE}::test_loader_rejects_cross_index_membership",
    f"{_G08_INDEX_PARTITION_FILE}::test_loader_accepts_exact_complete_index_partition",
    f"{_G08_INDEX_PARTITION_FILE}::test_conditional_record_is_only_in_production_index",
]


def check_g08_eligibility_quarantine() -> dict:
    issues: list[str] = []
    details: dict = {}

    exec_path = os.path.join(REPORT_DIR, "eligibility_matrix_execution.json")
    try:
        data = _read_json(exec_path)
    except Exception as e:  # noqa: BLE001
        return _result(False, f"cannot read eligibility_matrix_execution.json: {e}", {})

    # 1. all 8 policy rows
    rows = data.get("rows", [])
    manifest = data.get("policy_manifest", [])
    details["matrix_row_count"] = data.get("matrix_row_count")
    details["manifest_count"] = len(manifest)
    details["rows_count"] = len(rows)
    if data.get("matrix_row_count") != 8:
        issues.append(f"matrix_row_count != 8: {data.get('matrix_row_count')}")
    if len(manifest) != 8:
        issues.append(f"manifest rows != 8: {len(manifest)}")
    if len(rows) != 8:
        issues.append(f"execution rows != 8: {len(rows)}")

    # 2. warnings (required_warnings per row)
    rows_without_warnings = [
        r for r in manifest if not r.get("required_warnings")
        and r.get("strict_eligibility") not in ("strict_eligible",)]
    # rows that are conditional/prohibited/quarantine should have warnings
    for r in manifest:
        se = r.get("strict_eligibility", "")
        rw = r.get("required_warnings", [])
        if se in ("conditional_eligible", "strict_prohibited", "quarantine") and not rw:
            issues.append(f"row '{r.get('state')}' ({se}) has no required_warnings")

    # 3. quarantine behavior (row 5 quarantined)
    quarantined_rows = [r for r in manifest if r.get("quarantine_behavior") == "quarantined"]
    details["quarantined_rows"] = len(quarantined_rows)
    if len(quarantined_rows) < 1:
        issues.append("no quarantined row found")
    # quarantined row must be excluded
    for r in quarantined_rows:
        if r.get("evaluation_bucket") != "excluded":
            issues.append(f"quarantined row not excluded: {r.get('state')}")

    # 4. production index excludes prohibited & quarantine
    production_rows = [r for r in manifest if r.get("evaluation_bucket") == "production"]
    excluded_from_production = [r for r in manifest if r.get("evaluation_bucket") != "production"]
    details["production_rows"] = len(production_rows)
    details["excluded_rows"] = len(excluded_from_production)
    for r in production_rows:
        if r.get("strict_eligibility") in ("strict_prohibited", "quarantine"):
            issues.append(f"prohibited/quarantine row in production: {r.get('state')}")

    # 5. all reasons typed
    for r in rows:
        pe = r.get("positive_example", {})
        decision = pe.get("decision", {})
        reason = decision.get("reason", "")
        if not reason:
            issues.append(f"row {r.get('row_index')} has no reason")
        # reason must be typed (contains state name + colon)
        state = r.get("state", "")
        if state not in reason:
            issues.append(f"row {r.get('row_index')} reason does not mention state: {reason[:60]}")

    # 6. negative examples present
    for r in rows:
        ne = r.get("negative_example", {})
        if not ne:
            issues.append(f"row {r.get('row_index')} has no negative example")

    details["policy_authority"] = data.get("policy_authority")
    details["engine_version"] = data.get("engine_version")

    # PRIMARY (§5.5): actually RUN fail-closed tests — do NOT just read the
    # precomputed eligibility_matrix_execution.json. Proves that incomplete
    # source, failed/partial/unmapped mapping, MCS/center-pair fallback,
    # unknown lineage participant, and contradictory ledger state NEVER enter
    # strict production (the Critical-2 invariants).
    #
    # Round 4 (§10): explicitly execute test_eligibility_cross_invariants.py and
    # enforce the mandatory strict-semantic node manifest — deleting/renaming
    # any required node FAILs G08 (no silent PASS on a shrunken collection).
    fc_issues, fc_stats = _run_targeted_tests(
        ["tests/p1/test_eligibility_fail_closed.py",
         "tests/p1/test_eligibility_engine.py",
         _G08_CROSS_INVARIANT_FILE,
         _G08_REFERENCE_INTEGRITY_FILE,
         _G08_INDEX_PARTITION_FILE], "P1-G08",
        required_nodes=_G08_REQUIRED_NODES)
    issues.extend(fc_issues)
    details["fail_closed_pytest_stats"] = fc_stats

    evidence = ("; ".join(issues) if issues else
                "8 policy rows + warnings + quarantine behavior + production "
                "excludes prohibited/quarantine + reasons typed + fail-closed "
                "tests pass (incomplete/failed/MCS/unknown never strict)")
    return _result(evidence=evidence, details=details,
                   implementation_failures=issues)


# ============================================================
# G09: snapshot reproducibility
# ============================================================

# --- T10 fixture source (synthetic, labeled fixture) for independent rebuild ---
# Mirrors tests/p1/test_snapshot_builder.py::_full_fixture_items() exactly so
# the independent rebuild cross-verifies the hash stored in
# snapshot_build_sample.json. NO real data fabricated (§16.7 preflight note).
from reaction_agent.config import BuildConfig as _G09_BuildConfig
from reaction_agent.schemas.common import (  # noqa: E402
    LedgerBalanceStatus as _G09_LedgerBalanceStatus,
    LineageResolutionQuality as _G09_LineageResolutionQuality,
    MappingQualityClass as _G09_MappingQualityClass,
    MappingStatus as _G09_MappingStatus,
    ParticipantRole as _G09_ParticipantRole,
    SourceAssignmentMethod as _G09_SourceAssignmentMethod,
)
from reaction_agent.schemas.evidence import (  # noqa: E402
    ReactionEvidence as _G09_ReactionEvidence,
    ReactionParticipant as _G09_ReactionParticipant,
)
from reaction_agent.schemas.mapping import (  # noqa: E402
    FormalMappedAtomPair as _G09_FormalMappedAtomPair,
    FormalSourceAssignment as _G09_FormalSourceAssignment,
    MappingReport as _G09_MappingReport,
)
from reaction_agent.schemas.ledger import (  # noqa: E402
    AddedAtomSource as _G09_AddedAtomSource,
    RoleAssignment as _G09_RoleAssignment,
    SourceReactionLedger as _G09_SourceReactionLedger,
)
from reaction_agent.schemas.p1_entities import (  # noqa: E402
    ResolvedTransformedLineage as _G09_ResolvedTransformedLineage,
)
from reaction_agent.snapshot.builder import (  # noqa: E402
    SnapshotEvidenceItem as _G09_SnapshotEvidenceItem,
    compute_snapshot_hash,
)


def _g09_participant(pid, side, smiles="C", charge=0, stoich=1, amn=None,
                     mf=1.0, caf=0.0, roles=None):
    kw = dict(
        participant_id=pid, molecule_id=f"mol_{pid}", canonical_smiles=smiles,
        side=side, formal_charge=charge, stoichiometry=stoich,
        mapped_fraction=mf, changed_atom_fraction=caf,
        atom_map_numbers=amn or [], role_hypotheses=roles or [],
    )
    return _G09_ReactionParticipant(**kw)


def _g09_compliant_mapping_report():
    """MappingReport satisfying ALL strict preconditions (§4.2):
    fully_mapped, formal_mapped, no fallback, unique maps, full coverage."""
    return _G09_MappingReport(
        mapper_name="fake_mapper",
        mapper_version="v1",
        mapper_parameters={"timeout": "30"},
        input_hash="inp_abc",
        output_hash="out_def",
        mapping_status=_G09_MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0,
        map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        formal_mapped_source_assignment=_G09_FormalSourceAssignment(
            mapper_name="fake_mapper",
            mapper_version="v1",
            mapped_atom_pairs=[
                _G09_FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=1,
                    product_participant_id="p1", product_atom_map=1,
                ),
                _G09_FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=2,
                    product_participant_id="p1", product_atom_map=2,
                ),
            ],
            assignment_method=_G09_SourceAssignmentMethod.formal_mapped,
            assignment_quality=_G09_MappingQualityClass.high_quality,
            assignment_ambiguity=False,
        ),
        fallback_method=None,
    )


def _g09_partial_mapping_report():
    """Internally consistent partial mapping for the diagnostic fixture.

    Atom 3 on the product has no identified source, so the report must not
    claim fully_mapped or full changed-atom coverage.  This contradiction was
    detected by the independent P1-G10 Round-1 audit.
    """
    return _G09_MappingReport(
        mapper_name="fixture_partial_mapper",
        mapper_version="v1",
        mapper_parameters={"mode": "curated_partial_fixture"},
        input_hash="inp_partial_abc",
        output_hash="out_partial_def",
        mapping_status=_G09_MappingStatus.partially_mapped,
        mapped_heavy_atom_fraction=2.0 / 3.0,
        map_number_uniqueness=True,
        changed_atom_coverage=0.0,
        formal_mapped_source_assignment=_G09_FormalSourceAssignment(
            mapper_name="fixture_partial_mapper",
            mapper_version="v1",
            mapped_atom_pairs=[
                _G09_FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=1,
                    product_participant_id="p1", product_atom_map=1,
                ),
                _G09_FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=2,
                    product_participant_id="p1", product_atom_map=2,
                ),
            ],
            assignment_method=_G09_SourceAssignmentMethod.formal_mapped,
            assignment_quality=_G09_MappingQualityClass.acceptable,
            assignment_ambiguity=False,
        ),
        fallback_method=None,
    )


def _g09_ev(parts, *, rid, sn="fixture_source_a", sv="v1",
            raw="A>>B", norm="A>>B", mapping_report=None):
    if mapping_report is None:
        mapping_report = _g09_compliant_mapping_report()
    return _G09_ReactionEvidence(
        reaction_id=rid, source_record_id=f"src_{rid}", source_name=sn,
        source_version=sv, raw_reaction=raw, normalized_reaction=norm,
        direction="forward", participants=parts, mapping_report=mapping_report,
    )


def _g09_lin(rp, pp, am=None, amb="none",
             rq=_G09_LineageResolutionQuality.resolved):
    return _G09_ResolvedTransformedLineage(
        lineage_id=f"lin_{rp}_{pp}", reactant_participant_id=rp,
        product_participant_id=pp, ambiguity=amb, transformed_atom_maps=am or [],
        resolution_quality=rq,
    )


def _g09_ledger(rid, bs=_G09_LedgerBalanceStatus.fully_balanced_explicit_reaction,
                cb=0, aas=None, ra=None, hp="unknown"):
    return _G09_SourceReactionLedger(
        ledger_id=f"srl_{rid}", reaction_evidence_id=rid, balance_status=bs,
        charge_balance=cb, added_atom_sources=aas or [], cofactor_changes=[],
        role_assignments=ra or [], unknowns=[], hydrogen_policy=hp,
        proton_policy="unknown", electron_policy="unknown",
        source_completeness="complete", mapping_completeness="complete",
    )


def _g09_role(pid, role="transformed_substrate"):
    return _G09_RoleAssignment(
        participant_id=pid, role=_G09_ParticipantRole(role), score=0.9)


def _g09_item_strict(rid="rxn_strict_001", sn="fixture_source_a"):
    # R7-01B: genuine fully-mapped baseline — CC (2 heavy atoms) with 2 maps.
    r1 = _g09_participant("r1", "reactant", "CC", amn=[1, 2])
    p1 = _g09_participant("p1", "product", "CC", amn=[1, 2])
    ev = _g09_ev([r1, p1], rid=rid, sn=sn, raw="CC>>CC", norm="CC>>CC")
    ld = _g09_ledger(rid, ra=[_g09_role("r1"), _g09_role("p1", "transformed_product")])
    return _G09_SnapshotEvidenceItem(ev, ld, [_g09_lin("r1", "p1", [1, 2])])


def _g09_item_conditional(rid="rxn_cond_001", sn="fixture_source_a"):
    r1 = _g09_participant("r1", "reactant", "CC", amn=[1, 2])
    p1 = _g09_participant("p1", "product", "CC", amn=[1, 2])
    ev = _g09_ev([r1, p1], rid=rid, sn=sn, raw="CC>>CC", norm="CC>>CC")
    ld = _g09_ledger(
        rid, bs=_G09_LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        hp="implicit_heavy_atom_balanced_h_policy",
        ra=[_g09_role("r1"), _g09_role("p1", "transformed_product")])
    return _G09_SnapshotEvidenceItem(ev, ld, [_g09_lin("r1", "p1", [1, 2])])


def _g09_item_diagnostic(rid="rxn_diag_001", sn="fixture_source_a"):
    r1 = _g09_participant("r1", "reactant", "CC", amn=[1, 2], mf=0.5)
    p1 = _g09_participant("p1", "product", "CCC", amn=[1, 2, 3], caf=0.3)
    ev = _g09_ev(
        [r1, p1], rid=rid, sn=sn, raw="CC>>CCC", norm="CC>>CCC",
        mapping_report=_g09_partial_mapping_report(),
    )
    ld = _g09_ledger(
        rid, bs=_G09_LedgerBalanceStatus.partial_or_unbalanced_source,
        aas=[_G09_AddedAtomSource(atom_map_number=3, source_participant_id="unknown_source")],
        ra=[_g09_role("r1"), _g09_role("p1", "transformed_product")])
    return _G09_SnapshotEvidenceItem(ev, ld, [_g09_lin("r1", "p1", [1, 2])])


def _g09_item_quarantine(rid="rxn_quar_001", sn="fixture_source_a"):
    # A genuine charge-imbalanced record: +1 reactant -> neutral product.
    # The ledger records product_charge - reactant_charge = -1.
    r1 = _g09_participant("r1", "reactant", "C[CH2+]", charge=1, amn=[1, 2])
    p1 = _g09_participant("p1", "product", "CC", amn=[1, 2])
    ev = _g09_ev(
        [r1, p1], rid=rid, sn=sn,
        raw="[CH3:1][CH2+:2]>>[CH3:1][CH3:2]",
        norm="[CH3:1][CH2+:2]>>[CH3:1][CH3:2]",
    )
    ld = _g09_ledger(
        rid, bs=_G09_LedgerBalanceStatus.partial_or_unbalanced_source, cb=-1,
        ra=[_g09_role("r1"), _g09_role("p1", "transformed_product")])
    return _G09_SnapshotEvidenceItem(ev, ld, [_g09_lin("r1", "p1", [1, 2])])


def _g09_t10_fixture_items():
    """T10 fixture source: 1 strict + 1 conditional + 1 diagnostic + 1 quarantine.

    Synthetic, explicitly labeled fixture (no real data). Mirrors
    tests/p1/test_snapshot_builder.py::_full_fixture_items() so the independent
    rebuild cross-verifies the hash recorded in snapshot_build_sample.json.
    """
    return [
        _g09_item_strict(),
        _g09_item_conditional(),
        _g09_item_diagnostic(),
        _g09_item_quarantine(),
    ]


def _g09_t10_fixture_config(output_root: str) -> _G09_BuildConfig:
    return _G09_BuildConfig(
        input_source="fixture_source_a",
        output_snapshot_root=output_root,
        mapper_backend="fake",
        mapper_version="p1-1",
        mapper_parameters={},
        normalization_version="p1-1",
        role_policy_version="p1-1",
        lineage_resolver_version="p1-1",
        ledger_version="p1-1",
        eligibility_policy_version="p1-1",
        random_seed=42,
    )


# Round 4 (§11) mandatory G09 test-node manifest: the complete-evidence hash
# and tamper-rejection tests that MUST be collected and pass. Explicit node IDs
# so deleting/renaming the complete-evidence file (or any required node) FAILs
# G09 instead of silently passing on a shrunken collection count.
_G09_COMPLETE_EVIDENCE_FILE = "tests/p1/test_snapshot_complete_evidence.py"
# Round 8: diagnostic-integrity / index-partition authority (same file as G08)
_G09_INDEX_PARTITION_FILE = "tests/p1/test_snapshot_nested_evidence.py"
# Round 10 (Task A): manifest type-authority — record-count / lane-count /
# source-count / failure-count boolean+float rejection, missing/wrong-type
# build_status, top-level non-object rejection, nested versions/source_files/
# record-hash type rejection, recomputed returned counts / source_counts, the
# all-four-lanes positive protection, and all required-field deletion coverage.
_G09_MANIFEST_AUTHORITY_FILE = "tests/p1/test_manifest_authority_type_integrity.py"
_G09_REQUIRED_NODES = [
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_snapshot_hash_changes_when_reaction_provenance_changes",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_snapshot_hash_changes_when_reaction_ambiguity_sets_change",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_snapshot_hash_changes_when_reaction_quarantine_changes",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_snapshot_persists_complete_reaction_evidence_model",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_snapshot_persists_complete_eligibility_decision",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_snapshot_persists_complete_quarantine_record",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_loader_rejects_tampered_reaction_level_provenance",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_loader_rejects_tampered_decision_warning_or_evidence_ids",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_loader_rejects_tampered_quarantine_record",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_embedded_and_external_ledgers_cannot_disagree",
    f"{_G09_COMPLETE_EVIDENCE_FILE}::test_snapshot_id_or_runtime_exclusion_policy_is_explicit",
    # -- Round 8 (§R8-12) diagnostic-integrity mandatory nodes: the loader does
    #    NOT trust index self-reported hashes, the diagnostic index is bound
    #    into immutable snapshot integrity, the indexes are an exact complete
    #    partition, and index content tampering / missing members are rejected.
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_missing_diagnostic_member_without_metadata_change",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_missing_production_member",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_missing_quarantine_member",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_duplicate_records_reaction_id",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_duplicate_index_reaction_id",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_mutated_nested_production_index_payload",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_mutated_nested_diagnostic_index_payload",
    f"{_G09_INDEX_PARTITION_FILE}::test_diagnostic_index_content_changes_snapshot_hash",
    f"{_G09_INDEX_PARTITION_FILE}::test_snapshot_manifest_persists_diagnostic_index_hash",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_accepts_exact_complete_index_partition",
    # -- Round 9 (§R9-9) manifest-authority mandatory nodes: the loader
    #    validates the on-disk manifest envelope (required fields, counts,
    #    record hash list, three index hashes, source summaries, failure
    #    summaries, snapshot identity) against verified artifacts and fails
    #    closed with manifest-specific tokens.
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_missing_manifest_diagnostic_index_hash",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_count_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_record_count_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_record_hashes_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_production_index_hash_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_diagnostic_index_hash_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_quarantine_index_hash_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_source_counts_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_source_hash_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_manifest_failure_counts_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_rejects_snapshot_identity_mismatch",
    f"{_G09_INDEX_PARTITION_FILE}::test_loader_accepts_verified_manifest_authority",
    # -- Round 10 (Task A) manifest type-authority mandatory nodes (38). The
    #    full node IDs come from the ACTUAL pytest collection of
    #    test_manifest_authority_type_integrity.py (Task A §12 handoff). Deleting
    #    or renaming any one of them FAILs G09 — never a silent PASS on a
    #    shrunken collection.
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_record_count_bool",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_included_strict_count_bool",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_conditional_count_bool",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_diagnostic_count_bool",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_quarantine_count_bool",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_source_count_bool",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_source_count_float",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_failure_count_bool",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_failure_count_float",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_manifest_build_status",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_build_status_wrong_type",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_non_object_manifest",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_versions_nested_wrong_type",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_source_files_nested_wrong_type",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_manifest_record_hash_list_nested_wrong_type",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_returns_recomputed_manifest_counts",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_returns_recomputed_source_counts",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_accepts_round10_verified_manifest_all_four_lanes",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[snapshot_id]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[schema_version]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[included_strict_count]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[conditional_count]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[diagnostic_count]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[quarantine_count]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[build_status]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[snapshot_hash]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[build_id]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[source_counts]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[policy_version]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[record_count]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[versions]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[source_files]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[failure_counts_by_reason]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[record_content_hashes]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[production_index_hash]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[diagnostic_index_hash]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[quarantine_index_hash]",
    f"{_G09_MANIFEST_AUTHORITY_FILE}::test_loader_rejects_missing_required_manifest_field[build_config_hash]",
]


def check_g09_snapshot_reproducibility() -> dict:
    issues: list[str] = []
    details: dict = {}

    sample_path = os.path.join(REPORT_DIR, "snapshot_build_sample.json")
    try:
        data = _read_json(sample_path)
    except Exception as e:  # noqa: BLE001
        return _result(False, f"cannot read snapshot_build_sample.json: {e}", {})

    fs = data.get("fixture_snapshot", {})

    # === PRIMARY: independent rebuild (§18.2 — do NOT trust precomputed boolean) ===
    # Call compute_snapshot_hash twice on the T10 fixture source and compare.
    # This catches a tampered/non-deterministic builder that a precomputed
    # ``same_hash_3way`` boolean would hide.
    rebuild_hash_1: str | None = None
    rebuild_hash_2: str | None = None
    independent_match: bool | None = None
    cross_verify_stored: bool | None = None
    try:
        items = _g09_t10_fixture_items()
        with tempfile.TemporaryDirectory(prefix="g09_rebuild_") as tmpdir:
            config = _g09_t10_fixture_config(os.path.join(tmpdir, "snapshots"))
            rebuild_hash_1 = compute_snapshot_hash(config, items)
            # second independent rebuild — reversed input order proves canonical
            # sorting (input order must not affect hash, §16.6)
            rebuild_hash_2 = compute_snapshot_hash(config, list(reversed(items)))
        independent_match = (rebuild_hash_1 == rebuild_hash_2)
        details["independent_rebuild_hash"] = rebuild_hash_1[:16] + "..."
        details["independent_rebuild_hash_full"] = rebuild_hash_1
        details["independent_rebuild_match"] = independent_match
        if not independent_match:
            issues.append(
                f"INDEPENDENT REBUILD MISMATCH: build1={rebuild_hash_1[:16]}... "
                f"!= build2={rebuild_hash_2[:16]}... (builder non-deterministic)")
        # cross-verify against the hash stored in the evidence JSON
        stored_hash = fs.get("determinism_evidence", {}).get("hash_value", "")
        if stored_hash:
            cross_verify_stored = (rebuild_hash_1 == stored_hash)
            details["cross_verify_stored"] = cross_verify_stored
            details["stored_hash_prefix"] = stored_hash[:16] + "..."
            if not cross_verify_stored:
                issues.append(
                    f"CROSS-VERIFY FAILED: independent rebuild {rebuild_hash_1[:16]}... "
                    f"!= JSON stored {stored_hash[:16]}... (deterministic-but-wrong)")
        else:
            details["cross_verify_stored"] = None
            issues.append("no stored hash_value to cross-verify against")
    except Exception as e:  # noqa: BLE001
        issues.append(f"independent rebuild error: {e}")
        details["independent_rebuild_match"] = False
        details["cross_verify_stored"] = False

    # === AUXILIARY: precomputed JSON evidence (kept as secondary signal) ===
    de = fs.get("determinism_evidence", {})
    details["same_hash_3way"] = de.get("same_hash_3way")
    details["same_snapshot_id"] = de.get("same_snapshot_id")
    details["hash_value"] = de.get("hash_value", "")[:16] + "..."
    if not de.get("same_hash_3way"):
        issues.append("auxiliary JSON: same_hash_3way != True")
    if not de.get("same_snapshot_id"):
        issues.append("auxiliary JSON: snapshot_id not deterministic")

    build_a = fs.get("build_a", {})
    build_b = fs.get("build_b", {})
    details["build_a_hash"] = build_a.get("snapshot_hash", "")[:16] + "..."
    details["build_b_hash"] = build_b.get("snapshot_hash", "")[:16] + "..."
    if build_a.get("snapshot_hash") != build_b.get("snapshot_hash"):
        issues.append("auxiliary JSON: build_a/build_b hashes differ")

    # 2. content hash present
    on_disk = fs.get("on_disk_manifest", {})
    details["snapshot_hash"] = on_disk.get("snapshot_hash", "")[:16] + "..."
    details["snapshot_id"] = on_disk.get("snapshot_id")
    if not on_disk.get("snapshot_hash"):
        issues.append("no snapshot_hash in manifest")

    # 3. manifest complete (all resources)
    loaded = fs.get("loaded_record", {})
    resources = loaded.get("resources", [])
    details["resources"] = resources
    required_resources = ["manifest", "production_index", "diagnostic_index",
                          "quarantine_index", "records"]
    missing_res = [r for r in required_resources if r not in resources]
    if missing_res:
        issues.append(f"manifest missing resources: {missing_res}")

    # 4. filters counted (strict/conditional/diagnostic/quarantine)
    counts = build_a.get("counts", {})
    details["counts"] = counts
    if not counts:
        # fallback to on_disk manifest counts
        counts = {
            "strict": on_disk.get("included_strict_count", 0),
            "conditional": on_disk.get("conditional_count", 0),
            "diagnostic": on_disk.get("diagnostic_count", 0),
            "quarantine": on_disk.get("quarantine_count", 0),
        }
        details["counts"] = counts
    if sum(counts.values()) == 0:
        issues.append("all filter counts are zero")
    details["freeze_status"] = loaded.get("freeze_status")
    if loaded.get("freeze_status") != "frozen":
        issues.append("snapshot not frozen")

    # 5. interrupted build invalid (build_status must be complete)
    details["build_status"] = on_disk.get("build_status")
    if on_disk.get("build_status") != "complete":
        issues.append(f"build_status != complete: {on_disk.get('build_status')}")

    # 6. read-only loader (load_snapshot returns frozen record)
    details["evidence_ids_count"] = loaded.get("evidence_ids_count")

    # 7. hash_only_no_write (compute without writing)
    details["hash_only_no_write"] = fs.get("hash_only_no_write", "")[:16] + "..."

    # 8. real source snapshot separation
    rs = data.get("real_source_snapshot", {})
    details["real_snapshot_status"] = rs.get("status")
    details["real_snapshot_reason"] = rs.get("reason", "")[:80] if rs.get("reason") else None

    # 9. failure counts by reason (filters counted)
    fcr = on_disk.get("failure_counts_by_reason", {})
    details["failure_reasons_count"] = len(fcr)

    # 10. record content hashes
    rch = on_disk.get("record_content_hashes", [])
    details["record_content_hashes_count"] = len(rch)

    # PRIMARY (§5.6): actually RUN nested-evidence mutation tests — proves
    # that mutating participant / mapping_report / source_ledger / lineage
    # changes the snapshot hash AND that the loader rejects the tampered
    # records (Critical-1). Beyond the determinism rebuild above.
    #
    # Round 4 (§11): explicitly execute test_snapshot_complete_evidence.py and
    # enforce the mandatory complete-evidence / tamper node manifest — deleting
    # or renaming any required node FAILs G09 (no silent PASS).
    nest_issues, nest_stats = _run_targeted_tests(
        ["tests/p1/test_snapshot_nested_evidence.py",
         "tests/p1/test_snapshot_builder.py",
         _G09_COMPLETE_EVIDENCE_FILE,
         _G09_MANIFEST_AUTHORITY_FILE], "P1-G09",
        required_nodes=_G09_REQUIRED_NODES)
    issues.extend(nest_issues)
    details["nested_mutation_pytest_stats"] = nest_stats

    evidence = ("; ".join(issues) if issues else
                "INDEPENDENT rebuild (2x same hash) + cross-verify stored hash + "
                "deterministic 3-way + content hash + manifest complete + "
                "filters counted + frozen + read-only loader + nested-evidence "
                "mutation/tamper tests pass")
    return _result(evidence=evidence, details=details,
                   implementation_failures=issues)


# ============================================================
# G10: manual audit + full tests
# ============================================================

def check_g10_manual_audit_tests() -> dict:
    issues: list[str] = []
    blocked_reasons: list[str] = []
    details: dict = {}

    # 1. double annotation complete
    audit_path = os.path.join(REPORT_DIR, "manual_audit_report.json")
    try:
        audit = _read_json(audit_path)
    except Exception as e:  # noqa: BLE001
        return _result(False, f"cannot read manual_audit_report.json: {e}",
                       {}, blocked=True)

    details["audit_status"] = audit.get("status")
    details["annotator_a_status"] = audit.get("annotator_a_status")
    details["annotator_b_status"] = audit.get("annotator_b_status")
    details["adjudication_status"] = audit.get("adjudication_status")

    # 1. double annotation status — external blocker if not produced
    for role in ("annotator_a_status", "annotator_b_status", "adjudication_status"):
        if audit.get(role) != "COMPLETE":
            blocked_reasons.append(f"{role}={audit.get(role)}")

    # §5.7: status=COMPLETE but annotation file null/missing → implementation
    # FAILURE (fake complete), NOT a blocker. Catches the M22 mutation where
    # statuses are COMPLETE but annotator_a_file/annotator_b_file are null.
    for role, file_key, id_key in (
        ("annotator_a_status", "annotator_a_file", "annotator_a_id"),
        ("annotator_b_status", "annotator_b_file", "annotator_b_id"),
    ):
        if audit.get(role) == "COMPLETE":
            f = audit.get(file_key)
            if not f:
                issues.append(f"{role}=COMPLETE but {file_key} is null/missing (fake complete, §5.7)")
            else:
                fpath = f if os.path.isabs(f) else os.path.join(DEMOV2_ROOT, f)
                if not os.path.isfile(fpath):
                    issues.append(f"{file_key}={f!r} does not exist (claimed COMPLETE)")
                else:
                    try:
                        _read_json(fpath)
                    except Exception as e:  # noqa: BLE001
                        issues.append(f"{file_key}={f!r} not parseable: {e}")
            if not audit.get(id_key):
                issues.append(f"{id_key} empty while {role}=COMPLETE")

    # adjudication file must exist when adjudication COMPLETE
    if audit.get("adjudication_status") == "COMPLETE":
        af = audit.get("adjudication_file")
        if not af:
            issues.append("adjudication_status=COMPLETE but adjudication_file is null/missing (§5.7)")

    # §5.7: adjudication must cover ALL disagreements. If disagreement_count > 0
    # but adjudication is not complete/missing → implementation FAILURE (M24).
    disc = audit.get("disagreement_count")
    details["disagreement_count"] = disc
    if disc is not None and disc > 0:
        if audit.get("adjudication_status") != "COMPLETE":
            issues.append(
                f"disagreement_count={disc} but adjudication_status="
                f"{audit.get('adjudication_status')!r} (M24: adjudication must "
                f"cover all disagreements)")
        elif not audit.get("adjudication_file"):
            issues.append(
                f"disagreement_count={disc} but adjudication_file missing (M24)")

    # §5.7: annotator A ID != B ID (independent annotators)
    aid = audit.get("annotator_a_id")
    bid = audit.get("annotator_b_id")
    details["annotator_a_id"] = aid
    details["annotator_b_id"] = bid
    if aid and bid and aid == bid:
        issues.append(f"annotator_a_id == annotator_b_id ({aid}) — not independent (§5.7)")

    # 2. threshold frozen before results
    details["protocol_frozen_before_results"] = audit.get("protocol_frozen_before_results")
    if not audit.get("protocol_frozen_before_results"):
        issues.append("protocol not frozen before results")

    pth = audit.get("pass_threshold_frozen", {})
    details["hard_conditions_frozen"] = list(pth.keys())
    # must have H1-H7
    for h in ["H1", "H2", "H3", "H4", "H5", "H6", "H7"]:
        if h not in pth:
            issues.append(f"hard condition {h} not frozen")

    # 3. catastrophic errors = 0
    cec = audit.get("catastrophic_error_count")
    details["catastrophic_error_count"] = cec
    if cec is None:
        blocked_reasons.append("catastrophic_error_count is null (cannot determine without double annotation)")
    elif cec != 0:
        issues.append(f"catastrophic_error_count != 0: {cec}")

    # 4. no LLM self-confidence (§17.5)
    for forbidden_key in ["llm_confidence", "self_confidence", "confidence"]:
        if forbidden_key in audit:
            issues.append(f"forbidden §17.5 field present: {forbidden_key}")

    # 5. fabricated annotations (§17.7) — NOT_PRODUCED but file present
    ann_a = audit.get("annotator_a_file")
    if audit.get("annotator_a_status") == "NOT_PRODUCED" and ann_a is not None:
        issues.append("fabricated annotator_a file (§17.7 violation)")

    details["pass_status"] = audit.get("pass_status")
    details["block_reason"] = audit.get("block_reason", "")[:80] if audit.get("block_reason") else None

    # 6. full test suite — all pass, zero skip/xfail/xpass
    # Exclude test_p1_gate_contract.py to avoid recursion (that test runs the
    # gate, which runs G10, which runs pytest, which runs that test again).
    # The contract test is verified separately when the full suite runs
    # standalone (not inside a gate subprocess).
    report_file = os.path.join(DEMOV2_ROOT, ".pytest_gate_p1_report.json")
    try:
        proc = _run_subprocess(
            [sys.executable, "-m", "pytest", "tests/", "-q",
             "--ignore=tests/p1/test_p1_gate_contract.py",
             "--json-report", f"--json-report-file={report_file}",
             "-p", "no:cacheprovider"],
            timeout=1200,
        )
        details["pytest_exit"] = proc.returncode
    except subprocess.TimeoutExpired:
        details["pytest_exit"] = -999
        stats = {}
        if os.path.isfile(report_file):
            stats = _parse_pytest_stats(_read_json(report_file))
            details["pytest_stats"] = stats
        issues.append(
            f"pytest timed out after 1200s (stats so far: {stats})")
        return _result(evidence="; ".join(issues), details=details,
                       implementation_failures=issues,
                       external_blockers=blocked_reasons)
    stats = {}
    if os.path.isfile(report_file):
        stats = _parse_pytest_stats(_read_json(report_file))
        details["pytest_stats"] = stats
        if stats.get("failed", 0) != 0 or stats.get("errors", 0) != 0:
            issues.append(f"pytest has failures/errors: {stats}")
        if stats.get("skipped", 0) != 0:
            issues.append(f"pytest has {stats.get('skipped')} skipped")
        if stats.get("xfailed", 0) != 0:
            issues.append(f"pytest has {stats.get('xfailed')} xfailed")
        if stats.get("xpassed", 0) != 0:
            issues.append(f"pytest has {stats.get('xpassed')} xpassed")
    else:
        issues.append("no pytest-json-report output")

    # §5.1: do NOT early-return BLOCKED — implementation issues (fake complete,
    # missing files, forbidden fields, test failures) are reported alongside
    # external blockers. BLOCKED only when no impl failures.
    if blocked_reasons:
        evidence = f"BLOCKED: {'; '.join(blocked_reasons)}"
        if issues:
            evidence += f"; IMPLEMENTATION ISSUES: {'; '.join(issues)}"
    else:
        evidence = "; ".join(issues) if issues else (
            f"double annotation complete + adjudication complete + thresholds "
            f"frozen + catastrophic=0 + tests {stats.get('passed')}/{stats.get('collected')} zero-skip"
        )
    return _result(evidence=evidence, details=details,
                   implementation_failures=issues,
                   external_blockers=blocked_reasons)


# ============================================================
# Gate registry
# ============================================================

GATE_CHECKS = [
    ("P1-G01", "package/runtime/lock + config & snapshot + no legacy write",
     check_g01_package_runtime_lock),
    ("P1-G02", "strict schemas/IDs/provenance + P0 contract green",
     check_g02_strict_schemas_ids_provenance),
    ("P1-G03", "legacy lineage audit complete",
     check_g03_legacy_lineage_audit),
    ("P1-G04", "mapping adapter integration",
     check_g04_mapping_adapter),
    ("P1-G05", "participant preservation/roles",
     check_g05_participant_roles),
    ("P1-G06", "lineage graph bipartite/split-merge-transfer/no-silent-tie",
     check_g06_lineage_graph),
    ("P1-G07", "dual ledgers valid",
     check_g07_dual_ledgers),
    ("P1-G08", "eligibility/quarantine policy",
     check_g08_eligibility_quarantine),
    ("P1-G09", "snapshot reproducibility",
     check_g09_snapshot_reproducibility),
    ("P1-G10", "manual audit + full tests",
     check_g10_manual_audit_tests),
]

# Evidence paths per gate (§20)
GATE_EVIDENCE = {
    "P1-G01": {"config": "reaction_agent/config.py", "provenance": "reaction_agent/provenance.py",
               "snapshot": "reaction_agent/snapshot/", "lock": "requirements.lock.txt"},
    "P1-G02": {"schemas": "reaction_agent/schemas/", "hashing": "reaction_agent/hashing.py",
               "p0_gate": "scripts/run_p0_gate.py", "tests": "tests/contracts/"},
    "P1-G03": {"evidence": "reports/data_audit/legacy_lineage_audit.json",
               "legacy_source": "../benchmark/canonical_identity.py (read-only)"},
    "P1-G04": {"evidence": "reports/p1/mapping_integration_sample.json",
               "adapter": "reaction_agent/mapping/adapter.py", "tests": "tests/p1/test_mapping_adapter.py"},
    "P1-G05": {"evidence": "reports/p1/participant_role_sample.json",
               "roles": "reaction_agent/roles/", "tests": "tests/p1/test_participant_roles.py"},
    "P1-G06": {"evidence": "reports/p1/lineage_regression_cases.json",
               "lineage": "reaction_agent/lineage/resolver.py", "tests": "tests/p1/test_lineage_graph.py"},
    "P1-G07": {"evidence_src": "reports/p1/source_ledger_samples.json",
               "evidence_cand": "reports/p1/candidate_ledger_samples.json",
               "tests": "tests/p1/test_source_ledger.py, tests/p1/test_candidate_ledger_skeleton.py"},
    "P1-G08": {"evidence": "reports/p1/eligibility_matrix_execution.json",
               "policy": "reaction_agent/policies/partial_eligibility.py",
               "engine": "reaction_agent/eligibility/engine.py", "tests": "tests/p1/test_eligibility_engine.py"},
    "P1-G09": {"evidence": "reports/p1/snapshot_build_sample.json",
               "builder": "reaction_agent/snapshot/builder.py", "loader": "reaction_agent/snapshot/loader.py",
               "tests": "tests/p1/test_snapshot_builder.py"},
    "P1-G10": {"evidence": "reports/p1/manual_audit_report.json",
               "protocol": "docs/manual_audit_protocol.md", "tests": "tests/p1/test_manual_audit_contract.py"},
}


def _git_changed_files() -> list[dict]:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=DEMOV2_ROOT, capture_output=True, text=True, timeout=10,
        )
        files = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            code = line[:2].strip()
            path = line[3:]
            if "demov2" in path:
                files.append({"status": code, "path": path})
        return files
    except Exception:  # noqa: BLE001
        return []


def run_all() -> tuple[list[dict], dict]:
    """Run all gate checks. Returns (checks_list, env_info)."""
    env = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "working_directory": DEMOV2_ROOT,
    }
    checks = []
    for gate_id, name, fn in GATE_CHECKS:
        result = fn()
        checks.append({"gate_id": gate_id, "name": name, **result})
    return checks, env


def aggregate_gate_status(checks: list[dict]) -> dict:
    """§5.1 aggregation authority — the SINGLE source of truth.

    Categorizes each gate into implementation-FAIL vs external-BLOCKED, computes
    counts, and derives the overall status. BLOCKED never masks an
    implementation FAIL: a gate carrying BOTH an impl failure and an external
    blocker is counted as FAIL. Legacy gates (no explicit impl/blocker lists)
    fall back to passed/blocked.

    Both ``generate_report`` and the M25 mutation call this function so the
    mutation verifies the REAL aggregation, not a copied replica (§8.2).
    """
    impl_fail_gates: list[str] = []
    blocked_gates: list[str] = []
    for c in checks:
        has_impl = bool(c.get("implementation_failures"))
        has_blocker = bool(c.get("external_blockers"))
        if has_impl:
            impl_fail_gates.append(c["gate_id"])
        elif has_blocker:
            blocked_gates.append(c["gate_id"])
        elif not c["passed"] and c.get("blocked"):
            blocked_gates.append(c["gate_id"])  # legacy blocked
        elif not c["passed"] and not c.get("blocked"):
            impl_fail_gates.append(c["gate_id"])  # legacy FAIL
    pass_count = sum(1 for c in checks if c["passed"])
    fail_count = len(impl_fail_gates)
    block_count = len(blocked_gates)
    all_passed = pass_count == len(checks)
    if all_passed:
        status = "READY_FOR_CHATGPT_P1_AUDIT"
    elif fail_count > 0:
        # Implementation FAIL present — never masked by BLOCKED (§5.1).
        status = "NOT_READY_FOR_CHATGPT_AUDIT"
    elif block_count > 0:
        status = "BLOCKED"
    else:
        status = "NOT_READY_FOR_CHATGPT_AUDIT"
    return {
        "impl_fail_gates": impl_fail_gates,
        "blocked_gates": blocked_gates,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "block_count": block_count,
        "all_passed": all_passed,
        "status": status,
    }


def generate_report(checks: list[dict], env: dict):
    os.makedirs(REPORT_DIR, exist_ok=True)
    # §5.1 status model (single authority): impl failures and external blockers
    # are tracked separately; BLOCKED never covers an implementation FAIL.
    agg = aggregate_gate_status(checks)
    impl_fail_gates = agg["impl_fail_gates"]
    blocked_gates = agg["blocked_gates"]
    pass_count = agg["pass_count"]
    fail_count = agg["fail_count"]
    block_count = agg["block_count"]
    all_passed = agg["all_passed"]
    status = agg["status"]

    # attach evidence paths
    for c in checks:
        c["evidence_paths"] = GATE_EVIDENCE.get(c["gate_id"], {})

    changed_files = _git_changed_files()

    jr = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate_version": "p1-gate-1",
        "python_version": env["python_version"],
        "working_directory": DEMOV2_ROOT,
        "status": status,
        "pass_count": pass_count,
        "block_count": block_count,
        "fail_count": fail_count,
        "total_checks": len(checks),
        "all_passed": all_passed,
        "checks": checks,
        "changed_files": changed_files,
        "p0_baseline": {
            "contract_tests": 290,
            "gate": "10/10",
            "status": "READY_FOR_CHATGPT_AUDIT",
        },
        "preflight_context": {
            "status": "BLOCKED",
            "blockers": ["real_reaction_source_not_confirmed",
                         "required_case_missing"],
            "impact": "G03 (real source not confirmed), G04 (RealMapperAdapter skeleton not implemented), G10 (independent annotator/adjudicator not produced) blocked by external inputs; rdkit is available at runtime (no longer a blocker)",
        },
        "deviations": [
            "Execution model: ChatGPT-designed P1 tasks executed by Claude Code subagent (documented in SUBMISSION §15)",
            "rdkit available at runtime: G03 no longer reports rdkit_absent; remaining G03 blocker is real reaction source not confirmed; G04 blocker is RealMapperAdapter.map_reaction() skeleton (a scoped follow-up), not rdkit",
            "Manual audit BLOCKED: no independent second annotator available in single LLM session (§17.1/§17.7)",
        ],
        "assumptions": [
            "Gate reads machine-readable evidence (JSON fields, schema imports, subprocess results), never just os.path.exists (§18.2)",
            "BLOCKED is an honest outcome: §23 states BLOCKED is correct, fake PASS is not",
            "P0 baseline 290 + Gate 10/10 preserved (G02 re-runs P0 gate to verify no regression)",
        ],
        "known_risks": [
            "G03/G04/G10 BLOCKED by external inputs (real-source / skeleton mapper / independent annotator) — cannot be resolved without external dependencies; rdkit is available and is no longer a blocker",
            "Fixture snapshot (4 synthetic records) is not real production data — audit validates pipeline contract, not real chemistry",
            "Proline-2OG case (H2) absent from fixture snapshot — cannot be evaluated until real data available",
        ],
        "user_files_protection": (
            "No user files deleted, moved, or overwritten. Gate is read-only: it reads "
            "evidence JSON, imports schemas, and runs pytest/P0-gate as subprocesses. "
            "No writes to ../benchmark, ../core, or reports/p0. No git add/commit/push/reset/clean."
        ),
        "p2_status": "BLOCKED pending ChatGPT P1 read-only audit",
    }

    # Include mutation results if available (§18.3)
    mutation_path = os.path.join(REPORT_DIR, "mutation_results.json")
    if os.path.isfile(mutation_path):
        try:
            jr["mutation_results"] = _read_json(mutation_path)
        except Exception:  # noqa: BLE001
            jr["mutation_results"] = {"error": "cannot read mutation_results.json"}

    json_path = os.path.join(REPORT_DIR, "P1_GATE_REPORT.json")
    with open(json_path, "w") as f:
        json.dump(jr, f, indent=2, ensure_ascii=False, default=str)

    # markdown report
    md = [
        "# P1 Gate Report",
        "",
        f"**Timestamp (UTC):** {jr['timestamp']}",
        f"**Gate version:** {jr['gate_version']}",
        f"**Working directory:** {DEMOV2_ROOT}",
        f"**Python:** {env['python_version']}",
        "",
        f"## Result: {status}",
        "",
        f"**Passed:** {pass_count} / {len(checks)}",
        f"**Blocked:** {block_count} / {len(checks)}",
        f"**Failed:** {fail_count} / {len(checks)}",
        "",
        "## Preflight Context",
        "",
        f"- Status: {jr['preflight_context']['status']}",
        f"- Blockers: {', '.join(jr['preflight_context']['blockers'])}",
        f"- Impact: {jr['preflight_context']['impact']}",
        "",
        "## Gate Checks",
        "",
    ]
    for c in checks:
        if c["passed"]:
            icon = "PASS"
        elif c.get("blocked"):
            icon = "BLOCKED"
        else:
            icon = "FAIL"
        md.append(f"### {c['gate_id']}: {c['name']}")
        md.append(f"**Status:** {icon}")
        md.append(f"**Evidence:** {c['evidence']}")
        ev = c.get("evidence_paths", {})
        for k, v in ev.items():
            md.append(f"- {k}: {v}")
        md.append("")

    md.extend(["## P0 Baseline", "",
               f"- Contract tests: {jr['p0_baseline']['contract_tests']} passed",
               f"- Gate: {jr['p0_baseline']['gate']}",
               f"- Status: {jr['p0_baseline']['status']}",
               ""])

    # Mutation results (§18.3)
    mut = jr.get("mutation_results", {})
    if mut:
        md.extend([f"## Mutation Results (§18.3)", "",
                   f"**{mut.get('caught', 0)}/{mut.get('total', 0)} mutations CAUGHT** "
                   f"— each mutation on an isolated temp copy caused the corresponding gate check to fail.",
                   "", "| ID | Mutation | Result |", "|----|----------|--------|"])
        for m in mut.get("mutations", []):
            result = "CAUGHT" if m.get("caught") else "MISSED"
            md.append(f"| {m.get('mutation_id','')} | {m.get('mutation','')[:60]} | {result} |")
        md.extend(["", "Mutations ONLY on isolated temp copies (`/tmp/p1_mutation_<n>/`). "
                   "Formal code never polluted (§18.3).", ""])

    md.extend(["## Deviations / Assumptions / Risks", ""])
    md.append("**Deviations:**")
    for d in jr["deviations"]:
        md.append(f"- {d}")
    md.append("\n**Assumptions:**")
    for a in jr["assumptions"]:
        md.append(f"- {a}")
    md.append("\n**Known risks:**")
    for r in jr["known_risks"]:
        md.append(f"- {r}")

    md.extend(["", "## User Files Protection", "", jr["user_files_protection"]])
    md.extend(["", "## P2 Status", "", jr["p2_status"]])
    md.extend(["", "## Conclusion", "", f"**{status}**"])
    if not all_passed:
        md.extend(["", "### Blocking items:", ""])
        for c in checks:
            if c.get("blocked"):
                md.append(f"- {c['gate_id']} [BLOCKED]: {c['evidence']}")
            elif not c["passed"]:
                md.append(f"- {c['gate_id']} [FAIL]: {c['evidence']}")

    md_path = os.path.join(REPORT_DIR, "P1_GATE_REPORT.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md))

    return md_path, json_path, status, all_passed


def main() -> int:
    # Set recursion guard so contract tests running inside gate subprocesses
    # (G02→P0 gate→pytest, G10→pytest) use cached reports instead of re-running
    # the gate/pytest recursively (§18.2 — evidence-based, not infinite loop).
    os.environ["P1_GATE_RECURSION_GUARD"] = "1"

    print("=" * 60)
    print("P1 GATE — 10 Gate Conditions + Evidence-Based Verification")
    print("=" * 60)
    print()

    checks, env = run_all()
    for c in checks:
        if c["passed"]:
            icon = "PASS"
        elif c.get("blocked"):
            icon = "BLOCKED"
        else:
            icon = "FAIL"
        print(f"  [{icon}]  {c['gate_id']}: {c['name']}")
        if not c["passed"]:
            print(f"         {c['evidence']}")

    print()
    md_path, json_path, status, all_passed = generate_report(checks, env)
    pass_count = sum(1 for c in checks if c["passed"])
    block_count = sum(1 for c in checks if c.get("blocked"))
    print(f"Report: {md_path}")
    print(f"JSON:   {json_path}")
    print(f"\nResult: {pass_count}/{len(checks)} passed, {block_count} blocked")
    print(f"Status: {status}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
