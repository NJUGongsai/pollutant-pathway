"""RA-3 RHEA core+change rule derivation + transfer to X + merged pool.

Design: reports/RA_3_DESIGN.md (pre-registered, commit 7eb7ee0).

Deterministic, fail-closed, answer-isolated. Derives a mapped reaction
transform from each RHEA single-reactant reaction using MCS as the unchanged
CORE and explicitly keeping the changed region (A\\core leaving, B\\core
entering) — the reaction centre is never silently dropped by the MCS. Every
rule must pass the ROUNDTRIP gate (applying the rule to donor A reproduces
canonical B), then transfers to each blind parent X by substructure match +
RunReactants with robust sanitize (kekulize fallback + canonical roundtrip),
mirroring envipath_rules.apply_rule. The merged pool replaces the old
RHEA-verbatim `rhea` rows with `rhea-transfer` candidates.
"""
import hashlib
import json
import logging

from rdkit import Chem
from rdkit.Chem import rdChemReactions as R, rdFMCS

from ra import chem  # noqa: F401
from ra.chem import ChemParseError, canonical_smiles, parse_mol
from ra.io import sha256_text, stable_json_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# derivation
# ---------------------------------------------------------------------------

def _canon_multi(components: list) -> str:
    """Deterministic canonical multi-component SMILES (sorted, dotted)."""
    try:
        return chem.canonical_multi_smiles(components)
    except ChemParseError:
        return None


def _mcs(a, b):
    """MCS(A,B) = unchanged CORE; CompareElements + CompareAny bonds."""
    return rdFMCS.FindMCS(
        [a, b],
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareAny,
        ringMatchesRingOnly=True,
        completeRingsOnly=False,
        timeout=10,
    )


def _map_core_atoms(mol, core_match: tuple) -> None:
    """Set atom map numbers from the MCS core match (donor/product side)."""
    for core_idx, atom_idx in enumerate(core_match):
        mol.GetAtomWithIdx(atom_idx).SetAtomMapNum(core_idx + 1)
    # leaving / entering atoms get unique maps (beyond core)
    n_core = len(core_match)
    for atom in mol.GetAtoms():
        if atom.GetAtomMapNum() == 0:
            atom.SetAtomMapNum(n_core + atom.GetIdx() + 1)


def _build_mapped_reaction(a_mapped, b_mapped, a, b, core_match_a, core_match_b):
    """Construct a ChemicalReaction from mapped A/B; return (rxn, smarts)."""
    rxn = R.ChemicalReaction()
    rxn.AddReactantTemplate(a_mapped)
    rxn.AddProductTemplate(b_mapped)
    rxn.Initialize()
    smarts = R.ReactionToSmarts(rxn)
    return rxn, smarts


