#!/usr/bin/env python3
"""S4 回修 r2:冻结 legacy/共享源码 code identity 聚合(两树比对)。

52 份非 pollutant/ 的 src .py 文件(legacy/export_v3/storage/domain/
vendor 等冻结面)逐文件 SHA-256 → 聚合 content_hash;当前工作树与
直接父 0dd35d1 detached worktree 各算一次,比对一致 ⇒ 本批
(S4-C02/S4-C04,只改 pollutant/ 与 tests/)对冻结 legacy 面零触碰。
只读,不写任何仓内文件;输出 JSON 落调用方给定的新 tmp 路径。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from pathway_v43.domain.models import content_hash  # noqa: E402


def aggregate(src_root: Path) -> dict:
    files = sorted(
        p for p in src_root.rglob("*.py")
        if "pollutant" not in p.relative_to(src_root).parts
        and "__pycache__" not in p.parts)
    hashes = {
        str(p.relative_to(src_root)): hashlib.sha256(
            p.read_bytes()).hexdigest() for p in files}
    return {"files": len(files), "aggregate": content_hash(hashes),
            "per_file_sha256": hashes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-src", required=True, type=Path)
    parser.add_argument("--parent-src", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"输出已存在,须用新 tmp:{args.out}")
    current = aggregate(args.current_src.resolve())
    parent = aggregate(args.parent_src.resolve())
    differing = sorted(
        k for k in current["per_file_sha256"]
        if current["per_file_sha256"][k] != parent["per_file_sha256"].get(k))
    result = {
        "purpose": "S4 r2 冻结 legacy/共享源码 code identity 两树比对",
        "current_src": str(args.current_src.resolve()),
        "parent_src": str(args.parent_src.resolve()),
        "current": {"files": current["files"],
                    "aggregate": current["aggregate"]},
        "parent": {"files": parent["files"],
                   "aggregate": parent["aggregate"]},
        "byte_identical": current["aggregate"] == parent["aggregate"],
        "differing_files": differing,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("current", "parent", "byte_identical",
                       "differing_files")}, ensure_ascii=False))
    return 0 if result["byte_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
