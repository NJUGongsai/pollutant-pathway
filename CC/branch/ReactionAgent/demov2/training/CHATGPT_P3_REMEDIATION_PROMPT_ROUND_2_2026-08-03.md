# ChatGPT → P3 Round 2 严格返工提示词

> 用途：把本文件交给负责 `codex/p3-strict-kernel` 的 coding agent。
>
> 本轮不是扩展功能，也不是进入 P4；目标是修复 ChatGPT P3 Round 1 只读审阅中已经被独立对抗探针复现的实现不变量错误，并提交可复现的 Round 2 审核材料。

---

## 0. 你的角色与最终状态

你是 **P3 remediation worker**，只负责修复 P3 strict one-step kernel。

你不能：

- 修改 P0/P1 authority、final design/plan、ADR 来迁就当前 P3 代码；
- 把 P3 的实现不变量错误解释成“真实数据缺失所以 BLOCKED”；
- 进入 P4 ranking/abstention、P5 benchmark、P6 MCP；
- 用增加测试数量代替修复真实漏洞；
- 把 synthetic fixture 冒充 real evidence；
- 通过硬编码报告、状态字符串或人工布尔值制造 PASS。

本轮期望达到的诚实状态是：

```text
P3_IMPLEMENTATION_INVARIANTS = PASS
P3_SYNTHETIC_FIXTURE_MACHINERY = PASS
P3_P4_INTERFACE = READY_FOR_CHATGPT_REVIEW
P3_REAL_EVIDENCE_GATE = BLOCKED
```

真实 snapshot、automatic donor view 和 P2 pilot 仍缺失时，正式 P3 scientific Gate 继续 `BLOCKED` 是正确结果；但所有纯实现和 fixture machinery 不变量必须修复并独立通过。

---

## 1. 唯一工作目录与运行环境

必须在以下独立 worktree 中工作：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2
```

预期分支：

```text
codex/p3-strict-kernel
```

该 worktree 当前没有本地 `.venv/bin/python`。不得安装依赖，也不得谎报以下不存在的命令可运行：

```text
.venv/bin/python
```

使用已有主项目虚拟环境：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

建议设置一个仅用于文档简写的 shell 变量时，使用任务专用变量名，例如：

```bash
P3_PY=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

不得使用或覆盖 `$HOME`、`$CODEX_HOME` 等系统变量。

---

## 2. 开始前必须记录真实 Git 状态

在修改任何文件前，运行并保存输出：

```bash
cd /Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2
git rev-parse --show-toplevel
git branch --show-current
git log -1 --oneline
git status --short
git diff --stat
git diff --name-status
git ls-files --others --exclude-standard
```

当前 worktree 已知不是干净状态，含大量继承的 P1 修改与 untracked 文件。你必须：

1. 把 starting dirty state 原样记录到：

   ```text
   reports/p3/P3_ROUND_2_STARTING_WORKTREE_STATE.md
   ```

2. 明确区分：

   - 本轮开始前已存在的修改；
   - 本轮实际新增或修改的 P3 文件；
   - 本轮结束后的全部状态。

3. 不得把 `_changed_files()` 的预设目录遍历冒充真实 Git changed-files；
4. 不得声称“No P0/P1 files modified”，除非 starting/ending diff 证明本轮没有改变它们；
5. 不得执行 `git reset`、`git checkout --`、`git clean`、`stash`、`merge`、`push`、`commit`；
6. 不得删除、覆盖或整理不属于本轮的用户/其他 agent 产物。

如果无法可靠区分 starting 与 ending delta，必须在提交中明确写 `PROVENANCE_BLOCKED`，不能猜测。

---

## 3. 修改前必须完整阅读

### 3.1 最终权威设计

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_discussion.md
```

重点重读 `final_plan.md` P3 §6.1–§6.11。

### 3.2 冻结 ADR 与 P1 authority

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0001-authority-and-scope.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0002-hypothesis-lanes.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0003-ledger-and-source-semantics.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0004-partial-eligibility.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0005-scientific-decision-authority.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0006-mcp-side-effects.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_FINAL_PASS.md
```

