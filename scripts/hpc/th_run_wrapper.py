#!/usr/bin/env python
"""T-H 发车 wrapper(run 期;chain14 族参数化复用,单臂)。

T-H 预注册(docs/T_H_LAUNCH_PREP_2026-10-20.md §2,CC 2026-10-20 签字):
单臂 298 修复批;**证据卡=关**(沿 chain14 对照臂配置);
- 变量面=已登记修复集(D1.2/E1a/E1b/C/T-F),行内不变;证据卡关卡级关闭;- profile_policy(每题≤3 真实调用 + 2 格式反馈轮)、gate(RPM 200/
  TPM 3M/max_calls 4470)、workers 8、no-cap 标记、transport 重试
  (双臂共享)全部沿 chain13(直接复用 chain13_run_wrapper.CHAIN13_
  PROFILE,不重写语义)。

臂→开关映射在本文件单一写死(EVIDENCE_CARD_BY_ARM),发车参数冻结进
批根 orchestration.json(改参即拒;worker 侧同判据核对)。

用法(HPC 仓根,PYTHONPATH=<v43c14>/src):
    python -B th_run_wrapper.py --batch-root <批根> \
        --runs-root <run根> --env-file <env> [--limit N] [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import sys

from pathway_v43.pollutant.s5b_orchestrator import (
    run_s5b_batch,
)
from chain13_run_wrapper import CHAIN13_PROFILE

# T-H 批根日期段(任务书 2026-10-20;批根/runs 根由 sbatch 脚本派生)
TH_BATCH_DATESTAMP = "20261020"

# T-H 单臂:证据卡关卡级关闭(单一写死,不提供其它取值路径)
EVIDENCE_CARD_ENABLED_T_H = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="T-H 发车(单臂;证据卡关;transport 重试同享)")
    parser.add_argument("--batch-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--limit", type=int, default=None,
                        help="冻结注册序前 N 题(冒烟段并入正式批)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--gate-max-calls", type=int, default=4470,
                        help="298×3 logical×5 HTTP attempts 上限(沿 "
                             "chain13;transport 重试诚实占额,门不放开)")
    args = parser.parse_args(argv)

    evidence_card_enabled = EVIDENCE_CARD_ENABLED_T_H
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
        evidence_card_enabled=evidence_card_enabled,
        question_limit=args.limit,
    )
    out = {
        "command": "th_run",
        "evidence_card_enabled": evidence_card_enabled,
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
