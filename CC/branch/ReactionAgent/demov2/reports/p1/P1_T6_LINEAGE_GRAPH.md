# P1-T6: Bipartite fragment-lineage graph — checkpoint

- timestamp: 2026-07-30T04:30Z (UTC)
- task: P1-T6 Bipartite fragment-lineage graph
- verdict: **UNIT_CONTRACT_COMPLETE**
- preflight: BLOCKED (rdkit_absent + required_case_missing — does not block T6 unit contract; resolver operates on formal atom mapping only, no chemistry fabricated)

## 1. Scope

Implements the bipartite fragment-lineage graph resolver per `final_design` §9
(= brief §12):

- `build_lineage_graph(participants, mapping_report) -> LineageResolution` —
  builds the reactant↔product bipartite graph with §9.1 edge features (9
  dimensions), detects ties / splits / merges / atom transfers, records
  ambiguity_sets, and returns a LineageResolution.
- `resolve_lineages(graph) -> list[ResolvedTransformedLineage]` — converts
  graph hypotheses into resolved transformed lineages with the ambiguity
  verdict (none / partial / critical).

## 2. Files

| file | purpose |
|------|---------|
| `reaction_agent/lineage/__init__.py` | package exports |
| `reaction_agent/lineage/resolver.py` | `build_lineage_graph()` + `resolve_lineages()` + `_build_edges()` |
| `tests/p1/test_lineage_graph.py` | 41 contract tests (14 regression + 3 prohibitions + hard Gate + stable ID + resolution types) |
| `reports/p1/lineage_regression_cases.json` | 14 regression cases with nodes/edges/resolution/ambiguity/eligibility |
| `reports/p1/P1_T6_LINEAGE_GRAPH.md` | this checkpoint |

NOT modified: P0 schemas (`schemas/lineage.py`, `schemas/p1_entities.py`,
`schemas/mapping.py`, `schemas/evidence.py`, `schemas/common.py`),
`reports/p0/`, `../benchmark/`, `../core/`.

## 3. TDD evidence

### RED (Step 2)
```
.venv/bin/python -m pytest tests/p1/test_lineage_graph.py -q -p no:cacheprovider -ra
→ 39 failed, 2 passed (ModuleNotFoundError: No module named 'reaction_agent.lineage')
```
(2 passed = documentation test + canonical_hash basic-type test.)

### GREEN (Step 4)
```
.venv/bin/python -m pytest tests/p1/test_lineage_graph.py -q -p no:cacheprovider -ra
→ 41 passed in 0.14s
```

Initial GREEN had 1 failure (`test_no_independent_side_picking_weak_cross_edge_ignored`:
a weak spurious cross edge with overlapping atoms but unequal strength was being
returned as a resolved lineage). Root cause: the overlap detection treated ALL
overlaps as ties, including unbalanced ones. Fixed by distinguishing:
- **Equal-strength overlap** (same shared_mapped_heavy_atoms) → tie → critical
  ambiguity (both lineages retained with ambiguity="critical").
- **Unequal-strength overlap** (different shared_mapped_heavy_atoms) → the
  weaker edge is a "weak cross edge" → NOT a resolved lineage (recorded in
  atom_transfer_edges as diagnostic, removed from transformed lineages).

This distinction is critical for §9.2 rule 1 (no independent side picking):
a weak spurious cross edge must NOT become a resolved transformed lineage.

### Step 6 (full regression)
```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
→ 512 passed in 0.48s (471 baseline + 41 T6, 0 fail/error/skip/xfail/xpass)

.venv/bin/python scripts/run_p0_gate.py
→ 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
```

## 4. §9.1 Edge features (9 dimensions)

Each `LineageEdge` carries all 9 §9.1 features:

| feature | computation |
|---------|-------------|
| `shared_mapped_heavy_atoms` | count of formal atom pairs for the (reactant, product) edge |
| `reactant_retention_fraction` | shared / total_mapped_reactant (len(atom_map_numbers) or distinct atoms) |
| `product_origin_fraction` | shared / total_mapped_product |
| `changed_mapped_atoms` | reactant atoms where changed_atom_fraction > 0 |
| `bond_edit_participation` | bool: changed_atom_fraction > 0 on either side |
| `transferred_atom_sets` | from mechanistic evidence (empty if formal only — §10.4) |
| `scaffold_continuity` | = reactant_retention_fraction (proxy; rdkit absent) |
| `role_compatibility` | transformed_substrate ↔ transformed_product (True if no roles) |
| `mapping_quality` | 1.0 (fully_mapped) / 0.6 (partial) / 0.4 (ambiguous) / 0.0 (unmapped); -0.2 for MCS/center_pair fallback |

