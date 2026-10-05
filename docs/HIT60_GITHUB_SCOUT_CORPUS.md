# HIT60 侦察附册：微生物/环境降解反应数据集与语料（GitHub + 网络检索）

- 侦察窗口：2024-09 → 2026-09（存量老库有重大更新的记"存量更新"）
- 检索执行日：2026-09-29
- 性质：**情报储备（附册）**。本报告不构成 S3（语料扩充）启动建议；S3 启用前提（泄漏审计 + 报告口径降级为"覆盖+排序"）不变。本轮**未做任何数据集成/入库**。
- 已在库（只记存量更新，不重复列）：BRENDA 2026、RHEA 142、EnzymeMap、enviPath、BIOSYSMOdb（CC BY-NC-SA）、UM-HP。
- 检索环境说明：本环境 GitHub API（api.github.com）直连超时，全部改用 WebSearch 间接检索；故各仓库 LICENSE 字段多数**未能直接打开核实**，标注"待核"者启用前必须人工确认。

---

## 一、大白话摘要（≤200 字）

没有"下一代主粮"级新库，但有三类值得 S3 时优先对账：① RHEA 血统补全包——BioRGroup（2025，把 RHEA 引用的约 1.3 万个含 R 基团模糊 ChEBI 分子展开成具体结构）和 ReactZyme（2024，17.8 万酶-反应对，CC0/MIT）；② 疑似漏收的老底子——ECREACT（约 6.2 万条原子映射生物催化反应，2022）及其升级合集 EVODEX（约 8.3 万条，持续维护）；③ Eawag 2026 漆酶-污染物酶级新基准。注意：ECREACT 含 BRENDA 衍生数据，入库前许可与泄漏审计必做。

---

## 二、情报总表（按 规模 × 新鲜度 × 许可友好 排序）

| # | 名称 | 类型 | 规模（反应/分子） | 许可 | 新鲜度/维护 | 与已知库关系 | S3 适用性 |
|---|------|------|------------------|------|-------------|--------------|-----------|
| 1 | **BioRGroup dataset**（Gricourt & Faulon, Sci Data 2025） | 数据集 | 约 13,000 个 R 基团分子展开（RHEA 引用的 ChEBI） | 论文 OA（CC BY 倾向）；数据仓许可**待核** | 2025-10 发布，新 | RHEA release 134 直系衍生 | **高**（RHEA 模糊反应具体化的直接杠杆） |
| 2 | **ReactZyme**（NeurIPS 2024 D&B） | 数据集+基准 | 178,463 酶-反应对 / 7,726 反应（SwissProt+RHEA ≤2024-01-08） | GitHub CC0-1.0；Zenodo MIT（已核实） | 2024-09 发表，库稳定 | 反应侧与 RHEA 高重叠；酶-底物配对为新 | **中高**（检索评测基准 + 配对语料） |
| 3 | **EVODEX**（UCB-BioE-Anderson-Lab） | 数据集+工具 | 约 83,000 条合并反应（EnzymeMap+ECREACT），含"partial reactions"机理片段 | 仓库许可**待核** | PyPI 在更（0.1.23+），2026 年 ACS 论文仍在用 | EnzymeMap/ECREACT 上游合集 | **中高**（现成加工语料 + 反应规则库） |
| 4 | **ModelSEED Biochemistry, 2026 update** | 通用生化库 | 约 56,000 反应 / 46,000 化合物（KEGG/MetaCyc 等整合） | 仓库许可**待核**；内含 KEGG/MetaCyc 衍生条款风险 | 2026-09 论文更新，活跃 | 通用代谢，环境降解重叠低 | 中（体量大但需重映射+去重） |
| 5 | **ECREACT**（Probst et al., Nat Commun 2022） | 数据集（窗口外老库） | 约 62,222 条原子映射生物催化反应（7 大 EC 类） | 仓库许可**待核**；**含 BRENDA 衍生 → 禁商用风险** | 2022 冻结；2024-2025 仍被广泛引用作训练集 | 与 BRENDA/RHEA 衍生语料部分重叠 | **高（补漏优先）**但许可风险高 |
| 6 | **Eawag 漆酶酶级基准**（bioRxiv 2026-01，Yu/Zhang/Steiner/Poltorak/Robinson） | 基准+数据 | 环境细菌漆酶 × 污染物水体归宿（规模**待核**） | 预印本；数据许可**待核** | 2026-01，新 | enviPath 生态（Eawag 系） | **高相关基准**（闭卷出题风向标） |
| 7 | **MERMaid / MERMES**（Matter 2025，the-matter-lab） | 工具（VLM 反应挖掘） | 从 PDF 挖反应建知识图谱（规模视语料而定） | 预印本 CC BY；代码许可**待核** | 2025-07 发表；MERMES 为后继在推 | 无重叠（自建语料工具） | 中（自建环保文献反应语料的流水线） |
| 8 | **mibPOPdb**（iMeta 2022） | 数据库（窗口外老库） | 3,479 菌株条目（POPs，含降解反应/基因/酶，实验验证） | **待核** | 2022 冻结，2024-2026 持续被引 | 与 enviPath 主题重叠、粒度不同 | 中低（实验验证金标准，规模小） |
| 9 | **NORMAN-SLE / SusDat** | 化合物清单 | 100+ 清单、>100 万条目（含 TP 清单，SMILES/InChI 可下） | 逐清单不一（多 CC 系），**待核** | 持续更新（2025-05 快照） | 产物级清单，非反应对 | 低中（作"产物覆盖"核对表） |
| 10 | **Plastic-MBR DB**（Environ Microbiol Rep 2025-09） | 多组学数据库 | 塑料降解微生物基因/组学（非反应语料） | **待核** | 2025-09，新 | 与 PlasticDB 主题重叠 | 低（无反应对） |
| 11 | **PlasticDB**（2022） | 数据库 | 875 物种 × 塑料（酶/文献） | **待核** | 存量 | 同上 | 低 |
| 12 | **OASIS Microbial Degradation Database** | 商业库 | 551 代谢图 / 514 农药母体 | **商业（OASIS LMC）** | 存量 | 农药路径，与 enviPath Eawag-Soil 主题重叠 | 不可入库（许可）；仅可作外部对照 |
| 13 | **CARE**（2024） | 酶分类/检索基准套件 | 酶检索基准（规模未核） | 待核 | 2024 | 与 ReactZyme 同用途 | 低中（评测用） |
| 14 | **PFAS-AI / AI4PFAS**（GitHub） | 小型数据/管道 | PFAS 降解产物识别管道；毒性数据 | 待核 | 新但维护度存疑 | 无重叠 | 低 |