def derive_rules(rows: list) -> tuple:
    """Derive rules from RHEA single-reactant corpus rows.

    Returns (rules, stats). Deterministic; fail-closed (no MCS -> no rule).
    stats-ledger keys: n_records, n_parse_failed, n_noop, n_core_too_small,
    n_mcs_failed, n_build_failed, n_smarts_unparseable, n_roundtrip_mismatch,
    n_dedup, n_rules.
    """
    stats = {
        "n_records": len(rows),
        "n_parse_failed": 0, "n_noop": 0, "n_core_too_small": 0,
        "n_mcs_failed": 0, "n_build_failed": 0, "n_smarts_unparseable": 0,
        "n_roundtrip_mismatch": 0, "n_dedup": 0, "n_rules": 0,
        "skip_reasons": {"parse_failed": 0, "noop": 0, "core_lt_2": 0,
                         "mcs_failed": 0, "build_failed": 0,
                         "smarts_unparseable": 0, "roundtrip": 0, "dedup": 0},
    }
    rules = []
    seen_smarts = set()
    for rec in sorted(rows, key=lambda r: r["record_id"]):
        donors = rec.get("donor_components") or []
        products = rec.get("product_components") or []
        if len(donors) != 1 or len(products) < 1:
            continue
        a_smi = donors[0]
        try:
            a = parse_mol(a_smi)
            b_components = []
            for p in products:
                b_components.append(canonical_smiles(p))
            b_smi = ".".join(sorted(b_components))
            b = Chem.MolFromSmiles(b_smi)
            if b is None:
                raise ChemParseError(f"unparseable product: {b_smi!r}")
        except ChemParseError:
            stats["skip_reasons"]["parse_failed"] = stats["skip_reasons"].get("parse_failed", 0) + 1
            stats["n_parse_failed"] += 1
            continue
        b = Chem.MolFromSmiles(".".join(sorted(b_components)))

        # NO-OP: same molecule both sides -> reaction does nothing
        if canonical_smiles(a_smi) == _canon_multi(products):
            stats["skip_reasons"]["noop"] = stats["skip_reasons"].get("noop", 0) + 1
            stats["n_noop"] += 1
            continue

        # --- MCS core ---------------------------------------------------------
        try:
            mcs = _mcs(a, b)
        except Exception:  # noqa: BLE001 -- fail-closed ledger
            stats["skip_reasons"]["mcs_failed"] += 1
            stats["n_mcs_failed"] += 1
            continue
        if mcs is None or mcs.numAtoms < 2:
            stats["skip_reasons"]["core_lt_2"] += 1
            stats["n_core_too_small"] += 1
            continue
        core_query = Chem.MolFromSmarts(mcs.smartsString)
        if core_query is None:
            stats["skip_reasons"]["mcs_failed"] += 1
            stats["n_mcs_failed"] += 1
            continue
        match_a = a.GetSubstructMatch(core_query)
        match_b = b.GetSubstructMatch(core_query)
        if not match_a or not match_b:
            stats["skip_reasons"]["mcs_failed"] += 1
            stats["n_mcs_failed"] += 1
            continue

        # --- reaction-aware mapping: core first, then leaving/entering ---------
        a_map = Chem.Mol(a)
        b_map = Chem.Mol(b)
        _map_core_atoms(a_map, match_a)
        _map_core_atoms(b_map, match_b)

        try:
            rxn, smarts = _build_mapped_reaction(a_map, b_map, a, b, match_a, match_b)
            # re-parse gate
            r2 = R.ReactionFromSmarts(smarts)
            _ = r2.GetNumReactantTemplates()
        except Exception:  # noqa: BLE001
            stats["skip_reasons"]["smarts_unparseable"] = stats["skip_reasons"].get("smarts_unparseable", 0) + 1
            stats["n_smarts_unparseable"] += 1
            continue

        # --- roundtrip gate: rule applied to A must reproduce canonical B -------
        try:
            outcomes = rxn.RunReactants((a,))
            products_out = set()
            ok = True
            for product_set in outcomes:
                for product_mol in product_set:
                    try:
                        smi = Chem.MolToSmiles(product_mol, canonical=True)
                        products_out.add(smi)
                    except Exception:  # noqa: BLE001
                        ok = False
            if not ok or ".".join(sorted(products_out)) != b_smi:
                stats["skip_reasons"]["roundtrip"] = stats["skip_reasons"].get("roundtrip", 0) + 1
                stats["n_roundtrip_mismatch"] += 1
                continue
        except Exception:  # noqa: BLE001
            stats["skip_reasons"]["roundtrip"] = stats["skip_reasons"].get("roundtrip", 0) + 1
            stats["n_roundtrip_mismatch"] += 1
            continue

        # dedup identical SMARTS (keep first record_id)
        if smarts in seen_smarts:
            stats["skip_reasons"]["dedup"] = stats["skip_reasons"].get("dedup", 0) + 1
            stats["n_dedup"] += 1
            continue
        seen_smarts.add(smarts)

        rules.append({
            "record_id": rec["record_id"],
            "source_id": rec.get("source_id"),
            "ec": rec.get("ec"),
            "donor_smiles": a_smi,
            "product_smiles": b_smi,
            "smarts": smarts,
            "core_size": mcs.numAtoms,
            "n_reactant_components": 1,
            "n_product_components": len(products),
            "roundtrip": True,
            "provenance_sha256": sha256_text(stable_json_text({
                "record_id": rec["record_id"], "donor": a_smi,
                "product": b_smi, "smarts": smarts,
            })),
        })
        stats["n_rules"] += 1

    rules.sort(key=lambda r: r["record_id"])
    return rules, stats


# ---------------------------------------------------------------------------
# transfer to X
# ---------------------------------------------------------------------------

