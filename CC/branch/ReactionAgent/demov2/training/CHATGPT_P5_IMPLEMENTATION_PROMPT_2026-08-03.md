# ChatGPT -> P5 实施提示词：Full Snapshot、Rebuilt Benchmark、Six-Layer Reporting

用途：把本文件完整交给一个没有历史聊天记忆的 coding-agent 窗口。
目标：实现 P5 full snapshot、rebuilt benchmark、fair baselines、six-layer reports 和 P5 Gate skeleton。
当前状态：P0/P1 已接受；P2 formal Gate BLOCKED；P3/P4 可能只有 contract machinery。P5 可以并行开发 protocol、schemas、pure functions、fixtures 和 Gate skeleton，但不得生成虚假真实 performance 或 PASS。

## 0. 身份与交付

你是 P5 worker，不是总集成者。只负责 full snapshot、rebuilt examples、leakage-safe splits、fair legacy baselines、six-layer reporting 和 P5 Gate。不要实现 P6 MCP、P7 production Agent、P3 chemistry kernel 或 P4 ranking。

必须交付：

1. P5 schemas、artifact readers、snapshot/index/reporting code；
2. RED to GREEN tests、synthetic/protocol fixtures、anti-false-positive mutations；
3. P1/P2/P3/P4 artifact adapters 与 cross-stage validation；
4. full snapshot、split、benchmark、report manifests；
5. reports/p5/SUBMISSION_TO_CHATGPT_P5.md；
6. reports/p5/P5_GATE_REPORT.md/json；
7. reports/p5/P5_MUTATION_RESULTS.json；
8. reports/p5/p5_p6_interface_manifest.json；
9. exact commands、changed files、assumptions、blocked items、real-vs-fixture evidence。

代码完成、fixture 通过、真实 full snapshot benchmark 存在、P5 Gate PASS 必须分别报告。

## 1. 安全边界

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

- 使用独立 worktree/branch；
- 不 reset、checkout、clean、删除、stash、merge、push、commit；
- 不修改 final_design、final_plan、final_discussion、ADR、P0/P1 evidence；
- 不修改 P2/P3/P4 worker 代码或 Gate；
- legacy source/raw datasets 只读；
- 不联网、安装依赖、调用真实 LLM/MCP/Orchestra/provider；
- 不伪造 real audit、ground truth、lineage、performance 或 KPI；
- fixtures 必须标记 synthetic_fixture 或 protocol_only；
- source/time split provenance 不达标时输出 unavailable/blocked，不编造 source/timestamp；
- 不复制旧 legacy accuracy/KPI 作为正式 threshold；
- P5 不建立另一份 snapshot/mapping/lineage/eligibility authority。

## 2. 必须完整阅读

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
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/CHATGPT_P4_IMPLEMENTATION_PROMPT_2026-08-03.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/README.md
~~~

如果存在，也阅读 P2/P3/P4 submission 和 interface manifests。P2 当前是 implementation incomplete + formal Gate BLOCKED；P3/P4 缺真实 authority 时，P5 只能输出 machinery complete + Gate BLOCKED。

## 3. Authority 与 cross-stage validation

P5 只允许消费：

- P1 snapshot/hash、complete reaction evidence、mapping、lineage、ledgers、eligibility/quarantine；
- 严格验证过的 P2 truth/fold/views；
- P3 frozen strict candidate/trace；
- P4 frozen evidence/ranking/applicability/abstention artifacts。

加载任何 artifact 前必须验证 schema、strict fields、content hash、snapshot/fold/run/policy binding、case/query joins、fixture-vs-real classification 和 leakage boundary。不得相信 stored status string。

不得修改 P1 source、mapping、lineage、roles、eligibility；不得从 raw A/B 自己制造 truth；不得把 incomplete/unaudited truth 当 ground truth；不得把 database absence、低频、未收录或未找到第二 enzyme 当 negative；不得把 oracle 结果放进 primary；不得复制旧 41.5%、23.5%、79.5%、A1/A2 等指标。

## 4. P5 工作包

### P5-T1 Full snapshot and production index

只读 P1 snapshot，生成版本化 manifest/index：

- production、diagnostic、quarantine index；
- source counts；
- pre/post normalization；
- included/quarantine/excluded；
- duplicate/unresolved counts；
- mapping/lineage/ledger quality distributions；
- provenance、snapshot hash；
- 每个 filter 的 denominator 和 reason。

不允许静默删除；每个 filter 必须能回溯到 eligibility/quarantine reason。production、diagnostic、quarantine namespace 必须隔离。

### P5-T2 Rebuilt examples

从已验证的 P1 lineage、P2 truth audit、P3/P4 artifacts 构造：

- X/query；
- allowed Y set，不压缩 multi-answer；
- source/reaction context；
- donor availability；
- transform/site truth；
- ambiguity/incomplete truth；
- provenance；
- fold eligibility；
- case/run/snapshot/policy hashes；
- real/synthetic/blocked classification。

没有 audited annotation 时保留 case 并标记 incomplete/blocked，不能删除以改善 benchmark。

### P5-T3 Split families

实现并显式报告：

~~~
exact-X
scaffold
transformation-family
source
time
OOD challenge
~~~

每个 split 必须包含 frozen snapshot/fold/split ID/hash、train/validation/test query/reaction/evidence/source/truth identity sets、overlap findings、train/validation/test capability views、cache identities、audit_complete 和 unavailable/blocker semantics。

