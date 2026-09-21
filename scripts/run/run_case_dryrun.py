#!/usr/bin/env python3
# scripts/run/run_case_dryrun.py
# ============================================================
# 本地 dry-run 端到端执行器
# ============================================================
# 用途：接 case JSON → 调 main.run(query, mode) → 落盘结果 → 核验 expected 断言
#
# 溯源：
#   - 本地 .env 应有 ENZYMECAGE_DRY_RUN=1（md5-based mock，不真调 wrapper）
#   - case JSON 位于 cases/case_*.json
#   - 输出落盘到 reports/dryrun/<case_id>_<timestamp>/
#     - result.json     : main.run 返回的完整 dict
#     - evidence.json   : 独立提取的 evidence_chain
#     - verdict.json    : expected 断言逐项核验结果
#     - console.log     : stdout/stderr 捕获
# ============================================================

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- 确保项目根在 sys.path ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- 加载 .env（config/settings.py 内部会做，这里保险再来一次） ---
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    # 手工 fallback
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().split("#", 1)[0].strip()
            os.environ.setdefault(k, v)


# --- 常量 ---
CASES_DIR = PROJECT_ROOT / "cases"
REPORTS_DIR = PROJECT_ROOT / "reports" / "dryrun"


# ═══════════════════════════════════════════════════════════════
# 断言核验
# ═══════════════════════════════════════════════════════════════

