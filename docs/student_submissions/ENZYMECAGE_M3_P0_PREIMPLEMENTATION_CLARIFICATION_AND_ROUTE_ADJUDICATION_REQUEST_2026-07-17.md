# EnzymeCAGE M3-P0 正式实施前证据汇总与路线裁定申请

日期：2026-07-17  
候选酶路线与资产扩充补充审计：2026-07-18  
回复文件：

```text
00_Authority_Teacher_Plan/
TEACHER_REPLY_D4_ACCEPTED_AND_M3_STARTUP_PACKAGE_2026-07-16.md
```

当前状态：D4 v1.1 已由老师正式验收，M2 已收官；M3-P0 的最终证据包
M3-P0A1A 与候选池公平比较包 M3-P0B1 均已通过独立本地内容、manifest、tar
和外部 identity 审计。M3-P1 至 M3-P4 尚未启动，三个端到端 case、候选池路线
和验收口径均未擅自选定。

本文件只完成老师要求的 M3 实施前四项本地建议，并如实列出证据不能支持的
部分。请老师逐项裁定后再发布 M3 正式实施口径。

---

## 一、先给结论

老师要求的四项前置调研均已执行，但调研结果显示原设想不能全部原样落地：

1. P0 中找到 9 个具有污水/新污染物规则匹配证据且有冻结资产的候选反应，
   但它们只是 `SUPPORTED_PLAUSIBLE_REQUIRES_REVIEW`，不是生物学验证的污染物
   降解反应；其中 7 个为强档、2 个为中档、弱档为 0。因此“污水场景 ×
   强/中/弱三档”目前不能完整构成。
2. 没有建立任意 `reaction SMILES -> EC` 的稳定在线能力。当前 EC 证据主要
   来自固定下载到本地的 Rhea 140 官方文件离线精确连接。对 451 个 P0 反应，
   已知 Rhea ID 的精确 EC 覆盖为 294/451，另有 157 个缺失。
3. 公平排除全部 P0 查询反应后，B 路线命中 91/450，C 路线命中 246/450。
   C 覆盖更高，但候选池中位数为 61.5、P95 约 1,267、最大 3,078；B 的池更小，
   但中位数为 0、覆盖不足。C 并非“走不通”：它为 450/450 个可评估反应形成
   候选池，并在 246 个反应中召回至少一个已知正例；但它也不能被描述为普适
   成功方案。B、C 均有独有命中，当前证据不支持放弃任一路线。
4. 当前 scoped roots 中没有可运行的 Substrate Agent、Reaction Agent、
   EnzymePoolAgent、EnzymeCAGEAgent 或 orchestrator；14 项 schema、工具绑定、
   编排边和测试均待实现。这不是漏做 M3，而是遵守老师“P0 裁定前先不写代码”。
5. 没有新反应预测器。`MissingReactionAssetError` 只表示冻结资产域外拒绝，
   不会生成反应、EC、特征或预测，因此不能称为 fallback。
6. 当前 B/C 基准只统计具有 D4 完整资产的 UID，尚未测量“生物学候选已被
   B/C 召回、但因缺少冻结资产而未进入模型”的规模。原版代码证明可以为预先
   确定、且具备序列和可用口袋结构的外部候选重新计算 ESM/GVP 特征，但当前
   D4 v1.1 没有经授权、验证的资产生成分支。建议把候选召回、资产补齐和模型
   排序分开治理，并由老师另行裁定是否在 M3 内做有界资产补齐。

基于以上事实，本地建议不是直接选择老师原始的 B 或 C，而是申请老师裁定一个
受限的 M3 v1 口径：

```text
case：采用 C 的受限变体，兼顾污水场景和能力边界，但不虚构弱档污水 case；
pool：不放弃 B 或 C；暂建议 B（离线精确 EC）优先、C（原始 EnzymeCAGE
      相似反应 top-10）回退，并保留两路独立 provenance；
asset：候选全集与 D4 可计算资产池分层；是否为外部候选补资产另请老师裁定；
Agent：先做最小可用版，只支持 retrieved + 冻结预计算资产域；
验收：采用 B，学生证据自审 + 老师最终复核，定量结果必须披露但不作硬门槛。
```

该建议仍是待裁定方案，不是已批准架构，也没有进入实现。

---

## 二、与老师 M3-P0 要求逐项对照

