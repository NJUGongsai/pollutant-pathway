# Design Spec: 位点驱动检索 (Site-Driven Retrieval)

**Date**: 2026-07-29
**Status**: Approved
**Author**: CC + Claude

## 1. Problem Statement

Benchmark 诚实评估 (`honest_eval.py`) 暴露漏斗唯一卡点在"造出真产物"层：random 划分仅 28% 的案例能造出真产物。诊断 (`diagnose_selection.py`) 将"造不出"拆分为：

- **病A (72%)**: 没检索到对的变法 → 病根在检索
- **病B (28%)**: 检索到了却施加不上 → 病根在施加器

病A 进一步切分为 A1（库里有、排到 top-5 外）和 A2（全库都没有、真 novel）。A1 占失败的 ~65%，意味着**改进检索策略可救回大量案例**：

| 划分 | 检索已带回 | A1 可救 | A2 真缺失 | 检索天花板 |
|---|---|---|---|---|
| random (692) | 41.5% | 65.6% | ~20% | ~79.5% |
| scaffold (702) | 37.6% | 64.2% | ~22% | ~77.0% |
| reaction_family (742) | 19.4% | 55.0% | ~36% | ~63.2% |

**目标**: 将检索从"全分子 Morgan 指纹找 top-5 相似 donor"升级为"反应位点局部环境检索"，把 `edit_retrieved/scope` 从 41.5% 向 ~79.5% 推进。

## 2. Solution Overview

**核心思想**: 检索的钥匙从"整个分子长得像"换成"反应位点周围长得像"。全分子 Morgan 指纹被骨架主导、压低了反应位点权重，导致"相似分子发生的是别的反应"。位点驱动直接匹配"谁在类似的局部环境里发生过变法"。

**改动范围**: 仅在检索层加 `site` 模式，复用现有诚实漏斗与归因口径。打分器、splits、归因逻辑、`core/*` 全部冻结。

## 3. Design Decisions (Resolved)

### 3.1 位点粒度 + 环境编码 (Q1+Q2)

**决策**: 单原子根 Morgan 指纹，radius=2，2048-bit。

| 端 | 位点定义 | 编码方式 |
|---|---|---|
| Donor | 晨羽真值中心原子集合 | `GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048, fromAtoms=center_atom_indices)` |
| Query X | 枚举每个候选重原子 | `GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048, fromAtoms=[atom_i])` |
| 匹配 | donor site FP vs 每个 X 原子 FP | `BulkTanimotoSimilarity`，取 max |

**理由**:
- RDKit 原生 `fromAtoms` 参数，零额外开发
- 指纹维度一致（2048-bit），Tanimoto 直接可用
- r=2 从单原子出发覆盖 ~2 跳邻居 ≈ 一个官能团范围
- 枚举 ~8-12 个候选原子（过滤后），计算量可控

**否决方案**:
- SMARTS 子结构匹配: 二值匹配，无相似度排序，召回率低
- 多原子根 Morgan (双端对齐): query 端无法预知中心原子组合，组合爆炸

### 3.2 Donor 中心来源 (Q3)

**决策**: 全用晨羽真值 `reaction_center_from_chenyu`，无需回退。

**数据支撑**: `reacting_center.pkl` 在训练集上覆盖率 100%（2829/2829）。

**反应中心统计**:
- 中心原子数: 均值 5.9，中位数 5，范围 2-31
- 跨片段数: 均值 2.2，众数 2（1729/2829）

### 3.3 位点匹配度量 (Q4)

**决策**: Tanimoto similarity on 2048-bit vectors。

**理由**: 方案 A（单原子根 Morgan）自然搭配 Tanimoto。edit-signature 联合打分留给 v2 消融实验。

### 3.4 召回 K × 过滤 × 去重 (Q5)

**决策**: 过滤惰性原子 → 每站点 top-3 → edit_key 去重 → 全局 top-10。

**Step 1: 过滤候选位点**

排除饱和 sp3 碳骨架（惰性位点）：
```python
# 排除条件
is_inert = (
    atom.GetAtomicNum() == 6
    and atom.GetDegree() <= 3
    and not atom.GetIsAromatic()
    and all(n.GetAtomicNum() in (1, 6) for n in atom.GetNeighbors())
)
```

保留: 杂原子 (N/O/S/P/halogen)、不饱和碳（双键/三键/芳香环）、杂原子邻位碳。预估从 ~22 重原子缩减到 ~8-12 候选位点。

**Step 2: 每站点 top-3 donor**

