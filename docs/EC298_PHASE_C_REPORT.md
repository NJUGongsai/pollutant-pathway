# EC298 Phase C 报告:类比适用性门禁与 AtomTool 编辑协议 v2

> 任务书:[`TASK_V43_EC298_PHASE_C.md`](TASK_V43_EC298_PHASE_C.md);上游依据:Phase A 报告([`EC298_PHASE_A_REPORT.md`](EC298_PHASE_A_REPORT.md))、R2 review §4/§6([`EC298_REVIEW_R2.md`](EC298_REVIEW_R2.md))、Phase B 报告([`EC298_PHASE_B_REPORT.md`](EC298_PHASE_B_REPORT.md))。
> 实施日期:2026-09-28。**全程零 API、零 298 重跑**:离线部分只读封存首跑镜像(逐文件只读访问,封存目录零写入);金标仅进入显式标注的离线诊断列。实施会话与 Phase B 会话共享工作树(按用户指示未另建 worktree),Phase B 交付保持原样,双方改动经全仓回归共同验证。
>
> **R3 review 修正(2026-09-28 下午,以本版数字为准)**:①初版审计的"0/23 匹配金标"系**审计脚本题号 bug**(run 目录名剥掉 `RXNG_` 前缀而金标保留 → 逐题查找全部落空、诊断列假性归零);修正后 **8/23 复现、与 R2 原始口径一致**,初版对 R2 的撤回作废(§7)。②修复 rank 任务候选筛选的 kind 泄漏(非 recorded 卡"资格判据空表"≠ 合格,与 classify 同一守卫,伪造挂牌的 analog 卡不得充当 usable recorded)。③AtomTool 非法元素双层 fail-closed(周期表预校验 + 执行层结构化拒绝)。④编辑列表"先增后引"按列表时点语义放行。⑤对齐枚举**评估全量**、落盘明细样本分离(`n_alignments_assessed` 留痕)。⑥"66/66 不可达"限定适用域(§11.7)。全仓回归与离线审计已全部重跑。
>
> **Phase C 二轮复核修复(2026-09-28 傍晚,复核报告:[`EC298_PHASE_C_REVIEW_R2.md`](EC298_PHASE_C_REVIEW_R2.md))**:上一轮修复经独立复核确认,另发现并修复 **rank 选中原始 rule/analog 卡可直进报告首位并提交 ReactionEvent** 的集成阻断(详见 §7.1)与三项 P2(金标覆盖门禁逐题必中+唯一、编辑协议严格四操作拒绝未声明字段与旧别名、对齐枚举显式上限 + 触顶 `alignment_limit_exceeded` fail-closed,§11.9)。全仓回归 387 passed、离线审计重跑(各臂计数不变;再分类 TSV 仅一行拒因文本顺序变化,金标诊断仍 8/23)。**三审补强(2026-09-28 晚)**:金标覆盖门禁再进一步——金标**行重复**(同 qid 多行被索引静默覆盖)也 fail-closed(§11.9②);该项修复只改审计脚本与夹具,封存数字与各臂计数不变。

## 0. 摘要

