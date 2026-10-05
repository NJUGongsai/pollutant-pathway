#!/usr/bin/env python3
"""HIT60 T8 门 1 — 深位召回器纯检索能力测量(零 LLM;金标仅在本离线进程只读)。

测量(依据 docs/TASK_V43_HIT60_S1R2_GENERATION_ARMS.md §1 与 teacher 2026-09-30
批复 §四建议 1 先决 1):
  A. 引擎原序(检索位次)top-K 金标卡召回率,K = 16/24/32 三档;
     22 题「候选含金」(FULL_SURFACE_LEAK_AUDIT §2 / COVERAGE_STAT M1,C0-b 口径)
     各档实际捞出题数与捞至位次分布;rank 75 案例核验。
  B. 独立排序信号测试(teacher 先决 2 预演):
     S1  候选卡底物与题面底物的 Morgan 指纹 Tanimoto。口径注:卡上
         reactant_smiles 与题面底物 cn 全等(引擎"当前分子"字段),真正可比的
         卡底物 = donor_refs 供体反应物(analog 1,668 + rule 281 张卡有);
         无供体的模板/记录卡与题面底物同为 1.0(并列,引擎位次破平)。
         另报 analog 通道内部按 S1 的局部位次(选择性召回的通道内形态)。
     S2a 卡来源强度分层(recorded > uspto > envipath > retrieval);
     S2b USPTO 通道模板分(engine_edge.p_uspto);
     S3  候选卡产物与题面底物的 Morgan 指纹 Tanimoto(变换幅度先验,mimo
         ③④ 过滤器的连续化版本;独立于引擎分数,不含金标信息)。
     指纹输入一律先过 cn_identity(电荷归一+立体盲),消电荷态伪影;
     口径 = 仓内 SIMILARITY_VERSION v43-rsim-1(morgan/2/2048/立体盲/Tanimoto)。
     每信号:按信号排序 top-K 金标召回率 vs 引擎原序同 K 对照;22 题中
     金标卡提前入 K 的题数与位次。
  C. 判定线素材:测量分布进 summary(判定线数值由用户/teacher 冻结)。

红线:输出件(sealed/)只含 qid/位次/旗标/信号值/来源标签,零 SMILES 零身份串;
金标只在本地离线进程打开;封存远端产物只读;不改 src/。

用法(本地 conda depending43,OMP_NUM_THREADS=1):
  PYTHONPATH=src python reports/phase_s15_hit60/deep_recall_gate1/gate1_measure.py \
      --measure            # 默认:计算并写 sealed/
  ... --check              # 复算并与 sealed/ 逐数对拍
输入:raw_dumps/(gitignored,远端只读拉取,见 gate1_remote_extract.py)、
  dev_gold/dev_gold.jsonl(gitignored)、dev_questions.jsonl、qid_flags_C0b.tsv。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # .../reports/phase_s15_hit60/deep_recall_gate1
REPO = HERE.parents[2]  # 仓根(HERE[0]=phase_s15_hit60,[1]=reports,[2]=repo)
sys.path.insert(0, str(REPO / 'src'))

from rdkit import Chem, RDLogger  # noqa: E402
from rdkit.Chem import DataStructs, rdMolDescriptors  # noqa: E402

RDLogger.DisableLog('rdApp.*')

K_GRID = (16, 24, 32)
K_ENGINE_TOP = 8  # 引擎顶块保留宽度(现产 rank 任务合格卡窗 8;hybrid 形态)
BATCH_TAGS = ('C0a', 'C0b', 'E1', 'E2a', 'E2b', 'E3')
REF_BATCH = 'C0b'  # 22 题清单与审计 2x2 的参照批(FULL_SURFACE §2)
TSV = REPO / 'reports/phase_s1_hit60/coverage_stat/qid_flags_C0b.tsv'
QUESTIONS = REPO / 'reports/phase_s1_hit60/dev_questions.jsonl'
GOLD = REPO / 'reports/phase_s1_hit60/dev_gold/dev_gold.jsonl'

# 指纹口径 = 仓内 SIMILARITY_VERSION v43-rsim-1(analog_source.py):
# morgan / radius 2 / 2048 bit / 立体盲(useChirality=False)/ Tanimoto
FP_RADIUS, FP_BITS, FP_CHIRAL = 2, 2048, False


# ---------------------------------------------------------------- fingerprints
# 口径注:卡上 reactant_smiles 与题面底物 cn 全等(六批 12,321/12,321 实测,
# =引擎"当前分子"字段),不是供体;真正可比的"候选卡底物"= donor_refs 的
# 供体反应物(analog 1,668 + rule 281 张卡有)。指纹输入一律先过 cn_identity
# (电荷归一 + 立体盲,与 SIMILARITY_FP 口径一致),消电荷态伪影。
from pathway_v43.domain.identity import cn_identity  # noqa: E402

_FP_CACHE: dict[str, object] = {}


def cn_fp(smiles: str | None):
    if not smiles:
        return None
    key = smiles
    if key in _FP_CACHE:
        return _FP_CACHE[key]
    vec = None
    for form in (cn_identity(smiles), smiles):
        m = Chem.MolFromSmiles(form) if form else None
        if m is not None:
            vec = rdMolDescriptors.GetMorganFingerprintAsBitVect(
                m, radius=FP_RADIUS, nBits=FP_BITS, useChirality=FP_CHIRAL)
            break
    _FP_CACHE[key] = vec
    return vec


def tanimoto(a, b) -> float:
    if a is None or b is None:
        return 0.0
    return DataStructs.TanimotoSimilarity(a, b)


def product_fp(products: list[dict]):
    for p in products:
        for key in ('product_smiles', 'product_smiles_full', 'product_identity'):
            v = cn_fp(p.get(key))
            if v is not None:
                return v
    return None


def donor_smiles(e: dict) -> str | None:
    for d in e.get('donors') or []:
        rs = d.get('reactant_smiles')
        if rs:
            return rs
    return None


def donor_s1(e: dict, sub_vec) -> float:
    """S1:卡供体(来源反应的底物)与题面底物的指纹 Tanimoto。
    无 donor(模板/记录直查,反应直接作用于题面底物)→ 1.0(并列,按引擎位次)。"""
    rs = donor_smiles(e)
    if rs is None:
        return 1.0
    return round(tanimoto(cn_fp(rs), sub_vec), 6)


# ---------------------------------------------------------------- statistics
def spearman(xs, ys) -> float | None:
    def _ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        rk = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for t in range(i, j + 1):
                rk[order[t]] = avg
            i = j + 1
        return rk

    if len(xs) < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return num / (dx * dy) if dx > 0 and dy > 0 else None


# ---------------------------------------------------------------- data loading
def load_gold():
    from pathway_v43.exam_v2 import load_gold as _lg
    return _lg(GOLD)


def load_questions():
    subs = {}
    for line in QUESTIONS.read_text(encoding='utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            subs[r['qid']] = r['root_smiles']
    return subs


def load_flags_tsv():
    rows = {}
    header = None
    for line in TSV.read_text(encoding='utf-8').splitlines():
        fs = line.split('\t')
        if header is None:
            header = fs
            continue
        rows[fs[0]] = dict(zip(header, fs))
    return rows


def gold_evidences(q_data: dict, gids: set, gexact: set):
    """金标卡判定:卡任一产物 product_identity ∈ 金标 cn 集或 product_smiles
    精确串 ∈ 金标串集(与 FULL_SURFACE §2 / M1 同判据)。返回金标证据列表。"""
    out = []
    for t in q_data['tasks']:
        for e in t['evidences']:
            hit = any(
                (p.get('product_identity') in gids)
                or (p.get('product_smiles') in gexact)
                for p in e.get('products') or []
            )
            if hit:
                out.append(e)
    return out


def source_tier(e: dict) -> int:
    if e.get('kind') == 'recorded_reaction':
        return 4
    src = e.get('source_id') or ''
    if 'uspto' in src:
        return 3
    if 'envipath' in src:
        return 2
    return 1


def channel(e: dict) -> str:
    src = e.get('source_id') or ''
    parts = [p for p in ('uspto', 'envipath', 'retrieval') if p in src]
    if e.get('kind') == 'recorded_reaction':
        return 'recorded'
    return '+'.join(parts) if parts else 'other'


# ---------------------------------------------------------------- measurement
def run(dump_dir: Path):
    gold = load_gold()
    subs = load_questions()
    tsv = load_flags_tsv()
    dumps = {tag: json.loads((dump_dir / f'gate1_{tag}.json').read_text())
             for tag in BATCH_TAGS}

    # ---- 批间一致性:测量相关骨架(rank/score/产物身份;evidence_id 与 run/配置
    # 家族绑定不比) + 金标位次
    def skeleton(d):
        return {qid: [(e['retrieval_rank'], e.get('score'),
                       tuple(p.get('product_identity') for p in e.get('products') or []))
                      for t in q['tasks'] for e in t['evidences']]
                for qid, q in d.items()}
    ref_skel = skeleton(dumps[REF_BATCH])
    batch_invariance = {tag: skeleton(dumps[tag]) == ref_skel
                        for tag in BATCH_TAGS}
    # 金标位次批间稳定性(测量结论的直接口径;2 题采样抖动题单独核)
    def gold_ranks_by_batch(d):
        out = {}
        for qid in sorted(gold):
            g = gold[qid]
            gids, gex = g['gold_ids'], set(g['products_smiles'])
            out[qid] = sorted(e['retrieval_rank']
                              for t in d[qid]['tasks'] for e in t['evidences']
                              if any((p.get('product_identity') in gids)
                                     or (p.get('product_smiles') in gex)
                                     for p in e.get('products') or []))
        return out
    ref_gr = gold_ranks_by_batch(dumps[REF_BATCH])
    gold_rank_invariance = {tag: gold_ranks_by_batch(dumps[tag]) == ref_gr
                            for tag in BATCH_TAGS}
    jitter_qids = [qid for qid, sk in ref_skel.items()
                   if any(skeleton(dumps[t]).get(qid) != sk for t in BATCH_TAGS)]

    rows = []
    mono_pairs = mono_viol = 0
    sig_corr_s1, sig_corr_s2b, sig_corr_s3 = [], [], []
    engine_score_is_order = None  # 见 summary:引擎序 ≈ 卡总分序的证据

    for qid in sorted(gold):
        g = gold[qid]
        gids, gexact = g['gold_ids'], set(g['products_smiles'])
        qd = dumps[REF_BATCH][qid]
        assert len(qd['tasks']) == 1, f'{qid}: expect single root retrieval task'
        evs = list(qd['tasks'][0]['evidences'])
        evs.sort(key=lambda e: e['retrieval_rank'])
        ranks = [e['retrieval_rank'] for e in evs]
        assert ranks == list(range(1, len(evs) + 1)), f'{qid}: ranks not 1..N'

        sub_fp = cn_fp(subs.get(qid))

        # ---- 信号值(全卡)
        s1v, s2av, s2bv, s3v = [], [], [], []
        n_donor_backed = 0
        for e in evs:
            s1v.append(donor_s1(e, sub_fp))
            if donor_smiles(e) is not None:
                n_donor_backed += 1
            s2av.append(source_tier(e))
            s2bv.append(round(float((e.get('engine_edge') or {}).get('p_uspto') or 0.0), 6))
            s3v.append(round(tanimoto(product_fp(e.get('products') or []), sub_fp), 6))

        # 引擎分序单调性(排除合并去重追加的尾卡)
        pool = [e for e in evs if not e.get('deduped')]
        for i in range(len(pool) - 1):
            mono_pairs += 1
            if (pool[i].get('score') or 0) < (pool[i + 1].get('score') or 0):
                mono_viol += 1

        for v, acc in ((s1v, sig_corr_s1), (s2bv, sig_corr_s2b), (s3v, sig_corr_s3)):
            sp = spearman(v, ranks)
            if sp is not None:
                acc.append(sp)

        # ---- 金标卡(检索产物口径,主口径)
        gold_evs = gold_evidences(qd, gids, gexact)
        # 审计口径(cardval verdicts,C0-b)
        cv_in_pool = any(
            any((v.get('product_identity') in gids)
                or (v.get('product_smiles') in gexact)
                for v in c.get('verdicts') or [])
            for c in qd['cardvals'].values())

        def best_rank(sortkey):
            """全局重排:按 sortkey 升序(信号大者在前)。"""
            if not gold_evs:
                return None
            order = sorted(range(len(evs)), key=sortkey)
            pos = {i: p + 1 for p, i in enumerate(order)}
            return min(pos[evs.index(ge)] for ge in gold_evs)

        def hybrid_rank(sortkey):
            """选择性召回形态:引擎顶 K_ENGINE_TOP 位原序保留,其余深位卡按
            信号降序补位(teacher 先决 2 的部署形态,非全局重排)。"""
            if not gold_evs:
                return None
            top = [i for i in range(len(evs)) if evs[i]['retrieval_rank'] <= K_ENGINE_TOP]
            rest = [i for i in range(len(evs)) if evs[i]['retrieval_rank'] > K_ENGINE_TOP]
            rest.sort(key=sortkey)
            pos = {i: p + 1 for p, i in enumerate(top + rest)}
            return min(pos[evs.index(ge)] for ge in gold_evs)

        rk = evs.index  # 局部速查(复合键排序用)

        def desc(sig):  # 单调信号降序,引擎位次破平
            return lambda i: (-sig(i), evs[i]['retrieval_rank'])

        eng_rank = min((e['retrieval_rank'] for e in gold_evs), default=None)
        r_s1 = best_rank(desc(lambda i: s1v[i]))
        r_s2a = best_rank(desc(lambda i: s2av[i]))
        r_s2b = best_rank(desc(lambda i: s2bv[i]))
        r_s3 = best_rank(desc(lambda i: s3v[i]))
        # 复合信号 S4:来源强度层内按 S3(变换幅度)排序(可部署,零金标)
        r_s4 = best_rank(lambda i: (-s2av[i], -s3v[i], evs[i]['retrieval_rank']))
        h_s1 = hybrid_rank(desc(lambda i: s1v[i]))
        h_s2a = hybrid_rank(desc(lambda i: s2av[i]))
        h_s2b = hybrid_rank(desc(lambda i: s2bv[i]))
        h_s3 = hybrid_rank(desc(lambda i: s3v[i]))
        h_s4 = hybrid_rank(lambda i: (-s2av[i], -s3v[i], evs[i]['retrieval_rank']))

        # 模拟检索(供体)通道内部:仅 analog 卡按 S1 重排的通道内位次
        analog_idx = [i for i, e in enumerate(evs)
                      if e.get('kind') == 'analog_reaction']
        r_s1_analog = None
        if gold_evs:
            analog_order = sorted(analog_idx,
                                  key=lambda i: (-s1v[i], evs[i]['retrieval_rank']))
            apos = {i: p + 1 for p, i in enumerate(analog_order)}
            r_s1_analog = min(
                (apos[i] for i, e in enumerate(evs)
                 if e in gold_evs and i in apos), default=None)

        t = tsv.get(qid, {})
        in22 = (t.get('gold_in_pool') == 'true' and t.get('hit5_whole') == 'false')
        gold_channels = sorted({channel(e) for e in gold_evs})
        rows.append({
            'qid': qid,
            'route': t.get('route', ''),
            'n_evidences': len(evs),
            'n_analog': len(analog_idx),
            'n_rule': sum(1 for e in evs if e.get('kind') == 'rule_application'),
            'n_recorded': sum(1 for e in evs if e.get('kind') == 'recorded_reaction'),
            'n_donor_backed': n_donor_backed,
            'gold_in_pool_retrieval': bool(gold_evs),
            'gold_in_pool_cardval': bool(cv_in_pool),
            'tsv_gold_in_pool': t.get('gold_in_pool'),
            'in_22_list': in22,
            'bucket': t.get('bucket', ''),
            'n_gold_cards': len(gold_evs),
            'gold_engine_rank': eng_rank,
            'gold_rank_s1': r_s1,
            'gold_rank_s1_analog_local': r_s1_analog,
            'gold_rank_s2a_tier': r_s2a,
            'gold_rank_s2b_puspto': r_s2b,
            'gold_rank_s3_prodsub': r_s3,
            'gold_rank_s4_composite': r_s4,
            'gold_rank_hybrid_s1': h_s1,
            'gold_rank_hybrid_s2a_tier': h_s2a,
            'gold_rank_hybrid_s2b_puspto': h_s2b,
            'gold_rank_hybrid_s3_prodsub': h_s3,
            'gold_rank_hybrid_s4_composite': h_s4,
            'gold_channels': gold_channels,
        })

    # ---- 汇总
    in_pool = [r for r in rows if r['gold_in_pool_retrieval']]
    list22 = [r for r in rows if r['in_22_list']]

    def recall(subset, key, k):
        return sum(1 for r in subset
                   if r[key] is not None and r[key] <= k)

    def rank_dist(subset, key):
        ds = sorted((r[key] for r in subset if r[key] is not None))
        buckets = {'1-8': 0, '9-16': 0, '17-24': 0, '25-32': 0,
                   '33-64': 0, '65+': 0, 'none': 0}
        for v in ds:
            if v <= 8:
                buckets['1-8'] += 1
            elif v <= 16:
                buckets['9-16'] += 1
            elif v <= 24:
                buckets['17-24'] += 1
            elif v <= 32:
                buckets['25-32'] += 1
            elif v <= 64:
                buckets['33-64'] += 1
            else:
                buckets['65+'] += 1
        buckets['none'] = sum(1 for r in subset if r[key] is None)
        return buckets

    keys = {
        'engine': 'gold_engine_rank',
        's1_donor_substrate': 'gold_rank_s1',
        's1_analog_local': 'gold_rank_s1_analog_local',
        's2a_source_tier': 'gold_rank_s2a_tier',
        's2b_puspto': 'gold_rank_s2b_puspto',
        's3_product_substrate': 'gold_rank_s3_prodsub',
        's4_composite_tier_x_s3': 'gold_rank_s4_composite',
        'hybrid_s1': 'gold_rank_hybrid_s1',
        'hybrid_s2a_tier': 'gold_rank_hybrid_s2a_tier',
        'hybrid_s2b_puspto': 'gold_rank_hybrid_s2b_puspto',
        'hybrid_s3_prodsub': 'gold_rank_hybrid_s3_prodsub',
        'hybrid_s4_composite': 'gold_rank_hybrid_s4_composite',
    }
    recall_tables = {}
    for name, key in keys.items():
        recall_tables[name] = {
            'all56': {f'K={k}': recall(rows, key, k) for k in K_GRID},
            'in_pool(37 retrieval-caliber)': {f'K={k}': recall(in_pool, key, k) for k in K_GRID},
            'list22': {f'K={k}': recall(list22, key, k) for k in K_GRID},
            'rank_dist_list22': rank_dist(list22, key),
            'rank_dist_in_pool': rank_dist(in_pool, key),
        }

    # 逐题最优信号上界(oracle):仅在测量侧逐题取各可部署信号的最小位次,
    # 用于刻画信号族的可及上界——**用金标标签选信号,不可部署**,只作解读。
    deployable = ['gold_rank_s2a_tier', 'gold_rank_s2b_puspto',
                  'gold_rank_s3_prodsub', 'gold_rank_s4_composite',
                  'gold_rank_hybrid_s2a_tier', 'gold_rank_hybrid_s2b_puspto',
                  'gold_rank_hybrid_s3_prodsub', 'gold_rank_hybrid_s4_composite']
    oracle = {}
    for r in rows:
        vals = [r[k] for k in deployable if r[k] is not None]
        oracle[r['qid']] = min(vals) if vals else None

    def recall_o(subset, k):
        return sum(1 for r in subset if oracle[r['qid']] is not None
                   and oracle[r['qid']] <= k)

    recall_tables['oracle_best_of_deployable(measurement-only)'] = {
        'all56': {f'K={k}': recall_o(rows, k) for k in K_GRID},
        'in_pool(37 retrieval-caliber)': {f'K={k}': recall_o(in_pool, k) for k in K_GRID},
        'list22': {f'K={k}': recall_o(list22, k) for k in K_GRID},
        'note': '逐题取可部署信号最小位次(用金标标签选信号,不可部署,只作上界解读)',
    }

    # 22 题的桶切(C1=真丢弃 16 / B=口径假丢弃 6,见 COVERAGE_STAT M1 §1.4)
    c1 = [r for r in list22 if r['bucket'] == 'C1_pool_but_missed']
    bb = [r for r in list22 if r['bucket'] == 'B_component_rescuable']
    bucket_cut = {}
    for name, key in keys.items():
        bucket_cut[name] = {
            'C1_true_dropped(16)': {f'K={k}': recall(c1, key, k) for k in K_GRID},
            'B_caliber_rescuable(6)': {f'K={k}': recall(bb, key, k) for k in K_GRID},
        }
    summary_bucket_cut = bucket_cut

    gains = {}
    for name, key in keys.items():
        if name == 'engine':
            continue
        gains[name] = {}
        for k in K_GRID:
            g_up = [r['qid'] for r in list22
                    if r[key] is not None and r[key] <= k
                    and (r['gold_engine_rank'] is None or r['gold_engine_rank'] > k)]
            g_dn = [r['qid'] for r in rows
                    if r['gold_engine_rank'] is not None and r['gold_engine_rank'] <= k
                    and (r[key] is None or r[key] > k)]
            gains[name][f'K={k}'] = {
                'list22_gained': len(g_up), 'list22_gained_qids': g_up,
                'all56_lost_from_topK': len(g_dn), 'all56_lost_qids': g_dn,
            }

    # rank75 核验(FULL_SURFACE §2 抽样复核案例)
    q75 = next(r for r in rows if r['qid'].endswith('005__S01__BSY-r00480'))
    rank75_check = {
        'qid': q75['qid'],
        'in_22_list': q75['in_22_list'],
        'gold_engine_rank': q75['gold_engine_rank'],
        'expected_rank': 75,
        'match': q75['gold_engine_rank'] == 75,
        'gold_channels': q75['gold_channels'],
    }

    # ---- 信号 vs 引擎原序 的逐题符号检验(判定线显著性依据;精确二项两侧)
    import math

    def sign_test(key, k, subset):
        b01 = b10 = 0
        for r in subset:
            e = r['gold_engine_rank'] is not None and r['gold_engine_rank'] <= k
            s = r[key] is not None and r[key] <= k
            if s and not e:
                b01 += 1
            elif e and not s:
                b10 += 1
        n = b01 + b10
        if n == 0:
            p = 1.0
        else:
            p = min(1.0, 2.0 * sum(math.comb(n, i)
                                   for i in range(0, min(b01, b10) + 1)) / 2 ** n)
        return {'signal_in_engine_out': b01, 'engine_in_signal_out': b10,
                'sign_p_two_sided': round(p, 4)}

    sign_tests = {}
    for name, key in keys.items():
        if name == 'engine':
            continue
        sign_tests[name] = {f'K={k}': {'list22': sign_test(key, k, list22),
                                       'in_pool37': sign_test(key, k, in_pool)}
                            for k in K_GRID}

    summary = {
        'schema_version': 'gate1-recall-1',
        'caliber': {
            'denominator': 'dev 56(口径 v3 分母;quarantine 5 题待人审未生效,维持 56)',
            'gold_card': '证据卡任一产物 product_identity ∈ 金标 cn 或精确串(整串,与 FULL_SURFACE §2/M1 同判据)',
            'engine_order': 'retrieval_rank(引擎 merged 池 1 起始位次;含深位)',
            'reference_batch': REF_BATCH,
            'list22_source': 'qid_flags_C0b.tsv gold_in_pool & !hit5_whole(审计 2x2 的 22 题口径假+真丢弃合集)',
        },
        'batch_invariance': batch_invariance,
        'gold_rank_batch_invariance': gold_rank_invariance,
        'retrieval_jitter_qids': jitter_qids,
        'retrieval_jitter_note': (
            '53/56 题六批检索骨架(位次/分数/产物身份)完全一致;3 题深位采样'
            '抖动(见 jitter_qids),但金标卡位次六批全部一致,测量结论批间稳定'),
        'n_questions': len(rows),
        'n_in_pool_retrieval': len(in_pool),
        'n_in_pool_cardval': sum(1 for r in rows if r['gold_in_pool_cardval']),
        'n_list22': len(list22),
        'engine_score_vs_rank': {
            'adjacent_pairs': mono_pairs, 'monotonicity_violations': mono_viol,
            'violation_rate': round(mono_viol / mono_pairs, 6),
            'note': '引擎原序 ≈ 卡总分序(edge_score);按总分重排不是独立信号',
        },
        'signal_engine_spearman_mean': {
            's1_donor_substrate': round(sum(sig_corr_s1) / len(sig_corr_s1), 4),
            's2b_puspto': round(sum(sig_corr_s2b) / len(sig_corr_s2b), 4),
            's3_product_substrate': round(sum(sig_corr_s3) / len(sig_corr_s3), 4),
        },
        'k_engine_top': K_ENGINE_TOP,
        'engine_context': {
            'recall_K8': {
                'all56': recall(rows, 'gold_engine_rank', 8),
                'in_pool': recall(in_pool, 'gold_engine_rank', 8),
                'list22': recall(list22, 'gold_engine_rank', 8),
            },
            'note': 'K=8 为现产 rank 任务合格卡窗(参照行,非门 1 三档)',
        },
        'recall': recall_tables,
        'recall_list22_by_bucket': summary_bucket_cut,
        'sign_tests_vs_engine': sign_tests,
        'gains_vs_engine': gains,
        'rank75_case': rank75_check,
    }
    return rows, summary


# ---------------------------------------------------------------- io / check
def write_outputs(rows, summary, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'gate1_measurements.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=False),
        encoding='utf-8')
    (out_dir / 'gate1_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=False),
        encoding='utf-8')
    cols = ['qid', 'route', 'bucket', 'in_22_list', 'n_evidences',
            'gold_in_pool_retrieval', 'gold_in_pool_cardval', 'n_gold_cards',
            'gold_channels',
            'gold_engine_rank', 'gold_rank_s1', 'gold_rank_s1_analog_local',
            'gold_rank_s2a_tier', 'gold_rank_s2b_puspto', 'gold_rank_s3_prodsub',
            'gold_rank_s4_composite',
            'gold_rank_hybrid_s1', 'gold_rank_hybrid_s2a_tier',
            'gold_rank_hybrid_s2b_puspto', 'gold_rank_hybrid_s3_prodsub',
            'gold_rank_hybrid_s4_composite']
    with (out_dir / 'gold_depth_22.tsv').open('w', encoding='utf-8') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            if r['in_22_list']:
                f.write('\t'.join(str(r.get(c, '')) for c in cols) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump-dir', default=str(HERE / 'raw_dumps'))
    ap.add_argument('--out-dir', default=str(HERE / 'sealed'))
    ap.add_argument('--check', action='store_true',
                    help='复算并与 sealed/ 封存件逐数对拍')
    args = ap.parse_args()

    import os
    os.environ.setdefault('OMP_NUM_THREADS', '1')

    rows, summary = run(Path(args.dump_dir))
    out_dir = Path(args.out_dir)

    if args.check:
        ok = True
        for fn, fresh in (('gate1_measurements.json', rows),
                          ('gate1_summary.json', summary)):
            path = out_dir / fn
            if not path.exists():
                print(f'CHECK FAIL: {fn} missing')
                ok = False
                continue
            sealed = json.loads(path.read_text(encoding='utf-8'))
            if sealed == fresh:
                print(f'CHECK PASS: {fn} ({len(json.dumps(fresh))} bytes identical)')
            else:
                print(f'CHECK FAIL: {fn} differs')
                ok = False
        sys.exit(0 if ok else 1)

    write_outputs(rows, summary, out_dir)
    # 摘要速览
    print('n_questions:', summary['n_questions'],
          'in_pool(retrieval):', summary['n_in_pool_retrieval'],
          'in_pool(cardval):', summary['n_in_pool_cardval'],
          'list22:', summary['n_list22'])
    print('batch_invariance:', summary['batch_invariance'])
    for name in summary['recall']:
        t = summary['recall'][name]
        print(f"{name}: list22 K16/24/32 = "
              f"{t['list22']['K=16']}/{t['list22']['K=24']}/{t['list22']['K=32']}"
              f"  all56 = {t['all56']['K=16']}/{t['all56']['K=24']}/{t['all56']['K=32']}")
    print('rank75_case:', summary['rank75_case'])


if __name__ == '__main__':
    main()
