# ChatGPT P3 Round 5 Remediation Instructions

## 1. 任务与正式审计状态

你正在修复 ReactionAgent 的 P3 Strict Kernel。ChatGPT 已完成 P3 Round 4 只读审核。Round 4 的定向测试和完整 P3 测试能够通过，P3 Gate runner 也诚实返回了真实资源 `BLOCKED`；但是独立对抗性探针仍然能够伪造 Gate PASS，并能让完全同步剥离后的 A→B-only reaction 被 loader 接受。

正式状态为：

```text
CHATGPT_P3_ROUND_4_READ_ONLY_AUDIT = FAIL
P3_MACHINERY = FAIL_NEEDS_REMEDIATION
P3_REAL_EVIDENCE = BLOCKED
P3_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P3_GATE_RUNNER_REPORTED = BLOCKED
P3_GATE_AUDITED_EFFECTIVE_STATUS = FAIL
P4_INTEGRATION = BLOCKED
```

本轮是 **P3 Round 5 定向修复**。目标是建立真正的 Gate execution authority 和 reaction authority root，而不是继续给调用方自填的字段增加更多自签名 hash。

这不是 P4 实现，不是架构重写，也不是通过修改冻结合同来适配代码。真实 snapshot、automatic donor、strict learned mapper 或 P2 pilot funnel 缺失可以继续诚实标记为 `BLOCKED`，但任何 machinery failure 必须使审计状态为 `FAIL`，不能被 blocker 掩盖。

## 2. 工作树、分支和 Python

只在以下 P3 工作树中实施修复：

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

不要假定 P3 worktree 自己有 `.venv/bin/python`。

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
reports/p3/P3_ROUND_5_STARTING_WORKTREE_STATE.md
```

该工作树包含继承的 P0/P1 修改和大量未跟踪 P3 文件。必须保留它们。禁止使用：

- `git reset`
- `git checkout --`
- `git restore`
- `git clean`
- destructive deletion
- rebase
- cherry-pick
- merge

本轮不 commit、不 push、不 merge。

## 3. 必须完整阅读的材料

在修改任何代码之前，完整阅读 Round 4 交付物：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_4.md

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_4_AUDIT_EVIDENCE.json

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_4_REMEDIATION_WORKLOG.md

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_GATE_REPORT_ROUND_4.json

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_MUTATION_RESULTS_ROUND_4.json

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/p3_p4_interface_manifest_round_4.json
```

完整阅读本轮直接相关的生产和测试文件：

```text
reaction_agent/p3/schemas.py
reaction_agent/p3/gate.py
reaction_agent/p3/mutation_harness.py
reaction_agent/p3/mutations_round3.py
reaction_agent/p3/fixtures.py
reaction_agent/p3/load.py
reaction_agent/p3/manifest.py
reaction_agent/p3/kernel.py
reaction_agent/p3/store.py
reaction_agent/p3/generate.py
reaction_agent/p3/validate.py

tests/p3/test_r4a_evidence_reference.py
tests/p3/test_r4b_authority_fields.py
tests/p3/test_r4c_nested_binding.py
tests/p3/test_r4d_manifest_contract.py
tests/p3/test_r4e_ab_only.py
tests/p3/test_mutations.py
tests/p3/test_r3f_mutation_harness.py
tests/p3/test_r2i_gate.py

scripts/run_p3_gate.py
scripts/run_p3_mutation_case.py
scripts/run_p3_preflight.py
scripts/generate_p3_round4_reports.py
```

使用 `rg` 查找并阅读真正生效的 final design、final plan、P0/P1 frozen contracts、P1 snapshot authority、P2 fold/truth authority、P3 prompt、P3→P4 interface 和相关 ADR。不要凭文件名猜测：

```bash
rg --files plan training reports reaction_agent tests scripts | sort
rg -n "P1.*authority|snapshot.*authority|reaction_hash|root_hash|P2.*fold|P3|Strict Kernel|Gate|mutation|P3.*P4" plan training reports reaction_agent tests scripts
```

不得修改 final design、final plan、ADR、P0/P1 frozen contracts 或 P2 authority 来使现有实现看似合规。

## 4. 用户目标和不可混淆的化学边界

系统目标是：根据 query X 检索与 X 结构最相似的 donor A，然后读取 donor A 的**完整反应** A→B，并将完整 reaction transformation 严格转移到 X，推测 X→Y。

