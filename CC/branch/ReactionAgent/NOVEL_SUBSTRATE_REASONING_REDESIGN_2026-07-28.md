# 未知底物 X → 产物 Y 的新一代推理与训练方案

> 日期：2026-07-28  
> 基于：`HANDOFF_ENGINE_2026-07-23.md`、开发计划、`verify_substrate_retrieval.py`、`engine.py`、`reaction_scorer.py`  
> 目标：跳出“单个最近邻 donor + 固定模板迁移”的局限，同时保留现有引擎已经验证有效的规则外推与反应族证据。

---

## 1. 先给结论

现有系统不是失败，而是完成了一个很有价值的第一阶段：

> 它已经证明：当一个合适 donor 的模板能够生成真产物时，DRFP-酶反应族相似性可以帮助候选排序。

但它还没有证明：

> 对任意未知 X，只凭 X 本身，就能可靠地选择反应类型、找到反应位点、生成正确产物并给出校准过的置信度。

真正的新路线不应继续围绕“怎样找一个更像的 donor”小修小补，而应把问题改写为：

> 从多个已知反应中归纳“可迁移的转化概念”，再联合推断 X 的反应类型、反应位点、结构编辑、酶可行性和适用域。

最值得优先建设的是一个“神经—符号混合的类比推理系统”：

1. 多证据检索多个 support reactions，而不是押注一个 donor。
2. 从 support set 归纳 transformation prototype，而不是固定使用半径为 1 的模板。
3. 独立预测 X 上可能发生反应的原子/键位点。
4. 通过受化学约束的图编辑生成产物。
5. 使用 listwise ranker 联合评估位点、转化、酶、守恒和适用域。
6. 允许输出“证据不足/拒答”，而不是每个 X 都强行给一个高分产物。
7. Agent 负责组织检索、模型、规则、反证和证据报告，不负责凭语言直觉直接写 SMILES。

---

## 2. 当前 67.1% 的真实含义

`verify_substrate_retrieval.py` 的评估逻辑中存在多层条件筛选，因此 67.1% 是“条件排名能力”，不是端到端预测准确率。

### 2.1 只评估已经生成出真产物的案例

脚本只有在候选集合包含 `Y_true` 时才把案例计入 `n_case`。因此：

- 候选生成失败的案例不进入分母；
- donor 反应类型选错的案例不进入分母；
- 模板无法覆盖 X 的案例不进入分母；
- 正确转化不存在于模板库的案例不进入分母。

所以 67.1% 回答的是：

> “正确产物已在候选集合内时，排序器把它排第一的概率是多少？”

它没有回答：

> “面对一个任意未知 X，系统最终 top-1 命中真产物的概率是多少？”

### 2.2 donor 选择使用了真答案

脚本按相似度依次尝试 donor，但只有某个 donor 生成的候选包含 `Y_true` 时，才把该 donor 选为 `picked` 并进入评估。

这相当于使用真产物做了 oracle donor selection。现实预测时并不知道哪个 donor 能生成正确产物。

### 2.3 验证时使用了已知共反应物

验证脚本从 held-out 反应 `k` 中取得：

- 主底物：`reactants[0]`
- 共反应物：`reactants[1:]`
- 排序时的完整反应物侧：`r_side`

因此 donor 检索虽然只用了第一个底物，但候选生成和 DRFP 排序仍可能使用真反应里的共反应物。真实输入如果只有污染物 X，这些共反应物通常未知。

### 2.4 只排除字符串完全相同的真反应

`exclude_reaction=k` 只排除与 held-out 字符串完全一致的反应。以下近重复仍可能存在于酶反应族中：

- SMILES 顺序不同但化学等价；
- 原子映射、质子化、盐、立体标记不同；
- 同一反应被多个 UniProt 重复记录；
- 同一底物—产物转换的不同数据库版本。

必须在 canonical reaction identity 层面去重和分组，不能只比较原始字符串。

### 2.5 “有效 82 / 扫描 2500”需要拆解

82 个有效案例只占扫描量的约 3.3%。这不等于系统覆盖率就是 3.3%，因为中间还有“至少两个候选、有酶注释、模板成功”等人为条件；但它明确说明目前缺少逐阶段分母，无法知道损失发生在哪里。

