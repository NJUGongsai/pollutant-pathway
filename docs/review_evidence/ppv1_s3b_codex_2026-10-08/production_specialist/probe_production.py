#!/usr/bin/env python3
"""Independent synthetic public-chain S3b production contract probes.

Run once in fresh scratch only. No provider/network/real evaluation input.
Public runner and real AtomTool calls are instrumented, not replaced by success.
Negative mutations replace only explicitly documented proof/data boundaries.
"""
import contextlib
import copy
import dataclasses
import hashlib
import json
import sqlite3
import socket
import sys
import traceback
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from pathway_v43.config import resolve_config
from pathway_v43.domain.models import content_hash
from pathway_v43.pollutant import production as prod, runflow as flow
from pathway_v43.pollutant.audit import AuditContractError
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.path_context import build_path_context
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.queue import schedule_hypotheses
from pathway_v43.pollutant.search import SearchLedger, SearchCrashInjection, search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore
from pathway_v43.workflow.runner import start_run, resume_run

EDITS = [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1", "from_order": "single", "to_order": "double"}]
DONOR = {"center_atom_ids": ["S_C_2", "S_O_1"]}
ALIGN = {"status": "resolved", "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"}, "ref": "align-independent"}
RESULTS = []
NETWORK = []

def deny_network(*args, **kwargs):
    NETWORK.append({"args": repr(args), "kwargs": repr(kwargs)})
    raise AssertionError("Network is forbidden in this review")

def normal(value):
    if hasattr(value, "to_dict"):
        return normal(value.to_dict())
    if dataclasses.is_dataclass(value):
        return normal(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): normal(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normal(v) for v in value]
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return repr(value)

def spec(key="ind-B", **kw):
    d = {"key": key, "product_smiles": "CC=O", "coefficient": 1,
         "transformation_ref": "donor-" + key, "origin_group_key": "ind-" + key,
         "edits": copy.deepcopy(EDITS), "donor": copy.deepcopy(DONOR),
         "alignment": copy.deepcopy(ALIGN), "expectation": {"target_smiles": "CC=O"}}
    d.update(kw)
    return d

def database_snapshot(db):
    if not db.is_file():
        return {}
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    out = {}
    for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = r[0]
        rows = [dict(x) for x in conn.execute(f'SELECT * FROM "{name}"')]
        for row in rows:
            for k, v in list(row.items()):
                if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
                    try: row[k] = json.loads(v)
                    except json.JSONDecodeError: pass
        out[name] = rows
    conn.close()
    return out

def artifact_snapshot(run_dir):
    out = {}
    for path in sorted((run_dir / "results").rglob("*.json")):
        rel = str(path.relative_to(run_dir))
        data = path.read_bytes()
        try: parsed = json.loads(data)
        except json.JSONDecodeError: parsed = data.decode(errors="replace")
        out[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "content": parsed}
    return out

@contextlib.contextmanager
def trace_pipeline(trace, converter_mutation=None, audit_mutation=None):
    """Call each real function, preserve all inputs/results/exceptions."""
    with contextlib.ExitStack() as stack:
        for obj, attr in [(prod, "render"), (prod, "execute_edits"),
                          (prod, "check_edit_against_donor"),
                          (prod, "center_evidence_from_donor_diagnostic"),
                          (prod, "audit_hypothesis"), (prod, "decide_admission"),
                          (SearchLedger, "submit_action_event"),
                          (SearchLedger, "complete_action")]:
            original = getattr(obj, attr)
            def make_wrapper(original=original, attr=attr):
                def wrapped(*args, **kwargs):
                    entry = {"call": attr, "args": normal(args), "kwargs": normal(kwargs)}
                    trace.append(entry)
                    try:
                        if attr == "audit_hypothesis" and audit_mutation:
                            args, kwargs = audit_mutation(args, kwargs)
                            entry["mutated_input"] = {"args": normal(args), "kwargs": normal(kwargs)}
                        result = original(*args, **kwargs)
                        entry["real_result"] = normal(result)
                        if attr == "center_evidence_from_donor_diagnostic" and converter_mutation:
                            result = converter_mutation(copy.deepcopy(result), args[0])
                            entry["boundary_mutation_result"] = normal(result)
                        entry["result"] = normal(result)
                        return result
                    except Exception as exc:
                        entry["exception"] = {"type": type(exc).__name__, "message": str(exc), "detail": normal(getattr(exc, "detail", {}))}
                        raise
                return wrapped
            stack.enter_context(patch.object(obj, attr, make_wrapper()))
        yield