## 5. §9.2 Three core prohibitions (verified)

### Prohibition 1: NO independent side picking
- **Evidence**: `test_no_independent_side_picking` — 2 reactants + 2 products
  with edges r1→p1 (5 atoms) and r2→p2 (4 atoms). Resolver produces r1→p1 and
  r2→p2 (from EDGES), NOT r1→p2 or r2→p1.
- **Evidence**: `test_no_independent_side_picking_weak_cross_edge_ignored` —
  r1→p1 (5 atoms) + r1→p2 (1 atom, overlapping). The weak cross edge r1→p2 is
  NOT a resolved lineage (only r1→p1 is returned).

### Prohibition 2: NO tuple max() silent tie-breaking
- **Evidence**: `test_critical_tie_not_silently_resolved` — r1→p1 (4 atoms) +
  r1→p2 (4 atoms, overlapping). Equal-strength overlap → ambiguity_set, NOT a
  single silently-picked lineage. `strict_lineages` count = 0 (not 1).
- **Evidence**: `test_tie_produces_ambiguity_set_or_quarantine` — tie →
  `ambiguity_sets` non-empty OR quality=unresolved/failed.

### Prohibition 3: NO forced single primary pair
- **Evidence**: `test_no_forced_single_primary_pair` — split (r1→p1 + r1→p2,
  non-overlapping). Both lineages returned (`len >= 2`), no forced primary.
- **Evidence**: `test_no_forced_primary_when_independent_lineages` — 2
  independent lineages (r1→p1, r2→p2), both resolved, none failed.
- **Design**: `is_primary=False` for ALL LineageHypothesis entries (§9.2 rule 3).

## 6. §9.3 / §12.6 proline/2OG hard Gate

### Case A: correct resolution (CURATED fixture)
- `test_proline_2og_correct_resolution_curated` — CURATED fixture
  (hand-encoded correct chemistry, NOT real data). Resolves:
  - proline (r1) → hydroxyproline (p1) ✓
  - 2OG (r2) → succinate (p2) ✓
  - O2 (r3) → hydroxyproline (p1) recorded as atom_transfer_edge ✓
- `test_forbidden_2og_to_hydroxyproline_not_in_strict` — 2OG→hydroxyproline
  is NOT in the strict/conditional index. The forbidden pairing never appears
  as a resolved lineage (no edge supports it; and if it did, it would be
  critical, not strict).

### Case B: quarantine when mapping insufficient
- `test_proline_2og_quarantine_when_mapping_insufficient` — unmapped reaction
  → 0 strict lineages, quality=unresolved. No fabrication.

### Real source: required_case_missing
- `test_proline_2og_required_case_missing_not_fabricated` — documents the
  Preflight BLOCKED status. Real proline/2OG source record is
  `required_case_missing`. The hard Gate is verified on the CURATED fixture
  (Case A logic) and the quarantine path (Case B logic). Real-data
  verification is blocked until the user supplies a RHEA/BRENDA source record.

**Verdict: Case A (curated) + Case B (quarantine) verified. NEVER 2OG→hydroxyproline.**

## 7. §12.4 Stable lineage ID (verified)

- `test_lineage_id_stable_atom_order_invariant` — same mapping, atom pairs in
  different order → identical lineage_id (sorting makes it order-invariant).
- `test_lineage_id_changes_when_participants_differ` — different reactant →
  different lineage_id.
- `test_lineage_id_changes_when_reaction_differs` — different reaction
  (input_hash) → different lineage_id.
- `test_lineage_id_contains_resolver_version` — RESOLVER_VERSION embedded in
  resolution_id for traceability.
- `test_regression_14_atom_order_permutation` — permutation [4,2,0,3,1] vs
  [0,1,2,3,4] → same lineage_id.

**lineage_id = `lin_{canonical_hash({reaction, reactant, product, sorted_atom_pairs, version, kind})[:12]}`**

