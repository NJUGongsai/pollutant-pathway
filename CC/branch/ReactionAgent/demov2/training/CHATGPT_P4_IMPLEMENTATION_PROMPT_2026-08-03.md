# ChatGPT → P4 实施提示词：Evidence、Ranking、Applicability、Abstention

> 用途：把本文件完整交给一个没有历史聊天记忆的 coding-agent 窗口。
> 目标：实现 P4 的独立证据身份、support/counterevidence、strict-only baseline ranker、structural applicability、typed abstention 和 immutable run trace。
> 当前状态：P0/P1 已被接受；P2 formal Gate BLOCKED；P3 可能尚未具备真实 chemistry capability。P4 可以并行写纯函数、schemas、fixtures、contract tests 和 Gate skeleton，但不得虚构 P3/P4/P5 真实完成。

## 0. 你的身份与最终交付

你是 P4 worker，不是总集成者。你的范围只包括 P4 evidence/ranking/applicability/abstention，不实现 P3 graph-edit chemistry，不实现 P5 full snapshot/benchmark，不实现 MCP。

最终交付：

1. P4 code 与严格 schemas；
2. RED→GREEN tests、curated/synthetic fixtures 和 anti-false-positive mutations；
3. P3→P4 consumer adapter（只读消费 P3 interface manifest，不能读取 P3 内部对象）；
4. P4→P5 interface manifest；
5. P4 preflight、Gate skeleton、evidence report；
6. reports/p4/SUBMISSION_TO_CHATGPT_P4.md；
7. reports/p4/P4_GATE_REPORT.md/json；
8. reports/p4/P4_MUTATION_RESULTS.json；
9. changed-files、exact test commands、assumptions、blocked items、interface conflicts。

实现完成、fixture contract 通过、真实 strict candidate run、P4 Gate PASS 必须分别报告。

## 1. 工作目录与安全边界

项目根目录：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
~~~

开始前只读执行：

~~~
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git log -1 --oneline
git status --short
git diff --stat
~~~

必须：

- 使用独立 worktree/branch；
- 不 reset、checkout、clean、删除、stash、merge、push、commit；
- 不修改 P0/P1/final design/plan/discussion/ADR；
- 不改 P3 worker 的代码、P2 Gate、P1 evidence 或 legacy source；
- 不联网、不安装依赖、不调用真实 LLM/MCP/Orchestra/provider；
- 不把用户提示、数据库 absence、低频或“没有第二个 enzyme”当 counterevidence；
- 不引入 confidence、probability、activity probability 或类似字段；
- 不让 agent/model text 覆盖结构化 rank、lane、validation 或 abstention decision。

如果共享文件必须变化，只写 reports/p4/interface proposal，不直接修改共享 exports；最终由 integrator 单点合并。

## 2. 必须完整阅读的文件

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
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/CHATGPT_P3_IMPLEMENTATION_PROMPT_2026-08-03.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/README.md
~~~

如果存在，也阅读：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p2/SUBMISSION_TO_CHATGPT_P2.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p3/SUBMISSION_TO_CHATGPT_P3.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p3/p3_p4_interface_manifest.json
~~~

P2 当前审核口径：formal Gate BLOCKED；P2 truth matcher、leakage/Gate/mutation 不能被无条件信任。若 P3 interface 不存在或只提供 synthetic fixtures，P4 必须输出 typed BLOCKED/diagnostic，不得产生真实 performance。

## 3. P4 输入与 authority

P4 只能接收：

- P1 snapshot/fold/view/provenance authority；
- P3 frozen, content-addressed strict candidate/trace interface；
- P2 truth 只可通过严格 schema/identity/policy validation adapter 使用；
- P4 自己的 versioned policy/config。

P4 不得：

- 创建或修改 SMILES、graph edit、atom map、candidate identity；
- 读取 test labels 进入 runtime；
- 使用 P3 内部可变对象；
- 把同一 source lineage/publication/mirror/normalized reaction/mapper duplicate 计作独立 evidence；
- 把 absence、低频、未收录、未找到第二酶当 negative；
- 用 raw score 表述 probability 或 confidence；
- 横向混排 strict 与未来 generalized/agent_proposed lane；
- 让 LLM 或自由文本覆盖结构化 scientific decision。

## 4. P4 主流水线