def run_public(case, specs, *, converter_mutation=None, audit_mutation=None, plan_extra=None):
    runs_root = ROOT / "runs" / case
    run_id = case
    plan = {"pools": {"CCO": copy.deepcopy(specs)}}
    plan.update(copy.deepcopy(plan_extra or {}))
    trace = []
    rec = {"case": case, "entry": "workflow.runner.start_run", "input": {"smiles": "CCO", "plan": plan, "scripted": True}, "trace": trace}
    with trace_pipeline(trace, converter_mutation, audit_mutation):
        try:
            rec["output"] = start_run(config=resolve_config(v3_code_root=ROOT / "absent_v3", assets_root=ROOT / "absent_assets"),
                                     runs_root=runs_root, run_id=run_id, smiles="CCO", max_depth=3, max_expansions=20, max_frontier_width=3,
                                     finder=object(), scripted=True, profile="pollutant_pathway_v1", ppv1_plan=plan)
        except Exception as exc:
            rec["exception"] = {"type": type(exc).__name__, "message": str(exc), "detail": normal(getattr(exc, "detail", {})), "traceback": traceback.format_exc()}
    rec["tables"] = database_snapshot(runs_root / run_id / "pollutant.sqlite")
    rec["artifacts"] = artifact_snapshot(runs_root / run_id)
    rec["legacy_files"] = {n: (runs_root / run_id / n).exists() for n in ("pathway.sqlite", "checkpoint.sqlite")}
    RESULTS.append(rec)
    return rec

def audits(rec):
    return [t["result"] for t in rec["trace"] if t["call"] == "audit_hypothesis" and "result" in t]

def centers(rec):
    return [next(x for x in a["checks"] if x["name"] == "transformation_center") for a in audits(rec)]

def assertions(rec, func):
    try:
        func()
        rec["assertion"] = "passed"
    except Exception as exc:
        rec["assertion"] = "failed"
        rec["assertion_exception"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}

def require(condition, message):
    if not condition: raise AssertionError(message)

def check_public(rec, expected_events, center_status=None):
    require("exception" not in rec, "public run unexpectedly raised")
    require(len(rec["tables"].get("events", [])) == expected_events, "event count differs")
    require(not any(rec["legacy_files"].values()), "legacy storage opened")
    if center_status:
        require(centers(rec)[0]["status"] == center_status, "center differs: " + repr(centers(rec)))

