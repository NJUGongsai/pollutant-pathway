"""P3-T6 Deterministic graph-edit generation (final_plan §6.7, R2-E).

Versioned compiler: transform + site -> deterministic graph edit.
- deterministic edit application (RWMol)
- FAIL-CLOSED: a required edit that cannot be applied is a typed failure
  (never a silent skip / log-and-continue)
- H / charge / element handling
- transferred atom creation (incl. multi-atom group internal bonds)
- removed atom deletion
- sanitize / canonicalize (explicit-H independent canonical identity)
- NO LLM ever creates a structure here
"""
from __future__ import annotations

from rdkit import Chem  # type: ignore

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.p3.schemas import (
    ConditionedSite,
    EditApplicationLog,
    GenerationReport,
    NormalizedQuery,
    StrictTransformation,
)

GENERATION_VERSION = "p3-1"

# Typed failure codes (R2-E).
TRANSFORM_SITE_ID_MISMATCH = "TRANSFORM_SITE_ID_MISMATCH"
QUERY_SITE_ID_MISMATCH = "QUERY_SITE_ID_MISMATCH"
MISSING_EDIT_ENDPOINT = "MISSING_EDIT_ENDPOINT"
EXPECTED_BOND_ABSENT = "EXPECTED_BOND_ABSENT"
UNEXPECTED_EXISTING_BOND = "UNEXPECTED_EXISTING_BOND"
ATOM_STATE_TARGET_MISSING = "ATOM_STATE_TARGET_MISSING"
REMOVAL_TARGET_MISSING = "REMOVAL_TARGET_MISSING"
TRANSFER_ANCHOR_MISSING = "TRANSFER_ANCHOR_MISSING"
UNEXPECTED_MULTIFRAGMENT_PRODUCT = "UNEXPECTED_MULTIFRAGMENT_PRODUCT"


class GraphEditError(Exception):
    """Typed graph-edit failure (fail closed, never silently skipped)."""

    def __init__(self, failure_code: str, detail: str) -> None:
        super().__init__(detail)
        self.failure_code = failure_code
        self.detail = detail


def _order_type(order: float | int):
    if order == 1:
        return Chem.BondType.SINGLE
    if order == 2:
        return Chem.BondType.DOUBLE
    if order == 3:
        return Chem.BondType.TRIPLE
    if order == 1.5:
        return Chem.BondType.AROMATIC
    return Chem.BondType.SINGLE


def _set_h_count(atom, h: int) -> None:
    atom.SetNumExplicitHs(0)
    atom.SetNoImplicit(True)
    atom.SetNumExplicitHs(int(h))


def _atomic_num(element: str) -> int:
    from rdkit.Chem import PeriodicTable  # type: ignore
    return PeriodicTable.GetAtomicNumber(element)


def _apply_bond_changes(rwmol, transform, idx_from_map, log) -> None:
    for bc in transform.bond_changes:
        a = idx_from_map.get(bc.atom_map_a)
        b = idx_from_map.get(bc.atom_map_b)
        if a is None or b is None:
            raise GraphEditError(
                MISSING_EDIT_ENDPOINT,
                f"bond change {bc.atom_map_a}-{bc.atom_map_b} has a missing "
                f"endpoint on X",
            )
        if bc.operation == "delete":
            if not rwmol.GetBondBetweenAtoms(a, b):
                raise GraphEditError(
                    EXPECTED_BOND_ABSENT,
                    f"expected to delete bond {a}-{b} but it is absent",
                )
            rwmol.RemoveBond(a, b)
            log.append(EditApplicationLog(step="bond_delete", detail=f"removed bond {a}-{b}"))
        elif bc.operation == "order_change":
            bond = rwmol.GetBondBetweenAtoms(a, b)
            if bond is None:
                raise GraphEditError(
                    EXPECTED_BOND_ABSENT,
                    f"expected bond {a}-{b} for order change but it is absent",
                )
            bond.SetBondType(_order_type(bc.new_order))
            log.append(EditApplicationLog(
                step="bond_order_change", detail=f"bond {a}-{b} order -> {bc.new_order}",
            ))
        elif bc.operation == "add":
            if rwmol.GetBondBetweenAtoms(a, b):
                raise GraphEditError(
                    UNEXPECTED_EXISTING_BOND,
                    f"expected to add bond {a}-{b} but it already exists",
                )
            rwmol.AddBond(a, b, _order_type(bc.new_order))
            log.append(EditApplicationLog(
                step="bond_add", detail=f"added bond {a}-{b} order {bc.new_order}",
            ))


