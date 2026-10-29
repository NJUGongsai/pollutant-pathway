# 复审请求 — C 线共底物伴生供给实施（Codex，2026-10-14）

> 粘贴给 Codex 的完整提示词（自包含；可与终裁请求同会话或另开）。
> **题域标签：298=RHEA 通用酶学/已见题，与 dev 题域双向不外推。**
> 本文全部数字为实施验收/探针口径（解锁面、exact 正控、测试计数等），
> **非判分成绩、非预注册投影**。

---

工作目录：`/Volumes/CC/Enzyme_Agent/dependingv43`（fork 以此 cwd 发起）。请复审 C 线共底物供给实施件：**commit `873c323`**（10 文件 +1423/−22，以 `git show --stat 873c323` 为准；交付书 §五笔误 +1422 以 git 为准）。
这是已冻结设计书 `docs/C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md`（mimo 场景 1 已评+修正已应用）+ 任务书 `docs/TASK_C_COSUB_IMPL_2026-10-14.md` 的实施轮。输入清单：上述设计书+任务书、交付书 `docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md`、本 commit 本体、证据目录 `reports/ppv1_s5b/c_impl_2026-10-14/`。
**审谁**：只审 `873c323` 本体；当前 HEAD=`dda852b`（criteria-v2 P1fix2，`native_result.py/store.py/test_ppv1_s4b_export.py`）与本任务文件零重叠（`git diff 873c323..dda852b --name-only` 可验），HEAD 全量数仅作基线对照、不纳入本轮评审范围。

实施内容（交付书）：
1. **build 期伴生供给**（s5b_builder.py，语义 a）：analog 前置门拒的候选按共底物袋救援——主反应物=与底物最大 Tanimoto（归因探针同口径）、供给=模板袋精确多重集、裸通配 `*` 拦截、spectator 逐条披露、主 cn 不可解析 fail-closed；候选带完整声明面（participants/co_substrate_states/declared_copy_components/cosubstrate_event_contract/record_equation+ref）；池策略 **s5b-pool-policy-6→7**，池宽/阈值/排序/融合序零变化；
2. **run 期声明链发射**（production.py）：spec 记录方程成对声明 fail-closed 校验 → hypothesis.provenance_refs → 事件提交前 put_provenance（worker 提交路径，幂等）——严格按 criteria-v2 预注册 §二.1 的 pred1 消费契约（判分侧零改动）。

验收证据（`reports/ppv1_s5b/c_impl_2026-10-14/`，可用 `~/miniconda3/envs/depending43/bin/python` 复跑）：
- 解锁面复现 **45 行/35 题=探针锚**（454 行逐行对账：446 行 outcome 全等 + 8 行 corpus 只分类，拦截结果不变；裸通配 3 行 `wildcard_blocked`）：`unlock_face_replay.py`；
- **v2 豁免正控（端到端公共链）**：11 题纯 H₂O 袋 → 5 事件 exact（v1 口径 0）、5×v1_exempt tier、三谓词全过；其余 6 题机制类 extras 诚实维持 partial：`v2_exemption_positive_control.py`；
- 字节不变：262 题全等 + 35 题纯新增供给 spec + 1 题 W4 补位互动（供给入池抬高独特净反应数→不再触发降阈值重检索，如实披露非漂移）：`byte_invariance_probe.py`；
- 测试：新增 test_ppv1_s5b_cosub_supply.py 10/10 + 版本承载断言同步 + 全量 not-slow 零翻转。**基线口径全链条（防撞账，线性栈）**：`0ba764f`（doc-only，2121/0/16）→ `7e7855c`（P1+P2 实施）→ 本任务 `873c323`（+10 测试）→ `dda852b`（P1fix2，+4 测试）→ **当前 HEAD 主窗口复跑=2135/0/16（2026-10-14，6m01s 实测）**；交付书行文基线 2121（本任务开工前口径）。

请重点审：
1. 实现与冻结设计书的逐条款一致性（供给语义 a/精确多重集/wildcard 不供给/spectator 披露/方向限定声明带侧别）；
2. 交付书 §三 披露的六项偏差是否如实且不越范围（特别是 execution_input_smiles 新声明字段=运行期执行输入声明与首消费核验、NC-10 record_products 轴=执行净产物全量、不复制 donor rhs，与 record_equation=模板记录两侧分开）；
3. 判分侧零改动声明属实性（`git diff 7e7855c..873c323 --name-only` 应无 evaluation/s5b_scoring/recorded_source 运行时改动）；
4. 池宽 8/阈值 0.45/排序/截断/融合序零变化（单变量纪律，`S5B_POOL_MAX/THRESHOLD` 未动）；
5. 误供给面（不该救的救了/该拦的没拦——wildcard 口径、主 cn fail-closed、provenance 发射的幂等与 fail-closed）。

报告带 P1/P2/P3 分级+终判定（通过/有条件通过/退回），落 `docs/`（命名建议 C_COSUB_SUPPLY_IMPL_CODEX_REVIEW_2026-10-14.md，未跟踪、不提交）。纪律（不变）：只新增本报告与证据目录；不动 src/tests/既有 docs/AGENTS.md；不访问金标/题面/封存逐题 run；不 push；不调用外部模型。零金标零题面外带。
