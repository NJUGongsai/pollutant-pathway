# 语料血统对账：v1 检索语料是否含 ECREACT / EVODEX 记录

- 对账执行日：2026-09-29
- 对账对象：v1 检索语料（约 4.3 万条反应）
  - 远端本体：`chenyu:/usrdata/EnzymeCAGE_data/workspaces/dependingv3/assets/corpus_env/corpus_v1.jsonl`（v3 冻结部署）
  - 本仓副本：`assets/v3_reactions/corpus_env/corpus_v1.jsonl`，SHA256 `186a1dad17e9c92ac5beb0415f1b806146ac804206fc53c6e5dd941b0044b58c`，与远端**逐字节一致**（本轮所有字段级分析对二者等价）
- 方式：远端只读（SSH 查验 + curl 拉公开样例），零费用，未修改远端任何文件

---

## 一、结论（三选一）

**明确不包含。** v1 检索语料 43,177 条记录中，没有任何一条带 ECREACT 或 EVODEX 血统：来源枚举只有 RHEA 与 enviPath 两个值，全部 ID/出处字段与 ECREACT/EVODEX 的 ID 特征零交集，且语料零原子映射记录（ECREACT 的定义特征），构建管道上游亦无 ECREACT/EVODEX 输入。

唯一保留意见（内容层面，非血统层面）：ECREACT 自身含 6,715 条 source=rhea 的子集，与我们 37,100 条 RHEA 记录**可能存在同一化学反应的内容重合**——这是双方独立从 RHEA 知识库收录的同源重叠，不构成我方语料的 ECREACT 血统。精确量化需反应指纹对撞，属 S3 泄漏审计范畴，本轮未做。

---

## 二、证据

### 2.1 语料记录级（本体文件）

| 检查项 | 结果 |
|---|---|
| `source_type` 枚举 | 仅 `rhea`(37,100) + `envipath`(6,077)，无其他值 |
| `record_id` / `source_id` 前缀 | 仅 `rhea:10001..86965`（真实 RHEA 反应 ID 区间）与 `envipath:btXXXX-YYYY#hash` / `envipath:UUID`（enviPath EAWAG 系包 ID） |
| 全文串扫（大小写不敏感） | `ecreact` / `evodex` / `brenda` / `enzymemap` / `metanetx` / `pathbank` / `sabiork` / `pistachio` / `rxn4chemistry` 全部 **0 命中**（corpus_v1.jsonl 与 donor_index.jsonl 双文件） |
| 原子映射字段 | 43,177 / 43,177 条 `mapping_status="absent"`、`atom_mapping=null`，**零原子映射记录**；而 ECREACT 的标志特征就是原子映射反应 SMILES——若混入必有痕迹 |

### 2.2 管道级（构建代码与原始输入，远端 dependingv3）

- 构建器 `src/depending/ra/corpus.py`（docstring 自述：RHEA 子集无 AAM，atom_mapping 恒为 null）；上游输入清单在 `src/depending/ra/config.py`，**仅两类**：
  - RHEA 官方 dump：`demov3/data/rhea/`（`rhea-rel141.rd.gz`、`rhea-rxn.tar.gz`、三个官方 TSV）。`PROVENANCE.txt` 记录：**RHEA release 141（2026-06-10），CC-BY-4.0，ftp.expasy.org 直下，下载日 2026-08-12，逐文件 SHA256**——出处链干净封闭，无中间商数据集。
  - enviPath：`reaction_v3/data/lib_envipath/source_substrates.json`（EAWAG-BBD 等包，另有 `PROVENANCE.txt` 记录 envipath.org 包 ID 与抓取日 2026-08-15）。
- 远端全工作区扫描：`dependingv3` 资产目录与 `/Volumes/CC/Enzyme_Agent/depending`（原始数据根，深度 6）的**文件名与文件内容均无 ecreact/evodex 命中**。

### 2.3 对照物特征（远端 curl 实拉公开仓库，非二手资料）