必须区分：

```text
供体检索阶段：
允许为了结构相似性计算而剥离 cofactor / small molecule。

反应权威与变换提取阶段：
必须恢复并使用完整 A→B reaction，包括全部 reactants、products、
co-substrates、cofactors、coproducts、mapping、lineage、ledger 和 provenance。
```

`canonical_identity.py` 或 retrieval 层的 cofactor/small-molecule stripping 只能影响 donor similarity identity，绝不能成为 P3 reaction authority 的输入删减规则。

## 5. 强制工程纪律

对 R5-A 至 R5-E 的每项 finding，严格执行：

1. 先写一个通过真实生产路径复现漏洞的 RED test。
2. 单独运行 RED test并记录命令、exit code、观察结果和输出哈希。
3. 实施满足冻结合同的最小修复。
4. 单独运行 GREEN test。
5. 新增独立对抗性 mutation/probe。
6. 运行相关回归。
7. 将 RED、GREEN 和 adversarial evidence 写入结构化 JSON 与 worklog。

禁止：

- 通过修改期望值来让错误实现变绿；
- 删除、弱化、skip 或 xfail 现有测试；
- 用 `pytest.raises(Exception)` 代替 typed exception/failure code；
- 硬编码 PASS、BLOCKED、测试数或 observed failure code；
- 把 expected code 复制到 observed code；
- 让提交方自填的 status 成为 Gate authority；
- 把任意非空 hash 当成执行证明；
- 让 fixture 冒充 real evidence；
- 安装依赖、联网或调用 LLM/MCP/Orchestra；
- 修改冻结文档或 legacy source 来迎合实现；
- commit、push、merge；
- 开始 P4。

## 6. R5-A（P0）：建立真实 Gate execution authority

### Round 4 独立复现结果

ChatGPT 构造了一个完全未执行的 Gate artifact：

- 使用当前 live interface hash；
- G01–G10 全部由攻击者手写 `PASS`；
- G01/G03/G07 手写 `evidence_kind=real`；
- `artifact_type=attacker_claim`；
- artifact ID 指向不存在的对象；
- content 明确写着 `executed=false`、`real_artifact=false`；
- 攻击者同步计算 content hash；
- mutation command 写成 `never-executed`；
- cwd 写成 `/nonexistent`；
- artifact/stdout hash 使用任意非空字符串；
- mutation expected/observed code 全部改为 `ATTACKER_SELECTED_CODE`；
- mutation target 全部改为 G10。

当前生产验证结果：

```text
fully_fabricated_round4_verdict='PASS'
fully_fabricated_round4_verified=True
fully_fabricated_round4_failures=[]
```

另外，把 evidence reference 的 `run_id` 改为与 Gate report 不同的 run，仍然得到：

```text
evidence_run_mismatch_verdict='PASS'
evidence_run_mismatch_verified=True
```

### 根因

当前 `EvidenceReference` 是 self-authored/self-signed：调用方同时提供 content、content hash、artifact ID、artifact type、run ID、evidence kind 和 Gate status。验证器只证明调用方填写的 content 与调用方计算的 hash 一致，没有证明 content 来自真实执行。

`canonical_hash(ref.content) == ref.content_hash` 是完整性检查，不是来源真实性或执行证明。

### 必须选择并写清楚一个 trust model

优先选择最简单且可验证的正确方案，二选一：

#### 方案 A：in-process execution authority

- 只有实际 Gate runner 执行检查后才能产生 authoritative verdict；
- 每个 Gate item status 由检查函数返回值计算；
- 序列化 artifact 只能被标为 `structurally_valid`，不能仅凭 JSON 恢复为 `verified=True`；
- 任意外部 `dict` 输入的 `evaluate_gate_artifact()` 都不能在没有可信 execution context 的情况下返回 verified PASS；
- Gate runner 在同一进程中持有实际 typed execution objects，并直接重算每个 item。

#### 方案 B：trusted content-addressed artifact store

- Gate execution 将 typed raw artifacts 写入独立 run directory/store；
- 生成不可由 artifact payload 自己定义的 run manifest/root index；
- Evidence reference 只携带 content-addressed ID，不嵌入并信任调用方自填 content；
- verifier 通过受信任 resolver 读取真实 artifact；
- verifier 重算文件/对象 hash；
- verifier验证 artifact 属于当前 run manifest；
- verifier按 artifact type 解析对应 typed schema；
- 没有 resolver/root manifest 时只能 structural validate，不能 verified PASS。