1. **来源找回与迁移资格分层完成**:`mapping_status=resolved` 单独出现不再触发 `analogy_edit`;进入类比必须经过版本化 `applicability` 资格块(`v43-applicability-1`)——确定性变换提取、全对齐枚举、逐项结构必要条件检查、竞争弃权。封存 66 条类比任务在新门禁下 **23 条仍会进入类比路线**,43 条转受约束 fallback(逐层定性见 §6.1:24 条化学真竞争弃权、19 条结构失配/不可判定;**在当前资产(供体找回按产物身份键定)、候选顺序、预算 3 与现行门禁下,不存在可把 66 条全部放进类比的合理门禁**——下文有红线分析;适用域限定见 §11.7,Phase D 检索/资产改进可能改变该数字)。
2. **编辑协议 v2**(`v43-editproto-2`):新增 `change_bond_order`(显式 from/to 键级)、`add_atom` 强制显式 `new_atom_id`;废除 remove_atom。模型编辑在当前分子图副本**按列表顺序执行**,目标 MoleCode 独立解析后与执行结果图逐项对账(ID/元素/电荷/键集合/键级/canonical SMILES),文本伪造 ID 不再可能通过。`bond_already_present` 对 form_bond 保持硬拒绝。R3 修正:元素以 RDKit 周期表为事实源(形似元素 `Xx` 在预校验拒,执行层兜底结构化拒绝);"先增后引"按列表时点语义放行。
3. **旧 23 条编辑拒绝的离线再分类**(§6.5):同输入下新协议判 **1 条可执行 / 22 条不可执行**(8 结构校验拒 + 8 执行拒 + 6 目标不一致);**诊断列:22/23 目标文本可解析,8/23 匹配金标**(R3 修正:初版 0/23 系审计脚本题号 bug,见 §7)。旧 15 条接纳提案抽样:新门禁判 **6 inapplicable、4 ambiguous(竞争变换)、5 applicable;金标诊断 0/15**——门禁识别出 10/15 的结构风险;5 条门禁适用者同样 0 命中,印证"门禁是必要条件不是充分条件"。
4. **对 R2"8/23"的更正(撤销初版撤回)**:R2 §4 及任务书 §0 引用的"22/23 目标 MoleCode 可解析,8/23 的目标 SMILES 直接匹配金标"**可在封存数据上复现**。初版审计报 0/23 系脚本缺陷:run 目录名 `exam298_<batch>_RXNG_<hash>` 被剥成不含 `RXNG_` 的短号,而金标 qid 保留前缀,逐题查找全部落空 → 诊断列假性归零。初版据此对 R2 结论的"未能复现"撤回**作废**;修正过程与口径详见 §7。
5. **测试与回归**:全仓回归全绿(数字见 §10 实测行;Phase C 新增测试:门禁 25 + 编辑协议 13 + 工作流/恢复 7,另强化既有路由/端到端测试;R3 再补 4 个钉子:伪造挂牌 analog 卡不入 usable/不重复入候选、`Xx` 元素双层拒绝、先增后引合法、>16 对齐全评估)。恢复测试新钉"供体裁决落盘后硬杀"点,暴露并修复一个**既有**恢复语义洞(classify 重写不可变 decision 产物 → `ArtifactConflict`),修复后与 `retrieve_reactions` 同一读前写幂等模式。

## 1. 实施范围与版本变更

| 变更 | 文件 | 版本标识 |
|---|---|---|
| 新增:供体变换提取与适用性门禁 | `src/pathway_v43/services/donor_applicability.py`(新) | `v43-applicability-1` |
| 新增:编辑协议 v2(校验/顺序执行/目标对账) | `src/pathway_v43/services/atom_tool.py` | `v43-editproto-2` |
| 路由:类比资格改由资格块决定 + 消融开关 | `src/pathway_v43/domain/policy.py` | 策略 `v43-policy-3`;预测策略 `v43-predpol-2` |
| 任务书 v3:donor 块带 applicability/transform/协议版本/落选摘要 | `src/pathway_v43/services/prediction.py` | `v43-prediction-task-3` |
| 接线:classify 计算资格并落盘、prepare 传递、_apply_analogy 重写、停留理由携带拒因 | `src/pathway_v43/workflow/nodes.py` | — |
| 提示词:编辑语言 v2(四种操作+一致性要求) | `configs/prompts/analogy_editor.md` | SHA 进 prompt_versions(run 身份自动生效) |

Phase B 文件(`report_adjudication.py`/`export_v3.py`/`score_report.py`/`llm_client.py`/`batch.py` 等)**零改动**。类比资格块随 decision 产物落盘,Phase B 的候选裁决只读该结论,不自行推断"resolved 即可报告"——与任务书 §1.2 交接字段约定一致。

**run 身份影响**:代码身份(`code_identity` 逐文件 SHA)+ 策略/预测策略/提示词版本全部变化,旧 run resume 一律拒绝(设计行为);原始 298 封存、Phase A 产物与资产逐文件原样。

## 2. C0:人工审过的供体夹具与原路由只读审计

**夹具**(`tests/fixtures/applicability/donor_applicability_fixtures.json`,不从 298 金标反推;每条含预期/理由/审核者/日期,预期全部经实跑核对后冻结):

