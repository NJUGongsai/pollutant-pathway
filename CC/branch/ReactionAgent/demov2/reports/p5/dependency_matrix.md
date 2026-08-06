# P5 Dependency Matrix

**Updated:** 2026-08-06（真实数据接入后）

| Dependency | Status | Impact on P5 |
|------------|--------|--------------|
| P0 contracts | PASS | P5 schemas inherit from P0 StrictModel |
| P1 snapshot/hash | **PASS (real)** | `snap_19caddc6b312`（50 audited Rhea cases, read-only） |
| P1 mapping/lineage/ledger | **PASS (real)** | P5 consumes real evidence artifacts |
| P1 eligibility/quarantine | **PASS (real)** | 7 production + 43 diagnostic index partition |
| P2 truth/fold/views | **READY (real)** | 50 audited multi-answer allowed-product sets |
| P2 leakage audit | **READY (real)** | disjoint split 30/10/10, leakage=0, fold_real_0 |
| P3 strict kernel | **READY (real)** | `current_run_artifact.json`（1 strict candidate, evidence_kind=real） |
| P3 candidate/trace | **READY (real)** | generation/validation metrics computable |
| P4 ranking/abstention | **READY (real)** | verified bundle（14/14 gate PASS） |
| P4 immutable run | **READY (real)** | run binds to frozen bundle namespace |
| RDKit | Available | chemistry backend（Murcko scaffold split）+ real P3 pipeline |

## P5 internal dependencies

| P5 module | Depends on | Status |
|-----------|------------|--------|
| schemas.py | P0 StrictModel | Complete |
| snapshot_reader.py | P1 snapshot | Complete |
| builder.py (cases) | P1 snapshot, P2 truth | Complete |
| builder.py (splits) | P1 snapshot, cases | Complete |
| builder.py (baselines) | P1 snapshot, splits, P3 | Complete |
| builder.py (six-layer) | P1 snapshot, splits, baselines, P3, P4 | Complete |
| builder.py (KPI) | P3, P4 | Complete (registered) |
| builder.py (Go/No-Go) | KPI, P2, P3, P4 | Complete (go) |
| **real_data.py** | P1 snapshot + P2/P3/P4 real artifacts | **New (real adapters)** |

## Honest unavailability

- `transformation_family` split: real transformation_hypotheses empty → unavailable
- `source` split: single real source, provenance insufficient → unavailable
- `time` split: no time provenance → unavailable
- cost/runtime layer: no runtime instrumentation → unavailable
- oracle upper bound: diagnostic-only, not run → unavailable