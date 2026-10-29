# 终裁请求 — ppv1-criteria-v2 P1+P2 修复件（正链 Codex，2026-10-14）

> 本文件=可直接粘贴给 Codex 的完整提示词（自包含）。建议粘贴到
> 上一轮判据级复审会话（会话 id `01a13833-22e2-7e02-b832-08b22b6bda26`，
> 上下文连续）；若开新会话同样可用。

---

继续我们上一轮的 ppv1-criteria-v2 判据级复审（若你是新会话：读 docs/POLLUTANT_PATHWAY_CRITERIA_V2_CODEX_REVIEW_2026-10-14.md 补上下文）。你之前判了**不放行**：P1=官方 S4→评测首次消费接受已损坏的权威 state（cn 身份依赖未闭合），P2=预注册要求的批级 tier 单归属计数缺项。

现在修复件已提交：**commit `7e7855c`**（v43 仓 /Volumes/CC/Enzyme_Agent/dependingv43，本地未 push）。请做终裁。

修复内容（交付书 docs/POLLUTANT_PATHWAY_CRITERIA_V2_P1FIX_DELIVERY_2026-10-14.md）：
1. **P1**：`build_native_result` 首次消费闭合（native_result.py:93 `_validate_native_state_rows`，调用点 :243）——语义块×出现块逐对拼回完整 dict 后调既有 `ChemicalState.from_dict`（单一验证源，与 writer/from_dict/audit 同源，零新判据）；坏源 state 结构化拒绝（`native_result_state_corrupt`，底层 `state_fact_rederivation_mismatch` detail 保全），零出现记录 `native_result_state_unverifiable` fail-closed。入口矩阵 8 个全列（docs/review_evidence/criteria_v2_p1fix_2026-10-14/entry_matrix_and_closure.md）。
2. **P2**：逐边 `criteria_v2_tier_counts`（evaluation.py:1672）+ 批级 `tier_counts`（两 tier 计数，批级=逐边和）。

验证链（你之外的独立验证已完成）：
- 主会核对：负控恰在首次消费拒绝且链截断（你的验收原文逐字满足）、合法正控 8 步全过；
- 通道 C（tokeasy）复审：**放行 v2 生效**（P1/P2 清零、独立复跑 4 关键用例全过、v1 双树字节不变哈希全等）——报告 docs/POLLUTANT_PATHWAY_CRITERIA_V2_CODEX_REVIEW_P1FIX_2026-10-14.md（注意：备用通道结论不替代你的终裁权）。

请做的事：
1. 核对修复代码（native_result.py/evaluation.py + 新测试 4 件）与你的 P1 验收标准（"坏源 state 在原生构建或官方首次读取/评分消费处拒绝+合法 state 正控+相同身份事实校验共用现有源"）；
2. 可自行复跑探针/测试验证（工作仓在 /Volumes/CC/Enzyme_Agent/dependingv43；python 用 ~/miniconda3/envs/depending43/bin/python）；
3. 给你上一轮报告（docs/POLLUTANT_PATHWAY_CRITERIA_V2_CODEX_REVIEW_2026-10-14.md）补正式收尾，并给**终判定三选一：放行（v2 生效）/有条件放行（列条件）/不放行（列 P1）**；
4. 终裁报告落 docs/ 下（命名建议 POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_2026-10-14.md）。

纪律（不变）：只新增你的报告与证据目录（docs/review_evidence/ 下自建）；不改 src/tests/既有 docs/AGENTS.md；不访问金标/题面（questions.jsonl、reference_graphs/、metrics 逐题内容、gitignored reports 逐题数据）；封存 run 不进；不 git 提交不 push；不调用外部模型。报告证据带文件:行号或命令输出。

---

## 附：如走终端续会话（可选）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
CODEX=/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex
"$CODEX" exec resume 01a13833-22e2-7e02-b832-08b22b6bda26 \
  --dangerously-bypass-approvals-and-sandbox \
  -o /tmp/codex_v2_final.txt "$(cat docs/REVIEW_REQUEST_CRITERIA_V2_P1FIX_FINAL_2026-10-14.md | sed -n '/^继续我们/,/^纪律（不变）/p')"
```
（sed 段取提示词主体；或直接把上面分隔线之间的正文粘贴到 App 会话。）
