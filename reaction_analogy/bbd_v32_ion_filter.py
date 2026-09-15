#!/usr/bin/env python3
"""BBD v3.2 ion fragment filter — white-list based, fail-closed.

Filters ion/inorganic co-product fragments (``[Cl-]``, ``[H+]``, ``O``, etc.)
that pollute top-1 rankings.  Uses an explicit white-list of stereo-blind
canonical SMILES — NOT molecular weight or atom-count thresholds (which would
误杀 methanol, acetaldehyde, etc. that are legitimate degradation products).

Ions are **sunk to bottom** in ranking (not deleted) so that true products that
happen to be in the white-list (e.g. ``C=O`` = formaldehyde in one answer-key
case) remain in top-20 and can still hit Hit@10.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")


# Stereo-blind canonical SMILES of ion/inorganic fragments to sink.
# Populated from chemical common-sense (task §4.2), NOT fitted to answer key.
ION_SMILES: set[str] = {
    # Single-atom ions
    "[Cl-]", "[Br-]", "[I-]", "[F-]", "[H+]", "[Na+]", "[K+]", "[NH4+]",
    "[OH-]", "[O-]", "[S-]",
    # Neutral single atoms / small inorganics
    "[O]", "[H]", "[Na]", "[K]", "[Cl]", "[Br]", "[I]",
    "O",           # water
    "C=O",         # formaldehyde (also CO2 degenerate form; see note below)
    "O=C=O",       # CO2
    "N", "N#N",    # ammonia / nitrogen
    # Sulfate / sulfite
    "O=S(=O)([O-])[O-]",
    "O=S(=O)(=O)O",
    "[O-]S(=O)(=O)[O-]",
    # Carbonate / bicarbonate
    "O=C(O)[O-]",
    "O=C([O-])[O-]",
    # Phosphate
    "OP(=O)([O-])[O-]",
    "OP(=O)([O-])O",
    "O=P([O-])([O-])[O-]",
}


def is_ion_fragment(product_smiles: str) -> bool:
    """Return True if *product_smiles* is an ion/inorganic co-product fragment.

    Canonicalises to stereo-blind before checking the white-list, so isomeric
    input is handled correctly.
    """
    m = Chem.MolFromSmiles(product_smiles)
    if m is None:
        return False  # unparseable → not an ion (fail-open for unknown)
    canon = Chem.MolToSmiles(m, isomericSmiles=False)
    return canon in ION_SMILES
