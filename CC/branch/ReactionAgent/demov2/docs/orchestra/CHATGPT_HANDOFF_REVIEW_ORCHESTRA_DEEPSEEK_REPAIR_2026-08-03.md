# ChatGPT Handoff — Independent Read-Only Review of Orchestra DeepSeek Live-Dispatch Repair

> Date: 2026-08-03  
> Handoff type: new-window, zero-memory independent audit  
> Audit target: uncommitted Orchestra repair for DeepSeek live proposal dispatch  
> Audit mode: read-only review and independent local verification  
> Production code edits: forbidden in the review window  
> Real provider calls: forbidden  
> Expected output: evidence-backed ACCEPT / REJECT-REMEDIATION / BLOCKED verdict

---

## 0. Mission for the new review window

You are the independent reviewer of an Orchestra repair produced in another AI window.

Do not continue implementing the repair. Do not assume the repair report is correct. Do not promote a claim because tests are green or because a JSON file says PASS.

Your job is to:

1. read the original failure evidence and repair requirements;
2. inspect the exact uncommitted repair diff;
3. independently verify the repair report and structured evidence;
4. rerun focused and full local tests without network access;
5. test the scientific/engineering meaning of O-C01 through O-C12;
6. identify false-positive tests, missing failure-path coverage, budget/accounting errors, recovery gaps, or report contradictions;
7. decide whether the repair is safe enough to commit/restart/probe;
8. write an independent audit report and JSON verdict outside the Orchestra source worktree;
9. make no real model/provider call.

The repair worktree is expected to be dirty because it contains the proposed repair. Preserve it exactly. Do not reset, stash, clean, discard, format broadly, or overwrite any file.

---

## 1. Mandatory authorities to read completely

### 1.1 Orchestra skill contract

~~~text
/Users/frank_gong/.codex/skills/orchestra-live/SKILL.md
~~~

The audit must enforce these skill principles:

- workers return proposals only;
- Codex is local editor/verifier/acceptance authority;
- live calls may be billable;
- uncertain in-flight calls are never automatically repeated;
- policy/budget/schema/evidence failures preserve state and exact reason codes;
- model output is not local verification evidence;
- no fake artifact, evidence, acceptance, or workflow result;
- cost_minor_units=0 is not proof of a free provider call;
- no Git commit/push/merge/destructive mutation is implied by review.

### 1.2 Original failure handoff

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_HANDOFF_ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_2026-08-02.md
~~~

### 1.3 Original repair prompt

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_PROMPT_REPAIR_ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_2026-08-02.md
~~~

### 1.4 Repair submission report

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_REPORT_2026-08-02.md
~~~

### 1.5 Repair structured evidence

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_EVIDENCE_2026-08-02.json
~~~

Read every file completely. If any is missing or unreadable, do not infer its contents; record a blocker or evidence defect.

---

## 2. Target repository and expected state

Orchestra repair worktree:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl
~~~

Recorded base:

~~~text
branch: milestone-e-real-worker
base HEAD: ce53690cf6a806594871580aa941021cb0461466
base subject: fix: resolve migrations from MCP entrypoint
~~~

Observed proposed changes at handoff creation:

~~~text
M  src/orchestra/cognition/engine.py
M  src/orchestra/services/external_workflows.py
M  src/orchestra/services/live_dispatch.py
?? tests/services/test_live_dispatch_repair.py
?? docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_REPORT_2026-08-02.md
?? docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_EVIDENCE_2026-08-02.json
~~~

The dirty state is expected evidence. Do not stop merely because these files are modified/untracked. Stop only if additional unexplained changes exist, and report them separately.

Before review:

1. confirm Git root;
2. confirm branch and HEAD;
3. capture full short status including untracked files;
4. capture diff stat and numstat;
5. hash the two repair reports;
6. inventory applicable AGENTS.md instructions;
7. do not stage or commit anything.

---

## 3. Original production failures

Two real calls were previously persisted. They are the reason for this repair.

### Failure A — full P2 context