| 类别(任务书 §2 全覆盖) | 夹具 | 预期 |
|---|---|---|
| 全供体准确匹配 | F1 | applicable → 戊醛 |
| 中心匹配但一阶邻域冲突 | F2(叔醇无氢) | inapplicable `insufficient_hydrogen` |
| 键级不符 | F3(唯一 O–C 位点已是双键) | inapplicable `no_alignment`(查询携带键级,枚举处即拒) |
| 可用氢/价态冲突 | F3v(酯 O 无氢可失) | inapplicable `insufficient_hydrogen` |
| 形式电荷冲突 | F4(醇盐 O⁻ vs 供体中性 O) | inapplicable `charge_context_mismatch` |
| 对称位点等价匹配 | F5(丙二醇两端) | applicable,`n_equivalent_alignments=2` 合并 |
| 竞争位点不同转化 | F6(3-甲基-1,4-丁二醇) | ambiguous,2 个竞争目标 |
| 多供体指向不同变化 | F7(氧化 vs 氯取代) | 卡级 ambiguous `multiple_competing_transforms` |
| 没有可靠供体 | F8(酮模板 vs 戊醇) | inapplicable `no_alignment` |
| 模板不可解析 | F9 | unavailable `transform_unparseable_lhs` |
| 供体==底物 | F10 | inapplicable `donor_same_as_substrate` |
| 来源无映射 | F11 | unavailable / fallback `no_mapping` |
| 真实资产集成 | R1(corpus 模板 `env:EAWAG-BBD:bt0001#r0002`,第 42112 行) | applicable → 3-氯丙醛;测试核对资产 SHA 与本仓清单一致 |

标签纪律:所有场景在本夹具集内均可确定性判定,无硬纳入分母的争议例;对称合并(F5)与竞争弃权(F6/F7)两侧钉死。

**原路由只读审计**(`analogy_route_audit.tsv`,66 条 analogy_edit 任务):结局分布 **28 弃答 / 23 拒绝 / 15 接纳**(与 Phase A 锚点逐位一致);对齐策略 **44 条仅中心子图 / 22 条全供体**;供体模板反应中心原子数 ≤3 的任务 **62/66**(口径:模板 `center_atoms` 长度,即"供体只圈定 2–3 个中心原子"的弱映射画像);去向模型的即全部 66 条(旧路由 resolved 即进模型)。

## 3. C1:供体变换提取与适用性门禁

- **变换提取(确定性)**:`mapped_lhs → mapped_rhs` 提取保留/新增/消失映射号、元素/电荷/氢变化、被断/新成的键及键级变化、新增原子落位键。提取即核验:双侧可解析、映射号双侧唯一、保留原子元素一致;**不信任 `qc_flags.bijection`**(重复映射号/元素漂移留拒因 `duplicate_map_no`/`map_element_changed`);模板不可解析记 `unavailable` + 具体拒因,不补造映射。
- **全对齐枚举**:全供体优先(全部 `GetSubstructMatches(uniquify=False)`,不取首个),失败才落明示的中心子图保守候选;芳香形式匹配(避免 Kekulé 异构体假阴性)。R3 修正:**评估覆盖全部枚举对齐**(竞争目标判定不得漏掉第 17+ 个对齐),落盘明细只留 16 条样本,总数以 `n_alignments_full`/`n_alignments_center`/`n_alignments_assessed` 留痕。
- **逐对齐结构必要条件**:元素对应、键上下文(存在性/aromatic≡aromatic/键级)、电荷语境(供体电荷不变的原子当前须一致;电荷变化施加 delta 并记 `unverified_conditions`,**不写成环境相容**)、可用氢、施加后 sanitize(价态)、氢结算(保留原子最终氢 = 当前氢 + donor delta,捕获一阶邻域分歧)。施加成功才有预测产物;对称对齐同产物合并,异产物 `ambiguous`。
- **候选预算**:每父节点最多 `max_analogy_donor_candidates=3`(冻结进策略身份);卡内供体序 = donor_refs 序(检索来源序),卡序 = (retrieval_rank, evidence_id);先到先评、跨卡竞争目标弃权。
- **fallback 拒因词表**:逐题区分 `no_mapping` / `mapping_ambiguous` / `applicability_failed` / `applicability_unknown` / `multiple_competing_transforms`,不统称"无证据"。

## 4. C2:编辑协议 v2 与 AtomTool 顺序执行

- 操作语言:`break_bond` / `form_bond` / `change_bond_order`(from/to ∈ single|double|triple)/ `add_atom`(强制 `new_atom_id`,ID 内嵌元素须与声明一致,不得与既有/列表内冲突);remove_atom 废除。结构校验拒因全部带操作索引 `edit[i]`。
- **顺序执行**:当前分子图副本(kekulé 化)按列表执行,每步核验拓扑前提(键存在/不存在/原键级);中间态允许事务内暂存,最终 sanitize 必须通过。`bond_already_present` 对 form_bond 保持硬拒绝——键级变化必须显式 `change_bond_order` 并核对原键级(`bond_order_mismatch:expected_X_have_Y`)。
- **目标对账(不止解析成功)**:目标 MoleCode 经 vendored 解析器独立解析,与执行结果图做 ID 级带标签图对账(原子 ID 集合、元素、形式电荷、键集合与键级两侧 kekulé 归一)+ 最终 canonical SMILES(含立体)逐字符一致;任一失配 → `target_edit_mismatch:*`。文本中搜到 ID 不算结构相符。
- 空编辑仅当目标图==当前图**且策略允许**(`allow_noop_edit`,默认 false)才成立。表示有损/立体/电荷差异全部 fail-closed(沿用 MoleCode 往返边界与 vendor 7/7 哈希,vendor 未动)。
- 提案通过后仍走既有 `validate_event_products`、方向/来源/循环/元素门禁与 Phase B 候选裁决;供体原始产物不进入当前底物的报告产物。