## 8. 14 regression cases (§12.5)

| # | case | fixture | resolution | strict eligible | notes |
|---|------|---------|------------|-----------------|-------|
| 1 | proline hydroxylation 2OG/O2 | curated | r1→p1 + r2→p2 + O transfer | 2 | §9.3 canonical; forbidden 2OG→hydroxyproline NOT in strict |
| 2 | redox with NAD(P) | synthetic | r1→p1 (substrate→product) | 1 | NAD↔NADH weak edge (carrier, not transformed) |
| 3 | oxygen incorporation | synthetic | r1→p1 + O transfer | 1 | O2→product recorded as atom_transfer_edge |
| 4 | hydrolysis | synthetic | r1→p1 + r1→p2 (split) + H2O transfer | 2 | substrate splits, H2O contributes O |
| 5 | transferase | synthetic | r1→p1 + r2→p2 + CH3 transfer | 2 | group transfer (CH3 from donor to acceptor) |
| 6 | decarboxylation | synthetic | r1→p1 + r1→p2 (split) | 2 | CO2 from substrate (non-overlapping fragment) |
| 7 | cleavage | synthetic | r1→p1 + r1→p2 (split) | 2 | non-overlapping fragments |
| 8 | condensation | synthetic | r1→p1 + r2→p1 (merge) | 2 | two reactants → one product |
| 9 | split | synthetic | split_hypotheses recorded | 2 | non-overlapping fragments |
| 10 | merge | synthetic | merge_hypotheses recorded | 2 | two reactants → one product |
| 11 | equal-score tie | synthetic | ambiguity_set, 0 strict | 0 | tie → critical, not silently resolved |
| 12 | partial mapping | synthetic | partially_resolved | 1 | partial mapping → partial ambiguity |
| 13 | MCS fallback | synthetic | partially_resolved | 1 | MCS fallback downgrades quality |
| 14 | atom-order permutation | synthetic | same lineage_id as forward | 1 | order-invariant ID |

## 9. Resolution types supported (§9.2)

| type | test | evidence |
|------|------|----------|
| zero | `test_zero_lineages_unmapped` | unmapped → 0 lineages, quality=unresolved |
| one | `test_one_lineage_simple` | simple A→B → 1 resolved lineage |
| multiple independent | `test_multiple_independent_lineages` | 2 reactants → 2 products |
| split | `test_split_resolution` | 1 reactant → 2 products (non-overlapping) |
| merge | `test_merge_resolution` | 2 reactants → 1 product |
| atom transfer | `test_atom_transfer_recorded` | O2→product in atom_transfer_edges |
| ambiguity set | `test_critical_tie_not_silently_resolved` | equal-score tie → ambiguity_set |
| unresolved | `test_failure_reason_recorded_when_unresolved` | failure_reason recorded |

## 10. Deviations / concerns

- **rdkit absent**: `scaffold_continuity` uses `reactant_retention_fraction` as
  proxy (no heavy-atom counting). `changed_mapped_atoms` uses
  `changed_atom_fraction > 0` as proxy. Replace with real bond-edit analysis
  when rdkit available.
- **proline/2OG real source**: `required_case_missing` (Preflight BLOCKED).
  Hard Gate verified on CURATED fixture (Case A) + quarantine path (Case B).
  Real-data verification blocked until user supplies RHEA/BRENDA source record.
- **atom transfer detection heuristic**: `mapped_fraction == 0.0 AND shared <= 2
  AND another edge to same product has scaffold source`. This correctly
  classifies O2/H2O as atom transfer donors, but may need refinement for
  edge cases (e.g. a small mapped molecule that IS the substrate). Conservative:
  when in doubt, the edge remains a transformed lineage (not silently removed).
- **weak cross edge**: overlapping + unequal strength → weaker edge removed
  from lineages, recorded in `atom_transfer_edges` as `type=weak_cross_edge`.
  This prevents spurious cross edges from becoming resolved lineages (§9.2
  rule 1) while preserving diagnostic traceability.
- **resolve_lineages returns ALL lineages** (including critical) so callers
  can inspect them. Critical-ambiguity lineages have `ambiguity="critical"` and
  must be filtered out of the strict production index by the caller. The
  `ambiguity_sets` in the graph provides the tie grouping for traceability.
