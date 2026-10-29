# P1-B 设计与改法 — 声明产物 vs 执行产物「先修复、后兜底」（2026-10-21）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文只写改法，不执行、不付费、不改判据。
> 前置：P0b/D-6 已合入 `11aeeaf`；P0b 只做**旁路披露**（默认关闭），**未改生成/提交行为**。
>
> **2026-10-21 CC 拍板：首选 A（修复反馈），B（硬门）只做残余兜底与对照。**
> 本文 §2A 为 A 的完整设计；原 B 设计保留在 §2，作为 `gate` 对照臂与
> 反馈不可用/耗尽时的残余拒法。

## 0. 一句话

P0b 把「声明 ≠ 执行」**看见了**；P1-B 首选**让模型自己修**：在执行后、提交前
只对已证 `principal_absent` 的候选发起有界修复反馈（复用现有 2 轮
`format_feedback` 预算），模型改 edits 把声明主产物真正执行出来则正常提交；
2 轮仍 absent 才按残余兜底拒。合法多碎片/copy/unknown/stereo 不触发，
单变量、预注册、可回滚。

## 0.1 方案选择（A vs B）

| 维度 | **A. 修复反馈（首选）** | B. 硬门（残余/对照） |
|---|---|---|
| 对 principal_absent | 先反馈模型改 edits；改对则提交 | 直接拒提交 |
| 调用成本 | 每条最多 +2 轮（复用现有预算） | 0 额外调用 |
| 命中损失 | 有机会把 absent 救回 | 直接损失依赖该事件的命中 |
| 新增机制 | 复用 `format_feedback`/轮数/上限 | 无 |
| 失败残留 | 2 轮仍 absent ⇒ 同 B 拒 | 同左 |
| 实验臂开关 | `P0B_D6_RECONCILIATION_POLICY=feedback` | `=gate`（仅对照） |

## 1. 现状（代码事实）

| 位置 | 现状 |
|---|---|
| `production.py:392` | 主产物取自 spec 的声明 `product_smiles`（“工具已确定，只能引用”） |
| `production.py:415` | `build_product_state(product_smiles)` 建声明产物态 |
| `production.py:1004` | `execute_edits` 得到真实执行结果 `execution["result"]` |
| `production.py:1213` | `build_pathway_event(hypothesis)` 用**声明产物**建事件 |
| `production.py:1177` | `decide_admission(audit)` 只看 audit，**不看**声明-执行对账 |
| `native_result.py:775` | P0b 只在导出时调 `reconcile_declared_vs_executed` 做披露 |

⇒ 事件可以提交一个**没有由 edits 执行出来**的主产物；P0b 只把它记成 `inconsistent`。

## 2A. 首选方案 A：执行后修复反馈（2026-10-21 CC 拍板）

> 结论先行：A 把「声明 ≠ 执行」当成**可修复的模型错误**，在提交前用现有
> `format_feedback` 轮把「你的声明主产物未由 edits 执行出来」+ 执行碎片/
> 归属的必要摘要回给模型，让它改 edits；改对则正常提交，2 轮仍 absent 才拒。
> B 的硬门降为残余兜底与对照臂。

### 2A.1 触发

仅当执行后对账结果 = `inconsistent` 且
`inconsistency_subclass == "principal_absent"`。以下一律**不触发、不拒**：

- `consistent`；
- `principal_stereo_only`（立体差是另一子类，按合同不构成“未执行”）；
- `principal_isomeric_unspecified`（同位素/CX 扩展的未细分差）；
- `unknown`（缺资料/解析失败/执行未核）；
- `not_applicable`（确知空声明）。

四态/子类沿用 P0b v2 的单一判据 `reconcile_declared_vs_executed`，不另写
字符串比较、不新造身份。

### 2A.2 反馈内容（只涉及模型自己的声明/执行）

结构化 `feedback_error`：

