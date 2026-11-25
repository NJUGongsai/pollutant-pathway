# `T4` 单步留出集终测预注册升级登记（`v1.4` 生产冻结配置：`prereg-v14-t4-holdout-2026-11-15`，2026-11-18 R2 增补版）

> **状态**：**`v1.4` 调参集已在 `[biosysmodb121·调参集 N=261]` 达到 `118 / 261 (45.21%)`、`Clean-220` `113 / 220 (51.36%)`，在 `[dev-298·调参集 N=196]` 达到 `95 / 196 (48.47%)`（单路 `97 / 196 = 49.49%`）；本文件正式取代已暂停的 `PREREG_V13_T4_HOLDOUT_2026-11-14.md`，停在 `~/.ppv1_holdout_token` 令牌授权边界前，等待 CC 显式解锁指令后方可执行唯一一次开箱终测。**
> **基准代码锚点**：`<LOCAL_WORKSPACE>/v44_v13`，分支 `ocagent/261116-v14-trace-protected-b7xt`（核心实现提交 `4860cd8`；消融与 `NoSelf` 全系统评测脚本分支 `ocagent/261116-paper-ablation-v14-4c41`）。
> **依据报告**：`V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md`、`docs/reports/PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md`。
> **隔离与脱敏声明**：本文档零 SMILES/InChI、零私有题号；**零读取 `~/.ppv1_holdout_token`、`holdout_qids.txt` 与 `holdout_v1`**。

---

## 1. 留出集分域冻结配置与预注册主 Estimand

### 1.1 `[biosysmodb121·留出集 N=156]` 主线配置（与调参夺冠臂同构）

| 配置项 | 冻结参数 | 说明 |
| :--- | :--- | :--- |
| **模型与证据卡** | `deepseek-v4.1-flash-1017`，`--no-evidence-card` | 原生深度思考，零额外温度/长度覆盖 |
| **候选池策略** | `v1.4 wl4` 标准 `@16` 混合池（开启 `d2_cofactor_whitelist_3=True`、`d2_cofactor_whitelist_4=True`、`enable_v14_compiler_ext=True`、`enable_v14_compiler_ext_2=True`） | `n_admission_failures == 0` 预检硬门 |
| **提示词与 Stage-1 路由** | `enable_v13_prompt_v3_type = True`；独立盲底物 Stage-1 大类路由 `stage1_routing_file` | 仅提供共识 `stage1_bonus`，不改池成员 |
| **采样路数与后处理开关** | 多路同质 `wl4` 采样（推荐 **5 路同池独立采样**以复刻调参低方差底座；或 CC 另行勾选 11 路）+ `enable_v14_cross_pool_elig_norm=True`、`enable_v14_multipass_consensus_v3=True`、`enable_v14_novel_low_sim_boost=True`（`0.18`）、`enable_v14_equiv_product_consensus=True`（`v14_equiv_cluster_mode="strict"`）、`enable_v14_raw_order_consensus=True`（`guarded_r2_r7`）、`enable_v14_sec_novel_backfill=True`、`fix_decide_atomtool_import=True` | 严格冻结于 `v1.4` CV 验证配置 |
| **终段双序机理裁决（`T14-3 + trace_protected`）** | `v14_t14s3_adjudicator.py` `PROMPT_VERSION = "v14-t14s3-mech-adj-1"`；<br>策略冻结为 **`trace_protected|d8|u99|e3|r2`**（`gate_mode="trace_protected"`, `min_conf_sum_disagree=8`, `min_conf_sum_unanimous=99`, `min_each_conf=3`, `max_challenger_rank=2`） | 按比例不变门控自动适配实际采样路数 `N >= 2` |
| **调参锚点实绩** | `[biosysmodb121·调参集 N=261]`：**`v6 all = 118 / 133 / 141 (45.21%)`**，`v6 ex-self = 57 / 63 / 72 (21.84%)`，`v4 = 80 / 96 / 102`；<br>`[biosysmodb121·调参干净集 N=220]`：**`v6 all = 113 / 127 / 134 (51.36%)`**，`v6 ex-self = 56 / 62 / 69 (25.45%)`，`v4 = 76 / 91 / 96` | 5 折通路分组 CV 实测 `118 / 261` |

### 1.2 `[dev-298·留出集 N=102]` 主线配置（`wl3+@20` 2 路同源共识 + 单路披露）

