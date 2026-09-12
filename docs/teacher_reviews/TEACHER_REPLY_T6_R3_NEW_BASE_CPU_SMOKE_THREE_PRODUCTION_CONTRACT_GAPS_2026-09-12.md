# TEACHER_REPLY：T6-R3 新 base 零模型 CPU smoke 三项 production 合同缺口裁定与修复下发

- 回复对象：陈浩然《STUDENT_FEEDBACK_T6_R3_NEW_BASE_CPU_SMOKE_THREE_PRODUCTION_CONTRACT_GAPS_2026-09-12》（新 base commit `1ade158`，零模型 CPU smoke）
- 裁定日期：2026-09-12
- 裁定性质：三项缺口**全部裁定成立**，属我侧 production 固定合同裂隙。已修复并随本 commit 下发，你方无需改动 production/schema/bridge/graph。

---

## 一、总体判定

你方 15 项检查 12 通过、3 项缺口的定位准确，代码位置与根因判断我侧逐一核实无误。三项缺口均为我侧生产合同在「非空语义」与「MISS/fail_closed 语义」上未收严导致，属我方职责，现裁定落定并已修复：

| 缺口 | 裁定结论 | 修复文件 |
| --- | --- | --- |
| ① 来源字段接受空串/纯空白 | 成立，收严为非空语义 | `src/schemas/evidence.py` |
| ② Route C 真实 MISS 被置 fail_closed 阻断 BioTransformer fallback | 成立，区分 MISS 与真失败 | `src/nodes/reaction_node.py` + `src/graph.py` |
| ③ 空/空白酶 UID 误标 MATCHED | 成立，过滤脏 UID | `src/nodes/multi_step_bridge_node.py` |

---

## 二、三项缺口裁定

### ① 来源字段（source_tag/source_tool）接受空串与纯空白

- **根因**：`CandidateReaction` 的 `source_tag`/`source_tool` 声明为 `str` 且无默认值（Pydantic 层面的「必填」，缺参即报错），但 Pydantic 的 `str` 类型对空串 `""` 与纯空白 `"   "` 照单全收，此前未加「非空」语义校验。
- **裁定**：T6-R3 裁定 3 的「强制非空」的完整语义必须包含拒绝空串与纯空白，而不只是拒绝缺参。
- **修复**：新增 `field_validator`，`source_tag`/`source_tool` 为 `""` 或纯空白时构造即抛 `ValidationError`。
- **验证**：`CandidateReaction(..., source_tag="", ...)` 与 `source_tag="   "`、`source_tool=""`、`source_tool="\t \n"` 均抛异常（新增 4 项断言用例）。

### ② Route C 真实 MISS 被置 fail_closed 并直接结束

- **根因（两处）**：
  1. `reaction_node` 把「检索正常完成但无相似反应命中」这一合法 MISS 当成失败，返回 `{"error": ..., "fail_closed": True}`；
  2. `route_after_reaction` 的 `if state.fail_closed or state.error:` 分支内再判 `not state.fail_closed` 恒为 False，属不可达死支，导致 M5 模式无论如何都走 `end`，无法进入 `predict` fallback。
- **裁定**：MISS 是合法 fallback 触发条件，不是失败；仅「上游故障 / 检索工具异常」才置 fail_closed。M5 模式下无候选反应必须走 BioTransformer ENVMICRO 预测 fallback（T6-R3 裁定 2）。
- **修复**：
  - `reaction_node`：MISS 不再置 `fail_closed`/`error`，返回空候选 + `retrieval_miss` 证据（保留 `reaction_task_id` 锚定键）；
  - `route_after_reaction`：语义修正为「fail_closed/error → end；M5 且无候选 → predict；其余 → pool」。
- **验证**：MISS 输出 `fail_closed is not True`、无 `error`、证据含 `retrieval_miss`；`route_after_reaction` 在 M5 空候选下返回 `"predict"`、fail_closed 下返回 `"end"`（新增 3 项断言用例）。

### ③ 空/空白酶 UID 被接受并将步骤标为 MATCHED

- **根因**：`apply_step_enzyme_matches` 以 `if uids` 判断是否有酶，`uids = ["", " "]` 时列表非空即判真，误标 `MATCHED`，脏 UID 直接写入 `matched_enzyme_uids`。
- **裁定**：空串/纯空白不是有效酶 UID，必须过滤后再判定 MATCHED/UNMATCHED，且 `matched_enzyme_uids` 只保留有效 UID。
- **修复**：先 `strip` 并过滤空串/纯空白 UID，再判定并回填。
- **验证**：全空白 UID → `UNMATCHED_ENZYME` 且 `matched_enzyme_uids == []`；混合 UID（含空白）→ `MATCHED` 且仅保留 `["uid-1"]`（新增 2 项断言用例）。

---

## 三、回归测试与下发

- 回归覆盖：`tests/test_t6r3_contract_decisions.py` 新增 `TestGap1/TestGap2/TestGap3` 共 9 项用例，全套测试 **28 passed**（含既有六项裁定回归）。
- 下发方式：三项修复与回归测试随本 commit 推送至权威库 `depending` 的 `main` 分支，commit message 标识为 `fix(contract): T6-R3 新 base smoke 三项 production 合同缺口修复`。
- 你方职责：**无**。仅需在本修复 commit 上复核三项 smoke 检查由 FAIL 转 PASS，之后即可启动完整 T6。

---

## 四、红线约束（沿用并重申）

- 不改写我未授权拓扑。
- 不把图外 reattach 写成图内连续通过。
- 不把来源空串/纯空白视为来源保留。
- 不把 MISS 当失败、不把脏酶 UID 当匹配。