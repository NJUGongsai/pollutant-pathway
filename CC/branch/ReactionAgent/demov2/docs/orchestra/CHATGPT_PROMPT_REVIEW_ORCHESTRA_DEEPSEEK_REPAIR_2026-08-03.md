# ChatGPT Prompt — Independently Audit the Orchestra DeepSeek Repair

> Recipient: a fresh AI review window with no prior chat memory  
> Role: independent read-only reviewer  
> Target: proposed Orchestra live-dispatch repair  
> Editing repair code: forbidden  
> Real provider/model calls: forbidden  
> Required verdict: ACCEPT, REJECT-REMEDIATION, or BLOCKED

---

## 1. Read the audit handoff first

Read this file completely before taking any action:

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_HANDOFF_REVIEW_ORCHESTRA_DEEPSEEK_REPAIR_2026-08-03.md
~~~

Then read every authority and repair artifact referenced by that handoff, including:

~~~text
/Users/frank_gong/.codex/skills/orchestra-live/SKILL.md

/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_HANDOFF_ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_2026-08-02.md

/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_PROMPT_REPAIR_ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_2026-08-02.md

/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_REPORT_2026-08-02.md

/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_EVIDENCE_2026-08-02.json
~~~

Do not rely on summaries. Read the files directly and completely.

---

## 2. Audit objective

Independently determine whether the uncommitted Orchestra repair actually satisfies O-C01 through O-C12 and is safe to:

1. commit;
2. load by restarting the MCP process;
3. use for one separately authorized real DeepSeek probe;
4. unblock ReactionAgent P2A proposal dispatch.

A green self-authored test suite is not sufficient. Verify that tests reproduce the real failures and assert the original acceptance semantics.

Do not fix code in this review window. If defects remain, reject and specify exact remediation.

---

## 3. Target worktree

Review this worktree in place:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl
~~~

Expected base:

~~~text
branch: milestone-e-real-worker
HEAD: ce53690cf6a806594871580aa941021cb0461466
~~~

Expected proposed changes:

~~~text
M  src/orchestra/cognition/engine.py
M  src/orchestra/services/external_workflows.py
M  src/orchestra/services/live_dispatch.py
?? tests/services/test_live_dispatch_repair.py
?? docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_REPORT_2026-08-02.md
?? docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_EVIDENCE_2026-08-02.json
~~~

The dirty state is expected. Preserve it.

If additional unexplained changes exist:

- record them;
- do not reset, stash, clean, or overwrite;
- determine whether they contaminate the audit;
- use BLOCKED only if reliable review is genuinely impossible.

---

## 4. Prohibited actions

Do not:

- modify Orchestra source or tests;
- format or rewrite repair files;
- stage, commit, push, merge, reset, stash, or clean;
- restart or re-register MCP;
- call DeepSeek or any other provider;
- use Orchestra live dispatch;
- access the network;
- install/upgrade dependencies;
- modify or migrate orchestra.db;
- checkpoint/vacuum/delete WAL or SHM files;
- edit ReactionAgent implementation;
- overwrite the repair report or evidence;
- expose credentials, secret refs, authorization headers, or provider URLs.

Use fake/local tests and temporary databases only.

---

## 5. Mandatory audit workflow

### Step A — Capture repository evidence

Record:

~~~text
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --branch
git diff --stat
git diff --numstat
git diff --check
~~~

Read full tracked diffs and full untracked files.

Hash:

- repair report;
- repair JSON evidence;
- new repair test file;
- each modified source file.

Do not stage anything.

### Step B — Verify original failure evidence

Read orchestra.db with normal sqlite3 -readonly so WAL is included.

Confirm:

- Failure A model call and token counts;
- Failure B model call and token counts;
- both incomplete reasons;
- failed operation reason codes;
- zero proposal artifacts/executions;
- no extra model call from recovery;
- no additional real model call during repair.

Do not use immutable=1.

### Step C — Trace repair behavior

Trace the actual code path:

~~~text
MCP dispatch
→ operation/idempotency
→ attempt pre-check
→ context assembly
→ input estimate
→ output reservation
→ gateway max_tokens
→ provider result
→ usage settlement
→ model-call audit
→ artifact/no-artifact
→ workflow state
→ get_workflow next actions
→ same/new request recovery
~~~

Use exact file/function/line references.

### Step D — Rerun local tests independently

Use the existing environment without installing anything.

Run, at minimum:

1. the new repair test file;
2. existing live-dispatch service tests;
3. budget ledger tests;
4. gateway contract/Anthropic tests;
5. persistence model-call/journal/live tests;
6. MCP live-tool/stdio/schema tests;
7. cognition live-proposal tests;
8. relevant e2e bridge tests;
9. full test suite;
10. ruff check;
11. ruff format --check;
12. git diff --check.

Report exact commands, interpreter/tool versions, exit codes, counts, and durations.

### Step E — Run adversarial audit checks in temporary space

Do not edit the target worktree. Use temporary tests/databases/copies if needed.

Verify:

1. a realistic Failure-A context estimate larger than the 30,000 workflow/task budget is rejected before gateway invocation;
2. task max_tokens semantics are consistent across every layer;
3. actual token/cost usage above reservation does not become silently undercounted;
4. max_output_tokens is distinguished from other incomplete reasons;
5. public MCP/service diagnostics expose bounded terminal details;
6. same-request replay returns stable bounded terminal state;
7. new-request attempt exhaustion is typed;
8. multi-task and revised-plan attempts behave correctly;
9. a real simulated transport timeout cannot duplicate provider invocation;
10. failed diagnostic lookup does not fail open;
11. workflow state is not stuck incoherently in executing;
12. every advertised next action is a real supported operation;
13. incomplete content cannot enter artifact/evidence/acceptance.

### Step F — Decide every acceptance criterion

For each O-C01 through O-C12:

- PASS;
- FAIL;
- BLOCKED.

Cite independent evidence, not only repair-report text.

If the report's remaining-risks section admits required behavior is unfixed, that criterion cannot PASS.

---

## 6. Mandatory high-risk checks

### 6.1 Preflight input estimation

The repair report says actual input estimation is not implemented and worker_estimated_input_tokens remains fixed at 1,000.

Determine whether Failure A can still call the provider after the patch.

The test using task_tokens=100 is not equivalent to a 66,685-token context under a 30,000 budget.

O-C01 fails if realistic context size is not checked before provider invocation.

### 6.2 Budget and cost undercount

Review this logic:

~~~python
actual_tokens=min(tokens, reservation.max_tokens)
actual_cost_minor_units=min(cost_minor_units, reservation.max_cost_minor_units)
~~~

Determine whether it permits the workflow budget to understate actual provider usage/cost and later authorize additional calls.

Do not accept a design that preserves actual counts only in model_calls while the authoritative budget ledger records smaller spend, unless the budget authority explicitly and safely accounts for the debt/overspend elsewhere.

### 6.3 Incomplete reason correctness

Verify worker_output_truncated is used only when incomplete_reason means output truncation.

Other incomplete reasons must remain distinct and correctly actionable.

### 6.4 Public diagnostic accessibility

Direct DurableModelCallAudit database access is not automatically an MCP caller contract.

Verify whether get_workflow/get acceptance context or another supported bounded API exposes:

- route/profile;
- attempt;
- token counts;
- latency;
- incomplete reason;
- no-artifact reason;
- safe next action.

O-C05 fails if diagnostics exist only in internal tables.

### 6.5 Timeout safety

The repair report says timeout alignment is not fixed.

The R6 test immediately returns success and then replays; it does not simulate a client timeout, delayed provider completion, disconnect, poll, or background reconciliation.

O-C08 fails unless actual timeout-safe recovery is implemented and tested.

### 6.6 Fail-open exception

Review any broad exception around failed-dispatch lookup.

A diagnostic database error must not silently restore dispatch_worker_proposals_v2 as a safe next action.

### 6.7 Workflow state and action vocabulary

Verify:

- whether workflow remains executing forever after terminal incomplete;
- whether replan_or_revise_task corresponds to an actual callable transition/tool;
- whether state, version, next actions, operation journal, and attempts agree.

