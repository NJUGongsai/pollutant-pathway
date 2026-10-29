# T-H P0b/D-6 R1–R4 回修复审（qwen3.8max 代 Codex，2026-10-21）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告全部计数、
> 锚点与结论只在该题域成立，不外推到 dev、新题或其他题域；合成控制不是
> 科学性能。
>
> **provenance：本报告是 qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示
> 与 `docs/QWEN3_8MAX_REREVIEW_PACKAGE_2026-10-21.md` 授权执行；不冒充
> Codex 本人。** Codex 终审 `docs/T_H_P0B_D6_CODEX_REVIEW_2026-10-20.md`
> 保留为历史意见，不因本报告改写；若 Codex 05:20 自动重试产出新报告，
> 两套并存，采信顺序由 CC 决定。
> **审核对象：** 基线 HEAD `c9c6c7a7ae02b46769add09fbc2536323ce8a985` +
> `docs/review_evidence/t_h_p0b_fix_2026-10-21/impl.patch`
> （SHA256 `035123de…204aa4`，本轮实测吻合）；主树未合并。
> **审核纪律：** 只读主树；本轮独立执行全部在隔离副本
> `/tmp/qwen_rereview_p0b`（rsync src/tests/scripts/assets + git apply），
> 禁字节码/pytest 缓存；未跑 HPC、未调外部模型、未读金标/题面/
> `reference_graphs` 内容/`llm.env`/私钥；参考图仅由冻结 scorer 进程内
> 只读消费（与提供方脚本同规格，本审核未检查/复制/打印其内容）；
> 证据落 `docs/review_evidence/qwen_rereview_2026-10-21/task_a/`。

## 1. 总裁决

**放行（附条件）。** R1–R3 按 Codex 终审 §4 闭合：本轮不仅核对了提供方
证据，还在隔离副本**独立复现**了 35 项新测试、152 项相关既有测试、
35 项 Phase C 正负控、完整 Phase D 零漂移门与聚合 crosswalk，并用自己的
9 项同根反例探针确认 Codex 原三个反例全部按合同 v2 fail-closed；候选/
事件/rank/评分 mismatch 全 0，锚点 89/118/125、126/53/119 精确复现。
R4 规则级化学评审**尚未取得回应**，按“诚实登记 + 单独挂账”处理：
允许单独 commit 合并，但 **D-2 离线实施书启动前必须取得 R4 规则级回应
并与程序证据互证**（见 §5）。

## 2. R1–R4 逐条结论

### R1 装配多重集与 copy 引用 — **闭合**

| 核点 | 证据 |
|---|---|
| 共同多重集包含/交集计数 | patch `production.py`：`_p0b_d6_subset`/`_p0b_d6_missing`/`_p0b_d6_covered` 全部用 `collections.Counter`（多重集语义，同一出现只消费一次）；装配轴 `declared_generated`（主产物⊕coproducts，copy 不计入）对 `assembly_keys` 做包含判定 |
| Codex 反例一（重复 coproduct 缺一份曾判 consistent） | 本轮独立探针 P1：公开 derive 路径现输出 `inconsistent / declared_coproduct_missing_from_event`、`declared_generated_present=2`；正控 P2 份数齐全 `consistent`、计数 3（`qwen_probe_result.json`） |
| Codex 反例二（copy 引用 OR 结构） | `copy_in_event = all(ref and ref in ref_set)` 严格按声明 `state_ref`；结构对应移到 `structure_in_event_products` 仅披露。探针 P3：异 ref 同结构 ⇒ `copy_contract_violation`、引用轴 False、结构轴 True |
| 两层覆盖 | 测试文件 R1 reconcile 层 3 项 + derive 层 4 项；Phase C R1 共 8 项（本轮独立复跑全过）；空 `state_ref` 的 copy 条目按引用缺失处理（`bool(ref)` 条件），无静默豁免 |

### R2 缺资料保留 unknown — **闭合**

