# 复审请求 — T-H P0b/D-6 R1–R4 回修（2026-10-21）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文全部计数、
> 锚点与结论只在该题域成立，不外推到 dev、新题或其他题域。
>
> **请求类型：** 对你 2026-10-21 终审 §4 R1–R4 的**限定范围回修**做复审，
> 按 §5 放行条件给**放行 / 需修正**裁决。不重开已关闭的设计争议
> （旁路方案、块级版本、冻结导出→scorer 窄门、不复制 sibling 仓）。
>
> **边界：** 只改白名单五文件 + 本任务测试；主树未合并、未 push；未加硬门、
> 未改 admission/候选/池/检索/排序/评分，未修 D-3/D-7，未跑 HPC、未调模型、
> 未读金标/题面/参考图/凭证/封存逐题 run。**零金标、零题面、零凭证。**
>
> **R4 状态：** 规则级化学评审此前置**尚未完成**；本轮只落自包含请求
> `docs/T_H_P0B_D6_CHEM_REVIEW_REQUEST_2026-10-21.md`，未送审、未冒充已评。
> 本复审请求不要求你把程序审核当成化学终认。

## 1. 基线与环境

| 项 | 值 |
|---|---|
| 基线 HEAD | `c9c6c7a7ae02b46769add09fbc2536323ce8a985` |
| 独立 worktree | `/tmp/dependingv43_p0b`（主树未合并、未改） |
| 新 patch | `docs/review_evidence/t_h_p0b_fix_2026-10-21/impl.patch`（6 文件：5 源 + 1 新测试） |
| patch SHA256 | `035123de8fbd564c0632f665d31743433191cb25dbc3d85a82972cdde9204aa4` |
| 新证据目录 | `docs/review_evidence/t_h_p0b_fix_2026-10-21/` |
| 原交付证据（只读保留） | `docs/review_evidence/t_h_p0b_2026-10-20/`（未覆盖、未重跑写入） |
| 固定历史输入 | `/tmp/t_h_p0_r2/runs/<run_id>/native_export/<digest>/`（298 payload+manifest） |
| 批清单/案例/参考图 | `/tmp/t_h_p0_r2/scoring/`（参考图只读装入并做 sha 核对，仅传给冻结 scorer；未检查内容、未复制/打印/落盘/人工读取） |
| 判分 | 冻结 `evaluate_scientific` + criteria v2，零判据改动 |
| Python/RDKit | 3.11.16 / **2026.03.6**（批内登记 **2026.03.5**；版本差已披露） |
| 模型/HPC/网络 | 0 / 0 / 0 |

## 2. 请按序阅读

| 文件 | 作用 |
|---|---|
| `docs/T_H_P0B_D6_CODEX_REVIEW_2026-10-20.md` | 你的终审报告（R1–R4 与 §5 放行条件） |
| `docs/T_H_P0B_D6_CONTRACT_2026-10-20.md` | 已回修合同（v2：R1 多重集、R2 unknown、R3 立体代理/新子类） |
| `docs/T_H_P0B_D6_IMPL_2026-10-20.md` §12 | R1–R4 逐条回修记录与新子类解释 |
| `docs/review_evidence/t_h_p0b_fix_2026-10-21/impl.patch` | 全部代码改动（主树未合并） |
| `docs/review_evidence/t_h_p0b_fix_2026-10-21/phase_c/` | 35 项合成正负控（含原 C1–C8 与 R1–R3 两层矩阵） |
| `docs/review_evidence/t_h_p0b_fix_2026-10-21/phase_d/` | 正式零漂移门：candidate/event/rank/score diff、strict 6 事件、聚合 crosswalk、provenance、摘要 |
| `docs/review_evidence/t_h_p0b_fix_2026-10-21/test_evidence.md` | 测试命令/结果/patch 应用验证 |
| `docs/T_H_P0B_D6_CHEM_REVIEW_REQUEST_2026-10-21.md` | R4 规则级请求（未送审；诚实登记） |
| `docs/review_evidence/t_h_p0_2026-10-20/p0b_declared_vs_executed.json` | P0 历史探针读数（仅 crosswalk；不是新判据） |

## 3. R1–R4 回修内容（供逐条核对）

### R1 装配多重集与 copy 引用

| 项 | 实现 |
|---|---|
| 装配轴 | `production.reconcile_declared_vs_executed` 对 novel coproduct 使用**声明生成组分整体多重集**（主产物 + coproducts，保留重复）对事件产物侧做共同多重集包含；`declared_generated_present`/`copies_present` 改为 `Counter` 交集计数 |
| 重复份数 | 重复 coproduct 缺一份 ⇒ `declared_coproduct_missing_from_event`，不再因“同结构出现过”复用同一出现 |
| copy 引用 | `copy.in_event_products` 严格按声明 `state_ref` 非空精确匹配事件产物侧引用；结构对应移到新字段 `copy.structure_in_event_products`，仅披露、不参与合法性 |
| 新增控制 | reconcile + derive 各 4 项：重复缺一份（负）、份数齐全（正）、copy 引用缺失（负）、合法 copy（正），全过 |
| 真实数据 | 事件级计数不变（1381/204/1/0），crosswalk 仍 1290/204/91/1；未发现真实事件因该轴翻转 |