后续必须报告漏斗：

```text
所有测试 X
  → 可解析
  → 有适用 donor / transformation family
  → 至少生成一个候选
  → 真产物进入 top-K 候选（generation recall）
  → 真产物 top-1 / top-3（end-to-end accuracy）
  → 高置信预测中的准确率（selective accuracy）
```

### 2.6 其他需要修正的评估细节

- `reactants[0]` 被默认成主底物，但反应物顺序未必可靠。
- `frozenset` 会丢失计量数；`true_set.issubset(candidate_set)` 允许包含额外片段的候选被视为命中。
- `except Exception: pass` 隐藏了失败类型，无法形成错误谱系。
- 引擎只选 donor 关联酶列表中的第一个可用 UniProt，酶证据可能受数据库顺序影响。
- `engine.py` 顶部仍写旧的 N=17、82.4%，与当前 handoff 的 N=82、67.1% 不一致。

### 2.7 35% 生成召回与 67.1% 条件 top-1

如果二者来自完全相同的严格测试集，粗略端到端 top-1 会受两者乘积约束：

```text
generation recall × conditional ranking accuracy
≈ 0.35 × 0.671
≈ 0.235
```

但当前两组数字来自不同实验与筛选条件，不能正式相乘。这个计算只能用于说明：

> 排序器再强，也无法补救没有生成出来的正确产物；下一阶段的第一瓶颈很可能是 reaction family/site/candidate coverage，而不是继续优化 DRFP 排序。

---

## 3. 把任务重新定义成潜变量推断

不要直接学习：

```text
X → Y
```

而应显式建模：

```text
X
→ 可能的转化族 T
→ X 上的反应位点 S
→ 局部图编辑 Δ
→ 候选产物 Y
→ 可能催化的酶/EC E
→ 在环境 C 中的发生可能性
```

可以写成：

```text
p(Y, T, S, Δ, E | X, C, support reactions)
```

其中：

- `T`：氧化、还原、水解、脱卤、羟基化、裂解、转移等转化概念；
- `S`：X 上被改变的原子或键；
- `Δ`：加键、断键、键级变化、原子电荷变化、基团增删；
- `E`：EC、具体酶或酶家族；
- `C`：好氧/厌氧、土壤/污泥/水体、pH、共因子、菌群等上下文；
- `support reactions`：模型为当前 X 动态检索到的 Aᵢ→Bᵢ 证据集。

这样做的意义是：错误可以被定位。

- `T` 错：反应类型检索/分类问题；
- `S` 错：区域选择性问题；
- `Δ` 错：化学转化表示问题；
- `Y` 无效：解码和化学约束问题；
- `E` 错：酶—底物兼容性问题；
- `C` 不支持：环境可实现性问题。

---

## 4. 最值得尝试的新训练范式：episodic reaction analogy learning

这条路线最贴近你的原始目标：“Agent 看 A→B 后，推断 X 会变成什么”，但比普通最近邻迁移更严格。

### 4.1 一个训练 episode 怎么构造

先按“真实化学变化”聚类反应，例如用：

- 原子映射后的 bond-edit signature；
- 反应中心局部图；
- EC3/EC4；
- 反应模板；
- cofactor/redox 类型；
- 以上信息的组合。

每个 episode：

1. 采样一个 transformation family `T`。
2. 从该族取 K 条支持反应：
   `S_T = {A₁→B₁, A₂→B₂, …, A_K→B_K}`。
3. 再取同族但不同底物骨架的一条 query reaction：
   `X→Y_true`。
4. 加入若干来自相似底物但不同 transformation family 的干扰反应。
5. 模型根据 support set 和 X 预测：
   - transformation family；
   - X 上的 reaction site；
   - graph edits；
   - Y；
   - 是否应拒答。

这比“普通监督训练 X→Y”更适合你的目标，因为训练过程本身就要求模型学会：

> 如何从临时提供的 A→B 证据中抽象转化，再应用到新的 X。

### 4.2 模型结构建议