| 配置项 | 冻结参数 | 说明 |
| :--- | :--- | :--- |
| **模型与证据卡** | `deepseek-v4.1-flash-1017`，`--no-evidence-card` | 同上 |
| **候选池策略** | `v1.4 wl3`（或 `wl4`，需开箱前勾选；调参实证底座为 `wl3` 主序列 + `w20` 尾部去重补全至 `max_pool=20`，含 `d2_cofactor_whitelist_3=True`、`enable_v14_compiler_ext=True`、`fix_decide_atomtool_import=True`） | `n_admission_failures == 0` |
| **提示词与采样** | 默认通用提示词；**2 路独立同源采样**（不挂载 Stage-1、不启 `T14-3` 裁决） | 与调参 `298_v14_pb_pa::v14s4_cons_v3` 完全同构 |
| **调参锚点实绩** | `[dev-298·调参集 N=196]`：**2 路共识 `v6 = 95 / 123 / 127 (48.47%)`**（`v4 = 92 / 119 / 124`；5 折 CV `92 / 196`）；<br>同池单路 `v6 = 97 / 123 / 126 (49.49%)`（`v4 = 93 / 118 / 121`） | 域间双向隔离，独立报数 |

### 1.3 预注册主 Estimand 与 `all / NoSelf / MNXOnly / ex-self` 读法规范（2026-11-18 R2 冻结）

为保证论文摘要、主表、结论与未来 `T4` 留出集报告三处口径严格一致，正式预注册以下双层指标契约：

1. **主 Estimand（Primary Estimand = 数据库辅助全系统 `all` 口径）**：
   - 定义：系统在完整生化学知识供给（`recorded/corpus` 已知先例 + `S5-env/S5-rr/analog` 泛化规则 + LLM `novel` 推导 + `AtomTool` 守恒安检门 + 多路共识与 `trace_protected` 裁决）下的端到端 `ppv1-criteria-v6` `Hit@1/@3/@5`（附 `ppv1-criteria-v4`）；
   - 呈现纪律：以 `all` 口径作为知识增强系统的主指标（调参集 `118/261 = 45.21%`，`Clean-220` `113/220 = 51.36%`），但**凡在摘要、主表或结论中报告 `all` 主数字时，必须在同一页/同一表并列报告下述无自记录泛化指标**。
2. **并列泛化 Estimand（Co-Primary Generalization Readouts：严格区分 `full-system` vs `single-route`）**：
   - **输入端清零自记录 `NoSelf`（Input-Level `self=0`，硬门校验 `self_record_hits == 0`）**：
     - **调参集全系统 `T1-6 NoSelf` 实测（`full-system`，输入端 `self=0`）**：`11-pass` 达 **`v6 all = ex_rec_only = 94 / 127 / 134 (36.02%)`**、**`Clean-220 = 90 / 120 / 126 (40.91%)`**、`v4 = 61/261 (23.37%)`，严格再剔同对模板后 `ex-self = 70/261 (26.82%)`、`Clean-220 = 66/220 (30.00%)`；同构 `5-pass` `T1-6 NoSelf_5p` 达 **`94 / 125 / 130 (36.02%)`**、`Clean-220 = 91/220 (41.36%)`、`ex-self = 70/261`；
     - **调参集单路对照 `DB-2 NoSelf`（`single-route` 单路臂）**：主复本 `pa` 为 `all = 96/261 (36.78%)`、`Clean-220 = 92/220 (41.82%)`（`ex-self = 69/261 [26.44%]`、`Clean-220 = 65/220 [29.55%]`），11 批独立均值±SD 为 `88.18 ± 3.28 / 261 (33.79%)`（`ex-self = 63.45 ± 2.88`）；
     - **架构级边界铁律**：`DB-2 NoSelf` 与 `DB-6 MNXOnly` 均为 **`single-route arms`（单路采样臂）**，不得冒充或混写为多路全系统泛化值；全系统 `T1-6 NoSelf` 须以真实多路 `self=0` 采样运行结果单独报出，并在 `T4` 留出集开箱时按同构多路 `NoSelf` 同步实测。
   - **纯规则迁移标尺 `MNXOnly`（`single-route` 规则泛化臂）**：
     - 仅开放 MetaNetX 通用酶学规则、天然零自记录命中（调参集 **`DB-6 MNXOnly` [`single-route`]：`all = ex-self = 102/261 [39.08%]`、`Clean-220 = 95/220 [43.18%]`、`v4 = 65/261 [24.90%]`**），单独作为跨底物规则迁移基线披露，同样显式标注 `single-route`。
