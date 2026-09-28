"""EC298 Phase D retest pre-flight connectivity/billing smoke (paid, separate ledger).

Runs BEFORE the two 298-question arms, on a NON-298 synthetic substrate
(v3 benchmark dev route pb_0117 root_smiles), through the REAL worker path
(`pathway_v43.batch.worker_main`), once with C0 semantics
(reactant_similar_enabled=false) and once with D-3 semantics (true).

Cost/usage of these calls is recorded in the smoke root ONLY and is NOT
counted into either arm batch ledger. Smoke results are not used to tune any
arm configuration; a failure here stops the launch (per registry §7).

Usage (Chenyu):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python <this> \
      --smoke-root runs/ec298_pd_retest_smoke \
      --env-file /usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

SMOKE_SUBSTRATE_DEFAULT = "C\\C=C\\C=C(\\O)C([O-])=O"   # pb_0117 dev root_smiles (non-298)
SMOKE_SUBSTRATE_PB0002 = "C#CC(C)(C)NC(=O)C1=CC(=CC(=C1)Cl)Cl"  # pb_0002 dev root_smiles (non-298; needs model)
TIMEOUT_S = 3600.0
REQUEST_PARAMS = {"reasoning_effort": "max"}
BUDGETS = {"max_depth": 1, "max_expansions": 1, "max_frontier_width": 5,
           "max_llm_calls": 3, "max_proposals": 1}
POLICY_C0 = {"reactant_similar_enabled": False,
             "reactant_similar_threshold": 0.45,
             "reactant_similar_top_k": 16,
             "max_analogy_donor_candidates": 3}
POLICY_D3 = {"reactant_similar_enabled": True,
             "reactant_similar_threshold": 0.45,
             "reactant_similar_top_k": 16,
             "max_analogy_donor_candidates": 3}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-root", required=True)
    ap.add_argument("--env-file", required=True)
    ap.add_argument("--substrate", default="pb0117",
                    choices=["pb0117", "pb0002"],
                    help="pb0117 = recorded bypass (pipeline only); "
                         "pb0002 = needs the model (connectivity/billing)")
    ap.add_argument("--tag", default="",
                    help="suffix tag for run ids/summary (e.g. r2)")
    args = ap.parse_args()
    substrate = (SMOKE_SUBSTRATE_PB0002 if args.substrate == "pb0002"
                 else SMOKE_SUBSTRATE_DEFAULT)
    tag = ("_" + args.tag) if args.tag else ""
    from pathway_v43.batch import load_env_file, worker_main, api_account
    from pathway_v43.output.export_v3 import load_export_policy
    from pathway_v43.adapters.llm_client import real_provider_env

    import os
    os.environ.update(load_env_file(args.env_file))
    env = real_provider_env()
    missing = [k for k, ok in (
        ("V43_LLM_BASE_URL", env["base_url_set"]),
        ("V43_LLM_API_KEY", env["api_key_set"]),
        ("V43_LLM_MODEL", env["model_set"]),
    ) if not ok]
    if missing:
        print(json.dumps({"ok": False, "error": "missing env",
                          "missing": missing}, ensure_ascii=False))
        return 2

    smoke_root = Path(args.smoke_root).resolve()
    runs_root = smoke_root / "runs"
    export_policy = load_export_policy({})
    results = {}
    base_labels = (("smoke_pd_retest_c0like", POLICY_C0),
                   ("smoke_pd_retest_d3like", POLICY_D3))
    for label, policy in ((l + tag, p) for l, p in base_labels):
        plan = {
            "route_id": label,
            "run_id": label,
            "root_smiles": substrate,
            "runs_root": str(runs_root),
            "quarantine_root": str(smoke_root / "quarantine"),
            "model": {
                "provider": "openai_compatible",
                "model_id": "ZHIPU/GLM-5.3-Flash",
                "request_params": dict(REQUEST_PARAMS),
                "timeout_s": TIMEOUT_S,
                "policy_overrides": dict(policy),
            },
            "budgets": dict(BUDGETS),
            "export_policy": export_policy,
            "status_path": str(smoke_root / f"{label}.status.json"),
        }
        plan_path = smoke_root / f"{label}.plan.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n", encoding="utf-8")
        t0 = time.time()
        rc = worker_main(["--plan", str(plan_path)])
        status = json.loads(
            (smoke_root / f"{label}.status.json").read_text(encoding="utf-8"))
        results[label] = {
            "worker_rc": rc,
            "stop_reason": status.get("stop_reason", ""),
            "failed": status.get("failed"),
            "export_ok": status.get("export_ok"),
            "predictions_sha256": status.get("predictions_sha256"),
            "elapsed_s": round(time.time() - t0, 1),
        }
        print(json.dumps({label: results[label]}, ensure_ascii=False))

    account = api_account(runs_root, list(results),
                          price_snapshot=None)
    smoke_account = api_account(
        runs_root, list(results),
        price_snapshot={
            "model_id": "ZHIPU/GLM-5.3-Flash",
            "region": "cn-beijing",
            "input_cny_per_m": 0.8,
            "output_cny_per_m": 2.8,
            "cache_read_cny_per_m": 0.23,
            "checked": "2026-09-29",
            "source": "help.aliyun.com/zh/model-studio/glm-5-3-flash-by-zhipu",
        })
    summary = {
        "schema_version": "ec298-pd-retest-smoke-1",
        "substrate": substrate,
        "substrate_choice": args.substrate,
        "note": ("non-298 synthetic fixture (dev benchmark root_smiles); "
                 "paid connectivity/billing smoke; separate ledger, not "
                 "counted into arm batches; results not used to tune arms"),
        "results": results,
        "api_totals": account["totals"],
        "cost_estimate_cny": smoke_account.get("cost_estimate_cny"),
        "cost_estimate_known_usage_cny": smoke_account.get(
            "cost_estimate_known_usage_cny"),
        "cost_basis": smoke_account.get("cost_basis"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out = smoke_root / f"_smoke_summary{tag}.json"
    out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    ok = all(r["failed"] is None and r["export_ok"] for r in results.values())
    print(json.dumps({"ok": ok, "summary_path": str(out)},
                     ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