```text
Support encoder
  Aᵢ、Bᵢ → 原子级表示
  Aᵢ→Bᵢ → edit/delta 表示
        │
        ▼
Transformation prototype aggregator
  对多条 support 做 attention / set pooling
  得到当前 episode 的转化原型 z_T
        │
        ├─────────────┐
        ▼             ▼
Query site head     Edit head
对 X 每个原子/键     在候选位点预测图编辑
预测反应概率         并生成 Y
        │             │
        └──────┬──────┘
               ▼
Candidate ranker + abstention head
```

关键不是一定使用哪一种 GNN/Transformer，而是保持信息结构正确：

- support reaction 的“变化”与 query molecule 的“可反应位置”必须通过 cross-attention 交互；
- 不能把多个 donor 只压成一个最大相似度；
- 输出应是图编辑或受约束模板，而不是无约束 SMILES 文本。

### 4.3 推荐损失函数

```text
L =
  λ1 · L_family
+ λ2 · L_site
+ λ3 · L_edit
+ λ4 · L_product
+ λ5 · L_listwise_rank
+ λ6 · L_contrastive
+ λ7 · L_calibration_or_abstention
```

- `L_family`：转化族分类；
- `L_site`：原子/键级反应位点预测；
- `L_edit`：图编辑类型；
- `L_product`：最终产物图正确性；
- `L_listwise_rank`：同一 X 的候选列表整体排序；
- `L_contrastive`：正确 support/query 转化匹配靠近，干扰 donor 远离；
- `L_calibration_or_abstention`：在无适用证据时学会拒答。

### 4.4 必须加入“无反应/不适用”任务

真实系统必须能够说：

> 当前数据库中没有足够相似的转化证据，无法有依据地预测。

训练中需要负例：

- 同一 X 上错误位点的 counterfactual negatives；
- 正确底物配错误 transformation family；
- 正确酶配不兼容底物；
- 化学上可生成但环境中不支持的候选；
- 如果能获得实验 assay negatives，应与合成负例分开标记。

注意：合成负例只表示“模型应降低优先级”，不能被解释为“生物学上绝对不会发生”。

---

## 5. 检索不应只看全分子 Morgan 相似度

当前检索倾向找到“整体长得像”的底物，但真正决定反应迁移的往往是局部反应环境。

建议建立多视角索引：

| 检索视角 | 回答的问题 |
|---|---|
| 全局 scaffold 相似 | 整体化学空间是否相近？ |
| 局部 reactive motif 相似 | X 是否含有可接受同类编辑的局部结构？ |
| transformation embedding 相似 | A→B 的变化是否与当前假设一致？ |
| EC / enzyme family | 哪类酶通常实现这种变化？ |
| cofactor/context | 这种变化需要哪些隐含条件？ |
| pathway/environment | 在目标环境中是否被观察过？ |

### 5.1 从“单 donor”改成“证据集合”

检索目标不再是：

```text
argmax similarity(X, A)
```

而是：

```text
选出一个既相关又有多样性的 support set
```

可使用 MMR 或分层采样避免 top-5 全是近重复：

- 2 条高全局相似；
- 2 条高局部反应中心相似；
- 1 条同 transformation family、不同 scaffold 的远程类比；
- 1 条反例或竞争反应。

这让模型看到“什么是共同变化”和“什么只是骨架巧合”。

### 5.2 多尺度模板，而不是固定 radius=1

不同酶的底物 promiscuity 不同，固定模板半径不可能对所有酶都最佳。

建议为每个 transformation family 或 enzyme family 建立模板层级：

```text
最泛化核心
  └── 增加一层邻域
       └── 增加官能团约束
            └── 高特异性底物模式
```

推理时同时计算：

- 泛化模板是否匹配；
- 更具体模板匹配到哪一层；
- 当前 X 距离已知适用底物有多远；
- 该层历史 precision/recall。

EHreact 的 Hasse diagram 思路正是一个可直接借鉴的基线：它按酶已知底物中的公共子结构建立层级模板，并估计新底物适用性，而不是预设固定邻域大小。

---

## 6. 候选生成：优先学习“位点 + 图编辑”

### 6.1 推荐的混合生成器

同时保留三条候选来源：

1. **层级规则生成**
   - 高精度、可解释；
   - 对已知转化族非常可靠。
2. **site-conditioned graph edit**
   - 先预测位点，再预测键/原子编辑；
   - 可以突破固定 SMARTS 的边界。
