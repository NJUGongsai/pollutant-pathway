#!/usr/bin/env python3
"""Seal the S5a rework r1 evidence package: manifest.json + SHA256SUMS
over every file (nested manifests included); only the root control files
(manifest.json / SHA256SUMS themselves) are excluded from the hash list.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
now = datetime.now(timezone.utc).astimezone()
entries = {}
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT).as_posix()
    if rel in ("manifest.json", "SHA256SUMS", "seal_package.py"):
        continue
    entries[rel] = hashlib.sha256(
        path.read_bytes()).hexdigest()
head = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT.parents[2], text=True).strip()
manifest = {
    "package": "ppv1_s5a_rework_r1_2026-10-09",
    "created": now.isoformat(timespec="seconds"),
    "repo_head_at_seal": head,
    "file_count": len(entries),
    "hash_scope": ("every file under this directory including nested "
                   "manifests and sub-package controls; only root "
                   "control files (manifest.json, SHA256SUMS, "
                   "seal_package.py) excluded"),
    "files": entries,
}
(ROOT / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8")
lines = [f"{digest}  {rel}" for rel, digest in sorted(entries.items())]
(ROOT / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"file_count": len(entries), "created": manifest["created"],
                  "head": head}))