| 老师要求 | 已完成证据 | 当前结论 | 仍需老师裁定 |
|---|---|---|---|
| 决策 1：调研 P0 中是否存在已知酶且与污水相关的反应 | 451 个 P0 反应、10,804 个正例 UID、污水证据表和 9 个候选均已审计 | 有 9 个规则匹配候选，但 0 个直接支持，且无弱档 | case 采用受限 C、退回 A，还是另开弱档污水/Fallback 工作 |
| 决策 2：确认 pool 来源及 reaction-to-EC/API 能力 | 6,151 EC 分布、14 次有界官方接口探测、B/C 公平候选池基准和原版检索/特征代码均已审计 | 在线任意 SMILES-to-EC 未建立；B 覆盖不足，C 池过宽；当前只比较 D4-valid UID | B/C 如何编排；大于 100 的 pool 如何处理；是否授权外部候选资产补齐 |
| 决策 3：最小可用还是先做 prompt 迭代 | 14 项 Agent/schema/tool/test 缺口已逐项盘点 | 无 live implementation，无法先测 prompt 质量 | 是否批准最小可用、retrieved-only、资产域内版本 |
| 决策 4：M3 验收标准及审核人 | 12 项人工审核 rubric 已形成 | B 最符合 demo 定位 | 是否批准学生自审 + 老师复核，外部专家延后 |

老师要求 P0 阶段先澄清、后实施。目前没有少做已经授权的 M3 实现，因为老师
尚未发布 P0 裁定；真正未具备的是任意新反应预测、资产在线生成、稳定在线
SMILES-to-EC 和完整弱档污水 case，这些能力不能在汇报中写成已有。

---

## 三、决策 1：三个端到端 case

### 3.1 老师原要求

老师倾向方案 C，即三个 case 同时体现污水业务相关性和强/中/弱难度分层，并
要求确认 P0 test 中是否有已知酶、provenance rank 和污水处理相关证据。

### 3.2 实测结果

P0 固定评估域为 451 个反应，其中 450 个有正例、1 个无正例。难度分布为：

```text
STRONG_TOP_5:   292
MEDIUM_6_TO_30:  82
WEAK_OVER_100:   21
OTHER:            55
```

450 个可评估反应的冻结基线为：

```text
Hit@10:                 0.7288888888888889
MRR@10:                 0.5042936507936507
unrestricted MRR:       0.5131785553067092（仅诊断，不作为 MRR@10）
```

难度档位与上述指标来自固定五个 seed 预测表的独立重算，不是根据候选 case
主观指定。

规则匹配得到 9 个污水/新污染物候选：

```text
SUPPORTED_DIRECT:                     0
SUPPORTED_PLAUSIBLE_REQUIRES_REVIEW:  9
  strong: 7
  medium: 2
  weak:   0
```

这 9 个候选来自项目底物表中的显式“新污染物”标记、ChEBI 精确名称和 Rhea
反应记录的交叉筛查。项目底物表不是污染物专库，规则命中也不等于该反应已经被
证实适用于污水降解。部分反应是抗生素的磷酸化、腺苷化、糖基化或其他转化，
不能仅凭底物属于污染物就写成“降解已验证”。

### 3.3 九个待人工审核候选及候选池结果

表中“B/C pool”表示候选池大小，“recover”表示已知正确 UID 被召回的数量；
它们不是 EnzymeCAGE 最终 rank。

| 候选反应简述 | 难度 / 最佳 rank | 完整 EC | B pool/recover | C pool/recover |
|---|---:|---|---:|---:|
| 10-deoxymethymycin hydroxylation | strong / 1 | 1.14.15.33 | 1/1 | 5/1 |
| (S)-6-hydroxynicotine oxidation | strong / 2 | 无 | 0/0 | 15/2 |
| streptomycin phosphorylation | strong / 3 | 2.7.1.87 | 0/0 | 51/0 |
| 10-deoxymethynolide glycosylation | strong / 4 | 2.4.1.277 | 0/0 | 11/0 |
| spectinomycin adenylylation | strong / 4 | 无 | 0/0 | 1472/5 |
| ribostamycin-related glycosylation | strong / 5 | 2.4.1.285 | 0/0 | 84/0 |
| 4'-demethylrebeccamycin hydrolysis | medium / 8 | 4.3.3.5 | 0/0 | 119/0 |
| tetracenomycin F2 conversion | medium / 10 | 4.2.1.154 | 0/0 | 17/0 |
| rifampicin phosphorylation | strong / 1 | 2.7.9.6 | 0/0 | 291/0 |

九个候选合计 22 个已知正例 UID：公平排除后的 B 只召回 1/22，C 召回 8/22；
B 只命中 1/9，C 命中 3/9。两个中档候选的正确 UID 均未进入 B 或 C 候选池。
因此不能为了凑三个 demo case 而声称候选池已经包含正确酶。

### 3.4 本地建议与待裁定项

本地建议采用 **C 的受限变体 C\***：

```text
1 个 strong 污水 plausible case
+ 1 个 medium 污水 plausible case
+ 1 个 weak P0 技术边界 case（不宣称污水相关）
```

理由：它最大程度保留老师要求的业务场景和能力上下限，同时不虚构不存在的弱档
污水证据。具体 reaction SHA256 暂不冻结，先由学生对 9 个 plausible 候选做
机理证据自审，再由老师决定是否适合作为业务 case。

请老师裁定：

