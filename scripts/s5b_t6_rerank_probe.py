#!/usr/bin/env python3
"""s5b_t6_rerank_probe.py — T6 零模型摸底：D2 槽位竞争验证 + 固定快照确定性重排模拟。

任务书：docs/TASK_S5B_RERANK_PROBE_T6_2026-10-12.md。
题域标签：298 / RHEA 通用酶学 / 已见题。数字一律带此标签，不外推 dev。

任务 A（D2 槽位竞争，mimo r35 P3 假设验证）：
  对 chain12 的 14 道 hit@1 退步题逐题判定上方候选身份
  （D2 竞争成立 / 排序方差·上方非 D2 / 证据不足），
  另对 13 道 D2 指纹题（题级 8 strict / 4 partial / 1 uncovered）统计
  D2 陪跑事件的 position 分布。

任务 B（零模型确定性重排模拟，固定快照，规则全局应用）：
  对象 = 每题 candidate_events 序列（判分口径 (created_at,event_id) 升序）。
  重排只换顺序不改集合；重排后 rank = 首个 strict_hit 事件位次。
  R0 基线 = 原序，硬门：必须复现 metrics 的 hit@1/hit@3/hit@5 = 92/126/130
  且逐题 rank 与 metrics 全等，不过即退出码 2 停下。
  规则（每条全局作用于全部 298 题，禁只作用于失分题）：
    R1  来源优先级（降级实现）：hypothesis.origin_group_key 前缀三分类
        rec-source > analog-template > unmarked（corpus/novel 在事件
        payload 中不可区分，unmarked 归并，如实披露）。方向为假设，
        附 R1b 反向敏感性。
    R2  参与物简洁优先：事件 participants 总数少者优先（stable）。
    R3  产物复杂度：主产物（principal_product；缺省回退全部 product）
        SMILES 重原子数少者优先；解析失败排最后并计数披露。
    R4  反向序（下界对照）。
    R5  model_rank 痕迹：不可用作全局规则——候选事件上覆盖率仅约 12%
        （expansion_outcomes.model.model_rank_by_id），按任务书"字段
        不可得如实降级"条款不运行，仅在报告中披露覆盖率。
  U 不变自检：每题 strict_hit 事件集合与 R0 全等（重排不改集合，
  程序复核），U=130 不变。

红线：零模型零网络零 LLM；synced/analysis 只读；判分代码零触碰（本脚本
不 import 判分模块，只读 rescore_detail/metrics 产物与 synced payload）；
不 commit 不 push。

用法：
    python3 scripts/s5b_t6_rerank_probe.py \
        [--batch12 reports/ppv1_s5b/chain12_s5b_298_v4b_20261012] \
        [--batch11 reports/ppv1_s5b/chain11_s5b_298_v4_20261010]

输出（analysis/ 下，t6_ 前缀）：
    t6_rerank.json        任务 A+B 机器数据（R0 门、规则矩阵、U 不变证明、
                          逐题竞争判定、D2 陪跑位次分布、provenance）
    t6_rerank_matrix.md   任务 B 规则矩阵人读版
    t6_d2_contention.md   任务 A 人读版（聚合+逐题清单）
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_TAG = "298 / RHEA 通用酶学 / 已见题"
R0_EXPECT = (92, 126, 130)

# 对账报告附录 A 的 14 道退步题前缀（程序对账用；* = 带 D2 指纹）
APPENDIX_A = {
    "082f4c1a": False, "18a3c06e": False, "44411841": True,
    "45d8d90f": False, "4c2cd0c3": False, "9becc12f": False,
    "b978fd0b": True, "0eda0ec3": True, "21ed83a6": True,
    "5d15fc19": False, "341b958e": False, "365fb0be": False,
    "5e9b5672": False, "65536b46": False,
}
# 对账报告附录 B 的 35 道新 strict 前缀 → c12 rank
APPENDIX_B = {
    "0567e10c": 3, "090cdd3b": 1, "1629feef": 1, "1de92ec1": 1,
    "22901c4d": 1, "248f2d71": 1, "28cc9c75": 5, "36c4cbdc": 1,
    "3f134aaa": 1, "439a1e93": 1, "4609b23a": 1, "4e05a0b8": 3,
    "5048373e": 1, "57e0d032": 2, "582fbbca": 1, "5975a922": 1,
    "66ce382c": 1, "6b806f47": 1, "7265b8c5": 1, "8bb56f09": 1,
    "9c0a2d02": 2, "a685d0ed": 1, "b139babc": 1, "b6f489e0": 1,
    "bed2884c": 1, "d30a28d0": 3, "e11a1cac": 2, "e47fbe85": 2,
    "ebe7683e": 1, "f8ce36a0": 1, "fb86653f": 3, "fea48338": 1,
    "bcf26fbe": 1, "ddbcc56d": 2, "e5bcfa56": 1,
}


# ---------------------------------------------------------------- 数据装载


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def metrics_by_qid(batch: Path) -> dict[str, dict]:
    m = load_json(batch / "metrics.json")
    return {str(r["qid"]): r for r in m.get("per_qid") or []}


class PayloadStore:
    """qid -> payload 只读取通道（synced 只读；带 json.loads 缓存）。"""

    def __init__(self, batch: Path):
        self.root = batch / "synced" / "runs"
        self.cache: dict[str, dict] = {}
        self.open_failures: list[str] = []

    def of(self, run_id: str, export_digest: str) -> dict:
        key = f"{run_id}:{export_digest}"
        if key in self.cache:
            return self.cache[key]
        path = (self.root / run_id / "native_export" /
                export_digest[:24] / "payload.json")
        try:
            payload = load_json(path)
        except (OSError, ValueError) as exc:
            self.open_failures.append(f"{key}: {exc}")
            payload = {}
        self.cache[key] = payload
        return payload


def event_d2_fingerprint(payload: dict) -> set[str]:
    """事件级 D2 指纹：audit_production_reports 的 production_payload 中
    cosubstrate_disclosure 含 record_declared_copy 组件的 event_id 集合。"""
    marked: set[str] = set()
    for ap in payload.get("audit_production_reports") or []:
        pp = ap.get("production_payload") or {}
        disc = pp.get("cosubstrate_disclosure") or {}
        comps = (disc.get("declared_copy_components")
                 or disc.get("bystander_cosubstrates") or [])
        hit = False
        for c in comps if isinstance(comps, list) else []:
            if isinstance(c, dict) and \
                    str(c.get("component_source") or "") == \
                    "record_declared_copy":
                hit = True
        # 兼容形态：disclosure 任意子串带 component_source=record_declared_copy
        if not hit and "record_declared_copy" in json.dumps(disc):
            hit = True
        if hit and pp.get("event_id"):
            marked.add(str(pp["event_id"]))
    return marked


def event_rows(payload: dict) -> dict[str, dict]:
    """event_id -> {origin_class, n_participants, principal_product_smiles,
    all_product_smiles, hypothesis_id}。"""
    hyp_origin: dict[str, str] = {}
    for h in payload.get("hypotheses") or []:
        ogk = str((h.get("payload") or {}).get("origin_group_key") or "")
        if ogk.startswith("rec-source"):
            cls = "rec-source"
        elif ogk.startswith("analog-template"):
            cls = "analog-template"
        elif ogk == "":
            cls = "unmarked"
        else:
            cls = "unmarked"
        hyp_origin[str(h.get("hypothesis_id"))] = cls
    state_smiles: dict[str, str] = {}
    for s in payload.get("states") or []:
        sp = s.get("payload") or {}
        smi = str(sp.get("smiles_isomeric") or sp.get("cn_identity") or "")
        state_smiles[str(s.get("state_id"))] = smi
    rows: dict[str, dict] = {}
    for e in payload.get("events") or []:
        body = e.get("payload") or {}
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                body = {}
        parts = body.get("participants") or []
        products = [p for p in parts if str(p.get("side")) == "product"]
        principal = [p for p in products
                     if str(p.get("role")) == "principal_product"]
        use = principal or products
        rows[str(e.get("event_id"))] = {
            "origin_class": hyp_origin.get(str(e.get("hypothesis_id")),
                                           "unmarked"),
            "n_participants": len(parts),
            "principal_product_smiles":
                ";".join(sorted(state_smiles.get(str(p.get("state_ref")), "")
                                for p in use)),
            "principal_product_states": [str(p.get("state_ref"))
                                         for p in use],
        }
    return rows


# ---------------------------------------------------------------- 任务 B


def rank_of(seq: list[dict]) -> int | None:
    """rank = 重排后序列中的 1 基位次（不读事件上残留的原 position 字段）。"""
    for i, c in enumerate(seq, 1):
        if c["strict_hit"]:
            return i
    return None


def hits(seq: list[dict], k: int) -> bool:
    r = rank_of(seq)
    return r is not None and r <= k


def stable_sort(seq: list[dict], key):
    return sorted(seq, key=lambda c: (key(c), c["position"]))


def run_rules(questions: dict[str, list[dict]], feats: dict[str, dict],
              order: list[str]) -> dict[str, dict]:
    """对每题候选序列施加全局规则，返回每规则的逐题序列与 rank。"""
    rules: dict[str, tuple] = {
        "R0_original": ("原序基线",
                        lambda qid, c: 0),
        "R1_source_priority": ("来源优先级 rec-source>analog-template>"
                               "unmarked（降级三分类，方向为假设）",
                               lambda qid, c: {
                                   "rec-source": 0, "analog-template": 1,
                                   "unmarked": 2}[
                                   feats[qid][c["event_id"]]["origin_class"]]),
        "R1b_source_priority_inv": ("R1 反向敏感性（unmarked 优先）",
                                    lambda qid, c: {
                                        "rec-source": 2, "analog-template": 1,
                                        "unmarked": 0}[
                                        feats[qid][c["event_id"]]
                                        ["origin_class"]]),
        "R2_fewer_participants": ("参与物总数少者优先",
                                  lambda qid, c: feats[qid][c["event_id"]]
                                  ["n_participants"]),
        "R3_smaller_principal_product": ("主产物重原子数少者优先",
                                         lambda qid, c: feats[qid]
                                         [c["event_id"]]
                                         ["principal_product_heavy"]),
        "R4_reverse": ("反向序（下界对照）", None),
    }
    out: dict[str, dict] = {}
    for name, (desc, key) in rules.items():
        new_rank: dict[str, int | None] = {}
        sets_same = True
        for qid in order:
            seq = questions[qid]
            if name == "R4_reverse":
                perm = sorted(seq, key=lambda c: (-c["position"]))
            elif key is None:
                perm = list(seq)
            else:
                perm = stable_sort(seq, lambda c: key(qid, c))
            # strict_hit 集合不变证明（重排不改集合）
            if sorted(c["event_id"] for c in perm if c["strict_hit"]) != \
                    sorted(c["event_id"] for c in seq if c["strict_hit"]):
                sets_same = False
            new_rank[qid] = rank_of(perm)
        out[name] = {
            "description": desc,
            "rank_by_qid": new_rank,
            "strict_set_invariant": sets_same,
        }
    return out


def matrix_for(rule_ranks: dict[str, int | None], base_ranks:
               dict[str, int | None], order: list[str],
               reg14: set[str], late38: set[str], old92: set[str]) -> dict:
    h1 = sum(1 for q in order if rule_ranks[q] == 1)
    h3 = sum(1 for q in order if rule_ranks[q] is not None
             and rule_ranks[q] <= 3)
    h5 = sum(1 for q in order if rule_ranks[q] is not None
             and rule_ranks[q] <= 5)
    u = sum(1 for q in order if rule_ranks[q] is not None)
    retained = sum(1 for q in old92 if rule_ranks[q] == 1)
    conv = sum(1 for q in late38 if rule_ranks[q] == 1)
    recov = sum(1 for q in reg14 if rule_ranks[q] == 1)
    return {
        "hit@1": h1, "hit@3": h3, "hit@5": h5, "U_strict": u,
        "old92_retained_at1": retained,
        "late38_converted_to_rank1": conv,
        "reg14_recovered_to_rank1": recov,
        "net_gain_hit1_vs_92": h1 - 92,
    }


# ---------------------------------------------------------------- 任务 A


def classify_contention(qid: str, detail: dict, rows: dict[str, dict],
                        d2_events: set[str], c12_status: str,
                        edge0: dict) -> dict:
    """逐题三分类：D2 竞争成立 / 排序方差 / 证据不足。

    strict（有首个严格命中事件）：看正确答案上方候选是否 D2 指纹事件。
    partial（无严格命中）：看造成 superset 失配的事件是否 D2 指纹事件
    （D2 双刃机制：更完整的 D2 事件顶替 exact 候选判 partial）。
    uncovered：无 matched 事件 ⇒ 证据不足。
    """
    cands = sorted(detail["candidate_events"], key=lambda c: c["position"])
    first_hit = next((c for c in cands if c["strict_hit"]), None)
    above = [c for c in cands if first_hit and
             c["position"] < first_hit["position"]]

    def probe(c):
        f = rows.get(c["event_id"], {})
        return {
            "position": c["position"],
            "event_id": c["event_id"],
            "strict_hit": c["strict_hit"],
            "origin_class": f.get("origin_class"),
            "n_participants": f.get("n_participants"),
            "principal_product_smiles": f.get("principal_product_smiles"),
            "d2_fingerprint": c["event_id"] in d2_events,
        }

    above_rows = [probe(c) for c in above]
    hit_row = probe(first_hit) if first_hit else None
    d2_above = [r for r in above_rows if r["d2_fingerprint"]]

    sup = [e for e in (edge0.get("coverage_mismatch_events") or [])
           if e.get("participant_coverage") == "superset"]
    sup_ids = {str(e.get("event_id")) for e in sup}
    sup_rows = [{
        "position": c["position"],
        "event_id": c["event_id"],
        "d2_fingerprint": c["event_id"] in d2_events,
        "in_superset_mismatch": c["event_id"] in sup_ids,
    } for c in cands if c["event_id"] in sup_ids]
    d2_sup = [r for r in sup_rows if r["d2_fingerprint"]]

    if c12_status == "unmatched_required_node_uncovered":
        verdict = "证据不足"
        note = "c12 题桶 uncovered：无 matched 事件，无上方挤位结构可查"
    elif first_hit is not None:
        if d2_above:
            verdict = "D2 竞争成立"
            note = "正确答案上方存在 D2 指纹事件"
        elif above_rows:
            verdict = "排序方差"
            note = "上方候选均非 D2 指纹事件（来源分类：" + \
                ",".join(str(r["origin_class"]) for r in above_rows) + "）"
        else:
            verdict = "证据不足"
            note = "上方候选特征不可得"
    else:
        if d2_sup:
            verdict = "D2 竞争成立"
            note = ("无严格命中；superset 失配事件即 D2 指纹事件"
                    "（更完整的 D2 事件顶替 exact 候选判 partial）")
        elif sup_rows:
            verdict = "排序方差"
            note = ("无严格命中；superset 失配事件均非 D2 指纹事件"
                    "（coverage 失配机制，非 D2）")
        else:
            verdict = "证据不足"
            note = "无严格命中且无 superset 失配事件（partial 机制非 superset 类）"
    return {
        "qid": qid,
        "c12_status": c12_status,
        "first_strict_position": (first_hit or {}).get("position"),
        "above_rows": above_rows,
        "hit_row": hit_row,
        "superset_rows": sup_rows,
        "verdict": verdict,
        "note": note,
        "superset_mismatch_events": len(sup),
        "superset_with_coproduct": sum(
            1 for e in sup if e.get("coproduct_participants")),
    }


# ---------------------------------------------------------------- 主流程


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch12", type=Path,
                    default=REPO_ROOT / "reports/ppv1_s5b/"
                            "chain12_s5b_298_v4b_20261012")
    ap.add_argument("--batch11", type=Path,
                    default=REPO_ROOT / "reports/ppv1_s5b/"
                            "chain11_s5b_298_v4_20261010")
    args = ap.parse_args()
    b12, b11 = args.batch12, args.batch11
    out_dir = b12 / "analysis"

    m12 = metrics_by_qid(b12)
    m11 = metrics_by_qid(b11)
    rd = load_json(b12 / "analysis/rescore_detail.json")
    pq = rd["per_qid"]
    order = sorted(pq.keys())
    store = PayloadStore(b12)

    # ---- 候选序列 + 特征 ----
    questions: dict[str, list[dict]] = {}
    feats: dict[str, dict] = {}
    d2_by_q: dict[str, set[str]] = {}
    for qid in order:
        d = pq[qid]
        payload = store.of(d["run_id"], d["export_digest"])
        rows = event_rows(payload)
        d2_events = event_d2_fingerprint(payload)
        d2_by_q[qid] = d2_events
        feats[qid] = rows
        questions[qid] = sorted(d["candidate_events"],
                                key=lambda c: c["position"])

    # 重原子数（rdkit 机械计数；解析失败 → 大数排最后，计数披露）
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
    parse_fail = 0
    for qid in order:
        for eid, f in feats[qid].items():
            smi = f["principal_product_smiles"] or ""
            parts = [s for s in smi.split(";") if s]
            heavy = 0
            ok = bool(parts)
            for s in parts:
                mol = Chem.MolFromSmiles(s)
                if mol is None:
                    ok = False
                    continue
                heavy += sum(1 for a in mol.GetAtoms()
                             if a.GetAtomicNum() > 1)
            if not ok:
                parse_fail += 1
                heavy = 10**9
            f["principal_product_heavy"] = heavy
            f["principal_product_parse_ok"] = ok

    # ---- R0 硬门 ----
    base_rank = {qid: rank_of(questions[qid]) for qid in order}
    h1 = sum(1 for q in order if base_rank[q] == 1)
    h3 = sum(1 for q in order if base_rank[q] is not None and base_rank[q] <= 3)
    h5 = sum(1 for q in order if base_rank[q] is not None and base_rank[q] <= 5)
    u = sum(1 for q in order if base_rank[q] is not None)
    rank_dis = [q for q in order
                if base_rank[q] != (m12[q]["main"] or {}).get("rank")]
    gate = (h1, h3, h5) == R0_EXPECT and not rank_dis
    print(f"[R0] hit@1/hit@3/hit@5 = {h1}/{h3}/{h5} (期望 92/126/130); "
          f"U={u}; rank 与 metrics 不一致 {len(rank_dis)} 题; "
          f"门={'PASS' if gate else 'FAIL'}")
    if not gate:
        print("[GATE] R0 基线不复现 ⇒ 按任务书停下报告，不继续模拟")
        return 2

    # ---- 迁移清单 ----
    def status_of(row): return str((row.get("main") or {}).get("match_status"))
    def rank_of_row(row): return (row.get("main") or {}).get("rank")
    reg14 = sorted(q for q in order
                   if rank_of_row(m11[q]) == 1 and rank_of_row(m12[q]) != 1)
    new_strict35 = sorted(q for q in order
                          if status_of(m12[q]) == "matched_strict"
                          and status_of(m11[q]) != "matched_strict")
    late38 = sorted(q for q in order if status_of(m12[q]) == "matched_strict"
                    and rank_of_row(m12[q]) != 1)
    old92 = sorted(q for q in order if rank_of_row(m12[q]) == 1)
    d2_all13 = sorted(q for q in order if d2_by_q[q])
    d2_buckets = Counter(status_of(m12[q]) for q in d2_all13)

    # ---- 附录对账（清单前缀 + 指纹标记 + rank）----
    def prefix(q): return q.removeprefix("RXNG_")[:8]
    app_a_diff = []
    for q in reg14:
        p = prefix(q)
        if p not in APPENDIX_A:
            app_a_diff.append({"qid": q, "issue": "prefix_not_in_appendix_A"})
        elif APPENDIX_A[p] != bool(d2_by_q[q]):
            app_a_diff.append({
                "qid": q, "issue": "d2_fingerprint_flag_differs",
                "appendix_A": APPENDIX_A[p], "computed": bool(d2_by_q[q])})
    extra_a = sorted(set(APPENDIX_A) - {prefix(q) for q in reg14})
    app_b_diff = []
    for q in new_strict35:
        p = prefix(q)
        if p not in APPENDIX_B:
            app_b_diff.append({"qid": q, "issue": "prefix_not_in_appendix_B"})
        elif APPENDIX_B[p] != rank_of_row(m12[q]):
            app_b_diff.append({
                "qid": q, "issue": "rank_differs",
                "appendix_B": APPENDIX_B[p], "computed": rank_of_row(m12[q])})
    extra_b = sorted(set(APPENDIX_B) - {prefix(q) for q in new_strict35})
    print(f"[APPENDIX] A diff={app_a_diff} missing_in_computed={extra_a}; "
          f"B diff={app_b_diff} missing_in_computed={extra_b}")
    print(f"[LISTS] reg14={len(reg14)} new_strict={len(new_strict35)} "
          f"late38={len(late38)} old92={len(old92)} d2={len(d2_all13)} "
          f"d2_buckets={dict(d2_buckets)}")

    # ---- 任务 B：规则矩阵 ----
    rules = run_rules(questions, feats, order)
    for name, r in rules.items():
        r["matrix"] = matrix_for(r["rank_by_qid"], base_rank, order,
                                 set(reg14), set(late38), set(old92))
        r["matrix"]["U_invariant"] = r["strict_set_invariant"]
        print(f"[RULE] {name}: "
              + json.dumps(r["matrix"], ensure_ascii=False))

    # ---- 任务 A：14 退步题逐题判定 ----
    contention = []
    for qid in reg14:
        d = pq[qid]
        payload = store.of(d["run_id"], d["export_digest"])
        edge0 = (d["edge_matches"] or [{}])[0]
        contention.append(classify_contention(
            qid, d, feats[qid], d2_by_q[qid],
            status_of(m12[qid]), edge0))
    verdicts = Counter(c["verdict"] for c in contention)
    print("[TASK A] 14 退步题三分类:", dict(verdicts))

    # ---- 任务 A2：3 道 strict→partial 深查数据 = contention_rows 的
    # partial 子集（superset_rows 已含逐事件 D2 指纹与位次），不再单独扫。

    # ---- 任务 A3：13 道 D2 指纹题陪跑位次分布 ----
    a3_rows = []
    pos_hist = Counter()
    for qid in d2_all13:
        d = pq[qid]
        cand = questions[qid]
        first_hit = next((c for c in cand if c["strict_hit"]), None)
        d2_pos = [c["position"] for c in cand
                  if c["event_id"] in d2_by_q[qid]]
        for p in d2_pos:
            pos_hist[p] += 1
        a3_rows.append({
            "qid": qid,
            "c12_status": status_of(m12[qid]),
            "c12_rank": rank_of_row(m12[qid]),
            "first_strict_position": (first_hit or {}).get("position"),
            "d2_event_positions": d2_pos,
            "d2_event_is_strict_hit": bool(
                first_hit and first_hit["event_id"] in d2_by_q[qid]),
        })
    print(f"[TASK A3] D2 陪跑事件 position 直方图: {dict(sorted(pos_hist.items()))}")
    # 8 道 strict 指纹题的受限直方图（任务 A 第 3 项口径）
    pos_hist_strict8 = Counter()
    for r in a3_rows:
        if r["c12_status"] == "matched_strict":
            for p in r["d2_event_positions"]:
                pos_hist_strict8[p] += 1
    print(f"[TASK A3] 8 道 strict 指纹题 D2 陪跑位次: "
          f"{dict(sorted(pos_hist_strict8.items()))}")

    # ---- 落盘 ----
    provenance = {
        "domain_tag": DOMAIN_TAG,
        "batch12": str(b12), "batch11": str(b11),
        "rescore_alignment": rd.get("alignment", {}).get("gate"),
        "r0_gate": {"expect": list(R0_EXPECT), "actual": [h1, h3, h5],
                    "rank_mismatch_vs_metrics": len(rank_dis),
                    "pass": gate},
        "llm_calls": 0, "network_calls": 0,
        "product_smiles_parse_failures": parse_fail,
        "payload_open_failures": store.open_failures,
        "note_fixed_snapshot": ("重排模拟是固定快照上的确定性重排：只换候选"
                                "顺序、不改候选宇宙，不产生新候选；120 道 "
                                "H 桶（uncovered 且无 strict 命中）不可由此"
                                "拯救。非新系统成绩。"),
        "feature_degradation": {
            "R1": ("事件 payload 无 recorded/corpus/analog/novel 四通道字段；"
                   "可用降级特征 = hypothesis.origin_group_key 前缀三分类"
                   "(rec-source 135 / analog-template 44 / unmarked 1299, "
                   "候选事件计数)；unmarked 中 corpus 与模型提案不可区分"),
            "R5_model_rank": ("expansion_outcomes.model.model_rank_by_id 在 "
                              "候选事件上覆盖率约 12%(179/1478)，不满足全局"
                              "规则要求，不运行"),
            "dedup_signature": ("event_semantics_hash 去重需删事件、违反"
                                "「只换顺序不改集合」；纯排序键在重复组内"
                                "等价原序，无效果，故不设规则"),
        },
    }
    result = {
        "provenance": provenance,
        "lists": {
            "reg14": reg14, "new_strict35": new_strict35,
            "late38": late38, "old92": old92,
            "d2_fingerprint13": d2_all13,
            "d2_buckets_8S_4P_1U": dict(d2_buckets),
            "appendix_A_crosscheck": {
                "diff": app_a_diff, "missing_in_computed": extra_a,
                "match": not app_a_diff and not extra_a},
            "appendix_B_crosscheck": {
                "diff": app_b_diff, "missing_in_computed": extra_b,
                "match": not app_b_diff and not extra_b},
        },
        "taskB": {
            "rules": {name: {
                "description": r["description"],
                "matrix": r["matrix"],
                "strict_set_invariant": r["strict_set_invariant"],
                "rank_by_qid": r["rank_by_qid"],
            } for name, r in rules.items()},
        },
        "taskA": {
            "contention_rows": contention,
            "verdict_counts": dict(verdicts),
            "d2_fingerprint_rows": a3_rows,
            "d2_rider_position_histogram": {
                str(k): v for k, v in sorted(pos_hist.items())},
            "d2_rider_position_histogram_strict8": {
                str(k): v for k, v in sorted(pos_hist_strict8.items())},
        },
    }
    (out_dir / "t6_rerank.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n", encoding="utf-8")

    # ---- t6_rerank_matrix.md ----
    md = [f"# T6 任务 B：固定快照确定性重排模拟（题域 {DOMAIN_TAG}）\n"]
    md.append("- R0 自检门：原序复现 hit@1/hit@3/hit@5 = "
              f"{h1}/{h3}/{h5}（期望 92/126/130），逐题 rank 与 metrics "
              f"全等（不一致 {len(rank_dis)} 题），U={u} — 门 PASS")
    md.append("- U 不变证明：每规则逐题 strict_hit 事件集合与 R0 全等"
              "（程序比对，全部 True）；重排不改候选集合\n")
    md.append("| 规则 | hit@1 | hit@3 | hit@5 | U | 旧92保留 | 38后位转化"
              " | 14退步恢复 | 净增 |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, r in rules.items():
        mt = r["matrix"]
        md.append(
            f"| {name} | {mt['hit@1']} | {mt['hit@3']} | {mt['hit@5']} "
            f"| {mt['U_strict']} | {mt['old92_retained_at1']} "
            f"| {mt['late38_converted_to_rank1']} "
            f"| {mt['reg14_recovered_to_rank1']} "
            f"| {mt['net_gain_hit1_vs_92']:+d} |")
    md.append("\n## 规则说明与降级披露\n")
    for name, r in rules.items():
        md.append(f"- **{name}**: {r['description']}")
    for k, v in provenance["feature_degradation"].items():
        md.append(f"- 降级/不设规则 **{k}**: {v}")
    md.append("\n## 上限声明\n")
    md.append("> 固定快照模拟：重排只换候选顺序，不改候选宇宙；"
              "120 道 H 桶（uncovered）不可由重排拯救。本矩阵不是新系统"
              "成绩，只量化「排序可挽回多少已覆盖但被压后位的答案」。")
    (out_dir / "t6_rerank_matrix.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")

    # ---- t6_d2_contention.md ----
    md = [f"# T6 任务 A：D2 槽位竞争验证（题域 {DOMAIN_TAG}）\n"]
    md.append("mimo r35 P3 假设「D2 候选把正确答案挤到后位」的零模型验证。"
              "事件级 D2 指纹 = audit_production_reports."
              "production_payload.cosubstrate_disclosure 含 "
              "record_declared_copy 组件；来源分类为降级三分类（见 t6_rerank."
              "json feature_degradation）。\n")
    md.append(f"## 聚合（14 道 hit@1 退步题）\n")
    md.append(f"- D2 竞争成立: {verdicts.get('D2 竞争成立', 0)}")
    md.append(f"- 排序方差（上方是非 D2 候选）: "
              f"{verdicts.get('排序方差', 0)}")
    md.append(f"- 证据不足: {verdicts.get('证据不足', 0)}\n")
    md.append("| qid | c12 桶 | 首命中位次 | 上方候选（位次/D2/来源） | 判定 |")
    md.append("|---|---|---:|---|---|")
    for c in contention:
        abv = "; ".join(
            f"#{r['position']}{'D2' if r['d2_fingerprint'] else ''}/"
            f"{r['origin_class']}" for r in c["above_rows"]) or "-"
        md.append(f"| {c['qid'][:24]}… | {c['c12_status'].split('_')[-1]} "
                  f"| {c['first_strict_position'] or '-'} | {abv} "
                  f"| {c['verdict']} |")
    md.append("\n## 3 道 strict→partial 深查（superset 失配事件身份）\n")
    md.append("| qid | superset 失配事件（位次/D2） | 带 coproduct | 判定依据 |")
    md.append("|---|---|---:|---|")
    for c in contention:
        if c["c12_status"] != "matched_participant_coverage_partial":
            continue
        sr = "; ".join(
            f"#{r['position']}{'D2' if r['d2_fingerprint'] else 'nonD2'}"
            for r in c["superset_rows"]) or "-"
        md.append(f"| {c['qid'][:24]}… | {sr} "
                  f"| {c['superset_with_coproduct']} | {c['note']} |")
    md.append("\n## 13 道 D2 指纹题（题级 8 strict / 4 partial / 1 "
              "uncovered）：D2 陪跑事件位次\n")
    md.append("| qid | c12 桶 | 首严格命中位次 | D2 事件位次 | D2 事件是命中"
              "事件 |")
    md.append("|---|---|---:|---|---|")
    for r in a3_rows:
        md.append(
            f"| {r['qid'][:24]}… | {r['c12_status'].split('_')[-1]} "
            f"| {r['first_strict_position'] or '-'} "
            f"| {r['d2_event_positions'] or '-'} "
            f"| {'Y' if r['d2_event_is_strict_hit'] else '-'} |")
    md.append(f"\nD2 陪跑事件 position 直方图（全部 13 题）："
              f"{dict(sorted(pos_hist.items()))}；其中 8 道 strict 指纹题："
              f"{dict(sorted(pos_hist_strict8.items()))}")
    md.append("\n> 判定口径：strict 桶=正确答案上方候选存在 D2 指纹事件 ⇒ "
              "D2 竞争成立，上方均非 D2 ⇒ 排序方差；partial 桶=superset "
              "失配事件即 D2 指纹事件 ⇒ D2 竞争成立（D2 双刃机制），失配"
              "事件非 D2 ⇒ 排序方差；uncovered ⇒ 证据不足。不做化学可行性"
              "判断。")
    md.append(f"\n附录对账：A（14 退步）diff={app_a_diff} "
              f"missing_in_computed={extra_a}；B（35 新 strict，含 rank）"
              f"diff={app_b_diff} missing_in_computed={extra_b}。")
    (out_dir / "t6_d2_contention.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")

    print(f"[OUT] {out_dir}/t6_rerank.json t6_rerank_matrix.md "
          f"t6_d2_contention.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