- `kind = declared_product_not_executed`（新反馈类别，仅用于本路径）；
- 回给模型**它自己的**声明与执行事实的必要摘要：
  - 声明主产物（模型自己写的 `product_smiles`）与共同产物；
  - 当前 `reaction_spec`（含 edits/donor/alignment/expectation）；
  - 实际执行碎片 `execution.result.product_smiles`；
  - 主产物归属：投影 rank1 状态与声明主产物一致、但不在执行碎片；
  - 计数/关系：`declared_missing_from_executed`、`executed_extra`、
    `relation`、`boundary`；
  - 指令：**保持声明主产物/共同产物/expectation 不变，只改 edits**
    （必要时 donor/alignment），使声明主产物真实出现在执行碎片中。
    expectation 不允许改（否则可用改期望绕过 `principal_absent` 判据）。
- **不读**金标、参考图、题面、`reference_graphs`、`questions.jsonl`、
  `llm.env`；只消费本事件自己的 spec/execution/report projection。
- 反馈轮的用户载荷新增 `reconciliation_feedback` 块；该块缺席时
  `build_proposals_user_payload` 的输出逐字节不变。

### 2A.3 预算（不新增调用预算）

复用现有 `format_feedback` 轮机制：

- 同一 purpose = `format_feedback`；同一持久计数
  `format_feedback_rounds_used(ledger, action_id)`；
- 同一上限 `max_format_feedback_rounds`（T-I/chain13 批 = **2**）；
- **每 expand action 最多 2 轮**；每轮仍受 run 级
  `max_real_model_requests` 真实请求预算即时占额（T-I 每题 3 请求语义）；
- **不新增 purpose、不新增轮数预算、不新增每题调用上限、不新造计数器**。
- 反馈登记新增一个可接受错误类别 `declared_product_not_executed`；
  现有四类 JSON 格式错误（json_field/json_type/allowed_id/syntax）不变。

### 2A.4 流程（单 action 内，事件提交前）

1. 执行 edits（现有 `execute_atomtool_expansion`，真实工具）；
2. audit → admission（R1–R7 不变）；只有 admission 可提交的候选才进对账，
   避免为本来就会被 admission 拒的候选花反馈调用；
3. 构建事件投影/展开计划，用同一 P0b 判据对账
   （`reconcile_declared_vs_executed`，事件参与物侧 + 执行结果侧）；
4. 若 `principal_absent` 且 principal 边界 = `model_declared`
   （novel、spec 无 `compile` 块）：
   - **未提交**；
   - 登记反馈轮 → 向模型要一个 revised `reaction_spec`；
   - 校验 revised spec **保持身份字段不变**：`product_smiles`、
     `coproducts`、`declared_copy_components`、`requirements`、
     `dependencies`、`assumptions`、`transformation_ref`、
     `expectation`、`compile`；只允许改 `edits`/`donor`/`alignment`；
   - 用同一 `prepare_hypothesis` 重建：新 `hypothesis_id` 必须等于
     action 的 `subject_ref`（事件身份冻结门；不等 ⇒ 该轮失败）；
   - 重新执行/对账；
   - **非 principal_absent**（consistent / stereo / isomeric / copy /
     unknown / not_applicable）⇒ 正常提交流程；
   - 仍 absent 且还有轮数 ⇒ 再反馈；轮数耗尽 ⇒ 拒提交；
5. 拒提交：structured reason = `declared_product_not_executed`；**不写事件**；
   action 记 `admission_rejected`，detail 带 `p0b_d6` 行与轮数；候选/池/
   分母不变；
6. 非 `model_declared` 边界（compiled `execution_derived` 或 boundary
   `unknown`）**不发起反馈**（模型改不了该声明），直接按残余兜底拒；
   本批 146 条全部是 novel `model_declared`，不触发该分支；
7. 反馈响应不可解析 / 改了声明的身份字段 / revised edits 非法 /
   与当前 edits 相同：该轮视为失败并**直接残余拒**（不再花第二轮，
   避免用坏响应反复占额）；2 轮预算用于“模型给了有效修订但执行后
   仍 absent”的持续情形；
