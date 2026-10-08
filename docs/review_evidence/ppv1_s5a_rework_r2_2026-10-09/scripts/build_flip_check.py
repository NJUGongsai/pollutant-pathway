#!/usr/bin/env python3
"""S5a rework r2 flip check: aggregate the B1 six-case contract assertions
(before/after) and the 17-case public-bucket diff (4 changed / 13 kept)
from the conditions_before / conditions_after evidence packages, plus the
r2 test counts. Writes flip_check.json at the evidence root.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

EV = Path(sys.argv[1]).resolve()
before_assert = json.loads(
    (EV / "conditions_before" / "results" / "B1_contract_assertions.json")
    .read_text(encoding="utf-8"))
after_assert = json.loads(
    (EV / "conditions_after" / "results" / "B1_contract_assertions.json")
    .read_text(encoding="utf-8"))
before_sum = json.loads(
    (EV / "conditions_before" / "results" / "mimo" /
     "conditions_summary.json").read_text(encoding="utf-8"))
after_sum = json.loads(
    (EV / "conditions_after" / "results" / "mimo" /
     "conditions_summary.json").read_text(encoding="utf-8"))

changed, kept = [], []
for b, a in zip(before_sum, after_sum):
    assert b["name"] == a["name"]
    if b["public_evaluation_buckets"] != a["public_evaluation_buckets"]:
        changed.append({
            "name": b["name"],
            "before": b["public_evaluation_buckets"],
            "after": a["public_evaluation_buckets"]})
    else:
        kept.append({"name": b["name"],
                     "buckets": a["public_evaluation_buckets"]})

result = {
    "review_source": "POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R2_2026-10-09 "
                     "section 4 (S5A-02 sole remaining P1)",
    "probe": "reviewer's mimo_conditions_probe.py + assert_B1_contract.py "
             "copied byte-faithful (SHA equal to the r2 review package), "
             "executed in fresh /private/tmp trees before (HEAD bytes) "
             "and after (r2 bytes)",
    "b1_contract_assertions": {
        "before": {
            "rows": before_assert,
            "n_pass": sum(1 for r in before_assert if r["passes_contract"]),
            "n_fail": sum(1 for r in before_assert
                          if not r["passes_contract"]),
            "exit_code": 1},
        "after": {
            "rows": after_assert,
            "n_pass": sum(1 for r in after_assert if r["passes_contract"]),
            "n_fail": sum(1 for r in after_assert
                          if not r["passes_contract"]),
            "exit_code": 0},
    },
    "seventeen_case_bucket_diff": {
        "n_cases": len(before_sum),
        "n_changed": len(changed),
        "n_kept": len(kept),
        "changed": changed,
        "kept": kept,
        "note": "changed = exactly the four unsupported-requirement-unit "
                "cases downgraded to condition_unknown; kept = two B1 "
                "lawful controls (C / empty unit stay compatible) plus "
                "the ten B2 species cases and B3 point-mismatch case "
                "(all byte-identical buckets)",
    },
    "scoring_status_all_scored_after": all(
        x["scoring_status"] == "scored" for x in after_sum),
}
out = EV / "flip_check.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
               encoding="utf-8")
print(json.dumps({
    "before_pass": result["b1_contract_assertions"]["before"]["n_pass"],
    "before_fail": result["b1_contract_assertions"]["before"]["n_fail"],
    "after_pass": result["b1_contract_assertions"]["after"]["n_pass"],
    "after_fail": result["b1_contract_assertions"]["after"]["n_fail"],
    "changed": len(changed), "kept": len(kept)}))
