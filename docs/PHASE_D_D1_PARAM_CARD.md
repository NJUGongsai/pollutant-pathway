# Phase D D1 参数卡:供体反应物相似度检索(reactant_similar 通道)

> 提交时点:**任何 dev 评分之前**(2026-09-28)。本卡不含 dev 20 / EC298
> 的任何输入、答案或归因数据;依据只有①资产自身无标签分布
> (`reports/phase_d/asset_similarity_stats.json`,脚本
> `scripts/phase_d_asset_stats.py`,seed=20260928)与②合成夹具。
> 参数与版本进入 prediction policy / run identity;变更即拒绝旧 run resume。

## 1. 冻结参数

| 参数 | 值 | policy 键 |
|---|---|---|
| 指纹 | Morgan(ECFP 类),radius=2,nBits=2048,useChirality=False | (版本串内) |
| 度量 | Tanimoto | (版本串内) |
| 阈值 | **0.45**,边界比较 **>=**(恰在阈值召回) | `reactant_similar_threshold` |
| 检索 top-K | **16** | `reactant_similar_top_k` |
| 通道开关 | true;false/非正参数 = C0 旧检索配置 | `reactant_similar_enabled` |
| 算法版本 | `v43-rsim-1`(指纹/半径/位数/立体/度量/边界任一变化必须升版) | `SIMILARITY_VERSION` |
| 输入规范化 | 供体侧 = `_strip_map(mapped_lhs)`(去映射 canonical);底物侧 = RDKit canonical | (实现内) |
| 无效 SMILES | 底物无效 → 返回 `[]`;资产行反应物无效 → 该行不进索引(不崩、不猜) | (实现内) |
| 召回排序 | `(-similarity, line_no, record_id)` 确定性 tie-break;与引擎异构 score 无关 | (实现内) |
| 去重键 | `(asset_sha256, line_no, record_id)`;同键多通道召回合并 `find_channels`,只评估一次 | (实现内) |
| 评估序 | resolved 卡 → reactant_similar 通道(相似度降序)→ 其余卡(rank, evidence_id) | `extra_channel_order` |
| 候选总上限 | 检索 top-K(16)与每父实际评估数 `max_analogy_donor_candidates`(3/5/10,按臂)分别计数 | policy 两键 |

## 2. 阈值与 top-K 的资产分布依据(无标签)

资产 `analog/corpus_templates_v1.jsonl` 17183 行全部反应物可解析
(0 条无效);13003 个唯一反应物;2504 个 SMILES 组有重复记录
(最多 52 条/SMILES —— 去重键必须含 record_id/line_no 的直接证据)。

固定种子抽样 2000 行的"资产内最近邻相似度":p25=0.815、p50=0.980
(资产高度冗余:同反应物多模板);"前 5 相似供体的第 5 近邻":p25=0.558、
p50=0.731 —— 结构相关的供体群通常落在 0.55 以上。

各阈值的召回量(抽样底物、资产内、不含自身):

| 阈值 | 中位召回 | p90 | 零召回率 |
|---|---:|---:|---:|
| 0.40 | 15 | 150 | 2.2% |
| **0.45** | **10** | **102** | **6.0%** |
| 0.50 | 8 | 77 | 7.4% |
| 0.55 | 6 | 41 | 10.6% |

**选 0.45**:低于"结构相关群"下沿(0.55)以保召回、显著高于随机碰撞
水平;中位召回 10 与 top-K 16、预算档位 3/5/10 形成区分度(0.40 的
p90=150 会让 top-16 挤满同簇冗余;0.50 以上零召回率抬升)。
**选 top-K 16**:约 1.6× 最大评估预算(10),保证预算内候选有筛选
余量而检索成本可忽略(见 §3)。未进评估的召回项标
`budget_not_assessed`,不是化学失败。

## 3. 性能成本(实测,本机 depending43 env)

索引构建(17183 指纹)1.24 s(进程内一次,类级缓存键含资产 SHA +
算法版本);单底物查询(全库扫描 BulkTanimoto)3.1 ms。运行时开销
相对检索引擎可忽略;无网络、无凭证。

## 4. 语义边界(与门禁的关系)

- 相似度**只决定召回次序**,绝不替代 `assess_donor`:召回供体仍走
  Phase C 全部变换提取、全对齐、氢/价态/电荷/键级门禁;
- resolved 卡优先评估,新通道不得挤掉已对齐唯一模板供体;被挤掉的
  其余卡供体逐条记 `displaced_by_similar_channel`;
- 供体原始产物不得直接报告为当前底物产物;不同目标继续 `ambiguous`;
- 无映射 `corpus_trace` 引用不因相似升格;`mapping_status=resolved`
  单独仍不代表可迁移(Phase C 语义不变);
- 新供体只属于当前父节点、当前底物的资格块(纯函数按底物计算)。

## 5. 夹具依据

`tests/test_reactant_similar.py` 18 例:旧通道漏召回而新通道找回、
阈值边界含等、双高于最高相似度为空、无效底物、同 SMILES 52 记录不
误合并、双通道去重保双标签且只评估一次、resolved 不被饥饿、高相似
仍被化学门禁拒(F2 夹具)、竞争歧义弃权(F7 夹具)、budget_not_assessed
不冒充 inapplicable、displaced 留痕、C0 无 similar_refs 行为与 Phase C
一致(F7)、兄弟路径不串线、索引键含 SHA+版本、真实资产 ref 的 SHA/
行号可回查、workflow 节点级接线(classify_evidence 经 finder 的
analog_resolver 真实召回并落盘通道留痕)。

## 6. 已知限制

- 立体盲指纹:对映异构体间相似度=1(与既有 stereo_blind 身份口径一致;
  立体区分由下游门禁与 canonical SMILES 承担);
- 阈值/top-K 是**工程参数**,由资产分布定标;其最终取舍由 D3 配对实验
  的预注册规则裁决,本卡不预设结论;
- 检索是全库扫描(3 ms/查询),无需近似索引;若资产规模增长 >100×
  再评估。