8. 传输失败/超时/悬空：仍按既有 run 失败语义（失败题留分母），
   不吞成“拒”也不吞成“成功”。

### 2A.5 开关

`P0B_D6_RECONCILIATION_POLICY`：

| 取值 | 语义 |
|---|---|
| `disclose`（默认） | 完全不执行本段；行为与 P0b/基线**逐字节一致** |
| `feedback`（A；P1-B 实验臂） | 上述执行后修复反馈 |
| `gate`（纯 B；仅对照/残余） | `principal_absent` 直接拒，不发反馈 |

- 未知取值 **fail-closed**（结构化拒），不静默回退 `disclose`。
- 该 env **不在** run identity/profile 块（未改 `profile.py`）；预注册/
  发车脚本必须显式记录其值，并保证 A/B 两臂只差这一项。
- 单变量：P1-B 批只切这一个环境变量；模型/池/判据/prompt/预算全冻结。
- `disclose` 下不得调用 `reconcile_declared_vs_executed`、不得写
  `p0b_d6` 键、不得登记反馈轮。

### 2A.6 合法正控（必须保留）

| 控制 | 期望 |
|---|---|
| 合法多碎片主产物 | `consistent`；不反馈、不拒 |
| 合法 copy（21 条正控类型） | `consistent`/`not_applicable`；不反馈、不拒 |
| 仅立体差 | `principal_stereo_only`；不反馈、不拒 |
| 同位素/CX 未细分差 | `principal_isomeric_unspecified`；不反馈、不拒 |
| 明确空声明 | `not_applicable`；不反馈、不拒 |
| 资料缺失/坏类型/执行未核 | `unknown`；不反馈、不拒 |
| `principal_absent` + `feedback` | 反馈；改对则提交，耗尽才拒 |
| `principal_absent` + `gate` | 直接拒（reason 同 A 的残余拒） |
| `disclose` | 与基线逐字节等价 |

### 2A.7 不做

- 不改判分/评分/池/检索/排序/prompt 版本；
- 不改 R1–R7、不改 `ADMISSION_SUBMITTABLE`、不改答案定义（C 方案不启）；
- 不回溯改旧批/封存 run；不回写旧成绩；不把 absent 写成“化学错误”；
- 不新增调用预算/purpose/第六个源码文件；不读金标/参考图。

### 2A.8 代价与 unknown

- P0b v2 的 **146 条 `principal_absent` / 95 题**（分类证据
  `docs/review_evidence/p1b_impact_2026-10-21/`）：A 可能为每条多花
  1–2 次逻辑调用；**A 的实际回收率 unknown，需新批测量**。
- 146 条里 **33 题有 2–5 条 absent 事件**（1 题 5 条）；同一题的
  `max_real_model_requests=3` 可能先被前面的反馈耗尽，后续 absent
  只能按残余兜底拒——这是 A 的真实代价，不是“免费修复”。
- 模型未必能改对：66 条 `disjoint`（执行碎片与声明生成组分完全不相交）
  比 80 条 `overlap`（至少保留共同产物、但主产物仍缺席）更难救；
  本设计不承诺收益。
- B 残余拒的命中损失仍需按原 §3 离线复算；本批 5 个 strict absent
  事件中 3 个 rank1、2 个 rank2，可能被 A 救回，也可能被拒。

### 2A.9 与 6 个 strict 事件

- 6 个 strict 对照事件 = **5 个 `principal_absent` + 1 个
  `principal_stereo_only`**（4 rank1 + 2 rank2；absent 侧 3 rank1 + 2 rank2）。
- **不在旧批回溯改分**；新批才启用 A。
- 5 个 absent 可能被反馈救回或被拒；stereo 不触发 A。
- 化学真伪仍按 P0b 挂账：规则级评审不等于真实结构复核；A 的程序回收率
  不等于化学正确。

### 2A.10 实现落点（独立 worktree）

