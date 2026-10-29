# L2 n003 供给面扩库覆盖率探针（2026-10-27）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有数字只在该题域、
> 该 133 题分母内成立，与 dev 域双向不外推。
>
> **性质：零模型调用、零付费、零网络。** 三个库文件只读、未搬移未修改；不改生产代码与判分器；
> 不 commit / 不 push；金标只在 notebook `/root/v43_migration`（700）消费，报告只写聚合与 qid 级。
>
> 执行：notebook `crdnotebook-2113560935535583233-aclhl3hbth-81040`（Python 3.11.9，
> RDKit 2026.03.5，numpy 1.26.4，128 核 / 503 GiB）；本地仓 HEAD `2aa4502`。
> 开工 `ps` 复核：无在飞批（仅 jupyter/zcode server，load average 7.66）。
>
> 上游：`/root/v43_migration/iter/probe/n001/POOL_CEILING.json`（池上限）、
> `/root/v43_migration/iter/data/r2/batch_manifest.json`（298 题参考图映射）。
> 三库 SHA 见 `docs/T_P2_BUILD_DIAG_2026-10-21.md:60-62`。

---

## 0. 结论先行

| 问题 | 结论 |
|---|---|
| **接线现状** | **未接线**：三库只有原始 JSON；`v43cP2` 与 `dependingv3` 全树没有 `.py` 读取它们。只有部署哈希清单和两份文档提到文件名；`--recorded-source` 通道读的是 `corpus_v1.jsonl` / `library_full.jsonl`，不是这三件。 |
| **133 题可补池（任务口径 fp≥0.45）** | **131 / 133（98.5%）**：rhea 129、metanetx 131、uspto 102；合并 131。 |
| **化学更严口径** | rhs 子结构 108；rhs 精确产物 60；**RDKit 直译反应验证 61（下界）**。 |
| **与降阈值差集** | thr025 只救 **3 / 133**，thr030 **0 / 133**；新库 fp 真增量 **128**、子结构 **105**、反应验证 **58**；thr025 救回的 3 题全部被新库覆盖，无 thr-only。 |
| **与现行语料关系** | **84 / 133 的参考产物已在现行语料**（corpus_v1/library_full/eawag/analog corpus）；83 题 fp 命中、44 题精确命中是“已有产物 + 新模板”；**48 题 fp / 16 题精确 / 22 题反应验证是真新产物**。 |
| **扩库预期收益上界（粗估）** | fp 口径 131×0.5≈**66**；反应验证 61×0.5≈**31**；真新产物反应验证 22×0.5≈**11**。0.5 = n001 63/(63+63)，是现行池选成功率代理，不是实测扩库后池选率。 |
| **建议** | **优先接 `rhea.json`，其次 `METANETX.json`；`USPTO.json` 暂缓**（反应验证 0、转换失败 37%、426 MB）。建议新建 retro-template 通道，不要硬塞现有 `corpus_templates` 格式（详见 §6）。 |

**一句话**：三库对 133 道 nopool 题的产物侧供给非常广（任务口径 131/133），但其中 84 题的产物
本来就在现行语料里、只是缺“可执行的映射模板”；真正新增产物的反应验证增量是 22 题。
扩库的主要价值是**把已知 RHEA 反应变成可编译模板**，不是单纯“加新分子”。

---

## 1. 接线现状查证

### 1.1 结论

**未接线（三个库都只有原始库）**。没有任何生产、评测或离线构建代码按文件名读取
`assets/rhea.json`、`assets/METANETX.json`、`assets/USPTO.json`。

### 1.2 证据

