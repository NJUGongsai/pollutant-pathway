#!/usr/bin/env python3
"""S3b runner worker —— 在独立进程里驱动 PPV1 公开 start/resume 后**硬杀
进程**(os._exit),模拟真实进程崩溃(不能以同进程内存异常冒充);
也提供 barrier 双进程争抢同一 run 的并发驱动证据。

由 tests/test_ppv1_s3b_runner.py 以子进程调用;全部输入为合成规则级
夹具(CCO → CC=O),无金标/题面/封存材料。用法:
    python tests/s3b_worker.py start-crash --runs-root R --run-id ID
        --crash-after after_claim|after_request_registered|
        after_bundle_written|after_event_submitted
    python tests/s3b_worker.py resume --runs-root R --run-id ID
    python tests/s3b_worker.py barrier-start --runs-root R --run-id ID
        --barrier-dir D --worker W [--out-json PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def spec(key: str, product: str, tref: str) -> dict:
    return {
        "key": key, "product_smiles": product, "coefficient": 1,
        "transformation_ref": tref, "origin_group_key": f"donor-{key}",
        "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                   "atom2": "S_O_1", "from_order": "single",
                   "to_order": "double"}],
        "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
        "alignment": {"status": "resolved",
                      "donor_to_current": {"S_C_2": "S_C_2",
                                           "S_O_1": "S_O_1"},
                      "ref": "align-A"},
        "expectation": {"target_smiles": product},
    }


def plan(with_model: bool = False) -> dict:
    base = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    if with_model:
        base["model"] = {"provider_kind": "scripted",
                         "responses": ['{"proposals": "not-a-list"}']}
    return base


def hard_exit(code: int = 1) -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)  # 真实进程崩溃:连接不 close、事务不收尾


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["start-crash", "resume",
                                     "barrier-start"])
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--crash-after", default="after_event_submitted")
    ap.add_argument("--with-model", action="store_true",
                    help="计划带 scripted 模型(B2 注入需要请求登记)")
    ap.add_argument("--barrier-dir", default=None)
    ap.add_argument("--worker", default="w1")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    from pathway_v43.config import resolve_config
    from pathway_v43.pollutant.runflow import (
        PPV1RunError,
        resume_ppv1_run,
        start_ppv1_run,
    )
    from pathway_v43.pollutant.search import SearchCrashInjection

    if args.mode == "start-crash":
        try:
            start_ppv1_run(
                config=resolve_config(), runs_root=args.runs_root,
                run_id=args.run_id, smiles="CCO",
                plan=plan(args.with_model), scripted=True,
                crash_after=args.crash_after)
            print(json.dumps({"crashed": False}))
        except SearchCrashInjection as exc:
            print(json.dumps({"crashed": True,
                              "kind": "SearchCrashInjection",
                              "detail": exc.detail}, ensure_ascii=False))
        hard_exit(1)  # 崩溃点之后硬杀(不做清理)

    if args.mode == "resume":
        out = resume_ppv1_run(config=resolve_config(),
                              runs_root=args.runs_root,
                              run_id=args.run_id,
                              plan=plan(args.with_model))
        print(json.dumps({"stop_reason": out["stop_reason"],
                          "events": out["counts"]["events"],
                          "resumed": out["resumed"]},
                         ensure_ascii=False))
        return 0

    if args.mode == "barrier-start":
        # 双进程同时 start 同一 run(RunAlreadyExists 只有一方成立)
        bdir = Path(args.barrier_dir)
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"{args.worker}.ready").write_text("ready\n",
                                                   encoding="utf-8")
        go = bdir / "GO"
        deadline = time.monotonic() + 60.0
        while not go.exists():
            if time.monotonic() > deadline:
                print(json.dumps({"error": "barrier_timeout"}))
                return 9
            time.sleep(0.02)
        try:
            out = start_ppv1_run(
                config=resolve_config(), runs_root=args.runs_root,
                run_id=args.run_id, smiles="CCO", plan=plan(),
                scripted=True)
            result = {"worker": args.worker, "started": True,
                      "stop_reason": out["stop_reason"],
                      "events": out["counts"]["events"]}
            code = 0
        except Exception as exc:  # noqa: BLE001 — 竞争失败也是结果
            result = {"worker": args.worker, "started": False,
                      "error": type(exc).__name__,
                      "kind": getattr(exc, "detail", {}).get("kind")}
            code = 3
        if args.out_json:
            Path(args.out_json).write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return code
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
