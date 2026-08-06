"""R3-H Git-state independence tests.

Round 2 defect: ``test_changed_files_derived_from_git_state`` required P3
files to be UNTRACKED in the real project — it passed only in the dirty
worktree and failed in an isolated/committed checkout.

Round 3 contract: Git behavior is tested against a TEMPORARY Git repository
created with ``tmp_path`` (clean tracked, modified tracked, untracked and
ignored files created explicitly).  No test inspects or requires the real
project to be dirty.  The report classifies inherited vs Round-3 changes
from structured start/end Git state.
"""
import subprocess

import pytest

import scripts.generate_p3_round3_reports as gen3


def _git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
    )


@pytest.fixture()
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q"], repo)
    _git(["config", "user.email", "r3h@test.local"], repo)
    _git(["config", "user.name", "R3H Test"], repo)
    _git(["config", "commit.gpgsign", "false"], repo)
    # clean tracked file + file that will be modified later
    (repo / "a_clean.txt").write_text("clean tracked content\n")
    (repo / "b_tracked.txt").write_text("original content\n")
    (repo / ".gitignore").write_text("ignored.log\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", "baseline"], repo)
    return repo


def _start_state(repo):
    import hashlib
    state = gen3.git_current_state(str(repo))
    hashes = {}
    for rel in state["untracked"]:
        hashes[rel] = hashlib.sha256(
            (repo / rel).read_bytes()
        ).hexdigest()
    return {
        "modified_tracked_inherited": state["modified_tracked"],
        "untracked_inherited": state["untracked"],
        "untracked_sha256": hashes,
    }


def test_clean_repo_classifies_nothing(tmp_path, git_repo):
    # A committed/clean checkout must classify to EMPTY sets — the old
    # dirty-only test failed exactly here.
    changed = gen3.classify_round3_changes(_start_state(git_repo), str(git_repo))
    assert changed["inherited_tracked_modified"] == []
    assert changed["round3_modified_tracked"] == []
    assert changed["round3_modified_untracked"] == []
    assert changed["round3_new"] == []
    assert changed["generated_reports"] == []


def test_modified_tracked_classified_as_round3(tmp_path, git_repo):
    start = _start_state(git_repo)
    (git_repo / "b_tracked.txt").write_text("MODIFIED in round 3\n")
    changed = gen3.classify_round3_changes(start, str(git_repo))
    assert changed["round3_modified_tracked"] == ["b_tracked.txt"]
    assert changed["inherited_tracked_modified"] == []


def test_untracked_new_classified_and_ignored_excluded(tmp_path, git_repo):
    start = _start_state(git_repo)
    (git_repo / "new_untracked.txt").write_text("round 3 new file\n")
    (git_repo / "ignored.log").write_text("must never appear\n")
    changed = gen3.classify_round3_changes(start, str(git_repo))
    assert changed["round3_new"] == ["new_untracked.txt"]
    # ignored files must NOT leak into any category
    all_paths = (
        changed["inherited_untracked"] + changed["round3_new"]
        + changed["round3_modified_untracked"] + changed["generated_reports"]
    )
    assert "ignored.log" not in all_paths


def test_inherited_untracked_preserved_when_unchanged(tmp_path, git_repo):
    (git_repo / "existing_untracked.txt").write_text("pre-existing\n")
    start = _start_state(git_repo)
    assert start["untracked_inherited"] == ["existing_untracked.txt"]
    changed = gen3.classify_round3_changes(start, str(git_repo))
    assert changed["inherited_untracked"] == ["existing_untracked.txt"]
    assert changed["round3_new"] == []


def test_changed_untracked_classified_as_round3_modified(tmp_path, git_repo):
    (git_repo / "existing_untracked.txt").write_text("pre-existing\n")
    start = _start_state(git_repo)
    # capture hashes like the real round-start snapshot does
    import hashlib
    start["untracked_sha256"] = {
        "existing_untracked.txt": hashlib.sha256(b"pre-existing\n").hexdigest(),
    }
    (git_repo / "existing_untracked.txt").write_text("changed during round 3\n")
    changed = gen3.classify_round3_changes(start, str(git_repo))
    assert changed["round3_modified_untracked"] == ["existing_untracked.txt"]
    assert changed["inherited_untracked"] == []


def test_generated_reports_category(tmp_path, git_repo):
    start = _start_state(git_repo)
    reports_dir = git_repo / "reports" / "p3"
    reports_dir.mkdir(parents=True)
    (reports_dir / "P3_ROUND_3_FAKE.json").write_text("{}")
    changed = gen3.classify_round3_changes(start, str(git_repo))
    assert "reports/p3/P3_ROUND_3_FAKE.json" in changed["generated_reports"]


def test_git_current_state_shape(git_repo):
    state = gen3.git_current_state(str(git_repo))
    assert isinstance(state["modified_tracked"], list)
    assert isinstance(state["untracked"], list)
    assert state["modified_tracked"] == []
    assert state["untracked"] == []
