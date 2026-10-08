#!/usr/bin/env python3
"""Read-only adjudication of captured once-run evidence. No imports of project code.

Original raw assertion failures are retained verbatim. This corrects two mistaken
chemical expectations and one SQL/payload-field mistake, and bounds one unused
historical appearance case by the already fixed R8 first-consumption contract.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = ROOT / "results.json"
results = json.loads(source.read_text())
output = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "probe_reexecuted": False, "case_count": len(results), "cases": []}

for r in results:
    case = r["case"]
    verdict = {"case": case, "raw_assertion": r["assertion"], "adjudication": "contract_conforms", "method": "read captured input/output only"}
    if r["assertion"] == "passed":
        verdict["note"] = "Original assertion passed; no revision."
    elif case == "target_deviation":
        audit = next(t["result"] for t in r["trace"] if t["call"] == "audit_hypothesis" and "result" in t)
        center = next(c for c in audit["checks"] if c["name"] == "transformation_center")
        assert center["status"] == "violated"
        assert center["detail"]["strict_target_match"] is False
        assert len(r["tables"]["events"]) == 1
        verdict["note"] = "Our original unknown expectation was wrong. Actual bound/full-coverage proof with strict=False gives center violated. Conditional event remains allowed by R5v; no verified/R6."
    elif case == "full_balanced_extra_participant":
        audit = next(t["result"] for t in r["trace"] if t["call"] == "audit_hypothesis" and "result" in t)
        checks = {c["name"]: c for c in audit["checks"]}
        center = checks["transformation_center"]
        assert center["status"] == "verified"
        assert checks["element_accounting"]["status"] == "verified"
        assert checks["formal_charge_accounting"]["status"] == "verified"
        assert center["detail"]["completion_license"] == "composition_only_hydrogen_equivalents"
        assert center["detail"]["unlicensed_uncovered_identities"] == []
        assert center["detail"]["uncovered_product_elements"] == {"H": "2"}
        assert len(r["tables"]["events"][0]["payload"]["participants"]) == 3
        verdict["note"] = "Our original unknown expectation was wrong: H2 is already registered composition-only completion. Fully balanced H2 control correctly remains verified; this does not prove mechanism or extend license to unregistered multi-atom cosubstrates. Original checks after the early center assertion were not executed; these checks inspect captured output only."
    elif case == "audit_contract_driver":
        assert "exception" not in r
        assert len(r["tables"]["events"]) == 1
        assert sorted(a["status"] for a in r["tables"]["search_attempts"]) == ["failed", "recorded"]
        aborted = [a for a in r["tables"]["search_actions"] if a["payload"].get("hypothesis_key") == "bad-B"]
        assert len(aborted) == 1 and aborted[0]["status"] == "done"
        assert all(e["hypothesis_id"] != aborted[0]["subject_ref"] for e in r["tables"]["events"])
        commit = [c for c in r["tables"]["search_commit_records"] if c["action_id"] == aborted[0]["action_id"]]
        assert len(commit) == 1 and commit[0]["event_id"] == "" and commit[0]["commit_kind"] == "outcome_recorded"
        verdict["note"] = "Our original last assertion read hypothesis_id from event.payload, but it is an SQL identity column. Captured actual driver narrow catch fails B attempt and records outcome settlement; only already-scheduled C submits an event. Broad caller production control is a separate actual function case with zero ledger change."
    elif case == "state_appearance_hash_tamper":
        bad = r["before_tables"]["state_appearances"][0]
        assert bad["payload"]["structure_smiles_raw"] == "CCO |r|"
        assert len(r["before_tables"].get("events", [])) == 0
        assert len(r["tables"]["events"]) == 1
        assert r["put_state_output"] is None
        event = r["tables"]["events"][0]
        manifest = event["payload"]["event_appearance_manifest"]
        assert {"state_id": bad["state_id"], "appearance_hash": bad["appearance_hash"]} not in manifest
        assert not any(c["commit_kind"] == "event_committed" for c in r["tables"]["search_commit_records"])
        stopped = r["output"]["stop"]["run_error"]
        assert stopped["kind"] == "event_ledger_authority_failed"
        err = next(t["exception"] for t in r["trace"] if t["call"] == "complete_action" and "exception" in t)
        assert err["detail"]["source_detail"]["kind"] == "appearance_hash_corrupt"
        assert err["detail"]["source_detail"]["appearance_hash"] == bad["appearance_hash"]
        verdict["adjudication"] = "P2_unused_historical_occurrence_boundary"
        verdict["note"] = "Bad original root appearance is NOT reused by this event: driver supplies distinct lawful substrate occurrence (different source_refs/hash), manifest and links contain the new occurrence. New event first saves; complete's all-SID historical appearance replay then refuses. No successful event commit or event budget consumption. Do not call this a same-hash R8 regression; do not call put_state(None) a certificate or all old rows validated."
        verdict["before_events"] = 0
        verdict["after_events"] = 1
        verdict["bad_appearance_in_event_manifest"] = False
        verdict["successful_event_commit"] = False
    else:
        raise AssertionError("Unclassified raw assertion failure: " + case)
    output["cases"].append(verdict)

assert len(output["cases"]) == 17
output["blocking_P1"] = []
output["nonblocking_P2_case_count"] = sum(c["adjudication"].startswith("P2_") for c in output["cases"])
(ROOT / "adjudicated_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(json.dumps({"case_count": len(output["cases"]), "raw_passed": sum(r["assertion"] == "passed" for r in results), "raw_failed": sum(r["assertion"] == "failed" for r in results), "adjudicated_P1": [], "P2_cases": output["nonblocking_P2_case_count"], "probe_reexecuted": False}, ensure_ascii=False, indent=2))
