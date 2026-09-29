#!/usr/bin/env python3
"""SUPERSEDED — v1 audit script, kept only as bug-chain record (review R3).

Known bug: the D1 source section reads top-level "products" from
report_adjudication.json, but the real schema nests them under
"payload.products" (same caliber as _first_reportable_source in
scripts/ec298_pd_retest_pairing.py). Its source section therefore
reported 0 matches and MUST NOT be used. All D1/code/asset/isolation
conclusions now come from audit_raw_run_v2.py and v2_* evidence.
Only non-source sections of v1 (manifests, requests, fees, concurrency,
independent scoring) remain valid and are unchanged in v2's scope.
"""
"""V43 EC298 Phase D retest raw-run audit (read-only, zero LLM, no paid API).
Remote: /usrdata/EnzymeCAGE_data/workspaces/dependingv43
Out: /tmp/raw_audit/ (independent dir, never inside arm roots or scoring/)
Covers TASK_V43_EC298_PHASE_D_RETEST_RAW_RUN_AUDIT sections A-D.
Gold is opened ONLY for isolated offline scoring; outputs keep ranks/hits/counts/SHAs, never gold SMILES, prompt text, raw model text, or credentials.
"""
import hashlib, json, os, sys, time
from pathlib import Path
from collections import Counter

BASE = Path("/usrdata/EnzymeCAGE_data/workspaces/dependingv43")
OUT = Path("/tmp/raw_audit")
C0 = BASE / "runs/ec298_pd_retest_C0"
D3 = BASE / "runs/ec298_pd_retest_D3"
ENG = BASE / "runs/ec298_pd_retest_engine"
SMOKE = BASE / "runs/ec298_pd_retest_smoke"
GOLD = Path("/usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl")

EXPECTED = {
    "batch_C0": "31549aab3db5fd2ef832996d5622d80ec8e17984e5b32e19a966455ac3b42df8",
    "batch_D3": "cfe1534a93d7fe1596f997272cb2e3260001f0861ecd4d66f286c6e99b2495b4",
    "whitelist": "cb5996c9b960bb4a61fd5747d275077c65ef49bf2cdb74102b9d22dc7f11d703",
    "gold": "9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c",
    "code": "07fef84f0945bcba055a6424d37efcab2c60ebf47cd1d639d676dd00133764bc",
    "assets": "ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c",
    "engine": "0e16268c375585f622f826a3649ef272f70154d22b2bae02c6e99b90537992cf",
    "merged_C0": "48c84bd693636162ea157cd3c5ff4bdc068fdf2235cdcb88a01c0783f9426855",
    "merged_D3": "61386590f37146da6cb142a6b78ac6be9fc5d6c6cfed93e39590d220228e92bc",
    "seal_C0": "e83ad5333e0e28400ae8b93669a74f8f3c6dbec4d32b2dafc45fcddad42b9a62",
    "seal_D3": "ac1e0d2c10016184df33a0218f09806aeeb7e6e0fdcf2474de671fb0e1b7adeb",
}

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()

def flatten(d, pre=""):
    out = {}
    if isinstance(d, dict):
        for k in sorted(d.keys()):
            out.update(flatten(d[k], f"{pre}{k}." if pre else f"{k}."))
    elif isinstance(d, list):
        out[pre.rstrip(".")] = f"<list len={len(d)}>"
    else:
        out[pre.rstrip(".")] = d
    return out