| 数据集 | 实测格式 | 与我方语料对照 |
|---|---|---|
| **ECREACT**（github rxn4chemistry/biocatalysis-model，`data/ecreact-1.0.csv`） | 62,222 行（与公开规模吻合），三列 `rxn_smides,ec,source`；source 构成：**pathbank 27,835 / metanetx 19,176 / brenda 8,496 / rhea 6,715**；记录以原子映射 rxn_smiles 为身份，**无独立记录 ID 体系** | 我方语料无任何 `*_reaction_smiles` 式 source、无原子映射 SMILES、无 brenda/metanetx/pathbank 字样 |
| **EVODEX**（github UCB-BioE-Anderson-Lab/EVODEX，`evodex/data/EVODEX-*.csv`） | ID 形如 `EVODEX.2.1-E1`、`EVODEX.2.1-P1`（列：id, smirks/mass, sources, hash）；sources 引用 EVODEX 算子链 | 我方语料无 `EVODEX.*` ID，零命中 |

---

## 三、v1 检索语料来源构成表

### corpus_v1.jsonl（检索主语料，43,177 条）

| source_type | 条数 | parse_note 明细 | 出处 |
|---|---|---|---|
| rhea | 37,100 | rxn-parsed 37,098 + no-structure 2 | RHEA release 141 官方 dump（expasy FTP，CC-BY-4.0，2026-08-12 下载） |
| envipath | 6,077 | eawag-soil 2,485 + eawag-sediment 1,393 + eawag-bbd 1,066 + educt(仅底物侧) 580 + eawag-sludge 553 | enviPath EAWAG 系包（envipath.org，2026-08-15 抓取） |
| **合计** | **43,177** | | **ECREACT：0；EVODEX：0** |

### 附：配套与隔离语料

| 文件 | 规模 | 构成 |
|---|---|---|
| `donor_index.jsonl`（供体索引） | 95,782 | rhea 90,026 + envipath 5,756（同样零 ECREACT/EVODEX 命中） |
| `corpus_env_eval/`（评测隔离语料，**不进检索库**） | 42,307 | rhea 37,100 + envipath 5,207（RHEA 侧与主语料同源同量） |

---

## 四、若后续补录 ECREACT 的工程量粗估（仅登记，不构成启动建议）

- 数据面：单 CSV、三列、62,222 行，规整；新增一个 `ra/` 式 source 模块（解析原子映射 rxn_smiles → 决定保留/剥离映射 → 规范化 SMILES）即可走现有构建器。
- 主要工作量在**去重与前置审计**而非解析：与现有 37,100 条 RHEA 记录按规范化反应指纹对撞（ECREACT 的 rhea 子集 6,715 条预期数千级重合）、与闭卷评测集双向对撞（泄漏纪律）；随后 rebuild corpus + donor_index + 检索索引。
- 粗估：纯工程 **约 2–4 人日**；但**许可结论必须先行**（含 8,496 条 BRENDA 衍生子集，禁商用风险；pathbank/metanetx/rhea 子集各受上游条款约束）——与 HIT60 侦察附册（`docs/HIT60_GITHUB_SCOUT_CORPUS.md` 第 5 节）的判断一致。
- EVODEX 若一并考虑：属"深加工粮"（EnzymeMap+ECREACT 合并 + 反应规则库），补录 ECREACT 后再评估增量价值，避免双跳引入。

---

## 五、复现命令要点

- 远端 SHA 对拍：`sha256sum /usrdata/.../corpus_env/corpus_v1.jsonl` → `186a1dad…4b58c`（与本地 `assets/v3_reactions/corpus_env/corpus_v1.jsonl` 一致）
- 来源枚举：逐行解析 `source_type` / `parse_note` 计数（结果见上表）
- 串扫：`grep -ci` 于 corpus_v1.jsonl、donor_index.jsonl（全 0）
- 管道：`grep -n 'corpus_env\|corpus_v1' src/depending/ra/corpus.py src/depending/ra/config.py`；上游 PROVENANCE：`demov3/data/rhea/PROVENANCE.txt`、`reaction_v3/data/lib_envipath/PROVENANCE.txt`
- 对照物：`curl -r 0-2000 https://raw.githubusercontent.com/rxn4chemistry/biocatalysis-model/main/data/ecreact-1.0.csv`（头部样例）；全量流式 awk 统计 source 列（62,222 行）；EVODEX `evodex/data/EVODEX-E.csv` 头部样例

---

## 勘误（2026-09-30，用户指正）

