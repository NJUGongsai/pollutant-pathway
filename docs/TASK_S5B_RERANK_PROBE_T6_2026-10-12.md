# 任务书 T6：重排零模型摸底 + D2 槽位竞争验证 + hwall 位点统计（2026-10-12）

> 主会话起草，交实施子代理。零上下文可接。
> 上游：CC 拍板"重排先零模型摸底"；mimo r35 P3（D2 槽位竞争）与 watch item（hwall 位点抽查）；T3 基建已就位（298/298 对齐的逐事件匹配明细）。
> 必读背景：docs/S5B_CHAIN11_TO_CHAIN12_RECON_2026-10-12.md（含勘误节——D2 指纹题级 8S/4P/1U、事件级新 strict 0/35 两个口径）。

## 0. 一句话目标

三个零模型分析：① 验证 mimo 的"D2 槽位竞争"假设（D2 候选是否把正确答案挤到后位）；② 对固定提交集（chain12 封存候选序）跑确定性规则重排模拟，量化 38 道后位答案的首位转化潜力与旧成功退步风险；③ 20 道 hwall 指纹新 strict 的脱氢位点机械统计（化学解读归 mimo 下轮，本轮只出结构事实）。

## 1. 输入（全部本地已就位）

| 项 | 路径 | 关键内容 |
|---|---|---|
| 逐事件匹配明细 | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/rescore_detail.json` | per_qid[qid].candidate_events[{event_id, position, strict_hit, created_at}]、matched_events、d2_declared_copy_components_occurrences |
| 判分 | `…chain12_s5b_298_v4b_20261012/metrics.json` | per_qid 桶与 rank |
| 逐题 payload | `…synced/runs/<run_id>/native_export/*/payload.json` | events（全字段）、states、search_actions、deferred 等 |
| 漏斗 | `…analysis/funnel_chain12.json` | T2 产物 |
| 退步/新 strict 清单 | 对账报告 §附录 A/B | 14 退步 qid、35 新 strict qid |

## 2. 任务 A：D2 槽位竞争（mimo P3 假设验证）

对 14 道 hit@1 退步题逐题回答："把正确答案挤下去的上方候选是什么"：

1. 7 道 rank 掉位题：查 c12 该题 rank1 事件的身份与特征（是否 D2/带 coproduct 参与物/来源通道），与正确答案事件（rank2-4）对比；
2. 3 道 strict→partial 题（0eda0ec3/21ed83a68 带 D2 指纹、5d15fc19 不带）：查题内是否存在"更完整的 D2 事件顶替了原本 exact 的候选"；
3. 8 道题级 strict 指纹题（勘误后的新事实）：D2 陪跑事件普遍排在第几位（position 分布统计）；
4. 结论三选一逐题给出：**D2 竞争成立 / 排序方差（上方是非 D2 候选）/ 证据不足**，聚合计数。

## 3. 任务 B：零模型确定性重排模拟（固定快照，全局应用）

- **对象**：每题 candidate_events 序列（判分口径 (created_at,event_id) 序）。重排只换顺序不改集合；每题重排后重算 rank（首个 strict_hit 事件的位次）→ 新 hit@1。
- **规则集（先探字段可得性，每条规则全局作用于全部 298 题，禁只作用于失分题）**：
  - R0 基线=原序（应复现 92/126/130，自检门）；
  - R1 来源优先级：事件按来源通道排序（recorded/corpus/analog/novel 的优先序从事件 provenance/record 字段判；字段不可得时如实说明并降级为可用特征）；
  - R2 参与物简洁优先：参与物总数少者优先（近似"主反应优先"）；
  - R3 产物复杂度：事件主产物重原子数少者优先（states 里 SMILES 可解析）；
  - R4 反向序（下界对照，预期显著退步）。
  - 允许根据实际字段增删规则（如 dedup 签名、model_rank 痕迹），增删要在报告里说明依据。
- **报告矩阵**：每规则的新 hit@1/hit@3/hit@5、旧 92 题保留数、38 道后位答案转化数（到位次 1）、14 退步题恢复数、净增（新 hit@1 − 92）；U 不变自检（每题 strict_hit 集合与 R0 全等）。
- **纪律**：这是固定快照模拟，不是新系统成绩；结论上限声明=重排不改变候选宇宙（120 道 H 桶不可救）。

## 4. 任务 C：hwall 位点机械统计（mimo watch item）

对 20 道 hwall 指纹新 strict（识别法：附录 B 35 新 strict 中，c11 同题 payload 含 AtomValenceException 而 c12 消失——用 synced 两批 payload 重现识别，/tmp/recon_c11_c12 的旧脚本已易失勿依赖）：

- 对每题命中事件：底物 SMILES（batch_manifest entries/substrate_smiles 或 payload states 根状态）→ 主产物 SMILES，RDKit 机械统计：变化键的类型分布（C-O/C-N/C-C/C-S/其他，按两端原子元素）、脱氢原子类型分布（C/N/O/S）、每事件脱氢总数；
- 聚合表 + 异常单列（非氧化还原常规模式的题，如有）；不做化学可行性判断（mimo 明确不建议工具层加机理门）。

## 5. 红线

零模型零网络零 LLM；synced/analysis 只读（新产出写 `…analysis/t6_rerank.json`/`t6_d2_contention.md`/`t6_hwall_sites.md`，文件名避开 funnel_/partial_/rescore_ 前缀）；脚本新文件 `scripts/s5b_t6_rerank_probe.py`（可拆多脚本）；判分代码零触碰；R0 自检不过（≠92/126/130）停下报告；不 commit 不 push；题域标签 298/RHEA 已见题写进输出头。

## 6. 排障表

| 症状 | 处置 |
|---|---|
| 事件字段与预期不符（如来源通道不可得） | 如实记录，规则降级或跳过并说明；不硬造特征 |
| R0 不复现 92/126/130 | 检查 candidate_events 取用是否与判分候选序定义一致（reactant 侧命中根严格状态、(created_at,event_id) 升序）；仍不齐停下 |
| hwall 指纹识别与对账报告 20 题不符 | 以本次程序识别为准并报告差异（旧 /tmp 脚本已易失） |

## 7. 回传义务

1. 任务 A 三分类聚合表+逐题清单（14+8 题）；2. 任务 B 规则矩阵（含 R0 自检与 U 不变证明）；3. 任务 C 位点分布表+异常单列；4. known limits（尤其字段不可得降级处）；5. 产出文件路径。不贴大段 JSON。
