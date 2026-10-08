#!/usr/bin/env python3
"""S3b runner worker —— 在独立进程里驱动 PPV1 公开 start/resume 后**硬杀
进程**(os._exit),模拟真实进程崩溃(不能以同进程内存异常冒充);
也提供 barrier 双进程争抢同一 run 的并发驱动证据,以及 r2 回修的
队列级故障注入与并发恢复互斥证据。

由 tests/test_ppv1_s3b_runner.py / tests/test_ppv1_s3b_r2.py 以子进程
调用;全部输入为合成规则级夹具(CCO → CC=O),无金标/题面/封存
材料。用法:
    python tests/s3b_worker.py start-crash --runs-root R --run-id ID
        --crash-after after_claim|after_request_registered|
        after_bundle_written|after_event_submitted
        [--with-model] [--injection after_two_followups|
        after_transition_enqueued]
    python tests/s3b_worker.py resume --runs-root R --run-id ID
        [--with-model] [--no-plan]
    python tests/s3b_worker.py barrier-start --runs-root R --run-id ID
        --barrier-dir D --worker W [--out-json PATH]
    python tests/s3b_worker.py concurrent-resume --runs-root R
        --run-id ID --barrier-dir D --worker first|second
        --tool-receipt-dir T [--out-json PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def spec(key: str, product: str, tref: str, coproducts=None) -> dict:
    d = {
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
    if coproducts is not None:
        d["coproducts"] = list(coproducts)
    return d


def plan(with_model: bool = False, coproducts=None,
         transitions=None) -> dict:
    base = {"pools": {"CCO": [spec("B", "CC=O", "donor-B",
                                   coproducts=coproducts)]}}
    if transitions is not None:
        base["scenario_transitions"] = transitions
    if with_model:
        base["model"] = {"provider_kind": "scripted",
                         "responses": ['{"proposals": "not-a-list"}']}
    return base


def hard_exit(code: int = 1) -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)  # 真实进程崩溃:连接不 close、事务不收尾(flock 由 OS 释放)


def install_injection(injection: str) -> None:
    """队列级故障注入(S3B-03 窗口;只影响本进程,测试用)。"""
    if not injection:
        return
    from pathway_v43.pollutant.search import SearchLedger

    def _hard(kind, detail=None):
        print(json.dumps({"hard_kill": kind, "detail": detail,
                          "pid": os.getpid()}), flush=True)
        hard_exit(77)

    if injection == "after_two_followups":
        orig = SearchLedger.enqueue_action
        count = [0]

        def enqueue(self, *a, **kw):
            r = orig(self, *a, **kw)
            if kw.get("action_kind") == "retrieve" and \
                    (kw.get("payload") or {}).get("source_event_id"):
                count[0] += 1
                if count[0] == 2:
                    _hard(injection, {"count": count[0], "result": dict(r)})
            return r
        SearchLedger.enqueue_action = enqueue
    elif injection == "after_transition_enqueued":
        orig = SearchLedger.enqueue_action

        def enqueue(self, *a, **kw):
            r = orig(self, *a, **kw)
            if kw.get("action_kind") == "scenario_transition":
                _hard(injection, {"result": dict(r)})
            return r
        SearchLedger.enqueue_action = enqueue
    else:
        raise SystemExit(f"未知注入:{injection}")


def _result(exc=None, **kw) -> dict:
    out = dict(kw)
    if exc is not None:
        out["error"] = type(exc).__name__
        out["kind"] = getattr(exc, "detail", {}).get("kind")
        out["message"] = str(exc)[:200]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["start-crash", "resume",
                                     "barrier-start", "concurrent-resume"])
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--crash-after", default="after_event_submitted",
                    help="after_claim|after_request_registered|"
                         "after_bundle_written|after_event_submitted|none"
                         "(none=只靠 --injection 硬杀)")
    ap.add_argument("--with-model", action="store_true",
                    help="计划带 scripted 模型(B2 注入需要请求登记)")
    ap.add_argument("--coproducts", default=None,
                    help="逗号分隔的共同产物 SMILES 列表")
    ap.add_argument("--transitions", action="store_true",
                    help="计划带显式场景转换(after B)")
    ap.add_argument("--injection", default=None,
                    help="队列级故障注入(after_two_followputs 类型)")
    ap.add_argument("--no-plan", action="store_true",
                    help="resume 不传计划(沿冻结输入,S3B-01)")
    ap.add_argument("--barrier-dir", default=None)
    ap.add_argument("--worker", default="w1")
    ap.add_argument("--tool-receipt-dir", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    from pathway_v43.config import resolve_config
    from pathway_v43.pollutant.runflow import (
        PPV1RunError,
        resume_ppv1_run,
        start_ppv1_run,
    )
    from pathway_v43.pollutant.search import SearchCrashInjection

    coproducts = None
    if args.coproducts:
        coproducts = [c for c in args.coproducts.split(",") if c]
    transitions = None
    if args.transitions:
        transitions = [{
            "after_hypothesis_key": "B",
            "transition": {"source_ref": "user:switch-anaerobic",
                            "new_phase_id": "phase-1",
                            "new_scenario_ref": "scenario-anaerobic"}}]
    run_plan = plan(args.with_model, coproducts=coproducts,
                    transitions=transitions)

    if args.mode == "start-crash":
        install_injection(args.injection)
        try:
            start_ppv1_run(
                config=resolve_config(), runs_root=args.runs_root,
                run_id=args.run_id, smiles="CCO",
                plan=run_plan, scripted=True,
                crash_after=(None if args.crash_after == "none"
                             else args.crash_after))
            print(json.dumps({"crashed": False}))
        except SearchCrashInjection as exc:
            print(json.dumps({"crashed": True,
                              "kind": "SearchCrashInjection",
                              "detail": exc.detail}, ensure_ascii=False))
        hard_exit(1)  # 崩溃点之后硬杀(不做清理)

    if args.mode == "resume":
        try:
            out = resume_ppv1_run(
                config=resolve_config(), runs_root=args.runs_root,
                run_id=args.run_id,
                plan=(None if args.no_plan else run_plan))
            result = {"stop_reason": out["stop_reason"],
                      "events": out["counts"]["events"],
                      "resumed": out["resumed"]}
            code = 0
        except Exception as exc:  # noqa: BLE001 — 拒绝也是结果
            result = _result(exc, resumed=False)
            code = 3
        if args.out_json:
            Path(args.out_json).write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return code

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
            result = _result(exc, worker=args.worker, started=False)
            code = 3
        if args.out_json:
            Path(args.out_json).write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return code

    if args.mode == "concurrent-resume":
        # S3B-04:两个独立公开 resume 进程争同一 run 的执行权。
        # - first:barrier GO 后 resume(取得 flock)→ 进入真实工具时
        #   写收据并等 second 的尝试标记(证明两进程实际重叠);
        # - second:等 first 的工具收据(此时 first 持锁在执行)后
        #   resume ⇒ 应在执行前被拒(driver_session_active);
        # 工具入口计数 = patched execute_atomtool_expansion 包装
        # (调用真实冻结工具,只加计数;不改产物)。
        import pathway_v43.pollutant.production as production
        bdir = Path(args.barrier_dir)
        bdir.mkdir(parents=True, exist_ok=True)
        receipts = Path(args.tool_receipt_dir)
        receipts.mkdir(parents=True, exist_ok=True)
        orig_tool = production.execute_atomtool_expansion
        receipt_path = receipts / f"{args.worker}.tool_entered.json"
        entries = [0]

        def counting_tool(*a, **kw):
            entries[0] += 1
            receipt_path.write_text(json.dumps({
                "worker": args.worker, "pid": os.getpid(),
                "entries": entries[0],
                "substrate_smiles": kw.get("substrate_smiles")}),
                encoding="utf-8")
            if args.worker == "first":
                # 等待 second 的尝试标记(有界;证明并发重叠)
                deadline = time.monotonic() + 60.0
                marker = bdir / "second_attempted"
                while not marker.exists():
                    if time.monotonic() > deadline:
                        break
                    time.sleep(0.02)
            return orig_tool(*a, **kw)

        production.execute_atomtool_expansion = counting_tool
        if args.worker == "second":
            # second 先等 first 进入工具(锁被持有、执行中)再尝试
            deadline = time.monotonic() + 60.0
            first_receipt = receipts / "first.tool_entered.json"
            while not first_receipt.exists():
                if time.monotonic() > deadline:
                    break
                time.sleep(0.02)
        else:
            go = bdir / "GO"
            deadline = time.monotonic() + 60.0
            while not go.exists():
                if time.monotonic() > deadline:
                    print(json.dumps({"error": "barrier_timeout"}))
                    return 9
                time.sleep(0.02)
        try:
            out = resume_ppv1_run(
                config=resolve_config(), runs_root=args.runs_root,
                run_id=args.run_id, plan=None)
            result = {"worker": args.worker, "resumed": True,
                      "stop_reason": out["stop_reason"],
                      "events": out["counts"]["events"],
                      "tool_entries": entries[0]}
            code = 0
        except Exception as exc:  # noqa: BLE001 — 竞争拒绝也是结果
            result = _result(exc, worker=args.worker, resumed=False,
                             tool_entries=entries[0])
            code = 3
        if args.worker == "second":
            (bdir / "second_attempted").write_text(
                json.dumps({"worker": "second", "pid": os.getpid()}),
                encoding="utf-8")
        if args.out_json:
            Path(args.out_json).write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return code
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