| 检查 | 结果 | 证据 |
|---|---|---|
| 本地 `src/ scripts/ configs/` grep 三文件名 | 仅 `scripts/hpc/deploy.md:73` 提到“不进包” | 本仓 grep |
| notebook `v43cP2` + `dependingv3` 全树 `.py` grep | **0 命中** | `grep -rn -E 'rhea\.json|METANETX\.json|USPTO\.json' v43cP2 dependingv3 --include='*.py'` |
| notebook 全树（含 md/json/sh） | 仅 `v43cP2/docs/REPO_COMPLIANCE_TASK7_RECEIPT_2026-10-16.md:25`（未跟踪件登记）与 `v43cP2/scripts/hpc/deploy.md:73` | 同上，去掉 `--include='*.py'` |
| 运行时资产清单 | `assets/MANIFEST.sha256` **22 条**、`assets/MANIFEST.json` **22 条**，**不含三件** | `wc -l assets/MANIFEST.sha256`；`MANIFEST.json` `asset_count/open` |
| 资产白名单 | `ANALOG_INDEX_FILES` 只有 `uspto_relaxed_index_v1` / `corpus_templates_v1` / `v2`；`EXTENSION_FILES` 只有 v3_reactions 五件 | `src/pathway_v43/adapters/asset_manifest.py:29-40` |
| 部署完整性面 | `deploy_assets_sha256.txt` 的 **27 文件**包含三件；`T_P2_BUILD_DIAG_2026-10-21.md:49,60-62` 记录 SHA | 部署拷贝/哈希核对，不是运行时消费 |
| `--recorded-source` 通道 | 读 `corpus_v1.jsonl`（43,177 行，全部 `mapping_status=absent`）与 `library_full.jsonl`；不读三件 | `src/pathway_v43/pollutant/s5b_cli.py:455`；`recorded_source.py:42-43,964-972` |
| `dependingv3` RA | RHEA 源解析读 `/Volumes/CC/Enzyme_Agent/depending/demov3/data/rhea/{rxn_subset,rhea-reaction-smiles.tsv,...}`；`rhea_transfer` 从 `corpus_v1` 行派生规则 | `dependingv3/src/depending/ra/config.py`；`ra/rhea_sources.py`；`ra/rhea_transfer.py` |
| 部署说明 | `scripts/hpc/deploy.md:73` 写“只有 `--recorded-source` 引擎通道需要”三件 | 与现行代码不符，见下 |

**与 deploy.md 的冲突（明确登记）**：`scripts/hpc/deploy.md:73` 说三件是 `--recorded-source`
通道需要；但现行 `--recorded-source` 代码读的是 `corpus_v1` / `library_full`，不是三件。
按代码事实判 **未接线**；该句登记为**待澄清**（可能是数据血统表述、历史说明或旧版本残留），
不作为已接线证据。

### 1.3 三件与现行索引的关系（回答“精编索引还是同源另制”）

| 项 | 事实 |
|---|---|
| `assets/analog/uspto_relaxed_index_v1.jsonl` 行数 | **188,725**（实际 `wc -l`；任务书写的 188,705 差 20 行） |
| 索引 build report 输入 | `v3_reactions/templates/uspto_templates.json`，`n_templates=188,725`，SHA `65a5ad25cbd0cb49eb860205456544f0da8579da13a18278f992e4118d1ce5b8` |
| `assets/USPTO.json` | **814,990** 条 RetroRules 模板（`TEMPLATE_ID` = `RR:…`，`TEMPLATE` = reaction SMARTS） |
| 两者 `TEMPLATE` 原串交集 | **0** |
| 两者 rhs 组分原串交集（粗归一） | **0** |
| 结论 | **不是同一件，也不是“USPTO.json 的精编索引”**。索引来自 v3 自己的 `uspto_templates.json`（188,725 条，`{"templates": {smarts: freq}}`），`USPTO.json` 是另一套 RetroRules 导出。两者可能都源自 USPTO 上游，但本地文件与派生管线不同。 |
| `assets/analog/corpus_templates_v2.jsonl` | 17,183 行，来自 v1 的 EAWAG/corpus 映射；与三件无关 |

**接线三选一结论：未接线（只有原始库）。** 没有任何一个库已接；不存在“部分接线”。

---

## 2. 探针方法

### 2.1 题目与参考产物

- 133 题 = `POOL_CEILING.json` 的 `detail.unmatched_nopool`（110）+ `detail.partial_nopool`（23）。
  `detail` 里的 `unmatched_pool_exact`（6）、`partial_pool_exact`（30）、`unmatched_pool_flat`（3）
  **不属于 nopool，未计入**。
- qid 17 位前缀 → 全长：`batch_manifest.json` 的 `entries` key `[:17]`；**133/133 全部映射成功，0 缺失**。
- 参考产物口径：参考图 `nodes` 中 `role != root` 的节点（本题卷全部是 `principal_product`；
  root 是底物，不能算产物命中）。110 题 1 个产物、21 题 2 个、2 题 3 个。
