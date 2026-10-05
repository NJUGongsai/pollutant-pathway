#!/usr/bin/env python3
"""HIT60 T8 门 1 迭代 2 — 纯检索信号升级(零 LLM、零金标信息、离线)。

失败分支(teacher 预声明:门 1 不过 → 退纯检索优化)的信号函数库。
在 raw_dumps 同一封存 dump 上重算;不改 src/ 与 configs/。

信号族(全部逐卡、确定性、零金标零 LLM):
  特征层(features per card,均相对题面底物,输入先过 cn_identity):
    sim_morgan   Morgan r2/2048/立体盲 Tanimoto(=基线 S3 口径,v43-rsim-1)
    sim_maccs    MACCS 166-bit Tanimoto
    sim_fcfp6    Morgan r3/2048/useFeatures(FCFP6)Tanimoto
    sim_taut     互变异构规范化(TautomerEnumerator.Canonicalize)后的 Morgan r2 Tanimoto
    dC/dN/dO/dS/dP/dX   分子式元素计数差(产物 − 底物;X=卤素)
    dRing/dHeavy/dBond/dDouble/dArom   环数/重原子数/键数/双键数/芳环数差
  守恒罚分(mimo 守恒判据连续化;权重化学先验,未在 dev 上调):
    cons = |dC| + 2|dN| + 2|dS| + 2|dP| + 3|dX| + W_O*|dO|
    W_O 主口径 0.25(加/脱水、水解等 O 变动常见且良性;变体 0/1 作敏感性)
  排序层(见 build_order_* 函数;全部以「信号值降序,引擎位次破平」为骨架):
    s3x          (cons 罚分升序, sim_morgan 降序)——主复合信号(预声明)
    s3x_add      sim_morgan − cons(加法形态,敏感性)
    s3x_taut     (cons, sim_taut)(子序换互变规范指纹,敏感性)
    s3_maccs / s3_fcfp6 / s3_taut   单指纹(特征消融)
    s2b_z / s2b_q  p_uspto 的 USPTO 通道内 z-score / 分位数校准
    hC           通道感知复合:先判卡通道(recorded/uspto/envipath/retrieval),
                 通道内用各自有效信号(uspto→p_uspto 校准;envipath→p_envipath
                 校准;retrieval→s3x;recorded→顶),跨通道按统一分位数对齐
    filterA_*    守恒硬过滤(dC∈{0,-1,-2} 且 dN=dS=dP=dX=0,O 自由;
                 任务书预演变体,规则不冻结)后按信号排序,被剔除卡垫底
  hybrid 形态(hS3x/hC 等):引擎顶 8 位保留 + 信号补位(teacher 先决 2 形态)。

红线:本文件不 import 任何金标;输出数值不含 SMILES/身份串。
指纹/分子解析失败 → sim=0.0、元素差按 -99 记(排序垫底,如实可审计)。
"""
from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / 'src'))

from rdkit import Chem, DataStructs, RDLogger  # noqa: E402
from rdkit.Chem import rdMolDescriptors  # noqa: E402
from rdkit.Chem.MACCSkeys import GenMACCSKeys  # noqa: E402
from rdkit.Chem.MolStandardize import rdMolStandardize  # noqa: E402

RDLogger.DisableLog('rdApp.*')

from pathway_v43.domain.identity import cn_identity  # noqa: E402

# ---------------- 守恒罚分权重(预声明主口径;化学先验,未调参) ----------------
W_C, W_N, W_S, W_P, W_X = 1.0, 2.0, 2.0, 2.0, 3.0
W_O_MAIN = 0.25
HALO = ('F', 'Cl', 'Br', 'I')


# ---------------------------------------------------------------- molecule cache
class MolFeat:
    """cn_identity 归一后的分子级特征(按 SMILES 全局缓存)。"""

    __slots__ = ('ok', 'morgan', 'fcfp6', 'maccs', 'taut_morgan', 'elems', 'n_ring',
                 'n_heavy', 'n_bond', 'n_double', 'n_arom')


_MOL_CACHE: dict[str, MolFeat | None] = {}
_TE = rdMolStandardize.TautomerEnumerator()
_TE.SetMaxTautomers(1000)


def _formula_elems(m) -> Counter:
    return Counter(a.GetSymbol() for a in m.GetAtoms())


def _ring_count(m) -> int:
    ri = m.GetRingInfo()
    return len([r for r in ri.AtomRings() if len(r) >= 3])