3. **template-free Transformer 基线**
   - 直接做 `X → Y` 或 `[EC] X → Y`；
   - 用于增加覆盖和做独立模型共识；
   - 不应单独承担最终解释。

三个生成器的交集可以获得较高置信，差异可以作为不确定性来源。

### 6.2 为什么先预测 site 很重要

对于一个分子，主要歧义通常不是“有没有氧化模板”，而是：

- 氧化发生在哪个碳？
- 水解哪一个酯键？
- 脱卤发生在哪个卤代位点？
- 多个相似官能团中哪个更易被酶接近？

GLORY/GLORYx 的结构值得借鉴：先用机器学习预测 site of metabolism，再应用反应规则生成并排序产物。对你的项目，可以把人源代谢的特定规则替换为污染物微生物转化规则和酶反应族。

### 6.3 基本化学约束

所有候选在进入学习排序器前至少经过：

- RDKit sanitization；
- 原子价与芳香性检查；
- 质量/元素守恒检查；
- 显式识别新增/丢失的小分子、共因子和水；
- 电荷与质子化标准化；
- 重复产物 canonicalization；
- 不合理碎裂过滤；
- 可选的简化氧化还原/cofactor 约束。

这些规则不是最终“发生概率”，但能有效减少无意义候选。

---

## 7. 从 DRFP max-similarity 升级为证据融合排序

当前分数：

```text
score(candidate) =
max similarity(candidate reaction, reactions catalyzed by one selected enzyme)
```

问题：

- 单个偶然近邻即可给出高分；
- 只使用一个酶；
- 没有显式位点概率；
- 没有 donor consensus；
- 没有适用域惩罚；
- 分数不是校准概率。

建议新排序分数：

```text
Score(Y) =
  w1 · log p(transformation family | X, supports)
+ w2 · log p(site | X, transformation)
+ w3 · log p(edit | X, site, transformation)
+ w4 · support consensus
+ w5 · enzyme–substrate compatibility
+ w6 · reaction-family density
+ w7 · chemical/context feasibility
- w8 · out-of-domain penalty
```

其中：

- `support consensus`：多少独立 donor / 模板 / 模型支持同一局部编辑；
- `reaction-family density`：不是取单个 max，而是聚合 top-m 相似度、核密度或 prototype 距离；
- `enzyme–substrate compatibility`：使用全部合理酶/EC 的 evidence pooling；
- `out-of-domain penalty`：全局结构、局部位点、转化三层适用域。

训练方式推荐：

- 同一 X 的候选组成一个 list；
- 使用 listwise softmax 或 pairwise ranking loss；
- hard negatives 优先来自：
  - 同一规则作用于错误位点；
  - 相似 donor 的竞争转化；
  - 元素守恒但生物学不常见的候选；
  - 其他模型高分但错误的候选。

最后在严格 held-out validation 上做 temperature scaling、isotonic regression 或 conformal calibration，使“0.8”尽量具有真实频率含义。

---

## 8. Agent 应该做什么

“Agent”不应等同于一个端到端大模型。更合适的定位是证据编排器。

### 8.1 推荐的 Agent 推理循环

```text
1. 标准化 X
   - 主体结构、盐、互变异构体、质子化状态

2. 提取可反应位点
   - 官能团、潜在断键、氧化/还原位点

3. 并行提出 transformation hypotheses
   - 不同转化族、不同位点、不同环境条件

4. 为每个 hypothesis 检索 support set
   - 正例 donor、远程类比、竞争反应、反例

5. 多生成器产生候选 Y
   - 层级模板、graph edits、template-free baseline

6. 多个 critic 审查
   - 化学守恒 critic
   - transformation/site critic
   - enzyme compatibility critic
   - environment/pathway critic
   - novelty/applicability critic

7. 汇总并校准
   - 排名、置信区间、拒答判断

8. 输出证据卡
   - 支持证据、反证、适用域、待验证实验
```

### 8.2 输出不应只有一个 score

每个预测建议输出：

```text
候选产物 Y
转化类型 T
X 上的反应位点 S
具体图编辑 Δ
支持 donor（多条）
支持酶/EC（多条）
局部结构相似度
全局结构相似度
support consensus
适用域：in / borderline / out
主要反证
置信度及其校准来源
建议的实验验证方式
```

