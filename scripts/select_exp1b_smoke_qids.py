#!/usr/bin/env python3
"""EXP-1b 冒烟题目确定性挑选脚本 (B4 规范).

根据 pre-registration / launch order 要求:
从各域调参子集 (holdout_v1 dev_qids.txt) 中按候选池宽度 (只读 batch_manifest.json 的 pool_size，零金标触碰)
确定性挑选 3 题:
1. 空池 (pool_size == 0)
2. 池宽 1–3 (1 <= pool_size <= 3)
3. 池宽 4–8 (4 <= pool_size <= 8)
挑选顺序严格遵照 manifest.registration_order 中出现的首题。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def select_smoke_qids(manifest_path: Path, dev_qids_path: Path) -> list[str]:
    manifest_path = Path(manifest_path)
    dev_qids_path = Path(dev_qids_path)

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not dev_qids_path.is_file():
        raise FileNotFoundError(f"dev_qids not found: {dev_qids_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dev_qids = set(dev_qids_path.read_text(encoding="utf-8").splitlines())

    entries = manifest.get("entries") or []
    if isinstance(entries, list):
        entry_by_qid = {e["qid"]: e for e in entries if "qid" in e}
    elif isinstance(entries, dict):
        entry_by_qid = entries
    else:
        raise ValueError("Invalid entries format in manifest")

    order = manifest.get("registration_order")
    if not order:
        order = list(entry_by_qid.keys())

    empty_qid: str | None = None
    w1_3_qid: str | None = None
    w4_8_qid: str | None = None

    for qid in order:
        if qid not in dev_qids:
            continue
        entry = entry_by_qid.get(qid)
        if not entry:
            continue
        pool_size = int(entry.get("pool_size", 0))

        if empty_qid is None and pool_size == 0:
            empty_qid = qid
        elif w1_3_qid is None and 1 <= pool_size <= 3:
            w1_3_qid = qid
        elif w4_8_qid is None and 4 <= pool_size <= 8:
            w4_8_qid = qid

        if empty_qid and w1_3_qid and w4_8_qid:
            break

    if not empty_qid:
        raise RuntimeError("No candidate found for empty pool (pool_size == 0)")
    if not w1_3_qid:
        raise RuntimeError("No candidate found for pool width 1-3")
    if not w4_8_qid:
        raise RuntimeError("No candidate found for pool width 4-8")

    return [empty_qid, w1_3_qid, w4_8_qid]


def main() -> None:
    parser = argparse.ArgumentParser(description="Select deterministic smoke QIDs for EXP-1b")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to batch_manifest.json")
    parser.add_argument("--dev-qids", type=Path, required=True, help="Path to dev_qids.txt")
    parser.add_argument("--out", type=Path, default=None, help="Output path to save selected QIDs")
    parser.add_argument("--domain", type=str, default="", help="Domain label (for info)")
    args = parser.parse_args()

    selected = select_smoke_qids(args.manifest, args.dev_qids)

    out_content = "\n".join(selected) + "\n"
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_content, encoding="utf-8")
        print(f"[{args.domain or 'INFO'}] Selected 3 smoke QIDs saved to {out_path}:")
    else:
        print(f"[{args.domain or 'INFO'}] Selected 3 smoke QIDs:")

    for idx, (label, qid) in enumerate(
        zip(["pool_size=0", "pool_size=1-3", "pool_size=4-8"], selected), start=1
    ):
        print(f"  {idx}. {label}: {qid}")


if __name__ == "__main__":
    main()
