#!/usr/bin/env python3
"""P5 evidence-packet integrity self-check (read-only).

Closes the recurring evidence-truncation defect class (R1-04 → P5-R2-01 →
P5-R3-01): before every submission the packet is checked for:

1. Probe A/B round-trip: the exact prose the auditor script extracts
   (``extract_probes``) must contain every mandatory evidence line intact —
   no mid-line cut, no unclosed backtick, no missing status cell;
2. code fences / inline backticks balanced;
3. every referenced evidence file exists and is readable;
4. every table row has the same number of cells as its header.

Read-only: never mutates the packet or any source artifact.
"""
from __future__ import annotations

import os
import re
import sys

_DEMOV2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKET = os.path.join(
    _DEMOV2, "reports", "p5", "INDEPENDENT_VERIFICATION_PACKET_R3.md")

# The mandatory evidence lines the auditor must see, verbatim substrings.
MANDATORY_LINES = [
    "P4=`reports/p4/P4_GATE_REPORT.json`(READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT",
    "工件(R6-01)",
    "豁免(R6-04)",
    "护栏(R6-03)",
    "R0 链(R6-02)",
    "R5-01..04 全 Closed",
    "86 passed",
]

# Evidence file paths referenced in the packet (relative to demov2 root).
REFERENCED_FILES = [
    "reports/p1/real_snapshot/snap_19caddc6b312/manifest.json",
    "reports/p1/real_snapshot/snap_19caddc6b312/records.jsonl",
    "reports/p2/truth_records.json",
    "reports/p2/split_manifest.json",
    "reports/p3/current_run_artifact.json",
    "reports/p4/P4_GATE_REPORT.json",
]


def extract_probes(text: str) -> str:
    """Mirror run_kimi_audit.extract_probes exactly (1500-char cap)."""
    m = re.search(
        r"(#{2,3} Probe A[^\n]*\n(?:.*\n){0,14}?)(?=#{2,3} Probe B|## |\Z)",
        text, re.DOTALL)
    m2 = re.search(
        r"(#{2,3} Probe B[^\n]*\n(?:.*\n){0,14}?)(?=#+ [A-Z]|\Z)",
        text, re.DOTALL)
    return ((m.group(1) if m else "") + (m2.group(1) if m2 else ""))[:1500]


def check() -> list[str]:
    issues: list[str] = []
    text = open(PACKET, encoding="utf-8").read()

    # 1. Round-trip: mandatory lines must survive extract_probes intact.
    probes = extract_probes(text)
    for line in MANDATORY_LINES:
        if line not in probes:
            issues.append(f"mandatory line truncated by extract_probes: {line[:60]}")

    # 2. Inline backticks + code fences balanced.
    if text.count("`") % 2 != 0:
        issues.append("unbalanced inline backticks")
    fences = len(re.findall(r"^```", text, re.MULTILINE))
    if fences % 2 != 0:
        issues.append(f"unbalanced code fences ({fences})")

    # 3. Referenced evidence files exist and are readable.
    for rel in REFERENCED_FILES:
        path = os.path.join(_DEMOV2, rel)
        if not os.path.exists(path):
            issues.append(f"referenced file missing: {rel}")
        else:
            try:
                with open(path, "rb"):
                    pass
            except OSError as exc:
                issues.append(f"referenced file unreadable: {rel} ({exc})")

    # 4. Table rows have the same cell count as their header.
    header = None
    for line in text.splitlines():
        if line.startswith("|") and re.match(r"^\|[\s\-|]+$", line):
            continue  # separator
        if line.startswith("|"):
            cells = line.count("|") - 1
            if header is None:
                header = cells
            elif cells != header:
                issues.append(f"table row cell mismatch: {line[:60]}")

    return issues


def main() -> int:
    issues = check()
    if issues:
        print(f"P5_PACKET_SELFCHECK: FAIL ({len(issues)} issues)")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(f"P5_PACKET_SELFCHECK: PASS (packet {os.path.basename(PACKET)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())