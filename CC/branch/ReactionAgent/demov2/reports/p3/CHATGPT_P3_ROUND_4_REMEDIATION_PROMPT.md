# ChatGPT P3 Round 4 Remediation Instructions

## 1. 任务与当前正式状态

你正在修复 ReactionAgent 的 P3 Strict Kernel。ChatGPT 已完成 P3 Round 3 只读审计，正式结论如下：

```text
CHATGPT_P3_ROUND_3_READ_ONLY_AUDIT = FAIL
P3_MACHINERY = FAIL_NEEDS_REMEDIATION
P3_REAL_EVIDENCE = BLOCKED
P3_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P4_INTEGRATION = BLOCKED
```

本轮是 **P3 Round 4 定向修复**，不是重新设计系统，也不是开始 P4。真实 snapshot、自动 donor 或严格 learned mapper 等外部资源仍可诚实保持 `BLOCKED`，但真实资源 blocker 不得掩盖 machinery failure。

你的目标是修复下述全部 P0/P1 完整性问题，提供真实 RED→GREEN→对抗性回归证据，并重新提交给 ChatGPT 只读审核。在 ChatGPT 明确放行前，不得进入 P4。

## 2. 工作树与运行时

只在以下工作树中实施修复：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2
```

预期分支：

```text
codex/p3-strict-kernel
```

使用现有 Python：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

不要假定 P3 工作树自身存在 `.venv/bin/python`。

开始前必须运行并记录：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git diff --stat
git diff --name-status
git ls-files --others --exclude-standard
```

将起始状态写入：

```text
reports/p3/P3_ROUND_4_STARTING_WORKTREE_STATE.md
```

工作树已有继承修改和未跟踪 P3 文件。必须保留它们，不得使用：

- `git reset`
- `git checkout --`
- `git restore`
- `git clean`
- destructive deletion
- rebase/cherry-pick/merge

本轮不 commit、不 push、不 merge。

## 3. 必须完整阅读的材料

先完整阅读 Round 3 交付物：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_3.md

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_3_AUDIT_EVIDENCE.json

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_3_REMEDIATION_WORKLOG.md

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_GATE_REPORT_ROUND_3.json
```

然后完整阅读至少这些生产和测试文件：

```text
reaction_agent/p3/gate.py
reaction_agent/p3/fixtures.py
reaction_agent/p3/load.py
reaction_agent/p3/schemas.py
reaction_agent/p3/manifest.py
reaction_agent/p3/mutations_round3.py
reaction_agent/p3/mutations.py
reaction_agent/p3/generate.py
reaction_agent/p3/validate.py
reaction_agent/p3/kernel.py

tests/p3/test_r3a_gate_artifact.py
tests/p3/test_r3b_reaction_authority.py
tests/p3/test_r3e_candidate_path.py
tests/p3/test_r3f_mutation_evidence.py
tests/p3/test_r3i_manifest.py
tests/p3/test_mutations.py