def _sanitize_to_smiles(mol):
    """Robust mol->canonical smiles: sanitize, kekulize fallback, roundtrip."""
    for step in (
        lambda m: Chem.SanitizeMol(m),
        lambda m: Chem.Kekulize(m, clearAromaticFlags=True),
    ):
        try:
            step(mol)
            return Chem.MolToSmiles(mol, isomericSmiles=True)
        except Exception:  # noqa: BLE001
            continue
    try:
        return canonical_smiles(Chem.MolToSmiles(mol, isomericSmiles=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("sanitize failed: %r", exc)
        return None


def transfer_to_x(rules: list, q_map: dict) -> tuple:
    """Apply each derived rule to each blind parent X.

    q_map: {case_id: canonical X smiles}. Never raises; failures are counted
    (`nomatch` / `raised`), never fabricated. Returns (transfer_records, stats).
    """
    stats = {"pairs": 0, "applied": 0, "clean": 0, "raised": 0,
             "sanitize_failed": 0, "nomatch": 0}
    records = []
    for case_id in sorted(q_map):
        x_smi = q_map[case_id]
        try:
            xmol = parse_mol(x_smi)
        except ChemParseError:
            continue
        for rule in rules:
            stats["pairs"] += 1
            stats["applied"] += 1
            try:
                rxn = R.ReactionFromSmarts(rule["smarts"])
                pre = rxn.GetReactantTemplate(0)
                if not xmol.HasSubstructMatch(pre):
                    stats["nomatch"] += 1
                    continue
                outcomes = rxn.RunReactants((xmol,))
            except Exception:  # noqa: BLE001
                stats["raised"] += 1
                continue
            products = set()
            product_failures = 0
            for product_set in outcomes:
                for product_mol in product_set:
                    smi = _sanitize_to_smiles(product_mol)
                    if smi:
                        products.add(smi)
                    else:
                        product_failures += 1
            if products:
                stats["clean"] += 1
            elif product_failures:
                stats["sanitize_failed"] += 1
            else:
                stats["nomatch"] += 1
            for cand in sorted(products):
                body = {
                    "case_id": case_id,
                    "x_smiles": x_smi,
                    "candidate_smiles": cand,
                    "source_id": rule["record_id"],
                    "rule_ref": rule["record_id"],
                    "rule_smarts": rule["smarts"],
                    "donor_ref": rule["record_id"],
                    "donor_smiles": rule["donor_smiles"],
                    "mapping_status": "in-smarts",
                    "provenance_sha256": sha256_text(stable_json_text({
                        "case_id": case_id, "rule": rule["record_id"],
                        "candidate": cand,
                    })),
                    "lineage": {
                        "donor_ref": rule["record_id"],
                        "rule_ref": rule["record_id"],
                        "product_B_ref": rule["product_smiles"],
                        "x_ref": case_id,
                    },
                }
                records.append(body)
    records.sort(key=lambda r: (r["case_id"], r["candidate_smiles"], r["rule_ref"]))
    return records, stats


# ---------------------------------------------------------------------------
# merged pool
# ---------------------------------------------------------------------------

def build_merged_pool(env_rows: list, transfer: list) -> tuple:
    """Merged pool: enviPath track (frozen rows with envipath track) +
    rhea-transfer candidates; the old RHEA-verbatim `rhea` rows are REPLACED
    (never emitted). source_track ∈ {envipath, rhea-transfer,
    envipath+rhea-transfer}.

    env_rows: retrieval_v2/pool_union.jsonl rows with 'envipath' in track.
    transfer: rhea-transfer records {case_id, candidate_smiles}.
    """
    env_by_case = {}
    for r in env_rows:
        env_by_case.setdefault(r["case_id"], set()).add(r["candidate_smiles"])
    tr_by_case = {}
    for r in transfer:
        tr_by_case.setdefault(r["case_id"], set()).add(r["candidate_smiles"])

    all_cases = sorted(set(env_by_case) | set(tr_by_case))
    rows = []
    stats_cases = []
    for case_id in all_cases:
        env = env_by_case.get(case_id, set())
        tr = tr_by_case.get(case_id, set())
        seen = set()
        case_rows = []
        for cand in sorted(env | tr):
            if cand in seen:
                continue
            seen.add(cand)
            in_env = cand in env
            in_tr = cand in tr
            track = ("envipath" if in_env else "") + ("rhea-transfer" if in_tr else "")
            if in_env and in_tr:
                track = "envipath+rhea-transfer"
            case_rows.append({"case_id": case_id, "candidate_smiles": cand,
                              "source_track": track})
        rows.extend(case_rows)
        stats_cases.append({"case_id": case_id,
                            "candidates": [r["candidate_smiles"] for r in case_rows]})
    rows.sort(key=lambda r: (r["case_id"], r["candidate_smiles"]))

    n_with = sum(1 for s in stats_cases if s["candidates"])
    coverage = {
        "cases_total": len(stats_cases),
        "cases_with_candidate": n_with,
        "coverage": round(n_with / len(stats_cases), 6) if stats_cases else 0.0,
        "n_candidates_total": len(rows),
    }
    return rows, coverage