def main():
    # 1. Real tools and all downstream production functions, public start.
    r = run_public("legal", [spec()])
    assertions(r, lambda: (check_public(r, 1, "verified"), require([t["call"] for t in r["trace"]].index("render") < [t["call"] for t in r["trace"]].index("audit_hypothesis"), "ordering")))

    # 2–4. Missing evidence vs execution failure are different real paths.
    r = run_public("missing_alignment", [spec(alignment={"status": "unavailable", "donor_to_current": {}, "ref": "no-map"})])
    assertions(r, lambda: check_public(r, 1, "unknown"))
    r = run_public("missing_proof", [spec()], converter_mutation=lambda e, d: {k: v for k, v in e.items() if k != "proof_record"})
    assertions(r, lambda: (check_public(r, 1, "unknown"), require("proof_missing" in centers(r)[0]["reason_code"], "missing proof reason")))
    r = run_public("execution_failed", [spec(edits=[{"op": "break_bond", "atom1": "S_X", "atom2": "S_Y"}])])
    def failure_checks():
        check_public(r, 0)
        require(not audits(r), "failure was incorrectly audited")
        diag = next(t["result"] for t in r["trace"] if t["call"] == "check_edit_against_donor")
        require(all(diag[k] is None for k in ("reaction_center_match", "strict_target_match", "legacy_cn_match")), "three None violated")
        require(diag["center_evidence"] == {}, "failed diagnostic evidence not empty")
        conv = next(t["result"] for t in r["trace"] if t["call"] == "center_evidence_from_donor_diagnostic")
        require(conv["center_match"] is None and conv["checker_version"], "converter metadata missing")
        require(all(a["status"] == "failed" for a in r["tables"]["search_attempts"]), "method failure not failed")
    assertions(r, failure_checks)

    # 5–7. Actual output is a verification input; declared event identity remains frozen pool identity.
    r = run_public("target_deviation", [spec(expectation={"target_smiles": "CC(=O)O"})])
    assertions(r, lambda: (check_public(r, 1, "unknown"), require(any(t.get("result", {}).get("strict_target_match") is False for t in r["trace"] if t["call"] == "check_edit_against_donor"), "strict false missing")))
    r = run_public("declared_product_differs", [spec(product_smiles="CC(=O)O")])
    assertions(r, lambda: (check_public(r, 1, "unknown"), require(any(s["payload"].get("smiles_isomeric") == "CC(=O)O" for s in r["tables"]["states"]), "declared product identity absent")))
    r = run_public("ambiguous_alignment", [spec(alignment={"status": "ambiguous", "donor_to_current": {}, "ref": "ambiguous-map"})])
    assertions(r, lambda: check_public(r, 1, "unknown"))

    # 8. Balanced full declared reaction does not enlarge single-target center proof.
    substrate = build_chemical_state("CCO", "raw_input")
    product = build_chemical_state("CC=O", "source_product")
    coproduct = build_chemical_state("[H][H]", "source_product")
    participants = [
        {"state_ref": substrate.state_id, "side": "reactant", "role": "primary_substrate", "coefficient": 1, "coefficient_status": "known"},
        {"state_ref": product.state_id, "side": "product", "role": "principal_product", "coefficient": 1, "coefficient_status": "known"},
        {"state_ref": coproduct.state_id, "side": "product", "role": "coproduct", "coefficient": 1, "coefficient_status": "known"}]
    r = run_public("full_balanced_extra_participant", [spec(coproducts=["[H][H]"], participants=participants, participant_list_status="source_complete")])
    def extra_checks():
        check_public(r, 1, "unknown")
        checks = {c["name"]: c for c in audits(r)[0]["checks"]}
        require(checks["element_accounting"]["status"] == "verified", "full element balance fixture failed")
        require(checks["formal_charge_accounting"]["status"] == "verified", "full charge balance fixture failed")
        require(len(r["tables"]["events"][0]["payload"]["participants"]) == 3, "coproduct lost")
        require("partial" in centers(r)[0]["reason_code"], "coverage gap not disclosed")
    assertions(r, extra_checks)

    # 9. Actual driver narrow catch writes failure settlement, continues already scheduled sibling.
    conv_calls = [0]
    def tamper_first(e, d):
        conv_calls[0] += 1
        if conv_calls[0] == 1: e["center_match"] = not bool(e["center_match"])
        return e
    r = run_public("audit_contract_driver", [spec("bad-B"), spec("good-C")], converter_mutation=tamper_first)
    def narrow_checks():
        check_public(r, 1)
        excs = [t["exception"] for t in r["trace"] if t["call"] == "audit_hypothesis" and "exception" in t]
        require(excs and excs[0]["type"] == "AuditContractError", "proof rejection missing")
        require(excs[0]["detail"]["kind"] == "center_evidence_integrity_mismatch", "proof rejection wrong kind")
        attempts = r["tables"]["search_attempts"]
        require(sorted(a["status"] for a in attempts) == ["failed", "recorded"], "driver did not settle aborted and continue sibling")
        aborted = [a for a in r["tables"]["search_actions"] if a["payload"].get("hypothesis_key") == "bad-B"]
        require(len(aborted) == 1 and aborted[0]["status"] == "done", "failed settlement does not finish action")
        require(not any(e["payload"]["hypothesis_id"] == aborted[0]["subject_ref"] for e in r["tables"]["events"]), "aborted event submitted")
    assertions(r, narrow_checks)

    # 10. Direct public production entry under deliberately broad caller preserves zero successful writes.
    broad_caller_case()

    # 11. Cross-hypothesis proof reached through actual runner remains unknown.
    foreign = prod.execute_atomtool_expansion(substrate_smiles="CO", tool_inputs={"edits": [{"op": "change_bond_order", "atom1": "S_C_1", "atom2": "S_O_1", "from_order": "single", "to_order": "double"}], "donor": {"center_atom_ids": ["S_C_1", "S_O_1"]}, "alignment": {"status": "resolved", "donor_to_current": {"S_C_1": "S_C_1", "S_O_1": "S_O_1"}, "ref": "foreign-align"}, "expectation": {"target_smiles": "C=O"}})["center_evidence"]
    r = run_public("cross_hypothesis", [spec()], converter_mutation=lambda e, d: copy.deepcopy(foreign))
    assertions(r, lambda: (check_public(r, 1, "unknown"), require("binding" in centers(r)[0]["reason_code"], "binding reason missing")))

    # 12–13. Factory/constructor RuntimeError escapes honestly, never successful chemistry.
    r = run_public("raw_cx_factory_refused", [spec(product_smiles="CC=O |atomProp:0.n,r|")])
    assertions(r, lambda: (require(r.get("exception", {}).get("type") == "ChemicalStateError", "factory exception missing"), require(len(r["tables"].get("events", [])) == 0, "bad raw wrote event"), require(not audits(r), "bad pool audited")))
    r = run_public("hypothesis_constructor_refused", [spec(participant_list_status="invalid")])
    assertions(r, lambda: (require(r.get("exception", {}).get("type") == "HypothesisContractError", "hypothesis exception missing"), require(len(r["tables"].get("events", [])) == 0, "bad hypothesis wrote event")))

    # 14–15. Public resume after documented B1 pause reads corrupted context, retains original evidence.
    context_tamper_case("context_envelope_tamper", rehash=False)
    context_tamper_case("context_content_tamper", rehash=True)

    # 16–17. put_state return is no ledger certificate; public first event consumption still refuses damage.
    state_row_tamper_case("state_appearance_hash_tamper", "appearance")
    state_row_tamper_case("state_semantic_fact_tamper", "semantic")

    (ROOT / "results.json").write_text(json.dumps(normal(RESULTS), ensure_ascii=False, indent=2))
    summary = {"cases": len(RESULTS), "passed": sum(r.get("assertion") == "passed" for r in RESULTS), "failed": [{"case": r["case"], "exception": r.get("assertion_exception")} for r in RESULTS if r.get("assertion") != "passed"], "network_calls": NETWORK}
    (ROOT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))

