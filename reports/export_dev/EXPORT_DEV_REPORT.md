# v4.3 第四阶段:dev 20 路真实模型批跑、冻结导出与对照报告

> 生成:`scripts/build_dev_report.py` + `scripts/render_export_dev_report.py`(确定性渲染,零 LLM);批次身份 sha256 前 16 位 `c366e72412daa232`。

## 0. 结论速览

- 批次:c366e724 / {'max_depth': 6, 'max_expansions': 40, 'max_frontier_width': 3, 'max_llm_calls': 42, 'max_proposals': 40}
- 模型:`ZHIPU/GLM-5.3-Flash`(provider=openai_compatible,request_params={"reasoning_effort": "max"},timeout=300.0s)
- **cn 主口径**:step hit@1=0.3333 hit@3=0.3333 hit@5=0.3333;route_recall=0.5671;gold-leaf reached=0.5746;spurious=0.0000
- **raw_sb 对照**:hit@1=0.3333 hit@5=0.3333;recall=0.5671;spurious=0.0000
- S/M/D 分层(cn hit@5):D=0.3077, M=0.3261, S=0.4054
- API:issued=48,响应=48,孤儿=0,429=0,传输失败=18;tokens in/out=318181/267147(cache 30784,思考 242232)
- 估算费用:unknown CNY(口径:known-usage portion priced at help.aliyun.com/zh/model-studio/glm-5-3-flash-by-zhipu @ 2026-09-25; 18 attempt(s) without usage (timeout/transport/orphan) remain unknown)

## 1. 协议限定(必随数字外传)

- Corpus-graph assembly: every gold edge carries its own btid#reac_id evidence, but whole-route experimental validity is NOT verified (A->B and B->C may come from different experiments). Mirrors how the engine consumes the same data.
- Public EAWAG/enviPath data may be in the model's pretraining corpus, and the v4.3 retrieval assets share provenance with the dev gold routes; dev metrics measure path/ranking performance on this benchmark, NOT environmental generalization.
- External 298 single-step results are a different metric class and must not be merged into pathway percentages.

## 2. 逐路线状态

| route_id | run_id | 停止原因 | 答卷类型 | 失败原因 |
|---|---|---|---|---|
| pb_0002 | dev_c366e724_pb_0002 | awaiting_prediction | partial |  |
| pb_0065 | dev_c366e724_pb_0065 | awaiting_prediction | partial |  |
| pb_0074 | dev_c366e724_pb_0074 | awaiting_prediction | partial |  |
| pb_0117 | dev_c366e724_pb_0117 | awaiting_prediction | partial |  |
| pb_0130 | dev_c366e724_pb_0130 | awaiting_prediction | partial |  |
| pb_0201 | dev_c366e724_pb_0201 | awaiting_prediction | partial |  |
| pb_0221 | dev_c366e724_pb_0221 | completed | full |  |
| pb_0241 | dev_c366e724_pb_0241 | awaiting_prediction | partial |  |
| pb_0253 | dev_c366e724_pb_0253 | awaiting_prediction | partial |  |
| pb_0276 | dev_c366e724_pb_0276 | awaiting_prediction | partial |  |
| pb_0313 | dev_c366e724_pb_0313 | awaiting_prediction | partial |  |
| pb_0316 | dev_c366e724_pb_0316 | completed | full |  |
| pb_0324 | dev_c366e724_pb_0324 | completed | full |  |
| pb_0349 | dev_c366e724_pb_0349 | completed | full |  |
| pb_0370 | dev_c366e724_pb_0370 | awaiting_prediction | partial |  |
| pb_0401 | dev_c366e724_pb_0401 | completed | full |  |
| pb_0410 | dev_c366e724_pb_0410 | awaiting_prediction | partial |  |
| pb_0447 | dev_c366e724_pb_0447 | awaiting_prediction | partial |  |
| pb_0459 | dev_c366e724_pb_0459 | awaiting_prediction | partial |  |
| pb_0471 | dev_c366e724_pb_0471 | awaiting_prediction | empty |  |

## 3. 逐路线诊断(描述性,非冻结评测器原生切片)

### pb_0002

