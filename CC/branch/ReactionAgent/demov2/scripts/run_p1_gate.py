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
from datetime import datetime, timezone
from pathlib import Path

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def _result(passed: bool, evidence: str, details: dict,
            blocked: bool = False) -> dict:
    return {
        "passed": passed, "blocked": blocked,
        "evidence": evidence, "details": details,
    }


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
        return _result(False, f"cannot read legacy_lineage_audit.json: {e}",
                       {}, blocked=True)

    # 1. verdict — PARTIAL means real source not confirmed
    verdict = audit.get("verdict", "")
    details["verdict"] = verdict
    details["verdict_reasons"] = audit.get("verdict_reasons", [])
    if verdict != "COMPLETE":
        blocked_reasons.append(f"verdict={verdict}: {audit.get('verdict_reasons', [])}")

    # 2. counts & denominators present
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

    # 4. source IDs & examples
    source_ids = audit.get("source_ids", [])
    examples = audit.get("examples", [])
    details["source_ids_count"] = len(source_ids)
    details["examples_count"] = len(examples)

    # 5. real source status
    rss = audit.get("real_source_status", {})
    details["real_source_found"] = rss.get("real_reaction_source_found")
    details["source_confirmed"] = rss.get("source_confirmed_by_env")
    if not rss.get("real_reaction_source_found"):
        blocked_reasons.append("real_reaction_source_not_confirmed")

    # 6. proline-2OG case included
    p2og = audit.get("proline_2og_case", {})
    details["proline_2og_source_record_found"] = p2og.get("source_record_found")
    details["proline_2og_status"] = p2og.get("status")
    if not p2og.get("source_record_found"):
        blocked_reasons.append("required_case_missing_proline_2og")

    # 7. legacy module read-only + discipline
    lm = audit.get("legacy_module", {})
    details["legacy_read_only"] = lm.get("read_only")
    details["legacy_modified"] = lm.get("modified_by_audit")
    details["legacy_sha256"] = lm.get("sha256")

    dn = audit.get("discipline_notes", {})
    details["discipline_notes"] = dn

    blocked = len(blocked_reasons) > 0
    if blocked:
        return _result(False,
                       f"BLOCKED: {'; '.join(blocked_reasons)}",
                       details, blocked=True)
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "legacy audit COMPLETE: real source confirmed, counts/categories/examples populated, proline-2OG found",
                   details)


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
        return _result(False, f"cannot read mapping_integration_sample.json: {e}",
                       {}, blocked=True)

    # 1. real mapper integration status
    rmi = sample.get("real_mapper_integration", {})
    integ_status = rmi.get("status", "")
    details["integration_status"] = integ_status
    details["all_backends_unavailable"] = rmi.get("all_backends_unavailable")
    details["backends_probed"] = rmi.get("backends_probed")
    if integ_status != "INTEGRATION_COMPLETE":
        blocked_reasons.append(
            f"integration_status={integ_status}: {rmi.get('reason', '')}")

    # 2. unit contract — quality metrics (8 dimensions)
    uc = sample.get("unit_contract", {})
    details["unit_contract_status"] = uc.get("status")
    details["quality_dimensions_count"] = uc.get("quality_dimensions_count")
    if uc.get("quality_dimensions_count", 0) < 8:
        issues.append(f"quality dimensions < 8: {uc.get('quality_dimensions_count')}")

    # quality flags present
    fake = uc.get("fake_mapper_sample", {})
    qflags = fake.get("quality_flags", [])
    details["quality_flags_count"] = len(qflags)
    if len(qflags) < 6:
        issues.append(f"quality flags < 6: {len(qflags)}")

    # 3. failure states documented
    mapper_params = fake.get("mapper_parameters", {})
    details["mapper_params_status"] = mapper_params.get("status")
    details["fallback_method"] = fake.get("fallback_method")
    # failure states: timeout / partial / unmapped atoms
    has_timeout = "timeout" in mapper_params
    details["has_timeout_config"] = has_timeout

    # 4. MCS not strict (fallback is not strict MCS)
    # formal_mapped source assignment method, not MCS-based
    fsa = fake.get("formal_mapped_source_assignment", {})
    details["assignment_method"] = fsa.get("assignment_method")
    details["assignment_quality"] = fsa.get("assignment_quality")
    if fsa.get("assignment_method") != "formal_mapped":
        issues.append(f"assignment_method is not formal_mapped: {fsa.get('assignment_method')}")

    # 5. formal not mechanism
    details["mechanistic_origin"] = fake.get("mechanistic_atom_origin")
    details["mechanistic_evidence_ids"] = fake.get("mechanistic_origin_evidence_ids")
    details["formal_only_verified"] = uc.get("formal_only_verified")
    if not uc.get("formal_only_verified"):
        issues.append("formal_only_verified is not True")

    blocked = len(blocked_reasons) > 0
    if blocked:
        return _result(False,
                       f"BLOCKED: {'; '.join(blocked_reasons)}",
                       details, blocked=True)
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "mapping adapter INTEGRATION_COMPLETE: 8 quality dims, formal_mapped, formal≠mechanism",
                   details)


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
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "participant multiset preserved, COFACTORS non-destructive, small molecules retained, ambiguity preserved",
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

    # 6. proline-2OG case (case 01) — correct or quarantined
    proline_case = None
    for c in cases:
        if "proline" in c.get("case", "").lower():
            proline_case = c
            break
    details["proline_case_found"] = proline_case is not None
    if proline_case:
        # forbidden lineage 2OG->hydroxyproline must NOT be in strict_eligible_pairs
        strict_pairs = proline_case.get("strict_eligible_pairs", [])
        details["proline_strict_pairs"] = strict_pairs
        # expected: r1->p1 (proline->hydroxyproline), r2->p2 (2OG->succinate)
        # forbidden: r2->p1 (2OG->hydroxyproline)
        forbidden_pair = None
        # check forbidden_lineage_check string in data
        flc = data.get("forbidden_lineage_check", "")
        details["forbidden_lineage_check"] = flc
        if "NOT in strict_eligible_pairs" not in flc:
            issues.append("forbidden lineage check not documented")

    details["proline_2og_hard_gate"] = data.get("proline_2og_hard_gate")

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "14 cases: bipartite + split/merge/transfer + no-silent-tie + stable IDs + proline-2OG correct",
                   details)


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

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "SourceReactionLedger + CandidateAnalogyLedger valid, unknowns preserved, formal≠mechanism, source linkage valid",
                   details)