- 未取 `run_inputs` 的池内容做对照；池上限结论直接继承 n001。

### 2.2 rhs 产物侧转换与指纹

- 每库 `TEMPLATE` 按 `>>` 拆 lhs/rhs；rhs 先剥外层括号，再按顶层 `.` 拆组分
  （括号/方括号深度跟踪，避免拆坏 `[O;H0]` 之类）。
- 每个组分两种转换：
  - **tier1**：`Chem.MolFromSmarts(comp)` → `Chem.MolToSmiles` → `Chem.MolFromSmiles`；成功即取。
  - **tier2**：方括号转换器保留显式 H 数与形式电荷（如 `[C;H0:1]` → `[C]`、
    `[c;H1:4]` → `[cH]`、`[S;H0;+1]` → `[S+]`），去 atom map 后 `MolFromSmiles`。
  - 不能变成有效 RDKit 分子的组分跳过并计数（绝大多数是非环芳香片段/价态非法，
    不是漏读）。
- 指纹：Morgan radius 2、2048 bit、`useChirality=False`（与引擎
  `SIMILARITY_FP_RADIUS=2 / SIMILARITY_FP_BITS=2048 / SIMILARITY_FP_CHIRALITY=False` 同参数）。
- 检索：参考产物指纹 vs **全库每个 rhs 组分的指纹**，Tanimoto ≥ **0.45** 即任务口径命中。
  逐库单独搜，再合并（union）。
- **口径提醒（必须看 §7）**：生产池的 0.45 阈值是 **底物 vs donor 反应物（lhs）** 的相似度；
  本探针按任务书要求把它用作 **产物侧** 相似度门槛，是供给面代理，不是生产检索分数。

### 2.3 四个层级的“命中”

| 层级 | 定义 | 用途 |
|---|---|---|
| **T0 fp≥0.45** | 参考产物 fp vs 任一 rhs 组分 fp，Tanimoto ≥ 0.45 | 任务书主口径；“可补池题数” |
| **T1 rhs 子结构** | 原始 rhs 组分 SMARTS 是参考产物的子结构（`HasSubstructMatch`） | 排除“只是指纹像”的假阳性；模板局部环境必须能嵌进产物 |
| **T2 精确产物** | rhs 组分 canonical isomeric SMILES == 参考产物 canonical | 最严的产物身份 |
| **T3 反应验证（下界）** | 完整原始 `TEMPLATE` 的 lhs 能匹配题目底物，且 RDKit `RunReactants` 直接产出等于参考产物的组分 | “模板真的能从这道题的底物做出产物”的直译验证 |

T3 的做法：
- 对 T0 命中且 T1 子结构确认的候选（每节点每库最多 20 个 uid），取每个 uid 的**首个**完整模板，
  先查 lhs 任一顶层组分是否匹配底物，再用 `ReactionFromSmarts(TEMPLATE).RunReactants((substrate,))`
  跑反应，产物去 map/规范后与参考产物 isomeric 或 stereo-blind 精确比较。
- 对 T2 精确产物，另做**全模板枚举**：扫描全库、收集所有产出该精确组分的模板
  （每 uid 最多 3000 条），同样查 lhs + 跑反应。
- 两次扫描按 qid 取并集；T3 = 61。**这是下界**：T1 扫描只取 20 个 uid/首模板，T2 扫描只覆盖精确产物；
  多反应物模板（需共底物）在 RDKit 单底物直译下会跳过（实测仅 3 个 metanetx 候选被标记）。

### 2.4 缓存规模与转换成功率

| 库 | 模板数 | 至少一个有效产物组分的模板 | 唯一 rhs 组分 | rhs 组分提及转换成功 | 转换失败（跳过） | 文件 |
|---|---:|---:|---:|---:|---:|---:|
| `rhea.json` | 134,738 | 126,353 | 47,602 | 197,223 / 221,650（**89.0%**） | 24,427 | 83 MB |
| `METANETX.json` | 336,966 | 312,630 | 101,510 | 486,593 / 558,460（**87.1%**） | 71,867 | 221 MB |
| `USPTO.json` | 814,990 | 545,813 | 343,903 | 657,183 / 1,049,955（**62.6%**） | 392,772 | 426 MB |
| 合计 | 1,286,694 | 984,796 | 493,015 | 1,340,999 / 1,830,065（73.3%） | 489,066 | 730 MB |