不要自行发明没有密钥管理的“签名”。一个存储在同一 payload 中、由同一调用方计算的所谓 signature 仍然是自签名，不能作为 trust root。

### 强制语义

- Gate item status 必须从 typed evidence 内容推导，调用方不能直接决定；
- `artifact_type` 必须是冻结 enum/union，不得是任意字符串；
- 每种 artifact type 必须有明确 typed content schema；
- `artifact_id` 必须由真实 artifact 内容或可信 execution receipt 派生；
- `evidence_kind` 必须从 artifact provenance 推导；
- `schema_version` 必须等于当前支持版本，未知版本 fail-closed；
- `ref.run_id == gate.run_id` 必须成立；
- case/query/fold/snapshot ID/hash 必须完整绑定；
- artifact path/ID 不存在必须失败；
- artifact 内容与 hash 同时被替换，但不属于当前 trusted run manifest，必须失败；
- 未知顶层字段和未知 authority 字段 fail-closed；
- machinery failure 优先于 real-resource blocker。

### 必须新增的 RED/GREEN/adversarial tests

至少覆盖：

1. 完全伪造的 G01–G10 PASS artifact；
2. content 与 content hash 同时由攻击者替换；
3. 不存在的 artifact ID/path；
4. 未知 artifact type；
5. artifact type 与 content schema 不匹配；
6. evidence run ID mismatch；
7. case/query/fold/snapshot namespace mismatch；
8. 攻击者手写 evidence kind=real；
9. 攻击者手写 status=PASS，但实际 evidence 表示失败；
10. 合法 executed artifact 被移动到另一个 run；
11. 未知 schema version；
12. 未提供 trusted resolver/context 的离线 dict；
13. 真正执行的最小 machinery Gate 能被验证；
14. machinery FAIL 与 real BLOCKED 同时存在时总体为 FAIL。

## 7. R5-B（P0）：冻结 mutation 完整合同并绑定真实执行

### Round 4 独立复现结果

当前 `_frozen_mutation_ids()` 只冻结 mutation IDs，没有冻结：

- target Gate item；
- expected failure code；
- baseline/mutated case identity；
- implementation/component version；
- command contract；
- artifact schema。

Gate 只检查 artifact hash/stdout hash 是否非空，并比较提交方自己填写的 expected/observed code。因此不存在的命令、任意非空 hash 和攻击者选择的 failure code 仍能通过。

### 强制修复要求

- 创建一个 typed frozen mutation contract/registry；
- 每条 contract 至少绑定 mutation ID、target Gate item、expected failure code、baseline case、mutated case、component、schema/version；
- registry 必须有 canonical hash，并绑定当前 Gate execution；
- Gate 按完整 metadata 比较，不能只比较 ID set；
- baseline/mutated execution receipt 必须来自 R5-A 的可信 execution authority；
- 从真实 stdout/stderr 重算 stdout hash；
- 从真实 typed output 重算 artifact hash；
- 从真实 output 解析 observed failure code；
- 验证 exit code、status、failure code 三者相互一致；
- 验证 `baseline_status == baseline.status`；
- 验证 `mutated_status == mutated.status`；
- 验证 PASS/FAIL/ERROR 与 exit code 合同；
- command/case identity 与 registry 不一致必须失败；
- cwd 或 executable 字符串本身不能被当作执行证据；
- 删除生产代码中的 fabricated/synthetic-valid mutation baseline helper，或确保它只能用于明确的 structural unit test，绝不能进入 Gate authority；
- `run_mutations=False` 不得静默使用没有可信 root/hash 的旧缓存。

### 必须新增的攻击测试

- 正确 IDs、全部错误 targets；
- 正确 IDs、攻击者选择的 expected code；
- expected=observed 但均不等于 registry；
- baseline_status 与 baseline.status 冲突；
- mutated_status 与 mutated.status 冲突；
- status 与 exit code 冲突；
- raw output 被修改但 stdout hash 未更新；
- raw output 与 stdout hash 同时更新但 execution receipt 不属于当前 run；
- artifact hash 只填任意非空字符串；
- command 指向不存在程序；
- cached mutation 属于另一个 run/component version；
- mutation implementation/registry hash drift。

