# 评审请求 — T-H P0b/D-6 旁路披露实施与零漂移门（2026-10-20）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文全部计数、
> 锚点与结论只在该题域成立，不外推到 dev、新题或其他题域。
>
> **请求类型：** 对 P0b/D-6 的**合同 + 实施 + 合成正负控 + 正式零漂移回放门**
> 做最终审核，并给出**放行 / 需修正**的最终裁决。
>
> **授权链：** CC 2026-10-20 明确「开始做，然后直接推进到 P2；需要我/师姐
> 裁决的由 Codex 代为裁决，Codex 的裁决即为最终裁决」；你的 P0 审核报告
> `docs/T_H_P0_DECISION_CODEX_REVIEW_2026-10-20.md` §四/§五 把 P0b/D-6 定为
> 本轮唯一最高优先，并冻结“只披露、不加硬门”的最小范围。本请求据此请求
> 你对本任务实施给出最终裁决（代 CC/师姐）。
>
> **边界：** 本任务未加对账硬门，未改 admission/候选/池/检索/排序/评分，
> 未做 v3 promotion，未修 D-3/D-7，未跑 HPC、未调模型、未 push、未写封存
> 批根/runs 根、未读金标/题面/凭证/封存逐题 run。**零金标、零题面、零凭证。**

## 1. 一句话

在独立 worktree 给原生结果加了**可选、默认关闭**的
`declared_vs_executed` 诊断块（冻结 strict 身份、主产物归属、执行/装配边界、
copy 来源、proof_scope、四态、unknown_reason）；8 项合成控制全过；用固定
历史导出做 A/B 回放，**剔掉新字段后候选成员、1586 事件身份/内容/顺序、
126 strict rank、评分语义零漂移**，复现 **hit@1=89、strict=126、partial=53、
unmatched=119**。请裁决：**放行**（才允许主树合并、进入 D-2）或**需修正**。

## 2. 基线与环境

| 项 | 值 |
|---|---|
| 基线 HEAD | `c9c6c7a7ae02b46769add09fbc2536323ce8a985` |
| 独立 worktree | `/tmp/dependingv43_p0b`（主树未合并、未改） |
| patch | `docs/review_evidence/t_h_p0b_2026-10-20/impl.patch`（6 文件：5 源 + 1 新测试） |
| 固定历史输入 | `/tmp/t_h_p0_r2/runs/<run_id>/native_export/<digest>/`（298 payload+manifest；P0 下载副本，本机不可达 HPC runs 根） |
| 批清单/案例/参考图 | `/tmp/t_h_p0_r2/scoring/`（参考图只读装入并做 sha 核对，仅传给冻结 scorer；未检查内容、未复制/打印/落盘/人工读取） |
| 判分 | 冻结 `evaluate_scientific` + criteria v2，零判据改动 |
| Python/RDKit | 3.11 / **2026.03.6**（批内登记 **2026.03.5**；版本差已披露） |
| 模型/HPC/网络 | 0 / 0 / 0 |

## 3. 请按序阅读

| 文件 | 作用 |
|---|---|
| `docs/T_H_P0B_D6_CONTRACT_2026-10-20.md` | **实施前冻结的合同**（字段/边界/四态/unknown/proof_scope/开关/白名单） |
| `docs/T_H_P0B_D6_IMPL_2026-10-20.md` | 实施报告（实现语义、白名单、crosswalk、未决项） |
| `docs/review_evidence/t_h_p0b_2026-10-20/impl.patch` | 全部代码改动（主树未合并） |
| `docs/review_evidence/t_h_p0b_2026-10-20/phase_c/` | 8 项合成正负控（脚本 + JSON + 摘要） |
| `docs/review_evidence/t_h_p0b_2026-10-20/phase_d/` | 正式门：candidate/event/rank/score diff、strict 6 事件、披露聚合、provenance、摘要 |
| `docs/review_evidence/t_h_p0b_2026-10-20/test_evidence.md` | 新测试/既有测试/全量测试/patch 应用验证 |
| `docs/review_evidence/t_h_p0_2026-10-20/p0b_declared_vs_executed.json` | P0 历史探针读数（仅用于 crosswalk；不是新判据） |

## 4. 实施要点（供你核对）

1. **合同先行：** origin、结构身份版本（`chemstate.strict_identity_of`，
   未新造第二套）、主产物、实际生成组分、copy 来源、执行/装配边界、
   适用性、proof_scope、四态互斥、unknown_reason 枚举均已冻结。
2. **旁路：** 诊断只在 `build_native_result` 顶层新增可选块；不写事件/
   hypothesis/action/report 权威；不进入 admission/排序/评分。
