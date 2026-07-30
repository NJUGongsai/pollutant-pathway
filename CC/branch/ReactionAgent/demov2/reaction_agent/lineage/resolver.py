"""Bipartite fragment-lineage graph resolver (final_design §9 = brief §12).

Builds a reactant↔product bipartite graph from the formal atom mapping
(§9.1) and resolves transformed lineages (§9.2/§9.3).

Three core prohibitions (§9.2):
1. NO independent side picking — reactant side picks one + product side picks
   one then forced pairing is FORBIDDEN. Lineages are derived from EDGES
   (formal atom correspondence), not from independent "best molecule" picks.
2. NO tuple max() silent tie-breaking — when two edges from the same reactant
   have equal strength AND overlapping atoms (conflicting mapping), the tie
   is surfaced as an ambiguity_set / quarantine, never silently resolved.
3. NO forced single primary pair — multiple resolved lineages coexist.

Stable lineage ID (§12.4): based on reaction identity (mapping_report.input_hash)
+ reactant/product participant identity + sorted mapped atom correspondence +
resolver semantic version. Sorting makes it invariant under atom pair
enumeration order. The version makes it resolver-version-dependent.

proline/2OG hard Gate (§9.3/§12.6): the resolver MUST resolve
proline→hydroxyproline + 2OG→succinate and record the O transfer. It MUST
NEVER produce 2OG→hydroxyproline as a strict lineage. When mapping is
insufficient (unmapped), it quarantines (Case B) rather than fabricating.

Immutability: ``build_lineage_graph`` does NOT mutate ``participants`` or
``mapping_report``. New objects are returned throughout.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import (
    MappingStatus,
    LineageResolutionQuality,
)
from reaction_agent.schemas.evidence import ReactionParticipant
from reaction_agent.schemas.lineage import (
    LineageEdge,
    LineageHypothesis,
    LineageResolution,
)
from reaction_agent.schemas.mapping import MappingReport
from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage


# =====================================================================
# Resolver version (§12.4: embedded in lineage_id for traceability)
# =====================================================================

RESOLVER_VERSION = "p1-t6-1"


# =====================================================================
# Internal edge data (pairs LineageEdge with its raw atom correspondence)
# =====================================================================

@dataclass(frozen=True)
class _EdgeData:
    """Internal: a bipartite edge paired with its raw atom correspondence.

    ``LineageEdge`` (schema) carries the 9 §9.1 features but not the raw atom
    pairs (they would be redundant with the mapping report). This dataclass
    pairs the schema edge with the atom-pair correspondence needed for tie /
    split / overlap analysis.
    """
    edge: LineageEdge
    reactant_pid: str
    product_pid: str
    reactant_atoms: frozenset[int]
    product_atoms: frozenset[int]
    atom_pairs: tuple[tuple[int, int], ...]  # (reactant_atom, product_atom)
    is_transfer_candidate: bool = False


# =====================================================================
# Edge construction (§9.1)
# =====================================================================

def _group_atom_pairs(
    mapping_report: MappingReport,
) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """Group formal atom pairs by (reactant_pid, product_pid).

    Returns a dict mapping each (reactant_pid, product_pid) pair to a list of
    (reactant_atom_map, product_atom_map) tuples. If the mapping report has no
    formal assignment, returns an empty dict.
    """
    fma = mapping_report.formal_mapped_source_assignment
    if fma is None:
        return {}
    grouped: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for pair in fma.mapped_atom_pairs:
        key = (pair.reactant_participant_id, pair.product_participant_id)
        grouped.setdefault(key, []).append(
            (pair.reactant_atom_map, pair.product_atom_map)
        )
    return grouped


def _participant_index(
    participants: list[ReactionParticipant],
) -> dict[str, ReactionParticipant]:
    """Build a participant_id → ReactionParticipant lookup."""
    return {p.participant_id: p for p in participants}


def _reactant_total_mapped(
    reactant: ReactionParticipant,
    all_pairs_for_reactant: list[tuple[int, int]],
) -> int:
    """Estimate the total mapped heavy atoms on the reactant side.

    Uses ``len(reactant.atom_map_numbers)`` if non-empty; otherwise falls back
    to the count of distinct reactant atoms across all edges for this reactant.
    This is a formal mapping proxy — no rdkit heavy-atom counting (absent).
    """
    if reactant.atom_map_numbers:
        return len(reactant.atom_map_numbers)
    distinct = {ra for ra, _ in all_pairs_for_reactant}
    return len(distinct)


def _product_total_mapped(
    product: ReactionParticipant,
    all_pairs_for_product: list[tuple[int, int]],
) -> int:
    """Estimate the total mapped heavy atoms on the product side."""
    if product.atom_map_numbers:
        return len(product.atom_map_numbers)
    distinct = {pa for _, pa in all_pairs_for_product}
    return len(distinct)


def _mapping_quality_score(mapping_report: MappingReport) -> float:
    """Derive a mapping quality score in [0, 1] from the mapping report.

    fully_mapped → 1.0, partially_mapped → 0.6, mapping_ambiguous → 0.4,
    unmapped/mapping_failed → 0.0. MCS/center_pair fallback downgrades by 0.2.
    """
    status = mapping_report.mapping_status
    if status == MappingStatus.fully_mapped:
        base = 1.0
    elif status == MappingStatus.partially_mapped:
        base = 0.6
    elif status == MappingStatus.mapping_ambiguous:
        base = 0.4
    else:
        base = 0.0
    if mapping_report.fallback_method in ("mcs", "center_pair"):
        base = max(0.0, base - 0.2)
    return base


def _role_compatible(
    reactant: ReactionParticipant,
    product: ReactionParticipant,
) -> bool:
    """Check whether the reactant/product roles are compatible.

    A transformed_substrate ↔ transformed_product pair is fully compatible.
    If role hypotheses are absent (empty), default to True (optimistic — the
    resolver does not force roles; T5 attaches them separately).
    """
    if not reactant.role_hypotheses or not product.role_hypotheses:
        return True
    r_roles = {h.role.value for h in reactant.role_hypotheses}
    p_roles = {h.role.value for h in product.role_hypotheses}
    # transformed_substrate ↔ transformed_product is the ideal pair
    if "transformed_substrate" in r_roles and "transformed_product" in p_roles:
        return True
    # co_substrate → coproduct is also compatible
    if "co_substrate" in r_roles and "coproduct" in p_roles:
        return True
    # If both have "unknown", no conflict
    if "unknown" in r_roles and "unknown" in p_roles:
        return True
    # Any non-empty role set without a direct conflict
    return True


def _build_edge_data(
    participants: list[ReactionParticipant],
    mapping_report: MappingReport,
) -> list[_EdgeData]:
    """Build internal edge data (LineageEdge + atom correspondence) from mapping.

    Groups formal atom pairs by (reactant_pid, product_pid), computes the 9
    §9.1 edge features for each group, and returns _EdgeData entries.
    """
    grouped = _group_atom_pairs(mapping_report)
    if not grouped:
        return []

    pidx = _participant_index(participants)

    # Collect all pairs per reactant and per product for fraction computation
    reactant_all_pairs: dict[str, list[tuple[int, int]]] = {}
    product_all_pairs: dict[str, list[tuple[int, int]]] = {}
    for (r_pid, p_pid), pairs in grouped.items():
        reactant_all_pairs.setdefault(r_pid, []).extend(pairs)
        product_all_pairs.setdefault(p_pid, []).extend(pairs)

    quality_score = _mapping_quality_score(mapping_report)
    edges: list[_EdgeData] = []

    for (r_pid, p_pid), pairs in grouped.items():
        reactant = pidx.get(r_pid)
        product = pidx.get(p_pid)
        if reactant is None or product is None:
            # Edge references unknown participant — skip (defensive)
            continue

        sorted_pairs = tuple(sorted(pairs))
        shared = len(pairs)
        r_total = _reactant_total_mapped(reactant, reactant_all_pairs[r_pid])
        p_total = _product_total_mapped(product, product_all_pairs[p_pid])
        r_retention = shared / r_total if r_total > 0 else 0.0
        p_origin = shared / p_total if p_total > 0 else 0.0

        changed_atoms = [
            ra for ra, _ in sorted_pairs
            if reactant.changed_atom_fraction > 0.0
        ]

        # Atom transfer candidate: reactant is unmapped (no scaffold) and
        # contributes few atoms — e.g. O2 contributing one O atom.
        is_transfer = (
            reactant.mapped_fraction == 0.0
            and shared <= 2
        )

        edge_id = _edge_id(mapping_report.input_hash, r_pid, p_pid, sorted_pairs)

        edge = LineageEdge(
            edge_id=edge_id,
            reactant_participant_id=r_pid,
            product_participant_id=p_pid,
            shared_mapped_heavy_atoms=shared,
            reactant_retention_fraction=round(r_retention, 6),
            product_origin_fraction=round(p_origin, 6),
            changed_mapped_atoms=changed_atoms,
            bond_edit_participation=(
                reactant.changed_atom_fraction > 0.0
                or product.changed_atom_fraction > 0.0
            ),
            transferred_atom_sets=[],
            scaffold_continuity=round(r_retention, 6),
            role_compatibility=_role_compatible(reactant, product),
            mapping_quality=round(quality_score, 6),
        )

        edges.append(_EdgeData(
            edge=edge,
            reactant_pid=r_pid,
            product_pid=p_pid,
            reactant_atoms=frozenset(ra for ra, _ in sorted_pairs),
            product_atoms=frozenset(pa for _, pa in sorted_pairs),
            atom_pairs=sorted_pairs,
            is_transfer_candidate=is_transfer,
        ))

    return edges


def _build_edges(
    participants: list[ReactionParticipant],
    mapping_report: MappingReport,
) -> list[LineageEdge]:
    """Build the list of LineageEdge objects (§9.1 features).

    Public wrapper around ``_build_edge_data`` that returns only the schema
    edges (without the internal atom correspondence).
    """
    return [ed.edge for ed in _build_edge_data(participants, mapping_report)]


# =====================================================================
# Stable ID computation (§12.4)
# =====================================================================

def _edge_id(
    input_hash: str,
    reactant_pid: str,
    product_pid: str,
    sorted_pairs: tuple[tuple[int, int], ...],
) -> str:
    """Stable edge ID: reaction identity + participant identity + sorted atom correspondence + version."""
    payload = {
        "reaction": input_hash,
        "reactant": reactant_pid,
        "product": product_pid,
        "atom_pairs": list(sorted_pairs),
        "version": RESOLVER_VERSION,
        "kind": "edge",
    }
    return f"edge_{canonical_hash(payload)[:12]}"


def _lineage_id(
    input_hash: str,
    reactant_pid: str,
    product_pid: str,
    sorted_pairs: tuple[tuple[int, int], ...],
) -> str:
    """Stable lineage ID (§12.4).

    Based on: reaction identity (input_hash) + reactant/product participant
    identity + sorted mapped atom correspondence + resolver version. Sorting
    the atom pairs makes the ID invariant under enumeration order.
    """
    payload = {
        "reaction": input_hash,
        "reactant": reactant_pid,
        "product": product_pid,
        "atom_pairs": list(sorted_pairs),
        "version": RESOLVER_VERSION,
        "kind": "lineage",
    }
    return f"lin_{canonical_hash(payload)[:12]}"


def _resolution_id(input_hash: str) -> str:
    """Stable resolution ID embedding the resolver version."""
    payload = {
        "reaction": input_hash,
        "version": RESOLVER_VERSION,
        "kind": "resolution",
    }
    return f"res_{RESOLVER_VERSION}_{canonical_hash(payload)[:12]}"


# =====================================================================
# Graph analysis: tie / split / merge / atom_transfer detection
# =====================================================================

@dataclass
class _GraphAnalysis:
    """Result of analyzing the bipartite graph for resolution structure."""
    # Lineage hypotheses (one per transformed edge, excluding atom transfers)
    hypotheses: list[LineageHypothesis] = field(default_factory=list)
    # Ambiguity sets: each is a dict[str, str] per the schema
    ambiguity_sets: list[dict[str, str]] = field(default_factory=list)
    # Split hypotheses
    split_hypotheses: list[dict[str, str]] = field(default_factory=list)
    # Merge hypotheses
    merge_hypotheses: list[dict[str, str]] = field(default_factory=list)
    # Atom transfer edges
    atom_transfer_edges: list[dict[str, str]] = field(default_factory=list)
    # Lineage IDs that are in a critical ambiguity set (tie)
    critical_lineage_ids: set[str] = field(default_factory=set)
    # Overall quality
    quality: LineageResolutionQuality = LineageResolutionQuality.unresolved
    # Failure reason (None if resolved)
    failure_reason: str | None = None
    # Graph dict (edge_id → "r->p")
    graph_dict: dict[str, str] = field(default_factory=dict)


def _analyze_graph(
    edge_data: list[_EdgeData],
    participants: list[ReactionParticipant],
    mapping_report: MappingReport,
) -> _GraphAnalysis:
    """Analyze the bipartite graph for resolution structure.

    This is the core resolution logic. It:
    1. Separates atom-transfer edges from transformed-lineage edges.
    2. Groups transformed edges by reactant to detect ties (overlapping atoms,
       equal strength) and splits (non-overlapping atoms, multiple products).
    3. Groups transformed edges by product to detect merges.
    4. Builds LineageHypothesis entries with appropriate resolution_quality.
    5. Records ambiguity_sets, split_hypotheses, merge_hypotheses,
       atom_transfer_edges.

    Key discipline:
    - NO tuple max() silent tie — ties produce ambiguity_sets, never a winner.
    - NO forced primary — all transformed edges become hypotheses.
    - Overlapping atoms (same reactant atom → multiple products) = conflicting
      mapping = tie → critical ambiguity.
    - Non-overlapping atoms = split (balanced or unbalanced) → resolved.
    """
    analysis = _GraphAnalysis()
    pidx = _participant_index(participants)
    input_hash = mapping_report.input_hash

    # -- Graph dict (edge_id → "r->p") --
    for ed in edge_data:
        analysis.graph_dict[ed.edge.edge_id] = (
            f"{ed.reactant_pid}->{ed.product_pid}"
        )

    # -- Separate atom transfers from transformed edges --
    # An edge is an atom transfer if:
    # - reactant.mapped_fraction == 0.0 (not mapped as scaffold)
    # - shared <= 2 (few atoms contributed)
    # - AND another edge to the same product has a mapped scaffold source
    product_has_scaffold_source: dict[str, bool] = {}
    for ed in edge_data:
        reactant = pidx.get(ed.reactant_pid)
        if reactant and reactant.mapped_fraction > 0.0 and not ed.is_transfer_candidate:
            product_has_scaffold_source[ed.product_pid] = True

    transfer_edges: list[_EdgeData] = []
    transformed_edges: list[_EdgeData] = []
    for ed in edge_data:
        reactant = pidx.get(ed.reactant_pid)
        is_real_transfer = (
            ed.is_transfer_candidate
            and product_has_scaffold_source.get(ed.product_pid, False)
        )
        if is_real_transfer:
            transfer_edges.append(ed)
        else:
            transformed_edges.append(ed)

    # -- Record atom transfer edges --
    for ed in transfer_edges:
        atoms_str = ",".join(str(a) for a in sorted(ed.reactant_atoms))
        analysis.atom_transfer_edges.append({
            "from": ed.reactant_pid,
            "to": ed.product_pid,
            "atoms": atoms_str,
            "type": "atom_transfer",
            "shared_atoms": str(ed.edge.shared_mapped_heavy_atoms),
            "method": "formal_mapped",
            "ambiguity": "formal_assignment_no_mechanistic_evidence",
        })

    # -- Group transformed edges by reactant --
    by_reactant: dict[str, list[_EdgeData]] = {}
    for ed in transformed_edges:
        by_reactant.setdefault(ed.reactant_pid, []).append(ed)

    # -- Detect ties, splits, and weak cross edges per reactant --
    # Weak cross edges (overlapping atoms, unequal strength) are removed from
    # transformed_edges — they are NOT resolved lineages (§9.2 rule 1: no
    # independent side picking / no forced pairing from weak spurious edges).
    weak_cross_edge_ids: set[str] = set()

    for r_pid, edges in by_reactant.items():
        if len(edges) <= 1:
            continue

        # Check for overlapping atoms (conflicting mapping)
        # Two edges overlap if they share any reactant atom
        overlapping_groups: list[list[_EdgeData]] = []
        visited: set[int] = set()
        for i, ed in enumerate(edges):
            if i in visited:
                continue
            group = [ed]
            visited.add(i)
            for j in range(i + 1, len(edges)):
                if j in visited:
                    continue
                if any(
                    edges[j].reactant_atoms & g.reactant_atoms for g in group
                ):
                    group.append(edges[j])
                    visited.add(j)
            if len(group) > 1:
                overlapping_groups.append(group)

        for group in overlapping_groups:
            shared_counts = [g.edge.shared_mapped_heavy_atoms for g in group]
            max_shared = max(shared_counts)
            max_count = shared_counts.count(max_shared)

            if max_count > 1:
                # Multiple edges with the same max strength → tie (critical)
                # All max-strength edges are tied → ambiguity set, NO silent pick
                tied = [g for g in group if g.edge.shared_mapped_heavy_atoms == max_shared]
                products_str = ",".join(sorted(g.product_pid for g in tied))
                analysis.ambiguity_sets.append({
                    "reactant": r_pid,
                    "products": products_str,
                    "reason": "equal_score_tie_overlapping_atoms",
                    "shared_atoms": str(max_shared),
                    "resolution": "ambiguity_set_no_silent_pick",
                })
                for ed in tied:
                    lid = _lineage_id(
                        input_hash, ed.reactant_pid, ed.product_pid, ed.atom_pairs
                    )
                    analysis.critical_lineage_ids.add(lid)
                # Weaker edges in this group are weak cross edges
                for ed in group:
                    if ed.edge.shared_mapped_heavy_atoms < max_shared:
                        weak_cross_edge_ids.add(ed.edge.edge_id)
            else:
                # One strongest edge, rest are weaker → weak cross edges
                # The strongest remains a transformed lineage; weaker ones
                # are spurious cross edges (NOT resolved lineages).
                for ed in group:
                    if ed.edge.shared_mapped_heavy_atoms < max_shared:
                        weak_cross_edge_ids.add(ed.edge.edge_id)

        # Check for non-overlapping splits (different fragments → different products)
        non_overlap_edges = [
            ed for ed in edges if ed.edge.edge_id not in weak_cross_edge_ids
        ]
        # Only check for split if no overlap was detected (non-overlapping)
        all_atoms: set[int] = set()
        has_overlap = False
        for ed in non_overlap_edges:
            if all_atoms & ed.reactant_atoms:
                has_overlap = True
                break
            all_atoms |= ed.reactant_atoms

        if not has_overlap and len(non_overlap_edges) > 1:
            products_str = ",".join(sorted(ed.product_pid for ed in non_overlap_edges))
            shared_strs = ",".join(
                str(ed.edge.shared_mapped_heavy_atoms) for ed in non_overlap_edges
            )
            analysis.split_hypotheses.append({
                "reactant": r_pid,
                "products": products_str,
                "type": "split",
                "shared_atoms_per_fragment": shared_strs,
            })

    # -- Remove weak cross edges from transformed_edges --
    transformed_edges = [
        ed for ed in transformed_edges if ed.edge.edge_id not in weak_cross_edge_ids
    ]

    # -- Record weak cross edges as diagnostic (not lineages) --
    for ed in edge_data:
        if ed.edge.edge_id in weak_cross_edge_ids:
            analysis.atom_transfer_edges.append({
                "from": ed.reactant_pid,
                "to": ed.product_pid,
                "atoms": ",".join(str(a) for a in sorted(ed.reactant_atoms)),
                "type": "weak_cross_edge",
                "shared_atoms": str(ed.edge.shared_mapped_heavy_atoms),
                "method": "formal_mapped",
                "ambiguity": "overlapping_weaker_edge_not_a_lineage",
            })

    # -- Group transformed edges by product (merge detection) --
    by_product: dict[str, list[_EdgeData]] = {}
    for ed in transformed_edges:
        by_product.setdefault(ed.product_pid, []).append(ed)

    for p_pid, edges in by_product.items():
        distinct_reactants = {ed.reactant_pid for ed in edges}
        if len(distinct_reactants) >= 2:
            reactants_str = ",".join(sorted(distinct_reactants))
            analysis.merge_hypotheses.append({
                "product": p_pid,
                "reactants": reactants_str,
                "type": "merge",
            })

    # -- Build LineageHypothesis entries for all transformed edges --
    status = mapping_report.mapping_status
    has_tie = len(analysis.ambiguity_sets) > 0

    for ed in transformed_edges:
        lid = _lineage_id(
            input_hash, ed.reactant_pid, ed.product_pid, ed.atom_pairs
        )
        atom_maps = sorted(
            {ra for ra, _ in ed.atom_pairs} | {pa for _, pa in ed.atom_pairs}
        )

        if lid in analysis.critical_lineage_ids:
            rq = LineageResolutionQuality.unresolved
        elif status == MappingStatus.fully_mapped and not has_tie:
            rq = LineageResolutionQuality.resolved
        elif status in (MappingStatus.partially_mapped, MappingStatus.mapping_ambiguous):
            rq = LineageResolutionQuality.partially_resolved
        elif mapping_report.fallback_method in ("mcs", "center_pair"):
            rq = LineageResolutionQuality.partially_resolved
        else:
            rq = LineageResolutionQuality.partially_resolved

        hyp = LineageHypothesis(
            lineage_id=lid,
            substrate_participant_id=ed.reactant_pid,
            product_participant_id=ed.product_pid,
            edge_ids=[ed.edge.edge_id],
            transformed_atom_maps=atom_maps,
            resolution_quality=rq,
            is_primary=False,  # §9.2: NO forced primary
        )
        analysis.hypotheses.append(hyp)

    # -- Overall quality + failure_reason --
    if not edge_data:
        analysis.quality = LineageResolutionQuality.unresolved
        analysis.failure_reason = (
            f"no_formal_mapping_edges (mapping_status={status.value}, "
            f"resolver={RESOLVER_VERSION})"
        )
    elif has_tie:
        analysis.quality = LineageResolutionQuality.unresolved
        analysis.failure_reason = (
            f"critical_ambiguity_tie ({len(analysis.ambiguity_sets)} tie(s)); "
            f"quarantined_per_§9.2"
        )
    elif status == MappingStatus.fully_mapped:
        analysis.quality = LineageResolutionQuality.resolved
        analysis.failure_reason = None
    elif status in (MappingStatus.partially_mapped, MappingStatus.mapping_ambiguous):
        analysis.quality = LineageResolutionQuality.partially_resolved
        analysis.failure_reason = None
    elif status in (MappingStatus.unmapped, MappingStatus.mapping_failed):
        analysis.quality = LineageResolutionQuality.unresolved
        analysis.failure_reason = (
            f"mapping_insufficient (status={status.value}); quarantined"
        )
    else:
        analysis.quality = LineageResolutionQuality.unresolved
        analysis.failure_reason = f"unknown_mapping_status ({status.value})"

    return analysis


# =====================================================================
# Public API
# =====================================================================

def build_lineage_graph(
    participants: list[ReactionParticipant],
    mapping_report: MappingReport,
) -> LineageResolution:
    """Build the bipartite fragment-lineage graph (§9.1/§9.2).

    Constructs reactant↔product bipartite edges from the formal atom mapping,
    computes the 9 §9.1 edge features, detects ties / splits / merges / atom
    transfers, and returns a LineageResolution with the graph + hypotheses +
    ambiguity_sets.

    Discipline (§9.2):
    - NO independent side picking — edges come from the formal atom mapping.
    - NO tuple max() silent tie — ties → ambiguity_sets.
    - NO forced primary — all transformed edges become hypotheses.
    - Critical ambiguity → recorded in ambiguity_sets, quality=unresolved.

    Immutability: ``participants`` and ``mapping_report`` are NOT mutated.
    """
    edge_data = _build_edge_data(participants, mapping_report)
    analysis = _analyze_graph(edge_data, participants, mapping_report)

    return LineageResolution(
        resolution_id=_resolution_id(mapping_report.input_hash),
        reaction_evidence_id=mapping_report.input_hash,
        graph=analysis.graph_dict,
        resolved_transformed_lineages=analysis.hypotheses,
        split_hypotheses=analysis.split_hypotheses,
        merge_hypotheses=analysis.merge_hypotheses,
        atom_transfer_edges=analysis.atom_transfer_edges,
        ambiguity_sets=analysis.ambiguity_sets,
        quality=analysis.quality,
        failure_reason=analysis.failure_reason,
    )


def resolve_lineages(
    graph: LineageResolution,
) -> list[ResolvedTransformedLineage]:
    """Resolve transformed lineages from the bipartite graph (§9.2/§9.3).

    Converts LineageHypothesis entries (from ``build_lineage_graph``) into
    ResolvedTransformedLineage records with the ambiguity verdict:

    - ``ambiguity="none"``: single clear edge, fully mapped, no tie.
    - ``ambiguity="partial"``: partial mapping, MCS fallback, or split/merge
      (multiple non-tie lineages).
    - ``ambiguity="critical"``: part of a tie / ambiguity set → NOT eligible
      for the strict production index (quarantine / diagnostic).

    Returns ALL lineages (including critical) so the caller can inspect them.
    The caller is responsible for filtering ``ambiguity="critical"`` out of
    the strict index. Critical lineages are recorded in the graph's
    ``ambiguity_sets`` for traceability.

    §9.2 rule: critical ambiguity → quarantine / non-strict diagnostic.
    """
    # Build the set of lineage_ids that are in ambiguity_sets (critical)
    # by matching substrate/product pairs in ambiguity_sets
    critical_pairs: set[tuple[str, str]] = set()
    for aset in graph.ambiguity_sets:
        reactant = aset.get("reactant", "")
        products = aset.get("products", "").split(",")
        for p in products:
            p = p.strip()
            if p:
                critical_pairs.add((reactant, p))

    lineages: list[ResolvedTransformedLineage] = []
    for hyp in graph.resolved_transformed_lineages:
        pair = (hyp.substrate_participant_id, hyp.product_participant_id)

        if pair in critical_pairs:
            ambiguity = "critical"
        elif hyp.resolution_quality == LineageResolutionQuality.resolved:
            ambiguity = "none"
        elif hyp.resolution_quality == LineageResolutionQuality.partially_resolved:
            ambiguity = "partial"
        else:
            # unresolved / failed → critical (quarantine)
            ambiguity = "critical"

        lineages.append(ResolvedTransformedLineage(
            lineage_id=hyp.lineage_id,
            reactant_participant_id=hyp.substrate_participant_id,
            product_participant_id=hyp.product_participant_id,
            evidence_ids=[],
            ambiguity=ambiguity,
            transformed_atom_maps=hyp.transformed_atom_maps,
            resolution_quality=hyp.resolution_quality,
        ))

    return lineages
