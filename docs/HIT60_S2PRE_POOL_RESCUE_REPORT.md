# HIT60 T7 报告：题源决策支撑——mibPOPdb 评估 + EAWAG 留出差集核查

- 执行日：2026-09-30（分支 v4.3，工作树不提交；开工 git 状态已留档）
- 依据：`TASK_V43_HIT60_S2PRE_POOL_RESCUE.md`（任务书）+ teacher 批复 §三.①（`TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md`）
- 纪律：全零 LLM API（许可与获取调研走远端 chenyu curl 公开源，只读）；本地/远端资产只读；不实施题卷切分；不 git commit
- **题域标签声明**：本报告所有数字均属**题源评估域**（候选题池结构与证据面对撞预检），不是任何考试成绩；路一候选题域为「持久性有机污染物（POPs）微生物降解单步转化」（环境域，与 dev 的 B1 环境路径中间步骤题域同族、与 298 的 RHEA 通用酶学题域不同族），数字双向不外推。

---

## 〇、一句话结论

**路一（mibPOPdb）：有条件可行——许可与分子层结构过关，但反应边（底物→产物对）没有机器可读源，须人工重建；离线可达数据全力裁剪后约 60–150 题，处在 100–150 目标区间的下沿，达成有风险。路二（EAWAG 留出差集）：不可行——library_full 与 corpus_v1 的 envipath 侧是同一内容的两种形态，差集为 0，且 library_full 本身就是引擎运行时的 recorded 路由查找库，任何取自它的题都会被直查答出。两路合计后 100–150 盲测 + dev v2 的双目标大概率不达，按任务书 §4 走兜底回报缺口，不自行放宽。**

---

## 一、大白话摘要（≤200 字）

mibPOPdb 论文开放、数据免费下载、要求引用——许可这一关过了。我们把能离线拿到的数据（论文补充表 + GitHub 快照）全部清点核验：593 个降解中间体里 573 个 SMILES 能解析、48 条通路分好组，分子身份证齐全。**卡点在"反应对"：库里只有化合物清单，没有"谁变成谁"的机器可读边**，得靠人工按通路图和文献重建，官网又恰好宕机，全量 9,215 条菌株数据拿不到。EAWAG 那路彻底没戏：所谓"没进 v1 语料的 EAWAG 包"根本不存在——两个库内容一模一样，差集算出来是 0。

---

## 二、路一：mibPOPdb 闭卷金标种子源评估

### 2.1 许可与获取

| 项 | 核验结果 | 证据 |
|---|---|---|
| 论文 | iMeta 2022，DOI 10.1002/imt2.45，**CC BY 4.0**（OA） | Europe PMC 元数据 `pmc-license-ref=CC BY`；全文 XML 已存档（见 §七） |
| 数据库官网 | `http://mibpop.genome-mining.cn/` **不可达**（本地与 chenyu 双通道 curl 均 000，http 明文亦超时） | 2026-09-30 实测 |
| Wayback 存档 | **本环境不可核**（archive.org 双通道均不可达；沙盒代理宕机 + chenyu 无法出境到 archive.org） | 同上，登记待复核项 |
| 官网下载政策（论文转述） | "All data sets … can be freely accessed on the download page. Users are strongly encouraged to cite the original works when redistributing or reproducing." —— 免费获取 + 引用要求 | 论文 Data access and usage 节原文 |
| 数据库正式许可文本 | **未见**（论文与已获取材料中无 CC/EULA 条款）；官网条款待其恢复后复核 | 全文串扫 licen*/terms of/user agreement |
| GitHub 快照 | `monsterZeng/MIBPOP`，**无 LICENSE 文件**（默认版权保留）；2021-12 冻结；内容 = 论文数据集 + GNN 代码 | GitHub API `license=null` |