## 5. C3:工作流接线与失败语义

- 资格块在 `classify_evidence` 计算(纯函数)并**随 decision 不可变落盘**;路由读资格块,`resolved` 单独出现只产生具体拒因 fallback。旧卡兼容读取:缺资格块一律 `unavailable/not_assessed`(`read_applicability_compat`),旧 run 不追写、不追认。
- `analogy_enabled=false`(消融开关):类比路由整体关闭;recorded/rank 语义不变;预测性证据按既有 novel 策略与预算处置,reason 携带 `analogy_disabled`。
- 模型 `apply` 的执行序:① `referenced_evidence_id` 必须等于选定供体所属证据 ID(否则结构化 `donor_reference_mismatch`,携带双方引用);② 结构化校验 → ③ 顺序执行 → ④ 目标对账 → ⑤ no-op 策略;任一步失败写结构化 `rejected`(操作索引/供体 record_id/资产文件/SHA/行号随 `atomtool_checks` 留痕),不假成功。
- 分开计数:模型弃答 / 供体不适用(资格块)/ 表示有损 / 编辑拒绝 / LLM 预算耗尽;传输/解析失败仍记 `failed`,不冒充化学不适用。`novel_proposal` 在"有检索产品但映射/适用性失败"时 reason 保留具体拒因(如实上下文,不宣称完全无证据)。
- **恢复语义修复**:新增注入点 `classify_evidence`(供体裁决落盘后硬杀)暴露既有洞——重放时 decision(含 `created_at`)重写触发 `ArtifactConflict`。修复为读前写复用(与 `retrieve_reactions` 同模式);`test_crash_after_classify_resume_consistent` 实测:恢复后资格块逐字节一致、供体选择/AtomTool verdict/调用数(计数文件=1)/事件数一致。

## 6. 离线审计与再分类(零 API;`reports/ec298/phase_c/`)

复现:`OMP_NUM_THREADS=1 python scripts/phase_c_offline_audit.py --seal-run-dir <封存>/runs/ec298_v43r1 --gold <封存>/ec298_gold_readonly/questions.jsonl`(封存只读,脚本不含地址与凭证;`summary.json` 记录金标 SHA256 `9f5955d4…9211c`)。

| 臂 | 结果 |
|---|---|
| 原路由画像(66 题) | 28/23/15 = 弃答/拒绝/接纳(与 Phase A 锚点一致);44 中心对齐 / 22 全供体;62 题供体中心原子 ≤3 |
| **23 条旧拒绝 × 新协议** | **1 可执行 / 22 不可执行**(edit_invalid 8 + edit_execution_failed 8 + target_edit_mismatch 6;唯一可执行题目标亦不匹配金标) |
| 诊断列(金标,仅离线) | 22/23 目标文本可解析,**8/23 匹配金标**(R3 修正:初版 0/23 系题号失配 bug,详见 §7) |
| **15 条旧接纳 × 新门禁** | **6 inapplicable、4 ambiguous(竞争变换)、5 applicable**;金标诊断 **0/15** |
| 路由消融(66 题) | 新门禁下 **23/66 仍进类比、43/66 → novel_or_hold**;开关关闭全部 66 → novel_or_hold(零调用模拟,非新预测) |

**解读(有证据边界的)**:15 条旧接纳提案在新门禁下 5 适用 / 4 竞争歧义 / 6 结构失配——门禁能识别部分风险,但**门禁是必要条件不是充分条件**:5 条门禁适用的旧接纳同样 0 命中金标;而 23 条旧拒绝同输入重放 22 条在新编辑协议下仍不可执行(模型当年的编辑列表本身结构破损)。本阶段不把任何再分类/消融数字写成新模型成绩,未向模型回灌任何结果;298 不作调参集,后续复跑只能标 `post_hoc_repair_check`。