3. **开关：** `PPV1_P0B_D6_DIAGNOSTICS` 默认关闭；关闭时 payload 零新增键、
   导出 payload/manifest 与基线逐字节等价。
4. **版本承载：** 块级 `schema=p0b-declared-vs-executed-1`、`version=1`、
   `rule_version=p0b-d6-reconcile-1`；导出 manifest 在开启时新增
   `diagnostic_bindings` 并绑定块 digest。**未升**全局
   `ppv1-native-result-2` / `ppv1-native-export-3` / 导出策略版本；理由：
   可选附加块，旧导出走完全相同的读取路径，全局升位会使历史导出全部失败
   且需改白名单外的 `profile.py`。这是本任务最需要你裁决的设计点之一。
5. **不改既有语义：** `prepare_hypothesis`/`execute_atomtool_expansion`/
   `expand_hypothesis_production` 既有行为未动；builder/compiler 只新增纯
   常量函数；既有测试断言口径未改。
6. **受控词纪律：** 新代码未新增受控词字面量，T11 通过（详见
   `test_evidence.md` §2）。

## 5. 关键读数

### 5.1 四态与 crosswalk（1586 事件）

新合同（冻结边界）：

| 状态 | 事件数 |
|---|---:|
| consistent | 1381 |
| inconsistent | 204 |
| unknown | 1 |
| not_applicable | 0 |

- inconsistent 204 = `principal_absent` **146** + `principal_stereo_only` **58**；
- unknown 1 = `executed_unparseable`（执行产物串被冻结 strict 身份拒绝；
  P0 用普通 canonical SMILES 曾计入 inconsistent）；
- 全部 204 不一致均为 `novel`；recorded 151、template 368 全部 consistent。

P0 crosswalk（同一 1586 事件、按 event_id 前缀逐条对齐，0 缺失）：

| P0 | 新合同 | 事件数 |
|---|---|---:|
| consistent | consistent | 1290 |
| inconsistent, main 不在执行碎片 | inconsistent | 204 |
| inconsistent, main 在执行、仅组分差 | consistent（装配侧披露） | 91 |
| inconsistent, main 在执行、执行串被 strict 身份拒绝 | unknown | 1 |

- **请特别核对：** P0 的 296 不能直接写成新合同 204；92 条 main-present
  中 91 条按冻结边界归“装配侧披露”、1 条按冻结身份 unknown。这是合同
  §1.6/§1.9 的直接结果，不是洗数。
- P0 的 52 stereo 是“整声明平键集合相等”代理；新 58 是“主产物轴立体子类”
  计数；定义不同，未互换。

### 5.2 8 项合成控制（Phase C）

`all_pass=true`：

| # | 控制 | 结果 |
|---|---|---|
| C1 | 合法主产物 + 多碎片 | consistent（额外执行组分只披露） |
| C2 | 合法 copy | consistent（事件产物侧、未执行、未进期望） |
| C3 | 仅立体差 | inconsistent / `principal_stereo_only` |
| C4 | 明确矛盾 | inconsistent / `principal_absent` |
| C5 | 解析失败 | unknown / `principal_unparseable` |
| C6 | 空声明 | not_applicable |
| C7 | 未核执行范围 | unknown / `execution_not_verified` + proof_scope |
| C8 | 开关关闭等价 | 无块；剔块 canonical 相等 |

合法正控 C1/C2、诚实 unknown C5/C7 均保留；C3 ≠ C4 子类未合并。

### 5.3 正式零漂移门（Phase D）

| 项 | 结果 |
|---|---|
| 候选成员/顺序（298 题） | mismatch **0** |
| 事件身份/内容/顺序 | **1586 vs 1586**，mismatch **0** |
| strict rank（126 题） | mismatch **0** |
| 评分语义（桶/位次） | mismatch **0** |
| 基线对 metrics 桶/rank | 298/298、126/126 |
| 剔新字段后字节等价 | payload+manifest **298/298** |
| 锚点 | hit@1 **89**、hit@3 **118**、hit@5 **125**、strict **126**、partial **53**、unmatched **119** |

### 5.4 6 个 strict 对照事件

- 126 个 strict 题中 **6 个**对照事件诊断状态为 `inconsistent`；
  **4 个 rank1、2 个 rank2**。
- 6/6 `principal_in_executed=False`、`strict_target_match=False`；
  **5 个 `principal_absent` + 1 个 `principal_stereo_only`**（与 P0 的
  “5 组分集合差 + 1 isomeric 代理”对齐）。
- 6 个均为 `novel`；逐条字段在 `phase_d/strict_control_events.json`
  （qid/event 前缀、rank、状态、子类、中心交叉、reason；无结构正文）。