**许可判定**：研究评测内部使用无阻塞（论文 CC BY 4.0 + 官网免费下载政策）；题卷若含 mibPOPdb 来源的题面/金标，按引用要求在卷宗登记溯源即可；**再分发原始数据表**（比如把 xlsx 发给评审人）需引用原论文并注意 GitHub 快照无许可文件的保留状态；正式数据库许可文本列为待复核（官网恢复触发）。ECREACT 式的"禁商用风险"在 mibPOPdb 上**不存在**（无 BRENDA 衍生链；其基因表只是外链 BRENDA EC 号，非衍生数据）。

**规模口径勘正**（teacher/任务书引用的 3,479 与论文摘要 9,215 的关系）：9,215 = 官网全量菌株条目；**3,479 = 其中有 16S/18S rRNA 或基因组分类学描述的子集**；另有 5,736 = 带功能基因注释的条目。两个数字都真实，是总集/子集关系，不是版本差异。

**获取现状**：官网宕机 → 全量 9,215 条不可得；离线可得 = PMC 补充材料（s002.xlsx：中间体表）+ GitHub 快照（POP_Compounds / Organism / Genes 23+32 个 xlsx / GNN 代码）。两处均已实拉到本地并解析（见 §七路径表）。

### 2.2 数据结构清点（离线可得部分，全部实拉实算）

