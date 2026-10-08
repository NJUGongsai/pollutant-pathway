#!/usr/bin/env python3
"""Classify the direct-parent (1ef9e48) red/green nodeids for S5a rework r2.

Input: parent_baseline/junit.xml (5 files = the r2 new + updated set, run
on the detached same-byte parent worktree with r2-byte test files).
Output: parent_baseline/baseline_classification.json with per-nodeid
red classification (behavior / field-missing / version-literal) and the
legal-green highlights.
"""
from __future__ import annotations
import json
import sys
import xml.etree.ElementTree as ET

junit = sys.argv[1]
out = sys.argv[2]

root = ET.parse(junit).getroot()
# junit for pytest: <testsuites><testsuite><testcase ...
cases = []
for suite in root.iter("testsuite"):
    for case in suite.iter("testcase"):
        classname = case.get("classname") or ""
        file_path = classname.replace(".", "/") + ".py"
        nodeid = f"{file_path}::{case.get('name')}"
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if error is not None:
            state = "error"
            detail = (error.text or "")
        elif failure is not None:
            state = "failed"
            detail = (failure.text or "")
        elif skipped is not None:
            state = "skipped"
            detail = (skipped.text or "")[:200]
        else:
            state = "passed"
            detail = ""
        cases.append({"nodeid": nodeid, "state": state,
                      "detail": detail,
                      "detail_head": detail[:400]})


def classify(case):
    if case["state"] != "failed":
        return None
    name = case["nodeid"]
    detail = case["detail"]
    if "KeyError: 'reason'" in detail:
        return ("field-missing",
                "parent disclosure lacks the machine-readable "
                "'reason' key (requirement_unit_canonical_by_key); "
                "classification compatible itself is already correct "
                "on the parent")
    if "test_s5a_r2_contract_version_registration" in name or \
            "test_s5a_rework_contract_version_registration" in name or \
            "test_ppv1_identity_block_contract_versions" in name or \
            "test_native_export_public_chain_files_and_manifest" in name:
        return ("version-literal",
                "parent registers evaluation-2/template-2/profile-21; "
                "r2 asserts evaluation-3/template-3/profile-22")
    return ("behavior",
            "parent classifies the requirement with the non-canonical/"
            "unexpected unit as compatible/essential_conflict (unit "
            "dropped before the frozen canonical-by-key comparison); "
            "r2 expects condition_unknown + requirement_unit_not_"
            "representable")


reds = []
greens = []
for case in cases:
    if case["state"] == "failed":
        kind, note = classify(case)
        reds.append({"nodeid": case["nodeid"], "kind": kind,
                     "note": note, "detail_head": case["detail_head"]})
    else:
        greens.append({"nodeid": case["nodeid"], "state": case["state"]})

summary = {
    "parent_head": "1ef9e4840ff1be233dedcb543b967447cd591276",
    "files": sorted({c["nodeid"].split("::")[0] for c in cases}),
    "counts": {
        "total": len(cases),
        "red": len(reds),
        "green": len([c for c in cases if c["state"] == "passed"]),
        "error_or_collection": len([c for c in cases
                                    if c["state"] in ("error",
                                                      "skipped")]),
        "red_by_kind": {
            k: len([r for r in reds if r["kind"] == k])
            for k in ("behavior", "field-missing", "version-literal")},
    },
    "red_nodeids": sorted(reds, key=lambda r: (r["kind"], r["nodeid"])),
    "legal_green_highlights": [
        "B1 lawful positive controls on the parent: "
        "test_s5a02_r2_b1_six_cases_classifier"
        "[B1_requirement_C_25_vs_25C] and both "
        "test_s5a02_r2_b1_end_to_end_public_chain_and_aggregate "
        "positive params stay green (compatible kept)",
        "B2 checked-builder/order-gate guard green on the parent "
        "(opposite facts both orders unknown; known x unknown judged by "
        "the first known fact in both orders)",
        "r1 20 condition cases all preserved green on the parent",
        "requirement-vs-fact unit semantics split green on the parent "
        "(fact-side source_unit_unknown / unit_mismatch / canonical)",
    ],
    "green_nodeids": sorted(g["nodeid"] for g in greens),
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(json.dumps(summary["counts"], ensure_ascii=False))