scripts/run_p3_gate.py
scripts/run_p3_preflight.py
scripts/generate_p3_round3_reports.py
```

使用 `rg` 找到并阅读真正生效的 final design、final plan、P3 prompt、P0/P1 frozen contracts、P2 authority、P3→P4 interface 和 ADR。不得凭文件名猜测：

```bash
rg --files plan training reports reaction_agent tests scripts | sort
rg -n "P3|Strict Kernel|P3.*P4|Gate|evidence|mutation|reaction_hash|candidate_path|manifest_schema_hash|authority" plan training reports reaction_agent tests scripts
```

不得修改 final design、final plan、ADR、P0/P1 frozen contracts 或 P2 authority 来迎合现有 P3 代码。

## 4. 强制工程纪律

对 R4-A 至 R4-E 的每一个 finding，严格执行：

1. 先新增或修正一个通过真实生产路径复现问题的 RED test。
2. 单独运行 RED test，记录命令、exit code、观察到的错误和输出哈希。
3. 做满足冻结合同的最小生产修复。
4. 单独运行 GREEN test。
5. 新增对抗性 mutation/probe，证明旧漏洞不能再次通过。
6. 运行相关回归测试。
7. 将 RED、GREEN、对抗性结果写入结构化证据和 worklog。

禁止：

- 先改测试期望来迎合错误生产行为；
- 删除、弱化、skip 或 xfail 现有测试；
- 使用 `pytest.raises(Exception)` 替代明确异常或 typed failure code；
- 手写 Gate PASS；
- 让 artifact 提交方自由填写并决定 Gate PASS；
- 把 expected failure code 复制为 observed failure code；
- 硬编码测试数量；
- 让 fixture 冒充 real evidence；
- 仅用 schema-valid 证明 evidence-valid；
- 安装依赖、联网、调用 LLM/MCP/Orchestra；
- 修改 legacy source 或冻结文档以适配实现；
- 开始 P4；
- commit、push、merge。

## 5. R4-A（P0）：关闭 Gate artifact 完全伪造漏洞

### 已独立复现的问题

当前 `GateItemResult.evidence` 只是非空字符串列表。`evaluate_gate_artifact()` 没有证明 evidence 文件存在、内容哈希正确、属于本次执行、绑定当前 authority，且空 mutation 列表可以绕过 mutation 验证。

ChatGPT 独立构造以下 artifact 并得到：

```text
fully_fabricated_typed_gate_verdict='PASS'
fully_fabricated_typed_gate_verified=True
```

伪造 artifact 只需要：

- 当前 live interface schema hash；
- 10 个手写 `PASS` item；
- 任意非空 evidence 字符串；
- G01/G03/G07 填写校验器期待的 evidence kind；
- 空 mutations。

现有 `tests/p3/test_r3a_gate_artifact.py` 和 Round 3 mutation baseline 还把这种伪造对象当作有效正向 baseline，因此必须修正这些测试，而不是保留错误预期。

### 强制修复要求

Gate 必须验证实际执行证据，而不仅是 Pydantic 结构：

- artifact 调用方不得自由决定每个 Gate item 的 PASS；
- PASS 必须由 Gate runner 根据实际检查结果生成；
- evidence 必须是结构化、typed、版本化 reference，不得只是任意字符串；
- evidence reference 至少绑定 artifact type、path/ID、content hash、schema/version、run ID；
- 校验器必须重算 evidence content hash；
- evidence 必须绑定当前 snapshot、fold、reaction/candidate authority 与 interface manifest；
- G01–G10 必须完整、无重复、无未知项；
- mutation 集必须是必选项，空或缺失必须失败；
- mutation ID 集必须与冻结 registry 精确相等；
- 每个 mutation 必须绑定真实 baseline 和 mutated execution artifact；
- baseline 非 PASS、mutant 逃逸、ERROR、observed code 不匹配都必须使 machinery Gate FAIL；
- machinery failure 必须优先于外部资源 BLOCKED；
- synthetic fixture evidence 不得满足 real-evidence Gate item。

### 必须新增的对抗性测试

至少覆盖：

1. 任意非空 evidence strings；
2. evidence path 不存在；
3. evidence 内容被篡改但 reference hash 未更新；
4. evidence hash 被替换为另一个有效 artifact；
5. run ID/snapshot/fold namespace mismatch；
6. 手写 10 个 PASS；
7. mutations 缺失；
8. mutations 为空；
9. mutations 少一个、多一个、重复一个、未知一个；
10. mutation result 没有实际 execution artifact；
11. synthetic evidence 冒充 real evidence；
12. machinery FAIL 与 real-resource BLOCKED 同时存在时总体必须 FAIL；
13. 由真实最小执行链生成的合法 Gate artifact 能通过 machinery 验证。

## 6. R4-B（P0）：完整绑定 ReactionEvidence authority

### 已独立复现的问题

`reaction_agent/p3/fixtures.py` 中的 reaction canonical preimage 是手工字段投影，遗漏了大量 authority-relevant 字段。ChatGPT 修改以下字段后，canonical reaction hash 未变化，旧 reference 仍被 loader 接受：

```text
raw_reaction
source_name
source_version
source_uri_or_citation
provenance
quality_report
```

遗漏还包括或可能包括：

```text
fragment_lineage_graph
ambiguity_sets
transformation_hypotheses
snapshot_id
quarantine
participant.formal_charge
participant.changed_atom_fraction
participant.role_hypotheses
participant.donor_eligibility
participant.provenance
```

### 强制修复要求

建立一个唯一、版本化的 canonical reaction authority preimage。优先采用完整、稳定、规范化的模型 dump；如果必须显式投影，则要定义独立 typed preimage schema，并逐项穷举所有语义字段。

必须做到：

- reaction reference hash 从该唯一 preimage 派生；
- train-view/snapshot preimage 绑定完整 sorted reaction refs 和 reaction hashes；
- loader 对实际 reaction 重新计算 hash 并与 reference 比较；
- source、raw reaction、participants、mapping、lineage、ledger、eligibility、provenance、quality、quarantine 等审计内容不能静默排除；
- 如有字段被明确排除，必须证明其为 non-semantic，并在版本化合同中列出；
- 输入集合的等价重排不得改变 hash；
- 任意语义字段改变必须改变 hash 或触发明确 typed rejection。

### 必须新增的测试

为每一个 authority-relevant 字段做字段级 mutation。至少包括：

- source metadata；
- raw reaction；
- participant mapped/canonical structure；
- participant formal charge；
- role hypotheses；
- donor eligibility；
- mapping report；
- fragment lineage graph；
- ambiguity sets；
- transformation hypotheses；
- source ledger；
- provenance；
- quality report；
- quarantine；
- snapshot ID；
- 同 reaction ID、不同内容；
- 等价集合重排 hash 不变。

不要只测试 `reaction_hash` 字符串本身被手工篡改；必须修改真实 reaction 内容并重新走生产校验路径。

## 7. R4-C（P0）：完整绑定 StrictCandidate 的嵌套内容

### 已独立复现的问题

`candidate_path_preimage()` 只绑定 generation 和 candidate ledger 的少数字段。以下伪造被 `StrictCandidate.model_validate()` 接受：

```text
forged_unhashed_nested_generation_accepted=True
forged_unhashed_nested_ledger_accepted=True
forged_top_candidate_ledger_accepted=True
orphan_support_lineage_accepted=True
forged_parent_generation_content_accepted=True
```

当前遗漏的 generation 内容包括：

```text
edit_application_log
raw_product
changed_atoms
changed_bonds
sanitize_report
dedup_key
```

当前遗漏的 candidate ledger 内容包括：

```text
adaptation
inherited_context
inherited_assumptions
formal_transfers
balance
unknowns
evidence_ids
```

此外：

- 顶层 `candidate_analogy_ledger.source_ledger_id` 可被替换后仍通过；
- 顶层 generation path 内容可在 generation ID 不变时伪造；
- validator 只证明 `path_lineages <= support_lineage_ids`，而没有证明合同要求的集合精确相等。

### 强制修复要求

选择并完整实现一种明确策略：

1. candidate/path preimage 直接包含全部 P4 可消费的 canonical nested content；或
2. 每个 nested artifact 使用独立 content-addressed hash，candidate/path preimage 绑定这些 hash，并在验证时重算所有 nested hash。

无论采用哪种策略，都必须做到：

- generation ID 不能代替 generation content validation；
- top-level generation 与 path generation report 内容一致；
- top-level candidate ledger 与 path/nested ledger identity 和内容一致；
- source ledger ID 必须绑定权威 source ledger；
- transformation、site、lineage、generation、source ledger、candidate ledger 全链一致；
- parent ID sets 与所有 path ID unions 精确相等；
- support lineage IDs 与 path 实际使用 lineage IDs 精确相等；
- orphan、额外、重复或未消费 lineage 必须失败；
- strict candidate 至少包含一个完整合法 evidence path；
- 所有失败使用明确 typed error/failure code。

### 必须新增的对抗性测试

逐项 mutation 至少包括：

- generation.raw_product；
- generation.edit_application_log；
- generation.changed_atoms；
- generation.changed_bonds；
- generation.sanitize_report；
- generation.dedup_key；
- ledger.inherited_assumptions；
- ledger.formal_transfers；
- ledger.balance；
- ledger.unknowns；
- ledger.evidence_ids；
- top-level source_ledger_id；
- parent generation 内容但保持 generation ID；
- orphan support lineage；
- missing support lineage；
- duplicate path/lineage；
- path 与 parent namespace mismatch。

## 8. R4-D（P1）：Manifest hash 必须保护完整语义合同

### 已独立复现的问题

当前 `manifest_schema_hash()` 只覆盖 interface schema hashes、fields 和 required fields。修改以下内容后 hash 仍不变：

```text
nested_record_contract.mode
id_preimage_contract
```

未可靠绑定的语义合同还包括：

- manifest version；
- evidence kind semantics；
- blocker semantics；
- `p4_must_not`；
- namespace/binding semantics。

### 强制修复要求

- 对完整 canonical semantic manifest 计算 hash；
- 只允许明确列为 non-semantic 的展示字段排除；
- manifest version、nested record contract、ID/hash preimage contract、evidence semantics、blocker semantics、namespace contract、P4 禁止项全部进入 preimage；
- 未知 semantic 字段 fail-closed；
- live schema、manifest schema hashes 与实际模型必须可重算；
- Gate 必须绑定这个完整 manifest hash，而不是旧的部分投影 hash。

必须增加逐字段 mutation tests，证明任意 semantic contract 改变都会改变 hash或被拒绝；等价字典/集合排序变化不得改变 hash。

## 9. R4-E（P1）：重写 A/B-only stripped reaction mutation

### 已独立确认的问题

Round 3 的所谓 A/B-only mutation 构造了空 reaction view、`tampered_hash` 和伪造引用，最终因 `FOLD_AUTHORITY_HASH` 被拒绝。它测试的是浅层 hash tamper，不是完整 reaction 被剥离为 A/B-only 后是否仍会进入系统。

registry 还把 `FOLD_AUTHORITY_HASH` 固定为该 mutation 的 expected code，因此错误原因被标记为有效 mutation。

### 强制修复要求

重新实现 mutation：

1. 从一个合法、baseline PASS 的完整 reaction authority 开始；
2. 只剥离 A/B 之外的完整反应信息、参与者、cofactor/context、lineage/ledger 或合同要求的信息；
3. 重新计算所有攻击者按公开规则可以重新计算的 hash；
4. 保持外围 snapshot/fold/ref 结构自洽；
5. 通过真实生产 loader/kernel/Gate 路径执行；
6. 必须因 reaction completeness/authority violation 被拒绝，而不是因手写错误 hash 被提前拒绝；
7. observed failure code 必须从实际执行结果读取；
8. baseline 与 mutant 必须分别保存 artifact hash、exit/status 和真实 observed code。

Mutation 的原则是攻击目标不变量，不能依赖另一个更浅层校验提前失败。

## 10. 不得回归的已确认行为

保留 Round 3 已修复或已有的正确行为：

- transform preimage 覆盖 transferred `bonds_to` 与 removed sink pairs；
- transform binding verifier 有效；
- 单个坏 reaction 被隔离，不使整个 kernel 崩溃；
- report collected count 真实且非零；
- Git-state tests 不依赖当前脏工作树；
- negative formal charges 合法；
- isotope-preserving identity 保留 isotope 差异；
- query/product 使用一致 identity policy；
- fixture 始终标记为 `synthetic_fixture`；
- fixture 不满足 real-evidence Gate；
- donor 保留所有 eligible reactions；
- kernel 遍历 donor × eligible reactions；
- source ledger forge 被拒绝；
- critical contradiction 不能进入 strict lane；
- system failure 与 scientific abstention 分离；
- P3 不把结构生成委托给 LLM；
- P3 输出 unranked strict candidates；
- P4 才拥有 ranking/abstention；
- 缺真实资源时 P3 Gate 诚实 `BLOCKED`，exit code 2。

## 11. 强制验证矩阵

设置：

```bash
P3_PY=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