source/time provenance 不足则 unavailable，不伪造。retrieval、support、counterevidence、ranking、calibration reference 不得访问 test。

### P5-T4 Fair baselines

在同一 snapshot、同一 split、同一 case registry、同一 train-only view 上定义：

- Morgan；
- legacy template；
- DRFP/reaction-space reference similarity；
- random/order；
- nearest donor；
- P3/final deterministic strict kernel。

每次 run 记录 baseline ID/version、config/seed、train-only resource、case registry、output hash、availability/blocker、oracle flag、primary/diagnostic namespace。oracle upper bound 只能 diagnostic；unavailable 不能用假输出替代。

### P5-T5 Six-layer reports

每个 split/baseline/run 输出：

1. data；
2. retrieval；
3. transform/site；
4. generation；
5. rank/abstention；
6. cost/runtime。

每层记录 numerator、denominator、N、CI 或 unavailable reason、coverage、failure/abstention reasons、system failures、incomplete truth not scored、evidence scope、artifact hashes、run/snapshot/fold binding。structured JSON 是 authority，Markdown 只能由 JSON 渲染。

### P5-T6 Formal KPI and Go/No-Go

真实冻结数据产生结果后才注册 donor recall、candidate recall、valid rate、top-K、risk at coverage、selective accuracy、abstention quality、catastrophic error、unexplained failure、runtime/cost 等 KPI。不得预宣称 accuracy threshold；Go/No-Go 必须基于 data integrity、retrieval availability、failure funnel、deterministic slice viability、research/service value。

## 5. P5 interface

写 reports/p5/p5_p6_interface_manifest.json，冻结：

- FullSnapshotManifest；
- ProductionIndexManifest；
- RebuiltCaseRecord；
- SplitFamilyManifest；
- BaselineRunArtifact；
- LayerMetricReport；
- MetricUnavailableReason；
- FormalKPIRegistry；
- GoNoGoDecision；
- P5RunManifest；
- artifact/hash/version contract。

每个 artifact 必须分类为 real、synthetic_fixture、derived_diagnostic、protocol_only 或 blocked，分类必须与内容一致。

## 6. Tests, mutations, Gate

先写 RED tests。至少覆盖：

- snapshot authority/hash/reproducibility；
- filter accounting/no silent drop；
- production/diagnostic/quarantine separation；
- rebuilt multi-answer truth；
- incomplete/unaudited retention；
- all split families and overlap domains；
- source/time unavailable fail closed；
- train-only isolation；
- same-data/same-split baseline fairness；
- oracle exclusion from primary；
- six-layer numerator/denominator/N/CI/reason；
- JSON authority over Markdown；
- no old KPI injection；
- report hash/freeze/replay；
- upstream P2/P3/P4 schema/hash validation；
- real-vs-fixture boundary；
- status string cannot promote PASS。

Mutations 至少覆盖：drop filtered rows、relabel quarantine production、change snapshot hash、leak test IDs、split overlap、fabricate source/time、drop incomplete truth、collapse multi-answer、copy oracle into primary、use different baseline splits、omit N/CI、fake unavailable as zero、JSON/Markdown contradiction、change KPI threshold、stale run ID、upstream BLOCKED while claiming PASS。

Mutation 必须从 PASS-capable fixture 开始，逐项验证目标 PASS→FAIL；BLOCKED baseline 下的整体 BLOCKED 不能算 caught。no-op/error/escaped 都必须阻止 Gate PASS。

P5 Gate 至少包含：

1. leakage zero 且全部要求的 domain 已审计；
2. all filters 与 denominator 完整；
3. multi-answer active 且 policy-bound；
4. strict metrics complete 或显式 unavailable blocker；
5. baselines fair 且 oracle separated；
6. formal KPI registry 只在数据允许时记录；
7. Go/No-Go 可追溯。

上游 P2/P3/P4 或 real snapshot 缺失时 BLOCKED；实现 invariant/hash/artifact integrity 失败时 FAIL；Gate 必须从当前 structured evidence 推导。

## 7. 报告与提交

只写 reports/p5/，至少包含：

~~~
P5_PREFLIGHT.md/json
P5_GATE_REPORT.md/json
P5_MUTATION_RESULTS.json
full_snapshot_manifest.json
production_index_manifest.json
rebuilt_case_manifest.json
split_family_manifest.json
baseline_run_manifest.json
six_layer_report.json
fixture_vs_real_evidence_manifest.json
p5_p6_interface_manifest.json
dependency_matrix.md
integration_worklog.md
SUBMISSION_TO_CHATGPT_P5.md
~~~

封面必须回答 Git state、changed files、exact commands/results、P1/P2/P3/P4 status、hashes、real-vs-fixture scope、split/leakage、baseline fairness、six-layer metrics、KPI/Go-No-Go、assumptions、blockers、no network/install/provider/commit/push。最后一行只能是 READY_FOR_CHATGPT_P5_READ_ONLY_AUDIT、P5_IMPLEMENTATION_COMPLETE_GATE_BLOCKED 或 P5_GATE_FAIL_NEEDS_REMEDIATION。

没有真实 full snapshot、validated upstream artifacts 和 leakage-audited split 时，不得宣称 P5 Gate PASS。
