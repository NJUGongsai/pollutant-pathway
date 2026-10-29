# T-I C8 站点代理停跑 + P2 token 门停点（2026-10-21 早）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文只记工程状态，不产生成绩。
> 状态：**T-I 与 P2 均停在付费批之前；旧批/证据 100% 保全；无残留作业。**

## 1. T-I：站点代理两次 soak 失败，按代决停

| 轮 | 时间（北京） | 计算节点 | 登录经代理 | 判定 |
|---|---|---:|---:|---|
| soak 1（job 47016807） | 2026-10-21 05:46–05:58 | **8/12** | 1/3 | SOAK-RED |
| soak 2（job 47026973） | 2026-10-21 08:07–08:19 | **1/12** | 未达门槛 | SOAK-RED |

- 失败均为 `curl 28` 连代理 `10.15.2.115:3000` 超时（~7s）；直连 dashscope 返 401，API 层正常。
- **结论：站点代理间歇→大面积不可达，不是 GLM/DeepSeek、不是代码、不是判分。**
- qwen3.8max 代 Codex 代决（`docs/T_I_C8_STOP_QWEN_DECISION_2026-10-21.md`）：选 **B2 新批/新时间窗**；
  连续两轮 soak 失败 ⇒ **停并报 CC**。本轮已触发，**不再重试**。

### 已保全/未发生

- 旧批：`~/ppv1_hpc/batch/t_i_298_20261020_{glm,deepseek}` 原样；`stop.json` 未改；
  未建任何新批；`squeue` 无残留。
- full 未发；只花 C5 两次预检 + smoke 少量调用（GLM 2 题、DeepSeek 12 题量级），金额 unknown。
- 旧批 run：GLM smoke2 1/2（1 题 timeout）；DeepSeek smoke10 3 题 timeout；均按 TI-F1 硬停。

### 恢复条件（下次会话照此）

1. 计算节点 **12/12** 探测成功（HTTP 401 + connect<3.5s，60s 间隔，window≥720s）+ 登录经代理 3/3 + 直连对照 401。
2. 绿后 30min 内过官方 C3 netcheck（`COMPLETED 0:0` + `NETCHECK-PASS`）。
3. 按 qwen B2 执行：新 batch_tag/新批根/新协调目录；旧两根入 immutable；config 唯一件改 + 锁重算
   （预期 13/14 不变）+ C2–C5 新窗重跑 + 两臂 build/身份（新指纹需 qwen/Codex 确认件）+
   prepare（P2 计数 531/242/298 等照旧）+ 发车 + monitor（TI-F1 阈值零改动）。
4. 同批 `--resume` 不采用（需移 4 个终态 case 且用掉唯一重投；qwen 已裁 B2）。

## 2. P2：真实池 token 门 FAIL，冻结设计需修订

- 全 298 题真实池预测量（当前 tokenizer `87a7830d…`，零模型/零金标）：
  **批合计 +8.2165% 过**；**逐题 194/298 过、104 题超限、最大 +64.1263%**（`RXNG_1eba3a0`，8 候选）。
- 分桶：0/1 候选 0 超；2 候选 21/57 超；3 候选 47/53 超；4 候选 24/24 超；5 候选 8/8 超；6+ 全超。
- qwen 代决（`docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md`）：
  逐题例外**不批**；锚缩放投影不接受；**全 298 真实池+最终 tokenizer 预测量为付费硬前置**。
- 结论：**冻结 v2 证据卡在真实池上过不了 token 门**，需要设计级修订（例如按候选取 top-K 证据、
  按题聚合证据、或多候选走紧凑 schema），属设计变更，须新冻结/评审；本轮停在付费批前。
- 证据：`docs/T_P2_TOKEN_PREMEASURE_298_2026-10-21.md` + `docs/review_evidence/p2_token_298_2026-10-21/`。

## 3. 下一步（建议）

1. **T-I**：等站点代理恢复 → 重跑 soak → 绿后按 B2 自动发新批；不碰旧批。
2. **P2**：先由 QwenReviewer/CC 裁设计修订方向（token 门是设计硬门）；修订后重测全 298，
   最终 tokenizer 在 T-I 选模型后复测。
3. 不 push 旧批/证据；金额等账单回填，不估算。

## 4. 关键文件

- T-I 停点：`~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261020/stop.json`
- C8 诊断：`docs/review_evidence/ti_c0_c5_2026-10-21/c8_netprobe_*`、`c8_soak_*`
- qwen 代决：`docs/T_I_C8_STOP_QWEN_DECISION_2026-10-21.md`
- P2 token：`docs/T_P2_TOKEN_PREMEASURE_298_2026-10-21.md`
- P2 qwen：`docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md`、
  `docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md`