原报告把"语料"框窄为 corpus_v1（43,177 条 = rhea 37,100 + envipath 6,077），未覆盖系统其余证据资产（library_full、USPTO 模板/类比索引、corpus_templates、envipath/EAWAG 规则、donor_index 等）。本节补全证据面；逐资产明细与 dev 56 题泄漏矩阵见 `reports/phase_s1_hit60/dev_gold/FULL_SURFACE_LEAK_AUDIT.md`（gitignored，含金标级细节；资产级审计数据 `full_surface_asset_audit.json` 同目录）。

### E.1 全证据面清点（2026-09-30 实测）

| 资产 | 规模 | 血统/来源构成 | ID 形态 |
| --- | --- | --- | --- |
| `v3_reactions/corpus_env/corpus_v1.jsonl` | 43,177 行 | rhea 37,100（release 141）+ envipath 6,077（EAWAG-SOIL 2,485 / SEDIMENT 1,393 / BBD 1,066 / educt 580 / SLUDGE 553） | `rhea:10001..86965`、`env:…`、`envipath:btXXXX-YYYY#hash` |
| `v3_reactions/corpus_env/donor_index.jsonl` | 95,782 行（16,875 个 distinct donor_smiles = 引擎 n_donors） | rhea 90,026 + envipath 5,756 | `donor_record_id`（rhea:/env:） |
| `v3_reactions/library/library_full.jsonl` | **4,454 行 / 772 个 btid** | **纯 EAWAG 系**：EAWAG-SOIL 1,977 + EAWAG-BBD 1,002 + EAWAG-SEDIMENT 931 + EAWAG-SLUDGE 544（`package` 字段逐行统计） | `btid`（bt0001 式 BBD 生物转化号 / `EAWAG-SEDIMENT:` 包前缀）、`reac_id`（r0002 式或十六进制哈希） |
| `v3_reactions/eawag/donor_product.jsonl` | 1,066 行 | EAWAG-BBD 给体-产物对 | `btid`+`reac_id` |
| `v3_reactions/eawag/rules_new_clean.jsonl` | 49 行 | EAWAG 规则（rxnmapper 回环校验，带示例给体/产物） | `btid`+`reac_id` |
| `v3_reactions/envipath/templates_implicitH.jsonl` + `templates.tsv.gz` | 286 + 287 行（含表头） | enviPath 规则模板（EAWAG 系包挖掘） | `envipath:btXXXX-YYYY` |
| `v3_reactions/templates/uspto_templates.json` | 188,725 模板 | **USPTO 专利反应**（`n_train`=409,035 条训练反应，freq 合计 409,006） | 反应 SMARTS 模板串（无记录 ID） |
| `analog/uspto_relaxed_index_v1.jsonl` | 188,725 行（SHA `28fdf6bf…`） | 上行 USPTO 模板的 r1/r2/r3 放宽索引（v4 derived，2026-09-22 构建，构建报告留档） | `template_id` = 模板串 |
| `analog/corpus_templates_v1.jsonl` / `v2.jsonl` | 各 17,183 行 | corpus 映射模板（v1 自 corpus_mapped；v2 = v43-analogmap-1 确定性 MCS 重映射，行数不变） | `env:EAWAG-BBD:btXXXX#rYYYY#Lnnnnn` |
| `v3_reactions/rankers/*.txt`（3 个） | — | LightGBM 模型转储（27 特征），无分子内容 | — |
| `v3_reactions/calibrators/*.json`（2 个） | — | isotonic 分箱数值，无分子内容 | — |

### E.2 核心修正：library_full 不是 BRENDA / EnzymeCAGE union 血统

此前（旧 298 Phase A 时代）"library_full 是 recorded 主库、182/298 底物重叠"的记录容易让人猜测它是 EnzymeCAGE union / BRENDA 派生大库。**实测否定**：4,454 行全部带 `package` 字段且枚举仅 EAWAG-SOIL/BBD/SEDIMENT/SLUDGE 四值；全文件 `ecreact/evodex/brenda/enzymemap/metanetx/pathbank` 串扫 **0 命中**；远端 `/usrdata/EnzymeCAGE_data/workspaces/dependingv3/assets/library/library_full.jsonl` SHA256 `042e9e2c…` 与本仓逐字节一致（EnzymeCAGE 只是服务器目录名，不是数据血统）。v3.5 资产 README 的自述（"EAWAG-BBD + EAWAG-SOIL/SLUDGE/SEDIMENT packages, 4,454 rows, 2,678 donors"）与实测吻合。

