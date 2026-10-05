#!/usr/bin/env python
"""S1 HIT60 dev 评分器(零 LLM;金标只在独立评分进程读取)。

口径与 exam_v2(v43-ec298-scorer-2)同源:直接 import 其
``load_gold`` / ``agent_candidates`` / ``first_hit_rank`` ——
cn_identity(仓内 pathway_v43.domain.identity,IDENTITY_VERSION=cn-v1)、
整条候选字符串计分、不可解析候选占名次、重复身份跳过、
任一金标产物的最早 1-based 位次。分母恒 56(空答留分母)。

用法(远端 dependingv43_s1 内,PYTHONPATH=src):

  单臂评分:
  .venv/bin/python scripts/s1_dev_score.py \
      --answers runs/<臂>/merged/predictions.jsonl \
      --gold exam/restricted/dev_gold.jsonl \
      --out-dir runs/<臂>/scoring --label s1_dev_C0_a

  两份答卷配对(四格/净赢/翻转):
  .venv/bin/python scripts/s1_dev_score.py \
      --pair runs/<A>/scoring/score.json runs/<B>/scoring/score.json \
      --out runs/<A>_vs_<B>_pair.json

  合成夹具自检(上岗前必过):
  .venv/bin/python scripts/s1_dev_score.py --self-test

红线:输出只含 qid/计数/位次/运行侧候选,不含任何金标 SMILES;
金标文件只在评分进程打开,评分后不回写、不复制。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCORER_VERSION = "s1-dev-scorer-1 (exam_v2 同口径)"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(out_path: Path, payload: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    tmp.replace(out_path)


def score_answers(*, answers_path: str | Path, gold_path: str | Path,
                  out_dir: str | Path, label: str) -> dict:
    from pathway_v43.exam_v2 import (
        agent_candidates, first_hit_rank, load_gold,
    )
    from pathway_v43.domain.identity import cn_identity

    gold = load_gold(gold_path)
    n_expected = len(gold)
    per_question = []
    seen: set[str] = set()
    for row in _iter_jsonl(answers_path):
        qid = row.get("route_id")
        if qid not in gold:
            raise SystemExit(f"答卷 qid 不在金标(fail-closed):{qid}")
        if qid in seen:
            raise SystemExit(f"答卷 qid 重复(fail-closed):{qid}")
        seen.add(qid)
        products = agent_candidates(row)
        g = gold[qid]
        rank = first_hit_rank(products, g["gold_ids"])
        pred_ids = {i for i in (cn_identity(p) for p in products) if i}
        n_hit_products = len(pred_ids & g["gold_ids"])
        per_question.append({
            "qid": qid,
            "n_predicted": len(products),
            "rank": rank,
            "hit@1": rank is not None and rank <= 1,
            "hit@3": rank is not None and rank <= 3,
            "hit@5": rank is not None and rank <= 5,
            "empty_answer": len(products) == 0,
            "spurious": (len(products) > 0 and n_hit_products == 0),
            "first_product": (products[0] if products else ""),
        })
    if len(per_question) != n_expected or seen != set(gold):
        raise SystemExit(
            f"答卷题数/集合与金标不一致(fail-closed):"
            f"n={len(per_question)} gold={n_expected}")

    def hits(k: int) -> int:
        return sum(1 for q in per_question if q["rank"] is not None
                   and q["rank"] <= k)

    n = len(per_question)
    summary = {
        "scorer_version": SCORER_VERSION,
        "identity_caliber": ("cn (pathway_v43.domain.identity,与 exam_v2/"
                             "判分同源;整条候选字符串,不可解析占名次,"
                             "任一金标产物最早 1-based 位次)"),
        "label": label,
        "n_questions": n,
        "hit@1": hits(1), "hit@3": hits(3), "hit@5": hits(5),
        "hit@1_rate": round(hits(1) / n, 4),
        "hit@3_rate": round(hits(3) / n, 4),
        "hit@5_rate": round(hits(5) / n, 4),
        "n_miss": sum(1 for q in per_question if q["rank"] is None),
        "n_empty_answer": sum(1 for q in per_question if q["empty_answer"]),
        "n_spurious": sum(1 for q in per_question if q["spurious"]),
        "answers_sha256": _sha256_file(Path(answers_path)),
        "gold_sha256": _sha256_file(Path(gold_path)),
    }
    out_dir = Path(out_dir)
    _write_json(out_dir / "score.json", {
        "summary": summary, "per_question": per_question})
    _write_tsv(out_dir / "per_question.tsv", [
        "qid", "n_predicted", "rank", "hit@1", "hit@3", "hit@5",
        "empty_answer", "spurious", "first_product"], per_question)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return {"summary": summary, "per_question": per_question}


def pair_scores(*, score_a_path: str | Path, score_b_path: str | Path,
                out_path: str | Path) -> dict:
    a = json.loads(Path(score_a_path).read_text(encoding="utf-8"))
    b = json.loads(Path(score_b_path).read_text(encoding="utf-8"))
    qa = {q["qid"]: q for q in a["per_question"]}
    qb = {q["qid"]: q for q in b["per_question"]}
    if set(qa) != set(qb):
        raise SystemExit("两份评分 qid 集合不一致(fail-closed)")
    four = {f"@{k}": {"both": 0, "a_only": 0, "b_only": 0, "neither": 0}
            for k in (1, 3, 5)}
    rows = []
    n_a1 = n_b1 = 0
    n_flip_hit1 = 0
    n_flip_outcome_or_top = 0
    for qid in sorted(qa):
        x, y = qa[qid], qb[qid]
        for k in (1, 3, 5):
            key = f"@{k}"
            xa, yb = bool(x[f"hit@{k}"]), bool(y[f"hit@{k}"])
            four[key]["both" if xa and yb else "a_only" if xa else
                  "b_only" if yb else "neither"] += 1
        a1_hit, b1_hit = bool(x["hit@1"]), bool(y["hit@1"])
        n_a1 += a1_hit
        n_b1 += b1_hit
        flip1 = a1_hit != b1_hit
        top_changed = (x["first_product"] != y["first_product"])
        if flip1:
            n_flip_hit1 += 1
        if flip1 or top_changed:
            n_flip_outcome_or_top += 1
        rows.append({
            "qid": qid,
            "a_hit@1": a1_hit, "b_hit@1": b1_hit,
            "a_rank": x["rank"], "b_rank": y["rank"],
            "a_empty": x["empty_answer"], "b_empty": y["empty_answer"],
            "flip_hit@1": flip1,
            "first_product_changed": top_changed,
            "win_a_minus_b_at1": int(a1_hit) - int(b1_hit),
        })
    result = {
        "schema_version": "s1-dev-pair-1",
        "label_a": a["summary"]["label"], "label_b": b["summary"]["label"],
        "n": len(rows),
        "a_hit@1": n_a1, "b_hit@1": n_b1,
        "net_a_minus_b_hit@1": n_a1 - n_b1,
        "four_cell": four,
        "n_flip_hit@1": n_flip_hit1,
        "n_flip_hit@1_or_first_product": n_flip_outcome_or_top,
        "a_empty": a["summary"]["n_empty_answer"],
        "b_empty": b["summary"]["n_empty_answer"],
        "a_spurious": a["summary"]["n_spurious"],
        "b_spurious": b["summary"]["n_spurious"],
        "per_question": rows,
    }
    _write_json(Path(out_path), result)
    print(json.dumps({k: v for k, v in result.items()
                      if k != "per_question"}, ensure_ascii=False,
                     sort_keys=True))
    return result


def _iter_jsonl(path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _write_tsv(path: Path, columns: list[str], rows: list[dict]) -> None:
    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, bool):
            return "true" if v else "false"
        return str(v).replace("\t", " ").replace("\n", " ")

    lines = ["\t".join(columns)]
    for r in rows:
        lines.append("\t".join(fmt(r.get(c)) for c in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 合成夹具

FIXTURE_GOLD = [
    {"qid": "S1", "products_smiles": ["CCO"]},
    {"qid": "S2", "products_smiles": ["c1ccccc1"]},
    {"qid": "S3", "products_smiles": ["CC(=O)O"]},
    {"qid": "S4", "products_smiles": ["CCC"]},
    {"qid": "S5", "products_smiles": ["CCO", "CCC"]},
    {"qid": "S6", "products_smiles": ["c1ccccc1"]},
]
FIXTURE_ANSWERS_A = [
    {"route_id": "S1", "steps": [{"predicted_products": ["CCO"]}]},
    {"route_id": "S2", "steps": [{"predicted_products":
                                  ["CCO", "c1ccccc1"]}]},
    {"route_id": "S3", "steps": [{"predicted_products":
                                  ["this_is_NOT_smiles", "CC(=O)O"]}]},
    {"route_id": "S4", "steps": []},
    {"route_id": "S5", "steps": [{"predicted_products": ["CCC"]}]},
    {"route_id": "S6", "steps": [{"predicted_products": ["CCO"]}]},
]
# 与 A 的差异:S1 顺序对调(@1 翻转 hit→miss)、S2 首位直接命中(@1 翻转
# miss→hit)、S5 换成金标另一产物(仍@1,不算翻转)、S6 不变。
FIXTURE_ANSWERS_B = [
    {"route_id": "S1", "steps": [{"predicted_products":
                                  ["c1ccccc1", "CCO"]}]},
    {"route_id": "S2", "steps": [{"predicted_products":
                                  ["c1ccccc1", "CCO"]}]},
    {"route_id": "S3", "steps": [{"predicted_products":
                                  ["this_is_NOT_smiles", "CC(=O)O"]}]},
    {"route_id": "S4", "steps": []},
    {"route_id": "S5", "steps": [{"predicted_products": ["CCO"]}]},
    {"route_id": "S6", "steps": [{"predicted_products": ["CCO"]}]},
]


def self_test(tmp_dir: Path) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    gold_p = tmp_dir / "fixture_gold.jsonl"
    ans_a = tmp_dir / "fixture_a.jsonl"
    ans_b = tmp_dir / "fixture_b.jsonl"
    gold_p.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n"
                for r in FIXTURE_GOLD), encoding="utf-8")
    ans_a.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n"
                for r in FIXTURE_ANSWERS_A), encoding="utf-8")
    ans_b.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n"
                for r in FIXTURE_ANSWERS_B), encoding="utf-8")
    sa = score_answers(answers_path=ans_a, gold_path=gold_p,
                       out_dir=tmp_dir / "a", label="fixture_a")
    sb = score_answers(answers_path=ans_b, gold_path=gold_p,
                       out_dir=tmp_dir / "b", label="fixture_b")
    exp_a = {"hit@1": 2, "hit@3": 4, "hit@5": 4, "n_empty_answer": 1,
             "n_spurious": 1, "n_miss": 2}
    exp_b = {"hit@1": 2, "hit@3": 4, "hit@5": 4, "n_empty_answer": 1,
             "n_spurious": 1, "n_miss": 2}
    got_a = {k: sa["summary"][k] for k in exp_a}
    got_b = {k: sb["summary"][k] for k in exp_b}
    assert got_a == exp_a, f"夹具 A 期望 {exp_a},实际 {got_a}"
    assert got_b == exp_b, f"夹具 B 期望 {exp_b},实际 {got_b}"
    pr = pair_scores(score_a_path=tmp_dir / "a" / "score.json",
                     score_b_path=tmp_dir / "b" / "score.json",
                     out_path=tmp_dir / "pair.json")
    assert pr["a_hit@1"] == 2 and pr["b_hit@1"] == 2
    assert pr["net_a_minus_b_hit@1"] == 0
    assert pr["four_cell"]["@1"] == {"both": 1, "a_only": 1,
                                     "b_only": 1, "neither": 3}
    assert pr["four_cell"]["@3"] == {"both": 4, "a_only": 0,
                                     "b_only": 0, "neither": 2}
    # S1 @1 翻转(a_hit→b_miss,顺序对调致 rank2);S2 @1 翻转
    # (a_miss rank2→b_hit rank1)→ 恰 2;S5 同为 @1(金标另一产物,不翻转)
    assert pr["n_flip_hit@1"] == 2, pr["n_flip_hit@1"]
    print(json.dumps({"ok": True, "self_test": "PASS",
                      "checked_a": got_a, "checked_b": got_b,
                      "pair": {k: v for k, v in pr.items()
                               if k != "per_question"}},
                     ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers")
    ap.add_argument("--gold")
    ap.add_argument("--out-dir")
    ap.add_argument("--label", default="")
    ap.add_argument("--pair", nargs=2, metavar=("SCORE_A", "SCORE_B"))
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test(Path("/tmp/s1_dev_score_selftest"))
        return 0
    if args.pair:
        assert args.out, "--pair 需要 --out"
        pair_scores(score_a_path=args.pair[0], score_b_path=args.pair[1],
                    out_path=args.out)
        return 0
    assert args.answers and args.gold and args.out_dir and args.label
    score_answers(answers_path=args.answers, gold_path=args.gold,
                  out_dir=args.out_dir, label=args.label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
