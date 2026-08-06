# ChatGPT → P3 实施提示词：Strict One-Step Kernel

> 用途：把本文件完整交给一个没有历史聊天记忆的 coding-agent 窗口。
> 目标：实现 P3 strict one-step kernel 的可验证代码、契约测试、fixtures、Gate skeleton 和审计提交材料。
> 当前状态：P0/P1 已被接受；P2 formal Gate 仍 BLOCKED，且 P2 implementation 需要后续整改。
> 重要：P3 可以并行开发不依赖真实证据的部分，但不得把 P2 BLOCKED 或 synthetic fixture 写成 P3 PASS。

## 0. 你的身份与最终交付

你是 P3 worker，不是项目总集成者。你只负责 strict one-step kernel，不能顺手实现 P4 ranking/abstention 或 P5 benchmark。

最终必须交付：

1. P3 implementation code；
2. P3 strict schemas/interfaces；
3. RED→GREEN contract tests 和 anti-false-positive mutation tests；
4. synthetic/curated fixtures（明确标记为 synthetic_fixture，不得冒充 real evidence）；
5. P3 preflight、Gate skeleton、blocked/failed/pass evidence；
6. reports/p3/SUBMISSION_TO_CHATGPT_P3.md；
7. reports/p3/P3_GATE_REPORT.json 与 reports/p3/P3_GATE_REPORT.md；
8. reports/p3/p3_p4_interface_manifest.json，供 P4 只读消费；
9. changed-files、测试命令、assumptions、blocked items、未解决冲突的完整说明。

“代码和 fixture 测试通过”“真实 P3 Gate PASS”“可用于生产”是三个不同结论，必须分别报告。

## 1. 工作范围与 Git/外部边界

项目根目录：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
~~~

开始前只读核验：

~~~
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git log -1 --oneline
git status --short
git diff --stat
~~~

规则：

- 使用独立 worktree/branch；如果当前窗口没有独立 worktree，先报告，不要直接覆盖其他 worker 的修改。
- 不执行 git reset、git checkout --、git clean、删除、stash、merge、push、commit。
- 不修改 final_design.md、final_plan.md、final_discussion.md、六份 ADR、P0/P1 evidence。
- 不写入 legacy raw source、原始数据、credentials 或 provider 配置。
- 不联网、不安装/升级依赖、不调用真实 LLM、MCP、Orchestra 或外部模型。
- 只能使用现有依赖；缺少 RDKit/mapper/真实 snapshot 时实现 capability detection 和 typed blocker，不得伪造化学结果。
- 不扩大到 P4/P5；如发现需要修改共享接口，只写 proposal/manifest，不直接改共享 authority 文件。

## 2. 必须完整阅读的权威文件

先完整阅读（不能只看摘要）：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_discussion.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0001-authority-and-scope.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0002-hypothesis-lanes.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0003-ledger-and-source-semantics.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0004-partial-eligibility.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0005-scientific-decision-authority.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0006-mcp-side-effects.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_FINAL_PASS.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/chatgpt_p1_train.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/README.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/pyproject.toml
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/requirements.lock.txt
~~~

如果存在，也必须只读阅读：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/P2A_COMPACT_CONTEXT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p2/SUBMISSION_TO_CHATGPT_P2.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p2/P2_GATE_REPORT.json
~~~

P2 审核口径：P2 Gate BLOCKED；P2 中的 truth/isolation/Gate/mutation 当前不能作为已经可信的 scientific authority。P3 必须以 P1 authority 为数据源，不能复制 P2 Gate 的布尔值/浅字典判定。

## 3. P1 authority 与 P3 输入边界

P3 唯一允许消费的 data authority 是 P1 冻结的：

- snapshot ID/hash 与 manifest；
- complete reaction evidence；
- participant role hypotheses；
- formal mapping status；
- fragment-lineage graph；
- source reaction ledger；
- candidate ledger skeleton；
- eligibility/quarantine/provenance。

不得：

- 只读取 A/B 两个 SMILES 拼一个 reaction；
- 删除 COFACTORS、co-substrates 或 small molecules；
- 用 COFACTORS 作为 destructive exclusion；
- 把 formal mapping 说成 mechanism/atom origin；
- 把 mirror row、同一 publication 或同一 lineage 当独立 donor evidence；
- 生成不存在的 reaction/atom/map/ID；
- 用字符串相似或 LLM 自由文本代替 audited identity/graph edit。

