# EC298 Phase C 二轮独立复核（2026-09-28）

**结论：暂不通过。** 提交说明中的三项 P1（非 recorded 直通、金标题号错位、非法元素异常）及两项补齐（先增后引、超过 16 个对齐）在本轮检查范围内均已修复；但 Phase B/C 集成后仍有一条原始类比卡绕过适用性与编辑门禁、占报告首位并提交事件的路径。另有三项较低优先级的审计或协议缺口。此复核只改本报告，不改预测实现、资产、封存首跑或金标。

## 1. 阻断项

### P1：rank 可以把原始 analog/rule 卡选为已验证产物并提交

[`prediction.py`](../src/pathway_v43/services/prediction.py) 第 182–191 行已正确把非 recorded 卡排除在 `usable` 外，解决了本轮所报的“伪装 recorded 直通”和候选重复问题；但 `predictive` 仍被拼入 **同一个可选候选集**。模型可把其中的原始 `analog_reaction` 置于 `order[0]`。[`nodes.py`](../src/pathway_v43/workflow/nodes.py) 第 772–776 行将任意 `selected` 送入提交路径，验证阶段的 recorded 资格门禁对非 recorded 返回通过；[`report_adjudication.py`](../src/pathway_v43/services/report_adjudication.py) 第 253–279 行又把选中的非 recorded 卡标成 `card_eligible=true`、`not_validated_for_reporting=false`。这绕过了 Phase C 适用性块、AtomTool 顺序编辑和 Phase B 对原始类比卡的 `not_validated_for_reporting` 约束。

**独立临时 run 复现：** 当前底物为儿茶酚，同父检索含两张真实 recorded 卡和一张普通原始 analog 卡（`match_type=analog_similarity`，产物 `CC#N`）；fake rank 响应 `selected=E-an, order=[E-an,E-r1,E-r2]`。运行结束有 **1 个 ReactionEvent**，最终裁决中 `E-an` 的 `report_rank=1`、`committed_event_ref` 非空，卡级 `card_eligible=true` 且 `not_validated_for_reporting=false`。无需伪造 recorded 挂牌即可复现。已有 `test_forged_analog_card_never_passes_as_usable_recorded` 只让模型选择 recorded 卡，未覆盖“模型选择 analog 卡”这一侧。

**修复门槛：** rank 的可选择 ID 仅限同底物且通过 recorded 资格判据的卡；若保留规则/类比原始卡作推理上下文，应与可选择集合分字段。解析、`validate_products` 和最终候选裁决均防御性拒绝 rank 选中的原始规则/类比卡，不得因模型选择而改变证据类型。新增完整工作流反例：两张 usable recorded + 原始 analog/rule，模型分别尝试选原始卡时不产生其报告产品或事件；正常选择 recorded、未选中原始卡留 `not_validated_for_reporting` 的行为不退化。此问题违反 [`TASK_V43_EC298_PHASE_C.md`](TASK_V43_EC298_PHASE_C.md) §5 和 [`TASK_V43_EC298_PHASE_B.md`](TASK_V43_EC298_PHASE_B.md) §2 的交接约束。

## 2. 其他需补齐项

### P2：金标题号门禁只拒“零交集”，漏一题仍静默计成未命中

[`phase_c_offline_audit.py`](../scripts/phase_c_offline_audit.py) 第 159–165 行仅在 66 个任务与金标 **零**交集时失败。独立反例：从临时金标副本只删去一个类比题 qid，再运行相同审计；命令以 0 退出并写报告，`n_analogy_tasks=66`、`n_task_qids_found_in_gold=65`，缺题的诊断匹配会被当成 `false`。本次正式封存输入为 66/66，**已报告的 8/23 不受此反例影响**。请要求所有审计任务 qid 均在金标中且唯一，缺任一题时失败，并加一题缺失夹具。

### P2：编辑协议 v2 仍接受未声明字段及旧操作别名

[`atom_tool.py`](../src/pathway_v43/services/atom_tool.py) 第 325–358 行没有逐操作的允许字段表。独立调用 `validate_edits(render('CCO'), [{'op':'add_atom','atom1':'S_C_1','element':'O','new_atom_id':'S_O_9','unexpected':'ignore_me'}])` 返回 `ok=true`；第 71–72 行还把 `remove_bond` / `add_bond` 当作有效操作。任务书 §4 明确要求未知字段/操作有稳定拒因，提示词声明“仅以下四种操作”。请使 v2 校验严格按四种操作及各自字段集拒绝多余字段与旧别名；若旧协议需要别名，通过显式旧版本分派处理，并补测试。

### P2：修复 16 条落盘截断后，RDKit 默认仍会截取第 1000 个匹配

[`donor_applicability.py`](../src/pathway_v43/services/donor_applicability.py) 第 273–285 行两次 `GetSubstructMatches` 都未设置 `maxMatches`。独立合成例：1001 个断开的碳原子作为当前分子，单碳查询经 `enumerate_alignments` 只得到 `n_alignments_full=1000`；同一 RDKit 调用显式 `maxMatches=2000` 得 1001。环境底物通常远小于此例，封存 66 题的 23/43 统计没有据此判定错误；但“评估全部相关对齐”的无条件声明仍不成立。建议设版本化的安全上限，达到上限时 fail-closed 标记 `alignment_limit_exceeded`，或明确足量上限并证明未截断；不能把截断集合当作唯一适用目标。

## 3. 已独立核实与效果边界

- 在独立 `/tmp` 输出目录按报告命令重跑 Phase C 只读离线审计；五个产物与交付件**逐字节一致**。66 个任务题号全部进入金标索引；旧结果为 28 弃答 / 23 拒绝 / 15 接纳，拒绝臂 22/23 目标文本可解析、**8/23 文本匹配金标**，新协议同输入再分类 1 可执行 / 22 不可执行，路由模拟 23 类比 / 43 分流。8/23 是被拒目标文本的诊断，**不是管线命中数**。初版“0/23”确由 qid 前缀错位造成，现已更正。
- 对本轮修复及相关集成独立运行 70 个定向测试：**70 passed**。资产清单 **21/21 OK**、MoleCode vendor 清单 **7/7 OK**。本轮未独立重跑全仓 360 项；实施方的 `360 passed` 与上述阻断反例可以同时成立，因为该路径原本缺回归夹具。
- 代码核查与定向测试确认：`_usable_recorded`/rank 的 kind 守卫、非法元素 RDKit 周期表校验及执行层结构化拒绝、先增后引、超过 16 个对齐参与判定均已落地。修复前的 8/23 撤回应以本版报告更正为准。
- 共享树在复核开始时有另一会话的全仓 `pytest` 进程；本轮没有修改实现文件，后续检查该进程已结束。`HEAD=5c8f284`，Phase B/C 实现仍主要是未提交改动；结论针对本轮实际读取到的代码内容，不将其归于单一提交。
- 当前仍没有真实模型 dev 三臂对照，也没有新版 298 预测。离线分流数不能解释为 @1/@5 改善；旧 298 只能用于事后修复检查，不能作为选参集。

**三轮入口：** 先修 P1 并给出 rank 选中原始 analog/rule 的完整失败夹具，再补三个 P2 的失败测试；附当前代码快照或提交范围、重新生成的相关审计产物、定向与全仓测试结果。本轮尚不能签收 Phase C 与 Phase B 的集成门禁。
