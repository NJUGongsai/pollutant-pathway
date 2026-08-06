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
import pickle
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
        "mapper_backend": (
            "rdkit_explicit_map_validator+mcs_diagnostic_fallback"
            if py_avail("rdkit") is not None else None
        ),
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
    """Inspect only the project-declared legacy donor assets (read-only)."""
    env_keys = [k for k in os.environ if "REACTION" in k.upper() or "RHEA" in k.upper()
                or "BRENDA" in k.upper() or "META" in k.upper() or "DATA_ROOT" in k.upper()]
    data_root = os.environ.get(
        "ENZYMECAGE_DATA_ROOT", "/Volumes/CC/Enzyme_Agent/depending/data"
    )
    reaction_path = os.path.join(data_root, "rxn2enzyme_positives.pkl")
    center_path = os.path.join(
        data_root, "feature", "reaction", "reacting_center", "reacting_center.pkl"
    )
    reaction_count = 0
    center_count = 0
    overlap_count = 0
    load_error = None
    try:
        with open(reaction_path, "rb") as handle:
            reactions = pickle.load(handle)  # noqa: S301 -- controlled local asset
        with open(center_path, "rb") as handle:
            centers = pickle.load(handle)  # noqa: S301 -- controlled local asset
        if not isinstance(reactions, dict) or not isinstance(centers, dict):
            raise TypeError("declared source assets must both contain dicts")
        reaction_count = len(reactions)
        center_keys = {str(key) for key in centers}
        center_count = len(centers)
        overlap_count = sum(str(key) in center_keys for key in reactions)
    except Exception as exc:
        load_error = f"{type(exc).__name__}: {exc}"
    found = reaction_count > 0 and overlap_count == reaction_count
    return {
        "candidate_env_keys_present": env_keys,  # 只记 key 名，不记 value
        "real_reaction_source_found": found,
        "data_root_scan_allowed": False,         # 禁止扫整个 home
        "source_confirmation_method": "project_declared_legacy_donor_table",
        "reaction_source_path": reaction_path,
        "reacting_center_path": center_path,
        "reaction_count": reaction_count,
        "reacting_center_count": center_count,
        "reaction_center_overlap_count": overlap_count,
        "load_error": load_error,
    }


PROLINE_2OG_CASE = {
    "reaction": "2-oxoglutarate + proline + O2 -> succinate + hydroxyproline + CO2",
    "expected_lineages": ["proline -> hydroxyproline", "2-oxoglutarate -> succinate"],
    "forbidden_lineage": "2-oxoglutarate -> hydroxyproline",
    "source_record_found": None,  # None=required_case_missing
}


def case_inventory() -> dict:
    case = dict(PROLINE_2OG_CASE)
    audit_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports", "data_audit", "legacy_lineage_audit.json",
    )
    try:
        with open(audit_path, encoding="utf-8") as handle:
            audited = json.load(handle).get("proline_2og_case", {})
        case["source_record_found"] = bool(audited.get("source_record_found"))
        case["source_ids"] = audited.get("source_ids", [])
        case["structure_match_count"] = audited.get("structure_match_count", 0)
        case["verification_method"] = "G03 stereo-independent structure audit"
    except (OSError, ValueError):
        case["source_record_found"] = None
    return {"proline_2og": case}


# ============================================================
# Step 6: stop condition + main
# ============================================================

def evaluate_stop_condition(rt: dict, src: dict, case: dict) -> tuple[str, list[str]]:
    """返回 (status, reasons)。status ∈ {GO, PARTIAL, BLOCKED}。"""
    blockers: list[str] = []
    if rt.get("rdkit") is None:
        blockers.append("rdkit_absent")
    if not src["real_reaction_source_found"]:
        blockers.append("real_reaction_source_not_confirmed")
    if not case["proline_2og"]["source_record_found"]:
        blockers.append("required_case_missing")
    if not blockers:
        return "GO", []
    # mapper 缺但其余齐 → PARTIAL；source/case 缺 → BLOCKED
    if any(b in blockers for b in ("real_reaction_source_not_confirmed", "required_case_missing")):
        return "BLOCKED", blockers
    return "PARTIAL", blockers


_BLOCKER_MEANINGS = {
    "rdkit_absent": "rdkit not importable in `.venv` — atom mapping / chemistry deps missing",
    "real_reaction_source_not_confirmed": "No real complete-reaction-record source (RHEA/BRENDA/MetaCyc) confirmed",
    "required_case_missing": "Proline/2-oxoglutarate source record not yet provided",
}


def _fmt(v) -> str:
    if v is None:
        return "`null`"
    return str(v)


