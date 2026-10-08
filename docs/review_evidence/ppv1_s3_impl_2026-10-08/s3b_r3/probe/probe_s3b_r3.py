#!/usr/bin/env python3
"""S3b-r3 evidence probe: S3B-01 post-segment anchor (Codex S3b-r2
review, single residual P1) — flip verification of the two original
counterexamples plus directly affected legal recovery retention
controls.

Counterexamples replicated from the r2 review's recovery_specialist
(case names/inputs preserved):
  self_consistent_replaced_plan_after_bundle_written      (B3)
  self_consistent_replaced_plan_after_event_submitted     (B4)
Both: hard kill via real subprocess (os._exit), then ONLY the
frozen_plan artifact file is changed (add the injected scenario
transition, recompute that file's plan_digest and envelope
payload_hash); run identity / root retrieve task plan_digest /
database / events stay original. Public resume WITHOUT plan must now
be structurally refused with business tables / events / commits /
consume byte-logically unchanged and the mutated file preserved.

Retention controls (legal behavior must stay): same plan / omitted
plan / changed plan (first-layer frozen_plan_mismatch), four crash
boundaries legal recovery, legal original-plan transition (normal +
B4) with new-context followups, three-product partial followup
completion 2/3 -> 3/3, repeated resume no new counts, novel/abstain
model consumers, zero-depth+budget composite stop disclosure.

Public entries only (workflow.runner.start_run / resume_run) driven
in real worker subprocesses; rule-level synthetic inputs (CCO ->
CC=O); scripted network 0; no gold/benchmark/sealed-run/v4 access;
no provider; zero-LLM. Writes only to --out (fresh tmp, existing
output refused); never writes inside --repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PY = sys.executable


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2,
                               sort_keys=True), encoding="utf-8")


def spec(key="B", product="CC=O", **kw):
    d = {"key": key, "product_smiles": product, "coefficient": 1,
         "transformation_ref": f"donor-{key}",
         "origin_group_key": f"donor-{key}",
         "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                    "atom2": "S_O_1", "from_order": "single",
                    "to_order": "double"}],
         "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
         "alignment": {"status": "resolved",
                       "donor_to_current": {"S_C_2": "S_C_2",
                                            "S_O_1": "S_O_1"},
                       "ref": "align-A"},
         "expectation": {"target_smiles": product}}
    d.update(kw)
    return d


def plan(**kw):
    d = {"pools": {"CCO": [spec()]}}
    d.update(kw)
    return d


INJECTED = [{"after_hypothesis_key": "B",
             "transition": {"source_ref": "injected:changed-plan",
                            "new_phase_id": "phase-injected",
                            "new_scenario_ref": "scenario-injected"}}]

WORKER_SOURCE = '''
import json, os, sys
from pathlib import Path
sys.path.insert(0, %(src)r)
from pathway_v43.config import resolve_config
from pathway_v43.workflow.runner import start_run, resume_run
from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
from pathway_v43.pollutant.search import SearchCrashInjection, SearchLedger

inp = json.loads(Path(sys.argv[1]).read_text())
run_id = inp["run_id"]
runs_root = Path(inp["runs_root"])

def hard(tag, detail=None):
    print(json.dumps({"hard_kill": tag, "detail": detail or {},
                      "pid": os.getpid()}, ensure_ascii=False), flush=True)
    sys.stderr.flush()
    os._exit(77)

if inp.get("injection") == "after_two_followups":
    orig = SearchLedger.enqueue_action
    count = [0]
    def enqueue(self, *a, **k):
        r = orig(self, *a, **k)
        if k.get("action_kind") == "retrieve" and (k.get("payload") or {}).get("source_event_id"):
            count[0] += 1
            if count[0] == 2:
                hard(inp["injection"], {"count": count[0], "result": dict(r)})
        return r
    SearchLedger.enqueue_action = enqueue

try:
    if inp["mode"] == "start":
        out = start_run(config=resolve_config(), runs_root=runs_root,
                        run_id=run_id, smiles=inp.get("smiles", "CCO"),
                        max_depth=3, max_expansions=10,
                        max_frontier_width=2, finder=object(),
                        scripted=True,
                        profile=PROFILE_POLLUTANT_PATHWAY_V1,
                        ppv1_plan=inp.get("plan"),
                        profile_policy=inp.get("policy"),
                        crash_after=inp.get("crash_after"))
    else:
        out = resume_run(config=resolve_config(), runs_root=runs_root,
                         run_id=run_id, finder=object(),
                         ppv1_plan=inp.get("plan"),
                         crash_after=inp.get("crash_after"))
    print(json.dumps({"result": out, "pid": os.getpid()},
                     ensure_ascii=False), flush=True)
except SearchCrashInjection as exc:
    hard(inp.get("crash_after"), exc.detail)
except Exception as exc:
    print(json.dumps({"exception": type(exc).__name__,
                      "detail": getattr(exc, "detail", {}),
                      "message": str(exc)[:300], "pid": os.getpid()},
                     ensure_ascii=False), flush=True)
    sys.exit(3)
'''


def snapshot(run_dir: Path) -> dict:
    import sqlite3
    out = {"tables": {}, "artifacts": {}, "identity": None}
    db = run_dir / "pollutant.sqlite"
    if db.exists():
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        for r in con.execute("SELECT name FROM sqlite_master WHERE"
                             " type='table' ORDER BY name"):
            rows = []
            for row in con.execute(f'SELECT * FROM "{r[0]}"'):
                v = dict(row)
                for key, value in list(v.items()):
                    if isinstance(value, str) and value[:1] in "[{":
                        try:
                            v[key] = json.loads(value)
                        except ValueError:
                            pass
                rows.append(v)
            out["tables"][r[0]] = rows
        con.close()
    results = run_dir / "results"
    for p in (sorted(results.rglob("*.json"))
              if results.exists() else []):
        try:
            v = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            v = {"unparseable": True}
        out["artifacts"][str(p.relative_to(run_dir))] = {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "content": v}
    ident = run_dir / "run_identity.json"
    if ident.exists():
        out["identity"] = json.loads(ident.read_text(encoding="utf-8"))
    return out


OBS: list[dict] = []


def record(name: str, check: bool, detail: dict) -> None:
    OBS.append({"case": name, "observed_check": bool(check),
                "detail": detail})
    print(json.dumps(OBS[-1], ensure_ascii=False), flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    repo = args.repo.expanduser().resolve()
    out = args.out.expanduser().resolve()
    if out.exists():
        raise RuntimeError(f"Output already exists; use fresh tmp: {out}")
    if repo == out or repo in out.parents or out in repo.parents:
        raise RuntimeError("Output must be outside and separate from repo")
    out.mkdir(parents=True)
    src = str(repo / "src")
    worker_file = out / "probe_worker.py"
    worker_file.write_text(WORKER_SOURCE % {"src": src},
                            encoding="utf-8")
    runs_root = out / "synthetic_runs" / "runs"
    env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": src}

    def launch(label: str, inp: dict):
        f = out / "inputs" / f"{label}.json"
        dump(f, inp)
        cmd = [PY, "-B", str(worker_file), str(f)]
        p = subprocess.run(cmd, cwd=str(repo), text=True,
                           capture_output=True, env=env, timeout=180)
        (out / "logs" / f"{label}.stdout.txt").parent.mkdir(
            parents=True, exist_ok=True)
        (out / "logs" / f"{label}.stdout.txt").write_text(p.stdout)
        (out / "logs" / f"{label}.stderr.txt").write_text(p.stderr)
        parsed = None
        for line in p.stdout.splitlines():
            try:
                parsed = json.loads(line)
            except ValueError:
                pass
        v = {"label": label, "command": cmd, "environment": env,
             "cwd": str(repo), "returncode": p.returncode,
             "stdout": p.stdout, "stderr": p.stderr, "parsed": parsed}
        dump(out / "logs" / f"{label}.execution.json", v)
        snap = snapshot(runs_root / inp["run_id"])
        dump(out / "tables" / f"{label}.json", snap)
        return v, snap

    def base(name: str, p=None, **kw):
        d = {"mode": "start", "run_id": name,
             "runs_root": str(runs_root),
             "plan": p if p is not None else plan()}
        d.update(kw)
        return d

    def tables(s, n):
        return s["tables"].get(n, [])

    def eventids(s):
        return [r["event_id"] for r in tables(s, "events")]

    def counters(s):
        return {n: len(v) for n, v in s["tables"].items()}

    def content_hash(obj):
        sys.path.insert(0, src)
        from pathway_v43.domain.models import content_hash as ch
        return ch(obj)

    # ---- A. two original counterexamples: flip verification ----
    for boundary in ("after_bundle_written", "after_event_submitted"):
        name = "self_consistent_replaced_plan_" + boundary
        first, s0 = launch(name + "_start",
                           base(name, plan(), crash_after=boundary))
        run = runs_root / name
        target = run / "results" / "run-plan" / "frozen_plan.json"
        before = target.read_bytes()
        data = json.loads(before)
        newp = plan(scenario_transitions=INJECTED)
        data["payload"]["plan"] = newp
        data["payload"]["plan_digest"] = content_hash(newp)
        data["payload_hash"] = content_hash(data["payload"])
        target.write_text(json.dumps(data, ensure_ascii=False),
                          encoding="utf-8")
        dump(out / "inputs" / f"{name}_mutation.json",
             {"before_envelope": json.loads(before),
              "new_envelope": json.loads(target.read_text()),
              "reason": ("Only frozen artifact changed (add injected "
                         "scenario transition, recompute that file's "
                         "plan_digest and envelope payload_hash); root "
                         "task plan_digest, run identity, ledger and "
                         "events remain original.")})
        sm = snapshot(run)
        dump(out / "tables" / f"{name}_mutated.json", sm)
        mutated_bytes = target.read_bytes()
        inp = dict(base(name, plan()), mode="resume")
        inp.pop("plan")
        second, s1 = launch(name + "_resume", inp)
        root = next(r for r in tables(sm, "search_actions")
                    if r["action_kind"] == "retrieve"
                    and not r["payload"].get("source_event_id"))
        trans = [r for r in tables(s1, "search_actions")
                 if r["action_kind"] == "scenario_transition"]
        parsed = second["parsed"] or {}
        exc = parsed.get("exception", "")
        kind = ((parsed.get("detail") or {}).get("kind"))
        record(name,
               second["returncode"] == 3
               and exc == "PPV1RunError"
               and kind == "frozen_plan_binding_mismatch"
               and sm["tables"] == s1["tables"]
               and target.read_bytes() == mutated_bytes
               and not trans,
               {"first": first["parsed"], "resume": parsed,
                "root_frozen_digest": root["payload"]["plan_digest"],
                "root_status": root["status"],
                "new_frozen_digest": data["payload"]["plan_digest"],
                "plan_version": data["payload"]["plan_version"],
                "transition_actions": trans,
                "before": counters(sm), "after": counters(s1),
                "unchanged_tables": sm["tables"] == s1["tables"],
                "evidence_preserved":
                    target.read_bytes() == mutated_bytes,
                "classification": "S3B01_post_segment_anchor_closed"})

    # ---- B. retention controls (legal behavior stays) ----
    for variant in ("same", "omitted", "changed"):
        name = "frozen_plan_" + variant
        first, s0 = launch(name + "_start",
                           base(name, plan(), crash_after="after_claim"))
        rp = (plan() if variant == "same"
              else (None if variant == "omitted"
                    else plan(pools={"CCO": [spec("X")]})))
        inp = dict(base(name, rp), mode="resume")
        if variant == "omitted":
            inp.pop("plan")
        second, s1 = launch(name + "_resume", inp)
        parsed = second["parsed"] or {}
        if variant == "changed":
            record(name, second["returncode"] == 3
                   and ((parsed.get("detail") or {}).get("kind")
                        == "frozen_plan_mismatch")
                   and not eventids(s1),
                   {"resume": parsed, "events": eventids(s1),
                    "classification": "first_layer_kept"})
            continue
        record(name, second["returncode"] == 0
               and len(eventids(s1)) == 1
               and len(tables(s1, "search_commit_records")) == 4,
               {"resume": parsed, "events": eventids(s1),
                "commits": len(tables(s1, "search_commit_records")),
                "classification": "legal_control"})

    for boundary in ("after_claim", "after_request_registered",
                     "after_bundle_written", "after_event_submitted"):
        name = "crash_" + boundary
        p = plan()
        if boundary == "after_request_registered":
            p["model"] = {"provider_kind": "scripted",
                          "responses": ['{"proposals": "not-a-list"}']}
        first, s0 = launch(name + "_start",
                           base(name, p, crash_after=boundary))
        inp = dict(base(name, p), mode="resume")
        inp.pop("plan")
        second, s1 = launch(name + "_resume", inp)
        third, s2 = launch(name + "_again", dict(inp))
        check = (first["returncode"] == 77
                 and second["returncode"] == 0
                 and counters(s1) == counters(s2))
        if boundary == "after_request_registered":
            check = check and len(tables(s1, "model_requests")) == 1 \
                and all(r["network_request_count"] == 0
                        for r in tables(s1, "model_requests")) \
                and bool((second["parsed"] or {}).get(
                    "result", {}).get("recovery", {}).get(
                        "pending_requests"))
        else:
            check = check and len(eventids(s1)) == 1 \
                and len(tables(s1, "search_commit_records")) == 4
        record(name, check,
               {"first": first["parsed"], "resume": second["parsed"],
                "again": third["parsed"],
                "initial_counts": counters(s0),
                "after_counts": counters(s1),
                "again_counts": counters(s2),
                "classification": "legal_recovery_kept"})

    tp = plan(scenario_transitions=[{
        "after_hypothesis_key": "B",
        "transition": {"source_ref": "user:switch",
                       "new_phase_id": "phase-1",
                       "new_scenario_ref": "scenario-new"}}])
    for variant in ("normal", "after_event_submitted"):
        name = "transition_" + variant
        kw = {} if variant == "normal" else {"crash_after": variant}
        first, s0 = launch(name + "_start", base(name, tp, **kw))
        if variant != "normal":
            inp = dict(base(name, tp), mode="resume")
            inp.pop("plan")
            second, s1 = launch(name + "_resume", inp)
        else:
            second, s1 = first, s0
        inp = dict(base(name, tp), mode="resume")
        inp.pop("plan")
        third, s2 = launch(name + "_again", inp)
        trans = [r for r in tables(s1, "search_actions")
                 if r["action_kind"] == "scenario_transition"]
        fu = [r for r in tables(s1, "search_actions")
              if r["action_kind"] == "retrieve"
              and r["payload"].get("source_event_id")]
        phases = []
        ctx_by_id = {a["content"]["payload"]["context_id"]:
                     a["content"]["payload"]["phase_id"]
                     for a in s1["artifacts"].values()
                     if a["content"].get("payload", {}).get(
                         "context_id")}
        phases = [ctx_by_id.get(r["context_ref"]) for r in fu]
        record(name, second["returncode"] == 0
               and len(trans) == 1 and trans[0]["status"] == "done"
               and phases == ["phase-1"]
               and counters(s1) == counters(s2),
               {"start": first["parsed"], "resume": second["parsed"],
                "transitions": trans, "followups": fu,
                "followup_phases": phases,
                "before": counters(s0), "after": counters(s1),
                "again": counters(s2),
                "classification": "legal_transition_kept"})

    pp = plan(pools={"CCO": [spec(coproducts=["[H][H]", "O"])]})
    policy = {"search_limits": {"max_product_expansion_width": 3,
                                "max_total_search_actions": 30}}
    name = "three_products_after_two"
    first, s0 = launch(name + "_start",
                       base(name, pp, policy=policy,
                            injection="after_two_followups"))
    inp = dict(base(name, pp, policy=policy), mode="resume")
    inp.pop("plan")
    second, s1 = launch(name + "_resume", inp)
    third, s2 = launch(name + "_again", inp)
    products = [p["state_ref"] for e in tables(s1, "events")
                for p in e["payload"]["participants"]
                if p["side"] == "product"]
    fu = [r for r in tables(s1, "search_actions")
          if r["action_kind"] == "retrieve"
          and r["payload"].get("source_event_id")]
    missing = sorted(set(products) - {r["subject_ref"] for r in fu})
    record(name, first["returncode"] == 77
           and second["returncode"] == 0
           and len(products) == 3 and len(fu) == 3 and not missing
           and counters(s1) == counters(s2),
           {"start": first["parsed"], "resume": second["parsed"],
            "products": products, "followup_refs":
                [r["subject_ref"] for r in fu],
            "missing": missing, "before": counters(s0),
            "after": counters(s1), "again": counters(s2),
            "note": "budget widened to 30 (from default 10) for the "
                    "3-product fixture, same as r2 evidence",
            "classification": "legal_recovery_kept"})

    novel = {"hypothesis_id": "novel:1",
             "proposal_context": {"reference_hypothesis_ids": [],
                                   "output_origin": "novel_outside_pool"},
             "reaction_spec": spec("Novel")}
    for tag, p in (
            ("novel_nonempty",
             plan(model={"provider_kind": "scripted",
                         "responses": [json.dumps(
                             {"proposals": [novel]})]})),
            ("abstain_empty",
             {"pools": {},
              "model": {"provider_kind": "scripted",
                        "responses": ['{"proposals": []}']}})):
        name = "model_" + tag
        v, s = launch(name, base(name, p))
        requests = tables(s, "model_requests")
        check = v["returncode"] == 0 and all(
            r["network_request_count"] == 0 for r in requests)
        if tag == "novel_nonempty":
            check = check and len(eventids(s)) == 2
        else:
            check = check and len(eventids(s)) == 0 and len(requests) == 1
        record(name, check, {"stop": v["parsed"],
                             "events": eventids(s),
                             "requests": requests,
                             "counts": counters(s),
                             "classification": "consumer_kept"})

    name = "zero_depth_budget"
    v, s = launch(name, base(name, plan(),
                             policy={"search_limits":
                                     {"max_search_depth": 0}}))
    stop = (v["parsed"] or {}).get("result", {}).get("stop", {})
    unexplored = stop.get("unexplored", {})
    record(name, v["returncode"] == 0
           and stop.get("primary") == "budget_limit"
           and "depth_limit" in (stop.get("other_reasons") or [])
           and unexplored.get("blocked") == 1
           and len(unexplored.get("blocked_objects") or []) == 1
           and (unexplored.get("blocked_objects") or [{}])[0].get(
               "reason") == "depth_limit",
           {"stop": stop, "counts": counters(s),
            "classification": "blocked_disclosure_kept"})

    dump(out / "observations.json", OBS)
    ok = all(o["observed_check"] for o in OBS)
    summary = {"total": len(OBS),
               "observed": sum(1 for o in OBS if o["observed_check"]),
               "not_observed": [o["case"] for o in OBS
                                if not o["observed_check"]],
               "exit": 0 if ok else 1}
    dump(out / "probe_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
