# HIT60 T9 报告：编辑路径修复后重放——「从全灭能否活过来」（零 LLM）

> 任务书 [TASK_V43_HIT60_T9_EDIT_REPLAY.md](TASK_V43_HIT60_T9_EDIT_REPLAY.md)；
> teacher 批复 §六 老师侧加项（2026-09-30）。实施 2026-09-30，零 LLM 零 API
> 零费用，封存 run 只读，不改任何既有判定与正式分数，不 git commit。
> 通俗版：[HIT60_T9_EDIT_REPLAY_REPORT_PLAIN.md](HIT60_T9_EDIT_REPLAY_REPORT_PLAIN.md)。
> 产物：`reports/phase_s15_hit60/edit_path_replay/`（复现见其
> [REPRODUCE.md](../reports/phase_s15_hit60/edit_path_replay/REPRODUCE.md)）。

## 0. 一句话结论

**门禁误杀面已复活，但「全灭」的旧 8 题死于编辑列表本身破损，不是误杀——
0/8 复活；修复后 C0 臂 12 道被门禁全拒的题 10/12 过闸（全部为「同分子
被杀」平反），其中仅 1 题（b978fd0b 锚点）产物=金标；dev 六批 16/18 与
运行记录一致、0 分歧。编辑路径「活没活过来」要拆成两问：门禁活了
（该活的都活了），命中没多（重放面内净增命中 = 1 题，就是锚点）。**

| 批 | 对象 | 修复前 | 修复后 | 复活 |
|---|---|---|---|---|
| 批1 | 旧「8 题编辑重放」集（298 首跑） | 8/8 不可执行 | 8/8 不可执行，**拒因逐字相同** | **0/8** |
| 批2a | 298 重测 C0 臂 12 道 edit_blocked（11 empty + 1 b978fd0b） | 12/12 门禁拒 | **10/12 过闸**（10/10 走 canonical 短路）；2/12 真不一致仍拒 | **10/12**（其中产物=金标 **1/12**） |
| 批2b | dev 56 中 analogy_edit 路由题（S1 六批 3 qid × 6 = 18 实例） | S1 记录：14 proposed + 2 noop 拒 + 2 弃答 | 16/18 与记录一致，**0 分歧**；2 弃答无提案不可重放 | 一致性对照（S1 已跑在修复后代码上） |

## 1. 重放对象定位（含任务书勘误登记）

- **批1 找到了**：即 HIT1 归因报告 §6.1 的 8 道 `validation_rejected_gold`
  题（`RXNG_7701b699/4609b23a/208874cb/30ab4108/cf89ba36/d7656c5f/
  6455b8da/7d281486`，声明目标=金标、编辑被确定性拒因拒绝）。原始编辑
  输入在本地封存首跑镜像
  `/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/…/runs/ec298_v43r1`
  （只读）；「修复前全部不可执行」结论出自
  `reports/ec298/phase_c/rejections_reclassified.tsv`（Phase C 同输入
  重放，1 可执行/22 不可执行中的 8 题）。
- **任务书一处勘误**：任务书把「11 道 empty_no_model_answer + 1 道
  validation_rejected_gold（b978fd0b）」写作 dev 56 题。实测该 12 题
  **不在 dev 56**（b978fd0b 为 298 题号；dev 56 题号为 b1_BIOPATH150_*
  格式）——它们是 **S0 边界表 `boundary_pools.tsv` 的 edit_blocked 池**
  （298 Phase D 重测 **C0 臂**，registry_pool_definitions §登记「只用
  C0 臂」）。本报告按实际数据面处理：批2a = 该 12 题（原始输入在远端
  `…/dependingv43/runs/ec298_pd_retest_C0/`，只读抽取）；批2b = dev 56
  中真实走 analogy_edit 路由的题（S1 六批每批恰 3 qid：
  `b1_BIOPATH150_067__S05__BSY-r02911 / 095__S05__BSY-r03787 /
  124__S03__BSY-r02044`，六批合计 18 个任务实例）。两部分都做了。

## 2. 重放口径（零 LLM 确定性；修复前结论不重放旧代码）