def verify_expected(case: dict, result: dict) -> dict:
    """
    根据 case.expected 逐项核验 result。
    返回：{"passed": bool, "checks": [{"name","expected","actual","ok"}]}
    """
    expected = case.get("expected", {})
    checks: list[dict] = []

    ec = result.get("evidence_chain") or []
    stages = [e.get("stage") for e in ec if isinstance(e, dict)]

    # 1. fail_closed 语义
    should_fail = expected.get("should_fail_closed", False)
    actually_failed = (result.get("status") == "failed")
    checks.append({
        "name": "fail_closed_semantics",
        "expected": should_fail,
        "actual": actually_failed,
        "ok": (should_fail == actually_failed),
    })

    if should_fail:
        # fail 路径：只需核验 fail_at_stage 与 evidence_chain 长度
        allow = set(expected.get("fail_at_stage_in", []))
        if allow:
            # 优先用 evidence_chain 末段；若为空（node 报错前未写 evidence）
            # 则从 error 消息里推断（学生节点实现都以 'XxxNode: ...' 开头）
            last_stage = stages[-1] if stages else None
            err = (result.get("error") or "").lower()
            if last_stage is None and err:
                for s in allow:
                    if f"{s}node" in err.replace("_", ""):
                        last_stage = s
                        break
            checks.append({
                "name": "fail_at_expected_stage",
                "expected": f"stage in {sorted(allow)}",
                "actual": last_stage,
                "ok": (last_stage in allow) if last_stage else False,
            })
        min_len = expected.get("evidence_chain_min_len", 0)
        # 允许 min_len=0：fail-closed 在首个 node 内部异常时允许 evidence 为空
        checks.append({
            "name": "evidence_chain_min_len",
            "expected": f">= {min_len}",
            "actual": len(ec),
            "ok": len(ec) >= min_len,
        })
    else:
        # success 路径：substrate / reaction / pool / ranking 逐段
        # substrate
        exp_sub = expected.get("substrate", {})
        sub_smiles = result.get("substrate_smiles")
        if "smiles" in exp_sub:
            checks.append({
                "name": "substrate_smiles",
                "expected": exp_sub["smiles"],
                "actual": sub_smiles,
                "ok": sub_smiles == exp_sub["smiles"],
            })

        # pool route
        exp_pool = expected.get("pool", {})
        route = result.get("pool_route")
        if "route_used" in exp_pool:
            checks.append({
                "name": "pool_route_used",
                "expected": exp_pool["route_used"],
                "actual": route,
                "ok": route == exp_pool["route_used"],
            })
        if "min_pool_size" in exp_pool:
            ps = result.get("pool_size") or 0
            checks.append({
                "name": "pool_size_min",
                "expected": f">= {exp_pool['min_pool_size']}",
                "actual": ps,
                "ok": ps >= exp_pool["min_pool_size"],
            })

        # ranking
        exp_rk = expected.get("ranking", {})
        n_ranked = len(result.get("ranked_enzymes") or [])
        if "min_num_ranked" in exp_rk:
            checks.append({
                "name": "num_ranked_min",
                "expected": f">= {exp_rk['min_num_ranked']}",
                "actual": n_ranked,
                "ok": n_ranked >= exp_rk["min_num_ranked"],
            })

        # evidence_chain 完整性
        exp_stages = expected.get("evidence_chain_stages", [])
        for s in exp_stages:
            checks.append({
                "name": f"evidence_stage:{s}",
                "expected": "present",
                "actual": s in stages,
                "ok": s in stages,
            })

    passed = all(c["ok"] for c in checks)
    return {"passed": passed, "checks": checks, "num_checks": len(checks)}


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def run_case(case_path: Path) -> dict:
    """跑单个 case，返回 verdict + 报告目录路径。"""
    with case_path.open("r", encoding="utf-8") as f:
        case = json.load(f)

    case_id = case.get("case_id") or case_path.stem
    query = case["query"]
    mode = case.get("mode", "m3")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = REPORTS_DIR / f"{case_id}_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"[CASE] {case_id} :: {case.get('case_name', '')}")
    print(f"[CASE] query: {query}")
    print(f"[CASE] mode:  {mode}")
    print(f"[CASE] DRY_RUN env: {os.environ.get('ENZYMECAGE_DRY_RUN', '(unset)')}")
    print(f"[CASE] outdir: {outdir}")
    print(f"{'='*70}")

    # --- 捕获 stdout/stderr ---
    buf_out = io.StringIO()
    buf_err = io.StringIO()

    result: dict | None = None
    exc_info: str | None = None
    try:
        # 惰性 import main（避免脚本启动即触发 config 加载）
        from main import run as pipeline_run
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            # 顺带把根 logger 打到 buf_err
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                stream=buf_err,
                force=True,
            )
            result = pipeline_run(query=query, mode=mode)
    except Exception as e:
        exc_info = traceback.format_exc()
        result = {
            "status": "failed",
            "error": f"unhandled_exception: {type(e).__name__}: {e}",
            "evidence_chain": [],
        }

    # --- 落盘 ---
    (outdir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (outdir / "evidence.json").write_text(
        json.dumps(result.get("evidence_chain", []), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    console_log = buf_out.getvalue() + "\n---STDERR---\n" + buf_err.getvalue()
    if exc_info:
        console_log += "\n---UNHANDLED EXCEPTION---\n" + exc_info
    (outdir / "console.log").write_text(console_log, encoding="utf-8")

    # --- 核验 ---
    verdict = verify_expected(case, result)
    verdict_full = {
        "case_id": case_id,
        "case_name": case.get("case_name"),
        "timestamp": ts,
        "outdir": str(outdir.relative_to(PROJECT_ROOT)),
        "passed": verdict["passed"],
        "num_checks": verdict["num_checks"],
        "checks": verdict["checks"],
        "result_status": result.get("status"),
        "result_error": result.get("error"),
    }
    (outdir / "verdict.json").write_text(
        json.dumps(verdict_full, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- 打印摘要 ---
    print(f"\n[RESULT] status={result.get('status')}")
    if result.get("error"):
        print(f"[RESULT] error={result.get('error')}")
    print(f"[RESULT] evidence_chain_len={len(result.get('evidence_chain') or [])}")
    print(f"[RESULT] ranked_enzymes_len={len(result.get('ranked_enzymes') or [])}")
    print(f"\n[VERDICT] {'PASS' if verdict['passed'] else 'FAIL'}  ({sum(c['ok'] for c in verdict['checks'])}/{verdict['num_checks']} checks passed)")
    for c in verdict["checks"]:
        mark = "✓" if c["ok"] else "✗"
        print(f"  {mark} {c['name']}: expected={c['expected']!r} actual={c['actual']!r}")
    print(f"\n[SAVED] {outdir}")

    return verdict_full


def main():
    ap = argparse.ArgumentParser(description="EnzymeCrew local dry-run runner")
    ap.add_argument("--case", type=str, help="case id (e.g. case_2)，或不填则跑 cases/ 目录下所有 case_*.json")
    ap.add_argument("--case-file", type=str, help="直接指定 case JSON 文件路径")
    args = ap.parse_args()

    if args.case_file:
        targets = [Path(args.case_file)]
    elif args.case:
        p = CASES_DIR / f"{args.case}.json"
        if not p.exists():
            print(f"[ERR] case file not found: {p}", file=sys.stderr)
            sys.exit(2)
        targets = [p]
    else:
        targets = sorted(CASES_DIR.glob("case_*.json"))
        if not targets:
            print(f"[ERR] no cases found under {CASES_DIR}", file=sys.stderr)
            sys.exit(2)

    verdicts = [run_case(t) for t in targets]

    # 汇总
    print(f"\n{'='*70}")
    print(f"[SUMMARY] {sum(v['passed'] for v in verdicts)}/{len(verdicts)} cases PASSED")
    print(f"{'='*70}")
    for v in verdicts:
        mark = "PASS" if v["passed"] else "FAIL"
        print(f"  [{mark}] {v['case_id']}  {v['case_name']}")

    sys.exit(0 if all(v["passed"] for v in verdicts) else 1)


if __name__ == "__main__":
    main()
