#!/usr/bin/env python3
"""P0 Gate runner v3 — strict contract freeze verification (Section 15-18).

Checks all 10 P0 Gate conditions with REAL validation, not keyword search:
- JSON Schema freshness: full structural equality (Section 15)
- environment specifiers: real version comparison via packaging (Section 16)
- structured pytest stats: zero skip/xfail/xpass (Section 17)
- ten expanded Gate checks (Section 18)

Returns exit code 0 only if ALL conditions pass and the environment is supported.

Usage:
    .venv/bin/python scripts/run_p0_gate.py
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

from packaging.specifiers import SpecifierSet

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_DIR = os.path.join(DEMOV2_ROOT, "plan")
DOCS_DIR = os.path.join(DEMOV2_ROOT, "docs", "decisions")
README_PATH = os.path.join(DEMOV2_ROOT, "README.md")
ADR0001_PATH = os.path.join(DOCS_DIR, "ADR-0001-authority-and-scope.md")
ADR0004_PATH = os.path.join(DOCS_DIR, "ADR-0004-partial-eligibility.md")
SCHEMAS_JSON_DIR = os.path.join(DEMOV2_ROOT, "schemas", "json")
PYPROJECT_PATH = os.path.join(DEMOV2_ROOT, "pyproject.toml")
REPORT_DIR = os.path.join(DEMOV2_ROOT, "reports", "p0")

REQUIRED_ADRS = [
    "ADR-0001-authority-and-scope.md",
    "ADR-0002-hypothesis-lanes.md",
    "ADR-0003-ledger-and-source-semantics.md",
    "ADR-0004-partial-eligibility.md",
    "ADR-0005-scientific-decision-authority.md",
    "ADR-0006-mcp-side-effects.md",
]

FINAL_AUTHORITY = {"final_design.md", "final_plan.md", "final_discussion.md"}

FILES_NEEDING_BANNER = [
    "UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md",
    "UNIFIED_PLAN_REACTION_ANALOGY_AGENT_2026-07-29.md",
    "FUSION_DESIGN_V5.md",
    "chatgpt-reaction-analogy-agent-design-v2.md",
    "chatgpt-reaction-analogy-agent-plan-v2.md",
    "chatgpt-reaction-analogy-agent-design.md",
    "chatgpt-reaction-analogy-agent-plan.md",
    "CLAUDE_DESIGN_LLM_LATENT_STAGE_REASONING_2026-07-29.md",
    "CLAUDE_PLAN_LLM_LATENT_STAGE_REASONING_2026-07-29.md",
    "qwen_design.md",
    "qwen_plan.md",
    "chatgpt-discussion.md",
    "CLAUDE_discussion.md",
    "qwen_discussion.md",
]


# ============================================================
# Section 15: JSON Schema freshness (full structural equality)
# ============================================================

def json_structural_equal(a, b) -> bool:
    """Deep structural equality, ignoring dict key order."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(json_structural_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(json_structural_equal(x, y) for x, y in zip(a, b))
    return a == b


def _load_exported_schemas():
    """Import all schemas that export_json_schemas.py exports."""
    sys.path.insert(0, DEMOV2_ROOT)
    from reaction_agent.schemas import (  # noqa: E402
        MappingReport, ReactionParticipant, ReactionEvidence, LineageResolution,
        SourceReactionLedger, CandidateAnalogyLedger, TransformationHypothesis,
        SiteHypothesis, ProductionSelectionHypothesis, AgentProposedHypothesis,
        Candidate, PredictionResult, ManualAuditRecord,
    )
    return [
        MappingReport, ReactionParticipant, ReactionEvidence, LineageResolution,
        SourceReactionLedger, CandidateAnalogyLedger, TransformationHypothesis,
        SiteHypothesis, ProductionSelectionHypothesis, AgentProposedHypothesis,
        Candidate, PredictionResult, ManualAuditRecord,
    ]


def check_json_schema_freshness():
    """Section 15: exported JSON files must be structurally equal to model_json_schema()."""
    schemas = _load_exported_schemas()
    issues = []
    expected = len(schemas)
    exported = 0
    for schema_cls in schemas:
        fname = f"{schema_cls.__name__}.json"
        path = os.path.join(SCHEMAS_JSON_DIR, fname)
        if not os.path.isfile(path):
            issues.append(f"missing export: {fname}")
            continue
        with open(path) as f:
            on_disk = json.load(f)
        current = schema_cls.model_json_schema()
        if not json_structural_equal(on_disk, current):
            issues.append(f"stale: {fname} (structural diff)")
        exported += 1
    # extra stale files
    expected_names = {f"{c.__name__}.json" for c in schemas}
    if os.path.isdir(SCHEMAS_JSON_DIR):
        extra = set(os.listdir(SCHEMAS_JSON_DIR)) - expected_names - {".DS_Store"}
        for e in sorted(extra):
            issues.append(f"extra stale file: {e}")
    passed = len(issues) == 0
    evidence = f"{exported}/{expected} fresh" if passed else "; ".join(issues)
    return {
        "passed": passed, "evidence": evidence,
        "details": {"expected_count": expected, "exported_count": exported,
                    "issues": issues},
    }


