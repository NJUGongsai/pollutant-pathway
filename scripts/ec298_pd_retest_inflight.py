"""EC298 Phase D retest — per-request in-flight evidence table (zero LLM).

R2 review P2 fix: the arm post-processing kept only the peak and discarded
the per-request time spans, so the reported peak (33/32) could not be
independently recomputed from in-repo materials. This script re-derives the
credential-free per-request table read-only from the sealed response
artifacts and recomputes the peak with the SAME caliber as the batch
coordinator (`pathway_v43.exam.inflight_evidence`: half-open spans
[sent_at_epoch, done_at_epoch) over provider-ok responses; gate rejections
and failures do not count; at equal timestamps completions sort before
sends, so boundary-touching spans do not overlap).

v3 (combined-review F1) fix: per-request attempt numbers are read from EACH
response file's own payload. The previous version kept a single
(run_id, task_id) entry overwritten by the last file, mislabeling the
first of two attempts as attempt 2. Each row is additionally cross-checked
against its filename (`prediction_response.aN.json` implies attempt N),
and request_id uniqueness is asserted in the summary.

Outputs (no credentials, no raw model text):
  <out-dir>/<label>_inflight_events.tsv    one row per provider-ok response
  <out-dir>/<label>_inflight_summary.json  recomputed peak + cross-check
                                            against the arm summary's recorded
                                            peak

Usage (Chenyu, zero LLM, read-only over sealed runs):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
      scripts/ec298_pd_retest_inflight.py \
      --arm-root runs/ec298_pd_retest_C0 --label C0 \
      --out-dir /tmp/repro_inflight
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

_ATTEMPT_RE = re.compile(r"^prediction_response\.a(\d+)\.json$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-root", required=True)
    ap.add_argument("--label", required=True, choices=["C0", "D3"])
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    from pathway_v43.exam import inflight_evidence

    arm_root = Path(a.arm_root).resolve()
    out_dir = Path(a.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    identity = json.loads(
        (arm_root / "batch_identity.json").read_text(encoding="utf-8"))
    prefix = f"exam298_{identity['short']}_"
    run_ids = sorted(
        p.name for p in (arm_root / "runs").iterdir() if p.is_dir())
    inflight = inflight_evidence(arm_root / "runs", run_ids)

    # Per-FILE attempt ledger: (run_id, task_id, filename) -> attempt, read
    # from that file's own payload; cross-checked against the filename
    # (prediction_response.aN.json implies attempt N). Never collapse to
    # one entry per (run_id, task_id): a retried task keeps one row per
    # attempt, each with its own request_id and time span.
    attempt_by_file: dict[tuple[str, str, str], object] = {}
    filename_mismatches: list[dict] = []
    for run_id in run_ids:
        results = arm_root / "runs" / run_id / "results"
        if not results.is_dir():
            continue
        for task_dir in sorted(results.iterdir()):
            for rp in sorted(task_dir.glob("prediction_response.*.json")):
                try:
                    payload = json.loads(
                        rp.read_text(encoding="utf-8")).get("payload", {})
                except Exception:
                    continue
                attempt = payload.get("attempt")
                attempt_by_file[(run_id, task_dir.name, rp.name)] = attempt
                m = _ATTEMPT_RE.match(rp.name)
                if m is not None and attempt != int(m.group(1)):
                    filename_mismatches.append({
                        "run_id": run_id, "task_id": task_dir.name,
                        "file": rp.name, "payload_attempt": attempt,
                        "filename_attempt": int(m.group(1)),
                    })

    # Map each provider-ok span back to its source file via request_id, so
    # the row carries that file's own attempt (not a per-task overwrite).
    attempt_by_request: dict[str, object] = {}
    file_by_request: dict[str, str] = {}
    for (run_id, task_id, fname), attempt in attempt_by_file.items():
        rp = arm_root / "runs" / run_id / "results" / task_id / fname
        try:
            transport = json.loads(
                rp.read_text(encoding="utf-8")).get("payload", {}).get(
                    "transport", {}) or {}
        except Exception:
            continue
        if transport.get("ok") is not True or transport.get("status") != 200:
            continue
        rid = transport.get("request_id")
        if rid:
            attempt_by_request[rid] = attempt
            file_by_request[rid] = fname

    cols = ["qid", "run_id", "task_id", "attempt", "request_id",
            "sent_at_epoch", "done_at_epoch", "duration_s", "http_status",
            "total_tokens"]
    lines = ["\t".join(cols)]
    seen_requests: list[str] = []
    for s in inflight["requests"]:
        run_id, task_id = s["run_id"], s["task_id"]
        qid = run_id[len(prefix):] if run_id.startswith(prefix) else run_id
        usage = s.get("usage") or {}
        rid = s.get("request_id") or ""
        seen_requests.append(rid)
        lines.append("\t".join(str(x) for x in [
            qid, run_id, task_id,
            attempt_by_request.get(rid, ""),
            rid, s.get("sent_at"), s.get("done_at"),
            round(float(s["done_at"]) - float(s["sent_at"]), 3),
            s.get("status"), usage.get("total_tokens", ""),
        ]))
    tsv_path = out_dir / f"{a.label}_inflight_events.tsv"
    tsv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    recorded = None
    arm_summary_path = arm_root / "_arm_summary.json"
    if arm_summary_path.is_file():
        recorded = (json.loads(arm_summary_path.read_text(
            encoding="utf-8")).get("inflight") or {}).get(
                "peak_in_flight_provider_ok")

    dup_requests = sorted(
        {r for r in seen_requests if seen_requests.count(r) > 1})
    summary = {
        "schema_version": "ec298-pd-retest-inflight-2",
        "label": a.label,
        "arm_root": str(arm_root),
        "n_provider_ok_responses": inflight["n_provider_ok_responses"],
        "n_failed_or_rejected": inflight["n_failed_or_rejected"],
        "recomputed_peak_in_flight_provider_ok":
            inflight["peak_in_flight_provider_ok"],
        "recorded_peak_in_flight_provider_ok": recorded,
        "peaks_match": recorded == inflight["peak_in_flight_provider_ok"],
        "n_duplicate_request_ids": len(dup_requests),
        "duplicate_request_ids": dup_requests,
        "attempt_crosscheck": {
            "n_response_files": len(attempt_by_file),
            "n_filename_mismatches": len(filename_mismatches),
            "filename_mismatches": filename_mismatches,
        },
        "caliber": inflight["note"],
        "derived_from": "sealed results/T_*/prediction_response.*.json "
                        "transport (sent_at_epoch/done_at_epoch/request_id); "
                        "per-file payload.attempt cross-checked against "
                        "prediction_response.aN.json filename; "
                        "same function as batch coordinator: "
                        "pathway_v43.exam.inflight_evidence",
        "events_tsv": str(tsv_path),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (out_dir / f"{a.label}_inflight_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in (
        "label", "n_provider_ok_responses",
        "recomputed_peak_in_flight_provider_ok",
        "recorded_peak_in_flight_provider_ok", "peaks_match",
        "n_duplicate_request_ids",
        "attempt_crosscheck")},
        ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