def broad_caller_case():
    case = "broad_caller_production"
    root = ROOT / "runs" / case
    root.mkdir(parents=True)
    store = PollutantPathwayStore(root / "pollutant.sqlite")
    art = ArtifactStore(root / "runs", case)
    ledger = SearchLedger(store, art, case)
    ledger.register_search_run(case, build_profile_identity_block())
    substrate = build_chemical_state("CCO", "raw_input", [{"record": "independent-substrate"}])
    store.put_state(substrate.to_dict())
    ctx = build_path_context()
    ctxref = prod.persist_context(art, ctx)
    prepared = prod.prepare_hypothesis(spec(), parent_path_id="broad-parent", substrate_state=substrate, transformation_ref="independent-broad")
    chosen = schedule_hypotheses(ledger, run_id=case, parent_path_id="broad-parent", context_ref=ctxref, parent_search_revision=0, pool=[{"hypothesis_key": "ind-B", "hypothesis_id": prepared["hypothesis"].hypothesis_id, "rank": 1, "payload": {"task_key": "ind-broad-task", "spec": spec(), "substrate_smiles": "CCO", "context_ref": ctxref, "parent_path_id": "broad-parent", "depth": 1}}], policy_version=search_policy_version(), depth=1)
    aid = chosen["selected"][0]["action_id"]
    receipt = ledger.claim_action(aid, worker_id="ind-worker")
    before = database_snapshot(root / "pollutant.sqlite")
    trace = []
    r = {"case": case, "entry": "production.expand_hypothesis_production (actual function, broad caller negative control)", "input": {"spec": spec(), "prepared": normal(prepared), "context": ctx.to_dict(), "receipt": receipt}, "before_tables": before, "trace": trace}
    def corrupt(e, d):
        e["center_match"] = not bool(e["center_match"])
        return e
    with trace_pipeline(trace, corrupt):
        try:
            r["output"] = prod.expand_hypothesis_production(ledger, aid, prepared=prepared, context=ctx, worker_id="ind-worker", attempt_id=receipt["attempt_refs"][0], task_key="ind-broad-task", substrate_state=substrate, limits=ledger._limits(case), depth=1)
        except Exception as exc:  # Deliberately broad negative-control caller only.
            r["broad_caught"] = {"type": type(exc).__name__, "detail": normal(getattr(exc, "detail", {})), "message": str(exc)}
    after = database_snapshot(root / "pollutant.sqlite")
    r["tables"] = after
    r["artifacts"] = artifact_snapshot(root / "runs" / case)
    RESULTS.append(r)
    assertions(r, lambda: (require(r.get("broad_caught", {}).get("type") == "AuditContractError", "wide caller did not catch actual contract error"), require(before == after, "broad capture production mutated ledger"), require(after["search_actions"][0]["status"] == "claimed", "aborted action no longer claimed")))