对每个候选位点，在 donor 位点索引里 Tanimoto top-3。12 站点 × 3 = 36 条 (donor, site) 配对。

**Step 3: edit_key 去重 + top-10 截断**

- 同一 edit_key 只保留最高 Tanimoto 的那条
- 按 Tanimoto 全局排序，取 top-10 进打分器
- 确保变法多样性

**对比当前系统**:

| | 当前 (smarts) | 位点驱动 (site) |
|---|---|---|
| 检索 key | 全分子 Morgan r=2 | 位点局部 Morgan r=2 |
| Donor 数 | 5 | ~10 (去重后) |
| 变法多样性 | 低（相似分子 → 相似变法） | 高（edit_key 去重） |
| WHERE 信息 | 无 | 有（匹配位点已知） |

### 3.5 施加衔接 (Q6)

**决策**: align_transfer + 位点预知（跳过子结构搜索）。

**机制**:
1. 位点检索输出 `(donor_rxn, query_atom_idx, tanimoto_sim)`
2. 从 donor 的 `EditScript` 获取 `changed_atoms`
3. 构造 `donor2x` 映射: donor 中心原子 → X 匹配位点附近原子（BFS 对齐邻居）
4. 调用 `align_transfer._replay(query_mol, edit_script, donor2x)` → 候选产物

**优势**: 跳过 align_transfer 原有的 `GetSubstructMatches`（全分子搜索 WHERE），直接用位点检索给出的 WHERE。更高效、更准确。

## 4. Architecture

```
                    离线建索引                          在线检索+施加
                ┌──────────────┐              ┌──────────────────────────┐
Train reactions │  晨羽真值中心  │              │  X (未知底物)             │
     2829 条 ──→│  + Morgan     │──→ 位点索引  │  ↓                       │
                │  r=2, fromAt  │   (list)     │  ① 枚举候选位点(过滤惰性) │
                │  = center_atoms│              │  ② 每位点 Morgan r=2 FP  │
                └──────────────┘              │  ③ 在索引中 Tanimoto     │
                                              │     top-3/site           │
                                              │  ④ edit_key 去重→top-10  │
                                              │  ⑤ align_transfer 施加   │
                                              │     (位点预知,跳过匹配)    │
                                              │  ⑥ DRFP 打分排序         │
                                              └──────────────────────────┘
```

### 4.1 数据流

```
Test reaction (rxn_smiles)
  ├─ ci.main_substrate(rxn) → X
  ├─ ci.main_product(rxn) → Y_true
  │
  ├─ site_retrieval.retrieve_by_site(X, site_index, ...)
  │   ├─ enumerate_candidate_sites(X) → [atom_idx, ...]
  │   ├─ for each site: Morgan(fromAtoms=[atom_i]) → BulkTanimoto vs index
  │   ├─ exclude_group filter
  │   ├─ per-site top-3 → aggregate
  │   ├─ edit_key dedup → global top-10
  │   └─ return List[SiteHit(donor_rxn, query_atom_idx, tanimoto, edit_key)]
  │
  └─ for each SiteHit:
       ├─ site_retrieval.generate_from_site_hit(hit, X)
       │   ├─ _donor_edit(donor_rxn) → (EditScript, center_atoms)
       │   ├─ build donor2x mapping (center_atoms → query_atom neighborhood)
       │   └─ _replay(X_mol, EditScript, donor2x) → candidate SMILES
       │
       └─ candidate products → DRFP scoring (unchanged)
```

### 4.2 索引结构

```python
@dataclass
class SiteIndexEntry:
    donor_rxn: str            # 原始反应 SMILES
    site_fp: ExplicitBitVect  # fromAtoms Morgan r=2, 2048-bit
    edit_key: tuple           # EditScript.key() 变法签名
    center_atoms: List[int]   # 晨羽真值中心原子(per-fragment local idx)
    xd: str                   # 辅酶剥离后的底物
    yd: str                   # 辅酶剥离后的产物

class SiteIndex:
    entries: List[SiteIndexEntry]
    fps: List[ExplicitBitVect]  # 冗余引用，BulkTanimoto 用
```

## 5. Integration with honest_eval

### 5.1 新增参数

```python
RETRIEVAL_MODE = "smarts"  # "smarts" | "site"
# CLI: --retrieval smarts|site
```

### 5.2 改动点（最小侵入）