def _apply_atom_state_changes(rwmol, transform, idx_from_map, log) -> None:
    for st in transform.atom_state_changes:
        idx = idx_from_map.get(st.atom_map_number)
        if idx is None:
            raise GraphEditError(
                ATOM_STATE_TARGET_MISSING,
                f"atom-state target for map {st.atom_map_number} missing on X",
            )
        atom = rwmol.GetAtomWithIdx(idx)
        if st.element_change:
            atom.SetAtomicNum(_atomic_num(st.element_change))
            log.append(EditApplicationLog(step="element_change", detail=f"atom {idx} -> {st.element_change}"))
        if st.target_formal_charge is not None:
            atom.SetFormalCharge(st.target_formal_charge)
            log.append(EditApplicationLog(step="charge_change", detail=f"atom {idx} charge -> {st.target_formal_charge}"))
        if st.target_h_count is not None:
            _set_h_count(atom, st.target_h_count)
            log.append(EditApplicationLog(step="h_count_set", detail=f"atom {idx} H -> {st.target_h_count}"))
        if st.aromaticity_change == "to_aromatic":
            atom.SetIsAromatic(True)
            log.append(EditApplicationLog(step="aromaticity_to_aromatic", detail=f"atom {idx} marked aromatic"))
        elif st.aromaticity_change == "from_aromatic":
            atom.SetIsAromatic(False)
            log.append(EditApplicationLog(step="aromaticity_from_aromatic", detail=f"atom {idx} marked non-aromatic"))


def _remove_atoms(rwmol, transform, idx_from_map, log) -> None:
    for removed_map in transform.removed_atom_maps:
        if removed_map not in idx_from_map:
            raise GraphEditError(
                REMOVAL_TARGET_MISSING,
                f"removed atom map {removed_map} has no target on X",
            )
    indices = sorted(
        (idx_from_map[m] for m in transform.removed_atom_maps if m in idx_from_map),
        reverse=True,
    )
    for idx in indices:
        rwmol.RemoveAtom(idx)
        log.append(EditApplicationLog(step="atom_remove", detail=f"removed atom {idx}"))


def _add_transferred_atoms(rwmol, transform, idx_from_map, log) -> None:
    added: list[tuple[int, int]] = []
    for tr in transform.transferred_atoms:
        for bt in tr.bonds_to:
            if bt.get("atom_map") not in idx_from_map:
                raise GraphEditError(
                    TRANSFER_ANCHOR_MISSING,
                    f"transferred atom {tr.transfer_map_number} anchor "
                    f"{bt.get('atom_map')} missing on X",
                )
        new_idx = rwmol.AddAtom(Chem.Atom(_atomic_num(tr.element)))
        atom = rwmol.GetAtomWithIdx(new_idx)
        atom.SetFormalCharge(tr.formal_charge)
        _set_h_count(atom, tr.h_count)
        for bt in tr.bonds_to:
            anchor = idx_from_map[bt["atom_map"]]
            rwmol.AddBond(new_idx, anchor, _order_type(bt.get("order", 1)))
            log.append(EditApplicationLog(
                step="transferred_bond", detail=f"transferred atom {new_idx} bonded to common anchor {anchor}",
            ))
        added.append((tr.transfer_map_number, new_idx))
        log.append(EditApplicationLog(
            step="transferred_atom",
            detail=f"added {tr.element} atom {new_idx} (source {tr.source_participant_id})",
        ))
    # Multi-atom transferred group internal bonds (R2-D).
    transfer_index = dict(added)
    for tr in transform.transferred_atoms:
        idx = transfer_index.get(tr.transfer_map_number)
        if idx is None:
            continue
        for bt in tr.bonds_to_transferred:
            other = transfer_index.get(bt.get("atom_map"))
            if other is None:
                raise GraphEditError(
                    TRANSFER_ANCHOR_MISSING,
                    f"transferred-internal anchor {bt.get('atom_map')} missing",
                )
            rwmol.AddBond(idx, other, _order_type(bt.get("order", 1)))
            log.append(EditApplicationLog(
                step="transferred_internal_bond", detail=f"transferred group bond {idx}-{other}",
            ))


