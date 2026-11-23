# `T4` 单步留出集终测正式任务书（`prereg-v14-t4-holdout-2026-11-15`）

> **日期**：2026-11-23  
> **状态**：已获 CC 显式解锁 留出集解锁令牌 并确认发车清单；执行分支 `t4/holdout-final-20261123`（独立 worktree，基于 `v44_v13 @ b5a6e64607b4a782d0556adfdb9cae93e04b9abd`）。  
> **预注册锚点**：`docs/PREREG_V14_T4_HOLDOUT_2026-11-15.md`（R2 增补版）。  
> **算力调度约定**：全量重 CPU 计算（建池、准入预检、`NoSelf` 自记录核查、零调用重放、GIP 与 `ppv1-criteria-v6 --self-check` 判分）提交至 **HPC 乌镇**（Slurm 32C+ 节点，隔离目录 `<HPC_T4>`）；代码通过 `rsync` 增量同步（排除 `.git/` 与 `reports/`），金标/题面严禁入仓；本机仅运行 2 题前置冒烟、受控并发在线模型调用、`T14-3` 裁决在线调用、打包离线复现校验与轻量单测。  
> **隔离与脱敏声明**：本文档与全部脚本零 SMILES/InChI、零私有题号、零密钥、零 `git push`。

---

## 一、冻结口径、算力与红线

| 约束项 | 冻结值 / 规则 | 说明 |
| :--- | :--- | :--- |
| **主判分口径** | `ppv1-criteria-v6`（受控质子化不变身份，附 `ppv1-criteria-v4` / `v2`） | `Clean-Holdout` 仅在 `[biosysmodb121·留出集 N=156]` 并列报告 |
| **冻结判分器 SHA256** | `scripts/eval/score_disclosure_v4cn.py`: `0ffb8b71330653f7b0373a67d028b14a84d4c5f13a83abd17db89a3c82a28f2f`<br>`src/pathway_v43/pollutant/evaluation.py`: `ac38ea393bfb91e420e98730415cba334df2f9d3d9de4ecfde90914f45363f41`<br>`src/pathway_v43/pollutant/s5b_scoring.py`: `5a677550ef54a3a1e16d5b5a1ce4dd8d2cdcb55dd56224e8a148f50511dc456d` | 前后核对完全一致，`--self-check` 强制 `n_diffs == 0` |
| **留出集唯一性** | 严格独立开箱 **1 次**，零回传调参、零留出集阈值重扫 | 裁决门控策略固定为冻结 `trace_protected\|d8\|u99\|e3\|r2` |
| **题域双向隔离** | `[biosysmodb121·留出集 N=156]`（`43` 组）vs `[dev-298·留出集 N=102]`（`67` 组） | 严禁跨域外推 |
| **模型与证据卡** | `deepseek-v4.1-flash-1017`，`--no-evidence-card` | 原生深度思考，API 密钥通过 `--env-file <LOCAL_LLM_ENV_FILE>` 静默注入 |
| **并发与预算上限** | 总在途请求数 `<= 24`；累计总 Token 硬上限 **`65,000,000` tokens** | 无本地单价快照时金额统一记 `cost_status = "no_snapshot"`，严禁估算金额 |
| **双 Estimand 呈现** | 主报告 `all` 必须同页/同表并列输入端 `NoSelf`（同构 5 路与单路分列）、`MNXOnly`（单路）与事后 `ex-self` / `ex_rec_only` | 不得以事后 `ex-self` 替代实测 `NoSelf`；外部基线显式标注未做 `ex-self` 剥离 |
| **数字发布约束** | 自跑数属内部实测，对外引用（汇报/论文）前须经一次独立复核 | 提交隔离在 `t4/holdout-final-20261123`，不 push |

---

## 二、两域实验矩阵与 15 批采样计划

### 2.1 `[biosysmodb121·留出集 N=156]`（`43` 个 `case_id` 分组）

1. **盲底物 Stage-1 大类路由**：`b121_s1_routing`（`156` calls；`enable_v13_two_stage_routing=True, v13_routing_stage1_only=True`，提取 `b121_holdout_stage1_map.json`，校验解析率 `>= 0.90`）。
2. **`T1-6_Holdout_all_5p`（全系统主线 `wl4@16`，5 路同构）**：
   - 建池：`b121_wl4_full`（`max_pool=16`, `d2_cofactor_whitelist_3=True`, `d2_cofactor_whitelist_4=True`, `enable_v14_compiler_ext=True`, `enable_v14_compiler_ext_2=True`）。
   - 采样：`b121_all_pa..pe`（`5 × 156 = 780` calls；`enable_v13_prompt_v3_type=True`）。
   - 重放与裁决：`Consensus v3` + `b121_holdout_stage1_map.json` + `T14-3` 双序互换裁决（冻结门控 `trace_protected|d8|u99|e3|r2`，共享内容寻址缓存）。
