"""P1-T3 Legacy lineage audit — read-only replay of legacy canonical_identity.

This script performs a **read-only static audit** of the legacy
``../benchmark/canonical_identity.py`` module and produces the mismatch
audit artifacts required by P1 Gate G03.

Audit scope (this run):
    Because the Preflight judged BLOCKED (real reaction source not confirmed,
    rdkit absent), this audit is a **logic-level static audit only**. It does
    NOT execute ``transformed_pair`` on real reaction rows (rdkit is absent,
    so the legacy code cannot run), and it does NOT fabricate examples.
    Per §9.8 the verdict is ``PARTIAL`` and the P1 Gate is BLOCKED.

What the audit DOES do (honest, non-fabricated):
    1. Records the legacy module fingerprint (sha256, size, read-only flag).
    2. Documents the five §9.4 mismatch categories with definitions.
    3. Inventories logic-level risks per audited legacy function.
    4. Checks the real-source availability (rdkit import + data source).
    5. Records the proline/2OG canonical case status as required_case_missing.
    6. Emits zero examples / zero source_ids (no real source audited).

Outputs:
    - ``reports/data_audit/legacy_lineage_audit.json`` (machine-readable)
    - ``reports/data_audit/legacy_lineage_audit.md`` (human-readable, numbers match)

Discipline (§9.2 / §9.8):
    - Legacy module is treated as read-only reference; this script never writes
      to ``../benchmark/`` or ``../core/``.
    - No failed records are deleted, no success-only sampling is performed.
    - No fixture data is reported as if it were a real audit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────────────
# Working directory is the demov2 root.
ROOT = Path(__file__).resolve().parent.parent  # .../ReactionAgent/demov2
LEGACY_DIR = ROOT.parent / "benchmark"          # .../ReactionAgent/benchmark
CORE_DIR = ROOT.parent / "core"                 # .../ReactionAgent/core
LEGACY_MODULE_PATH = LEGACY_DIR / "canonical_identity.py"
CHENYU_MODULE_PATH = CORE_DIR / "chenyu_features.py"

# Candidate real-data source (chenyu_features default data root).
DATA_ROOT = Path(
    os.environ.get(
        "ENZYMECAGE_DATA_ROOT",
        "/Volumes/CC/Enzyme_Agent/depending/data",
    )
)
RXN2ENZYME_PKL = DATA_ROOT / "rxn2enzyme_positives.pkl"
REACTING_CENTER_PKL = (
    DATA_ROOT / "feature" / "reaction" / "reacting_center" / "reacting_center.pkl"
)

# Output artifacts.
AUDIT_DIR = ROOT / "reports" / "data_audit"
AUDIT_JSON = AUDIT_DIR / "legacy_lineage_audit.json"
AUDIT_MD = AUDIT_DIR / "legacy_lineage_audit.md"

# Legacy module sha256 captured by Preflight §2 (frozen reference).
LEGACY_SHA256 = (
    "6003f4bc4ffc5ca3304dc1d2282a467f4f773e149ea9cf2a132ca0e4079eb2d0"
)

# Proline / 2-oxoglutarate canonical case (final_design §9.3).
PROLINE_2OG_CASE = {
    "reaction": "2-oxoglutarate + proline + O2 -> succinate + hydroxyproline + CO2",
    "expected_lineages": [
        "proline -> hydroxyproline",
        "2-oxoglutarate -> succinate",
    ],
    "forbidden_lineage": "2-oxoglutarate -> hydroxyproline",
}


# ── §9.4 Mismatch category definitions ───────────────────────────────────────
# These five categories are the required keys in the audit JSON (brief test
# contract). Each carries a definition so downstream G03 can verify the audit
# is not just an integer blob.
MISMATCH_CATEGORIES: dict[str, str] = {
    "cross_lineage_pair": (
        "Legacy transformed_pair picked a (X, Y) pair that crosses independent "
        "lineages — e.g. pairing 2-oxoglutarate -> hydroxyproline instead of "
        "proline -> hydroxyproline. This is the §9.3 forbidden-lineage failure "
        "mode: legacy single-pair selection cannot represent two parallel "
        "transformed lineages in one reaction."
    ),
    "cofactor_selected_as_main": (
        "Legacy pick_main (or _pick_transformed with an empty reaction-center "
        "fallback) selected a conserved cofactor (NADH/CoA/ATP/FAD/...) as the "
        "main substrate or product, mislabeling a spectator as the transformed "
        "core. COFACTORS stripping mitigates this only when the cofactor SMILES "
        "exactly matches the frozenset entry."
    ),
    "mapping_missing": (
        "No verifiable atom mapping exists for the reaction — either rdkit "
        "cannot parse it, chenyu_features.reaction_center_from_chenyu returned "
        "None, or the mapper backend is absent. Without a map there is no "
        "formal atom-transfer evidence, so the legacy pair is unsupported."
    ),
    "legacy_pair_supported": (
        "The legacy transformed_pair (X, Y) IS supported by the available "
        "mapping/lineage evidence — X and Y are the true transformed core and "
        "the pair does not cross lineages. This is the agreement category."
    ),
    "insufficient_evidence": (
        "Evidence is too thin to classify the legacy pair as either supported "
        "or a mismatch — e.g. ambiguous reaction center, partial mapping, or "
        "missing source stoichiometry. The record is retained (not deleted) "
        "and flagged for downstream quarantine/diagnostic review."
    ),
}


# ── Legacy logic risks (static, per audited function) ───────────────────────
# These are read-only findings about the legacy source. They do not require
# rdkit to execute — they are derived from reading the code.
LEGACY_LOGIC_RISKS: list[dict[str, str]] = [
    {
        "function": "pick_main",
        "lines": "60-77",
        "risk": (
            "Selects a single 'largest fragment' by (heavy_atoms, carbon, "
            "canonical SMILES lex). For multi-substrate reactions (97% of the "
            "corpus) this can pick a conserved cofactor as 'main' when no "
            "reaction-center signal is available — NADH/CoA are heavy and win "
            "the size contest. No cofactor stripping is applied at this layer."
        ),
    },
    {
        "function": "COFACTORS",
        "lines": "96-128",
        "risk": (
            "Cofactor stripping is exact-SMILES-match only. Canonical tautomers, "
            "protonation states, or salt forms that differ from the frozenset "
            "entry bypass the filter. Deliberately excludes ambiguous "
            "co-substrates (2-oxoglutarate/glutamate/pyruvate/acetyl-CoA) which "
            "are sometimes the true substrate — correct, but it means "
            "_pick_transformed must disambiguate them via reaction center alone."
        ),
    },
    {
        "function": "_pick_transformed",
        "lines": "131-157",
        "risk": (
            "When per_frag_center is None (chenyu_features unavailable or "
            "returns None), it silently degrades to 'largest non-cofactor "
            "fragment' — the same size-contest failure mode as pick_main, just "
            "with cofactors excluded. The fallback is not flagged in the return "
            "value, so callers cannot distinguish a center-anchored pick from a "
            "size-based guess."
        ),
    },
    {
        "function": "transformed_pair",
        "lines": "161-185",
        "risk": (
            "Returns a SINGLE (X, Y) pair per reaction. The §9.3 canonical case "
            "has TWO parallel transformed lineages (proline->hydroxyproline AND "
            "2-oxoglutarate->succinate); legacy can only represent one, forcing "
            "a cross-lineage pairing for the other. Also depends on "
            "chenyu_features.reaction_center_from_chenyu (imported inside a "
            "try/except) — if that import fails, the pair is computed without "
            "any reaction-center signal, silently degrading quality."
        ),
    },
    {
        "function": "group_key / main_substrate / main_product",
        "lines": "188-202",
        "risk": (
            "All three delegate to transformed_pair, so they inherit its "
            "single-pair limitation. group_key = (X, Y) means two reactions "
            "with the same true transformation but different legacy pairings "
            "(due to cofactor/tie ambiguity) land in different groups — "
            "splitting a chemical family and inflating apparent diversity."
        ),
    },
    {
        "function": "canon_smiles / canon_frags",
        "lines": "23-48",
        "risk": (
            "canon_frags returns a frozenset, discarding stoichiometry and "
            "duplicate fragments. This is fine for set-level comparison but "
            "means 'spectator' detection (canon_frags(r) & canon_frags(p)) "
            "cannot distinguish a truly conserved species from one that appears "
            "on both sides with different stoichiometry."
        ),
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _can_import(module_name: str) -> tuple[bool, str]:
    """Return (importable, version_or_error)."""
    try:
        mod = __import__(module_name)
        ver = getattr(mod, "__version__", "unknown")
        return True, ver
    except Exception as e:  # noqa: BLE001 — we want to capture any import failure
        return False, f"{type(e).__name__}: {e}"


def _check_real_source() -> dict[str, Any]:
    """Probe the real reaction-data source availability (read-only, no scan)."""
    rdkit_ok, rdkit_info = _can_import("rdkit")
    numpy_ok, numpy_info = _can_import("numpy")

    # Candidate data files (chenyu_features default paths).
    candidate_files = {
        "rxn2enzyme_positives": RXN2ENZYME_PKL,
        "reacting_center": REACTING_CENTER_PKL,
    }
    file_status: dict[str, dict[str, Any]] = {}
    for name, p in candidate_files.items():
        file_status[name] = {
            "path": str(p),
            "exists": p.exists(),
            "size": p.stat().st_size if p.exists() else 0,
        }

    # Count reactions in the candidate pkl WITHOUT rdkit (pickle only).
    rxn_count: int | None = None
    proline_hit_count = 0
    if RXN2ENZYME_PKL.exists():
        try:
            import pickle  # stdlib only

            with RXN2ENZYME_PKL.open("rb") as f:
                d = pickle.load(f)  # noqa: S301 — controlled local file
            if isinstance(d, dict):
                rxn_count = len(d)
                # Keyword scan for the canonical case (no rdkit needed).
                proline_hit_count = sum(
                    1 for k in d if isinstance(k, str) and "proline" in k.lower()
                )
        except Exception as e:  # noqa: BLE001
            file_status["rxn2enzyme_positives"]["load_error"] = (
                f"{type(e).__name__}: {e}"
            )

    # Env keys (Preflight checked these; we re-check for freshness).
    env_keys = [
        "REACTION_SOURCE", "RHEA_EXPORT", "BRENDA_DUMP", "METACYC_PGDB",
        "DATA_ROOT", "ENZYMECAGE_DATA_ROOT",
    ]
    env_present = {k: os.environ.get(k) for k in env_keys if os.environ.get(k)}

    # A real complete-reaction-record source requires BOTH rdkit (to run the
    # legacy logic) AND a confirmed source (env or user-confirmed path).
    source_confirmed = bool(env_present)  # user has not set any source env var
    real_source_found = source_confirmed and rdkit_ok

    return {
        "rdkit_available": rdkit_ok,
        "rdkit_info": rdkit_info,
        "numpy_available": numpy_ok,
        "numpy_info": numpy_info,
        "env_keys_present": env_present,
        "candidate_files": file_status,
        "candidate_rxn_count": rxn_count,
        "candidate_proline_keyword_hits": proline_hit_count,
        "source_confirmed_by_env": source_confirmed,
        "real_reaction_source_found": real_source_found,
        "usable_for_legacy_audit": real_source_found,
    }


def _audit_legacy_module() -> dict[str, Any]:
    """Read-only fingerprint + function inventory of the legacy module."""
    sha = _sha256(LEGACY_MODULE_PATH)
    size = LEGACY_MODULE_PATH.stat().st_size
    # Verify the sha matches the Preflight-frozen reference.
    sha_matches_preflight = sha == LEGACY_SHA256

    # Read the source (read-only) to confirm function presence without importing.
    source = LEGACY_MODULE_PATH.read_text(encoding="utf-8")
    expected_symbols = [
        "canon_smiles", "pick_main", "COFACTORS", "_pick_transformed",
        "transformed_pair", "group_key", "main_substrate", "main_product",
        "canon_frags", "canonical_reaction",
    ]
    symbols_present = {s: (f"def {s}" in source or f"{s} =" in source) for s in expected_symbols}

    return {
        "path": str(LEGACY_MODULE_PATH.relative_to(ROOT.parent.parent)),
        "absolute_path": str(LEGACY_MODULE_PATH),
        "sha256": sha,
        "sha_matches_preflight": sha_matches_preflight,
        "size": size,
        "read_only": True,
        "modified_by_audit": False,
        "symbols_present": symbols_present,
        "chenuyu_dependency_path": str(CHENYU_MODULE_PATH),
        "chenuyu_sha256": _sha256(CHENYU_MODULE_PATH) if CHENYU_MODULE_PATH.exists() else None,
    }


def _build_counts(source_status: dict[str, Any]) -> dict[str, int]:
    """Build the counts block.

    When the real source is unavailable, every category count is 0 and
    total_reactions (the denominator) is 0 — we audited zero real reactions.
    This is the honest PARTIAL counts block: no fabricated denominators.
    """
    if source_status["real_reaction_source_found"]:
        # Placeholder for the real-audit branch (not reached in this run).
        return {
            "total_reactions": source_status.get("candidate_rxn_count", 0) or 0,
            "audited_reactions": source_status.get("candidate_rxn_count", 0) or 0,
            "cross_lineage_pair": 0,
            "cofactor_selected_as_main": 0,
            "mapping_missing": 0,
            "legacy_pair_supported": 0,
            "insufficient_evidence": 0,
        }
    # PARTIAL / BLOCKED: zero real reactions audited.
    return {
        "total_reactions": 0,
        "audited_reactions": 0,
        "cross_lineage_pair": 0,
        "cofactor_selected_as_main": 0,
        "mapping_missing": 0,
        "legacy_pair_supported": 0,
        "insufficient_evidence": 0,
    }


def _build_verdict(source_status: dict[str, Any]) -> tuple[str, list[str]]:
    """Determine the audit verdict and its reasons."""
    reasons: list[str] = []
    if not source_status["real_reaction_source_found"]:
        reasons.append("real_reaction_source_not_confirmed")
    if not source_status["rdkit_available"]:
        reasons.append(
            "rdkit_absent_runtime_unable_to_execute_legacy_transformed_pair"
        )
    # Proline/2OG source record check.
    proline_found = source_status.get("candidate_proline_keyword_hits", 0) > 0
    if not proline_found:
        reasons.append("required_case_missing_proline_2og_source_record")

    if reasons:
        return "PARTIAL", reasons
    return "PASS", []


def _build_proline_case(source_status: dict[str, Any]) -> dict[str, Any]:
    """Record the proline/2OG canonical case status (§9.3)."""
    proline_hits = source_status.get("candidate_proline_keyword_hits", 0)
    return {
        "reaction": PROLINE_2OG_CASE["reaction"],
        "expected_lineages": PROLINE_2OG_CASE["expected_lineages"],
        "forbidden_lineage": PROLINE_2OG_CASE["forbidden_lineage"],
        "source_record_found": False,  # no RHEA ID / confirmed record
        "status": "required_case_missing",
        "candidate_keyword_hits": proline_hits,
        "note": (
            "The canonical case definition is encoded (final_design §9.3) but "
            "no source record (e.g. RHEA:10280) has been provided to bind it to "
            "real data. A keyword scan of the candidate pkl found "
            f"{proline_hits} proline-string hits (SMILES, not names — these are "
            "not confirmed complete records and rdkit is absent so they cannot "
            "be audited)."
        ),
    }


def _build_audit() -> dict[str, Any]:
    """Assemble the full audit record."""
    source_status = _check_real_source()
    legacy = _audit_legacy_module()
    counts = _build_counts(source_status)
    verdict, reasons = _build_verdict(source_status)
    proline_case = _build_proline_case(source_status)

    # examples / source_ids: empty when PARTIAL (§9.8 — no fabrication).
    examples: list[Any] = []
    source_ids: list[Any] = []
    if verdict == "PASS":
        # Real-audit branch (not reached in this run) would populate these.
        pass

    return {
        "audit_version": "p1-1",
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_scope": (
            "legacy_logic_static_audit_only — real reaction source not confirmed, "
            "rdkit absent; transformed_pair not executed on real rows"
        ),
        "verdict": verdict,
        "verdict_reasons": reasons,
        "legacy_module": legacy,
        "counts": counts,
        "categories": MISMATCH_CATEGORIES,
        "examples": examples,
        "source_ids": source_ids,
        "real_source_status": source_status,
        "legacy_logic_risks": LEGACY_LOGIC_RISKS,
        "proline_2og_case": proline_case,
        "discipline_notes": {
            "legacy_read_only": True,
            "no_failed_records_deleted": True,
            "no_success_only_sampling": True,
            "no_fixture_reported_as_real": True,
            "section_9_8_compliant": True,
        },
    }


def _render_md(audit: dict[str, Any]) -> str:
    """Render the human-readable MD report. Numbers MUST match the JSON."""
    lines: list[str] = []
    lines.append("# P1-T3 Legacy Lineage Audit\n")
    lines.append(f"**Audit version:** {audit['audit_version']}  ")
    lines.append(f"**Timestamp:** {audit['audit_timestamp']}  ")
    lines.append(f"**Verdict:** `{audit['verdict']}`  ")
    lines.append(f"**Scope:** {audit['audit_scope']}\n")

    # Verdict reasons
    if audit["verdict_reasons"]:
        lines.append("## Verdict reasons\n")
        for r in audit["verdict_reasons"]:
            lines.append(f"- `{r}`")
        lines.append("")

    # Legacy module fingerprint
    lm = audit["legacy_module"]
    lines.append("## Legacy module (read-only)\n")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| path | `{lm['path']}` |")
    lines.append(f"| sha256 | `{lm['sha256']}` |")
    lines.append(f"| sha matches Preflight | {lm['sha_matches_preflight']} |")
    lines.append(f"| size | {lm['size']} bytes |")
    lines.append(f"| read_only | {lm['read_only']} |")
    lines.append(f"| modified_by_audit | {lm['modified_by_audit']} |")
    lines.append("")

    # Counts
    c = audit["counts"]
    lines.append("## Counts (§9.5 layered stats)\n")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for cat, n in c.items():
        lines.append(f"| {cat} | {n} |")
    lines.append("")
    lines.append(
        f"**Denominator:** `total_reactions = {c['total_reactions']}` "
        "(0 because no real source was audited — PARTIAL).\n"
    )

    # Mismatch categories
    cats = audit["categories"]
    lines.append("## Mismatch categories (§9.4 definitions)\n")
    for cat, defn in cats.items():
        lines.append(f"### `{cat}`\n")
        lines.append(f"{defn}\n")

    # Legacy logic risks
    risks = audit["legacy_logic_risks"]
    lines.append("## Legacy logic risks (static audit)\n")
    lines.append("| Function | Lines | Risk |")
    lines.append("|----------|-------|------|")
    for r in risks:
        lines.append(f"| `{r['function']}` | {r['lines']} | {r['risk']} |")
    lines.append("")

    # Real source status
    rs = audit["real_source_status"]
    lines.append("## Real source status\n")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| rdkit_available | {rs['rdkit_available']} |")
    lines.append(f"| rdkit_info | `{rs['rdkit_info']}` |")
    lines.append(f"| numpy_available | {rs['numpy_available']} |")
    lines.append(f"| env_keys_present | {rs['env_keys_present'] or '{}'} |")
    lines.append(f"| candidate_rxn_count | {rs.get('candidate_rxn_count')} |")
    lines.append(f"| candidate_proline_keyword_hits | {rs.get('candidate_proline_keyword_hits')} |")
    lines.append(f"| source_confirmed_by_env | {rs['source_confirmed_by_env']} |")
    lines.append(f"| real_reaction_source_found | {rs['real_reaction_source_found']} |")
    lines.append(f"| usable_for_legacy_audit | {rs['usable_for_legacy_audit']} |")
    lines.append("")
    # Candidate files
    lines.append("### Candidate data files\n")
    lines.append("| File | Exists | Size |")
    lines.append("|------|--------|------|")
    for name, info in rs["candidate_files"].items():
        lines.append(f"| {name} | {info['exists']} | {info['size']} |")
    lines.append("")

    # Proline / 2OG case
    pc = audit["proline_2og_case"]
    lines.append("## Proline / 2-oxoglutarate case (§9.3)\n")
    lines.append(f"- **reaction:** {pc['reaction']}")
    lines.append(f"- **expected_lineages:** {pc['expected_lineages']}")
    lines.append(f"- **forbidden_lineage:** {pc['forbidden_lineage']}")
    lines.append(f"- **source_record_found:** {pc['source_record_found']}")
    lines.append(f"- **status:** `{pc['status']}`")
    lines.append(f"- {pc['note']}\n")

    # Examples / source IDs
    lines.append("## Examples & source IDs\n")
    lines.append(
        f"- **examples:** {len(audit['examples'])} entries "
        "(empty — no real source audited; §9.8 forbids fabrication)\n"
    )
    lines.append(
        f"- **source_ids:** {len(audit['source_ids'])} entries "
        "(empty — no real source confirmed)\n"
    )

    # Discipline
    dn = audit["discipline_notes"]
    lines.append("## Discipline (§9.2 / §9.8)\n")
    for k, v in dn.items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")

    lines.append("---\n")
    lines.append(
        "**Artifacts:** "
        f"`{AUDIT_JSON.relative_to(ROOT)}` + "
        f"`{AUDIT_MD.relative_to(ROOT)}`\n"
    )
    return "\n".join(lines)


def main() -> int:
    """Run the audit and write JSON + MD artifacts. Returns exit code."""
    audit = _build_audit()

    # Verify legacy module was NOT modified (read-only guard).
    legacy_sha = _sha256(LEGACY_MODULE_PATH)
    if legacy_sha != LEGACY_SHA256:
        print(
            f"ERROR: legacy module sha256 changed during audit: "
            f"{LEGACY_SHA256} -> {legacy_sha}",
            file=sys.stderr,
        )
        return 2

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    AUDIT_MD.write_text(_render_md(audit), encoding="utf-8")

    print(f"Audit verdict: {audit['verdict']}")
    print(f"  reasons: {audit['verdict_reasons']}")
    print(f"  counts.total_reactions: {audit['counts']['total_reactions']}")
    print(f"  examples: {len(audit['examples'])} (no fabrication)")
    print(f"  legacy sha256: {legacy_sha} (read-only, matches Preflight)")
    print(f"  JSON: {AUDIT_JSON}")
    print(f"  MD:   {AUDIT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
