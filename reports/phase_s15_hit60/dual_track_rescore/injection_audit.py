#!/usr/bin/env python
"""口径 v3 错配注入审计(真实六批答卷;零 LLM;金标只在本离线进程使用)。

预注册 §2.2:对六批每题构造注入变体,证明口径 v3 不会把错答洗成对答。
四类:
1. 缺一组分:v3 命中题的触发候选删去一个金标组分 → 命中必须消失或降位;
2. 多一错误组分:v3 miss 题的首候选追加一个非金标错误组分 → 必须 still miss;
   (v3 命中题的触发候选追加错误组分 → 仍命中 = 已注册超集边界,断言
   hit_with_extra_components 旗标亮起,计 n_superset_registered;)
3. 部分命中对照组(|G|≥2):金标组分拆成单组分候选(scattered)→ 必须
   miss + partial + scattered_full;
4. 完全命中对照组:金标全部组分拼成一条候选 → 必须 v3 rank=1。

输出只有 qid/计数/旗标,无任何 SMILES。判据:violations == 0。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from pathway_v43.exam_v2 import (  # noqa: E402
    agent_candidates,
    candidate_component_ids,
    component_coverage_profile,
    first_full_coverage_rank,
    gold_main_component_ids,
)

REPO = Path(__file__).resolve().parents[3]
WORK = REPO / "reports/phase_s1_hit60/dev_gold/coverage_stat_work/m1_dump"
GOLD_PATH = REPO / "reports/phase_s1_hit60/dev_gold/dev_gold.jsonl"
TAGS = ["C0a", "C0b", "E1", "E2a", "E2b", "E3"]
OUT = (REPO / "reports/phase_s15_hit60/dual_track_rescore/sealed"
       / "injection_audit.json")

# 注入用"错误组分"候选池(确定性;运行时校验其身份不在该题金标内)
JUNK_POOL = ["CC(C)=O", "C1CCCCC1", "c1ccccc1", "CCN", "CC(=O)N", "CCCCO"]


def _pick_junk(gold: frozenset[str], extra: frozenset[str] = frozenset()) -> str:
    for j in JUNK_POOL:
        ident = candidate_component_ids(j)
        if ident and not (ident & set(gold)) and not (ident & set(extra)):
            return j
    raise SystemExit("junk 池耗尽(fail-closed)")


def audit() -> dict:
    gold_products: dict[str, list[str]] = {}
    gold: dict[str, frozenset[str]] = {}
    for line in GOLD_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            gold_products[rec["qid"]] = rec.get("products_smiles", [])
            gold[rec["qid"]] = gold_main_component_ids(rec["products_smiles"])

    per_batch = {}
    for tag in TAGS:
        answers = {}
        for line in (WORK / f"answers_{tag}.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                answers[rec["route_id"]] = rec
        counters = {
            "n_questions": len(gold),
            "miss_one_injected": 0, "miss_one_degraded_or_lost": 0,
            "miss_one_violation": 0, "miss_one_skipped_no_hit": 0,
            "extra_wrong_injected_miss": 0, "extra_wrong_still_miss": 0,
            "extra_wrong_violation": 0, "extra_wrong_skipped_hit_or_empty": 0,
            "extra_wrong_on_hit_registered": 0,
            "extra_wrong_on_hit_still_hit": 0,
            "extra_wrong_on_hit_flag_lit": 0,
            "scattered_built": 0, "scattered_miss_partial": 0,
            "scattered_violation": 0,
            "full_control_built": 0, "full_control_rank1": 0,
            "full_control_violation": 0,
        }
        violations = []
        for qid in sorted(gold):
            g = gold[qid]
            prods = agent_candidates(answers[qid])
            orig_rank = first_full_coverage_rank(prods, g)

            # ① 缺一组分:触发候选删去一个金标组分
            if orig_rank is None:
                counters["miss_one_skipped_no_hit"] += 1
            else:
                trigger = prods[orig_rank - 1]
                parts = trigger.split(".")
                drop = sorted(set(g))[0]  # 确定性:删去排序首个金标组分
                kept = [p for p in parts
                        if (candidate_component_ids(p) or {None}).isdisjoint({drop})
                        or not candidate_component_ids(p)]
                # 逐 part 删除:身份 == drop 的 part 全删
                kept = []
                for p in parts:
                    ident = candidate_component_ids(p)
                    if ident and drop in ident:
                        continue
                    kept.append(p)
                if kept:
                    new_trigger = ".".join(kept)
                else:
                    new_trigger = "this_is_NOT_smiles"  # 占名次不可命中
                sheet = list(prods)
                sheet[orig_rank - 1] = new_trigger
                new_rank = first_full_coverage_rank(sheet, g)
                counters["miss_one_injected"] += 1
                if new_rank is None or new_rank > orig_rank:
                    counters["miss_one_degraded_or_lost"] += 1
                else:
                    counters["miss_one_violation"] += 1
                    violations.append(
                        {"qid": qid, "kind": "miss_one", "orig": orig_rank,
                         "new": new_rank})

            # ② 多一错误组分
            if not prods:
                counters["extra_wrong_skipped_hit_or_empty"] += 1
            elif orig_rank is None:
                junk = _pick_junk(g)
                sheet = list(prods)
                first = sheet[0]
                sheet[0] = f"{first}.{junk}" if first else junk
                new_rank = first_full_coverage_rank(sheet, g)
                counters["extra_wrong_injected_miss"] += 1
                if new_rank is None:
                    counters["extra_wrong_still_miss"] += 1
                else:
                    counters["extra_wrong_violation"] += 1
                    violations.append(
                        {"qid": qid, "kind": "extra_wrong_on_miss",
                         "new": new_rank})
            else:
                # v3 命中题:错误组分追加到触发候选 → 超集语义仍命中(注册边界)
                junk = _pick_junk(g)
                sheet = list(prods)
                sheet[orig_rank - 1] = f"{sheet[orig_rank - 1]}.{junk}"
                new_rank = first_full_coverage_rank(sheet, g)
                profile = component_coverage_profile(sheet, g)
                counters["extra_wrong_on_hit_registered"] += 1
                if new_rank is not None:
                    counters["extra_wrong_on_hit_still_hit"] += 1
                if profile["hit_with_extra_components"]:
                    counters["extra_wrong_on_hit_flag_lit"] += 1
                if new_rank is None or not profile["hit_with_extra_components"]:
                    counters["extra_wrong_violation"] += 1
                    violations.append(
                        {"qid": qid, "kind": "extra_wrong_on_hit",
                         "new": new_rank})

            # ③ 部分命中对照组(scattered;|G|≥2)
            if len(g) >= 2:
                comp_sheet = sorted(set(g))  # 金标组分各自单候选
                prof = component_coverage_profile(comp_sheet, g)
                counters["scattered_built"] += 1
                if (prof["rank"] is None and prof["partial"]
                        and prof["scattered_full"]):
                    counters["scattered_miss_partial"] += 1
                else:
                    counters["scattered_violation"] += 1
                    violations.append({"qid": qid, "kind": "scattered",
                                       "profile": prof})
            # ④ 完全命中对照组(全部金标组分拼一条候选)
            entry_parts = []
            for entry in gold_products[qid]:
                entry_parts.extend([p for p in entry.split(".") if p])
            full_sheet = [".".join(entry_parts)]
            rank = first_full_coverage_rank(full_sheet, g)
            counters["full_control_built"] += 1
            if rank == 1:
                counters["full_control_rank1"] += 1
            else:
                counters["full_control_violation"] += 1
                violations.append({"qid": qid, "kind": "full_control",
                                   "rank": rank})
        per_batch[tag] = {"counters": counters, "violations": violations}

    total_violations = sum(
        len(b["violations"]) for b in per_batch.values())
    summary = {
        "preregistration": "PREREGISTRATION_V3 §2.2(条件②假阳性分析义务)",
        "caliber": "v43-exam-caliber-3",
        "n_batches": len(TAGS),
        "total_violations": total_violations,
        "verdict": "PASS" if total_violations == 0 else "FAIL",
        "per_batch": {
            tag: {**b["counters"], "n_violations": len(b["violations"])}
            for tag, b in per_batch.items()},
        "violations_detail": [v for b in per_batch.values()
                              for v in b["violations"]][:50],
    }
    return summary


def main() -> int:
    summary = audit()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2,
                              sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("violations_detail", "per_batch")},
                     ensure_ascii=False, sort_keys=True))
    for tag, b in summary["per_batch"].items():
        print(tag, json.dumps(b, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