- stop_reason=awaiting_prediction;事件=4({"recorded_reaction": 4});展开=5;最大深度=4
- 失分归因:{"parent_never_reached": 9, "retrieved_not_committed": 4}
- 检索池诊断命中(非正式分数):top5={'hits': 14, 'n': 17},全池={'hits': 17, 'n': 17}

### pb_0065

- stop_reason=awaiting_prediction;事件=3({"recorded_reaction": 3});展开=4;最大深度=3
- 失分归因:{"parent_never_reached": 27, "retrieved_not_committed": 5}
- 检索池诊断命中(非正式分数):top5={'hits': 15, 'n': 35},全池={'hits': 21, 'n': 35}

### pb_0074

- stop_reason=awaiting_prediction;事件=2({"recorded_reaction": 2});展开=3;最大深度=2
- 失分归因:{}
- 检索池诊断命中(非正式分数):top5={'hits': 2, 'n': 2},全池={'hits': 2, 'n': 2}

### pb_0117

- stop_reason=awaiting_prediction;事件=2({"recorded_reaction": 2});展开=3;最大深度=2
- 失分归因:{}
- 检索池诊断命中(非正式分数):top5={'hits': 2, 'n': 2},全池={'hits': 2, 'n': 2}

### pb_0130

- stop_reason=awaiting_prediction;事件=4({"recorded_reaction": 4});展开=5;最大深度=4
- 失分归因:{}
- 检索池诊断命中(非正式分数):top5={'hits': 4, 'n': 4},全池={'hits': 4, 'n': 4}

### pb_0201

- stop_reason=awaiting_prediction;事件=3({"recorded_reaction": 3});展开=4;最大深度=3
- 失分归因:{"parent_never_reached": 14, "retrieved_not_committed": 3}
- 检索池诊断命中(非正式分数):top5={'hits': 6, 'n': 20},全池={'hits': 10, 'n': 20}

### pb_0221

- stop_reason=completed;事件=6({"recorded_reaction": 6});展开=6;最大深度=6
- 失分归因:{"parent_never_reached": 13, "retrieved_not_committed": 6}
- 检索池诊断命中(非正式分数):top5={'hits': 16, 'n': 25},全池={'hits': 25, 'n': 25}

### pb_0241

- stop_reason=awaiting_prediction;事件=4({"recorded_reaction": 4});展开=5;最大深度=4
- 失分归因:{"parent_never_reached": 5, "retrieved_not_committed": 6}
- 检索池诊断命中(非正式分数):top5={'hits': 14, 'n': 15},全池={'hits': 15, 'n': 15}

### pb_0253

- stop_reason=awaiting_prediction;事件=3({"recorded_reaction": 3});展开=4;最大深度=3
- 失分归因:{"retrieved_not_committed": 1}
- 检索池诊断命中(非正式分数):top5={'hits': 4, 'n': 4},全池={'hits': 4, 'n': 4}

### pb_0276

- stop_reason=awaiting_prediction;事件=1({"recorded_reaction": 1});展开=2;最大深度=1
- 失分归因:{"parent_never_reached": 12, "parent_not_expanded": 2, "retrieved_not_committed": 4}
- 检索池诊断命中(非正式分数):top5={'hits': 8, 'n': 19},全池={'hits': 19, 'n': 19}

### pb_0313

- stop_reason=awaiting_prediction;事件=3({"recorded_reaction": 3});展开=4;最大深度=3
- 失分归因:{}
- 检索池诊断命中(非正式分数):top5={'hits': 3, 'n': 3},全池={'hits': 3, 'n': 3}

### pb_0316

- stop_reason=completed;事件=6({"recorded_reaction": 6});展开=6;最大深度=6
- 失分归因:{"parent_never_reached": 1, "parent_not_expanded": 1, "retrieved_not_committed": 1}
- 检索池诊断命中(非正式分数):top5={'hits': 7, 'n': 9},全池={'hits': 8, 'n': 9}

### pb_0324

- stop_reason=completed;事件=6({"recorded_reaction": 6});展开=6;最大深度=6
- 失分归因:{"parent_not_expanded": 1}
- 检索池诊断命中(非正式分数):top5={'hits': 6, 'n': 7},全池={'hits': 6, 'n': 7}