def mol_feat(smiles: str | None) -> MolFeat | None:
    if not smiles:
        return None
    if smiles in _MOL_CACHE:
        return _MOL_CACHE[smiles]
    feat = None
    m = None
    for form in (cn_identity(smiles), smiles):
        if not form:
            continue
        m = Chem.MolFromSmiles(form)
        if m is not None:
            break
    if m is not None:
        feat = MolFeat()
        feat.ok = True
        feat.morgan = rdMolDescriptors.GetMorganFingerprintAsBitVect(
            m, radius=2, nBits=2048, useChirality=False)
        feat.fcfp6 = rdMolDescriptors.GetMorganFingerprintAsBitVect(
            m, radius=3, nBits=2048, useFeatures=True, useChirality=False)
        feat.maccs = GenMACCSKeys(m)
        try:
            tc = _TE.Canonicalize(m)
            feat.taut_morgan = rdMolDescriptors.GetMorganFingerprintAsBitVect(
                tc, radius=2, nBits=2048, useChirality=False)
        except Exception:
            feat.taut_morgan = None
        e = _formula_elems(m)
        feat.elems = e
        feat.n_ring = _ring_count(m)
        feat.n_heavy = m.GetNumAtoms()
        feat.n_bond = m.GetNumBonds()
        feat.n_double = sum(1 for b in m.GetBonds() if b.GetBondTypeAsDouble() == 2.0)
        feat.n_arom = sum(1 for b in m.GetBonds() if b.GetIsAromatic())
    _MOL_CACHE[smiles] = feat
    return feat


def tanimoto(a, b) -> float:
    if a is None or b is None:
        return 0.0
    return DataStructs.TanimotoSimilarity(a, b)


# ---------------------------------------------------------------- per-card features
def card_features(e: dict, sub: MolFeat | None) -> dict:
    """单卡特征(零金标)。e = evidence;sub = 题面底物 MolFeat。
    全部 12,321 卡均恰 1 产物(已核);产物键序 product_smiles →
    product_smiles_full → product_identity(与 gate1_measure.product_fp 同链,
    保证基线 S3 可复现对拍)。"""
    ps = None
    for p in e.get('products') or []:
        for k in ('product_smiles', 'product_smiles_full', 'product_identity'):
            if p.get(k):
                ps = p[k]
                break
        if ps:
            break
    p = mol_feat(ps)
    s = sub
    if p is None or s is None or not p.ok or not s.ok:
        return {
            'sim_morgan': 0.0, 'sim_maccs': 0.0, 'sim_fcfp6': 0.0, 'sim_taut': 0.0,
            'dC': -99, 'dN': 0, 'dO': 0, 'dS': 0, 'dP': 0, 'dX': 0,
            'dRing': 0, 'dHeavy': 0, 'dBond': 0, 'dDouble': 0, 'dArom': 0,
            'parse_ok': False,
        }
    pe, se = p.elems, s.elems
    dx = sum(pe.get(h, 0) - se.get(h, 0) for h in HALO)
    return {
        'sim_morgan': round(tanimoto(p.morgan, s.morgan), 6),
        'sim_maccs': round(tanimoto(p.maccs, s.maccs), 6),
        'sim_fcfp6': round(tanimoto(p.fcfp6, s.fcfp6), 6),
        'sim_taut': round(tanimoto(p.taut_morgan, s.taut_morgan), 6),
        'dC': pe.get('C', 0) - se.get('C', 0),
        'dN': pe.get('N', 0) - se.get('N', 0),
        'dO': pe.get('O', 0) - se.get('O', 0),
        'dS': pe.get('S', 0) - se.get('S', 0),
        'dP': pe.get('P', 0) - se.get('P', 0),
        'dX': dx,
        'dRing': p.n_ring - s.n_ring,
        'dHeavy': p.n_heavy - s.n_heavy,
        'dBond': p.n_bond - s.n_bond,
        'dDouble': p.n_double - s.n_double,
        'dArom': p.n_arom - s.n_arom,
        'parse_ok': True,
    }


def cons_penalty(f: dict, w_o: float = W_O_MAIN) -> float:
    """mimo 守恒判据连续化:元素级差绝对值加权和(不含键型;环与键型单记)。"""
    return round(abs(f['dC']) * W_C + abs(f['dN']) * W_N + abs(f['dS']) * W_S
                 + abs(f['dP']) * W_P + abs(f['dX']) * W_X + abs(f['dO']) * w_o, 6)


