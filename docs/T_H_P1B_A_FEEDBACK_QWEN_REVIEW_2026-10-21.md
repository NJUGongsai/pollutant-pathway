# T-H P1-B A（修复反馈）复审报告（2026-10-21）

> **provenance：qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示。**
> 非 Codex 正链终审、非 CC 本人；结论采信到与程序证据互证为止。
> 题域：**[298域] = RHEA 通用酶学 / 已见题（post-hoc）**；合成控制不是
> 科学性能，不外推 dev/新题。
>
> 审阅对象：`docs/T_H_P1B_A_FEEDBACK_QWEN_REVIEW_REQUEST_2026-10-21.md`
> 所列 8 件。基线 HEAD `11aeeaf`（本审实际主树 HEAD 同值，经
> `git rev-parse` 记录）。patch SHA256 实测
> `b9d91f985c152a7633cd5cc213aa253829addcba5eebae42fa7f93fcd9d181d4`
> = 请求声明值；证据目录无 SHA256SUMS 文件（SHA 内联在请求/实施报告，
> 已核对一致）。本审只读；未改 src/tests/既有 docs/证据原件；未跑
> HPC/真实模型；未读金标/题面/reference_graphs 内容/llm.env/私钥；
> 本文不输出结构正文。
>
> **本审独立执行的核验**（隔离副本，PYTHONDONTWRITEBYTECODE=1、
> `-p no:cacheprovider`，环境 ~/miniconda3/envs/depending43）：
> 1. `git archive 11aeeaf` 全新导出 `/tmp/qwen_p1b_verify` →
>    `git apply --check` + 应用 patch 通过；
> 2. 实现方 worktree `/tmp/dependingv43_p1b` 的 `git diff HEAD` 与
>    impl.patch **逐字节同 SHA**（b9d91f98…）；
> 3. 新测试 16 项在隔离副本独立复跑：**16 passed**；
> 4. 相关既有面抽跑：production/queue/runner/endpoint/export/
>    search/batch/export_v2/v3/p0b 10 文件 **235 passed**；
>    model/chain14 重试/r2r3 rework/edit_protocol/r2_storage 6 文件
>    **197 passed**；
> 5. `disclose_equivalence.py` 复制到 `/tmp/qwen_p1b_eq` 独立重跑
>    （不在证据目录原地跑）：三方 SHA256 均
>    `ab8e976a0324212dff518f627e321fddcd22eddb54c488ecc50318ee0378fed1`，
>    all_pass=true，与落盘证据一致；
> 6. 主树 `tests/test_engine_asset_parity.py` 复跑 **10 passed**，
>    证实全量日志唯一失败（symlink 环境路径）与 patch 无关、披露如实；
> 7. 146 分类 JSON 逐字段重算（见 Q7/必核 5）。

## 1. 总裁定

**放行（附条件）**。触发面、预算复用、disclose 零漂移、实现边界、
身份门均有代码+独立复跑证据支撑，无同合同内阻塞缺陷；条件 =
§3 最小回修 1 项（一处潜在 TypeError，一行修复）+ §6 预注册前置
由 CC/Codex 正链确认。具备进入 P1-B 预注册**起草**的条件；预注册
批准与付费发车不归本审。

## 2. 逐项结论（Q1–Q8）