3. **`T1-6_Holdout_NoSelf_5p`（全系统输入端清零自记录，5 路同构）**：
   - 建池：`b121_db2_noself`（`wl4@16` + 完整 `DB-2 NoSelf` 零金标剔除链：`ablation_source_filter` + corpus 扩展剔除 + `_drop_self_specific_s5_rr`；硬门 `self_record_hits == 0`）。
   - 采样：`b121_noself_pa..pe`（`5 × 156 = 780` calls；`enable_v13_prompt_v3_type=True`）。
   - 重放与裁决：`Consensus v3` + `b121_holdout_stage1_map.json` + `T14-3`（冻结门控 `trace_protected|d8|u99|e3|r2`，复用/共享缓存）。
4. **`DB-6_Holdout_MNXOnly`（纯通用规则迁移对照，`single-route`）**：
   - 建池：`b121_db6_mnxonly`（`wl4@16` + `DB-6` 过滤）；采样 `b121_mnxonly`（`156` calls）。
5. **`T1-0a_Holdout_bare_gate`（无池盲写+守恒门，`single-route`；同时输出 `T1-0 bare` 免安检原始答卷与三项化学幻觉率）**：
   - 建池：`b121_db1_empty`（空池）；采样 `b121_bare_gate`（`156` calls，`disable_atomtool_prompt=True`）。

### 2.2 `[dev-298·留出集 N=102]`（`67` 个 `substrate_strict_identity` 分组）

- **`D298_Holdout_2p`（2 路同构共识 + 单路披露）**：
  - 建池：`d298_wl3_w20`（先构建 `wl3` `max_pool=16` [`d2_cofactor_whitelist_3=True`, `enable_v14_compiler_ext=True`]，再以无 `wl3/ext` 的 `w32` 按 `v14_t14s2_build._spec_sig` 尾部去重补齐至 `max_pool=20`，对齐调参冠军批 `batch_v14_t14s2_298_pa_r2`；`n_admission_failures == 0`）。
  - 采样：`d298_wl3_pa`, `d298_wl3_pb`（`2 × 102 = 204` calls；默认通用提示词，不挂载 `v3_type`、不挂载 Stage-1、不启 `T14-3`）。
  - 重放：`Consensus v3`（主复本对齐 `298_v14_pb_pa::v14s4_cons_v3`，并同报两路单路成绩）。

### 2.3 同步附加计算（零新 LLM 调用）

1. **四层 `Clean-Holdout` 自动分桶**：按调参 `b121_261_layer_classification.jsonl` 同源规则（`L1A` 中枢碳汇 / `L1B` 脂肪酰基 CoA 管家代谢 / `L2` 自环无反应 / `L3` 缺重原子给体 / `L4` 仅立体异构 / `CLEAN`），先在调参 `261` 题校验 **`261/261` 逐题一致**，再作用于 `B121-156`。
2. **全集归档基线 `ppv1-criteria-v6` 补齐**：使用冻结 `score_disclosure_v4cn.py --self-check` 重算 `B121-417` 与 `298-298` 全集归档基线的 `v4` / `v6`（并拆出调参/留出分集对照）。
3. **跨全系统与单路的防截断与归档自检**：全部重放臂通过 `v13_t11_anti_truncation.py`（`n_violations == 0`），全部 `v6` 评分满足 `self_check n_diffs == 0`。

---

## 三、分阶段执行步骤与门禁

| 阶段 | 执行地 | 核心产物 / 验证门 |
| :--- | :--- | :--- |
| **T4-1 建池与准入** | HPC 乌镇 32C | `scripts/hpc/t4_holdout_pools_hpc.py` + `sbatch_t4_holdout_pools.sh`；5 臂全量 `n_admission_failures == 0`，`b121_db2_noself` 断言 `self_record_hits == 0` |
| **T4-2 建批与冒烟** | 本机 | `scripts/eval/t4_holdout_batches.py build/smoke`；15 批自检通过；5 臂代表 2 题前置冒烟（10 calls）`n_failed == 0` 且 `usage_missing_calls == 0` |
| **T4-3 在线采样** | 本机 | 15 批全量（2,232 calls，并发 `<= 24`，总 Token `< 65M`）；`n_failed == 0`；`Stage-1` 映射解析率 `>= 0.90` |
| **T4-4 重放与裁决** | HPC + 本机 | `pre-adj` 重放 `SINGLE_V2_PATCH` 与 `Consensus v3`、生成无泄漏裁决队列 → 本机 `v14_t14s3_adjudicator --mode run` → HPC `post-adj` 重放 `T1-6` 与防截断 `0` 违例 |
| **T4-5 冻结判分** | HPC 乌镇 32C | 4 层分类器 `261/261` 验证；全臂 `--self-check n_diffs == 0`；`raw_score`；全集历史基线 `v6` 补齐；三份冻结脚本 SHA256 复核 |
| **T4-6 报告与封存** | 本机 | 脱敏报告 `docs/reports/T4_HOLDOUT_FINAL_EVAL_REPORT_2026-11-23.md`；离线复现打包 `.tar.gz` + `/tmp/` 解压复算验真；轻量单测全绿；本地 commit（不 push） |