### R2 缺资料保留 unknown

| 项 | 实现 |
|---|---|
| 聚合入口 | `native_result._p0b_d6_event_body` 缺失/非对象/解析失败返回 `None`；新 `_p0b_d6_product_participants` 区分“不可用”与“合法空列表”；不再 `participants or []` |
| 来源优先 | `not_applicable` 增加来源在位条件（report/spec 可核、execution 在位且 `execution_ok/result.ok`）；报告缺失先 `missing_production_report`，spec 缺失先 `missing_spec` |
| 装配 unknown | 需要装配比较但资料不可用/坏类型 ⇒ `unknown / event_assembly_unavailable`，写入 `proof_scope.unverified_ranges`；不需要装配时不因不可解析误伤 |
| 坏类型 | spec 的 product/coproduct/copy/expectation 坏类型不再静默归一成空，按对应 `*_unparseable` 阻断 |
| 新增控制 | 报告缺失、spec 缺失、资料缺失/坏类型、明确空参与物、已知空声明、合法完整、确有矛盾、解析失败；reconcile 与 derive 两层覆盖，全过 |
| 保留正控 | C6 已知空声明仍 `not_applicable`；C5/C7 诚实 unknown 保留 |

### R3 立体子类不得覆盖同位素差

| 项 | 实现 |
|---|---|
| 身份 | 既有 strict 身份仍是唯一相等来源 |
| 立体代理 | 新 `p0b_d6_nonstereo_component_keys`：`RemoveStereochemistry` 后以 `isomericSmiles=True` 写回并按 strict 身份规范化，**保留同位素/电荷/连接/SGroup**；只有 strict 不等且该代理相等才 `principal_stereo_only` |
| 诚实未细分 | 旧非异构代理（`isomericSmiles=False`）相等但去立体代理不等 ⇒ 新子类 `principal_isomeric_unspecified`；不洗成 `consistent`，不沿用 `stereo_only` 强义 |
| 连接差 | 两个代理都不等 ⇒ `principal_absent` |
| 披露字段 | `principal_nonstereo_in_executed`（唯一支持 stereo_only）、`principal_nonisomeric_in_executed`（披露）、`principal_flat_in_executed`（兼容旧非异构代理，仅披露） |
| 版本 | 块内 `schema=p0b-declared-vs-executed-1`、`version=2`、`rule_version=p0b-d6-reconcile-2`；manifest 绑定同核 schema/version/rule_version/digest；**未升**全局导出/原生结果版本 |
| 新增控制 | 真实合成立体差、纯同位素差、连接差、解析 unknown；reconcile 与 derive 两层覆盖，全过 |
| 真实计数 | `principal_absent=146`、`principal_stereo_only=58`、`principal_isomeric_unspecified=0`。计数与原 58 相同，但**依据变强**：58 条现在通过保留同位素的去立体代理验证；旧代理不再能单独支持该子类。未把 58 写死为验收目标。 |

### R4 规则级化学评审前置

| 项 | 状态 |
|---|---|
| 事实 | 终审前**未见**本任务专门的规则级请求/回应或与程序证据互证的结论；此前置**未完成** |
| 本轮 | 已落 `docs/T_H_P0B_D6_CHEM_REVIEW_REQUEST_2026-10-21.md`（自包含、零金标零题面、规则级） |
| 送审 | 本轮**未调用外部模型**；通道与采信由 CC/Codex 决定 |
| 限度 | 程序正负控/零漂移门不替代化学终认；不倒填为“实施前已评” |

## 4. 关键读数

### 4.1 Phase C（35 项，`all_pass=true`、`all_checks_pass=true`）

- 原 C1–C8 全部保留并通过（合法多碎片、合法 copy、合成立体差、明确矛盾、
  解析失败、空声明、未核执行、开关关闭等价）。
- R1 8 项、R2 13 项、R3 6 项（含 reconcile 与 derive 两层）；每项的
  `checks` 均进入 `all_pass`，不重复旧脚本“pass 只看状态”的弱点。
- 合法正控与诚实 unknown 均保留；未出现“全面拒绝换通过”。

### 4.2 pytest（worktree）

| 命令面 | 结果 |
|---|---|
| 新测试 `test_p0b_declared_vs_executed.py`（12 原 + 23 新） | **35 passed** |
| 新测试 + 相关既有（s3b production / s4a endpoint / s4b export / s5b build identity / s5b cosub supply / s5b product identity gate）+ T11 | **152 passed** |
| off/default/on→export 公共集成 | 包含在 35 passed 内；关闭无块且剔块 canonical 等价，开启 manifest 绑定可显式读取 |

### 4.3 Phase D 正式零漂移门