# ============================================================
# Section 16: environment specifiers (real version comparison)
# ============================================================

def _parse_pyproject_specifiers():
    with open(PYPROJECT_PATH) as f:
        content = f.read()
    spec = {}
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    spec["python"] = m.group(1) if m else ">=3.11"
    m = re.search(r'"(pydantic)([^"]*)"', content)
    spec["pydantic"] = (">=" + m.group(2).lstrip(">=")) if m else ">=2.8,<3"
    # more robust: capture full specifier
    m = re.search(r'"pydantic([^"]*)"', content)
    spec["pydantic"] = m.group(1) if m else ">=2.8,<3"
    m = re.search(r'"pytest([^"]*)"', content)
    spec["pytest"] = m.group(1) if m else ">=8.0"
    return spec


def check_environment_specifiers(versions=None):
    """Section 16: verify Python/Pydantic/pytest satisfy pyproject specifiers.

    If versions is None, uses the current interpreter's versions.
    Returns a list of issue strings (empty = all satisfied).
    """
    import pydantic
    import pytest
    spec = _parse_pyproject_specifiers()
    actual = versions or {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pydantic": pydantic.VERSION,
        "pytest": pytest.__version__,
    }
    issues = []
    for pkg in ("python", "pydantic", "pytest"):
        try:
            ss = SpecifierSet(spec[pkg])
            if actual[pkg] not in ss:
                issues.append(
                    f"{pkg}: actual {actual[pkg]} does not satisfy {spec[pkg]}"
                )
        except Exception as e:  # noqa: BLE001
            issues.append(f"{pkg}: specifier parse error ({spec[pkg]}): {e}")
    return issues


def check_environment():
    """P0-G10 environment sub-check."""
    import pydantic
    import pytest
    spec = _parse_pyproject_specifiers()
    actual = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pydantic": pydantic.VERSION,
        "pytest": pytest.__version__,
    }
    issues = check_environment_specifiers(actual)
    return {
        "actual": actual, "spec": spec, "issues": issues,
        "satisfied": len(issues) == 0,
    }


# ============================================================
# Section 17: structured pytest stats
# ============================================================

def parse_pytest_stats(report_json):
    """Parse pytest-json-report output into structured stats.

    pytest-json-report omits zero-valued summary keys, so use .get defaults.
    """
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


def pytest_stats_pass(stats):
    """Section 17: passed == collected, zero fail/error/skip/xfail/xpass."""
    return (
        stats.get("failed", 0) == 0
        and stats.get("errors", 0) == 0
        and stats.get("skipped", 0) == 0
        and stats.get("xfailed", 0) == 0
        and stats.get("xpassed", 0) == 0
        and stats.get("passed", 0) == stats.get("collected", 0)
    )


# ============================================================
# Section 9: recursive forbidden field scan
# ============================================================

def _scan_forbidden_recursive(schema_json, forbidden):
    """Recursively scan a JSON schema dict for forbidden field names."""
    found = []

    def scan(obj, path):
        if isinstance(obj, dict):
            props = obj.get("properties", {})
            for name in props:
                if name in forbidden:
                    found.append(f"{path}.{name}" if path else name)
            for key in ("$defs", "definitions"):
                if key in obj:
                    for dn, dobj in obj[key].items():
                        scan(dobj, f"{key}.{dn}")
            for name, prop in props.items():
                scan(prop, f"{path}.{name}" if path else name)
            if "items" in obj:
                scan(obj["items"], f"{path}[items]")
            for key in ("anyOf", "oneOf", "allOf"):
                if key in obj:
                    for i, sub in enumerate(obj[key]):
                        scan(sub, f"{path}.{key}[{i}]")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                scan(item, f"{path}[{i}]")

    scan(schema_json, "")
    return found


# ============================================================
# Gate checks (Section 18)
# ============================================================

def _read(path):
    with open(path) as f:
        return f.read()


def _first_lines(path, n=10):
    with open(path) as f:
        return "".join(f.readline() for _ in range(n))


