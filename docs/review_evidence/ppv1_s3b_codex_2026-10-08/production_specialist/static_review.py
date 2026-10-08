#!/usr/bin/env python3
"""Capture primary source snippets for mimo 13 mutual verification (no execution)."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src/pathway_v43"
CHECKS = [
    ("mimo A malformed atomProp", "pollutant/chemstate.py", 310, 335, "consistent: malformed item not independent unknown r head"),
    ("mimo E early execution failure", "pollutant/production.py", 396, 409, "consistent: execution failure returns method_failed before audit"),
    ("mimo 0d2 narrow AuditContractError", "pollutant/runflow.py", 615, 656, "consistent: try excludes preparation and context load; narrow catch writes failure settlement"),
    ("mimo E/0d2 other RuntimeError escape", "pollutant/runflow.py", 321, 340, "consistent: drive catch lacks ChemicalStateError/HypothesisContractError/ConditionContractError"),
    ("mimo C proof branch order", "pollutant/audit.py", 1128, 1227, "scope correction: strict=False violated only after prior binding/coverage/inconclusive branches"),
    ("mimo B/G4 lambda_s times delta", "pollutant/audit.py", 913, 995, "verified source: coefficient binding separate, exact completion equations at973-979"),
    ("mimo D audit context strong guard", "pollutant/audit.py", 455, 478, "consistent: context and state strong guards in audit"),
    ("mimo D derive parent guard", "pollutant/path_context.py", 2322, 2333, "consistent: parent validate then source_ref"),
    ("mimo 0d8 claimed file wrong", "pollutant/runflow.py", 214, 223, "WRONG FILE: these are reconcile_followups, not start_run profile split"),
    ("mimo 0d8 actual start file", "workflow/runner.py", 214, 228, "correction: start_run split here"),
    ("mimo 0d8 actual resume file", "workflow/runner.py", 305, 320, "correction: resume_run split here"),
    ("R8 same-hash occurrence guard", "pollutant/store.py", 1085, 1154, "actual same-hash reused row guard, unchanged source"),
    ("first event unused old occurrence bound", "pollutant/store.py", 1719, 1785, "provided occurrences versus reuse_refs; unused distinct old appearance not current manifest"),
    ("all-SID old occurrences replay", "pollutant/store.py", 1330, 1382, "replay checks every old occurrence for participating SID"),
    ("readonly state helper bound", "pollutant/runflow.py", 870, 883, "get_state by itself not certificate; event-based recover verified upstream, no global certification"),
]
out = {"mode": "read_only_static_primary_source", "checks": []}
for title, rel, start, end, judgment in CHECKS:
    p = SRC / rel
    raw = p.read_bytes()
    lines = raw.decode().splitlines()
    out["checks"].append({"title": title, "source": str(p), "relative_source": str(p.relative_to(ROOT)), "source_sha256": hashlib.sha256(raw).hexdigest(), "start": start, "end": end, "snippet": "\n".join(f"{i}:{lines[i-1]}" for i in range(start, min(end,len(lines))+1)), "judgment": judgment})
specific = []
raises = []
for path in sorted(SRC.rglob("*.py")):
    if "vendor" in path.parts: continue
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type:
            names = [n.id for n in ast.walk(node.type) if isinstance(n, ast.Name)]
            if "AuditContractError" in names: specific.append({"path": str(path.relative_to(ROOT)), "line": node.lineno, "types": names})
        if isinstance(node, ast.Raise) and node.exc and isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name) and node.exc.func.id == "AuditContractError":
            raises.append({"path": str(path.relative_to(ROOT)), "line": node.lineno})
out["AuditContractError_specific_catches"] = specific
out["AuditContractError_direct_raise_sites"] = raises
out["mimo_G1_test_function_vs_case_warning"] = "A function count cannot identify parametrized parent-green cases. Retain R4 independent JUnit 11+1 historical evidence; no rerun performed here."
(ROOT / "static_checks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps({"snippets": len(CHECKS), "specific_catches": specific, "direct_AuditContractError_raise_count": len(raises)}, ensure_ascii=False, indent=2))
