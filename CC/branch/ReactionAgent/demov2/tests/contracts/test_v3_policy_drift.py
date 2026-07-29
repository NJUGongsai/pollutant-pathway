"""V3 remediation: ADR-0004 / eligibility policy drift (Section 13, 19 #19).

Verifies the eligibility policy artifact and ADR-0004 use the same warning IDs
and fields, and that the Gate drift check can detect a mismatch.
"""

import os
import re

import pytest

DEMOV2_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DOCS_DIR = os.path.join(DEMOV2_ROOT, "docs", "decisions")
ADR0004_PATH = os.path.join(DOCS_DIR, "ADR-0004-partial-eligibility.md")


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


# -- Section 19 #19: partial-cofactor warning ID must not drift --

@pytest.mark.contract
def test_adr0004_uses_partial_cofactor_stoichiometry():
    """ADR-0004 must use partial_cofactor_stoichiometry, not bare partial_cofactor."""
    adr = _read(ADR0004_PATH)
    assert "partial_cofactor_stoichiometry" in adr
    standalone = re.findall(r"partial_cofactor(?!_stoichiometry)", adr)
    assert standalone == [], (
        "ADR-0004 has drift ID 'partial_cofactor' (without _stoichiometry)"
    )


@pytest.mark.contract
def test_adr0004_has_research_diagnostic_column():
    """Section 13: ADR-0004 must have a Research/Diagnostic eligibility column."""
    adr = _read(ADR0004_PATH)
    assert "Research/Diagnostic" in adr


@pytest.mark.contract
def test_policy_manifest_eight_states_six_fields():
    """Policy manifest must have 8 states, each with all 6 fields (Section 13)."""
    from reaction_agent.policies.partial_eligibility import export_policy_manifest

    manifest = export_policy_manifest()
    assert len(manifest) == 8
    required_keys = {
        "state", "strict_eligibility", "required_warnings",
        "quarantine_behavior", "evaluation_bucket",
        "research_or_diagnostic_eligibility",
    }
    for row in manifest:
        assert set(row.keys()) == required_keys, (
            f"row {row.get('state')} has wrong keys: {set(row.keys())}"
        )


@pytest.mark.contract
def test_adr0004_contains_all_policy_warning_ids():
    """Every policy warning ID must appear in ADR-0004."""
    from reaction_agent.policies.partial_eligibility import ELIGIBILITY_MATRIX

    adr = _read(ADR0004_PATH)
    for row in ELIGIBILITY_MATRIX:
        for w in row.required_warnings:
            assert w in adr, f"ADR-0004 missing warning ID: {w}"


@pytest.mark.contract
def test_adr_manifest_matches_policy():
    """Gate drift check: ADR-0004 JSON manifest must match the policy manifest."""
    from reaction_agent.policies.partial_eligibility import (
        export_policy_manifest,
        parse_adr_manifest_json,
        compare_manifests,
    )

    adr_text = _read(ADR0004_PATH)
    adr_manifest = parse_adr_manifest_json(adr_text)
    policy_manifest = export_policy_manifest()
    issues = compare_manifests(adr_manifest, policy_manifest)
    assert issues == [], f"ADR/policy drift: {issues}"


@pytest.mark.contract
def test_compare_manifests_detects_warning_id_drift():
    """If ADR has partial_cofactor but policy has partial_cofactor_stoichiometry,
    the drift check must detect it (Section 19 #19)."""
    from reaction_agent.policies.partial_eligibility import (
        export_policy_manifest,
        compare_manifests,
    )

    tampered = export_policy_manifest()
    for row in tampered:
        if "partial_cofactor_stoichiometry" in row["required_warnings"]:
            row["required_warnings"] = ["partial_cofactor"]
    issues = compare_manifests(tampered, export_policy_manifest())
    assert any("required_warnings" in i for i in issues), (
        f"warning ID drift not detected: {issues}"
    )


@pytest.mark.contract
def test_compare_manifests_detects_state_drift():
    """A missing state in the ADR manifest must be detected as drift."""
    from reaction_agent.policies.partial_eligibility import (
        export_policy_manifest,
        compare_manifests,
    )

    tampered = export_policy_manifest()[:-1]  # drop last state
    issues = compare_manifests(tampered, export_policy_manifest())
    assert any("drift" in i for i in issues), (
        f"state drift not detected: {issues}"
    )