| # | 结论 | 依据摘要 |
|---|---|---|
| Q1 触发 | **sound** | production.py 触发条件仅 `status=="inconsistent" and inconsistency_subclass=="principal_absent"`；判据复用 P0b 单一入口 `reconcile_declared_vs_executed`（无第二套结构字符串比较）；对账段插入点在 `decide_admission` 不可提交早退之后（主树 production.py:1180-1187 早退先于 1218 插入点），只消费可提交候选。origin 前缀规则与 `native_result._p0b_d6_origin` 同常量同源（均 `ATTEMPT_STATUS_RECORDED`，controlled_vocab）。非 absent 六组（consistent/stereo/isomeric/copy 违规/unknown/not_applicable）由 6 组参数化测试 + consistent 真链正控证明不反馈、不拒、正常提交 |
| Q2 反馈内容 | **sound** | `reconciliation_feedback` 块只含模型自己的 current_reaction_spec/声明主产物/共同产物/执行碎片/对账计数/relation/boundary/rank1 归属 + 底物 execution_graph + 指令；`pool_entries=[]` 防改选池候选。全 patch 无任何金标/参考图/题面读取路径。指令要求 expectation/声明不变，且**代码层强制**（身份字段校验），不依赖模型服从 |
| Q3 预算 | **sound** | purpose 仍 `format_feedback`；轮数仍 `format_feedback_rounds_used`（持久计数，排除 retry_of 行）；上限仍 `max_format_feedback_rounds`（T-I 预注册 line 82 = 2，实测核对）；real provider 经 `register_format_feedback_round → ledger.register_model_request` 即时占 `max_real_model_requests`（search.py 预约+`SearchBudgetExhausted`），耗尽被 `_run_expand` 捕获 → 残余拒 `feedback_budget_exhausted`，与「不新增调用预算」一致。新类别经独立 `RECONCILIATION_FEEDBACK_ELIGIBLE` 参数放行，默认 `FEEDBACK_ELIGIBLE` 不变；测试证明不带该参数时新类别被拒（`feedback_ineligible_error`），既有四类 JSON 反馈语义/预算未被侵占。0 轮预算 → 直接残余拒、零反馈行（测试证实）。无新 purpose/计数器/上限 |
| Q4 流程与身份 | **sound（1 处潜在缺陷，见 §3）** | 执行→对账→未提交（`revision_required` 裸返回，不写报告不落事件）→登记/复用反馈轮→解析 revised→身份保持（20 个字段 JSON 规范形比较；缺席字段从当前 spec 保留；只拷贝 edits/donor/alignment）→`validate_edits` + edits 必须变化→`prepare_hypothesis` 重建→`hypothesis_id == subject_ref` 冻结门→重执行重对账→非 absent 才提交。坏响应/改身份/edits 非法或未变 ⇒ 当轮失败**直接残余拒**（不花第二轮）。2 轮耗尽 ⇒ 拒；拒路径不写事件、`admission_rejected` outcome 带 p0b_d6/history、`write_reconciliation_rejection_report` 落 rejected 报告、分母不变。传输失败 ⇒ `_call_real_fetch` 包装 `PPV1RunError` → 驱动层 run_error → 失败题留分母，不吞成拒/成功。resume 复用走 `latest_format_feedback_round` 统一身份门（原键重算/payload_hash 同源核验），坏行/跨 attempt ⇒ `feedback_round_identity_corrupt` 结构化拒，fail-closed。绕过面：expectation/声明主产物均在身份字段清单内，改任一 ⇒ 拒；无发现可绕过路径 |
| Q5 disclose 零漂移 | **sound** | `policy != disclose` 守卫全部对账段；submitted_extra 仅 feedback 臂加键。本审独立重跑三方等价（§0 provenance 第 5 项）SHA 全同；证明范围如实限定（合成场景、不含 run_identity、不替代 298 全链重跑——equivalence JSON note 原文写明）。disclose 测试断言 reconcile 不被调用、返回值与持久报告均无 p0b_d6 键。gate 仅对照/残余：测试证 0 model_requests 行、直接拒 |
| Q6 测试 | **sound（有非阻断缺口）** | 16 项独立复跑全过；断言是行为级（events 计数、model_requests 行、报告 artifact、outcome detail、history 序列），非只看 status。全量 2365/1 如实披露且本审证实该 1 失败为主树通过的环境路径问题；203 相关面与本审抽跑（235+197 全绿）互证。缺口（不阻断）：resume/复用路径、run 级真实预算耗尽 outcome、非 model_declared 边界残余拒、edits 未变/非法/prepare 失败/多 novel/不可解析响应各分支无直接测试（仅改声明主产物分支有） |
| Q7 红线与范围 | **sound** | patch 恰 4 源 + 1 新测试（diff --git 清单核对）；decide_admission/ADMISSION_SUBMITTABLE/R1–R7/评分/池/检索/排序/prompt 版本零触碰；无第六源码文件；不回溯旧批；stereo 不当「未执行」（触发仅 absent；strict_control_events.json 证实 6 strict = 5 absent + 1 stereo，分类内 5 条 rank 分布 {rank1:3, rank2:2} 与声明一致）。「146 真不符/0 合法多步/0 unknown」是**程序级**分类且 JSON limits 原文写明「not a chemical error verdict / chemical truth remains unknown」，未过度解读。33 题多 absent 争用每题 3 请求的代价在 JSON notes 与设计 §2A.8 如实登记 |
| Q8 总体 | 见 §1/§3/§5/§6 | 无阻塞缺陷；1 项最小回修 + 若干非阻断观察；具备预注册起草条件 |

