# v4.3 EC298 Phase C 任务书：类比适用性与 AtomTool 编辑协议

> 交给独立实施模型；本会话只负责 review。目标仓：`/Volumes/CC/Enzyme_Agent/dependingv43/`。依据已验收的 [`EC298_PHASE_A_REPORT.md`](EC298_PHASE_A_REPORT.md)、[`EC298_PHASE_A_REVIEW.md`](EC298_PHASE_A_REVIEW.md) R3、[`EC298_REVIEW_R2.md`](EC298_REVIEW_R2.md) §4/§6 和 [`TASK_V43_EC298_PHASE_B.md`](TASK_V43_EC298_PHASE_B.md)。**Phase C 可与 Phase B 并行开发**，但正式合并后需共同回归；本任务聚焦类比供体适用性、编辑执行与回退，不修改 Phase B 的报告排序/导出契约，也不开展 Phase D 的 prompt、思考预算或成本调参。

## 0. 问题、目标和证据边界

Phase A 首跑的 66 条类比路线为：弃答 28、AtomTool 编辑拒绝 23、接纳提案 15；接纳的 15 条在本卷均未命中。23 条拒绝中 20 条含 `bond_already_present`、3 条含 `unknown_atom`；22/23 个目标 MoleCode 可解析，但只有 8/23 个目标 SMILES 直接匹配金标。上述是**已见 298 题的事后归因**，不能把 23 条拒绝当作可恢复命中，也不能根据金标改路由或放宽门禁。

当前 [`policy.py`](../src/pathway_v43/domain/policy.py) 见到任一 `mapping_status=resolved` 就进入 `analogy_edit`；[`prediction.py`](../src/pathway_v43/services/prediction.py) 只拿检索排序第一条 resolved 卡；[`analog_source.py`](../src/pathway_v43/services/analog_source.py) 可把“唯一模板 + 反应中心子图命中”标为 resolved，而 [`atom_tool.py`](../src/pathway_v43/services/atom_tool.py) 取第一个 RDKit 子结构匹配。`resolved` 只证明**找回并对齐**，尚不证明供体反应可迁移。现有 AtomTool 独立检查引用和目标文本，未在真实分子图上按序执行编辑、核对结果与目标结构；当前编辑语言也缺 `change_bond_order`。

目标：把 **来源映射状态、化学适用性、模型编辑执行、最终产物验证** 分为四个可审计阶段；只有通过适用性门禁的供体进入类比任务，模型编辑必须在当前分子图上逐步执行并与目标 MoleCode 一致。结果属于受约束预测，不声称机理证明或环境条件已实测。

## 1. 与 Phase B 的并行边界和版本策略

1. Phase C 主要改 `services/analog_source.py`、`services/atom_tool.py`、`services/prediction.py` 中的供体块、`domain/policy.py` 中的类比资格、`configs/prompts/analogy_editor.md`、对应测试及少量 `workflow/nodes.py::_apply_analogy` 接线。Phase B 负责 `report_adjudication`、导出和报告宽度。两边在 `nodes.py`/`prediction.py` 若有交叠，只提交各自独立函数与明确接口；合并时由一个整合提交解决冲突，不用旧版同名函数覆盖对方改动。
2. 约定交接字段：检索卡仍保留 `mapping_status/mapping_reason/donor_refs` 表达**来源找回**；新增版本化 `applicability`（状态 `applicable|inapplicable|ambiguous|unavailable`、逐项 gate、候选供体列表、选中供体 ID、对齐及理由）表达**迁移资格**。Phase B 只读取这一资格/最终提案验证结论，不自行推断“resolved 即可报告”。已记录 exact 反应的直通与 `rank_candidates` 优先级不变。
3. 新任务、提示词、门禁和策略分别升 schema/version，并进入 `run_identity`/task_id；新代码不得静默 resume 旧 run。旧类比任务及提案仍能被只读审计，不能被新适用性规则追认成旧首跑的新答案。原始 298 run、Phase A 产物、资产与 v3 冻结评测器逐文件保持原样。
4. 工作树已有其他任务改动。实施前记录状态与起点 SHA；不要清理、重置或顺手改 Phase B 文件。若共享文件出现冲突，交付清晰补丁及整合说明，不以“暂时把 Phase B 回退”解决。

## 2. C0：先建人工审过的供体适用性夹具与离线消融

建立小而有判别力的、**不从 298 金标反推**的供体/目标底物夹具。每条固定资产供体 `record_id`、文件 SHA、`mapped_lhs/mapped_rhs` 与当前底物、预期适用性、理由和审核者/日期；从现有资产选例并可增加合成负例。至少覆盖：全供体准确匹配、中心匹配但一阶邻域冲突、键级不符、可用氢不足、形式电荷/价态冲突、对称位点等价匹配、竞争位点得到不同转化、多条供体指向不同变化、没有可靠供体、来源无映射或 QC 不足。夹具应同时有正例、负例和需弃权的歧义例；任何标签争议留 `uncertain`，不硬纳入通过率分母。