| 函数 | 改动 |
|---|---|
| `build_donor_index` | 新增 `if RETRIEVAL_MODE == "site"` 分支，调用 `site_retrieval.build_site_index` |
| `retrieve_donors` | 新增 `site` 分支，调用 `site_retrieval.retrieve_by_site`，返回含 `query_atom_idx` 的扩展结果 |
| `generate_candidates` | 新增 `site_hit` 参数，有值时走 `site_retrieval.generate_from_site_hit` |
| `eval_one` | `site` 模式下把 `site_hit` 传给 `generate_candidates` |

### 5.3 不变的部分

- `diagnose_selection.py` — 只读诊断，口径不变
- `canonical_identity.py` — 辅酶剥离/反应中心锚定不变
- `edit_script.py` — 变法签名提取不变
- `align_transfer.py` — 复用 `_replay`，不改原有 `transfer` 函数
- `splits.py` — 防泄漏逻辑不变
- `reaction_scorer.py` — DRFP 打分不变
- `core/*` — 全部冻结

## 6. Measurement Protocol

### 6.1 命令

```bash
cd CC/branch/ReactionAgent/benchmark

# 位点驱动模式 - 三划分
PYTHONPATH=../core python honest_eval.py --strategy random --retrieval site --out ../reports/p1_site/random_site.json
PYTHONPATH=../core python honest_eval.py --strategy scaffold --retrieval site --out ../reports/p1_site/scaffold_site.json
PYTHONPATH=../core python honest_eval.py --strategy reaction_family --retrieval site --out ../reports/p1_site/reaction_family_site.json

# A1/A2 诊断（对比基线）
PYTHONPATH=../core python diagnose_selection.py --out ../reports/p1_site/selection_diagnosis_site.json
```

### 6.2 成功判据

| 指标 | 基线 (smarts) | 目标 (site) | 理论上限 |
|---|---|---|---|
| `edit_retrieved/scope` (random) | 41.5% | >55% | ~79.5% |
| `selection_failure` (random) | ~50% | <35% | ~20% (A2 硬顶) |
| top5 命中 (造出后) | ~94% | >=90% | — |
| A1 回收率 | 0% (基线) | >40% | 100% |

### 6.3 消融计划（v2）

如果 v1 效果未达预期，可尝试：
- 去掉惰性原子过滤（看过滤是否过激）
- 调 top_per_site (2→5) 和 final_top_k (5→15)
- 加入 edit-signature 联合打分
- 调整 Morgan radius (1→3)

## 7. New Files

| 文件 | 职责 | 预估行数 |
|---|---|---|
| `benchmark/site_retrieval.py` | 位点索引构建、候选位点枚举、位点级检索、位点感知施加 | ~250 行 |
| `honest_eval.py` 改动 | 新增 `site` retrieval mode 分支 | ~30 行改动 |
| `reports/p1_site/` | 结果输出目录 | — |

## 8. Frozen (Do Not Touch)

- 打分器 (`reaction_scorer.py`)
- 6 步框架
- demov1
- splits 防泄漏逻辑 (`splits.py`)
- honest_eval 的四类防作弊与归因口径
- `core/*` 全部文件
- `canonical_identity.py`
- `edit_script.py`
- `align_transfer.py`（复用 `_replay`，不改 `transfer`）
- A2 (~20% 真 novel) 不在本次射程

## 9. Reusable Building Blocks

| 积木 | 位置 | 用途 |
|---|---|---|
| `reaction_center_from_chenyu(rxn)` | `core/chenyu_features.py` | 晨羽真值反应中心 |
| `AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits, fromAtoms)` | RDKit | 根原子 Morgan 指纹 |
| `DataStructs.BulkTanimotoSimilarity` | RDKit | 批量 Tanimoto |
| `edit_script.extract_edit(xd, yd)` | `benchmark/edit_script.py` | 变法签名 |
| `align_transfer._replay(x_mol, es, donor2x)` | `benchmark/align_transfer.py` | 编辑回放 |
| `ci.transformed_pair(rxn)` | `benchmark/canonical_identity.py` | 辅酶剥离 + 中心锚定 |
| `pipeline._get_env_atoms(mol, center, radius)` | `core/pipeline.py` | BFS 邻域扩展 |

## 10. Risk Register

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 惰性原子过滤过激，漏掉真正反应位点 | 中 | 高 | 消融: 不过滤 vs 过滤对比 |
| 单原子 FP 信息量不足，假阳性多 | 中 | 中 | 消融: r=1 vs r=2 vs r=3 |
| donor2x 映射构造失败（BFS 对齐不上） | 低 | 高 | 回退到 align_transfer 原有子结构匹配 |
| top-10 打分器负载增加 | 低 | 低 | 观察打分时间，必要时调 SCORER_CAP |