这样“有依据”不再等于“列出一条 donor”，而是完整的可审计推理链。

---

## 9. 数据层的新思路

### 9.1 不要只扩大反应数量，要提高反应可学习性

优先建设统一反应数据层：

- 原子映射；
- 反应物/试剂/共因子/产物角色；
- 主底物识别；
- 化学计量；
- reaction center 与 bond edits；
- EC 层级；
- UniProt 聚类；
- 环境条件；
- 数据来源和证据等级；
- canonical reaction identity；
- 重复、近重复和冲突记录。

EnzymeMap 已提供经校正、验证、原子映射的酶反应数据和相关训练基线，适合用来补充或交叉校验当前 4,541 条反应。ECREACT 可作为带 EC token 的 template-free forward model预训练来源。enviPath 更贴近环境污染物和微生物转化，应优先于只覆盖人源药物代谢的数据。

### 9.2 数据分层

建议把数据划成：

1. **通用酶反应预训练层**
   - EnzymeMap、ECREACT、Rhea 等；
2. **环境污染物适配层**
   - enviPath BBD/soil/sludge 等；
3. **项目高价值污染物层**
   - 真实关注底物、实验结果、阴性结果；
4. **机制与酶证据层**
   - EC、UniProt、序列、口袋、cofactor；
5. **环境上下文层**
   - 好氧/厌氧、介质、菌群、pH、温度。

先用大而泛的数据学习“化学变化语言”，再用环境数据学习“哪些变化在污染物降解中实际发生”。

---

## 10. 严格评估协议

### 10.1 三个必须分开的指标

#### A. Coverage / generation

- 有候选率；
- 真产物 top-10/top-50 candidate recall；
- 每个 X 的候选数量；
- 无效产物率；
- 正确反应位点 recall。

#### B. Ranking

- 在固定候选集上的 top-1/top-3/MRR；
- PR-AUC；
- 每个候选数区间的表现；
- 不允许 oracle donor selection。

#### C. End-to-end

- 所有 held-out X 上的 top-1/top-3/top-10；
- 没有生成真产物的案例必须进入分母；
- precision—recall / coverage—accuracy 曲线；
- 高置信子集的选择性准确率；
- abstention 后的风险。

### 10.2 拆分方式

至少做四种 split：

1. **随机 split**：只做 sanity check。
2. **scaffold split**：测试新骨架。
3. **reaction-family split/bucket**：区分已见转化和未见转化。
4. **enzyme-cluster split**：按序列相似性或 UniProt cluster 隔离。

更严格时加入：

- time split；
- product-similarity split；
- canonical reaction group split；
- source/database split；
- pollution-domain external test。

反应预测文献已经显示：随机拆分会因 scaffold/series bias 显著高估泛化性能，因此不能只依赖随机 held-out。

### 10.3 novelty 分桶

每个测试 X 同时按以下维度分桶：

- 最近底物全局相似度；
- 最近反应中心局部相似度；
- transformation family 训练频次；
- 酶家族训练频次；
- 是否缺少已知共反应物；
- 是否处于环境数据域。

这样才能知道系统到底是在：

- 插值；
- 新骨架上的同类转化；
- 新位点上的已知转化；
- 近乎未知转化。

### 10.4 逐级排除泄漏

- 不只排除原始字符串相同反应；
- canonicalize 后按反应图编辑去重；
- 同一 substrate—product 对必须同组；
- 同一反应不同 UniProt 不能跨 train/test 造成复制；
- donor 检索库必须只含训练折；
- enzyme reaction family 证据也必须只来自训练折；
- 验证时不得读取 held-out 共反应物，除非它们被显式定义为输入。

---

## 11. 四条可并行比较的研究路线

### 路线 A：保守但最可能快速提升——Site + hierarchical rules + learned ranker

组成：

- transformation family 分类；
- atom/bond site predictor；
- EHreact 风格多尺度模板；
- 现有 RDKit 规则生成；
- listwise ranker；
- applicability domain。

优点：

- 可解释；
- 数据需求相对低；
- 能最大化利用当前代码；
- 最适合作为下一代主基线。

风险：

- 仍受规则库覆盖限制。