~~~text
workflow_id: wf-8c6ac1eccb5348f2a0f985671b684f0f
request_id: reactionagent-p2-dispatch-20260802-v1
profile_id: deepseek
status: incomplete
input_tokens: 66,685
output_tokens: 29,000
total_tokens: 95,685
incomplete_reason: max_output_tokens
latency_ms: 316,581
workflow max_total_tokens: 30,000
operation error: reservation_token_limit
artifact: none
live_execution: none
~~~

This proves the old code allowed an input larger than the entire workflow token budget to reach the provider.

### Failure B — compact P2A context

~~~text
workflow_id: wf-dd44f94e4dc24a5688712ee7a0b8e0e1
request_id: reactionagent-p2a-dispatch-20260802-v1
profile_id: deepseek
status: incomplete
input_tokens: 6,571
output_tokens: 11,000
total_tokens: 17,571
incomplete_reason: max_output_tokens
latency_ms: 98,453
workflow max_total_tokens: 30,000
task max_tokens: 12,000
operation error: reservation_token_limit
artifact: none
live_execution: none
~~~

A recovery request in Failure A created no second model call and failed with worker_unexpected.

The production-like database containing these records is read-only audit evidence:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra-data/orchestra.db
~~~

Use normal sqlite3 -readonly access so WAL data is visible. Do not use immutable=1, migrate, checkpoint, vacuum, overwrite, or otherwise mutate this database.

---

## 4. Repair claims to verify

The repair submission claims:

~~~text
status: READY_FOR_CHATGPT_ORCHESTRA_REVIEW
focused tests: 10 passed
full suite: 760 passed
ruff check: pass
ruff format --check: pass
git diff --check: pass
database migration: not required
MCP restart: required
real provider calls during repair: zero
~~~

Claimed code changes:

1. Add _settle_actual_usage for incomplete/failed calls.
2. Use worker_output_truncated for incomplete output.
3. Replay failed operation error_code instead of operation_not_replayable.
4. Pre-check task attempt exhaustion.
5. Return recovery/replan next actions.
6. Detect failed/incomplete model calls in get_workflow.
7. Avoid suggesting blind redispatch after failure.

Do not accept these claims until independently verified.

---

## 5. Preliminary audit risk flags

These are not the final verdict. They are high-priority questions the reviewer must resolve with code and tests.

### RF-01 — O-C01 appears materially unsupported

Original O-C01 requires an impossible request to be rejected before provider invocation based on estimated input plus reserved output.

The repair report itself says:

~~~text
worker_estimated_input_tokens is still a fixed constant
actual input size is not estimated at dispatch time
future preflight should estimate input from context bytes
~~~

The new R1 test sets task_tokens=100, so the existing fixed 1,000-token estimate makes the partition trivially infeasible. It does not reproduce:

~~~text
actual input = 66,685
workflow budget = 30,000
task budget = 30,000
~~~

Review whether the original production failure would still reach the provider after the repair. If yes, O-C01 cannot PASS.

### RF-02 — O-C02 token semantics may remain internally inconsistent

The repair continues to use:

~~~text
TaskLimits.max_tokens as total per-attempt budget
provider max_tokens as max_tokens minus a fixed 1,000 estimate
~~~

Without actual input estimation, provider output capacity can still be far too large. Verify whether the same field remains overloaded and whether task/workflow preflight actually enforces input plus output.

### RF-03 — Actual usage may be deliberately undercounted

The proposed _settle_actual_usage uses:

~~~python
actual_tokens=min(tokens, reservation.max_tokens)
actual_cost_minor_units=min(cost_minor_units, reservation.max_cost_minor_units)
~~~

This avoids masking worker_output_truncated but may cause the budget ledger to understate real provider usage and real cost.

The repair report explicitly acknowledges:

~~~text
budget may not reflect true cost
~~~

Audit whether this violates budget authority, max-total enforcement, cost accounting, subsequent-call safety, and the skill contract. Preserving actual numbers only in model_calls may not be sufficient if the ledger still permits later calls based on understated spend.

### RF-04 — worker_output_truncated may be too broad

The code appears to map every ModelCallStatus.INCOMPLETE to worker_output_truncated, regardless of incomplete_reason.

