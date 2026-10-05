#!/usr/bin/env python
"""金标体检 R1–R4 全量打标(dev 56 + 298 全卷;零 LLM;金标只在本进程读)。

任务书 §D;预注册 §5;规则实现 src/pathway_v43/gold_health.py
(判据待 mimo 评审冻结)。输出只有 qid/旗标/计数,无任何 SMILES。

- dev:题面 = dev_questions.jsonl 的 root_smiles;金标 = dev_gold.jsonl
  (gitignored,仅本进程打开);
- 298:题面/金标 = dual_track_rescore/work/questions_298.jsonl
  (gitignored 只读副本,SHA 9f5955d4…;只诊断打标,不动分数不动金标);
- quarantine 提案(仅 dev):R1/R3/R4 命中题 → 处置建议"剔出分母",
  标注**待人审 + mimo 评审后生效**;本轮只出提案。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from pathway_v43.gold_health import (  # noqa: E402
    FLAG_R1,
    FLAG_R3,
    FLAG_R4,
    RULES_VERSION,
    gold_health_labels,
)

REPO = Path(__file__).resolve().parents[3]
DEV_QUESTIONS = REPO / "reports/phase_s1_hit60/dev_questions.jsonl"
DEV_GOLD = REPO / "reports/phase_s1_hit60/dev_gold/dev_gold.jsonl"
Q298 = (REPO / "reports/phase_s15_hit60/dual_track_rescore/work"
        / "questions_298.jsonl")
OUT = REPO / "reports/phase_s15_hit60/gold_health_check"

COLUMNS = [
    "qid", "flags", "r1", "r3", "r4", "r1_hit_elements", "new_elements",
    "unlisted_new_elements", "r2_retained", "substrate_c", "gold_c",
    "n_products", "n_parse_fail_products",
]

PROPOSAL_COLUMNS = [
    "qid", "flags", "rule_hits", "substrate_c", "gold_c",
    "proposed_disposition", "status",
]
PROPOSED_DISPOSITION = "剔出分母入 quarantine(题卷与金标冻结不改)"
PROPOSAL_STATUS = "提案:待人审+mimo 评审后生效(本轮不生效)"


def _iter_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, set)):
        return ";".join(sorted(str(x) for x in v)) if v else ""
    return str(v).replace("\t", " ").replace("\n", " ")


def _write_tsv(path: Path, columns: list[str], rows: list[dict]) -> None:
    lines = ["\t".join(columns)]
    for r in rows:
        lines.append("\t".join(_fmt(r.get(c)) for c in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_corpus(name: str, question_rows: list[dict], gold_rows: dict,
                out_prefix: str) -> tuple[list[dict], dict]:
    rows = []
    for q in question_rows:
        qid = q["qid"]
        if qid not in gold_rows:
            raise SystemExit(f"{name}:题面 qid 无金标(fail-closed):{qid}")
        labels = gold_health_labels(
            substrate_smiles=q["substrate_smiles"],
            products_smiles=gold_rows[qid])
        rows.append({"qid": qid, **labels})
    _write_tsv(OUT / f"gold_health_labels_{out_prefix}.tsv", COLUMNS, rows)
    stats = {
        "corpus": name,
        "rules_version": RULES_VERSION,
        "n_questions": len(rows),
        "n_flagged": sum(1 for r in rows if r["flags"]),
        "n_r1": sum(1 for r in rows if r["r1"]),
        "n_r3": sum(1 for r in rows if r["r3"]),
        "n_r4": sum(1 for r in rows if r["r4"]),
        "n_r2_retained": sum(1 for r in rows if r["r2_retained"]),
        "n_unlisted_new_elements": sum(
            1 for r in rows if r["unlisted_new_elements"]),
        "distinct_flagged_qids": sorted(
            r["qid"] for r in rows if r["flags"]),
    }
    return rows, stats


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- dev 56 ----
    dev_questions = [{"qid": r["qid"], "substrate_smiles": r["root_smiles"]}
                     for r in _iter_jsonl(DEV_QUESTIONS)]
    dev_gold = {r["qid"]: r.get("products_smiles", [])
                for r in _iter_jsonl(DEV_GOLD)}
    dev_rows, dev_stats = _run_corpus(
        "dev56(B1 环境路径中间步骤)", dev_questions, dev_gold, "dev")

    # dev quarantine 提案(R1/R3/R4 命中;R2 保留不入提案)
    proposal = []
    for r in dev_rows:
        if r["flags"]:
            proposal.append({
                "qid": r["qid"], "flags": r["flags"],
                "rule_hits": "+".join(
                    {"gold_cosubstrate_unreachable": "R1",
                     "gold_conserv_violation": "R3",
                     "degenerate": "R4"}[f] for f in r["flags"]),
                "substrate_c": r["substrate_c"], "gold_c": r["gold_c"],
                "proposed_disposition": PROPOSED_DISPOSITION,
                "status": PROPOSAL_STATUS,
            })
    _write_tsv(OUT / "quarantine_proposal_dev.tsv",
               PROPOSAL_COLUMNS, proposal)

    # ---- 298 全卷(只诊断打标,不动分数不动金标) ----
    q298 = [{"qid": r["qid"], "substrate_smiles": r["substrate_smiles"],
             "products_smiles": r["products_smiles"],
             "nucleotide_fallback": r.get("nucleotide_fallback", False),
             "fallback_large": r.get("fallback_large", False),
             "ambiguous_substrate": r.get("ambiguous_substrate", False)}
            for r in _iter_jsonl(Q298)]
    q298_gold = {r["qid"]: r["products_smiles"] for r in q298}
    rows298, stats298 = _run_corpus(
        "ec298(RHEA 通用酶学;只诊断打标)",
        [{"qid": r["qid"], "substrate_smiles": r["substrate_smiles"]}
         for r in q298], q298_gold, "298")

    # 298 旗标交叉(nucleotide_fallback / fallback_large / ambiguous)
    cross = {}
    for key in ("nucleotide_fallback", "fallback_large",
                "ambiguous_substrate"):
        flagged = [r["qid"] for r in q298
                   if r[key] and any(
                       x["qid"] == r["qid"] and x["flags"]
                       for x in rows298)]
        cross[key] = {"n_true": sum(1 for r in q298 if r[key]),
                      "n_true_and_flagged": len(flagged),
                      "flagged_qids": flagged}
    stats298["question_flag_cross"] = cross

    summary = {
        "dev": dev_stats,
        "dev_quarantine_proposal": {
            "n_proposed": len(proposal),
            "proposed_denominator": 56 - len(proposal),
            "disposition": PROPOSED_DISPOSITION,
            "status": PROPOSAL_STATUS,
            "note": "提案不生效:剔分母处置等人审 + mimo 评审"
                    "(docs/mimo_gold_rules_review_request.md 待送)后再生效;"
                    "v3 主封存仍为全 56 分母。",
        },
        "ec298": stats298,
        "inputs_sha256": {
            "dev_questions": hashlib.sha256(
                DEV_QUESTIONS.read_bytes()).hexdigest(),
            "dev_gold": hashlib.sha256(DEV_GOLD.read_bytes()).hexdigest(),
            "questions_298": hashlib.sha256(
                Q298.read_bytes()).hexdigest(),
        },
    }
    (OUT / "gold_health_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
