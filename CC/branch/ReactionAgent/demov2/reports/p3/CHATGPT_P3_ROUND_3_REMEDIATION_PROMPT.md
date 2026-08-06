# ChatGPT P3 Round 3 Remediation Prompt

## 1. Mission

Repair the ReactionAgent P3 Strict Kernel after the failed ChatGPT Round 2 read-only audit. This is a targeted remediation round, not a redesign and not P4 implementation.

The current formal audit state is:

```text
CHATGPT_P3_ROUND_2_READ_ONLY_AUDIT = FAIL
P3_MACHINERY = FAIL_NEEDS_REMEDIATION
P3_REAL_EVIDENCE = BLOCKED
P3_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P4_INTEGRATION = BLOCKED
```

Implementation failures are `FAIL`; missing real snapshot, automatic donor, and strict learned atom mapper may remain honestly `BLOCKED`. A real-evidence blocker must never hide a machinery failure.

## 2. Worktree and runtime

Worktree:

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2
```

Expected branch:

```text
codex/p3-strict-kernel
```

Python:

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

Do not assume the P3 worktree has a local `.venv/bin/python`.

Before editing, run and record:

```bash
pwd
git branch --show-current
git status --short
git diff --stat
git diff --name-status
git ls-files --others --exclude-standard
```

Save the starting state to:

```text
reports/p3/P3_ROUND_3_STARTING_WORKTREE_STATE.md
```

The worktree contains inherited P0/P1 changes and P3 untracked files. Preserve them. Do not use `git reset`, `git checkout --`, `git restore`, `git clean`, destructive deletion, or any operation intended to make the worktree artificially clean.

Do not commit, push, merge, rebase, or cherry-pick.

## 3. Required reading

Read these files completely before modifying code:

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_2.md

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_2_AUDIT_EVIDENCE.json

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_2_REMEDIATION_WORKLOG.md

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_GATE_REPORT_ROUND_2.json

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_MUTATION_RESULTS_ROUND_2.json

/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/p3_p4_interface_manifest_round_2.json
```

Read the production and test files relevant to the findings:

```text
reaction_agent/p3/gate.py
reaction_agent/p3/fixtures.py
reaction_agent/p3/load.py
reaction_agent/p3/kernel.py
reaction_agent/p3/transform.py
reaction_agent/p3/schemas.py
reaction_agent/p3/store.py
reaction_agent/p3/manifest.py
reaction_agent/p3/generate.py
reaction_agent/p3/validate.py
reaction_agent/p3/retrieve.py

tests/p3/test_mutations.py
tests/p3/test_r2d_transform.py
tests/p3/test_r2e_generate.py
tests/p3/test_r2f_validate.py
tests/p3/test_r2g_interface.py
tests/p3/test_r2i_gate.py
tests/p3/test_r2j_reports.py

scripts/generate_p3_round2_reports.py
scripts/run_p3_gate.py
scripts/run_p3_preflight.py
```

Use `rg` to locate and read the actual final design, final plan, P3 prompt, frozen P0/P1 contracts, P2 authority, and relevant ADRs. Do not guess filenames:

```bash
rg --files plan training reports | sort
rg -n "P3|Strict Kernel|strict kernel|P3.*P4|Gate|mutation|snapshot|reaction_hash|transform_hash" plan training reports
```

Do not modify final design, final plan, ADRs, P0 contracts, or P1 contracts to make broken P3 code appear compliant.

## 4. Engineering discipline

For every finding below:

1. Add a real RED test that reproduces the defect through the relevant production path.
2. Record the RED command, exit code, observed failure, and output hash.
3. Make the smallest production change that fixes the invariant.
4. Run the targeted GREEN test.
5. Run relevant regressions.
6. Record the GREEN command, counts, exit code, and output hash.
7. Add an adversarial mutation that would fail if the fix regresses.

Do not:

- use `pytest.raises(Exception)` where a typed exception or failure code is available;
- weaken, delete, skip, or xfail an existing test;
- hardcode Gate PASS;
- hardcode baseline PASS;
- copy an expected failure code into an observed failure field;
- hardcode test counts;
- let fixtures masquerade as real evidence;
- install dependencies or access the network;
- call LLM, MCP, or Orchestra;
- modify legacy source, frozen contracts, or final documents to fit the implementation;
- commit, push, or merge.

## 5. R3-A — Gate artifact forgery

### Defect

`evaluate_gate_from_artifacts()` currently treats a truthy value under a recognized key as verified evidence. This forged payload incorrectly returns `PASS`:

```python
{
    "schema_hash": "not-a-schema-hash",
    "items": {"G01": "PASS"},
}
```

### Required fix

- Validate typed artifacts, not key presence.
- Recompute schema hashes from live schemas.
- Require the complete G01–G10 item set.
- Reject missing, duplicate, unknown, or invalid items.
- Bind each Gate item to validated evidence.
- Validate run/case/query/fold/snapshot namespace consistency.
- Validate evidence-kind semantics.
- A synthetic artifact must not satisfy a real-evidence item.
- A stored status string must never be authority.
- Any machinery invariant failure must make the overall verdict `FAIL`, even when other items are `BLOCKED`.

Required tests include fake hash, incomplete items, unknown item, truthy fake trace, namespace mismatch, synthetic-as-real, and a genuinely validated artifact case.

## 6. R3-B — Snapshot/reaction authority

### Defect

`recompute_train_view_hash()` covers fold, donor structural identity, and reaction IDs, but omits `ReactionRef.reaction_hash` and actual reaction content. The loader does not recompute or compare the reaction hash.

The following was reproduced:

```text
train_hash_unchanged_after_reaction_hash_forge=True
forged_reaction_hash_accepted=True
```

### Required fix

Define a canonical reaction authority preimage covering at least:

- reaction ID and normalized reaction;
- participants and mapped structures;
- mapping report;
- resolved lineages;
- source ledger;
- eligibility and donor eligibility;
- donor participant binding;
- component/schema versions.

Derive every `ReactionRef.reaction_hash` from that preimage. Include the complete, sorted reaction references and hashes in the train-view snapshot preimage. During load, recompute the actual reaction hash and compare it with the reference.

Use typed failures such as `REACTION_HASH_MISMATCH`, `REACTION_REF_BINDING_MISMATCH`, or equivalent explicit codes.

Required mutations include reaction hash, participant, mapped structure, mapping report, lineage, ledger, eligibility, and same reaction ID with changed content. Semantically irrelevant input ordering must not change the canonical hash.

## 7. R3-C — Transform hash collisions

### Defect

The transform preimage omits transferred `bonds_to` common anchors and their bond orders. `sorted(removed_sinks)` hashes only dictionary keys and drops sink participant values. `StrictTransformation` does not preserve removed sink assignments.

Reproduced result:

```text
transfer_anchor_semantics_changed=True
transform_hash_same_after_anchor_change=True
transform_id_same_after_anchor_change=True
strict_transform_has_removed_sink_assignments=False
```

### Required fix

Create a single canonical transform preimage used by both `canonical_transform_hash` and `transformation_id`. It must include:

- selected lineage and reaction authority hash;
- all bond edits and atom-state edits;
- transferred element, charge, H count, source participant;
- transferred bonds to common anchors, including atom map and bond order;
- internal transferred bonds;
- removed atom maps and exact map-to-sink participant assignments;
- donor site, local environment, preconditions, ledger requirements;
- versions and policies.

Add an explicit removed-sink structure to `StrictTransformation`. Validation must prove exact coverage of removed atoms, not merely that a ledger contains at least one sink.

Required collision tests must mutate anchor map, anchor order, internal bond, source participant, sink participant, charge, and H count. Each semantic change must change hash and ID. Reordering equivalent input collections must not.

## 8. R3-D — Bad reaction crashes kernel

### Defect

The reaction-load and transform-extraction exception branches pass `detail=exc` into `StageTraceEntry`, but the strict schema has no `detail` field. A malformed reaction therefore crashes the run with a Pydantic `ValidationError`.

### Required fix

- Add a declared, JSON-serializable typed diagnostic field or use an existing legal field.
- Store `str(exc)`, never an Exception object.
- Record reaction ID, component, and failure code.
- Isolate a bad reaction and continue processing other donor reactions.
- If every reaction fails, return a structured result with typed failures.
- Preserve the system/scientific failure distinction.

Required kernel-level tests must cover one good plus one bad reaction, all reactions bad, loader failure, transform failure, deterministic replay, and JSON serialization of the trace.

## 9. R3-E — CandidateEvidencePath integrity

### Defect

`StrictCandidate` only checks that each path source ledger appears in the parent list. Forged path transformation and forged nested candidate-ledger source IDs pass model validation:

```text
forged_path_transform_accepted=True
forged_path_ledger_accepted=True
```

### Required fix

Enforce:

