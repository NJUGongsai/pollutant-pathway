#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bible_checks 汇总 runner:跑目录下全部 check_*.py,输出汇总表。

调用:
    python3 scripts/bible_checks/run_all.py [--repo <repo根>]

- 每个子检查以 `python3 <script> --repo <repo>` 独立进程运行;
- 汇总表:check / status / n_pass / n_fail / 耗时;
- 退出码:任一 fail → 1;无 fail 但有 error → 2;全 pass → 0。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT  # noqa: E402

CHECK_DIR = Path(__file__).resolve().parent


def discover_checks() -> list[Path]:
    """发现 check_*.py(不含 runner 自身),按名字排序。"""
    return sorted(p for p in CHECK_DIR.glob("check_*.py") if p.is_file())


def last_json_line(stdout: str) -> dict | None:
    """从子检查 stdout 提取最后一行契约 JSON;解析失败返回 None。"""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except ValueError:
                return None
    return None


def run_one(script: Path, repo: Path) -> dict:
    """跑单个子检查,返回汇总行(dict)。子检查崩溃 → error 行。"""
    t0 = time.monotonic()
    try:
        r = subprocess.run([sys.executable, str(script), "--repo", str(repo)],
                           capture_output=True, text=True, timeout=120)
        elapsed = time.monotonic() - t0
        payload = last_json_line(r.stdout)
        if payload is None:
            return {"check": script.stem, "status": "error", "n_pass": 0, "n_fail": 0,
                    "elapsed": elapsed, "detail": (r.stderr or r.stdout).strip()[:160]}
        return {"check": payload.get("check", script.stem),
                "status": payload.get("status", "error"),
                "n_pass": payload.get("n_pass", 0), "n_fail": payload.get("n_fail", 0),
                "elapsed": elapsed, "detail": ""}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"check": script.stem, "status": "error", "n_pass": 0, "n_fail": 0,
                "elapsed": time.monotonic() - t0, "detail": str(e)[:160]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="bible_checks 汇总 runner")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(传给各子检查)")
    args = ap.parse_args(argv)
    repo = Path(args.repo)

    scripts = discover_checks()
    if not scripts:
        print("未发现任何 check_*.py", file=sys.stderr)
        return 2

    rows = [run_one(s, repo) for s in scripts]

    print(f"{'check':<28}{'status':<8}{'pass':>6}{'fail':>6}{'耗时s':>9}")
    print("-" * 57)
    for r in rows:
        print(f"{r['check']:<28}{r['status']:<8}{r['n_pass']:>6}{r['n_fail']:>6}{r['elapsed']:>9.2f}")
        if r.get("detail"):
            print(f"    └ {r['detail']}")
    statuses = [r["status"] for r in rows]
    print("-" * 57)
    print(f"合计 {len(rows)} 项检查: pass={statuses.count('pass')} "
          f"fail={statuses.count('fail')} error={statuses.count('error')}")
    if "fail" in statuses:
        return 1
    if "error" in statuses:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
