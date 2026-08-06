"""P3-T5 Transformation-conditioned site enumeration (final_plan §6.6).

- transform precondition matching against X
- stable site IDs
- symmetry dedup (automorphism-equivalent sites collapse to one)
- ambiguity groups (multiple distinct sites are all retained)
- local environment + failed preconditions with structured reasons
"""
from __future__ import annotations

from rdkit import Chem  # type: ignore

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.p3.schemas import (
    ConditionedSite,
    NormalizedQuery,
    SiteEligibility,
    SitePrecondition,
    StrictTransformation,
)


def _rdkit_chem():
    return Chem


class SitePreconditionError(ValueError):
    """Typed error: an unknown precondition kind fails closed (R2-E)."""


def _precondition_matches(
    atom,
    precondition: SitePrecondition,
) -> bool:
    kind = precondition.kind
    params = precondition.params
    if kind == "heavy_atom_degree":
        degree = sum(1 for n in atom.GetNeighbors() if n.GetAtomicNum() > 1)
        return degree == params.get("degree")
    if kind == "h_count":
        return atom.GetTotalNumHs() == params.get("h")
    if kind == "formal_charge":
        return atom.GetFormalCharge() == params.get("charge")
    if kind == "element_neighbor":
        counts: dict[str, int] = {}
        for n in atom.GetNeighbors():
            if n.GetAtomicNum() > 1:
                counts[n.GetSymbol()] = counts.get(n.GetSymbol(), 0) + 1
        return counts.get(params.get("element")) == params.get("count")
    # Unknown precondition kind: TYPED fail closed (never silent False).
    raise SitePreconditionError(f"unknown precondition kind: {kind!r}")


def enumerate_sites(
    transform: StrictTransformation,
    query: NormalizedQuery,
    *,
    query_id: str = "",
    case_id: str = "",
) -> list[ConditionedSite]:
    """Enumerate all conditioned sites for X under the transform.

    Rules (final_design §13): stable site IDs, atom-order invariance,
    symmetric-site dedup, multiple valid sites retained.
    """
    Chem = _rdkit_chem()
    query_mol = Chem.MolFromSmiles(query.canonical_smiles)
    if query_mol is None:
        return []

    pattern_mol = Chem.MolFromSmarts(transform.donor_site_pattern)
    if pattern_mol is None:
        return []

    # Map number on each pattern position.
    pattern_map_by_pos: dict[int, int] = {}
    for pos, atom in enumerate(pattern_mol.GetAtoms()):
        num = atom.GetAtomMapNum()
        if num > 0:
            pattern_map_by_pos[pos] = num

    matches = query_mol.GetSubstructMatches(pattern_mol)

    raw_sites: list[dict] = []
    for match in matches:
        correspondence: dict[str, int] = {}
        for pos, num in pattern_map_by_pos.items():
            correspondence[str(num)] = int(match[pos])

        matched: list[str] = []
        failed: list[SitePrecondition] = []
        for precondition in transform.strict_preconditions:
            num = precondition.atom_map_number
            if num is None or str(num) not in correspondence:
                failed.append(precondition)
                continue
            x_idx = correspondence[str(num)]
            atom = query_mol.GetAtomWithIdx(x_idx)
            if _precondition_matches(atom, precondition):
                matched.append(precondition.precondition_id)
            else:
                failed.append(precondition)

        site_atom_indices = sorted(correspondence.values())
        symmetry_class = _site_symmetry_key(query_mol, site_atom_indices)

        eligible = not failed
        raw_sites.append({
            "correspondence": correspondence,
            "site_atom_indices": site_atom_indices,
            "matched": matched,
            "failed": failed,
            "symmetry_class": symmetry_class,
            "eligible": eligible,
        })

    # Symmetry dedup by automorphism-equivalence (colored-canonical key).
    unique: dict[str, dict] = {}
    for site in raw_sites:
        key = site["symmetry_class"]
        if key not in unique:
            unique[key] = site

    ordered = sorted(unique.values(), key=lambda s: sorted(s["site_atom_indices"]))
    sites: list[ConditionedSite] = []
    # The site's query identity is AUTHORITATIVE from the query object (R2-E):
    # a site must reference the same query as the one it was enumerated on.
    resolved_query_id = query.query_id
    resolved_case_id = case_id or f"diag_case_{resolved_query_id}"
    for site in ordered:
        similarity = _local_env_similarity(transform, query_mol, site["site_atom_indices"])
        site_id = stable_id("site", {
            "query": query.identity_hash,
            "transform": transform.canonical_transform_hash,
            "sym": site["symmetry_class"],
        })
        sites.append(ConditionedSite(
            site_id=site_id,
            run_id=transform.run_id,
            case_id=resolved_case_id,
            fold_id=transform.fold_id,
            query_id=resolved_query_id,
            snapshot_id=transform.snapshot_id,
            snapshot_hash=transform.snapshot_hash,
            transformation_id=transform.transformation_id,
            query_atom_ids=site["site_atom_indices"],
            query_bond_ids=_query_bond_ids(query_mol, site["site_atom_indices"]),
            atom_map_correspondence=site["correspondence"],
            matched_preconditions=site["matched"],
            failed_preconditions=site["failed"],
            symmetry_class=site["symmetry_class"],
            # ambiguity_group = 0: the enumeration never fabricates genuine
            # ambiguity; distinct non-symmetric sites are independent valid
            # sites, NOT ambiguous alternative interpretations.
            ambiguity_group=0,
            eligibility=(
                SiteEligibility.eligible if site["eligible"]
                else SiteEligibility.ineligible
            ),
            local_environment_similarity=round(similarity, 4),
        ))
    return sites