至少运行：

```bash
$P3_PY -m pytest <每个新增RED测试> -q -p no:cacheprovider --color=no
$P3_PY -m pytest <每个修复后的GREEN测试> -q -p no:cacheprovider --color=no
$P3_PY -m pytest tests/p3 -q -p no:cacheprovider --color=no
$P3_PY -m pytest tests -q -p no:cacheprovider --color=no
$P3_PY -m pytest tests/p3/test_mutations.py -q -p no:cacheprovider --color=no
$P3_PY scripts/run_p0_gate.py
$P3_PY scripts/run_p1_gate.py
$P3_PY scripts/run_p3_preflight.py
$P3_PY scripts/run_p3_gate.py
```

如果存在 P2 Gate runner，也必须运行它；先用 `rg --files scripts | rg 'p2.*gate|run_p2'` 确认真实文件名，不能猜测。

Gate 语义必须保持：

```text
PASS    -> exit 0
FAIL    -> exit 1
BLOCKED -> exit 2
```

规则：

- machinery failure 与真实资源 blocker 同时存在时，总体为 FAIL；
- machinery 全部通过而真实资源缺失时，P3 Gate 可保持 BLOCKED/2；
- 不得为获得 exit 0 而伪造真实资源；
- P0/P1/P2 回归失败必须如实报告；
- 不得硬编码 expected test counts；
- collected/pass/fail/error/skip 等必须由真实输出解析。

