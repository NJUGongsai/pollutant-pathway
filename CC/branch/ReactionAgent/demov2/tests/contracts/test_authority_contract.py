"""ADR-0001: Authority and scope contract tests.

Verifies:
- Three final files are the ONLY current authority
- final_discussion.md is NOT caught by historical wildcard
- Six ADRs exist with correct Status field
- Non-final files have HISTORICAL banner
- README and ADR-0001 have no conflicting promises
- Legacy metrics marked provisional
"""

import os
import re
import pytest

DEMOV2_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
PLAN_DIR = os.path.join(DEMOV2_ROOT, "plan")
DOCS_DIR = os.path.join(DEMOV2_ROOT, "docs", "decisions")
README_PATH = os.path.join(DEMOV2_ROOT, "README.md")

FINAL_AUTHORITY_FILES = [
    "final_design.md",
    "final_plan.md",
    "final_discussion.md",
]

REQUIRED_ADRS = [
    "ADR-0001-authority-and-scope.md",
    "ADR-0002-hypothesis-lanes.md",
    "ADR-0003-ledger-and-source-semantics.md",
    "ADR-0004-partial-eligibility.md",
    "ADR-0005-scientific-decision-authority.md",
    "ADR-0006-mcp-side-effects.md",
]

FILES_NEEDING_HISTORICAL_BANNER = [
    "UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md",
    "UNIFIED_PLAN_REACTION_ANALOGY_AGENT_2026-07-29.md",
    "FUSION_DESIGN_V5.md",
    "chatgpt-reaction-analogy-agent-design-v2.md",
]


# -- ADR existence and status --

@pytest.mark.contract
@pytest.mark.parametrize("adr_name", REQUIRED_ADRS)
def test_adr_exists(adr_name):
    path = os.path.join(DOCS_DIR, adr_name)
    assert os.path.isfile(path), f"ADR missing: {adr_name}"


@pytest.mark.contract
@pytest.mark.parametrize("adr_name", REQUIRED_ADRS)
def test_adr_status_is_approved(adr_name):
    """Parse Status: field precisely — not just keyword search."""
    path = os.path.join(DOCS_DIR, adr_name)
    with open(path) as f:
        content = f.read()
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Status:") or stripped.startswith("**Status:**"):
            status_text = stripped.split(":", 1)[1].strip().strip("*").strip()
            assert status_text == "Approved", (
                f"{adr_name} status is '{status_text}', expected 'Approved'"
            )
            return
    pytest.fail(f"{adr_name}: no Status: line found")


# -- Final authority files --

@pytest.mark.contract
@pytest.mark.parametrize("doc", FINAL_AUTHORITY_FILES)
def test_final_authority_file_exists(doc):
    assert os.path.isfile(os.path.join(PLAN_DIR, doc))


# -- README authority --

@pytest.mark.contract
def test_readme_exists():
    assert os.path.isfile(README_PATH)


@pytest.mark.contract
def test_readme_references_all_three_final_docs():
    with open(README_PATH) as f:
        content = f.read()
    for doc in FINAL_AUTHORITY_FILES:
        assert doc in content, f"README missing reference to {doc}"


@pytest.mark.contract
def test_readme_final_discussion_not_in_historical_wildcard():
    """final_discussion.md must NOT be caught by a '*discussion*' wildcard
    in the historical section."""
    with open(README_PATH) as f:
        content = f.read()
    # Find the historical section
    assert "final_discussion.md" in content
    # Check that there's no "*discussion*" wildcard that would include it
    # The README should explicitly list final_discussion.md as authority
    # and list non-final discussions separately
    lines = content.split("\n")
    in_historical_section = False
    for line in lines:
        if "Historical" in line or "Non-Authoritative" in line:
            in_historical_section = True
        if in_historical_section and "*discussion*" in line:
            pytest.fail("README uses '*discussion*' wildcard in historical section")


@pytest.mark.contract
def test_readme_marks_legacy_metrics_provisional():
    with open(README_PATH) as f:
        content = f.read().lower()
    assert "provisional" in content


# -- Non-final files have HISTORICAL banner --

@pytest.mark.contract
@pytest.mark.parametrize("fname", FILES_NEEDING_HISTORICAL_BANNER)
def test_non_final_file_has_historical_banner(fname):
    """Section 17: missing file = FAIL (not skip), zero-skip requirement."""
    path = os.path.join(PLAN_DIR, fname)
    assert os.path.isfile(path), f"Non-final doc missing: {fname}"
    with open(path) as f:
        first_lines = "".join(f.readline() for _ in range(10))
    assert "HISTORICAL" in first_lines or "NON-AUTHORITATIVE" in first_lines, (
        f"{fname} missing HISTORICAL banner in first 10 lines"
    )


# -- README and ADR-0001 consistency --

@pytest.mark.contract
def test_readme_and_adr0001_no_conflict():
    """README and ADR-0001 must both identify the same three final docs as authority."""
    with open(README_PATH) as f:
        readme = f.read()
    adr_path = os.path.join(DOCS_DIR, "ADR-0001-authority-and-scope.md")
    with open(adr_path) as f:
        adr = f.read()
    for doc in FINAL_AUTHORITY_FILES:
        assert doc in readme, f"README missing {doc}"
        assert doc in adr, f"ADR-0001 missing {doc}"