### 6.1 问题定位:43 条为什么进不了类比(逐层定性 + 一处已修复的实现缺陷)

**先修掉的实现缺陷(本轮 review 中发现)**:评估器最初按纯 (retrieval_rank, evidence_id) 序跨卡消费供体预算(每父 3 个),排位靠前的规则卡先耗尽预算,**43/66 任务被旧路由实际选中的 resolved 供体根本没被评估到**——"11/66"当时是预算饥饿伪影,不是化学结论。已按任务书 §3 的明文优先级("可执行且证据充分优先,再按固定、可说明的来源与检索位次排序")改为 **resolved 卡优先评估**;修正后 applicable 11→23,并与旧路由逐条对质核验。

修复后的 43 条未通过逐层定性(被路由供体级,全部可回查):

| 层 | 数量 | 机制 | 抽查核验 |
|---|---|---|---|
| ① 化学真竞争 → 弃权 | 24 任务 `multiple_competing_transforms` | 同一模板对当前分子的多个对齐产生**真正不同的产物**(2,3- vs 2,4-二氯苯酚;甾体 Δ 异构体;双键迁移多个落点)。任务书 §3 明文:"若得到不同目标或供体互相冲突,应标 ambiguous,**不得只拿第一个**" | 15 例逐一采样核对:0 例为立体/规范化伪影,全部骨架真不同 |
| ② 可用氢不足 | 10 个供体 `insufficient_hydrogen` | 例:甲醛→甲酸模板对齐到底物**无氢酮碳**(酮不该走醛→酸这条反应) | 抽查正确 |
| ③ 价态不可执行 | 7 个供体 `valence_infeasible` | 例:氯代脱卤模板(Cl 未映射)对映射区只能表达"+1H",施加后 5 价;硝基→羟胺单步压缩模板在图上确实走不通 | 抽查正确 |
| ④ 模板映射不完整 | 12 个供体 `transform_no_change` → unavailable | 模板只映射骨架、真实反应在**未映射位置**(如胍基苯胺→苯酚只映射苯环)。按任务书"模板不完整记 unavailable,**不补造原子映射**"如实标不可判定 | 与旧路由对质:旧管线照样送模型,由模型猜未映射化学——正是 Phase A 大量弃答来源之一 |
| (检索层根源) | 39 次 `no_alignment`(预算内 198 次评估) | 供体找回按**产物身份**键定(`templates_producing`:谁能产出该产物),供体反应物与当前底物可以毫无结构关系 | 这是 D1"按底物相似度找回"的量化依据;修复排序后 19 条 inapplicable 任务的供体拒因分布:no_alignment 39 / 氢 20 / 价态 14 / 电荷 1 |

**补充诊断(封死最后一个 conceivable 杠杆)**:对 24 条竞争歧义任务,把"下游确定性门禁(可解析性/元素变化)提前用于筛选竞争目标"做了零代码量化——**24/24 仍为多存活**(竞争产物元素组成相同,如二氯苯酚异构体),即不存在"唯一通过门禁的产物"的合法解析路径;歧义弃权是终态,不是待解状态。

**为什么 66/66 全部进入类比不是合理目标**(红线声明):
1. 24 条竞争歧义若强行"通过"= 任选一个产物,产出的答卷把 2,3-二氯苯酚当成 2,4-二氯苯酚一样报告——这正是任务书 §7 阻断点"用已见 298 选择供体/门槛"要防的结果造假;
2. 12 条部分映射模板若强行"通过"= 从未映射区猜反应(补造映射),同属 §7/任务书 §3 红线;
3. 10+7 条氢/价态失败是 RDKit 可复算的结构事实,放宽即对分子图撒谎;
4. 旁证:旧管线"66 条全部送模型"的**最终报告产物** = 28 弃答 + 23 编辑拒绝 + 15 接纳,金标 0 命中(Phase A 评分口径:拒绝/弃答不产出可报告产品。注意区分:其中 23 条被拒编辑的目标**文本**有 8 条与金标一致 —— 模型在文本里"知道"目标、却提交了结构破损的编辑列表,这正是编辑协议 v2 与本阶段再分类的对象,不构成放宽门禁的理由);门禁的意义就是把这类结构上撑不住的类比如实分流。