Verify behavior for:

- max_output_tokens;
- provider timeout;
- content filtering;
- tool-use truncation;
- malformed/partial structured response;
- unknown incomplete reason.

The public reason must not falsely call all incomplete outcomes output truncation.

### RF-05 — O-C05 may not be caller-retrievable

The repair test reads DurableModelCallAudit directly from the database. The public get_workflow view appears to change next_actions but does not expose the required sanitized diagnostics:

- route/profile;
- attempt;
- input/output/total tokens;
- latency;
- incomplete reason;
- prompt/schema hashes or digest;
- why no artifact exists.

Determine whether O-C05 requires an MCP-accessible bounded diagnostic, not only internal DB persistence.

### RF-06 — O-C08 timeout safety is not genuinely tested or fixed

The R6 test is named client timeout but the fake gateway immediately returns a successful response. No client disconnect, transport timeout, long-running provider, background completion, poll, or recovery state is simulated.

The repair report explicitly says:

~~~text
timeout alignment not fixed
provider timeout can still exceed MCP transport timeout
start-and-poll is not implemented
~~~

O-C08 cannot be accepted solely because successful same-request replay was already idempotent.

### RF-07 — Fail-open broad exception

external_workflows.py appears to use:

~~~python
try:
    query failed/incomplete model calls
except Exception:
    pass
~~~

If the diagnostic query fails, get_workflow may silently fall back to suggesting dispatch. This is a fail-open behavior on a duplicate-billing safety boundary.

Review whether it must fail closed or surface a typed system diagnostic.

### RF-08 — Workflow state may remain semantically stale

The workflow can remain state=executing/version=4 with no execution artifact after a non-retryable incomplete call. The patch only changes next_actions.

Review whether durable workflow/decision state should transition to revising, replanning, failed_system, paused_budget, or a recovery state rather than remaining executing indefinitely.

Also verify whether replan_or_revise_task is a real registered action/tool or only an invented string.

### RF-09 — Attempt counting semantics

The pre-check counts all execute-purpose model calls for a task. Review:

- whether started but abandoned calls count;
- whether refused/failed/incomplete/completed all consume attempts;
- whether retries from the engine are distinguished;
- multi-task workflows;
- revision rounds;
- plan replacement/version changes;
- whether task_contexts subsets are handled correctly;
- whether counting all historical calls can permanently block legitimate revised work.

### RF-10 — Terminal replay payload remains thin

Failed operation result_json remains null. Same-request replay returns stored error_code but not necessarily the original bounded terminal diagnostic.

Review whether idempotency requires a stable structured result/hash, not merely the same reason code.

### RF-11 — Report/evidence coherence

At handoff creation:

- tests/services/test_live_dispatch_repair.py contains 784 lines;
- the report's changed-file section described a different size/stat presentation;
- git diff --stat does not include untracked files unless separately handled;
- JSON changed_files excludes the Markdown/JSON report artifacts themselves.

Verify every reported path, count, command, exit code, and changed-file list against current state.

### RF-12 — Test independence and false positives

The repair test imports the private _stack helper from another test module and creates local git repositories. Review:

- isolation and determinism;
- whether tests pass only because of existing implementation assumptions;
- whether they assert exact required behavior or allow old behavior through broad alternative reason-code sets;
- whether test comments claim scenarios that are not simulated;
- whether R1 was actually RED before production changes;
- whether the tests meaningfully veto the known production failures.

### RF-13 — No real-call and production-DB claims

Independently verify:

- repair test transports are fake;
- no network calls are reachable;
- no new model_calls appeared after repair start;
- production-like DB/WAL timestamps and records are consistent with read-only use;
- no migration was executed;
- no ReactionAgent file was changed by the repair window.

Do not print secrets or provider configuration.

---

## 6. Original acceptance criteria O-C01 through O-C12

The independent reviewer must decide each criterion based on the original meaning, not the repair report's self-assigned PASS.

### O-C01 — No preflight overspend

A request whose actual/estimated repository input plus reserved output cannot fit task and workflow limits is rejected before provider invocation. Fake gateway count is zero in a realistic Failure-A reproduction.