~~~
P3 frozen candidate/trace
→ independent evidence identity resolution
→ support aggregation with evidence IDs
→ allowed counterevidence
→ strict-only versioned feature vector
→ deterministic tie-broken ranking
→ structural applicability
→ typed abstention precedence
→ immutable run/trace/manifest
→ ranked strict top-K OR typed abstention
~~~

P4 不生成候选结构；只处理已经由 P3 产生且通过 strict validation 的候选。

## 5. 必须实现的 P4 工作包

### P4-T1 Independent evidence identity

实现可重算、版本化的 evidence identity/dedup：

- source lineage；
- database mirror；
- same publication；
- same normalized reaction；
- mapper duplicate；
- same donor-transform evidence；
- donor reaction/source/candidate path identity。

必须保留 raw IDs、canonical identity、dedup reason、parent/child provenance 和 independent group ID。重复记录不能增加 support count；合并时不能丢失 provenance。

必须测试：同一 source 的多行、同一 publication 的 mirror、同一 mapped reaction 的 mapper duplicate、不同 source 的相同 transform、完全不同 source 的独立 support。

### P4-T2 Support aggregation

支持特征必须逐项绑定 evidence IDs：

- donor structural similarity；
- transform recurrence；
- site compatibility；
- mapping/lineage quality；
- source quality；
- source/candidate ledger completeness；
- independent support count；
- retrieval stability。

输出应是可解释的 weighted/ordinal support breakdown，不得叫 probability、confidence 或 enzyme activity likelihood。每个 feature 必须能追溯到 source evidence；空 evidence 不得自动成为支持。

### P4-T3 Counterevidence

第一版仅允许：

- competing transform；
- failed transform preconditions；
- site incompatibility；
- invalid generation；
- ledger contradiction；
- provenance/direction/role conflict；
- strict failure 或只能显著 relaxation；
- supports 全部为低质量或同源重复。

禁止：

- database absence；
- 没找到第二个 enzyme；
- 相似分子未收录；
- 来源未报告阴性；
- 低频；
- 无法访问 test fold。

counterevidence 必须有 typed reason、evidence IDs、source identity、scope 和 policy version；absence 只能是 not observed/unknown，不能转换为 negative。

### P4-T4 Strict-only baseline ranker

实现 versioned feature vector 与 deterministic ranker：

- strict lane only；
- configurable frozen weights；
- feature contributions；
- conflict penalty；
- source/evidence independence；
- retrieval stability；
- deterministic tie-break；
- ablation outputs；
- rank is ordinal/relative selection, never probability。

不同 lane 不横向混排。未来 generalized/agent_proposed 只留 interface，不在 P4 Gate 混入 strict production ranking。

### P4-T5 Structural applicability

只表示 structural analogy applicability，不表示 enzyme activity：

~~~
in_domain
near_domain
out_of_domain
conflicted
unknown
~~~

每个 label 必须有 structural evidence/reason codes。没有 enzyme sequence、assay context 或 activity data 时，不能写 activity probability、feasibility probability 或 biological confidence。

### P4-T6 Typed abstention

严格使用 official precedence：

~~~
INVALID_INPUT
NO_IN_DOMAIN_DONOR
NO_RESOLVED_LINEAGE
NO_TRANSFERABLE_TRANSFORM
NO_COMPATIBLE_SITE
ALL_CANDIDATES_CHEMICALLY_INVALID
EVIDENCE_CONFLICT
INSUFFICIENT_SUPPORT
OUT_OF_DOMAIN
~~~

system failures 必须走 failed，不得变成 abstained。每个 abstention 必须：

- 0 candidates；
- 一个 primary reason；
- 可选 secondary reasons；
- complete trace；
- policy/config version；
- source evidence scope。

必须测试 precedence：若同时有 invalid input、no donor、conflict、insufficient support，结果按照冻结顺序只选择最早 primary reason。

### P4-T7 PredictionResult invariants

若复用 P1 PredictionResult，必须用 adapter 验证，不得创建同义 schema。强制：

- completed/predicted → 至少一个 validated strict candidate；
- abstained → 0 candidate + reason；
- partial → partial_reason；
- failed → infrastructure/system error；
- system failure 不能包装成 scientific abstention；
- rank/lane/validation/applicability/decision 只能来自 versioned policy；
- agent text 只能解释，不能覆盖结构化字段。