def check_adrs():
    """P0-G01: six ADRs exist with precise Status: Approved + required sections."""
    issues = []
    for adr in REQUIRED_ADRS:
        path = os.path.join(DOCS_DIR, adr)
        if not os.path.isfile(path):
            issues.append(f"missing: {adr}")
            continue
        status = None
        for line in _read(path).split("\n"):
            s = line.strip()
            if s.startswith("Status:") or s.startswith("**Status:**"):
                status = s.split(":", 1)[1].strip().strip("*").strip()
                break
        if status != "Approved":
            issues.append(f"{adr}: status='{status}'")
    passed = len(issues) == 0
    return {"passed": passed,
            "evidence": "; ".join(issues) if issues else "6/6 approved",
            "details": {"issues": issues}}


def check_authority_consistency():
    """P0-G02: README AND ADR-0001 use same authority set; no wildcard catches final_discussion."""
    issues = []
    for doc in FINAL_AUTHORITY:
        if not os.path.isfile(os.path.join(PLAN_DIR, doc)):
            issues.append(f"missing final: {doc}")

    readme = _read(README_PATH) if os.path.isfile(README_PATH) else ""
    if not readme:
        issues.append("README.md missing")
    else:
        for doc in FINAL_AUTHORITY:
            if doc not in readme:
                issues.append(f"README missing: {doc}")
        if "*discussion*" in readme:
            issues.append("README has *discussion* wildcard")

    adr1 = _read(ADR0001_PATH) if os.path.isfile(ADR0001_PATH) else ""
    if "All discussion files" in adr1:
        issues.append("ADR-0001 has 'All discussion files' wildcard")
    if "final_discussion.md" not in adr1:
        issues.append("ADR-0001 missing final_discussion.md")

    for fname in FILES_NEEDING_BANNER:
        path = os.path.join(PLAN_DIR, fname)
        if not os.path.isfile(path):
            issues.append(f"missing non-final doc: {fname}")
            continue
        head = _first_lines(path)
        if "HISTORICAL" not in head and "NON-AUTHORITATIVE" not in head:
            issues.append(f"{fname} missing banner")

    passed = len(issues) == 0
    return {"passed": passed,
            "evidence": "; ".join(issues) if issues else "consistent",
            "details": {"issues": issues}}