| 核点 | 证据 |
|---|---|
| 聚合入口不再 `or []` | `native_result._p0b_d6_event_body`：缺失/非对象/解析失败 ⇒ `None`；`_p0b_d6_product_participants`：参与物缺失/非列表/条目非对象/产物侧 `state_ref` 缺失 ⇒ `(None, None)`，合法空列表 ⇒ `([], [])`——“不可用”与“已核为空”在类型上分离 |
| Codex 反例三（participants 删除曾判 inconsistent） | 探针 P4：现输出 `unknown / event_assembly_unavailable`，且写入 `proof_scope.unverified_ranges` |
| Codex 反例四（report 缺失曾提前 not_applicable） | 探针 P5：derive 层现输出 `unknown / missing_production_report`、`applicability=applicable`；reconcile 收 `production_report_present` 参数，`missing_production_report`/`missing_spec` 在冻结枚举序最前 |
| `not_applicable` 收紧 | 仅当来源在位 + `execution_ok/result.ok` 真 + 主产物/执行/coproducts/copy 均确知为空 + 无坏类型标记（`known_empty` 条件）；C6/R2-e 正控保留 |
| 坏类型阻断 | `build_declaration_disclosure` 的 `*_invalid` 标记 ⇒ 对应 `*_unparseable` 阻断，不再静默归一成空 |
| 明确空参与物 | `participants=[]` 且需装配比较 ⇒ 确定性 `inconsistent`（R2-d/P 探针外的测试 `test_r2_*_explicit_empty_*` 两层覆盖），未升级成 unknown |
| 残留 `or []` 检查 | reconcile/derive 中剩余 `or []` 只作用于顶层迭代列表（states/search_actions/reports）与已经过类型校验的 disclosure 字段，不在参与物/装配语义路径上 |

### R3 立体子类不得覆盖同位素差 — **闭合**

| 核点 | 证据 |
|---|---|
| 去立体代理保留同位素 | `p0b_d6_nonstereo_component_keys`：`MolFromSmiles → RemoveStereochemistry → MolToSmiles(isomericSmiles=True) → strict_identity_of`；同位素/电荷/连接/SGroup 保留，仅去四面体/双键/增强立体 |
| Codex 反例五（纯同位素差曾标 stereo_only） | 探针 P6：现输出 `principal_isomeric_unspecified`（诚实未细分），`principal_nonstereo_in_executed=False`、`principal_nonisomeric_in_executed=True`；正控 P7 真实立体差仍 `principal_stereo_only` 且 nonstereo 代理为 True |
| 子类优先级 | `principal_in_executed is False` 时按 nonstereo → nonisomeric → absent 顺序取第一个成立者，三子类互斥；不洗成 consistent |
| 版本承载 | 常量 `P0B_D6_DIAGNOSTIC_VERSION=2`、`RULE_VERSION="p0b-d6-reconcile-2"`；探针 P8 确认逐事件行携带；聚合确认 298 个导出块全部 v2/reconcile-2；未升全局 `ppv1-native-result-2`/`ppv1-native-export-3`，未改评分（Phase D 零漂移佐证） |
| 兼容字段 | `principal_flat_in_executed` = 旧非异构代理，仅披露；`read_declared_vs_executed` 对 version≠2 fail-closed，旧 v1 块不被新读取器消费 |

### R4 规则级化学评审前置 — **诚实登记成立；作为挂账项，不视为已闭合**

- 事实核对：`docs/T_H_P0B_D6_CHEM_REVIEW_REQUEST_2026-10-21.md` 已在盘，
  内容自包含、规则级（R0–R4 摘要 + 8 个评审问题 + 判定词格式）、零金标
  零题面零结构正文，头部明确“本轮尚未送审”“程序审核不等于化学终认”。
  合同 §5、实施报告 §12.4、provenance `r4_status.completed=false` 三处
  登记一致，未倒填、未冒充已评。
- 本报告的程序结论**不冒充**化学终认；`principal_stereo_only` 等子类
  仍是程序标签。R4 的处置决定见 §5（挂账方式），这是本代复审对
  复审请求 §5.4 问题的正式回答。

## 3. 回归与零漂移（本轮独立执行，非采信提供方读数）

| 项 | 提供方声明 | 本轮独立复跑结果 |
|---|---|---|
| 新测试文件 | 35 passed | **35 passed**（隔离副本） |
| 新测试+相关既有+T11 | 152 passed | **152 passed**（首跑 19 failed 系我方最小副本缺 `assets/`，补齐后全绿；非代码回归，已留档说明） |
| Phase C | 35/35，all_pass+all_checks_pass | **35/35 全过**；checks 字典已并入 pass 判定（`phase_c_controls.py:217`），旧“pass 只看状态”弱点确认修复；合法正控 6 项、诚实 unknown 11 项保留 |
| Phase D 零漂移门 | all_gate_items_pass=true | **true**：候选 mismatch 0（298 题）、事件 1586 vs 1586 mismatch 0、strict rank 126 mismatch 0、评分桶/位次 mismatch 0、剔块字节等价 strip_ok 298/298、对基线 metrics 桶 298/298 rank 126/126 |
| 锚点 | 89/118/125、126/53/119 | **A/B 两臂均精确复现**（hit@1 89、hit@3 118、hit@5 125、strict 126、partial 53、unmatched 119） |
| 聚合/crosswalk | 1381/204/1/0；146+58+0；1290/204/91/1 | **逐位复现**；算术闭合（1290+204+91+1=1586；146+58=204；1381=1290+91）；P0 行缺失 0 |
| 6 个 strict 对照事件 | 4 rank1+2 rank2、5 absent+1 stereo_only、全 novel | **一致**；stereo_only 事件（`ppev_df52361d5d85466`）`principal_nonstereo_in_executed=true`、块版本 v2/reconcile-2，子类判定有可复核依据（仍是程序标签，非化学终判） |
| 独立反例探针 | — | **9/9 通过**（P1–P9，含输出无结构正文检查） |