def manifest(arm):
    recs = []
    targets = ["exam_inputs.jsonl", "input_manifest.json", "batch_identity.json",
               "workers", "runs", "merged", "_arm_summary.json", "_seal"]
    for t in targets:
        p = arm / t
        if p.is_file():
            recs.append({"path": t, "size": p.stat().st_size, "sha256": sha(p)})
        elif p.is_dir():
            for fp in sorted(p.rglob("*")):
                if fp.is_file():
                    rel = str(fp.relative_to(arm))
                    recs.append({"path": rel, "size": fp.stat().st_size, "sha256": sha(fp)})
        else:
            recs.append({"path": t, "missing": True})
    root = hashlib.sha256("\n".join(f"{r.get('path')} {r.get('size')} {r.get('sha256')}" for r in recs if "sha256" in r).encode()).hexdigest()
    return {"arm": str(arm), "n_files": len([r for r in recs if "sha256" in r]),
            "root_summary": root, "files": recs}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = lambda m: (print(m, flush=True))
    audit_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    # env
    import platform
    env = {"audit_start": audit_start, "base": str(BASE),
           "python": sys.version, "platform": platform.platform(),
           "cwd": os.getcwd()}
    try:
        import rdkit
        env["rdkit"] = rdkit.__version__
    except Exception as e:
        env["rdkit"] = f"missing: {e}"
    (OUT / "audit_env.json").write_text(json.dumps(env, indent=2) + "\n")

    # A2 pre manifests
    preC0 = manifest(C0); preD3 = manifest(D3)
    (OUT / "manifest_pre_C0.json").write_text(json.dumps({k: v for k, v in preC0.items() if k != "files"}, indent=2) + "\n")
    (OUT / "manifest_pre_D3.json").write_text(json.dumps({k: v for k, v in preD3.items() if k != "files"}, indent=2) + "\n")
    (OUT / "manifest_pre_C0_files.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in preC0["files"]) + "\n")
    (OUT / "manifest_pre_D3_files.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in preD3["files"]) + "\n")
    log(f"pre manifests: C0 {preC0['n_files']} files, D3 {preD3['n_files']} files")

    # SHA checks vs expected
    checks = {}
    def chk(name, path):
        try:
            v = sha(Path(path))
            checks[name] = {"path": str(path), "actual": v, "expected": EXPECTED.get(name.split(':')[0], None), "match": None}
        except Exception as e:
            checks[name] = {"path": str(path), "error": str(e)}
    # batch sha is inside _arm_summary/batch_identity? actual batch_sha256 field in _arm_summary and export_metadata
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        s = json.loads((arm / "_arm_summary.json").read_text())
        checks[f"batch_{lab}:arm_summary"] = {"actual": s.get("batch_sha256"), "expected": EXPECTED[f"batch_{lab}"], "match": s.get("batch_sha256") == EXPECTED[f"batch_{lab}"]}
        bi = json.loads((arm / "batch_identity.json").read_text())
        # batch_identity has no top-level sha? check identity/sha fields
        checks[f"batch_{lab}:identity_file_sha"] = {"actual": sha(arm / "batch_identity.json")}
    checks["whitelist:C0"] = {"actual": sha(C0 / "exam_inputs.jsonl"), "expected": EXPECTED["whitelist"], "match": sha(C0 / "exam_inputs.jsonl") == EXPECTED["whitelist"]}
    checks["whitelist:D3"] = {"actual": sha(D3 / "exam_inputs.jsonl"), "expected": EXPECTED["whitelist"], "match": sha(D3 / "exam_inputs.jsonl") == EXPECTED["whitelist"]}
    checks["gold"] = {"actual": sha(GOLD), "expected": EXPECTED["gold"], "match": sha(GOLD) == EXPECTED["gold"]}
    checks["engine"] = {"actual": sha(ENG / "engine_results.jsonl"), "expected": EXPECTED["engine"], "match": sha(ENG / "engine_results.jsonl") == EXPECTED["engine"]}
    checks["merged_C0"] = {"actual": sha(C0 / "merged/predictions.jsonl"), "expected": EXPECTED["merged_C0"], "match": sha(C0 / "merged/predictions.jsonl") == EXPECTED["merged_C0"]}
    checks["merged_D3"] = {"actual": sha(D3 / "merged/predictions.jsonl"), "expected": EXPECTED["merged_D3"], "match": sha(D3 / "merged/predictions.jsonl") == EXPECTED["merged_D3"]}
    # seal manifest sha: seal.json contains seal_sha256_of_manifest; seal.sha256 file?
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        sj = json.loads((arm / "_seal/seal.json").read_text())
        checks[f"seal_{lab}:manifest"] = {"actual": sj.get("seal_sha256_of_manifest"), "expected": EXPECTED[f"seal_{lab}"], "match": sj.get("seal_sha256_of_manifest") == EXPECTED[f"seal_{lab}"]}
    # code aggregate + assets: read from batch_identity
    bi0 = json.loads((C0 / "batch_identity.json").read_text())
    ident = bi0.get("identity", bi0)
    checks["code:identity"] = {"actual": ident.get("code_aggregate_sha256"), "expected": EXPECTED["code"], "match": ident.get("code_aggregate_sha256") == EXPECTED["code"]}
    checks["assets:identity"] = {"actual": ident.get("asset_manifest_sha256"), "expected": EXPECTED["assets"], "match": ident.get("asset_manifest_sha256") == EXPECTED["assets"]}
    # input_manifest sha in identity?
    checks["input_manifest_sha:identity_C0"] = {"actual": ident.get("input_manifest_sha256")}
    (OUT / "sha_checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    log("sha checks done")

    # A3 config + identity diffs
    c0cfg = json.loads((C0 / "batch_identity.json").read_text()).get("identity", {}).get("config", json.loads((C0 / "batch_identity.json").read_text()).get("config"))
    # batch_identity structure: top has identity.config; also arm config files in reports? use identity.config
    b0 = json.loads((C0 / "batch_identity.json").read_text())
    b3 = json.loads((D3 / "batch_identity.json").read_text())
    cfg0 = (b0.get("identity") or b0).get("config", {})
    cfg3 = (b3.get("identity") or b3).get("config", {})
    f0, f3 = flatten(cfg0), flatten(cfg3)
    allk = sorted(set(f0) | set(f3))
    vdiff = {k: {"C0": f0.get(k), "D3": f3.get(k)} for k in allk if f0.get(k) != f3.get(k)}
    # identity flatten (exclude timestamps?)
    i0, i3 = flatten(b0.get("identity", b0)), flatten(b3.get("identity", b3))
    allki = sorted(set(i0) | set(i3))
    # exclude volatile keys for diff display but still count
    vdiffi = {k: {"C0": i0.get(k), "D3": i3.get(k)} for k in allki if i0.get(k) != i3.get(k)}
    (OUT / "config_identity_diff.json").write_text(json.dumps({
        "n_config_keys_C0": len(f0), "n_config_keys_D3": len(f3), "n_config_compared": len(allk),
        "config_value_diffs": vdiff,
        "n_identity_keys_C0": len(i0), "n_identity_keys_D3": len(i3), "n_identity_compared": len(allki),
        "identity_value_diffs": vdiffi}, indent=2, ensure_ascii=False) + "\n")
    log(f"config keys {len(allk)} diffs {list(vdiff)}; identity keys {len(allki)} diffs {len(vdiffi)}")

    # A4 exam_inputs
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        rows = [json.loads(l) for l in (arm / "exam_inputs.jsonl").read_text().splitlines() if l.strip()]
        man = json.loads((arm / "input_manifest.json").read_text())
        qids = [r.get("qid") for r in rows]
        res = {"n": len(rows), "n_unique": len(set(qids)),
               "order_match_manifest": qids == man.get("route_order"),
               "bad_keys": [r for r in rows if set(r.keys()) != {"qid", "substrate_smiles", "input_index"}][:3],
               "n_bad_keys": sum(1 for r in rows if set(r.keys()) != {"qid", "substrate_smiles", "input_index"}),
               "answer_fields_present": sum(1 for r in rows if any(k in r for k in ("products_smiles", "products", "gold", "answer"))),
               "substrate_empty": sum(1 for r in rows if not r.get("substrate_smiles")),
               "input_index_sequential": [r.get("input_index") for r in rows][:5],
               "manifest_gold_excluded": man.get("gold_fields_excluded")}
        (OUT / f"exam_inputs_{lab}.json").write_text(json.dumps(res, indent=2) + "\n")
    log("exam inputs done")

    # B per-question linkage (uses input_manifest route_order, not dirname slicing)
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        man = json.loads((arm / "input_manifest.json").read_text())
        order = man.get("route_order", [])
        ident_short = json.loads((arm / "batch_identity.json").read_text()).get("short") or json.loads((arm / "batch_identity.json").read_text()).get("identity", {}).get("short")
        # run_id derivation check: expect exam298_<short>_<qid>
        exp_run = {q: f"exam298_{ident_short}_{q}" for q in order}
        workers = {}
        for sp in sorted((arm / "workers").glob("*.status.json")):
            try:
                st = json.loads(sp.read_text())
            except Exception:
                continue
            # status file name is <qid>.status.json
            qid = sp.name[:-len(".status.json")]
            workers[qid] = st
        export_meta = json.loads((arm / "merged/export_metadata.json").read_text())
        per_route = {r["route_id"]: r for r in export_meta.get("per_route", [])}
        preds = {}
        for line in (arm / "merged/predictions.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                preds[r["route_id"]] = r
        runs_root = arm / "runs"
        actual_runs = sorted([p.name for p in runs_root.iterdir() if p.is_dir()]) if runs_root.is_dir() else []
        rows_out = []
        for q in order:
            rid = exp_run[q]
            rd = runs_root / rid
            w = workers.get(q, {})
            pr = per_route.get(q, {})
            pj = preds.get(q, {})
            steps = pj.get("steps", [])
            n_pred = sum(len(s.get("predicted_products", [])) for s in steps)
            # results dir inspection
            results = rd / "results"
            task_dirs = sorted([t.name for t in results.iterdir()]) if results.is_dir() else []
            # checkpoint existence
            ckpt = (rd / "checkpoint.json").is_file() if rd.is_dir() else False
            rows_out.append({
                "qid": q, "run_id": rid, "run_dir_exists": rd.is_dir(),
                "worker_state": w.get("state") or w.get("status") or w.get("terminal_state"),
                "worker_stop": w.get("stop_reason") or w.get("stopReason"),
                "export_answer_kind": pr.get("answer_kind"),
                "export_route_state": pr.get("route_state"),
                "export_stop": pr.get("stop_reason"),
                "export_sha": pr.get("predictions_sha256"),
                "n_predicted": n_pred, "n_task_dirs": len(task_dirs),
                "has_checkpoint": ckpt,
                "run_id_match_expected": (rid in actual_runs),
            })
        summ = {"n_order": len(order), "n_unique_order": len(set(order)),
                "n_run_dirs": len(actual_runs), "unexpected_runs": [r for r in actual_runs if r not in set(exp_run.values())][:5],
                "missing_runs": [q for q in order if exp_run[q] not in actual_runs][:5],
                "answer_kinds": dict(Counter(r["export_answer_kind"] for r in rows_out)),
                "route_states": dict(Counter(r["export_route_state"] for r in rows_out)),
                "width_over_5": sum(1 for r in rows_out if (r["n_predicted"] or 0) > 5),
                "width_hist": dict(Counter(r["n_predicted"] for r in rows_out)),
                "mismatch_run_link": sum(1 for r in rows_out if not r["run_id_match_expected"])}
        (OUT / f"per_question_{lab}.json").write_text(json.dumps({"summary": summ, "rows": rows_out}, indent=2) + "\n")
        log(f"{lab} per-question: {summ}")
    # B3 engine
    eng_rows = [json.loads(l) for l in (ENG / "engine_results.jsonl").read_text().splitlines() if l.strip()]
    eng_q = [r.get("qid") for r in eng_rows]
    (OUT / "engine_check.json").write_text(json.dumps({
        "n": len(eng_rows), "n_unique": len(set(eng_q)),
        "sha": sha(ENG / "engine_results.jsonl"), "match_expected": sha(ENG / "engine_results.jsonl") == EXPECTED["engine"],
        "sample_keys": sorted(eng_rows[0].keys()) if eng_rows else []}, indent=2) + "\n")
    log("engine done")

    # C requests rebuild
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        man = json.loads((arm / "input_manifest.json").read_text())
        order = man.get("route_order", [])
        q_of_run = {}
        for q in order:
            # short from identity
            b = json.loads((arm / "batch_identity.json").read_text())
            short = b.get("short") or b.get("identity", {}).get("short")
            q_of_run[f"exam298_{short}_{q}"] = q
        reqs = []
        n_calls = n_orph = 0
        for run_dir in sorted((arm / "runs").iterdir()):
            if not run_dir.is_dir():
                continue
            qid = q_of_run.get(run_dir.name, run_dir.name)
            res = run_dir / "results"
            if not res.is_dir():
                continue
            for td in sorted(res.iterdir()):
                if not td.is_dir():
                    continue
                for cp in sorted(td.glob("prediction_call.*.json")):
                    n_calls += 1
                for op in sorted(td.glob("prediction_orphan.*.json")):
                    n_orph += 1
                for rp in sorted(td.glob("prediction_response.*.json")):
                    try:
                        j = json.loads(rp.read_text())
                    except Exception:
                        continue
                    p = j.get("payload", {}) or {}
                    t = p.get("transport", {}) or {}
                    u = t.get("usage") or {}
                    reqs.append({
                        "qid": qid, "run_id": run_dir.name, "task_id": td.name,
                        "file": str(rp.relative_to(arm)), "file_sha": sha(rp),
                        "attempt": p.get("attempt"), "status": p.get("status"),
                        "ok": t.get("ok"), "http": t.get("status"),
                        "request_id": t.get("request_id"),
                        "sent": t.get("sent_at_epoch"), "done": t.get("done_at_epoch"),
                        "elapsed_s": t.get("elapsed_s"),
                        "http_attempts": t.get("http_attempts") or [],
                        "usage": {"input": u.get("prompt_tokens"), "output": u.get("completion_tokens"),
                                  "cached": (u.get("prompt_tokens_details") or {}).get("cached_tokens"),
                                  "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                                  "total": u.get("total_tokens")},
                    })
        # stats
        rids = [r["request_id"] for r in reqs]
        oks = [r for r in reqs if r["ok"] is True and r["http"] == 200]
        fails = [r for r in reqs if not (r["ok"] is True and r["http"] == 200)]
        h429 = sum(1 for r in reqs for a in r["http_attempts"] if isinstance(a, dict) and a.get("status") == 429)
        per_q = Counter(r["qid"] for r in reqs)
        dist = dict(Counter(per_q.values()))
        usage_missing = sum(1 for r in reqs if not r["usage"].get("total"))
        # usage sums
        si = sum((r["usage"].get("input") or 0) for r in reqs)
        so = sum((r["usage"].get("output") or 0) for r in reqs)
        sc = sum((r["usage"].get("cached") or 0) for r in reqs)
        sr = sum((r["usage"].get("reasoning") or 0) for r in reqs)
        # fees: snapshot input 0.8/M output 2.8/M cache_read 0.23/M, thinking billed as output (already in output)
        # cached tokens: billed at cache_read rate instead of input? assume cached portion at 0.23, rest input at 0.8
        fee = (si - sc) * 0.8 / 1e6 + sc * 0.23 / 1e6 + so * 2.8 / 1e6
        # clock anomalies
        neg = sum(1 for r in reqs if r["sent"] is not None and r["done"] is not None and r["done"] < r["sent"])
        zero = sum(1 for r in reqs if r["sent"] == r["done"])
        missing_iv = sum(1 for r in reqs if r["sent"] is None or r["done"] is None)
        elapsed_mismatch = []
        for r in reqs:
            if r["sent"] is not None and r["done"] is not None and r["elapsed_s"] is not None:
                d = abs((r["done"] - r["sent"]) - r["elapsed_s"])
                if d > 5.0:
                    elapsed_mismatch.append({"qid": r["qid"], "diff": round(d, 3)})
        # concurrency: two calibers
        spans = [(r["sent"], r["done"]) for r in oks if r["sent"] is not None and r["done"] is not None]
        def peak(events_sorted):
            cur = peakv = 0
            for _, d in events_sorted:
                cur += d
                peakv = max(peakv, cur)
            return peakv
        ev_sent_first = []
        for s, d in spans:
            ev_sent_first.append((s, 1)); ev_sent_first.append((d, -1))
        ev_sent_first.sort(key=lambda x: (x[0], -x[1]))
        ev_done_first = []
        for s, d in spans:
            ev_done_first.append((s, 1)); ev_done_first.append((d, -1))
        ev_done_first.sort(key=lambda x: (x[0], x[1]))
        # arm summary recorded peak
        arm_sum = json.loads((arm / "_arm_summary.json").read_text())
        rec_peak = (arm_sum.get("inflight") or {}).get("peak_in_flight_provider_ok")
        out = {"n_requests": len(reqs), "n_unique_req": len(set(rids)), "n_ok": len(oks),
               "n_fail": len(fails), "n_429_in_attempts": h429, "n_calls": n_calls, "n_orphans": n_orph,
               "per_q_dist": dist, "two_attempt_qids": sorted([q for q, c in per_q.items() if c == 2]),
               "zero_call_qids_n": 298 - len(per_q),
               "usage_missing": usage_missing, "sums": {"input": si, "output": so, "cached": sc, "reasoning": sr},
               "fee_recomputed": round(fee, 4),
               "fee_recorded": arm_sum.get("cost_estimate_cny"),
               "neg_dur": neg, "zero_dur": zero, "missing_iv": missing_iv,
               "elapsed_mismatch_gt5s": elapsed_mismatch[:10], "n_elapsed_mismatch": len(elapsed_mismatch),
               "peak_sent_first": peak(ev_sent_first), "peak_done_first": peak(ev_done_first),
               "recorded_peak": rec_peak,
               "dup_request_ids": [k for k, c in Counter(rids).items() if c > 1]}
        (OUT / f"requests_{lab}.json").write_text(json.dumps(out, indent=2) + "\n")
        # per-request desensitized table (no raw text)
        with open(OUT / f"requests_{lab}.tsv", "w") as f:
            f.write("qid\trun_id\ttask_id\tattempt\trequest_id\tsent\tdone\thttp\tinput\toutput\tcached\treasoning\ttotal\tfile_sha\n")
            for r in sorted(reqs, key=lambda x: (x["qid"], x["attempt"] or 0)):
                u = r["usage"]
                f.write("\t".join(str(x) for x in [r["qid"], r["run_id"], r["task_id"], r["attempt"], r["request_id"], r["sent"], r["done"], r["http"], u.get("input"), u.get("output"), u.get("cached"), u.get("reasoning"), u.get("total"), r["file_sha"]]) + "\n")
        log(f"{lab} requests: {out}")
    # attempt bug detail
    bug = {}
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        for run_dir in sorted((arm / "runs").iterdir()):
            if not run_dir.is_dir():
                continue
            for td in sorted((run_dir / "results").iterdir()) if (run_dir / "results").is_dir() else []:
                rps = sorted(td.glob("prediction_response.*.json"))
                if len(rps) > 1:
                    atts = []
                    for rp in rps:
                        p = json.loads(rp.read_text()).get("payload", {})
                        atts.append({"file": rp.name, "attempt": p.get("attempt"), "req": (p.get("transport") or {}).get("request_id")})
                    bug[lab] = {"run": run_dir.name, "task": td.name, "files": atts}
    (OUT / "attempt_bug.json").write_text(json.dumps(bug, indent=2) + "\n")

    # smoke
    try:
        srows = []
        for run_dir in sorted((SMOKE).iterdir()) if SMOKE.is_dir() else []:
            srows.append(str(run_dir.name))
        (OUT / "smoke.json").write_text(json.dumps({"entries": srows[:20], "n": len(srows)}, indent=2) + "\n")
    except Exception as e:
        (OUT / "smoke.json").write_text(json.dumps({"error": str(e)}) + "\n")

    # D1 source per-position
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        man = json.loads((arm / "input_manifest.json").read_text())
        order = man.get("route_order", [])
        b = json.loads((arm / "batch_identity.json").read_text())
        short = b.get("short") or b.get("identity", {}).get("short")
        mismatch_first = []
        n_nonempty = 0
        n_first_ok = 0
        pos_stats = Counter()
        for q in order:
            rid = f"exam298_{short}_{q}"
            # merged preds
            # (read preds file line by line? cache)
            pass
        # do bulk read
        preds = {}
        for line in (arm / "merged/predictions.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                plist = []
                for s in r.get("steps", []):
                    plist.extend(s.get("predicted_products", []))
                preds[r["route_id"]] = plist
        total_pos = 0
        match_pos = 0
        width_viol = []
        for q in order:
            rid = f"exam298_{short}_{q}"
            rd = arm / "runs" / rid
            plist = preds.get(q, [])
            if plist:
                n_nonempty += 1
            if len(plist) > 5:
                width_viol.append(q)
            # adjudication
            results = rd / "results"
            adj_products = []
            if results.is_dir():
                for td in sorted(results.iterdir()):
                    rp = td / "report_adjudication.json"
                    if rp.is_file():
                        try:
                            aj = json.loads(rp.read_text())
                        except Exception:
                            continue
                        for pr in aj.get("products", []):
                            if pr.get("reportable") is True:
                                adj_products.append(pr)
                        break  # single task per run? actually one task dir per run; take first found
                # sort by report_rank
                adj_products.sort(key=lambda x: (x.get("report_rank") is None, x.get("report_rank")))
                adj_smiles = []
                for pr in adj_products:
                    adj_smiles.append(pr.get("product_smiles_full") or pr.get("product_smiles"))
            else:
                adj_smiles = []
            # compare position-wise (use full string equality)
            for i, s in enumerate(plist):
                total_pos += 1
                if i < len(adj_smiles) and adj_smiles[i] == s:
                    match_pos += 1
                pos_stats[f"pos{i}"] += 1
            if plist:
                if adj_smiles and adj_smiles[0] == plist[0]:
                    n_first_ok += 1
                else:
                    # record mismatch with evidence refs (desensitized: no SMILES)
                    ev = adj_products[0].get("evidence_id") if adj_products else None
                    mismatch_first.append({"qid": q, "adj_len": len(adj_smiles), "pred_len": len(plist),
                                           "first_evidence": ev,
                                           "first_card": adj_products[0].get("card_kind") if adj_products else None,
                                           "first_rank": adj_products[0].get("report_rank") if adj_products else None})
        (OUT / f"source_{lab}.json").write_text(json.dumps({
            "n_nonempty": n_nonempty, "n_first_match": n_first_ok,
            "n_first_mismatch": len(mismatch_first), "mismatch_first": mismatch_first[:20],
            "total_positions": total_pos, "matched_positions": match_pos,
            "width_violations": width_viol}, indent=2) + "\n")
        log(f"{lab} source: nonempty {n_nonempty} first_ok {n_first_ok} total {total_pos} match {match_pos}")

    # D2 independent scoring (isolated gold open)
    sys.path.insert(0, str(BASE / "src"))
    from pathway_v43.domain.identity import cn_identity
    gold = {}
    for line in GOLD.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            ids = {i for i in (cn_identity(p) for p in r.get("products_smiles", [])) if i}
            gold[r["qid"]] = ids
    eng = {}
    for line in (ENG / "engine_results.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            eng[r["qid"]] = r
    def rank_of(cands, gids):
        for i, c in enumerate(cands, start=1):
            try:
                cid = cn_identity(c)
            except Exception:
                continue
            if cid and cid in gids:
                return i
        return None
    indep = {}
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        per = {}
        for line in (arm / "merged/predictions.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            q = r["route_id"]
            cands = []
            for s in r.get("steps", []):
                cands.extend(s.get("predicted_products", []))
            per[q] = rank_of(cands, gold.get(q, set()))
        indep[lab] = per
    # compare vs score_v2 files on remote scoring dir
    sdir = BASE / "reports/phase_d/retest/scoring"
    diff = {}
    for lab in ["C0", "D3"]:
        sp = sdir / f"score_v2_{lab}.json"
        if sp.is_file():
            sj = json.loads(sp.read_text())
            # per_question list with qid/agent_rank
            rec = {r["qid"]: r.get("agent_rank") for r in sj.get("per_question", [])}
            mism = [{"qid": q, "indep": indep[lab].get(q), "recorded": rec.get(q)} for q in indep[lab] if indep[lab].get(q) != rec.get(q)]
            # summary hits
            def hits(per, k):
                return sum(1 for v in per.values() if v is not None and v <= k)
            diff[lab] = {"n_mismatch": len(mism), "mismatches": mism[:20],
                         "indep_hits": {f"@{k}": hits(indep[lab], k) for k in (1, 3, 5)},
                         "recorded_summary": sj.get("summary", sj.get("hits", {}))}
        else:
            diff[lab] = {"error": "score file missing"}
    # paired four cells @1/3/5 indep
    qids = sorted(set(indep["C0"]) & set(indep["D3"]))
    paired = {}
    for k in (1, 3, 5):
        b = c = d = n = 0
        for q in qids:
            hc = indep["C0"][q] is not None and indep["C0"][q] <= k
            hd = indep["D3"][q] is not None and indep["D3"][q] <= k
            if hc and hd: b += 1
            elif hc and not hd: c += 1
            elif not hc and hd: d += 1
            else: n += 1
        paired[f"@{k}"] = {"both": b, "C0_only": c, "D3_only": d, "neither": n}
    (OUT / "scoring_independent.json").write_text(json.dumps({"diff_vs_recorded": diff, "paired_indep": paired,
        "indep_hits": {lab: {f"@{k}": sum(1 for v in indep[lab].values() if v is not None and v <= k) for k in (1,3,5)} for lab in ["C0","D3"]}}, indent=2) + "\n")
    log("scoring done")

    # D3 seal + isolation
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        sj = json.loads((arm / "_seal/seal.json").read_text())
        # verify manifest entries: seal.json may contain files list? check keys
        (OUT / f"seal_{lab}.json").write_text(json.dumps({
            "keys": sorted(sj.keys()), "n_sealed": sj.get("n_sealed_files"),
            "leak": sj.get("leak_scan"),
            "manifest_sha": sj.get("seal_sha256_of_manifest")}, indent=2) + "\n")
    # isolation scan: count files containing gold markers / credential patterns (paths only, no values)
    import re
    cred_pat = re.compile(r"(sk-|sk-ant|ghp_|xoxb-|AKIA|api[_-]?key\s*[:=]\s*['\"][^'\"]{8,})", re.I)
    gold_markers = ["ec298_gold_readonly", "products_smiles", "raw_reaction"]
    iso = {}
    for arm, lab in [(C0, "C0"), (D3, "D3")]:
        nscan = ncred = 0
        bad = []
        for fp in sorted((arm).rglob("*")):
            if not fp.is_file():
                continue
            # skip binary? only json/jsonl
            if fp.suffix not in (".json", ".jsonl"):
                continue
            nscan += 1
            try:
                t = fp.read_text(encoding="utf-8", errors="strict")[:200000]
            except Exception:
                continue
            hit_gold_path = [m for m in gold_markers if m in t]
            hit_cred = bool(cred_pat.search(t))
            if hit_gold_path or hit_cred:
                bad.append({"file": str(fp.relative_to(arm)), "gold_markers": hit_gold_path, "cred_pattern": hit_cred})
                if hit_cred:
                    ncred += 1
        iso[lab] = {"n_json_scanned": nscan, "n_flagged": len(bad), "n_cred_pattern": ncred, "flagged": bad[:20]}
    (OUT / "isolation_scan.json").write_text(json.dumps(iso, indent=2) + "\n")
    log("seal/isolation done")

    # post manifests + diff
    postC0 = manifest(C0); postD3 = manifest(D3)
    def diff_manifest(pre, post):
        pm = {r["path"]: r for r in pre["files"]}; qm = {r["path"]: r for r in post["files"]}
        changed = [p for p in pm if p in qm and pm[p].get("sha256") != qm[p].get("sha256")]
        added = [p for p in qm if p not in pm]; removed = [p for p in pm if p not in qm]
        return {"changed": changed, "added": added, "removed": removed}
    # reload pre files
    preC0f = {"files": [json.loads(l) for l in (OUT / "manifest_pre_C0_files.jsonl").read_text().splitlines() if l.strip()]}
    preD3f = {"files": [json.loads(l) for l in (OUT / "manifest_pre_D3_files.jsonl").read_text().splitlines() if l.strip()]}
    (OUT / "manifest_post_diff.json").write_text(json.dumps({
        "C0": diff_manifest(preC0f, postC0), "D3": diff_manifest(preD3f, postD3),
        "post_C0_root": postC0["root_summary"], "post_D3_root": postD3["root_summary"]}, indent=2) + "\n")
    (OUT / "audit_done.json").write_text(json.dumps({"audit_end": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, indent=2) + "\n")
    log("DONE")

if __name__ == "__main__":
    main()
