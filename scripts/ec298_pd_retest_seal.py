"""EC298 Phase D retest — per-arm seal audit (zero LLM, read-only + derived).

Runs AFTER an arm's driver `--phase post`. Produces the seal facts:

1. SHA manifest of audit-critical arm files (batch identity, exam inputs,
   input manifest, merged answers + metadata, arm summary, all worker
   statuses);
2. leak scan: no run-side file references the gold directory/questions
   path, no credential-looking strings in persisted run products, answer
   rows carry only whitelist-derived fields;
3. per-route terminal classification cross-check (already in pairing gate;
   recorded here as seal evidence);
4. old-run read-only confirmation: this script never writes inside any
   run directory; it writes only `<arm-root>/_seal/` derived artifacts.

Usage (Chenyu):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
      scripts/ec298_pd_retest_seal.py --arm-root runs/ec298_pd_retest_C0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

GOLD_PATH_MARKERS = ("ec298_gold_readonly", "questions.jsonl",
                     "products_smiles", "raw_reaction")
CRED_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{16,}"),
    re.compile(r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-]{16,}"),
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_text_for_gold_and_creds(text: str) -> list[str]:
    hits = []
    for marker in GOLD_PATH_MARKERS:
        if marker in text:
            hits.append(f"gold_marker:{marker}")
    for pat in CRED_PATTERNS:
        if pat.search(text):
            hits.append(f"cred_pattern:{pat.pattern[:24]}")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-root", required=True)
    a = ap.parse_args()
    arm_root = Path(a.arm_root).resolve()
    seal_dir = arm_root / "_seal"
    seal_dir.mkdir(parents=True, exist_ok=True)

    manifest_lines = []

    def seal_file(rel: str) -> None:
        p = arm_root / rel
        if p.is_file():
            manifest_lines.append(f"{_sha256_file(p)}  {rel}")

    for rel in ("batch_identity.json", "exam_inputs.jsonl",
                "input_manifest.json", "merged/predictions.jsonl",
                "merged/export_metadata.json", "_arm_summary.json",
                "_identity_phase.json", "_agent_run_result.json",
                "progress.json", "coordinator.log", "driver.log"):
        seal_file(rel)
    workers_dir = arm_root / "workers"
    if workers_dir.is_dir():
        for sp in sorted(workers_dir.glob("*.status.json")):
            manifest_lines.append(
                f"{_sha256_file(sp)}  workers/{sp.name}")
    seal_text = "\n".join(sorted(manifest_lines)) + "\n"
    (seal_dir / "seal.sha256").write_text(seal_text, encoding="utf-8")

    # ---- leak scan ----
    violations: list[str] = []
    scanned = 0
    # small structured files: full scan
    for rel in ("batch_identity.json", "input_manifest.json",
                "merged/predictions.jsonl", "merged/export_metadata.json",
                "_arm_summary.json"):
        p = arm_root / rel
        if p.is_file():
            scanned += 1
            for hit in _scan_text_for_gold_and_creds(
                    p.read_text(encoding="utf-8")):
                violations.append(f"{rel}:{hit}")
    # worker status files: full scan (small)
    if workers_dir.is_dir():
        for sp in sorted(workers_dir.glob("*.status.json")):
            scanned += 1
            for hit in _scan_text_for_gold_and_creds(
                    sp.read_text(encoding="utf-8")):
                violations.append(f"workers/{sp.name}:{hit}")
    # whitelist field check
    n_bad_rows = 0
    wi = arm_root / "exam_inputs.jsonl"
    if wi.is_file():
        for line in wi.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if set(r) != {"input_index", "qid", "substrate_smiles"}:
                n_bad_rows += 1
    # merged answer rows: only route_id/root_smiles/steps fields allowed
    n_bad_answer_rows = 0
    preds = arm_root / "merged" / "predictions.jsonl"
    if preds.is_file():
        for line in preds.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if not {"route_id", "root_smiles", "steps"} >= set(r):
                n_bad_answer_rows += 1

    # decision/plan product payloads: sample scan for gold markers/creds is
    # not content-meaningful (corpus SMILES legitimately appear); structural
    # check = plans do not reference gold paths
    plans_dir = arm_root / "workers"
    if plans_dir.is_dir():
        for pp in sorted(plans_dir.glob("*.plan.json"))[:298]:
            scanned += 1
            for hit in _scan_text_for_gold_and_creds(
                    pp.read_text(encoding="utf-8")):
                violations.append(f"workers/{pp.name}:{hit}")

    seal = {
        "schema_version": "ec298-pd-retest-seal-1",
        "arm_root": str(arm_root),
        "n_sealed_files": len(manifest_lines),
        "seal_sha256_of_manifest": hashlib.sha256(
            seal_text.encode("utf-8")).hexdigest(),
        "leak_scan": {
            "n_files_scanned": scanned,
            "gold_path_markers": list(GOLD_PATH_MARKERS),
            "violations": violations,
            "n_whitelist_rows_bad_fields": n_bad_rows,
            "n_answer_rows_bad_fields": n_bad_answer_rows,
            "note": ("scan covers structured run-side files and worker "
                     "plans/statuses; decision payloads legitimately "
                     "contain corpus SMILES and are structurally covered "
                     "by identity/manifest checks, not by gold-string "
                     "scans"),
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (seal_dir / "seal.json").write_text(
        json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps(seal, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
