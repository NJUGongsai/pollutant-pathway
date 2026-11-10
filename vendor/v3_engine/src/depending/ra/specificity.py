"""Generalized (de-transductive) rule specificity — a pure function of the rule.

Replaces the transductive ``log2(83 / support)`` specificity of RA-RREF (which
counted how many of the 83 public blind parents a rule's reactant SMARTS matched
—— i.e. it encoded the benchmark's own query-set distribution, so it does NOT
generalise to unseen molecules).

The signal here is a **pure function of the reaction SMARTS / its parsed reactant
template** (plus, optionally, a frozen independent donor set — not used in the
default ``rank_gen`` build).  It NEVER reads the 83 blind parents and NEVER reads
any answer key.  Therefore deleting or replacing the 83-parent list leaves these
values bit-identical (see ``tests/test_specificity.py::test_83_independence``).

Two chemistry-meaningful axes are combined (see ``reports/RA_MG_RANKING_KEY.md``):

1. **SMARTS constraint degree** —— how *tightly* the reactant pattern pins down the
   atoms it will match.  Intuition: a query that demands a specific recursive
   environment, a halogen, an explicit H-count / connectivity / formal charge
   matches far fewer molecules than a bare aromatic-carbon ring, and is therefore
   a *characteristic* (rare) transformation rather than *generic* noise.

       constraint(r) = n_rec + 2*n_hal + n_hcnt + 2*n_conn + 2*n_charge

   with per-feature weights justified in the ranking key (halogen demand,
   connectivity and formal charge are the tightest; an H-count is a single
   positional pin; recursion is one environment constraint).

2. **Reaction-centre complexity** —— the fraction of the reactant pattern that the
   rule actually changes.  A rule that surgically modifies one substituent on a big
   scaffold is a narrow transfer; a rule that breaks a ring into two fragments is a
   distinctive transformation.

       complexity(r) = (n_changed + n_added + n_removed) / n_atoms

   The centre is located from the SMIRKS's own atom-mapping numbers (enviPath
   templates are natively atom-mapped): a mapped atom whose query/smarts, formal
   charge or bond (order, neighbour map-number) signature changes across the arrow
   counts as changed; unmapped heavy atoms on each side count as removed / added.

The scalar is

    specificity(r) = log1p(constraint) + 0.50*n_hetero

where ``n_hetero`` counts non-carbon, non-hydrogen heavy atoms in the pattern (a
pattern built around N/O/S/P is a priori more selective).  The ratio ``complexity``
is computed and exported for audit, but its weight is 0 in the released formula:
dev-44 calibration showed the ratio is anti-informative (it inflates tiny generic
functional-group rules such as alcohol→aldehyde, whose centre is a large fraction
of a 3-atom pattern), so it is deliberately not scored.  All arithmetic is
deterministic and depends on nothing but ``smirks``.
"""
from __future__ import annotations

import math
import re
from typing import Dict, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem

# --------------------------------------------------------------------------- #
# feature extraction
# --------------------------------------------------------------------------- #

_HAL_RE = re.compile(r"Cl|Br|#9|#17|#35|#53")
_HCNT_RE = re.compile(r"H\d")
_CONN_RE = re.compile(r"[XD]\d")

# constraint feature weights (pre-registered; see reports/RA_MG_RANKING_KEY.md)
W_REC = 1
W_HAL = 2
W_HCNT = 1
W_CONN = 2
W_CHARGE = 2


def _reactant_template(smirks: str):
    """Return the single reactant template mol of a SMIRKS, or None if not 1-reactant."""
    if ">>" not in smirks:
        return None
    rxn = AllChem.ReactionFromSmarts(smirks)
    if rxn is None or rxn.GetNumReactantTemplates() != 1:
        return None
    return rxn


def _bond_signature(mol, atom) -> Tuple:
    """Sorted (bond-order, neighbour map-number) multiset — pure, deterministic."""
    out = []
    for b in atom.GetBonds():
        nb = mol.GetAtomWithIdx(b.GetOtherAtomIdx(atom.GetIdx()))
        out.append((round(b.GetBondTypeAsDouble(), 1), nb.GetAtomMapNum()))
    return tuple(sorted(out))