> “转换成功”的分母是 rhs **组分提及**（不是模板数）；一个模板可含多组分。
> USPTO 的 37.4% 失败主要是非环芳香片段（SMARTS 里 `[c]`/`[n]` 不在环上）和价态非法；
> 这些模板本身不能变成有效产物分子，跳过是如实处理，但也意味着 **USPTO 覆盖率被低估**。

缓存位置（notebook，原始 JSON 未搬移）：
`/root/v43_migration/iter/probe/n003/cache/{rhea,metanetx,uspto}.npz` +
`*_components.jsonl`（uid→canonical smiles/smarts/first_tid）+ `*_components_full.jsonl`
（uid→完整原始 TEMPLATE）。SHA 见 §8。

---

## 3. 覆盖率结果

### 3.1 分库与合并（133 题）

| 口径 | rhea | metanetx | uspto | **合并（union）** |
|---|---:|---:|---:|---:|
| T0 fp ≥ 0.45 | 129 | 131 | 102 | **131** |
| T1 rhs 子结构 | 84 | 91 | 39 | **108** |
| T2 精确产物组分 | 52 | 60 | 40 | **60** |
| T3 反应验证（下界） | 49 | 56 | **0** | **61** |

> 合并不是简单相加：101 题三库都 fp 命中，28 题 rhea+metanetx，1 题仅 metanetx，
> 1 题 metanetx+uspto。T3 的合并 = 61（rhea 49、metanetx 56、uspto 0 的并集）。
> **USPTO 在 T3 为 0**：它有 102 题 fp 命中、40 题精确产物，但模板 lhs 只匹配 11 题底物，
> RDKit 直译产出参考产物 0 题；对这批 RHEA 题没有可直接应用的模板。

### 3.2 按 nopool 桶拆分

| 桶 | n | T0 fp | T1 子结构 | T2 精确 | T3 反应验证 |
|---|---:|---:|---:|---:|---:|
| `unmatched_nopool` | 110 | 109 | 90 | 43 | 50 |
| `partial_nopool` | 23 | 22 | 18 | 17 | 11 |
| **合计** | **133** | **131** | **108** | **60** | **61** |

分库 × 桶（T0 / T1 / T2）：

| 库 | unmatched_nopool（110） | partial_nopool（23） |
|---|---|---|
| rhea | 107 / 70 / 37 | 22 / 14 / 15 |
| metanetx | 109 / 78 / 43 | 22 / 13 / 17 |
| uspto | 83 / 34 / 29 | 19 / 5 / 11 |

分库 × 桶 T3（反应验证）：

| 库 | unmatched_nopool | partial_nopool | 合计 |
|---|---:|---:|---:|
| rhea | 41 | 8 | 49 |
| metanetx | 45 | 11 | 56 |
| uspto | 0 | 0 | 0 |
| **合并** | **50** | **11** | **61** |

### 3.3 最高相似度分布（133 题，合并口径）

| best Tanimoto | 题数 |
|---|---:|
| ≥ 0.95 | 103 |
| 0.80–0.95 | 3 |
| 0.70–0.80 | 3 |
| 0.60–0.70 | 13 |
| 0.50–0.60 | 7 |
| 0.45–0.50 | 2 |
| **< 0.45（未命中）** | **2** |

未命中的 2 题：`RXNG_56d8303ebd8a`、`RXNG_cee619845b65`（均 unmatched_nopool）。
103/133 的 best sim ≥0.95，说明大量命中是**近精确产物**，不是靠 0.45 阈值硬凑。
低分段（0.45–0.60，9 题）里只有 3 题通过 T1 子结构确认，报告把它们与高分段分开看。

### 3.4 反应验证的构成

61 题 T3 中：
- 单产物题 47 题；多产物题 14 题（12 题 2 产物、2 题 3 产物）。
- 多产物题的反应验证是“至少一个参考产物被产出”，**不保证同一事件同时覆盖全部参考产物**；
  这 14 题全部在 `unmatched_nopool`。
