"""P7 T4 P2-closure pin tests (RED first).

Closes the three P2 findings from the T0② Round 1 audit:

- P7-T0②-01: ``_evidence_id_of`` dead code removed from ``p3_p4_bridge.py``
  (no callsite — delete).
- P7-T0②-03: the default ``current_run_path``
  (``reports/p3/current_run_artifact.json``) is gitignored so production
  wiring using the default cannot create an untracked file in the committed
  ``reports/p3/`` tree.

RED until the P2 fixes land; GREEN after.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_evidence_id_of_dead_code_removed():
    """P7-T0②-01: the unused ``_evidence_id_of`` helper is gone."""
    import reaction_agent.adapters.p3_p4_bridge as bridge

    assert not hasattr(bridge, "_evidence_id_of"), (
        "_evidence_id_of is dead code (no callsite) — must be removed"
    )
    # And no leftover reference anywhere in the bridge source.
    src = Path(bridge.__file__).read_text(encoding="utf-8")
    assert "_evidence_id_of" not in src, (
        "_evidence_id_of still referenced in p3_p4_bridge.py source"
    )


def test_default_current_run_path_is_gitignored():
    """P7-T0②-03: the default current-run artifact path is gitignored so
    production wiring using the default cannot pollute the committed
    ``reports/p3/`` tree with an untracked file."""
    target = "reports/p3/current_run_artifact.json"
    # Must NOT be tracked by git (it's a generated artifact).
    tracked = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "ls-files", "--", target],
        capture_output=True, text=True,
    )
    assert tracked.stdout.strip() == "", f"{target} must not be tracked"

    # Must be gitignored.
    check = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "check-ignore", "--quiet", target],
    )
    assert check.returncode == 0, (
        f"{target} must be gitignored (git check-ignore returned "
        f"{check.returncode})"
    )