- **重放链** = `workflow/nodes.py::_apply_analogy` 的确定性门禁序，用当前
  工作树（含 T4 修复，未提交；`src/pathway_v43` 聚合 SHA
  `0f0a4be5…7e02`，`atom_tool.py` `b20092dc…6f27`，HEAD `bf1ac38`）：
  ①供体引用 → ②`validate_edits` → ③`execute_edits` →
  ④`check_target_consistency`（T4 主战场：canonical 双口径短路前置 +
  `product_mapped_smiles` 统一索引空间 + 死检查改真比对）→ ⑤空编辑
  no-op 策略（`allow_noop_edit` 默认 False）→ ⑥`validate_event_products`
  （产物验证；ancestry=[底物 cn] 最保守环检、siblings=空、
  check_elements=True 按 analog 提案卡口径——跨路径 sibling_dedup 与
  方向/来源门禁需完整路径上下文，不在确定性重放面，T4 修复不触这两处）。
- **修复前结论来源（既有文档/封存产物直读，不重放旧代码）**：批1 =
  Phase C TSV（其运行时点即修复前代码）；批2a = C0 臂 run 自带
  `atomtool_checks`（C0 臂跑在修复前代码上——b978fd0b 的 19 条错位
  拒因原样在案，即证据）+ boundary_pools 池标签；批2b = S1 六批运行
  记录（S1 部署时**已含** T4 修复：发车锚代码聚合 `fff3b417…` 为
  508 绿时点快照，RUN_JOURNAL §0/§1——故批2b 是修复后行为的确定性
  回归对照，不是修复效果测量）。
- **金标红线**：金标只读（298 用封存镜像、dev 用 gitignored
  `dev_gold.jsonl`）；比对结论只以旗标（`*_matches_gold`）进发布层；
  金标/底物/产物 SMILES 原文只落 `raw_inputs/`（gitignore `.gitignore:30`）。
  b978fd0b 锚点按三步取证口径验证「执行产物=金标」（旗标呈现）。
- **确定性**：`PYTHONHASHSEED=0` 双跑逐字节一致；跨 seed（0 vs 1）38 行
  **判定零差异**（仅 2 行对称分子的拒因排列序随集合迭代序变化——展示
  层噪声，判定稳定；复现命令已钉 seed）。
- **身份对齐**：38 个可重放任务实例全部 `roundtrip(底物)` 渲染成功、
  封存原子 ID 与现渲染零漂移（drift 0/36 可比对行）、供体引用全对齐。

## 3. 批1 结果：旧 8 题 0/8 复活——「全灭」根因不是误杀

修复前后逐题判定与拒因**逐字相同**（TSV 逐题对照
`replay_per_question.tsv` 批1 节）：

| 死法 | 题数 | 机制（重放实测） |
|---|---|---|
| `edit_execution_failed:bond_already_present` | 3 | 模型对**已存在的键**下 `form_bond`（未先 break）——编辑协议 v2 按设计硬拒（键级变化必须显式 `change_bond_order`） |
| `target_edit_mismatch:bond_order:…(single!=double)` | 5 | 模型编辑列表 = `break_bond X~Y` + `form_bond X~Y`：执行产物该键为**单键**，而其**自己声明的目标**（=金标）该键为**双键**——编辑语言表达错误，执行产物与声明目标确为**两个不同分子**（canonical 不同，短路正确不触发） |

- 8/8 声明目标=金标（模型「知道」答案），但编辑列表结构破损，无法把
  目标做出来。这正是 Phase C 报告的结论（「模型在文本里知道目标、却
  提交了结构破损的编辑列表」）——**T4 修复修的是「同分子被杀」，救不了
  「编辑做不出目标」**。修复前后拒因不变 = 修复对该 8 题零行为漂移（负
  向无回归，正向无虚放）。
- 历史注记：5 题用 break+form 表达升键级，可能受首跑 v1 编辑语言表达
  能力限制（v2 才有 `change_bond_order`）；该注记不改判定——当前协议
  下这些编辑列表就是错的，要复活需**重新表达编辑**（模型侧行为），不是
  门禁侧修复。

## 4. 批2a 结果：C0 臂 12 题 10/12 过闸，锚点全绿，但过闸≠命中

- **10/12 复活**：全部经 `canonical_equivalence_short_circuit` 过闸。
  交叉验证（运行时记录直读）：这 10 题修复前的 `target_smiles` 与
  `edit_execution.product_smiles` **本来就逐字符相同**（同分子被杀
  10/10 坐实），各自挂着 2–28 条 ID 级伪拒因（b978fd0b 案同型）。
  修复精准命中：同分子→放行，无一条虚放（负例由 T4 测试钉住）。
- **2/12 仍拒**（`RXNG_31299a2c / e11a1cac`）：目标与执行产物 canonical
  **真不同**（多键键级差异），短路正确不触发，ID 级对账正确拒绝——
  这些题的失败在模型侧（目标与编辑不符），不是门禁。