def _local_env_similarity(
    transform: StrictTransformation,
    query_mol,
    site_atom_indices: list[int],
) -> float:
    """Structural local-environment similarity (R2-E, auditable semantics).

    Tanimoto of Morgan fingerprints (radius 1) of the DONOR site subgraph
    (transform.donor_site_smiles) vs the QUERY site subgraph (the induced
    subgraph on the matched site atoms + their heavy neighbors).  This is a
    real local-environment measure, NOT a precondition pass ratio.
    """
    from rdkit.Chem import AllChem, rdFingerprintGenerator  # noqa: F401
    from rdkit.DataStructs import TanimotoSimilarity  # type: ignore

    def _fp_from_smiles(smiles: str, radius: int = 1, bits: int = 2048):
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=bits)

    donor_fp = _fp_from_smiles(transform.donor_site_smiles)
    if donor_fp is None:
        return 0.0

    # Query site subgraph: site atoms + their heavy neighbors.
    atom_set = set(site_atom_indices)
    env_set = set(site_atom_indices)
    for idx in site_atom_indices:
        atom = query_mol.GetAtomWithIdx(idx)
        for n in atom.GetNeighbors():
            if n.GetAtomicNum() > 1:
                env_set.add(n.GetIdx())
    query_sub = Chem.MolFromSmiles(
        Chem.MolFragmentToSmiles(query_mol, atomsToUse=sorted(env_set))
    )
    if query_sub is None:
        return 0.0
    query_fp = AllChem.GetMorganFingerprintAsBitVect(query_sub, 1, nBits=2048)
    return float(TanimotoSimilarity(donor_fp, query_fp))


def _site_symmetry_key(query_mol, site_atom_indices: list[int]) -> str:
    """Automorphism-based symmetry key.

    Colors every site atom with a fixed atom-map tag and canonicalizes.  Two
    site atom SETS are automorphism-equivalent iff their colored-canonical
    SMILES are identical.  Uses a copy; the input mol is not mutated.
    """
    mol = Chem.Mol(query_mol)
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    for idx in site_atom_indices:
        mol.GetAtomWithIdx(idx).SetAtomMapNum(7)
    return Chem.MolToSmiles(mol)


def _query_bond_ids(query_mol, atom_indices: list[int]) -> list[int]:
    atom_set = set(atom_indices)
    bond_ids: list[int] = []
    for bond in query_mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        if i in atom_set and j in atom_set:
            bond_ids.append(bond.GetIdx())
    return sorted(bond_ids)