```text
M3D1-A：批准受限 C*；第三个 weak case 只作技术边界，不声称污水相关。（本地建议）
M3D1-B：三个 case 全部采用污水 plausible 候选，接受只有 strong/medium、没有 weak。
M3D1-C：退回纯 A，先完成强/中/弱技术联调，不承担污水业务代表性。
M3D1-D：坚持原始 C；另行授权弱档污水数据或新反应/fallback 专项，M3 暂不启动。
```

无论选择哪项，9 个候选都仍需人工机理审查；当前报告不选择最终 case。

---

## 四、决策 2：`enzyme_pool_uids` 来源

### 4.1 在线 API 与本地数据的真实边界

2026-07-17 保存了 14 次有界官方接口探测及重试证据。能够确认的是当天 HTTPS
接口可访问和部分 ID 映射文档存在；不能确认的是：

```text
任意 reaction SMILES -> EC：未建立
Rhea/KEGG 官方 reaction similarity API：保存证据未证明
长期稳定性或生产 SLA：未建立
无需凭据的 BRENDA 通用查询：未建立
```

当前已接受的 EC、Rhea 和 UID 数据主要来自固定下载的 Rhea 140 官方文件：

```text
rhea-directions.tsv
rhea2ec.tsv
rhea2uniprot_sprot.tsv
rhea-reaction-smiles.tsv
```

处理方式是离线精确连接，不是在线逐条查询，也不是大模型生成。对 451 个 P0
反应，精确 Rhea-ID/EC 覆盖为 294/451（280 个单 EC、14 个多 EC、157 个缺失）。

6,151 个完整 EC 的 D4-valid UID 池分布为：

```text
zero:       3322
1--49:      2428
50--100:     113
101--200:     89
>200:        199
median:         0
max:         2139
```

因此“EC 下通常有 50--200 个可用酶”不符合当前冻结资产实测；只有 113/6,151
个 EC 的 D4-valid pool 位于 50--100。

### 4.2 B/C 公平候选池基准

M3-P0B 的 B 索引包含查询反应自身正例行，原比较被本地拒绝。M3-P0B1 已在构建
B 索引前全局排除全部 451 个查询反应 SMILES，并保持 C 的原始 EnzymeCAGE
top-10 相似反应证据不变。最终独立重算结果为：

#### 4.2.1 本次比较使用了什么数据

本次是固定数据、CPU-only、无网络的候选池能力实验。输入边界为：

```text
P0 query：451 个唯一反应
可评估 query：450 个
无已知正例 query：1 个
可评估 query 的已知正例 UID 行：10,804

正式 train/valid/test：
  623,854 / 79,563 / 70,815 行
正式 Label=1：
  109,129 / 14,156 / 10,804 行，合计 134,089
正式正例反应：4,501
排除全部 P0 query 后的参考反应：4,051
正式正例映射 UID：107,602
D4 完整资产 UID 域：107,705
```

Rhea/EC 证据只使用固定下载的 Rhea 140 本地文件；没有在线逐反应调用 API，
没有大模型生成 EC，也没有从 UniProt/Swiss-Prot 全库临时补 UID。

#### 4.2.2 公平比较前怎样防止目标泄漏

本次先固定全部 451 个 query reaction SMILES，再执行以下排除：

```text
B fair：构建 EC -> UID 索引时，排除全部 451 个 query reaction 的正例行；
C：从参考反应域全局排除全部 451 个 query reaction；
C per-query：再排除与当前 query 共享 Rhea master 的参考反应。
```

已知正确 UID 只在候选池构造完成后用于计算 hit/recall，不参与公平路线的候选
选择。唯一例外是明确标为上界诊断的 `B oracle query-excluded`，它使用已知
正例行 EC，因此不参与 B/C 公平配对。

#### 4.2.3 B 路线本次具体怎样构造

公平 B 使用 `b_query_excluded`，步骤是：

```text
1. 从 P0 inventory 读取 query 已知 Rhea ID；
2. 通过 rhea-directions.tsv 精确归一到 Rhea master；
3. 通过 rhea2ec.tsv 只取格式完整的官方四级 EC；
4. 从正式 train/valid/test 的 Label=1 行建立 EC -> UID 索引；
5. 建索引前全局删除全部 451 个 query reaction 的行；
6. 每行只使用该行显式记录且经 Rhea master 校验的完整 EC；
7. 不因一个 Rhea master 具有多个 EC 而把其他 EC 的 UID 交叉扩入；
8. 合并 query 精确 EC 对应的 UID，形成 D4-valid B pool。
```

同时保留两个不能与 C 当作公平结果的诊断：

```text
b_direct_metadata：索引包含 query 自身正例，只表示已知元数据查表覆盖；
b_oracle_query_excluded：使用已知正例行 EC，是条件上界。
```

报告中所有 B/C 公平结论只比较 `b_query_excluded` 与 `c_original_top10`。

#### 4.2.4 C 路线本次具体怎样构造

公平 C 使用原版 EnzymeCAGE 的相似反应召回思路，步骤是：