## 4. P3 目标流水线

必须实现并保持以下边界：

~~~
X only
→ normalize
→ adaptive distinct donor retrieval
→ complete reaction load
→ formal mapped lineage
→ strict transform extraction
→ conditioned site enumeration
→ deterministic graph-edit generation
→ molecule/ledger/transform validation
→ canonical strict candidates
→ unranked candidate + trace
~~~

P3 不做最终 ranking、applicability decision、typed abstention policy 的最终裁决；P4 消费 P3 的 candidate/trace。

## 5. 必须实现的 P3 工作包

### P3-T1 Query normalization

实现 versioned normalization contract：

- parse/sanitize capability；
- canonical/exact identity；
- charge、salt/mixture、tautomer、isotope、stereo policy；
- identity hash；
- invalid input 与 backend unavailable 的 typed errors。

必须测试：等价 SMILES、atom permutation、invalid、salts、多 fragment、explicit/implicit H、charge、stereo。缺少 chemistry backend 时只能返回 blocker，不能修复或创造 SMILES。

### P3-T2 Adaptive distinct-donor retrieval

实现：

- 输入仅为 X 与指定 fold 的 train-only P1 view；
- donor A 必须是 eligible transformed participant；
- Morgan/size/charge 等 baseline feature 仅表示 structural retrieval，不表示 activity/probability；
- source/lineage quality、identity diversity、transform diversity；
- duplicate reaction rows/source mirrors 不得挤占 donor slots；
- deterministic tie-break、seed/config/version manifest、stop reason；
- quarantine/excluded records fail closed；
- 不得访问 test query、test reaction、test truth、test product。

### P3-T3 Complete reaction loader

每个 donor 必须返回完整、可审计的：

- donor participant；
- all participants/co-substrates/cofactors/coproducts；
- source reaction identity/provenance；
- formal mapping report；
- resolved fragment lineage；
- source reaction ledger；
- transform/site context；
- eligibility/quarantine decision。

loader 必须拒绝只含 A/B 的不完整 record、partial map、critical ambiguity、source/lineage 不一致。

### P3-T4 Strict transformation extraction

输出 canonical, content-addressed transform：

- mapped atom edits；
- bond delete/add/order；
- atom attributes；
- transferred atoms；
- donor site/local environment；
- strict preconditions；
- source/sink ledger requirements；
- canonical transform hash/version。

必须支持 replay、atom-order invariance、canonicalization、duplicate support dedup、partial-map rejection、source trace。

### P3-T5 Conditioned sites

实现：

- transform precondition matching；
- stable site IDs；
- symmetry dedup；
- ambiguity groups；
- local environment；
- failed preconditions 的结构化原因。

必须覆盖 multiple/symmetric/no site、wrong functional group、aromatic/aliphatic、charge、atom-order。

### P3-T6 Deterministic graph-edit generation

实现 versioned compiler：

- transform + site → graph edit；
- deterministic edit application；
- sanitize/canonicalize；
- invalid valence/aromaticity/multi-fragment handling；
- duplicate product merging；
- GenerationReport 与 typed failures；
- 不依赖 LLM 生成任何结构。

必须包含回归：

~~~
CCCCCCCCO → CCCCCCCC=O
~~~

并覆盖 bond changes、atom properties、transferred atom、invalid valence、aromaticity、duplicate products、多路径。

### P3-T7 Candidate validation

候选只有在以下全部满足时才进入 strict lane：

- valid molecule；
- transform fidelity；
- precondition recheck；
- formal heavy-atom source accounting；
- CandidateAnalogyLedger 合法；
- mapping/lineage/source ledger 无 critical contradiction；
- no relaxation；
- no critical ambiguity。

拒绝结果必须是 typed failure，不能悄悄降级为“低质量候选”。

### P3-T8 Canonical candidate store

至少记录：

~~~
candidate_id
canonical_product_identity
lane=strict
origin
generation_paths[]
support_lineage_ids[]
transformation_ids[]
site_ids[]
validation
source_ledger_ids[]
candidate_analogy_ledger
provenance
~~~

相同结构必须合并，但 generation paths、support lineage、transform/site/source ledger 证据不得丢失。candidate ID 必须由系统生成并可重算，不能由输入字符串随意推导。

### P3-T9 Deterministic predictor lifecycle

至少支持并记录：

