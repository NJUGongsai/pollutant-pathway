# P1-T3 Legacy Lineage Audit

**Audit version:** p1-2
**Timestamp:** 2026-08-01T16:23:12.461743+00:00
**Verdict:** `COMPLETE`
**Scope:** full-corpus read-only replay of the project-declared legacy donor table; 3,601 complete reaction SMILES checked against reacting-center fragment-pair evidence

## Legacy module (read-only)

| Field | Value |
|-------|-------|
| path | `ReactionAgent/benchmark/canonical_identity.py` |
| sha256 | `6003f4bc4ffc5ca3304dc1d2282a467f4f773e149ea9cf2a132ca0e4079eb2d0` |
| sha matches Preflight | True |
| size | 8986 bytes |
| read_only | True |
| modified_by_audit | False |

## Counts (§9.5 layered stats)

| Category | Count |
|----------|-------|
| total_reactions | 3601 |
| audited_reactions | 3601 |
| cross_lineage_pair | 415 |
| cofactor_selected_as_main | 0 |
| mapping_missing | 0 |
| legacy_pair_supported | 3007 |
| insufficient_evidence | 179 |

**Denominator:** `total_reactions = 3601` (0 because no real source was audited — PARTIAL).

## Mismatch categories (§9.4 definitions)

### `cross_lineage_pair`

Legacy transformed_pair picked a (X, Y) pair that crosses independent lineages — e.g. pairing 2-oxoglutarate -> hydroxyproline instead of proline -> hydroxyproline. This is the §9.3 forbidden-lineage failure mode: legacy single-pair selection cannot represent two parallel transformed lineages in one reaction.

### `cofactor_selected_as_main`

Legacy pick_main (or _pick_transformed with an empty reaction-center fallback) selected a conserved cofactor (NADH/CoA/ATP/FAD/...) as the main substrate or product, mislabeling a spectator as the transformed core. COFACTORS stripping mitigates this only when the cofactor SMILES exactly matches the frozenset entry.

### `mapping_missing`

No verifiable atom mapping exists for the reaction — either rdkit cannot parse it, chenyu_features.reaction_center_from_chenyu returned None, or the mapper backend is absent. Without a map there is no formal atom-transfer evidence, so the legacy pair is unsupported.

### `legacy_pair_supported`

The legacy transformed_pair (X, Y) IS supported by the available mapping/lineage evidence — X and Y are the true transformed core and the pair does not cross lineages. This is the agreement category.

### `insufficient_evidence`

Evidence is too thin to classify the legacy pair as either supported or a mismatch — e.g. ambiguous reaction center, partial mapping, or missing source stoichiometry. The record is retained (not deleted) and flagged for downstream quarantine/diagnostic review.

## Legacy logic risks (static audit)

| Function | Lines | Risk |
|----------|-------|------|
| `pick_main` | 60-77 | Selects a single 'largest fragment' by (heavy_atoms, carbon, canonical SMILES lex). For multi-substrate reactions (97% of the corpus) this can pick a conserved cofactor as 'main' when no reaction-center signal is available — NADH/CoA are heavy and win the size contest. No cofactor stripping is applied at this layer. |
| `COFACTORS` | 96-128 | Cofactor stripping is exact-SMILES-match only. Canonical tautomers, protonation states, or salt forms that differ from the frozenset entry bypass the filter. Deliberately excludes ambiguous co-substrates (2-oxoglutarate/glutamate/pyruvate/acetyl-CoA) which are sometimes the true substrate — correct, but it means _pick_transformed must disambiguate them via reaction center alone. |
| `_pick_transformed` | 131-157 | When per_frag_center is None (chenyu_features unavailable or returns None), it silently degrades to 'largest non-cofactor fragment' — the same size-contest failure mode as pick_main, just with cofactors excluded. The fallback is not flagged in the return value, so callers cannot distinguish a center-anchored pick from a size-based guess. |
| `transformed_pair` | 161-185 | Returns a SINGLE (X, Y) pair per reaction. The §9.3 canonical case has TWO parallel transformed lineages (proline->hydroxyproline AND 2-oxoglutarate->succinate); legacy can only represent one, forcing a cross-lineage pairing for the other. Also depends on chenyu_features.reaction_center_from_chenyu (imported inside a try/except) — if that import fails, the pair is computed without any reaction-center signal, silently degrading quality. |
| `group_key / main_substrate / main_product` | 188-202 | All three delegate to transformed_pair, so they inherit its single-pair limitation. group_key = (X, Y) means two reactions with the same true transformation but different legacy pairings (due to cofactor/tie ambiguity) land in different groups — splitting a chemical family and inflating apparent diversity. |
| `canon_smiles / canon_frags` | 23-48 | canon_frags returns a frozenset, discarding stoichiometry and duplicate fragments. This is fine for set-level comparison but means 'spectator' detection (canon_frags(r) & canon_frags(p)) cannot distinguish a truly conserved species from one that appears on both sides with different stoichiometry. |

## Real source status

| Field | Value |
|-------|-------|
| rdkit_available | True |
| rdkit_info | `2026.03.4` |
| numpy_available | True |
| env_keys_present | {} |
| candidate_rxn_count | 3601 |
| candidate_proline_keyword_hits | 0 |
| source_confirmed_by_env | False |
| real_reaction_source_found | True |
| usable_for_legacy_audit | True |

### Candidate data files

| File | Exists | Size |
|------|--------|------|
| rxn2enzyme_positives | True | 3133338 |
| reacting_center | True | 4494676 |

## Proline / 2-oxoglutarate case (§9.3)

- **reaction:** 2-oxoglutarate + proline + O2 -> succinate + hydroxyproline + CO2
- **expected_lineages:** ['proline -> hydroxyproline', '2-oxoglutarate -> succinate']
- **forbidden_lineage:** 2-oxoglutarate -> hydroxyproline
- **source_record_found:** True
- **status:** `audited_from_real_source`
- Located by exact stereo-independent participant structures, not by molecule-name keywords. Reacting-center pairs support fragment lineages but are not represented as full atom mapping.

## Examples & source IDs

- **examples:** 12 entries (empty — no real source audited; §9.8 forbids fabrication)

- **source_ids:** 3601 entries (empty — no real source confirmed)

## Discipline (§9.2 / §9.8)

- `legacy_read_only`: True
- `no_failed_records_deleted`: True
- `no_success_only_sampling`: True
- `no_fixture_reported_as_real`: True
- `section_9_8_compliant`: True

---

**Artifacts:** `reports/data_audit/legacy_lineage_audit.json` + `reports/data_audit/legacy_lineage_audit.md`
