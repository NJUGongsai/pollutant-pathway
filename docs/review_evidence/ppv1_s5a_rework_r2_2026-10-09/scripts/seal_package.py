#!/usr/bin/env python3
"""Seal the S5a rework r2 evidence package: manifest.json + SHA256SUMS
over EVERY file in the package (including nested manifests, junit,
stdout/stderr, sub-package controls and this script itself), excluding
only the two root self-control files (manifest.json and SHA256SUMS
themselves). SQLite/pyc/pytest-cache/symlinks are not packaged by
policy (paths-only lists of isolated pyc are already recorded in
post_run_sha_result.json).
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
SELF_CONTROL = {"manifest.json", "SHA256SUMS"}
SKIP_SUFFIXES = (".pyc",)
SKIP_NAMES = {".DS_Store"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


entries = []
for path in sorted(ROOT.rglob("*")):
    if path.is_symlink():
        raise RuntimeError(f"symlink in evidence package: {path}")
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT).as_posix()
    if len(rel.split("/")) == 1 and rel in SELF_CONTROL:
        continue
    if rel.endswith(SKIP_SUFFIXES) or path.name in SKIP_NAMES:
        continue
    entries.append({"path": rel, "sha256": sha256(path), "bytes":
                    path.stat().st_size})

head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                               cwd=ROOT.parents[2], text=True).strip()
manifest = {
    "package": "ppv1_s5a_rework_r2_2026-10-09",
    "sealed_at_head": head,
    "note": ("sealed before the r2 commit; the working tree carried the "
             "r2 deliverable bytes (git status recorded in the suite "
             "execution records); only the two root self-control files "
             "are excluded from hashing; this script is hashed"),
    "n_files": len(entries),
    "files": entries,
}
(ROOT / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8")
with (ROOT / "SHA256SUMS").open("w", encoding="utf-8") as fh:
    for entry in entries:
        fh.write(f"{entry['sha256']}  {entry['path']}\n")
print(json.dumps({"n_files": len(entries), "head": head}))
