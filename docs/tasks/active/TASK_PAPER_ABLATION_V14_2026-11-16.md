# 任务书：`v44-Next v1.4` 论文级单步消融实验（聚焦 `[biosysmodb121]`：`AtomTool` 专项 + 全栈架构 + `assets/` 数据库全满贯 + 判据阶梯）（2026-11-16）

> **拍板依据（2026-11-16 CC 最终确认）**：
> 1. **目标定位与唯一评测题域**：专为撰写论文主消融章节（Ablation Study）产出完整、零空格、可正面回应顶会审稿人全部质询的实证大表；**严格聚焦核心环境污染物主战场 `[biosysmodb121]`（同时并列汇报主分母 `[biosysmodb121·调参集 N=261]` 与 4 层去噪子集 `[biosysmodb121·调参干净集 N=220]`），不测 `[dev-298]`**（两题域双向不外推）；
> 2. **性能总锚点**：直接采用主窗口已结项终验的 **`v44-Next v1.4`（`T14-4D`）官方落盘数据**（[`V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md`](file:///Volumes/CC/Enzyme_Agent/v44_v13/docs/reports/V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md)）：
>    - **`[biosysmodb121·调参集 N=261]`（主分母）**：`b121_wl4_pa_11p_at16::v14s4_cons_v3_prom_adj`，`v6 Hit@1/@3/@5 = 118 / 133 / 141`（**`45.21%`** / `50.96%` / `54.02%`），附 `v4 = 80 / 96 / 102`（`30.65%`）；
>    - **`[biosysmodb121·调参干净集 N=220]`（并列必报）**：同配置下 `v6 Hit@1/@3/@5 = 113 / 127 / 134`（**`51.36%`** / `57.73%` / `60.91%`），附 `v4 = 76 / 91 / 96`（`34.55%`）；
>    - **`[biosysmodb121]` 单路基线（现成 5 批独立重复采样 `b121_wl4_pa..pe`，0 新调 API）**：主分母 `v6 Hit@1 = 104.60 ± 4.28 / 261`（**`40.08% ± 1.64%`**），干净集 `99.60 ± 3.97 / 220`（**`45.27% ± 1.80%`**），附 `v4 Hit@1 = 70.80 ± 4.32 / 261`（`27.13%`）；
> 3. **实验档位与范围**：
>    - **`AtomTool` 专项深度拆解**：正面覆盖 **① 考前原子编号执行图视图（`execution_graph` + `atom_id_map`）**、**② 交卷期正向手写算子 vs 逆向产物反推双通道**、**③ 交卷后物理拼装与守恒安检门（含化学幻觉违例率统计）**，并确立 **“真·裸大模型（无池 + 无 `AtomTool`）”** 绝对零起点；
>    - **数据库知识供给采用顶会全满贯档（7 大正交干预臂全跑）**；
>    - **多步矿化通路消融暂不实施**（按 CC 拍板留待后续单独安排）；
> 4. **算力与协作纪律**：代码实现与调度委派 `ocagent`（OpenCode 执行者），全部建池、零调用重放、判分与 Bootstrap 统计提交远端 **HPC 乌镇**（`wuzh02.hpccube.com:65091` Slurm `wzhcnormal` 32C），本机仅执行轻量单测与纯 HTTP API 并发采样。

---

## 0. 活状态总表

| 阶段 | 核心内容 | 是否付费 API | 预计调用 / Token | 当前状态 |
| :--- | :--- | :---: | :---: | :--- |
| **Stage P1-A** | **论文表 1（存量部分 + `AtomTool` 后置拆解）+ 论文表 4 零调用重放**：新增默认 `False` 的消融开关（去 `AtomTool` 提示词视图、关逆向反推、关裂解补碳、裸提案免 `AtomTool` 安检门判分与幻觉率统计），在乌镇 HPC 32C 对 `[biosysmodb121]` 完成正控 `diffs == 0` 对账、存量重放行与五口径阶梯表 | 否（`0` call） | `0` | ✅ 已完成 |
| **Stage P1-B** | **论文表 2 全满贯 7 个数据库消融池乌镇 32C 并行构建与零调用 `GIP@16` 审计**：先验正控 `DB0_full_ctrl` 与 `pools_v14_wl4_b121.json` `261/261` 逐题逐槽相等（`diffs == 0`），再构建 `DB-1..DB-7` 共 7 个 `@16` 消融池，校验 `n_admission_failures == 0` 与 `NoSelf` 零自记录泄漏，输出全表 `GIP@16` 与错池率 | 否（`0` call） | `0` | ✅ 已完成 |
| **Stage P2** | **`[biosysmodb121]` 付费在线采样（仅 9 批单路）与乌镇 32C 终判合表**：<br>• **`AtomTool` 专项 2 批**：`AT-RawBlind`（无池+无 `AtomTool`）+ `AT-FullPool-NoGraph`（满配 `wl4@16` 池但去 `AtomTool` 分子图与编辑协议）（`522` calls）<br>• **表 2 数据库全满贯 7 批**：`DB-1..DB-7`（`1,827` calls；`DB-0` 基线直接复用现成 5 批 `wl4_pa..pe` 零新调用！）<br>跑完推回乌镇 32C 统一出齐论文表 1、表 1B（`AtomTool` 专表）、表 2、表 4 | 是 | **`2,349` calls**<br>（实耗 **`33,068,487` tokens**，`0` 失败） | ✅ 已完成 |
| **Stage P3** | **零调用脚本回修与乌镇 32C 隔离子目录终判重跑**：修复 4 项 P1 缺陷（`T1-L6`/`T1-L12`/`DB0..DB7` 缺 `SINGLE_V2_PATCH` 重放/`runflow.py` 次级 pass 绕过+`T1-L` 仲裁基线对齐）+ 补齐 2 项表缺漏（表 2 错池率 + 表 4 世代/41 题 4 层/9 批 `ex-self`）；在隔离 `code_p3` 重跑 `49233683`/`49233684` 并更新双仓报告 | 否（`0` call） | `0` | ✅ 已完成 |

---

## 1. 论文核心消融表完整规格设计（全表题域：`[biosysmodb121]`）

### 1.1 论文表 1：单步全栈架构主消融表（Full-Stack Architecture Ablation: Waterfall + Leave-One-Out）

- **设计逻辑**：
  - **上半栏（阶梯爬坡 Additive Waterfall，`T1-0` → `T1-6`）**：以 **“真·裸大模型（无检索池、无 `AtomTool` 分子图、无 `AtomTool` 守恒安检门）”** 为第 0 阶绝对起点，第一步先单独装上 **`AtomTool`**（零外部数据库！直接证明纯 `AtomTool` 带来的提分与化学幻觉清零），随后依次装入检索池、裂解/逆编/排序、辅因子氧化还原编译扩容、多路等价共识与 `trace_protected` 对称深度思考仲裁，直达 **`118/261 (45.21%)`**（干净集 **`113/220 = 51.36%`**）！
  - **下半栏（留一剔除 Leave-One-Out，`T1-L1` → `T1-L12`）**：从完整系统（或对应单路底座）每次单拔一个核心零件，消除叠加顺序依赖质疑。
- **必报分母与口径列**：每行必须同时并排输出 **`[biosysmodb121·调参集 N=261]`** 与 **`[biosysmodb121·调参干净集 N=220]`** 下的 `v6 Hit@1 / @3 / @5`（主）、`v4 Hit@1`（附）、相对锚点 $\Delta\text{Hit@1}$，以及针对 `AtomTool` 相关行同步报 **Top-1 化学幻觉/不守恒违例率（`Spurious Top-1 %`）**。

| 行号 | 栏位类型 | 论文表展示名称 | 工程配置与数据源（`[biosysmodb121]`） | 是否新调 API | 核心科学论证点 |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **T1-0** | **真·裸起点** | `Vanilla LLM Raw-SMILES (No Pool, No AtomTool)` | 空池 `pools=[]` + 提示词剥离 `execution_graph` 与 `atom_id_map` + 纯 SMILES 输出合同 + **不走 `AtomTool` 安检门直接按模型原始 SMILES 排序判分**（`AT-RawBlind` 批次直判） | Stage P2 `AT-RawBlind`（`261` calls） | 确立没有任何检索库、也没有 `AtomTool` 时大模型的真实裸考基准与高幻觉率 |
| **T1-0a** | **`AtomTool` 阶梯 ①** | `+ AtomTool Verification Gate (Zero Pool)` | 对同一份 `AT-RawBlind` 答卷启用 `AtomTool` 逆向编译与 11 项守恒安检门（踢除无法在分子图上合法拼装的幻觉 SMILES） | **0 call**（同批重判） | 零数据库下，单测 **`AtomTool` 交卷后守恒安检门**剔除排前幻觉废品带来的净提分与幻觉清零 |
| **T1-1** | **`AtomTool` 阶梯 ②** | `+ AtomTool Execution Graph & Dual-Edit Protocol (Zero Pool)` | 空池 `pools=[]` + **恢复完整 `AtomTool` 原子身份证分子图（`execution_graph` + `atom_id_map`）与正反双通道编辑核验**（即表 2 `DB-1 EmptyPool`） | 复用 Stage P2 `DB-1` | **零题库正面证明整套 `AtomTool`**：对比 `T1-0` 直接给出纯 `AtomTool` 在无外部数据库时的总净增益！ |
| **T1-2** | 阶梯爬坡 | `+ Base Bio-Hybrid Pool (v1.0)` | 存量 `v44_next_tuning_20261110/runs_b121_tuning_v44next` 重放 | 0 call | 在 `AtomTool` 底座上接入初代混合检索池 |
| **T1-3** | 阶梯爬坡 | `+ Cleavage Auto-Upgrade & Rank Calibration (v1.2)` | 存量 `v44_next_v1_2_tuning_20261110/runs_b121_tuning_v44next_v12` 重放 | 0 call | 水解裂解含碳副产物自动补全 + 初代化学先验排序校准 |
| **T1-4** | 阶梯爬坡 | `+ Cofactor/Redox Compiler Expansion & Type Prompt (v1.4 1-pass)` | 存量 `b121_wl4_pa..pe`（报 5 批均值±SD `104.60 ± 4.28 / 261` 及 `pa` `107/261` 代表值） | **0 call** | 辅因子借原子 + `O2/H2O/NAD(P)H` 旁观对消直编（`wl4@16`）+ 反应大类引导提示词 |
| **T1-5** | 阶梯爬坡 | `+ Multi-Sample Equiv/Elig Consensus (Consensus v3)` | 存量 `b121_wl4_pa_11p_at16::v14s4_cons_v3`（`116/261`，干净集 `111/220`） | **0 call** | 同产物等价骨架合票 + 跨池资格归一化消除单次采样抖动与分票 |
| **T1-6** | **全栈顶点** | **`v44-Next v1.4 Full (+ Trace-Protected Sym-Adjudicator)`** | **`118 / 133 / 141` (`45.21%`)**；干净集 **`113 / 127 / 134` (`51.36%`)**；`v4 = 80 / 96 / 102` | **0 call（官方锚点）** | 正反互换深度思考二选一 + 溯源保护门控精准捞回分歧题真金标 |
| **T1-L1** | 留一剔除 | `w/o Trace-Protected Gate (Unconditional Sym-Adj)` | 在 `T1-6` 上将仲裁门控退回无保护双向互换（复用已存仲裁缓存） | 0 call | **关键反证**：无保护锁盲目翻盘会误伤文献强锚点与独有 novel，证明保守门控必不可少 |
| **T1-L2** | 留一剔除 | `w/o Selective Thinking Adjudicator` | 关断仲裁器（退回 `T1-5` 纯共识 `116/261`） | 0 call | 剥离深度思考二选一仲裁的独立净贡献 |
| **T1-L3** | 留一剔除 | `w/o Equiv-Product & Elig-Norm Consensus (v3 → v1)` | 在同组样本上关断等价簇合票与资格归一化，退回 `Consensus v1` | 0 call | 测定消除“异键同产物分票”与“跨池分母稀释”的净增益 |
| **T1-L4** | 留一剔除 | `w/o Multi-Sample Consensus (Multi-pass → 1-pass)` | 关断多路融合，退回 `wl4` 同池单路 5 批均值（`T1-4`） | 0 call | 分离测试时多采样共识相对单次前向推理的边际贡献 |
| **T1-L5** | 留一剔除 | `w/o Stage-1 Reaction-Type Prompt (v3-type → v1)` | 在同池存量批 `t8_c/t9_c2` vs `t8_pa/pb/t9_pc` 上重放对照 | 0 call | 测定“先判 12 类生化反应大类再写结构”的净增益 |
| **T1-L6** | 留一剔除 | `w/o Redox & Multi-O Compiler Expansion (wl4 → w32)` | 对比 `wl4` 采样与未做氧化还原扩容的 `w32@16`（`t8_pa/pb/t9_pc`）重放 | 0 call | 测定 `O2/H2O` 直编与 `NAD(P)H` 旁观对消释放的候选池天花板与实得增益 |
| **T1-L7** | 留一剔除 | `w/o Ranking Calibration & Guarded Rules` | 在 `v1.4` 单路与共识链中关断 `calibrate_submittable_ranking` / `R1` | 0 call | 测定回复后化学先验与共产物完整性排序校准的净贡献 |
| **T1-L8** | 留一剔除 | `w/o Cleavage Coproduct Auto-Upgrade` | 开启新增开关 `disable_cleavage_upgrade=True` 重放 `v1.4` | 0 call | 测定裂解含碳离去碎片自动补全对严格守恒准入的独立贡献 |
| **T1-L9** | **`AtomTool` 留一 ①** | `w/o AtomTool Graph View & Edit Prompt (Full Pool, SMILES-Only)` | 保持满配 `wl4@16` 候选池，但在提示词中**剥离 `AtomTool` 分子执行图 `execution_graph`、`atom_id_map` 与 `edits` 算子协议**（对比单路基线 `T1-4`） | Stage P2 `AT-FullPool-NoGraph`（`261` calls） | 正面证明即使在满配检索池下，**`AtomTool` 考前原子身份证分子图与算子协议**依然有独立增益 |
| **T1-L10** | **`AtomTool` 留一 ②** | `w/o AtomTool Forward Edits (Product-First Only)` | 在 `v1.4` 存量答卷上设 `fix_decide_atomtool_import=False`，废除模型正向手写 `AtomTool edits` 先行，全部强制只走逆向反推 | **0 call** | 测定模型正向手写 `AtomTool` 原子操作指令对复杂重排/位点特异反应的独立贡献 |
| **T1-L11** | **`AtomTool` 留一 ③** | `w/o AtomTool Inverse Compiler (Forward Edits Only)` | 在 `v1.4` 存量答卷上设 `disable_product_first_fallback=True`，废除产物优先逆向反推，只允许手写 `AtomTool edits` | **0 call** | 与 `T1-L10` 成对互证：**`AtomTool` 正向算子执行 + 逆向图差编译双通道缺一不可** |
| **T1-L12** | **`AtomTool` 留一 ④** | `w/o AtomTool Verification Gate (Raw Unverified Proposals)` | 在 `v1.4` 单路存量答卷（及 `EmptyPool` 答卷）上跳过 `AtomTool` 可执行核验与守恒门，直接按模型原始声明的产物 SMILES 交卷判分，并统计**化学幻觉违例率** | **0 call** | 证明撤掉 `AtomTool` 安检门后，非法价态与凭空增减原子的幻觉分子会直接混入输出，破坏科学可靠性 |

> **💡 独立专表同步产出**：报告中除生成完整主表 1 外，将自动把 `T1-0`、`T1-0a`、`T1-1` 与 `T1-L9..L12` 抽取汇总为独立的 **`论文表 1B：AtomTool 分子图表示、双向编辑与防化学幻觉专项消融表`**（并列展示 `Hit@1`、`Parse/Valence Error %`、`Atom Conservation Violation %`、`Spurious Top-1 %` 四维指标）。

---

### 1.2 论文表 2：`[biosysmodb121]` 生化知识库（`assets/`）顶会全满贯正交消融表

- **公平控制基座（100% 纯净单变量）**：全部 8 个数据库配置统一固定在 **`[biosysmodb121]` `v1.4` 最强单路基座** 上横向对比：
  - `@16` 槽位上限 + `enable_v13_prompt_v3_type=True` + `d2_cofactor_whitelist_3/4=True` + `fix_decide_atomtool_import=True` + `enable_v14_compiler_ext/ext_2=True` + `--no-evidence-card`；
  - 控制组 `DB-0` 直接复用磁盘现成 5 批同配独立采样 `b121_wl4_pa..pe`（自带精确的 5 次采样均值 ± 标准差噪声底，**0 新调 API**！）。
- **正交零泄漏拔除矩阵（5 大物理供给通道全覆盖，绝不留暗道！）**：

| 臂代号 | 论文表名称 | `recorded`<br>(`library_full` EAWAG) | `corpus`<br>(`corpus_v1` `wl4`) | `analog`<br>(`corpus_templates_v2`) | `S5-env`<br>(`envipath`+`eawag`) | `S5-rr`<br>(`rhea`+`mnx`) | `USPTO`<br>(有机合成库) | 新调 API 数 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DB-0** | **`Full Bio-Assets (Control)`** | ✅ 全开 | ✅ `rhea:` + `env:` | ✅ `rhea:` + `env:` | ✅ 全开 | ✅ `rhea` + `mnx` | ❌ 关 | **0**（复用现成 5 批 `wl4_pa..pe`） |
| **DB-1** | **`EmptyPool`（零池 + `AtomTool`）** | ❌ 关 | ❌ 关 | ❌ 关 | ❌ 关 | ❌ 关 | ❌ 关 | `261` |
| **DB-2** | **`NoSelf`（未见底物零样本）** | ❌ **关断同底物查表** | ❌ **关断同底物查表** | ⚠️ **剔除含当前底物/同反应ID模板** | ⚠️ **剔除仅源自当前底物/同反应ID规则** | ⚠️ **剔除含当前反应ID或父底物全为当前底物规则** | ❌ 关 | `261` |
| **DB-3** | **`NoEnv`（去全部环境降解源）** | ❌ 全关 | ⚠️ **仅留 `rhea:`**<br>(丢弃 `env:`/`envipath:`) | ⚠️ **仅留 `rhea:`**<br>(丢弃 `env:`) | ❌ 全关 | ✅ `rhea` + `mnx` | ❌ 关 | `261` |
| **DB-4** | **`NoRR`（去大规模 RetroRules）** | ✅ 全开 | ✅ `rhea:` + `env:` | ✅ `rhea:` + `env:` | ✅ 全开 | ❌ **全关** | ❌ 关 | `261` |
| **DB-5** | **`RheaOnly`（纯 Rhea 单源）** | ❌ 全关 | ⚠️ **仅留 `rhea:`** | ⚠️ **仅留 `rhea:`** | ❌ 全关 | ⚠️ **仅留 `rhea`** | ❌ 关 | `261` |
| **DB-6** | **`MNXOnly`（纯 MetaNetX 单源）** | ❌ 全关 | ❌ 全关（无 MNX） | ❌ 全关（无 MNX） | ❌ 全关 | ⚠️ **仅留 `mnx`** | ❌ 关 | `261` |
| **DB-7** | **`AddUSPTO`（混入有机合成库）** | ✅ 全开 | ✅ `rhea:` + `env:` | ✅ `rhea:` + `env:` | ✅ 全开 | ✅ `rhea` + `mnx` | ✅ **开启 `uspto_channel`** | `261` |

> **🚨 `DB-2 NoSelf` 建池阶段“绝对零金标接触”硬红线（防审稿质疑与防金标泄漏）**：
> 在构建 `DB-2 NoSelf` 候选池（Prompt 前）时，**严禁读取 `reference_graphs/` 或任何金标产物 SMILES**！必须严格采用 **“未见底物模拟（Leave-One-Substrate-Out）”** 纯输入端规则：
> 1. 仅使用题目自身的输入底物 `substrate_smiles`（取 `strict_identity` 与 `cn` 去质子身份）及非金标题源反应标识元数据（如 `source_id` / `reaction_id`）；
> 2. 彻底关断同底物精确查表通道（`recorded` 与 `corpus` 对当前底物返回空，模拟该污染物从未被数据库直接收录）；
> 3. 在 `analog` 中剔除原始反应左端（`mapped_lhs` 去映射后严格或去质子组分集合）包含当前输入底物、或模板 ID 匹配题源反应 ID 的模板（只允许从**异源其他分子**做结构类比迁移）；
> 4. 在 `S5-env` 与 `S5-rr` 中剔除 `parent_reaction_ids` 命中题源反应 ID 的规则，以及所有支撑父反应的左端底物均等于当前输入底物的单样本特异规则；
> 5. 建池完成后，在离线 `GIP@16` 审计阶段调用既有只读 `ex-self` 核验器断言：**`DB-2 NoSelf` 全池 `self_record_hits == 0`（261/261 零自记录残留）**！

---

### 1.3 论文表 4：`[biosysmodb121]` 判分契约演进与数据分层透明披露表（100% 零调用）

在同一份 `[biosysmodb121]` 答卷（覆盖 `T1-0 Vanilla Raw-SMILES`、`T1-1 EmptyPool+AtomTool`、`v1.0`、`v1.2`、`v1.4 1-pass`、`v1.4 Full` 及 `DB-2 NoSelf`）上，一次性并排输出以下 5 列判分读数与数据分层拆解：
1. **`ppv1-criteria-v2`**：严格全边与共产物角色配平命中率；
2. **`ppv1-criteria-v4`**：严格主产物精确电荷/立体命中率（永久历史基线）；
3. **`v4 (ex-self)`**：剔除自记录后的严格 `v4` 命中率；
4. **`ppv1-criteria-v6`（主口径）**：受控生理质子化不变主产物命中率（`CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md`）；
5. **`v6 (ex-self)`**：剔除自记录后的主口径 `v6` 泛化命中率；
6. **`N=261` vs `N=220` 四层透明拆解**：同步展示主分母 `[调参集 N=261]`、并列 `[调参干净集 N=220]`，以及被归入 4 类题面边界层的 41 道题（5 自环、16 缺重原子供体、6 纯顺反/手性、14 多步折叠）上的各自得分（证明不删分母、双报透明）。

---

## 2. 全局红线与工程护栏（无例外执行）

1. **留出集与非目标题域隔离**：严禁读取 `~/.ppv1_holdout_token`、`holdout_qids.txt` 或任何 `holdout` 目录；全部实验 100% 限定在 `[biosysmodb121·调参集 N=261]`（含并列子集 `N=220`），不跑 `[dev-298]`。
2. **零金标、零 SMILES、零私有题号入仓**：任何 git 跟踪文件（`src/`、`scripts/`、`tests/`、`docs/`、commit message）及回传摘要中严禁出现分子 SMILES/InChI 或私有题号字符串；带题号的中间审计文件仅允许写入 gitignored 目录 `reports/manual_review/paper_ablation_v14_20261116/` 及远端 `chmod 700` 目录。
3. **三份冻结判分器只读**：实验前后必须校验并记录以下三文件 SHA256 逐字节未变：
   - `scripts/eval/score_disclosure_v4cn.py`：`0ffb8b71330653f7b0373a67d028b14a84d4c5f13a83abd17db89a3c82a28f2f`
   - `src/pathway_v43/pollutant/evaluation.py`：`ac38ea393bfb91e420e98730415cba334df2f9d3d9de4ecfde90914f45363f41`
   - `src/pathway_v43/pollutant/s5b_scoring.py`：`5a677550ef54a3a1e16d5b5a1ce4dd8d2cdcb55dd56224e8a148f50511dc456d`
4. **正控零容忍硬门（`diffs == 0`）**：
   - **重放正控门**：新增消融开关全部默认 `False` 时：
     - 用户载荷 `build_proposals_user_payload` 与系统提示词 `proposals_system_prompt` SHA256 逐字节不变；
     - 重放 `b121_wl4_pa_11p_at16::v14s4_cons_v3_prom_adj` 必须精确复现 `118 / 133 / 141`（干净集 `113 / 127 / 134`；`v4: 80 / 96 / 102`），重放单路 `b121_wl4_pa..pe` 必须与 `t14_step4_summary.json` 逐题全等（`diffs == 0`）；
   - **建池正控门**：新消融建池脚本在 `--arm DB0_full_ctrl` 模式下，在乌镇 32C 重建的候选池必须与既有 `pools_v14_wl4_b121.json`（261 题 `@16`）逐题逐槽相等（`diffs == 0`），任一不等立即退出码 `2` 急停排查，未归零前严禁发任何付费 API！
5. **跨臂缓存隔离铁律**：在乌镇 32C 构建 `DB-0..DB-7` 候选池时，每个子进程必须清空 `V43_RECORDED_CORPUS_CACHE_DIR` 或按臂隔离缓存子目录，严禁不同数据库消融臂之间共享磁盘检索缓存导致串味！
6. **工作树隔离与不删不推纪律**：
   - **唯一消融工作树**：直接使用 `/Volumes/CC/Enzyme_Agent/v44_v13`（当前已在 `v1.4` 结项节点 `83aec48` 上切出分支 `ocagent/261116-paper-ablation-v14-4c41`；保留工作区既有未跟踪的 `audit_abiotic_chemical_assets` 相关文件不动）。消融期间严禁在同一工作树内并发启动 `T4` 留出集终测；若需与 `T4` 并行推进，`T4` 必须另行 `git worktree add` 隔离本地与远端代码目录。
   - **严禁改动主树与破坏性操作**：严禁修改 `/Volumes/CC/Enzyme_Agent/dependingv43` 主树代码；严禁执行 `rm`、`unlink`、`git clean`、`git reset --hard`；所有 Python 命令带 `PYTHONDONTWRITEBYTECODE=1` 与 `-B`；严禁 `git push`。

---

## 3. 代码改造与新增脚本清单（最小无损增量）

1. **源码最小消融开关（默认全部 `False`，正控逐字节零漂移）**：
   - **`AtomTool` 输入视图与纯 SMILES 协议消融开关（`disable_atomtool_prompt=False`）**：
     - 在 `src/pathway_v43/pollutant/runflow.py`（约 L5137 `_call_real_fetch`）与 `src/pathway_v43/pollutant/real_model.py`（`build_proposals_user_payload` 及 `proposals_system_prompt`）：
       - 当 `plan.get("disable_atomtool_prompt", False)` 为真时：用户消息载荷不注入 `"execution_graph"` 且不注入 `"substrate_atom_id_map"`（仅保留 `"substrate_smiles"` 与 `"pool_hypotheses"`）；
       - 系统提示词切换至 `v3_type_raw_smiles` 合同变体（保留 12 类生化反应大类审题引导，但彻底移除全部 `edits` 算子、`atom_id`、`donor`、`alignment` 描述与原子编号示例；`model_protocol.py` 在该开关下允许 `novel` 提案只含 `{"product_smiles": ..., "coproducts": [...]}`，跑通时走 `compile_novel_product_first` 或在 `T1-0` 免门重判器中直接取原始声明 SMILES）。
   - **`AtomTool` 交卷后逆向反推与裂解补碳消融开关**：
     - `src/pathway_v43/pollutant/runflow.py`：
       - `disable_cleavage_upgrade=False`：为真时跳过 `try_upgrade_cleavage_spec`（约 L1083）；
       - `disable_product_first_fallback=False`：为真时关断 `product_first` 逆向图差编译回退（约 L1903），强制池外 `novel` 只能靠模型正向手写 `AtomTool edits` 通过；
       - （既有开关直接复用）`fix_decide_atomtool_import=False`：关断正向手写 `AtomTool edits` 先行，强制全部走逆向反推。
   - **免 `AtomTool` 安检门的原始提案评估与化学幻觉率统计器（`score_raw_unverified_proposals`，纯评测侧函数，不污染生产 `ledger`）**：
     - 针对 `T1-0`（`AT-RawBlind`）与 `T1-L12`（`v1.4` 单路 / `EmptyPool` 原始响应），直接从保存的模型原始响应 JSON 按 `rank_hypotheses` 顺序提取候选的 `product_smiles`（池候选映射池内 `product_smiles`，`novel` 直接取模型原始写出的 `reaction_spec.product_smiles` 字符串，完全不经过 `AtomTool` 编译过滤），调用冻结 `score_disclosure_v4cn` / `strict_identity_of` 计算 `v6` 与 `v4` `Hit@1/@3/@5`，并精确统计 3 项化学幻觉指标：
       1. `unparseable_or_valence_err_pct`：模型提出的 `novel` SMILES 无法通过 RDKit 解析或价态非法的比例；
       2. `conservation_violation_pct`：模型提出的 `novel` 无法通过 `AtomTool` + `wl4` 辅因子守恒编译（即凭空多碳、丢卤素、重原子不配平等幻觉）的比例；
       3. `spurious_top1_pct`：最终排在 Top-1 的答案属于上述非法或不守恒幻觉产物的题目占比（对照启用 `AtomTool` 安检门后的 `0.00%`！）。
   - **数据库正交过滤配置（`ablation_source_filter: dict | None = None`）**：
     - 在 `src/pathway_v43/pollutant/s5b_builder.py` / `src/pathway_v43/services/s5_hybrid_choice.py` 中统一拦截并按 §1.2 规则过滤 `recorded`、`corpus`（按 `rhea:` vs `env:`/`envipath:` 前缀及零金标 `NoSelf` 底物排除）、`analog`（按前缀、零金标底物排除及可选 `uspto_channel=True`）、`S5-env`、`S5-rr`（`rr_datasets` 子集及零金标父反应/父底物排除）。
2. **新增评测与 HPC 调度脚本**：
   - `scripts/hpc/paper_ablation_table1_table4_hpc.py` + `scripts/hpc/sbatch_paper_ablation_t1_t4.sh`：在乌镇 32C 对 `[biosysmodb121]` 一次性跑完表 1 全部零调用重放行（`T1-2..T1-6`、`T1-L1..T1-L8`、`T1-L10..T1-L12`）与表 4 五口径阶梯矩阵，含正控 `diffs == 0` 断言、`anti_truncation == 0` 检查与 `AtomTool` 幻觉率统计。
   - `scripts/hpc/paper_ablation_pools_hpc.py` + `scripts/hpc/sbatch_paper_ablation_pools.sh`（基于 `t14_step1b_gip_hpc.py` Linux 父进程预热 COW 32C 并行架构扩展，支持 `--arms` 分片参数以便多节点同时提交）：在乌镇 32C 并行构建 `[biosysmodb121]` 的 `DB0_full_ctrl` + `DB1..DB7` 全部 `@16` 池 JSON（按臂隔离独立临时缓存目录），逐池跑生产链 4 步准入硬门（`n_admission_failures == 0`）、`NoSelf` 零泄漏断言、双口径 `GIP@16`（含 `N=261` 与 `N=220`）及错池率统计。
   - `scripts/eval/paper_ablation_build_batches.py`：在本地 gitignored `reports/ppv1_s5b/paper_ablation_v14_20261116/` 下生成 Stage P2 全部 **9 个 `[biosysmodb121]` 待跑单路批根**（`AT-RawBlind`、`AT-FullPool-NoGraph`、`DB1..DB7`）。
   - `scripts/hpc/paper_ablation_final_score_hpc.py` + `scripts/hpc/sbatch_paper_ablation_final.sh`：9 批采样完成后同步至乌镇 32C，合成完整 **论文表 1（全栈主表）**、**论文表 1B（`AtomTool` 专项深度拆解与防幻觉表）**、**论文表 2（`assets/` 数据库全满贯表，含相对 `DB-0` 5 批基线的 `n_boot=10,000` 配对 Bootstrap 95% CI 与双侧精确 McNemar $p$ 值）** 与 **论文表 4（五口径与分层透明表）**。
3. **本地轻量单测**：
   - `tests/pollutant/test_paper_ablation_v14.py`：覆盖 `disable_atomtool_prompt` 开启时载荷不含 `execution_graph`/`substrate_atom_id_map` 且关闭时 SHA256 逐字节不变、后置开关默认 `False` 零漂移、7 种 `ablation_source_filter` 精确过滤、`NoSelf` 零金标底物剥离、`EmptyPool` 端到端无崩溃及 `score_raw_unverified_proposals` 幻觉率统计正负控（本地耗时 `< 15s`）。

---

## 4. 并行调度架构、分阶段执行步骤与预算账本

### 4.1 四轨并行拓扑（最大化乌镇 HPC 32C 多节点吞吐 + 零等待在线采样）

```text
[本地代码 + 单测全绿 + 同步代码至乌镇]
   ├──▶ 轨 A1 (HPC sbatch #1): 表 1 存量 + AtomTool 后置 + 表 4 零调用重放 ──┐
   ├──▶ 轨 A2 (HPC sbatch #2..k, 同时提交): DB0_full_ctrl + DB1..DB7 多臂并行建池 ─┼─▶ 轨 D (HPC 32C 终判合表)
   └──▶ 轨 B  (本机 HTTP API, 零等待立刻开跑): AT-RawBlind + AT-FullPool-NoGraph ──┤
                                                                                    │
        [轨 A2 过门: DB0 diffs==0 & NoSelf 零漏水 & admission_fail==0]              │
              └──▶ 轨 C (本机 HTTP API, 7 批并发限流总并发<=24): DB1..DB7 ─────────┘
```

### 4.2 Stage P1（零付费 API）：代码落地 + 乌镇多作业同时提交 + 轨 B 先行触发
1. **工作树与基线校验**：确认 `/Volumes/CC/Enzyme_Agent/v44_v13` 位于 `ocagent/261116-paper-ablation-v14-4c41`（基于 `83aec48`），校验三份判分器 SHA256 逐字节一致。
2. **实现与本地单测**：完成 §3 开关、脚本与 `test_paper_ablation_v14.py`，本地 `PYTHONDONTWRITEBYTECODE=1 pytest -B -p no:cacheprovider` 全绿（提示词/载荷开关关闭态 `SHA256` 不变）。
3. **增量同步至乌镇 HPC**：仅将 `{src, scripts, tests}` `rsync` 至 `wuzh02.hpccube.com:65091:/work/home/aclhl3hbth/ppv1_hpc/v44_v13_hpc_20261113/code/`；远端输出固定写入新建隔离目录 `${HPC_BASE}/paper_ablation_v14_20261116/`（`chmod 700`）。
4. **同时提交乌镇 HPC 多作业（轨 A1 + 轨 A2 并行）**：
   - 同时 `sbatch` 提交 `sbatch_paper_ablation_t1_t4.sh`（表 1 存量 + `AtomTool` 后置 + 表 4 重放）与 `sbatch_paper_ablation_pools.sh`（可按 `--arms` 拆为 1 个全量池批或 2–4 个并列 `sbatch` / Job Array 分占多个 `wzhcnormal` 32C 节点并行构建 `DB0_full_ctrl` 与 `DB1..DB7`，**每作业独立隔离缓存目录与输出文件名，零写冲突**）。
5. **轨 B 无需等建池（与轨 A 并行启动）**：本地单测通过且确认 `pools_v14_wl4_b121.json` 就位后，立刻构批并并行跑起 Stage P2 的前 2 批 **`AT-RawBlind`（空池）** 与 **`AT-FullPool-NoGraph`（复用现成 `wl4@16` 池）**。
6. **Stage P1 硬门核验（全过才准放行轨 C `DB1..DB7` 付费采样）**：
   - 表 1 正控 `T1-6` 100% 精确等于 `118/261`（干净集 `113/220`；`diffs == 0`）；
   - 表 2 正控 `DB0_full_ctrl` 与 `pools_v14_wl4_b121.json` 261/261 逐题逐槽相等（`diffs == 0`）；
   - 全部 7 个消融池 `n_admission_failures == 0`；
   - `DB-2 NoSelf` 全池 `self_record_hits == 0`；
   - `DB-1 EmptyPool` 全池长全为 `0`。

### 4.3 Stage P2（付费在线采样并发推进 + 乌镇 32C 终判合表）
1. **付费批次清单与预注册预算表**：

| 序号 | 批次名称 | 执行轨道 | 池与 `AtomTool` / 提示词配置 | 调用数 (`calls`) | 预估 Tokens |
| :---: | :--- | :---: | :--- | :---: | :---: |
| 1 | `batch_ablation_b121_at_raw_blind` | **轨 B（零等待先跑）** | **空池 + `disable_atomtool_prompt=True`（真·裸模型 Raw-SMILES，供 `T1-0` 与 `T1-0a`）** | `261` | `~1.4M` |
| 2 | `batch_ablation_b121_at_fullpool_nograph` | **轨 B（零等待先跑）** | **现成满配 `wl4@16` 池 + `disable_atomtool_prompt=True`（供 `T1-L9`）** | `261` | `~2.8M` |
| 3–9 | `batch_ablation_b121_db1..db7` | **轨 C（轨 A2 过门后并发）** | `@16` 各消融池（`EmptyPool / NoSelf / NoEnv / NoRR / RheaOnly / MNXOnly / AddUSPTO`）+ 完整 `AtomTool` + `prompt-v3-type` | `1,827` (`261×7`) | `~25.6M` |
| **合计** | **共 9 个单路采样批** | 仅 `[biosysmodb121]`（双报 `N=261` & `N=220`） | `--no-evidence-card`；模型 `deepseek-v4.1-flash-1017` | **`2,349`** | **`~29.8M`**（硬熔断上限 `45M`） |

2. **本机并发 HTTP 采样纪律**：加载 `/Users/cc/.config/enzyme_agent/llm.env`（严禁打印任何环境变量内容），轨 C `DB1..DB7` 可多批同时起跑以缩短总耗时，但**所有并行采样进程的总并发请求数之和须受控（建议分 2–3 组并发或总 `--concurrency <= 24`）**，防止触及 API 网关 `429` 限流；实时记录每批 Input / Output / Total Tokens（无价目快照时费用栏记「未核实」），要求全 9 批 `failed_runs == 0`。
3. **推回乌镇 32C 终判与统计检验（轨 D）**：将 9 批运行结果 `rsync` 至乌镇 `${HPC_BASE}/paper_ablation_v14_20261116/runs/`，提交 `sbatch_paper_ablation_final.sh`，32 核并发一次性生成（全部带 `[biosysmodb121·调参集 N=261]` 与 `[biosysmodb121·调参干净集 N=220]` 双分母列）：
   - **论文表 1**：`[biosysmodb121]` 单步全栈架构主消融表（`T1-0` 真·裸模型 $\to$ `T1-6` `45.21%` 爬坡 + `T1-L1..L12` 留一剔除）；
   - **论文表 1B**：`AtomTool` 专项深度拆解与防化学幻觉表；
   - **论文表 2**：`[biosysmodb121]` 生化数据库（`assets/`）顶会全满贯正交消融表（含离线 `GIP@16`、错池率、端到端 `v6/v4 Hit@1/@3/@5`、Bootstrap 95% CI 与 McNemar $p$ 值）；
   - **论文表 4**：五口径判据阶梯与 `N=261/220` 四层题面边界透明披露表。
4. **落盘正式脱敏报告与本地提交**：
   - 正式报告写入 `/Volumes/CC/Enzyme_Agent/v44_v13/docs/reports/PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md`，并同步复制一份脱敏副本至 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/reports/PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md`；
   - 校验三份判分器 SHA256 与零 SMILES / 零私有题号，在 `v44_v13` 专属分支 `ocagent/261116-paper-ablation-v14-4c41` 本地 `git commit`（严禁 `git push`）。

### 4.4 Stage P3（独立审计 4 项 P1 脚本/重放缺陷与 2 项表缺漏：零调用回修与终判重跑）

> 2026-11-17 独立审计已确认 `b0e1331` 所产 9 个付费采样批（`2,349` 次调用、`33,068,487` tokens、`0` 失败）与 8 套建池全部有效；问题仅出在零调用后处理/重放与合表环节。**Stage P3 全程零 LLM 调用（0 tokens），由主会话直接实施，不重跑任何付费批。**

1. **6 项必改修复清单**：
   - **修 1（P1：`T1-L6` 错填左组 `T1-4`）**：`scripts/hpc/paper_ablation_table1_table4_hpc.py` `_run_group_compare_alias` 将 `right_arms`（`w32@16` 3 臂 `t8_pa/pb + t9_pc`，均值 `100.33`）的 `v6/v4/clean_220` 与 `group_stats` 填入 `T1-L6` 行指标，不再把左组 `T1-4`（`107`）冒充为右组结果。
   - **修 2（P1：`T1-L12` 错映射 `AT-FullPool-NoGraph` + `raw_score` 缺 `Clean-220`）**：`scripts/eval/paper_ablation_raw_score.py` 增加基于 `CLEAN_220_SHA16` 的 `clean_220`（`v6` & `v4`）分桶输出；`paper_ablation_final_score_hpc.py` `_build_table1` / `_build_table1b` 移除把 `T1-L12` 硬映到 `at_fullpool_nograph` 的错误覆盖，改为直接读 `replay_results["T1-L12"]`（即 `wl4_pa` raw rescore，`v6=99/261`、`spurious_top1=3.83%`、`clean_220` 实算）。
   - **修 3（P1：`DB-0..DB-7` 未经 `SINGLE_V2_PATCH` 重放导致基准偏低）**：`paper_ablation_final_score_hpc.py` `_run_batch` 对未经过 `v13_t1b_replay.py` + `SINGLE_V2_PATCH` 重放的单路批（`DB-0 pa..pe`、`DB-1..DB-7` 以及 `AT-RawBlind`/`AT-FullPool-NoGraph`，保持各批原 `disable_atomtool_prompt` / `enable_v13_prompt_v3_type` 开关不变）统一在 `work_dir/replay/` 内完成零调用 `v13_t1b_replay.py` + `SINGLE_V2_PATCH` 重放后再判分，强制正控 `DB-0` 5 批均值精确复现官方 `104.60 ± 4.28`（`107/109/98/103/106`）。
   - **修 4（P1：次级 pass 绕过 `disable_product_first_fallback` + `T1-L` 阶梯仲裁对齐）**：
     - `src/pathway_v43/pollutant/runflow.py` `_collect_secondary_consensus_ranks` 在 `self.disable_product_first_fallback=True` 时禁止走 `_verify_novel_product_first` 与 `enable_v14_sec_novel_backfill`（仅允许携带合规 `edits` 的提案走 AtomTool 正向执行核验）；默认关闭时不改变任何生产路径；
     - `scripts/hpc/paper_ablation_table1_table4_hpc.py` 为 `_ladder_arm` 挂载脱敏缓存 `trace_protected|d8|u99|e3|r2` 仲裁映射（零模型调用），使 `T1-L3/L7/L8/L10/L11` 与 `T1-6 (118)` 同基线对齐；同时增设单路诊断行 `T1-L7s/L8s/L10s/L11s`（对 `wl4_pa::single_v2`，基线 `107`）直观披露单路机制真实贡献。
   - **修 5（表 2 缺 `错池率 %` 列）**：保留 `paper_table2.json` 已有的 `wrong_pool_rate_at_16` 并纳入报告表 2 正式展示。
   - **修 6（表 4 缺世代阶梯、41 题真实 4 层分布、与 9 批 `ex-self`）**：
     - 生成仅含 `{qid_sha16, layer}` 的纯脱敏 4 层映射文件（零 SMILES、零明文题号，`chmod 600`）随 `code_p3` 传入 `--mode table4 --layer-file`，区分 `T1-5`（`116/79`，pre-adj）与 `T1-6`（`118/80`，post-adj），并补充 `T1-2/T1-3/T1-4/T1-5/T1-6` 世代行；
     - `paper_ablation_final_score_hpc.py` 复用 `_self_record_index` / `_event_self_flags` 为 9 个消融批（含 `replay` 导出后完整事件 payload）补齐真实事件级 `ex-self`（`v4(ex-self)` 与 `v6(ex-self)`）。
2. **乌镇远端严格隔离纪律**：
   - 因在跑任务 `49232315`（`ppv1_e2e_v14_pools`）正在读取 `${HPC_BASE}/code/src`，**严禁改动 `${HPC_BASE}/code/`**；
   - Stage P3 代码全量增量同步至隔离目录 `${HPC_BASE}/paper_ablation_v14_20261116/code_p3/`，`sbatch_paper_ablation_t1_t4.sh` 与 `sbatch_paper_ablation_final.sh` 改用 `CODE_DIR="${CODE_DIR:-${HPC_BASE}/code}"`；
   - 以新输出目录 `table1_table4_p3/` 与 `final_p3/` 串联提交 32C Slurm 作业（`dependency=afterok`），回收结果并刷新 `PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md`（双仓同步）后在 `v44_v13` 本地 commit（禁 push）。

---

## 5. 排障与熔断预案

| 异常现象 | 处置规则 |
| :--- | :--- |
| Stage P1 正控重放、提示词 SHA256 或 `DB0_full_ctrl` 建池出现哪怕 1 题 `diffs > 0` | **最高优先级停手**：绝不进入 Stage P2，定位默认开关泄漏或缓存污染直至 `diffs == 0` |
| `DB-2 NoSelf` 离线校验出现 `self_record_hits > 0` | 检查漏网候选键的前缀（`rec-` / `tpl-` / `s5-`）及父反应底物集，补齐零金标输入端剔除条件直至归零 |
| `AT-RawBlind` 或 `AT-FullPool-NoGraph` 模型在纯 SMILES 合同下偶发返回非法 JSON | 保持与主线相同的 JSON 格式解析重试上界；不可解析或空输出按分母不删题铁律诚实计 `0` 分，并记入解析失败率 |
| 在线采样遇网关限流 `429` 或瞬断 | 使用内置断点续跑机制原批补齐 `failed_runs == 0`；若单批均耗超 `2×` 基线或累计达 `45M` tokens 硬帽则暂停汇报 |
| 任何触碰留出集路径或冻结判分器哈希变动 | 立即急停并上报 CC |

---

## 6. 执行者回传义务清单

`ocagent` 交付时必须向主窗口一次性回传：
1. `v44_v13` 分支名、commit hash、OpenCode session ID；
2. 乌镇 HPC 全部 Slurm Job ID 清单（表 1/4 存量重放、表 2 建池、9 批终判）；
3. 三份冻结判分器前后 SHA256 校验结果、正控 `diffs == 0` 核验结果、`NoSelf` `self_record_hits == 0` 核验结果、`anti_truncation == 0` 核验结果；
4. 9 个付费批逐批精确调用数与 Input / Output / Total Tokens 账单表；
5. 脱敏后的论文表 1、表 1B（`AtomTool` 专表）、表 2、表 4 核心汇总数字与正式报告文件路径（严禁在回传正文中带任何 SMILES 或私有题号）。
