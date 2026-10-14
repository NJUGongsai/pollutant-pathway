# chain13 三模型并行对比·预注册增补（2026-10-14）

> 状态：**preregistration_confirmed_2026-10-14**（CC 当日拍板：mimo 位
> 换 qwen3.8-flash[百炼无 mimo-v2.6-flash，实查仅 xiaomi/mimo-v2.5-pro]、
> 三模型同时跑、全套协议沿用、探索性不设判定线）。
> 题域标签：**298=RHEA 通用酶学/已见题，与 dev 双向不外推**。
> 红线：金标/题面零外带；判分零 LLM；旧批零回写；封存 run 只读。

## 一、三臂定义（模型=唯一变量）

| 臂 | 模型（百炼实查 ID） | 批根 | 状态 |
|---|---|---|---|
| GLM | ZHIPU/GLM-5.3-Flash | `~/ppv1_hpc/batch/chain13_s5b_20261014` | chain13 主批（build 46548633 在跑，`docs/CHAIN13_S5B_298_PREREG_2026-10-14.md` 为其主预注册） |
| qwen | **qwen3.8-flash** | `~/ppv1_hpc/batch/chain13q_s5b_20261014` | 本增补登记 |
| ds | **deepseek-v4.1-flash** | `~/ppv1_hpc/batch/chain13d_s5b_20261014` | 本增补登记 |

## 二、协议（三臂完全同参，全套沿用 chain13）

- 代码 v43@b6ba35f（policy-7 共底物伴生供给+声明链）+ v2 headline
  双口径判分（v1 敏感性并列）；
- **每题 3 真实调用**（max_real_model_requests=3+format_feedback 2，
  profile_policy 发车覆盖）；gate_max_calls=4470；workers 8/
  RPM 200/TPM 3M（各批独立 gate，三模型走 DashScope 不同模型级
  配额池互不挤兑）；
- no-cap（CC 2026-10-14 沿用拍板）；冒烟 2→10→全量并入正式批；
- env：`~/ppv1_hpc/env/llm_qwen.env`、`llm_ds.env`（从 llm.env
  服务端 sed 仅换 V43_LLM_MODEL 行，密钥零打印零外带）。

## 三、对比纪律

- **探索性，不设判定线**（P4"≥5pp 且桶迁移"线留正式模型选型轮）；
- 三臂同题卷/注册序/判分链/协议；模型间差异如实报，不做模型选型
  结论；多变量叠加披露（vs chain12 的差异含 C 供给+声明链+v2+3
  调用，归因以三臂内部对照+与 chain12 的口径注释呈现）；
- 输出=三模型对照表（hit@1/3/5、桶、U、账目，v2 headline 口径）。

## 四、发车门

各臂独立：approve（preregistration_id=chain13-modelcmp-20261014，
本增补）+ budget（no-cap 标记同文）+ 冒烟门（2 题至少 1 完成）。