- 22 题不是 T2 精确产物（模板 rhs 是产物片段，应用到底物后由底物补全其余部分才得到完整产物）；
  3 题不是 T1 子结构（来自 T2 精确产物 + 全模板枚举）。

---

## 4. 与 n001 阈值探针 / 现行语料的关系

### 4.1 与降阈值命中的差集（真增量）

n001 的 `thr025` / `thr030` 重建池用**产物精确身份（strict identity，products-only）**重新核对，
覆盖 133 题。结果：

| 指标 | 题数 |
|---|---:|
| `thr025` 救回（池里出现正确产物） | **3 / 133**（2 unmatched + 1 partial） |
| `thr030` 救回 | **0 / 133** |
| 新库 T0 fp 命中且 thr025 救不回 | **128** |
| 新库 T1 子结构且 thr025 救不回 | **105** |
| 新库 T3 反应验证且 thr025 救不回 | **58** |
| thr025 救回且 T0 未命中 | **0** |

- n001 `RECALL.json` 里 `thr025` 的 8 个 `pool_with_answer` 是 **60 道空池题**里的；
  落到 133 nopool 只剩 3 个（另外 5 个是 `strict_pool_exact`，本来就有正确候选）。
- 我们按 products-only 重算的逐题分类与 n001 `RECALL.json` **0 处不一致**（交叉核对）。
- **结论：降阈值不是这批 nopool 的解**（3/133）；新库 T0 覆盖 131/133，其中 128 题是
  阈值 0.25 也救不回的。新库相对“调阈值”是真增量。

### 4.2 与现行语料的产品重叠（关键）

现行语料产品集合（canonical isomeric，去重 58,817 个；flat 54,920 个）来自：
`v3_reactions/corpus_env/corpus_v1.jsonl`（`product_B_smiles` + `product_components`）、
`v3_reactions/library/library_full.jsonl`、`v3_reactions/eawag/donor_product.jsonl`、
`analog/corpus_templates_v2.jsonl` 的 `mapped_rhs`。

| 项 | 全部 133 | unmatched 110 | partial 23 |
|---|---:|---:|---:|
| 现行语料已有该参考产物 | **84** | 69 | 15 |
| T0 fp 命中 & 产物已在现行语料 | 83 | 68 | 15 |
| T0 fp 命中 & **新产物** | **48** | 41 | 7 |
| T2 精确 & 产物已在现行语料 | 44 | 32 | 12 |
| T2 精确 & **新产物** | **16** | 11 | 5 |
| T3 反应验证 & 产物已在现行语料 | 39 | 31 | 8 |
| T3 反应验证 & **新产物** | **22** | 19 | 3 |

**为什么“产物已在语料”却 nopool？** 现行 `corpus_v1.jsonl` 43,177 行**全部**
`mapping_status=absent`（37,098 行 rhea + 5,497 行 envipath 有产物，但零原子映射）。
`recorded` 通道对无原生映射的记录走推断映射；`s5b-recorded-source` 的
`corpus_cosubstrate_participants_unsupported` 等许可规则会拒掉大量有共底物/无映射的行；
`analog` 通道只覆盖 `corpus_templates_v2`（17,183 行 EAWAG 映射语料）。因此
“库里有产物”≠“池里能出现可编译候选”。

**这决定了扩库的定位**：
- 84/133 的扩库价值是**给已有 RHEA 产物补可执行映射模板**（不是新分子）；
- 48/133 的 T0、16/133 的 T2、22/133 的 T3 才是**新产物增量**；
- 如果只想修“已有产物但没模板”的问题，理论上也可以给 `corpus_v1` 的 37,098 条 RHEA 记录
  补映射；但那是另一条工程量，且 RetroRules 已经把映射准备好了（见 §6）。

---

## 5. 扩库预期收益上界（粗估）

**0.5 的来源**：n001 池参数探针的 `strict_pool_exact 63 / (strict_pool_exact 63 + strict_nopool 63)
= 63/126 ≈ 0.5`。它衡量“池里有正确候选时，最终 strict 命中/池选成功”的历史比例，
**不是**“新模板进池后一定被选中”的概率。扩库会改变池宽竞争、编译失败率和模型选择，
所以下面全部是**粗估**，不是实测。