### 路线 B：最贴合研究问题——Episodic analogical graph-edit learner

组成：

- support set encoder；
- transformation prototype；
- query-support cross-attention；
- site-conditioned edit decoder；
- episodic/meta-learning；
- distractor donor 与 abstention。

优点：

- 直接学习“如何从 A→B 类比到 X”；
- 能用多 donor 归纳共同变化；
- 具备清晰的论文创新点。

风险：

- 需要高质量 atom mapping、edit labels 和严格 episode 构造；
- 数据量较小时需要预训练。

### 路线 C：覆盖型独立基线——enviFormer / biochemical Transformer

组成：

- `X → Y` 序列生成；
- 可选 `[EC] X → Y`；
- 通用反应数据预训练；
- 环境转化数据微调；
- beam search + 概率阈值。

优点：

- 不受显式模板匹配失败限制；
- 是当前环境降解产物预测领域直接相关的强基线；
- 可提供与规则模型不同的错误分布。

风险：

- 数据偏差大；
- 解释较弱；
- SMILES 生成可能产生无效或记忆型预测。

建议定位：独立生成器和共识模型，而不是唯一主模型。

### 路线 D：长期高价值——酶/环境条件化模型

组成：

- reaction proposal；
- enzyme retrieval；
- enzyme—substrate compatibility；
- 口袋/序列/结构；
- cofactor 与环境条件；
- pathway search。

优点：

- 更接近“这条反应在目标微生物环境里会不会发生”；
- 能从化学可能性走向生物可实现性。

风险：

- 当前缺少可靠负例、动力学和环境条件；
- 不应在候选生成能力尚未诚实测清前先投入 3B 模型重工程。

---

## 12. 最推荐的近期实验顺序

### P0：先建立诚实 benchmark

不训练新模型，先改评估：

1. 去掉 oracle donor selection。
2. 不使用 held-out 共反应物。
3. 所有 X 都进入端到端分母。
4. 记录逐阶段漏斗。
5. canonical reaction 去重。
6. scaffold + transformation 双维度 split。
7. 报告 confidence—coverage 曲线。

这是所有后续判断的地基。

### P1：建立三组强基线

在同一个 benchmark 上对比：

1. 当前 Morgan donor + MCS template + DRFP；
2. EHreact 风格层级模板；
3. enviFormer/biochemical Transformer。

目的不是马上选最终模型，而是分清：

- 规则法缺 coverage 还是缺 ranking；
- Transformer 是否真能补未覆盖候选；
- 多尺度模板是否优于固定 radius=1。

### P2：加 site-of-transformation 模型

先做一个小模型即可：

- 输入 X 的分子图；
- 输出每个原子/键成为反应中心的概率；
- 标签来自 atom-mapped reaction edits；
- 可选用 transformation family 作为条件。

把 site 概率用于：

- 检索局部 donor；
- 限制模板应用位置；
- 候选排序；
- 解释输出。

这一步通常比“上更大的酶模型”更直接地解决当前生成瓶颈。

### P3：训练 listwise candidate ranker

使用当前引擎、层级模板、site model、Transformer 共同生成候选。

对每个 X 建立候选列表，训练统一 ranker。DRFP-酶集分数作为一个输入特征，而不是最终答案。

### P4：做 episodic analogy 原型

从反应量较多的 transformation family 开始：

- K=1/3/5 support；
- 加入相似底物但错误转化的 distractors；
- 预测 site 和 edits；
- 与“只用 X 的普通监督模型”对比；
- 与“只取最近 donor”对比。

核心消融：

- 单 donor vs 多 support；
- 全局 Morgan vs 局部 site-aware retrieval；
- 固定模板 vs prototype-conditioned edit；
- 无 distractor vs 有 distractor；
- 无拒答 vs 有拒答。

### P5：扩展到多步降解图

一阶产物稳定后，再做 beam search：

```text
X
├── Y1
│   ├── Z11
│   └── Z12
├── Y2
└── Y3
```

每条边都有：

- 转化概率；
- 适用域；
- 酶/EC；
- 环境证据；
- 累积路径分数。

路径分数不应只做简单乘积，可加入：

- 深度惩罚；
- 分支惩罚；
- 中间体可检测性；
- 降解速率；
- 毒性/持久性变化；
- 是否更接近矿化。