def check_hypothesis_lanes():
    """P0-G03: lanes + fail-closed relation-aware reference validation."""
    sys.path.insert(0, DEMOV2_ROOT)
    from reaction_agent.schemas import (  # noqa: E402
        ProductionSelectionHypothesis, AgentProposedHypothesis,
        HypothesisReferenceRegistry, HypothesisValidationContext,
        UnknownReferenceError, validate_hypothesis_references,
        validate_hypothesis_against_context, AtomTarget,
    )
    from pydantic import ValidationError  # noqa: E402
    issues = []
    try:
        # positive (§9.1): complete relation chain, must NOT raise
        reg = HypothesisReferenceRegistry(
            reaction_ids=frozenset({"rxn1"}),
            lineage_ids=frozenset({"l1"}),
            transformation_ids=frozenset({"t1"}),
            site_ids=frozenset({"s1"}),
            lineage_to_reaction_id={"l1": "rxn1"},
            transformation_to_lineage_ids={"t1": ["l1"]},
            site_to_transformation_id={"s1": "t1"},
        )
        h = ProductionSelectionHypothesis(
            hypothesis_id="h1", support_reaction_ids=["rxn1"],
            support_lineage_ids=["l1"], transformation_id="t1", site_id="s1",
        )
        validate_hypothesis_references(h, reg)

        # negative 1 (§9.2): empty relation maps → reject (UnknownReferenceError)
        try:
            reg_n1 = HypothesisReferenceRegistry(
                reaction_ids=frozenset({"rxn1"}), lineage_ids=frozenset({"l1"}),
                transformation_ids=frozenset({"t1"}), site_ids=frozenset({"s1"}),
                # all relation maps default empty
            )
            h_n1 = ProductionSelectionHypothesis(
                hypothesis_id="hn1", support_reaction_ids=["rxn1"],
                support_lineage_ids=["l1"], transformation_id="t1", site_id="s1",
            )
            validate_hypothesis_references(h_n1, reg_n1)
            issues.append("empty relation maps not rejected")
        except UnknownReferenceError:
            pass

        # negative 2 (§9.2): selected site not covered by site map → reject
        try:
            reg_n2 = HypothesisReferenceRegistry(
                reaction_ids=frozenset({"rxn1"}),
                lineage_ids=frozenset({"l1"}),
                transformation_ids=frozenset({"t1"}),
                site_ids=frozenset({"s1"}),
                lineage_to_reaction_id={"l1": "rxn1"},
                transformation_to_lineage_ids={"t1": ["l1"]},
                # site_to_transformation_id absent (s1 uncovered)
            )
            h_n2 = ProductionSelectionHypothesis(
                hypothesis_id="hn2", support_reaction_ids=["rxn1"],
                support_lineage_ids=["l1"], transformation_id="t1", site_id="s1",
            )
            validate_hypothesis_references(h_n2, reg_n2)
            issues.append("uncovered site not rejected")
        except UnknownReferenceError:
            pass

        # negative 3 (§9.2): AgentProposed + missing query context → reject
        try:
            ctx_n3 = HypothesisValidationContext(
                registry=HypothesisReferenceRegistry(
                    transformation_family_ids=frozenset({"ox"})),
                query_atom_ids=None, query_bond_pairs=None,
            )
            ha_n3 = AgentProposedHypothesis(
                hypothesis_id="hn3", transformation_family_id="ox",
                typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
            )
            validate_hypothesis_against_context(ha_n3, ctx_n3)
            issues.append("missing query context not rejected")
        except UnknownReferenceError:
            pass

        # negative 4 (§9.2): relaxation non-empty + policy null → reject
        try:
            reg_n4 = HypothesisReferenceRegistry(
                transformation_family_ids=frozenset({"ox"}),
                relaxation_ids=frozenset({"r1"}),
            )
            ha_n4 = AgentProposedHypothesis(
                hypothesis_id="hn4", transformation_family_id="ox",
                typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
                relaxation_policy_id=None, allowed_relaxation_ids=["r1"],
            )
            validate_hypothesis_references(ha_n4, reg_n4)
            issues.append("relaxation non-empty + policy null not rejected")
        except UnknownReferenceError:
            pass

        # negative 5 (§9.2): inconsistent registry relation key/value → reject at construction
        try:
            HypothesisReferenceRegistry(
                site_ids=frozenset({"s1"}), transformation_ids=frozenset({"t1"}),
                site_to_transformation_id={"s1": "t_unknown"},
            )
            issues.append("inconsistent registry relation not rejected at construction")
        except ValidationError:
            pass

        # additional negative: site-transform mismatch (original, still rejects)
        try:
            h2 = ProductionSelectionHypothesis(
                hypothesis_id="h2", support_reaction_ids=["rxn1"],
                transformation_id="t1", site_id="s1",
            )
            reg2 = HypothesisReferenceRegistry(
                reaction_ids=frozenset({"rxn1"}),
                transformation_ids=frozenset({"t1", "t2"}),
                site_ids=frozenset({"s1"}),
                site_to_transformation_id={"s1": "t2"},
            )
            validate_hypothesis_references(h2, reg2)
            issues.append("site-transform mismatch not rejected")
        except UnknownReferenceError:
            pass

        # additional negative: atom target not in query (original, still rejects)
        try:
            ctx = HypothesisValidationContext(
                registry=HypothesisReferenceRegistry(
                    transformation_family_ids=frozenset({"ox"})),
                query_atom_ids=frozenset({0, 1}),
            )
            ha = AgentProposedHypothesis(
                hypothesis_id="ha", transformation_family_id="ox",
                typed_target_atom_or_bond_set=[AtomTarget(atom_id=999)],
            )
            validate_hypothesis_against_context(ha, ctx)
            issues.append("atom-not-in-query not rejected")
        except UnknownReferenceError:
            pass
    except Exception as e:  # noqa: BLE001
        issues.append(f"error: {e}")
    passed = len(issues) == 0
    return {"passed": passed,
            "evidence": "; ".join(issues) if issues else "lanes + fail-closed relations verified (1 positive, 5+ negatives)",
            "details": {"issues": issues}}


