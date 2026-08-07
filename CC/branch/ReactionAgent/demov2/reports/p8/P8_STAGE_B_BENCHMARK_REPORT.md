# P8 Generalized-Lane Benchmark Report

> **Exploratory, NON-production lane.** Results here are not production decisions; they quantify what the generalized (relaxed-structure) lane adds beyond the strict baseline.

- Lane: `generalized`
- Output semantics: `exploratory_non_production`
- Policy: `p8-generalized-relaxation` v`1.0.0` (content_hash `540b875f8508…`)

## Population

| Item | Count |
|------|-------|
| Hypotheses | 5 |
| Predictions | 5 |
| Truth (held-out) | 4 |
| Strict baseline | 1 |

## Metrics

| Metric | Value |
|--------|-------|
| Incremental recall | 1.0000 |
| False additions | 2 (rate 0.4000) |
| Coverage | 1.0000 |
| Risk | 0.4000 |
| Risk @ 90% coverage | 0.2500 |
| OOD ratio | 0.2000 (count 1) |
| Cost | 24 calls / 8200 tokens / 52.30s |

## Risk–coverage curve

| k | coverage | risk |
|---|----------|------|
| 1 | 0.5000 | 0.0000 |
| 2 | 0.7500 | 0.0000 |
| 3 | 0.7500 | 0.3333 |
| 4 | 1.0000 | 0.2500 |
| 5 | 1.0000 | 0.4000 |

## Distance buckets

| Bucket | Count | Correct | Incorrect |
|--------|-------|---------|-----------|
| `0.0-0.2` [0.0, 0.2) | 0 | 0 | 0 |
| `0.2-0.5` [0.2, 0.5) | 4 | 3 | 1 |
| `0.5-1.0` [0.5, 1.0) | 1 | 0 | 1 |
| `1.0+` [1.0, inf) | 0 | 0 | 0 |

_This report is structurally independent of the strict P5 gate report and the P7 three-way evaluation; it covers only the generalized exploratory lane._