| 文件 | 改动 | 约束 |
|---|---|---|
| `src/pathway_v43/pollutant/production.py` | 策略开关；从 prepared/event/execution 组装同一 P0b 对账；`principal_absent` 返回 `revision_required` 或最终拒 | 不改 disclose 路径；不改 admission |
| `src/pathway_v43/pollutant/runflow.py` | `_run_expand` 消费 `revision_required`：登记/复用反馈轮 → 解析 revised spec → 身份保持校验 → 重建 prepared → 重新执行 | 反馈耗尽/不可修复 ⇒ admission_rejected detail `declared_product_not_executed` |
| `src/pathway_v43/pollutant/model_protocol.py` | 反馈登记增加 `declared_product_not_executed` 可接受类别 | 同一 purpose/轮数/上限；四类 JSON 错误不变 |
| `src/pathway_v43/pollutant/real_model.py` | `build_proposals_user_payload` 可选 `reconciliation_feedback` 块 | 无该块时载荷逐字节不变 |
| `tests/test_p1b_reconciliation_feedback.py`（新增） | 6 组正负控 + disclose 等价 | stub 模型/合成载荷，零真实调用 |

## 2. 残余兜底 B：硬门（仅对照）

> 2026-10-21 CC 拍板后，B 不再是首选：它只作为 `gate` 对照臂，以及 A 在
> 2 轮后仍 absent / 反馈不可用时**残余兜底**的拒法。以下原设计保留。

### 2.1 开关

在 `production.py` 增加（与 P0b 同文件、同块版本）：

```python
P0B_D6_RECONCILIATION_POLICY_ENV = "P0B_D6_RECONCILIATION_POLICY"
# 取值："disclose"（默认，行为逐字节不变）
#      | "feedback"（A，首选；见 §2A）
#      | "gate"（纯 B，仅对照/残余）
```

- `disclose`：完全保持现状（P0b 披露块默认关）；不得在 T-I 批启用。
- `feedback`：P1-B 实验臂（A）；单变量差分只有这一项。
- `gate`：只作为对照臂与 A 耗尽后的残余拒法；不单独发车。
- 未知取值 fail-closed（结构化拒），不静默回退。

### 2.2 插入点

在 `production.py` 的 `expand_hypothesis_production` 内，**`execution` 成功、
`decide_admission` 判定可提交之后、`write_commit_bundle`/事件提交之前**插入
（约 1184 行后）。放在 admission 之后的原因：只有本来就会提交的候选才需要
对账/反馈；被 R1–R7 拒的候选保持原 admission 理由，不改变 admission 语义。
P0b 已证 146 条 absent 都通过了 admission（retain_conditional），该插入点
与“提交前拦截”等价。

```python
if p0b_d6_reconciliation_policy() != "disclose":
    event = build_pathway_event(hypothesis, ...)          # 先建事件供产物侧
    report_projection = build_report_projection(...)
    refs, smiles = _p0b_d6_event_product_side(event, states)
    recon = reconcile_declared_vs_executed(
        build_declaration_disclosure(spec),
        execution=execution,
        event_product_refs=refs,
        event_product_smiles=smiles,
        expectation_target=..., expectation_invalid=...,
        projection_ranks=report_projection.to_dict()["product_ranks"],
        state_smiles_by_ref={s.state_id: s.smiles_isomeric for s in states.values()},
        audit_center=execution.get("center_evidence"),
        origin=p0b_d6_origin_from_logical_id(receipt["payload"]["logical_proposal_id"]),
        production_report_present=True,
    )
    if (recon.get("status") == "inconsistent"
            and recon.get("inconsistency_subclass") == "principal_absent"):
        if policy == "gate":
            return _report("rejected", ...,
                           admission={"disposition": "rejected",
                                      "reasons": ["declared_product_not_executed"]},
                           event=None, p0b_d6=recon)
        # policy == "feedback": 不写报告、不提交，返回 revision_required
        return {"status": "revision_required", "p0b_d6": recon, ...}
```

