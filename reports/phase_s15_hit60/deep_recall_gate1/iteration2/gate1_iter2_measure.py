#!/usr/bin/env python3
"""HIT60 T8 门 1 迭代 2 — 新信号测量(零 LLM;金标仅在本离线进程只读)。

失败分支(门 1 预判不过 → 纯检索优化)的复测:在 raw_dumps 同一封存 dump
(C0-b 参照批)上重算升级信号(gate1 同口径),与基线对照。

加载与判定函数复用 gate1_measure.py(gold_evidences/load_gold/load_questions/
load_flags_tsv/source_tier/spearman/K_GRID);新信号函数在 signals2.py。
sign_test 为 gate1_measure.run 内嵌函数的同款复制(精确二项两侧)。

流程:
  1. 复算基线(engine 序 + S3 Morgan)并与 sealed/ 逐数对拍(管线校验);
  2. 计算新信号(见 signals2.py docstring)的全局重排与 hybrid 形态
     (引擎顶 8 保留 + 信号补位)金标位次;
  3. 汇总:22 题/in-pool 37/全 56 三档召回、对引擎原序符号检验、
     C1/B 桶切、位次分布、oracle 上界(测量侧逐题最优,不可部署)、
     全 56 回撤护栏;附与基线(gate1 sealed)的对照块。

红线:输出件(sealed 目录,本脚本写 iteration2/sealed/)只含 qid/位次/
旗标/信号值,零 SMILES 零身份串;金标只在本地离线进程只读;封存远端产物
只读;不改 src/ 与 configs/;不碰 298;零 LLM 零 API。

用法(本地 conda depending43,OMP_NUM_THREADS=1):
  PYTHONPATH=src python reports/phase_s15_hit60/deep_recall_gate1/iteration2/gate1_iter2_measure.py
  ... --check   # 复算并与 iteration2/sealed/ 逐数对拍
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent           # .../deep_recall_gate1/iteration2
GATE1 = HERE.parent                              # .../deep_recall_gate1
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(GATE1))                   # 复用门 1 脚本
sys.path.insert(0, str(HERE))                    # 本迭代信号库

import gate1_measure as g1                        # noqa: E402  (加载与判定函数)
import signals2                                   # noqa: E402  (新信号函数)

# hybrid 形态集合(引擎顶 8 + 信号补位):主信号 + 敏感性子集
HYBRID_ORDERS = ('s3x', 's3x_add', 's3x_taut', 's3x_maccs', 's3x_max_fp',
                 's3_maccs', 's3_fcfp6', 's3_taut', 's3_max_fp',
                 'hC', 'hC_flat', 'filterA_s3x', 'filterB_s3x', 's2b_q')
# 部署族(oracle 统计口径:全部可部署新信号,零金标)
DEPLOYABLE_GLOBAL = ('s3_maccs', 's3_fcfp6', 's3_taut', 's3_max_fp',
                     's3x', 's3x_wo0', 's3x_wo1', 's3x_taut', 's3x_maccs',
                     's3x_max_fp', 's3x_add', 's2b_z', 's2b_q', 'hC', 'hC_flat',
                     'filterA_engine', 'filterA_s3x', 'filterA_s3x_add',
                     'filterB_s3x')


def sign_test(key_vals: list, eng_vals: list, k: int) -> dict:
    """与 gate1_measure.run.sign_test 同款(精确二项两侧)。"""
    b01 = b10 = 0
    for s, e in zip(key_vals, eng_vals):
        e_in = e is not None and e <= k
        s_in = s is not None and s <= k
        if s_in and not e_in:
            b01 += 1
        elif e_in and not s_in:
            b10 += 1
    n = b01 + b10
    if n == 0:
        p = 1.0
    else:
        p = min(1.0, 2.0 * sum(math.comb(n, i)
                               for i in range(0, min(b01, b10) + 1)) / 2 ** n)
    return {'signal_in_engine_out': b01, 'engine_in_signal_out': b10,
            'sign_p_two_sided': round(p, 4)}


def run(dump_dir: Path, sealed_g1: Path):
    gold = g1.load_gold()
    subs = g1.load_questions()
    tsv = g1.load_flags_tsv()
    dumps = {tag: json.loads((dump_dir / f'gate1_{tag}.json').read_text())
             for tag in g1.BATCH_TAGS}
    d = dumps[g1.REF_BATCH]

    # ---- 基线封存件(只读,用于对照与管线校验)
    sealed_rows = json.loads((sealed_g1 / 'gate1_measurements.json').read_text())
    sealed_by_qid = {r['qid']: r for r in sealed_rows}

    rows = []
    spearman_cons, spearman_s3x_add = [], []
    n_parse_fail = 0
    for qid in sorted(gold):
        g = gold[qid]
        gids, gexact = g['gold_ids'], set(g['products_smiles'])
        qd = d[qid]
        assert len(qd['tasks']) == 1, f'{qid}: expect single root retrieval task'
        evs = list(qd['tasks'][0]['evidences'])
        evs.sort(key=lambda e: e['retrieval_rank'])
        ranks = [e['retrieval_rank'] for e in evs]
        assert ranks == list(range(1, len(evs) + 1)), f'{qid}: ranks not 1..N'

        sub = signals2.mol_feat(subs.get(qid))
        feats = [signals2.card_features(e, sub) for e in evs]
        n_parse_fail += sum(1 for f in feats if not f['parse_ok'])

        gold_evs = g1.gold_evidences(qd, gids, gexact)
        gold_idx = {id(e) for e in gold_evs}
        gold_pos_engine = min((e['retrieval_rank'] for e in gold_evs), default=None)

        orders, extras = signals2.build_orders(evs, feats)

        # ---- 基线 S3 复算(管线校验用;= gate1 口径 Morgan 首产物)
        s3_base = [f['sim_morgan'] for f in feats]
        base_order = sorted(range(len(evs)),
                            key=lambda i: (-s3_base[i], evs[i]['retrieval_rank']))
        base_pos = {i: p + 1 for p, i in enumerate(base_order)}
        r_s3_base = min((base_pos[i] for i, e in enumerate(evs)
                         if id(e) in gold_idx), default=None)

        def rank_of(order):
            pos = {i: p + 1 for p, i in enumerate(
                sorted(range(len(evs)), key=order))}
            return min((pos[i] for i, e in enumerate(evs)
                        if id(e) in gold_idx), default=None)

        def rank_of_hybrid(order):
            pos = signals2.hybrid_order(evs, order, g1.K_ENGINE_TOP)
            return min((pos[i] for i, e in enumerate(evs)
                        if id(e) in gold_idx), default=None)

        ranks_global = {name: rank_of(o) for name, o in orders.items()
                        if name in DEPLOYABLE_GLOBAL}
        ranks_hybrid = {name: rank_of_hybrid(orders[name])
                        for name in HYBRID_ORDERS}

        # 管线校验:engine 序与基线 S3 位次须与门 1 封存件逐数一致
        sr = sealed_by_qid[qid]
        assert sr['gold_engine_rank'] == gold_pos_engine, \
            f'{qid}: engine rank drift ({sr["gold_engine_rank"]} vs {gold_pos_engine})'
        assert sr['gold_rank_s3_prodsub'] == r_s3_base, \
            f'{qid}: baseline S3 drift ({sr["gold_rank_s3_prodsub"]} vs {r_s3_base})'

        # 信号独立性(对引擎位次的 Spearman)
        cons = [signals2.cons_penalty(f) for f in feats]
        s3x_add = [f['sim_morgan'] - c for f, c in zip(feats, cons)]
        for v, acc in ((cons, spearman_cons), (s3x_add, spearman_s3x_add)):
            sp = g1.spearman(v, ranks)
            if sp is not None:
                acc.append(sp)

        t = tsv.get(qid, {})
        in22 = (t.get('gold_in_pool') == 'true' and t.get('hit5_whole') == 'false')
        gold_channels = sorted({g1.channel(e) for e in gold_evs})
        gold_cons = [signals2.cons_penalty(f) for f, e in zip(feats, evs)
                     if id(e) in gold_idx]
        row = {
            'qid': qid, 'route': t.get('route', ''), 'bucket': t.get('bucket', ''),
            'n_evidences': len(evs), 'in_22_list': in22,
            'gold_in_pool_retrieval': bool(gold_evs),
            'n_gold_cards': len(gold_evs), 'gold_channels': gold_channels,
            'gold_engine_rank': gold_pos_engine,
            'gold_rank_s3_baseline': r_s3_base,
            'gold_cons_penalty_min': min(gold_cons) if gold_cons else None,
            'gold_dC': [f['dC'] for f, e in zip(feats, evs)
                        if id(e) in gold_idx] or None,
            'gold_dO': [f['dO'] for f, e in zip(feats, evs)
                        if id(e) in gold_idx] or None,
        }
        for name in DEPLOYABLE_GLOBAL:
            row[f'rank_{name}'] = ranks_global.get(name)
        for name in HYBRID_ORDERS:
            row[f'rank_hybrid_{name}'] = ranks_hybrid.get(name)
        # 守恒硬过滤对金标卡的存活性(filterA)
        gold_pass_a = [0 if f['dC'] in (0, -1, -2) and f['dN'] == 0
                       and f['dS'] == 0 and f['dP'] == 0 and f['dX'] == 0 else 1
                       for f, e in zip(feats, evs) if id(e) in gold_idx]
        row['gold_filterA_killed'] = min(gold_pass_a) if gold_pass_a else None
        rows.append(row)

    # ---- 汇总
    in_pool = [r for r in rows if r['gold_in_pool_retrieval']]
    list22 = [r for r in rows if r['in_22_list']]
    c1 = [r for r in list22 if r['bucket'] == 'C1_pool_but_missed']
    bb = [r for r in list22 if r['bucket'] == 'B_component_rescuable']

    all_keys = ([f'rank_{n}' for n in DEPLOYABLE_GLOBAL]
                + [f'rank_hybrid_{n}' for n in HYBRID_ORDERS])

    def recall(subset, key, k):
        return sum(1 for r in subset if r.get(key) is not None and r[key] <= k)

    def eng_of(r):
        return r['gold_engine_rank']

    recall_tables, sign_tests, guard = {}, {}, {}
    for key in all_keys:
        name = key.replace('rank_', '').replace('rank_hybrid_', 'hybrid_')
        recall_tables[name] = {
            'list22': {f'K={k}': recall(list22, key, k) for k in g1.K_GRID},
            'in_pool(37 retrieval-caliber)': {
                f'K={k}': recall(in_pool, key, k) for k in g1.K_GRID},
            'all56': {f'K={k}': recall(rows, key, k) for k in g1.K_GRID},
            'C1_true_dropped(16)': {
                f'K={k}': recall(c1, key, k) for k in g1.K_GRID},
            'B_caliber_rescuable(6)': {
                f'K={k}': recall(bb, key, k) for k in g1.K_GRID},
        }
        sign_tests[name] = {
            f'K={k}': {
                'list22': sign_test([r.get(key) for r in list22],
                                    [eng_of(r) for r in list22], k),
                'in_pool37': sign_test([r.get(key) for r in in_pool],
                                       [eng_of(r) for r in in_pool], k),
            } for k in g1.K_GRID}
        guard[name] = {
            f'K={k}': {
                'all56_vs_engine': recall(rows, key, k)
                - recall(rows, 'gold_engine_rank', k),
                'list22_gained_qids': [r['qid'] for r in list22
                                       if r.get(key) is not None and r[key] <= k
                                       and (eng_of(r) is None or eng_of(r) > k)],
                'all56_lost_qids': [r['qid'] for r in rows
                                    if eng_of(r) is not None and eng_of(r) <= k
                                    and (r.get(key) is None or r[key] > k)],
            } for k in g1.K_GRID}

    # oracle:测量侧逐题取可部署新信号最小位次(不可部署,仅上界)
    oracle = {r['qid']: min((r[k] for k in all_keys if r.get(k) is not None),
                            default=None) for r in rows}
    recall_tables['oracle_iter2_family(measurement-only)'] = {
        'list22': {f'K={k}': sum(1 for r in list22
                                 if oracle[r['qid']] is not None
                                 and oracle[r['qid']] <= k) for k in g1.K_GRID},
        'in_pool(37 retrieval-caliber)': {
            f'K={k}': sum(1 for r in in_pool if oracle[r['qid']] is not None
                          and oracle[r['qid']] <= k) for k in g1.K_GRID},
        'all56': {f'K={k}': sum(1 for r in rows if oracle[r['qid']] is not None
                                and oracle[r['qid']] <= k) for k in g1.K_GRID},
        'note': '逐题取本迭代全部可部署新信号最小位次(用金标标签选信号,'
                '不可部署,只作上界解读;口径与门 1 oracle 同,族更宽)',
    }

    # ---- 基线对照块(读门 1 封存 summary,只读)
    g1_summary = json.loads((sealed_g1 / 'gate1_summary.json').read_text())
    baseline_recall = {name: g1_summary['recall'][name]['list22']
                       for name in ('engine', 's2a_source_tier', 's2b_puspto',
                                    's3_product_substrate', 's4_composite_tier_x_s3',
                                    'hybrid_s2a_tier', 'hybrid_s2b_puspto',
                                    'hybrid_s3_prodsub', 'hybrid_s4_composite')}
    baseline_sign = {name: {f'K={k}':
                            g1_summary['sign_tests_vs_engine'][name]
                            [f'K={k}']['list22']
                            for k in g1.K_GRID} for name in
                     ('s2a_source_tier', 's2b_puspto', 's3_product_substrate',
                      'hybrid_s2a_tier', 'hybrid_s2b_puspto',
                      'hybrid_s3_prodsub')}

    summary = {
        'schema_version': 'gate1-iter2-recall-1',
        'caliber': g1_summary['caliber'],
        'reference_batch': g1.REF_BATCH,
        'signal_defs': '见 iteration2/signals2.py docstring(预声明主口径 s3x:'
                       'cons 升序 + Morgan 子序;权重 W_C/N/S/P/X/O=1/2/2/2/3/0.25,'
                       '化学先验定,未在 dev 调参;其余为敏感性变体)',
        'multiplicity_note': (
            '本迭代为信号族测量(17 全局 + 12 hybrid 形态);「任一配置过线」的'
            '判定含多重比较风险,须结合预声明主口径 s3x/hybrid_s3x 解读'),
        'n_questions': len(rows),
        'n_list22': len(list22),
        'n_parse_fail_cards': n_parse_fail,
        'baseline_reproduction': {
            'engine_rank_and_s3_rank_vs_sealed': 'PASS(assert 逐题相等)',
            'baseline_list22_recall': baseline_recall,
            'baseline_sign_p_list22': baseline_sign,
        },
        'signal_engine_spearman_mean': {
            'cons_penalty': round(sum(spearman_cons) / len(spearman_cons), 4),
            's3x_additive': round(sum(spearman_s3x_add)
                                  / len(spearman_s3x_add), 4),
        },
        'recall': recall_tables,
        'sign_tests_vs_engine': sign_tests,
        'guardrails': guard,
    }
    return rows, summary


def write_outputs(rows, summary, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'iter2_measurements.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=False),
        encoding='utf-8')
    (out_dir / 'iter2_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=False),
        encoding='utf-8')
    # 22 题逐题位次表(引擎/基线/新信号主口径 + 过滤存活性)
    cols = ['qid', 'bucket', 'n_evidences', 'gold_engine_rank',
            'gold_rank_s3_baseline', 'gold_cons_penalty_min', 'gold_dC',
            'gold_dO', 'gold_filterA_killed', 'gold_channels',
            'rank_s3x', 'rank_s3x_add', 'rank_s3x_taut', 'rank_s3_maccs',
            'rank_s3_max_fp', 'rank_hC', 'rank_hC_flat', 'rank_filterA_s3x',
            'rank_filterB_s3x', 'rank_s2b_q', 'rank_hybrid_s3x',
            'rank_hybrid_s3x_add', 'rank_hybrid_s3x_taut', 'rank_hybrid_hC',
            'rank_hybrid_hC_flat', 'rank_hybrid_filterA_s3x',
            'rank_hybrid_filterB_s3x', 'rank_hybrid_s2b_q',
            'rank_hybrid_s3_maccs', 'rank_hybrid_s3_max_fp']
    with (out_dir / 'iter2_gold_depth_22.tsv').open('w', encoding='utf-8') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            if r['in_22_list']:
                f.write('\t'.join(str(r.get(c, '')) for c in cols) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump-dir', default=str(GATE1 / 'raw_dumps'))
    ap.add_argument('--sealed-g1', default=str(GATE1 / 'sealed'))
    ap.add_argument('--out-dir', default=str(HERE / 'sealed'))
    ap.add_argument('--check', action='store_true',
                    help='复算并与 iteration2/sealed/ 封存件逐数对拍')
    args = ap.parse_args()

    import os
    os.environ.setdefault('OMP_NUM_THREADS', '1')

    rows, summary = run(Path(args.dump_dir), Path(args.sealed_g1))
    out_dir = Path(args.out_dir)

    if args.check:
        ok = True
        for fn, fresh in (('iter2_measurements.json', rows),
                          ('iter2_summary.json', summary)):
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
    print('n_questions:', summary['n_questions'], 'list22:', summary['n_list22'])
    print('baseline reproduction:', summary['baseline_reproduction']
          ['engine_rank_and_s3_rank_vs_sealed'])
    for name in ('s3x', 's3x_add', 's3x_taut', 's3x_maccs', 's3x_max_fp',
                 's3_maccs', 's3_fcfp6', 's3_taut', 's3_max_fp',
                 's2b_z', 's2b_q', 'hC', 'hC_flat', 'filterA_engine',
                 'filterA_s3x', 'filterB_s3x',
                 'hybrid_s3x', 'hybrid_s3x_add', 'hybrid_s3x_max_fp',
                 'hybrid_hC', 'hybrid_hC_flat',
                 'hybrid_filterA_s3x', 'hybrid_s2b_q',
                 'oracle_iter2_family(measurement-only)'):
        t = summary['recall'][name]
        sp = summary['sign_tests_vs_engine'].get(name, {})
        p16 = sp.get('K=16', {}).get('list22', {}).get('sign_p_two_sided', '—')
        p32 = sp.get('K=32', {}).get('list22', {}).get('sign_p_two_sided', '—')
        print(f"{name}: list22 K16/24/32 = "
              f"{t['list22']['K=16']}/{t['list22']['K=24']}/{t['list22']['K=32']}"
              f"  all56 = {t['all56']['K=16']}/{t['all56']['K=24']}/"
              f"{t['all56']['K=32']}  p(list22,K16/32) = {p16}/{p32}")


if __name__ == '__main__':
    main()