| 口径 | 可补池题数 | ×0.5 粗估 | 说明 |
|---|---:|---:|---|
| T0 fp ≥0.45（任务口径） | 131 | **≈66** | 最乐观上界；含指纹相似但未必能编译的题 |
| T1 rhs 子结构 | 108 | **≈54** | 去掉“只是像”的题 |
| T3 反应验证（下界） | 61 | **≈31** | 模板能从底物直译做出产物；仍未过引擎 compiler/中心锚定/池宽 |
| T3 & 新产物 | 22 | **≈11** | 真正新增化学的保守增量 |
| 分库：rhea T3 | 49 | ≈25 | 83 MB，性价比最高 |
| 分库：metanetx T3 | 56 | ≈28 | 221 MB；与 rhea 并集 61 |
| 分库：uspto T3 | 0 | ≈0 | 426 MB；对本批 RHEA 题无直译模板 |

**建议对外只用区间表述**：在“新模板能过 compiler 且池选率维持 0.5”的乐观假设下，
扩库对 133 题的增量上界约 **61–66 题**；按“必须能直译做出产物”的保守口径约 **31 题**；
其中真正新产物的保守增量约 **11 题**。真实值还要扣除 compiler 拒绝、池宽截断、模型不选。

---

## 6. 接线方案建议与工作量

### 6.1 三个方案对比

| 方案 | 做法 | 优点 | 代价/风险 | 粗估工作量 |
|---|---|---|---|---|
| **A. 转成 `analog/` 索引格式** | 把每库转成 `corpus_templates` 风格：`template_id/record_id/mapped_lhs/mapped_rhs/center_atoms/env_shell/confidence/qc_flags` | 复用现有 `analog_source.templates_similar_to` 通道，builder/测试改动相对小 | RetroRules `TEMPLATE` 是 **SMARTS**（`;H`、atom map），`analog_source.align` 用 `MolFromSmiles` 解析 `mapped_lhs` 会失败；转 mapped SMILES 有损（丢 H 约束/半径语义）；center/env 需从 atom map 差推；还要升 manifest/池策略版本 | **2–4 人日** |
| **B. 新建 retro-template 通道（推荐）** | 新增 loader（TEMPLATE_ID/TEMPLATE/RADII/ECS/REACTIONS/VALID）→ lhs 指纹索引 → builder 新通道（类似 `recorded`/`analog`）→ 复用/适配 `s5b_compiler` | 保留原始 SMARTS、半径、ECS、反应 ID；无有损转换；可复用同一 compiler 与诊断面；RHEA/MetaNetX 直接按原 schema 接 | 新代码面较大：loader、索引、builder 通道、compiler 适配、池策略版本/诊断/测试；需要化学评审 | **4–6 人日** |
| **C. 转成 `donor_index.jsonl` 格式** | `{donor_record_id, donor_smiles, source_id, source_type}` | 极快 | **不够**：donor_index 只是 donor 查找索引，不带产物/模板/映射，不能单独补池；只能做溯源附件 | 0.5 人日（但无效） |

### 6.2 推荐路线

1. **先接 `rhea.json`**（83 MB，134,738 模板，转换成功 89%，T3 49/133）。
   - 对 298 域，rhea 与题库**高度同源**（题域标签 RHEA；corpus_v1 有 37,098 条 rhea 行带产物）；
     本探针未独立追溯题目构建来源，故按“同源 recall”而非独立泛化理解。
   - 建议用方案 B：新 retro-template 通道，lhs 侧建 Morgan r2 b2048 指纹索引，
     检索用底物 vs lhs；产物侧用原模板 `RunReactants`/compiler。
2. **再接 `METANETX.json`**（221 MB，336,966 模板，T3 56/133；与 rhea 并集 61）。
   - 它补的是 rhea 之外的 12 题左右（并集 61 vs rhea 49），并且精确新产物上
     metanetx 的 exact_new 为 16（合并也是 16）。
3. **暂缓 `USPTO.json`**（426 MB，814,990 模板，T3 **0**，转换失败 37%）。
   - 它对这批 RHEA 题的模板 lhs 几乎不匹配（仅 11 题），直译产物 0；
   - 若未来做非 RHEA/通用化学域，再评估；当前不要为它付 426 MB 和 37% 解析失败成本。