- generation report transformation equals path transformation;
- generation report site equals path site;
- nested candidate ledger source equals path source ledger;
- nested candidate ledger candidate ID equals parent candidate ID;
- path validation satisfies strict-lane rules;
- path transformation/site/lineage/source IDs belong to the parent;
- parent ID sets exactly equal the union of path IDs;
- parent generation paths exactly correspond to path generation reports;
- strict candidates have at least one evidence path;
- namespaces and evidence kinds are consistent.

Add a content-addressed path ID/hash or an equivalent immutable binding. Include donor, reaction, lineage, transformation, site, generation, source ledger, and candidate ledger in its preimage.

Mutate every linkage independently and prove validation fails.

## 10. R3-F — Real mutation evidence

### Defect

The Round 2 mutation harness only observes pytest `PASSED/FAILED/ERROR`, then hardcodes `baseline_status="PASS"` and copies `expected_failure_code` into `observed_failure_code`.

### Required fix

Each mutation definition must provide an executable baseline case and mutated case. Run them separately and record actual:

- baseline status, exit code, artifact hash, failure code;
- mutated status, exit code, artifact hash, observed failure code;
- command, duration, and stdout/stderr hash.

Rules:

- baseline not PASS -> `INVALID_BASELINE` and Gate FAIL;
- mutation PASS -> escaped mutation and Gate FAIL;
- mutation ERROR -> Gate FAIL;
- observed code mismatch -> Gate FAIL;
- helper-only test that does not exercise the relevant production path -> invalid mutation evidence.

Include mutations for A/B-only stripped reaction, deleted participant, partial mapping, missing lineage, precondition skip, forged ledger, fold pollution, relaxed edit, system-as-abstention, forged Gate PASS, reaction hash forgery, transform hash collision, forged evidence path, and bad-reaction kernel crash.

## 11. R3-G — Pytest count integrity

### Defect

Round 2 evidence records `collected=0` with positive passed counts, and `_fail_closed()` accepts it.

### Required fix

- Record a trustworthy, nonzero collected count.
- Derive it consistently from the pytest summary or run a separate collect-only command.
- Verify collected count against all outcome categories without double counting.
- Treat zero, missing, malformed, interrupted, timeout, or inconsistent summaries as fail-closed.

Add parser tests for successful quiet output, failures, errors, skipped/xfailed/xpassed, no-tests, collection errors, malformed output, ANSI output, warning summaries, interruptions, and timeouts.

## 12. R3-H — Git-state-dependent test

### Defect

`test_changed_files_derived_from_git_state` requires P3 files to be untracked. It passes only in the current dirty worktree and fails in an isolated or committed checkout. Independent result was `174 passed, 1 failed`.

### Required fix

Test Git behavior using a temporary Git repository created with `tmp_path`. Explicitly create clean tracked, modified tracked, untracked, and ignored files. Do not inspect or require the real project to be dirty.

The report must distinguish:

- inherited tracked modifications;
- inherited untracked files;
- Round 3 modified files;
- Round 3 new files;
- generated reports.

Capture structured Git state at the beginning and end, then calculate the Round 3 delta. Do not label the entire final dirty state as this round's changes.

## 13. R3-I — P3-to-P4 manifest completeness

### Defect

The current manifest omits nested records that P4 actually consumes, including `CandidateEvidencePath`, `GenerationReport`, `CandidateValidation`, and `CandidateAnalogyLedger`.

### Required fix

Generate the manifest from live Pydantic models. Include all P4-consumed models, fields, required fields, JSON schema hashes, namespace contract, evidence-kind semantics, and ID/hash preimage contract.

Choose and implement one explicit nested-record contract:

1. every independently transmitted nested record carries the full run namespace and evidence kind; or
2. nested records cannot be used independently and are cryptographically/content-addressedly bound to the parent namespace and path hash.

Do not leave the behavior implicit. Manifest tampering and live-schema drift must be detected by tests.

## 14. Behaviors that must not regress

Preserve all of the following:

- negative formal charges are valid;
- isotope-preserving identity distinguishes isotope labels;
- query and product identity share the same policy;
- fixture outputs remain `synthetic_fixture`;
- fixture evidence cannot satisfy real-evidence Gate items;
- caller fold mismatch is rejected;
- one donor retains every eligible reaction;
- kernel traverses donor × all eligible reactions;
- wrong products with equal heavy-atom counts fail replay;
- forged source ledger is rejected;
- critical contradiction cannot enter strict lane;
- missing graph-edit endpoints, anchors, and targets fail with typed codes;
- candidate merge retains every evidence path;
- RDKit chemistry, explicit-map validation, strict learned mapping, and MCS diagnostics remain separate capabilities;
- system failure remains separate from scientific abstention;
- P3 never delegates structure creation to an LLM;
- P3 produces unranked strict candidates; P4 owns ranking and abstention;
- missing real resources remain honestly `BLOCKED`.