```text
1. 以排除 query 后的 4,051 个正式 Label=1 反应作为参考域；
2. 对 query 和参考反应两侧分子做 RDKit 处理；
3. 使用 Morgan radius-8 指纹和 Tanimoto 分子相似度；
4. 对反应物/产物分子做贪心一对一配对；
5. 分别计算同向和反向反应相似度，取二者较大值；
6. 按相似度降序、反应 SHA256 稳定打破并列，取 Top-10 参考反应；
7. 汇总这 10 个反应在正式正例映射中的 D4-valid UID 并去重，形成 C pool。
```

本次没有复现原版约 32 万正向配对的全部候选域，也没有叠加原版候选预排序中的
taxonomic distance/protein evidence 分数；它复现的是原版反应相似度 Top-10
召回逻辑，并把候选 UID 限制在当前冻结正式数据和 D4 可计算资产域。

#### 4.2.5 本次究竟评价了什么

对每个可评估 query，先取其 10,804 行已知正例中属于该 query 的 UID 集合，再
计算：

```text
nonempty：候选池是否非空；
hit：候选池与该 query 已知正例 UID 是否至少有一个交集；
recovered：一共召回多少已知正例 UID；
micro recall：全部召回正例 UID / 10,804；
pool distribution：min / median / P90 / P95 / max；
paired outcome：BOTH / B_ONLY / C_ONLY / NEITHER。
```

本实验没有加载 checkpoint、没有执行 EnzymeCAGE 推理、没有比较候选的模型
rank，也没有测试 B+C 合并后的排序。因此它回答的是“正确酶有没有进入候选池”，
不是“模型最终能不能把正确酶排到前面”。

| 路线 | 非空 query | 命中 query | 正例 UID 召回 | pool min/median/P90/P95/max |
|---|---:|---:|---:|---:|
| B direct metadata | 294/450 | 294/450 | 9787/10804 = 90.59% | 0/1/47/139/761 |
| B query-excluded | 93/450 | 91/450 | 2884/10804 = 26.69% | 0/0/3/9.1/761 |
| B oracle query-excluded | 91/450 | 91/450 | 2879/10804 = 26.65% | 0/0/3/9.1/761 |
| C original top-10 | 450/450 | 246/450 | 3324/10804 = 30.77% | 1/61.5/724.7/1267/3078 |

`B direct metadata` 包含目标自身记录，只能说明元数据查询覆盖，不能作为预测召回
或与 C 的公平比较。公平配对只比较 `B query-excluded` 与 C：

```text
BOTH=77
B_ONLY=14
C_ONLY=169
NEITHER=190
```

该结果说明 B 和 C 存在互补，但没有完成混合路线的模型排序实验，也不能把
`B_ONLY + C_ONLY` 直接包装成已验证的混合系统效果。

### 4.3 原版 EnzymeCAGE 为什么能使用 C 路线

本地原版代码和 README 支持以下有限而明确的结论：

```text
目标反应
-> 从正向反应-酶数据库中排除全部待检索反应及显式 exclude_rxns
-> 计算目标反应与其余已知反应的相似度
-> 取 top-10 相似反应
-> 汇总这些反应已记录的 UID
-> 构造目标反应 x 候选 UID 配对
-> 再由 EnzymeCAGE 推理排序
```

`retrieve.py` 把候选数据库定义为约 32 万条正向酶-反应对，并明确执行：

```python
all_cand_rxns = set(df_db[smiles_col]) - exclude_rxns - rxns_to_retrieve
cand_enzs = RXN_TO_UID.get(cand_rxn, [])
```

因此原版 C 不是从一个与反应注释无关的通用酶库随意追加候选，而是利用较宽的
已知反应-酶映射做召回；README 中的 `Orphan-335` 也明确先运行 `retrieve.py`，
再运行 `infer.py`。这解释了 C 的正确定位：**相似反应负责候选召回，
EnzymeCAGE 负责池内排序**。

本次 C 基准不能解释为“原版方法失效”，原因如下：

1. C 为全部 450 个可评估 query 形成非空 pool，并在 246 个 query 中召回至少
   一个已知正例，说明路线确实具有召回能力。
2. 204/450 个 query 未召回任何已知正例，且 pool 最大达到 3,078，说明该能力
   并非对所有反应稳定，也不能从若干论文案例推广为普遍成功。
3. 本次对全部 451 个 P0 查询反应做全局排除，严格阻止目标反应自匹配泄漏。
   但必须说明：原版 `retrieve.py` 本来也会排除 `rxns_to_retrieve`，所以“排除
   自身”是公平评估和原版检索共同遵守的原则，不是本次额外削弱 C 的人为条件。
4. 本次是覆盖 450 个可评估反应的系统性候选召回测试，不是只展示成功个案；
   评价对象是“已知正例是否入池”，尚未运行 EnzymeCAGE 最终排序。
5. 本次 C 的邻居只汇总当前正式数据中具有完整 D4 资产的 UID，参考域为排除
   query 后的 4,051 个反应、D4-valid UID 域为 107,705。它不是对原版约 32 万
   正向配对数据库和所有潜在外部酶的无条件复现。
