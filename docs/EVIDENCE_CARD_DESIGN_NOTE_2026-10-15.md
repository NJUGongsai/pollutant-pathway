# 候选证据卡设计书（Phase A 产出，2026-10-15）

> 任务书 `docs/TASK_EVIDENCE_CARD_IMPL_2026-10-15.md` §三；Plan v1 §2.1。
> 题域标签：298。结论：六类证据事实五类在线可得；donor 匹配层级与
> EAWAG/corpus 通道细分**v1 范围不纳入**——部分通道事实可得但完整
> 恢复尚未证明（§四矛盾停点;P1 修复轮 2026-10-15 措辞纠正,原
> 「不可在线获得 → 不做」说得过满）。

## 一、入口枚举（同一证据函数共用）

| 入口 | 位置 | 说明 |
|---|---|---|
| decide 主调用 | `_run_decide`→`_model_proposals`→`_call_real_fetch` | 池条目装配唯一处 |
| 格式反馈轮 | `_model_proposals` 内复用 `_call_real_fetch` | 证据自动一致 |
| 序列化/发送 | `ppv1_real_fetch`→`build_proposals_user_payload` | 唯一 JSON 渲染点 |

scripted 桩继承 `ppv1_real_fetch`，scripted/real 同载荷路径。接线点
定死两处：`_call_real_fetch`（证据计算）+ `build_proposals_user_payload`
（渲染）。池/检索/排序/去重零触碰；证据调用期现算，不入 run_inputs。

## 二、字段清单冻结（来源=spec+prepared+底物 RDKit 计算；缺失=unknown）

**a. 候选级（每池条目 `evidence` 子对象）**
- `edit_summary`：spec.edits 逐 op 确定性渲染（n_edits/op_counts/
  bonds_broken/bonds_formed/bond_order_changes/added_atoms）；
  edits 缺 ⇒ unknown（s5b_compiler.py:981 产出，production.py:391 校验）
- `participants[]{side,role,coefficient,coefficient_status,smiles}`：
  prepared.hypothesis.participants 直读（production.py:498-521 单一装配
  源，含共底物显式与缺省装配两形态）；smiles 由 prepared.states 回查；
  prepared 缺 ⇒ unknown（不重派生第二套装配）
- `source{source_kind,transformation_ref,origin_group_key,alignment_ref}`：
  key 前缀+origin_group_key+alignment.ref 确定性派生
  （rec-∧recorded-inferred:*⇒recorded_inferred；tpl-⇒analog_template）
- `alignment_quality{status,mapping_origin,n_alignments_total,
  n_equivalent_alignments,enumeration_truncated,stereo_dissolution_
  applied,n_donor_atoms_mapped}`：spec.alignment+spec.compile 直读
  （s5b_compiler.py:1075-1100 在线诊断块）
- `conditions_and_scope{requirements,participant_list_status,step_scope}`：
  spec.requirements（键在位=真值可空表，键缺=unknown）+spec 两 scope
  字段（按 production.py:534-536 同一缺省规则）

**b. 底物级（顶层 `substrate_evidence`）**：functional_groups（模块固定
SMARTS 表×atom_tool.render("S") 同 ID 空间，类序=渲染序）/gasteiger_
charges_reference（参考描述符，字段名自带 _reference）/element_counts/
molecular_formula/representation_fidelity/condition_keys_known（后两项
substrate_profile 在线值穿参，缺=unknown）。

**c. 检索级**：并入 alignment_quality（compile.truncated=枚举截断等）。
builder 逐候选谱系行不入 spec 本体 → decide 不可见，不消费。

## 三、载荷形状（定死一种）

pool_hypotheses[] 每条新增 `evidence` 子对象 + 顶层 `substrate_evidence`
与 `candidate_evidence_schema_version`（"candidate-evidence-2";P1 修复
轮 2026-10-15 由 -1 升 -2,理由见交付书 P1 修复轮节）;未接线
调用方三键全缺 ⇒ 载荷字节与现状逐字节同。提示词 Rules 段尾增补「候选
证据字段语义+unknown 处理+描述符纪律」最小段 ⇒ PROPOSALS_PROMPT_VERSION
自动升版=新批身份（CI T1 基线同步钉新值）。

## 四、矛盾停点（部分事实可得但完整恢复未证明 ⇒ v1 范围不纳入，不硬造）

> P1 修复轮（2026-10-15）措辞纠正：原「通道事实完全不入 spec、decide
> 完全不可获得」说得过满——部分通道事实实际可得，但完整恢复尚未证明。

1. donor 匹配层级 strict_exact/cn：检索期候选包装字段，不进 compile
   spec；donor_smiles 不在 spec 上，decide 期不可复算 ⇒ v1 不纳入
   （部分事实可得：检索包装 `donor_match_kind` whole/component 在；
   层级与供体串未整体进入 spec，完整恢复尚未证明）。代之以在线
   mapping_origin/n_alignments/status。
2. EAWAG vs corpus 通道：**部分通道事实可得**——corpus 两条路径在
   spec 写 `corpus` 块（块在位 = corpus 正向标记），但通道名只在那与
   builder 诊断行，strict_exact/cn 层级与合并后来源的完整恢复尚未
   证明 ⇒ v1 范围不纳入；source_kind 只分 recorded_inferred/analog_
   template。**不得**为补字段透传整个 `corpus` 块（内含 EC，禁展示）。

## 五、确定性声明与预期影响面

同输入 ⇒ 同载荷字节（纯函数/无随机/无时序/列表显式定序/sort_keys 兜
底；Phase C 探针双跑验证）。提示词哈希变（全批身份变化；resume 拒旧批
=预期）；池条目集合与顺序/run_inputs/判分侧零变化；tokens 增量估算
≈每候选 200-500 B×池宽 8+底物档案 400-800 B ≈ +2~5 KB/题（298 题域，
发车前 CC 拍板）。