def _atom_env(mol, atom) -> Tuple:
    """The identity used to detect 'this atom is the reaction centre'."""
    return (
        atom.GetSmarts(),          # query/smarts incl. element, aromaticity, map num
        atom.GetFormalCharge(),
        _bond_signature(mol, atom),
    )


def smarts_specificity_features(smirks: str) -> Dict[str, object]:
    """Compute the de-transductive specificity features of one SMIRKS rule.

    Pure function of ``smirks``: no benchmark parents, no answer key.  Returns a
    deterministic dict (all ints / floats) keyed by the feature names below, or
    ``{"error": "..."}`` when the SMIRKS does not parse as a single-reactant rule
    (fail-closed).
    """
    rxn = _reactant_template(smirks)
    if rxn is None:
        return {"error": "unparseable_or_not_single_reactant"}

    lhs = smirks.split(">>", 1)[0]
    r = rxn.GetReactants()[0]
    p = rxn.GetProducts()[0]

    n_atoms = r.GetNumAtoms()
    n_rec = lhs.count("$(")
    n_hal = 0
    n_hcnt = 0
    n_conn = 0
    n_charge = 0
    n_hetero = 0
    for a in r.GetAtoms():
        s = a.GetSmarts()
        if _HAL_RE.search(s):
            n_hal += 1
        if _HCNT_RE.search(s):
            n_hcnt += 1
        if _CONN_RE.search(s):
            n_conn += 1
        if a.GetFormalCharge() != 0:
            n_charge += 1
        if a.GetAtomicNum() not in (0, 6, 1):
            n_hetero += 1

    rmap = {a.GetAtomMapNum(): a for a in r.GetAtoms() if a.GetAtomMapNum() > 0}
    pmap = {a.GetAtomMapNum(): a for a in p.GetAtoms() if a.GetAtomMapNum() > 0}
    n_changed = 0
    for m in set(rmap) & set(pmap):
        if _atom_env(r, rmap[m]) != _atom_env(p, pmap[m]):
            n_changed += 1
    n_added = sum(1 for a in p.GetAtoms() if a.GetAtomMapNum() == 0)
    n_removed = sum(1 for a in r.GetAtoms() if a.GetAtomMapNum() == 0)
    center = n_changed + n_added + n_removed

    constraint = (
        W_REC * n_rec
        + W_HAL * n_hal
        + W_HCNT * n_hcnt
        + W_CONN * n_conn
        + W_CHARGE * n_charge
    )
    complexity = center / max(1, n_atoms)

    return {
        "n_atoms": n_atoms,
        "n_rec": n_rec,
        "n_hal": n_hal,
        "n_hcnt": n_hcnt,
        "n_conn": n_conn,
        "n_charge": n_charge,
        "n_hetero": n_hetero,
        "n_changed": n_changed,
        "n_added": n_added,
        "n_removed": n_removed,
        "center": center,
        "constraint": constraint,
        "complexity": round(complexity, 6),
    }


# component weights (pre-registered; see reports/RA_MG_RANKING_KEY.md)
W_N_HETERO = 0.50
W_COMPLEXITY = 0.00   # computed for audit only; ratio is anti-informative (dev-44)


def specificity(smirks: str) -> Optional[float]:
    """Scalar de-transductive specificity of one SMIRKS rule (None = fail-closed)."""
    f = smarts_specificity_features(smirks)
    if "error" in f:
        return None
    return (
        math.log1p(f["constraint"])
        + W_N_HETERO * f["n_hetero"]
        + W_COMPLEXITY * f["complexity"]
    )


def specificity_map(smirks_by_tid: Dict[str, str]) -> Dict[str, Optional[float]]:
    """template_id -> scalar specificity, computed over the rules themselves only."""
    return {tid: specificity(smirks_by_tid[tid]) for tid in sorted(smirks_by_tid)}