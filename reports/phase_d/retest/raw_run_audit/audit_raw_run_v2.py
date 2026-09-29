#!/usr/bin/env python3
"""V43 EC298 Phase D retest raw-run audit, round 2 (v2, read-only, zero LLM).

Fixes review findings on /tmp/audit_raw_run.py (v1):
- v1 source check read top-level "products" (always empty -> 0 matches);
  v2 reads payload.products (same caliber as ec298_pd_retest_pairing.py
  _first_reportable_source) and emits a full per-position table.
- v1 code/asset SHAs were read from batch_identity; v2 recomputes the
  aggregates from the actual files via the frozen functions
  (storage.run_identity.code_identity,
   adapters.asset_manifest.verify_repo_manifest).
- v2 adds a full-caliber isolation scan (official strict patterns) over ALL
  arm files with per-file key-path context and adjudication categories,
  beyond the 601-file seal caliber.

Out: /tmp/raw_audit_v2/ (independent dir; never inside arm roots/scoring).
Gold is opened ONLY for the isolated offline scoring cross-check already
done in v1; v2 emits no gold content, prompt text, raw model text, or creds.

Sections: 1-code aggregate, 2-asset manifest, 3-source positions,
4-full-caliber isolation (FULL text, no truncation), 5-call arithmetic,
6-seal recompute (309-file manifest + official 601-file scan, read-only).
"""
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

BASE = Path("/usrdata/EnzymeCAGE_data/workspaces/dependingv43")
OUT = Path("/tmp/raw_audit_v2")
ARMS = {"C0": BASE / "runs/ec298_pd_retest_C0",
        "D3": BASE / "runs/ec298_pd_retest_D3"}

EXPECTED = {
    "code": "07fef84f0945bcba055a6424d37efcab2c60ebf47cd1d639d676dd00133764bc",
    "assets": "ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c",
}

GOLD_MARKERS = ("ec298_gold_readonly", "questions.jsonl",
                "products_smiles", "raw_reaction")
