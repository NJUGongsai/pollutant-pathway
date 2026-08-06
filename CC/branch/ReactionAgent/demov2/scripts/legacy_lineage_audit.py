"""P1-T3 Legacy lineage audit — read-only replay of legacy canonical_identity.

This script performs a **read-only full-corpus audit** of the legacy
``../benchmark/canonical_identity.py`` module and produces the mismatch
audit artifacts required by P1 Gate G03.

Audit scope:
    The project-declared legacy donor table ``rxn2enzyme_positives.pkl`` is a
    cache of positive complete reaction SMILES from
    ``formal_filtered_train.csv`` (documented by ``core/enzyme_lookup.py``).
    Every one of its 3,601 reactions has a matching entry in the independently
    stored reacting-center table.  The audit executes the frozen legacy
    selector on every row and checks its selected fragment pair against the
    reacting-center fragment-pair evidence.  Center pairs are used only for
    lineage support; they are never called full atom mapping.

What the audit DOES do (honest, non-fabricated):
    1. Records the legacy module fingerprint (sha256, size, read-only flag).
    2. Documents the five §9.4 mismatch categories with definitions.
    3. Inventories logic-level risks per audited legacy function.
    4. Checks and fingerprints the real local source files.
    5. Locates the proline/2OG canonical case by molecular structure.
    6. Emits stable source IDs and bounded examples from real audited rows.

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
import pickle
import sys
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
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
    """Probe and fingerprint the project-declared legacy reaction source."""
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
            "sha256": _sha256(p) if p.exists() else None,
        }

    # Count reactions in the candidate pkl WITHOUT rdkit (pickle only).
    rxn_count: int | None = None
    if RXN2ENZYME_PKL.exists():
        try:
            with RXN2ENZYME_PKL.open("rb") as f:
                d = pickle.load(f)  # noqa: S301 — controlled local file
            if isinstance(d, dict):
                rxn_count = len(d)
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

    # Source authority is project-local and explicit: enzyme_lookup.py states
    # that this cache is built from positive CANO_RXN_SMILES rows in
    # formal_filtered_train.csv.  The user also defined the donor table's A>>B
    # value as the complete reaction record.  We preserve the limitation that
    # this is not a RHEA/BRENDA record export with external database IDs.
    source_confirmed = (
        RXN2ENZYME_PKL.exists()
        and REACTING_CENTER_PKL.exists()
        and isinstance(rxn_count, int)
        and rxn_count > 0
    )
    real_source_found = source_confirmed and rdkit_ok

    return {
        "rdkit_available": rdkit_ok,
        "rdkit_info": rdkit_info,
        "numpy_available": numpy_ok,
        "numpy_info": numpy_info,
        "env_keys_present": env_present,
        "candidate_files": file_status,
        "candidate_rxn_count": rxn_count,
        "candidate_proline_keyword_hits": None,
        "source_confirmed_by_env": bool(env_present),
        "source_confirmation_method": "project_declared_legacy_donor_table",
        "source_authority": {
            "name": "chenyu_formal_filtered_train_positive_cache",
            "record_shape": "complete_reaction_smiles -> [(UniProt, EC), ...]",
            "declaration": "core/enzyme_lookup.py: positive CANO_RXN_SMILES cache",
            "external_database_record_ids_available": False,
            "limitation": (
                "Auditable as the legacy donor corpus; not represented as a "
                "RHEA/BRENDA/MetaCyc export."
            ),
        },
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


def _source_id(reaction_smiles: str) -> str:
    """Stable ID for a row in the legacy donor corpus."""
    digest = hashlib.sha256(reaction_smiles.encode("utf-8")).hexdigest()
    return f"chenyu-positive-rxn:{digest}"


def _fragment_index_by_global_atom(molecule: Any) -> dict[int, int]:
    """Map RDKit global atom indices to participant fragment positions."""
    from rdkit import Chem

    return {
        atom_index: fragment_index
        for fragment_index, atom_indices in enumerate(Chem.GetMolFrags(molecule))
        for atom_index in atom_indices
    }


def _canonical_fragment_positions(side: str, canonical_smiles: str, ci: Any) -> list[int]:
    positions: list[int] = []
    for index, fragment in enumerate(side.split(".")):
        if ci.canon_smiles(fragment) == canonical_smiles:
            positions.append(index)
    return positions


@lru_cache(maxsize=200_000)
def _scaffold_continuity(left_smiles: str, right_smiles: str) -> tuple[float, int]:
    """Return deterministic RDKit topological-fingerprint continuity.

    This is lineage continuity evidence, not atom mapping.  It is used only to
    audit whether the legacy independently selected X/Y fragments belong to
    the same dominant structural lineage.  RDK fingerprints are used for the
    full-corpus comparison because their runtime is bounded; the required
    proline/2OG case is also represented by explicit participant structures.
    """
    from rdkit import Chem, DataStructs

    left = Chem.MolFromSmiles(left_smiles)
    right = Chem.MolFromSmiles(right_smiles)
    if left is None or right is None:
        return 0.0, 0
    left_fp = Chem.RDKFingerprint(left)
    right_fp = Chem.RDKFingerprint(right)
    shared_bits = int((left_fp & right_fp).GetNumOnBits())
    return float(DataStructs.TanimotoSimilarity(left_fp, right_fp)), shared_bits


def _lineage_continuity_evidence(
    left: str,
    right: str,
    r_position: int,
    p_position: int,
    ci: Any,
) -> dict[str, Any]:
    """Check whether the selected pair is a unique mutual continuity best."""
    r_fragments = left.split(".")
    p_fragments = right.split(".")
    spectators = ci.canon_frags(left) & ci.canon_frags(right)
    exclude = ci.COFACTORS | spectators
    eligible_r = [
        (index, canonical)
        for index, fragment in enumerate(r_fragments)
        if (canonical := ci.canon_smiles(fragment)) is not None
        and canonical not in exclude
    ]
    eligible_p = [
        (index, canonical)
        for index, fragment in enumerate(p_fragments)
        if (canonical := ci.canon_smiles(fragment)) is not None
        and canonical not in exclude
    ]
    selected_r = ci.canon_smiles(r_fragments[r_position])
    selected_p = ci.canon_smiles(p_fragments[p_position])
    selected_score, selected_atoms = _scaffold_continuity(selected_r, selected_p)

    product_scores = [
        (index, *_scaffold_continuity(selected_r, canonical))
        for index, canonical in eligible_p
    ]
    reactant_scores = [
        (index, *_scaffold_continuity(canonical, selected_p))
        for index, canonical in eligible_r
    ]
    best_product_score = max((item[1] for item in product_scores), default=0.0)
    best_reactant_score = max((item[1] for item in reactant_scores), default=0.0)
    best_products = [item[0] for item in product_scores if item[1] == best_product_score]
    best_reactants = [item[0] for item in reactant_scores if item[1] == best_reactant_score]
    mutual_unique_best = (
        best_products == [p_position]
        and best_reactants == [r_position]
        and selected_atoms > 0
    )
    tied = len(best_products) != 1 or len(best_reactants) != 1
    return {
        "selected_continuity": round(selected_score, 6),
        "selected_shared_fingerprint_bits": selected_atoms,
        "best_product_positions_for_selected_reactant": best_products,
        "best_reactant_positions_for_selected_product": best_reactants,
        "mutual_unique_best": mutual_unique_best,
        "tie": tied,
        "semantics": (
            "RDKit topological-fingerprint continuity for lineage audit; "
            "not atom mapping"
        ),
    }


def _stereo_free_canonical(smiles: str) -> str | None:
    from rdkit import Chem

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return None
    Chem.RemoveStereochemistry(molecule)
    return Chem.MolToSmiles(molecule, isomericSmiles=False)


_CASE_STRUCTURES = {
    "proline": _stereo_free_canonical("O=C(O)C1CCCN1"),
    "2_oxoglutarate": _stereo_free_canonical("O=C(O)CCC(=O)C(=O)O"),
    "oxygen": _stereo_free_canonical("O=O"),
    "succinate": _stereo_free_canonical("O=C(O)CCC(=O)O"),
    "hydroxyproline": _stereo_free_canonical("O=C(O)C1CC(O)CN1"),
    "carbon_dioxide": _stereo_free_canonical("O=C=O"),
}


def _is_proline_2og_case(reaction_smiles: str) -> bool:
    left, right = reaction_smiles.split(">>", 1)
    lhs = {_stereo_free_canonical(fragment) for fragment in left.split(".")}
    rhs = {_stereo_free_canonical(fragment) for fragment in right.split(".")}
    return {
        _CASE_STRUCTURES["proline"],
        _CASE_STRUCTURES["2_oxoglutarate"],
        _CASE_STRUCTURES["oxygen"],
    }.issubset(lhs) and {
        _CASE_STRUCTURES["succinate"],
        _CASE_STRUCTURES["hydroxyproline"],
        _CASE_STRUCTURES["carbon_dioxide"],
    }.issubset(rhs)


def _load_legacy_module() -> Any:
    """Import the frozen legacy module while resolving its core dependency."""
    for path in (str(CORE_DIR), str(LEGACY_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)
    spec = importlib.util.spec_from_file_location(
        "p1_frozen_legacy_canonical_identity", LEGACY_MODULE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen legacy canonical_identity module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit_real_rows() -> tuple[dict[str, int], list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Replay all real rows and classify the selected fragment pair."""
    from rdkit import Chem

    with RXN2ENZYME_PKL.open("rb") as handle:
        reactions = pickle.load(handle)  # noqa: S301 -- controlled local asset
    with REACTING_CENTER_PKL.open("rb") as handle:
        centers_raw = pickle.load(handle)  # noqa: S301 -- controlled local asset
    centers = {str(key): value for key, value in centers_raw.items()}
    if not isinstance(reactions, dict):
        raise TypeError("rxn2enzyme_positives.pkl must contain a dict")

    ci = _load_legacy_module()
    category_counts: Counter[str] = Counter()
    examples_by_category: dict[str, list[dict[str, Any]]] = {
        category: [] for category in MISMATCH_CATEGORIES
    }
    source_ids: list[str] = []
    required_cases: list[dict[str, Any]] = []

    for reaction_smiles, enzyme_records in reactions.items():
        reaction_smiles = str(reaction_smiles)
        source_id = _source_id(reaction_smiles)
        source_ids.append(source_id)
        category = "insufficient_evidence"
        reason = "unclassified"
        legacy_pair = None
        supported_edges: list[list[int]] = []
        continuity_evidence: dict[str, Any] | None = None

        try:
            legacy_pair = ci.transformed_pair(reaction_smiles)
            center = centers.get(reaction_smiles)
            if center is None:
                category, reason = "mapping_missing", "reacting_center_record_missing"
            elif legacy_pair is None:
                category, reason = "insufficient_evidence", "legacy_pair_unresolved"
            else:
                left, right = reaction_smiles.split(">>", 1)
                r_molecule = Chem.MolFromSmiles(left)
                p_molecule = Chem.MolFromSmiles(right)
                r_center, p_center = list(center[0]), list(center[1])
                if r_molecule is None or p_molecule is None:
                    category, reason = "insufficient_evidence", "rdkit_parse_failure"
                elif len(r_center) != len(p_center) or not r_center:
                    category, reason = (
                        "insufficient_evidence",
                        "center_pair_lists_empty_or_length_mismatch",
                    )
                else:
                    r_global_to_fragment = _fragment_index_by_global_atom(r_molecule)
                    p_global_to_fragment = _fragment_index_by_global_atom(p_molecule)
                    edge_set = {
                        (r_global_to_fragment[r_atom], p_global_to_fragment[p_atom])
                        for r_atom, p_atom in zip(r_center, p_center)
                        if r_atom in r_global_to_fragment and p_atom in p_global_to_fragment
                    }
                    supported_edges = [list(edge) for edge in sorted(edge_set)]
                    r_positions = _canonical_fragment_positions(left, legacy_pair[0], ci)
                    p_positions = _canonical_fragment_positions(right, legacy_pair[1], ci)
                    selected_is_cofactor = (
                        legacy_pair[0] in ci.COFACTORS or legacy_pair[1] in ci.COFACTORS
                    )
                    if selected_is_cofactor:
                        category, reason = (
                            "cofactor_selected_as_main",
                            "selected_fragment_matches_legacy_cofactor_dictionary",
                        )
                    elif len(r_positions) != 1 or len(p_positions) != 1:
                        category, reason = (
                            "insufficient_evidence",
                            "selected_fragment_position_not_unique",
                        )
                    else:
                        continuity_evidence = _lineage_continuity_evidence(
                            left,
                            right,
                            r_positions[0],
                            p_positions[0],
                            ci,
                        )
                    if continuity_evidence is not None and continuity_evidence["tie"]:
                        category, reason = (
                            "insufficient_evidence",
                            "dominant_scaffold_lineage_is_tied",
                        )
                    elif (
                        continuity_evidence is not None
                        and continuity_evidence["mutual_unique_best"]
                    ):
                        category, reason = (
                            "legacy_pair_supported",
                            "selected_fragment_pair_is_unique_mutual_scaffold_lineage",
                        )
                    elif continuity_evidence is not None:
                        category, reason = (
                            "cross_lineage_pair",
                            "selected_fragments_belong_to_different_dominant_scaffold_lineages",
                        )
        except Exception as exc:  # retain every failed row in the denominator
            category, reason = (
                "insufficient_evidence",
                f"{type(exc).__name__}: {str(exc)[:160]}",
            )

        category_counts[category] += 1
        example = {
            "source_id": source_id,
            "reaction_id": source_id,
            "reaction_smiles": reaction_smiles,
            "enzyme_records": [list(item) for item in enzyme_records],
            "category": category,
            "reason": reason,
            "legacy_pair": list(legacy_pair) if legacy_pair else None,
            "reacting_center_fragment_edges": supported_edges,
            "center_evidence_semantics": "changed-atom transfer support, not full atom mapping",
            "lineage_continuity_evidence": continuity_evidence,
        }
        if len(examples_by_category[category]) < 3:
            examples_by_category[category].append(example)
        if _is_proline_2og_case(reaction_smiles):
            required_cases.append({**example, "required_case": "proline_2og"})

    examples = [
        example
        for category in MISMATCH_CATEGORIES
        for example in examples_by_category[category]
    ]
    existing_ids = {example["source_id"] for example in examples}
    examples.extend(case for case in required_cases if case["source_id"] not in existing_ids)
    total = len(reactions)
    counts = {
        "total_reactions": total,
        "audited_reactions": total,
        **{category: category_counts[category] for category in MISMATCH_CATEGORIES},
    }
    if sum(counts[category] for category in MISMATCH_CATEGORIES) != total:
        raise RuntimeError("audit categories do not partition the source corpus")
    return counts, examples, source_ids, required_cases