def pause_initial(case, specs):
    root = ROOT / "runs" / case
    plan = {"pools": {"CCO": copy.deepcopy(specs)}}
    cfg = resolve_config(v3_code_root=ROOT / "absent_v3", assets_root=ROOT / "absent_assets")
    try:
        start_run(config=cfg, runs_root=root, run_id=case, smiles="CCO", max_depth=3, max_expansions=20, max_frontier_width=3, finder=object(), scripted=True, profile="pollutant_pathway_v1", ppv1_plan=plan, crash_after="after_claim")
    except SearchCrashInjection as exc:
        pause = {"type": type(exc).__name__, "detail": normal(exc.detail), "message": str(exc)}
    else:
        raise AssertionError("B1 pause not reached")
    return root, plan, cfg, pause

def context_tamper_case(case, rehash):
    root, plan, cfg, pause = pause_initial(case, [spec()])
    path = next((root / case / "results").rglob("path_context.json"))
    original = path.read_bytes()
    envelope = json.loads(original)
    envelope["payload"]["scenario_ref"] = "mutated-context-retains-id"
    if rehash: envelope["payload_hash"] = content_hash(envelope["payload"])
    changed = json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode()
    path.write_bytes(changed)
    trace = []
    r = {"case": case, "entry": "public start B1 pause -> synthetic artifact mutation -> workflow.runner.resume_run", "input": {"plan": plan, "original_artifact": json.loads(original), "mutated_artifact": envelope, "rehash": rehash}, "initial_pause": pause, "trace": trace}
    with trace_pipeline(trace):
        try: r["output"] = resume_run(config=cfg, runs_root=root, run_id=case, finder=object(), ppv1_plan=plan)
        except Exception as exc: r["exception"] = {"type": type(exc).__name__, "detail": normal(getattr(exc, "detail", {})), "message": str(exc), "traceback": traceback.format_exc()}
    r["tables"] = database_snapshot(root / case / "pollutant.sqlite")
    r["artifacts"] = artifact_snapshot(root / case)
    r["original_artifact_preserved_after_refusal"] = path.read_bytes() == changed
    RESULTS.append(r)
    def check():
        require(len(r["tables"]["events"]) == 0, "bad context wrote event")
        require(r["original_artifact_preserved_after_refusal"], "resume cleaned artifact")
        if rehash:
            require(r.get("exception", {}).get("type") == "ConditionContractError", "content identity exception expected")
            require(r["exception"]["detail"].get("kind") == "context_content_identity_mismatch", "content identity kind expected")
        else:
            detail = r.get("exception", {}).get("detail") or r.get("output", {}).get("stop", {}).get("run_error", {})
            require(detail.get("kind") == "artifact_hash_mismatch", "envelope integrity kind expected")
    assertions(r, check)

