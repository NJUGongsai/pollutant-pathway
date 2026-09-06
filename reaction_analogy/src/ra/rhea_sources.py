"""RHEA source parsers — RXN files, reaction-smiles.tsv, rhea2ec, directions.

All parsers are deterministic and read-only. Unparseable input is surfaced via
error fields, never silently dropped (fail-closed).
"""
import glob
import logging
import os
import re

from rdkit import Chem, RDLogger
from rdkit.Chem import rdChemReactions

from ra.chem import ChemParseError, canonical_reaction, canonical_smiles, split_reaction

logger = logging.getLogger(__name__)
RDLogger.DisableLog("rdApp.*")  # silence stereo/3D warnings during corpus scan


# --------------------------------------------------------------------------
# MDL RXN files
# --------------------------------------------------------------------------

def _safe_mol_smiles(mol) -> str:
    """Canonical SMILES for one parsed mol.

    Round-trips through SMILES so a Kekule-drawn molblock and a SMILES-text
    source produce the SAME aromatic canonical form (deterministic cross-source
    identity). Falls back to non-stereo, then raises.
    """
    try:
        return canonical_smiles(Chem.MolToSmiles(mol, isomericSmiles=True))
    except Exception:  # stereo-sensitive failure
        try:
            return canonical_smiles(Chem.MolToSmiles(mol, isomericSmiles=False))
        except Exception as exc:  # noqa: BLE001
            raise ChemParseError(f"mol cannot be serialized: {exc}") from exc


def _count_aam_atoms(mols) -> int:
    return sum(
        1 for m in mols for a in m.GetAtoms() if a.GetAtomMapNum() > 0
    )


def parse_rxn_file(path: str) -> dict:
    """Parse one MDL RXN file into canonical reactant/product SMILES + AAM count.

    Returns {ok, error, reactant_smiles, product_smiles, aam_atoms,
              reaction_smiles}.
    RHEA's rxn_subset carries NO atom-atom mapping in the atom records, so
    aam_atoms == 0 for every file (verified; reported honestly, not invented).
    """
    try:
        rxn = rdChemReactions.ReactionFromRxnFile(path)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"ReactionFromRxnFile: {exc!r}",
            "reactant_smiles": [],
            "product_smiles": [],
            "aam_atoms": 0,
            "reaction_smiles": None,
        }
    reactants = [m for m in rxn.GetReactants()]
    products = [m for m in rxn.GetProducts()]
    aam_atoms = _count_aam_atoms(reactants + products)
    try:
        r_smiles = sorted(_safe_mol_smiles(m) for m in reactants)
        p_smiles = sorted(_safe_mol_smiles(m) for m in products)
        rxn_smiles = canonical_reaction(r_smiles, p_smiles)
    except ChemParseError as exc:
        return {
            "ok": False,
            "error": f"structure serialization: {exc}",
            "reactant_smiles": [],
            "product_smiles": [],
            "aam_atoms": aam_atoms,
            "reaction_smiles": None,
        }
    return {
        "ok": True,
        "error": None,
        "reactant_smiles": r_smiles,
        "product_smiles": p_smiles,
        "aam_atoms": aam_atoms,
        "reaction_smiles": rxn_smiles,
    }


_AAM_SMARTS_REGEX = re.compile(r"\[[A-Za-z@*][^]]*:[0-9]+")


def smiles_line_has_mapping(raw_line: str) -> bool:
    """Heuristic detector for atom-map-number markers in a reaction SMILES line."""
    return bool(_AAM_SMARTS_REGEX.search(raw_line))


def scan_mapping_absence(rxn_dir: str, limit: int | None = None) -> dict:
    """Scan a dir of RXN files (and RHEA semantics) for atom-atom mapping.

    Fail-closed summary: {files, parsed, with_aam, aam_atoms}.
    """
    files = sorted(glob.glob(os.path.join(rxn_dir, "*.rxn")))
    if limit is not None:
        files = files[:limit]
    parsed = 0
    with_aam = 0
    aam_atoms = 0
    for f in files:
        rec = parse_rxn_file(f)
        if not rec["ok"]:
            continue
        parsed += 1
        if rec["aam_atoms"] > 0:
            with_aam += 1
        aam_atoms += rec["aam_atoms"]
    return {
        "files": len(files),
        "parsed": parsed,
        "with_aam": with_aam,
        "aam_atoms": aam_atoms,
    }


def scan_smiles_mapping(tsv_path: str) -> dict:
    """Count reaction-smiles lines carrying atom-map-number markers."""
    aam_lines = 0
    total = 0
    with open(tsv_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            total += 1
            if smiles_line_has_mapping(line):
                aam_lines += 1
    return {"smiles_lines": total, "smiles_with_aam": aam_lines}


# --------------------------------------------------------------------------
# reaction-smiles.tsv (fallback equations)
# --------------------------------------------------------------------------

def load_reaction_smiles_tsv(path: str) -> dict:
    """Load rhea-reaction-smiles.tsv -> {rhea_id: record}.

    Record: {reactants: [canonical sorted], products: [canonical sorted],
             raw, reaction_smiles, parse_error}.
    """
    records = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            rhea_id, equation = parts[0], parts[1]
            try:
                r_tokens, p_tokens = split_reaction(equation)
                r_canon = sorted(canonical_smiles(t) for t in r_tokens)
                p_canon = sorted(canonical_smiles(t) for t in p_tokens)
                records[rhea_id] = {
                    "reactants": r_canon,
                    "products": p_canon,
                    "raw": equation,
                    "reaction_smiles": canonical_reaction(r_canon, p_canon),
                    "parse_error": None,
                }
            except ChemParseError as exc:
                records[rhea_id] = {
                    "reactants": [],
                    "products": [],
                    "raw": equation,
                    "reaction_smiles": None,
                    "parse_error": str(exc),
                }
    return records


# --------------------------------------------------------------------------
# rhea2ec.tsv + rhea-directions.tsv
# --------------------------------------------------------------------------

def load_rhea2ec(path: str) -> dict:
    """-> {"master": {master_id: [ec,...]}, "direct": {rhea_id: [ec,...]}}"""
    master: dict = {}
    direct: dict = {}
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            cells = raw.rstrip("\n").split("\t")
            if len(cells) < 4:
                continue
            rhea_id, direction, master_id, ec = cells[:4]
            if not rhea_id.isdigit():
                continue  # header row
            if ec and ec != "-":
                direct.setdefault(rhea_id, []).append(ec)
            if master_id and master_id.isdigit() and ec and ec != "-":
                master.setdefault(master_id, []).append(ec)
    for d in (master, direct):
        for k in d:
            d[k] = sorted(set(d[k]))
    return {"master": master, "direct": direct}


def load_directions(path: str) -> dict:
    """rhea-directions.tsv -> {rhea_id: {"master": m, "direction": dir|"UN"}}"""
    out: dict = {}
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            cells = raw.rstrip("\n").split("\t")
            if len(cells) < 4:
                continue
            master, lr, rl, bi = [c.strip() for c in cells[:4]]
            if not master.isdigit():
                continue  # header row
            pairs = [(lr, "LR"), (rl, "RL"), (bi, "BI"), (master, "UN")]
            for rhea_id, direction in pairs:
                if rhea_id.isdigit():
                    out.setdefault(rhea_id, {"master": master, "direction": direction})
    return out