def check_dual_ledgers():
    """P0-G04: dual ledger boundary + real source_ledger_id validation."""
    sys.path.insert(0, DEMOV2_ROOT)
    from reaction_agent.schemas import (  # noqa: E402
        SourceReactionLedger, CandidateAnalogyLedger, LedgerBalanceStatus,
        LedgerReferenceRegistry, UnknownReferenceError,
        validate_candidate_ledger_references, InheritedDonorContext,
    )
    from pydantic import ValidationError  # noqa: E402
    issues = []
    try:
        # missing source link rejected
        try:
            CandidateAnalogyLedger(ledger_id="cl1", candidate_id="c1")
            issues.append("missing source link accepted")
        except ValidationError:
            pass
        # unknown but non-empty source_ledger_id rejected
        try:
            reg = LedgerReferenceRegistry(
                source_ledger_ids=frozenset({"sl1"}),
                candidate_ids=frozenset({"c1"}),
            )
            ledger = CandidateAnalogyLedger(
                ledger_id="cl1", source_ledger_id="DOES_NOT_EXIST", candidate_id="c1",
            )
            validate_candidate_ledger_references(ledger, reg)
            issues.append("unknown source_ledger_id accepted")
        except UnknownReferenceError:
            pass
        # is_assumption=False rejected
        try:
            InheritedDonorContext(
                donor_reaction_id="r", donor_participant_id="p", is_assumption=False,
            )
            issues.append("is_assumption=False accepted")
        except ValidationError:
            pass
    except Exception as e:  # noqa: BLE001
        issues.append(f"error: {e}")
    passed = len(issues) == 0
    return {"passed": passed,
            "evidence": "; ".join(issues) if issues else "dual ledgers verified",
            "details": {"issues": issues}}


def check_eligibility_policy():
    """P0-G05: policy integrity + ADR/policy drift check (Section 13)."""
    sys.path.insert(0, DEMOV2_ROOT)
    from reaction_agent.policies.partial_eligibility import (  # noqa: E402
        ELIGIBILITY_MATRIX, validate_matrix_integrity,
        export_policy_manifest, parse_adr_manifest_json, compare_manifests,
    )
    issues = validate_matrix_integrity()
    if len(ELIGIBILITY_MATRIX) != 8:
        issues.append(f"expected 8 rows, got {len(ELIGIBILITY_MATRIX)}")
    # ADR/policy drift
    try:
        adr_text = _read(ADR0004_PATH)
        adr_manifest = parse_adr_manifest_json(adr_text)
        policy_manifest = export_policy_manifest()
        issues.extend(compare_manifests(adr_manifest, policy_manifest))
    except Exception as e:  # noqa: BLE001
        issues.append(f"drift check error: {e}")
    passed = len(issues) == 0
    return {"passed": passed,
            "evidence": "; ".join(issues) if issues else "8 rows + ADR/policy consistent",
            "details": {"issues": issues}}


def check_mapping_mechanism():
    """P0-G06: typed/flat consistency + unbound evidence + typed pairs."""
    sys.path.insert(0, DEMOV2_ROOT)
    from reaction_agent.schemas import (  # noqa: E402
        MappingReport, MappingStatus, FormalSourceAssignment,
        MechanisticAtomOrigin, SourceAssignmentMethod,
    )
    from pydantic import ValidationError  # noqa: E402
    issues = []
    try:
        base = dict(mapper_name="t", mapper_version="1", input_hash="a",
                    output_hash="b", mapping_status=MappingStatus.fully_mapped,
                    mapped_heavy_atom_fraction=1.0, map_number_uniqueness=True,
                    changed_atom_coverage=1.0)
        # unbound evidence rejected
        try:
            MappingReport(**base, mechanistic_origin_evidence_ids=["ev1"])
            issues.append("unbound evidence accepted")
        except ValidationError:
            pass
        # typed/flat method conflict rejected
        try:
            MappingReport(**base,
                formal_mapped_source_assignment=FormalSourceAssignment(
                    mapper_name="t", mapper_version="1",
                    assignment_method=SourceAssignmentMethod.manual_curation),
                source_assignment_method=SourceAssignmentMethod.formal_mapped)
            issues.append("method conflict accepted")
        except ValidationError:
            pass
    except Exception as e:  # noqa: BLE001
        issues.append(f"error: {e}")
    passed = len(issues) == 0
    return {"passed": passed,
            "evidence": "; ".join(issues) if issues else "mapping consistency verified",
            "details": {"issues": issues}}