### pb_0349

- stop_reason=completed;事件=6({"recorded_reaction": 6});展开=6;最大深度=6
- 失分归因:{}
- 检索池诊断命中(非正式分数):top5={'hits': 6, 'n': 6},全池={'hits': 6, 'n': 6}

### pb_0370

- stop_reason=awaiting_prediction;事件=2({"recorded_reaction": 2});展开=3;最大深度=2
- 失分归因:{}
- 检索池诊断命中(非正式分数):top5={'hits': 2, 'n': 2},全池={'hits': 2, 'n': 2}

### pb_0401

- stop_reason=completed;事件=6({"recorded_reaction": 6});展开=6;最大深度=6
- 失分归因:{"parent_not_expanded": 1}
- 检索池诊断命中(非正式分数):top5={'hits': 6, 'n': 7},全池={'hits': 6, 'n': 7}

### pb_0410

- stop_reason=awaiting_prediction;事件=2({"recorded_reaction": 2});展开=3;最大深度=2
- 失分归因:{"parent_never_reached": 3, "retrieved_not_committed": 4}
- 检索池诊断命中(非正式分数):top5={'hits': 8, 'n': 9},全池={'hits': 9, 'n': 9}

### pb_0447

- stop_reason=awaiting_prediction;事件=1({"recorded_reaction": 1});展开=2;最大深度=1
- 失分归因:{"parent_never_reached": 3, "retrieved_not_committed": 4}
- 检索池诊断命中(非正式分数):top5={'hits': 5, 'n': 8},全池={'hits': 7, 'n': 8}

### pb_0459

- stop_reason=awaiting_prediction;事件=5({"recorded_reaction": 5});展开=6;最大深度=5
- 失分归因:{"retrieved_not_committed": 1}
- 检索池诊断命中(非正式分数):top5={'hits': 6, 'n': 6},全池={'hits': 6, 'n': 6}

### pb_0471

- stop_reason=awaiting_prediction;事件=0({});展开=1;最大深度=0
- 失分归因:{"parent_never_reached": 3, "parent_not_expanded": 4}
- 检索池诊断命中(非正式分数):top5={'hits': 5, 'n': 7},全池={'hits': 7, 'n': 7}

## 4. 历史基线对照(同 dev 20 路、同冻结评测器;口径不同,仅供参考)

### v41_llm_mc

- 状态:scored_with_caveats;答卷 8 行(缺 12 行按空计分)
- cn hit@1=0.1111 hit@5=0.1643 recall=0.2007 spurious=0.2747
- 注:historical arm: different model/architecture/budget regime; reference only, NOT directly comparable

### v42_hybrid_fix

- 状态:scored_with_caveats;答卷 10 行(缺 10 行按空计分)
- cn hit@1=0.2077 hit@5=0.3527 recall=0.3259 spurious=0.4466
- 注:historical arm: different model/architecture/budget regime; reference only, NOT directly comparable

### v43_depth3_r2

- 状态:scored_with_caveats;答卷 20 行(缺 0 行按空计分)
- cn hit@1=0.2271 hit@5=0.2271 recall=0.4365 spurious=0.0000
- 注:v4.3 supplementary ablation: same model/architecture, smaller budget regime (max_depth=3/max_expansions=24)

## 5. 基线可比性声明

- v4.1/v4.2 dev 臂模型为 deepseek-v4.1-flash(temperature=0,非思考),
  预算为 max_depth=12/max_expands=50/max_nodes=200;v4.3 本轮为
  ZHIPU/GLM-5.3-Flash(仅思考,reasoning_effort=max),预算为 max_depth=6/max_expansions=40;
  架构(v4 引擎三段式 vs v4.3 LangGraph 逐路径检索-裁决-验证)与
  排序语义均不同 —— 数字并列仅作参考,不构成提升/下降百分比。
  v43_depth3_r2 为同模型同架构的小预算(depth 3)消融,供预算敏感性
  参考;其余 v41/v42 臂不可直接比。

## 6. worker 进程与时间证据(协调器日志摘录)

- spawn 事件 20 次(20 路一次派发,无失败重试);
  全部 20 个 worker 均有唯一终态,失败恢复 0 次。