4. **前置工程**：三件不在运行时 `assets/MANIFEST.sha256`（22 条）里，
   而 `verify_repo_manifest` 是 fail-closed；接线必须新增清单条目/独立 manifest
   并升资产身份版本，否则运行时会直接拒绝或无法哈希校验。
5. **同源泄漏披露**：rhea 库与 298 题库高度同源（按题域标签与 corpus_v1 来源；未独立追溯
   题目构建来源）。扩库后的提升应标注为“同源 recall”，不能直接外推到 unseen 化学或 dev 域。
   若要做泛化结论，需要另设 held-out 题/库切分。

### 6.3 工作量拆解（方案 B，粗估）

| 工作项 | 人日 |
|---|---:|
| loader + schema 校验（三库字段/版本/来源/半径） | 0.5–1 |
| lhs 指纹索引 + 检索（复用 `analog_source` 参数与 tie-break） | 0.5–1 |
| builder 新通道 + 诊断/候选行/池策略版本 | 1–1.5 |
| compiler 适配（mapped SMARTS → 现有 compile 入口；负控） | 1–1.5 |
| manifest/身份版本 + 测试 + 回放 | 1 |
| 合计 | **4–6 人日** |

> 若只做方案 A 的“快速试点”（先接 rhea、转 mapped SMILES、接受有损），可压到 2–3 人日，
> 但会丢半径/H 约束，后续还要返工；不建议作为正式路线。

---

## 7. 偏离与 unknown

1. **口径偏离（最重要）**：生产池 0.45 阈值是**底物 vs donor 反应物（lhs）**相似度；
   本探针按任务书把它用作**产物侧**相似度门槛。T0 是供给面代理，不是生产检索分数。
   真正的“能否进池”还要过 lhs 检索、compiler、中心锚定、池宽截断。
2. **rhs 是局部反应环境，不是完整产物**：RetroRules 模板按半径 0–10 抽取；半径 0 的 rhs
   只是反应中心。T0 对低半径模板会低估（小片段 vs 大产物），T3 用完整模板直译来补；
   T1 子结构确认也帮助排除假阳性。
3. **USPTO 转换失败 37.4%**（392,772 / 1,049,955 组分提及）：主要是非环芳香片段/价态非法；
   USPTO 的 T0/T1/T2 覆盖可能被低估。但 T3 在精确产物上也是 0，故“暂缓 USPTO”的结论不受影响。
4. **T3 是下界**：T1 扫描每节点每库最多 20 个 uid、每 uid 只取首个模板；T2 扫描每 uid 最多
   3000 条模板；多反应物模板（需共底物）在 RDKit 单底物直译下跳过（实测仅 3 个 metanetx 候选
   被标记）。更多模板可能把 T3 抬高。
5. **精确匹配是 isomeric canonical**；stereo-blind/flat 精确未单独算（会 ≥60）。
6. **多产物题**：23 题有 2–3 个参考产物；T0/T1/T2/T3 都是“至少一个产物”口径（任务书口径）。
   T3 的 14 道多产物题只保证至少一个产物被直译产出，不保证同一事件覆盖全部产物。
7. **同源泄漏**：84/133 的参考产物已在现行 `corpus_v1`（rhea 37,098 行有产物、全部无映射），
   而 `rhea.json` 也是 RHEA 派生（按题域标签与 corpus_v1 来源；未独立追溯题目构建来源）。
   扩库的提升有相当部分是“同源 recall + 补映射”，不能外推到 unseen 化学或 dev 域。
8. **deploy.md 冲突**：`scripts/hpc/deploy.md:73` 说三件是 `--recorded-source` 需要；
   现行代码读的是 `corpus_v1`/`library_full`。登记为待澄清，不按“已接线”处理。
9. **n001 RECALL 的 8 vs 3**：n001 `thr025` 的 8 个 `pool_with_answer` 是 60 道空池题；
   落到 133 nopool 只剩 3（另 5 个是 strict_pool_exact，本来就有正确候选）。逐题交叉核对
   0 处不一致。