# ---------------------------------------------------------------- channel
def channel_of(e: dict) -> str:
    """卡通道(先决 3/门 1 报告 §3.3 通道结构同口径):
    recorded > analog 检索迁移 > uspto 模板 > envipath 规则 > other。"""
    if e.get('kind') == 'recorded_reaction':
        return 'recorded'
    if e.get('kind') == 'analog_reaction':
        return 'retrieval'
    src = e.get('source_id') or ''
    if 'uspto' in src:
        return 'uspto'
    if 'envipath' in src:
        return 'envipath'
    return 'other'


def channel_p(e: dict) -> tuple[str, float]:
    """卡通道与其通道模板分(uspto→p_uspto;envipath→p_envipath;
    retrieval→p_retrieval;recorded/other→0)。"""
    ch = channel_of(e)
    ee = e.get('engine_edge') or {}
    key = {'uspto': 'p_uspto', 'envipath': 'p_envipath',
           'retrieval': 'p_retrieval'}.get(ch)
    p = float(ee.get(key) or 0.0) if key else 0.0
    return ch, p


# ---------------------------------------------------------------- calibration
def zscore(vals: list[float]) -> list[float]:
    n = len(vals)
    if n == 0:
        return []
    mu = sum(vals) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / n)
    if sd < 1e-12:
        return [0.0] * n
    return [(v - mu) / sd for v in vals]


def quantile_desc(vals: list[float]) -> list[float]:
    """降序分位数:值最大者 1/n,次大 2/n …(与升序排序键兼容:越小越前)。"""
    n = len(vals)
    order = sorted(range(n), key=lambda i: -vals[i])
    q = [0.0] * n
    for pos, i in enumerate(order):
        q[i] = (pos + 1) / n
    return q