---

## 13. 最小可行的新架构

如果只允许做一轮工程，我建议：

```text
输入 X
  │
  ├─ 1. Site predictor
  │      输出 top-N 反应原子/键
  │
  ├─ 2. Multi-view retriever
  │      全局结构 + 局部位点 + transformation family
  │
  ├─ 3. Hierarchical support builder
  │      为每个 hypothesis 组织多尺度、多 donor 证据
  │
  ├─ 4. Hybrid candidate generator
  │      层级模板 + site-conditioned edits + Transformer baseline
  │
  ├─ 5. Unified listwise ranker
  │      site / edit / donor consensus / DRFP / enzyme / balance / OOD
  │
  └─ 6. Calibrated reporter
         top-K + 证据卡 + 适用域 + 反证 + 拒答
```

现有模块的去留：

| 现有能力 | 新架构中的位置 |
|---|---|
| Morgan substrate retrieval | 保留为全局检索特征，不再独占 donor 选择 |
| MCS template extraction | 保留为候选生成器之一 |
| RDKit RunReactants | 保留 |
| DRFP-酶集 | 保留为 ranker 特征和证据，不再是唯一 score |
| EnzymeCAGE 3B | 后置，用于高价值候选的酶兼容性增强 |
| pocket outer.mean | 继续废弃 |
| Agent | 升级为 hypothesis/evidence orchestrator |

---

## 14. 一句话研究命题

可以把下一阶段的科研问题凝练为：

> Can a model infer a transferable biotransformation concept from a dynamically retrieved set of enzymatic reactions, localize that transformation on an unseen xenobiotic, and produce calibrated, evidence-grounded product hypotheses?

中文：

> 模型能否从动态检索的一组酶反应中归纳可迁移的生物转化概念，在未知污染物上定位反应位点，并生成经过校准、具有证据链的产物假设？

这比“最近邻模板迁移”更完整，也比“直接用大模型生成 SMILES”更可验证。

---

## 15. 推荐阅读与可复用资源

1. [EHreact：按酶底物集合建立层级反应模板并估计 promiscuity](https://pubs.acs.org/doi/10.1021/acs.jcim.1c00921)
2. [GLORYx：site-of-metabolism 预测 + 反应规则 + 产物排序](https://pubs.acs.org/doi/10.1021/acs.chemrestox.0c00224)
3. [enviFormer：用 Transformer 预测生物降解产物，并用 precision–recall/阈值评估](https://pmc.ncbi.nlm.nih.gov/articles/PMC11834682/)
4. [enviPath 2024：环境污染物转化、整体路径评估和 applicability domain](https://pmc.ncbi.nlm.nih.gov/articles/PMC11304562/)
5. [EnzymeMap：酶反应清洗、原子映射和数据驱动预测](https://pubs.rsc.org/en/content/articlehtml/2023/sc/d3sc02048g)
6. [ECREACT / biocatalysed synthesis planning：EC 条件化的 forward model](https://www.nature.com/articles/s41467-022-28536-w)
7. [Graph-edit reaction outcome prediction](https://pmc.ncbi.nlm.nih.gov/articles/PMC5445544/)
8. [反应预测中的 scaffold bias 与误导性随机拆分](https://pmc.ncbi.nlm.nih.gov/articles/PMC7966799/)

---

## 16. 最终建议

下一步不要立即做：

- 更大的酶 3D 模型；
- 更复杂的口袋打分；
- 直接训练一个 LLM 从 X 输出 SMILES；
- 继续只调 Morgan 半径、top-k 或 DRFP 权重。

下一步应该做：

1. 先把端到端 benchmark 改诚实；
2. 把 reaction family、site、edit、enzyme、context 拆开；
3. 引入多 support、多尺度模板和局部检索；
4. 训练 site model 与 listwise ranker；
5. 把 episodic reaction analogy 作为核心创新路线；
6. 让 Agent 输出“支持 + 反证 + 适用域 + 拒答”。

最关键的思想转变是：

> 不再问“哪个 A 最像 X”，而要问“哪些 A→B 共同证明了某种转化规律，这条规律能否在 X 的某个位点成立，以及有哪些证据反对它”。
