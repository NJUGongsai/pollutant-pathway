# ChatGPT Handoff — Repair Orchestra DeepSeek Live Proposal Dispatch

> Date: 2026-08-02  
> Handoff type: new-window, zero-memory engineering handoff  
> Primary target: Orchestra Live MCP bridge and DeepSeek worker integration  
> ReactionAgent status: paused before P2A implementation  
> Safety: repair Orchestra with fake/local tests first; no additional real provider call without fresh user authorization

---

## 0. Prompt for the new AI window

Read this file completely before taking action.

You are taking over an Orchestra infrastructure defect discovered while dispatching a bounded ReactionAgent P2 proposal to DeepSeek Flash. Your job is to diagnose and repair Orchestra itself.

Do not implement ReactionAgent P2 in this window. Do not modify ReactionAgent source or either preserved failed workflow. Do not make another live model/provider call unless the user explicitly authorizes one post-fix probe after local tests pass.

Required workflow:

1. Read the Orchestra skill contract and repository documentation listed below.
2. Verify the Orchestra target worktree is clean.
3. Reproduce the defects with fake/deterministic gateways and temporary databases.
4. Write RED tests for budget reservation, incomplete structured output, idempotent recovery, attempt exhaustion, timeout alignment, and diagnostic persistence.
5. Make the smallest coherent Orchestra fix.
6. Run focused tests and the full Orchestra suite.
7. Report changed files, tests, remaining risks, database compatibility, and whether a real provider probe is still required.
8. Stop for explicit authorization before any real provider call, commit, push, merge, production-database migration, dependency/network change, or destructive operation.

Do not paper over the problem by increasing token limits. The observed failure involves budget enforcement, structured-output completion, recovery semantics, timeout behavior, and loss of diagnosable output.

---

## 1. Paths and repositories

### 1.1 Orchestra skill contract

Read completely:

~~~text
/Users/frank_gong/.codex/skills/orchestra-live/SKILL.md
~~~

Important skill requirements:

- Worker models return proposals only.
- Codex remains editor, test runner, evidence submitter, and acceptance authority.
- Live dispatch may be billable.
- An uncertain in-flight dispatch must not be automatically repeated.
- orchestra_dispatch_worker_proposals_v2 is the only real worker proposal tool.
- Policy, budget, schema, and evidence errors must preserve state and report exact reason codes.
- Raw credentials, secret refs, base URLs, and arbitrary profile selection must not enter MCP requests.
- A worker response is not local verification evidence.

### 1.2 Orchestra implementation worktree

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl
~~~

Observed at handoff:

~~~text
branch: milestone-e-real-worker
HEAD: ce53690 fix: resolve migrations from MCP entrypoint
working tree: clean
~~~

Re-check this yourself before editing. If dirty, do not reset, stash, discard, or overwrite changes. Ask whether to create a separate clean worktree.

### 1.3 Orchestra CLI and database

CLI:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/.venv/bin/orchestra
~~~

Database containing the two preserved failures:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra-data/orchestra.db
~~~

Companion WAL and SHM files exist. Read current evidence through a normal read-only SQLite connection so WAL entries are included:

~~~bash
sqlite3 -readonly -json /Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra-data/orchestra.db '<QUERY>'
~~~

Do not use immutable=1 for current forensic reads. An immutable connection initially hid the relevant WAL entries and falsely appeared to show that no model call existed.

Do not modify, vacuum, migrate, checkpoint, delete, or overwrite this database during diagnosis. Use temporary databases for tests. If a schema migration is needed, first present compatibility, backup, and rollback plans and request explicit authorization.

### 1.4 ReactionAgent clean integration worktree — read-only for this repair

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra
~~~

Observed branch and commits:

~~~text
branch: codex/p2-orchestra
93a541a docs(p2a): add compact Orchestra worker context
55eab3e chore(p2): snapshot accepted ReactionAgent P1 baseline
working tree: clean
~~~

Compact P2A context used for the second real call:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/orchestra/P2A_COMPACT_CONTEXT.md
~~~

This worktree is evidence only for the Orchestra repair. Do not edit it in the repair window.

### 1.5 Original ReactionAgent worktree — dirty and protected

~~~text
/Volumes/CC/Enzyme_Agent/depending
~~~

It contains extensive pre-existing user changes. Do not reset, stash, clean, overwrite, or use it as the Orchestra repair target.

---

## 2. Executive defect summary