**必核 5（146 分类是否支持 A 首选、B 残余）**：JSON 逐字段重算全部
吻合声明——146 事件/95 题/146-0-0 分类/disjoint 66/overlap 80/共同
产物 0:35,1:91,2:20/5 strict absent（3 rank1+2 rank2）/33 题多 absent
（2 条×18、3 条×13、4 条×1、5 条×1）。146 条全部 novel、
principal_boundary=model_declared、无 compile、net_reaction、rank1
归属与声明一致、expectation 含声明主产物 ⇒ **全体落在 A 可作用面内，
无边界排除项**，程序级支持「A 首选、B 残余」。但该分类只证明目标
人群均质可寻址，**不证明 A 能救回任何一条**——A 实际回收率在所有
交付物中均如实标 unknown（设计 §2A.8/§3.2、实施 §7、请求 §4），
本审确认无一处把 unknown 写成预期收益。66 disjoint 比 80 overlap
更难救的定性也如实标注为「不承诺收益」。

**必核 6（崩溃风险是否可接受）**：修订 spec 仅在进程内存；崩溃后
resume 从 action 冻结原始 spec 重跑。两条可能路径均 fail-closed：
(a) 同 attempt 且响应已落盘 ⇒ 身份门核验通过后 R3 重放修订（零新增
付费调用）；(b) attempt/载荷不符 ⇒ `feedback_round_identity_corrupt`
结构化拒 → run 失败、题留分母、**不静默提交错误事件**。就效度而言
可接受（最坏损失是题目产出，不是坏事件入册）；但 (b) 把「本可残余
拒」转成「run 失败」，若 HPC 崩溃率不可忽略，A 臂失败题数可能高于
gate 臂——请求方已如实声明 B1–B4 未闭合。**是否要求付费批前先做
修订 artifact 持久化，归 CC 预注册拍板**，本审不代决；预注册文本
必须登记该失败模式及其分母后果。多轮反馈对 3 请求预算的影响见 Q3：
共享即时占额，无膨胀；33 题争用代价已登记。

## 3. 必须修正项（最小回修清单，仅请求范围内）

1. **`_p0b_d6_event_product_side` 裸 `return None`**（production.py，
   patch 行 349）：参与物出现非 dict 条目时返回单值 `None`，调用方
   `refs, smiles = ...` 解包将抛 `TypeError`（非结构化崩溃；仍
   fail-closed，不会静默提交）。与同义源 `native_result.
   _p0b_d6_product_participants` 的 `return None, None` 不一致，
   违背其自身 docstring「同义」声明。按 build_pathway_event 契约
   参与物恒为 dict，故实际不可达 ⇒ **不升级为阻塞**；最小修复 =
   改为 `return None, None`，并补一条非 dict 参与物走 unknown 不拒
   的单测。合入预注册批前必须修（一行）。