在实现新门禁前，使用**只读封存 dev 产物**或同输入的离线检索输出做一次原路由审计：有多少条 `resolved`、其中多少仅中心匹配、多少供体只覆盖 2–3 个中心原子、哪些被送到模型、最终弃答/拒绝/接纳如何分布。另设计 `analogy_enabled=false` 的消融开关，保持 recorded/rank 先行；类比关闭时，若现有工作流确有独立且已验证的规则路线，可走该路线，否则按现有策略与预算尝试 `novel_proposal`，不满足则显式停留。不能为消融新造未经验证的规则执行器，也不能把已知 exact 随开关改走 novel。先验证开关的路由差异及调用预算，不用旧 run 重新判分冒充新预测。

## 3. C1：供体变换与适用性门禁

从映射模板的 `mapped_lhs → mapped_rhs` **确定性提取反应变化**：保留/新增/消失原子映射号、元素/电荷/氢变化、被断/新成的键及键级变化；模板可解析、映射号唯一性、双侧关系和原有 `qc_flags` 逐项检查。不能仅凭 `qc_flags.bijection=true` 假定实际映射有效；模板不完整时记录 `unavailable` 与具体拒因，不补造原子映射。供体的原反应物/产物、反应中心、变化表、资产文件/SHA/行号写入不可变审计产物。

对每个供体枚举当前分子的**全部相关对齐**，先尝试全供体，再以明示的中心子图策略作保守候选；不能无条件取 RDKit 返回的第一个匹配。每个对齐须检查反应中心原子/键对应、一阶邻域约束、芳香性和键级、形式电荷、可用氢、预期编辑的价态可执行性及已有路径约束；缺少可判断的条件则 `unknown`，不得写成环境条件相容。对称对齐若施加变化后得到相同目标结构，可按稳定键合并并保留所有匹配引用；若得到不同目标或供体互相冲突，应标 `ambiguous`，不得只拿第一个。明确哪些检查是**确定性结构必要条件**，哪些仍是未证实的生化适用性。

对同一父节点最多检查冻结配置中的 N 个候选供体（N、候选枚举顺序和 tie-break 写入策略身份）。当前 `build_card_mapping_fields` 在多模板时只给 `ambiguous`、不对齐任何一条；新评估器须读取这些真实 `donor_refs` 逐条核查，不能把歧义卡直接丢弃或伪装成唯一模板。多供体按**可执行且证据充分**优先，再按固定、可说明的来源与检索位次排序；不能跨来源直接比较引擎 score 或以金标选供体。若无唯一可信供体，按开关和预算走既有 fallback，理由分别记为 `no_mapping`、`mapping_ambiguous`、`applicability_failed`、`applicability_unknown`、`multiple_competing_transforms`，不把这些情况统称“无证据”。PredictionTask 只拿选定且通过门禁的供体，同时保留其它评估过的供体及拒因摘要；`referenced_evidence_id` 必须与选定供体所属证据 ID 一致。

## 4. C2：版本化编辑协议与 AtomTool 顺序执行

扩展类比编辑协议，至少支持 `change_bond_order`（明确 from/to 键级，例如 SINGLE→DOUBLE），并保留受控的 `break_bond`、`form_bond`、`add_atom`。每条操作结构化校验 `op`、原子 ID、新原子 ID、元素和键级；未知字段/操作、重复新 ID、引用不存在原子、非法键级、重复成键、断不存在的键均有稳定拒因。**`bond_already_present` 仍是 form_bond 的硬拒绝**，不得通过忽略该错误来放行单→双键；必须显式使用键级变更并检查原键级。

在当前 RDKit 图的副本上**按列表顺序执行**编辑，每一步用更新后的图/原子 ID 映射检查操作前提和价态；中间态若是预期短暂不满足完整价态，可允许事务内暂存，但每一步仍须满足拓扑、身份和操作前提，最终必须 RDKit sanitize 成功。旧原子 ID 不能凭空消失或变更元素；新增原子 ID 与元素、价态、外源元素例外须一致。模型给出的 `target_molecode` 独立解析并按实际节点/边及 ID 校验，**不能只在文本中用正则搜到 ID 就算结构相符**；编辑执行后的分子图与目标图必须在原子 ID、元素、键、键级、形式电荷、必要立体信息上同构，最终 canonical SMILES 一致。若目标与编辑不一致，`target_edit_mismatch` 拒绝；空 `edits` 仅在目标图与当前图确实相同且策略允许 no-op 时成立，否则拒绝。

继续保持 MoleCode 往返能力边界、vendor 7/7 哈希和原有元素门禁；若需要扩展 MoleCode 表示，先做独立版本/来源/哈希审核，不能直接改 vendor 文件绕过完整性校验。对断裂成多个组分、质子转移、立体变化、芳香键与不支持元素给显式边界，无法无损执行则弃权或拒绝，不生成近似结构。AtomTool 通过只说明编辑协议与表示一致，**最终提案仍须经过现有 `validate_event_products`、来源/方向/循环/元素等确定性门禁**。

## 5. C3：工作流接线与失败语义

