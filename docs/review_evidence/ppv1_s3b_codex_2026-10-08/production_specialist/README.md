# S3b production specialist permanent evidence package

HEAD `c1211183c0874b12c5b5461845d3c61f0a84719c`, parent `b7f2bba02ca49edd0a45a13bc9b8434909d99175`, actual local review date2026-10-08. See `SPECIALIST_REVIEW.md` for bounded conclusions. Package is immutable/read-only; **copy to fresh tmp before any reproduction**.

- `probe_production.py`: once-run 17 synthetic actual production/public-runner controls.
- `results.json`: full inputs, reached calls, results/exceptions, full15-table snapshots and full JSON artifact inputs/outputs.
- `summary.json` and `probe.*.log`: original13 passed/4 failed assertions retained, no rerun. Three oracle/field mistakes and one acceptedP2 unused historical-occurrence boundary are not disguised as original passes.
- `adjudicate_capture.py`, `adjudicated_results.json`, `adjudication.*.log`: read-only captured-output adjudication; no project import/execution. Originalfailed v1 and logs also preserved.
- `static_review.py`, `static_checks.json`, `static.*.log`: primary source15-snippet mutual verification, AST specific catch/raise inventory; no execution claim from static facts.
- `src/`, `pyproject.toml`, `input_docs/`, `input_snapshot.json`: exact isolated full source/vendor/metadata plus scoped source-document snapshots; full hashes in input and package manifests.
- `artifacts/`: raw JSON artifact envelopes from exclusively synthetic scratch runs; binarySQLite files omitted, their SHA/bytes explicitly listed in `omitted_sqlite_files.json`; all table contents needed for checks are in results.json.
- `execution_metadata.json`, `runtime.json`, `source_integrity.json`, `source_diff.patch`: actual command/runtime/provenance/source hash guard.
- `manifest.json`: payload entries list `{path,bytes,sha256}`; `SHA256SUMS` covers all payload and manifest; `manifest.sha256` pins manifest itself.

Execution command (cwd originalfreshscratch):

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/ppv1_s3b_production_84agv6jv/src /Users/cc/miniconda3/envs/depending43/bin/python -B probe_production.py > probe.stdout.log 2> probe.stderr.log
```

The real AtomTool operations were executed, notsuccess-mocked. Documented negative proof/artifact/data mutations are synthetic. Broadcatch wraps actual `expand_hypothesis_production`; actual runner narrows AuditContractError then intentionally records failure settlement. RuntimeError escape and unused old appearance limitations are explicitly disclosed.

No PPV1/G01/full-crash/barrier suite rerun by this specialist; no externalmodel/provider/network, realgold/questions/sealedrun/v4 access, commit/push or main-repository mutation. These are engineering contract controls and do not measuredev/298 scientific performance. Criteria remainunfrozen.
