#!/usr/bin/env python3
"""Probe flip comparison: before (parent HEAD 2e1e7af behavior, reproduced
pre-fix) vs after (rework r1) for the four S5A P1 groups.

Consumes the probe outputs recorded in fresh /private/tmp workspaces:
- identity: probe/outputs/summary.json (six scope cases + required-node
  cases + controls)
- conditions: probe/outputs/conditions_summary.json (20 cases with the
  frozen same-source comparison)
- write boundary: probe/outputs/write_boundary.json (5 cases)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BEFORE = Path(sys.argv[1])
AFTER = Path(sys.argv[2])
FROZEN_MAP = {
    "satisfied": "compatible",
    "conflict": "essential_conflict",
    "unknown": "condition_unknown",
}


def load(root: Path, name: str):
    return json.loads((root / "probe" / "outputs" / name)
                      .read_text(encoding="utf-8"))


checks: list[dict] = []


def add(name: str, passed: bool, detail: dict) -> None:
    checks.append({"check": name, "passed": bool(passed), **detail})


# ---- S5A-01/03 identity flips ----
before_id = load(BEFORE, "summary.json")
after_id = load(AFTER, "summary.json")
before_by_case = {r["case"]: r for r in before_id}
after_by_case = {r["case"]: r for r in after_id}
for case in [c for c in after_by_case
             if c.startswith("reference_intermediates_")
             or c.startswith("reference_all_")]:
    b, a = before_by_case[case], after_by_case[case]
    scopesafe_b = all(
        n["scope"] == "strict_structure"
        or n["status"] != "strict_structure"
        for n in b["nodes"].values())
    scopesafe_a = all(
        n["scope"] == "strict_structure"
        or n["status"] != "strict_structure"
        for n in a["nodes"].values())
    edgesafe_a = all(e["status"] != "matched_strict"
                     for e in a["edges"].values())
    strict_a = all(e["status"] == "matched_strict"
                   for e in a["edges"].values())
    add("s5a01_scope_cap_" + case,
        (not scopesafe_b) and scopesafe_a and edgesafe_a,
        {"before_nodes_strict_violations": sum(
            1 for n in b["nodes"].values()
            if n["scope"] != "strict_structure"
            and n["status"] == "strict_structure"),
         "after_limited_nodes_cn_only": sum(
             1 for n in a["nodes"].values()
             if n["scope"] != "strict_structure"
             and n["status"] == "cn_only"),
         "after_edge_statuses": sorted(
             {e["status"] for e in a["edges"].values()})})
control_b = before_by_case["strict_control"]
control_a = after_by_case["strict_control"]
add("s5a01_legal_strict_control_kept",
    all(e["status"] == "matched_strict"
        for e in control_a["edges"].values())
    and control_a["status"] == "interface_verified_only"
    and all(e["status"] == "matched_strict"
            for e in control_b["edges"].values()),
    {"before_edge_statuses": sorted(
        {e["status"] for e in control_b["edges"].values()}),
     "after_edge_statuses": sorted(
         {e["status"] for e in control_a["edges"].values()})})
for name in ("isotope", "charge"):
    case = "strict_mismatch_" + name
    a = after_by_case[case]
    nodes_cn = all(
        n["status"] == "cn_only"
        for n in a["nodes"].values()
        if n["scope"] == "strict_structure"
        and n["status"] != "strict_structure")
    add("s5a01_real_cn_collateral_kept_" + name,
        nodes_cn and all(e["status"] != "matched_strict"
                         for e in a["edges"].values()),
        {})
for case in [c for c in after_by_case
             if c.endswith("_unmatched_structure")
             or c.endswith("_limited_duplicate")]:
    b, a = before_by_case[case], after_by_case[case]
    add("s5a03_required_node_" + case,
        b["target_edge"]["match_status"] == "matched_strict"
        and a["target_edge"]["match_status"] ==
        "unmatched_required_node_uncovered"
        and a["aggregate_reference_edges"]["buckets"].get(
            "matched_strict") == 1,
        {"before_edge": b["target_edge"]["match_status"],
         "after_edge": a["target_edge"]["match_status"],
         "after_gaps": [g["node_id"]
                        for g in a["target_edge"]["required_node_gaps"]]})
for case in [c for c in after_by_case
             if c.endswith("_inconsistent_participant_nodes")]:
    b, a = before_by_case[case], after_by_case[case]
    add("s5a03_participants_only_p2_deferred_" + case,
        b["target_edge"]["match_status"] == "matched_strict"
        and a["target_edge"]["match_status"] == "matched_strict",
        {"note": "participants-only P2: deferred, unchanged"})

# ---- S5A-02 conditions flips ----
before_cd = load(BEFORE, "conditions_summary.json")
after_cd = load(AFTER, "conditions_summary.json")
before_cd_by = {r["name"]: r for r in before_cd}
after_cd_by = {r["name"]: r for r in after_cd}
for name, row in after_cd_by.items():
    frozen_status = (row.get("frozen_assessment") or {}).get("status")
    buckets = row.get("public_evaluation_buckets") or {}
    after_cls = next(iter(buckets), None)
    before_cls = next(
        iter((before_cd_by[name].get("public_evaluation_buckets")
              or {})), None)
    if frozen_status in FROZEN_MAP:
        expected = FROZEN_MAP[frozen_status]
        passed = after_cls == expected
        detail = {"frozen": frozen_status, "before": before_cls,
                  "after": after_cls, "expected": expected}
    else:  # not_directly_representable (2 required_absent cases)
        expected = "requirement_status_not_representable"
        passed = after_cls == expected
        detail = {"frozen": frozen_status, "before": before_cls,
                  "after": after_cls, "expected": expected}
    add("s5a02_condition_" + name, passed, detail)

# ---- S5A-04 write boundary flips ----
before_wb = load(BEFORE, "write_boundary.json")
after_wb = load(AFTER, "write_boundary.json")
before_wb_by = {r["name"]: r for r in before_wb}
after_wb_by = {r["name"]: r for r in after_wb}
expect_refused = {
    "explicit_root_relative_wrong_cwd",
    "explicit_root_absolute_outside",
    "explicit_root_relative_symlink_escape",
    "explicit_root_absolute_symlink_escape",
}
for name, row in after_wb_by.items():
    b = before_wb_by[name]
    if name in expect_refused:
        if name in ("explicit_root_absolute_outside",
                    "explicit_root_absolute_symlink_escape"):
            # 评审口径:两绝对路径案父基线已拒(保持类,非翻转)
            add("s5a04_refused_kept_" + name,
                "exception" in b and "exception" in row
                and not row["target_exists_after"],
                {"before_refused": "exception" in b,
                 "after_refused": "exception" in row,
                 "after_kind": (row.get("exception") or {}).get(
                     "detail", {}).get("kind")})
        else:
            # 两相对路径案:父基线真实越界写入(评审反例)⇒ 翻转为拒
            add("s5a04_refused_" + name,
                "receipt" in b and "exception" in row
                and not row["target_exists_after"],
                {"before_accepted": "receipt" in b,
                 "after_refused": "exception" in row,
                 "after_kind": (row.get("exception") or {}).get(
                     "detail", {}).get("kind")})
    else:  # lawful positive
        lawful_path = Path(row["receipt"]["path"])
        add("s5a04_lawful_" + name,
            "receipt" in row and lawful_path.is_file(),
            {"after_receipt_path": row["receipt"]["path"]})

out = {
    "checks": checks,
    "pass": sum(1 for c in checks if c["passed"]),
    "fail": sum(1 for c in checks if not c["passed"]),
}
print(json.dumps(out, ensure_ascii=False, indent=2))
raise SystemExit(1 if out["fail"] else 0)
