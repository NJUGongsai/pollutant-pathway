# HIT60 任务书 T1：S1 Phase E 变更集施工（E1 协议 / E2 噪声 / E3 窗口 / E4 模型）

> 状态：待执行。前置：[T0 边界表](TASK_V43_HIT60_S0_BOUNDARY_AND_REVIEW.md) 落盘
> （本任务的唯一合法归因输入）＋ D1/D2 拍板；E4 另依赖 D3（五模型裸测）。
> API 预算 <¥50。依据 [teacher 指导书](TEACHER_PLAN_V43_HIT60_MASTERPLAN_2026-09-29.md) §4 S1。

## 0. 目标与止损门

在冻结 dev 集上逐项配对实验，把"信息已在系统内"的失分（T0 边界表的
L1 排序池 + L2 选错池 + L3 引擎有 agent 无）转化为 hit@1 增益。

**止损门（回路的保险丝）：dev 集累计增益 <+8pp → 停止冲刺，出止损结论，
重估目标或转 S3——不带弱证据去碰 298。**

红线（Phase F 草案 §0 全部继续有效，摘要）：
金标只在运行结束后的独立评分进程读取；不得用 298 逐题信息选规则/权重/阈值/
prompt/特例（I1）；不放宽任何确定性门禁；`ambiguous` 不任选；原始 rule/analog
卡不绕验证占报告位；单变量成臂；预注册先于跑分（I2）；超时/重试/孤儿/usage/
费用全记账，缺 usage 不报总额；跨配置 resume 拒绝。

## 1. F0｜dev 集构建与冻结（D2 拍板后）

1. 来源：BIOSYSMOdb 121 题拆单步 + RHEA/BRENDA 留出拼合（决策 D2；涉陈浩然线
   资产共享，开工前完成知会）。dev 取 50–100 题；与 T2 盲测卷在拼合时一次性
   划开并各自冻结 SHA；与 298 题不交叠。
   **题源资产与核验状态见 [陈浩然回复](REPLY_TO_GONGSAI_V43_D2_ASSET_SHARING_20260929.md)**：
   B1 冻结包（Chenyu 只读，SHA `6858c165…`，121 路径/533 步/460 去重反应）可立即
   作题源；先跑其建议的 **D2 preflight**（B1 533 + RHEA broad-87 + BRENDA 213
   候选的统一去重、方向/规范化/与旧 298 及训练集重叠审计、primary-product 口径），
   报真实可用量后再划 dev/blind；BRENDA 213 有 accession 拆分/表示分歧 bug 不得
   直接并入；新工作目录用其指定的 `v43_hit60_d2_question_assembly_20260929/`；
   许可 CC BY-NC-SA 4.0（署名 BIOSYSMOdb 及原始来源）。
2. **构建纪律（S0 溯源教训，2026-09-29）**：禁止沿用"辅因子/共底物剥离 +
   单底物呈现 + 产物侧全留"的投影口径——共底物若剥离必须显式登记口径，
   且不得剥离主产物；**豁免酰基-CoA 硫酯等 >80 字符长 SMILES 主产物**
   （298 卷曾因该剥离规则误伤 2 题主产物，见
   `reports/phase_s0_hit60/manual_review/gold_convention_registry.md`）；
   多产物并列须显式声明语义（"同步产物清单"还是"备选答案"）并写入登记。
3. **泄漏审计先行**：题面底物/金标 vs v1 检索语料，精确串 + 规范化 CN 双口径；
   审计规则预注册；命中题移出或标 `leaked`（处理规则同时登记）。
4. 金标构建双人确认（I3 同款纪律）；运行输入仅
   `question_id/root_smiles/root_smiles_sha256` 三字段，答案永不进运行侧。
5. 单步预算与 EC298 同口径：`max_depth=1`、`max_expansions=1`、
   `max_frontier_width=5`、`max_llm_calls=3`、`max_proposals=1`、
   `reactant_similar_enabled=false`（类比线封存，任何臂不得打开）。
   评分用正式整串 `cn_identity`、scorer v2 同口径、固定分母、空答留分母。
6. 旧 dev20 多步分数不可作基线（口径差异）；dev20 单步评分器的构建教训
   （根节点一跳语义、6 金标不因宽度 5 裁剪、双臂身份逐字段相等）沿用
   [旧 Phase E 任务书](TASK_V43_EC298_PHASE_E_POST_RETEST.md) §2。