| 数据块 | 规模 | 结构核验结论 |
|---|---|---|
| 中间体表（PMC s002 "POP and Intermediates"） | 593 行 | 字段：通路名 / 母体 POP / 中间体名 / CAS / 分子式 / MW / **SMILES** / PubChem CID / KEGG / ChemSpider。**SMILES 合法率 583/593 有值、573 RDKit 可解析**（10 个占位值 "not yet determined"）；去重后 303 个分子（cn 口径）；452 行有 CAS。按 48 条通路分组 |
| POP 母体表（GitHub POP_Compounds.xlsx） | 442 行（33 sheet，每 POP 一 sheet） | 主 POP 行带 SMILES（30 行有值、27 个去重分子）与 PubChem/DSSTox/KEGG ID；同系物行多缺 SMILES 但 ID 齐全可回补 |
| 菌株表（GitHub Organism/*.xlsx） | **115 行**（32 文件合计；官网全量 9,215 的离线快照仅此） | 一行 = 一个菌株 × 一个 POP；含 **Primary Intermediate/s / Final product**（自由文本名，非 SMILES）、酶活、修复类型、采样、PMID。名称→SMILES 解析率：精确匹配 8/269，括号缩写+同义词通道 67/269；未解析项多为泛称（Epoxide、tri-/tetra-）或一格多值 |
| 基因表（GitHub Genes/*.xlsx） | 1,468 行 | 一行 = 基因×酶×菌株×化合物；通路图字段是**链接到 eawag-bbd.ethz.ch 旧站**（本身已停服）——注意 mibPOPdb 的通路血统与 EAWAG-BBD 同源（泄漏审计要点，见 2.5） |
| **反应边（底物→产物对）** | **0 行** | **四份数据均无机器可读边字段**。通路以三种形态存在：①中间体清单+表内行序（实测 BDE-209 为去溴级联序——**阶段分组有序，但分支区相邻行不构成边**，如 BDE-206 与 BDE-207 是兄弟不是母子）；②官网图形通路图（宕机拿不到）；③文献（1,064 篇，人工回溯成本极高） |

**记录粒度回答任务书问题**：一条记录 ≠ 一个菌株×底物×产物集合的完整三元组。中间体记录 = 一个中间体×一条通路（无前驱信息）；菌株记录 = 菌株×POP（产物是文本名）。**单步题面（底物 SMILES）可支撑**（573 合法中间体 + 30 母体 + ID 回补通道）；**金标推导（产物 SMILES）要靠人工重建边**——这是路一的核心成本与风险。

### 2.3 出题适用性与题量预估

题量按三个通道分账（全部离线可得数据、经结构过滤后）：

| 通道 | 候选上限 | 过滤后估计 | 说明 |
|---|---|---|---|
| 母体→第一中间体（菌株表 Primary Intermediate 字段） | 269 个名称提及 / 115 条记录 | **约 20–40 题** | 需同义词解析（已验证 67/269 可自动解，其余人工）；官网恢复后此通道可放大（全量 9,215 条） |
| 通路内相邻中间体对（行序+化学验证候选） | ≤545（593−48 首边） | **约 80–150 题** | 行序只是排序线索非金标；每条边需化学守恒校验（卤素数/分子式）+文献核对（双人确认） |
| 交叉通路同产物去重后 | — | −10~−20% | 303 去重分子已含 1.9 倍重复率 |
| **合计（离线全力）** | | **约 60–150 题** | 再扣泄漏审计命中、I3/金标纪律淘汰（按 dev 经验 5–10% 缺陷率），**冻结卷期望 55–135 题** |

**结论：60–150 区间的下沿，达不达 100 全看边重建的文献核对兑现率**。官网若恢复（触发器见 §六），全量菌株表可把通道一放大到 100–300 题，目标区间即稳。

### 2.4 选题指标设计：「rank/recorded 路由题占比」（teacher §六.2 原文要求）

**方法（出题前可算，冻结时复核）**：对每个候选题的**题面底物**做三桶分类（cn 口径，脚本化）：

1. **recorded 桶**：底物 ∈ library_full 给体集（2,678 个分子）→ 引擎 recorded 路由会命中（`eawag_lookup` 精确 cn 匹配给体 → recorded 产物置顶候选）；
2. **rank 桶**：底物 ∈ corpus_v1/donor_index 给体集（recorded 桶为其子集，实测 library 给体 ⊆ corpus/donor_index 给体）→ 类比检索有同给体反应可喂，重排有活干；
3. **novel 桶**：两处皆无 → 只有模板/规则/novel 生成路径。

按 dev 56 题的承载面（题面底物在 library 给体侧可见 11/56≈20%）校准目标配比，出题前对 mibPOPdb 候选池预估结果：

| 桶 | 分子数 | 占比 | 对 dev 的参照 |
|---|---: |---:|---|
| 底物全集（中间体 303 + 母体 27，cn 去重） | 321 | 100% | — |
| recorded 可达 | 67 | 20.9% | dev 20% 同型 |
| 检索可达（含 recorded） | 85 | 26.5% | — |
| novel | 236 | 73.5% | dev novel 面更大 |

**判定**：mibPOPdb 池的天然路由结构与 dev 同型（recorded≈21%），**重排类杠杆的承载面成立**——不是一张纯 novel 卷。切分时按桶配比选题（建议显式定一个目标配比窗口，如 recorded 15–25% / rank 附加 10–15% / novel 60–75%），冻结时把实际占比写进卷宗。数据与脚本：`pool_rescue/intermediates/mibpop_routing_buckets.json`。

### 2.5 泄漏审计方案（写方案不实施——题卷未构建）

沿用 D2 preflight 与全证据面审计（`reports/phase_s1_hit60/dev_gold/FULL_SURFACE_LEAK_AUDIT.md`）的方法骨架，改题源输入：

1. **对象**：候选题卷的（题面底物 SMILES，金标产物 SMILES 集合）对，逐题。
2. **双口径**：精确串 + cn_identity（电荷归一化+立体盲 canonical，IDENTITY_VERSION=cn-v1；corpus_templates 剥映射号后进 cn 口径）。
3. **配对级判据（leak 判定）**：同一资产记录内题面命中给体侧 且 金标命中产物侧，正反双向（题面→金标 与 金标→题面）。**命中处理规则预注册**：命中题从池中剔除并登记（沿用 dev 冻结时 B1 池剔 328 题的做法），不做改写抢救。
4. **审计面**：全证据面 22 项资产（corpus_v1、library_full、donor_index、eawag/donor_product、eawag/rules、corpus_templates v1/v2、envipath 模板、uspto_templates、uspto_relaxed_index、rankers/calibrators）。**mibPOPdb 特有两条**：
   - 通路血统同源性：mibPOPdb 基因表的通路图链到 eawag-bbd.ethz.ch——其通路与 EAWAG-BBD 同源，须额外做"题对 vs library_full EAWAG-BBD 1,002 行"的配对对撞（已纳入 22 项面，单列计数）；
   - mibPOPdb 中间体分子在我方证据面的分子级可见性已预检：**63–84/303（21–28%）已可见**（library 给体 63 / corpus 给体 74 / donor_index 80 / templates 84）——分子级可见不是泄漏（与 dev 同性质，如实登记进卷宗 novel 宣传口径即可）。
5. **运行时抽查（冻结后）**：复用全证据面审计的 cardval 扫描法，对首批考卷跑一次证据卡整串产物对撞，登记"候选含金"题数（不判分，只做闭卷成色披露）。

### 2.6 金标构建纪律预案（沿用 T1/T2 + teacher §五.4.3）

1. **边重建纪律**：候选边 = 行序相邻 + 化学守恒自动筛（元素守恒、卤素数单调性、分子式/质量差合理性——POPs 降解以脱卤/羟化/开环为主，模式可用 RDKit 自动预筛）→ 人工核对（通路图/文献回溯，mibPOPdb 每条记录带 PMID）→ **双人确认**；
2. **I3 盲性**：复核人不接触任何模型输出/答卷（沿用在案纪律）；
3. **构建口径沿用**：不剥离共底物/主产物（>80 字符剥离豁免条款沿用）、多产物语义显式登记（断裂/水解多主产物按组分语义登记）、酰基-CoA 长产物豁免沿用；
4. **T6 R4 退化打标先过滤**：切分前先跑退化规则（金标=题面、CO2 矿化端点、题面缺来源元素等三条确定性规则），退化题入 quarantine 不进分母；
5. **题面缺结构回补**：POP 母体行缺 SMILES 的用 PubChem CID 回补（表内已带 CID），回补后过合法性校验才入池；
6. 顺带登记：mibPOPdb 金标流程建立后，按 teacher §八.3 把 **12 道 B 分歧题**的证据可达性判据一并回看（列为其任务的必做子项）。

### 2.7 落地路径与工作量（从数据到冻结题卷）

| 步骤 | 内容 | 工作量 |
|---|---|---|
| ① 数据固化 | 离线四块数据入 gitignored 工作区（已拉好，见 §七）；官网恢复则补拉全量 | 0（已完成）/ 恢复后 0.5 人日 |
| ② 边重建 | 候选边自动生成（行序+守恒筛）→ 人工核对 48 条通路 → 双人确认 | 自动 1 人日 + 人工 **8–12 人日**（窄口径：母体首边+高置信相邻对）；全边重建口径 25–50 人日（不推荐） |
| ③ 题面/金标规范化 | SMILES 校验、退化过滤（R4 规则）、多产物语义登记 | 1 人日 |
| ④ 泄漏审计 | 2.5 方案实施（脚本骨架复用全证据面审计，换题源输入） | 1 人日 |
| ⑤ 选题与路由配比 | 按 2.4 三桶配比切分候选卷，写卷宗 | 0.5 人日 |
| ⑥ 考卷评审 + 冻结 | mimo 考卷抽审请求 md（抽题化学合理性+金标口径+路由结构核对）→ 用户批 + 双人确认（**涉题面/金标外发逐次拍板**）→ 冻结 | 1–2 人日 + 评审等待期 |
| **合计** | 窄口径 | **约 12–18 人日**（不含评审等待） |

### 2.8 路一 verdict

**有条件可行**：许可过、分子结构过、路由承载面过；条件 = ①反应边人工重建（12–18 人日的主体成本）②官网宕机导致全量不可得，题量顶格 60–150、期望冻结 55–135，达 100 有风险；③正式数据库许可文本待官网恢复复核。

---

## 三、路二：EAWAG 留出差集核查

### 3.1 差集口径与结果（双口径 + CORPUS_LINEAGE 四重验证沿用）

对象：library_full（4,454 行，SHA `042e9e2c…` 与远端 dependingv3 一致）vs corpus_v1 envipath 侧（6,077 行，SHA `186a1dad…` 一致）。ID 映射打通：BBD 走 `btXXXX#rYYYY`，SOIL/SEDIMENT/SLUDGE 走 reac_id UUID（corpus `record_id` 后缀即 library `reac_id`）。

| 口径 | 结果 |
|---|---|
| A. 包级 | library 包枚举 {BBD, SEDIMENT, SLUDGE, SOIL} = corpus v1 envipath 包枚举（parse_note 映射）。**library_only = ∅，corpus_only = ∅（educt 是 BBD 的给体侧子集口径）** |
| B. 记录级 | library 4,128 个规范化键 **100% ∈ corpus 键集**（5,546）；library−corpus = **0**；corpus−library = 1,418（同反应多 representation 的重复键） |
| C. 配对指纹（精确串 + cn 双口径） | library 4,454 行的 donor→product 对 **4,454/4,454 命中 corpus 配对集**（两口径均 100%）；反向：corpus 5,497 个配对记录的对 **5,497/5,497 ∈ library 配对集**。**两库配对宇宙相同** |
| D. 全文串扫 | library_full 对 ecreact/evodex/brenda/enzymemap/metanetx/pathbank **0 命中**（纯 EAWAG 复核通过） |
| 抽样复核 | 各包抽 5 行键匹配核对 donor/product cn 全对；corpus 独有键抽 8 条配对均真在 library（非解析伪影） |

**差集规模：0 行、0 package。**

交叉验证：library 2,678 个去重给体分子、772 个 btid（BBD 211 / SOIL 289 / SEDIMENT 146 / SLUDGE 126）与 v3.5 资产 README 自述（"4,454 rows, 2,678 donors"）吻合。

### 3.2 结构性结论：为什么差集=0 之外还有第二道死锁

引擎运行时（`src/pathway_v43/adapters/v3_engine.py`）把 library_full 装载为 **recorded 路由查找库**（`eawag_lookup.build_index` → 查询时给体精确 cn 匹配 → recorded 产物置顶候选；`reaction_finder` 的 `EVIDENCE_KIND_RECORDED` 溯源）。因此：

1. 任何取自 library_full 记录的题（底物=donor、金标=recorded product）会被 recorded 路由**直查答出**——配对级泄漏 by construction；
2. 即使差集非零，差集条目本身就在 library_full 里（差集从它派生），泄漏红线（不得与任何检索/模板/规则资产重叠）自动全扣；
3. 留出集要成立必须做**语料手术**（从 library_full/corpus_v1/模板资产里删记录 + 重建索引）——而现在连手术对象都不存在（差集=0）。

**回答 teacher §三.① 的问题：EAWAG 未入 v1 语料的 package 不存在，library_full 与 corpus_v1 是同一 EAWAG 内容的两种形态；EAWAG 我方持有内容不构成任何留出集。**

### 3.3 上游核查（envipath.org）

- envipath.org 现已**登录墙**（匿名访问全部 302 到 /login/，含公开 REST API 探针 `/api/`、`/api/package/<uuid>`；v3 抓取时代用的 legacy API 需 Django CSRF 登录，凭证在 BiocrewV2/.env 线，本轮不启用）；
- enviPath 2024 NAR 论文（Hafner et al.，PMC11304562，已存档）Table 1 给上游主包规模：**Eawag-BBD 1,480 反应 / Eawag-Soil 2,447 / Eawag-Sludge 521**（化合物 1,399/1,780/1,070，通路 219/317/184）；
- 对照我方语料：BBD **1,066**（上游缺口约 414 条）、Soil 2,485（≥上游）、Sludge 553（≥上游）、Sediment 1,393（上游论文未列，无从比对）；
- **上游缺口≠留出集**：即便补抓 BBD 缺口（需凭证+用户批），抓回的记录属 S3 语料扩充范畴；要做留出同样先过泄漏审计，且要保证不进任何证据资产——属另一任务书的决策，本轮只登记。

### 3.4 路二 verdict

**不可行**（作为留出集）：差集 0 + recorded 路由结构性死锁 + 上游登录墙。EAWAG 线对我方只剩一个残余情报点：上游 BBD 约 414 条未抓记录（凭证受限，登记不投入）。

---

## 四、互补性与 100–150 目标测算

| 来源 | 冻结卷期望题量 | 对 100–150 盲测 | 对 dev v2 |
|---|---|---|---|
| 路一 mibPOPdb（离线全力） | 55–135 | **下沿勉强/不保证** | 够切 dev v2（几十题量级）没问题 |
| 路二 EAWAG 差集 | **0** | 0 | 0 |
| 合计 | 55–135 | **大概率不达或贴线** | 可满足 |

**互补性结论**：路二贡献为零，两路不能拼出 100–150 盲测 + dev v2 的双目标；能否到 100 完全押在路一边重建的兑现率上（期望值约 90，区间下沿 55）。结构性出路的优先序：①官网恢复（`mibpop.genome-mining.cn` 恢复即触发全量补拉，通道一可放大到 100–300）；②S3 语料扩充候选里的 RHEA 血统补全包（BioRGroup/ReactZyme——注意那会触发报告口径降级，属既定绑定纪律，不在本任务范围）；③其他新源再侦察。

## 五、兜底（任务书 §4 预先声明）

两路均不达 100–150 目标的情形**已实质成立一半**（路二=0、路一贴线）。按批复口径：**回报缺口，teacher 侧再议放宽口径；学生侧不自行放宽、不静默降标**。本报告只登记缺口与可选出路，不做任何放宽动作。

## 六、登记项（不投入工程）

| 项 | 状态 | 说明 |
|---|---|---|
| ECREACT | 后置，仅情报储备 | 禁商用风险维持（BRENDA 衍生 8,496 条），仓外许可结论必须先行；已在侦察附册 §3.5 登记，本轮不投入 |
| BRENDA extra-213 | **不修，从候选移除** | teacher 裁定：accession 分歧 + 血统混杂，成本收益不成立；原 T7 草案的 BRENDA bug 取证条目作废 |
| mibPOPdb 官网恢复触发器 | 监视项 | 官网恢复 → 补拉全量 9,215 菌株 + 通路图数据 + 正式许可文本复核 + 12 道 B 分歧题回看（teacher §八.3）一并启动 |
| Wayback 复核 | 环境受限项 | 本环境 archive.org 双通道不可达；有外网条件时补核官网历史快照（通路图边数据可能存档在案） |
| envipath 上游 BBD 缺口 ~414 条 | 决策项 | 凭证在 BiocrewV2/.env 线；属 S3 范畴，须用户批 + 泄漏审计先行 |
| 12 道 B 分歧题 | 维持原判 | 待 mibPOPdb 金标流程建立后一并回看（已写入 2.6.6） |

## 七、支撑数据与路径表

入仓（池级统计与脚本，无任何金标产物 SMILES）：

- `reports/phase_s1_hit60/pool_rescue/eawag_diff_stats.json` — 路二全量差集数字（A/B/C/D 四口径）
- `reports/phase_s1_hit60/pool_rescue/mibpop_access_facts.json` — 路一许可/获取/结构事实卡（含论文引文与核验证据）
- `reports/phase_s1_hit60/pool_rescue/_eawag_diff.py`、`_mibpop_structure_check.py` — 复现脚本（只读资产，产物见上）

gitignored 中间件（`reports/phase_s1_hit60/pool_rescue/intermediates/`，含源库原始记录的 SMILES——按交付纪律不入仓，.gitignore 已登记）：

- `mibpop_intermediates.tsv`（593 行中间体：通路/母体/名称/SMILES/CAS）
- `mibpop_compounds.tsv`（357 行 POP 母体化合物）
- `mibpop_organisms.tsv`（115 行菌株记录含 Primary Intermediate 文本）
- `mibpop_surface_collision.json`（分子级命中明细）、`mibpop_routing_buckets.json`（路由三桶）
- `mibpop_imeta45_paper_fulltext.xml`、`envipath_nar2024_paper_fulltext.xml`（两篇论文全文存档）
- `eawag_diff_rows.tsv`（差集行明细——本轮为空表，留档口径）

远端只读核验记录：library_full/corpus_v1/donor_index/donor_product SHA 与本地一致（2026-09-30）；远端中间产物均在 chenyu /tmp（易失，已回拉本地）。

## 八、复现要点

- 路二差集：`~/miniconda3/envs/depending43/bin/python reports/phase_s1_hit60/pool_rescue/_eawag_diff.py`（读 assets 只读，出 eawag_diff_stats.json）
- 路一结构/对撞：`~/miniconda3/envs/depending43/bin/python reports/phase_s1_hit60/pool_rescue/_mibpop_structure_check.py`（读 intermediates/ TSV + assets；TSV 由远端 `/tmp/extract_tsv.py` 从 PMC/GitHub 原始 xlsx 生成，生成脚本逻辑内嵌于本报告过程，关键列映射：s002 列 0/1/2/6/3，POP_Compounds 按 r 属性列定位）
- 调研来源：Europe PMC REST（PMC10989864 论文与补充材料）、GitHub API（monsterZeng/MIBPOP）、envipath.org 探测、NAR 2024 enviPath 论文（PMC11304562）——全部经远端 chenyu curl，只读

---

## 通俗版（术语对照在文末）

**这次要回答的问题**：闭卷考试没题了（56 道全进了 dev 集），老师定了两条找题路线，我这次把两条都摸了一遍底。

**mibPOPdb 这条路**：它是个"微生物降解持久性污染物"的数据库——什么菌能把什么毒物拆成什么。查证结果：论文开放、数据免费、要求引用，**用起来没有许可障碍**。数据本身拿到的部分很干净：593 个降解中间产物，573 个都能转成标准化学结构式，还按 48 条降解通路分好了组。但**最大的坑：库里只有"清单"没有"路线图"**——知道通路里有这些分子，不知道谁连着谁。要出"给底物猜产物"的题，得靠人工把通路图里的箭头一条条重建出来，还得两个人核对。能出的题估算 60 到 150 道，目标是 100–150，**够不够看运气和人工投入**。它的官网恰好宕机了，全量数据拿不到，这是个明确的等待项——官网哪天恢复，题量上限直接翻几倍。

**EAWAG 这条路**：老师问"我们有没有没用过的 EAWAG 数据可以当考题"。答案干脆：**没有**。两份数据库逐条对过，内容一模一样——所谓差集算出来是 **0**。而且那份数据库本来就是引擎的"直查答案本"（recorded 路由），拿它出题等于开卷考试。这条路**判死**。

**合起来**：两条路凑不出老师要的 100–150 道新盲测题。按规矩，我们**回报缺口，不自己偷偷放水**——放宽口径是老师那边的事，怎么放宽都留了痕迹可以重算。

**下一步选项**（给用户的三选一）：① 等 mibPOPdb 官网恢复再评估全量；② 先按离线数据走窄口径（12–18 人日，55–135 题，接受可能不到 100）；③ 老师/用户另定第三源。

### 术语对照

- **闭卷/盲测**：题目和答案在系统平时的"复习资料"（证据资产）里没有现成记录，考的是真本事
- **配对级泄漏**：题面底物和金标产物在某个资产里以"同一反应"的形式成对出现——等于答案被抄进考场
- **分子级可见性**：答案分子在资料库里出现过（但不是作为这道题的答案）——不算作弊，但要登记在案
- **recorded 路由**：引擎的"直查模式"——底物在降解记录库里查得到，就直接抄记录里的产物
- **rank/路由题占比**：一道题最终答案走的是直查、排序还是凭空生成——老师要求新题卷里这三种都要有合理配比，排序类题才有验证价值
- **cn_identity**：把分子式按"电荷归一化+忽略立体异构"重新标准化后的身份证，用于比对两个写法不同的分子是不是同一个
- **差集**：A 有而 B 没有的部分——本次算出来是 0
- **金标**：标准答案；**dev 集**：开发调试用考卷；**冻结**：定稿不许再改
- **I3 盲性**：核对答案的人不许看模型的答卷，防止被带偏
- **POPs**：持久性有机污染物（如 DDT、多氯联苯、阻燃剂）——环境毒物，正好是我们系统的主战场
