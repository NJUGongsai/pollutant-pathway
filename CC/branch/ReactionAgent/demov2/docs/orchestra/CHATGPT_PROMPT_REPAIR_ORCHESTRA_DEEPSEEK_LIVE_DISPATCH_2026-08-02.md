# ChatGPT Prompt — Repair Orchestra DeepSeek Live Dispatch Safely

> Intended recipient: a fresh AI coding-agent window with no prior conversation memory  
> Target repository: Orchestra  
> Task type: diagnose, implement, test, and report a local infrastructure repair  
> Real provider calls: forbidden unless separately authorized after all local tests pass  
> ReactionAgent implementation: out of scope

---

## 1. Mandatory first action

Read the following handoff completely before inspecting or modifying code:

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_HANDOFF_ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_2026-08-02.md
~~~

Also read the Orchestra skill contract completely:

~~~text
/Users/frank_gong/.codex/skills/orchestra-live/SKILL.md
~~~

The handoff contains the authoritative failure evidence, workflow IDs, token counts, WAL caveat, forensic SQL, source-file map, required RED tests, acceptance criteria, and safety constraints.

Do not summarize those files from memory. Read them directly and use their exact facts.

---

## 2. Objective

Repair Orchestra's real worker proposal dispatch so that all of the following become true:

1. A request that cannot fit task and workflow token limits is rejected before any provider call.
2. Token-limit fields have unambiguous, documented semantics.
3. A provider response truncated by max output is represented as an explicit incomplete worker outcome, not mislabeled as a generic reservation failure.
4. Truncated, malformed, refused, or incomplete output never becomes a proposal artifact or acceptance evidence.
5. Sanitized terminal diagnostics remain retrievable even when no proposal artifact exists.
6. Repeating the same request ID after a terminal failure is idempotent and never calls the provider again.
7. A new request for a task with no remaining attempts returns a typed attempts-exhausted/revision-required result instead of worker_unexpected.
8. A client/MCP timeout cannot cause an unsafe duplicate provider call.
9. Workflow next actions reflect incomplete, failed, recovery-required, and attempts-exhausted states coherently.
10. All behavior is frozen by deterministic local tests using fake gateways and temporary databases.
11. Existing planning, approval, fake dispatch, real-worker routing, evidence, and acceptance contracts continue to pass.
12. No live provider call is made during the repair.

Do not solve this by merely increasing token limits.

---

## 3. Target worktree and protected data

Primary Orchestra worktree:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl
~~~

Expected starting state recorded in the handoff:

~~~text
branch: milestone-e-real-worker
HEAD: ce53690
working tree: clean
~~~

Before editing:

1. run a read-only status check;
2. confirm the resolved Git root;
3. confirm current branch and HEAD;
4. read any AGENTS.md or repository instructions;
5. read pyproject.toml, README, live-dispatch design, and MCP runbook;
6. inspect the existing test commands and virtual environment.

If the worktree is dirty:

- stop;
- show the exact changed-file list;
- do not reset, stash, clean, discard, or overwrite;
- ask the user whether to create a separate clean worktree.

Protected production-like database:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra-data/orchestra.db
~~~

During diagnosis it is read-only evidence. Do not:

- modify it;
- run migrations against it;
- checkpoint or vacuum it;
- delete or replace WAL/SHM files;
- rewrite either preserved failed workflow.

Use normal read-only SQLite access so WAL entries are included. Do not use immutable=1 for current forensic reads.

Use temporary databases for all RED/GREEN tests.

Protected ReactionAgent paths:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra
/Volumes/CC/Enzyme_Agent/depending
~~~

Do not edit either ReactionAgent worktree in this task.

---

## 4. Authorization boundary

This prompt authorizes local Orchestra source/test changes needed to repair the diagnosed defect and local non-network verification.

This prompt does not authorize:

- a real DeepSeek call;
- any other real model/provider call;
- network access;
- dependency installation or upgrade;
- changing model endpoints, profiles, credentials, secret refs, or base URLs;
- modifying or migrating the existing orchestra.db;
- commit;
- push;
- merge;
- PR creation;
- deleting a worktree;
- destructive Git operations;
- modifying ReactionAgent;
- changing the preserved workflow evidence.