### 3.3 P3 原始实施要求与 Round 1 提交

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/CHATGPT_P3_IMPLEMENTATION_PROMPT_2026-08-03.md
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/SUBMISSION_TO_CHATGPT_P3.md
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_GATE_REPORT.json
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_MUTATION_RESULTS.json
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/p3_p4_interface_manifest.json
```

P2 当前仍是 formal Gate `BLOCKED`。不得把 P2 truth/isolation/Gate/mutation 当作已冻结 scientific authority。

---

## 4. 核心目标不能改变

系统的核心不是“套一个最近邻模板”，而是：

```text
用户只输入 X
→ 在指定 train-only fold 中检索结构相似且 eligible 的 distinct donor A
→ 对每个 A 读取它在 authority 中所有 eligible、完整、可审计的 reactions
→ 对每条完整 A→B transformed lineage 提取 strict transformation
→ 在 X 上枚举满足该 transformation 的 conditioned sites
→ 确定性 graph edit 生成 Y
→ 严格 replay、lineage、dual-ledger 和 provenance 验证
→ 输出 unranked strict candidates + immutable trace
```

特别强调：

- `distinct donor A` 不等于“每个 A 只取第一条 reaction”；
- 同一个 A 的多个不同完整反应必须全部进入后续 transform 枚举；
- duplicate/mirror/source-equivalent reaction 要去重，但 transformation diversity 不能丢失；
- 完整 reaction 包含所有参与物、co-substrates、cofactors、coproducts、mapping、lineage、source ledger 与 provenance；
- COFACTORS 只能是 role prior，不能用于破坏性剥离；
- formal mapping 不等于 mechanistic atom origin；
- fixture 只能证明 machinery，不能证明真实科学性能。

---

## 5. 必须先写 RED tests，再修改实现

每个缺陷必须遵循：

```text
1. 写一个只针对该缺陷的 RED test；
2. 运行并保留 RED 失败证据；
3. 做最小、明确、可审计的实现修改；
4. 运行 GREEN；
5. 运行相关模块回归；
6. 运行 P3 全套；
7. 最后运行 full suite 与 Gate。
```

禁止：

- `pytest.raises(Exception)`；
- 同时注入多个无关非法字段，让测试因错误原因通过；
- helper 尾部 `assert False`，外层又捕获宽泛异常；
- 通过改测试接受错误行为；
- mock 掉被测试的核心 production validator；
- 只断言“总体仍为 BLOCKED”来声称 mutation caught；
- 把某个已存在 P1 helper 的测试冒充 P3 production path 的测试。

每个 negative test 必须验证准确的 typed exception 或 failure code。

---

## 6. R2-A：修复 normalization 与证据标签

### 6.1 Signed formal charge

当前 `NormalizedQuery` 把 `formal_charge` 与 atom/fragment count 一起限制为非负数，导致合法阴离子失败。

要求：

- `heavy_atom_count >= 0`；
- `fragment_count >= 1` 对有效 query；
- `formal_charge` 必须是任意合法有符号整数；
- 覆盖正、负、中性、多 fragment 总电荷。

至少新增：

```text
test_negative_formal_charge_is_valid
test_positive_formal_charge_is_valid
test_multifragment_total_formal_charge
```

必须覆盖：

```text
[Cl-]
C[O-]
C[N+](C)(C)C
CCO.[Na+]
```

### 6.2 Isotope policy 必须与实现一致

当前默认声明 `preserve_isotopes`，但 `isomericSmiles=False` 会删除 isotope marker，导致 `[13CH4]` 与 `C` identity 相同。

要求：

- 如果 policy 是 `preserve_isotopes`，isotope 必须进入 canonical identity/hash；
- stereo 忽略策略不能顺便删除 isotope；
- 如果无法实现，必须更改明确的 versioned policy，并使报告与 schema 一致；不得口头声称 preserve。

至少新增：

```text
test_preserve_isotopes_policy_distinguishes_identity
test_stereo_agnostic_identity_preserves_isotope
test_candidate_identity_policy_matches_query_identity_policy
```

### 6.3 Evidence kind 必须由 run context 传播

当前 `normalize_query()` 无条件输出 `EvidenceKind.real`，导致 fixture KernelResult 内嵌 `NormalizedQuery(real)`。

要求：

- fixture run 的所有输出对象都必须明确为 `synthetic_fixture`；
- real run 才能标 `real`；
- diagnostic/blocked 也必须明确；
- 不得让调用者随意把 fixture 重标成 real；
- 证据种类必须来自 immutable run context/manifest。

至少新增：

```text
test_fixture_run_contains_no_real_evidence_labels
test_real_mode_cannot_consume_synthetic_train_view
test_evidence_kind_cross_object_consistency
```

---

## 7. R2-B：修复 fold isolation 与 donor/reaction 语义

### 7.1 Fold authority

当前 loader 接受外部 `fold_id` 并覆盖 `train_view.fold_id`。

要求：

- fold ID 只能由冻结 train-only view/snapshot manifest 提供；
- caller fold 与 train view fold 不一致必须 typed reject；
- donor participant、reaction、lineage、truth/product/source provenance 全部必须属于 train fold；
- test/query truth 不得出现在 retrieval 或 loader 输入对象；
- 对 train view 做结构化 authority/hash 验证，不能只信一个字符串标签。

至少新增：

```text
test_requested_fold_must_equal_train_view_fold
test_test_fold_donor_rejected
test_test_fold_reaction_rejected
test_test_truth_or_product_not_accessible_to_retrieval
test_train_view_hash_or_manifest_mismatch_rejected
```

### 7.2 Distinct donor A 与所有 reaction 分离建模

当前 retrieval 汇总 `reaction_ids`，loader 却按 donor identity 只返回第一条 reaction。

要求重新设计接口：

```text
RetrievedDonor A
  └── eligible_reaction_refs[]
        └── explicit reaction_id/source/reaction hash/lineage refs
