# 任务书 — chain14 发车物实施（证据卡开关+传输重试+双臂发车族，2026-10-15）

> 派单：主会话（CC 睡前授权代确认+自动推进）。执行者：实施子代理。
> 上游：预注册 `docs/CHAIN14_EVIDENCE_AB_PREREG_2026-10-15.md`（**已确认
> 生效**：双臂 A/B、transport 重试双臂共享、novel 反馈轮推迟）。
> 题域标签：**298=RHEA 通用酶学/已见题**。基线：HEAD `b4b89dc`（证据卡
> 实施+P1 修复已提交），全量 not-slow **2158/0/16**。
> 一句话：给已实施的证据卡装**批级开关**（A 臂关/B 臂开）+给传输失败装
> **双臂共享的自动重试**+适配 **chain14 双臂发车族脚本**。本任务**只在
> 本地实施与验证**，HPC 部署与发车由主会话执行。

## 一、三个实施件

### 件 1：证据卡批级开关（A/B 唯一差分变量）

- **机制**（沿 chain13「3 调用预算」先例）：经 `run_s5b_batch` 的批级参数
  发车覆盖 `evidence_card_enabled ∈ {true,false}`，冻结进 orchestration.json
  （改参即拒、fail-closed：键缺失/非法值 ⇒ 结构化拒，不缺省）；worker/run
  侧同判据核对（沿 no-cap 先例 worker 核对模式）。
- **消费点**：`runflow._call_real_fetch`——false ⇒ 池条目不带 `evidence`
  子对象、不传 `substrate_evidence` ⇒ 载荷=既有四字段形状（**与证据卡
  实施前逐字节兼容**，测试断言）；true ⇒ 现行 candidate-evidence-2 行为。
- **提示词两臂同版**：系统提示词（含 evidence 规则段）两臂**相同**，
  `PROPOSALS_PROMPT_VERSION` 两臂一致——**A/B 唯一差分=用户载荷证据字段**。
- **诊断披露**：批报告/run 诊断 `evidence_card_enabled`；批身份含该键。
- **受控词表**：新字面量进 T11 登记。

### 件 2：传输失败自动重试（双臂共享，预注册落字）

- **触发**：真实调用 transport 失败（`real_model_transport_failure`/error_kind
  transport_error）⇒ **自动重试 1 次**（每逻辑调用至多 1 次，重试后仍败 ⇒
  按现行失败语义终止该题模型路径）。
- **计费/账目**：每次 HTTP 尝试=一次 issued 请求（gate/budget 诚实计数，
  每题 max_real_model_requests=3 语义不变）；calls 记录 `http_attempts`
  逐尝试留痕（字段已在）。
- **两臂同享**（不构成 A/B 差分变量）；批报告披露 retry 计数。

### 件 3：chain14 双臂发车族（chain13 族参数化复用）

- **必读先例**：`scripts/hpc/sbatch_chain13_{build,run,score}.sh` +
  `chain14 前身的 chain13_run_wrapper.py/chain13_gate.py/chain13_score_v2.py`
  （同目录）。
- 新增 `scripts/hpc/sbatch_chain14_{build,run,score}.sh` +
  `chain14_run_wrapper.py`：ARM 参数化（a/b），批根
  `~/ppv1_hpc/batch/chain14{a,b}_s5b_20261015`、runs 根同款、env=llm.env
  （GLM）、A 臂发车参数 `evidence_card_enabled=false`、B 臂 `true`、
  no-cap 标记+approve+budget 流程沿 chain13、判分双口径（v2 headline+
  v1 改名 .v1）沿 chain13_score_v2。
- 脚本本地不做 HPC 提交（只写文件）；沿既有坑写死：脚本实体化（不
  heredoc）、sbatch 环境变量前置、家目录中转。

## 二、红线

1. 判分侧/池/检索/排序/硬拒绝表零改动；A 臂载荷四字段形状逐字节兼容
   （测试断言与证据卡实施前 build_proposals_user_payload 输出一致）。
2. 单差分变量纪律：除开关+重试+发车物外零行为变化；重试两臂同享。
3. 零金标零题面零模型零网络（实施期）；不 push（commit 留主会话统一
   处理）；`PYTHONDONTWRITEBYTECODE=1`。
4. 全量 not-slow 2158/0/16 零翻转（新测另计）；对外数字带 298 标签。

## 三、测试要求（新文件或并入既有）

- **开关正负控**：true⇒载荷含 evidence/substrate_evidence/schema 版本；
  false⇒四字段形状**逐字节**=实施前口径（对照快照或重构旧形状断言）；
  键缺失/坏值⇒结构化拒（fail-closed）；orchestration 冻结后改参即拒。
- **重试正负控**：首次 transport 失败⇒重试 1 次成功⇒题成功且
  http_attempts=2；两连败⇒现行失败语义（零静默吞）；重试不越每题 3 请求
  上限语义。
- **发车物冒烟**：脚本存在性/参数化正确性（ARM a/b 各渲染一次 dry 校验，
  本地零提交）。

## 四、回传义务（≤30 行）

①三件改动文件与行数；②开关 byte-兼容断言结果；③重试正负控数字；
④全量数字；⑤发车物脚本清单（ARM 参数化样例各一行）；⑥偏差（有必列）；
⑦交付书 `docs/CHAIN14_LAUNCH_IMPL_DELIVERY_2026-10-15.md` 路径。主会话
将抽查：A 臂字节形状、fail-closed、重试计数、全量独立复跑，并走 Codex
fork 复审后上 HPC。

## 五、排障表

| 症状 | 处置 |
|---|---|
| A 臂载荷与旧形状有差 | 停下逐字节 diff 定位（预期=完全一致，含 JSON 键序） |
| 重试与预算/gate 冲突 | 读 gate 语义再定，不得改每题 3 请求语义；如实报告设计取舍 |
| chain13 脚本读不懂 | 沿 sbatch_chain13_* 逐行读，参数化不重写语义 |
| 全量红 | 版本字面量/CI 合法更新按先例；行为红=修或停报 |