### 6.8 Report/evidence accuracy

Verify:

- changed-file list includes all source/test/report artifacts appropriately;
- line counts and stats;
- 760-pass claim;
- focused 10-pass claim;
- no skips/xfails hidden;
- no production DB changes;
- no real provider call;
- no migration;
- exact MCP restart requirement.

---

## 7. Acceptance criteria

### O-C01

Impossible input/reservation rejected before provider call using realistic context estimation.

### O-C02

Token semantics unambiguous across task, workflow, gateway, reservation, settlement, and persistence.

### O-C03

Output truncation and other incomplete outcomes correctly typed without masking.

### O-C04

No incomplete output enters proposal artifact or acceptance evidence.

### O-C05

Durable sanitized terminal diagnostics are retrievable through supported service/MCP APIs.

### O-C06

Same-request terminal replay is stable and non-billable.

### O-C07

Attempt exhaustion is typed and provider is not recalled.

### O-C08

Client/transport timeout recovery prevents duplicate calls and supports durable reconciliation.

### O-C09

Workflow state and next actions are coherent and supported.

### O-C10

Meaningful focused/full regression and static checks pass.

### O-C11

Production-like DB remains unmodified and schema compatibility is accurate.

### O-C12

No real provider call occurs during repair or audit.

---

## 8. Verdict policy

Return ORCHESTRA_REPAIR_ACCEPTED only if all O-C01 through O-C12 pass and no critical/high issue remains.

Return ORCHESTRA_REPAIR_REJECTED_REMEDIATION_REQUIRED if any acceptance criterion is unsupported, falsely passed, or contradicted by known remaining risks.

Return ORCHESTRA_REPAIR_AUDIT_BLOCKED only when required local evidence cannot be accessed or executed without new authority. Do not use BLOCKED merely because the review is difficult.

Do not authorize commit, MCP restart, or a real probe when verdict is REJECTED or BLOCKED.

---

## 9. Required outputs

Write the independent Markdown audit to:

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/ORCHESTRA_DEEPSEEK_REPAIR_READ_ONLY_AUDIT_2026-08-03.md
~~~

Write structured evidence to:

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/ORCHESTRA_DEEPSEEK_REPAIR_READ_ONLY_AUDIT_EVIDENCE_2026-08-03.json
~~~

The Markdown report must include:

1. executive verdict;
2. starting Git state;
3. authorities and files read;
4. source/test/report diff inventory;
5. original failure evidence confirmation;
6. independently rerun test results;
7. O-C01 through O-C12 table;
8. findings by severity;
9. budget/token/cost analysis;
10. incomplete-output analysis;
11. idempotency/attempt analysis;
12. timeout/recovery analysis;
13. state/next-action analysis;
14. public diagnostic analysis;
15. report/evidence contradictions;
16. production DB and real-call safety;
17. exact remediation requirements;
18. safe-to-commit/restart/probe decisions;
19. final status.

The JSON must contain:

- repository path;
- base HEAD;
- observed changes;
- file hashes;
- test commands/exit codes/counts;
- O-C01 through O-C12 status/evidence;
- findings with severity/file/line/remediation;
- production_db_modified;
- real_provider_calls_during_audit;
- safe_to_commit;
- safe_to_restart_mcp;
- safe_for_real_probe;
- final_status.

Do not fabricate data.

---

## 10. Final response format

Return:

1. one-sentence verdict;
2. critical/high findings first;
3. O-C pass/fail summary;
4. independent test totals;
5. safe-to-commit boolean;
6. safe-to-restart boolean;
7. safe-for-real-probe boolean;
8. report and JSON absolute paths;
9. exact next action;
10. real provider calls during audit;
11. final status.

End with exactly one of:

~~~text
ORCHESTRA_REPAIR_ACCEPTED
ORCHESTRA_REPAIR_REJECTED_REMEDIATION_REQUIRED
ORCHESTRA_REPAIR_AUDIT_BLOCKED
~~~

Do not modify the repair in this review window.