### P4-T8 Immutable run, trace, manifest

实现 content-addressed immutable run：

- request hash；
- snapshot ID/hash；
- fold/view ID；
- normalization/config/policy versions；
- P3 kernel/candidate/ranker versions；
- D/T/S/Δ/Y/L/R/A trace；
- evidence IDs and dedup groups；
- result hash；
- freeze state；
- replay contract；
- parent/child run binding；
- capability and blocked status。

同 request + same versions + same frozen evidence 必须产生相同 result hash。冻结后禁止静默改动；child run 必须保留 parent identity，不能覆盖 parent result。

## 6. P3→P4 与 P4→P5 接口

P4 只读消费 reports/p3/p3_p4_interface_manifest.json。若不存在，使用显式 adapter fixture 并标记 synthetic_fixture/blocked；不能读取 P3 私有 Python objects。

写入 reports/p4/p4_p5_interface_manifest.json，至少冻结：

- EvidenceIdentity；
- SupportBreakdown；
- CounterevidenceRecord；
- RankedStrictCandidate；
- ApplicabilityAssessment；
- AbstentionDecision；
- PredictionDecision；
- ImmutableRunManifest；
- P4CapabilityStatus；
- metric/trace hash and version。

所有输出必须带 case/query/fold/snapshot/run binding、evidence scope 和 real/fixture/blocked/diagnostic classification。

## 7. 测试与 anti-false-positive Gate

先写 RED tests，再实现。至少覆盖：

- schema strictness、unknown fields、strict types、forbidden probability names；
- evidence dedup 不增加 independent support；
- mirror/publication/mapper/source lineage identity；
- absence 不成为 negative；
- allowed counterevidence only；
- train-only/test-label isolation；
- strict-only lane；
- deterministic feature/rank/tie；
- applicability structural-only；
- typed abstention precedence；
- completed/abstained/partial/failed cross-field invariants；
- system failure ≠ abstention；
- immutable hash/freeze/replay/child run；
- agent text cannot override structured decision；
- no candidate structure creation；
- cross-case/fold/snapshot/policy rejection。

Mutation 至少覆盖：

- duplicate evidence rows；
- source mirror relabeled independent；
- database absence turned negative；
- test evidence inserted into support；
- oracle output inserted into primary;
- probability/confidence field injected；
- strict candidate assigned generalized lane；
- rank changed after freeze；
- conflict removed from trace；
- system failure relabeled abstained；
- abstention reason deleted；
- completed result with zero candidates；
- altered result hash;
- stored PASS status with failing artifact。

Mutation runner 不能在 BLOCKED baseline 上把“整体仍 BLOCKED”当 caught。必须有一个真实可验证的 PASS-capable contract fixture，逐 mutation 验证目标 item PASS→FAIL；no-op/error/escaped 都不能通过。

P4 Gate 至少核验：

- ranked strict top-K 或 typed abstention；
- support/counterevidence traceable；
- absence not negative；
- no probability labels；
- system failure separate；
- selective metrics computable；
- full trace persisted；
- result/manifest hashes valid；
- current-run P3 input and P2 truth policy valid；
- mutation escaped/error = 0；
- synthetic-only or missing P3/real evidence = BLOCKED，不是 PASS。

## 8. 报告和提交

只写 reports/p4/：

~~~
P4_PREFLIGHT.md/json
P4_GATE_REPORT.md/json
P4_MUTATION_RESULTS.json
p4_p5_interface_manifest.json
fixture_vs_real_evidence_manifest.json
dependency_matrix.md
integration_worklog.md
SUBMISSION_TO_CHATGPT_P4.md
~~~

提交封面必须逐项给出：

- Git/worktree starting and ending state；
- changed files and ownership；
- exact tests/commands/results；
- P1 authority binding；
- P2 truth/isolation dependency validation；
- P3 input status；
- real vs synthetic evidence；
- Gate item-by-item PASS/FAIL/BLOCKED；
- mutation baseline validity；
- all assumptions and blockers；
- no network/install/provider/commit/push；
- 最后一行只能是 READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT、P4_IMPLEMENTATION_COMPLETE_GATE_BLOCKED 或 P4_GATE_FAIL_NEEDS_REMEDIATION。

不要把 support score 写成 probability，不要生成 ungrounded candidate，不要在 P3 不可用时伪造 P4 PASS。
