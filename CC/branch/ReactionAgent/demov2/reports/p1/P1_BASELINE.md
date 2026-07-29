# P1 Baseline

**Recorded at (UTC):** 2026-07-29T12:25:37.508203+00:00
**P0 baseline commit:** `a96b763` (feat: P0 contract freeze baseline for demov2)
**Baseline locked:** true

## P0 Contract Tests

| Metric | Count |
|--------|-------|
| Collected | 290 |
| Passed | 290 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |

Command:
```
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra \
  --json-report --json-report-file=reports/p1/.baseline_pytest.json
```
Output: `290 passed in 0.42s`

## P0 Gate

| Metric | Count |
|--------|-------|
| Passed | 10 |
| Failed | 0 |
| Status | `READY_FOR_CHATGPT_AUDIT` |

Command: `.venv/bin/python scripts/run_p0_gate.py`
Output: `Result: 10/10 passed` / `Status: READY_FOR_CHATGPT_AUDIT`

All ten gate checks (P0-G01 … P0-G10) passed: ADRs, authority consistency, hypothesis lanes,
dual ledger boundary, eligibility policy, mapping/mechanism consistency, decision state machine,
MCP side-effect policy, legacy-provisional marking, and contract tests + JSON freshness + env.

## Evidence

- pytest JSON report: `reports/p1/.baseline_pytest.json`
- P0 Gate JSON report: `reports/p0/P0_GATE_REPORT.json`
- P0 Gate Markdown report: `reports/p0/P0_GATE_REPORT.md`

## Conclusion

P0 baseline is green and locked. P1 may proceed subject to Preflight stop-condition
(see `P1_PREFLIGHT.{md,json}`).
