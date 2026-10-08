#!/usr/bin/env python3
"""Run a pytest command with full evidence capture (argv/env/exit/SHA).

Usage: run_with_capture.py <cwd> <out_dir> <args...>
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

cwd = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
command = [sys.executable, "-B", "-m", "pytest",
           "-p", "no:cacheprovider"] + sys.argv[3:]
env = dict(os.environ)
env["PYTHONDONTWRITEBYTECODE"] = "1"
env.setdefault("PYTHONPATH", str(cwd / "src"))
start = time.monotonic()
with (out / "stdout.txt").open("w", encoding="utf-8") as so, \
        (out / "stderr.txt").open("w", encoding="utf-8") as se:
    result = subprocess.run(command, cwd=cwd, env=env,
                            stdout=so, stderr=se)
elapsed = round(time.monotonic() - start, 3)
record = {
    "command": command,
    "cwd": str(cwd),
    "env": {"PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": env.get("PYTHONPATH", ""),
            "PATH": env.get("PATH", "")},
    "exit_code": result.returncode,
    "elapsed_wall_seconds": elapsed,
    "stdout_sha256": hashlib.sha256(
        (out / "stdout.txt").read_bytes()).hexdigest(),
    "stderr_sha256": hashlib.sha256(
        (out / "stderr.txt").read_bytes()).hexdigest(),
    "git_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=cwd, text=True).strip(),
    "git_dirty": subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=cwd,
        text=True).strip().splitlines(),
}
(out / "execution_record.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8")
print(json.dumps({k: record[k] for k in
                  ("exit_code", "elapsed_wall_seconds")}))
raise SystemExit(result.returncode)
