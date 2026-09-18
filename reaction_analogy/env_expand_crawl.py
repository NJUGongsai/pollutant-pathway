#!/usr/bin/env python3
"""enviPath environmental-package crawler (soil/sludge repair, 2026-09-18).

Fetches ALL reactions (educts + products with SMILES) from the public
enviPath packages EAWAG-SOIL / EAWAG-SLUDGE / EAWAG-SEDIMENT via the legacy
JSON API (Django CSRF login — credentials read at runtime from
/Volumes/CC/BiocrewV2/.env, never stored).

Discipline (mirrors bbd_crawl.py):
  - deterministic ordering (sorted reaction ids), idempotent (raw JSON kept
    on disk; re-runs skip existing), polite rate limit, retries with backoff;
  - a crawl manifest records url/path/sha256/status per reaction;
  - NO answer key is consulted — the enumeration is the packages' public
    reaction lists (systematic, not cherry-picked).

Output:
  data/env_expand/raw/<pkg>/<reaction-uuid>.json   raw reaction details
  data/env_expand/manifest.json                    crawl manifest
  data/env_expand/env_reactions.jsonl              (educt, product) pairs:
    {package, pathway_id, pathway_name, reaction_id, reaction_name,
     educt_smiles, product_smiles, educt_name, product_name, smirks,
     ec_numbers, multistep, review_status}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "reaction_v3"))
sys.path.insert(0, os.path.join(_HERE, "..", "reaction_v3", "reaction_v3"))

from reaction_v3.sources.envipath import login, _get_json, EnviPathError  # noqa: E402

OUT_DIR = os.path.join(_HERE, "data", "env_expand")

PACKAGES = {
    "EAWAG-SOIL": "5882df9c-dae1-4d80-a40e-db4724271456",
    "EAWAG-SLUDGE": "521c547a-fd2a-491c-ad5b-7eaa1577fb65",
    "EAWAG-SEDIMENT": "f05e38d8-e9b4-4c3e-b0d8-9ab29966eccf",
}


def api_url(u: str) -> str:
    return u.replace("https://envipath.org", "https://envipath.org/api/legacy")


def short_id(u: str) -> str:
    return u.rstrip("/").split("/")[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rate", type=float, default=0.15)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--packages", default=",".join(PACKAGES))
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    session = login()
    print("login OK", flush=True)

    manifest = []
    rows = []
    for pkg_name in args.packages.split(","):
        pkg_id = PACKAGES[pkg_name]
        raw_dir = os.path.join(OUT_DIR, "raw", pkg_name)
        os.makedirs(raw_dir, exist_ok=True)
        print(f"[{pkg_name}] listing reactions...", flush=True)
        listing = _get_json(session, api_url(
            f"https://envipath.org/package/{pkg_id}/reaction"))
        reactions = listing.get("reaction", [])
        print(f"[{pkg_name}] {len(reactions)} reactions", flush=True)
        n_ok = n_fail = n_cached = 0
        for i, r in enumerate(sorted(reactions, key=lambda x: x.get("id", ""))):
            rid = r.get("id", "")
            if not rid:
                continue
            path = os.path.join(raw_dir, short_id(rid) + ".json")
            detail = None
            if os.path.exists(path) and os.path.getsize(path) > 50:
                detail = json.load(open(path))
                n_cached += 1
            else:
                for attempt in range(1, args.retries + 1):
                    try:
                        t_req = time.time()
                        detail = _get_json(session, api_url(rid))
                        req_el = time.time() - t_req
                        with open(path, "w") as f:
                            json.dump(detail, f, ensure_ascii=False, indent=1)
                        n_ok += 1
                        # adaptive cooldown: a slow request signals server/
                        # proxy throttling — pause once and let it reset
                        if req_el > 8.0:
                            print(f"[{pkg_name}] slow request {req_el:.0f}s "
                                  f"— cooling down 240s", flush=True)
                            time.sleep(240)
                        break
                    except (EnviPathError, Exception) as e:  # noqa: BLE001
                        time.sleep(min(2.0 * attempt, 30.0))
                        last = e
                else:
                    n_fail += 1
                    manifest.append({"url": rid, "path": path,
                                     "status": "failed", "error": str(last)})
                    continue
            manifest.append({
                "url": rid, "path": path, "status": "ok",
                "sha256": hashlib.sha256(
                    open(path, "rb").read()).hexdigest()})
            if (i + 1) % 200 == 0:
                print(f"[{pkg_name}] {i+1}/{len(reactions)} "
                      f"(ok={n_ok} cached={n_cached} fail={n_fail})",
                      flush=True)
            # build rows
            pathways = detail.get("pathways") or []
            pw = pathways[0] if pathways else {}
            ecs = [str(e) for e in (detail.get("ecNumbers") or [])]
            for ed in detail.get("educts") or []:
                e_smi = (ed.get("smiles") or "").strip()
                if not e_smi:
                    continue
                for pr in detail.get("products") or []:
                    p_smi = (pr.get("smiles") or "").strip()
                    if not p_smi:
                        continue
                    rows.append({
                        "package": pkg_name,
                        "pathway_id": short_id(pw.get("id", "")),
                        "pathway_name": pw.get("name", ""),
                        "reaction_id": short_id(rid),
                        "reaction_name": detail.get("name", ""),
                        "educt_smiles": e_smi,
                        "product_smiles": p_smi,
                        "educt_name": ed.get("compoundName", ""),
                        "product_name": pr.get("compoundName", ""),
                        "smirks": detail.get("smirks", ""),
                        "ec_numbers": ecs,
                        "multistep": detail.get("multistep", None),
                        "review_status": detail.get("reviewStatus", ""),
                    })
            time.sleep(args.rate)

    rows.sort(key=lambda r: (r["package"], r["reaction_id"],
                             r["educt_smiles"], r["product_smiles"]))
    with open(os.path.join(OUT_DIR, "env_reactions.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump({"n_reactions": len(manifest), "n_pairs": len(rows),
                   "packages": args.packages.split(","),
                   "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "entries": manifest}, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print(f"DONE: {len(manifest)} reactions, {len(rows)} (educt,product) pairs",
          flush=True)
    print("pairs by package:", dict(Counter(r["package"] for r in rows)),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
