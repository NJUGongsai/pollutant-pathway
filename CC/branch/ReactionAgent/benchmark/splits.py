"""数据折划分：random / scaffold / reaction-family，全部在 group 粒度上进行。

为什么在 group 粒度上划分
  同一化学转化(group_key = 主底物→主产物)可能对应多条反应(不同酶/写法)。若按反应随机划分，
  测试集里的转化可能在训练集里以另一条反应出现 → donor 库/酶家族"见过答案" → 泄漏、指标虚高。
  因此先按 group_key 聚合，再整组分配到 train / test，保证同一转化不跨折。

三种策略(泛化难度递增)
  random          : 组随机分配。衡量同分布内的检索-迁移能力。
  scaffold        : 按主底物 Murcko 骨架聚桶；大桶优先进 train，稀有骨架落 test。
                    衡量"没见过这类骨架"时的泛化。
  reaction-family : 按主催化酶 EC 前三级(x.y.z)聚桶；整个 EC 家族被 hold out。
                    衡量"没见过这类反应化学"时的泛化(最严格)。

划分只决定 train/test 归属；donor 库与酶家族在评估时只允许取 train 组，见 honest_eval.py。
"""
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

import canonical_identity as ci


@dataclass
class Split:
    strategy: str
    train_rxns: List[str]
    test_rxns: List[str]
    group_of: Dict[str, Tuple[str, str]] = field(default_factory=dict)   # rxn -> group_key
    fold_of_group: Dict[Tuple[str, str], str] = field(default_factory=dict)  # group_key -> 'train'/'test'

    def summary(self) -> str:
        ng_tr = sum(1 for v in self.fold_of_group.values() if v == "train")
        ng_te = sum(1 for v in self.fold_of_group.values() if v == "test")
        return (f"[{self.strategy}] rxns train/test = {len(self.train_rxns)}/{len(self.test_rxns)}; "
                f"groups train/test = {ng_tr}/{ng_te}")


# ── 论域与分组 ──────────────────────────────────────────────────────────
def load_universe() -> List[str]:
    """P0 论域：同时具备 reacting_center、DRFP、酶标签的反应(canonical 去重后)。"""
    import chenyu_features as cf
    import enzyme_lookup as el
    rc = cf._load_rc()
    r2e = el._load_rxn2enzymes()
    raw = set(rc) & set(r2e)
    # canonical 去重：同一 canonical_reaction 只保留一条(取原始串字典序最小者，确定性)
    by_canon: Dict[str, str] = {}
    for rxn in raw:
        c = ci.canonical_reaction(rxn)
        if c is None:
            continue
        if c not in by_canon or rxn < by_canon[c]:
            by_canon[c] = rxn
    return sorted(by_canon.values())


def build_groups(rxns: List[str]) -> Tuple[Dict[Tuple[str, str], List[str]], Dict[str, Tuple[str, str]]]:
    """反应列表 → (group_key -> [rxns], rxn -> group_key)；无法定主片段的反应被丢弃。"""
    groups: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    group_of: Dict[str, Tuple[str, str]] = {}
    for rxn in rxns:
        g = ci.group_key(rxn)
        if g is None:
            continue
        groups[g].append(rxn)
        group_of[rxn] = g
    return dict(groups), group_of


# ── EC / scaffold 桶键 ──────────────────────────────────────────────────
def _primary_ec3(group_rxns: List[str]) -> str:
    """一组反应的主 EC 前三级(x.y.z)：取组内所有酶 EC 里最常见者。缺失记 'NA'。"""
    import enzyme_lookup as el
    cnt: Dict[str, int] = defaultdict(int)
    for rxn in group_rxns:
        for _uni, ec in el.enzymes_for_reaction(rxn):
            if not ec:
                continue
            parts = str(ec).split(".")
            if len(parts) >= 3 and all(parts[:3]):
                cnt[".".join(parts[:3])] += 1
    if not cnt:
        return "NA"
    return max(cnt, key=lambda k: (cnt[k], k))