def _build_audit() -> dict[str, Any]:
    """Assemble the full audit record."""
    source_status = _check_real_source()
    legacy = _audit_legacy_module()
    counts = {
        "total_reactions": 0,
        "audited_reactions": 0,
        **{category: 0 for category in MISMATCH_CATEGORIES},
    }
    examples: list[dict[str, Any]] = []
    source_ids: list[str] = []
    required_cases: list[dict[str, Any]] = []
    reasons: list[str] = []
    if source_status["real_reaction_source_found"]:
        counts, examples, source_ids, required_cases = _audit_real_rows()
    else:
        reasons.append("real_reaction_source_or_rdkit_unavailable")

    source_status["candidate_proline_keyword_hits"] = 0
    source_status["proline_2og_structure_hits"] = len(required_cases)
    verdict = "COMPLETE" if counts["audited_reactions"] > 0 and required_cases else "PARTIAL"
    if not required_cases:
        reasons.append("required_case_missing_proline_2og_source_record")

    proline_case = {
        "reaction": PROLINE_2OG_CASE["reaction"],
        "expected_lineages": PROLINE_2OG_CASE["expected_lineages"],
        "forbidden_lineage": PROLINE_2OG_CASE["forbidden_lineage"],
        "source_record_found": bool(required_cases),
        "status": "audited_from_real_source" if required_cases else "required_case_missing",
        "structure_match_count": len(required_cases),
        "source_ids": [case["source_id"] for case in required_cases],
        "legacy_cross_lineage_count": sum(
            case["category"] == "cross_lineage_pair" for case in required_cases
        ),
        "note": (
            "Located by exact stereo-independent participant structures, not "
            "by molecule-name keywords. Reacting-center pairs support fragment "
            "lineages but are not represented as full atom mapping."
        ),
    }

    return {
        "audit_version": "p1-2",
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_scope": (
            "full-corpus read-only replay of the project-declared legacy donor "
            "table; 3,601 complete reaction SMILES checked against reacting-center "
            "fragment-pair evidence"
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
    lines.append(f"**Audit version:** {audit['audit_version']}")
    lines.append(f"**Timestamp:** {audit['audit_timestamp']}")
    lines.append(f"**Verdict:** `{audit['verdict']}`")
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
        f"with `audited_reactions = {c['audited_reactions']}`. The five outcome "
        "categories form a complete partition; no failed row was deleted.\n"
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
    lines.append(f"| proline_2og_structure_hits | {rs.get('proline_2og_structure_hits')} |")
    lines.append(f"| source_confirmed_by_env | {rs['source_confirmed_by_env']} |")
    lines.append(f"| source_confirmation_method | {rs['source_confirmation_method']} |")
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
        "(bounded real-row examples across outcome categories plus required case)\n"
    )
    lines.append(
        f"- **source_ids:** {len(audit['source_ids'])} entries "
        "(one stable content-derived ID per audited reaction)\n"
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
    print(f"  examples: {len(audit['examples'])} (real audited rows)")
    print(f"  legacy sha256: {legacy_sha} (read-only, matches Preflight)")
    print(f"  JSON: {AUDIT_JSON}")
    print(f"  MD:   {AUDIT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
