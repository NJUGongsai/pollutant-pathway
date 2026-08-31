# BBD Route Expansion — Submission Package

**Date**: 2026-08-30
**Generator**: `reaction_analogy/expand_bbd_routes.py` (BFS, depth D=3, K1=5, K2=5)
**Scoring**: v3.2 no-selector (uniform w=1/3) + ion fragment filter
**Source**: `feat/bbd-v32-ion-filter` branch (v3.2 models, no retraining)

## Files

| File | Content |
|------|---------|
| `edges.jsonl` | Full multi-depth edge table (9 required fields + extensions) |
| `nodes.jsonl` | Node table (node_id, case_id, depth, smiles, canonical_smiles, is_root, n_children, path_score) |
| `MANIFEST.sha256` | SHA256 hashes |

## Edge Table Fields

| Field | Description |
|-------|-------------|
| `source_smiles` | Substrate SMILES (isomeric canonical) |
| `product_smiles` | Product SMILES (isomeric canonical, max fragment) |
| `source_node_id` | Source node ID: `{case_id}:{depth}:{sha1[:12]}` |
| `product_node_id` | Product node ID |
| `edge_score` | ns_score = max over sources of (p_source / 3) (no-selector, shadow mechanism) |
| `rank` | Rank of this product among source node's candidates (1-based) |
| `depth` | Product node depth (root=0) |
| `parent_case_id` | The blind parent case ID (FR-BBD3-*) |
| `parent_copy_filtered` | Boolean: product == source substrate (stereo-blind) |
| `cycle` | Boolean: product canonical appears in ancestor chain |
| `product_in_frontier` | Boolean: product was selected for further expansion (top-K, non-ion, non-cycle) |
| `product_ion_filtered` | Boolean: product is an ion/inorganic fragment (sunk to bottom) |
| `source` | Engine source(s): uspto, envipath, retrieval, or combinations |
| `p_uspto` / `p_envipath` / `p_retrieval` | Per-source ranker probabilities |
| `n_candidates_at_source` | Total candidates from this source node |

## Node Table Fields

| Field | Description |
|-------|-------------|
| `node_id` | Content hash: `{case_id}:{depth}:{sha1[:12]}` |
| `case_id` | Blind parent case ID |
| `depth` | 0 (root), 1, 2, or 3 |
| `smiles` | SMILES |
| `canonical_smiles` | Stereo-blind canonical SMILES |
| `is_root` | Boolean: is this the blind parent? |
| `n_children` | Number of outgoing edges |
| `path_score` | Product of edge_scores from root to this node (path confidence) |

## Scoring Method

- **Per-source rankers**: 3 LightGBM models (uspto/envipath/retrieval), trained on RHEA reactions with hard negative mining (v3.1 training)
- **No-selector**: uniform weights w=1/3; `ns_score = max over candidate's sources of (p_source / 3)` (shadow mechanism for multi-source candidates)
- **Ion filter**: 28-species white-list (fail-closed); ions sunk to bottom, not deleted

## Generation-1 Local Results (sanity, stereo-blind)

| Metric | Value |
|--------|-------|
| Hit@1 | 33.7% (29/86) |
| Hit@10 | 68.6% (59/86) |
| MRR@10 | 0.4642 |

These match v3.2 exactly (depth-1 reuses v3.2 pool, not recomputed).

## Structure

| Depth | Nodes | Edges | Frontier |
|-------|-------|-------|----------|
| 0 | 93 | 0 | 465 |
| 1 | 465 | 15,222 | 2,174 |
| 2 | 2,174 | 96,179 | 9,969 |
| 3 | 9,969 | 499,268 | 0 |
| Total | 12,701 | 610,669 | — |

## Notes

- `path_score` is an auxiliary field for path-level confidence. The official scoring口径 is defined by the evaluator (senior's spec).
- Downstream (any-generation) scoring requires the v0.3 route answer key (not available locally; to be scored by the evaluator on their server).
- Determinism: double-run byte-identical (node IDs are content hashes, sorting is deterministic).
