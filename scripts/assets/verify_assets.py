#!/usr/bin/env python3
"""按 assets_manifest.json 校验本地文件是否与清单一致（只读）。"""
import hashlib, json, sys
from pathlib import Path


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    manifest = Path(sys.argv[1] if len(sys.argv) > 1 else "assets_manifest.json")
    root = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    ok = missing = mismatch = 0
    for item in data["files"]:
        p = root / item["path"]
        if not p.exists():
            missing += 1
            print(f"MISSING  {item['path']}")
        elif sha256(p) != item["sha256"]:
            mismatch += 1
            print(f"MISMATCH {item['path']}")
        else:
            ok += 1
    print(f"\n一致 {ok} / 缺失 {missing} / 校验失败 {mismatch}（共 {len(data['files'])}）")
    return 1 if (missing or mismatch) else 0


if __name__ == "__main__":
    raise SystemExit(main())