**诚实上限与后续杠杆**:预算诊断(budget=10,仅诊断不落策略)可将 applicable 提到 30/66——预算取值属 Phase D 政策,须用 dev 集验证后再冻结。提升类比进入率的正路:① 供体找回按**底物相似度**键定(现按产物身份,上表"检索层根源"行,属 Phase D);② 资产侧语料模板**重映射**(上表第④层,需独立版本/哈希审核);两者都不是放宽门禁。三杠杆的任务书草案见 [`TASK_V43_EC298_PHASE_D.md`](TASK_V43_EC298_PHASE_D.md)(状态:草稿,待用户裁决发车;D1/D2/D3 全部走 dev 集验证,§7 红线原样继承)。

## 7. 对 R2"8/23"的更正(撤销初版撤回;R3 review)

R2 §4 及任务书 §0 引用"22/23 目标 MoleCode 可解析,只有 8/23 的目标 SMILES 直接匹配金标"。初版审计在封存数据上重测报 0/23,并据此声明 R2 数字"未能复现"——**该撤回错误,现予更正**。

**根因(审计脚本缺陷,非数据或口径问题)**:脚本把 run 目录名 `exam298_<batch>_RXNG_<hash>` 规范成不含 `RXNG_` 的短号作 qid,而金标 qid 保留 `RXNG_<hash>` 前缀 → `qid → 金标` 逐题查找全部落空 → 诊断列假性归零。23/43 分流、1 可执行/22 不可执行等**不依赖金标列**的臂不受影响。

**修复与防再发**:脚本对金标与 run 名两侧统一采用含 `RXNG_` 前缀的同一规范形(`_norm_qid`);新增 fail-closed 自检——金标非空而任务题号零交集时直接失败退出,不再产出可被误读的"全 0"报告(自检结果随 `summary.json` 的 `n_task_qids_found_in_gold`=66 留痕)。

**修正后的复测**(同一封存数据,金标 SHA `9f5955d4…9211c` 不变):22/23 目标文本可解析,**8/23 目标 SMILES 匹配金标**,与 R2 原始口径一致(逐题行见 `rejections_reclassified.tsv`);15 条旧接纳金标诊断仍为 0/15。口径注记:8/23 是对模型目标**文本**的离线诊断列,不是管线成绩——被拒编辑不产出报告产物;初版报告 §0.3/§6 表中相应数字已同步更正。

## 7.1 Phase C 二轮复核阻断项修复:rank 不得选中原始 rule/analog 卡

**复核反例**(独立临时 run,见 [`EC298_PHASE_C_REVIEW_R2.md`](EC298_PHASE_C_REVIEW_R2.md) §1):同父检索含两张合格 recorded + 一张原始 analog 卡,rank 响应选中原始卡 → 未经适用性门禁与 AtomTool 编辑,其产物占报告第 1 位并提交 ReactionEvent,卡级 `card_eligible=true`。违反任务书 Phase C §5 / Phase B §2 交接约束。

**修复(全链路三层,可选择集与证据类型不因模型选择而改变)**:
1. **任务候选层**:`candidates` 仅含同底物且通过 recorded 完整资格判据的卡;原始 rule/analog 卡不再拼入可选集(留检索产物与裁决审查范围,作上下文不占可选择位)。解析层以任务候选为唯一合法 ID 集,引用原始卡 = `invalid_evidence_id` → 有界重试 → 显式停留。
2. **验证层**(`validate_products`):模型 rank 选择的**检索层**卡 kind 非 recorded → 全部产物拒绝,稳定拒因 `rank_selected_non_recorded`(防御层;提案卡不在检索集,不受此限)。
3. **裁决层**:检索层 rule/analog/novel 原始卡即使被选中 → `card_eligible=false`、`not_validated_for_reporting=true`、产物零占位,带 `not_validated_for_reporting` 拒因;order 内合格 recorded 不受牵连。

**反例夹具(rule 与 analog 各一对)**:端到端(选原始卡 → 零事件、零裁决、卡不进任务候选、3 次调用账、停留状态清晰)+ 裁决层纯函数(构造"选中原始卡"载荷 → 零占位、recorded 照常排名)。`test_rule_card_selected_via_rank_zero_commit`/`test_rule_card_rank_guard_at_adjudication_layer`/`test_analog_card_selected_via_rank_zero_commit`/`test_analog_card_rank_guard_at_adjudication_layer`。

## 8. 验收对照(任务书 §6)