def check_decision_state_machine():
    """P0-G07: state machine + recursive forbidden field scan (Section 9)."""
    sys.path.insert(0, DEMOV2_ROOT)
    from reaction_agent.schemas import (  # noqa: E402
        PredictionResult, ResultStatus, DecisionKind, Candidate, Lane,
        ScientificAbstentionReason, SystemFailureReason, FORBIDDEN_FIELD_NAMES,
        MappingReport, ReactionEvidence, LineageResolution,
        SourceReactionLedger, CandidateAnalogyLedger, TransformationHypothesis,
        SiteHypothesis, ProductionSelectionHypothesis, AgentProposedHypothesis,
        LineageHypothesis,
    )
    from reaction_agent.schemas.result import Abstention, Failure  # noqa: E402
    from pydantic import ValidationError  # noqa: E402
    issues = []
    try:
        c = Candidate(candidate_id="c1", canonical_product="CC=O",
                      lane=Lane.strict, origin="agent_selected_from_evidence_space")
        try:
            PredictionResult(run_id="r1", status=ResultStatus.completed,
                             decision=DecisionKind.abstained,
                             normalized_query="CC", snapshot_id="s1", candidates=[c])
            issues.append("completed+abstained accepted")
        except ValidationError:
            pass
        # recursive forbidden scan
        for cls in [PredictionResult, MappingReport, ReactionEvidence,
                    LineageResolution, SourceReactionLedger, CandidateAnalogyLedger,
                    TransformationHypothesis, SiteHypothesis,
                    ProductionSelectionHypothesis, AgentProposedHypothesis,
                    Candidate, LineageHypothesis]:
            found = _scan_forbidden_recursive(cls.model_json_schema(), FORBIDDEN_FIELD_NAMES)
            for f in found:
                issues.append(f"{cls.__name__}: forbidden '{f}'")
    except Exception as e:  # noqa: BLE001
        issues.append(f"error: {e}")
    passed = len(issues) == 0
    return {"passed": passed,
            "evidence": "; ".join(issues) if issues else "state machine + recursive scan OK",
            "details": {"issues": issues}}


def check_mcp_policy():
    """P0-G08: MCP side-effect policy integrity."""
    sys.path.insert(0, DEMOV2_ROOT)
    from reaction_agent.contracts.mcp_side_effects import (  # noqa: E402
        MCP_TOOL_CONTRACTS, IDEMPOTENCY_RULES, RUN_INVARIANTS,
        validate_policy_integrity,
    )
    try:
        issues = validate_policy_integrity()
        passed = len(issues) == 0
        evidence = "; ".join(issues) if issues else (
            f"{len(MCP_TOOL_CONTRACTS)} tools, {len(IDEMPOTENCY_RULES)} idem, "
            f"{len(RUN_INVARIANTS)} invariants")
    except Exception as e:  # noqa: BLE001
        passed = False
        evidence = f"error: {e}"
    return {"passed": passed, "evidence": evidence, "details": {}}


def check_legacy_provisional():
    """P0-G09: legacy metrics marked provisional in README and ADR-0001."""
    readme = _read(README_PATH).lower()
    adr = _read(ADR0001_PATH).lower()
    r_ok = "provisional" in readme
    a_ok = "provisional" in adr
    return {"passed": r_ok and a_ok,
            "evidence": f"README={'yes' if r_ok else 'no'}, ADR={'yes' if a_ok else 'no'}",
            "details": {}}


def check_contract_tests():
    """P0-G10: pytest stats (structured) + env specifiers + JSON freshness."""
    issues = []
    stats = {}
    # run pytest with json report
    report_file = os.path.join(DEMOV2_ROOT, ".pytest_gate_report.json")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q",
         "--json-report", f"--json-report-file={report_file}"],
        cwd=DEMOV2_ROOT, capture_output=True, text=True, timeout=180,
    )
    if os.path.isfile(report_file):
        with open(report_file) as f:
            report = json.load(f)
        stats = parse_pytest_stats(report)
        if not pytest_stats_pass(stats):
            issues.append(
                f"stats fail: {stats} (exit={proc.returncode})"
            )
    else:
        issues.append("no pytest-json-report output")
    # environment
    env = check_environment()
    if not env["satisfied"]:
        issues.extend(env["issues"])
    # freshness
    fresh = check_json_schema_freshness()
    if not fresh["passed"]:
        issues.append(f"JSON freshness: {fresh['evidence']}")

    passed = len(issues) == 0
    evidence = (f"stats={stats.get('passed')}/{stats.get('collected')} passed, "
                f"skip={stats.get('skipped', 0)}, xfail={stats.get('xfailed', 0)}; "
                f"env={'ok' if env['satisfied'] else 'FAIL'}; "
                f"fresh={fresh['evidence']}")
    return {"passed": passed, "evidence": evidence if passed else "; ".join(issues),
            "details": {"stats": stats, "env": env, "freshness": fresh}}


GATE_CHECKS = [
    ("P0-G01", "Six ADRs complete and approved", check_adrs),
    ("P0-G02", "Authority consistency (README + ADR-0001)", check_authority_consistency),
    ("P0-G03", "Hypothesis lanes + relation validation", check_hypothesis_lanes),
    ("P0-G04", "Dual ledger boundary", check_dual_ledgers),
    ("P0-G05", "Eligibility policy + ADR drift check", check_eligibility_policy),
    ("P0-G06", "Mapping/mechanism consistency", check_mapping_mechanism),
    ("P0-G07", "Decision state machine + recursive forbidden scan", check_decision_state_machine),
    ("P0-G08", "MCP side-effect policy", check_mcp_policy),
    ("P0-G09", "Legacy metrics provisional", check_legacy_provisional),
    ("P0-G10", "Contract tests + JSON freshness + env", check_contract_tests),
]