- `2026-09-24T18:42:19+0000 spawn pb_0002 pid=178377 run_id=dev_c366e724_pb_0002`
- `2026-09-24T18:42:19+0000 spawn pb_0065 pid=178378 run_id=dev_c366e724_pb_0065`
- `2026-09-24T18:42:19+0000 spawn pb_0074 pid=178379 run_id=dev_c366e724_pb_0074`
- `2026-09-24T18:42:19+0000 spawn pb_0117 pid=178380 run_id=dev_c366e724_pb_0117`
- `2026-09-24T18:42:19+0000 spawn pb_0130 pid=178381 run_id=dev_c366e724_pb_0130`
- `2026-09-24T18:42:19+0000 spawn pb_0201 pid=178382 run_id=dev_c366e724_pb_0201`
- `2026-09-24T18:42:19+0000 spawn pb_0221 pid=178383 run_id=dev_c366e724_pb_0221`
- `2026-09-24T18:42:19+0000 spawn pb_0241 pid=178384 run_id=dev_c366e724_pb_0241`
- `2026-09-24T18:42:19+0000 spawn pb_0253 pid=178385 run_id=dev_c366e724_pb_0253`
- `2026-09-24T18:42:19+0000 spawn pb_0276 pid=178386 run_id=dev_c366e724_pb_0276`
- `2026-09-24T18:42:19+0000 spawn pb_0313 pid=178387 run_id=dev_c366e724_pb_0313`
- `2026-09-24T18:42:19+0000 spawn pb_0316 pid=178388 run_id=dev_c366e724_pb_0316`
- `2026-09-24T18:42:19+0000 spawn pb_0324 pid=178389 run_id=dev_c366e724_pb_0324`
- `2026-09-24T18:42:19+0000 spawn pb_0349 pid=178390 run_id=dev_c366e724_pb_0349`
- `2026-09-24T18:42:19+0000 spawn pb_0370 pid=178391 run_id=dev_c366e724_pb_0370`
- `2026-09-24T18:42:19+0000 spawn pb_0401 pid=178392 run_id=dev_c366e724_pb_0401`
- `2026-09-24T18:42:19+0000 spawn pb_0410 pid=178393 run_id=dev_c366e724_pb_0410`
- `2026-09-24T18:42:19+0000 spawn pb_0447 pid=178394 run_id=dev_c366e724_pb_0447`
- `2026-09-24T18:42:19+0000 spawn pb_0459 pid=178395 run_id=dev_c366e724_pb_0459`
- `2026-09-24T18:42:19+0000 spawn pb_0471 pid=178396 run_id=dev_c366e724_pb_0471`
- `2026-09-24T18:43:39+0000 worker done pb_0324 exit=0 stop=completed`
- `2026-09-24T18:44:09+0000 worker done pb_0349 exit=0 stop=completed`
- `2026-09-24T18:44:09+0000 worker done pb_0401 exit=0 stop=completed`
- `2026-09-24T18:45:29+0000 worker done pb_0313 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:45:49+0000 worker done pb_0316 exit=0 stop=completed`
- `2026-09-24T18:47:29+0000 worker done pb_0074 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:49:59+0000 worker done pb_0459 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:50:09+0000 worker done pb_0130 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:50:59+0000 worker done pb_0447 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:51:49+0000 worker done pb_0002 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:51:59+0000 worker done pb_0253 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:52:39+0000 worker done pb_0201 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:53:19+0000 worker done pb_0117 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:56:29+0000 worker done pb_0241 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:58:20+0000 worker done pb_0471 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:58:30+0000 worker done pb_0370 exit=0 stop=awaiting_prediction`
- `2026-09-24T18:59:50+0000 worker done pb_0065 exit=0 stop=awaiting_prediction`
- `2026-09-24T19:00:50+0000 worker done pb_0410 exit=0 stop=awaiting_prediction`
- `2026-09-24T19:01:40+0000 worker done pb_0276 exit=0 stop=awaiting_prediction`
- `2026-09-24T19:22:21+0000 worker done pb_0221 exit=0 stop=completed`

## 7. 事故与恢复记录(如实披露)

