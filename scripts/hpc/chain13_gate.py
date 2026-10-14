#!/usr/bin/env python
"""chain13 阶段门(读批终态文件 batch_report.json;v43 仓发车无 v44
launcher,冒烟/全量门直读终态)。

用法: python -B chain13_gate.py run-gate --batch-root <B> --label smoke2|smoke10|full
      python -B chain13_gate.py score-gate --batch-root <B>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_gate(batch_root: str, label: str) -> int:
    root = Path(batch_root)
    report = json.loads(
        (root / "batch_report.json").read_text(encoding="utf-8"))
    n_c = int(report.get("n_completed") or 0)
    n_f = int(report.get("n_failed") or 0)
    n_p = int(report.get("n_pending") or 0)
    print(f"[{label}] completed={n_c} failed={n_f} pending={n_p}")
    if label == "smoke2":
        assert n_c + n_f + n_p == 2, (n_c, n_f, n_p)
        assert n_c >= 1, f"smoke2 零完成(传输/凭证问题)——停"
    elif label == "smoke10":
        assert n_c + n_f + n_p == 10, (n_c, n_f, n_p)
        assert n_c >= 2, f"smoke10 完成数异常(n_c={n_c})——停"
    else:
        assert n_c + n_f + n_p == 298, (n_c, n_f, n_p)
        assert n_p == 0, f"全量后仍有 pending={n_p}(断点续跑=同参重投)"
    print(f"[{label}] GATE-OK")
    return 0


def score_gate(batch_root: str) -> int:
    root = Path(batch_root)
    manifest = json.loads(
        (root / "batch_manifest.json").read_text(encoding="utf-8"))
    order = [str(q) for q in manifest.get("registration_order") or []]
    pending, invalid = [], []
    for qid in order:
        path = root / "cases" / f"{qid}.json"
        if not path.is_file():
            pending.append(qid)
            continue
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            invalid.append(qid)
            continue
        if str(case.get("status") or "") not in ("completed", "failed"):
            pending.append(qid)
    if pending or invalid:
        print(f"pending={len(pending)} head={pending[:5]} "
              f"invalid={len(invalid)}")
        return 1
    n_failed = sum(
        1 for qid in order
        if str((json.loads(
            (root / "cases" / f"{qid}.json").read_text(
                encoding="utf-8")) or {}).get("status")) == "failed")
    print(f"SCORE-GATE-OK: n_terminal={len(order)} n_failed={n_failed} "
          "(失败题留分母)")
    return 0


def build_gate(batch_root: str) -> int:
    root = Path(batch_root)
    manifest = json.loads(
        (root / "batch_manifest.json").read_text(encoding="utf-8"))
    order = manifest.get("registration_order") or []
    n = manifest.get("n_questions")
    assert n == 298 and len(order) == 298, f"n={n} len={len(order)}"
    assert manifest.get("provider_kind") == "real"
    assert str(manifest.get("questions_source_sha256")) == \
        "9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c"
    entries = manifest.get("entries") or []
    supplied = sum(
        1 for e in entries
        if isinstance(e.get("pool_diagnostics"), dict)
        and e["pool_diagnostics"].get("cosubstrate_pool_labels")
        is not None)
    print(f"BUILD-GATE-OK: n=298 sha=9f5955d4… "
          f"entries_with_cosub_labels={supplied}/298")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="phase", required=True)
    p_build = sub.add_parser("build-gate")
    p_build.add_argument("--batch-root", required=True)
    p_run = sub.add_parser("run-gate")
    p_run.add_argument("--batch-root", required=True)
    p_run.add_argument("--label", required=True,
                       choices=("smoke2", "smoke10", "full"))
    p_score = sub.add_parser("score-gate")
    p_score.add_argument("--batch-root", required=True)
    args = parser.parse_args(argv)
    if args.phase == "build-gate":
        return build_gate(args.batch_root)
    if args.phase == "run-gate":
        return run_gate(args.batch_root, args.label)
    return score_gate(args.batch_root)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except AssertionError as exc:
        print(f"GATE-FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