def _scaffold_key(main_substrate_smi: str) -> str:
    """主底物的 Murcko 通用骨架 SMILES；无环/解析失败退回分子式级别的稳定串。"""
    m = Chem.MolFromSmiles(main_substrate_smi)
    if m is None:
        return "NA"
    try:
        scaf = MurckoScaffold.GetScaffoldForMol(m)
        generic = MurckoScaffold.MakeScaffoldGeneric(scaf)
        s = Chem.MolToSmiles(generic)
        return s if s else "ACYCLIC:" + main_substrate_smi
    except Exception:
        return "ACYCLIC:" + main_substrate_smi


# ── 通用桶划分：整桶分配到 train/test，逼近 test_frac ──────────────────────
def _assign_buckets(bucket_to_groups: Dict[str, List[Tuple[str, str]]],
                    n_groups_total: int, test_frac: float,
                    seed: int, largest_to_train: bool) -> Dict[Tuple[str, str], str]:
    """把桶整体分到 train/test。

    largest_to_train=True(scaffold/family): 桶按大小降序，先填 train 到 (1-frac)，其余入 test
                     → 稀有桶落 test，构成更难的泛化测试。
    largest_to_train=False(random): 桶顺序随机打乱后累加到 test 直至达标。
    """
    buckets = list(bucket_to_groups.items())
    target_test = int(round(n_groups_total * test_frac))
    fold: Dict[Tuple[str, str], str] = {}
    if largest_to_train:
        buckets.sort(key=lambda kv: (-len(kv[1]), kv[0]))
        n_train_target = n_groups_total - target_test
        n_train = 0
        for _key, grps in buckets:
            if n_train + len(grps) <= n_train_target or n_train == 0:
                for g in grps:
                    fold[g] = "train"
                n_train += len(grps)
            else:
                for g in grps:
                    fold[g] = "test"
    else:
        rng = random.Random(seed)
        rng.shuffle(buckets)
        n_test = 0
        for _key, grps in buckets:
            put_test = n_test < target_test
            for g in grps:
                fold[g] = "test" if put_test else "train"
            if put_test:
                n_test += len(grps)
    return fold


def _build_split(strategy: str, groups, group_of, fold_of_group) -> Split:
    train_rxns, test_rxns = [], []
    for rxn, g in group_of.items():
        (test_rxns if fold_of_group.get(g) == "test" else train_rxns).append(rxn)
    return Split(strategy=strategy, train_rxns=sorted(train_rxns), test_rxns=sorted(test_rxns),
                 group_of=group_of, fold_of_group=fold_of_group)


def make_split(strategy: str, test_frac: float = 0.2, seed: int = 42,
               rxns: Optional[List[str]] = None) -> Split:
    """构造指定策略的划分。strategy ∈ {'random','scaffold','reaction_family'}。"""
    if rxns is None:
        rxns = load_universe()
    groups, group_of = build_groups(rxns)
    all_groups = list(groups.keys())

    if strategy == "random":
        # 每组自成一桶
        bucket = {f"g{i}": [g] for i, g in enumerate(all_groups)}
        fold = _assign_buckets(bucket, len(all_groups), test_frac, seed, largest_to_train=False)
    elif strategy == "scaffold":
        bucket: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for g in all_groups:
            bucket[_scaffold_key(g[0])].append(g)  # g[0] = canonical 主底物
        fold = _assign_buckets(dict(bucket), len(all_groups), test_frac, seed, largest_to_train=True)
    elif strategy == "reaction_family":
        bucket: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for g in all_groups:
            bucket[_primary_ec3(groups[g])].append(g)
        fold = _assign_buckets(dict(bucket), len(all_groups), test_frac, seed, largest_to_train=True)
    else:
        raise ValueError(f"未知划分策略: {strategy}")

    return _build_split(strategy, groups, group_of, fold)


if __name__ == "__main__":
    for strat in ("random", "scaffold", "reaction_family"):
        print(make_split(strat).summary())
