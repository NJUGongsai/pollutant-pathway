# 评审请求 — T-I 两臂终审与发车代决（2026-10-20）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 全部题数、比例只在该题域成立。
> **零金标、零题面、零凭证值。**
>
> **请求类型**：T-I 两臂实施的**最终审核 + 发车代决**。
> **授权链**：CC 2026-10-20：「开始做，然后直接推进到 P2；需要我/师姐裁决的由 Codex 代为裁决，
> Codex 的裁决即为最终裁决」。因此本次请 Codex **代 CC/师姐**对 T-I 预注册与发车做终审；
> 但真实作业凭证、netcheck、实际作业号等**事实**仍须先落实，不能凭报告宣布已发车。

## 1. 变更摘要（相对你上次看到的 T-I 草案）

| 项 | 变更 |
|---|---|
| 臂数 | **三臂 → 两臂**：A=GLM-5.3-Flash（基线，`llm.env`）；B=DeepSeek（挑战臂，`llm_ds.env`） |
| Kimi | **已按 CC 决定移除**（成本原因）；预注册/任务书/配置中的 Kimi 内容已删 |
| DeepSeek 模型 | 定死 **`deepseek-v4.1-flash-1017`**；HPC `llm_ds.env` 的 base=`https://dashscope.aliyuncs.com` |
| 统计 | 双挑战臂的 Holm 校正不再需要 → **单一主比较 B−A**；5pp 阈=15/298=5.03pp 不变 |
| 其余 | A 同批重跑、两臂 no-cap、证据卡关、profile/gate 沿 T-H 不变 |

## 2. HPC 事实（主窗口实测，未输出 key）

- `~/ppv1_hpc/env/llm_ds.env`：已备份为 `llm_ds.env.bak.20261020`；仅改 `V43_LLM_MODEL` 一行；
  现为 `deepseek-v4.1-flash-1017`；base host=`dashscope.aliyuncs.com`；权限 600；key 行在位（未读值）。
- `llm.env` 仍为 `ZHIPU/GLM-5.3-Flash` + dashscope。
- 两 env 均 600，未打印任何 key。

## 3. 必读输入

| 文件 | 作用 |
|---|---|
| `docs/T_I_PREREG_2026-10-20.md` | 两臂预注册（S2+单一主比较、M2+M1、no-cap、A 同批） |
| `docs/TASK_T_I_LAUNCH_2026-10-20.md` | 发车任务书（两臂；§7.1 监控阈值待你裁决） |
| `docs/T_I_IMPLEMENTATION_PREP_2026-10-20.md` | 实施收尾报告（71/71 合成验收；7 个 bug 修复） |
| `docs/review_evidence/ti_prep_2026-10-20/` | 合成验收证据（SHA256SUMS 全过） |
| `docs/T_I_SCRIPT_LOCK_2026-10-20.json` | 13 件脚本/依赖/文本 sha 锁（含两臂模型与 env 名） |
| `scripts/hpc/ti_operations.py`、`ti_run_wrapper.py`、`sbatch_ti_{build,run,score}.sh`、`ti_arm_config.json` | 实施件 |
| `docs/T_H_P0_DECISION_CODEX_REVIEW_2026-10-20.md` | 你上一轮 P0 审核（T-I 状态/边界） |

## 4. 审核重点

1. **两臂预注册**：单一主比较 B−A、5pp=15/298、M2+M1、no-cap、A 同批重跑是否写死且无残留 Kimi。
2. **实施**：71/71 合成验收是否覆盖关键 fail-closed；7 个 bug 修复是否改变科学行为；
   `arm_config` 是否只含两臂、DeepSeek 模型名是否与 env 一致；脚本锁 13 件 sha 是否与实际一致。
3. **监控阈值**（实施代理未硬停、交你决定）：
   - smoke10 失败 >0 是否应停整臂？
   - full 失败 >15 题是否应停整臂？
   请给明确阈值与处置（停/继续/登记）。
4. **发车前置**：真实作业凭证、netcheck、两臂 `V43_LLM_REQUEST_PARAMS` 逐字同值预检、
   P2 期望值人工核对——哪些是**必须**、哪些可并行；缺一是否 no-go。
5. **代决**：是否批准两臂 T-I 预注册与发车（代 CC/师姐）；若批准，给出**发车条件清单**与
   **唯一的 go/no-go 判据**；若不批准，给最小回修清单。
6. **与 P2 的关系**：T-I 出数后 P2 证据卡 v2 的启动条件是否仍按你上轮报告（P0b 正式门 +
   v2 离线实施书 + 付费签字）；T-I 两臂结果如何选择 P2 的模型臂。

## 5. 纪律

- **只读审核**；只允许新增 `docs/T_I_CODEX_FINAL_REVIEW_2026-10-20.md` 与
  `docs/review_evidence/t_i_codex_2026-10-20/`（如运行校验）。
- 不改 `src/`、`tests/`、`scripts/`、既有 docs、封存批根；不 push；不调外部模型；
  不跑 HPC 作业；不读金标/题面/reference_graphs/llm.env 内容/私钥；不输出 key 或化学结构正文。
- 不把“合成验收 71/71”写成“真实可发车”；不把“Codex 批准”写成“作业已发”。
- 你的裁决为最终裁决（代 CC/师姐），但必须落文档、列条件、保留 unknown。

## 6. 输出格式

`docs/T_I_CODEX_FINAL_REVIEW_2026-10-20.md`：

1. **总裁定**（3–5 行）：批准/需修正/不批准；一句话条件。
2. **逐项审核**：§4 的 6 个重点，每项“通过/需修正/不成立”+ 证据。
3. **监控阈值裁决**：smoke10、full 的明确阈值与处置。
4. **发车前条件清单**：必须项/可并行项/缺一 no-go 项。
5. **代决记录**：批准范围（预注册/发车/两臂配置/no-cap）、不批准项、需另行处理项。
6. **P2 启动条件与模型选择**。
7. **unknown/未核事项**（T-I 实时状态、凭证、金额等）。

所有数字带 **298 题域标签**；引用证据给路径与计数。