1. **供体适用性**:§2 夹具表逐条 + `test_two_donors_different_applicability_select_eligible`/`test_parent_eligibility_selection_and_fallbacks`/`test_donor_budget_is_frozen_cap`/真实资产 R1(SHA 核对)。✅
2. **编辑执行**:SINGLE→DOUBLE、DOUBLE→SINGLE;form_bond 对已有键硬拒;先断后成 vs 反向;新原子/重复 ID/未知原子/断不存在键/目标与编辑不符/伪造 ID/价态/电荷与元素差异全部 fail-closed;结果与目标图逐项对账(`tests/test_edit_protocol.py` 15 测试,R3 增补 `Xx` 双层拒绝与先增后引两钉)。✅
3. **路由与回退**:唯一 recorded 不进模型(既有回归);弱映射 resolved 不再触发类比;适用性失败 → 受约束 novel(可停)带具体拒因;多供体只选有资格者;`analogy_enabled=false` 不影响 recorded/rank;无预算不发请求(既有回归);`referenced_evidence_id` 不串线(`tests/test_phase_c_workflow.py`)。✅
4. **恢复与审计**:供体裁决落盘/模型响应落盘/提案提交后硬杀恢复一致(新增 classify 注入点 + 既有恢复回归);资产/策略/prompt/协议版本变化拒绝旧 resume(代码身份+版本断言,`test_phase1_style_run_resume_rejected_then_migrate_from_works` 更新预期版本);无网络无凭证可跑。✅
5. **旧 23 拒绝再分类 + 15 接纳抽查**:§6 表;15 条接纳也经新门禁抽查,未只测旧拒绝。✅

## 9. dev 消融边界

**`dev_real_run_not_executed`**:本环境无 Chenyu/DashScope 凭证,未执行付费三臂 dev 20 对照。已交付零 API 离线臂:夹具门禁通过率、旧路线重分类、编辑协议夹具、开关路由变化(§6)。若后续在远端执行,须以同一冻结 dev 20 输入与预算配置、新 run ID 跑三臂(旧路由 / `analogy_enabled=false` / 新门禁+协议),不与 Phase B 批次互相挤占额度,不同模型/资产/预算明示不可直接归因。

## 10. 复现命令与产物 SHA

```bash
# 全仓回归(无凭证)
source ~/miniconda3/etc/profile.d/conda.sh && conda activate depending43
OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/ -q
# → 387 passed(2026-09-28 二轮复核修复后实测;含 Phase B 全部测试共同回归)

# Phase C 离线审计(封存只读;二轮复核修复后重跑)
OMP_NUM_THREADS=1 python scripts/phase_c_offline_audit.py \
  --seal-run-dir /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/dependingv43_dev/runs/ec298_v43r1 \
  --gold /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl
# → gold_coverage_gate=task_qids_covered_unique_and_gold_rows_unique,
#   n_task_qids_found_in_gold=66、n_gold_unique_qids=298;
#   金标诊断:拒绝臂 8/23(22/23 可解析)、接纳臂 0/15;再分类 1/22;
#   消融 23/43 —— 与修复前一致(唯一文本差异:一行拒因顺序,见 §11.9③)
```

关键文件 SHA256(前 16 位,完整值见仓库;三审补强后实测):`donor_applicability.py c417ecb188eb0561`、`atom_tool.py d049f9c4466712ae`、`policy.py b63a8da26209be84`、`prediction.py d217d145275f0955`、`nodes.py 2eb04d3606838107`、`report_adjudication.py a278277b58756073`、`analogy_editor.md 6d228935da95f59a`、夹具 `0e363307147d24b8`、`phase_c_offline_audit.py 52c2443c212a7ae7`。工作树改动快照 patch:`/tmp/phase_c_backup/worktree_snapshot_001035.patch`(实施中备份,不入仓)。

## 11. 限定与已知边界

