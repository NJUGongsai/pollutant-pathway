# TASK — criteria-v2 P1+P2 修复（Codex 复审不放行项，2026-10-14）

> 派单：主窗口（评审-回修自动循环轮内①段）。执行：单个实施子代理。
> 范围=**有限**：Codex 复审报告的 P1（阻塞）+ P2（放行前应修）。
> 报告全文：`docs/POLLUTANT_PATHWAY_CRITERIA_V2_CODEX_REVIEW_2026-10-14.md`；
> 证据：`docs/review_evidence/criteria_v2_codex_2026-10-14/`。

## 一、P1（必改）：官方链首次消费接受已损坏权威 state

**现象**（Codex 探针 `false_exemption/source_corruption_output.json`）：
SQLite state 的 `cn_identity` 被单点腐蚀（O=O→O，结构/state_id/schema
不动）后：`ChemicalState.from_dict` 正确拒绝
（state_fact_rederivation_mismatch），但官方链
read_endpoint → build_native_result → persist → export → 默认 reader
→ 默认 evaluator **全部接纳**（9 步 ok=true；本次无实证错误分数——
坏 state 未被被评事件引用）。

**入口定位**（Codex 读码，修复时逐一核）：
- `src/pathway_v43/pollutant/native_result.py:77-89,169-176`
  （raw SQL / `_rows_sorted`：不做状态事实重算）
- `src/pathway_v43/pollutant/native_export.py:886-900`
  （graph facts 校验只比当前源内容摘要——坏源重聚合后摘要一致）
- `src/pathway_v43/pollutant/evaluation.py:1311-1327,978-986`
  （`_criteria_state_cn` 等消费声明 cn）

**修复要求**（Codex 验收原文）：
1. 上述坏源 state 在**原生构建或官方首次读取/评分消费处被拒绝**
   （选最小侵入的闭合点——按仓内返工教训 §1，**先列全所有适用入口**
   （build/parse/from_dict/derive/audit/首提/重放入口），标明各入口
   消费什么身份事实；**共用同一验证来源**（ChemicalState 事实重算），
   不在多个入口各写一套判据）；
2. 保持**合法 state 正控**（合法数据零行为差——字节不变纪律延续）；
3. 版本/不支持边界与旧批零回写保持；
4. **判据化学面零改动**（豁免清单/三谓词/完备二分不动——这是
   工程/完整性修复，不是判据变更）。

## 二、P2（必改）：批级 tier 单归属计数缺项

- 预注册 `POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md`
  §五（:63 行附近）要求批级 `criteria_v2` 块含两 tier 计数；
- 实现 `evaluation.py:3225-3244` 只发豁免族计数与 occurrence 计数——
  补 `v1_exempt` / `not_exempt_maintains_partial` 批级计数（机器披露
  字段；单归属不变量已有内部断言，批级补齐输出）；
- `s5b_scoring.py:543-544` 透传不动（块内加键自动带出）。

## 三、验收（实施代理自测，主会话复核）

1. **P1 负控复现**：按 Codex 探针同构（合成 run+单点腐蚀 cn）重跑
   官方链——坏 state 在闭合点被拒（结构化错误，错误类别进现有
   错误语义体系）；探针脚本+输出留证据目录（自建
   `docs/review_evidence/criteria_v2_p1fix_2026-10-14/`）；
2. **合法正控**：同链不腐蚀的合法 state 全通过；既有测试全绿
   （全量 not-slow 零翻转）+ 字节不变探针重跑（缺省 v1 零漂移）；
   （基线口径参考：全量 2117/0/16、G01 delta +16——Codex 兼容性
   分支已独立复验 parent/current 145→161 全绿零翻转，你修复后须
   保持同级零翻转）；
3. **P2 断言**：新测试断言批级块含两 tier 计数且单归属闭合；
4. 新测试（P1 拒绝+合法正控+P2 计数）入库。

## 四、红线

- 只改 src/tests 本轮范围文件 + 新增证据目录与交付书；
- **不得夹带**工作树既有未跟踪/已修改文件（teacher 回复、评审请求、
  预注册状态翻、C/D 任务书、评审报告等是主窗口的活——git add 只加
  你自己改动的文件）；
- 随轮本地 commit（**不 push**）；commit 信息如实写范围与红绿证据；
- 金标/题面/封存 run 零触碰；零模型零网络；
- 判据化学面零改动；生成侧零改动；旧批零回写。

## 五、回传义务

修复文件清单+行数、闭合点选择与入口矩阵（哪个入口验什么）、
P1 负控/合法正控的执行输出摘要、测试红绿（新增 N 件+全量零翻转+
字节不变探针结果）、commit hash、一切偏差如实。