### 存量更新（已在库，仅登记版本动态）

| 名称 | 动态 | 结论 |
|------|------|------|
| RHEA | 当前最新 release **即 142（2026-09-02）** | 我们已是最新版，无升级空间；增量方向只剩 BioRGroup 式展开 |
| BRENDA | 2026 版已在用 | 无动作 |
| EnzymeMap | 最新仍为 v2（2023，BRENDA 2023 底），**未见 2024-2026 新版** | 无动作；其血统已汇入 EVODEX |
| enviPath | 2024 大更新论文（Hafner et al.，NAR 系，PMC11304562）：新增数据集/包与 ML 功能；注：Eawag-Soil 包为 2017 老包（农药土壤降解+半衰期） | 建议对账 2024 论文新增包是否已入我们镜像 |
| BIOSYSMOdb | Zenodo 记录 2025-02（CC BY-NC-SA） | 已知，无动作 |

---

## 三、单项衔接评估（S3 路线）

### 1. BioRGroup dataset（最亮眼）
- 是什么：把 RHEA 反应里含 R 基团的模糊 ChEBI 分子，用 PubChem 实分子匹配展开成完全确定的结构（基于 RHEA release 134 抽取模板）。论文：Nature Scientific Data 2025（s41597-025-05983-w）；数据 DOI 10.57745/V3URYA（Recherche Data Gouv）。
- 对 S3 的意义：我们语料是 RHEA 衍生 → RHEA 里大量"_generic"反应因 R 基团无法做结构检索而被浪费；BioRGroup 相当于给这部分反应发"具体分子身份证"，是**对现有 4.3 万语料做乘法**而不是加法，直接提升闭卷 hit 的检索覆盖。
- 工程量：中。需要按 ChEBI ID 与 RHEA 反应模板回联，展开成具体底物-产物对后并入检索索引（估计新增数万可检索单位，具体倍数需实测）。
- 泄漏审计：重点是展开产物若与闭卷评测题分子重合，需按规范化反应 SMILES/InChI 与评测集对撞去重后再入检索库。
- 许可：Sci Data OA（CC BY 倾向），数据仓许可待核；RHEA 本体 CC BY 4.0，衍生链干净，风险低。

### 2. ReactZyme（NeurIPS 2024 D&B）
- 178,463 酶-反应对（178,327 酶 / 7,726 反应），SwissProt+RHEA（截至 2024-01-08）。GitHub WillHua127/ReactZyme（CC0），Zenodo 13635807（MIT）。
- 对 S3：反应侧与 RHEA 142 重叠高（非新反应粮草）；真正价值在**酶-底物配对层**（比我们"反应+EC"粒度更细），以及它本身就是"给定反应检索酶"的排序基准——与我们检索短板正对。
- 工程量：低（结构化好、双许可明确）。泄漏审计：其数据源时间戳 2024-01-08，需与闭卷评测题核对来源是否同源（SwissProt 注释时间切分是常见泄漏通道）。
- 许可：CC0/MIT，商用友好，无风险。