```

loader 必须按 explicit reaction reference 加载，不得按 donor identity 查找后返回第一条。

kernel 必须对每个 selected A 的所有 eligible complete reactions 执行：

```text
reaction load
→ lineage enumeration
→ transform extraction
→ sites
→ generation
→ validation
```

要求：

- canonical reaction duplicate、source mirror、同 publication/lineage duplicate 不重复占支持；
- 不同 reaction type/transform 必须保留；
- 同 A 多 reaction 的处理结果与 donor entry 顺序无关；
- trace 可看到 A 与每条 reaction 的一一对应；
- stop reason 反映 donor/reaction expansion，而不是固定字符串。

至少新增：

```text
test_same_donor_all_eligible_reactions_are_loaded
test_same_donor_reaction_order_invariant
test_duplicate_mirror_reaction_dedup
test_transform_diversity_not_lost_during_dedup
test_trace_links_each_donor_to_each_processed_reaction
```

### 7.3 Retrieval 必须真正 adaptive

当前实现本质是单轮 fixed Morgan top-K。

要求：

- distinct donor identity；
- deterministic adaptive rounds；
- source/lineage quality；
- identity diversity；
- transform/reaction diversity；
- size/charge structural compatibility；
- version/config/seed；
- typed stop reason；
- excluded/quarantine counted once；
- similarity 只能表示 structural retrieval，不是 activity/probability/confidence。

真实 donor authority 未接入时，允许保持 real mode `BLOCKED`，但 fixture machinery 必须完整测试 adaptive control flow。

---

## 8. R2-C：修复 complete reaction loader

当前 `_check_complete_record()` 通过 participant ID 是否包含 `reactant`/`product` 字符串判断完整性，无法证明 reaction 完整。

要求：

- 不依赖 participant ID 命名；
- 对比 reaction evidence、participant multiset、mapping report、resolved lineages、source ledger、eligibility 与 provenance；
- participant 数量、side、molecule IDs、atom-map ownership 必须交叉一致；
- evidence participants 被删除时必须 typed reject；
- cofactor/co-substrate/coproduct 不得丢失；
- source ledger 中的 source/sink/unknowns 必须能引用真实 participant；
- partial map、critical ambiguity、unresolved conditional eligibility 必须 fail closed；
- conditional eligibility 只有在对应条件被明确满足时才能进入 strict path。

至少新增：

```text
test_reaction_evidence_participant_deleted_rejected
test_participant_multiset_mismatch_rejected
test_participant_side_mismatch_rejected
test_mapping_participant_reference_mismatch_rejected
test_lineage_participant_reference_mismatch_rejected
test_source_ledger_participant_reference_mismatch_rejected
test_cofactor_and_cosubstrate_multiset_preserved
test_unresolved_conditional_eligibility_rejected
```

---

## 9. R2-D：修复 transformation content addressing

### 9.1 Selected lineage

当前 transform hash 使用 `context.resolved_lineages[0]`，而输出 `source_lineage_ids` 使用实际 selected lineage。

要求：

- canonical hash/ID 必须使用实际 selected lineage；
- explicit `lineage_id` 与 role-selected primary lineage 都必须一致；
- 非第一条 lineage 的 replay/hash 必须测试；
- unknown/critical ambiguous lineage 必须拒绝。

### 9.2 完整 hash preimage

canonical transform preimage 至少包含：

- selected lineage ID/hash；
- reaction ID/hash；
- mapped edits；
- bond operations/order；
- atom state changes；
- transferred atoms及 source participant；
- removed atoms及 sink participant；
- donor site；
- local environment；
- strict preconditions；
- ledger requirements；
- transform/compiler/schema/policy versions。

任何上述语义变化都必须改变 transform hash；纯 atom ordering 变化不得改变。

### 9.3 Mapping 与 edit 完整性

要求：

- duplicate map numbers typed reject，不得字典覆盖；
- aromatic bond order不能被 `int(1.5)` 静默变为 single；
- multi-atom transferred group 要保留 transferred-transferred bonds；
- removed atom必须解析真实 sink，不能用 `_ = removed_maps` 跳过；
- `unknown_source`/unknown sink 不得进入 strict transform；
- donor site atom maps 不能混淆“donor 中存在的 site atoms”与“生成时新增的 transferred atoms”；
- aromaticity、charge、degree、H、neighbor/bond environment 纳入 strict preconditions。

至少新增：

```text
test_selected_nonfirst_lineage_changes_transform_identity
test_transform_hash_covers_preconditions_and_ledger_requirements
test_duplicate_atom_map_rejected
test_aromatic_bond_order_preserved
test_multiatom_transfer_internal_bonds_preserved
test_removed_atom_sink_required
test_unknown_transfer_source_rejected
```

---

## 10. R2-E：修复 conditioned site 与 graph-edit fail-closed

### 10.1 Site contract

要求：

- site 必须引用同一 run/query/fold/snapshot/transform；
- SMARTS/graph pattern 必须正确处理环和 aromaticity；
- transform map role 不能在 symmetry dedup 中被错误折叠；
- ambiguity group 必须表示真正同组的替代解释，不是简单 row index；
- `local_environment_similarity` 若保留，必须有明确、可审计语义，不能只是通过 precondition 的比例并冒充 environment similarity；
- unknown precondition kind typed fail closed。

### 10.2 Graph edit 不得跳过关键步骤

以下情况必须返回 typed failure，不能 log 后继续：

```text
site.transformation_id != transform.transformation_id
site.query_id != query.query_id
required bond endpoint missing
required atom-state target missing
delete bond expected but absent
add bond expected but already exists
order-change source bond absent
removed atom missing
transferred anchor missing
unexpected disconnected fragment
undeclared edit
sanitize/aromaticity failure
```

建议 typed codes：

```text
TRANSFORM_SITE_ID_MISMATCH
QUERY_SITE_ID_MISMATCH
MISSING_EDIT_ENDPOINT
EXPECTED_BOND_ABSENT
UNEXPECTED_EXISTING_BOND
ATOM_STATE_TARGET_MISSING
REMOVAL_TARGET_MISSING
TRANSFER_ANCHOR_MISSING
UNEXPECTED_MULTIFRAGMENT_PRODUCT
EDIT_REPLAY_MISMATCH
```

至少新增：

```text
test_mismatched_transform_site_rejected
test_mismatched_query_site_rejected
test_missing_bond_endpoint_is_typed_failure
test_expected_bond_absent_is_typed_failure
test_existing_add_bond_is_typed_failure
test_missing_atom_state_target_is_typed_failure
test_missing_removed_atom_is_typed_failure
test_missing_transfer_anchor_is_typed_failure
test_ring_and_aromatic_site_preconditions
```

---

## 11. R2-F：修复 strict candidate validation 与 store

### 11.1 真正的 transform fidelity

当前只检查 heavy-atom count 和 product != query，已被独立探针证明会接受错误 product。

validation 必须独立验证：

```text
report transformation_id == transform transformation_id
report site_id == site site_id
query/site/run namespace一致
canonical edit replay == canonical product
全部 required edits执行一次
没有 undeclared edits
changed atoms/bonds与 replay一致
preconditions重新验证
formal source/sink accounting完整
candidate identity由实际 product重算
```

至少新增：

```text
test_wrong_product_same_heavy_atom_count_rejected
test_wrong_generation_transform_id_rejected
test_wrong_generation_site_id_rejected
test_missing_required_edit_rejected
test_extra_undeclared_edit_rejected
test_candidate_id_recomputed_from_product
```

### 11.2 Ledger authority

当前只检查 ledger ID 非空，已被证明 `FORGED_LEDGER` 可通过。

要求：

- source ledger必须等于 donor evidence authority 中的 ledger；
- 调用冻结的 reference registry validation；
- candidate ID、source ledger ID、donor reaction、lineage、transform、site、generation path 必须交叉一致；
- transfer source/sink participant必须存在；
- unknown actual co-substrates/cofactors/stoichiometry 保持 unknown，不能写成事实；
- formal balance不能用空 element balances + 固定 `charge_delta=0` 冒充验证成功；
- partial/unbalanced eligibility 要按 ADR-0004 明确处理。

至少新增：

```text
test_forged_source_ledger_rejected_by_p3_validator
test_unknown_candidate_id_rejected
test_ledger_reaction_lineage_mismatch_rejected
test_transfer_source_participant_must_exist
test_removed_atom_sink_participant_must_exist
test_formal_balance_is_derived_not_hardcoded
```

### 11.3 Strict lane predicate

必须同时要求：

```text
valid_molecule
transform_fidelity
precondition_recheck
formal_source_accounting
candidate_ledger_valid
not critical_contradiction
not relaxation_used
not critical_ambiguity
failure_code is None
```

新增：

```text
test_critical_contradiction_rejected_from_strict_lane
test_failure_code_rejected_even_if_flags_true
```

### 11.4 Candidate merge 不得丢失证据

当前相同 product 合并后只保留第一条 CandidateAnalogyLedger。

要求按 generation path 保留：

```text
donor
reaction
lineage
transform
site
generation report
source ledger
candidate analogy ledger
validation
provenance
```

可以设计 `candidate_evidence_paths[]` 或等价严格 schema，但不能让 `source_ledger_ids` 有多条、ledger 却只有第一条。

至少新增：

```text
test_candidate_merge_preserves_per_path_ledgers
test_candidate_merge_preserves_per_path_validation
test_candidate_merge_order_invariant
test_isotope_identity_not_incorrectly_deduped
```

---

## 12. R2-G：修复 P3→P4 frozen interface

原提示要求每个输出携带统一运行命名空间：

```text
case_id
query_id
fold_id
snapshot_id
snapshot_hash
run_id
evidence_kind
```

当前缺失：

```text
NormalizedQuery:
  case_id, fold_id, run_id, snapshot_id, snapshot_hash

