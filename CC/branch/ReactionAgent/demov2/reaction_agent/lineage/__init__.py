"""P1-T6 package: bipartite fragment-lineage graph resolver (final_design §9).

Implements:
- ``build_lineage_graph(participants, mapping_report) -> LineageResolution`` —
  builds the reactant↔product bipartite graph with §9.1 edge features.
- ``resolve_lineages(graph) -> list[ResolvedTransformedLineage]`` — resolves
  transformed lineages per §9.2/§9.3.

Design references (final_design §9 = brief §12):
- §9.1: bipartite graph, 9 edge features.
- §9.2: NO independent side picking, NO tuple max() silent tie, NO forced
  primary, critical ambiguity → quarantine/non-strict.
- §9.3: proline/2OG regression (proline→hydroxyproline + 2OG→succinate + O
  transfer; NEVER 2OG→hydroxyproline).
- §12.4: stable lineage_id (reaction identity + participant identity + mapped
  atom correspondence + resolver version; order/atom-enumeration invariant).

Discipline:
- Preflight BLOCKED (rdkit absent). The resolver operates on FORMAL atom
  mapping only (§10.4). No chemistry is fabricated; when mapping is
  insufficient, the resolver returns unresolved / ambiguity_set / quarantine.
- Immutability: input participants and mapping_report are NOT mutated.
"""
from reaction_agent.lineage.resolver import (
    RESOLVER_VERSION,
    build_lineage_graph,
    resolve_lineages,
)

__all__ = [
    "RESOLVER_VERSION",
    "build_lineage_graph",
    "resolve_lineages",
]