def generate_product(
    transform: StrictTransformation,
    site: ConditionedSite,
    query: NormalizedQuery,
    *,
    query_id: str = "",
    case_id: str = "",
) -> GenerationReport:
    """Compile transform + site into a deterministic product structure.

    Returns a GenerationReport.  Any required edit that cannot be applied, or
    a sanitization failure, yields a typed ``failure_code`` — NEVER a silent
    skip or a downgraded candidate.
    """
    # Fail-closed namespace checks (R2-E).
    if site.transformation_id != transform.transformation_id:
        return _failed_report(
            transform, site, query, TRANSFORM_SITE_ID_MISMATCH,
            f"site {site.site_id} references transform {site.transformation_id}, "
            f"expected {transform.transformation_id}",
        )
    if site.query_id != query.query_id:
        return _failed_report(
            transform, site, query, QUERY_SITE_ID_MISMATCH,
            f"site {site.site_id} references query {site.query_id}, "
            f"expected {query.query_id}",
        )

    query_mol = Chem.MolFromSmiles(query.canonical_smiles)
    if query_mol is None:
        return _failed_report(transform, site, query, "INVALID_QUERY_MOL", "query unparseable")

    rwmol = Chem.RWMol(query_mol)
    idx_from_map = {int(k): int(v) for k, v in site.atom_map_correspondence.items()}
    log: list[EditApplicationLog] = []

    try:
        _apply_bond_changes(rwmol, transform, idx_from_map, log)
        _apply_atom_state_changes(rwmol, transform, idx_from_map, log)
        _remove_atoms(rwmol, transform, idx_from_map, log)
        _add_transferred_atoms(rwmol, transform, idx_from_map, log)
    except GraphEditError as exc:
        return _failed_report(transform, site, query, exc.failure_code, exc.detail)

    changed_atoms = sorted(idx_from_map.values())
    changed_bonds = sorted(_query_bond_ids(query_mol, changed_atoms))

    product_mol = rwmol.GetMol()
    try:
        Chem.SanitizeMol(product_mol)
    except Exception as exc:  # noqa: BLE001 - typed failure on invalid structure
        return _failed_report(
            transform, site, query, "INVALID_VALENCE_OR_SANITIZE",
            f"sanitization failed: {type(exc).__name__}: {exc}", log, changed_atoms, changed_bonds,
        )

    # A generated product must be a single connected molecule (a multi-fragment
    # product is a fail-closed error, not a silently accepted result).
    if len(Chem.GetMolFrags(product_mol)) > 1:
        return _failed_report(
            transform, site, query, UNEXPECTED_MULTIFRAGMENT_PRODUCT,
            "generated product has multiple disconnected fragments",
            log, changed_atoms, changed_bonds,
        )

    clean = Chem.RemoveHs(product_mol)
    canonical = Chem.MolToSmiles(clean)
    raw = Chem.MolToSmiles(product_mol)

    return GenerationReport(
        generation_id=stable_id("gen", {"query": query.identity_hash, "site": site.site_id}),
        transformation_id=transform.transformation_id,
        site_id=site.site_id,
        edit_application_log=log,
        raw_product=raw,
        canonical_product=canonical,
        changed_atoms=changed_atoms,
        changed_bonds=changed_bonds,
        sanitize_report="ok",
        dedup_key=canonical_hash({
            "canonical_product": canonical,
            "transform": transform.canonical_transform_hash,
        }),
        component_version=GENERATION_VERSION,
    )


def _failed_report(
    transform, site, query, failure_code, detail,
    log=None, changed_atoms=None, changed_bonds=None,
) -> GenerationReport:
    return GenerationReport(
        generation_id=stable_id("gen", {"query": query.identity_hash, "site": site.site_id}),
        transformation_id=transform.transformation_id,
        site_id=site.site_id,
        edit_application_log=log or [],
        changed_atoms=changed_atoms or [],
        changed_bonds=changed_bonds or [],
        sanitize_report=detail,
        failure_code=failure_code,
        component_version=GENERATION_VERSION,
    )


def _query_bond_ids(query_mol, atom_indices: list[int]) -> list[int]:
    atom_set = set(atom_indices)
    out = []
    for bond in query_mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        if i in atom_set and j in atom_set:
            out.append(bond.GetIdx())
    return out
