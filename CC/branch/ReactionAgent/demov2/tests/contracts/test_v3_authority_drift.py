"""V3 remediation: authority drift regression tests (Section 5, 19).

Verifies ADR-0001 and README use the same precise authority set and that
no wildcard silently includes final_discussion.md in the historical set.

Negative cases (Section 19):
- #18 ADR-0001 "All discussion files" wildcard -> fail
- README historical wildcard includes final_discussion -> fail
- non-final authority-claiming document without historical banner -> fail
"""

import os

import pytest

DEMOV2_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
PLAN_DIR = os.path.join(DEMOV2_ROOT, "plan")
DOCS_DIR = os.path.join(DEMOV2_ROOT, "docs", "decisions")
README_PATH = os.path.join(DEMOV2_ROOT, "README.md")
ADR0001_PATH = os.path.join(DOCS_DIR, "ADR-0001-authority-and-scope.md")

FINAL_AUTHORITY_FILES = [
    "final_design.md",
    "final_plan.md",
    "final_discussion.md",
]

# All non-final documents that previously claimed or could claim authority.
# Each MUST carry a HISTORICAL/NON-AUTHORITATIVE banner in its first lines.
# Missing file = FAIL (not skip), per Section 17 zero-skip requirement.
NON_FINAL_AUTHORITY_DOCS = [
    "chatgpt-reaction-analogy-agent-design.md",
    "chatgpt-reaction-analogy-agent-plan.md",
    "chatgpt-reaction-analogy-agent-design-v2.md",
    "chatgpt-reaction-analogy-agent-plan-v2.md",
    "CLAUDE_DESIGN_LLM_LATENT_STAGE_REASONING_2026-07-29.md",
    "CLAUDE_PLAN_LLM_LATENT_STAGE_REASONING_2026-07-29.md",
    "UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md",
    "UNIFIED_PLAN_REACTION_ANALOGY_AGENT_2026-07-29.md",
    "FUSION_DESIGN_V5.md",
    "qwen_design.md",
    "qwen_plan.md",
    "chatgpt-discussion.md",
    "CLAUDE_discussion.md",
    "qwen_discussion.md",
]


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


def _first_lines(path: str, n: int = 10) -> str:
    with open(path) as f:
        return "".join(f.readline() for _ in range(n))


# -- ADR-0001 wildcard (Section 19 #18) --

@pytest.mark.contract
def test_adr0001_no_all_discussion_files_wildcard():
    """ADR-0001 must NOT contain the wildcard 'All discussion files' which
    would include final_discussion.md in the historical set."""
    content = _read(ADR0001_PATH)
    assert "All discussion files" not in content, (
        "ADR-0001 contains wildcard 'All discussion files' — this catches "
        "final_discussion.md and contradicts the three-final authority set"
    )


@pytest.mark.contract
def test_adr0001_final_discussion_in_authority_set():
    """final_discussion.md must be explicitly listed as authority in ADR-0001."""
    content = _read(ADR0001_PATH)
    assert "final_discussion.md" in content


# -- README wildcard --

@pytest.mark.contract
def test_readme_no_historical_wildcard_including_final_discussion():
    """README must not use a bare 'All other documents in plan/' wildcard
    that would include final_discussion.md without an explicit exception."""
    content = _read(README_PATH)
    bare_wildcard = "All other documents in `plan/` are historical"
    if bare_wildcard in content:
        lower = content.lower()
        assert "except" in lower or "excluding" in lower, (
            "README uses 'All other documents in plan/' wildcard without an "
            "explicit exception for the three final authority files"
        )


@pytest.mark.contract
def test_readme_and_adr0001_same_authority_set():
    """README and ADR-0001 must reference the same three final authority files."""
    readme = _read(README_PATH)
    adr = _read(ADR0001_PATH)
    for doc in FINAL_AUTHORITY_FILES:
        assert doc in readme, f"README missing authority file: {doc}"
        assert doc in adr, f"ADR-0001 missing authority file: {doc}"


# -- Non-final authority docs must have historical banner (Section 19 #18c) --

@pytest.mark.contract
@pytest.mark.parametrize("fname", NON_FINAL_AUTHORITY_DOCS)
def test_non_final_authority_doc_has_historical_banner(fname):
    """Every non-final authority-claiming document must carry a
    HISTORICAL/NON-AUTHORITATIVE banner in its first 10 lines.
    Missing file = FAIL (not skip), per Section 17 zero-skip requirement."""
    path = os.path.join(PLAN_DIR, fname)
    assert os.path.isfile(path), f"Non-final authority doc missing: {fname}"
    head = _first_lines(path)
    assert "HISTORICAL" in head or "NON-AUTHORITATIVE" in head, (
        f"{fname} missing HISTORICAL/NON-AUTHORITATIVE banner in first 10 lines"
    )