要点：
- **只拦 `principal_absent`**（已证主产物不在执行碎片）；`principal_stereo_only` 不拦
  （立体差是另一子类，按合同不构成“未执行”）；`unknown`/`not_applicable` 不拦。
- 拒因独立、结构化，别混进 audit 的 `rejected`；便于下一轮按 reason 统计。
- 拒提交时**不写事件**；候选仍留在池/披露面，分母不变。
- 不改 `decide_admission` 的 R1–R7；不改评分、池、检索、排序、prompt。
- 若未来要“改用执行产物而不是拒”，那是另一个变量（`derive` 策略），不在 P1-B 首轮。

### 2.3 复用同一判据（单一来源）

- 必须复用 `reconcile_declared_vs_executed`（P0b 已合入），**不另写一套字符串比较**。
- `disclosure` 直接用 `build_declaration_disclosure(spec)`（P0b 同一入口）；
  事件产物侧从 `build_pathway_event` 的产物参与物 + `states` 表解析，
  与 `native_result.derive_declared_vs_executed` 同源字段。
- 若字段缺失，走 helper 的 `unknown`，不 gate。

### 2.4 合法正控（必须保留）

| 控制 | 期望 |
|---|---|
| 合法多碎片主产物 | consistent / 通过 |
| 合法 copy（21 条正控类型） | consistent 或 not_applicable；不拦 |
| 仅立体差 | `principal_stereo_only`；**不 gate** |
| 同位素/CX 扩展差 | `principal_isomeric_unspecified`；先披露，不 gate |
| 明确空声明 | not_applicable；不拦 |
| 资料缺失/坏类型 | unknown；不拦（保留 proof_scope） |
| 主产物确不在执行碎片 | **gate 拒绝**，reason=`declared_product_not_executed` |
| `disclose`（默认，gate 关闭） | 与基线逐字节等价 |

### 2.5 测试

- 新增 `tests/test_p1b_reconciliation_feedback.py`（A 为主，B 只做对照分支）：
  - absent → 反馈 1 轮 → 模型改对 → 提交；
  - absent 持续 2 轮 → 拒、无事件、分母不变；
  - consistent/stereo/copy/isomeric/unknown → 不反馈、不拒；
  - 反馈轮耗尽 → 拒；
  - `disclose` 路径逐字节等价（不调用对账、不写 `p0b_d6` 键）；
  - `gate` 分支 principal_absent 直接拒、其它状态不拒。
- 跑既有 production/endpoint/export 相关面；不得改既有断言口径。

## 3. 零成本影响分类与离线复算（先看代价，再决定上线）

### 3.1 146 条 principal_absent 的只读分类（已做，零模型）

产物：`docs/review_evidence/p1b_impact_2026-10-21/`
（脚本 + `principal_absent_classification.json` + 运行日志）。

| 项 | 数值 |
|---|---:|
| principal_absent 事件 | 146 |
| 涉及题数（qid 前缀） | 95 |
| 真声明-执行不符（程序级） | 146 |
| 合法多步/装配分工 | 0 |
| unknown（元数据不足） | 0 |
| disjoint（执行碎片与声明完全不相交） | 66 |
| overlap（至少保留共同产物，主产物仍缺席） | 80 |
| 声明共同产物 0/1/2 个 | 35 / 91 / 20 |
| 6 个 strict 对照事件中的 absent | 5（3 rank1 + 2 rank2） |
| 有 2–5 条 absent 的题 | 33 |

- 分类只读冻结 T-H r2 导出 + 批清单；不读金标/题面/参考图，不输出结构正文。
- 146 条全部是 novel、无 `compile` 块、principal `model_declared`、
  `step_scope=net_reaction`、rank1 归属与声明一致、expectation 含声明主产物；
  因此全部落“真声明-执行不符”，不存在可归为“合法多步/装配分工”的元数据依据。
- 程序级分类 ≠ 化学真伪；146 条的化学正确性仍 unknown。

### 3.2 A 的回收率无法离线预知

