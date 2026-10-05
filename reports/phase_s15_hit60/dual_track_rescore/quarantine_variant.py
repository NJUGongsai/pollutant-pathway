#!/usr/bin/env python
"""quarantine 变体读数(分母 56 − 提案数;标「待人审+mimo 评审后生效」)。

预注册 §4:变体读数不替代主封存、不动题卷不动金标。本脚本从
sealed/readings_s15_dev_*.json(封存主读数)与
gold_health_check/quarantine_proposal_dev.tsv(提案,未生效)确定性推导:
剔除提案 qid 后的 v3/整串读数。零 LLM;输出无 SMILES。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SEALED = REPO / "reports/phase_s15_hit60/dual_track_rescore/sealed"
PROPOSAL = (REPO / "reports/phase_s15_hit60/gold_health_check"
            / "quarantine_proposal_dev.tsv")
TAGS = ["C0a", "C0b", "E1", "E2a", "E2b", "E3"]
OUT = SEALED / "quarantine_variant_dev.json"


def main() -> int:
    quarantine = set()
    for line in PROPOSAL.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip():
            quarantine.add(line.split("\t")[0])
    if not quarantine:
        raise SystemExit("quarantine 提案为空(fail-closed)")

    per_batch = {}
    for tag in TAGS:
        d = json.loads((SEALED / f"readings_s15_dev_{tag}.json").read_text(
            encoding="utf-8"))
        rows = d["per_question"]
        kept = [q for q in rows if q["qid"] not in quarantine]
        dropped = [q for q in rows if q["qid"] in quarantine]
        if len(kept) + len(dropped) != 56 or len(dropped) != len(quarantine):
            raise SystemExit(f"{tag}: 分母核算不符(fail-closed)")

        def hits(rws, key, k):
            return sum(1 for q in rws if q[f"hit_{key}@{k}"])

        v3 = [hits(kept, "v3", k) for k in (1, 3, 5)]
        wh = [hits(kept, "whole", k) for k in (1, 3, 5)]
        n = len(kept)
        per_batch[tag] = {
            "denominator": n,
            "component_v3": {
                "hit@1": v3[0], "hit@3": v3[1], "hit@5": v3[2],
                "hit@1_rate": round(v3[0] / n, 4),
                "hit@3_rate": round(v3[1] / n, 4),
                "hit@5_rate": round(v3[2] / n, 4)},
            "whole_string_v2": {"hit@1": wh[0], "hit@3": wh[1],
                                "hit@5": wh[2]},
            "quarantined_qids_all_miss": all(
                not (q["hit_v3@1"] or q["hit_v3@3"] or q["hit_v3@5"]
                     or q["hit_whole@1"] or q["hit_whole@3"]
                     or q["hit_whole@5"]) for q in dropped),
        }

    c0 = [per_batch["C0a"]["component_v3"]["hit@1"],
          per_batch["C0b"]["component_v3"]["hit@1"]]
    result = {
        "schema_version": "s15-quarantine-variant-1",
        "status": "待人审+mimo 评审后生效(本轮不生效;不替代全 56 分母主封存)",
        "basis": {
            "main_seal": "dual_track_rescore/sealed/readings_s15_dev_*.json"
                         "(全 56 分母,口径 v3)",
            "proposal": "gold_health_check/quarantine_proposal_dev.tsv"
                        "(R1/R3/R4 提案 5 题,未生效)",
        },
        "per_batch": per_batch,
        "c0_baseline_variant": {
            "hit@1_a": c0[0], "hit@1_b": c0[1], "hit@1_mean": sum(c0) / 2,
            "rate_mean": round(sum(c0) / 2 / per_batch["C0a"]["denominator"],
                               4),
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                              sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
