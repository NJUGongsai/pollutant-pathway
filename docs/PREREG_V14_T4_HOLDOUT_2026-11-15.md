# `T4` 单步留出集终测预注册升级登记（`v1.4` 生产冻结配置：`prereg-v14-t4-holdout-2026-11-15`）

> **状态**：**`v1.4` 调参集已在 `[biosysmodb121·调参集 N=261]` 达到 `118 / 261 (45.21%)`（并列 `[N=220]` `113 / 220 = 51.36%`）、在 `[dev-298·调参集 N=196]` 达到 `95 / 196 (48.47%)`（单路 `97 / 196 = 49.49%`）；本文件正式取代已暂停的 ``PREREG_V13_T4_HOLDOUT_2026-11-14.md``，停在 `~/.ppv1_holdout_token` 令牌授权边界前，等待 CC 显式解锁指令后方可执行唯一一次开箱终测。**
> **基准代码锚点**：``<LOCAL_WORKSPACE>/v44_v13``，分支 `ocagent/261116-v14-trace-protected-b7xt`（核心实现提交 `4860cd8`）。
> **依据报告**：``V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md``。
> **隔离与脱敏声明**：本文档零 SMILES/InChI、零私有题号；**零读取 `~/.ppv1_holdout_token`、`holdout_qids.txt` 与 `holdout_v1`**。

---

## 1. 留出集分域冻结配置（继承已通过 5 折 CV 的 `v1.4` 优胜底座）

### 1.1 `[biosysmodb121·留出集 N=156]` 主线配置（与调参夺冠臂同构）

| 配置项 | 冻结参数 | 说明 |
| :--- | :--- | :--- |
| **模型与证据卡** | `deepseek-v4.1-flash-1017`，`--no-evidence-card` | 原生深度思考，零额外温度/长度覆盖 |
| **候选池策略** | `v1.4 wl4` 标准 `@16` 混合池（开启 `d2_cofactor_whitelist_3=True`、`d2_cofactor_whitelist_4=True`、`enable_v14_compiler_ext=True`、`enable_v14_compiler_ext_2=True`） | `n_admission_failures == 0` 预检硬门 |
| **提示词与 Stage-1 路由** | `enable_v13_prompt_v3_type = True`；独立盲底物 Stage-1 大类路由 `stage1_routing_file` | 仅提供共识 `stage1_bonus`，不改池成员 |
| **采样路数与后处理开关** | 多路同质 `wl4` 采样（推荐 **5 路同池独立采样**以复刻调参低方差底座；或 CC 另行勾选路数）+ `enable_v14_cross_pool_elig_norm=True`、`enable_v14_multipass_consensus_v3=True`、`enable_v14_novel_low_sim_boost=True`（`0.18`）、`enable_v14_equiv_product_consensus=True`（`v14_equiv_cluster_mode="strict"`）、`enable_v14_raw_order_consensus=True`（`guarded_r2_r7`）、`enable_v14_sec_novel_backfill=True`、`fix_decide_atomtool_import=True` | 严格冻结于 `v1.4` CV 验证配置 |
| **终段双序机理裁决（`T14-3 + trace_protected`）** | ``v14_t14s3_adjudicator.py`` `PROMPT_VERSION = "v14-t14s3-mech-adj-1"`；<br>策略冻结为 **`trace_protected|d8|u99|e3|r2`**（`gate_mode="trace_protected"`, `min_conf_sum_disagree=8`, `min_conf_sum_unanimous=99`, `min_each_conf=3`, `max_challenger_rank=2`） | 按比例不变门控自动适配实际采样路数 `N >= 2` |
| **调参锚点实绩** | `[biosysmodb121·调参集 N=261]`：**`v6 = 118 / 133 / 141 (45.21%)`**，`v4 = 80 / 96 / 102`；<br>`[biosysmodb121·调参干净集 N=220]`：**`v6 = 113 / 127 / 134 (51.36%)`**，`v4 = 76 / 91 / 96` | 5 折通路分组 CV 实测 `118 / 261` |

### 1.2 `[dev-298·留出集 N=102]` 主线配置（`wl3+@20` 2 路同源共识 + 单路披露）

| 配置项 | 冻结参数 | 说明 |
| :--- | :--- | :--- |
| **模型与证据卡** | `deepseek-v4.1-flash-1017`，`--no-evidence-card` | 同上 |
| **候选池策略** | `v1.4 wl3`（或 `wl4`，需开箱前勾选；调参实证底座为 `wl3` 主序列 + `w20` 尾部去重补全至 `max_pool=20`，含 `d2_cofactor_whitelist_3=True`、`enable_v14_compiler_ext=True`、`fix_decide_atomtool_import=True`） | `n_admission_failures == 0` |
| **提示词与采样** | 默认通用提示词；**2 路独立同源采样**（不挂载 Stage-1、不启 `T14-3` 裁决） | 与调参 `298_v14_pb_pa::v14s4_cons_v3` 完全同构 |
| **调参锚点实绩** | `[dev-298·调参集 N=196]`：**2 路共识 `v6 = 95 / 123 / 127 (48.47%)`**（`v4 = 92 / 119 / 124`；5 折 CV `92 / 196`）；<br>同池单路 `v6 = 97 / 123 / 126 (49.49%)`（`v4 = 93 / 118 / 121`） | 域间双向隔离，独立报数 |

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
   - 开箱终测同时双报 `ppv1-criteria-v6`（主）与 `ppv1-criteria-v4`（附）的留出集与对应全集成绩，并一并重算全集基线 `v6` 对照（对外引用前须执行一次独立复核）。