## 8. R5-C（P0）：以冻结 P1/P2 authority root 阻止完全同步的 A/B-only 剥离

### Round 4 独立复现结果

Round 4 新增 participant/ledger exact set equality，只能检测单边删除。ChatGPT 从完整 hydrolysis reaction 开始，同步执行：

- 只保留 donor A 与 primary product B；
- 删除 H2O co-substrate；
- 删除 coproduct；
- 同步修改 fixture participants；
- 同步修改 ReactionEvidence participants；
- 同步修改 reactant/product entries、roles、stoichiometry；
- 同步过滤 formal transfers、added sources、removed sinks；
- 同步过滤 mapping pairs；
- 同步过滤 lineages；
- 同步修改 evidence resolved lineage IDs；
- 同步替换 evidence source ledger；
- 将 raw/normalized reaction 改为 A→B；
- 同步修改 reactant/product smiles；
- 重新计算 reaction hash；
- 重新生成 ReactionRef；
- 重新计算 TrainView snapshot hash。

生产 loader 结果：

```text
fully_self_consistent_ab_strip_accepted=True
fully_self_consistent_ab_participants=2
```

### 根因

完整 content hash 只能证明“当前内容自 hash 生成后未变化”，不能证明“当前内容与上游真实原始反应完全一致”。如果 P3 同时接受调用方提供的内容和调用方根据该内容重算的 expected hash，剥离后的新对象仍会成为一个自洽的新 authority。

### 强制修复要求

- 找到并复用现有 P1 snapshot/manifest/ledger authority，不要创建与 P1 同义但不兼容的新 schema；
- P3 必须从冻结的 P1/P2 authority root 获取 expected snapshot hash 和 reaction ID→reaction hash 映射；
- expected reaction hash 不能来自待验证 TrainView 自身；
- caller 不得通过 `snapshot_hash=recompute_train_view_hash(mutated_view)` 创造新 authority；
- P3 loader 必须同时接收或解析独立的 trusted authority manifest/resolver；
- mutation 可以修改 candidate reaction content，但必须保留上游冻结 expected root，因此同步剥离后必须出现 authority mismatch；
- fixture 模式要有测试启动前冻结的 fixture authority root，mutation 不能根据 mutation 后内容重建 expected root；
- 对 evidence 与 fixture 中重复保存的 mapping、ledger、participants、lineages、reaction strings 做双向内容一致性验证；
- `ReactionEvidence.source_reaction_ledger` 与 `FixtureReaction.source_ledger` 必须内容一致或通过同一 content hash 绑定；
- `ReactionEvidence.mapping_report` 与 fixture mapping report 必须一致；
- raw/normalized reaction 中的分子/atom maps 必须与 participant/mapping authority 相符；
- reaction authority 必须保留完整 reactant/product sides，而不是只要求至少一个 participant；
- donor retrieval 中的 cofactor stripping 不得改变完整 reaction authority。

### 正确的 A/B-only mutation

重写 mutation，使其：

1. 从一个 frozen-authority baseline PASS 的完整 hydrolysis reaction 开始；
2. 同步剥离所有 A/B 之外的 participants、ledger、mapping、lineage 和 reaction strings；
3. 重新计算攻击者可计算的局部/content hashes；
4. 不替换冻结的上游 expected reaction/snapshot root；
5. 通过真实 P3 loader path；
6. 因 `REACTION_AUTHORITY_MISMATCH`、`FROZEN_REACTION_HASH_MISMATCH` 或等价明确代码失败；
7. 不能因为故意保留 participant/ledger set mismatch 而提前失败；
8. observed code 必须来自实际执行。

### 必须新增的测试

- 单边 participant 删除；
- 单边 ledger 删除；
- participants 与 ledger 同步删除；
- participants/ledger/mapping/lineage/raw reaction 全同步删除；
- 同步删除并重算局部 reaction hash；
- 同步删除并重算 caller TrainView hash；
- 同 reaction ID、被完整裁剪的内容；
- evidence/fixture ledger 内容不一致；
- evidence/fixture mapping 内容不一致；
- raw reaction 与 participant structures 不一致；
- frozen authority baseline 合法加载；
- 通过正式 P1 snapshot builder 生成的新合法 snapshot 可以加载；
- retrieval identity stripping 不改变 reaction authority hash。