**证明范围核对：** 零漂移门证明范围仍限“冻结导出 → 冻结 scorer”；
实施报告 §3 与 test_evidence.md §3 明确未声称 298 题 production/
compiler/model 全链重跑，未冒认历史全量读数。RDKit 2026.03.6 vs 批内
登记 2026.03.5 的版本差已披露且历史桶/rank 对齐。**未发现证明范围
夸大。** 白名单核对：patch 恰为 5 源文件 + 1 新测试；production.py 仅
新增 import 与文件尾追加段，既有 prepare/execute/expand 函数未改；
builder/compiler 仅新增常量与返回副本的纯函数；native_export 仅在块
存在时新增 manifest 绑定；主树 `src/tests` 零 diff（本轮 git status 实测）。

## 4. 修正清单

**无。** 未发现 R1–R4 同合同内的新阻塞缺陷。不构成阻塞的两条观察
（无需回修，留档）：

1. `_p0b_d6_relation` 末位 `return "equal"` 是不可达兜底（双侧 missing
   均为 0 时首分支已捕获）；行为正确，仅是冗余。
2. `known_empty` 分支的 `not blocking` 条件在当前代码路径下恒真
   （该点之前可加入的 blocking 均被 known_empty 条件排除）；作为
   防御性写法可保留。

## 5. 放行范围与条件

| 项 | 决定 |
|---|---|
| 合并 | **允许**按 Codex 终审 §5 的提交面单独 commit：白名单五源文件 + 本任务测试 + 修订合同/交付书/请求文档。不 push 组织仓与否仍按仓库既定推送纪律由 CC 拍板 |
| R4 挂账方式（对复审请求 §5.4 的回答） | **程序面先放行，化学评审作为单独硬挂账**：R4 规则级回应取得并与修后程序证据互证之前，(a) 不得启动 D-2 离线实施书；(b) 不得在对外材料中把 `principal_stereo_only` 等子类当作化学结论引用。送审通道由 CC 决定（原 mimo 通道已退役，通道选择不在本审核授权内） |
| 与 Codex 终审的差异点（逐条列出，不静默） | Codex §5 原文“R1–R4 收口……才允许单独合并”。本报告判定 R1–R3 收口 + R4 诚实登记成立，将 R4 从“合并前置”调整为“D-2 启动与对外化学引用的前置”。理由：R4 的剩余动作（送审取得回应）依赖 CC 决定的外部通道，非实施方可闭合项；块本身只披露、默认关闭、零评分影响，合并风险受控；复审请求 §5.4 明确授权本报告在两种处置中作选择。**若 Codex 复权重申“回应先行才可合并”，以 Codex 正链裁定为准** |
| 已关闭争议 | 旁路方案、块级版本、冻结导出→scorer 窄门、不复制 sibling 仓：维持 Codex 终审结论，不重开 |
| 仍需 CC/老师另行批准 | 判据/strict 认可口径变化、新增付费批、真实题面/金标/参考图外发、push 与发车顺序——均不在本放行范围内 |

## 6. unknown / 本审核未覆盖

| 项 | 限制 |
|---|---|
| 化学真伪 | 6 个 strict 对照事件与 58 条 `principal_stereo_only` 的化学正确性、机制、生物可行性均 unknown；本审核未读任何真实结构 |
| R4 回应 | 规则级化学评审未取得；本报告不构成化学终认 |
| 历史环境 | RDKit 2026.03.5 下新子类标签等价性未证明（版本差已披露、锚点对齐） |
| 全链 | 未重跑 298 题 production/compiler/model；未执行全量 pytest（历史 2326/1/20 读数按来源登记，不冒认） |
| 逐行语义 | `read_declared_vs_executed` 核块级完整性（schema/version/计数闭合/digest），不逐事件重派生语义；返回成功≠逐行正确性认证 |
| 扩批 | 事件前缀 join 唯一性只在本批 1586 事件验证；未来批扩大用途时再闭合 |
| T-I/远端 | 本审核不裁定远端 T-I 状态或发车顺序 |

**裁决效力：本报告为 qwen3.8max 代 Codex 的复审裁决（放行，附 §5 条件），
按 CC 2026-10-21 指示出具；与 Codex 正链报告并存，最终采信顺序归 CC。**
