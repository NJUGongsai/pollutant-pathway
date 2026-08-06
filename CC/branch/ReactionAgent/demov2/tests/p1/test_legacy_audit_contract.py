"""P1-T3 Legacy lineage audit — contract tests.

These tests define the contract for the legacy lineage audit artifact produced
by ``scripts/legacy_lineage_audit.py``.

Per task-3-brief Step 6: when the real reaction source is unavailable
(Preflight BLOCKED), the audit is marked ``verdict = "PARTIAL"`` and the
contract tests are adjusted to allow the PARTIAL marker. Crucially (§9.8):
PARTIAL audits must NOT fabricate examples — the ``examples`` array is empty
when verdict is PARTIAL, and the proline/2OG case requirement is relaxed
exactly because the source record is missing (not because we invented data).
"""
import json
from pathlib import Path

AUDIT_JSON = Path("reports/data_audit/legacy_lineage_audit.json")
AUDIT_MD = Path("reports/data_audit/legacy_lineage_audit.md")

# The five mismatch categories required by the brief test contract (§9.4).
REQUIRED_CATEGORIES = {
    "cross_lineage_pair",
    "cofactor_selected_as_main",
    "mapping_missing",
    "legacy_pair_supported",
    "insufficient_evidence",
}


def _load_audit() -> dict:
    """Load and return the audit JSON. Fails loudly if missing."""
    assert AUDIT_JSON.exists(), "audit JSON not generated — run scripts/legacy_lineage_audit.py"
    return json.loads(AUDIT_JSON.read_text())


def test_audit_json_exists_and_machine_readable():
    """Audit JSON exists and contains the four top-level keys from the brief."""
    assert AUDIT_JSON.exists(), "audit 未生成"
    data = json.loads(AUDIT_JSON.read_text())
    assert "counts" in data and "categories" in data
    assert "examples" in data and "source_ids" in data


def test_audit_has_counts_and_denominators():
    """Every count is a non-negative int and the denominator key exists."""
    data = _load_audit()
    for cat, n in data["counts"].items():
        assert isinstance(n, int) and n >= 0, f"count {cat}={n!r} must be non-negative int"
    assert "total_reactions" in data["counts"], "counts must include total_reactions denominator"


def test_md_matches_json_counts():
    """The human-readable MD report must contain every JSON count value."""
    j = _load_audit()
    m = AUDIT_MD.read_text()
    for cat, n in j["counts"].items():
        assert str(n) in m, f"MD 缺 {cat}={n}"


def test_mismatch_categories_complete():
    """All five §9.4 mismatch categories must be present as keys."""
    data = _load_audit()
    assert REQUIRED_CATEGORIES.issubset(set(data["categories"].keys())), (
        f"missing categories: {REQUIRED_CATEGORIES - set(data['categories'].keys())}"
    )


def test_verdict_matches_live_source_availability():
    """COMPLETE requires a live source and a non-empty full-corpus audit."""
    data = _load_audit()
    verdict = data.get("verdict", "")
    source_found = data.get("real_source_status", {}).get(
        "real_reaction_source_found", False
    )
    counts = data.get("counts", {})
    if source_found:
        assert verdict == "COMPLETE"
        assert counts.get("total_reactions", 0) > 0
        assert counts.get("audited_reactions") == counts.get("total_reactions")
        assert data.get("source_ids")
        assert data.get("examples")
    else:
        assert verdict in ("PARTIAL", "BLOCKED")
        reasons = data.get("verdict_reasons", [])
        assert isinstance(reasons, list) and reasons


def test_no_fabricated_examples_when_partial():
    """§9.8: a PARTIAL audit must NOT fabricate examples.

    When verdict is PARTIAL/BLOCKED, the examples array must be empty —
    we do not invent proline/2OG rows to satisfy a green-looking report.
    When verdict is PASS (real source available), examples may be populated.
    """
    data = _load_audit()
    verdict = data.get("verdict", "")
    examples = data.get("examples", [])
    if verdict in ("PARTIAL", "BLOCKED"):
        assert examples == [], (
            f"PARTIAL/BLOCKED audit must not fabricate examples, got {len(examples)}"
        )
    # source_ids must also be empty when no real source was audited
    source_ids = data.get("source_ids", [])
    if verdict in ("PARTIAL", "BLOCKED"):
        assert source_ids == [], (
            f"PARTIAL/BLOCKED audit must not list fabricated source_ids, got {len(source_ids)}"
        )


def test_proline_2og_case_handled_honestly():
    """Proline/2OG case: either included (real source) or explicitly marked missing.

    When the source record is missing (Preflight blocker), the audit must
    record the case as 'required_case_missing' — NOT silently omit it and
    NOT fabricate a proline example.
    """
    data = _load_audit()
    verdict = data.get("verdict", "")
    case = data.get("proline_2og_case", {})
    assert isinstance(case, dict), "proline_2og_case must be a dict"
    if verdict in ("PARTIAL", "BLOCKED"):
        # Source missing: the case must be marked missing, not fabricated.
        assert case.get("source_record_found") is False, (
            f"PARTIAL audit must mark proline/2OG source_record_found=False, "
            f"got {case.get('source_record_found')!r}"
        )
        assert case.get("status") == "required_case_missing", (
            f"PARTIAL audit proline_2og_case.status must be 'required_case_missing', "
            f"got {case.get('status')!r}"
        )
    else:
        # Real source available: a proline example must be present.
        assert any(
            "proline" in str(ex).lower() for ex in data.get("examples", [])
        ), "proline/2OG case must be included when source is available"


def test_legacy_module_fingerprint_recorded():
    """The audit must record the legacy module's read-only fingerprint.

    This proves the audit replayed against the exact frozen legacy source
    (sha256 from Preflight §2) and did not modify it.
    """
    data = _load_audit()
    legacy = data.get("legacy_module", {})
    assert isinstance(legacy, dict), "legacy_module must be a dict"
    assert legacy.get("path", "").endswith("canonical_identity.py"), (
        f"legacy_module.path must point at canonical_identity.py, got {legacy.get('path')!r}"
    )
    assert legacy.get("sha256") == (
        "6003f4bc4ffc5ca3304dc1d2282a467f4f773e149ea9cf2a132ca0e4079eb2d0"
    ), f"legacy sha256 mismatch: {legacy.get('sha256')!r}"
    assert legacy.get("read_only") is True, "legacy_module.read_only must be True"


def test_legacy_logic_risks_documented():
    """The static audit must document at least one risk per audited function.

    A PARTIAL audit's value is the logic-level risk inventory — this is what
    downstream T4-T6 consume to avoid repeating legacy mistakes.
    """
    data = _load_audit()
    risks = data.get("legacy_logic_risks", [])
    assert isinstance(risks, list) and len(risks) >= 4, (
        f"legacy_logic_risks must list >=4 risks (one per audited function), got {len(risks)}"
    )
    for r in risks:
        assert isinstance(r, dict), "each risk must be a dict"
        assert "function" in r and "risk" in r, (
            f"risk entry must have 'function' and 'risk' keys: {r!r}"
        )


def test_categories_carry_definitions():
    """Each mismatch category must carry a human-readable definition.

    The audit is the authoritative reference for what each category means —
    a bare integer count is not enough for downstream gate checks (G03).
    """
    data = _load_audit()
    for cat in REQUIRED_CATEGORIES:
        defn = data["categories"].get(cat)
        assert isinstance(defn, str) and len(defn) >= 10, (
            f"category {cat} must carry a >=10-char definition, got {defn!r}"
        )