6. 已知正例 UID 是当前观测标签，不是所有真实可催化酶的穷尽真值；pool miss
   证明未召回已知正例，但不能证明池内所有其他酶都无催化可能。

所以当前应报告为：**C 可用但召回不完整、池规模不稳定；B 更窄但覆盖更低；
两路均不能单独保证正确酶入池，也均不应在老师裁定前被放弃。**

### 4.4 候选酶全集与模型资产池必须分开

用户提出的“B 找到当前全量资产库外的酶后，为其补齐特征再送入模型”在技术
方向上有道理，但解决的是**候选已找到却不可计算**，不是**B/C 没有召回正确
候选**。建议把三个集合分开记录：

本节只申请老师判断这个方向是否值得进入下一轮方案设计，不是资产扩充实施
合同。当前不预先指定用哪个酶库扩充、下载哪个版本、使用哪套结构/口袋工具、
复用或改写哪段代码，也不预先承诺扩充规模、成功率和完成时间。老师同意方向后，
再逐项调研、比较并请老师确认具体实现。

```text
1. biological_candidate_universe
   完全相同反应已知酶 / 可靠完整 EC 对应酶 / top-10 相似反应对应酶

2. d4_computable_asset_pool
   已同时具备冻结 v1 所需序列、结构/口袋、ESM、pocket-node ESM、GVP，
   且通过身份、维度和节点对齐验证的候选

3. asset_completion_queue
   已有可追溯候选依据，但缺少一项或多项模型资产、暂不能评分的候选
```

其中“完全相同反应已知酶”只适用于真实部署时的已知反应查询；在本次 held-out
候选召回基准中仍必须排除目标反应自身，不能把直接命中作为预测能力。

还必须澄清：当前 B 基准并没有在线查询 UniProt/Swiss-Prot 全库下某个 EC 的
所有酶。它只使用正式 `Label=1` 行中明确记录的完整 EC，并与 D4-valid UID 域
对齐。因此“B 已找到当前资产库外 UID”目前尚无实测清单。要执行用户建议，
必须先建立并冻结一个可追溯的 `complete EC -> external UID/sequence` 数据源，
再把新增 UID 分入资产完整、待补资产或无法补齐三类。

对候选 UID 应保留三类状态：

```text
A：资产完整 -> 可进入当前模型排序
B：资产缺失但可能补齐 -> 进入独立资产补齐队列
C：当前无法补齐 -> 保留为未评分候选，不得写成低分或负例
```

原版仓库提供了技术可行性证据，但不能被写成当前已经具备的能力：

1. `feature/main.py` 可从给定 UID 和序列计算全序列 ESM 表征。
2. GVP 和 pocket-node ESM 还要求可用蛋白结构、口袋坐标和残基映射；只有序列
   不能完成完整模型输入。
3. 代码会检查 GVP 与 pocket-node ESM 节点数；推理数据加载也会取候选 UID、
   GVP 和 ESM 资产的交集，缺资产 UID 可能在模型评分前被移除。
4. README 对外部 P450、terpene synthase 和 phosphatase 测试集要求先生成特征，
   说明预先确定的外部候选可以另算资产；这不等于原版 C 自动连接一个未注释
   通用酶库，也不证明所有外部酶都能成功生成结构和口袋。

若老师授权，候选优先的有界资产补齐流程应另立合同并至少包含：

```text
候选 UID/序列及来源快照
-> 实验结构或固定版本预测结构
-> 固定口袋提取/预测方法
-> 全序列 ESM
-> pocket-node ESM
-> GVP pocket feature
-> UID、序列、结构、口袋、节点和维度对齐
-> 与冻结 v1 特征语义兼容的独立验证
-> 注册为可评分资产
-> 目标反应 x 候选酶配对打分
```

上面只是模型所需信息链条，不表示已经选择其中任何数据源或软件。老师原则同意
后，下一轮至少需要共同商定：

```text
1. 候选酶来源：采用哪个权威酶库或哪些库的固定快照，是否只取 reviewed 条目；
2. 收录边界：按完整 EC、Rhea 已知映射、特定酶家族还是三案例按需扩充；
3. 去重与质量：UID/序列版本、isoform、片段、异常长度和重复序列如何处理；
4. 结构来源：实验结构、已有预测结构或另行结构预测的优先级与许可边界；
5. 口袋方法：沿用已有口袋资产逻辑还是采用新的固定工具和参数；
6. 特征代码：复用原版 feature 代码、适配当前正式 3B/v1 流程，还是写独立脚本；
7. 兼容验收：ESM/GVP 维度、节点对齐、UID/序列身份、manifest 和负向测试；
8. 执行规模：先做三案例按需试点，还是建设可复用扩展库；
9. 与 D4/M3 的关系：作为 M3 前置子任务、M3 内支路，还是 M3 后专项。
```

这些均为老师批准方向后的下一轮待讨论问题。本报告不替老师选择答案，也不据此
启动下载、特征生成或 HPC 运行。