def _render_md(report: dict) -> str:
    """Render P1_PREFLIGHT.md from the SAME live inventory dict (Round 4 §13):
    the human-readable report is data-driven so it never claims RDKit absent
    when the live runtime probe found it present."""
    rt = report["runtime"]
    status = report["status"]
    blockers = report["blockers"]
    lines: list[str] = []
    lines.append("# P1 Preflight — Real-Resource Inventory")
    lines.append("")
    lines.append("**Generated by:** `scripts/p1_preflight.py` (per chatgpt_p1_train.md §6)")
    lines.append(f"**Working directory:** `{rt.get('working_directory')}`")
    lines.append("")
    lines.append(f"## Stop Condition: `{status}`")
    lines.append("")
    if blockers:
        lines.append("| Blocker | Meaning |")
        lines.append("|---------|---------|")
        for b in blockers:
            lines.append(f"| `{b}` | {_BLOCKER_MEANINGS.get(b, b)} |")
    else:
        lines.append("No blockers — status GO.")
    lines.append("")
    if status == "BLOCKED":
        lines.append(
            "Per §6 stop-condition logic: because "
            "`real_reaction_source_not_confirmed` and/or `required_case_missing` "
            "are present, status is **BLOCKED**. RDKit availability is determined "
            "by the live runtime probe below — it is NOT hard-coded.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Runtime Inventory")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    for k in ("python_version", "platform", "working_directory",
              "pydantic_version", "pytest_version", "rdkit", "numpy",
              "networkx", "scipy", "mapper_backend"):
        lines.append(f"| {k} | {_fmt(rt.get(k))} |")
    lines.append("")
    chem = {k: rt.get(k) for k in ("rdkit", "numpy", "networkx", "scipy")}
    present = [k for k, v in chem.items() if v is not None]
    absent = [k for k, v in chem.items() if v is None]
    lines.append(
        f"**Finding:** chemistry deps present: {present or 'none'}; "
        f"absent: {absent or 'none'}. `mapper_backend` is set in T1 after the "
        f"atom-mapper decision.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Legacy Source Inventory (read-only)")
    lines.append("")
    lines.append("| Relative path | Exists | sha256 | size |")
    lines.append("|---------------|--------|--------|------|")
    for it in report["legacy"]["legacy_sources"]:
        sha = it.get("sha256") or "— (directory)"
        lines.append(
            f"| `{it['relative_path']}` | {str(it['exists']).lower()} | "
            f"`{sha}` | {_fmt(it.get('size'))} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Real Reaction Source")
    lines.append("")
    rsrc = report["real_source"]
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| candidate_env_keys_present | {_fmt(rsrc.get('candidate_env_keys_present'))} |")
    lines.append(f"| real_reaction_source_found | {_fmt(rsrc.get('real_reaction_source_found'))} |")
    lines.append(f"| data_root_scan_allowed | {str(rsrc.get('data_root_scan_allowed')).lower()} |")
    lines.append("")
    if rsrc.get("real_reaction_source_found"):
        lines.append(
            "**Finding:** The project-declared legacy donor corpus is readable and "
            f"all {rsrc.get('reaction_count')} reaction rows have reacting-center records."
        )
    else:
        lines.append(
            "**Finding:** The declared local donor corpus is missing, unreadable, or "
            "does not have complete reacting-center coverage."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Proline / 2-Oxoglutarate Case")
    lines.append("")
    c = report["case"]["proline_2og"]
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| reaction | `{c['reaction']}` |")
    lines.append(f"| expected_lineages | `{c['expected_lineages']}` |")
    lines.append(f"| forbidden_lineage | `{c['forbidden_lineage']}` |")
    lines.append(f"| source_record_found | {_fmt(c.get('source_record_found'))} |")
    lines.append("")
    if c.get("source_record_found"):
        lines.append(
            f"**Finding:** G03 located {c.get('structure_match_count')} real source "
            "records by participant structure."
        )
    else:
        lines.append(
            "**Finding:** The canonical case is encoded but has not yet been bound "
            "to a structure-verified source row."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("- Machine-readable: `reports/p1/P1_PREFLIGHT.json`")
    lines.append("- This report: `reports/p1/P1_PREFLIGHT.md`")
    return "\n".join(lines) + "\n"


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
    # Render the human-readable report from the SAME live inventory so it can
    # never drift stale from the machine-readable JSON (Round 4 §13).
    with open("reports/p1/P1_PREFLIGHT.md", "w", encoding="utf-8") as f:
        f.write(_render_md(report))
    print(f"P1 Preflight status: {status}")
    print(f"Blockers: {reasons}")
    return 0 if status == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