### 3. EVODEX（UCB-BioE-Anderson-Lab/EVODEX）
- Heid 等"提取-清洗-验证-预测"框架的产物：EnzymeMap + ECREACT 合并约 83,000 条原子映射反应，并提供 partial reactions（机理片段）与反应规则库；PyPI 包在更，2026 年 ACS 论文仍在引用，属**活跃维护**。
- 对 S3：现成的"深加工语料"——已做原子映射与平衡校验，并入工程量小；partial reactions 可作为检索侧的"机理级"模糊匹配特征。
- 泄漏审计：其上游 EnzymeMap 基于 BRENDA 2023，与我们的 BRENDA 血统重叠，需做来源级去重。
- 许可：仓库 LICENSE 待核（加州大学伯克利实验室仓库）；启用前必须确认（BRENDA 衍生链意味着即便仓库许可宽松，再分发也可能受 BRENDA 条款约束）。

### 4. ModelSEED Biochemistry 2026 update
- 2026-09 更新论文：约 46,000 化合物 / 56,000 反应（KEGG、MetaCyc 等多源整合），KBase 底座。GitHub ModelSEED/ModelSEEDBiochemistry。
- 对 S3：体量最大的免费通用生化反应池，但**环境降解/xenobiotic 专属内容占比低**，属于"广度粮草"而非"领域粮草"；对闭卷环境题的边际覆盖提升有限。
- 工程量：大。化合物 ID 体系（别名/重命名）与我们的 ChEBI 体系需大规模重映射，去重负担重。
- 泄漏审计：若闭卷题源自 KEGG/MetaCyc 系出题方，需按反应规范化指纹去重。
- 许可：仓库许可待核；其内含 KEGG/MetaCyc 衍生条目，再分发条款是灰色地带，商用需法务过目。

### 5. ECREACT（"早该有"级补漏候选）
- Probst et al., Nat Commun 2022：约 62,222 条覆盖 7 大 EC 类的原子映射生物催化反应；GitHub rxn4chemistry/biocatalysis-model（IBM RXN）。
- 对 S3：**如果我们的 4.3 万语料只走了 BRENDA/RHEA 衍生线而没收 ECREACT，这是第一优先对账项**——它是文献+多源清洗的原子映射反应集，2024-2025 仍是酶反应预测的标准训练集。
- 工程量：低-中（数据规整，CSV 可得）。泄漏审计：四源拼接（含 BRENDA 系），需按反应指纹与现有语料和评测集双向对撞。
- 许可：仓库许可待核；**BRENDA 衍生 → 禁商用风险明确存在**，与 BIOSYSMOdb 同级风险，入库前许可结论必须落地。

### 6. Eawag 漆酶酶级基准（bioRxiv 2026-01）
- Yu, Zhang, Steiner, Poltorak, Robinson（Eawag/ETH）："An enzyme-level benchmark based on environmental bacterial laccases for predicting contaminant fate in water"。
- 对 S3：不是大粮草，但**是闭卷评测的风向标**——环境转化预测正从"路径级"走向"酶级"，未来闭卷新题很可能出自这类基准。数据是否随附开放、规模多大，需拿到预印本正文核实（DOI 10.64898/2026.01 线索）。
- 工程量/风险：暂只做跟踪登记，不涉及入库。

### 7. MERMaid / MERMES（反应挖掘工具）
- Matter 2025（多伦多 Matter Lab/Aspuru-Guzik 组）：VLM 端到端从 PDF（图、scheme、表）挖反应并建知识图谱；GitHub the-matter-lab/MERMaid，后继 aspuru-guzik-group/MERMES 转 HTML 挖掘。
- 对 S3：这是"自己造粮"的流水线——可定向喂生物降解/环境化学文献，半自动产出反应对（再配人工质检）。若 S3 启用且现成库不够，这是扩展路径。
- 工程量：高（管线+算力+质检）。泄漏审计：从文献挖出的反应天然与评测题文献同源，去重必须做。
- 许可：预印本 CC BY；代码许可待核。

### 8. mibPOPdb（老库补漏，实验验证金标准）
- iMeta 2022：3,479 菌株条目，POPs 微生物降解，含降解反应/基因/酶，**实验验证**属性突出。
- 对 S3：规模小、非 SMILES 化反应语料，不宜作主粮；但"实验验证"子集适合做闭卷评测的**金标准种子**或检索命中质量的人工核对集。
- 许可：待核；网站型数据库，可能无批量下载条款。