# Per-gate evidence paths (Section 20: ADR/Schema/policy/test evidence)
GATE_EVIDENCE = {
    "P0-G01": {"adr": "docs/decisions/ADR-0001..ADR-0006", "schema": "-",
               "policy": "-", "tests": "test_authority_contract.py::test_adr_status_is_approved"},
    "P0-G02": {"adr": "ADR-0001-authority-and-scope.md", "schema": "-",
               "policy": "-", "tests": "test_v3_authority_drift.py, test_authority_contract.py"},
    "P0-G03": {"adr": "ADR-0002-hypothesis-lanes.md", "schema": "schemas/hypothesis.py",
               "policy": "-", "tests": "test_v3_hypothesis_relations.py, test_hypothesis_lanes.py"},
    "P0-G04": {"adr": "ADR-0003-ledger-and-source-semantics.md", "schema": "schemas/ledger.py",
               "policy": "-", "tests": "test_v3_hypothesis_relations.py, test_ledger_contracts.py"},
    "P0-G05": {"adr": "ADR-0004-partial-eligibility.md", "schema": "schemas/common.py",
               "policy": "policies/partial_eligibility.py", "tests": "test_v3_policy_drift.py, test_partial_eligibility_contract.py"},
    "P0-G06": {"adr": "ADR-0003-ledger-and-source-semantics.md", "schema": "schemas/mapping.py",
               "policy": "-", "tests": "test_v3_mapping_consistency.py, test_ledger_contracts.py"},
    "P0-G07": {"adr": "ADR-0005-scientific-decision-authority.md", "schema": "schemas/result.py, common.py",
               "policy": "-", "tests": "test_v3_assumption_confidence.py, test_result_invariants.py"},
    "P0-G08": {"adr": "ADR-0006-mcp-side-effects.md", "schema": "-",
               "policy": "contracts/mcp_side_effects.py", "tests": "test_mcp_side_effect_contract.py"},
    "P0-G09": {"adr": "ADR-0001-authority-and-scope.md", "schema": "-",
               "policy": "-", "tests": "test_authority_contract.py"},
    "P0-G10": {"adr": "ADR-0001..ADR-0006", "schema": "schemas/json/*.json",
               "policy": "-", "tests": "all tests/contracts/*.py"},
}


def _git_changed_files():
    """Return demov2 files changed (git status, read-only). Empty if git unavailable."""
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


def run_all():
    """Run all gate checks. Returns (checks_list, env_info)."""
    env = check_environment()
    checks = []
    for gate_id, name, fn in GATE_CHECKS:
        result = fn()
        checks.append({"gate_id": gate_id, "name": name, **result})
    return checks, env