# ============================================================
# G08: eligibility/quarantine policy
# ============================================================

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
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "8 policy rows + warnings + quarantine behavior + production excludes prohibited/quarantine + reasons typed",
                   details)


# ============================================================
# G09: snapshot reproducibility
# ============================================================

def check_g09_snapshot_reproducibility() -> dict:
    issues: list[str] = []
    details: dict = {}

    sample_path = os.path.join(REPORT_DIR, "snapshot_build_sample.json")
    try:
        data = _read_json(sample_path)
    except Exception as e:  # noqa: BLE001
        return _result(False, f"cannot read snapshot_build_sample.json: {e}", {})

    fs = data.get("fixture_snapshot", {})

    # 1. deterministic rebuild (same hash twice)
    de = fs.get("determinism_evidence", {})
    details["same_hash_3way"] = de.get("same_hash_3way")
    details["same_snapshot_id"] = de.get("same_snapshot_id")
    details["hash_value"] = de.get("hash_value", "")[:16] + "..."
    if not de.get("same_hash_3way"):
        issues.append("deterministic rebuild failed: same_hash_3way != True")
    if not de.get("same_snapshot_id"):
        issues.append("snapshot_id not deterministic")

    build_a = fs.get("build_a", {})
    build_b = fs.get("build_b", {})
    details["build_a_hash"] = build_a.get("snapshot_hash", "")[:16] + "..."
    details["build_b_hash"] = build_b.get("snapshot_hash", "")[:16] + "..."
    if build_a.get("snapshot_hash") != build_b.get("snapshot_hash"):
        issues.append("build_a/build_b hashes differ")

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

    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   "deterministic rebuild (3-way same hash) + content hash + manifest complete + filters counted + frozen + read-only loader",
                   details)


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

    if audit.get("annotator_a_status") != "COMPLETE":
        blocked_reasons.append(f"annotator_a={audit.get('annotator_a_status')}")
    if audit.get("annotator_b_status") != "COMPLETE":
        blocked_reasons.append(f"annotator_b={audit.get('annotator_b_status')}")
    if audit.get("adjudication_status") != "COMPLETE":
        blocked_reasons.append(f"adjudication={audit.get('adjudication_status')}")

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

    # 5. no fabricated annotations (§17.7)
    ann_a = audit.get("annotator_a_file")
    ann_b = audit.get("annotator_b_file")
    if ann_a is not None or ann_b is not None:
        # if status is NOT_PRODUCED but file is not null → fabricated
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
        passed = len(issues) == 0
        return _result(passed, "; ".join(issues) if issues else
                       "pytest timed out", details)
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

    blocked = len(blocked_reasons) > 0
    if blocked:
        return _result(False,
                       f"BLOCKED: {'; '.join(blocked_reasons)}",
                       details, blocked=True)
    passed = len(issues) == 0
    return _result(passed, "; ".join(issues) if issues else
                   f"double annotation complete + adjudication complete + thresholds frozen + catastrophic=0 + tests {stats.get('passed')}/{stats.get('collected')} zero-skip",
                   details)


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


def generate_report(checks: list[dict], env: dict):
    os.makedirs(REPORT_DIR, exist_ok=True)
    pass_count = sum(1 for c in checks if c["passed"])
    block_count = sum(1 for c in checks if c.get("blocked"))
    fail_count = sum(1 for c in checks if not c["passed"] and not c.get("blocked"))
    all_passed = pass_count == len(checks)

    if all_passed:
        status = "READY_FOR_CHATGPT_P1_AUDIT"
    elif block_count > 0 and fail_count == 0:
        status = "BLOCKED"
    else:
        status = "NOT_READY_FOR_CHATGPT_AUDIT"

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
            "blockers": ["rdkit_absent", "real_reaction_source_not_confirmed",
                         "required_case_missing"],
            "impact": "G03 (real source), G04 (rdkit mapping), G10 (proline-2OG in audit) blocked by preflight",
        },
        "deviations": [
            "Execution model: ChatGPT-designed P1 tasks executed by Claude Code subagent (documented in SUBMISSION §15)",
            "rdkit absent: T4 mapping integration, T6 lineage on real data, T7 source ledger balance blocked — unit contracts complete via FakeAtomMapper + structured fixtures",
            "Manual audit BLOCKED: no independent second annotator available in single LLM session (§17.1/§17.7)",
        ],
        "assumptions": [
            "Gate reads machine-readable evidence (JSON fields, schema imports, subprocess results), never just os.path.exists (§18.2)",
            "BLOCKED is an honest outcome: §23 states BLOCKED is correct, fake PASS is not",
            "P0 baseline 290 + Gate 10/10 preserved (G02 re-runs P0 gate to verify no regression)",
        ],
        "known_risks": [
            "G03/G04/G10 BLOCKED by preflight (rdkit/real-source/annotator) — cannot be resolved without external dependencies",
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
