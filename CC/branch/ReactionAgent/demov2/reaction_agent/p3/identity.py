"""Shared canonical identity policy (R2-A / R2-F).

The query identity and the candidate product identity MUST use the SAME
policy: stereo-agnostic but isotope-preserving by default.  A stereo-agnostic
identity must NEVER silently delete isotope markers.
"""
from __future__ import annotations

from rdkit import Chem  # type: ignore


def canonical_identity(
    smiles: str,
    *,
    stereo_policy: str = "ignore_stereo_for_identity",
    isotope_policy: str = "preserve_isotopes",
) -> str:
    """Canonical SMILES for identity under the versioned policy.

    - stereo_policy=ignore_stereo_for_identity strips chirality + bond stereo;
    - isotope_policy=preserve_isotopes keeps isotope markers in the identity.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return smiles
    if stereo_policy == "ignore_stereo_for_identity":
        copy = Chem.Mol(mol)
        for atom in copy.GetAtoms():
            atom.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
        for bond in copy.GetBonds():
            bond.SetStereo(Chem.BondStereo.STEREONONE)
        base = Chem.MolToSmiles(copy, isomericSmiles=True)
    else:
        base = Chem.MolToSmiles(Chem.Mol(mol), isomericSmiles=True)
    if isotope_policy == "preserve_isotopes":
        return base
    return Chem.MolToSmiles(Chem.MolFromSmiles(base), isomericSmiles=False)