Two real DeepSeek proposal calls were performed through Orchestra. Both routed correctly to profile deepseek, generated substantial output, hit max_output_tokens, were persisted as model_calls.status=incomplete, and produced no live_artifact.

The surrounding dispatch operations failed with reservation_token_limit, even though that reason did not explain the actual incomplete model response. Recovery attempts produced operation_not_replayable or worker_unexpected instead of a stable recovery contract.

The first call exceeded the workflow's nominal 30,000-token budget by more than three times. Its input alone exceeded the budget, but the provider call still occurred.

The second call used a compact 6,571-token input and remained below the workflow-level 30,000-token total. It still generated exactly 11,000 output tokens, hit the output cap, and failed without an artifact. Therefore the defect is not only oversized input: structured response completion and token-limit semantics are also involved.

No usable worker proposal exists. Do not treat incomplete provider output as accepted evidence or reconstruct its content from token counts.

---

## 3. Failure A — full P2 workflow

### 3.1 Workflow identity

~~~text
workflow_id: wf-8c6ac1eccb5348f2a0f985671b684f0f
workflow version: 4
state: executing
workflow_status: promoted
plan approved: true
plan_sha256: 6231f98133096fcc97bdcfe1137cbb57fdf251770eb91a9eb92e321c76c1d948
planning_context_sha256: babff6cacc44c2e51bfad9742f35f449fa277207b0e16f421cd5cc03567733a5
execution_sha256: null
acceptance_sha256: null
Claude requested: false
Claude approved: false
~~~

Workflow budget:

~~~json
{
  "max_total_tokens": 30000,
  "max_cost_minor_units": 3000,
  "currency": "CNY",
  "max_duration_seconds": 1800,
  "max_model_calls": 8
}
~~~

Task limit for P2-W1:

~~~json
{
  "max_attempts": 1,
  "max_cost_minor_units": 3000,
  "max_revision_rounds": 0,
  "max_tokens": 30000,
  "timeout_seconds": 1500
}
~~~

### 3.2 First request

~~~text
request_id: reactionagent-p2-dispatch-20260802-v1
task_id: P2-W1
actual profile_id: deepseek
purpose: execute
model_call status: incomplete
input_tokens: 66685
output_tokens: 29000
total_tokens: 95685
incomplete_reason: max_output_tokens
latency_ms: 316581
attempt: 1
operation status: failed
operation error_code: reservation_token_limit
artifact: none
live_execution: none
~~~

The MCP client timed out at roughly 300 seconds, about 16.6 seconds before the model call completed. The provider call continued and the terminal incomplete record was later written to WAL.

Critical invariant violation:

~~~text
workflow max_total_tokens = 30,000
actual input_tokens       = 66,685
actual total_tokens       = 95,685
~~~

The provider call should have been rejected before invocation if its input/reservation could not fit the budget.

### 3.3 Same-request recovery

Repeating the exact request ID after the uncertain timeout returned:

~~~text
category: invalid_state
reason_code: operation_not_replayable
message: prior live dispatch is not available for replay
retryable: false
~~~

It returned no persisted result and no explicit recovery handle.

### 3.4 New-request recovery in the same workflow/task

~~~text
request_id: reactionagent-p2-dispatch-recovery-20260802-v2
operation status: failed
operation error_code: worker_unexpected
new model_call: none
~~~

Likely cause to verify in code: P2-W1 already consumed its single attempt, and the new request reached an attempt/idempotency path that collapsed into worker_unexpected. Treat this as a hypothesis until traced and frozen by a RED test.

---

## 4. Failure B — compact P2A workflow

### 4.1 Workflow identity

~~~text
workflow_id: wf-dd44f94e4dc24a5688712ee7a0b8e0e1
workflow version: 4
state: executing
workflow_status: promoted
plan approved: true
plan_sha256: b1eb0d3f1c2a06252009300edf82b309459b8a204f66a69da13f953605cfde4f
planning_context_sha256: bf002458e4dcdeb9ba2e35c72dcb55a0af9b4cc2dc77679f9be78cf3ef0b90b7
execution_sha256: null
acceptance_sha256: null
Claude requested: false
Claude approved: false
~~~

Workflow budget:

~~~json
{
  "max_total_tokens": 30000,
  "max_cost_minor_units": 3000,
  "currency": "CNY",
  "max_duration_seconds": 1200,
  "max_model_calls": 1
}
~~~

Task limit for P2A-W1:

~~~json
{
  "max_attempts": 1,
  "max_cost_minor_units": 3000,
  "max_revision_rounds": 0,
  "max_tokens": 12000,
  "timeout_seconds": 900
}
~~~