### O-C02 — Unambiguous token semantics

Task total, provider output cap, workflow total, reservation, and actual usage have one coherent documented meaning across MCP, domain, gateway, ledger, persistence, and tests.

### O-C03 — Typed incomplete response

max_output_tokens remains an explicit incomplete outcome and is not masked by an unrelated budget error. Other incomplete reasons remain correctly typed.

### O-C04 — No false artifact

Truncated, malformed, refused, and incomplete output never becomes proposal artifact or acceptance evidence.

### O-C05 — Durable bounded diagnostics

The caller can retrieve sanitized route, attempt, usage, latency, incomplete reason, and no-artifact reason through supported service/MCP context, without reading raw tables or exposing secrets.

### O-C06 — Idempotent terminal replay

Same request after terminal failure returns the same bounded terminal result without another model call.

### O-C07 — Typed attempt exhaustion

New request with no attempts remaining fails before provider invocation with a stable attempts-exhausted/revision action.

### O-C08 — Timeout-safe recovery

A real client/transport timeout cannot produce an unsafe duplicate provider call; durable state supports recovery/polling after provider completion.

### O-C09 — Workflow state and next-action coherence

Workflow state and next actions accurately represent failure/recovery/attempt exhaustion and never encourage blind redispatch.

### O-C10 — Regression safety

Focused and full suites, lint, format check, and diff check pass; tests are meaningful and not false positives.

### O-C11 — Database safety

No destructive migration or mutation of the production-like DB; compatibility is accurate.

### O-C12 — No unauthorized live call

Repair and audit use only fake/local providers. Real-call count during repair and review is zero.

A criterion cannot PASS if its own report lists the required behavior as a remaining unfixed risk.

---

## 7. Required independent verification

### 7.1 Read-only Git/diff audit

Capture:

~~~text
git status --short --branch
git diff --stat
git diff --numstat
git diff --check
git diff for each modified tracked source
full contents of every untracked test/report/evidence file
~~~

Do not stage files.

### 7.2 Source trace

Trace exact behavior from:

~~~text
src/orchestra/services/live_dispatch.py
src/orchestra/cognition/engine.py
src/orchestra/budget/ledger.py
src/orchestra/gateway/anthropic.py
src/orchestra/gateway/contracts.py
src/orchestra/services/external_workflows.py
src/orchestra/services/operations.py
src/orchestra/persistence/model_calls.py
src/orchestra/persistence/journal.py
src/orchestra/persistence/live.py
src/orchestra/mcp/live_tools.py
src/orchestra/mcp/live_schemas.py
~~~

Review private API access, broad exception handling, state transitions, error mapping, accounting, idempotency, concurrency, and retry behavior.

### 7.3 Independent test rerun

Use the existing environment without installing dependencies or accessing the network.

Prefer the already-created project virtual environment. Record exact interpreter and tool versions.

Rerun:

~~~text
focused repair tests
all service live-dispatch tests
budget tests
gateway tests
persistence model-call/journal/live tests
MCP live-tool and stdio tests
cognition live-proposal tests
full test suite
ruff check
ruff format --check
git diff --check
~~~

Report exact commands, exit codes, pass/fail/error/skip/xfail/xpass counts, and durations.

### 7.4 Adversarial audit checks

Without modifying the target worktree, use temporary files/databases or a temporary copy to verify:

1. Failure A scale: context/input larger than workflow budget with nominal task budget 30,000.
2. Incomplete reason other than max output.
3. Actual usage above reservation and its effect on remaining budget.
4. Actual cost above reservation.
5. Diagnostic-query failure in get_workflow.
6. Same request after failed operation with null result_json.
7. New request after attempts exhausted.
8. Multiple tasks where only one is exhausted.
9. Revised plan/task identity after a prior incomplete call.
10. A simulated transport/client timeout rather than immediate success.
11. Whether replan_or_revise_task is a callable/recognized next action.
12. Whether workflow remains stuck in executing.
13. Public MCP response diagnostic content.
14. No artifact/evidence leakage from incomplete response.

Do not perform a real provider call.

---

## 8. Audit verdict rules

