# 复审请求 — T-I TI-F1/F2 回修关闭确认（2026-10-21）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 零金标、零题面、零凭证值。
>
> **请求类型**：按你 2026-10-20 终审报告 §5 的**固定面**，复核 **TI-F1（监控/双臂阶段硬停）**
> 与 **TI-F2（批准包首消费校验）** 是否关闭。**只审这两项**，不扩 P0b/证据卡/池/检索/排序/
> 评分/D-1/D-3/D-7/付费批。你的结论为最终裁决（代 CC/师姐）。

## 1. 你上轮的要求（原文要点）

- TI-F1：smoke2 身份/usage 门；smoke10 非豁免 failed>0、非已登记结构性零调用>0、pending>0 ⇒
  停两臂；full 非模型内容运行失败>15（第 16 个失败 qid）⇒ 停两臂；fatal 信号立即停；
  恢复仅 prediction_recovery 白名单同题同参一次、二败停；**无 token/金额硬停**，超规划只告警；
  15 分钟巡检、单协调者、取消/阻断路径；两臂 smoke10 都过才准 full。
- TI-F2：批准包含原预注册/任务书/终审报告/脚本锁完整快照 SHA；`approval_source=Codex 代 CC/师姐`
  + 授权链；`no_cap_ack=true`；文本 SHA 与批准 JSON SHA 分列；缺件/SHA 不符 fail-closed；
  不得伪填 CC 本人。

## 2. 本轮修复与证据

| 件 | 路径/值 |
|---|---|
| 回修报告 | `docs/T_I_TI_F1_F2_REPORT_2026-10-20.md` |
| 证据目录 | `docs/review_evidence/ti_f1f2_2026-10-20/`（含 SHA256SUMS） |
| 代码落位 | `scripts/hpc/ti_operations.py` 第 49/549/638/876/986/1513/2084 行；`sbatch_ti_run.sh` 第 63/86/96 行；新增 `sbatch_ti_monitor.sh` |
| 正负控 | 本机 50 项 + 公共链 13 场景 = **63/63 通过**（含 smoke10 1 failed、未登记零调用、pending、full 15/16、fatal、恢复一次/二败、token 超带只告警、批准包缺件/`no_cap_ack=false`） |
| 脚本锁 | `docs/T_I_SCRIPT_LOCK_2026-10-20.json`：14 文件全匹配、`missing=[]`；锁 SHA `1ed4f278…5528d13d0` |
| 批准包 | `docs/T_I_APPROVAL_PACKAGE_2026-10-20/`：`approval_basis=原预注册+任务书+本终审增补`；`source_kind=codex_delegated_cc_shijie`；`approved_at=2026-10-20T15:49:53Z`；`no_cap_ack=true`；四文书 SHA 全绑；批准 JSON SHA `1766734b…07fa6b1` |

## 3. 请你核（固定面）

1. **TI-F1 阈值实现**是否逐条符合你 §3 的裁决；按唯一 qid 计数、失败分类、unknown 不豁免；
   两臂 barrier；15 分钟巡检/取消路径是否可执行。
2. **TI-F2 批准包**字段/来源/SHA/`no_cap_ack` 是否合规；首消费校验是否 fail-closed；
   是否错误伪填 CC 本人；文本 SHA 与 JSON SHA 是否分列。
3. **63/63 正负控**是否覆盖你点名的全部反例；是否有“只测 helper 不测消费入口”的缺口。
4. **脚本锁**是否与实际文件一致；是否只改白名单（ti_* + 新 monitor + 测试）。
5. **是否允许关闭 TI-F1/F2**；若否，给最小回修清单（不得扩范围）。
6. 关闭后 **C0–C8** 还需哪些事实（C2 凭证/分区、C3 netcheck、C4 请求参数、C5 最小真实调用、
   C6 build 身份、C7 P2-face 读数、C8 协调/smoke 回执）；哪些可并行、哪些缺一 no-go。
7. 当前发车状态：仍 **NO-GO** 直到 C0–C8 全绿；请确认。

## 4. 纪律

- 只读审核；只新增 `docs/T_I_CODEX_REREVIEW_2026-10-21.md` 与
  `docs/review_evidence/t_i_codex_rereview_2026-10-21/`（如运行校验）。
- 不改 `src/`/`tests/`/`scripts/`/既有 docs/封存批；不 push；不调模型；不跑 HPC；
  不读金标/题面/reference_graphs/env/key；不输出 key 或结构正文。
- 不把“63/63 合成绿”写成“真实可发车”；不把“批准包生成”写成“已发车”。

## 5. 输出

`docs/T_I_CODEX_REREVIEW_2026-10-21.md`：
1. 总裁定（关闭/需修正）；
2. TI-F1、TI-F2 逐项通过/需修正；
3. 63/63 覆盖评价；
4. 脚本锁与白名单；
5. 关闭后 C0–C8 最小清单与唯一 go/no-go；
6. unknown/未核事项。