### 4.2 Compact dispatch

~~~text
request_id: reactionagent-p2a-dispatch-20260802-v1
task_id: P2A-W1
actual profile_id: deepseek
purpose: execute
model_call status: incomplete
input_tokens: 6571
output_tokens: 11000
total_tokens: 17571
incomplete_reason: max_output_tokens
latency_ms: 98453
attempt: 1
operation status: failed
operation error_code: reservation_token_limit
artifact: none
live_execution: none
~~~

The MCP caller received:

~~~text
category: invalid_state
reason_code: reservation_token_limit
message: live worker proposal execution failed safely
retryable: false
~~~

The compact context reduced input from 66,685 to 6,571 tokens and latency from 316.581 to 98.453 seconds, but DeepSeek still emitted until the output boundary and failed to close the required structured proposal.

Critical semantic ambiguity:

~~~text
workflow max_total_tokens = 30,000
task max_tokens           = 12,000
input + output            = 17,571
output alone              = 11,000
~~~

Determine and document whether task.limits.max_tokens means maximum output, maximum total input plus output, reservation quantity, or something else. The current behavior appears inconsistent: the gateway allowed an 11,000-token generation, then the operation failed with a reservation limit after total usage exceeded the task's 12,000 value while workflow usage remained below 30,000.

---

## 5. Read-only forensic queries

Use a normal read-only connection so WAL is visible.

### 5.1 Operations

~~~sql
SELECT
  operation_id,
  idempotency_key,
  operation_type,
  status,
  error_code,
  created_at,
  updated_at,
  substr(result_json, 1, 1000) AS result_excerpt
FROM operation_journal
WHERE idempotency_key LIKE '%reactionagent-p2%';
~~~

### 5.2 Model calls

~~~sql
SELECT
  call_id,
  workflow_id,
  task_id,
  profile_id,
  purpose,
  status,
  input_tokens,
  output_tokens,
  total_tokens,
  cost_minor_units,
  incomplete_reason,
  error_category,
  error_code,
  retryable,
  latency_ms,
  attempt,
  started_at,
  finished_at
FROM model_calls
WHERE workflow_id IN (
  'wf-8c6ac1eccb5348f2a0f985671b684f0f',
  'wf-dd44f94e4dc24a5688712ee7a0b8e0e1'
)
ORDER BY started_at;
~~~

### 5.3 Live artifacts and executions

~~~sql
SELECT *
FROM live_executions
WHERE workflow_id IN (
  'wf-8c6ac1eccb5348f2a0f985671b684f0f',
  'wf-dd44f94e4dc24a5688712ee7a0b8e0e1'
);

SELECT
  artifact_id,
  workflow_id,
  task_id,
  profile_id,
  attempt,
  summary,
  artifact_sha256,
  created_at
FROM live_artifacts
WHERE workflow_id IN (
  'wf-8c6ac1eccb5348f2a0f985671b684f0f',
  'wf-dd44f94e4dc24a5688712ee7a0b8e0e1'
);
~~~

Expected current result: no live_executions and no live_artifacts for either workflow.

Do not print secret_ref, credentials, authorization headers, provider base URLs, or raw secrets.

---

## 6. Primary code areas to inspect

Start with these files and use rg before expanding scope:

~~~text
src/orchestra/services/live_dispatch.py
src/orchestra/services/operations.py
src/orchestra/services/live_artifacts.py
src/orchestra/budget/ledger.py
src/orchestra/gateway/anthropic.py
src/orchestra/gateway/contracts.py
src/orchestra/models/runtime.py
src/orchestra/models/routing.py
src/orchestra/persistence/model_calls.py
src/orchestra/persistence/journal.py
src/orchestra/persistence/live.py
src/orchestra/domain/live.py
src/orchestra/mcp/live_tools.py
src/orchestra/mcp/live_schemas.py
src/orchestra/mcp/live_server.py
~~~

Read these design/runbook references:

~~~text
docs/superpowers/specs/2026-07-23-live-proposal-dispatch-design.md
docs/superpowers/specs/2026-07-19-codex-mcp-bridge-design.md
docs/runbooks/codex-mcp.md
docs/mcp-contract-changelog.md
~~~

Most relevant existing tests:

~~~text
tests/services/test_live_dispatch.py
tests/services/test_operations.py
tests/budget/test_ledger.py
tests/gateway/test_anthropic.py
tests/gateway/test_contracts.py
tests/persistence/test_model_calls.py
tests/persistence/test_journal.py
tests/persistence/test_live_repositories.py
tests/mcp/test_live_tools.py
tests/mcp/test_live_stdio.py
tests/mcp/test_live_schemas.py
tests/cognition/test_live_proposals.py
tests/e2e/test_codex_mcp_bridge.py
~~~

Suggested searches:

~~~bash
rg -n "reservation_token_limit|max_output_tokens|incomplete_reason|max_tokens" src tests
rg -n "operation_not_replayable|worker_unexpected|recovery_required" src tests
rg -n "live_artifact|live_execution|model_calls|operation_journal" src tests
rg -n "timeout_seconds|tools/call" src tests docs
~~~

---

## 7. Root-cause questions

Do not jump directly to a patch. Answer each question with code references and RED tests.

### 7.1 Pre-dispatch budget enforcement

1. When are repository-context tokens estimated or counted?
2. When is output capacity reserved?
3. Why was a 66,685-token input sent under a 30,000-token workflow budget?
4. Is reservation enforced before or after provider invocation?
5. Do task and workflow limits both participate in preflight?
6. Are actual provider counts reconciled atomically with the ledger?
7. Can a failed/incomplete call overspend the declared limit?

### 7.2 Meaning of max_tokens

1. Is TaskLimits.max_tokens total or output-only?
2. Is it mapped directly to provider max_tokens?
3. Why did max_tokens=12000 lead to exactly 11,000 output tokens?
4. Why was 17,571 total mapped to reservation_token_limit?
5. Should the schema split estimated input, maximum output, and maximum total/reservation?

### 7.3 Structured proposal completion

1. What exact schema must DeepSeek return?
2. Does the prompt request unbounded full patches?
3. Is the provider using JSON/structured-output mode or plain text?
4. How are malformed, truncated, refused, and semantically invalid responses distinguished?
5. Why does max-output truncation become a budget error?
6. Can the response contract be bounded to a summary, file manifest, concise patch chunks, and explicit deferrals?

### 7.4 Persistence and diagnostics

1. Why is model_call persisted while no terminal execution/failure diagnostic is exposed through workflow context?
2. Should partial output be represented by a non-acceptance diagnostic record with digest and truncation reason?
3. How can Codex inspect sanitized failure context without treating it as a proposal artifact?
4. Why does get_workflow still advertise ordinary dispatch after a non-retryable attempt?

### 7.5 Idempotency and recovery

1. Why does the same request ID return operation_not_replayable rather than the stored terminal result?
2. Why does a new request ID for an attempted task become worker_unexpected?
3. Where is max_attempts enforced and what typed error should it return?
4. What is the intended live_dispatch_recovery_required pathway?
5. Can the service distinguish never-started, in-flight, provider-completed-but-not-persisted, incomplete, and terminal-failed operations?

### 7.6 Timeout alignment

1. Why can provider/task timeout exceed MCP tools/call timeout?
2. Should live dispatch use start-and-poll semantics?
3. If synchronous, how is a margin enforced so transport outlives provider work?
4. How is an uncertain client disconnect reconciled with the durable journal?

---

## 8. Required RED tests

Use fake/deterministic gateways and temporary databases. No real DeepSeek call is required.

### 8.1 Budget preflight

1. Workflow total budget 30,000 and estimated input 66,685: reject before gateway invocation.
2. Fake-gateway call count remains zero.
3. Typed error includes estimated input, reserved output, task/workflow remaining, and stable reason code.
4. Freeze whether a preflight rejection creates no model-call row or a separate reservation record.

### 8.2 Token-limit semantics

1. Freeze the meaning of TaskLimits.max_tokens.
2. If total: input plus max output must fit before dispatch.
3. If output-only: use a separate total reservation field/check.
4. Enforce both task and workflow limits before provider invocation.
5. Accepted reservation must not later become unexplained reservation_token_limit under the same accounted bounds.

### 8.3 Incomplete max-output response

Fake gateway returns:

~~~text
status=incomplete
incomplete_reason=max_output_tokens
input_tokens=6571
output_tokens=11000
~~~

Assert:

- no proposal/acceptance artifact is created;
- terminal model-call record is persisted;
- terminal operation diagnostic is persisted;
- error is explicit, for example worker_output_truncated, unless a separate budget violation occurred;
- next actions do not encourage blind repeat;
- acceptance cannot consume the partial result.

### 8.4 Idempotent replay

