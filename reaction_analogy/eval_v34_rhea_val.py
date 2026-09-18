#!/usr/bin/env python3
"""v3.4 vs v3.3 on the RHEA validation split (domain-shift reference).

The EAWAG calib/val splits are the primary (environmental) validation; this
script reports the RHEA val split (1,234 educts, retrieval-covered regime)
as the second reference domain required by the feedback protocol: v3.4 must
not catastrophically regress where v3.3 is strong.

NEVER reads soil/sludge gold.  Reuses the diag module's helpers.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import bbd_v33_fusion as V33  # noqa: E402
import bbd_v34_fusion as V34  # noqa: E402
import diag_ss_feedback_20260918 as D  # noqa: E402

OUT = os.path.join(_HERE, "reports/SS_DIAG_2026-09-18")
KS = (1, 3, 5, 10)


def main() -> int:
    t0 = time.time()
    rankers = D.load_rankers(os.path.join(D.ROOT, "data/bbd_v31"))
    calib = V34.SourceCalibrator.load(
        os.path.join(D.ROOT, "data/bbd_v34/calibrator_v34.json"))

    val = set(json.load(open(D.VAL_SPLIT))["val_educts_sb"])
    truth = D.corpus_truth_for(val)
    groups: dict[str, list[dict]] = defaultdict(list)
    with open(D.RHEA_CACHE) as f:
        for line in f:
            r = json.loads(line)
            if r["educt_sb"] in val:
                groups[r["educt_sb"]].append(r)
    print(f"{len(groups)} RHEA-val educts loaded ({time.time()-t0:.0f}s)",
          flush=True)

    hits = {"v33": {k: 0 for k in KS}, "v34": {k: 0 for k in KS}}
    n = 0
    items = sorted(groups.items())
    for i, (esb, cands) in enumerate(items):
        ts = truth.get(esb, set())
        tsn = {D.sbn(t) for t in ts}
        cands = [dict(c) for c in cands]
        D.score_case(cands, esb, rankers)

        r33 = V33.score_candidates_v33([dict(c) for c in cands], esb)
        r34 = V34.score_candidates_v34([dict(c) for c in cands], esb, calib)

        def hr(ranked):
            for j, m in enumerate(ranked):
                pid = m.get("product_identity", m.get("product_smiles", ""))
                if D.sbn(pid) in tsn:
                    return j + 1
            return None
        h33, h34 = hr(r33), hr(r34)
        n += 1
        for k in KS:
            if h33 is not None and h33 <= k:
                hits["v33"][k] += 1
            if h34 is not None and h34 <= k:
                hits["v34"][k] += 1
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(items)} ({time.time()-t0:.0f}s)", flush=True)

    out = {
        "n": n,
        "v33": {f"hit@{k}": round(hits["v33"][k] / max(n, 1), 4) for k in KS},
        "v34": {f"hit@{k}": round(hits["v34"][k] / max(n, 1), 4) for k in KS},
    }
    with open(os.path.join(OUT, "v34_rhea_val_reference.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=1), flush=True)
    print(f"DONE {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