10. **未做**：没有把三库转成任何生产索引；没有跑引擎 compiler/池构建；没有模型调用；
    没有测 dev 域；没有做 held-out 泛化。所有“可补池”数字都是产物侧/直译代理，不是端到端跑分。

---

## 8. 证据路径与 SHA256SUMS

### 8.1 Notebook 工作区（数据与缓存）

```
/root/v43_migration/iter/probe/n003/
├── n003_build_cache.py          # rhs 组分转换 + 指纹缓存
├── n003_probe.py                # 133 题 T0/T1/T2 + n001 diff
├── n003_overlap_current.py      # 现行语料产品重叠
├── n003_reaction_check.py       # T3（子结构候选 + 首模板直译）
├── n003_exact_template_check.py # T3（精确产物全模板枚举）
├── n003_attach_templates.py     # uid → 完整原始 TEMPLATE
├── n003_summary.py              # 聚合摘要
├── n003_tsv.py                  # 逐题 TSV
├── N003_RESULT.json             # 逐题主结果
├── N003_SUMMARY.json            # 聚合摘要（机读）
├── N003_CURRENT_CORPUS_OVERLAP.json
├── N003_REACTION_CHECK.json
├── N003_EXACT_TEMPLATE_CHECK.json
├── n003_per_qid.tsv             # 逐题清单：qid/命中库/最高相似度/模板/T1-T3 标记
├── SHA256SUMS                   # 本目录 + cache 的 SHA
└── cache/
    ├── rhea.npz / metanetx.npz / uspto.npz
    ├── *_components.jsonl / *_components_full.jsonl
    └── *_stats.json / ALL_STATS.json
```

### 8.2 本地证据（untracked）

```
docs/review_evidence/n003_asset_coverage_2026-10-27/
├── N003_RESULT.json
├── N003_SUMMARY.json
├── N003_CURRENT_CORPUS_OVERLAP.json
├── N003_REACTION_CHECK.json
├── N003_EXACT_TEMPLATE_CHECK.json
├── n003_per_qid.tsv
├── cache_ALL_STATS.json
├── rhea_stats.json / metanetx_stats.json / uspto_stats.json
├── n003_*.py（8 个脚本）
├── n003_*.log（3 份运行日志）
├── SHA256SUMS                   # notebook 侧原始 SHA（含 cache）
└── SHA256SUMS.local             # 本地证据目录逐文件 SHA
```

### 8.3 关键 SHA（源资产，notebook 实测）

| 文件 | SHA-256 |
|---|---|
| `assets/rhea.json` | `8927221e4c5d866d259bba5ba269b6da995340b766e94deec440ad8503b173d9` |
| `assets/METANETX.json` | `d2f5e2cf935f1a07383812ecc7b288fec3a74a18bb71eb07a94fbdedd300a27f` |
| `assets/USPTO.json` | `4baebf7582fc218f5ef1d7df98dbb9837c31ce43028f9e5cf97d784667e2327e` |

### 8.4 复跑命令（notebook）

```bash
cd /root/v43_migration/iter/probe/n003
python3 n003_build_cache.py --workers 64
python3 n003_probe.py --workers 48
python3 n003_overlap_current.py
python3 n003_reaction_check.py
python3 n003_exact_template_check.py
python3 n003_summary.py
python3 n003_tsv.py
sha256sum -c SHA256SUMS
```

---

## 9. 给决策者的三句话

1. **接线前**：三库对 133 道 nopool 题的产物侧供给很广（任务口径 131/133），但三库**完全没接线**；
   现行 `--recorded-source` 读的是 `corpus_v1`，不是这三件。
2. **接线后**：按“模板必须能从底物直译做出参考产物”的保守口径，**61/133** 有直接证据；
   按任务口径 131/133 是乐观上界。0.5 池选率粗估下，增量上界约 **31–66 题**，
   真新产物保守增量约 **11 题**。
3. **先接哪个**：**rhea.json 先行**（49/133 直译、83 MB、同源），**METANETX 第二**（并集 61），
   **USPTO 暂缓**（0 直译、426 MB、37% 转换失败）。方案选新的 retro-template 通道（4–6 人日），
   不要硬塞 `corpus_templates` 格式（SMARTS→SMILES 有损）。