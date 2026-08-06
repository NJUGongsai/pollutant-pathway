"""R2-J report generator tests (real commands, git-based changed-files)."""
import os
import pytest

import scripts.generate_p3_round2_reports as gen


def test_report_full_suite_count_comes_from_actual_command():
    # The generator runs the full suite and parses its REAL pytest summary.
    record = gen.run_command(
        [gen.P3_PY, "-m", "pytest", "tests/p3/test_normalize.py", "-q", "-p", "no:cacheprovider", "--color=no"],
        cwd=gen.PROJECT_ROOT, label="normalize_suite",
    )
    assert record["exit_code"] == 0
    assert record["counts"]["passed"] >= 1
    assert record["stdout_stderr_hash"]
    assert record["python_executable"] == gen.P3_PY


def test_parse_pytest_summary_counts():
    text = "10 passed, 1 failed, 2 errors, 3 skipped, 1 xfailed, 1 xpassed in 5s\n20 tests collected\n"
    counts = gen._parse_pytest_summary(text)
    assert counts["passed"] == 10
    assert counts["failed"] == 1
    assert counts["errors"] == 2
    assert counts["skipped"] == 3
    assert counts["xfailed"] == 1
    assert counts["xpassed"] == 1
    assert counts["collected"] == 20


def test_report_generator_fails_when_full_suite_fails():
    records = [{
        "label": "full_suite", "exit_code": 1,
        "counts": {"collected": 5, "passed": 4, "failed": 1},
    }]
    with pytest.raises(SystemExit):
        gen._fail_closed(records)


def test_report_generator_fails_when_no_tests_collected():
    records = [{
        "label": "full_suite", "exit_code": 0,
        "counts": {"collected": 0, "passed": 0, "failed": 0},
    }]
    with pytest.raises(SystemExit):
        gen._fail_closed(records)


def test_changed_files_derived_from_git_state(tmp_path):
    # R3-H: Git classification is tested against a TEMPORARY repository —
    # never against the (dirty) real project state.  Round 2 asserted P3
    # files were untracked in the real worktree, which only passed in the
    # dirty checkout.
    import subprocess
    import scripts.generate_p3_round3_reports as gen3

    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, check=True,
                       capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "r3h@test.local")
    git("config", "user.name", "R3H Test")
    git("config", "commit.gpgsign", "false")
    (repo / "tracked.txt").write_text("committed\n")
    git("add", "-A")
    git("commit", "-q", "-m", "baseline")

    start = gen3.git_current_state(str(repo))
    start_state = {
        "modified_tracked_inherited": start["modified_tracked"],
        "untracked_inherited": start["untracked"],
        "untracked_sha256": {},
    }
    # Round 3 changes: one modified tracked file + one new file.
    (repo / "tracked.txt").write_text("modified\n")
    (repo / "reaction_agent_p3_module.py").write_text("# p3\n")
    changed = gen3.classify_round3_changes(start_state, str(repo))
    assert changed["round3_modified_tracked"] == ["tracked.txt"]
    assert changed["round3_new"] == ["reaction_agent_p3_module.py"]
    assert changed["inherited_tracked_modified"] == []


def test_submission_does_not_claim_nonexistent_local_venv():
    # The submission must state the worktree has no local .venv and name the
    # actual python used.
    assert not os.path.exists(os.path.join(gen.PROJECT_ROOT, ".venv", "bin", "python"))
    assert gen.P3_PY.startswith("/Volumes/CC/Enzyme_Agent/depending")