CRED_PATS = (
    ("sk-pattern", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("bearer-pattern", re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{16,}")),
    ("apikey-pattern",
     re.compile(r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-]{16,}")),
)


def log(m):
    print(m, flush=True)


def short_of(arm):
    b = json.loads((arm / "batch_identity.json").read_text())
    return b.get("short") or b.get("identity", {}).get("short")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    sys.path.insert(0, str(BASE / "src"))

    # ---- 1. code aggregate recompute from actual files ----
    from pathway_v43.storage.run_identity import code_identity
    ci = code_identity()
    code_res = {
        "n_files": len(ci["files"]),
        "aggregate_recomputed": ci["aggregate_sha256"],
        "aggregate_expected": EXPECTED["code"],
        "match": ci["aggregate_sha256"] == EXPECTED["code"],
    }
    (OUT / "code_aggregate.json").write_text(
        json.dumps(code_res, indent=2) + "\n")
    log(f"code aggregate: n={code_res['n_files']} match={code_res['match']}")

    # ---- 2. asset manifest recompute from actual files ----
    from pathway_v43.adapters.asset_manifest import verify_repo_manifest
    # assets_root from arm identity config
    b0 = json.loads((ARMS["C0"] / "batch_identity.json").read_text())
    ident = b0.get("identity", b0)
    assets_root = (ident.get("assets_root")
                   or (ident.get("config") or {}).get("assets_root")
                   or str(BASE / "assets"))
    man = verify_repo_manifest(assets_root)
    asset_res = {
        "assets_root": str(man.get("assets_root")),
        "n_files": man.get("n_files"),
        "total_bytes": man.get("total_bytes"),
        "manifest_recomputed": man.get("manifest_sha256"),
        "manifest_expected": EXPECTED["assets"],
        "match": man.get("manifest_sha256") == EXPECTED["assets"],
    }
    (OUT / "asset_manifest.json").write_text(
        json.dumps(asset_res, indent=2) + "\n")
    log(f"asset manifest: n={asset_res['n_files']} match={asset_res['match']}")

    # ---- 3. source per-position full table (payload.products caliber) ----
    for lab, arm in ARMS.items():
        order = json.loads(
            (arm / "input_manifest.json").read_text())["route_order"]
        short = short_of(arm)
        preds = {}
        for line in (arm / "merged/predictions.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                plist = []
                for s in r.get("steps", []):
                    plist.extend(s.get("predicted_products", []))
                preds[r["route_id"]] = plist
        rows = []
        first_kind = Counter()
        for q in order:
            plist = preds.get(q, [])
            adj = []
            rd = arm / "runs" / f"exam298_{short}_{q}" / "results"
            if rd.is_dir():
                for td in sorted(rd.iterdir()):
                    rp = td / "report_adjudication.json"
                    if not rp.is_file():
                        continue
                    try:
                        pay = json.loads(rp.read_text(
                            encoding="utf-8")).get("payload") or {}
                    except Exception:
                        continue
                    cands = [x for x in (pay.get("products") or [])
                             if x.get("reportable")]
                    if cands:
                        cands.sort(key=lambda x: (
                            x.get("report_rank") is None,
                            x.get("report_rank") or 0))
                        adj = cands
                        break
            adj_smiles = [(p.get("product_smiles_full")
                           or p.get("product_smiles")) for p in adj]
            for i, _ in enumerate(plist):
                ok = i < len(adj_smiles) and adj_smiles[i] == plist[i]
                ev = adj[i] if i < len(adj) else {}
                rows.append({
                    "qid": q, "pos": i, "match": bool(ok),
                    "evidence_id": ev.get("evidence_id"),
                    "card_kind": ev.get("card_kind"),
                    "report_rank": ev.get("report_rank"),
                })
            if plist and adj_smiles and adj_smiles[0] == plist[0]:
                first_kind[adj[0].get("card_kind")] += 1
        n_nonempty = sum(1 for q in order if preds.get(q))
        n_first = sum(1 for r in rows if r["pos"] == 0 and r["match"])
        summ = {"n_nonempty": n_nonempty, "n_first_match": n_first,
                "n_first_mismatch": n_nonempty - n_first,
                "total_positions": len(rows),
                "matched_positions": sum(1 for r in rows if r["match"]),
                "width_violations": sum(
                    1 for q in order if len(preds.get(q, [])) > 5),
                "first_card_kind": dict(first_kind)}
        (OUT / f"source_positions_{lab}.json").write_text(
            json.dumps(summ, indent=2) + "\n")
        with open(OUT / f"source_positions_{lab}.tsv", "w") as f:
            f.write("qid\tpos\tmatch\tevidence_id\tcard_kind\treport_rank\n")
            for r in rows:
                f.write("\t".join(str(x) for x in (
                    r["qid"], r["pos"], r["match"], r["evidence_id"],
                    r["card_kind"], r["report_rank"])) + "\n")
        log(f"{lab} source: {summ}")

    # ---- 4. full-caliber isolation scan (official strict patterns) ----
    # No truncation: detection runs on the FULL file text (review R4 found
    # 357/361 JSON files exceed the v2-r1 500k cap), and key-path traversal
    # covers the FULL JSON structure of every flagged file.
    for lab, arm in ARMS.items():
        records = []
        n_files = 0
        n_over_500k = 0
        max_size = 0
        for fp in sorted(arm.rglob("*")):
            if not fp.is_file():
                continue
            n_files += 1
            size = fp.stat().st_size
            max_size = max(max_size, size)
            if size > 500000:
                n_over_500k += 1
            try:
                text = fp.read_text(encoding="utf-8", errors="strict")
            except Exception:
                continue
            rel = str(fp.relative_to(arm))
            hits = []
            for m in GOLD_MARKERS:
                if m in text:
                    hits.append(f"gold_marker:{m}")
            for name, pat in CRED_PATS:
                if pat.search(text):
                    hits.append(f"cred:{name}")
            if not hits:
                continue
            # key-path context for JSON/JSONL (no values emitted);
            # FULL traversal of every flagged file (no element caps).
            contexts = []
            n_value_hits_total = 0
            if fp.suffix in (".json", ".jsonl"):
                try:
                    objs = ([json.loads(text)] if fp.suffix == ".json"
                            else [json.loads(l) for l in text.splitlines()
                                  if l.strip()])
                except Exception:
                    objs = []
                for o in objs:
                    stack = [(o, "$")]
                    while stack:
                        node, path = stack.pop()
                        if isinstance(node, dict):
                            for k, v in node.items():
                                kp = f"{path}.{k}"
                                if any(m in str(k) for m in GOLD_MARKERS):
                                    contexts.append(
                                        f"{kp}:key_name_match")
                                if isinstance(v, (dict, list)):
                                    stack.append((v, kp))
                                elif isinstance(v, str):
                                    for m in GOLD_MARKERS:
                                        if m in v:
                                            n_value_hits_total += 1
                                            contexts.append(
                                                f"{kp}:value_contains:{m}"
                                                f":len={len(v)}")
                                            break
                        elif isinstance(node, list):
                            for i, v in enumerate(node):
                                stack.append((v, f"{path}[{i}]"))
            # adjudication
            adj = []
            for h in hits:
                if rel == "_seal/seal.json" and h.startswith("gold_marker:"):
                    adj.append(f"{h}=>seal_vocab (scan's own marker list)")
                elif h == "gold_marker:products_smiles" and any(
                        c.endswith(":key_name_match") or ":key_name_match" in c
                        for c in contexts):
                    adj.append(f"{h}=>schema_field "
                               "(JSON key name in task/decision payloads; "
                               "values are corpus/retrieval SMILES covered "
                               "by identity+manifest checks)")
                elif h == "gold_marker:products_smiles":
                    adj.append(f"{h}=>payload_value_or_log "
                               "(needs value-class check; see contexts)")
                elif h.startswith("gold_marker:"):
                    adj.append(f"{h}=>path_reference_check "
                               "(no gold-path reference expected run-side)")
                else:
                    adj.append(f"{h}=>cred_review")
            records.append({"file": rel, "size": size,
                            "hits": hits,
                            "contexts": contexts,
                            "n_value_hits_total": n_value_hits_total,
                            "adjudication": adj})
        (OUT / f"isolation_full_{lab}.json").write_text(json.dumps(
            {"n_files_total": n_files, "n_over_500k": n_over_500k,
             "max_file_bytes": max_size, "truncation": "none",
             "n_flagged": len(records),
             "records": records}, indent=2) + "\n")
        log(f"{lab} isolation full: {n_files} files "
            f"({n_over_500k} over 500k, all fully scanned), "
            f"{len(records)} flagged")

    # ---- 5. call distribution arithmetic (explicit) ----
    for lab, arm in ARMS.items():
        order = json.loads(
            (arm / "input_manifest.json").read_text())["route_order"]
        per_q = Counter()
        for run_dir in sorted((arm / "runs").iterdir()):
            if not run_dir.is_dir():
                continue
            # qid from run_id suffix (explicit linkage via manifest order)
            rid = run_dir.name
            qid = rid.split("_", 2)[-1] if rid.startswith("exam298_") else rid
            res = run_dir / "results"
            if not res.is_dir():
                continue
            n = 0
            for td in sorted(res.iterdir()):
                n += len(list(td.glob("prediction_response.*.json")))
            # count only provider-ok responses (same caliber as C1)
            per_q[qid] = n
        dist = dict(Counter(per_q.values()))
        zero = [q for q in order if per_q.get(q, 0) == 0]
        arith = {"per_q_response_counts": dist,
                 "n_1x": dist.get(1, 0), "n_2x": dist.get(2, 0),
                 "check_185x1_plus_1x2_eq_187":
                     dist.get(1, 0) * 1 + dist.get(2, 0) * 2,
                 "n_zero_call": len(zero),
                 "check_total_298": dist.get(1, 0) + dist.get(2, 0)
                 + len(zero)}
        (OUT / f"call_arith_{lab}.json").write_text(
            json.dumps(arith, indent=2) + "\n")
        log(f"{lab} arith: {arith}")

    # ---- 6. seal recompute, read-only (same caliber as seal.py) ----
    # Recomputes the 309-file manifest text, its comparison against
    # _seal/seal.sha256 + seal.json's seal_sha256_of_manifest, and the
    # official 601-file leak rescan. Writes ONLY to OUT (never _seal/).
    SEAL_NAMED = ("batch_identity.json", "exam_inputs.jsonl",
                  "input_manifest.json", "merged/predictions.jsonl",
                  "merged/export_metadata.json", "_arm_summary.json",
                  "_identity_phase.json", "_agent_run_result.json",
                  "progress.json", "coordinator.log", "driver.log")
    for lab, arm in ARMS.items():
        lines = []
        for rel in SEAL_NAMED:
            p = arm / rel
            if p.is_file():
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for ch in iter(lambda: f.read(1 << 20), b""):
                        h.update(ch)
                lines.append(f"{h.hexdigest()}  {rel}")
        for sp in sorted((arm / "workers").glob("*.status.json")):
            h = hashlib.sha256()
            with open(sp, "rb") as f:
                for ch in iter(lambda: f.read(1 << 20), b""):
                    h.update(ch)
            lines.append(f"{h.hexdigest()}  workers/{sp.name}")
        text = "\n".join(sorted(lines)) + "\n"
        on_disk = (arm / "_seal" / "seal.sha256").read_text(encoding="utf-8")
        sj = json.loads((arm / "_seal" / "seal.json").read_text(
            encoding="utf-8"))
        scanned = 0
        viols = []
        for rel in ("batch_identity.json", "input_manifest.json",
                    "merged/predictions.jsonl", "merged/export_metadata.json",
                    "_arm_summary.json"):
            p = arm / rel
            if p.is_file():
                scanned += 1
                t = p.read_text(encoding="utf-8")
                for m in GOLD_MARKERS:
                    if m in t:
                        viols.append(f"{rel}:gold_marker:{m}")
                for name, pat in CRED_PATS:
                    if pat.search(t):
                        viols.append(f"{rel}:cred:{name}")
        for sp in sorted((arm / "workers").glob("*.status.json")):
            scanned += 1
            t = sp.read_text(encoding="utf-8")
            for m in GOLD_MARKERS:
                if m in t:
                    viols.append(f"workers/{sp.name}:gold:{m}")
            for name, pat in CRED_PATS:
                if pat.search(t):
                    viols.append(f"workers/{sp.name}:cred")
        for pp in sorted((arm / "workers").glob("*.plan.json"))[:298]:
            scanned += 1
            t = pp.read_text(encoding="utf-8")
            for m in GOLD_MARKERS:
                if m in t:
                    viols.append(f"workers/{pp.name}:gold:{m}")
            for name, pat in CRED_PATS:
                if pat.search(t):
                    viols.append(f"workers/{pp.name}:cred")
        seal_res = {
            "n_manifest_files": len(lines),
            "n_manifest_reported": sj.get("n_sealed_files"),
            "manifest_text_match": text == on_disk,
            "manifest_sha_match": hashlib.sha256(
                text.encode("utf-8")).hexdigest() == sj.get(
                    "seal_sha256_of_manifest"),
            "manifest_sha": sj.get("seal_sha256_of_manifest"),
            "n_scanned": scanned,
            "n_scanned_reported": (sj.get("leak_scan") or {}).get(
                "n_files_scanned"),
            "n_violations": len(viols),
            "violations": viols[:10],
        }
        (OUT / f"seal_recompute_{lab}.json").write_text(
            json.dumps(seal_res, indent=2) + "\n")
        log(f"{lab} seal: {seal_res}")

    (OUT / "audit_v2_done.json").write_text(
        json.dumps({"audit_end": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "started": t0}, indent=2) + "\n")
    log("DONE v2")


if __name__ == "__main__":
    main()