ResolvedDonorEvidence:
  run_id

StrictTransformation:
  case_id, query_id, fold_id, run_id, snapshot_id, snapshot_hash

ConditionedSite:
  fold_id, run_id, snapshot_id, snapshot_hash

StrictCandidate:
  case_id, query_id, fold_id, run_id, snapshot_id, snapshot_hash
```

要求：

- 修复 schema；
- 所有跨对象 namespace 必须一致；
- P4 不需要读取 P3 内部 mutable objects；
- interface manifest 必须从实际 Pydantic model fields/JSON schemas 生成，不能手工复制字段列表；
- manifest 必须包含 model/schema hash、ID preimage、evidence semantics、blocker semantics；
- manifest/schema drift 必须使 contract test FAIL；
- 当前 manifest 在 ChatGPT 重新批准前不得标 frozen/accepted。

至少新增：

```text
test_every_p3_output_has_full_run_namespace
test_cross_object_run_namespace_consistency
test_interface_manifest_matches_model_fields
test_interface_schema_hash_recomputable
test_p4_can_deserialize_without_p3_mutable_objects
```

---

## 13. R2-H：修复 capability 语义

当前 preflight 把 `RealMapperAdapter(backend='rdkit')` 报成：

```text
atom_mapper = available
```

但提交同时承认 RDKit 不是 atom mapper。

必须拆分至少：

```text
chemistry_backend_available
explicit_map_validator_available
strict_atom_mapper_available
mcs_diagnostic_available
real_snapshot_available
automatic_donor_available
```

当前环境可诚实报告：

```text
chemistry_backend_available       = true
explicit_map_validator_available  = true
mcs_diagnostic_available          = true
strict_atom_mapper_available      = false  # 若 rxnmapper 等未接入
real_snapshot_available           = false
automatic_donor_available         = false
```

MCS 永远不能让 strict mapping capability 变为 available。

至少新增：

```text
test_rdkit_is_not_reported_as_strict_atom_mapper
test_explicit_map_validator_capability_separate
test_mcs_diagnostic_never_satisfies_strict_mapping_gate
```

---

## 14. R2-I：重写 Gate 与 mutation 证据链

### 14.1 Gate 不得信任状态字典

删除或重写当前浅层 `evaluate_gate_from_artifacts()`。

以下输入必须拒绝，且不需要攻击者主动设置 `no_artifacts=True`：

```python
{
  "status": "PASS",
  "items": {"G01": "PASS", ..., "G10": "PASS"}
}
```

Gate 必须独立读取和验证：

- typed artifacts；
- schema version/hash；
- snapshot/run/fold namespace；
- candidate trace；
- transform replay；
- dual-ledger references；
- evidence kind；
- capability probes；
- mutation results；
- test command exit status。

`derived_from_artifacts` 不能是默认 `True` 常量；只能由成功验证得出。

### 14.2 Real Gate items 必须运行真实路径

当真实能力未来可用时：

- G01 不能只看两个 capability bool；必须运行 X-only automatic pipeline；
- G03 不能只看 snapshot bool；必须验证 donor/reaction/lineage/transform/site/dual-ledger 完整；
- G07 必须读取和验证 P2 pilot authority artifact，而不是永久硬编码字符串。

当前能力缺失时这些项保持 typed `BLOCKED`。

### 14.3 Mutation 必须是基线 `PASS→FAIL`

每个 mutation 结果至少包含：

```text
mutation_id
target_gate_item
baseline_artifact_hash
baseline_status=PASS
mutated_artifact_hash
mutated_status=FAIL
expected_failure_code
observed_failure_code
caught=true/false
```

若 baseline 不能 PASS，该 mutation 状态必须是 `INVALID_BASELINE`，不能计入 caught。

若 mutation 引发错误但不是预期 failure code，必须是 `ERROR`，不能计入 caught。

implementation mutation 逃逸必须让 P3 Gate 为 `FAIL`，即使 real-evidence items 同时 `BLOCKED`。

至少新增：

```text
test_artifactless_pass_dictionary_rejected
test_gate_recomputes_artifact_hashes
test_gate_rejects_schema_invalid_artifact
test_gate_rejects_namespace_mismatch
test_gate_rejects_fixture_as_real_evidence
test_mutation_requires_pass_baseline
test_mutation_requires_target_pass_to_fail
test_mutation_requires_expected_failure_code
test_mutation_escape_causes_gate_fail_even_when_real_items_blocked
```

---

## 15. R2-J：修复报告生成器

当前报告生成器用：

```python
906 + _p3_test_count()
```

合成 full-regression 数量，必须删除。

报告生成器必须真实运行并记录：

```text
command
cwd
python executable
started_at/finished_at
exit_code
collected
passed
failed
errors
skipped
xfail/xpass
stdout/stderr artifact hash
```

如果命令未运行、解析失败、exit code 非预期或测试未收集，报告生成必须 fail closed，不能继续写成功提交。

changed-files 必须基于 starting/ending Git state，不得只 walk 预设目录。

提交中必须写明：

- worktree 内没有 `.venv`；
- 实际使用的 Python 绝对路径；
- starting dirty state；
- 本轮 delta；
- inherited unrelated changes；
- 未经验证的内容。

至少新增：

```text
test_report_full_suite_count_comes_from_actual_command
test_report_generator_fails_when_full_suite_fails
test_report_generator_fails_when_no_tests_collected
test_changed_files_derived_from_git_state
test_submission_does_not_claim_nonexistent_local_venv
```

---

## 16. 必须保留的现有正确行为

修复时不得破坏：

- octanol regression：`CCCCCCCCO → CCCCCCCC=O`；
- equivalent atom ordering invariant；
- system failure 与 scientific abstention 分离；
- P3 不输出 rank/probability/final abstention；
- LLM 不创建/修改结构；
- formal mapping 不声称 mechanism；
- donor context 在 CandidateAnalogyLedger 中明确为 inherited assumption；
- synthetic fixtures 不满足 real-evidence Gate；
- P0/P1 Gate 与全量回归继续通过。

---

## 17. 验证命令

使用：

```bash
P3_PY=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