- 类比资格由 C1 的 `applicability` 决定，`mapping_status=resolved` 单独出现不再触发 `analogy_edit`；仅已验证的适用供体可进任务。为旧检索卡建立明确兼容读取：缺 `applicability` 一律按 `unavailable/not_assessed`，新 run 可从原始供体资产重新评估，旧 run 不追写。
- 模型返回 `apply` 时，先核对选中供体引用与 PredictionTask，随后 AtomTool 执行 `edits`、核对目标 MoleCode，再生成提案卡并走原有验证/提交；任一步失败写结构化 `rejected` 及操作索引、供体/对齐/资产引用。模型 `abstain`、供体不适用、表示有损、编辑拒绝、LLM 预算耗尽分别计数。不得把传输/解析失败写成化学不适用。
- fallback 仅用已有、可说明的规则/novel 路由和预算；`novel_proposal` 在“有检索产品但映射/适用性失败”时应如实保留这个上下文，不宣称完全无证据。保留 `prediction_call/response/orphan` 账本，重试及崩溃恢复不会新增重复事件、漏记调用或把失败改成成功。
- 与 Phase B 合并时，类比提案只有通过最终结构与产品门禁后才可成为 `reportable` 候选；供体原始产物不可作为当前底物的报告产物。若 B 尚未完成，Phase C 先在现有单卡报告语义下测试，集成测试待两边合并后补做。

## 6. 必须覆盖的验收用例

1. **供体适用性**：同一反应中心、不同邻域的适用/不适用对照；全供体优于弱中心对齐；同供体多个等价匹配合并、竞争匹配拒绝；两供体适用性不同、同级冲突弃权；`qc_flags` 假阳性、映射号重复、键级/氢/价态冲突均留拒因。用真实资产中至少一组可复核模板作集成夹具，并核对文件 SHA。
2. **编辑执行**：SINGLE→DOUBLE、DOUBLE→SINGLE 成功夹具；`form_bond` 对已有键仍报 `bond_already_present`；先断后成依序可行，反向顺序失败；新原子引用、重复 ID、未知原子、断不存在的键、目标 MoleCode 与 edits 不符、文本伪造 ID、非法价态、表示有损和立体/电荷差异均 fail-closed。反应执行结果与目标图/SMILES 逐项对账，而不只是解析成功。
3. **路由与回退**：unique recorded 不进模型；弱映射 `resolved` 不能再单独触发类比；适用性失败转受约束 fallback 或显式停留；多个供体只选有资格者；`analogy_enabled=false` 不影响 recorded/rank；无预算时不发模型请求。对同一路径的祖先链、兄弟路径和 `referenced_evidence_id` 不串线。
4. **恢复与审计**：在供体裁决落盘、模型响应落盘、提案/事件提交后各硬杀一次；恢复的供体选择、AtomTool verdict、模型调用数、最终事件与答卷哈希一致。资产/策略/prompt/编辑协议版本变化拒绝旧 run resume；旧首跑封存哈希不变。新增测试无网络、无凭证可运行；全仓现有回归不退化。
5. **已见 23 条编辑拒绝的离线再分类**：只读封存请求/目标/拒因，逐题列旧拒因、新协议在相同输入下的“可执行/不可执行/不确定”及原因；**目标是否匹配金标另列离线诊断列**，不把 8/23 写成新模型成绩，不向模型回灌这些结果。15 条旧接纳也需抽样检查新适用性门禁能否识别风险，不能只测旧拒绝。

## 7. dev 消融、交付与 review 门槛

先交**零 API 离线结果**：人工审核夹具、供体/对齐适用性门禁通过率、旧类比路线重分类、编辑协议夹具、关闭类比开关的路由变化。若需真实 dev 对照，用同一冻结 dev 20 输入与预算配置，新 run ID 分别运行旧路由、`analogy_enabled=false`、新适用性+编辑协议三臂；已有可复核旧 dev 批次可作基线，但不同模型/资产/预算必须明示不可直接归因。付费批次需先冻结每臂调用上限、模型与费用账，避免与 Phase B 的并行批次互相挤占共享 API 额度。**298 不作为调参集或新盲测**，若后续复跑只写 `post_hoc_repair_check`。

报告至少按臂列：进入类比的父节点数、供体资格通过/拒绝/歧义、模型弃答率、编辑拒绝率、接纳提案有效率、类比命中率、novel fallback 命中率、总 `cn/raw_sb` @1/@3/@5、展开数、LLM 调用数与成本。每项写分母与可追溯任务/产物引用；dev 20 若类比样本很少，报告 `n` 和置信限制，不能用单个总体分数宣称修复有效。评测必须调用同一冻结 v3 评测器；新实验不得覆盖旧 dev/298 答卷。

交付 `docs/EC298_PHASE_C_REPORT.md`、夹具与审核说明、供体/编辑协议 schema 与版本、代码和无凭证测试、旧拒绝再分类表、离线消融及有条件的 dev 实测对照、复现命令和产物 SHA。review 的阻断点是：**`resolved` 仍被当作适用；任取第一个匹配/供体；编辑只检查引用不执行；目标文本伪造原子 ID 可通过；用取消 `bond_already_present` 放行键级变化；用金标或已见 298 选择供体/门槛；回退后预算、调用账或旧 run 身份不一致。**
