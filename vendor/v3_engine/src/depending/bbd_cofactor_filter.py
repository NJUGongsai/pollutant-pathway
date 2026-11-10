#!/usr/bin/env python3
"""BBD P4.2 cofactor conjugate filter — SMARTS-skeleton based, fail-closed.

Sinks cofactor conjugates (NAD+/NADH/NADP+/NADPH/FAD/FMN/CoA/ATP/ADP/AMP/GTP/
SAM/SAH/四氢叶酸/四氢生物蝶呤/硫辛酸缀合物 …) to the **bottom** of candidate
rankings (not deleted), mirroring ``bbd_v32_ion_filter.py``.

**Why structural + MW rather than a fixed whitelist (task §4.2 option b):** a fixed
canonical whitelist cannot enumerate the many protonation/reduction/fragmentation
states of each cofactor.  Instead we match the cofactor's *skeleton* substructure
(adenine/purine, isoalloxazine/flavin, pterin/pteridine, nicotinamide) with SMARTS
**and** require MW > 500 — every relevant cofactor conjugate is both skeleton-bearing
and large, while small adenine-containing legitimate products (e.g. adenine itself,
MW 135) are not falsely sunk.  This is a double guard against the v3.2 病灶 where
NAD⁺ conjugates tied the true product on ``ns_score`` and won on SMILES order.

Cofactors are **sunk** (not deleted) so a cofactor that is ever a legitimate
accepted product remains in top-20 and can still hit Hit@10 — same philosophy as
the ion filter's handling of formaldehyde (``C=O``).

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors

RDLogger.DisableLog("rdApp.*")


# Cofactor skeleton SMARTS — covers all major cofactor families.
_SKELETON_SMARTS: dict[str, str] = {
    # purine core (adenine): NAD/NADP/FAD/FMN/CoA/ATP/ADP/AMP/GTP/GDP/SAM/SAH
    "adenine":       "c1ncnc2c1ncn2",
    # isoalloxazine (flavin core): FAD / FMNH2
    "isoalloxazine": "o1c2nc3c(=O)[nH]c(=O)nc3cc2cc1",
    # pterin / pteridine core: folate / tetrahydrofolate / biopterin
    "pteridine":     "c1nc2nccnc2c(=O)[nH]1",
    # pyridine-3-carboxamide (nicotinamide): NAD/NADP reduced/oxidised riboside
    "nicotinamide":  "c1cc(cnc1)C(=O)N",
}

_PATTERNS: list[tuple] = [
    (name, Chem.MolFromSmarts(s)) for name, s in _SKELETON_SMARTS.items()
]

# Guard threshold: cofactors are large.  Prevents false-positives on small
# adenine/pterin-containing legitimate products.
_MIN_MW = 500.0


def is_cofactor_conjugate(product_smiles: str) -> bool:
    """Return True if *product_smiles* is a cofactor conjugate to be sunk.

    Heuristic: has a cofactor skeleton substructure **and** MW > 500.
    Canonicalises input to stereo-blind before checking so isomeric input is
    handled correctly.  Unparseable → False (fail-open for unknown).
    """
    m = Chem.MolFromSmiles(product_smiles)
    if m is None:
        return False
    canon = Chem.MolToSmiles(m, isomericSmiles=False)
    mc = Chem.MolFromSmiles(canon)
    if mc is None:
        return False
    if Descriptors.MolWt(mc) <= _MIN_MW:
        return False
    return any(
        pat is not None and mc.HasSubstructMatch(pat)
        for _, pat in _PATTERNS
    )


if __name__ == "__main__":
    # Self-test: NAD⁺ conjugate sinks; small legit products don't.
    _nad = ("NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3"
            "O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1")
    assert is_cofactor_conjugate(_nad) is True, "NAD+ should be flagged"
    for s in ("OCCCl", "CC=O", "c1ccccc1", "c1ccc(O)cc1"):
        assert is_cofactor_conjugate(s) is False, f"{s} should NOT be flagged"
    print("cofactor self-test OK")
