#!/usr/bin/env python3
"""P1 preflight: real-resource inventory per chatgpt_p1_train.md §6.

Performs four read-only inventories:
  1. runtime  — Python + chem deps (rdkit/numpy/networkx/scipy/mapper_backend)
  2. legacy   — read-only legacy sources (../benchmark, ../core)
  3. source   — real complete-reaction-record source (RHEA/BRENDA/MetaCyc env probes)
  4. case     — proline/2-oxoglutarate case availability

Evaluates a stop condition (GO / PARTIAL / BLOCKED) and writes
reports/p1/P1_PREFLIGHT.json.

Exit code: 0 only if status == GO, else 1.

Deviations from brief code:
  - legacy_inventory(): brief uses 3 dirname() calls for `root` then 1 for
    `parent`, which resolves to .../branch/ (contradicting its own comment
    `# CC/branch/ReactionAgent`). Fixed to 2 dirname() calls for demov2_root
    so `parent` correctly resolves to .../ReactionAgent/ where ../benchmark
    and ../core actually live. All other values verbatim from the brief.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import importlib.metadata as md


# ============================================================
# Step 3: runtime inventory
# ============================================================

def runtime_inventory() -> dict:
    def ver(name: str) -> str | None:
        try:
            return md.version(name)
        except md.PackageNotFoundError:
            return None

    def py_avail(mod: str) -> str | None:
        try:
            m = __import__(mod)
            return getattr(m, "__version__", "present")
        except Exception:
            return None

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "working_directory": os.getcwd(),
        "pydantic_version": ver("pydantic"),
        "pytest_version": ver("pytest"),
        "rdkit": py_avail("rdkit"),
        "numpy": py_avail("numpy"),
        "networkx": py_avail("networkx"),
        "scipy": py_avail("scipy"),
        "mapper_backend": None,  # T1 决策后填
    }


# ============================================================
# Step 4: legacy source inventory (read-only)
# ============================================================

def _sha256(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def legacy_inventory() -> dict:
    # NOTE: brief uses 3 dirname() calls here; that resolves to .../branch/
    # (contradicting its own comment). Using 2 so `parent` = ReactionAgent.
    demov2_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parent = os.path.dirname(demov2_root)  # CC/branch/ReactionAgent
    targets = [
        "../benchmark/canonical_identity.py",
        "../benchmark",
        "../core",
    ]
    items = []
    for rel in targets:
        p = os.path.normpath(os.path.join(parent, rel.replace("../", "")))
        items.append({
            "relative_path": rel,
            "absolute_path": p,
            "exists": os.path.exists(p),
            "sha256": _sha256(p) if os.path.isfile(p) else None,
            "size": os.path.getsize(p) if os.path.exists(p) else None,
        })
    return {"legacy_sources": items}


# ============================================================
# Step 5: real reaction source + proline/2OG case
# ============================================================

def real_source_inventory() -> dict:
    """探明真实完整反应记录来源（§6.3/§6.4）。只读环境变量是否存在，不输出值。"""
    env_keys = [k for k in os.environ if "REACTION" in k.upper() or "RHEA" in k.upper()
                or "BRENDA" in k.upper() or "META" in k.upper() or "DATA_ROOT" in k.upper()]
    return {
        "candidate_env_keys_present": env_keys,  # 只记 key 名，不记 value
        "real_reaction_source_found": None,      # None=未确定，待 T3/T6 确认
        "data_root_scan_allowed": False,         # 禁止扫整个 home
    }


PROLINE_2OG_CASE = {
    "reaction": "2-oxoglutarate + proline + O2 -> succinate + hydroxyproline + CO2",
    "expected_lineages": ["proline -> hydroxyproline", "2-oxoglutarate -> succinate"],
    "forbidden_lineage": "2-oxoglutarate -> hydroxyproline",
    "source_record_found": None,  # None=required_case_missing
}


def case_inventory() -> dict:
    return {"proline_2og": PROLINE_2OG_CASE}


# ============================================================
# Step 6: stop condition + main
# ============================================================

def evaluate_stop_condition(rt: dict, src: dict, case: dict) -> tuple[str, list[str]]:
    """返回 (status, reasons)。status ∈ {GO, PARTIAL, BLOCKED}。"""
    blockers: list[str] = []
    if rt.get("rdkit") is None:
        blockers.append("rdkit_absent")
    if src["real_reaction_source_found"] is None:
        blockers.append("real_reaction_source_not_confirmed")
    if case["proline_2og"]["source_record_found"] is None:
        blockers.append("required_case_missing")
    if not blockers:
        return "GO", []
    # mapper 缺但其余齐 → PARTIAL；source/case 缺 → BLOCKED
    if any(b in blockers for b in ("real_reaction_source_not_confirmed", "required_case_missing")):
        return "BLOCKED", blockers
    return "PARTIAL", blockers


def main() -> int:
    rt = runtime_inventory()
    lg = legacy_inventory()
    src = real_source_inventory()
    case = case_inventory()
    status, reasons = evaluate_stop_condition(rt, src, case)
    report = {
        "status": status,
        "blockers": reasons,
        "runtime": rt,
        "legacy": lg,
        "real_source": src,
        "case": case,
    }
    os.makedirs("reports/p1", exist_ok=True)
    with open("reports/p1/P1_PREFLIGHT.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(f"P1 Preflight status: {status}")
    print(f"Blockers: {reasons}")
    return 0 if status == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
