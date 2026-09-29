"""EC298 Phase D retest arm driver (C0 / D-3).

Runs on Chenyu inside the dependingv43 workspace. Lives OUTSIDE src/ (no
code-identity impact). Three phases:

  --phase identity  : build exam manifest + batch identity, write them, exit.
                      No workers, no API calls (resolve_model_setup only reads
                      env; no network).
  --phase run       : verify batch identity matches the recorded one, then run
                      the BatchCoordinator to completion (idempotent resume:
                      finished routes are skipped, interrupted runs resume by
                      task_id, already persisted responses are never re-sent).
  --phase post      : merge + terminal classification + api account + inflight
                      evidence + pairing-gate validation; write _arm_summary.

Usage:
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python <this> \
      --arm-root runs/ec298_pd_retest_C0 \
      --config <arm config json> \
      --exam-inputs <frozen whitelist jsonl> \
      --env-file /usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env \
      --phase identity|run|post
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

FROZEN_EXAM_INPUTS_SHA256 = (
    "cb5996c9b960bb4a61fd5747d275077c65ef49bf2cdb74102b9d22dc7f11d703")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _emit(obj: dict, out: str | None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    if out and out != "-":
        Path(out).write_text(text + "\n", encoding="utf-8")
    print(text)


def phase_identity(args) -> int:
    from pathway_v43.batch import batch_identity_conflict_check, load_env_file
    from pathway_v43.adapters.llm_client import (
        real_provider_env, resolve_model_setup,
    )
    from pathway_v43.output.export_v3 import load_export_policy

    arm_root = Path(args.arm_root).resolve()
    arm_root.mkdir(parents=True, exist_ok=True)
    # frozen whitelist copy with fail-closed SHA check
    exam_inputs = arm_root / "exam_inputs.jsonl"
    if not exam_inputs.is_file():
        src = Path(args.exam_inputs).resolve()
        exam_inputs.write_bytes(src.read_bytes())
    actual = _sha256_file(exam_inputs)
    if actual != FROZEN_EXAM_INPUTS_SHA256:
        print(json.dumps({
            "ok": False, "phase": "identity",
            "error": "exam_inputs SHA mismatch (fail-closed)",
            "expected": FROZEN_EXAM_INPUTS_SHA256, "actual": actual,
        }, ensure_ascii=False))
        return 2

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.env_file:
        import os
        os.environ.update(load_env_file(args.env_file))
    env = real_provider_env()
    missing = [k for k, ok in (
        ("V43_LLM_BASE_URL", env["base_url_set"]),
        ("V43_LLM_API_KEY", env["api_key_set"]),
        ("V43_LLM_MODEL", env["model_set"]),
    ) if not ok]
    if missing:
        print(json.dumps({"ok": False, "phase": "identity",
                          "error": "missing env", "missing": missing},
                         ensure_ascii=False))
        return 2
    setup = resolve_model_setup(
        "openai_compatible",
        request_params=config["model_request_params"],
        timeout_s=config["llm_timeout_s"])
    required = config.get("provider_price_snapshot", {}).get("model_id")
    if required and setup.model_id != required:
        print(json.dumps({"ok": False, "phase": "identity",
                          "error": "model_id mismatch",
                          "required": required, "actual": setup.model_id},
                         ensure_ascii=False))
        return 2

    # Build the same manifest + identity as run_exam_agent would, but stop
    # before any worker is spawned.
    from pathway_v43.exam import EXAM_SPLIT_NAME, _exam_manifest, load_exam_inputs
    from pathway_v43.batch import build_batch_identity
    rows = load_exam_inputs(exam_inputs)
    manifest = _exam_manifest(rows, actual)
    manifest_path = arm_root / "input_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    export_policy = load_export_policy(
        config.get("export_policy_overrides") or {})
    model_block = {"provider": "openai_compatible",
                   "model_id": setup.model_id,
                   "request_params": dict(setup.request_params),
                   "timeout_s": float(setup.timeout_s)}
    identity = build_batch_identity(
        split=EXAM_SPLIT_NAME, input_manifest_path=manifest_path,
        config=config, provider=model_block["provider"],
        model_id=model_block["model_id"],
        request_params=model_block["request_params"],
        timeout_s=model_block["timeout_s"],
        export_policy=export_policy)
    batch_identity_conflict_check(arm_root, identity)
    (arm_root / "batch_identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    _emit({
        "ok": True, "phase": "identity", "arm_root": str(arm_root),
        "batch_sha256": identity["sha256"], "batch_short": identity["short"],
        "n_questions": len(rows),
        "exam_inputs_sha256": actual,
    }, str(arm_root / "_identity_phase.json"))
    return 0


def phase_run(args) -> int:
    from pathway_v43.exam import run_exam_agent

    arm_root = Path(args.arm_root).resolve()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    summary = run_exam_agent(
        batch_root=arm_root,
        exam_inputs_path=arm_root / "exam_inputs.jsonl",
        runs_root=arm_root / "runs",
        config=config, model_choice="real",
        env_file=args.env_file,
        workers=40, max_in_flight=40)
    _emit(summary, str(arm_root / "_agent_run_result.json"))
    return 0 if summary.get("status") not in (
        "not_run:no_credentials_or_access", "not_run:model_id_mismatch") else 2


def phase_post(args) -> int:
    from pathlib import Path as _P
    from pathway_v43.batch import (
        api_account, batch_terminal_summary, load_input_manifest,
        merge_predictions_terminal, run_id_for_route,
    )
    from pathway_v43.exam import inflight_evidence
    from pathway_v43.output.export_v3 import load_export_policy
    from pathway_v43.output.pairing_gate import validate_arm

    arm_root = Path(args.arm_root).resolve()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    manifest = load_input_manifest(arm_root / "input_manifest.json")
    identity = json.loads(
        (arm_root / "batch_identity.json").read_text(encoding="utf-8"))
    export_policy = load_export_policy(
        config.get("export_policy_overrides") or {})

    merged = merge_predictions_terminal(
        batch_root=arm_root, manifest=manifest, config=config,
        export_policy=export_policy)
    route_ids = list(manifest["route_order"])
    run_ids = [run_id_for_route(identity["short"], manifest["split"], rid)
               for rid in route_ids]
    runs_root = arm_root / "runs"
    terminal = {}
    for rid in route_ids:
        sp = arm_root / "workers" / f"{rid}.status.json"
        if sp.is_file():
            terminal[rid] = json.loads(sp.read_text(encoding="utf-8"))
    terminal_summary = batch_terminal_summary(route_ids, terminal)
    account = api_account(
        runs_root, run_ids,
        price_snapshot=config.get("provider_price_snapshot"))
    inflight = inflight_evidence(runs_root, run_ids)
    # R2 review P2 fix: persist the credential-free per-request spans so the
    # peak can be independently recomputed from in-repo materials (previously
    # only the peak was kept and the spans discarded).
    (arm_root / "_inflight_requests.json").write_text(
        json.dumps({"schema_version": "ec298-pd-retest-inflight-1",
                    "caliber": inflight["note"],
                    "requests": inflight["requests"]},
                   ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    gate = validate_arm(arm_root, expected_route_ids=route_ids)
    result = {
        "schema_version": "ec298-pd-retest-arm-summary-1",
        "arm_root": str(arm_root),
        "batch_sha256": identity["sha256"],
        "batch_short": identity["short"],
        "n_routes": len(route_ids),
        "terminal_summary": terminal_summary,
        "merged": {k: v for k, v in merged.items() if k != "per_route"},
        "api_account_totals": account["totals"],
        "cost_estimate_cny": account.get("cost_estimate_cny"),
        "cost_estimate_known_usage_cny": account.get(
            "cost_estimate_known_usage_cny"),
        "conservative_reservation": account.get("conservative_reservation"),
        "inflight": {k: v for k, v in inflight.items() if k != "requests"},
        "pairing_gate": gate,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out = arm_root / "_arm_summary.json"
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True, "phase": "post", "arm_root": str(arm_root),
        "batch_terminal_status": terminal_summary["status"],
        "n_valid_terminal": terminal_summary["n_valid_terminal"],
        "n_failed": terminal_summary["n_failed"],
        "n_export_failed": terminal_summary["n_export_failed"],
        "n_missing": terminal_summary["n_missing"],
        "pairing_gate_ok": gate["ok"],
        "peak_in_flight_provider_ok": inflight[
            "peak_in_flight_provider_ok"],
        "summary_path": str(out),
    }, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-root", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--exam-inputs", required=True)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--phase", required=True,
                    choices=["identity", "run", "post"])
    args = ap.parse_args()
    if args.phase == "identity":
        return phase_identity(args)
    if args.phase == "run":
        return phase_run(args)
    return phase_post(args)


if __name__ == "__main__":
    raise SystemExit(main())