If any of those becomes necessary, stop and request explicit authorization.

Never print or copy API keys, authorization headers, secret refs, provider base URLs, or sensitive configuration into reports, patches, or test output.

---

## 5. Required investigation sequence

### Phase A — Read-only evidence verification

Using the handoff's normal read-only SQL:

1. confirm both workflow records;
2. confirm the two DeepSeek model calls;
3. confirm input/output/total tokens and latency;
4. confirm both calls ended incomplete with max_output_tokens;
5. confirm surrounding operations failed with reservation_token_limit;
6. confirm no live_artifact and no live_execution exists;
7. confirm the recovery operation created no additional model call;
8. confirm cost_minor_units=0 is only missing pricing metadata, not proof of a free call.

Do not write to the database while verifying.

### Phase B — Trace the real code path

Trace, with exact file/function references:

~~~text
MCP tool
→ live dispatch service
→ operation journal/idempotency
→ task-attempt calculation
→ route selection
→ repository context assembly
→ token estimate/reservation
→ model-call persistence
→ gateway request and response parsing
→ actual-usage reconciliation
→ artifact persistence
→ workflow state/next-actions serialization
~~~

At minimum inspect:

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

Use rg before expanding scope.

### Phase C — Root-cause report before implementation

Before editing production code, write a concise root-cause section in the repair worklog covering:

1. why a 66,685-token input passed a 30,000-token workflow budget;
2. exact intended and actual meanings of TaskLimits.max_tokens;
3. why max_output_tokens became reservation_token_limit;
4. why incomplete output produced no retrievable terminal diagnostic through MCP;
5. why same-request replay returned operation_not_replayable;
6. why new-request recovery became worker_unexpected;
7. how max_attempts was applied;
8. why a 316.581-second provider call outlived the approximately 300-second MCP wait;
9. why get_workflow continued to advertise normal dispatch after a non-retryable failed attempt.

If a conclusion is not yet proven, mark it as a hypothesis and identify the RED test that will decide it.

---

## 6. RED-first requirements

Do not modify production behavior until the corresponding RED tests fail for the expected reason.

### R1 — Impossible input rejected before gateway

Scenario:

~~~text
workflow max total = 30,000
estimated input    = 66,685
~~~

Required assertions:

- dispatch is rejected before provider/gateway invocation;
- fake-gateway call count is zero;
- no billable model call is started;
- stable error contains sanitized estimated/reserved/remaining counts;
- error is categorized as budget preflight rejection.

### R2 — Explicit token semantics

Freeze one coherent contract.

Preferred direction:

- max_output_tokens: provider generation cap;
- max_total_tokens: task input plus output ceiling;
- workflow max_total_tokens: aggregate workflow ceiling;
- reserved_total_tokens: pre-call reservation derived from estimated input plus allowed output.

If retaining current field names, document and enforce one equivalent meaning everywhere.

Assert consistency across:

- MCP schema;
- domain models;
- plan validation;
- gateway request;
- budget ledger;
- persisted model-call usage;
- error serialization;
- documentation.

### R3 — Incomplete max-output response

Fake gateway returns:

~~~text
status=incomplete
incomplete_reason=max_output_tokens
input_tokens=6571
output_tokens=11000
~~~

Required assertions:

- model-call terminal status is persisted;
- no proposal artifact is created;
- no acceptance evidence is created;
- operation terminal diagnostic is persisted;
- public error explicitly describes output truncation;
- it is not reservation_token_limit unless a separate budget invariant genuinely failed;
- workflow next actions require recovery/revision/replan, not blind redispatch.

### R4 — Terminal same-request replay

After R3, call dispatch again with the same request ID.

Assert:

- gateway call count remains unchanged;
- the same terminal result or stable recovery record is returned;
- hashes/reason code remain stable;
- operation_not_replayable is not returned for a persisted terminal failure.

### R5 — Attempt exhaustion

A task with max_attempts=1 already has one incomplete call. Use a new dispatch request ID.

Assert:

- provider is not called;
- typed attempts_exhausted or revision_required is returned;
- worker_unexpected is not returned;
- next action points to revision/replan/user decision.

### R6 — Client timeout with provider completion

