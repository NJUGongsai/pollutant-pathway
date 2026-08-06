#!/usr/bin/env python
"""R3-F mutation case runner (one case x one variant per process).

Executes ONE mutation scenario (baseline or mutated) in its own process and
prints a UNIQUE, STRICT, VERSIONED JSON receipt on stdout (marker-delimited):

    ---P3_MUTATION_RECEIPT_1---
    {"schema_version": "p3-mutation-receipt-1", "session_nonce": ...,
     "run_id": ..., "case": ..., "variant": ..., "component": ...,
     "command": [...], "exit_code": ..., "status": "PASS"|"FAIL"|"ERROR",
     "failure_code": ..., "artifact_hash": ..., "artifact": {...}}
    ---P3_MUTATION_RECEIPT_END---

Every field is bound to the SAME trusted execution: the session nonce, run
id, case, variant, component, schema version, command identity, exit code,
status, failure code, typed artifact and canonical artifact hash.  The
harness parses this receipt from the raw output and builds the typed record
FROM it — the typed artifact is not an independently modifiable copy.

Exit codes: 0 = scenario PASS, 1 = scenario FAIL, 2 = ERROR (unexpected
exception / timeout — the mutation harness treats this as fail-closed).

The observed failure code is whatever the production machinery emitted —
never the expected code.
"""
from __future__ import annotations

import hashlib
import json
import sys
import traceback

sys.path.insert(0, ".")

RECEIPT_BEGIN = "---P3_MUTATION_RECEIPT_1---"
RECEIPT_END = "---P3_MUTATION_RECEIPT_END---"
RECEIPT_SCHEMA_VERSION = "p3-mutation-receipt-1"


def _emit(payload: dict, exit_code: int) -> int:
    print(RECEIPT_BEGIN)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
    print(RECEIPT_END)
    return exit_code


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--variant", required=True,
                        choices=["baseline", "mutated"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--session-nonce", required=True)
    args = parser.parse_args()

    from reaction_agent.p3.mutations_round3 import (
        case_by_id,
        run_case,
    )
    from reaction_agent.p3.mutation_harness import (
        RECEIPT_BEGIN as _RB,
        RECEIPT_END as _RE,
        RECEIPT_SCHEMA_VERSION as _RSV,
    )
    # The harness and the subprocess must agree on the receipt protocol.
    assert RECEIPT_BEGIN == _RB and RECEIPT_END == _RE
    assert RECEIPT_SCHEMA_VERSION == _RSV

    meta = case_by_id(args.case)
    component = meta.get("component", "")
    schema_version = meta.get("schema_version", "")
    # R6-B: the receipt's ``case`` is the FROZEN SCENARIO NAME (baseline_case
    # / mutated_case) of the registry — the same value the Gate verifier
    # binds against.  The mutation_id is carried separately as ``mutation_id``.
    case_name = (
        meta.get("baseline_case") if args.variant == "baseline"
        else meta.get("mutated_case")
    ) or ""
    try:
        status, failure_code, artifact = run_case(args.case, args.variant)
    except Exception as exc:  # noqa: BLE001 - ERROR is a harness-visible state
        payload = {
            "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
            "schema_version": schema_version,
            "session_nonce": args.session_nonce,
            "run_id": args.run_id,
            "mutation_id": args.case,
            "case": case_name,
            "variant": args.variant,
            "component": component,
            "command": sys.argv,
            "exit_code": 2,
            "status": "ERROR",
            "failure_code": "",
            "artifact_hash": "",
            "artifact": {
                "exception_type": type(exc).__name__,
                "detail": str(exc)[:500],
                "traceback_tail": traceback.format_exc(limit=3)[-800:],
            },
        }
        return _emit(payload, 2)

    artifact_json = json.dumps(artifact, ensure_ascii=False, sort_keys=True,
                               default=str)
    payload = {
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "schema_version": schema_version,
        "session_nonce": args.session_nonce,
        "run_id": args.run_id,
        "mutation_id": args.case,
        "case": case_name,
        "variant": args.variant,
        "component": component,
        "command": sys.argv,
        "exit_code": 0 if status == "PASS" else 1,
        "status": status,
        "failure_code": failure_code,
        "artifact_hash": hashlib.sha256(artifact_json.encode("utf-8")).hexdigest(),
        "artifact": artifact,
    }
    return _emit(payload, 0 if status == "PASS" else 1)


if __name__ == "__main__":
    sys.exit(main())