至少运行：

```bash
$P3_PY -m pytest tests/p3 -q -p no:cacheprovider
$P3_PY -m pytest tests -q -p no:cacheprovider
$P3_PY scripts/run_p0_gate.py
$P3_PY scripts/run_p1_gate.py
$P3_PY scripts/run_p3_preflight.py
$P3_PY scripts/run_p3_gate.py
```

注意：

- P0/P1 Gate/report runner 可能写 reports；只允许在当前授权 P3 worktree 或临时可写副本中运行；
- 不得写主共享 authority worktree；
- P3 Gate 当前预期可为 `BLOCKED` exit 2，但前提是所有 implementation items PASS；
- 若任一 implementation invariant FAIL，P3 Gate 必须为 `FAIL` exit 1，不能返回 BLOCKED。

必须记录命令的真实原始结果，不得手工改数字。

---

## 18. Round 2 必交付物

写入当前 P3 worktree：

```text
reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_2.md
reports/p3/P3_ROUND_2_AUDIT_EVIDENCE.json
reports/p3/P3_ROUND_2_REMEDIATION_WORKLOG.md
reports/p3/P3_GATE_REPORT_ROUND_2.json
reports/p3/P3_GATE_REPORT_ROUND_2.md
reports/p3/P3_MUTATION_RESULTS_ROUND_2.json
reports/p3/p3_p4_interface_manifest_round_2.json
reports/p3/P3_ROUND_2_STARTING_WORKTREE_STATE.md
reports/p3/P3_ROUND_2_CHANGED_FILES.json
```