## 12. 结构化证据要求

每条命令记录至少包含：

```text
label
command
cwd
python_executable
started_at
finished_at
duration_seconds
exit_code
collected
passed
failed
errors
skipped
xfailed
xpassed
stdout_stderr_hash
raw_tail
```

每个 finding 至少包含：

```text
finding_id
severity
invariant
red_test
red_command
red_exit_code
red_observed_failure
red_stdout_hash
fix_files
fix_summary
green_test
green_command
green_exit_code
green_counts
green_stdout_hash
adversarial_probe
adversarial_command
adversarial_result
adversarial_stdout_hash
status
```

不能只在 Markdown 中声称“RED→GREEN”；必须有可复查的真实命令记录和输出哈希。

## 13. Round 4 交付物

不得覆盖 Round 1–3 文件。至少生成：

```text
reports/p3/P3_ROUND_4_STARTING_WORKTREE_STATE.md
reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_4.md
reports/p3/P3_ROUND_4_AUDIT_EVIDENCE.json
reports/p3/P3_ROUND_4_REMEDIATION_WORKLOG.md
reports/p3/P3_GATE_REPORT_ROUND_4.json
reports/p3/P3_GATE_REPORT_ROUND_4.md
reports/p3/P3_MUTATION_RESULTS_ROUND_4.json
reports/p3/p3_p4_interface_manifest_round_4.json
reports/p3/P3_ROUND_4_CHANGED_FILES.json
```

