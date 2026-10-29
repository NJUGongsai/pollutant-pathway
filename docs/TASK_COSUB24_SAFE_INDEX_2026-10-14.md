# TASK — COSUB24 安全索引与来源覆盖核定（2026-10-14）

> 派单：主窗口（CC 授权「建安全索引核定 24 题来源真带共底物」）。
> 依据：Codex 裁定 `docs/ADJUDICATION_COSUB24_CODEX_2026-10-14.md`
> §Q6（索引字段清单+五桶统计口径）。执行：子代理。
> 目的一句话：**24 题机制共底物 partial 里，多少题的来源语料方程
> 真的带那些共底物**（R1 参考侧补全的覆盖面核定）。

## 一、Codex 给的口径（照办）

- **索引字段**（不含题面、结构取值、预测或分数）：匿名成员键
  （member-01…24）、来源文件 SHA、行号、record_id、master_id/
  方向、fingerprint（**哈希形态**，非 SMILES）、关联唯一性/歧义、
  生成 provenance（链接怎么建立的）；主底物定位可用来源组件
  ordinal。
- **五桶统计**（只出聚合计数）：已关联 / 结构缺失或泛化 / 方向
  歧义 / **覆盖可核（来源方程真带该共底物）** / 仍未核。
- 禁止按 24 题预测 extras 反填金标；禁止用来源全库 37,098 条推
  子集比例。

## 二、方法（数据面）

1. **24 题成员定位**：chain12 synced 批数据（gitignored）里 43
   partial 三拆的 superset-40 → 24 机制共底物成员（CS2c 补证
   `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/`
   cs2c_side_predicates.md 一带有逐 qid 分桶，可直接对齐口径）。
2. **关联建立**：每成员的事件 → 其候选来源（payload 里
   scheduled/pool 的 record_key，形如 tpl-rhea:xxx / rhea:xxx）→
   corpus_v1.jsonl 行（Codex 已核：文件 SHA+来源 manifest 对上；
   重复 record_id 组 303 个——按 SHA+行号+record_id+方向/master
   定位，不凭 record_id 单键）。无来源关联（novel 型）单列一桶。
3. **覆盖判定**（判分进程内，cn_identity 同源工具）：该成员事件
   extras 的机制共底物身份 ↔ 来源方程两侧组分多重集——出现且
   同侧=**覆盖可核**；出现但方向歧义=方向歧义桶；来源方程无该
   身份=来源未带（如实单列）；来源行泛化 `*`/结构缺失=对应桶。
4. **产物**：`reports/ppv1_s5b/cosub24_index_2026-10-14/`
   （gitignored）：`safe_index.json`（Codex 字段清单，零 SMILES
   零 qid 零题面——成员用匿名键）+ `coverage_aggregate.json`
   （五桶+novel 桶聚合计数）+ `coverage_report.md`（大白话）。

## 三、红线

- 零模型零网络零 LLM；金标/题面/结构取值**只在本地进程内**，
  索引与报告零外带（匿名键+哈希+行号+计数 only）；
- 不改 src/tests/既有 docs；不 push 不提交；产物目录 gitignored；
- 关联建立不了/口径拿不准 → 停下报告，不硬凑；
- 第一步先落 START_MARKER+progress（防无痕死亡）。

## 四、回传义务

六桶计数表（含 novel 桶与来源未带桶）、索引规模与关联唯一性
统计（唯一/歧义各多少）、对 R1 覆盖面的直接答案（"24 题里 N 题
来源真带共底物"）、方法与偏差如实。