The octanol donor reactions `fx_oct` and `fx_oct_dehyd` must both continue through the kernel.

## 15. Required verification

Use:

```bash
P3_PY=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

Run at least:

```bash
$P3_PY -m pytest tests/p3 -q -p no:cacheprovider --color=no
$P3_PY -m pytest tests -q -p no:cacheprovider --color=no
$P3_PY -m pytest tests/p3/test_mutations.py -q -p no:cacheprovider --color=no
$P3_PY scripts/run_p0_gate.py
$P3_PY scripts/run_p1_gate.py
$P3_PY scripts/run_p3_preflight.py
$P3_PY scripts/run_p3_gate.py
```

Run every new targeted test and prove `tests/p3` also passes in an isolated/clean Git-state fixture.

Expected Gate semantics:

- PASS exit 0;
- FAIL exit 1;
- BLOCKED exit 2;
- machinery failure dominates blockers and produces FAIL;
- after machinery is fixed, unavailable real resources may keep the formal P3 Gate BLOCKED with exit 2;
- P0 and P1 Gates must remain exit 0, or the real failure must be reported without fabrication.

## 16. Structured evidence contract

Every command record must include:

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

Every remediation finding must include:

```text
finding_id
severity
red_test
red_command
red_exit_code
red_observed_failure
fix_files
green_test
green_command
green_exit_code
green_counts
green_stdout_hash
adversarial_probe
adversarial_result
status
```

A one-line assertion that a finding went RED-to-GREEN is not sufficient.

## 17. Round 3 deliverables

Do not overwrite Round 2 files. Generate:

```text
reports/p3/P3_ROUND_3_STARTING_WORKTREE_STATE.md
reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_3.md
reports/p3/P3_ROUND_3_AUDIT_EVIDENCE.json
reports/p3/P3_ROUND_3_REMEDIATION_WORKLOG.md
reports/p3/P3_GATE_REPORT_ROUND_3.json
reports/p3/P3_GATE_REPORT_ROUND_3.md
reports/p3/P3_MUTATION_RESULTS_ROUND_3.json
reports/p3/p3_p4_interface_manifest_round_3.json
reports/p3/P3_ROUND_3_CHANGED_FILES.json
```

If a new generator is needed, use:

```text
scripts/generate_p3_round3_reports.py
```

The submission must explicitly answer every R3-A through R3-I finding, show real RED/GREEN/adversarial evidence, list exact commands and counts, separate inherited changes from Round 3 changes, declare real versus fixture evidence, list capabilities and blockers, publish the P3-to-P4 schema hashes, and state whether P4 may proceed.

## 18. Completion and terminal status

Round 3 is complete only if:

- all R3-A through R3-I findings have real RED-to-GREEN evidence;
- all adversarial probes are caught through production paths;
- P3 and full tests pass with valid nonzero counts;
- P0 and P1 Gates remain green;
- P3 has no machinery invariant failure;
- real blockers remain honestly labeled;
- the interface manifest is complete and recomputable;
- no prohibited operation occurred.

If all machinery fixes are complete but real resources remain unavailable, the final line of the submission must be exactly:

```text
P3_ROUND_3_IMPLEMENTATION_READY_GATE_BLOCKED_PENDING_CHATGPT_READ_ONLY_AUDIT
```

If any machinery failure or required evidence remains incomplete, use exactly:

```text
P3_ROUND_3_REMEDIATION_INCOMPLETE_NOT_READY_FOR_CHATGPT_ACCEPTANCE
```

Do not claim P3 PASS, production readiness, or P4 unblocked.

After completing the work, return only:

1. absolute path to the Round 3 submission;
2. absolute path to structured evidence;
3. absolute path to the remediation worklog;
4. absolute path to the P3 Gate report;
5. concise real test/Gate results;
6. the exact terminal status;
7. these lines:

```text
READY_FOR_CHATGPT_P3_ROUND_3_READ_ONLY_AUDIT
P4_BLOCKED_PENDING_CHATGPT_AUDIT
```

Then stop. Do not start P4 and do not merge.
