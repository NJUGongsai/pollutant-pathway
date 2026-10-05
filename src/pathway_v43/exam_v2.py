"""EC298 Phase A — 同口径重评分器 v2(``v43-ec298-scorer-2``)。

阶段任务书:docs/TASK_V43_EC298_PHASE_A.md。v1(``exam.score_exam``,
scorer-1)对 agent 臂从原始 SMILES 求 ``cn_identity``,对引擎臂却直接使用
封存 ``engine_results.jsonl`` 里的缓存 ``product_identity``(可能保留电荷),
两臂与金标并非同一身份口径;且 ``pool_identities`` 只由 ``top_k=10`` 的
返回值填充,不能代表完整候选池。v2 的唯一主修正:

- **两臂统一从原始候选 SMILES 计算** ``cn_identity``(charge-normalized
  stereo-blind,v3 ``eawag_lookup._cn_identity`` 同口径);引擎评分显式
  忽略缓存 ``product_identity``。
- 计分单位仍为 v1 的**整条候选字符串**;排名/空答/去重/金标提取/298
  分母规则与 v1 完全一致。含 ``.`` 的多组分候选不混入主分数,只进
  ``multicomponent_sensitivity`` 的"任一组分命中"探索性表。

**口径 v3(component-aware,HIT60 S1.5 判分勘误)**:主分判定改为
"候选组分集合包含全部金标主产物组分"(``gold_main_component_ids`` +
``first_full_coverage_rank``;细则见
``reports/phase_s15_hit60/PREREGISTRATION_V3.md``)。既有
``component_mode``(any-of)与整串 any-of 语义均被 v3 明令禁止进主分,
仅保留用于历史敏感性读数的复现。

判分零 LLM、零网络;金标仅在判分进程读取;不写回任何封存输入。
v1 实现与结果原样保留供审计(exam.py / scoring/per_question_scoring.json)。

零网络复算命令(路径显式传入)::

    python -m pathway_v43.exam_v2 \
        --agent-predictions <sealed>/agent_batch/merged/predictions.jsonl \
        --engine-results <sealed>/engine_arm/engine_results.jsonl \
        --gold <gold>/questions.jsonl \
        --out-dir <out> [--v1-scoring <sealed>/scoring/per_question_scoring.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SCORER_V2_VERSION = "v43-ec298-scorer-2"
SCORER_V1_VERSION = "v43-ec298-scorer-1"
CALIBER_V3_VERSION = "v43-exam-caliber-3"
CALIBER_V3_DEF = (
    "component-aware,全主产物命中:候选按 '.' 拆分的 cn 身份集合 ⊇ 金标"
    "主产物组分身份集合(部分命中=partial 单列不进主分;any-of 禁止;"
    "超集不破命中——见 reports/phase_s15_hit60/PREREGISTRATION_V3.md)"
)
IDENTITY_CALIBER = (
    "cn (v3 eawag_lookup._cn_identity 同口径:charge-normalized stereo-blind;"
    "两臂均从原始候选 SMILES 现算,引擎缓存 product_identity 一律忽略)"
)

TIER_TOP10_HIT = "engine_top10_hit"
TIER_NOT_IN_TOP10 = "not_in_exported_top10"


class ScorerV2Error(RuntimeError):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _iter_jsonl(path: str | Path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _write_json(out_path: Path, payload: dict) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    os.replace(tmp, out_path)


# ---------------------------------------------------------------- 金标与候选


def load_gold(gold_questions_path: str | Path) -> dict[str, dict]:
    """金标集合(qid → cn 身份集合);任一含碳产物命中即算,提取规则与 v1 一致。"""
    from .domain.identity import cn_identity

    gold: dict[str, dict] = {}
    for rec in _iter_jsonl(gold_questions_path):
        qid = rec.get("qid")
        if not qid:
            raise ScorerV2Error("金标行缺 qid", {"path": str(gold_questions_path)})
        if qid in gold:
            raise ScorerV2Error("金标 qid 重复(fail-closed)", {"qid": qid})
        products = rec.get("products_smiles", [])
        gold_ids = {i for i in (cn_identity(p) for p in products) if i}
        gold[qid] = {
            "category": rec.get("category"),
            "products_smiles": products,
            "n_gold_products": len(products),
            "gold_ids": gold_ids,
        }
    if not gold:
        raise ScorerV2Error("金标为空", {"path": str(gold_questions_path)})
    return gold


def agent_candidates(row: dict) -> list[str]:
    """答卷有序候选(跨 step 顺次拼接;排名按原候选位置计数,与 v1 一致)。"""
    products: list[str] = []
    for step in row.get("steps", []):
        products.extend(step.get("predicted_products", []))
    return products


def first_hit_rank(candidates: list[str], gold_ids: set[str],
                   component_mode: bool = False) -> int | None:
    """首个命中 rank:逐候选 cn 身份,命中任一金标即取该名次。

    - 不可解析候选(身份 None)跳过,但**占名次**;
    - 重复身份跳过(首-hit 语义下与 v1 等价,保留以防口径漂移);
    - ``component_mode`` 仅用于多组分敏感性表:含 ``.`` 的候选任一组分
      命中即算;主分数一律整条候选。

    .. deprecated-v3::
        ``component_mode=True`` 是 **any-of 语义,口径 v3 明令禁止进主分**
        (见 PREREGISTRATION_V3 §1.1)。保留仅为复现历史探索性读数
        (multicomponent_sensitivity / COVERAGE_STAT M3);v3 主分路径
        一律使用 :func:`first_full_coverage_rank`。
    """
    from .domain.identity import cn_identity

    rank = None
    seen: set[str] = set()
    r = 0
    for p in candidates:
        r += 1
        if component_mode and "." in p:
            idents = [cn_identity(part) for part in p.split(".")]
        else:
            idents = [cn_identity(p)]
        hit = False
        for ident in idents:
            if ident is None or ident in seen:
                continue
            seen.add(ident)
            if ident in gold_ids:
                hit = True
        if hit and rank is None:
            rank = r
    return rank


# ---------------------------------------------------------------- 口径 v3


def candidate_component_ids(candidate: str) -> frozenset[str]:
    """候选(或金标产物条目)按 ``.`` 拆分后的非 None cn 身份集合。

    与 cn-v1 同口径(电荷归一 + 立体盲);条目无 ``.`` 时退化为单身份。
    不可解析片段贡献空;全部不可解析 → 空集合(候选占名次但不可能命中)。
    """
    from .domain.identity import cn_identity

    return frozenset(
        i for i in (cn_identity(part) for part in candidate.split("."))
        if i)


def gold_main_component_ids(products_smiles: list[str]) -> frozenset[str]:
    """v3 金标主产物组分身份集合 G(qid)。

    每条 ``products_smiles`` 条目按 ``.`` 拆分(点串条目为前瞻泛化,现有
    dev/298 题卷条目内均无点串,与 v2 ``gold_ids`` 同集),逐组分取
    ``cn_identity``,收集全部非 None 身份。

    fail-closed:集合为空(全部产物不可解析)时抛错——空 G 会令任何候选
    平凡"全覆盖",必须拦截。
    """
    ids: set[str] = set()
    for product in products_smiles:
        ids |= candidate_component_ids(product)
    if not ids:
        raise ScorerV2Error(
            "金标主产物组分集合为空(全部不可解析;fail-closed)",
            {"n_products": len(products_smiles)})
    return frozenset(ids)


def first_full_coverage_rank(candidates: list[str],
                             gold_component_ids: frozenset[str] | set[str],
                             ) -> int | None:
    """口径 v3 主分 rank:最早满足 ``G ⊆ S(c_r)`` 的 1-based 位次。

    - "全部主产物组分命中 = 对"(teacher §五.4.1);部分命中不取名次;
    - **any-of 禁止**:单组分候选只命中多产物金标之一 → 不命中;
    - 不可解析候选**占名次但不命中**(与 v2 整串口径一致);
    - 超集不破命中:触发候选含 G 之外组分仍算命中(已注册边界,
      PREREGISTRATION_V3 §1.2,配套 hit_with_extra_components 披露列)。
    """
    for r, candidate in enumerate(candidates, 1):
        if gold_component_ids <= candidate_component_ids(candidate):
            return r
    return None


def component_coverage_profile(candidates: list[str],
                               gold_component_ids: frozenset[str] | set[str],
                               ) -> dict:
    """v3 partial 指标(单列,不进主分)。

    - ``covered``:答卷(全部候选并集)覆盖的金标组分身份集合;
    - ``partial``:主分未命中且 covered 非空(部分命中,单列指标);
    - ``scattered_full``:主分未命中但 covered = G——金标组分全被覆盖、
      却分散在不同候选、无任何单候选全覆盖(any-of 假阳性的残影,
      归 partial 不归主分);
    - ``hit_with_extra_components``:触发候选组分严格多于 G(注册边界
      披露列)。
    """
    gold = set(gold_component_ids)
    rank = first_full_coverage_rank(candidates, gold)
    covered: set[str] = set()
    for c in candidates:
        covered |= candidate_component_ids(c) & gold
    hit_extra = False
    if rank is not None:
        hit_extra = candidate_component_ids(candidates[rank - 1]) - gold != set()
    return {
        "rank": rank,
        "n_gold_components": len(gold),
        "n_covered": len(covered),
        "partial": rank is None and bool(covered),
        "scattered_full": rank is None and covered == gold,
        "hit_with_extra_components": hit_extra,
    }


def _engine_rows(engine_results_path: str | Path | None) -> dict[str, dict]:
    """显式传入引擎文件即严格要求:存在、非空、qid 唯一;None 才是无引擎臂。"""
    if not engine_results_path:
        return {}
    p = Path(engine_results_path)
    if not p.is_file():
        raise ScorerV2Error("显式传入的引擎结果文件不存在(fail-closed)",
                            {"path": str(p)})
    rows: dict[str, dict] = {}
    for r in _iter_jsonl(p):
        qid = r.get("qid")
        if not qid:
            raise ScorerV2Error("引擎结果行缺 qid", {"path": str(p)})
        if qid in rows:
            raise ScorerV2Error("引擎结果 qid 重复(fail-closed)", {"qid": qid})
        rows[qid] = r
    if not rows:
        raise ScorerV2Error("引擎结果文件为空(fail-closed)", {"path": str(p)})
    return rows


def engine_first_hit(eng: dict | None, gold_ids: set[str]) -> dict:
    """引擎臂 v2 首命中:**忽略缓存 product_identity**,从原始 SMILES 现算。"""
    from .domain.identity import cn_identity

    if not eng or eng.get("status") != "ok":
        return {"rank": None, "trigger_smiles": None,
                "trigger_cached_identity": None, "trigger_position": None}
    seen: set[str] = set()
    er = 0
    for entry in eng.get("top10", []):
        er += 1
        raw = entry.get("product_smiles", "")
        ident = cn_identity(raw)
        if not ident or ident in seen:
            continue
        seen.add(ident)
        if ident in gold_ids:
            return {"rank": er, "trigger_smiles": raw,
                    "trigger_cached_identity": entry.get("product_identity"),
                    "trigger_position": er}
    return {"rank": None, "trigger_smiles": None,
            "trigger_cached_identity": None, "trigger_position": None}


# ---------------------------------------------------------------- 主评分


def score_exam_v2(*, agent_predictions_path: str | Path,
                  engine_results_path: str | Path | None,
                  gold_questions_path: str | Path,
                  out_path: str | Path | None = None,
                  inputs_sha: dict[str, str] | None = None) -> dict:
    """v2 冻结判分(零 LLM;分母恒为全部题目,空/部分/失败行计入)。

    fail-closed:答卷/金标/引擎臂 qid 必须一一对应且无重复;``inputs_sha``
    (角色 → SHA256)非空时随结果封存,供正式 ``score_v2.json`` 审计。
    """
    gold = load_gold(gold_questions_path)
    engine: dict[str, dict] = {}
    if engine_results_path is not None:
        # 显式传入引擎文件即要求引擎臂参与判分:文件必须存在、非空,
        # qid 集合(含空文件情形)必须与金标完全一致;传 None 才是无引擎臂。
        eng_path = Path(engine_results_path)
        if not eng_path.is_file():
            raise ScorerV2Error("显式传入的引擎结果文件不存在(fail-closed)",
                                {"path": str(eng_path)})
        for r in _iter_jsonl(eng_path):
            qid = r.get("qid")
            if not qid:
                raise ScorerV2Error("引擎结果行缺 qid",
                                    {"path": str(eng_path)})
            if qid in engine:
                raise ScorerV2Error("引擎结果 qid 重复(fail-closed)",
                                    {"qid": qid})
            engine[qid] = r
        if set(engine) != set(gold):
            raise ScorerV2Error(
                "引擎结果 qid 集合与金标不一致(空文件亦不例外;fail-closed)",
                {"path": str(eng_path),
                 "missing": sorted(set(gold) - set(engine))[:5],
                 "extra": sorted(set(engine) - set(gold))[:5]})
    seen_agent: set[str] = set()
    per_question = []
    for row in _iter_jsonl(agent_predictions_path):
        qid = row.get("route_id")
        if qid not in gold:
            raise ScorerV2Error("答卷 qid 不在金标(判分失败)", {"qid": qid})
        if qid in seen_agent:
            raise ScorerV2Error("答卷 qid 重复(fail-closed)", {"qid": qid})
        seen_agent.add(qid)
        g = gold[qid]
        products = agent_candidates(row)
        agent_rank = first_hit_rank(products, g["gold_ids"])
        efh = engine_first_hit(engine.get(qid), g["gold_ids"])
        per_question.append({
            "qid": qid,
            "category": g["category"],
            "n_gold_products": g["n_gold_products"],
            "agent_rank": agent_rank,
            "engine_rank": efh["rank"],
            "n_predicted": len(products),
            "tier_v2": TIER_TOP10_HIT if efh["rank"] is not None
                       else TIER_NOT_IN_TOP10,
        })
    total = len(per_question)
    if total != len(gold):
        raise ScorerV2Error(
            "答卷题数与金标不一致(fail-closed)",
            {"n_predictions": total, "n_gold": len(gold)})

    def hits(k: int, key: str) -> int:
        return sum(1 for q in per_question
                   if q[key] is not None and q[key] <= k)

    paired = {"both": 0, "agent_only": 0, "engine_only": 0, "neither": 0}
    for q in per_question:
        a, e = q["agent_rank"] is not None and q["agent_rank"] <= 5, \
               q["engine_rank"] is not None and q["engine_rank"] <= 5
        paired["both" if a and e else "agent_only" if a else
               "engine_only" if e else "neither"] += 1
    summary = {
        "schema_version": "v43-exam-1",
        "scorer_version": SCORER_V2_VERSION,
        "identity": IDENTITY_CALIBER,
        "scoring_unit": "整条候选字符串(与 v1 相同;多组分敏感性另表)",
        "n_questions": total,
        "agent": {
            "hit@1": hits(1, "agent_rank"),
            "hit@3": hits(3, "agent_rank"),
            "hit@5": hits(5, "agent_rank"),
            "hit@10": hits(5, "agent_rank"),
            "hit@10_note": "agent 每步最多报告五个候选,hit@10 恒等于 "
                           "hit@5(输出宽度上限,不代表第 6-10 位性能)",
            "n_miss": sum(1 for q in per_question if q["agent_rank"] is None),
        },
        "engine_top10": {
            "hit@1": hits(1, "engine_rank"),
            "hit@3": hits(3, "engine_rank"),
            "hit@5": hits(5, "engine_rank"),
            "hit@10": hits(10, "engine_rank"),
            "n_miss": sum(1 for q in per_question
                          if q["engine_rank"] is None),
        },
        "tiers_v2": {
            TIER_TOP10_HIT: sum(1 for q in per_question
                                if q["tier_v2"] == TIER_TOP10_HIT),
            TIER_NOT_IN_TOP10: sum(1 for q in per_question
                                   if q["tier_v2"] == TIER_NOT_IN_TOP10),
            "note": "仅描述已导出 Top-10 内外;不能称为完整候选池分档"
                    "(封存件无真实全池)",
        },
        "paired_hit5": paired,
        "paired_delta_note": "逐题配对净差见 per_question(agent_rank/"
                             "engine_rank 比较)与 paired_hit5",
    }
    result = {"summary": summary, "per_question": per_question}
    if inputs_sha:
        result["inputs_sha256"] = dict(inputs_sha)
    if out_path is not None:
        _write_json(Path(out_path), result)
    return result


# ------------------------------------------------------- 多组分敏感性(探索性)


def multicomponent_sensitivity(*, agent_predictions_path: str | Path,
                               engine_results_path: str | Path | None,
                               gold_questions_path: str | Path,
                               out_path: str | Path | None = None) -> dict:
    """含 ``.`` 候选的"任一组分命中"敏感性表;探索性,不是主结果。"""
    gold = load_gold(gold_questions_path)
    engine = _engine_rows(engine_results_path)
    rows = []
    affected_qids: set[str] = set()
    n_multi_agent = n_multi_engine = 0
    for row in _iter_jsonl(agent_predictions_path):
        qid = row.get("route_id")
        g = gold[qid]
        products = agent_candidates(row)
        agent_main = first_hit_rank(products, g["gold_ids"])
        agent_sens = first_hit_rank(products, g["gold_ids"],
                                    component_mode=True)
        eng = engine.get(qid)
        eng_products = [e.get("product_smiles", "")
                        for e in (eng.get("top10", []) if eng else [])]
        engine_main = engine_first_hit(eng, g["gold_ids"])["rank"]
        engine_sens = first_hit_rank(eng_products, g["gold_ids"],
                                     component_mode=True)
        if any("." in p for p in products):
            n_multi_agent += sum(1 for p in products if "." in p)
            affected_qids.add(qid)
        if any("." in p for p in eng_products):
            n_multi_engine += sum(1 for p in eng_products if "." in p)
            affected_qids.add(qid)
        rows.append({
            "qid": qid, "category": g["category"],
            "agent_rank_main": agent_main, "agent_rank_sensitivity": agent_sens,
            "engine_rank_main": engine_main,
            "engine_rank_sensitivity": engine_sens,
            "changed": (agent_main != agent_sens)
                       or (engine_main != engine_sens),
        })

    def hits(rows_, k, key):
        return sum(1 for q in rows_
                   if q[key] is not None and q[key] <= k)

    summary = {
        "exploratory": True,
        "note": "敏感性口径:含 . 候选取任一组分命中;两臂同法;探索性诊断,"
                "不是正式成绩,不得与主分数混算",
        "n_questions": len(rows),
        "n_multi_component_agent_candidates": n_multi_agent,
        "n_multi_component_engine_candidates": n_multi_engine,
        "n_affected_qids": len(affected_qids),
        "agent": {"hit@1": hits(rows, 1, "agent_rank_sensitivity"),
                  "hit@3": hits(rows, 3, "agent_rank_sensitivity"),
                  "hit@5": hits(rows, 5, "agent_rank_sensitivity")},
        "engine_top10": {"hit@1": hits(rows, 1, "engine_rank_sensitivity"),
                         "hit@3": hits(rows, 3, "engine_rank_sensitivity"),
                         "hit@5": hits(rows, 5, "engine_rank_sensitivity"),
                         "hit@10": hits(rows, 10, "engine_rank_sensitivity")},
        "n_changed_rows": sum(1 for r in rows if r["changed"]),
    }
    result = {"summary": summary, "per_question": rows}
    if out_path is not None:
        _write_json(Path(out_path), result)
    return result


def cn_from(smiles: str) -> str | None:
    from .domain.identity import cn_identity
    return cn_identity(smiles)


# ------------------------------------------------------- v1↔v2 逐题差异


DIFF_COLUMNS = [
    "qid", "agent_rank_v1", "agent_rank_v2", "agent_rank_changed",
    "engine_rank_v1", "engine_rank_v2", "engine_rank_changed",
    "engine_trigger_smiles_raw", "engine_trigger_cached_identity",
    "engine_trigger_recomputed_identity", "engine_trigger_position",
    "note",
]


def diff_v1_v2(*, v1_scoring_path: str | Path, v2_result: dict,
               engine_results_path: str | Path | None,
               agent_predictions_path: str | Path,
               out_path: str | Path | None = None) -> dict:
    """逐题列出 v1(scorer-1)与 v2(scorer-2)的 rank 差异及触发候选。

    - agent 差异应为 0(若不为 0,逐题给原始 SMILES 供回查);
    - 引擎差异触发候选给出原始 SMILES、缓存身份与重算身份,可回到封存
      候选;v2 丢命中时以 v1 触发候选为准。
    """
    from .domain.identity import cn_identity

    v1 = {q["qid"]: q for q in
          json.loads(Path(v1_scoring_path).read_text(encoding="utf-8"))
          ["per_question"]}
    v2 = {q["qid"]: q for q in v2_result["per_question"]}
    if set(v1) != set(v2):
        raise ScorerV2Error("v1/v2 qid 集合不一致",
                            {"only_v1": sorted(set(v1) - set(v2))[:5],
                             "only_v2": sorted(set(v2) - set(v1))[:5]})
    engine = _engine_rows(engine_results_path)
    rows = []
    for qid, q2 in v2.items():
        q1 = v1[qid]
        a1, a2 = q1.get("agent_rank"), q2["agent_rank"]
        e1, e2 = q1.get("engine_rank"), q2["engine_rank"]
        trigger_smiles = cached = recomputed = None
        position = None
        note = ""
        if e1 != e2:
            eng = engine.get(qid) or {}
            entries = eng.get("top10", []) if eng.get("status") == "ok" else []
            ent = None
            if e2 is not None and e2 <= len(entries):
                ent = entries[e2 - 1]
                note = "v2 新命中或 rank 变化;以 v2 首命中候选为准"
            elif e1 is not None and e1 <= len(entries):
                ent = entries[e1 - 1]
                note = "v2 丢失 v1 命中;以 v1 首命中候选为准"
            if ent is not None:
                trigger_smiles = ent.get("product_smiles", "")
                cached = ent.get("product_identity")
                recomputed = cn_identity(trigger_smiles)
                position = ent.get("engine_rank")
        if a1 != a2:
            note = (note + ";" if note else "") + "agent rank 变化(应逐题回查)"
        rows.append({
            "qid": qid,
            "agent_rank_v1": a1, "agent_rank_v2": a2,
            "agent_rank_changed": a1 != a2,
            "engine_rank_v1": e1, "engine_rank_v2": e2,
            "engine_rank_changed": e1 != e2,
            "engine_trigger_smiles_raw": trigger_smiles,
            "engine_trigger_cached_identity": cached,
            "engine_trigger_recomputed_identity": recomputed,
            "engine_trigger_position": position,
            "note": note,
        })
    stats = {
        "n_questions": len(rows),
        "n_agent_rank_changed": sum(1 for r in rows if r["agent_rank_changed"]),
        "n_engine_rank_changed": sum(1 for r in rows if r["engine_rank_changed"]),
        "n_engine_new_hit": sum(1 for r in rows
                                if r["engine_rank_v1"] is None
                                and r["engine_rank_v2"] is not None),
        "n_engine_lost_hit": sum(1 for r in rows
                                 if r["engine_rank_v1"] is not None
                                 and r["engine_rank_v2"] is None),
        "n_engine_rank_shift": sum(
            1 for r in rows if r["engine_rank_changed"]
            and r["engine_rank_v1"] is not None
            and r["engine_rank_v2"] is not None),
        "scorer_v1": SCORER_V1_VERSION,
        "scorer_v2": SCORER_V2_VERSION,
    }
    result = {"summary": stats, "columns": DIFF_COLUMNS, "rows": rows}
    if out_path is not None:
        _write_json(Path(out_path), result)
    return result


# ---------------------------------------------------------------- TSV 输出


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v).replace("\t", " ").replace("\n", " ")


def write_tsv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(columns)]
    for r in rows:
        lines.append("\t".join(_fmt(r.get(c)) for c in columns))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- CLI 入口


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="EC298 同口径重评分 v2(零 LLM、零网络;路径显式传入)")
    ap.add_argument("--agent-predictions", required=True,
                    help="封存 merged predictions.jsonl")
    ap.add_argument("--engine-results", required=True,
                    help="封存 engine_arm/engine_results.jsonl")
    ap.add_argument("--gold", required=True, help="只读金标 questions.jsonl")
    ap.add_argument("--v1-scoring", default=None,
                    help="封存 v1 per_question_scoring.json(给出生成 diff)")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs_sha = {
        "agent_predictions": _sha256_file(Path(args.agent_predictions)),
        "engine_results": _sha256_file(Path(args.engine_results)),
        "gold_questions": _sha256_file(Path(args.gold)),
    }

    v2 = score_exam_v2(
        agent_predictions_path=args.agent_predictions,
        engine_results_path=args.engine_results,
        gold_questions_path=args.gold,
        out_path=out_dir / "score_v2.json",
        inputs_sha=inputs_sha)
    s = v2["summary"]
    print(json.dumps({
        "scorer_version": s["scorer_version"],
        "n_questions": s["n_questions"],
        "agent_hit@1/3/5": [s["agent"]["hit@1"], s["agent"]["hit@3"],
                            s["agent"]["hit@5"]],
        "engine_hit@1/3/5/10": [s["engine_top10"]["hit@1"],
                                s["engine_top10"]["hit@3"],
                                s["engine_top10"]["hit@5"],
                                s["engine_top10"]["hit@10"]],
        "tiers_v2": s["tiers_v2"],
    }, ensure_ascii=False))

    sens = multicomponent_sensitivity(
        agent_predictions_path=args.agent_predictions,
        engine_results_path=args.engine_results,
        gold_questions_path=args.gold,
        out_path=out_dir / "multicomponent_sensitivity.json")
    print(json.dumps({"multicomponent": sens["summary"]},
                     ensure_ascii=False))

    if args.v1_scoring:
        diff = diff_v1_v2(
            v1_scoring_path=args.v1_scoring, v2_result=v2,
            engine_results_path=args.engine_results,
            agent_predictions_path=args.agent_predictions,
            out_path=out_dir / "score_v1_v2_diff.json")
        print(json.dumps({"v1_v2_diff": diff["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