该方案不需要为了补资产而虚构新的反应-酶训练标签；如果只新增模型输入资产，
原则上也不等同于重新训练模型。但新增资产能否与冻结 v1 特征生成参数、维度、
语义和 wrapper 行为兼容，仍必须独立验证，不能仅凭文件存在就并入 D4。

还需警惕以下风险：结构或口袋可能不可得/预测失败，GVP 与 ESM 节点可能错位，
资产覆盖会偏向研究充分的蛋白和物种，批量预计算所有 6,151 个完整 EC 的全部酶
可能规模过大。当前也没有完成“D4-valid 交集前后的 B/C 召回差额”实验，因此
不能先声称资产扩充一定能补回多少 query 或正确 UID。

### 4.5 本地建议与待裁定项

两条路线的作用和风险应并列呈现：

| 路线 | 当前优势 | 当前限制 | 适合承担的角色 |
|---|---|---|---|
| B：完整 EC 索引 | 功能类别明确；命中时 pool 通常较小；来源可精确追溯 | 任意 SMILES-to-EC 未建立；157/451 无精确 EC；大量 EC 在 D4 域为 zero pool；同 EC 也不保证具体底物适配 | 高置信完整 EC 存在时的窄召回支路 |
| C：top-10 相似反应 | 不依赖 EC；符合原版 Orphan 检索；450/450 非空，命中 246/450 | 相似化学转化不等于相同催化能力；204/450 未命中；pool 可远超 100 | 无 EC 时的主要召回支路及 B 的互补证据 |
| B+C 编排 | `B_ONLY=14`、`C_ONLY=169` 证明存在互补 | 尚未做并集/分阶段压缩后的正确 UID 保留和最终排序；不能直接把互补计数写成系统效果 | 待老师裁定的 M3 架构候选 |
| 外部资产补齐 | 可让已召回但缺资产的候选获得评分机会 | 不产生候选、不修复错误 EC/错误邻居；当前无固定外部 EC-UID 源和兼容流水线 | B/C 之后的独立资产层 |

不建议方案 A 全局 pool。当前 D4-valid UID 域为 107,705，不是约 1,000 个；
全局排序不符合已验证的 50/100 候选运行范围。

不建议 B-only。B 在有可靠完整 EC 时可复现且通常较小，但精确 EC 覆盖不足、
大量 EC 无 D4-valid UID，公平基准只命中 91/450。

不建议直接锁定 C-only。C 对所有 450 个可评估查询都能形成 pool，命中
246/450，但池规模可达 3,078，候选池非空也不等于包含正确酶。这不是建议放弃
C，而是建议保留 C 的原始召回职责、provenance 和独立结果，同时控制池规模。

本地建议老师批准 **B-primary / C-fallback**，并保留独立 `EnzymePoolAgent`：

```text
1. 对 M3 的 P0 demo，候选参考索引继续排除全部 451 个 P0 查询反应，避免泄漏。
2. 若目标反应能在固定 Rhea 140 中精确匹配完整 EC，先构造 B pool。
3. 无完整 EC 或 B pool 为空时，使用原始 EnzymeCAGE top-10 相似反应路线 C。
4. 不默认把 B 与 C 全量取并集，不把 EC 置信度混入 EnzymeCAGE score。
5. 每个 case 分别记录候选来源、EC/邻居 provenance、pool 大小、正确 UID 是否
   入池，以及最终 EnzymeCAGE rank。
```

该“primary/fallback”只是受当前 D4 规模约束的 M3 v1 编排建议，不代表 B 的
召回能力优于 C。若仅在 B 为空时才触发 C，可能遗漏“B 非空但未含正确酶、C
反而命中”的 query；当前 paired 结果不足以证明该触发规则最优。因此 M3 证据中
应至少同时保存 B、C 的独立候选结果，是否并集、分阶段评分或压缩后合并仍由
老师在 `M3D2-A/B` 中裁定。

该方案的互补性有候选池证据支持，但完整混合编排和 EnzymeCAGE 排序尚未实现或
验证，必须在老师批准后进入 M3-P2/P3。

还需老师明确一个会改变实现的口径：D4 只正式 smoke 到 100 candidates，而 C
最大 pool 为 3,078。当前没有验证过“截断后仍保留正确酶”。请裁定：

```text
M3D2-A：批准 B-primary/C-fallback；M3 v1 只选择去重后 pool <=100 的 3 个 case，
      pool >100 明确 fail closed，不静默截断。（本地建议）
M3D2-B：批准混合路线，并授权 M3-P2 先增加 pool 压缩/截断基准，再选择 case。
M3D2-C：只批准 B，EC 缺失或 zero-pool 时 fail closed。
M3D2-D：只批准 C，并允许完整大 pool 进入 wrapper；需另行补 >100 性能门控。
```

