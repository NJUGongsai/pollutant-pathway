#!/usr/bin/env python
"""S3a 崩溃/并发 worker —— 在独立进程里执行搜索底座的认领/请求/捆绑/
提交各段后**硬杀进程**(os._exit),模拟真实进程崩溃(不能以同进程
内存异常冒充);也提供 barrier 双进程争抢同一 action 的 H06 驱动。

由 tests/test_ppv1_s3a_recover.py 以子进程调用;全部输入为合成规则级
夹具(CCO → CC=O),无金标/题面/封存材料。用法:
    python tests/s3a_worker.py claim-exit --db DB --run-id R --action-id A
        --worker W [--parent P --origin-key K --context C --task-key T]
    python tests/s3a_worker.py request-exit ... --request-key KEY
        [--provider-kind scripted]
    python tests/s3a_worker.py bundle-exit ... (--task-key 必填)
    python tests/s3a_worker.py submit-exit ...
    python tests/s3a_worker.py full-commit ... (--task-key 可选 bundle)
    python tests/s3a_worker.py barrier-claim ... --barrier-dir D
        --n-workers 2 --out-json PATH
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.events import (  # noqa: E402
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    build_profile_identity_block,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    SearchLedger,
    commit_search_event,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402


def make_fixture(run_id: str, parent: str, origin_key: str,
                 context: str):
    """合成事件夹具(CCO → CC=O;与测试同参数 ⇒ 同 hypothesis/event ID)。"""
    sub = build_chemical_state("CCO", "raw_input", [{"record": "sub-A"}])
    prod = build_chemical_state("CC=O", "source_product",
                                [{"record": "prod-A"}])
    hyp = build_hypothesis(
        parent_path_id=parent, substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant",
                        role="primary_substrate", coefficient=None,
                        coefficient_status="unknown"),
            Participant(state_ref=prod.state_id, side="product",
                        role="principal_product", coefficient=None,
                        coefficient_status="unknown")],
        participant_list_status="partial", step_scope="net_reaction",
        origin_group_key=origin_key)
    event = build_pathway_event(hyp, run_id=run_id, context_hash=context)
    args = {
        "report_projection": build_report_projection(
            hyp, max_reportable=1,
            ranked_state_refs=[prod.state_id]).to_dict(),
        "expansion_plan": build_expansion_plan(
            hyp, expanded=[prod.state_id], deferred=[],
            not_tracked=[]).to_dict(),
        "states": [sub.to_dict(), prod.to_dict()],
        "hypothesis_dict": hyp.to_dict(),
    }
    return sub, prod, hyp, event, args


def open_ledger(db: str, runs_root: str, run_id: str) -> SearchLedger:
    store = PollutantPathwayStore(db)
    art = ArtifactStore(runs_root, run_id)
    return SearchLedger(store, art, run_id)


def hard_exit(code: int = 1) -> None:
    """模拟进程崩溃:不做任何清理(连接不 close、事务不收尾)。"""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=[
        "claim-exit", "request-exit", "bundle-exit", "submit-exit",
        "full-commit", "barrier-claim"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--action-id", required=True)
    ap.add_argument("--worker", required=True)
    ap.add_argument("--parent", default="p1")
    ap.add_argument("--origin-key", default="k1")
    ap.add_argument("--context", default="ctx1")
    ap.add_argument("--task-key", default="")
    ap.add_argument("--request-key", default="req-1")
    ap.add_argument("--provider-kind", default="scripted")
    ap.add_argument("--barrier-dir", default=None)
    ap.add_argument("--n-workers", type=int, default=2)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    ledger = open_ledger(args.db, args.runs_root, args.run_id)

    def run_claim() -> dict:
        return ledger.claim_action(args.action_id, worker_id=args.worker)

    if args.mode == "claim-exit":
        receipt = run_claim()
        print(json.dumps({"claimed": receipt.get("claimed", True),
                          "attempt_id": (receipt.get("attempt_refs")
                                         or [""])[0],
                          "task_key": receipt.get("task_key")},
                         ensure_ascii=False))
        hard_exit(1)  # 认领/预约已提交落账,进程硬杀(B1)

    if args.mode == "request-exit":
        receipt = run_claim()
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        request = ledger.register_model_request(
            run_id=args.run_id, action_id=args.action_id,
            attempt_id=attempt_id, provider_kind=args.provider_kind,
            request_key=args.request_key, purpose="rank")
        print(json.dumps({"receipt_claimed": receipt.get("claimed", True),
                          "attempt_id": attempt_id,
                          "request": request}, ensure_ascii=False))
        hard_exit(1)  # 请求已登记、无响应,进程硬杀(B2)

    if args.mode == "bundle-exit":
        receipt = run_claim()
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        _, _, _, event, ev_args = make_fixture(
            args.run_id, args.parent, args.origin_key, args.context)
        ledger.write_commit_bundle(
            action_id=args.action_id, attempt_id=attempt_id,
            event=event, task_key=args.task_key, **ev_args)
        print(json.dumps({"receipt_claimed": True,
                          "attempt_id": attempt_id}, ensure_ascii=False))
        hard_exit(1)  # artifact 已写、事件未提交,进程硬杀(B3)

    if args.mode == "submit-exit":
        receipt = run_claim()
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        _, _, _, event, ev_args = make_fixture(
            args.run_id, args.parent, args.origin_key, args.context)
        out = ledger.submit_action_event(
            args.action_id, event, worker_id=args.worker, **ev_args)
        print(json.dumps({"receipt_claimed": True,
                          "attempt_id": attempt_id,
                          "submitted": out}, ensure_ascii=False))
        hard_exit(1)  # 事件已提交、搜索记账未闭合,进程硬杀(B4)

    if args.mode == "full-commit":
        receipt = run_claim()
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        _, _, _, event, ev_args = make_fixture(
            args.run_id, args.parent, args.origin_key, args.context)
        out = commit_search_event(
            ledger, args.action_id, event, worker_id=args.worker,
            attempt_id=attempt_id, task_key=args.task_key,
            write_bundle=bool(args.task_key), **ev_args)
        ledger.store.close()
        print(json.dumps({"receipt_claimed": True, "outcome": out},
                         ensure_ascii=False))
        return 0

    if args.mode == "barrier-claim":
        # H06:双进程 barrier 同时争同一 action(不靠顺序调用/sleep)
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
        # 全部就绪后才争抢(GO 由父进程在观察到 n ready 后落盘)
        try:
            receipt = run_claim()
            result = {"worker": args.worker, "claimed": True,
                      "claimed_by": receipt.get("claimed_by"),
                      "attempt_id": (receipt.get("attempt_refs")
                                     or [""])[0]}
            code = 0
        except Exception as exc:  # noqa: BLE001 — 竞争失败也是结果
            result = {"worker": args.worker, "claimed": False,
                      "error": type(exc).__name__,
                      "kind": getattr(exc, "detail", {}).get("kind")}
            code = 3
        if args.out_json:
            Path(args.out_json).write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8")
        ledger.store.close()
        print(json.dumps(result, ensure_ascii=False))
        return code

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