无其它必须修正项。

## 4. 非阻断观察

1. 测试缺口（Q6 所列五类分支）：建议合入前补 run 级预算耗尽
   outcome、resume 复用、非 model_declared 边界、edits 未变/非法、
   不可解析响应各 1 项；不阻断本轮。
2. 纵深防御：production 信任调用方传入的 `reconciliation_spec` 已过
   身份门；可考虑在 production 内对冻结 action payload spec 再核一次
   身份字段（现由 runflow 单点把关 + hypothesis_id==subject_ref 兜底，
   传递性归纳成立，非缺陷）。
3. 新 helper 与 native_result 在「refs 在位但状态结构缺失」时返回值
   不同（(None,None) vs (refs,None)）：两侧均落阻断型 unknown 方向、
   不 gate，结果一致；建议 docstring 注明差异。
4. JSON decide 路径把 register 的 `SearchBudgetExhausted` 升级为
   `PPV1RunError`（结构失败保持），而对账路径转残余拒——语义不同是
   有意为之（前者是解析失败保持、后者是候选拒），建议加一行注释防
   后人误统一。
5. feedback 臂 submitted 报告新增 p0b_d6/p0b_d6_history 键：仅实验臂
   形状变化，disclose/gate 不加键；预注册报告口径需注明该形状差。

## 5. unknown / 未核清单（维持 unknown，不因本审解除）

- A 的实际回收率（含 66 disjoint vs 80 overlap 的分层回收）——只能
  新批测量；
- B 残余拒的离线命中损失（设计 §3.3 冻结 scorer 复算**未做**）；
- 146 absent / 58 stereo 的化学真伪（R4 仅规则级；真实结构复核未做）；
- A 对 298 域 hit@1 的影响（可能降分，必须写入预注册口径）；
- 真实 HPC 环境复跑；RDKit 2026.03.6（本机）vs 2026.03.5（批内登记）
  逐事件对照未做；
- resume 场景 (a) 重放恢复在真实 attempt 语义下是否可达（本审只核了
  代码路径与 fail-closed 性，未做崩溃注入实测）；
- 全量 2365/1 与 203 相关面为实现方日志 + 本审部分抽跑互证，未逐项
  重跑全量。

## 6. 预注册条件（是否具备进入 P1-B 预注册）

**具备起草条件**；预注册成文并批准前仍需（归 CC/老师/Codex 正链，
本审只列不批）：

1. §3 一行回修合入（或显式接受为已登记潜在缺陷）；
2. §3.3 B 残余拒离线命中损失复算完成，或在预注册中显式登记为
   unknown 并给最坏情况口径；
3. 崩溃恢复失败模式（必核 6）写入预注册风险面；是否先做修订
   artifact 持久化由 CC 拍板；
4. `P0B_D6_RECONCILIATION_POLICY` 不在 run identity——发车脚本必须
   显式记录其值并保证 A/B 两臂单变量（实施报告 §7 已挂账，预注册
   须落为可核对条款）;
5. 「让模型改 edits」新提示面的化学规则级评审按仓库三触发点单独
   产出/送审（本轮未送审，设计 §4 已如实声明不冒充已评）；
6. 付费批批准、费用记录、批根独立、旧批零回写——均归 CC/老师；
   判据冻结（v3/T1′类）与真实题面外发不在本审职权，仅提示需另走
   拍板。

## 7. 与上一轮结论的关系

本轮无与 P0b D-6 合同/复审（`docs/T_H_P0B_D6_CONTRACT_2026-10-20.md`、
`docs/T_H_P0B_D6_QWEN_REREVIEW_2026-10-21.md`）冲突的取舍：P0b 旁路
披露默认关、单一判据、stereo/unknown 不 gate 的既有验收在本 patch
中保持；本审新增结论仅针对 P1-B 增量面。