上述 B/C 路线裁定与“是否补外部酶资产”是两个独立问题。无论老师选择 B、C
还是混合路线，都可能召回当前 D4 资产域外的 UID；反过来，资产库再大也不能
修复检索路线根本没有召回正确酶的问题。请老师再裁定资产边界：

```text
M3D2E-A：M3 v1 保持 D4 冻结资产域；域外候选保留 provenance 并标记未评分，
         不在 M3 内生成新资产。（最保守、与当前 D4 合同一致）
M3D2E-B：授权仅对老师最终选定 case 的 B/C 域外候选做候选优先、按需资产补齐；
         先单独完成来源、成本、失败率和冻结 v1 兼容性验证，通过后才能评分。
M3D2E-C：授权规划可复用的扩展酶资产库；先提交 UID 来源范围、规模、结构/口袋
         策略、算力成本、版本冻结和验收合同，不直接全量预计算后并库。
```

三个 `M3D2E` 选项也只是范围级裁定：A 表示本轮不扩，B 表示允许先设计小范围
按需试点，C 表示允许先设计可复用资源。选择 B/C 都不等于老师已经批准某个
数据库、程序、参数或正式执行；具体合同仍需下一轮单独提交。

本地不把资产扩充写成 M3 既定任务。若老师要求当前 M3 仍严格沿用已验收 D4，
应选 `M3D2E-A`；若老师认为“已召回但缺资产”的候选必须进入本次三案例排序，
则建议在 `M3D2E-B` 和 `M3D2E-C` 中优先选择范围更小、可审计的 `M3D2E-B`。

---

## 五、决策 3：Substrate Agent 与 Reaction Agent 实现深度

### 5.1 当前真实状态

老师草案中的三个 Pydantic schema、四个 Agent、两个工具绑定、三个编排边和
两类测试目前均未找到 live implementation。缺口矩阵共 14 项，均为 MISSING。

当前可用能力只有：

```text
固定反应的离线 Rhea/EC 精确连接；
冻结反应集合上的 RDKit/Morgan/Tanimoto 相似反应检索；
D4 冻结预计算资产域内的 EnzymeCAGE wrapper 排序。
```

当前不可用能力包括：

```text
从任意污水自然语言稳定解析并校验底物；
从任意底物预测新反应；
为新反应直接预测 EC；
为新反应在线生成 D4 所需特征资产；
资产域外继续完成 EnzymeCAGE 推理。
```

RXNMapper 是原子映射工具，不是 EC 分类器。`MissingReactionAssetError` 是
fail-closed 异常，不是预测分支。

### 5.2 本地建议

建议采纳老师倾向的最小可用版，但把运行域写清楚：

```text
Substrate Agent：只完成 3 个已裁定 case 的确定性底物解析与 provenance 输出；
Reaction Agent：只返回固定库中 retrieved、可追溯、具有 D4 资产的反应；
CandidateReaction.source：M3 v1 实际只产生 "retrieved"；
fallback_used：M3 v1 正常路径固定为 false；
无匹配或缺资产：明确 fail closed，不伪装成 predicted fallback；
prompt 迭代：等最小链路和 3 case 基线完成后再做，不作为 M3 启动前门槛。
```

不修改老师给出的 schema，不增加“unsupported”字段，也不把异常写成成功输出。

请老师裁定：

```text
M3D3-A：批准上述 retrieved-only、资产域内、最小可用版。（本地建议）
M3D3-B：M3 必须包含真实 predicted fallback；则需先单独发布新反应预测与资产生成
      任务，当前 M3-P1 暂不能启动。
M3D3-C：先做 prompt 迭代和 3 case 优化，再进入 M3 主链。
```

---

## 六、决策 4：M3 验收标准与审核角色

本地建议采纳老师倾向的 **B：链路跑通 + 合理性人工审核**，审核顺序为：

```text
学生基于证据逐 case 自审
-> 老师最终复核
-> 外部专家可选/延后，不作为 M3 demo 收官硬门槛
```

三层上游不确定性不应全部转嫁为“至少 2/3 正确酶进入 Top-K”的硬验收门槛，
但定量结果仍必须逐 case 披露，不能因为采用 B 就省略。每个 case 至少记录：

1. 每一 stage 是否完成、schema 是否有效。
2. 反应来源、Rhea/EC 或相似邻居 provenance。
3. pool 构造路线、大小及正确 UID 是否入池。
4. 正确 UID 的 EnzymeCAGE rank、Top-10/Top-50 可见性；缺失时明确写未召回。
5. EC class、反应机理和污水业务相关性的引用与人工判断。
6. 上游不确定性、batch-context sensitivity 和预计算资产域警告。
7. 不把 rank 1 表述为现实世界最优酶。
8. 学生自审、老师复核和外部专家状态分别记录。

请老师裁定：

```text
M3D4-A：批准 B，学生证据自审 + 老师最终复核；外部专家延后。（本地建议）
M3D4-B：批准 B，但 M3 收官前必须增加外部专家复核。
M3D4-C：改用定量硬门槛；请同时明确 K、至少通过 case 数和 pool-miss 如何计分。
```

