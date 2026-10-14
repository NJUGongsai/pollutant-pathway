#!/usr/bin/env python
"""chain13 v2 口径判分 wrapper(headline=ppv1-criteria-v2;生效后首个新批)。

用法(HPC 仓根,PYTHONPATH=<v43c13>/src):
    python -B chain13_score_v2.py <batch_root> <runs_root>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pathway_v43.pollutant.s5b_scoring import score_s5b_batch


def main(argv: list[str]) -> int:
    batch_root, runs_root = argv[1:3]
    agg = score_s5b_batch(
        batch_root,
        runs_root=runs_root,
        data_scope="real",
        criteria_version="ppv1-criteria-v2",
    )
    mc = agg["main_caliber"]
    out = {
        "command": "chain13_score_v2",
        "criteria_version": "ppv1-criteria-v2",
        "hit@1": mc["hit@1"], "hit@3": mc["hit@3"], "hit@5": mc["hit@5"],
        "buckets": agg.get("buckets"),
        "criteria_v2": agg.get("criteria_v2"),
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