Simulate provider completion after client/transport timeout.

Assert:

- durable in-flight/terminal operation is discoverable;
- same request retrieves/polls without duplicate call;
- no second provider charge is possible;
- final state is reconciled after provider completion;
- transport timeout does not destroy recovery metadata.

### R7 — Diagnostic persistence without false artifact

Freeze a safe diagnostic model containing at least:

- workflow ID;
- task ID;
- profile ID;
- attempt;
- terminal model-call status;
- incomplete reason;
- token counts;
- latency;
- prompt/schema hashes;
- response digest if safely available;
- truncated flag;
- explicit not-an-acceptance-artifact semantics.

If partial content is persisted:

- bound its size;
- sanitize it;
- do not expose chain-of-thought or secrets;
- never make it eligible for acceptance.

If partial content is not persisted, public diagnostics must still explain why no proposal exists.

### R8 — Workflow next-action coherence

For each state:

- preflight budget rejected;
- provider in flight;
- provider incomplete;
- provider failed;
- attempts exhausted;
- recovery required;
- complete artifact available;

assert that get_workflow returns coherent next actions and does not recommend unsafe blind redispatch.

### R9 — Actual-usage reconciliation

When preflight reservation succeeds but provider reports actual usage:

- reconcile atomically;
- preserve actual token usage on incomplete/failure;
- never silently exceed task/workflow budget;
- distinguish provider reporting variance from a preflight design error;
- use a specific error if actual usage violates reservation.

### R10 — No regression

Existing fake dispatch, planning approval, live approval, route selection, artifact retrieval, local evidence, acceptance, and finalization tests remain passing.

---

## 7. Implementation constraints

Use the smallest coherent change.

Prefer:

- explicit domain types over loosely related dictionaries;
- stable reason codes over generic worker_unexpected;
- a single token semantics source of truth;
- preflight checks before provider calls;
- durable operation transitions;
- deterministic idempotent replay;
- explicit recovery actions;
- no artifact for incomplete output;
- fake gateway fixtures for all failure paths;
- backward-compatible schema evolution when possible.

Avoid:

- broad refactoring unrelated to the defect;
- adding a new dependency;
- changing routing policy;
- changing provider profiles;
- editing the existing workflow rows;
- swallowing exceptions into generic invalid_state;
- converting infrastructure failure into scientific/acceptance success;
- increasing output limit as the only fix;
- weakening approval boundaries;
- persisting raw secrets or full untrusted responses.

If the correct fix requires a database schema migration:

1. stop before applying it to the existing DB;
2. write the migration against temporary test DBs;
3. document forward/backward compatibility;
4. provide backup and rollback steps;
5. request explicit authorization before production-like DB migration.

---

## 8. Error-contract expectations

Use stable, sanitized reason codes. Exact names may differ if repository conventions require, but distinguish at least:

~~~text
budget_preflight_input_exceeds_limit
budget_preflight_reservation_exceeds_limit
worker_output_truncated
worker_structured_response_invalid
worker_refused
worker_provider_failed
worker_attempts_exhausted
live_dispatch_recovery_required
actual_usage_exceeds_reservation
~~~

Do not collapse these into worker_unexpected.

A same-request terminal replay should return the same stored result, not operation_not_replayable.

A new request for a task with exhausted attempts should return attempts_exhausted/revision_required without calling a provider.

---

## 9. Timeout design requirement

Choose and document one safe design:

### Option A — Asynchronous start and poll

- dispatch reserves and starts;
- returns an operation handle before transport timeout;
- caller polls the durable operation;
- same request is idempotent;
- provider completion persists independently.

### Option B — Synchronous with enforced margin

- provider timeout must be safely lower than MCP transport timeout;
- task timeout, provider timeout, and client wait are validated for consistency;
- durable recovery still exists for disconnects.

Do not leave provider timeout greater than transport timeout without a durable polling/recovery contract.

---

## 10. Documentation requirements

Update only the Orchestra docs needed to freeze the repaired contract. Document:

- token-limit field meanings;
- preflight reservation order;
- incomplete-response handling;
- no-artifact rule;
- diagnostic retrieval;
- idempotent replay;
- attempt exhaustion;
- timeout/recovery semantics;
- workflow next actions;
- migration requirements, if any.