- 本次任务执行期间存在**两个并发实施会话**共享同一本地仓;Chenyu 上
  曾同时出现三个批跑协调器(本仓 batch_dev_v1、对方仓 devbatch_v43r1/r2),
  共享同一 DashScope 主账号额度。本会话发现后立即 pkill 停掉自己的
  batch_dev_v1(12/20 终态,已花调用极少量),保留产物供审计;最终
  正式批次 = 本仓 batch_dev_v2(修复后代码 + depth-6 冻结配置)。
- batch_dev_v1 与对方 r1 各有 6 条路线 worker 失败,根因相同:
  `predicted_evidence_id` 跨迭代泄漏(LangGraph State 键残留)→
  下一条确定性 recorded 路径误入提案卡分支 KeyError('proposed_card')。
  修复 = select_frontier 进入新路径前清空全部迭代引用 + 提案卡缺失
  改结构化 NodeStateError;修复后 batch_dev_v2 20/20 零 worker 失败。
- 18 次 HTTP 尝试 300s 超时(thinking 模型偶发长思考;无 429/403)。
  超时后节点层按 attempt 重试并逐次落盘;超时尝试的用量提供者未返回,
  费用账中如实标注 unknown。timeout=300s 是下一个明确的调参杠杆。
- 烟测与正式批次调用分开记录(smoke/dashscope_smoke.json,1 次调用)。

## 8. 已知限制与冻结候选

- **冻结候选** = 本报告批次配置(depth 6 / expansions 40 / width 3 /
  llm 42 / proposals 40 / timeout 300s / reasoning_effort=max);
  选择依据见 budget_rationale(dev 深度分布覆盖)与本轮实测。
- 15/20 路停于 awaiting_prediction:竞争 recorded 需模型裁决的路径上,
  模型 hold/abstain 或超时重试耗尽后显式停留(不假成功);答卷如实
  截断,不抬高分数。提高 timeout 与裁决重试是下一步杠杆。
- spurious_rate=0.0:答卷只含已提交事实,无模型杜撰产物进入答卷。
- 检索池诊断命中率(全池)远高于正式 hit(如 pb_0065 全池 21/35 vs
  答卷命中 0/35):主要失分在"检索到但未提交"与"父未到达",即预算/
  裁决/停留行为,而非检索覆盖 —— 与失分归因分桶一致。

## 6. 批次配置冻结

```json
{
  "batch_cost_cap_cny": 30.0,
  "budget_rationale": "dev 20 路金标深度分布 2:4,3:4,4:3,5:2,6:2,7:4,8:1;max_depth=6 覆盖 15/20 条路线的完整深度预算(leaf-reached 的结构性上限),expansions=40 为检索预算上限;LLM 调用上限随展开派生(+2)。v4.1/v4.2 历史臂用 depth=12/expands=50 且模型为 deepseek-v4.1-flash,口径不同,比较时须标注。",
  "budgets": {
    "max_depth": 6,
    "max_expansions": 40,
    "max_frontier_width": 3,
    "max_llm_calls": 42,
    "max_proposals": 40
  },
  "capacity": {
    "memory_gb_per_worker": 3.0,
    "min_free_disk_gb": 20.0
  },
  "export_policy_overrides": {},
  "llm_timeout_s": 300.0,
  "max_http_retries": 4,
  "max_parallel": 20,
  "max_worker_respawns": 2,
  "model_request_params": {
    "reasoning_effort": "max"
  },
  "poll_interval_s": 10.0,
  "provider_price_snapshot": {
    "cache_read_cny_per_m": 0.23,
    "checked": "2026-09-25",
    "input_cny_per_m": 0.8,
    "model_id": "ZHIPU/GLM-5.3-Flash",
    "output_cny_per_m": 2.8,
    "region": "cn-beijing",
    "rpm": 200,
    "source": "help.aliyun.com/zh/model-studio/glm-5-3-flash-by-zhipu",
    "thinking_billed_as_output": true,
    "tpm": 3000000
  },
  "rate": {
    "acquire_timeout_s": 600.0,
    "cooldown_cap_s": 60.0,
    "max_calls": 1000,
    "rpm": 180,
    "tpm": 2700000
  },
  "worker_wall_clock_cap_s": 28800
}
```