# ---------------------------------------------------------------- order builders
def build_orders(evs: list[dict], feats: list[dict]):
    """返回 {order_name: sortkey}。sortkey 为升序键(越小越前);
    所有键末位一律接引擎位次破平。evs 已按 retrieval_rank 升序。"""
    eng = [e['retrieval_rank'] for e in evs]
    cons = [cons_penalty(f) for f in feats]
    cons_w0 = [cons_penalty(f, w_o=0.0) for f in feats]
    cons_w1 = [cons_penalty(f, w_o=1.0) for f in feats]
    sim_m = [f['sim_morgan'] for f in feats]
    sim_mac = [f['sim_maccs'] for f in feats]
    sim_f = [f['sim_fcfp6'] for f in feats]
    sim_t = [f['sim_taut'] for f in feats]

    # 通道与通道模板分
    chs = [channel_of(e) for e in evs]
    ps = [float((e.get('engine_edge') or {}).get('p_uspto') or 0.0) for e in evs]
    pe_v = [float((e.get('engine_edge') or {}).get('p_envipath') or 0.0) for e in evs]
    pr_v = [float((e.get('engine_edge') or {}).get('p_retrieval') or 0.0) for e in evs]

    def key(sig):
        """信号值降序,引擎位次破平。"""
        return lambda i: (-sig(i), eng[i])

    def key_asc(sig):
        """罚分类信号升序,引擎位次破平。"""
        return lambda i: (sig(i), eng[i])

    orders: dict[str, callable] = {}

    # ---- 特征消融:单指纹(均与基线 S3 同位口径的升级变体)
    orders['s3_maccs'] = key(lambda i: sim_mac[i])
    orders['s3_fcfp6'] = key(lambda i: sim_f[i])
    orders['s3_taut'] = key(lambda i: sim_t[i])

    # ---- 主复合(预声明):cons 升序,sim_morgan 降序
    orders['s3x'] = key_asc(lambda i: (cons[i], -sim_m[i]))
    # 敏感性:O 权重 0 / 1;子序换 taut / maccs;加法形态
    orders['s3x_wo0'] = key_asc(lambda i: (cons_w0[i], -sim_m[i]))
    orders['s3x_wo1'] = key_asc(lambda i: (cons_w1[i], -sim_m[i]))
    orders['s3x_taut'] = key_asc(lambda i: (cons[i], -sim_t[i]))
    orders['s3x_maccs'] = key_asc(lambda i: (cons[i], -sim_mac[i]))
    orders['s3x_add'] = key(lambda i: sim_m[i] - cons[i])
    # 多视角相似度(max of Morgan/MACCS):任一指纹视角认为像即前置
    max_mm = [max(sim_m[i], sim_mac[i]) for i in range(len(evs))]
    orders['s3_max_fp'] = key(lambda i: max_mm[i])
    orders['s3x_max_fp'] = key_asc(lambda i: (cons[i], -max_mm[i]))

    # ---- S2b 通道内校准(uspto 通道内 z-score / 分位数;其余卡垫底按引擎序)
    us_idx = [i for i, c in enumerate(chs) if c == 'uspto']
    z_us = [0.0] * len(evs)
    q_us = [0.0] * len(evs)
    if us_idx:
        zs = zscore([ps[i] for i in us_idx])
        qs = quantile_desc([ps[i] for i in us_idx])
        for j, i in enumerate(us_idx):
            z_us[i] = zs[j]
            q_us[i] = qs[j]
    orders['s2b_z'] = key_asc(lambda i: (0 if chs[i] == 'uspto' else 1,
                                         -z_us[i]))
    orders['s2b_q'] = key_asc(lambda i: (0 if chs[i] == 'uspto' else 1,
                                         q_us[i]))

    # ---- hC 通道感知复合:通道内各自有效信号 → 通道内降序分位数 → 跨通道对齐
    # uspto: z(p_uspto);envipath: z(p_envipath);retrieval: s3x 复合分
    # (sim_m − cons,加法形态,越大越前);recorded 顶。
    retrieval_score = [sim_m[i] - cons[i] for i in range(len(evs))]
    intra = [0.0] * len(evs)  # 通道内归一分(0=通道最优)
    for ch in ('uspto', 'envipath', 'retrieval', 'recorded', 'other'):
        idx = [i for i, c in enumerate(chs) if c == ch]
        if not idx:
            continue
        if ch == 'uspto':
            sig = [ps[i] for i in idx]
        elif ch == 'envipath':
            sig = [pe_v[i] for i in idx]
        elif ch == 'retrieval':
            sig = [retrieval_score[i] for i in idx]
        else:  # recorded/other:引擎序
            sig = [-eng[i] for i in idx]
        qs = quantile_desc(sig)
        for j, i in enumerate(idx):
            intra[i] = qs[j]
    # 跨通道统一分位数对齐:recorded 通道整体前置(来源强度最高),其余按 intra
    ch_rank = {'recorded': 0, 'uspto': 1, 'envipath': 2, 'retrieval': 3, 'other': 4}
    orders['hC'] = key_asc(lambda i: (ch_rank[chs[i]], intra[i]))

    # ---- hC_v2:不前置 recorded,纯分位数对齐(敏感性)
    orders['hC_flat'] = key_asc(lambda i: intra[i])

    # ---- 守恒硬过滤(任务书预演变体,规则不冻结):
    # filterA:dC∈{0,-1,-2} 且 dN=dS=dP=dX=0(O 自由);被剔除卡垫底(引擎序)。
    def passes(i):
        f = feats[i]
        return (f['dC'] in (0, -1, -2) and f['dN'] == 0 and f['dS'] == 0
                and f['dP'] == 0 and f['dX'] == 0)

    flt = [0 if passes(i) else 1 for i in range(len(evs))]
    orders['filterA_engine'] = key_asc(lambda i: (flt[i],))  # 只过滤不重排
    orders['filterA_s3x'] = key_asc(lambda i: (flt[i], cons[i], -sim_m[i]))
    orders['filterA_s3x_add'] = key_asc(
        lambda i: (flt[i], -(sim_m[i] - cons[i])))

    # ---- filterB:紧变体(|dO| ≤ 4 另加约束,防 O 暴涨卡)
    def passes_b(i):
        f = feats[i]
        return passes(i) and abs(f['dO']) <= 4

    fltb = [0 if passes_b(i) else 1 for i in range(len(evs))]
    orders['filterB_s3x'] = key_asc(lambda i: (fltb[i], cons[i], -sim_m[i]))

    # ---- hybrid 形态(引擎顶 8 保留 + 信号补位)由测量脚本包装:
    # hybrid(order) = top8(引擎序) + rest 按 order 排序。这里返回原始 orders,
    # 测量脚本对 subset 顺序重排。为便复用,sortkey 直接可用于 rest。
    return orders, {'flta': flt, 'fltb': fltb, 'channels': chs}


def hybrid_order(evs, sortkey, k_engine_top: int = 8):
    """hybrid 形态:引擎顶 k 位原序保留,其余深位卡按 sortkey 升序补位。"""
    n = len(evs)
    top = [i for i in range(n) if evs[i]['retrieval_rank'] <= k_engine_top]
    rest = [i for i in range(n) if evs[i]['retrieval_rank'] > k_engine_top]
    rest.sort(key=sortkey)
    pos = {i: p + 1 for p, i in enumerate(top + rest)}
    return pos
