#!/usr/bin/env python3
"""Replay only frozen synthetic R8 review probes into fresh external tmp.

Use depending43 Python with --repo <R8 checkout> --out <nonexistent tmp>.
This archival controller is statically checked, not itself executed during
the interrupted review's resumption. Original execution logs remain separate.
It never runs pytest, models, real evaluation data, or probes inside this bundle.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HEAD = "00e509a974b40a7c9779fcd35e53b16637a13d60"
PARENT = "858dd94c7c6c8fc387940242403d67b6b36b5313"
ORIGINAL_REPO = Path("/Volumes/CC/Enzyme_Agent/dependingv43")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def source_inputs(repo, snapshot):
    expected = {}
    for name, digest in snapshot["input_sha256"].items():
        rel = Path(name).relative_to(ORIGINAL_REPO)
        if rel.parts[0] == "src" or rel == Path("pyproject.toml"):
            expected[str(rel)] = digest
    actual_names = {str(p.relative_to(repo)) for p in (repo / "src").rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts}
    actual_names.add("pyproject.toml")
    if actual_names != set(expected):
        raise RuntimeError("Source file set drift; only pinned R8 inputs are allowed")
    for name, digest in expected.items():
        p = repo / name
        if not p.is_file() or not p.resolve().is_relative_to(repo):
            raise RuntimeError("Missing or escaped source input: " + name)
        if sha(p) != digest:
            raise RuntimeError("Pinned source input hash drift: " + name)
    return expected


def bundle_inputs(bundle):
    # Publication adds this manifest after this new controller is included.
    sums = bundle / "SHA256SUMS"
    if not sums.is_file():
        raise RuntimeError("Published bundle SHA256SUMS is required")
    checked = {}
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts:
            raise RuntimeError("Unsafe bundle manifest path")
        p = bundle / rel
        if not p.is_file() or not p.resolve().is_relative_to(bundle) or sha(p) != digest:
            raise RuntimeError("Bundle hash drift or missing input: " + name)
        checked[name] = digest
    for required in ("reproduce.py", "replay_review.py", "input_snapshot.json",
                     "assert_r7_replay.py", "r6_selected_outcome_reference.json"):
        if required not in checked:
            raise RuntimeError("Unpinned controller dependency: " + required)
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    bundle = Path(__file__).resolve().parent
    out = args.out.expanduser().resolve()
    if out.exists():
        raise RuntimeError("Require a nonexistent output directory")
    for boundary in (repo, bundle):
        if out == boundary or out.is_relative_to(boundary) or boundary.is_relative_to(out):
            raise RuntimeError("Output must be separate from repository and permanent bundle")
    actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^"], text=True).strip()
    if (actual, parent) != (HEAD, PARENT):
        raise RuntimeError("Require the pinned R8 HEAD and parent")
    fixed_bundle = bundle_inputs(bundle)
    snapshot = json.loads((bundle / "input_snapshot.json").read_text())
    if (snapshot["actual_head"], snapshot["parent_head"]) != (HEAD, PARENT):
        raise RuntimeError("Unexpected archived input snapshot")
    fixed_source = source_inputs(repo, snapshot)
    out.mkdir(parents=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(out))
    commands = []
    metadata = {"actual_head": actual, "parent_head": parent, "repo": str(repo),
                "read_only_bundle": str(bundle), "out": str(out), "python": sys.version,
                "started_utc": datetime.now(timezone.utc).isoformat(), "synthetic_only": True,
                "pytest_or_models_invoked": False, "source_input_sha256": fixed_source,
                "bundle_input_sha256": fixed_bundle, "commands": commands}

    def run(argv, cwd, stdout, stderr, expected=0):
        record = {"argv": argv, "cwd": str(cwd), "stdout": stdout, "stderr": stderr,
                  "expected_exit_code": expected}
        with (out / stdout).open("w") as so, (out / stderr).open("w") as se:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=so, stderr=se)
        record.update(exit_code=result.returncode, stdout_sha256=sha(out / stdout),
                      stderr_sha256=sha(out / stderr))
        commands.append(record)
        write_json(out / "wrapper_commands.json", commands)
        if result.returncode != expected:
            raise RuntimeError("Unexpected probe exit: " + stdout)

    try:
        body = (bundle / "replay_review.py").read_text()
        replacements = {
            "P=Path(__file__).resolve().parent;REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43')":
                "P=Path(__file__).resolve().parent;REPO=Path(" + repr(str(repo)) + ")",
            "B=REPO/'docs/review_evidence/ppv1_r7_codex_2026-10-07'":
                "B=Path(" + repr(str(bundle)) + ")",
            "REPO/'docs/review_evidence/ppv1_r8_impl_2026-10-07/chem/r8_probe_completion.py'":
                "B/'chemistry_current/r8_probe_completion.py'",
        }
        for old, new in replacements.items():
            if body.count(old) != 1:
                raise RuntimeError("Archived replay controller shape changed")
            body = body.replace(old, new)
        ast.parse(body)
        (out / "replay_review.py").write_text(body)
        run([sys.executable, "-B", str(out / "replay_review.py")], out,
            "replay_review_controller.stdout.txt", "replay_review_controller.stderr.txt")

        isolated = out / "r6_replay"
        shutil.copy2(repo / "pyproject.toml", isolated / "pyproject.toml")
        lane = out / "chemical_matrix"
        lane.mkdir()
        (lane / "src").symlink_to(isolated / "src", target_is_directory=True)
        for name in ("state_first_consumer_probe.py", "static_contract_inventory.py", "assert_r8_chemical_observed.py"):
            shutil.copy2(bundle / "chemical_matrix" / name, lane / name)
        shutil.copytree(bundle / "chemical_matrix/tests", lane / "tests")
        chemical_meta = json.loads((bundle / "chemical_matrix/metadata.json").read_text())
        chemical_meta.update(actual_HEAD=actual, parent_HEAD=parent, source_repository=str(repo), python=sys.version,
                             source_files={"src/" + str(p.relative_to(isolated / "src")): sha(p)
                                           for p in sorted((isolated / "src").rglob("*")) if p.is_file()},
                             fixture_files={str(p.relative_to(lane)): sha(p)
                                            for p in sorted((lane / "tests").rglob("*")) if p.is_file()})
        from rdkit import rdBase
        chemical_meta["rdkit"] = rdBase.rdkitVersion
        write_json(lane / "metadata.json", chemical_meta)
        shutil.copy2(out / "r7_chemical_replay.stdout.txt", lane / "chemical_boundary_output.jsonl")
        shutil.copy2(out / "r7_chemical_replay.stderr.txt", lane / "chemical_boundary_stderr.txt")
        prior = json.loads((out / "root_commands.json").read_text())
        old_run = next(x for x in prior if x["stdout"] == "r7_chemical_replay.stdout.txt")
        write_json(lane / "chemical_probe_run.json", {"command": old_run["argv"], "cwd": old_run["cwd"],
                   "returncode": old_run["exit_code"], "jsonl_records": 55,
                   "note": "This fresh replay stopped at the expected unwrapped chiral refusal."})
        run([sys.executable, "-B", str(lane / "state_first_consumer_probe.py")], lane,
            "chemical_matrix/state_first_consumer_output.jsonl", "chemical_matrix/state_first_consumer_stderr.txt")
        if len((lane / "state_first_consumer_output.jsonl").read_text().splitlines()) != 60:
            raise RuntimeError("Expected 60 chemical matrix records")
        run([sys.executable, "-B", str(lane / "static_contract_inventory.py")], lane,
            "chemical_matrix/static_contract_inventory.json", "chemical_matrix/static_contract_inventory.stderr.txt")
        run([sys.executable, "-B", str(lane / "assert_r8_chemical_observed.py")], lane,
            "chemical_matrix/assert_r8_chemical_observed.stdout.txt", "chemical_matrix/assert_r8_chemical_observed.stderr.txt")

        storage = out / "storage_current"
        run([sys.executable, "-B", str(storage / "storage_r8_public_matrix.py"), str(isolated)], storage,
            "storage_r8_matrix.stdout.txt", "storage_r8_matrix.stderr.txt")
        storage_rows = [json.loads(line) for line in (out / "storage_r8_matrix.stdout.txt").read_text().splitlines()]
        if len(storage_rows) != 19 or storage_rows[-1].get("cases_checked") != 17 or storage_rows[-1].get("status") != "pass":
            raise RuntimeError("Expected all 17 storage cases and final assertion")
        run([sys.executable, "-B", str(storage / "assert_storage_r8_observed.py"),
             str(storage / "storage_contract_probe.output.jsonl")], storage,
            "storage_r8_old15_assert.stdout.txt", "storage_r8_old15_assert.stderr.txt")
        if source_inputs(repo, snapshot) != fixed_source or bundle_inputs(bundle) != fixed_bundle:
            raise RuntimeError("Read-only inputs changed during reproduction")
        metadata["status"] = "completed"
        metadata["counts"] = {"R6_probe_scripts": 12, "R7_chemical_rows_before_expected_stop": 55,
                              "chemical_tail_rows": 3, "R7_condition_cases": 16,
                              "R7_storage_cases": 15, "chemical_matrix_records": 60, "storage_matrix_cases": 17}
    except BaseException as exc:
        metadata.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(out / "reproduction_metadata.json", metadata)
    print(json.dumps({"status": metadata["status"], "actual_head": actual, "out": str(out),
                      "counts": metadata["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