- **只披露，未加门、未改分、未判化学错误。**

## 6. 请你裁决的问题

请逐项给结论（可引用证据行/计数），最后给总裁决：

1. **合同完整性：** origin、身份版本、主产物、生成组分、copy、执行/装配
   边界、适用性、proof_scope、四态互斥、unknown_reason 是否足以支撑
   “旁路披露”而不越权成硬门？四态优先级（unknown > inconsistent）是否
   可接受？`principal_stereo_only` 是否与“结构不同”清楚分开？
2. **旁路与白名单：** 5 源 + 1 新测试是否在白名单内？是否有任何改动
   实质影响 admission/候选/池/检索/排序/评分/事件提交？builder/compiler
   的纯常量函数是否构成“改装配/编译语义”？
3. **开关与版本：** 默认关闭逐字节等价是否可信？块级 schema/version +
   manifest 绑定而不升全局导出/原生结果版本，是否**放行**？若要求升位，
   是否明确授权把 `profile.py` 加入白名单并重跑门？
4. **合成控制：** 8 项是否覆盖你要求的合法多碎片/合法 copy/立体差/
   解析失败/空声明/未核范围/开关关闭？是否存在“全面拒绝换通过”或
   unknown 被洗成 consistent？
5. **正式门：** 298 候选、1586 事件、126 rank、评分语义零漂移与
   89/126/53/119 复现是否足以放行？A/B 用同一固定导出、B 仅加块并重算
   导出身份，是否满足“加字段零漂移”的证明范围？**注意证明范围：** 本门在
   “冻结导出 → 冻结 scorer”边界执行，证明加块不改变候选/事件/位次/评分；
   **不证明**在 298 题上重新执行 production/compiler/model 全链并开启开关
   （该路径由公共 `start_run` 集成测试覆盖）；B 导出是离线回放件，由离线
   读取器消费，不声称可被完整 `read_native_export` 消费。RDKit 2026.03.6
   vs 批内 2026.03.5 的版本差披露是否充分，还是要求 HPC 2026.03.5 复跑？
6. **crosswalk：** 296 → 204 inconsistent + 91 consistent + 1 unknown 的
   边界解释是否成立？新 58 stereo 与 P0 52 的定义差异是否如实、可接受？
   1 条 `executed_unparseable` 保持 unknown 是否正确？
7. **6 个 strict 事件：** 字段是否足以支持“先披露、后复核”，而不是直接
   加门/判化学错误？是否要求补化学评审或额外范围？
8. **证明范围与措辞：** 是否存在把 `inconsistent` 写成化学错误、把
   `consistent` 写成机制已证、把毛空间写收益、或把 unknown 洗成通过的
   残留？请指出具体文件/行。
9. **测试与环境：** 新测试 12 passed、既有相关测试 116 passed、全量
   2326 passed / 1 个 symlink 路径断言失败（同测试主树通过）是否足够？
   是否要求全量必须在 worktree 零失败（需复制 414MB sibling 仓）？
10. **最终裁决：** **放行**（允许主树单独 commit 合并、进入 D-2 离线
    实施书），或 **需修正**（给编号修正清单；不得自行降级门或扩范围）。

## 7. 输出格式（请写回 `docs/T_H_P0B_D6_CODEX_REVIEW_2026-10-20.md`）

1. **总裁决**（3–5 行）：放行 / 需修正；一句话理由。
2. **逐项结论**：§6 的 10 项，每项“通过 / 需修正 / 不成立”+ 证据。
3. **修正清单**（若需修正）：编号、文件、具体改法、必须重跑的门。
4. **放行范围与条件**：允许合并的文件/提交范围；D-2 启动的前置条件；
   哪些事项仍需 CC/老师另行批准。
5. **unknown/无法核清单**：本审核未覆盖或证据不足的事项。

## 8. 审核纪律（请遵守）

- 只读审核；只允许新增本报告 `docs/T_H_P0B_D6_CODEX_REVIEW_2026-10-20.md`
  与（如需）新证据目录；**不改**主树 `src/tests/scripts/docs`、不改
  worktree 代码、不改封存批根、不 push。
- 不调外部模型、不跑 HPC/sbatch、不读金标/`reference_graphs`/
  `questions.jsonl`/`llm.env`/私钥；不输出候选 SMILES 或结构正文。
- 不把“声明≠执行”判成化学错误；不把 unknown 洗成通过；不承诺收益。
- 你的裁决为**最终裁决**（代 CC/师姐）；判据变更与新增付费批仍保留
  CC/老师签字权，不在本请求授权内。
- 若你认为必须看代码行为，可在隔离副本跑只读测试；不得改主树。