### ACCEPT only if

- every O-C01 through O-C12 is independently supported;
- no critical/high issue remains;
- claimed tests are reproducible;
- budget ledger does not understate actual usage/cost in a way that permits overspend;
- realistic preflight prevents Failure A before provider call;
- timeout recovery is actually implemented and tested;
- bounded diagnostics are caller-accessible;
- state/next-actions are coherent;
- no report/evidence contradiction remains;
- no real provider probe is required to establish basic correctness.

### REJECT — remediation required if

- one or more criteria are falsely marked PASS;
- a known production failure can still occur;
- tests do not reproduce their claimed scenario;
- actual usage/cost can be undercounted;
- timeout safety remains unimplemented;
- public diagnostics are missing;
- broad fail-open behavior can recommend unsafe redispatch;
- workflow remains in an incoherent state;
- evidence/report claims are materially inaccurate.

### BLOCKED only if

The reviewer cannot run required local checks because of missing existing tools, inaccessible files, or an external condition that cannot be resolved without new authorization. Difficulty or a large diff is not a blocker.

---

## 9. Review safety boundary

The review window may:

- read all listed sources and reports;
- query the production-like DB read-only;
- run existing tests and offline checks;
- create temporary audit scripts/tests outside the target worktree;
- write only the independent audit report and JSON evidence to the output paths below.

The review window may not:

- edit Orchestra production source or its repair tests;
- fix findings;
- modify the production-like DB;
- run a migration;
- restart/re-register MCP;
- call DeepSeek or any provider;
- install dependencies or access the network;
- stage, commit, push, merge, clean, reset, or stash;
- edit ReactionAgent implementation;
- overwrite the repair report/evidence.

If remediation is needed, describe it precisely for a separate implementation window.

---

## 10. Required audit outputs

Write the independent Markdown report to:

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/ORCHESTRA_DEEPSEEK_REPAIR_READ_ONLY_AUDIT_2026-08-03.md
~~~

Write structured evidence to:

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/ORCHESTRA_DEEPSEEK_REPAIR_READ_ONLY_AUDIT_EVIDENCE_2026-08-03.json
~~~

The report must contain:

1. executive verdict;
2. reviewed Git state;
3. files and authorities read;
4. repair diff summary;
5. independent test results;
6. O-C01 through O-C12 verdict table;
7. findings ordered by severity with file/line references;
8. report-versus-repository contradictions;
9. budget/token/cost accounting analysis;
10. incomplete-output analysis;
11. idempotency/recovery/attempt analysis;
12. timeout analysis;
13. workflow-state/next-action analysis;
14. public diagnostic/MCP analysis;
15. DB and real-call safety verification;
16. exact remediation requirements;
17. whether commit/restart/real probe is safe;
18. final audit status.

The JSON must include:

- repository and base HEAD;
- observed changed files;
- report/evidence hashes;
- test commands and exit codes;
- exact counts;
- O-C01 through O-C12 statuses and evidence;
- findings with severity, file, line, criterion, and remediation;
- production DB modified boolean;
- real provider calls during audit;
- safe_to_commit boolean;
- safe_to_restart_mcp boolean;
- safe_for_real_probe boolean;
- final status.

Do not fabricate a line number, hash, test count, or command result.

---

## 11. Allowed final statuses

End the report and final response with exactly one:

~~~text
ORCHESTRA_REPAIR_ACCEPTED
ORCHESTRA_REPAIR_REJECTED_REMEDIATION_REQUIRED
ORCHESTRA_REPAIR_AUDIT_BLOCKED
~~~

Do not use ACCEPTED if any O-C criterion is unsupported or contradicted by the repair report's own remaining-risks section.

---

## 12. Current continuation rule

Until the independent review returns ORCHESTRA_REPAIR_ACCEPTED:

- do not commit the repair;
- do not restart MCP with the repair;
- do not run the proposed real post-fix probe;
- do not resume ReactionAgent DeepSeek dispatch;
- preserve both failed workflows and the dirty repair worktree.

If rejected, produce a separate remediation prompt from the audit findings. Do not repair in the audit window.

