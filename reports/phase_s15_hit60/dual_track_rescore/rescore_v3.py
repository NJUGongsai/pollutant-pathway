#!/usr/bin/env python
"""口径 v3 双轨重算 driver(零 LLM;金标只在本离线评分进程打开)。

预注册:reports/phase_s15_hit60/PREREGISTRATION_V3.md。
双轨 = 整串(v2,exam_v2.first_hit_rank,锚点复现)+ 组分 v3
(exam_v2.first_full_coverage_rank,全主产物命中)。主分只认 v3 轨;
partial/scattered/超集披露列单列;rank_v3_cum 为累计覆盖敏感性辅读
(不进主分,见预注册 §1.2)。

用法(本地 conda depending43,OMP_NUM_THREADS=1 PYTHONPATH=src):

  # 单批评分(锚点 fail-closed:@1/@3/@5 与官方读数不符即停):
  python reports/phase_s15_hit60/dual_track_rescore/rescore_v3.py \
      --answers <answers.jsonl> --gold <gold.jsonl> \
      --label s15_dev_C0a --out-dir <sealed_dir> \
      --anchor-whole 8,16,19 \
      [--expect-answers-sha <sha256>] [--expect-gold-sha <sha256>]

  # --check 复算(与封存 readings 逐字节一致):
  python .../rescore_v3.py --check <sealed_dir>/readings_<label>.json \
      --answers ... --gold ...

输出(不含任何金标 SMILES,只有 qid/计数/位次/旗标):
readings_<label>.json(summary + per_question)。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from pathway_v43.exam_v2 import (  # noqa: E402
    CALIBER_V3_DEF,
    CALIBER_V3_VERSION,
    agent_candidates,
    candidate_component_ids,
    first_full_coverage_rank,
    first_hit_rank,
    gold_main_component_ids,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _iter_jsonl(path: str | Path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _write_json(out_path: Path, payload: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    tmp.replace(out_path)


def _load_gold_components(gold_path: Path) -> dict[str, frozenset[str]]:
    gold: dict[str, frozenset[str]] = {}
    for rec in _iter_jsonl(gold_path):
        qid = rec.get("qid")
        if not qid:
            raise SystemExit("金标行缺 qid(fail-closed)")
        if qid in gold:
            raise SystemExit(f"金标 qid 重复(fail-closed):{qid}")
        gold[qid] = gold_main_component_ids(rec.get("products_smiles", []))
    if not gold:
        raise SystemExit("金标为空(fail-closed)")
    return gold


def score_answers(*, answers_path: Path, gold_path: Path, label: str,
                  routes: dict[str, str] | None = None,
                  anchor_whole: tuple[int, int, int] | None = None,
                  expect_answers_sha: str | None = None,
                  expect_gold_sha: str | None = None) -> dict:
    gold = _load_gold_components(gold_path)
    per_question: list[dict] = []
    seen: set[str] = set()
    for row in _iter_jsonl(answers_path):
        qid = row.get("route_id")
        if qid not in gold:
            raise SystemExit(f"答卷 qid 不在金标(fail-closed):{qid}")
        if qid in seen:
            raise SystemExit(f"答卷 qid 重复(fail-closed):{qid}")
        seen.add(qid)
        g = gold[qid]
        products = agent_candidates(row)
        rank_whole = first_hit_rank(products, set(g))
        rank_v3 = first_full_coverage_rank(products, g)
        # 累计覆盖敏感性辅读(scattered 全覆盖按覆盖完成位次;不进主分)
        cum: set[str] = set()
        rank_v3_cum = None
        for i, p in enumerate(products, 1):
            cum |= candidate_component_ids(p)
            if rank_v3_cum is None and g <= cum:
                rank_v3_cum = i
        covered: set[str] = set()
        for p in products:
            covered |= candidate_component_ids(p) & set(g)
        hit_extra = bool(
            rank_v3 is not None
            and candidate_component_ids(products[rank_v3 - 1]) - set(g))
        partial = rank_v3 is None and bool(covered)
        per_question.append({
            "qid": qid,
            "route": (routes or {}).get(qid, ""),
            "n_pred": len(products),
            "n_gold_components": len(g),
            "n_covered": len(covered),
            "rank_whole": rank_whole,
            "rank_v3": rank_v3,
            "rank_v3_cum_sensitivity": rank_v3_cum,
            "hit_whole@1": rank_whole is not None and rank_whole <= 1,
            "hit_whole@3": rank_whole is not None and rank_whole <= 3,
            "hit_whole@5": rank_whole is not None and rank_whole <= 5,
            "hit_v3@1": rank_v3 is not None and rank_v3 <= 1,
            "hit_v3@3": rank_v3 is not None and rank_v3 <= 3,
            "hit_v3@5": rank_v3 is not None and rank_v3 <= 5,
            "empty_answer": len(products) == 0,
            "partial": partial,
            "scattered_full": rank_v3 is None and covered == set(g),
            "hit_with_extra_components": hit_extra,
        })
    if len(per_question) != len(gold) or seen != set(gold):
        raise SystemExit(
            f"答卷题数/集合与金标不一致(fail-closed):"
            f"n={len(per_question)} gold={len(gold)}")

    def hits(key: str, k: int) -> int:
        return sum(1 for q in per_question
                   if q[f"hit_{key}@{k}"])

    whole = tuple(hits("whole", k) for k in (1, 3, 5))
    if anchor_whole is not None and whole != anchor_whole:
        raise SystemExit(
            f"锚点 fail-closed:{label} 整串 @1/@3/@5 = {whole},"
            f"官方锚点 = {anchor_whole}——不符即停")
    v3 = tuple(hits("v3", k) for k in (1, 3, 5))
    cum_hits = tuple(
        sum(1 for q in per_question
            if q["rank_v3_cum_sensitivity"] is not None
            and q["rank_v3_cum_sensitivity"] <= k)
        for k in (1, 3, 5))
    answers_sha = _sha256_file(answers_path)
    gold_sha = _sha256_file(gold_path)
    if expect_answers_sha and answers_sha != expect_answers_sha:
        raise SystemExit(f"answers SHA 不符(fail-closed):{label}")
    if expect_gold_sha and gold_sha != expect_gold_sha:
        raise SystemExit(f"gold SHA 不符(fail-closed):{label}")
    n = len(per_question)
    summary = {
        "label": label,
        "caliber_version": CALIBER_V3_VERSION,
        "caliber_definition": CALIBER_V3_DEF,
        "identity": "cn-v1 (pathway_v43.domain.identity;与判分同源)",
        "n_questions": n,
        "whole_string_v2": {
            "hit@1": whole[0], "hit@3": whole[1], "hit@5": whole[2],
            "n_miss": sum(1 for q in per_question if q["rank_whole"] is None),
            "note": "锚点复现轨(同输入同代码;官方读数不覆写)",
        },
        "component_v3_main": {
            "hit@1": v3[0], "hit@3": v3[1], "hit@5": v3[2],
            "hit@1_rate": round(v3[0] / n, 4),
            "hit@3_rate": round(v3[1] / n, 4),
            "hit@5_rate": round(v3[2] / n, 4),
            "n_miss": sum(1 for q in per_question if q["rank_v3"] is None),
            "n_partial": sum(1 for q in per_question if q["partial"]),
            "n_scattered_full": sum(1 for q in per_question
                                    if q["scattered_full"]),
            "n_hit_with_extra_components": sum(
                1 for q in per_question if q["hit_with_extra_components"]),
        },
        "delta_v3_minus_whole": {
            "@1": v3[0] - whole[0], "@3": v3[1] - whole[1],
            "@5": v3[2] - whole[2]},
        "sensitivity_cumulative_coverage": {
            "hit@1": cum_hits[0], "hit@3": cum_hits[1], "hit@5": cum_hits[2],
            "note": "辅读不进主分:scattered 全覆盖按覆盖完成位次"
                    "(PREREGISTRATION_V3 §1.2 已否决为主分语义,仅披露)",
        },
        "answers_sha256": answers_sha,
        "gold_sha256": gold_sha,
    }
    return {"summary": summary, "per_question": per_question}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--answers", help="封存 merged/predictions.jsonl")
    ap.add_argument("--gold", help="只读金标(仅本进程打开)")
    ap.add_argument("--label", default="")
    ap.add_argument("--out-dir", default=None,
                    help="输出目录(readings_<label>.json 落此)")
    ap.add_argument("--routes-json", default=None,
                    help="dev 批次路由图(m1_dump/meta_*.json,可选)")
    ap.add_argument("--anchor-whole", default=None,
                    help="官方整串 @1,@3,@5 锚点,如 8,16,19(fail-closed)")
    ap.add_argument("--expect-answers-sha", default=None)
    ap.add_argument("--expect-gold-sha", default=None)
    ap.add_argument("--check", default=None,
                    help="复算并与封存 readings JSON 逐字节比对")
    args = ap.parse_args(argv)

    routes: dict[str, str] | None = None
    if args.routes_json:
        meta = json.loads(Path(args.routes_json).read_text(encoding="utf-8"))
        routes = {qid: str(v) for qid, v in meta["routes"].items()}
    anchor = None
    if args.anchor_whole:
        anchor = tuple(int(x) for x in args.anchor_whole.split(","))

    result = score_answers(
        answers_path=Path(args.answers), gold_path=Path(args.gold),
        label=args.label, routes=routes, anchor_whole=anchor,
        expect_answers_sha=args.expect_answers_sha,
        expect_gold_sha=args.expect_gold_sha)

    if args.check:
        sealed = json.loads(Path(args.check).read_text(encoding="utf-8"))
        recomputed = json.dumps(result, ensure_ascii=False, sort_keys=True)
        sealed_txt = json.dumps(sealed, ensure_ascii=False, sort_keys=True)
        if recomputed != sealed_txt:
            raise SystemExit(f"--check 复算与封存件不一致(fail-closed):"
                             f"{args.check}")
        print(json.dumps({"check": "PASS", "label": args.label,
                          "path": args.check}, ensure_ascii=False))
        return 0

    if args.out_dir:
        out = Path(args.out_dir) / f"readings_{args.label}.json"
        _write_json(out, result)
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