def state_row_tamper_case(case, mode):
    root, plan, cfg, pause = pause_initial(case, [spec()])
    db = root / case / "pollutant.sqlite"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    r = {"case": case, "entry": "public start B1 pause -> synthetic state row damage -> put_state -> workflow.runner.resume_run", "input": {"plan": plan, "mode": mode}, "initial_pause": pause, "trace": []}
    rootrow = conn.execute("SELECT state_id,payload FROM states").fetchone()
    sid = rootrow["state_id"]
    original_semantic = json.loads(rootrow["payload"])
    original_app = dict(conn.execute("SELECT * FROM state_appearances WHERE state_id=?", (sid,)).fetchone())
    if mode == "appearance":
        app = json.loads(original_app["payload"])
        app["structure_smiles_raw"] = "CCO |r|"
        conn.execute("UPDATE state_appearances SET payload=? WHERE state_id=?", (json.dumps(app, ensure_ascii=False), sid))
    else:
        corrupted = copy.deepcopy(original_semantic)
        corrupted["formal_charge"] = 9
        conn.execute("UPDATE states SET payload=? WHERE state_id=?", (json.dumps(corrupted, ensure_ascii=False), sid))
    conn.commit()
    conn.close()
    before = database_snapshot(db)
    r["before_tables"] = before
    # Existing put_state may return success despite damaged same-hash appearance. It is not a certificate.
    store = PollutantPathwayStore(db)
    lawful = build_chemical_state("CCO", "raw_input", [{"record": "ppv1-root-input"}]).to_dict()
    try: r["put_state_output"] = store.put_state(lawful)
    except Exception as exc: r["put_state_exception"] = {"type": type(exc).__name__, "detail": normal(getattr(exc, "detail", {})), "message": str(exc)}
    store.conn.close()
    with trace_pipeline(r["trace"]):
        try: r["output"] = resume_run(config=cfg, runs_root=root, run_id=case, finder=object(), ppv1_plan=plan)
        except Exception as exc: r["exception"] = {"type": type(exc).__name__, "detail": normal(getattr(exc, "detail", {})), "message": str(exc), "traceback": traceback.format_exc()}
    r["tables"] = database_snapshot(db)
    r["artifacts"] = artifact_snapshot(root / case)
    RESULTS.append(r)
    def check():
        require(len(r["tables"]["events"]) == 0, "damaged authority accepted successful event")
        require(r.get("exception") or r.get("output", {}).get("stop", {}).get("run_error"), "damage not refused/disclosed")
        # Necessary rejection may happen during submit after actual tools/audit; this is recorded, not overclaimed.
        require(all(a["commit_kind"] != "event" for a in r["tables"]["search_commit_records"]), "event budget successfully consumed")
    assertions(r, check)

if __name__ == "__main__":
    with patch.object(socket.socket, "connect", deny_network), patch.object(socket, "create_connection", deny_network):
        main()