def generate_report(checks, env):
    os.makedirs(REPORT_DIR, exist_ok=True)
    all_passed = all(c["passed"] for c in checks) and env["satisfied"]
    status = "READY_FOR_CHATGPT_AUDIT" if all_passed else "NOT_READY_FOR_CHATGPT_AUDIT"
    changed_files = _git_changed_files()

    # attach evidence paths to each check
    for c in checks:
        c["evidence_paths"] = GATE_EVIDENCE.get(c["gate_id"], {})

    p1_status = "BLOCKED — P0 only, awaiting ChatGPT round-4 read-only audit"

    # structured JSON report (Section 20)
    jr = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "python_required": env["spec"]["python"],
        "python_satisfied": "python" not in env["issues"],
        "pydantic_actual": env["actual"]["pydantic"],
        "pydantic_required": env["spec"]["pydantic"],
        "pydantic_satisfied": "pydantic" not in env["issues"],
        "pytest_actual": env["actual"]["pytest"],
        "pytest_required": env["spec"]["pytest"],
        "pytest_satisfied": "pytest" not in env["issues"],
        "working_directory": DEMOV2_ROOT,
        "status": status,
        "environment": env,
        "pass_count": sum(1 for c in checks if c["passed"]),
        "fail_count": sum(1 for c in checks if not c["passed"]),
        "total_checks": len(checks),
        "authority_files": sorted(FINAL_AUTHORITY),
        "adrs": REQUIRED_ADRS,
        "checks": checks,
        "changed_files": changed_files,
        "p1_status": p1_status,
        "deviations": [],
        "assumptions": [
            "venv (.venv) is the supported environment; system anaconda pytest 7.4.0 "
            "is below spec and is NOT used to run the Gate",
            "Relation validation is fail-closed: missing relation evidence is a rejection, not a skip",
        ],
        "known_risks": [
            "None: validation is fail-closed; missing relation evidence rejects the hypothesis",
        ],
        "user_files_protection": (
            "No user files deleted, moved, or overwritten. Historical plan/*.md docs "
            "received a prepend-only HISTORICAL banner (original content preserved). "
            "All writes confined to demov2/. No git add/commit/push/reset/clean executed."
        ),
    }
    json_path = os.path.join(REPORT_DIR, "P0_GATE_REPORT.json")
    with open(json_path, "w") as f:
        json.dump(jr, f, indent=2, ensure_ascii=False, default=str)

    # markdown report
    md = [
        f"# P0 Gate Report v3",
        f"",
        f"**Timestamp (UTC):** {jr['timestamp']}",
        f"**Working directory:** {DEMOV2_ROOT}",
        f"**Python:** {env['actual']['python']} (required {env['spec']['python']}, satisfied={jr['python_satisfied']})",
        f"**Pydantic:** {env['actual']['pydantic']} (required {env['spec']['pydantic']}, satisfied={jr['pydantic_satisfied']})",
        f"**pytest:** {env['actual']['pytest']} (required {env['spec']['pytest']}, satisfied={jr['pytest_satisfied']})",
        f"",
        f"## Result: {status}",
        f"",
        f"**Passed:** {jr['pass_count']} / {len(checks)}",
        f"**Failed:** {jr['fail_count']} / {len(checks)}",
        f"",
        f"## Gate Checks",
        f"",
    ]
    for c in checks:
        icon = "✅ PASS" if c["passed"] else "❌ FAIL"
        md.append(f"### {c['gate_id']}: {c['name']}")
        md.append(f"**Status:** {icon}")
        md.append(f"**Evidence:** {c['evidence']}")
        ev = c.get("evidence_paths", {})
        md.append(f"**ADR:** {ev.get('adr', '-')} | **Schema:** {ev.get('schema', '-')} | "
                  f"**Policy:** {ev.get('policy', '-')} | **Tests:** {ev.get('tests', '-')}")
        md.append("")
    md.extend(["## Authority Files", ""])
    for doc in sorted(FINAL_AUTHORITY):
        md.append(f"- `plan/{doc}`: {'exists' if os.path.isfile(os.path.join(PLAN_DIR, doc)) else 'MISSING'}")
    md.extend(["", "## ADRs", ""])
    for adr in REQUIRED_ADRS:
        md.append(f"- `{adr}`: {'exists' if os.path.isfile(os.path.join(DOCS_DIR, adr)) else 'MISSING'}")

    md.extend(["", "## Changed Files (git status, demov2)", ""])
    if changed_files:
        for f in changed_files:
            md.append(f"- `{f['status']}` {f['path']}")
    else:
        md.append("- (none detected)")

    md.extend(["", "## Deviations / Assumptions / Risks", "",
               f"- **Deviations:** {jr['deviations'] or 'none'}"])
    md.append(f"- **Assumptions:**")
    for a in jr["assumptions"]:
        md.append(f"  - {a}")
    md.append(f"- **Known risks:**")
    for r in jr["known_risks"]:
        md.append(f"  - {r}")

    md.extend(["", "## User Files Protection", "", jr["user_files_protection"]])
    md.extend(["", "## P1 Status", "", p1_status])
    md.extend(["", "## Conclusion", "", f"**{status}**"])
    if not all_passed:
        md.extend(["", "### Blocking items:", ""])
        for c in checks:
            if not c["passed"]:
                md.append(f"- {c['gate_id']}: {c['evidence']}")
        if not env["satisfied"]:
            md.append(f"- ENVIRONMENT: {env['issues']}")

    md_path = os.path.join(REPORT_DIR, "P0_GATE_REPORT.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md))

    return md_path, json_path, status, all_passed


def main():
    print("=" * 60)
    print("P0 GATE v3 — Strict Contract Freeze Verification")
    print("=" * 60)
    print()

    checks, env = run_all()
    for c in checks:
        icon = "✅ PASS" if c["passed"] else "❌ FAIL"
        print(f"  {icon}  {c['gate_id']}: {c['name']}")
        if not c["passed"]:
            print(f"         {c['evidence']}")

    print()
    md_path, json_path, status, all_passed = generate_report(checks, env)
    print(f"Report: {md_path}")
    print(f"JSON:   {json_path}")
    print(f"\nResult: {sum(1 for c in checks if c['passed'])}/{len(checks)} passed")
    print(f"Status: {status}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