## 2. F0b｜判定规则预注册（先于任何付费调用）

每臂登记并落盘：主终点（dev 配对 cn@1 净赢）、最小有用增益、次级回退上限
（@3/@5 不降、空答率不升、spurious 率不升）、费用/失败上限、停机规则。
50–100 题仍是小样本：逐题四格 + 不确定性一起报，单次抽样不证因果；
hit@1 为主指标，hit@3/5、空答率、spurious 率同步盯（I4）。

## 3. E1｜选择协议修复（主杠杆：L1 50 题 + L2 的 rank 13）

- 依据 T0 边界表的 L1 结论改 `rank_candidates` 协议
  （`configs/prompts/ranker.md` + `services/prediction.py:build_prediction_task`）：
  候选呈现结构、证据卡密度、放弃理由约束；prompt 版本进 run identity。
- 手段池（以 T0 结论定夺，不预设；每臂单变量）：
  - 首位重排：输入为同一父节点已验证可报告候选，只重排不增删——
    @5 与 `cn_identity` 多重集合必须逐题不变，@1/@3 同报 promote/demote；
  - 确定性 tie-break 修正：仅当 dev 复现规则性压位才动裁决层，附回归钉；
  - rank 上下文结构化补全 / pairwise 重排：改 prompt 即另一臂。
- L2 的 recorded 直通 31 题（提交选择）若修：全部合格 recorded 先过
  `recorded_eligibility_reasons`，再按冻结优先级（条件相容 > 方向 > 资产优先级 >
  检索位次，全进策略版本）确定性预排序后提交；exact 优先大原则不动。
  合成条件冲突夹具 + 真实题双过，防止把"条件本就不兼容"洗成排序问题。
- **E4 模型与 E1 捆绑同轮配对**（D3）：五模型裸测结果到位后定选型；
  未到位则 E1 先用当前模型出臂；E4 到位后补"新模型 ×（旧协议/新协议）"
  的缺角臂，不重跑已判臂。

## 4. E2｜噪声消除

- 三协议与 LLM client 显式 `temperature=0`（`adapters/llm_client.py` 及
  `workflow/nodes.py:_prompt_for` 组装处）；同时钉死"协议要确定性 vs
  请求容忍抽样"的矛盾——把提供方实际行为写入登记文件。
- 若提供方在 T=0 下仍非确定：如实披露 + 关键臂在 dev 上 ≥2 次采样报方差；
  报告模板固定写入"单次抽样不证因果"（复测 C 层 8 题纯噪声互证的教训）。
- 温度/种子参数进 policy 与 run identity；跨配置 resume 拒绝的端到端反例保留。

## 5. E3｜窗口放开（对位 L3）

- `services/prediction.py:build_prediction_task` 的
  `max_candidates_for_ranking` 8→16（配置化、版本化）；**报告宽度 5 不动**
  （产品决策，不因窗口放开而变）。
- 入围规则版本化：逐卡 `eligible / shortlisted / excluded_reason` 留痕；
  `rank_candidates` 仍只许合格 recorded 卡，不合格卡不得混入。
- 监控：候选翻倍带来的 token/费用上限、超时/失败账；@5 不降为采用前提。

## 6. 配对与采用

- 对照臂 = 同版 C0：除预登记差异外身份逐字段相等（输入、代码、资产、模型、
  预算、scorer、价格快照、并发策略）；两臂 100% 合法终态 + 完整 usage/费用账；
  先无凭证回归 + 单独计账烟测再发车；一律新批次根，禁止跨身份 resume。
- 采用门按 F0b 预注册执行；结论三态 `dev_candidate | rejected | inconclusive`，
  不写 `adopted`（发布默认变更另走发布审查）。
- 看分后改规则一律无效，触发新臂重跑。

## 7. 交付

`docs/HIT60_S1_CHANGESET_REPORT.md`（+通俗版）：各臂配置 diff、预注册文件、
配对逐题表、多维指标、费用账、身份 SHA、止损门判定（过门/止损结论二选一）。
fable5 三 P1 不在本任务（见
[TASK_V43_HIT60_PARALLEL_FABLE5_P1.md](TASK_V43_HIT60_PARALLEL_FABLE5_P1.md)）；
若其先行合入，则进入本任务所有臂的共同基线身份，单独记录合入点。