### 18.1 Submission 必须逐项回答

1. starting/ending Git state；
2. inherited dirty files；
3. 本轮实际 changed files；
4. 每个 ChatGPT finding 的修复位置；
5. 每个 finding 对应 RED→GREEN 测试；
6. exact commands 与原始 exit code；
7. P0/P1/P3 测试与 Gate；
8. real vs fixture evidence；
9. capability inventory；
10. mutation baseline/target/outcome；
11. P3→P4 interface schema/hash；
12. remaining blockers；
13. no network/install/LLM/MCP/Orchestra/commit/push/merge declaration；
14. 未解决问题与诚实状态。

### 18.2 最后一行

只有当所有 implementation invariants 已通过、而真实能力仍缺失时，最后一行才能是：

```text
P3_IMPLEMENTATION_COMPLETE_GATE_BLOCKED_PENDING_CHATGPT_ROUND_2_AUDIT
```

如果仍有任何实现失败，必须写：

```text
P3_GATE_FAIL_NEEDS_REMEDIATION
```

不得写正式 P3 Gate PASS，不得宣称 production ready，不得进入 P4 正式集成。

---

## 19. 提交给用户时只返回

完成后，不要长篇自我评价，只返回：

```text
P3 Round 2 remediation completed.

Submission:
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_2.md

Structured evidence:
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_2_AUDIT_EVIDENCE.json

Worklog:
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_2_REMEDIATION_WORKLOG.md

Final status:
<精确复制 submission 最后一行>
```

等待 ChatGPT 只读审核；不得自行批准 P3，也不得开始 P4 正式集成。
