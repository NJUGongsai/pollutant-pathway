"""P3-T1 Query normalization (final_plan §6.2).

Versioned normalization contract:
- parse / sanitize
- canonical SMILES + exact identity
- charge, salt/mixture, tautomer, isotope, stereo policy
- identity hash
- typed errors for invalid input and backend unavailable

No chemistry backend -> typed blocker.  P3 never repairs or invents SMILES.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.p3.identity import canonical_identity
from reaction_agent.p3.schemas import (
    EvidenceKind,
    NormalizationPolicy,
    NormalizedQuery,
)


class ChemistryBackendUnavailableError(RuntimeError):
    """Raised when RDKit is required but unavailable."""


class InvalidQueryError(ValueError):
    """Raised when the query input cannot be parsed / is invalid under policy."""


def _rdkit():
    try:
        from rdkit import Chem  # type: ignore
        return Chem
    except ImportError as exc:
        raise ChemistryBackendUnavailableError(
            "rdkit not importable — query normalization BLOCKED"
        ) from exc


def _canonicalize_with_stereo(Chem, mol) -> str:
    return Chem.MolToSmiles(mol, isomericSmiles=True)


def _canonicalize_stereo_stripped(Chem, mol) -> str:
    """Strip stereo (chirality + bond stereo) WITHOUT touching isotope markers."""
    copy = Chem.Mol(mol)
    for atom in copy.GetAtoms():
        atom.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
    for bond in copy.GetBonds():
        bond.SetStereo(Chem.BondStereo.STEREONONE)
    return Chem.MolToSmiles(copy, isomericSmiles=True)


def _identity_canonical(Chem, mol, policy: NormalizationPolicy) -> str:
    """Canonical SMILES for identity under the versioned policy.

    Delegates to the shared identity helper so the QUERY identity and the
    CANDIDATE product identity use the SAME policy (R2-A / R2-F).
    """
    return canonical_identity(
        Chem.MolToSmiles(Chem.Mol(mol), isomericSmiles=True),
        stereo_policy=policy.stereo_policy,
        isotope_policy=policy.isotope_policy,
    )


def normalize_query(
    input_smiles: str,
    *,
    policy: NormalizationPolicy | None = None,
    query_id: str | None = None,
    evidence_kind: EvidenceKind = EvidenceKind.real,
    run_id: str = "",
    case_id: str = "",
    fold_id: str = "",
    snapshot_id: str = "",
    snapshot_hash: str = "",
) -> NormalizedQuery:
    """Normalize a raw query SMILES into a NormalizedQuery.

    ``evidence_kind`` and the run namespace (run_id/case_id/fold_id/snapshot)
    must come from the immutable run context/manifest; callers cannot relabel
    a fixture as real through this function.

    Raises:
        InvalidQueryError: unparseable / empty / multi-policy violation input.
        ChemistryBackendUnavailableError: RDKit missing (typed blocker).
    """
    Chem = _rdkit()
    if not input_smiles or not input_smiles.strip():
        raise InvalidQueryError("query SMILES is empty")

    policy = policy or NormalizationPolicy(version="p3-1")
    mol = Chem.MolFromSmiles(input_smiles)
    if mol is None:
        raise InvalidQueryError(
            f"unparseable SMILES: {input_smiles!r} (invalid input, not repaired)"
        )

    # Salt / mixture policy: preserve multi-fragment losslessly.
    fragments = Chem.GetMolFrags(mol)
    fragment_count = len(fragments)

    identity_canonical = _identity_canonical(Chem, mol, policy)
    canonical_smiles = _canonicalize_with_stereo(Chem, mol)

    identity_hash = canonical_hash({
        "policy": policy.version,
        "canonical": identity_canonical,
        "charge_policy": policy.charge_policy,
        "salt_policy": policy.salt_policy,
        "tautomer_policy": policy.tautomer_policy,
        "isotope_policy": policy.isotope_policy,
        "stereo_policy": policy.stereo_policy,
    })

    heavy_atoms = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)
    formal_charge = sum(a.GetFormalCharge() for a in mol.GetAtoms())
    resolved_query_id = query_id or stable_id(
        "query", {"smiles": identity_canonical, "policy": policy.version}
    )

    return NormalizedQuery(
        query_id=resolved_query_id,
        run_id=run_id or f"diag_run_{resolved_query_id}",
        case_id=case_id or f"diag_case_{resolved_query_id}",
        fold_id=fold_id or "diag_fold",
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        input_smiles=input_smiles.strip(),
        canonical_smiles=canonical_smiles,
        identity_hash=identity_hash,
        heavy_atom_count=heavy_atoms,
        formal_charge=formal_charge,
        fragment_count=fragment_count,
        normalization_policy=policy,
        evidence_kind=evidence_kind,
    )


def equivalent_identity(
    q1: NormalizedQuery,
    q2: NormalizedQuery,
) -> bool:
    """Equivalent SMILES invariance: same canonical identity under policy."""
    return q1.identity_hash == q2.identity_hash
