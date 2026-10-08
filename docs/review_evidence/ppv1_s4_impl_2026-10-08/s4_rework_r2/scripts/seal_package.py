#!/usr/bin/env python3
"""S4 回修 r2 证据封包:manifest.json + SHA256SUMS(全附件相对路径
SHA-256;外层 manifest/SHA256SUMS 自排除)。只读归档目录,不执行任何
写库程序。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    records: dict[str, str] = {}
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(package))
        if rel in ("manifest.json", "SHA256SUMS", "report.sha256"):
            continue
        records[rel] = sha256(path)
    lines = [f"{v}  {k}" for k, v in sorted(records.items())]
    (package / "SHA256SUMS").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8")
    manifest = {
        "package": "ppv1 S4 rework r2 implementation evidence",
        "n_files": len(records),
        "files": records,
        "note": ("全部附件相对路径 SHA-256;manifest.json/SHA256SUMS 自"
                 "排除;证据归档后只读,不在本目录运行任何写库程序"),
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({"n_files": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
