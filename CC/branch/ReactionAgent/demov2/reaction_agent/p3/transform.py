"""P3-T4 Strict transformation extraction (final_plan §6.5).

Derives a canonical, content-addressed, replayable transform from a mapped
A->B lineage:
- mapped atom edits
- bond delete / add / order changes
- atom attributes (charge, H count, aromaticity, element)
- transferred atoms (added heavy atoms with source participant)
- removed atoms (leaving group with sink participant)
- donor site + local environment
- strict preconditions (re-checked on query sites)
- source/sink ledger requirements
- canonical transform hash + version

Rejects (fail closed): partial maps, critical ambiguity, lineage/source
inconsistency.  Nothing here creates structures from free text.
"""
from __future__ import annotations

from rdkit import Chem  # type: ignore

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.p3.schemas import (
    AtomStateChange,
    BondChange,
    EvidenceKind,
    RemovedSinkAssignment,
    ResolvedDonorEvidence,
    SitePrecondition,
    StrictTransformation,
    TransferredAtom,
)

TRANSFORM_VERSION = "p3-1"
TRANSFORM_SCHEMA_VERSION = "p3-1"


class TransformExtractionError(ValueError):
    """Raised when a strict transform cannot be extracted (fail closed)."""


class TransformBindingError(TransformExtractionError):
    """Raised when a transform's stored hash/ID does not recompute from its
    own fields (R3-C): a forged or mutated transform is never trusted."""

    def __init__(self, message: str, failure_code: str = "TRANSFORM_HASH_COLLISION"):
        super().__init__(message)
        self.failure_code = failure_code


# -- Canonical transform preimage (R3-C) -------------------------------------


def canonical_transform_preimage(
    *,
    selected_lineage_id: str,
    source_lineage_hash: str,
    donor_reaction_id: str,
    reaction_authority_hash: str,
    mapped_edits: list[int],
    bond_changes: list[BondChange],
    atom_state_changes: list[AtomStateChange],
    transferred_atoms: list[TransferredAtom],
    removed_atom_maps: list[int],
    removed_atom_sinks: list[RemovedSinkAssignment],
    site_maps: list[int],
    local_environment: list[int],
    preconditions: list[SitePrecondition],
    ledger_requirements: list[str],
    site_pattern: str,
) -> dict:
    """The SINGLE canonical transform preimage (R3-C).

    Used by BOTH ``canonical_transform_hash`` and ``transformation_id``, and
    recomputable from ``StrictTransformation`` fields alone (see
    ``recompute_transform_preimage``).  Covers:

    - selected lineage and reaction authority hash;
    - all bond edits and atom-state edits;
    - transferred element, charge, H count, source participant;
    - transferred bonds to COMMON anchors (atom map AND bond order);
    - internal transferred bonds;
    - removed atom maps and exact map-to-sink participant assignments;
    - donor site, local environment, preconditions, ledger requirements;
    - versions and policies.

    Every collection is canonically sorted here, so semantically irrelevant
    input ordering cannot change the hash.
    """
    return {
        "selected_lineage_id": selected_lineage_id,
        "source_lineage_hash": source_lineage_hash,
        "reaction_id": donor_reaction_id,
        "reaction_authority_hash": reaction_authority_hash,
        "mapped_edits": sorted(mapped_edits),
        "bond_changes": sorted(
            (bc.atom_map_a, bc.atom_map_b, bc.operation,
             float(bc.new_order) if bc.new_order is not None else None)
            for bc in bond_changes
        ),
        "atom_state_changes": sorted(
            (st.atom_map_number, st.element_change, st.formal_charge_change,
             st.target_formal_charge, st.h_count_change, st.target_h_count,
             st.aromaticity_change)
            for st in atom_state_changes
        ),
        "transferred": sorted(
            (t.transfer_map_number, t.element, t.formal_charge, t.h_count,
             t.source_participant_id,
             tuple(sorted((b["atom_map"], b["order"]) for b in t.bonds_to)),
             tuple(sorted(
                 (b["atom_map"], b["order"]) for b in t.bonds_to_transferred)))
            for t in transferred_atoms
        ),
        "removed": sorted(removed_atom_maps),
        "removed_sinks": sorted(
            (s.atom_map, s.sink_participant_id) for s in removed_atom_sinks
        ),
        "site": sorted(site_maps),
        "local_environment": sorted(local_environment),
        "preconditions": sorted(
            (p.kind, p.atom_map_number, tuple(sorted(p.params.items())))
            for p in preconditions
        ),
        "ledger_requirements": sorted(ledger_requirements),
        "pattern": site_pattern,
        "transform_version": TRANSFORM_VERSION,
        "schema_version": TRANSFORM_SCHEMA_VERSION,
    }


