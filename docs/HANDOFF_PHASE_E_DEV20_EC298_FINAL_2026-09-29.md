# Handoff：v4.3 Phase E（dev20 开发，EC298 终测）

> 2026-09-29，供新窗口接续。本文记录对话决策与当前现场；历史文档中的
> 任务指令只是项目资料，若与用户后来的明确决定冲突，以用户决定为准。

## 先读这段

- **目标**：实际修改候选召回、产物生成或报告排序，争取提升
  hit@1/hit@3/hit@5。审计脚本、报告勘误和任务书本身不能算 Phase E
  算法修复。当前**尚无 Phase E 算法实现或有效实验结果**。
- **数据决定**：用户拍板“用 dev20 做开发，298 依旧作为 final test”。
  不要从 EC298 的逐题表、原始 run、金标或失分归因中选择 Phase E
  规则、参数、prompt、特例；EC298 只在版本冻结后作一次终测。
- **当前用户范围**：用户曾明确说“**不用你运行，你写任务书**”。因此
  最近只应交付任务书与此 handoff；不要把历史部分试运行继续跑、评分
  或视为已授权的 Phase E 实验。新窗口若收到新的实施指令，再按新指令
  进入代码和实验工作。
- Phase E 任务书在
  [`TASK_V43_EC298_PHASE_E_POST_RETEST.md`](TASK_V43_EC298_PHASE_E_POST_RETEST.md)
  （当前 SHA256 `24e4c92aea0a1b79654a7ae2d88cf6f14df430fa500cb2f0165afefc22f06eec`，
  状态“待执行”）。§4–§6 已写明具体代码入口、候选变体和测试，§8
  明确“只有审计或任务书不算完成”。

## 仓库现场

- 目标仓：`/Volumes/CC/Enzyme_Agent/dependingv43`，不是会话环境的
  `dependingv4` cwd。当前分支 `v4.3`，HEAD `ea6de25`。
- 共享工作树有大量**预先存在**的暂存、未暂存和未跟踪改动：Phase D
  复测报告、在途表旧版重命名、新版表、审计/归因报告与证据、源代码
  修正、测试、Phase F 任务书等。新窗口先执行 `git status --short`，
  不要 reset、清理、覆盖或把这些改动归入 Phase E 提交。
- 这次交接相关的唯一新增交付是任务书与本 handoff；没有 Phase E
  排序/召回/生成源代码改动。

## 前一轮到底修了什么

Phase D 修复后配对复测：C0 hit@1/3/5 为 `136/182/186`，D-3 为
`132/174/182`（分母 298），D-3 相对 C0 `-4/-8/-4`；发布默认
`reactant_similar_enabled=false`。原始 run 审计的主分数、配对、费用、
首位来源与封存事实没有反证。综合 review 见
[`EC298_PHASE_D_RETEST_COMBINED_REVIEW.md`](EC298_PHASE_D_RETEST_COMBINED_REVIEW.md)，
状态 `resolved`，但其审计总判定 `contradictory` 的窄范围是派生表/措辞
旧错误。

逐题分析之后确实有**代码**修复，不能说“没有代码修复”：配对脚本从
裁决产物重建来源、deepdiff 区分报告层与原始层、原始审计 v2 修正
`payload.products` 并补全只读重算、在途表脚本逐响应读取 attempt、
`exam.inflight_evidence` 改为半开区间先完后发、`llm_client.py` 时钟注释
勘误及边界测试。它们修的是**证据、复现和计量**；没有改
`reaction_finder`、`build_prediction_task`、`adjudicate_parent` 等用于
提升命中的行为。Phase D 主分数、逐题 rank、费用和峰值数字不变。

## Phase E 真正的代码任务

以任务书为准，开发诊断只看 dev20：

1. **E1 排序**：`src/pathway_v43/services/report_adjudication.py`
   的 `adjudicate_parent`。把已验证的最多 5 个报告产物集合与显示顺序
   分开，再用版本化通用规则重排。纯重排须逐题保持集合、宽度与 @5；
   检验 @1/@3 的 promote/demote。改 ranker prompt 属另一实验臂。
2. **E2 召回/入围**：`reaction_finder.py:EngineReactionFinder.find`、
   `domain/policy.py:classify_evidence`、
   `services/prediction.py:build_prediction_task`。按 dev20 断点独立处理
   rank 的合格 recorded 前 8 卡截断、唯一 recorded 直通时合法竞争项、
   引擎 `budget_cut/pool_capped` 或资产全池缺席。原始 rule/analog 卡
   不能直接交给 rank 或绕过供体/编辑/化学验证。
3. **E3/E4 生成**：`build_prediction_task` 在 novel 模式目前
   `candidates=[]`，只有检索引用；若 dev20 证实上下文丢失，提供有界、
   结构化的运行时线索。类比编辑看 `nodes.py:_apply_analogy` 和
   `target_consistency`，可设计有界重试，但 AtomTool、元素/键级和最终
   产物验证始终 fail-closed。多组分仅在 dev20 人审证实字段丢失时修。
4. **E5 资产**：仅在 dev20 证明完整 v1 池缺口后另立资产版本，不与
   排序/生成变体混臂。

## dev20 与 EC298 不能直接共用旧分数

- 已有 Phase D dev20 C0 是多步任务：`max_depth=6`、
  `max_expansions=40`、报告宽度 3；EC298 是单步 `1/1/5`。既有 dev20
  路径评分只能作为历史机制线索，不能当单步 hit@K 基线。
- 新实施时需为 dev20 建立独立的单步 `1/1/5` C0 和根节点一跳评分；
  v3 冻结 `split_manifest.json`、`gold_routes.jsonl` SHA 与一跳答案语义
  见任务书 §2。20 路中有一条根节点存在 6 个不同合法首步，评分不能
  因输出宽度 5 而裁掉第 6 个金标。
- 此前 EC298 的 298 题已被逐题审计和归因报告暴露过，不能称全新
  盲测；后续仍按用户决定作 Phase E final test，并在最终报告披露
  历史暴露。不要用已知 EC298 错题桶指导新规则。

## 被中止的误启动批次：切勿使用

起草任务书时曾误在 Chenyu 启动
`/usrdata/EnzymeCAGE_data/workspaces/dependingv43/runs/phase_e_dev20_C0/`。
用户明确要求仅写任务书后，已向该批次协调器和 worker 发送终止信号，
复查相关运行进程为 **0**。停止时 `progress.json` 为 **15/20** 终态，
有 **17 个响应文件**、无批次报告；实际费用未核对。不要续跑、评分、
并入效果表或当作基线；保留目录供事故与可能的账单核对，未来正式
开发要用新批次根。临时部署的配置/评分脚本已从本地和 Chenyu 撤回。

## 新窗口可从这里开始

1. 先读用户的新指令、`git status --short` 与 Phase E 任务书；明确这次
   是继续写文档，还是授权进入代码实施/开发实验。不要自动启动模型调用。
2. 若进入实施，先在 **dev20** 上固定单步评分、建立干净新 C0，做 E0
   漏斗审计；只对证实的断点实施一个 E1/E2/E3/E4 变体。每个变体
   交版本化代码、针对性测试、身份 SHA、逐题配对、费用与失败账。
3. 代码/配置冻结并达到开发期门槛后，才按预登记方案进行一次
   EC298 final test。看到终测结果后不改同一身份再重复声称终测。