- **b978fd0b 锚点（回归验证全绿）**：修复前 `target_consistency
  ok=False`（19 条错位拒因）→ 修复后 **ok=True**，`note=
  canonical_equivalence_short_circuit`；执行产物=金标旗标 **true**
  （且修复前产物亦=金标——即 S0 取证「误杀坐实」的重放复现：产物
  本来就对，是门禁杀错了）。
- **诚实上限（过闸≠命中）**：过闸 10 题中**仅 1 题（b978fd0b）产物
  =金标**；其余 9 题产物≠金标。若这些题在修复后代码上复跑，将由
  「空答」变为「有答」——1 题命中、9 题错答（spurious +9 风险面），
  最终答卷位次取决于候选裁决，不在确定性重放面内。**门禁是必要条件
  不是充分条件**的 Phase C 结论在修复后依然成立。
- 批2a 过闸 10 题的产物验证（⑥`validate_event_products`）全部通过
  （解析/价态/环检/元素变化门禁全绿）。

## 5. 批2b 结果：dev 六批 16/18 一致、0 分歧

- 18 实例：14 proposed → 重放全部 executable（过闸+产物验证）；2 实例
  （E2 两批的 r02911）模型提交**空编辑**且目标=底物自身 → 门禁④过
  （同分子短路）但⑤noop 策略拒（`noop_edit_not_allowed`，按设计），
  与运行记录一致；2 实例模型**主动弃答**（parsed.decision=abstain，
  无提案不可重放，如实留行）。
- **0 分歧**：重放判定与 S1 六批运行记录逐实例一致——S1 已跑在含 T4
  修复的代码上，此结果证明编辑门禁链路在 dev 上**行为确定可复现**
  （无漂移、无 flake）。
- dev 3 题**无一产物=金标**（analogy 路由在 dev 的 3 个承载题本来就不
  命中）；16/18 过闸实例走短路路径——短路是类比门禁当前的主通过路径。

## 6. 数据回执口（类比线封存维持）

- 类比线封存状态**维持不变**：发布默认
  `reactant_similar_enabled=false` 不动；本任务只回收数据供后续裁决，
  **不解封、不立项、不改任何臂判定与正式分数**。
- 回执数字（供 teacher 路径预算表「编辑路径修复后重测 视结果 0–2」对
  账）：修复在重放面内的**净增命中 = 1 题**（b978fd0b，298 侧）；dev
  侧 0（S1 已含修复，重放零差异）。298 侧若复跑（只能标
  `post_hoc_repair_check`），预期另有 9 题空答→错答、2 题维持空答。

## 7. mimo 复核触发点（后置，不外发数据）

本任务涉及化学可执行性判断的题面（按 AGENTS.md 触发点可后补 mimo 复核
请求，本任务零外发）：①批1 的 8 题——「break+form/既有键 form」在当年
协议下是否本无合法表达路径（编辑语言 vs 模型错误归因）；②批2a 仍拒的
2 题——目标分子经所提编辑是否化学可达；③批2a 过闸但非金的 9 题——
产物是否化学合理（spurious 风险面）。复核不改本回执事实。

## 8. 产物与复现

```text
reports/phase_s15_hit60/edit_path_replay/
  replay_per_question.tsv        # 38 行逐题表(无 SMILES:旗标+SHA12+拒因文本)
  replay_summary.json            # 汇总/身份/计数/b978fd0b 锚点块
  REPRODUCE.md                   # 命令+SHA(本节入口)
  scripts/t9_edit_replay.py      # 重放脚本(六步链)
  scripts/t9_remote_extract.py   # 批2 远端只读抽取脚本
  raw_inputs/                    # gitignored(含金标比对原文)
    remote_edit_inputs.jsonl     # 批2 原始编辑输入(30 行)
    batch1_sealed_inputs.jsonl   # 批1 原始编辑输入(8 行)
    replay_raw_results.jsonl     # 全量重放明细(38 行,含 SMILES)
```

复现（详见 REPRODUCE.md；零 API）：
`OMP_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONPATH=src python
reports/phase_s15_hit60/edit_path_replay/scripts/t9_edit_replay.py`；
批2 输入再生产需 `/tmp/cy_ssh.sh` 远端只读抽取（命令在 REPRODUCE.md §2）。

## 9. 红线遵守

零 LLM 零 API（费用 ¥0）；封存 run 与远端 run 全程只读；金标只读且
旗标化；未改任何既有判定/正式分数/封存产物；未 git commit（工作树
改动仅新增本目录产物、两份报告与 `.gitignore` 一行 raw_inputs 保护）；
坏结果（0/8、9/12 过闸不命中）如实上报。
