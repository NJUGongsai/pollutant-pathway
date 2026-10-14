#!/usr/bin/env python
"""chain13 发车 wrapper(run 期;v43 仓发车——profile_policy 覆盖入口)。

CC 2026-10-14 拍板:每题真实模型调用上限 1→3(max_real_model_requests=3
+ format_feedback_rounds 0→2 消费路径;attempts/hypothesis=1 不变)。
经 run_s5b_batch 的 profile_policy 参数发车覆盖(冻结进批根
orchestration.json,同批复用改参即拒,零代码改动;S5B_DEFAULT_
PROFILE_POLICY 全局缺省 1/0 不动)。

用法(HPC 仓根,PYTHONPATH=<v43c13>/src):
    python -B chain13_run_wrapper.py <batch_root> <runs_root> <env_file> \
        [--limit N] [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import sys

from pathway_v43.pollutant.s5b_orchestrator import (
    S5B_DEFAULT_PROFILE_POLICY,
    run_s5b_batch,
)

CHAIN13_PROFILE = {
    "search_limits": {
        **S5B_DEFAULT_PROFILE_POLICY["search_limits"],
        "max_real_model_requests": 3,
    },
    "format_feedback_policy": {
        **S5B_DEFAULT_PROFILE_POLICY["format_feedback_policy"],
        "max_format_feedback_rounds": 2,
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="chain13 发车(每题≤3 真实调用;no-cap)")
    parser.add_argument("--batch-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--limit", type=int, default=None,
                        help="冻结注册序前 N 题(冒烟段并入正式批)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--gate-max-calls", type=int, default=4470,
                        help="298×3 logical×5 HTTP attempts 上限")
    args = parser.parse_args(argv)

    agg = run_s5b_batch(
        args.batch_root,
        runs_root=args.runs_root,
        env_file=args.env_file,
        workers=args.workers,
        max_in_flight=args.workers,
        gate_rpm=200,
        gate_tpm=3_000_000,
        gate_max_calls=args.gate_max_calls,
        profile_policy=CHAIN13_PROFILE,
        question_limit=args.limit,
    )
    out = {
        "command": "chain13_run",
        "ok": True,
        "n_total": agg.get("n_total"),
        "n_completed": agg.get("n_completed"),
        "n_failed": agg.get("n_failed"),
        "n_pending": agg.get("n_pending"),
        "profile_policy": CHAIN13_PROFILE,
        "batch_report": str(agg.get("batch_report")),
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