A 需要模型实际重写 edits，离线不能用冻结导出模拟“模型会不会改对”。
因此 A 的回收率**只能新批测量**；本步只给代价面：146 条可能各多 1–2 轮，
33 题的多 absent 会互相争用每题 3 次真实请求额度。

### 3.3 B 残余拒的离线命中损失（仍要做）

用**冻结 T-H r2 导出 + 冻结 scorer**（零模型、零重判）在隔离副本里模拟
`gate` / A 耗尽后的残余拒：

1. 对 1586 事件按 `principal_absent` 标记——P0b 已给 **204 条**
   （146 absent + 58 stereo）；
2. 只移除 146 条 absent（stereo 不拒），重建已提交事件集（不重跑模型）；
3. 用冻结 scorer 重算：hit@1/@3/@5、strict/partial/unmatched、6 个 strict
   对照事件去向；
4. 输出：
   - 被拒事件数/题数；
   - 命中损失上限（多少 hit@1/strict 依赖这些事件）；
   - 6 个 strict 事件里几个被拒（预期 5 个 absent + 1 个 stereo 不拒）；
   - 合法正控是否被误伤（应为 0）。
5. **不改封存批根、不回写旧成绩**；产物写
   `docs/review_evidence/p1b_impact_2026-10-21/`。

> 这一步给出**最坏情况**（A 一轮都没救回）；A 的实际结果需新批。
> 预注册必须同时登记“可能降分”的报告口径。

## 4. 预注册与红线

- P1-B 是**效度修复**，不是提分项；可能让 hit@1 下降，报告必须如实写。
- 单变量：实验臂只开 `P0B_D6_RECONCILIATION_POLICY=feedback`，其它
  （模型/池/判据/prompt/预算）全冻结；`gate` 只作对照/残余，不单独发车。
- 反馈轮预算沿用 `max_format_feedback_rounds=2` 与每题
  `max_real_model_requests=3`；**不新增调用预算**。
- 预注册先于付费；分母仍 298；失败/unknown 不剔题；判分零 LLM。
- 新一轮批根独立；旧批零回写；封存批只读。
- 涉及 strict 认可口径的变化（如 stereo/isomeric 子类升格）仍归老师裁定，不在 P1-B。
- 不改 `ADMISSION_SUBMITTABLE` 的 R1–R7；P1-B 是**提交前独立对账/反馈/残余拒**，
  不是 audit 改判。
- 化学评审：A 新增“让模型改 edits”的提示面，涉及模型行为而非判据；规则级
  化学评审请求仍按仓库三触发点单独产出/送审，本设计不冒充已评。

## 5. P1-A（另一条，不要混）

NC-9（copy 进 expectation）是**装配源头**问题，修法是查 `production.py` 的
copy/expectation 构造，修源头并逐条拒绝坏 spec、继续合法候选；目标是恢复合法候选
可处理性，**不承诺“修完必增 2 题”**。P1-A 与 P1-B 分开预注册、分开验收。

## 6. 与 6 个 strict 事件的关系

- 6 个事件 = 4 rank1 + 2 rank2；5 个 `principal_absent` + 1 个 `principal_stereo_only`。
- A 只对 5 个 absent 发起反馈：可能救回、也可能 2 轮后拒；stereo 不触发。
- B 残余/对照臂只会拒 5 个 absent，不拒 stereo；实际 hit@1 损失需 §3.3 离线复算。
- **先化学复核定性**（R4 规则级评审已过，但 58/146 化学真伪仍 unknown）；
  不基于 6 个事件回溯改分；下一轮预注册批才启用 A。

## 7. 交付顺序

1. §3.1 146 条零成本分类（已做）；
2. P1-B A 章设计 + 独立 worktree 实现 + 正负控（本轮）；
3. §3.3 B 残余拒离线命中损失复算；
4. 预注册（单变量 `feedback`、A 可能降分/回收率 unknown 的报告口径）；
5. 付费批（CC/Codex 代决）；
6. P1-A 另立任务书。