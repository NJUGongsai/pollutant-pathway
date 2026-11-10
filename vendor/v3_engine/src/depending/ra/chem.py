"""Chemistry helpers over RDKit — deterministic canonicalisation + fingerprints."""
import logging

from rdkit import Chem, DataStructs
from rdkit.Chem import rdMolDescriptors

logger = logging.getLogger(__name__)


class ChemParseError(Exception):
    """Raised when a molecule cannot be parsed (fail-closed)."""


def parse_mol(smiles: str):
    """Parse SMILES into an RDKit mol; raise ChemParseError on failure."""
    if not isinstance(smiles, str) or not smiles.strip():
        raise ChemParseError(f"empty smiles: {smiles!r}")
    mol = Chem.MolFromSmiles(smiles)  # isomeric syntax honoured by default
    if mol is None:
        raise ChemParseError(f"unparseable smiles: {smiles!r}")
    return mol


def canonical_smiles(smiles: str, isomeric: bool = True) -> str:
    """Canonical (deterministic) SMILES for a single molecule."""
    mol = parse_mol(smiles)
    out = Chem.MolToSmiles(mol, isomericSmiles=isomeric, canonical=True)
    if not out:
        # isomeric=True failed on exotic stereo: retry without stereo info
        out = Chem.MolToSmiles(mol, isomericSmiles=False, canonical=True)
    if not out:
        raise ChemParseError(f"cannot canonicalise: {smiles!r}")
    return out


def component_smiles(multi_smiles: str) -> list:
    """Split a multi-component (dotted) SMILES into canonical, sorted components.

    The source order is intentionally destroyed: output is the deterministic
    sorted list of canonical component SMILES (degenerate duplicates kept).
    """
    comps = []
    for piece in multi_smiles.split("."):
        piece = piece.strip()
        if not piece:
            continue
        comps.append(canonical_smiles(piece))
    return sorted(comps)


def canonical_multi_smiles(components) -> str:
    """Join canonical, sorted component SMILES with '.' (deterministic)."""
    canon = sorted(canonical_smiles(c) for c in components)
    return ".".join(canon) if canon else ""


def split_reaction(equation: str):
    """Split 'A.B>>C.D' into (reactant_tokens, product_tokens), whitespace-trimmed.

    Tokens are returned verbatim (not canonicalised) so the caller decides.
    """
    if ">>" not in equation:
        raise ChemParseError(f"not a reaction equation: {equation!r}")
    lhs, rhs = equation.split(">>", 1)

    def tokens(side: str):
        return [t.strip() for t in side.split(".") if t.strip()]

    return tokens(lhs), tokens(rhs)


def canonical_reaction(reactants, products) -> str:
    """Deterministic canonical reaction SMILES: sorted sides, canonical comps."""
    r = canonical_multi_smiles(reactants)
    p = canonical_multi_smiles(products)
    return f"{r}>>{p}"


def morgan_fp(smiles: str, radius: int = 2, nbits: int = 2048):
    """Deterministic Morgan (ECFP-like) bit vector for a canonical SMILES."""
    mol = parse_mol(smiles)
    return rdMolDescriptors.GetMorganFingerprintAsBitVect(
        mol, radius=radius, nBits=nbits
    )


def tanimoto(fp_a, fp_b) -> float:
    if fp_a is None or fp_b is None:
        return 0.0
    return DataStructs.TanimotoSimilarity(fp_a, fp_b)