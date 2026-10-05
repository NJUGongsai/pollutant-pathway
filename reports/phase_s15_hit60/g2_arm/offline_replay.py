#!/usr/bin/env python
"""T8 G2 离线重放驱动(零 LLM;判据 v43-cons-2;金标只在本进程打开)。

定位(PREREGISTRATION_G2 v2 §5):**已见 dev 数据的工程设计验证**
(in-sample,非确证——E-3:dev 引导编目反哺后的读数不可作确证,确证
路径 = 冻结后付费跑双采样符号检验)。对封存六批(C0a/C0b/E1/E2a/
E2b/E3)答卷的 novel/analogy 路由题,离线应用守恒过滤 + 自排序(与
工作流挂接共用 `validation.conservation` 同一函数),重算口径 v3 读数
(分母 51,quarantine 后),输出:

- 逐题表(qid、原位次→新位次、降位/剔除/hold 标记、守恒判定明细;
  **零 SMILES**:qid + 旗标 + 计数,候选以 original_position 标识);
- 臂级预测:cn@1/@3/@5 净变化、spurious/空答变化、剔空 hold 触发数
  (hold_reason/reject_count 分账);
- 判据健全性预检:金标命中候选落剔除档计数(必须 = 0,否则判据回修
  走新冻结链);
- v1→v2 对照:若 `replay_summary_v1.json` 在场,自动生成
  `replay_v1_v2_comparison.json`(v1 判据读数 vs v2,重点:被 v1 降位
  的金标题是否被碎片重构判据救回、@3 反压是否缓解)。

锚点 fail-closed:重算的原始(未过滤)读数必须与封存
`quarantine_variant_dev.json` 的 per_batch component_v3 逐数相等,
不等即停(不静默继续)。金标 SHA256 与答卷 SHA256 同样锚定。

用法(本地 conda depending43,OMP_NUM_THREADS=1 PYTHONPATH=src):
  python reports/phase_s15_hit60/g2_arm/offline_replay.py            # 重放
  python reports/phase_s15_hit60/g2_arm/offline_replay.py --check    # 复算
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from pathway_v43.exam_v2 import (  # noqa: E402
    candidate_component_ids,
    first_full_coverage_rank,
    gold_main_component_ids,
)
from pathway_v43.validation.conservation import (  # noqa: E402
    TIER_DOWNGRADE,
    TIER_EXCLUDE,
    TIER_PASS,
    conservation_filter_and_rank,
)

HERE = Path(__file__).resolve().parent
ANSWERS_DIR = REPO / "reports/phase_s1_hit60/dev_gold/coverage_stat_work/m1_dump"
GOLD_PATH = REPO / "reports/phase_s1_hit60/dev_gold/dev_gold.jsonl"
SEALED_DIR = REPO / "reports/phase_s15_hit60/dual_track_rescore/sealed"
QUARANTINE_VARIANT = SEALED_DIR / "quarantine_variant_dev.json"

BATCHES = ("C0a", "C0b", "E1", "E2a", "E2b", "E3")
# 锚点:批名 → artifacts_remote 封存目录(answers_sha256 对账)
SEALED_SCORE = {
    "C0a": "s1_dev_C0_20260929T182619Z",
    "C0b": "s1_dev_C0_20260929T190054Z",
    "E1": "s1_dev_E1_20260930T023702Z",
    "E2a": "s1_dev_E2_20260929T192739Z",
    # E2b/E3 封存目录名在运行时按 answers_sha256 匹配解析
}

FILTERED_ROUTES = ("novel_proposal", "analogy_edit")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_jsonl(path: str | Path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _resolve_sealed_score(batch: str) -> dict:
    """批 → 封存 score.json(answers_sha256 锚);E2b/E3 按哈希匹配。"""
    if batch in SEALED_SCORE:
        d = REPO / "reports/phase_s1_hit60/artifacts_remote" / SEALED_SCORE[batch]
        return json.loads((d / "scoring" / "score.json").read_text())
    want = _sha256_file(ANSWERS_DIR / f"answers_{batch}.jsonl")
    for d in sorted((REPO / "reports/phase_s1_hit60/artifacts_remote").iterdir()):
        score = d / "scoring" / "score.json"
        if not score.is_file():
            continue
        try:
            payload = json.loads(score.read_text())
        except Exception:
            continue
        if payload.get("summary", {}).get("answers_sha256") == want:
            return payload
    raise SystemExit(f"封存 score.json 未找到(answers 哈希匹配失败):{batch}")


def _load_gold() -> dict[str, frozenset[str]]:
    gold: dict[str, frozenset[str]] = {}
    for rec in _iter_jsonl(GOLD_PATH):
        qid = rec.get("qid")
        if not qid or qid in gold:
            raise SystemExit("金标 qid 缺失或重复(fail-closed)")
        gold[qid] = gold_main_component_ids(rec.get("products_smiles", []))
    if not gold:
        raise SystemExit("金标为空(fail-closed)")
    return gold


def _score_products(products: list[str], g: frozenset[str]) -> dict:
    """口径 v3 单题读数(与 rescore_v3 同判据;零金标外泄)。"""
    rank_v3 = first_full_coverage_rank(products, g)
    covered: set[str] = set()
    for p in products:
        covered |= candidate_component_ids(p) & set(g)
    return {
        "n_pred": len(products),
        "rank_v3": rank_v3,
        "hit_v3@1": rank_v3 is not None and rank_v3 <= 1,
        "hit_v3@3": rank_v3 is not None and rank_v3 <= 3,
        "hit_v3@5": rank_v3 is not None and rank_v3 <= 5,
        "empty_answer": len(products) == 0,
        "spurious": len(products) > 0 and not covered,
        "n_covered": len(covered),
    }


def replay_batch(batch: str, gold: dict[str, frozenset[str]],
                 routes: dict[str, str], quarantine: set[str]) -> dict:
    """一批答卷的重放:novel/analogy 路由题过滤+自排序,其余不动。"""
    answers_path = ANSWERS_DIR / f"answers_{batch}.jsonl"
    sealed = _resolve_sealed_score(batch)
    want_sha = sealed.get("summary", {}).get("answers_sha256")
    got_sha = _sha256_file(answers_path)
    if want_sha and want_sha != got_sha:
        raise SystemExit(
            f"答卷哈希与封存不符(fail-closed):{batch} "
            f"want={want_sha[:12]} got={got_sha[:12]}")

    per_question: list[dict] = []
    n_hold = n_excluded_total = n_downgraded_total = 0
    gold_in_exclusion = 0   # 健全性预检:金标命中候选落剔除档(必须 0)
    rerouted = 0
    for row in _iter_jsonl(answers_path):
        qid = row.get("route_id")
        if qid not in gold:
            raise SystemExit(f"答卷 qid 不在金标(fail-closed):{qid}")
        if qid in quarantine:
            continue  # 分母 51:quarantine 题剔出
        g = gold[qid]
        route = routes.get(qid, "")
        steps = row.get("steps", [])
        products = [p for s in steps for p in s.get("predicted_products", [])]
        orig = _score_products(products, g)

        new_products = list(products)
        cons_meta: dict = {}
        if route in FILTERED_ROUTES and products:
            sub_smiles = steps[0].get("parent_smiles", "") \
                if steps else row.get("root_smiles", "")
            result = conservation_filter_and_rank(
                substrate_smiles=sub_smiles,
                candidates=[{"smiles": p, "note": ""}
                            for p in products],
                surface_text="")
            if result.status == "hold":
                new_products = []
                cons_meta = {
                    "hold": True,
                    "hold_reason": result.hold_reason,
                    "hold_detail": result.hold_detail,
                    "reject_count": result.reject_count,
                    "n_excluded": result.n_excluded,
                    "n_downgraded": 0,
                    "versions": result.versions,
                }
                n_hold += 1
                n_excluded_total += result.n_excluded
            else:
                new_products = [products[j.index] for j in result.ranked]
                cons_meta = {
                    "hold": False,
                    "n_excluded": result.n_excluded,
                    "n_downgraded": result.n_downgraded,
                    "versions": result.versions,
                    "ranked_original_positions": [j.index for j in result.ranked],
                    "excluded_original_positions": [
                        j.index for j in result.excluded],
                    "tiers": {str(j.index): j.tier for j in result.ranked},
                    "transform_classes": {
                        str(j.index): j.g3b.get("transform_class", "")
                        for j in result.ranked},
                    "g3b_matched": {
                        str(j.index): bool(j.g3b.get("matched"))
                        for j in result.ranked},
                    "dC_main": {str(j.index): j.dC_main
                                for j in result.ranked},
                    "rules": {str(j.index): j.rules for j in result.ranked},
                }
                n_excluded_total += result.n_excluded
                n_downgraded_total += result.n_downgraded
                if [j.index for j in result.ranked] != list(range(len(products))) \
                        or result.n_excluded:
                    rerouted += 1
            # 健全性预检(金标仅本进程):命中金标组分的候选若落剔除档
            gold_ids = set(g)
            for j in result.excluded:
                if candidate_component_ids(products[j.index]) & gold_ids:
                    gold_in_exclusion += 1
        new = _score_products(new_products, g)
        per_question.append({
            "qid": qid,
            "route": route,
            "orig": {k: orig[k] for k in (
                "n_pred", "rank_v3", "hit_v3@1", "hit_v3@3", "hit_v3@5",
                "empty_answer", "spurious")},
            "new": {k: new[k] for k in (
                "n_pred", "rank_v3", "hit_v3@1", "hit_v3@3", "hit_v3@5",
                "empty_answer", "spurious")},
            "conservation": cons_meta,
        })

    def hits(key: str, k: int) -> int:
        return sum(1 for q in per_question if q["new"][f"hit_v3@{k}"])

    summary = {
        "batch": batch,
        "denominator": len(per_question),
        "orig": {
            "hit@1": sum(1 for q in per_question if q["orig"]["hit_v3@1"]),
            "hit@3": sum(1 for q in per_question if q["orig"]["hit_v3@3"]),
            "hit@5": sum(1 for q in per_question if q["orig"]["hit_v3@5"]),
            "spurious": sum(1 for q in per_question if q["orig"]["spurious"]),
            "empty": sum(1 for q in per_question if q["orig"]["empty_answer"]),
        },
        "new": {
            "hit@1": hits("", 1),
            "hit@3": hits("", 3),
            "hit@5": hits("", 5),
            "spurious": sum(1 for q in per_question if q["new"]["spurious"]),
            "empty": sum(1 for q in per_question if q["new"]["empty_answer"]),
        },
        "n_hold": n_hold,
        "n_excluded_total": n_excluded_total,
        "n_downgraded_total": n_downgraded_total,
        "n_questions_rerouted": rerouted,
        "gold_in_exclusion_tier": gold_in_exclusion,
        "per_question": per_question,
    }
    return summary


def _v1_rank(v1: dict, batch: str, qid: str):
    """v1 逐题 TSV 副本里取该题的 v1 新位次(无则 None)。

    v1 summary 副本只存臂级聚合;逐题 v1 rank 从 replay_per_question_
    v1.tsv 的 new_rank_v3 列恢复。
    """
    tsv = HERE / "replay_per_question_v1.tsv"
    if not tsv.is_file():
        return None
    for line in tsv.read_text(encoding="utf-8").splitlines()[1:]:
        cols = line.split("\t")
        # 列序:new_rank_v3 为第 7 列(索引 6,见 TSV 表头)
        if len(cols) > 6 and cols[0] == batch and cols[1] == qid:
            return int(cols[6]) if cols[6].isdigit() else None
    return None


def _anchor_check(summary: dict, sealed_variant: dict) -> None:
    """原始(未过滤)读数与封存 quarantine variant 逐数相等,不等即停。"""
    batch = summary["batch"]
    sealed = sealed_variant.get("per_batch", {}).get(batch, {}).get(
        "component_v3")
    if not sealed:
        raise SystemExit(f"封存 51 分母读数缺失:{batch}")
    for key in ("hit@1", "hit@3", "hit@5"):
        if summary["orig"][key] != sealed[key]:
            raise SystemExit(
                f"锚点不符(fail-closed):{batch} {key} "
                f"orig={summary['orig'][key]} sealed={sealed[key]}")
    if summary["denominator"] != sealed_variant["per_batch"][batch][
            "denominator"]:
        raise SystemExit(f"分母不符:{batch}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="复算模式:与已落盘 replay_summary.json 逐字节核对")
    args = ap.parse_args()

    sealed_variant = json.loads(QUARANTINE_VARIANT.read_text(encoding="utf-8"))
    routes: dict[str, str] = {}
    for label in BATCHES:
        readings = json.loads(
            (SEALED_DIR / f"readings_s15_dev_{label}.json").read_text())
        for q in readings.get("per_question", []):
            routes.setdefault(q.get("qid", ""), q.get("route", ""))
    quarantine = {
        "b1_BIOPATH150_028__S04__BSY-r03812",
        "b1_BIOPATH150_067__S03__BSY-r02126",
        "b1_BIOPATH150_114__S01__BSY-r01911",
        "b1_BIOPATH150_149__S01__BSY-r01831",
        "b1_BIOPATH150_149__S06__BSY-r03410",
    }

    gold = _load_gold()
    summaries = []
    for batch in BATCHES:
        s = replay_batch(batch, gold, routes, quarantine)
        _anchor_check(s, sealed_variant)
        summaries.append(s)

    # ---- 判定对(C0a/C0b)合并读数 + 净赢/净输逐题
    pair = [s for s in summaries if s["batch"] in ("C0a", "C0b")]
    aggregate = {
        "batches": BATCHES,
        "denominator": 51,
        "per_batch": [
            {k: v for k, v in s.items() if k != "per_question"}
            for s in summaries],
        "pair_C0a_C0b": {
            b: {**{k: s["new"][k] for k in
                   ("hit@1", "hit@3", "hit@5", "spurious", "empty")},
                "n_hold": s["n_hold"],
                "gold_in_exclusion_tier": s["gold_in_exclusion_tier"]}
            for b, s in (("C0a", pair[0]), ("C0b", pair[1]))},
        "net_win_questions": {
            b: [
                {"qid": q["qid"], "route": q["route"],
                 "orig_rank": q["orig"]["rank_v3"],
                 "new_rank": q["new"]["rank_v3"]}
                for q in s["per_question"]
                if q["orig"]["hit_v3@1"] != q["new"]["hit_v3@1"]]
            for b, s in (("C0a", pair[0]), ("C0b", pair[1]))},
        "spurious_delta": {
            b: pair[i]["new"]["spurious"] - pair[i]["orig"]["spurious"]
            for i, b in enumerate(("C0a", "C0b"))},
        "empty_delta": {
            b: pair[i]["new"]["empty"] - pair[i]["orig"]["empty"]
            for i, b in enumerate(("C0a", "C0b"))},
    }

    # ---- 逐题 TSV(零 SMILES:qid + 旗标 + 计数)
    tsv_path = HERE / "replay_per_question.tsv"
    with tsv_path.open("w", encoding="utf-8") as fh:
        fh.write("\t".join([
            "batch", "qid", "route", "orig_n_pred", "new_n_pred",
            "orig_rank_v3", "new_rank_v3",
            "orig_hit1", "new_hit1", "orig_hit3", "new_hit3",
            "orig_hit5", "new_hit5",
            "orig_spurious", "new_spurious",
            "orig_empty", "new_empty",
            "hold", "n_excluded", "n_downgraded",
            "ranked_positions", "excluded_positions",
        ]) + "\n")
        for s in summaries:
            for q in s["per_question"]:
                c = q.get("conservation", {})
                fh.write("\t".join(str(x) for x in [
                    s["batch"], q["qid"], q["route"],
                    q["orig"]["n_pred"], q["new"]["n_pred"],
                    q["orig"]["rank_v3"], q["new"]["rank_v3"],
                    int(q["orig"]["hit_v3@1"]), int(q["new"]["hit_v3@1"]),
                    int(q["orig"]["hit_v3@3"]), int(q["new"]["hit_v3@3"]),
                    int(q["orig"]["hit_v3@5"]), int(q["new"]["hit_v3@5"]),
                    int(q["orig"]["spurious"]), int(q["new"]["spurious"]),
                    int(q["orig"]["empty_answer"]),
                    int(q["new"]["empty_answer"]),
                    int(bool(c.get("hold", False))),
                    c.get("n_excluded", 0), c.get("n_downgraded", 0),
                    ",".join(str(p) for p in c.get(
                        "ranked_original_positions", [])),
                    ",".join(str(p) for p in c.get(
                        "excluded_original_positions", [])),
                ]) + "\n")

    # ---- 逐候选守恒判定明细(零 SMILES:qid + 位次标识 + 档位/规则/变换类)
    details_path = HERE / "replay_candidate_details.json"
    details = {
        "note": "单次采样离线预测,付费跑换新采样需复验;零 SMILES"
                "(候选以 original_position 标识);金标仅本进程比对",
        "versions": next(
            (q["conservation"]["versions"]
             for s in summaries for q in s["per_question"]
             if q.get("conservation", {}).get("versions")), {}),
        "batches": {
            s["batch"]: [
                {"qid": q["qid"], "route": q["route"],
                 **q.get("conservation", {})}
                for q in s["per_question"]
                if q.get("conservation")]
            for s in summaries},
    }
    details_path.write_text(
        json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")

    out_path = HERE / "replay_summary.json"

    # ---- v1→v2 对照(v1 副本在场时;零 LLM 确定性 diff)
    v1_path = HERE / "replay_summary_v1.json"
    if v1_path.is_file():
        v1 = json.loads(v1_path.read_text(encoding="utf-8"))
        v1_by_batch = {b["batch"]: b for b in v1.get("per_batch", [])}
        comparison = {
            "note": "v1(v43-cons-1)→v2(v43-cons-2) 判据修订对照;"
                    "两侧均为同批复封答卷的离线重放(in-sample 工程验证,"
                    "非确证);零 SMILES",
            "per_batch": [
                {
                    "batch": s["batch"],
                    "orig": s["orig"],
                    "v1_new": v1_by_batch[s["batch"]]["new"],
                    "v2_new": s["new"],
                    "v1_downgraded": v1_by_batch[s["batch"]][
                        "n_downgraded_total"],
                    "v2_downgraded": s["n_downgraded_total"],
                    "v1_rerouted": v1_by_batch[s["batch"]][
                        "n_questions_rerouted"],
                    "v2_rerouted": s["n_questions_rerouted"],
                }
                for s in summaries],
            "rescue_check": {
                # v1 被降位压后(orig rank1 → v1 rank>1)而 v2 救回
                # (v2 rank==orig rank)的金标题
                q["qid"]: {
                    "batch": b, "route": q["route"],
                    "orig_rank": q["orig"]["rank_v3"],
                    "v1_rank": _v1_rank(v1, b, q["qid"]),
                    "v2_rank": q["new"]["rank_v3"],
                }
                for b, s in (("C0a", pair[0]), ("C0b", pair[1]))
                for q in s["per_question"]
                if q["orig"]["hit_v3@1"] and not q["orig"].get("empty_answer")
                and _v1_rank(v1, b, q["qid"]) not in (None, 1)
                and q["new"]["hit_v3@1"]
            },
        }
        (HERE / "replay_v1_v2_comparison.json").write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2,
                       sort_keys=True) + "\n", encoding="utf-8")

    if args.check:
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        if json.dumps(saved, sort_keys=True, ensure_ascii=False) != \
                json.dumps(aggregate, sort_keys=True, ensure_ascii=False):
            raise SystemExit("--check 失败:重算与已落盘 summary 不一致")
        saved_details = json.loads(details_path.read_text(encoding="utf-8"))
        if json.dumps(saved_details, sort_keys=True,
                      ensure_ascii=False) != json.dumps(
                          details, sort_keys=True, ensure_ascii=False):
            raise SystemExit("--check 失败:重算与已落盘 details 不一致")
        print("--check PASS: replay_summary.json + replay_candidate_details"
              ".json 复算一致")
        return 0
    out_path.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    for s in summaries:
        o, n = s["orig"], s["new"]
        print(f"{s['batch']}: @1 {o['hit@1']}→{n['hit@1']} "
              f"@3 {o['hit@3']}→{n['hit@3']} "
              f"@5 {o['hit@5']}→{n['hit@5']} "
              f"spurious {o['spurious']}→{n['spurious']} "
              f"empty {o['empty']}→{n['empty']} "
              f"hold={s['n_hold']} excl={s['n_excluded_total']} "
              f"downg={s['n_downgraded_total']} "
              f"gold_in_excl={s['gold_in_exclusion_tier']}")
    print("done:", out_path.name, tsv_path.name, details_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