1. Repeat the same request ID after terminal incomplete/failure.
2. Return the same sanitized terminal result/hash or a documented recovery result.
3. Do not invoke the gateway again.
4. Do not return operation_not_replayable when a terminal failure record exists.

### 8.5 Attempt exhaustion

1. Task with max_attempts=1 has one incomplete call.
2. New request ID returns typed attempts_exhausted/revision_required.
3. Gateway is not called.
4. Error is not worker_unexpected.

### 8.6 Uncertain client timeout

Simulate provider completion after client/transport timeout:

- operation remains discoverable;
- same request retrieves terminal state without provider re-call;
- in-flight state returns typed recovery/poll action;
- duplicate billing/model call is impossible.

### 8.7 Partial diagnostic persistence

At minimum persist:

- workflow, task, profile, attempt;
- terminal status and incomplete reason;
- token counts and latency;
- prompt/schema hashes;
- response digest when available;
- whether content was truncated;
- explicit not-an-acceptance-artifact semantics.

If partial content is stored, bound and sanitize it. Never expose secrets or chain-of-thought and never treat it as evidence. If content is not stored, MCP diagnostics must still explain why no artifact exists.

### 8.8 Workflow-summary coherence

After non-retryable incomplete/attempt-exhausted state, get_workflow must not misleadingly advertise a normal first dispatch as the only next action.

---

## 9. Repair acceptance criteria

### O-C01 — No preflight overspend

A request whose estimated input plus reserved output cannot fit task and workflow limits is rejected before provider invocation. Fake-gateway call count is zero.

### O-C02 — Unambiguous token semantics

Task/output/total token fields have one documented meaning across MCP schema, domain model, gateway mapping, budget ledger, persistence, and tests.

### O-C03 — Typed incomplete response

max_output_tokens remains an explicit incomplete worker outcome and is not mislabeled as a reservation failure unless an independent budget violation occurred.

### O-C04 — No false artifact

Truncated, malformed, or incomplete worker output never becomes a proposal artifact or acceptance evidence.

### O-C05 — Durable diagnostics

The caller can retrieve route, attempt, token usage, latency, incomplete reason, and the reason no artifact exists.

### O-C06 — Idempotent terminal replay

Repeating the same request ID after terminal failure returns/reconstructs the same result without another model call.

### O-C07 — Typed attempt exhaustion

A new request against a task with no attempts remaining returns a stable typed error/action, not worker_unexpected.

### O-C08 — Timeout-safe recovery

A client timeout cannot cause an automatic duplicate call. Durable state supports polling/recovery after provider completion.

### O-C09 — Coherent next actions

Workflow summary and next actions reflect incomplete, failed, or attempts-exhausted state and do not recommend unsafe redispatch.

### O-C10 — Regression safety

Focused budget/gateway/persistence/service/MCP tests and the full Orchestra suite pass. Existing fake dispatch, planning, acceptance, evidence, and non-Claude routing behavior remain intact.

### O-C11 — Database safety

No destructive migration of the current database. Any schema change has an Alembic migration, compatibility analysis, backup/rollback instructions, and explicit approval before production DB application.

### O-C12 — No unauthorized live call

All repair verification uses fake/local gateways. A real DeepSeek probe occurs only after local acceptance and explicit user authorization.

---

## 10. Suggested implementation directions — not pre-decided patches

Evaluate rather than force-fit these ideas:

1. Add a pre-dispatch reservation object with estimated input, maximum output, total reserved, task remaining, and workflow remaining.
2. Separate provider output cap from total task/workflow budget instead of overloading max_tokens.
3. Reject impossible requests before routing/gateway invocation.
4. Persist operation-level terminal diagnostics for every started live dispatch, including incomplete outcomes.
5. Map gateway terminal states to typed service reasons: refused, incomplete/max-output, malformed response, provider failure, budget preflight rejection, usage-reconciliation violation, and attempts exhausted.
6. Make terminal operation failures replayable by request ID.
7. Make attempt exhaustion an explicit domain decision.
8. Align transport and provider timeouts or use start/poll semantics.
9. Bound the worker proposal schema so a model can finish without tens of thousands of patch tokens.
10. Preserve the invariant that incomplete content is never an accepted artifact.

Do not merely raise output limits. The first call generated 29,000 output tokens and still did not complete.

---

## 11. Verification expectations

Read pyproject.toml, README, runbook, and repository-specific instructions before selecting commands. Use the existing virtual environment; do not install dependencies without approval.

Likely focused groups:

~~~text
tests/budget/test_ledger.py
tests/gateway/test_anthropic.py
tests/gateway/test_contracts.py
tests/services/test_live_dispatch.py
tests/services/test_operations.py
tests/persistence/test_model_calls.py
tests/persistence/test_journal.py
tests/persistence/test_live_repositories.py
tests/mcp/test_live_tools.py
tests/mcp/test_live_stdio.py
tests/cognition/test_live_proposals.py
tests/e2e/test_codex_mcp_bridge.py
~~~

Also run the full test suite, configured static/type checks, and git diff --check.

Report exact commands, exit codes, passed/failed/skipped counts, and any check that could not run. Model assertions are not evidence.

---

## 12. Safety and scope boundaries

### Allowed in the repair window

- Read Orchestra source, docs, tests, and the two workflows through read-only queries.
- Write RED tests and the minimal repair in the authorized Orchestra worktree.
- Use fake gateways and temporary databases.
- Run local Orchestra tests and non-network checks.

### Requires explicit user authorization

- Any real DeepSeek or other provider call.
- Modifying/migrating the production-like orchestra.db.
- Installing/upgrading dependencies or accessing the network.
- Commit, push, merge, worktree deletion, or PR creation.
- Editing ReactionAgent files.
- Changing provider profiles, endpoints, or credential configuration.
- Exposing base URLs, secret refs, API keys, or authorization material.

### Forbidden

- Delete or rewrite the preserved failed workflows.
- Reset, stash, discard, or overwrite user work.
- Describe cost_minor_units=0 as proof the calls were free.
- Treat truncated DeepSeek output as a valid proposal.
- Fake an artifact, execution hash, evidence bundle, or acceptance.
- Raise token limits to conceal budget defects.

---

## 13. Cost and provider-call facts

Two real DeepSeek calls are persisted:

~~~text
Call A: 66,685 input + 29,000 output = 95,685 tokens
Call B:  6,571 input + 11,000 output = 17,571 tokens
Total:  73,256 input + 40,000 output = 113,256 tokens
~~~

Both rows have cost_minor_units=0, but profile pricing was unavailable. Do not infer zero provider billing.

The recovery operation reactionagent-p2-dispatch-recovery-20260802-v2 created no additional model call.

---

## 14. Required handback from the repair window

Provide all of the following before ReactionAgent work resumes:

1. Root cause with exact file/function references.
2. Final token-limit semantics.
3. Incomplete/partial-output persistence decision.
4. Same-request replay and new-request attempt-exhaustion decision.
5. Changed-file list.
6. RED tests and what each reproduced.
7. GREEN implementation summary.
8. Focused and full test results with exact counts.
9. Database migration/compatibility assessment.
10. Whether MCP registration/restart is needed.
11. Minimal post-fix real probe design and expected token ceiling.
12. Explicit statement that no real provider call was made unless separately authorized.
13. Absolute path to the final repair report.
14. Final status: READY_FOR_CHATGPT_ORCHESTRA_REVIEW, BLOCKED, or FAILED.

Do not tell ReactionAgent to resume merely because unit tests pass. State exactly how the fixed MCP server is loaded/restarted and how one post-fix probe can avoid previous overspend.

---

## 15. ReactionAgent continuation point

ReactionAgent P1 is accepted. P2A implementation has not started. Its compact scope is frozen at:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/orchestra/P2A_COMPACT_CONTEXT.md
~~~

After Orchestra repair and one separately authorized successful DeepSeek probe, the ReactionAgent development window should:

1. Retrieve a complete persisted worker artifact.
2. Verify actual route is deepseek.
3. Review every proposal part against compact context and repository facts.
4. Explicitly accept, correct, or reject it.
5. Apply changes through Codex's local editing boundary.
6. Run P2A and complete P0/P1 verification.
7. Submit only local evidence to Orchestra.
8. Make final acceptance decision.

Until then, both failed workflows remain audit evidence and P2A remains unimplemented.

---

## 16. Final handoff statement

The defect must be repaired in Orchestra rather than worked around in ReactionAgent:

~~~text
pre-dispatch budget enforcement allowed impossible or ambiguous reservations;
DeepSeek output reached the cap without completing the proposal;
incomplete output was mapped to a misleading reservation failure;
no usable or sufficiently diagnostic artifact was exposed;
idempotent recovery and attempt exhaustion returned unstable generic errors;
workflow next actions remained misleading after non-retryable failure.
~~~

Repair these contracts with fake/local tests first. Preserve both workflows and all user work. Require explicit approval before any real provider probe.