---

## 七、请老师一次性裁定的实施口径

为避免 M3-P1 后再次返工，请老师明确回复以下四项原始决策，并在决策 2 下
补充确认资产边界：

```text
1. case：M3D1-A / M3D1-B / M3D1-C / M3D1-D
2. pool：M3D2-A / M3D2-B / M3D2-C / M3D2-D
2E. 域外候选资产：M3D2E-A / M3D2E-B / M3D2E-C
3. Agent：M3D3-A / M3D3-B / M3D3-C
4. 验收：M3D4-A / M3D4-B / M3D4-C
```

若老师采用本地建议，则正式实施基线为：

```text
M3D1-A + M3D2-A + M3D2E-A + M3D3-A + M3D4-A
```

其中 `M3D2E-A` 只是当前已验收 D4 边界下的保守基线，不否定后续资产扩充。
如老师选择 `M3D2E-B` 或 `M3D2E-C`，将在 M3-P2/P3 前先增加独立资产补齐
preflight、兼容性验证和验收包，不把它静默塞入既有 D4 wrapper。

收到裁定后再按老师原节奏执行：

```text
M3-P1：Substrate Agent + Reaction Agent 最小可用版
M3-P2：EnzymePoolAgent + 离线 EC 索引 + 相似反应回退工具
M3-P3：EnzymeCAGEAgent + orchestrator
M3-P4：3 case 端到端、m3_e2e_report.md、本地审计
```

M3-P1 开始前仍会先把老师裁定转写为逐项可验证合同，不会直接依据本文件中的
本地建议开工。

---

## 八、已完成、未完成和禁止越界项

### 已完成并本地闭环

```text
D4 v1.1 老师正式验收；
P0 rank/difficulty、污水候选、Rhea 140、EC/UID 分布和 API 能力证据；
B/C 查询泄漏修正后的公平候选池基准；
原版 C 检索代码、外部测试集特征生成入口和缺资产过滤边界核对；
A1A 与 B1 目录、manifest、tar、identity 独立审计；
四项决策的本地建议、B/C 路线解释和域外候选资产待裁定问题。
```

### 尚未完成且必须如实保留

```text
最终三个 case 的生物学审核与冻结；
B/C/hybrid 正式架构选择；
大于 100 候选的压缩、性能和正确酶保留验证；
未经过 D4-valid 资产交集的 B/C 候选全集召回、资产缺口规模与可补齐率基准；
外部 UID/序列来源快照、结构/口袋策略、资产生成流水线和冻结 v1 兼容性验证；
任何 live Agent、tool binding、orchestrator 和 M3 e2e 测试；
任意新反应预测、任意 SMILES-to-EC、在线资产生成；
老师对 M3-P0 的正式裁定。
```

### M3 当前仍不做

```text
metaTraits 接入；
酶到微生物反查；
Design Explaining Agent；
FastAPI 服务化；
把候选池命中、Top-50 可见或规则匹配包装成真实降解效果；
把本地审计通过写成老师已经验收。
```

---

## 九、证据索引

老师要求与 D4 已验收依据：

```text
00_Authority_Teacher_Plan/
TEACHER_REPLY_D4_ACCEPTED_AND_M3_STARTUP_PACKAGE_2026-07-16.md
```

最终 M3-P0A1A 证据包：

```text
03_HPC_Returned_Result_Summaries/
m3_p0a1a_decision_matrix_distribution_final_package_correction_20260717/
```

最终 B/C 公平基准包：

```text
03_HPC_Returned_Result_Summaries/
m3_p0b1_b_query_leakage_control_fair_bc_correction_20260717/
```

原版 EnzymeCAGE 本地代码依据：

```text
retrieve.py
README.md
feature/main.py
enzymecage/dataset/geometric.py
```

其中 `候选酶来源证据.md` 和 `候选酶资源扩充.md` 仅作为问题分析输入，不作为
老师权威文件或已验证结果；本报告只采用其中能被原版代码、README 或已接受
M3-P0 证据包支持的结论。

独立本地审计：

```text
04_Local_Review_Audits/
ENZYMECAGE_M3_P0A1A_DECISION_MATRIX_DISTRIBUTION_FINAL_PACKAGE_LOCAL_AUDIT_2026-07-17.md
ENZYMECAGE_M3_P0B1_B_QUERY_LEAKAGE_CONTROL_FAIR_BC_CORRECTION_LOCAL_AUDIT_2026-07-17.md
```

---

## 十、治理声明

本文件坚持老师要求的三条纪律：

1. **边界如实披露**：负面结果、zero pool、API/Agent/fallback 缺口和候选池 miss
   均完整保留。
2. **表述不越界**：候选入池不等于 EnzymeCAGE 排名成功，排名成功不等于真实
   污水降解有效，规则匹配不等于专家验证。
3. **收尾权限自觉**：当前结论是本地证据闭环并提交老师裁定，不写成老师已经
   批准 M3 路线，也不在回复前启动实现。