## 9. R5-D（P1）：Manifest hash 覆盖所有嵌套未知语义字段

### Round 4 独立复现结果

Round 4 已覆盖多个顶层语义字段，但 `interfaces` 中每个条目仍被手工投影成固定子集。向以下位置添加新语义字段：

```text
interfaces.StrictCandidate.unknown_semantic_contract
```

结果：

```text
nested_unknown_manifest_field_keeps_hash=True
```

这与 Round 4 Submission 中“unknown semantic fields fail-closed”的声明不符。

### 强制修复要求

- 对完整 manifest canonical dump 计算 hash；
- 仅通过明确、版本化的 non-semantic JSON path allowlist 排除字段；
- 不要为每个 interface 重新选择已知字段；
- interface 内任何新字段默认视为 semantic 并进入 hash；
- 或者使用严格 typed manifest schema，未知字段直接拒绝；
- nested dict/list 中未知 semantic field 也必须进入 hash或被拒绝；
- 等价字典排序不得改变 hash；
- 明确 non-semantic display 字段变化可不改变 hash；
- Gate 必须绑定修复后的完整 manifest hash。

必须测试：

- unknown top-level semantic field；
- unknown interface-level field；
- unknown nested dict field；
- unknown nested list element field；
- known semantic field mutation；
- explicit non-semantic field mutation；
- dict ordering invariance；
- manifest schema/version drift。

## 10. R5-E（P1）：报告与结构化证据单一来源

Round 4 Submission 使用：

```text
R4-A 21/21
R4-B 30/30
R4-C 22/22
R4-D 19/19
```

Worklog 各 finding 段落仍残留：

```text
R4-A 20/20
R4-B 29/29
R4-C 20/20
R4-D 18/18
```

但 Worklog verification matrix 又使用新数字。独立当前总数为 96 passed，因此测试并未失败，但报告存在 stale prose。

Round 5 必须：

- 所有 Markdown counts 从同一结构化 command record 生成；
- finding 段落、verification matrix、submission、audit evidence JSON 数字完全一致；
- 不手工复制计数；
- 不硬编码 expected collected；
- generator 在发现数字不一致时 fail-closed；
- RED 证据必须对应真实可执行命令，不得只写“ChatGPT audit repro”；
- 每个报告包含 generation timestamp、worktree、branch、HEAD 和真实 Git state；
- inherited changes 与 Round 5 changes 分开列出。

## 11. 不得回归的正确行为

以下 Round 4 或更早已正确实现的内容必须保留：

- reaction authority preimage 覆盖完整 ReactionEvidence 字段；
- source metadata、raw reaction、provenance、quality、mapping、lineage、ledger、eligibility 均进入 preimage；
- runtime-only mapping timing 可明确排除；
- candidate path preimage 包含完整 generation report；
- candidate path preimage 包含完整 candidate analogy ledger；
- top-level/path generation 内容双向一致；
- candidate/path ledger binding；
- exact support lineage equality；
- orphan/missing/duplicate support lineage 被拒绝；
- transform preimage 覆盖 transferred bonds 和 removed sinks；
- 单个坏 reaction 被 kernel 隔离；
- negative formal charge 合法；
- isotope-preserving identity；
- query/product identity policy 一致；
- fixture 永远标记 `synthetic_fixture`；
- system failure 与 scientific abstention 分离；
- P3 不调用 LLM 生成结构；
- P3 只输出 unranked strict candidates；
- P4 负责 ranking/abstention；
- 缺真实资源时 formal P3 Gate 保持诚实 BLOCKED/2。

## 12. 强制验证矩阵

使用：

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

使用 `rg --files scripts | rg 'p2.*gate|run_p2'` 查找真实 P2 Gate 命令；存在则必须运行，不得猜测文件名。

Gate exit contract：

```text
PASS    -> 0
FAIL    -> 1
BLOCKED -> 2
```

要求：

- machinery failure 与 blocker 同时存在时为 FAIL/1；
- machinery 全部通过但真实资源缺失时为 BLOCKED/2；
- 不得伪造真实资源使 Gate 变成 PASS；
- P0/P1/P2 回归失败必须如实报告；
- 测试 collected/pass/fail/error/skip 从真实输出解析。