如需生成器，创建 Round 4 专用生成器，不得把 Round 3 报告原地改写成 Round 4。

Submission 必须：

- 逐项回答 R4-A 至 R4-E；
- 明确区分 machinery evidence、synthetic fixture evidence 与 real evidence；
- 报告所有 RED/GREEN/对抗性结果；
- 列出精确 commands、counts、exit codes 和 hashes；
- 区分 inherited worktree changes 与 Round 4 changes；
- 列出完整 Gate/mutation/interface manifest 状态；
- 明确真实资源 blocker；
- 明确 P4 仍需等待 ChatGPT 审核；
- 不得声称 P3 正式 PASS 或 production ready。

## 14. 完成判据和终态

只有同时满足以下条件，才可称为 Round 4 implementation-ready：

- R4-A 至 R4-E 全部有真实 RED→GREEN 证据；
- ChatGPT Round 3 的全部独立伪造探针都已被生产路径拒绝；
- fully fabricated Gate artifact 不能 PASS；
- reaction audit fields 变化不能保留旧 authority；
- nested generation/ledger 篡改不能保留旧 candidate authority；
- orphan support lineage 被拒绝；
- manifest semantic contract tamper 被检测；
- A/B-only mutation 命中正确目标不变量；
- P3 tests 与 full tests 通过且统计真实一致；
- P0/P1/P2 已存在回归与 Gate 没有被破坏；
- P3 machinery 不再存在 FAIL；
- 缺真实资源时仍诚实 BLOCKED；
- 没有执行任何禁止操作。

若 machinery 修复完成但真实资源仍缺失，Submission 最后一行必须严格为：

```text
P3_ROUND_4_IMPLEMENTATION_READY_GATE_BLOCKED_PENDING_CHATGPT_READ_ONLY_AUDIT
```

若任一 machinery finding 未完成、证据不足或测试失败，最后一行必须严格为：

```text
P3_ROUND_4_REMEDIATION_INCOMPLETE_NOT_READY_FOR_CHATGPT_ACCEPTANCE
```

完成后只向用户返回：

1. Round 4 submission 绝对路径；
2. structured evidence 绝对路径；
3. remediation worklog 绝对路径；
4. P3 Gate report 绝对路径；
5. mutation results 与 interface manifest 绝对路径；
6. 精简的真实测试/Gate 结果；
7. exact terminal status；
8. 以下两行：

```text
READY_FOR_CHATGPT_P3_ROUND_4_READ_ONLY_AUDIT
P4_BLOCKED_PENDING_CHATGPT_AUDIT
```

然后停止。不得开始 P4，不得 merge。