Do not edit the Orchestra skill file in this task unless the implementation contract truly changes and the user separately authorizes updating the installed skill.

---

## 11. Verification commands

Discover exact project commands from pyproject.toml and README. Do not guess if the repository defines its own wrappers.

Run at minimum:

1. focused budget tests;
2. focused gateway tests;
3. live-dispatch service tests;
4. operations/idempotency tests;
5. model-call/journal/live persistence tests;
6. MCP live-tool and stdio tests;
7. cognition/live-proposal tests;
8. relevant e2e bridge tests;
9. full Orchestra test suite;
10. configured lint/type/static checks;
11. git diff --check.

Likely files include:

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
tests/mcp/test_live_schemas.py
tests/cognition/test_live_proposals.py
tests/e2e/test_codex_mcp_bridge.py
~~~

Report exact commands, exit codes, pass/fail/error/skip/xfail/xpass counts, and test duration.

Do not claim PASS based only on code review.

---

## 12. Mandatory deliverables

Create or update an Orchestra repair report at:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_REPORT_2026-08-02.md
~~~

If the docs/reports directory does not exist, create it inside the Orchestra worktree.

The report must contain:

1. starting Git state;
2. read files and authorities;
3. verified production-failure evidence;
4. root cause with file/function/line references;
5. RED tests and observed failures;
6. implementation decisions;
7. changed files;
8. token semantics before and after;
9. error semantics before and after;
10. recovery/idempotency behavior before and after;
11. partial diagnostic/artifact policy;
12. timeout design;
13. focused test results;
14. full-suite result;
15. static-check result;
16. git diff --check result;
17. database migration/compatibility assessment;
18. whether MCP restart/re-registration is required;
19. remaining risks;
20. proposed minimal real post-fix probe, without executing it;
21. explicit statement that no real provider call occurred;
22. final status.

Also create a machine-readable evidence file:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_EVIDENCE_2026-08-02.json
~~~

The JSON must contain:

- repository path;
- starting HEAD;
- changed files;
- test commands;
- exit codes;
- test counts;
- acceptance criteria O-C01 through O-C12;
- migration required boolean;
- MCP restart required boolean;
- real provider calls during repair;
- final status.

Do not fabricate hashes, command results, or test counts.

---

## 13. Acceptance checklist

The repair cannot be declared complete unless all are true:

- [ ] O-C01 impossible requests rejected before provider call;
- [ ] O-C02 token semantics unambiguous and tested;
- [ ] O-C03 max-output truncation is a typed incomplete outcome;
- [ ] O-C04 incomplete output never becomes proposal/evidence;
- [ ] O-C05 durable sanitized diagnostics available;
- [ ] O-C06 same-request terminal replay is idempotent;
- [ ] O-C07 attempt exhaustion is typed, not worker_unexpected;
- [ ] O-C08 timeout recovery prevents duplicate provider calls;
- [ ] O-C09 workflow next actions are coherent;
- [ ] O-C10 focused and full regression tests pass;
- [ ] O-C11 production-like DB remained untouched;
- [ ] O-C12 no real provider call occurred;
- [ ] Existing failed workflows remain unchanged;
- [ ] ReactionAgent files remain unchanged;
- [ ] No secret/base URL/credential exposure;
- [ ] No dependency/network mutation;
- [ ] git diff --check passes;
- [ ] Report and structured evidence are complete.

If any item fails, final status cannot be READY.

---

## 14. Required final response

Return:

1. one-sentence outcome;
2. root cause;
3. changed files;
4. RED-to-GREEN evidence;
5. focused and full test counts;
6. migration requirement;
7. MCP restart requirement;
8. remaining risk;
9. absolute paths to report and JSON evidence;
10. exact next step for ChatGPT review;
11. explicit real-provider-call count during repair;
12. final status.

End with exactly one of:

~~~text
READY_FOR_CHATGPT_ORCHESTRA_REVIEW
BLOCKED
FAILED
~~~

Do not commit, push, merge, migrate the production-like database, restart external services, or perform a real DeepSeek probe unless the user separately authorizes those actions after reviewing your report.

