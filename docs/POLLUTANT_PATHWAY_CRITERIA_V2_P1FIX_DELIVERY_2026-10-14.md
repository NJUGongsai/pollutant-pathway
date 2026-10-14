# 交付书 — criteria-v2 P1+P2 修复（回修轮，2026-10-14）

> 执行：单个实施子代理（评审-回修自动循环轮内①段）。
> 任务书：`docs/TASK_CRITERIA_V2_P1_FIX_2026-10-14.md`（有限范围）。
> 基线 HEAD：`0ba764f121af8cbe001cad9442f2799cd108e21f`（本轮改动在其
> 工作树上，随轮本地 commit，不 push）。
> 证据目录：`docs/review_evidence/criteria_v2_p1fix_2026-10-14/`。

## 一句话结论

P1（官方链接受已损坏权威 state）在**原生构建**这个官方链首次消费点
闭合——坏 state 被结构化拒绝，验证来源就是既有的
`ChemicalState.from_dict` 事实重算（零新判据）；P2（预注册要求的两
tier 批级计数）补齐 `tier_counts`；合法数据全链字节不变，全量测试
零翻转。

## 一、改了什么（4 文件，+289/-2）

| 文件 | 改动 | 行数 |
|---|---|---|
| `src/pathway_v43/pollutant/native_result.py` | 新增 `_validate_native_state_rows`（states 语义块 × appearances 出现块逐对拼回完整 dict 过 `ChemicalState.from_dict`；坏源 ⇒ `NativeResultContractError{kind: native_result_state_corrupt}`，底层 `state_fact_rederivation_mismatch` detail 原样保全；零出现记录 ⇒ `native_result_state_unverifiable` fail-closed）；`build_native_result` 加载 states/appearances 后调用（1 行）；import +1 行 | +67 |
| `src/pathway_v43/pollutant/evaluation.py` | P2：`match_reference_edges` 每边累加双 tier 计数（双键恒在=完备二分），v2 时 entry 附 `criteria_v2_tier_counts`（v1 零新键）；批级 `criteria_v2` 块新增 `tier_counts`（汇总自逐边键 + 非法 tier 断言） | +31/-2 中约 29 净增 |
| `tests/test_ppv1_s4b_export.py` | P1 测试 ×2：单点腐蚀负控（结构化拒绝 + 底层 kind 断言）+ 零出现记录 fail-closed 边界；含合法正控（digest 可复现、state 进聚合载荷） | +87 |
| `tests/test_ppv1_criteria_v2_exemption.py` | P2 测试 ×2：逐边两 tier 计数（豁免边 v1_exempt=1 / 无中生水边 not_exempt=1 / v1 零新键）+ 真实链批级闭合（批级 == 逐边和；v1 全无新键） | +106 |

## 二、为什么这个闭合点（详见证据目录 entry_matrix_and_closure.md）

按返工教训 §1 先列全 8 个入口（writer / from_dict / audit / 原生构建 /
导出 / 默认 reader / 评分消费 / 运行期+endpoint），逐一标明消费什么
身份事实：

- writer、from_dict、audit **本来就闭合**（Codex 探针的 from_dict
  对照也证实）——缺口只在**原生构建**：`SELECT * FROM states` raw
  SQL 原样聚合，零事实校验；
- `build_native_result` 是官方链（read_endpoint → build → persist →
  export → reader → evaluator）对持久 states 权威的**第一次消费**，
  后续每一步的 state 载荷都来自它——一处闭合全链受益，符合 Codex
  验收"原生构建**或**官方首次读取/评分消费处被拒绝（选最小侵入）"；
- 验证**共用单一来源**：新代码只做"语义块+出现块拼回完整 state dict
  后调 `ChemicalState.from_dict`"（与恢复入口/writer/audit 同源
  `validate_state_object`），逐行核对过 writer `_verify_state_payload_facts`
  与 `validate_state_object` 事实重推导等价 ⇒ 合法数据零误拒；
- **判据化学面零改动**：豁免清单/三谓词/完备二分/单归属断言原样；
  生成侧零改动；旧批零回写。

## 三、红绿证据（全部在证据目录，可复跑）

| 验收项 | 结果 | 证据 |
|---|---|---|
| P1 负控（Codex 探针同构：合成 run + O₂ state 单点腐蚀 cn O=O→O） | **拒绝**：`build_native_result` 抛 `NativeResultContractError{kind: native_result_state_corrupt, state_error_kind: state_fact_rederivation_mismatch, mismatches.cn_identity: {provided: O, rederived: O=O}}`；persist/export/reader/evaluator 不再被触达；from_dict 对照同拒 | `p1fix_source_corruption_output.json`（+`_probe.py`/`_command.json`/stderr；合成 run 落 /tmp，证据目录零 DB 写入） |
| P1 合法正控 | 同链不腐蚀：起始导出首消费 ok；合法 O₂ state 落账后 build/persist/export/默认 reader/默认 v2 evaluator **全链 ok**（evaluator status=interface_verified_only，与修复前一致） | 同上（正控臂 8 步 ok=true） |
| P2 断言 | 批级 `tier_counts` 两键恒在且单归属闭合（批级 == 逐边 `criteria_v2_tier_counts` 之和）；真实链非零 v2 聚合正控（H₂ 共同产物 → not_exempt=1，兼答兼容性分支"补一个非零 v2 聚合控制"的请求） | 新测试 `test_per_edge_criteria_v2_tier_counts_both_tiers` / `test_batch_criteria_v2_tier_counts_real_chain_closure` |
| 全量 not-slow 零翻转 | **2121 passed / 0 failed / 16 deselected**（基线 2117/0/16 + 新增 4 件；359.57s，EXIT=0） | `full_suite_not_slow.log` |
| 字节不变探针（缺省 v1 零漂移） | **双树全等**：`git archive 0ba764f` 父树 vs 本轮工作树——①公共链探针（start_run 生成一次 → 双树各自 evaluate+score，evaluate/score JSON 与 metrics.json/report.md/report_plain.md 哈希）IDENTICAL；②直连 17 接口用例（异常类型/消息/detail 全等）IDENTICAL | `byte_invariance/{public_native_default_v1_probe.py, parent_output.json, current_output.json, direct17_parent.json, direct17_current.json}` |
| 新增测试 | 4 件全绿（P1 ×2 + P2 ×2） | pytest 输出见交付记录 |

## 四、红线自查

- git add 只含本轮 4 个文件 + 新证据目录 + 本交付书；工作树主窗口的
  活文件（teacher 回复/评审请求/预注册状态翻/任务书/评审报告等）**零
  夹带**（提交前 `git status` 复核）；
- 本地 commit，不 push；
- 金标/题面/封存 run 零触碰（探针与测试全用合成数据，零模型零网络）；
- 判据化学面零改动（diff 可核：evaluation.py 判据函数未动，仅披露
  计数）；s5b_scoring.py 透传不动（块内加键自动带出）。

## 五、全量测试结果

`pytest tests/ -q -p no:cacheprovider -m "not slow"`：
**2121 passed, 16 deselected, 0 failed**（359.57s）。

- 基线口径 2117/0/16 + 本轮新增 4 件 = 2121/0/16，**零翻转**；
- 字节不变探针双树全等（见 §三），P1/P2 的新增键全部 v2 门控，
  缺省 v1 零漂移实证。