def recompute_transform_preimage(transform: StrictTransformation) -> dict:
    """Rebuild the canonical preimage from the transform's OWN fields (R3-C).

    If this preimage's hash differs from ``canonical_transform_hash`` (or the
    stable ID differs from ``transformation_id``), the transform was forged
    or mutated after extraction.
    """
    return canonical_transform_preimage(
        selected_lineage_id=(
            transform.source_lineage_ids[0] if transform.source_lineage_ids else ""
        ),
        source_lineage_hash=transform.source_lineage_hash,
        donor_reaction_id=transform.donor_reaction_id,
        reaction_authority_hash=transform.reaction_authority_hash,
        mapped_edits=list(transform.mapped_atom_edits),
        bond_changes=list(transform.bond_changes),
        atom_state_changes=list(transform.atom_state_changes),
        transferred_atoms=list(transform.transferred_atoms),
        removed_atom_maps=list(transform.removed_atom_maps),
        removed_atom_sinks=list(transform.removed_atom_sinks),
        site_maps=list(transform.donor_site_atom_map_numbers),
        local_environment=list(transform.local_environment),
        preconditions=list(transform.strict_preconditions),
        ledger_requirements=list(transform.ledger_requirements),
        site_pattern=transform.donor_site_pattern,
    )


def verify_transform_binding(transform: StrictTransformation) -> None:
    """Fail closed when hash/ID do not recompute from the fields (R3-C)."""
    try:
        preimage = recompute_transform_preimage(transform)
    except TransformBindingError:
        raise
    except Exception as exc:  # noqa: BLE001 - typed binding failure
        raise TransformBindingError(
            f"transform preimage is not recomputable from its fields: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    recomputed_hash = canonical_hash(preimage)
    if recomputed_hash != transform.canonical_transform_hash:
        raise TransformBindingError(
            f"canonical_transform_hash {transform.canonical_transform_hash[:12]}... "
            f"!= recomputed {recomputed_hash[:12]}... — transform content "
            f"changed without rebinding its hash"
        )
    recomputed_id = stable_id("tr", preimage)
    if recomputed_id != transform.transformation_id:
        raise TransformBindingError(
            f"transformation_id {transform.transformation_id} != recomputed "
            f"{recomputed_id} — transform content changed without rebinding its ID"
        )


# -- RDKit helpers -----------------------------------------------------------


def _mapped_mol(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise TransformExtractionError(f"unparseable mapped SMILES: {smiles!r}")
    return mol


def _atom_by_map(mol) -> dict[int, int]:
    """Map number -> atom index.

    Duplicate map numbers are a typed error (never silently overwritten).
    """
    out: dict[int, int] = {}
    for atom in mol.GetAtoms():
        num = atom.GetAtomMapNum()
        if num > 0:
            if num in out:
                raise TransformExtractionError(
                    f"duplicate atom map number {num} in mapped molecule"
                )
            out[num] = atom.GetIdx()
    return out


def _bond_key(a: int, b: int) -> tuple[int, int]:
    return (min(a, b), max(a, b))


def _bond_orders(mol) -> dict[tuple[int, int], int]:
    """Canonical bond key -> order (1/2/3), with aromatic marked as 1.5."""
    out: dict[tuple[int, int], int] = {}
    for bond in mol.GetBonds():
        key = _bond_key(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx())
        order = bond.GetBondTypeAsDouble()
        if bond.GetIsAromatic():
            order = 1.5
        out[key] = int(order) if order == int(order) else 1.5
    return out


# -- Edit-script extraction --------------------------------------------------


def _extract_edit_script(
    a_mol,
    b_mol,
    a_map_to_idx: dict[int, int],
    b_map_to_idx: dict[int, int],
) -> tuple[list[BondChange], list[AtomStateChange], list[int], list[dict]]:
    """Compute bond changes, atom state changes, removed maps, transferred atoms.

    Returns (bond_changes, atom_state_changes, removed_atom_maps, transferred).
    """
    a_atoms = {num: a_mol.GetAtomWithIdx(idx) for num, idx in a_map_to_idx.items()}
    b_atoms = {num: b_mol.GetAtomWithIdx(idx) for num, idx in b_map_to_idx.items()}

    common = sorted(set(a_atoms) & set(b_atoms))
    only_a = sorted(set(a_atoms) - set(b_atoms))
    only_b = sorted(set(b_atoms) - set(a_atoms))

    # Element mismatch check: a map number present in both must be same element.
    for num in common:
        if a_atoms[num].GetAtomicNum() != b_atoms[num].GetAtomicNum():
            raise TransformExtractionError(
                f"map {num} pairs different elements — mapping inconsistent"
            )

    common_maps = set(common)

    # Atom state changes for common atoms.
    atom_state_changes: list[AtomStateChange] = []
    for num in common:
        aa = a_atoms[num]
        ba = b_atoms[num]
        h_delta = ba.GetTotalNumHs() - aa.GetTotalNumHs()
        charge_delta = ba.GetFormalCharge() - aa.GetFormalCharge()
        aromatic_delta = "none"
        if aa.GetIsAromatic() != ba.GetIsAromatic():
            aromatic_delta = "from_aromatic" if aa.GetIsAromatic() else "to_aromatic"
        if h_delta != 0 or charge_delta != 0 or aromatic_delta != "none":
            atom_state_changes.append(AtomStateChange(
                atom_map_number=num,
                formal_charge_change=charge_delta if charge_delta != 0 else None,
                target_formal_charge=ba.GetFormalCharge(),
                h_count_change=h_delta if h_delta != 0 else None,
                target_h_count=ba.GetTotalNumHs(),
                aromaticity_change=aromatic_delta,
            ))

    # Bond changes among common atoms, keyed by MAP NUMBERS (never by atom
    # index, to avoid index/map-number collisions).
    def _common_bond_table(mol, map_to_idx, common_maps):
        idx_to_map = {v: k for k, v in map_to_idx.items()}
        table: dict[tuple[int, int], object] = {}
        for bond in mol.GetBonds():
            i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            mi = idx_to_map.get(i)
            mj = idx_to_map.get(j)
            if mi is None or mj is None or mi not in common_maps or mj not in common_maps:
                continue
            order = bond.GetBondTypeAsDouble()
            if bond.GetIsAromatic():
                order = 1.5
            table[_bond_key(mi, mj)] = int(order) if order == int(order) else 1.5
        return table

    bond_changes: list[BondChange] = []
    common_a_bonds = _common_bond_table(a_mol, a_map_to_idx, common_maps)
    common_b_bonds = _common_bond_table(b_mol, b_map_to_idx, common_maps)

    def _preserve_order(o) -> float:
        # aromatic (1.5) must NOT be truncated to single (int(1.5)==1).
        return o if o == int(o) else o

    for (ma, mb), order in common_a_bonds.items():
        if (ma, mb) not in common_b_bonds:
            bond_changes.append(BondChange(
                atom_map_a=ma, atom_map_b=mb, operation="delete",
            ))
        elif common_b_bonds[(ma, mb)] != order:
            bond_changes.append(BondChange(
                atom_map_a=ma, atom_map_b=mb,
                operation="order_change",
                new_order=_preserve_order(common_b_bonds[(ma, mb)]),
            ))
    for (ma, mb), order in common_b_bonds.items():
        if (ma, mb) not in common_a_bonds:
            bond_changes.append(BondChange(
                atom_map_a=ma, atom_map_b=mb,
                operation="add",
                new_order=_preserve_order(order),
            ))

    # Removed atoms (heavy atoms in A not in B).
    removed_atom_maps = [num for num in only_a if a_atoms[num].GetAtomicNum() > 1]
    removed_set = set(removed_atom_maps)

    # Cut bonds between a common atom and a removed atom must be deleted at
    # generation time (e.g. decarb C3-C4, hydrolysis C2-O4).  Bonds entirely
    # inside the removed group are implied by atom removal and not recorded.
    idx_to_map_a = {v: k for k, v in a_map_to_idx.items()}
    existing_keys = {_bond_key(b.atom_map_a, b.atom_map_b) for b in bond_changes}
    for bond in a_mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        mi = idx_to_map_a.get(i)
        mj = idx_to_map_a.get(j)
        if mi is None or mj is None:
            continue
        in_common = (mi in common_maps, mj in common_maps)
        in_removed = (mi in removed_set, mj in removed_set)
        if (in_common[0] and in_removed[1]) or (in_common[1] and in_removed[0]):
            key = _bond_key(mi, mj)
            if key not in existing_keys:
                bond_changes.append(BondChange(
                    atom_map_a=mi, atom_map_b=mj, operation="delete",
                ))
                existing_keys.add(key)

    # Transferred atoms (heavy atoms in B not in A).
    only_b_set = set(only_b)
    transferred: list[dict] = []
    for num in only_b:
        ba = b_atoms[num]
        if ba.GetAtomicNum() == 1:  # H handled as H-count change
            continue
        bonds_to = []
        bonds_to_transferred = []
        for neighbor in ba.GetNeighbors():
            nb_num = neighbor.GetAtomMapNum()
            bond = b_mol.GetBondBetweenAtoms(ba.GetIdx(), neighbor.GetIdx())
            order = int(bond.GetBondTypeAsDouble()) if not bond.GetIsAromatic() else 1.5
            if nb_num in common:
                bonds_to.append({"atom_map": nb_num, "order": order})
            elif nb_num in only_b_set:
                # internal bond of a multi-atom transferred group (R2-D):
                # must be preserved, referencing the other transfer map number.
                bonds_to_transferred.append({"atom_map": nb_num, "order": order})
        transferred.append({
            "transfer_map_number": num,
            "element": ba.GetSymbol(),
            "formal_charge": ba.GetFormalCharge(),
            "h_count": ba.GetTotalNumHs(),
            "bonds_to": bonds_to,
            "bonds_to_transferred": bonds_to_transferred,
        })

    return bond_changes, atom_state_changes, removed_atom_maps, transferred


def _maps_for_key(
    map_to_idx: dict[int, int],
    idx_i: int,
    idx_j: int,
) -> tuple[int, int]:
    inv = {v: k for k, v in map_to_idx.items()}
    return inv[idx_i], inv[idx_j]


# -- Site pattern ------------------------------------------------------------


def _build_site_smarts(
    a_mol,
    site_maps: list[int],
    env_maps: list[int],
) -> str:
    """Build a SMARTS query for the donor site + local environment.

    Site atoms carry their transform map number (``[#Z:map]``); environment
    atoms are element-specific but generic (``[#Z]``).  No H constraint is
    baked into the pattern: strictness about H counts is enforced by explicit
    ``h_count`` preconditions re-checked on the query site (this keeps e.g.
    decarboxylation applicable to CH2 or CH3 alpha carbons while still
    separating primary from secondary alcohols).
    """
    map_to_idx = _atom_by_map(a_mol)
    site_idx = sorted(map_to_idx[num] for num in site_maps if num in map_to_idx)
    env_idx = sorted(map_to_idx[num] for num in env_maps if num in map_to_idx)
    atoms_to_use = site_idx + env_idx
    if not atoms_to_use:
        raise TransformExtractionError("site has no heavy atoms — cannot build pattern")

    # Adjacency among the used atoms (deterministic order).
    used = set(atoms_to_use)
    adj: dict[int, list[tuple[int, object]]] = {i: [] for i in atoms_to_use}
    for bond in a_mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        if i in used and j in used:
            adj[i].append((j, bond))
            adj[j].append((i, bond))
    for key in adj:
        adj[key].sort(key=lambda pair: pair[0])

    site_by_idx = {idx: num for num, idx in map_to_idx.items() if num in site_maps}

    def _query(i: int) -> str:
        atom = a_mol.GetAtomWithIdx(i)
        num = site_by_idx.get(i)
        if num is not None:
            return f"[#{atom.GetAtomicNum()}:{num}]"
        return f"[#{atom.GetAtomicNum()}]"

    def _bond_symbol(bond) -> str:
        bt = bond.GetBondType()
        if bt == Chem.BondType.DOUBLE:
            return "="
        if bt == Chem.BondType.TRIPLE:
            return "#"
        if bt == Chem.BondType.AROMATIC:
            return ":"
        return "-"

    visited: set[int] = set()

    def _dfs(i: int) -> str:
        visited.add(i)
        parts = [_query(i)]
        for j, bond in adj[i]:
            if j in visited:
                continue
            parts.append(f"({_bond_symbol(bond)}{_dfs(j)})")
        return "".join(parts)

    smarts = _dfs(atoms_to_use[0])
    if not smarts:
        raise TransformExtractionError("site pattern generation returned empty SMARTS")
    # Validate the generated SMARTS parses.
    if Chem.MolFromSmarts(smarts) is None:
        raise TransformExtractionError(
            f"site pattern failed to parse as SMARTS: {smarts!r}"
        )
    return smarts


# -- Preconditions -----------------------------------------------------------


def _site_preconditions(
    a_mol,
    site_maps: list[int],
) -> list[SitePrecondition]:
    """Derive strict preconditions from the donor site atom environments."""
    map_to_idx = _atom_by_map(a_mol)
    preconditions: list[SitePrecondition] = []
    for num in site_maps:
        idx = map_to_idx[num]
        atom = a_mol.GetAtomWithIdx(idx)
        heavy_neighbors = [n for n in atom.GetNeighbors() if n.GetAtomicNum() > 1]
        preconditions.append(SitePrecondition(
            precondition_id=stable_id("pre", {"kind": "heavy_atom_degree", "map": num}),
            kind="heavy_atom_degree",
            atom_map_number=num,
            params={"degree": len(heavy_neighbors)},
        ))
        preconditions.append(SitePrecondition(
            precondition_id=stable_id("pre", {"kind": "h_count", "map": num}),
            kind="h_count",
            atom_map_number=num,
            params={"h": atom.GetTotalNumHs()},
        ))
        preconditions.append(SitePrecondition(
            precondition_id=stable_id("pre", {"kind": "formal_charge", "map": num}),
            kind="formal_charge",
            atom_map_number=num,
            params={"charge": atom.GetFormalCharge()},
        ))
        element_counts: dict[str, int] = {}
        for n in heavy_neighbors:
            element_counts[n.GetSymbol()] = element_counts.get(n.GetSymbol(), 0) + 1
        for element, count in sorted(element_counts.items()):
            preconditions.append(SitePrecondition(
                precondition_id=stable_id(
                    "pre", {"kind": "element_neighbor", "map": num, "el": element}
                ),
                kind="element_neighbor",
                atom_map_number=num,
                params={"element": element, "count": count},
            ))
    return preconditions


# -- Public extraction -------------------------------------------------------


def extract_transform(
    donor_evidence: ResolvedDonorEvidence,
    *,
    lineage_id: str | None = None,
    query_id: str = "",
    case_id: str = "",
    run_id: str = "",
    fold_id: str = "",
    snapshot_id: str = "",
    snapshot_hash: str = "",
) -> StrictTransformation:
    """Extract the strict transform for the donor's primary A->B lineage.

    Raises TransformExtractionError on fail-closed conditions.
    """
    context = donor_evidence.context
    donor_participant = _participant_by_id(
        context.reaction_evidence.participants,
        context.donor_participant_id,
    )
    lineage = _select_lineage(context, lineage_id)
    product_participant = _participant_by_id(
        context.reaction_evidence.participants,
        lineage.product_participant_id,
    )

    a_mol = _mapped_mol(donor_participant.canonical_smiles)
    b_mol = _mapped_mol(product_participant.canonical_smiles)
    a_map_to_idx = _atom_by_map(a_mol)
    b_map_to_idx = _atom_by_map(b_mol)

    if not a_map_to_idx or not b_map_to_idx:
        raise TransformExtractionError(
            "donor or product lacks atom map numbers — cannot extract transform"
        )

    bond_changes, atom_state_changes, removed_maps, transferred = _extract_edit_script(
        a_mol, b_mol, a_map_to_idx, b_map_to_idx
    )

    # Site atoms: changed common atoms + removed atoms + transferred heavy
    # atoms.  All of them must be locatable/creatable during generation.
    # BOTH endpoints of every bond change are changed atoms (R2-D).
    changed_maps = sorted(
        {map_num for bc in bond_changes for map_num in (bc.atom_map_a, bc.atom_map_b)}
        | {st.atom_map_number for st in atom_state_changes}
    )
    transferred_maps = [t["transfer_map_number"] for t in transferred]
    # Transferred atoms' common anchors must also be part of the site so they
    # can be located on X during generation (R2-D/R2-E).
    transferred_anchors = {
        bt["atom_map"] for t in transferred for bt in t["bonds_to"]
    }
    site_maps = sorted(
        set(changed_maps) | set(transferred_maps) | set(removed_maps)
        | transferred_anchors
    )
    if not site_maps:
        raise TransformExtractionError("no structural edit at the donor site")

    # Atoms to TAG in the site pattern = site atoms that exist in the donor A
    # (changed common + removed + transferred ANCHORS).  Transferred atoms are
    # created at generation time, but their common anchors must be matched on X.
    pattern_tag_maps = sorted(
        set(changed_maps) | set(removed_maps) | transferred_anchors
    )

    # Local environment: heavy neighbors of ALL site atoms in the donor.
    env_maps = _local_environment(a_mol, a_map_to_idx, site_maps)

    site_smiles = _site_smiles(a_mol, a_map_to_idx, site_maps, env_maps)
    site_pattern = _build_site_smarts(a_mol, pattern_tag_maps, env_maps)
    preconditions = _site_preconditions(a_mol, pattern_tag_maps)

    # Ledger requirements: formal source/sink for transferred/removed atoms.
    ledger_requirements = _ledger_requirements(context, transferred, removed_maps)

    # Sink/source participant resolution for removed/transferred atoms.
    removed_sinks = _resolve_atom_sources(context, transferred, removed_maps)

    # unknown_source / unknown sink never enters a strict transform.
    for t in transferred:
        if t["source_participant_id"] in ("", "unknown_source"):
            raise TransformExtractionError(
                f"transferred atom {t['transfer_map_number']} has no formal "
                f"source participant — rejected for strict"
            )
    for removed_map in removed_maps:
        if removed_sinks.get(removed_map) in ("", None, "unknown_source"):
            raise TransformExtractionError(
                f"removed atom {removed_map} has no formal sink participant — "
                f"rejected for strict"
            )

    source_lineage_id = lineage.lineage_id
    lineage_hash = canonical_hash({
        "lineage_id": lineage.lineage_id,
        "reactant": lineage.reactant_participant_id,
        "product": lineage.product_participant_id,
        "ambiguity": lineage.ambiguity,
    })

    # Typed structures FIRST; the canonical preimage is built from them so
    # extraction-time hashing and field-based recomputation are IDENTICAL.
    transferred_atoms = [
        TransferredAtom(
            transfer_map_number=t["transfer_map_number"],
            element=t["element"],
            formal_charge=t["formal_charge"],
            h_count=t["h_count"],
            source_participant_id=t.get("source_participant_id", "unknown_source"),
            bonds_to=t["bonds_to"],
            bonds_to_transferred=t.get("bonds_to_transferred", []),
        )
        for t in transferred
    ]
    removed_atom_sinks = [
        RemovedSinkAssignment(
            atom_map=removed_map,
            sink_participant_id=removed_sinks[removed_map],
        )
        for removed_map in sorted(removed_maps)
    ]

    # The SINGLE canonical content-addressed preimage (R2-D + R3-C):
    # selected lineage + reaction authority binding, mapped edits, bond
    # ops/order, atom state changes, transferred atoms + source + bonds to
    # common anchors (map AND order) + internal bonds, removed atoms + exact
    # sink assignments, donor site, local environment, strict preconditions,
    # ledger requirements, versions.
    preimage = canonical_transform_preimage(
        selected_lineage_id=source_lineage_id,
        source_lineage_hash=lineage_hash,
        donor_reaction_id=context.reaction_id,
        reaction_authority_hash=donor_evidence.reaction_authority_hash,
        mapped_edits=site_maps,
        bond_changes=bond_changes,
        atom_state_changes=atom_state_changes,
        transferred_atoms=transferred_atoms,
        removed_atom_maps=removed_maps,
        removed_atom_sinks=removed_atom_sinks,
        site_maps=site_maps,
        local_environment=env_maps,
        preconditions=preconditions,
        ledger_requirements=ledger_requirements,
        site_pattern=site_pattern,
    )
    canonical_hash_value = canonical_hash(preimage)

    return StrictTransformation(
        transformation_id=stable_id("tr", preimage),
        run_id=run_id or donor_evidence.run_id,
        case_id=case_id or donor_evidence.case_id,
        query_id=query_id or donor_evidence.query_id,
        fold_id=fold_id or donor_evidence.fold_id,
        snapshot_id=snapshot_id or donor_evidence.snapshot_id,
        snapshot_hash=snapshot_hash or donor_evidence.snapshot_hash,
        source_lineage_ids=[source_lineage_id],
        source_lineage_hash=lineage_hash,
        donor_reaction_id=context.reaction_id,
        reaction_authority_hash=donor_evidence.reaction_authority_hash,
        mapped_atom_edits=sorted(site_maps),
        bond_changes=bond_changes,
        atom_state_changes=atom_state_changes,
        removed_atom_maps=sorted(removed_maps),
        removed_atom_sinks=removed_atom_sinks,
        transferred_atoms=transferred_atoms,
        donor_site_atom_map_numbers=site_maps,
        donor_site_smiles=site_smiles,
        donor_site_pattern=site_pattern,
        local_environment=sorted(env_maps),
        strict_preconditions=preconditions,
        ledger_requirements=ledger_requirements,
        canonical_transform_hash=canonical_hash_value,
        transform_version=TRANSFORM_VERSION,
        evidence_kind=donor_evidence.evidence_kind,
    )


def _participant_by_id(participants, participant_id):
    for p in participants:
        if p.participant_id == participant_id:
            return p
    raise TransformExtractionError(
        f"participant {participant_id!r} not found in reaction participants"
    )


def _select_lineage(context, lineage_id: str | None):
    if lineage_id is not None:
        for lineage in context.resolved_lineages:
            if lineage.lineage_id == lineage_id:
                return lineage
        raise TransformExtractionError(f"unknown lineage_id {lineage_id!r}")
    # Primary: reactant == donor, product role transformed_product preferred.
    from reaction_agent.schemas.common import ParticipantRole

    candidates = [
        l for l in context.resolved_lineages
        if l.reactant_participant_id == context.donor_participant_id
    ]
    if not candidates:
        raise TransformExtractionError(
            "no lineage whose reactant is the donor participant"
        )
    role_by_participant = {
        p.participant_id: max(
            (h.role for h in p.role_hypotheses),
            key=lambda r: next(
                (h.score for h in p.role_hypotheses if h.role == r), 0.0
            ),
        )
        for p in context.reaction_evidence.participants
    }
    scored = sorted(
        candidates,
        key=lambda l: 0
        if role_by_participant.get(l.product_participant_id)
        == ParticipantRole.transformed_product
        else 1,
    )
    return scored[0]


def _local_environment(a_mol, a_map_to_idx, site_maps: list[int]) -> list[int]:
    site_idx = {a_map_to_idx[num] for num in site_maps if num in a_map_to_idx}
    env_maps: set[int] = set()
    for idx in site_idx:
        atom = a_mol.GetAtomWithIdx(idx)
        for neighbor in atom.GetNeighbors():
            if neighbor.GetAtomicNum() == 1:
                continue
            num = neighbor.GetAtomMapNum()
            if num > 0 and num not in site_maps:
                env_maps.add(num)
    return sorted(env_maps)


def _site_smiles(a_mol, a_map_to_idx, site_maps, env_maps) -> str:
    idx = sorted({a_map_to_idx[num] for num in site_maps if num in a_map_to_idx}
                 | {a_map_to_idx[num] for num in env_maps if num in a_map_to_idx})
    frag = Chem.MolFragmentToSmiles(a_mol, atomsToUse=idx)
    return frag or ""


def _ledger_requirements(context, transferred, removed_maps) -> list[str]:
    requirements = []
    for t in transferred:
        requirements.append(
            f"transferred_atom:{t['transfer_map_number']}:{t['element']}:"
            f"formal_source_required"
        )
    for num in removed_maps:
        requirements.append(f"removed_atom:{num}:formal_sink_required")
    return requirements


def _resolve_atom_sources(context, transferred: list[dict], removed_maps: list[int]) -> dict[int, str]:
    """Annotate transferred atoms with source participant IDs and compute the
    formal SINK participant for each removed atom map (R2-D).

    A removed atom is a leaving group atom that appears in a product
    coproduct participant (e.g. CO2 / H2O / ethanol).  Returns
    {removed_atom_map: sink_participant_id}.
    """
    participants = context.reaction_evidence.participants
    for t in transferred:
        t["source_participant_id"] = _find_participant_for_map(
            participants, t["transfer_map_number"], side="reactant"
        )
    removed_sinks: dict[int, str] = {}
    for removed_map in removed_maps:
        removed_sinks[removed_map] = _find_participant_for_map(
            participants, removed_map, side="product"
        )
    return removed_sinks


def _find_participant_for_map(participants, map_number: int, side: str) -> str:
    """Find the participant (side='reactant'|'product') owning an atom map."""
    for p in participants:
        if p.side != side:
            continue
        if map_number in p.atom_map_numbers:
            return p.participant_id
    return "unknown_source"