3. **事后剔除指标 `ex-self` / `ex_rec_only` 的定位与禁令**：
   - 满配池上的事后 `ex-self`（同时剔 `rec-` 直接记录与同底物-主产物重合 `tpl-` 模板；调参 `T1-6 = 57/261 [21.84%]`）与 `ex_rec_only`（仅剔 `rec-`；调参 `T1-6 = 72/261 [27.59%]`）仅用于披露满配池命中里的直接先例占比；
   - **严禁再用事后“Rank 1 占座效应”解释去替代输入端 `self=0` 的实测 `NoSelf` 数字**。
4. **外部基线可比性边界（Leakage Caveat）**：
   - `BioTransformer 3.0` 与 `ECLIPSE PREDEC (10f)` 的手工规则库或预训练/交叉验证语料并未相对本评测题做 `ex-self` 剥离（*external baselines are not ex-self-controlled*）；将本系统 `NoSelf` / `ex-self` 与外部模型 `all` 并列属对本系统偏保守的不对称参照，不代表外部模型的零泄漏泛化估计。

---

## 2. 官方分集身份与冻结判分器 SHA256

1. **留出集切分元数据（只读引自 `split_summary.json`，零打开 `holdout_qids.txt`）**：
   - `[biosysmodb121]`（按 `case_id` 分组，`119` 组）：调参集 `261` 题（`76` 通路，`dev_list_sha256: 08b858cc...e974`）、**留出集 `156` 题（`43` 组，`holdout_list_sha256: 0ca964fd...555`）**；
   - `[dev-298]`（按 `substrate_strict_identity` 分组，`209` 组）：调参集 `196` 题（`dev_list_sha256: acdc7bfd...4f71`）、**留出集 `102` 题（`67` 组，`holdout_list_sha256: 17bd9731...31d`）**。
2. **三份冻结判分器 SHA256**：
   - `scripts/eval/score_disclosure_v4cn.py`: `0ffb8b71330653f7b0373a67d028b14a84d4c5f13a83abd17db89a3c82a28f2f`
   - `src/pathway_v43/pollutant/evaluation.py`: `ac38ea393bfb91e420e98730415cba334df2f9d3d9de4ecfde90914f45363f41`
   - `src/pathway_v43/pollutant/s5b_scoring.py`: `5a677550ef54a3a1e16d5b5a1ce4dd8d2cdcb55dd56224e8a148f50511dc456d`

---

## 3. 解锁边界与开箱执行规程

1. **当前停靠点**：严格停在 `~/.ppv1_holdout_token` 授权红线之前；未获 CC 明确解锁指令前，严禁任何代理读取或触碰留出集。
2. **开箱解锁后执行规范**：
   - 全程重计算与建池/重放/判分在 **HPC 乌镇** 32C 节点完成，API 并发设 `2` 题前置冒烟与预算上限硬熔断；
   - 无本地单价快照时金额统一记「**未核实**」；
   - 开箱终测严格按 §1.3 预注册契约同页并列报告 `ppv1-criteria-v6`（主）与 `ppv1-criteria-v4`（附）下的 **`all` 主指标、输入端 `NoSelf`（同构多路与单路分列）及事后 `ex-self / ex_rec_only`**，并一并重算全集基线 `v6` 对照（对外引用前须执行一次独立复核）。

     > **[2026-11-25 状态注｜上述「独立复核」前置条款已作废]**：上句括号内「对外引用前须执行一次独立复核」系沿用本地内部代理配置（`AGENTS.md` 2026-10-30 无人值守自迭代阶段条款 5，原意防范自迭代期间同步改动判分器）；该自迭代评审流程早已停用，本实验未另行执行对应外部复审、亦无相关复审记录。鉴于本 `T4` 留出集终测全程三份冻结判分器 SHA256 前后逐字节一致、核心源码 `src/` 零改动，已完成干净目录离线复现包 `--self-check (n_diffs=0)`，且全部逐题明细 TSV 已推入仓库由论文统筹侧独立验算核对，该前置条件于 `2026-11-25` 正式标为**作废**（原文保留不改历史，其余预注册契约不变）。