因此原报告"语料不含 BRENDA"的表述在全证据面下**不需要修正为"library 含 BRENDA"——library 也不含**：corpus 不含、library 不含、全部 22 项资产都不含 ECREACT/EVODEX/BRENDA 血统标记。

### E.3 ECREACT 缺席结论在全证据面下仍成立（血统层面）

- 全部新增资产（library_full、eawag 两件、envipath 两件、uspto_templates、uspto_relaxed_index、corpus_templates v1/v2、donor_index）串扫 `ecreact/evodex/brenda/enzymemap/metanetx/pathbank` **全部 0 命中**（大小写双写各扫一遍）。
- USPTO 模板为专利反应宇宙（409,035 条），与 ECREACT（pathbank/metanetx/brenda/rhea）采集面不相交；无原子映射记录混入语料的旧结论不变。
- 内容层面保留意见两条（血统无关，与正文 §一 的 rhea 子集保留意见同级别）：① ECREACT rhea 6,715 子集与我方 rhea 37,100 可能内容重合（原报告已声明，未变）；② EAWAG 环境转化分子与 ECREACT 的 metanetx/brenda 分子可能有零星同分子重合——未做指纹对撞，如实登记为未量化。

### E.4 顺带对账：n_corpus_records=42,646 vs 文件 43,177 行

43,177 行中存在 **303 个 envipath 重复 record_id（多出 531 行**，全部 source_type=envipath，如 `env:EAWAG-SEDIMENT:<uuid>` 一式两/三份）；引擎按 record_id 去重装载 → **42,646 = 43,177 − 531**，与 `docs/ASSET_WIRING_REPORT.md` 第 6 节引擎加载口径吻合。donor 侧同法对上：95,782 行 → 16,875 distinct donor_smiles = n_donors。无静默丢数，均为重复行去重。

### E.5 连带补做：dev 56 题全证据面泄漏审计（D2 preflight 只扫过 corpus_v1）

结论（方法沿用 D2 双口径=精确串+cn_identity，配对级判据=同记录题面在给体侧且金标在产物侧，正反双向）：

- **配对级泄漏：全部资产 0 题**（library_full 0、eawag 两件 0、corpus_templates v1/v2 0、donor_index 结构性无产物侧、USPTO/envipath 模板为 SMARTS 无成对分子）。dev 56 的"配对级闭卷"属性在全证据面下成立。
- **分子级可见性（非泄漏，如实登记）**：金标分子作为**其它给体**的产物出现在 library_full 15 题、eawag donor_product 12 题、corpus_templates 18 题；作为**给体分子**出现在 donor_index 32 题、library_full 22 题。题面底物作为给体可见：library_full 11 题、donor_index 16 题。
- **运行时证据抽查（远端 C0×2/E2×2/E3 五个完整批次，7,553–12,310 张 cardval/批）**：金标以**完整产物候选**出现在检索证据里的题数为 **36–37/56（各臂一致）**，来源构成 USPTO 模板应用 22 题 + corpus_v1 类比检索 10–11 题 + enviPath 规则 9 题（有重叠）；其中最终答卷 top-5 落金的仅 15–17 题，**约 22 题金标已在候选集里被排序/选择丢弃**。
- **对"闭卷 15%"解读的影响**：dev 的"闭卷"是**记录级/配对级**闭卷（任何资产都不存在"该底物→该金标"的现成记录），这一定性在全证据面下加固；但**不是分子级闭卷、更不是候选级闭卷**——约三分之二题目的金标能被规则泛化/类比检索合法地推演出来并进入候选集。C0 hit@1≈15%（8–9/56）的天花板不在"系统没见过答案分子"，而在"候选含金但选不出来"。该 15% 仍是对"端到端闭卷新题能力"的有效度量，但归因表述应从"检索不到"改为"生成得到、排序选不中"（重排/选择层是主杠杆，与 E1 设计动机一致）。