| 门项 | 结果 |
|---|---|
| 候选成员/顺序（298 题） | mismatch **0** |
| 事件身份/内容/顺序 | **1586 vs 1586**，mismatch **0** |
| strict rank（126 题） | mismatch **0** |
| 评分语义（桶/位次） | mismatch **0** |
| 基线对 metrics 桶/rank | 298/298、126/126 |
| 剔新字段后字节等价 | payload+manifest **298/298** |
| 锚点 | hit@1 **89**、hit@3 **118**、hit@5 **125**、strict **126**、partial **53**、unmatched **119** |

crosswalk（1586 事件，P0 行缺失 0）：1290 consistent / 204
main-absent inconsistent / 91 main-present consistent / 1 unknown。
新四态：1381 / 204 / 1 / 0；子类 146 absent + 58 stereo_only + 0 unspecified。

### 4.4 6 个 strict 对照事件

- 126 个 strict 题中 **6 个**对照事件为 `inconsistent`；**4 个 rank1、
  2 个 rank2**。
- **5 个 `principal_absent` + 1 个 `principal_stereo_only`**；6/6
  `principal_in_executed=false`、`strict_target_match=false`；均为 novel。
- 该 1 条 stereo 事件在新代理下
  `principal_nonstereo_in_executed=true`（保留同位素后仍相等），因此
  `stereo_only` 现在有可复核依据；仍只是程序子类，不是化学终判。
- 只披露；未加门、未改分、未判化学错误。

## 5. 请你按固定面复核的问题

1. **R1 是否闭合：** 共同多重集包含/交集计数是否消除了“同结构出现过”的
   无限复用？重复 coproduct 缺一份负控、份数齐全正控、copy 引用缺失负控、
   合法 copy 正控在 reconcile 与 derive 两层是否都成立？copy 结构轴是否
   已与引用轴分离且未替代？
2. **R2 是否闭合：** 报告缺失、spec 缺失、资料缺失/坏类型是否都保留
   `unknown` 并写入 `unverified_ranges`？明确空参与物是否仍判确定性不一致、
   已知空声明是否仍 `not_applicable`？是否仍存在 `or []` 类归一化？
3. **R3 是否闭合：** `stereo_only` 是否只在去立体（保留同位素）代理相等时
   输出？纯同位素差是否落到诚实未细分 `principal_isomeric_unspecified`
   而不是 `stereo_only` 或 `consistent`？连接差是否仍 `principal_absent`？
   块内版本/规则版本是否同步且未升全局版本、未改评分？
4. **R4 是否按“诚实登记”处理：** 是否接受“此前置尚未完成 + 请求已落盘但
   未送审”的登记，而不把本次程序复审当作化学终认？是否要求先取得规则级
   回应再放行，或允许程序面先放行、化学评审作为单独挂账？
5. **回归与零漂移：** 新正负控、原 C1–C8、相关既有测试/T11、Phase C 全量、
   修后 Phase D 与 crosswalk 是否足以支持“R1–R3 闭合、候选/事件/rank/评分
   零漂移、锚点 89/118/125、126/53/119 复现”？证明范围是否仍限
   “冻结导出→冻结 scorer”，未冒充 298 题 production/compiler/model 全链？
6. **最终裁决：** 按你 §5：**放行**（允许单独 commit 合并；R4 化学评审作为
   明确挂账/前置）或 **需修正**（只列 R1–R4 同合同内的具体项，不扩
   D-1/D-3/D-7、不加硬门、不要求 HPC 重跑或 sibling 仓复制）。

## 6. 输出格式（请写回 `docs/T_H_P0B_D6_CODEX_REVIEW_2026-10-20.md`
或新报告 `docs/T_H_P0B_D6_CODEX_REREVIEW_2026-10-21.md`）

1. **总裁决**（3–5 行）：放行 / 需修正；一句话理由。
2. **R1–R4 逐条结论**：闭合 / 未闭合 + 证据（文件、行、控制项）。
3. **回归与零漂移**：锚点与 crosswalk 是否复现；证明范围是否被夸大。
4. **修正清单**（若需修正）：编号、文件、具体改法、必须重跑的门；
   不得借机扩范围。
5. **放行范围与条件**：允许合并的提交面；D-2 前置；R4 化学评审如何挂账；
   哪些事项仍需 CC/老师另行批准。
6. **unknown/未覆盖**：本轮证据不能证明的事项。

## 7. 审核纪律

- 只读审核；只新增复审报告与必要证据目录；**不改**主树 `src/tests/scripts/docs`、
  不改 worktree 代码、不改封存批根、不 push。
- 不调外部模型、不跑 HPC/sbatch、不读金标/`reference_graphs`/
  `questions.jsonl`/`llm.env`/私钥；不输出候选 SMILES 或结构正文。
- 不把“声明≠执行”判成化学错误；不把 unknown 洗成通过；不承诺收益。
- 你的裁决为最终裁决（代 CC/师姐）；判据变更与新增付费批仍保留
  CC/老师签字权，不在本请求授权内。
- 若需看代码行为，可在隔离副本跑只读测试；不得改主树。