### 9-14. 低适用项（一句话结论）
- **NORMAN-SLE/SusDat**：>100 万化合物条目含转化产物清单，可作"产物覆盖"核对表，非反应对，不入检索语料。
- **Plastic-MBR DB（2025）/ PlasticDB（2022）**：菌株-塑料-组学，无反应对；仅当闭卷题转向塑料降解时再评估。
- **OASIS Microbial Degradation Database**：551 农药代谢图但商业许可，**禁止入库**，只能作外部预测对照。
- **CARE（2024）**：酶分类/检索基准，评测用途，与 ReactZyme 二选一即可。
- **PFAS-AI/AI4PFAS**：PFAS 降解产物识别管道/毒性数据，规模小、维护存疑，暂记。

---

## 四、排除与澄清（避免后续重复侦察）

1. **Uni-ReaX**：检索确认为**不存在**（arXiv/期刊均无此名），疑为讹传，勿再投入。
2. **TSAR**：确认为 EU JRC 的 QSAR 模型注册工具（tsar.jrc.ec.europa.eu），与生物转化语料无关；关键词域里可删。
3. **Open Reaction Database（ORD）**：活跃但以有机合成为主，酶/环境反应占比低，边缘资源，暂不入册。
4. **gutBug/gutMGene 等肠菌代谢工具链**：偏医药肠菌方向，本轮未深挖；若闭卷题涉及异生菌代谢可再查。

---

## 五、泄漏审计与口径提醒（S3 若启用）

- 所有上述数据集入库前：与闭卷评测题做**规范化反应 SMILES / 产物 InChIKey 双向对撞**；记录每条的来源时间戳（如 ReactZyme 的 2024-01-08、BioRGroup 的 RHEA 134 基线）。
- BRENDA 衍生链（ECREACT、EVODEX）与 BIOSYSMOdb（CC BY-NC-SA）同属禁商用风险区，需法务/许可结论先行。
- 启用 S3 当天起，报告口径必须降级为"覆盖+排序"，不得再写端到端命中率结论——此为既定纪律，本报告不改变它。

---

## 六、检索式附录（供复现与下轮增量）

Web 检索（实际执行，均已跑）：
1. `biodegradation database 2025 new dataset microbial degradation reactions`
2. `xenobiotic metabolism dataset github 2025 machine learning transformation products`
3. `enviPath update 2025 new version Eawag biodegradation pathway database`
4. `TSAR Eawag biotransformation transformation structure-activity relationship tool 2024`
5. `RHEA knowledgebase release 2026 latest version reactions`
6. `ModelSEED Biochemistry Database 2026 update paper compounds reactions sources`
7. `"Eawag-Soil" enviPath pesticide soil biodegradation half-life package data`
8. `"Plastic-Microbial BioRemediation" database 2025 data availability`
9. `Uni-ReaX universal reaction dataset benchmark 2025 arxiv`
10. `MERmaid universal multimodal mining chemical reactions PDFs 2025 github dataset license`
11. `PFAS transformation products dataset 2025 github machine learning degradation`
12. `EnzymeMap github reaction atom mapping Rhea Brenda update 2025`
13. `ReactZyme benchmark enzyme reaction mining GitHub dataset size license`
14. `EVODEX dataset atom-mapped biochemical reactions ECREACT license github 2025`
15. `HuggingFace dataset enzyme reactions instruction tuning LLM 2025 Rhea Brenda corpus chemistry`
16. `Open Reaction Database ORD 2025 update enzyme reactions data dump license`
17. `bioRxiv 2026 benchmarking enzyme-level environmental biotransformation prediction enviPath`
18. `mibPOPdb persistent organic pollutants microbial strains database license reactions`
19. `NORMAN suspect list exchange transformation products 2025 chemicals list download`

GitHub API（规划但环境超时，下轮可补）：
- `https://api.github.com/search/repositories?q=biodegradation+database&sort=updated`
- `https://api.github.com/search/repositories?q=enviPath+OR+biotransformation&sort=updated`
- `https://api.github.com/search/repositories?q=microbial+degradation+dataset`
- 待核清单（下轮直接开 LICENSE 文件）：the-matter-lab/MERMaid、UCB-BioE-Anderson-Lab/EVODEX、rxn4chemistry/biocatalysis-model、ModelSEED/ModelSEEDBiochemistry、Recherche Data Gouv 的 BioRGroup 数据记录、Eawag 漆酶基准随附数据。

---

*本报告为情报储备附册，全部结论以"待核"标注为准绳；未执行任何下载、集成或语料变更。*