## 13. 结构化证据合同

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
adversarial_exit_code
adversarial_result
adversarial_stdout_hash
status
```

对 Gate execution authority 还必须记录：

```text
trust_model
run_manifest_id
run_manifest_hash
artifact_store_or_in_process_authority
artifact_ids
artifact_hashes
registry_hash
verification_mode
```

如果是离线 artifact 且无法证明执行来源，必须明确标记为 `structurally_valid_unverified`，不得写 `verified=true`。

## 14. Round 5 交付物

不得覆盖 Round 1–4 文件。至少生成：

```text
reports/p3/P3_ROUND_5_STARTING_WORKTREE_STATE.md
reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_5.md
reports/p3/P3_ROUND_5_AUDIT_EVIDENCE.json
reports/p3/P3_ROUND_5_REMEDIATION_WORKLOG.md
reports/p3/P3_GATE_REPORT_ROUND_5.json
reports/p3/P3_GATE_REPORT_ROUND_5.md
reports/p3/P3_MUTATION_RESULTS_ROUND_5.json
reports/p3/p3_p4_interface_manifest_round_5.json
reports/p3/P3_ROUND_5_CHANGED_FILES.json
```

如需 generator，创建 Round 5 专用生成器；不得原地改写 Round 4 报告。

Submission 必须逐项回答 R5-A 至 R5-E，并明确：

- 采用的 Gate trust model；
- 为什么 arbitrary dict 不再能得到 verified PASS；
- mutation registry 的完整 canonical contract/hash；
- mutation execution receipt 如何被验证；
- P1/P2 reaction/snapshot authority root 从何加载；
- 为什么完全同步的 A/B-only strip 会被拒绝；
- retrieval stripping 与 reaction authority 的边界；
- manifest nested unknown fields 如何 fail-closed；
- real、synthetic、diagnostic、blocked evidence 的区分；
- 真实资源 blocker；
- P4 仍需等待 ChatGPT 审核。

不得声称 P3 正式 PASS、production ready 或 P4 已解锁。

## 15. Round 5 完成判据

只有同时满足以下条件，才可称为 implementation-ready pending audit：

- R5-A 至 R5-E 全部真实 RED→GREEN；
- 完全伪造 Gate artifact 返回 FAIL/unverified；
- self-authored content+hash 不构成 execution proof；
- evidence run mismatch 被拒绝；
- unknown artifact type/schema 被拒绝；
- mutation metadata 与 frozen registry 完整匹配；
- fake command/fake hashes/fake expected code 被拒绝；
- mutation execution receipt 可复核；
- 完全同步剥离的 A/B-only reaction 被 frozen upstream authority 拒绝；
- P3 不接受 caller 重算的新 TrainView hash 作为 authority root；
- retrieval cofactor stripping 不影响完整 reaction authority；
- manifest nested unknown semantic field 被覆盖或拒绝；
- 全部报告计数一致；
- P3 tests 与 full tests 通过；
- P0/P1/P2 已存在回归和 Gate 不被破坏；
- 缺真实资源时 P3 Gate 仍诚实 BLOCKED/2；
- 没有执行禁止操作。

若 machinery 修复完成，但真实资源仍缺失，Submission 最后一行必须严格为：

```text
P3_ROUND_5_IMPLEMENTATION_READY_GATE_BLOCKED_PENDING_CHATGPT_READ_ONLY_AUDIT
```

如果任一 machinery finding、测试或证据未完成，最后一行必须严格为：

```text
P3_ROUND_5_REMEDIATION_INCOMPLETE_NOT_READY_FOR_CHATGPT_ACCEPTANCE
```

## 16. 完成后只返回

完成后只向用户返回：

1. Round 5 submission 绝对路径；
2. structured audit evidence 绝对路径；
3. remediation worklog 绝对路径；
4. P3 Gate report 绝对路径；
5. mutation results 绝对路径；
6. interface manifest 绝对路径；
7. 精简的真实测试/Gate 结果；
8. exact terminal status；
9. 以下两行：

```text
READY_FOR_CHATGPT_P3_ROUND_5_READ_ONLY_AUDIT
P4_BLOCKED_PENDING_CHATGPT_AUDIT
```

然后停止。不得开始 P4，不得 merge。