~~~
RECEIVED
NORMALIZED
BASELINE_EVIDENCE_LOADED
HYPOTHESES_COMPILED
SITES_ENUMERATED
CANDIDATES_VALIDATED
~~~

输出只能是 unranked validated strict candidates + complete trace。P3 不输出 rank、probability 或 final abstention decision。

## 6. P3→P4 冻结接口提案

在 reports/p3/p3_p4_interface_manifest.json 中冻结字段、版本、hash 算法和 blocker semantics，至少包含：

- KernelRunManifest：run/request/snapshot/fold/config/component versions；
- NormalizedQuery；
- ResolvedDonorEvidence；
- StrictTransformation；
- ConditionedSite；
- StrictCandidate；
- CandidateTrace；
- KernelFailure；
- CapabilityStatus。

每个输出必须带 case_id/query_id/fold_id/snapshot_id/snapshot_hash/run_id，并声明 real、synthetic_fixture、blocked 或 diagnostic。P4 不得需要读取 P3 内部可变对象。

如果现有 P2 schemas 与上述语义冲突，写 reports/p3/P2_INTERFACE_CONFLICT.md，在 adapter 中 fail closed，不修改 P2 authority。

## 7. P3 测试与 Gate

先写 RED tests，再实现。至少需要：

- schema strictness/unknown field/type coercion；
- query invariance；
- donor dedup/eligibility/quarantine/fold isolation/deterministic ties；
- complete reaction requirement；
- map/lineage/ledger consistency；
- transform replay and atom-order invariance；
- site preconditions/symmetry/ambiguity；
- graph-edit deterministic generation；
- invalid molecule/valence/ledger contradictions；
- candidate canonical dedup/evidence preservation；
- lifecycle/trace completeness；
- system failure ≠ scientific abstention；
- no LLM structure creation；
- no invented IDs/SMILES。

必须有 anti-false-positive mutations，至少覆盖：只给 A/B、删除 participants、改 mapping、漏 lineage、跳过 preconditions、伪造 ledger、污染 test view、启用 relaxed edit、把 system failure 改成 abstention、状态字符串伪造 PASS。

Gate skeleton 必须明确 PASS、FAIL、BLOCKED，并满足：

- fixture 只能验证 machinery，不能满足 real evidence Gate；
- chemistry backend、real snapshot、automatic donor 或 complete P1 evidence 缺失时准确 BLOCKED；
- implementation invariant 失败时 FAIL，不能被 evidence BLOCKED 掩盖；
- Gate 从 artifact/schema/hash 推导，不信任 stored status string；
- mutation escaped/error 阻止 PASS；
- runner 对 PASS/BLOCKED/FAIL 使用不同退出码。

P3 Gate 条件对齐 final_plan §6.11：X-only automatic path、strict candidate replayable、donor/reaction/lineage/transform/site/dual-ledger complete、equivalent-SMILES invariant、no LLM structure creation、system failure/abstention separate、pilot funnel interface、octanol carbon regression、formal mapping ≠ mechanism、donor context assumptions labeled。

没有真实能力时，正式 P3 Gate 必须保持 BLOCKED；不得生成 performance、recall、accuracy 或 production PASS。

## 8. 报告与提交

只在独立 worktree 中写 reports/p3/。至少包含：

~~~
P3_PREFLIGHT.md/json
P3_GATE_REPORT.md/json
P3_MUTATION_RESULTS.json
p3_p4_interface_manifest.json
fixture_vs_real_evidence_manifest.json
dependency_matrix.md
integration_worklog.md
SUBMISSION_TO_CHATGPT_P3.md
~~~

SUBMISSION_TO_CHATGPT_P3.md 必须逐项回答：

- starting/ending Git state；
- changed files；
- tests and exact commands；
- P0/P1/P2 dependency status；
- real vs fixture evidence；
- capability inventory；
- Gate item status；
- mutation result validity；
- assumptions；
- blocked items；
- no network/install/provider/commit/push declaration；
- 最后一行精确为 READY_FOR_CHATGPT_P3_READ_ONLY_AUDIT 或 P3_IMPLEMENTATION_COMPLETE_GATE_BLOCKED / P3_GATE_FAIL_NEEDS_REMEDIATION。

不要把 synthetic fixture、schema skeleton、unit tests 数量、P2 BLOCKED 或 status string 写成 P3 PASS。
