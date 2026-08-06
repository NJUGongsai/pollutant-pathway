# P5 Gate Report

**Timestamp:** 2026-08-06T08:02:10.770784+00:00
**Gate version:** p5-gate-1
**Run ID:** p5_run_20260806_080210
**Status:** **PASS**

## Summary

| Metric | Value |
|--------|-------|
| Pass | 8 |
| Block | 0 |
| Fail | 0 |
| Total | 8 |
| Mutations caught | 14/14 |
| Mutations escaped | 0 |
| Mutations errored | 0 |

## Upstream status

| Phase | Status |
|-------|--------|
| P1 | PASS |
| P2 | READY |
| P3 | READY |
| P4 | READY |

## P1 snapshot

- Snapshot ID: snap_19caddc6b312
- Snapshot hash: 19caddc6b312f476d93db8744c79a7851d5cf8393ab12644cb7d3a8fae770b59
- Artifact classification: real

## Gate items

| Gate ID | Name | Passed | Blocked | Evidence |
|---------|------|--------|---------|----------|
| P5-G01 | leakage_zero_and_domains_audited | True | False | leakage_zero=True, all_audited=True, source_unavailable=True, time_unavailable=True |
| P5-G02 | all_filters_and_denominators_complete | True | False | filters=4, no_silent_drop=True, partition_matches=True (partition_sum=50, pre_norm=50) |
| P5-G03 | multi_answer_active_and_policy_bound | True | False | multi_answer_active=True, incomplete_retained=True, cases=50 |
| P5-G04 | strict_metrics_complete_or_unavailable_blocker | True | False | metrics_have_n_or_unavailable=True, blocked_by_p3_missing=False, blocked_by_p4_missing=False |
| P5-G05 | baselines_fair_and_oracle_separated | True | False | baselines_fair=True, oracle_separated=True, baseline_count=7 |
| P5-G06 | formal_kpi_registry_only_when_data_allows | True | False | kpi_correct=True, registered=True, blocked_by_upstream=False |
| P5-G07 | go_no_go_traceable | True | False | go_no_go_traceable=True, decision=go |
| P5-G08 | invariant_tests_pass | True | False | tests_passed=86, tests_failed=0, tests_errors=0, exit_code=0 |

## Gate decision

The P5 Gate status is **PASS**.

## JSON authority

The JSON report at `P5_GATE_REPORT.json` is the authority. This Markdown
is rendered from the JSON and must not be used as the source of truth.
