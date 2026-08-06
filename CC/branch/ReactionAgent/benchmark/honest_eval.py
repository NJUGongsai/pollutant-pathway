"""P0 诚实评估：只给主底物 X，检索 train donor → 迁移模板生成 → 酶集打分，看真产物能否命中。

相对旧 verify_substrate_retrieval.py 修正的四类作弊(每一处都对应旧脚本的一个已确认缺陷)
  1. 去 oracle donor    : 旧脚本只在"候选恰好含真产物"时才选该 donor、才计入分母。本脚本 donor 选择
                          只看底物相似度(不看真产物)，固定取 top-K，绝不因是否命中而改变选择或分母。
  2. 不偷 held-out 共反应物: 旧脚本把真实反应的 co-reactants 注入生成/打分。本脚本反应左侧只放 X。
  3. 全 X 进分母        : 分母 = 全部可解析测试反应，失败按类型计入(不能生成也算一次未命中)。
  4. 防酶家族泄漏       : 打分参考的酶反应族里，剔除与测试反应同 group 的反应(不只精确串匹配)。

命中判定
  真产物 Y = 测试反应产物侧主片段(canonical)。候选命中 = Y ∈ 候选产物的 canonical 片段集合。

漏斗(全部以 N_test 为分母)
  parsable → has_donor → has_candidate → generated_true → top1 / top5 / top10
失败分型
  unparsable / no_donor / no_candidate / not_generated / generated_but_ranked_low / hit
novelty 分桶
  按"测试底物 X 对 train donor 的最高相似度"分桶，报告各桶 top-k 命中，展示随新颖度的性能衰减。
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")   # 抑制 RunReactants 的 valence/kekulize 噪声(无害且拖慢 I/O)

import canonical_identity as ci
import edit_script as esmod
import align_transfer as at
import splits as sp


# ── 可配置项 ─────────────────────────────────────────────────────────────
GENERATOR = "smarts"     # smarts | align | union  —— 由 CLI/run_p0 覆盖
TOP_DONORS = 5           # 每个测试底物取 top-K 相似 train donor 迁移模板
TEMPLATE_RADIUS = 1      # 转化对迷你反应的模板半径
CENTER_SOURCE = "mcs@transformed_pair"  # 模板中心来源(报告用标签): donor 转化对上的 MCS 中心
SCORER_CAP = 40          # 每次打分参考的酶反应族上限(沿用 reaction_scorer 默认)
FAMILY_CAP = 60          # donor 酶家族反应并集的总上限(控运行时)
HIT_TOPK = (1, 5, 10)
NOVELTY_BINS = [(0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0), (1.0, 1.01)]


@dataclass
class CaseResult:
    rxn: str
    x: Optional[str] = None
    y_true: Optional[str] = None
    outcome: str = ""                 # unparsable/no_donor/no_candidate/not_generated/generated_but_ranked_low/hit
    top_donor_sim: float = 0.0        # X 对最相似 train donor 的相似度(novelty 度量)
    n_candidates: int = 0
    hit_rank: Optional[int] = None    # 真产物在打分排序中的 1-based 名次(未命中为 None)
    # ── 失败归因(与生成器无关, 用编辑签名判定) ──
    req_edit_ok: bool = False         # 测试反应自身的转化(X→Y)能否抽出编辑脚本(否=多底物/退化, 内在难例)
    edit_retrieved: bool = False      # 检索到的 donor 里, 有无携带与测试反应【同类变换】者


# ── train donor 索引(底物 Morgan 检索, 只用训练折) ─────────────────────────
def build_donor_index(train_rxns: List[str]):
    """train 反应 → (reactions, MorganFPs, main_substrate_canon)；主底物不可解析者跳过。"""
    reactions, fps, subs = [], [], []
    for rxn in train_rxns:
        x = ci.main_substrate(rxn)
        if x is None:
            continue
        m = Chem.MolFromSmiles(x)
        if m is None:
            continue
        reactions.append(rxn)
        fps.append(AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048))
        subs.append(x)
    return reactions, fps, subs


def retrieve_donors(query_x: str, index, top_k: int, exclude_group: Optional[Tuple[str, str]]):
    """按主底物 Morgan 相似度取 top-K train donor；剔除与测试反应同 group 的 donor(防泄漏)。"""
    reactions, fps, _subs = index
    qm = Chem.MolFromSmiles(query_x)
    if qm is None or not fps:
        return []
    qfp = AllChem.GetMorganFingerprintAsBitVect(qm, 2, nBits=2048)
    sims = DataStructs.BulkTanimotoSimilarity(qfp, fps)
    order = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)
    out = []
    for i in order:
        rxn = reactions[i]
        if exclude_group is not None and ci.group_key(rxn) == exclude_group:
            continue
        out.append((rxn, float(sims[i])))
        if len(out) >= top_k:
            break
    return out


# ── 生成：donor 的"有机转化"迁移到 X ───────────────────────────────────────
# donor 模板从其自身的转化对 Xdonor>>Ydonor(辅酶剥离后的干净 1:1 迷你反应)提取，
# 只迁移有机编辑本身、剥掉辅酶管道。既贴合"从相似反应学转化"的本意，又避免多反应物模板
# 在单个 X 上不点火。模板与查询 X 无关 → 按 donor 缓存一次，跨全部测试底物复用(避开 rdFMCS 重算)。
@lru_cache(maxsize=20000)
def _donor_template(donor_rxn: str):
    """从 donor 的转化对(Xdonor>>Ydonor)构建并缓存反应模板(TemplateResult)；失败返回 None。"""
    import pipeline as pl
    tp = ci.transformed_pair(donor_rxn)
    if tp is None:
        return None
    mini = f"{tp[0]}>>{tp[1]}"
    try:
        maps = pl.mcs_atom_mapping(mini)
        center = pl.extract_reaction_center(mini, maps)   # 干净迷你反应用 MCS 中心即可
        return pl.extract_template(mini, center, radius=TEMPLATE_RADIUS)
    except Exception:
        return None


def _generate_smarts(donor_rxn: str, query_x: str) -> List[str]:
    """SMARTS 路径: (缓存的) donor 模板 RunReactants 作用于 X。"""
    import pipeline as pl
    tmpl = _donor_template(donor_rxn)
    if tmpl is None:
        return []
    try:
        cands = pl.apply_template_to_molecule(tmpl, query_x, co_reactants=None)
    except Exception:
        return []
    return [c.product_smiles for c in cands]


def generate_candidates(donor_rxn: str, query_x: str) -> List[str]:
    """按 GENERATOR 分派: smarts=模板匹配, align=模糊定位+编辑回放, union=两者并集。左侧只有 X。"""
    if GENERATOR == "smarts":
        return _generate_smarts(donor_rxn, query_x)
    if GENERATOR == "align":
        return at.transfer(donor_rxn, query_x)
    if GENERATOR == "union":
        return _generate_smarts(donor_rxn, query_x) + at.transfer(donor_rxn, query_x)
    return _generate_smarts(donor_rxn, query_x)


# ── 失败归因: 与生成器无关的"变换签名"判定 ─────────────────────────────────
# 每个反应抽一份 EditScript.key()(元素×键级变化, 忽略原子编号)。用它把 not_generated 切成:
#   application_failure(变换被检索到但没施加上→值得投 B 学施加) vs
#   selection_failure  (对的变换没被检索到/是多底物→该改检索, B 也救不了)。
@lru_cache(maxsize=40000)
def _reaction_edit_key(rxn: str):
    """反应自身转化对(X→Y)的编辑签名; 抽不出(多底物/退化)返回 None。"""
    tp = ci.transformed_pair(rxn)
    if tp is None:
        return None
    es = esmod.extract_edit(tp[0], tp[1])
    return es.key() if es is not None else None


# ── 酶家族反应族(用于 DRFP 打分), 剔除同 group 泄漏 ──────────────────────────
def enzyme_family_reactions(donors: List[Tuple[str, float]], exclude_group) -> List[str]:
    import enzyme_lookup as el
    uniprots = []
    seen_u = set()
    for donor_rxn, _sim in donors:
        for uni, _ec in el.enzymes_for_reaction(donor_rxn):
            if uni not in seen_u:
                seen_u.add(uni)
                uniprots.append(uni)
    fam, seen_r = [], set()
    for uni in uniprots:
        for r in el.reactions_for_enzyme(uni):
            if r in seen_r:
                continue
            if ci.group_key(r) == exclude_group:   # 剔除与测试同一化学转化的反应(防泄漏)
                continue
            seen_r.add(r)
            fam.append(r)
            if len(fam) >= FAMILY_CAP:
                return fam
    return fam


# ── 单例评估 ────────────────────────────────────────────────────────────
def eval_one(rxn: str, index, split: sp.Split) -> CaseResult:
    import reaction_scorer as rs
    res = CaseResult(rxn=rxn)
    x = ci.main_substrate(rxn)
    y_true = ci.main_product(rxn)
    res.x, res.y_true = x, y_true
    if x is None or y_true is None:
        res.outcome = "unparsable"
        return res

    exclude_group = ci.group_key(rxn)
    donors = retrieve_donors(x, index, TOP_DONORS, exclude_group)
    if donors:
        res.top_donor_sim = donors[0][1]
    if not donors:
        res.outcome = "no_donor"
        return res

    # ── 失败归因(生成器无关): 用编辑签名判定"对的变换有没有被检索到" ──
    req_key = _reaction_edit_key(rxn)
    res.req_edit_ok = req_key is not None
    if req_key is not None:
        donor_keys = {k for k in (_reaction_edit_key(d) for d, _s in donors) if k is not None}
        res.edit_retrieved = req_key in donor_keys

    # 生成：汇集所有 donor 的候选产物(canonical 去重)
    cand_canon_to_raw: Dict[str, str] = {}
    for donor_rxn, _sim in donors:
        for prod in generate_candidates(donor_rxn, x):
            key = ".".join(sorted(ci.canon_frags(prod)))
            if key and key not in cand_canon_to_raw:
                cand_canon_to_raw[key] = prod
    candidates = list(cand_canon_to_raw.values())
    res.n_candidates = len(candidates)
    if not candidates:
        res.outcome = "no_candidate"
        return res

    # 真产物是否被生成(排序前)
    generated = any(y_true in ci.canon_frags(c) for c in candidates)
    if not generated:
        res.outcome = "not_generated"
        return res

    # 打分：DRFP-酶集(左侧仅 X, 参考族已剔除同 group 泄漏)
    fam = enzyme_family_reactions(donors, exclude_group)
    if fam:
        scored = rs.score_candidates(x, candidates, fam, exclude_reaction=None, cap=SCORER_CAP)
        ranked = [s.product_smiles for s in scored]
    else:
        ranked = candidates  # 无酶家族参考时保持生成顺序(仍诚实, 只是无打分信号)
    hit_rank = None
    for i, prod in enumerate(ranked, 1):
        if y_true in ci.canon_frags(prod):
            hit_rank = i
            break
    res.hit_rank = hit_rank
    if hit_rank is not None and hit_rank <= max(HIT_TOPK):
        res.outcome = "hit"
    else:
        res.outcome = "generated_but_ranked_low"
    return res


# ── 聚合 ────────────────────────────────────────────────────────────────
def _bin_label(sim: float) -> str:
    for lo, hi in NOVELTY_BINS:
        if lo <= sim < hi:
            return f"[{lo:.1f},{hi:.1f})" if hi <= 1.0 else "==1.0"
    return "?"


def aggregate(results: List[CaseResult]) -> dict:
    n = len(results)
    outcomes = Counter(r.outcome for r in results)
    funnel = {
        "parsable": sum(1 for r in results if r.outcome != "unparsable"),
        "has_donor": sum(1 for r in results if r.outcome not in ("unparsable", "no_donor")),
        "has_candidate": sum(1 for r in results if r.outcome in ("not_generated", "generated_but_ranked_low", "hit")),
        "generated_true": sum(1 for r in results if r.outcome in ("generated_but_ranked_low", "hit")),
    }
    topk = {f"top{k}": sum(1 for r in results if r.hit_rank is not None and r.hit_rank <= k) for k in HIT_TOPK}

    # novelty 分桶命中
    by_bin = defaultdict(lambda: {"n": 0, **{f"top{k}": 0 for k in HIT_TOPK}})
    for r in results:
        if r.outcome == "unparsable":
            continue
        b = _bin_label(r.top_donor_sim)
        by_bin[b]["n"] += 1
        for k in HIT_TOPK:
            if r.hit_rank is not None and r.hit_rank <= k:
                by_bin[b][f"top{k}"] += 1

    # ── not_generated 失败归因切分 ──
    # unextractable      : 测试反应自身抽不出编辑(多底物/退化, 内在难例, 任何单底物生成器都救不了)
    # selection_failure  : 能抽出但检索到的 donor 没带同类变换 → 病根在检索(换更好的相似度/多底物召回)
    # application_failure : 检索到了同类变换却没生成出真产物 → 病根在"施加"(WHERE/WHAT, 值得投 B 学回放)
    ng = [r for r in results if r.outcome == "not_generated"]
    attribution = {
        "not_generated": len(ng),
        "unextractable": sum(1 for r in ng if not r.req_edit_ok),
        "selection_failure": sum(1 for r in ng if r.req_edit_ok and not r.edit_retrieved),
        "application_failure": sum(1 for r in ng if r.req_edit_ok and r.edit_retrieved),
    }
    # 全体(非 unparsable)的检索上界: 对的变换被检索到的比例 —— 检索天花板
    scope = [r for r in results if r.outcome != "unparsable"]
    retrieval = {
        "req_edit_ok": sum(1 for r in scope if r.req_edit_ok),
        "edit_retrieved": sum(1 for r in scope if r.edit_retrieved),
        "scope": len(scope),
    }

    return {
        "n_test": n,
        "outcomes": dict(outcomes),
        "funnel": funnel,
        "topk": topk,
        "attribution": attribution,
        "retrieval": retrieval,
        "novelty_bins": {k: by_bin[k] for k in sorted(by_bin)},
    }


def run(strategy: str, max_cases: Optional[int] = None, seed: int = 42,
        generator: Optional[str] = None) -> dict:
    global GENERATOR
    if generator is not None:
        GENERATOR = generator
    split = sp.make_split(strategy, seed=seed)
    index = build_donor_index(split.train_rxns)
    test = split.test_rxns[:max_cases] if max_cases else split.test_rxns
    print(f"[{strategy}|gen={GENERATOR}] donors(train)={len(index[0])}  test cases={len(test)}", flush=True)
    results, t0 = [], time.time()
    for i, rxn in enumerate(test, 1):
        results.append(eval_one(rxn, index, split))
        if i % 50 == 0 or i == len(test):
            print(f"  {i}/{len(test)}  ({time.time()-t0:.0f}s)", flush=True)
    agg = aggregate(results)
    agg["strategy"] = strategy
    agg["config"] = {"generator": GENERATOR, "top_donors": TOP_DONORS, "template_radius": TEMPLATE_RADIUS,
                     "center_source": CENTER_SOURCE, "scorer_cap": SCORER_CAP,
                     "family_cap": FAMILY_CAP, "hit_topk": list(HIT_TOPK)}
    return agg


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="random", choices=["random", "scaffold", "reaction_family"])
    ap.add_argument("--generator", default="smarts", choices=["smarts", "align", "union"])
    ap.add_argument("--max-cases", type=int, default=None)
    ap.add_argument("--out", default=None, help="写 JSON 结果到此路径")
    args = ap.parse_args()
    agg = run(args.strategy, max_cases=args.max_cases, generator=args.generator)
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(agg, f, ensure_ascii=False, indent=2)
