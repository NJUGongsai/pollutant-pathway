# BBD Route Expansion — Submission Package (P4.2 Hybrid)

**Date**: 2026-08-31
**Branch**: `feat/bbd-p42-lookup-hybrid` (from `feat/bbd-p41-fix-oracle`)
**Generator**: `reaction_analogy/build_hybrid_submission.py` (depth-1 hybrid) + `reaction_analogy/expand_bbd_routes.py` (depth≥2, P4.1 verbatim)
**Architecture**: Two-layer hybrid — Layer 1 EAWAG known-pathway lookup (Engine D) + Layer 2 v3.2 three-engine prediction (cofactor filter + full-precision re-rank).

## What changed vs P4.1

- **Depth-1 edges rebuilt** from the hybrid predictor: lookup candidates pinned on top
  (when the parent is a recorded EAWAG donor), prediction candidates follow (deduped).
- **Depth ≥ 2 unchanged** (P4.1 verbatim) — multi-depth hybrid expansion is a deliberate
  non-goal (task §2; "不做多步展开的 lookup"). Node IDs are content-hashed, so P4.1
  depth-2 references to depth-1 frontier nodes still resolve.
- New edge field on lookup hits: **`eawag_reactions`** (`["btid#reac_id", …]`) — trace
  each lookup edge to its EAWAG-BBD reaction page (`https://eawag-bbd.ethz.ch/servlets/pageservlet?ptype=r&reacID=<reac_id>`).
- New `source` value: **`eawag_lookup`** (Engine D). Existing `source` values
  (`uspto` / `envipath` / `retrieval` / combos) unchanged for prediction-layer edges.
- New fields on depth-1 edges: `layer` (`lookup` / `prediction`), `cofactor_filtered`.

## Files

| File | Content |
|------|---------|
| `edges.jsonl` | Multi-depth edge table (depth-1 hybrid + depth≥2 P4.1) |
| `nodes.jsonl` | Node table (depth 0/1 hybrid + depth≥2 P4.1) |
| `README_SUBMISSION.md` | This file |
| `MANIFEST.sha256` | SHA256 hashes |

## Three Calibers (stereo-blind, 86 matched answer-key cases)

| Caliber | Definition | Hit@1 | Hit@10 | MRR@10 |
|---------|-----------|-------|--------|--------|
| **A. Hybrid** (main, vs ECLIPSE/enviPath) | Layer 1 lookup pinned + Layer 2 fallback | **90.7%** (78/86) | 96.5% (83/86) | 0.9341 |
| **B. Prediction-only** (academic) | Lookup OFF; v3.2 + cofactor + full-precision | 38.4% (33/86) | 68.6% (59/86) | 0.4987 |
| **C. Lookup-only** (diagnostic) | Layer 1 only (Tanimoto order) | 89.5% (77/86) | 94.2% (81/86) | 0.9167 |

Dual donor==parent 口径 (leak-audit discipline): for each caliber the "no donor==parent"
variant excludes `donor_exact_match` candidates (EAWAG lookup hits + RHEA retrieval
exact-donor hits). Hybrid no-donor==parent Hit@1 = N/A (lookup tier is entirely
exact-donor). Prediction no-donor==parent Hit@1 = 23.3% (20/86), Hit@10 = 48.8%.

**Three calibers are disclosed side-by-side by design.** The answer key and the EAWAG
library (`donor_product.jsonl`) share provenance (both EAWAG-BBD), so the hybrid caliber
is **not** an independent generalization result — it is the known-pathway-lookup mode
(isomorphic to enviPath's documented "known-pathway lookup" baseline). The prediction
caliber is the independent generalization number; it is the figure to compare against
pure-prediction baselines. See `BBD_P42_HYBRID_REPORT_2026-08-31.md` for the full audit.

## Gate status (task §7)

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
| Hybrid Hit@1 | ≥ 85% | 90.7% | ✅ PASS |
| Hybrid Hit@10 | ≥ 90% | 96.5% | ✅ PASS |
| Prediction Hit@1 | ≥ 40% | 38.4% | ⚠️ 1 case short — §7 stop-clause triggered |
| Prediction Hit@10 | ≥ 68% | 68.6% | ✅ PASS |
| Three-caliber disclosure | complete | ✅ | ✅ |
| Lookup edges w/ evidence | 100% | 100% | ✅ |
| Determinism (depth-1) | byte-identical | ✅ | ✅ |

The prediction Hit@1 gate miss (38.4% vs 40%) is **not an implementation bug**: the
v3.2 baseline (33.7%) and the full-precision ablation (36.0%) were reproduced *exactly*
from task §1.2. The shortfall is because the §0 budget added the cofactor fix (+6) and
the round(6) fix (+2~3) as independent, but they **overlap** on two cases (c0039, c0245):
the round(6) ties are a *subset* of the cofactor-tie cases, so combined gain is +4 not +8.
Full audit + per-case attribution in the REPORT. Per task §7 stop-clause, the prediction
tier is submitted for GLM-5.3 review; the hybrid (main) tier passes.

## Edge Table Fields

| Field | Description |
|-------|-------------|
| `source_smiles` | Substrate SMILES (isomeric canonical) |
| `product_smiles` | Product SMILES (isomeric canonical, max fragment) |
| `source_node_id` | Source node ID: `{case_id}:{depth}:{sha1[:12]}` |
| `product_node_id` | Product node ID |
| `edge_score` | Ranking score: `ns_score` (prediction) or `tanimoto` (lookup, Layer 1) |
| `rank` | Rank within the source node's candidates (1-based, hybrid order at depth 1) |
| `depth` | Product node depth (root=0) |
| `parent_case_id` | Blind parent case ID (FR-BBD3-*) |
| `parent_copy_filtered` | Boolean: product == source substrate (stereo-blind) |
| `cycle` | Boolean: product canonical appears in ancestor chain |
| `product_in_frontier` | Boolean: selected for further expansion (top-K1, non-ion/wildcard/cofactor/cycle) |
| `product_ion_filtered` | Boolean: ion/inorganic fragment (sunk) |
| `product_wildcard_filtered` | Boolean: contains wildcard atom (atomic num 0) |
| `cofactor_filtered` | Boolean: cofactor conjugate (NAD/FAD/CoA…, sunk) — new in P4.2 |
| `source` | Engine source(s): `eawag_lookup` (new) / uspto / envipath / retrieval / combos |
| `layer` | `lookup` (Engine D) or `prediction` (Engines A/B/C) — new in P4.2 |
| `p_uspto` / `p_envipath` / `p_retrieval` | Per-source ranker probabilities (0 for lookup edges) |
| `n_candidates_at_source` | Total candidates from this source node |
| `eawag_reactions` | **Lookup edges only**: `["btid#reac_id", …]` trace to EAWAG pages |

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
| `path_score` | Product of edge_scores from root to this node |

## Notes

- **Depth ≥ 2 non-determinism** (~0.1%): the 30s Engine A wall-clock budget in P4.1's
  expansion is inherently non-deterministic at depth ≥ 2 (unchanged from P4.1). Depth-1
  (hybrid) is byte-identical across runs.
- **Frontier approximation**: depth-1 `product_in_frontier` reflects the hybrid order
  (cofactor now sunk); depth ≥ 2 expansion reflects P4.1's frontier (pre-cofactor-filter).
  A fully consistent multi-depth hybrid expansion is P5 scope.
- Downstream (any-generation) scoring requires the v0.3 route answer key (senior's server).
