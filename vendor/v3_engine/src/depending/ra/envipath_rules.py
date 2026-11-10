"""enviPath track: atom-mapped reaction SMARKS rules (RA-M2).

templates.tsv.gz (286 rules) carries reaction SMARKS WITH atom-map numbers
(e.g. `[#8:7]([H])-[#6:1]([H])-...>>...`) — the domain-exact, mapped lineage
source the RHEA corpus lacks. source_substrates.json links each rule to its
real donor educts.

fail-closed, deterministic: unparseable rules / non-matching runs are counted,
never invented; all outputs sorted.
"""
import gzip
import json
import logging
from functools import lru_cache

from rdkit import Chem
from rdkit.Chem import rdChemReactions as R

from ra.chem import ChemParseError, canonical_smiles, parse_mol
from ra.io import sha256_text, stable_json_text

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_templates(path: str) -> list:
    """Load templates.tsv.gz -> sorted list of rule dicts (deterministic).

    Rule: {template_id, score, smarts, reactant_count, parse_error}.
    A rule that fails ReactionFromSmarts is kept with parse_error (fail-closed).
    """
    rules = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        header = None
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            cells = line.split("\t")
            if header is None:
                header = cells
                continue
            row = dict(zip(header, cells))
            template_id = row.get("TEMPLATE_ID", "")
            smarts = row.get("TEMPLATE", "")
            try:
                rxn = R.ReactionFromSmarts(smarts)
                reactant_count = len(rxn.GetReactants())
                parse_error = None
            except Exception as exc:  # noqa: BLE001 -- fail-closed ledger
                reactant_count = -1
                parse_error = f"{type(exc).__name__}: {exc}"
            rules.append(
                {
                    "template_id": template_id,
                    "score": row.get("SCORE", ""),
                    "smarts": smarts,
                    "reactant_count": reactant_count,
                    "parse_error": parse_error,
                }
            )
    return sorted(rules, key=lambda r: r["template_id"])


def load_substrate_map(json_path: str) -> dict:
    """Load source_substrates.json -> {template_id: [canonical donor educts]}."""
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = {}
    for key in sorted(data):
        entry = data[key]
        if not isinstance(entry, dict):
            continue
        educts = set()
        for s in entry.get("substrates") or []:
            try:
                educts.add(canonical_smiles(s))
            except ChemParseError as exc:
                logger.warning("envipath substrate unparseable %s: %s", s, exc)
        if educts:
            out[key] = sorted(educts)
    return out


# --------------------------------------------------------------------------
# rule application
# --------------------------------------------------------------------------

def _sanitize_to_smiles(mol) -> str | None:
    """Robust mol->canonical-smiles: sanitize, kekulize fallback, roundtrip."""
    for step in (
        lambda m: Chem.SanitizeMol(m),
        lambda m: Chem.Kekulize(m, clearAromaticFlags=True),
    ):
        try:
            step(mol)
            return Chem.MolToSmiles(mol, isomericSmiles=True)
        except Exception:  # noqa: BLE001
            continue
    try:  # last resort: unsanitized roundtrip through smiles
        return canonical_smiles(Chem.MolToSmiles(mol, isomericSmiles=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("sanitize failed: %r", exc)
        return None


def apply_rule(rule: dict, query_smiles: str, counter: dict | None = None) -> list:
    """Apply a single-reactant rule to one molecule; never raises.

    Returns sorted, de-duplicated canonical product SMILES. Run-levstatistics
    are accumulated into `counter` (optional) --
      pairs/applied/clean/raised/sanitize_failed/nomatch.
    RunReactants exceptions (AtomKekulizeException on aromatic smarts vs
    non-aromatic substrate) are counted as `raised` and yield no products.
    """
    if counter is not None:
        counter["pairs"] += 1
        counter["applied"] += 1
    if rule.get("reactant_count") != 1:
        return []
    if rule.get("parse_error") is not None:
        return []
    try:
        rxn = _reaction_from_smarts(rule["smarts"])
    except Exception:  # noqa: BLE001
        return []
    try:
        mol = parse_mol(query_smiles)
    except ChemParseError:
        return []
    try:
        outcomes = rxn.RunReactants((mol,))
    except Exception as exc:  # noqa: BLE001
        if counter is not None:
            counter["raised"] += 1
        logger.debug("rule %s raised on %s: %s", rule["template_id"], query_smiles, exc)
        return []

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
        if counter is not None:
            counter["clean"] += 1
    elif product_failures:
        if counter is not None:
            counter["sanitize_failed"] += 1
    elif counter is not None:
        counter["nomatch"] += 1
    return sorted(products)


def provenance_sha256(body: dict) -> str:
    return sha256_text(stable_json_text(body))


@lru_cache(maxsize=None)
def _reaction_from_smarts(smarts: str):
    """Cached ReactionFromSmarts (deterministic); raises for callers to guard."""
    return R.ReactionFromSmarts(smarts)