1. 资格门禁是确定性**结构必要条件**,不证明机理或环境条件;`unverified_conditions`(增氢/电荷变化)逐条留痕,从不写成"环境相容"。
2. 芳香键级以 SINGLE 占位落图、由 sanitize 重感知,最终以 canonical SMILES 为准;中心查询携带键级,故"键级不符"多在枚举处表现为 `no_alignment`(F3),`bond_order_mismatch` 守卫由直接调用测试钉住。
3. 消融与再分类是**只读模拟/同输入重放**,不是新预测;23/66"仍适用"不等于这些题改走类比就能答对(旧结局 12 拒 / 6 弃 / 5 接纳、0 金标)。
4. 全量回归在共享工作树与 Phase B 交付共同通过;`test_state_isolation`/`test_export_v2` 等 Phase B 契约测试零退化。
5. 部分映射模板(反应在未映射区)按设计记 `unavailable` 不猜测;若未来要吃下这部分供体,须先做**资产侧**模板重映射(独立版本/哈希审核),不是放宽门禁。`enumerate_alignments` 对空 `center_atoms` 回退到全部带映射原子(与旧 `align_donor_mapping` 语义一致,回归测试钉住);该回退在 66 题预算内评估中无数字影响(此类模板先死于变换提取),属语义正确性修复。
6. 供体预算诊断:`max_donor_candidates=10`(仅诊断,未改冻结策略)可将 66 题中 applicable 提到 30;预算政策变更属 Phase D,须 dev 集验证。评估序缺陷(resolved 卡预算饥饿)已修复并以报告 §6.1 记录——教训:门禁的"拒因构成"必须与旧路由逐条对质后才能下结论,否则实现顺序会把评估覆盖问题伪装成化学事实。
7. **"66/66 不可达"的适用域限定(R3)**:§6.1 的分层定性与红线结论限定于**当前资产(供体找回按产物身份键定,39 次 `no_alignment` 的根源)、当前候选顺序(resolved 卡优先)、预算 3 与现行门禁**。Phase D 的检索键定改进(按底物相似度)或资产侧模板重映射可能改变该数字——那是"让更多供体在结构上站得住",不是放宽门禁;任一改动都先过 dev 集。
8. **R3 review 修复记录(实现级,协议语义不变)**:①审计脚本题号规范形 + 金标零交集守卫(§7);②`recorded_eligibility_reasons` 的空拒因对非 recorded 卡只表示"门禁不适用",`_usable_recorded` 与 rank 任务候选筛选两处显式限 kind,伪造挂牌的 analog 卡不得充当 usable recorded(钉子:`test_forged_analog_card_never_passes_as_usable_recorded`);③AtomTool 元素以 RDKit 周期表为事实源,预校验拒 `edit_invalid:bad_element`、执行层兜底 `edit_execution_failed:bad_element`,异常不再逃逸(钉子:`test_validate_rejects_fake_element_and_execute_stays_structured`);④`validate_edits` 引用检查按列表时点放行"先增后引"、仍拒"引用先于声明"(钉子:`test_add_atom_then_reference_in_later_edit_is_valid`);⑤对齐**评估全量**、落盘样本截 16、`n_alignments_assessed` 留痕(钉子:`test_all_alignments_assessed_beyond_storage_sample`;封存 66 题中 3 题 >16 匹配,修正后消融/再分类计数不变)。操作语言仍为 `v43-editproto-2` 所声明的四种操作,以上修复是把实现修正到与声明一致;相关文件代码身份变化照常拒绝旧 run resume。
9. **Phase C 二轮复核修复记录(§7.1 + 三项 P2)**:①P1 rank 原始卡直提——可选择集收窄为合格 recorded、`validate_products` 防御层、裁决层原始卡零升格(§7.1);②P2 审计金标覆盖门禁升级:**所有任务 qid 必须在金标中且唯一,且金标行自身不得重复**——金标为空 / 任务缺题 / 任务题号重复 / 金标同 qid 多行,任一发生都失败退出(初版只拒零交集;二轮补"缺一题"夹具后,三审仍复现金标行重复被 dict 静默覆盖的反例,已补 `_gold_index` 重复检出与夹具 `test_audit_fails_on_duplicate_gold_rows`;封存真金标 298 行 / 298 唯一,重跑 exit 0,`summary.json` 新增 `n_gold_unique_qids=298`、`n_gold_duplicate_qids=0`,四个 TSV 与金标诊断 8/23 均不变);③P2 编辑协议严格化:逐操作允许字段表,未声明字段拒 `edit_invalid:unknown_field:<name>`,旧别名 `remove_bond`/`add_bond` 拒 `edit_invalid:unknown_op`(无旧协议分派需求,直接拒绝;钉子:`test_validate_rejects_undeclared_fields_and_legacy_aliases`)——封存再分类有一行因 add_atom 带多余 `atom2` 字段拒因文本顺序变化,分类与计数不变;④P2 对齐枚举显式上限 `_ALIGNMENT_ENUM_LIMIT=2000`(RDKit 缺省 1000 也静默截断),触顶 `alignment_limit_exceeded` fail-closed:已评估有目标 → ambiguous(截断集合不得当唯一适用目标)、全败 → unavailable(不得假阴性 inapplicable)(钉子:`test_alignment_enum_limit_explicit_and_truncation_flagged`/`test_truncated_enum_never_claims_unique_target`;封存 66 题均在限内,各臂计数不变)。
